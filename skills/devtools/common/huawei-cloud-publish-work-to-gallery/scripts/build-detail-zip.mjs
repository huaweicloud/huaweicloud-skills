#!/usr/bin/env node
// build-detail-zip.mjs — 详情包一键「打包 + 校验」（零依赖、跨平台，一步到位）
// 用法:
//   node build-detail-zip.mjs --readme <README.md> --resources <dir> --out <workDetail.zip>
// 行为:
//   1) 内置正确目录结构（README.md@根 + resources/ 前缀），不再依赖 Compress-Archive/ZipFile/zip 的平台差异；
//   2) 打包完成后立即调用 <同目录>/validate-detail-zip.mjs 校验，失败即停（fail-stop）。
// 优点: 消除「打包→校验→失败重打」的多轮往返；Windows scripts/shell 编码历史问题一并绕开。
// 退出码: 0=打包且校验通过; 1=失败（含校验不过）; 2=参数错误
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, statSync, readdirSync } from "node:fs";
import { deflateRawSync, crc32 } from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";

const thisDir = path.dirname(fileURLToPath(import.meta.url));
const VALIDATE = path.join(thisDir, "validate-detail-zip.mjs");

const HELP = `build-detail-zip.mjs — 详情包一键「打包 + 校验」（零依赖、跨平台）

用法:
  node build-detail-zip.mjs --readme <README.md> --resources <dir> --out <workDetail.zip>

选项:
  --readme <file>     详解文章 README.md（内容写到 zip 根目录）
  --resources <dir>   图片目录（包含的图片写入 zip 的 resources/ 下；可省略）
  --out <zip>         输出 zip 路径（必填）
  -h, --help          显示本帮助

退出码: 0=打包且校验通过; 1=失败（含校验不过）; 2=参数错误`;

function parseArgs(argv) {
  const o = { readme: null, resources: null, out: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "-h" || a === "--help") { console.log(HELP); process.exit(0); }
    else if (a === "--readme") o.readme = argv[++i];
    else if (a === "--resources") o.resources = argv[++i];
    else if (a === "--out") o.out = argv[++i];
    else { console.error(`❌ 未知参数: ${a}`); process.exit(2); }
  }
  return o;
}

// ---- DOS 时间戳（本地时间）----
function dosDateTime(d = new Date()) {
  const time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  const date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  return { time, date: date & 0xffff };
}

// ---- 最小 ZIP 写入（deflate，UTF-8 文件名）----
function buildZip(entries) {
  const { time, date } = dosDateTime();
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const e of entries) {
    const nameBuf = Buffer.from(e.name, "utf8");
    const data = e.data;
    const compressed = deflateRawSync(data, { level: 9 });
    const crc = crc32 ? crc32(data) >>> 0 : 0;
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);          // sig
    local.writeUInt16LE(20, 4);                  // version needed
    local.writeUInt16LE(0x0800, 6);              // flags: UTF-8
    local.writeUInt16LE(8, 8);                   // method: deflate
    local.writeUInt16LE(time, 10);
    local.writeUInt16LE(date, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(compressed.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);                  // extra
    localParts.push(local, nameBuf, compressed);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);        // sig
    central.writeUInt16LE(20, 4);                // version made by
    central.writeUInt16LE(20, 6);                // version needed
    central.writeUInt16LE(0x0800, 8);            // flags: UTF-8
    central.writeUInt16LE(8, 10);                // method: deflate
    central.writeUInt16LE(time, 12);
    central.writeUInt16LE(date, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(compressed.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(nameBuf.length, 28);
    central.writeUInt16LE(0, 30);                // extra len
    central.writeUInt16LE(0, 32);                // comment len
    central.writeUInt16LE(0, 34);                // disk start
    central.writeUInt16LE(0, 36);                // internal attrs
    central.writeUInt32LE(0, 38);                // external attrs
    central.writeUInt32LE(offset, 42);           // local offset
    centralParts.push(central, nameBuf);
    offset += local.length + nameBuf.length + compressed.length;
  }
  const localData = Buffer.concat(localParts);
  const localStart = 0;
  const centralData = Buffer.concat(centralParts);
  const cdOffset = localData.length;
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);             // sig
  eocd.writeUInt16LE(0, 4);                      // disk
  eocd.writeUInt16LE(0, 6);                      // cd start disk
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralData.length, 12);
  eocd.writeUInt32LE(cdOffset, 16);
  eocd.writeUInt16LE(0, 20);                     // comment len
  void localStart;
  return Buffer.concat([localData, centralData, eocd]);
}

function collectResources(resourcesDir) {
  const out = [];
  if (!resourcesDir || !existsSync(resourcesDir)) return out;
  for (const f of readdirSync(resourcesDir).sort()) {
    const full = path.join(resourcesDir, f);
    if (!statSync(full).isFile()) continue;
    out.push({ name: `resources/${f}`, data: readFileSync(full) });
  }
  return out;
}

function main() {
  const o = parseArgs(process.argv.slice(2));
  if (!o.out || !existsSync(o.readme || "")) {
    console.error("❌ --out 必填且 --readme 须指向存在的文件");
    console.error(HELP);
    process.exit(2);
  }
  const readme = readFileSync(o.readme);
  const entries = [
    { name: "README.md", data: readme },
    { name: "resources/", data: Buffer.alloc(0) },
    ...collectResources(o.resources),
  ];
  const zip = buildZip(entries);
  writeFileSync(o.out, zip);
  console.log(`✅ 详情包已生成: ${o.out} (${zip.length} bytes，${entries.length - 2} 张图片)`);

  // 二次校验（复用服务端同源规则）
  try {
    execFileSync(process.execPath, [VALIDATE, o.out], { stdio: "inherit" });
  } catch {
    console.error(`\n❌ build-detail-zip 校验未通过（详情包不合格）。请修复后重跑。`);
    process.exit(1);
  }
  console.log("✅ build-detail-zip 打包 + 校验一步完成，可以发布会前门禁。");
}

main();