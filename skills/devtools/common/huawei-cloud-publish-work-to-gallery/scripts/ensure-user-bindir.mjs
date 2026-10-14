#!/usr/bin/env node
// ensure-user-bindir.mjs — 选定并落位用户级工具目录（免管理员），幂等写入用户 PATH。
//
// 背景:
//   各工具（hcloud/devbridge/gitcode-oauth）此前散装不同目录（~/.huawei/bin、D:\tools、
//   %TEMP% 等），发现逻辑各自硬编码候选，既不统一也不可维护。本脚本收敛为单一源头：
//
//   目录选择（Windows，免管理员，按优先级选第一个可写）:
//     ① %LOCALAPPDATA%\Programs\.huawei\bin    主路径（与 VS Code 用户安装同款惯例）
//     ② %USERPROFILE%\.local\bin               备选
//     ③ %TEMP%\.huawei\bin                     兜底（⚠️ 重启后可能被清理，非持久）
//   Linux/macOS: ~/.local/bin（跨平台惯例）
//
//   行为:
//   1. 按优先级探测候选目录：存在即用；不存在则尝试创建；不可写则跳过下一个。
//   2. 把选中的目录幂等写入「用户 PATH」（去重、保留 %VAR% 不展开、剔除不存在目录防死链）。
//      （Windows 写用户作用域 HKCU\Environment，不碰系统 PATH；Linux 写 ~/.bashrc export。）
//   3. stdout 一行 `#bindir=<abs> level=primary|fallback1|fallback2|unix`；失败 exit 1。
//
// 用法:
//   node ensure-user-bindir.mjs [--dry-run]
//   --dry-run  只探测输出，不创建目录、不改 PATH（供排查）
//
// 退出码: 0=成功（目录就绪且已在 PATH）; 1=无可写目录/参数错误

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, unlinkSync, readFileSync, appendFileSync } from "node:fs";
import { homedir, platform, tmpdir } from "node:os";
import path from "node:path";

const isWin = platform() === "win32";
const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");

if (args.includes("-h") || args.includes("--help")) {
  console.log(`ensure-user-bindir.mjs — 选定用户级工具目录并写入用户 PATH

用法:
  node ensure-user-bindir.mjs [--dry-run] [--print-path]

Windows 候选（免管理员，按优先级）:
  ① %LOCALAPPDATA%\\Programs\\.huawei\\bin
  ② %USERPROFILE%\\.local\\bin
  ③ %TEMP%\\.huawei\\bin        （非持久，重启后可能被清理）
Linux/macOS: ~/.local/bin

--print-path  仅输出当前用户 PATH（分号/冒号拼接），供 PATH-only 发现合并（新写入对当前进程不生效时用）

退出码: 0=目录就绪且在 PATH; 1=失败`);
  process.exit(0);
}

// ---- 候选目录 ----
function candidates() {
  if (!isWin) {
    return [{ dir: path.join(homedir(), ".local", "bin"), level: "unix" }];
  }
  const localAppData = process.env.LOCALAPPDATA || path.join(homedir(), "AppData", "Local");
  const tmp = process.env.TEMP || tmpdir();
  return [
    { dir: path.join(localAppData, "Programs", ".huawei", "bin"), level: "primary" },
    { dir: path.join(homedir(), ".local", "bin"), level: "fallback1" },
    { dir: path.join(tmp, ".huawei", "bin"), level: "fallback2" },
  ];
}

// 写探测：目录能建、能写临时文件即视为可用（无需真实落可执行，避免误报不可写）
function probeWritable(dir) {
  try {
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const probe = path.join(dir, `.bindir-probe-${process.pid}.tmp`);
    writeFileSync(probe, "ok", "utf8");
    unlinkSync(probe);
    return true;
  } catch {
    return false;
  }
}

// ---- 读/写 用户 PATH ----
function readUserPath() {
  if (isWin) {
    try {
      const out = execFileSync("reg", ["query", "HKCU\\Environment", "/v", "Path"], {
        encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"],
      });
      const line = out.split(/\r?\n/).find((l) => /REG_(?:EXPAND_)?SZ/.test(l));
      if (!line) return [];
      return line.replace(/^.*REG_(?:EXPAND_)?SZ\s+/, "").trim().split(";").map((s) => s.trim()).filter(Boolean);
    } catch {
      return [];
    }
  }
  try {
    const rc = path.join(homedir(), ".bashrc");
    if (!existsSync(rc)) return [];
    const m = readFileSync(rc, "utf8").match(/^\s*export\s+PATH\s*=\s*["']?([^"'\n]+)["']?\s*$/m);
    return m ? m[1].split(":").filter(Boolean) : [];
  } catch {
    return [];
  }
}

function writeUserPath(entries) {
  if (dryRun) return;
  if (isWin) {
    execFileSync("reg", ["add", "HKCU\\Environment", "/v", "Path", "/t", "REG_EXPAND_SZ", "/d", entries.join(";"), "/f"], {
      encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"],
    });
    return;
  }
  try {
    const rc = path.join(homedir(), ".bashrc");
    if (entries[0] && existsSync(rc) && !readUserPath().includes(entries[0])) {
      appendFileSync(rc, `\nexport PATH="${entries[0]}:$PATH"\n`, "utf8");
    }
  } catch {}
}

// Windows: 把 %VAR% 展开成实际路径（供死链判断）；展开失败则原样返回
function expandVar(s) {
  if (!isWin) return s;
  try {
    const r = execFileSync("powershell", ["-NoProfile", "-Command", `[Environment]::ExpandEnvironmentVariables('${s}')`], {
      encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"],
    });
    return r.trim() || s;
  } catch {
    return s;
  }
}

function norm(s) { return s.replace(/[\\/]+$/g, "").toLowerCase(); }

// 幂等写入：去重 + 剔除不存在目录（防死链）+ 确保含目标目录
function ensurePathEntry(dir) {
  const current = readUserPath();
  if (!current) { writeUserPath([dir]); return; }
  const seen = new Set();
  const out = [];
  let present = false;
  for (const e of current) {
    const nn = norm(e);
    if (nn === norm(dir)) { present = true; continue; }
    if (seen.has(nn)) continue;
    seen.add(nn);
    // 死链清理：展开后不存在则剔除（保留含无法展开 %VAR% 的条目）
    const expanded = expandVar(e);
    if (expanded.includes("%")) { out.push(e); continue; }
    if (expanded && !existsSync(expanded)) continue;
    out.push(e);
  }
  if (!present) out.push(dir);
  writeUserPath(out);
}

// ---- 主流程 ----
if (args.includes("--print-path")) {
  // 供 PATH-only 发现逻辑合并：输出当前用户 PATH 原始串（Windows 分号 / POSIX 冒号）
  const sep = isWin ? ";" : ":";
  console.log(readUserPath().join(sep));
  process.exit(0);
}

for (const { dir, level } of candidates()) {
  if (!probeWritable(dir)) {
    if (!dryRun) console.error(`[ensure-user-bindir] 不可写（跳过）: ${dir}`);
    continue;
  }
  if (!dryRun) ensurePathEntry(dir);
  console.log(`#bindir=${dir} level=${level}`);
  process.exit(0);
}
console.error("❌ 所有候选目录均不可写。Windows 请检查用户 profile 权限；或用 --dry-run 排查。");
process.exit(1);