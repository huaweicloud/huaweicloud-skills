#!/usr/bin/env node
// ensure-utf8.mjs — 渲染（截图 / 封面 / 图表）前强制「HTML/CSS 声明编码 == 实际 UTF-8」门禁（fail-stop）
//
// 背景:
//   UTF-8 字节被 `iso-8859-1` 解码会 mojibake（如「扫雷游戏」→「æ‰«é›·æ¸¸æˆÏ」）。
//   HTML 的 <meta charset> 与 CSS 的 @charset 是两个独立的编码声明单元——
//   HTML 声明正确不代表 CSS 也正确，CSS 的 @charset 错误会导致
//   content: "中文"、font-family: "微软雅黑" 等被按错误编码解码 → 乱码/字体匹配失败。
//   本脚本对要截图/嵌入封面的源码目录做编码归一（HTML + CSS）：声明非 UTF-8 但字节是
//   UTF-8 则改写声明、缺声明则插入 UTF-8，字节非合法 UTF-8 则 fail-stop。
// 用法、选项、退出码详见 node ensure-utf8.mjs --help。

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const target = process.argv[2];
if (target === "-h" || target === "--help") {
  console.log(`ensure-utf8.mjs — 渲染前强制「HTML/CSS 声明编码 == 实际 UTF-8」门禁（fail-stop）

用法:
  node ensure-utf8.mjs <dir> [--marker=<path>]

位置参数:
  <dir>                要扫描的目录（递归处理 .html/.htm/.css）

选项:
  --marker=<path>      标记文件路径（默认 /tmp/utf8-gate-ok，Windows: os.tmpdir()/utf8-gate-ok）
  -h, --help           显示本帮助

行为:
  HTML (.html/.htm):
    - <meta charset> 声明为非 UTF-8 但字节实际是 UTF-8 → 自动改 meta 为 UTF-8
    - 含非 ASCII 却缺 <meta charset> → 自动插入 UTF-8 声明
  CSS (.css):
    - @charset 声明为非 UTF-8 但字节实际是 UTF-8 → 自动改 @charset 为 UTF-8
    - 含非 ASCII 却缺 @charset → 自动在文件首插入 @charset "UTF-8";
  通用:
    - 字节非合法 UTF-8（如 GBK）→ exit 1（fail-stop）

退出码: 0=通过并写标记; 1=编码门禁未通过; 2=参数错误
`);
  process.exit(0);
}
if (!target) {
  console.error("❌ 用法: node ensure-utf8.mjs <dir>\n  运行 node ensure-utf8.mjs --help 查看完整用法。");
  process.exit(2);
}

const markerArg = process.argv.find((a) => a.startsWith("--marker="));
const MARKER = markerArg
  ? markerArg.slice("--marker=".length)
  : path.join(os.tmpdir(), "utf8-gate-ok");

const EXT = new Set([".html", ".htm", ".css"]);

function isAscii(buf) {
  for (let i = 0; i < buf.length; i++) if (buf[i] > 0x7f) return false;
  return true;
}

// 返回: { headEnd: 在原始 Buffer 中 <head...> 的最佳插入点（'>' 之后 0 号下标），found }
// 只找第一个 <head ...> 或 <html>。找不到则用文件头。
function findHeadInsert(buf) {
  const s = buf.toString("latin1");
  const headOpen = /<head\b[^>]*>/i.exec(s);
  if (headOpen) return { at: Buffer.byteLength(s.slice(0, headOpen.index + headOpen[0].length), "latin1"), ok: true };
  const htmlOpen = /<html\b[^>]*>/i.exec(s);
  if (htmlOpen) return { at: Buffer.byteLength(s.slice(0, htmlOpen.index + htmlOpen[0].length), "latin1"), ok: true };
  return { at: 0, ok: false };
}

// 只要字节恰是合法 UTF-8（且不含非 ASCII 之外问题）即为 UTF-8
function isUtf8(buf) {
  try {
    new TextDecoder("utf-8", { fatal: true }).decode(buf);
    return true;
  } catch {
    return false;
  }
}

