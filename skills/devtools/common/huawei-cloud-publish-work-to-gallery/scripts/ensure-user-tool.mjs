#!/usr/bin/env node
// ensure-user-tool.mjs — 用户级工具统一「解析 → 验证 → 落盘 → 供读取」（单一入口，PATH + 预装路径探测 + 自动安装）
//
// 形态:
//   一次调用完成工具路径解析：读索引 → 命中且可用直接返回；否则按 PATH → 预装路径探测 → bindir → 自动安装，
//   任一命中即写入索引（<bindir 上级>/tools-index.json）供各执行程序直接读取，无需重复检索。
//
// 支持工具:
//   gitcode-oauth  官方 release 预编译下载；冒烟 --help
//
// 2026-09-20：devbridge 不再由本脚本管理——隧道按仓库技能 huawei-cloud-devbridge-tunnel
// （skills/devtools/devbridge/huawei-cloud-devbridge-tunnel）说明执行，见 SKILL.md Step 2 / devbridge-tunnel.md；Windows 不使用 DevBridge。
//
// 索引文件: <工具目录上级>/tools-index.json
//   { "gitcode-oauth": {...} }
//   读索引后必须校验 path 存在且可运行（防死链），失败即走自愈重解析。
//
// 用法:
//   node ensure-user-tool.mjs --tool <gitcode-oauth> [--print] [--force-refresh]
//   --print          仅输出索引 JSON 原文（供外部读取，不触发解析/安装）
//   --force-refresh  忽略索引直接重解析
//
// 输出（stdout 单行契约）:
//   #tool=<name> path=<abs> source=cache|path|probe|bindir|installed
//   #tool=<name> missing reason=<…>（exit 1）
//
// 退出码: 0=就绪（path 可用）; 1=解析/安装失败

import { execSync, spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync, chmodSync } from "node:fs";
import { homedir, platform } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const isWin = platform() === "win32";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPTS = __dirname;

const args = process.argv.slice(2);
let tool = "";
let printOnly = false;
let forceRefresh = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--tool") tool = args[++i] || "";
  else if (args[i] === "--print") printOnly = true;
  else if (args[i] === "--force-refresh") forceRefresh = true;
  else if (args[i] === "-h" || args[i] === "--help") {
    console.log(`ensure-user-tool.mjs — 用户级工具统一解析/落盘

用法:
  node ensure-user-tool.mjs --tool <gitcode-oauth> [--force-refresh]
  node ensure-user-tool.mjs --print
  node ensure-user-tool.mjs --print --tool <gitcode-oauth>

输出:
  #tool=<name> path=<abs> source=cache|path|probe|bindir|installed   (exit 0)
  #tool=<name> missing reason=<…>                              (exit 1)

--print          输出索引 JSON（--tool 指定则只输出该工具条目，resolve 轴不触发解析/安装）
--force-refresh   忽略索引重解析（网络安装时用）
退出码: 0=就绪; 1=失败`);
    process.exit(0);
  }
}
if (!tool && !printOnly) { console.error("❌ 缺 --tool <gitcode-oauth>"); process.exit(2); }

// ---- 工具配置 ----
const TOOLS = {
  "gitcode-oauth": {
    exe: isWin ? "gitcode-oauth.exe" : "gitcode-oauth",
    smoke: ["--help"],
    install: installGitcodeOauth,
  },
};
const cfg = TOOLS[tool];
if (!cfg && !printOnly) { console.error(`❌ 不支持的 tool: ${tool}`); process.exit(2); }

