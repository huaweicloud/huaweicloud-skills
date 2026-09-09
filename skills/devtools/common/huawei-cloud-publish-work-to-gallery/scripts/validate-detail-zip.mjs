#!/usr/bin/env node
// validate-detail-zip.mjs — 发布前本地校验详情 zip（复用服务端 parseDetailZip 规则，独立实现，零依赖）
// 用法: node validate-detail-zip.mjs <workDetail.zip>
// 校验: README.md 必须存在且仅有一个 .md；resources/ 下仅限图片（png/jpg/jpeg/gif/webp）；
//       图片引用必须指向 resources/ 内实际存在的文件；条目数/大小限制。
// exit 0=通过; 1=不通过（fail-stop，禁止发布）
import { readFileSync, existsSync } from "node:fs";
import { inflateRawSync } from "node:zlib";

if (process.argv.length < 3 || process.argv[2] === "-h" || process.argv[2] === "--help") {
  console.log(`validate-detail-zip.mjs — 发布前本地校验详情 zip（零依赖）

用法:
  node validate-detail-zip.mjs <workDetail.zip>

校验:
  - README.md 必须存在且仅有一个 .md（根目录）
  - resources/ 下仅限图片（png/jpg/jpeg/gif/webp），每张 ≤5MB
  - 图片引用必须指向 resources/ 内实际存在的文件
  - zip ≤20MB，条目数 ≤50，解压总大小 ≤30MB

退出码: 0=通过; 1=不通过（fail-stop，禁止发布）; 2=参数错误`);
  process.exit(process.argv.length < 3 ? 2 : 0);
}
const file = process.argv[2];
if (!existsSync(file)) { console.error(`❌ 文件不存在: ${file}`); process.exit(2); }

const MAX_ZIP = 20 * 1024 * 1024;
const MAX_ENTRIES = 50;
const MAX_UNCOMPRESSED = 30 * 1024 * 1024;
const MAX_README = 512 * 1024;
const MAX_RESOURCE = 5 * 1024 * 1024;
const IMAGE_EXT = [".gif", ".jpeg", ".jpg", ".png", ".webp"];

const buffer = readFileSync(file);
if (buffer.length > MAX_ZIP) { console.error("❌ zip 超过 20MB"); process.exit(1); }

// ---- 读取中央目录 ----
const eocdOffset = (() => {
  for (let c = buffer.length - 22; c >= Math.max(0, buffer.length - 65557); c -= 1) {
    if (buffer.readUInt32LE(c) === 0x06054b50) return c;
  }
  return -1;
})();
if (eocdOffset < 0) { console.error("❌ 非合法 zip（无 EOCD）"); process.exit(1); }
const totalEntries = buffer.readUInt16LE(eocdOffset + 10);
if (totalEntries > MAX_ENTRIES) { console.error(`❌ 条目数 ${totalEntries} 超过 50`); process.exit(1); }
let cursor = buffer.readUInt32LE(eocdOffset + 16);
const entries = [];
for (let i = 0; i < totalEntries; i += 1) {
  if (cursor < 0 || cursor + 46 > buffer.length || buffer.readUInt32LE(cursor) !== 0x02014b50) {
    console.error("❌ 中央目录损坏"); process.exit(1);
  }
  const method = buffer.readUInt16LE(cursor + 10);
  const compressedSize = buffer.readUInt32LE(cursor + 20);
  const uncompressedSize = buffer.readUInt32LE(cursor + 24);
  const nameLength = buffer.readUInt16LE(cursor + 28);
  const extraLength = buffer.readUInt16LE(cursor + 30);
  const commentLength = buffer.readUInt16LE(cursor + 32);
  const localOffset = buffer.readUInt32LE(cursor + 42);
  const name = buffer.subarray(cursor + 46, cursor + 46 + nameLength).toString("utf8");
  entries.push({ name, method, compressedSize, uncompressedSize, localOffset });
  cursor += 46 + nameLength + extraLength + commentLength;
}
const totalUncompressed = entries.reduce((s, e) => s + e.uncompressedSize, 0);
if (totalUncompressed > MAX_UNCOMPRESSED) { console.error("❌ 解压总大小超限"); process.exit(1); }

// ---- 逐条目读取 ----
const files = new Map();
for (const e of entries) {
  const normalized = e.name.replace(/\\/g, "/");
  if (!normalized || normalized.endsWith("/")) continue;
  const limit = normalized === "README.md" ? MAX_README : MAX_RESOURCE;
  if (e.uncompressedSize > limit) { console.error(`❌ ${normalized} 超限`); process.exit(1); }
  const lh = e.localOffset;
  if (lh < 0 || lh + 30 > buffer.length || buffer.readUInt32LE(lh) !== 0x04034b50) {
    console.error(`❌ ${normalized} 本地文件头损坏`); process.exit(1);
  }
  const nl = buffer.readUInt16LE(lh + 26);
  const xl = buffer.readUInt16LE(lh + 28);
  const dataStart = lh + 30 + nl + xl;
  const compressed = buffer.subarray(dataStart, dataStart + e.compressedSize);
  let data;
  if (e.method === 0) data = Buffer.from(compressed);
  else if (e.method === 8) {
    try {
      data = inflateRawSync(compressed, { maxOutputLength: limit });
    } catch { console.error(`❌ ${normalized} 解压失败`); process.exit(1); }
    if (data.length !== e.uncompressedSize) { console.error(`❌ ${normalized} 解压长度不符`); process.exit(1); }
  } else { console.error(`❌ ${normalized} 不支持的压缩方法 ${e.method}`); process.exit(1); }
  files.set(normalized, data);
}

// ---- 内容规约 ----
const md = [...files.keys()].filter((n) => n.toLowerCase().endsWith(".md"));
if (!files.has("README.md") || md.some((n) => n !== "README.md")) {
  console.error("❌ 必须且只能有一个 README.md（根目录），不能有其他 .md");
  console.error("   当前条目: " + [...files.keys()].join(", "));
  process.exit(1);
}
for (const [p, data] of files.entries()) {
  if (p === "README.md") continue;
  if (!p.startsWith("resources/")) {
    console.error(`❌ ${p} 必须位于 resources/ 下`);
    console.error("   （常见原因：Windows Compress-Archive 压平子目录，只有 README.md + arch.png，须用 ZipFile::CreateFromDirectory 重新打包）");
    process.exit(1);
  }
  const ext = p.slice(p.lastIndexOf(".")).toLowerCase();
  if (!IMAGE_EXT.includes(ext)) { console.error(`❌ ${p} 不是受支持的图片格式`); process.exit(1); }
  if (data.length > MAX_RESOURCE) { console.error(`❌ ${p} 超过 5MB`); process.exit(1); }
}
const markdown = files.get("README.md").toString("utf8");
const refs = [...markdown.matchAll(/!\[[^\]]*]\(([^)\s]+)(?:\s+"[^"]*")?\)/g)].map((m) => m[1].split("#")[0].split("?")[0]);
const resourcePaths = new Set([...files.keys()].filter((p) => p.startsWith("resources/")));
for (const r of refs) {
  if (!r.startsWith("resources/") || !resourcePaths.has(r)) {
    console.error(`❌ 图片引用 ${r} 未指向 resources/ 内实际存在的文件`);
    process.exit(1);
  }
}
console.log(`✅ 详情 zip 校验通过：README.md + ${files.size - 1} 个资源（${[...resourcePaths].join(", ")}）`);
process.exit(0);