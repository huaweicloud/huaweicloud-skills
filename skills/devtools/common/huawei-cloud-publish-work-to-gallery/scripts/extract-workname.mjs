#!/usr/bin/env node
// extract-workname.mjs — 从作品目录提取作品名（前 4 级确定性提取，dirname 兜底交 agent）
//
// 背景:
//   SKILL.md Step 3 内联了命名优先级（frontmatter → H1 → manifest → index.html title → 目录名），
//   agent 每次都要试 4 种来源。本脚本封装前 4 级提取，仅 dirname 兜底时输出提示交 agent 合成。
//
// 用法:
//   node extract-workname.mjs <workDir>
//
// 提取优先级:
//   1. README frontmatter name/title
//   2. README H1 首行
//   3. package.json / pom.xml / pyproject.toml 的 name 字段
//   4. index.html <title> 或首个 <h1>
//   5. 目录名（kebab/snake_case → 可读标题）
//
// stdout: `#name=<name> source=<来源>`
//   source=frontmatter|h1|manifest|html-title|dirname
//   source=dirname 时 agent 可合成/修改（<30 字符）
//
// 退出码: 0=成功提取; 1=workDir 不存在; 2=参数错误

import fs from "node:fs";
import path from "node:path";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
}

const workDir = process.argv[2];
if (!workDir || workDir === "-h" || workDir === "--help") {
  console.log(`extract-workname.mjs — 从作品目录提取作品名

用法:
  node extract-workname.mjs <workDir>

提取优先级:
  1. README frontmatter name/title
  2. README H1 首行
  3. package.json / pom.xml / pyproject.toml name 字段
  4. index.html <title> 或首个 <h1>
  5. 目录名

stdout: #name=<name> source=<来源>
退出码: 0=成功; 1=workDir不存在; 2=参数错误`);
  process.exit(workDir ? 0 : 2);
}

if (!fs.existsSync(workDir)) {
  console.error(`❌ 目录不存在: ${workDir}`);
  process.exit(1);
}

function readReadme(dir) {
  for (const name of ["README.md", "readme.md", "README.MD"]) {
    const p = path.join(dir, name);
    if (fs.existsSync(p)) return fs.readFileSync(p, "utf8");
  }
  return "";
}

function cleanName(name) {
  if (!name) return "";
  // 去首尾空白/引号/Markdown 残留
  let s = name.trim().replace(/^["'`]|["'`]$/g, "");
  // 去掉常见副标题分隔（如 "扫雷游戏 · Minesweeper" → 取中文部分）
  // 但保留含英文的标题（如 "Smart QA System"）
  return s.substring(0, 30); // <30 字符
}

function dirnameToTitle(dir) {
  const base = path.basename(dir);
  // kebab-case / snake_case → 空格分隔 + 首字母大写
  let s = base.replace(/[-_]+/g, " ").trim();
  if (s) s = s.charAt(0).toUpperCase() + s.slice(1);
  return s;
}

// ---- 1. README frontmatter ----
const readme = readReadme(workDir);
if (readme) {
  const fmMatch = readme.match(/^---\s*\n([\s\S]*?)\n---/);
  if (fmMatch) {
    const fm = fmMatch[1];
    const nameMatch = fm.match(/^name:\s*(.+)$/m) || fm.match(/^title:\s*(.+)$/m);
    if (nameMatch) {
      const name = cleanName(nameMatch[1]);
      if (name) { console.log(`#name=${name} source=frontmatter`); process.exit(0); }
    }
  }

  // ---- 2. README H1 ----
  const h1Match = readme.match(/^#\s+(.+)$/m);
  if (h1Match) {
    const name = cleanName(h1Match[1]);
    if (name) { console.log(`#name=${name} source=h1`); process.exit(0); }
  }
}

// ---- 3. manifest name ----
const manifests = [
  ["package.json", (raw) => { try { return JSON.parse(raw).name; } catch { return ""; } }],
  ["pyproject.toml", (raw) => { const m = raw.match(/^name\s*=\s*["']([^"']+)["']/m); return m ? m[1] : ""; }],
  ["pom.xml", (raw) => { const m = raw.match(/<artifactId>([^<]+)<\/artifactId>/); return m ? m[1] : ""; }],
];
for (const [file, extract] of manifests) {
  const p = path.join(workDir, file);
  if (fs.existsSync(p)) {
    const name = cleanName(extract(fs.readFileSync(p, "utf8")));
    if (name) { console.log(`#name=${name} source=manifest`); process.exit(0); }
  }
}

// ---- 4. index.html title/h1 ----
for (const htmlPath of [path.join(workDir, "index.html"), path.join(workDir, "public", "index.html")]) {
  if (fs.existsSync(htmlPath)) {
    const html = fs.readFileSync(htmlPath, "utf8");
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    if (titleMatch) {
      const name = cleanName(titleMatch[1].split(/[·\-–—|]/)[0]);
      if (name) { console.log(`#name=${name} source=html-title`); process.exit(0); }
    }
    const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
    if (h1Match) {
      const name = cleanName(h1Match[1]);
      if (name) { console.log(`#name=${name} source=html-title`); process.exit(0); }
    }
  }
}

// ---- 5. 目录名兜底 ----
const name = dirnameToTitle(workDir);
console.log(`#name=${name} source=dirname`);
if (name) process.exit(0);
process.exit(1);