// 幂等：检测已存在且为常量的 meta charset，返回 {declared, metaStart, metaEnd, attrIdx}（字节下标）
function findDeclaredCharset(buf) {
  const s = buf.toString("latin1");
  const re = /<meta\b[^>]*\bcharset\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi;
  let m;
  while ((m = re.exec(s))) {
    // 仅当该 <meta> 位于 <head> 中（避免正文出现同样串被误判）
    const head = /<head\b[^>]*>/i.test(s.slice(0, m.index));
    if (!head) continue;
    const value = m[0].replace(/^.*charset\s*=\s*/, "").replace(/^["']|["']$/g, "");
    return {
      declared: value,
      metaStart: m.index,
      metaEnd: m.index + Buffer.byteLength(m[0], "latin1"),
      valueStart: m.index + m[0].indexOf("=") + 1,
      valueEnd: m.index + Buffer.byteLength(m[0], "latin1"),
    };
  }
  return null;
}

// ---- CSS @charset 检测 ----
// CSS 规范: @charset 必须在文件最开头（BOM 之后），格式 @charset "UTF-8";
// 浏览器按此声明解码 CSS 文件字节，独立于 HTML 的 <meta charset>。
// CSS 中的中文（content: "查看"、font-family: "微软雅黑"）若被按错误编码解码 → 乱码/字体匹配失败。
function findCssCharset(buf) {
  let offset = 0;
  // 跳过 UTF-8 BOM（EF BB BF）
  if (buf.length >= 3 && buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF) {
    offset = 3;
  }
  const s = buf.subarray(offset).toString("latin1");
  // @charset 必须在文件首（允许前导空白被 CSS 规范忽略，但严格模式下需在字节 0）
  const re = /^@charset\s+["']([^"']+)["']\s*;/i;
  const m = re.exec(s);
  if (m) {
    return {
      declared: m[1],
      matchStart: offset + m.index,
      matchEnd: offset + m.index + Buffer.byteLength(m[0], "latin1"),
    };
  }
  return null;
}

async function walk(dir, out = []) {
  let names;
  try {
    names = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const n of names) {
    if (n.name.startsWith("node_modules") || n.name.startsWith(".git")) continue;
    const p = path.join(dir, n.name);
    if (n.isDirectory()) await walk(p, out);
    else if (EXT.has(path.extname(n.name).toLowerCase())) out.push(p);
  }
  return out;
}

let fixed = 0;
let ok = 0;
const errors = [];

// 统一编码归一: HTML 处理 <meta charset>，CSS 处理 @charset，逻辑平行。
// isCss=true 时用 findCssCharset（@charset），否则用 findDeclaredCharset（<meta charset>）。
async function normalizeFile(file, isCss) {
  const buf = await fs.readFile(file);
  if (isAscii(buf)) {
    ok++;
    return;
  }
  if (isUtf8(buf)) {
    const c = isCss ? findCssCharset(buf) : findDeclaredCharset(buf);
    if (c && !/^utf[- ]?8$/i.test(c.declared)) {
      const patched = Buffer.concat([
        buf.subarray(0, isCss ? c.matchStart : c.valueStart),
        Buffer.from(isCss ? '@charset "UTF-8";' : '"UTF-8"', "latin1"),
        buf.subarray(isCss ? c.matchEnd : c.valueEnd),
      ]);
      await fs.writeFile(file, patched);
      fixed++;
      console.log(`✔ ${file}: ${isCss ? "@charset" : "meta charset"} ${c.declared} → UTF-8`);
      await ensureMarker();
      return;
    }
    if (!c) {
      if (isCss) {
        // CSS: 在文件首（BOM 之后）插入 @charset "UTF-8";
        let offset = 0;
        if (buf.length >= 3 && buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF) offset = 3;
        const insert = Buffer.from('@charset "UTF-8";\n', "latin1");
        const patched = Buffer.concat([buf.subarray(0, offset), insert, buf.subarray(offset)]);
        await fs.writeFile(file, patched);
        fixed++;
        console.log(`✔ ${file}: 缺 @charset，已插入 UTF-8 声明`);
      } else {
        // HTML: 在 <head> 首行插入 <meta charset="UTF-8">
        const head = findHeadInsert(buf);
        const insert = Buffer.from('<meta charset="UTF-8">', "latin1");
        const nl = Buffer.from("\n", "latin1");
        const patched = Buffer.concat([buf.subarray(0, head.at), insert, nl, buf.subarray(head.at)]);
        await fs.writeFile(file, patched);
        fixed++;
        console.log(`✔ ${file}: 缺 <meta charset>，已插入 UTF-8 声明`);
      }
      return;
    }
    ok++; // 已是 UTF-8 且声明为 UTF-8
    return;
  }
  errors.push(`${file}: 字节非 UTF-8 且含非 ASCII（如 GBK/GB2312），无法自动转 → 需先转成 UTF-8 再截图`);
}

async function run() {
  const stat = await fs.stat(target).catch(() => null);
  if (!stat) {
    console.error(`❌ 目标不存在: ${target}`);
    process.exit(2);
  }
  const files = stat.isDirectory() ? await walk(target) : [target];
  if (!files.length) {
    console.log("（无可检查的 .html/.css）");
  }
  for (const f of files) {
    const ext = path.extname(f).toLowerCase();
    await normalizeFile(f, ext === ".css");
  }

  if (errors.length) {
    console.error("\n❌ 编码门禁未通过:");
    for (const e of errors) console.error("   " + e);
    process.exit(1);
  }
  await ensureMarker();
  console.log(`✅ 编码门禁通过（检查 ${files.length} 个文件，UTF-8 保留 ${ok}，自动修正 ${fixed}）。见: ${MARKER}`);
}

let wroteMarker = false;
async function ensureMarker() {
  if (wroteMarker) return;
  await fs.mkdir(path.dirname(MARKER), { recursive: true }).catch(() => {});
  await fs.writeFile(MARKER, `ok=true\ngate=ensure-utf8\nts=${new Date().toISOString()}\nfixed=${fixed}\n`);
  wroteMarker = true;
}

run().catch((e) => {
  console.error("❌ ensure-utf8 异常:", e && e.message);
  process.exit(1);
});