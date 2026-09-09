#!/usr/bin/env node
// check-version.mjs — 单命令检查 publish-work-to-gallery 技能版本是否过时（零依赖，内部调用 api.mjs）。
// 自动读取本技能 SKILL.md frontmatter 的 version: 作为本地版本，
// 并经 api.mjs 请求平台 open-api-guest /v1/gallery/skills/version?name=<本技能名> 获取远端版本；
// 仅在「本地 < 远端」时经 /prompt 取 skills|outdated 文案后输出。
// 版本格式: YYYY.MM.DD[.NNN]（.NNN 可省略，缺段按 0 比较）。
// exit 0 = status=ok（本地 ≥ 远端）或 status=skip（平台不可达/解析失败 → 不阻塞发布）;
// exit 1 = status=outdated（技能已过时，须提示用户升级并停止发布，stdout 含平台下发文案）。
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

function parse(v) {
  if (typeof v !== "string" || !v.trim()) return null;
  const parts = v.trim().split(".");
  if (parts.length < 3 || parts.length > 4) return null;
  const nums = parts.map((p) => (/^\d+$/.test(p) ? Number(p) : NaN));
  if (nums.some((n) => Number.isNaN(n))) return null;
  while (nums.length < 4) nums.push(0);
  return nums;
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
const local = frontmatterValue(fm, "version");
const remoteRes = runApiGet(["/v1/gallery/skills/version", "--prefix", "open-api-guest", "--query", `name=${skillName}`]);
const remote =
  remoteRes.status >= 200 && remoteRes.status < 300 && typeof remoteRes.data?.data?.version === "string"
    ? remoteRes.data.data.version
    : null;

const a = parse(local);
const b = parse(remote);
if (!a || !b) {
  // 本地或远端版本无法解析/平台未返回有效版本：跳过升级判定，不阻塞发布
  console.log("status=skip");
  process.exit(0);
}
for (let i = 0; i < 4; i += 1) {
  if (a[i] < b[i]) {
    const promptRes = runApiGet(["/v1/gallery/prompt", "--prefix", "open-api-guest", "--query", "type=skills&target=outdated&params={}"]);
    const prompt = typeof promptRes.data?.data?.prompt === "string" ? promptRes.data.data.prompt.trim() : "";
    console.log("status=outdated");
    if (prompt) console.log(prompt);
    process.exit(1);
  }
  if (a[i] > b[i]) break;
}
console.log("status=ok");
process.exit(0);