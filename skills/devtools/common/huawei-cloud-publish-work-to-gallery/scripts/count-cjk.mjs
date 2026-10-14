#!/usr/bin/env node
// count-cjk.mjs — 中文字符计数 + 15~50 字数门禁（跨平台，替代 grep -oP '\x{4e00}-\x{9fff}'）
//
// 背景:
//   EulerOS 等旧 PCRE 环境下 `grep -oP '[\x{4e00}-\x{9fff}]'` 报
//   "character code point value in \x{} or \o{} is too large"，无法计数中文字符。
//   本脚本用 Node 原生 Unicode 码点比较，不依赖 PCRE/PCRE2 库版本，跨平台可靠。
// 校验规则:
//   服务端按「总字符数」校验简介长度（含英文/数字/标点/emoji），
//   故门禁判定只看总字符数是否落在 min~max（默认 15~50）内；中文字符数仅作信息输出。
// 用法 / 退出码详见 node count-cjk.mjs --help。

const fs = await import("node:fs");

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

function countCjk(s) {
  let cjk = 0, total = 0;
  for (const ch of s) {
    total++;
    const cp = ch.codePointAt(0);
    // CJK 统一表意文字 + 扩展A + 兼容表意文字（覆盖常见中文）
    if ((cp >= 0x4e00 && cp <= 0x9fff) ||
        (cp >= 0x3400 && cp <= 0x4dbf) ||
        (cp >= 0xf900 && cp <= 0xfaff)) {
      cjk++;
    }
  }
  return { cjk, total };
}

function printHelp() {
  console.log(`count-cjk.mjs — 中文字符计数 + 15~50 字数门禁

用法:
  node count-cjk.mjs "<text>"
  node count-cjk.mjs --file "<utf8.txt>"   # 从 UTF-8 文件读取（Windows 推荐，规避 PS 参数转码）
  echo "<text>" | node count-cjk.mjs
  node count-cjk.mjs "<text>" --min 15 --max 50

选项:
  --file <path> 从 UTF-8 文本文件读取（Windows 下经参数传中文会被系统代码页转码丢字，
               必须用 --file 或 stdin），不能与位置参数混用
  --min <n>     最少字符数（默认 15）
  --max <n>     最多字符数（默认 50）
  -h, --help    显示本帮助

输出:
  中文字符数: <n> / 总字符数: <n>
  ✅ 合格 或 ❌ 超出范围

校验规则:
  服务端按「总字符数」校验简介长度（含英文/数字/标点/emoji），门禁判定只看总字符数
  是否落在 min~max 内；中文字符数仅作信息输出，不参与判定。
  只统计中文字符会在简介含 Web/API 等英文字符时漏判超长（如 43 个中文字 +
  8 个英文字符 = 51 总字符 > 50 会被服务端拒绝）。

退出码: 0=合格; 1=超出范围; 2=参数错误
`);
}

const argv = process.argv.slice(2);
let min = 15, max = 50;
let file = null;
const textParts = [];

for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "-h" || a === "--help") { printHelp(); process.exit(0); }
  else if (a === "--min") min = parseInt(argv[++i], 10);
  else if (a === "--max") max = parseInt(argv[++i], 10);
  else if (a === "--file") file = argv[++i];
  else textParts.push(a);
}

let text = textParts.join(" ");

if (file) {
  // Windows 下经命令行参数传中文会被系统代码页转码导致字符丢失/误计，必须从 UTF-8 文件读取
  if (!fs.existsSync(file)) {
    console.error(`❌ 文件不存在: ${file}`);
    process.exit(2);
  }
  if (text) {
    console.error("❌ --file 与位置参数不能混用");
    process.exit(2);
  }
  text = fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "").trim();
  // 缺省经参数传中文同样会被转码，--file 强制从文件读，天然规避
} else if (!text) {
  // 从 stdin 读取
  text = await new Promise((resolve) => {
    let d = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (d += c));
    process.stdin.on("end", () => resolve(d.trim()));
    // 无 stdin 时（TTY）直接退出
    if (process.stdin.isTTY) resolve("");
  });
}

if (!text) {
  console.error("❌ 未收到文本（支持参数或 stdin）\n  运行 node count-cjk.mjs --help 查看用法。");
  process.exit(2);
}

const { cjk, total } = countCjk(text);
console.log(`中文字符数: ${cjk} / 总字符数: ${total}`);

// ⚠️ 判定只看总字符数：服务端按「总字符数」校验（含英文字母/数字/标点/emoji），
//    并非只统计中文字符。若简介含 Web/API 等拉丁字母或数字，中文字符数在范围内但
//    总字数可能超 50 → 服务端报 GALLERY.PARAM.INTRODUCTION_LENGTH_INVALID。
if (total < min) {
  console.error(`❌ 总字符数 ${total} 少于下限 ${min}，请补充技术栈或核心功能描述。`);
  process.exit(1);
}
if (total > max) {
  console.error(`❌ 总字符数 ${total} 超过上限 ${max}（服务端按总字符数校验，含英文/数字/标点），请精简为「基于 X 的 Y 系统」一句话简介。`);
  process.exit(1);
}
console.log(`✅ 字数合格（总字符数 ${total}，${min}~${max}）`);
process.exit(0);