// ---- bindir + 索引 ----
function readBindir() {
  try {
    const out = execSync(`node "${path.join(SCRIPTS, "ensure-user-bindir.mjs")}"`, {
      encoding: "utf8", timeout: 20000, stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    return out.match(/#bindir=(\S+)/)?.[1] || "";
  } catch { return ""; }
}
function indexPath(bindir) {
  // 索引放 bindir 上级（工具目录根），避免扫 bin 目录本身
  return path.join(path.dirname(bindir), "tools-index.json");
}
function readIndex() {
  const bindir = readBindir();
  if (!bindir) return { bindir: "", index: {} };
  try { return { bindir, index: JSON.parse(readFileSync(indexPath(bindir), "utf8")) }; }
  catch { return { bindir, index: {} }; }
}
function writeIndex(bindir, index) {
  try {
    const f = indexPath(bindir);
    mkdirSync(path.dirname(f), { recursive: true });
    writeFileSync(f, JSON.stringify(index, null, 2), "utf8");
  } catch {}
}

// ---- 冒烟校验：存在 + 可运行（stdio ignore，零 token）----
function isUsable(exe) {
  if (!exe || !existsSync(exe)) return false;
  const r = spawnSync(exe, cfg.smoke, { stdio: "ignore", timeout: 15000 });
  return !r.error && r.status === 0;
}

// ---- 能力门禁（仅在工具配置了 requireCapability 时生效）----
function hasRequiredCapability(exe) {
  if (!cfg.requireCapability) return true;
  if (!exe || !existsSync(exe)) return false;
  try {
    const r = spawnSync(exe, ["auth", "login", "--help"], { encoding: "utf8", timeout: 15000 });
    if (r.status !== 0) return false;
    const out = `${r.stdout || ""}${r.stderr || ""}`;
    return cfg.requireCapability.every((flag) => out.includes(flag));
  } catch {
    return false;
  }
}

// ---- PATH（合并注册表用户 PATH，规避当前进程缓存）----
function mergeUserPathIntoEnv() {
  try {
    const sep = isWin ? ";" : ":";
    const userPath = execSync(`node "${path.join(SCRIPTS, "ensure-user-bindir.mjs")}" --print-path`, {
      encoding: "utf8", timeout: 20000, stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    if (!userPath) return;
    const existing = new Set((process.env.PATH || "").split(sep).map((s) => s.trim()).filter(Boolean));
    const merged = [...new Set(userPath.split(sep))].filter((p) => p && !existing.has(p));
    if (merged.length) process.env.PATH = merged.join(sep) + sep + (process.env.PATH || "");
  } catch {}
}
function findOnPath(exe) {
  mergeUserPathIntoEnv();
  try {
    const cmd = isWin ? `where ${exe}` : `which ${exe}`;
    const out = execSync(cmd, { encoding: "utf8", timeout: 10000, stdio: ["ignore", "pipe", "ignore"] }).trim();
    if (out) return out.split(/\r?\n/)[0].trim();
  } catch {}
  return "";
}

// ---- 常见预装路径探测（华为云环境预置 / 运行时目录，不在 PATH 也能发现）----
function findInProbePaths() {
  const paths = cfg.probePaths;
  if (!paths || paths.length === 0) return "";
  for (const p of paths) {
    if (isUsable(p) && hasRequiredCapability(p)) return p;
  }
  return "";
}

// ---- 自动安装 ----
function installGitcodeOauth(bindir) {
  const dest = path.join(bindir, cfg.exe);
  if (isUsable(dest)) return dest;
  try {
    const api = "https://api.gitcode.com/api/v5/repos/zhoucungen/gitcode-oauth/releases?per_page=1";
    const tag = JSON.parse(execSync(`curl -sf --max-time 15 "${api}"`, { encoding: "utf8", timeout: 20000, stdio: ["ignore", "pipe", "ignore"] }))[0]?.tag_name;
    if (!tag) return "";
    const osName = isWin ? "windows" : (platform() === "darwin" ? "darwin" : "linux");
    const arch = process.arch === "arm64" ? "arm64" : "amd64";
    const suffix = isWin ? ".exe" : "";
    const url = `https://gitcode.com/zhoucungen/gitcode-oauth/releases/download/${tag}/gitcode-oauth-${osName}-${arch}${suffix}`;
    const tmp = `${dest}.tmp-${process.pid}`;
    execSync(`curl -sfL --max-time 120 "${url}" -o "${tmp}"`, { stdio: "ignore", timeout: 140000 });
    if (process.platform !== "win32") chmodSync(tmp, 0o755);
    renameSync(tmp, dest);
  } catch { return ""; }
  return isUsable(dest) ? dest : "";
}

// ---- 主流程 ----
const { bindir, index } = readIndex();

if (printOnly) {
  const out = tool ? { [tool]: index[tool] || null } : index;
  console.log(JSON.stringify({ bindir, index: out }));
  process.exit(0);
}

// 1) 索引命中（cache）
if (!forceRefresh) {
  const cached = index[tool]?.path;
  if (isUsable(cached) && hasRequiredCapability(cached)) { console.log(`#tool=${tool} path=${cached} source=cache`); process.exit(0); }
}

// 2) PATH
const onPath = findOnPath(cfg.exe);
if (isUsable(onPath) && hasRequiredCapability(onPath) && !forceRefresh) {
  index[tool] = { path: onPath, verifiedAt: new Date().toISOString() };
  writeIndex(bindir, index);
  console.log(`#tool=${tool} path=${onPath} source=path`);
  process.exit(0);
}

// 3) 常见预装路径探测（华为云环境预置 gitcode-oauth 等，不在 PATH 也能发现）
if (!forceRefresh) {
  const probed = findInProbePaths();
  if (probed) {
    index[tool] = { path: probed, verifiedAt: new Date().toISOString() };
    writeIndex(bindir, index);
    console.log(`#tool=${tool} path=${probed} source=probe`);
    process.exit(0);
  }
}

// 4) bindir 已有
if (bindir) {
  const inBindir = path.join(bindir, cfg.exe);
  if (isUsable(inBindir) && hasRequiredCapability(inBindir)) {
    index[tool] = { path: inBindir, verifiedAt: new Date().toISOString() };
    writeIndex(bindir, index);
    console.log(`#tool=${tool} path=${inBindir} source=bindir`);
    process.exit(0);
  }
}

// 5) 自动安装
if (bindir) {
  const dest = cfg.install(bindir);
  if (dest && hasRequiredCapability(dest)) {
    index[tool] = { path: dest, verifiedAt: new Date().toISOString() };
    writeIndex(bindir, index);
    console.log(`#tool=${tool} path=${dest} source=installed`);
    process.exit(0);
  }
}

console.log(`#tool=${tool} missing reason=parse_or_install_failed`);
console.error(`${tool} 解析/安装失败（无 PATH 命中、无 bindir 或安装失败）。请检查网络/权限或手动安装到用户级工具目录。`);
process.exit(1);