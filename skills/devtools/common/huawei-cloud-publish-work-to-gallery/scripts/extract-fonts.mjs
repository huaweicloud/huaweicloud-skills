#!/usr/bin/env node
// extract-fonts.mjs — 扫描 workDir 提取字体需求（CSS font-family + @font-face + JS ctx.font 绘制的字体）
// stdout 每行一个去重字体族名（供 screenshot-guard.mjs 的 --required 使用）。
// 用法详见 node extract-fonts.mjs --help。跨平台（Node），Linux/Windows 通用。

import fs from "node:fs";
import path from "node:path";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const workDir = process.argv[2];
if (workDir === "-h" || workDir === "--help") {
  console.log(`extract-fonts.mjs — 扫描 workDir 提取字体需求（CSS font-family + @font-face + JS ctx.font）

用法:
  node extract-fonts.mjs <workDir>
  node extract-fonts.mjs -h | --help

参数:
  <workDir>      要扫描的项目目录（递归处理 .html/.css/.vue/.scss/.less/.js/.jsx/.ts/.tsx）

输出:
  stdout 每行一个去重字体族名（供 screenshot-guard.mjs 的 --required-file 使用）

跳过: node_modules / .git / dist / build / .cache / __pycache__
`);
  process.exit(0);
}
if (!workDir) {
  console.error("❌ 用法: node extract-fonts.mjs <workDir>\n  运行 node extract-fonts.mjs --help 查看完整用法。");
  process.exit(2);
}

const EXTS = /\.(html?|css|vue|scss|less|js|jsx|ts|tsx)$/i;
const SKIP = /node_modules|\.git|dist|build|\.cache|__pycache__/;
const famRe = /font-family\s*:\s*([^;{}]+)/gi;
const atFaceRe = /@font-face\s*\{[^}]*?\}/gis;
const ctxRe = /(?:ctx\.font|context\.font|\.font)\s*=\s*["'`]([^"'`]+)["'`]/gi;

const families = new Set();

function parseList(str) {
  for (const seg of str.split(",")) {
    const n = seg.trim().replace(/^["'`]|["'`]$/g, "");
    if (n) families.add(n);
  }
}

function scan(file) {
  const s = fs.readFileSync(file, "utf8");
  let m;
  while ((m = famRe.exec(s))) parseList(m[1]);
  for (const a of s.matchAll(atFaceRe)) {
    const fm = /font-family\s*:\s*["']?([^;"'}]+)/.exec(a[0]);
    if (fm) parseList(fm[1]);
  }
  let cm;
  while ((cm = ctxRe.exec(s))) {
    const rest = cm[1].trim().replace(/^(italic|oblique|normal|bold|bolder|lighter|\d+(\.\d+)?(px|pt|em|rem)|\d{2,4})+\s+/i, "");
    parseList(rest);
  }
}

(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (SKIP.test(e.name)) continue;
    e.isDirectory() ? walk(p) : EXTS.test(e.name) && scan(p);
  }
})(workDir);

console.log([...families].join("\n"));