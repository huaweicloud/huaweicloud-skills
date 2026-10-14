#!/usr/bin/env node
// check-version.mjs — 单命令检查技能是否过时（零依赖，内部调用 api.mjs）。
// 读取本技能 SKILL.md frontmatter 的 name 与本地 version（兼容顶层 `version:` 与嵌套 `metadata.version:`），
// 调平台 open-api-guest /v1/gallery/skills/status?name=<本技能名>&version=<本地版本> 查询状态：
//   pass / skip → 不拦截（status=ok / status=skip，exit 0）；outdated → status=outdated + 平台下发升级文案，exit 1。
// 判定逻辑（含版本比较、已登记/未登记、version 缺失）统一在平台侧；
// 平台不可达/响应异常 → status=skip（尽力而为，不阻塞发布）。
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(__dirname, "..");

function frontmatter() {
  try {
    const md = fs.readFileSync(path.join(skillRoot, "SKILL.md"), "utf8");
    const m = md.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    return m ? m[1] : "";
  } catch {
    return "";
  }
}

function frontmatterValue(block, key) {
  const m = block.match(new RegExp(`^${key}\\s*:\\s*(.+?)\\s*$`, "m"));
  return m ? m[1].trim() : "";
}

// 本地版本：兼容顶层 `version:` 与嵌套 `metadata.version:`（缩进不定，取首个匹配）。
function frontmatterVersion(block) {
  const m = block.match(/^\s*version\s*:\s*(.+?)\s*$/m);
  return m ? m[1].trim() : "";
}

function runApiGet(args) {
  try {
    const out = execFileSync(process.execPath, [path.join(__dirname, "api.mjs"), "GET", ...args], {
      encoding: "utf8",
      timeout: 6000,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let status = 0;
    let data = null;
    for (const raw of String(out).split(/\r?\n/)) {
      if (status === 0 && raw.startsWith("#status=")) {
        status = Number(raw.slice(8)) || 0;
      } else {
        const t = raw.trim();
        if (!data && t.startsWith("{")) {
          try { data = JSON.parse(t); } catch { data = null; }
        }
      }
    }
    return { status, data };
  } catch {
    return { status: 0, data: null };
  }
}

const fm = frontmatter();
const skillName = frontmatterValue(fm, "name") || "publish-work-to-gallery";
const local = frontmatterVersion(fm);

// 本地 version 缺失/无法解析时按空串上报：已登记技能由平台判为 outdated（极老技能强制升级）；未登记技能平台返回 skip。
const statusRes = runApiGet(["/v1/gallery/skills/status", "--prefix", "open-api-guest", "--query", `name=${skillName}&version=${local}`]);
const status = typeof statusRes.data?.data?.status === "string" ? statusRes.data.data.status : null;

if (status === "pass") {
  console.log("status=ok");
  process.exit(0);
}
if (status === "skip") {
  console.log("status=skip");
  process.exit(0);
}
if (status === "outdated") {
  let prompt = typeof statusRes.data?.data?.prompt === "string" ? statusRes.data.data.prompt.trim() : "";
  if (!prompt) {
    // 兜底：响应未带文案时经 /prompt 拉取 skills|outdated（按本技能名渲染）。
    const promptRes = runApiGet(["/v1/gallery/prompt", "--prefix", "open-api-guest", "--query", `type=skills&target=outdated&params=${encodeURIComponent(JSON.stringify({ skillName }))}`]);
    prompt = typeof promptRes.data?.data?.prompt === "string" ? promptRes.data.data.prompt.trim() : "";
  }
  console.log("status=outdated");
  if (prompt) console.log(prompt);
  process.exit(1);
}
// 平台不可达/响应异常 → 尽力而为
console.log("status=skip");
process.exit(0);