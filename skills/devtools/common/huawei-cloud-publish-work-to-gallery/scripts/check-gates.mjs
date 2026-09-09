#!/usr/bin/env node
// check-gates.mjs — 发布前统一门禁复核（fail-stop，最终关卡）
//
// 背景:
//   各门禁脚本（preflight.sh / ensure-utf8.mjs / screenshot-guard.mjs / verify-glyphs.py）
//   散落在 Step 5 / Step 7，发布 API 调用（Step 9）前无统一复核，agent 可跳过门禁直接发布。
//   本脚本在发布前一次性校验全部门禁标记 + 产物文件存在性，任一未通过即 exit 1，
//   程序性阻止发布 API 调用。
//
// 标记文件校验逻辑:
//   不只检查文件存在（test -f），而是读取内容并验证关键字段（ok=true + gate=<expected>）。
//   这样 `touch /tmp/font-gate-ok` 伪造的空文件会被识破（无 ok=true 字段）。
// 同时提供 verifyGates 导出供未来在 api.mjs 发布动作前内嵌调用（当前未接入）。
// 用法、选项、退出码详见 node check-gates.mjs --help。

import { readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import os from "node:os";
import { pathToFileURL } from "node:url";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

// ---- 标记目录（跨平台，尊重 $TMPDIR）----
const TMP = os.tmpdir();

// ---- 参数解析（CLI）----
function printHelp() {
  console.log(`check-gates.mjs — 发布前统一门禁复核（fail-stop，最终关卡）

用法:
  node check-gates.mjs --cover <封面图路径> --detail <详情zip路径> [选项]

必填:
  --cover <path>    封面图片路径（须 ≥10KB）
  --detail <path>   详情 zip 路径（须 ≥1KB）

可选:
  --strict          严格模式: screenshot-gate-ok 也必须存在（Option 1/2 截图场景建议加）
  --max-age <s>     标记新鲜度上限（秒，0=不校验新鲜度）。启用时可拦截「上次会话旧标记」复用。
  --quiet           安静模式: 仅输出失败项
  --verbose         展开成功详情（默认成功仅 1 行）
  -h, --help        显示本帮助

校验内容:
  - 标记文件内容校验（非仅 test -f）: font-gate-ok / utf8-gate-ok / screenshot-gate-ok
  - 标记新鲜度校验（--max-age 时）: ts 字段须在有效期内，防旧标记绕过
  - 产物文件校验: 封面 ≥10KB、详情 zip ≥1KB

退出码: 0=全部门禁通过; 1=有门禁未通过; 2=参数错误
`);
}

function parseCli(argv) {
  const o = { cover: null, detail: null, strict: false, quiet: false, verbose: false, maxAge: 0 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") { printHelp(); process.exit(0); }
    else if (a === "--cover") o.cover = argv[++i];
    else if (a === "--detail") o.detail = argv[++i];
    else if (a === "--strict") o.strict = true;
    else if (a === "--max-age") o.maxAge = Number(argv[++i]) || 0;
    else if (a === "--quiet") o.quiet = true;
    else if (a === "--verbose") o.verbose = true;
    else { console.error(`❌ 未知参数: ${a}\n  运行 node check-gates.mjs --help 查看用法。`); process.exit(2); }
  }
  return o;
}

// ---- 标记文件内容校验器 ----
// 读取标记文件，解析为 key=value 行，验证 ok=true 且 gate=<expected>。
// 通过 stdout 打印结果；计数累加到外部 failed / warned 变量（经 verifyGates 重置）。
let failed = 0;
let warned = 0;

function checkMark(name, expectedGate, required, quiet, maxAgeMs = null) {
  const markerPath = join(TMP, name);
  if (!existsSync(markerPath)) {
    if (required) {
      if (!quiet) console.error(`✖ [${expectedGate}] 标记文件不存在: ${markerPath}`);
      failed++;
    } else {
      if (!quiet) console.warn(`⚠ [${expectedGate}] 标记文件不存在（宽松模式仅警告）: ${markerPath}`);
      warned++;
    }
    return;
  }
  let content;
  try {
    content = readFileSync(markerPath, "utf8");
  } catch (e) {
    if (!quiet) console.error(`✖ [${expectedGate}] 标记文件无法读取: ${markerPath} — ${e.message}`);
    failed++;
    return;
  }
  const fields = {};
  for (const line of content.split("\n")) {
    const idx = line.indexOf("=");
    if (idx > 0) fields[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  if (fields.ok !== "true") {
    if (!quiet) console.error(`✖ [${expectedGate}] 标记文件 ok 字段不为 true（实际: "${fields.ok}"）— 内容: ${content.trim()}`);
    failed++;
    return;
  }
  if (expectedGate && fields.gate !== expectedGate) {
    if (!quiet) console.error(`✖ [${expectedGate}] 标记文件 gate 字段不匹配（期望: "${expectedGate}"，实际: "${fields.gate}"）— 可能是伪造或错误脚本写入`);
    failed++;
    return;
  }
  // 新鲜度校验（默认关闭；调用方传 maxAgeMs 时启用）：
  // 防止「上次会话生成的旧标记」在本次复用绕过门禁——即使 ok=true + gate 字段都对，
  // 只要 ts 早于 maxAgeMs 前即判陈旧，强制本次重跑对应门禁脚本。
  const tsStr = fields.ts || "";
  if (maxAgeMs) {
    const ts = Date.parse(tsStr);
    if (Number.isNaN(ts)) {
      if (!quiet) console.error(`✖ [${expectedGate}] 标记文件 ts 字段无法解析（实际: "${tsStr}"）— 旧版标记或伪造文件，须重跑门禁`);
      failed++;
      return;
    }
    const ageMs = Date.now() - ts;
    if (ageMs > maxAgeMs) {
      if (!quiet) console.error(`✖ [${expectedGate}] 标记文件已陈旧（${formatAge(ageMs)} > ${Math.round(maxAgeMs / 1000)}s）— 疑似复用上次会话的旧标记，请重跑门禁脚本`);
      failed++;
      return;
    }
    if (!quiet) console.log(`✔ [${expectedGate}] 门禁通过${fields.ts ? ` (${fields.ts})` : ""}${fields.platform ? ` [${fields.platform}]` : ""}  (${formatAge(ageMs)} 内)`);
    return;
  }
  if (!quiet) console.log(`✔ [${expectedGate}] 门禁通过${fields.ts ? ` (${fields.ts})` : ""}${fields.platform ? ` [${fields.platform}]` : ""}`);
}

function formatAge(ageMs) {
  const s = Math.round(ageMs / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}

// ---- 产物文件校验器 ----
function checkArtifact(label, path, minSize, quiet) {
  if (!existsSync(path)) {
    if (!quiet) console.error(`✖ [${label}] 产物文件不存在: ${path}`);
    failed++;
    return;
  }
  let stat;
  try {
    stat = statSync(path);
  } catch (e) {
    if (!quiet) console.error(`✖ [${label}] 产物文件无法 stat: ${path} — ${e.message}`);
    failed++;
    return;
  }
  if (stat.size < minSize) {
    if (!quiet) console.error(`✖ [${label}] 产物文件过小（${stat.size} bytes < ${minSize}）: ${path} — 疑似无效/占位文件`);
    failed++;
    return;
  }
  if (!quiet) console.log(`✔ [${label}] 产物存在（${stat.size} bytes）: ${path}`);
}

// ---- 核心校验（模块可复用；不 process.exit） ----
export function verifyGates({ cover, detail, strict = false, quiet = false, maxAgeMs = 0 }) {
  failed = 0;
  warned = 0;

  // font-gate-ok — preflight.sh 写入（字体 + fontconfig + 依赖）
  checkMark("font-gate-ok", "preflight", true, quiet, maxAgeMs);

  // utf8-gate-ok — ensure-utf8.mjs 写入（编码归一）
  checkMark("utf8-gate-ok", "ensure-utf8", true, quiet, maxAgeMs);

  // screenshot-gate-ok — screenshot-guard / local mock 写入（页面字形自检 + 兜底注入）
  // 宽松模式（默认，Option 3 无前端场景）：缺失仅警告，不阻塞发布。
  // 严格模式（--strict）：缺失即判失败。Option 1/2 截图场景建议加 --strict。
  const screenshotRequired = strict;
  checkMark("screenshot-gate-ok", "screenshot-guard", screenshotRequired, quiet, maxAgeMs);

  // ================================================================
  // 2. 产物文件校验
  // ================================================================
  if (!quiet) console.log("");

  // 封面图片 — 必须 ≥10KB（与 Step 5 截图有效性校验一致）
  checkArtifact("封面图片", cover, 10240, quiet);

  // 详情 zip — 必须 ≥1KB
  checkArtifact("详情包", detail, 1024, quiet);

  return { ok: failed === 0, failed, warned };
}

// ---- 汇总（CLI 版） ----
// 默认成功静默（仅 1 行）；--verbose 展开详情；失败时无论 quiet 均输出全部未通过项。
function finish(fail, warn, quiet) {
  if (fail > 0) {
    // 失败时重新跑一次非静默校验以输出详情（若之前是 quiet 模式）
    if (quiet) {
      quiet = false;
      verifyGates({ cover: _lastCover, detail: _lastDetail, strict: _lastStrict, quiet: false, maxAgeMs: _lastMaxAge });
    }
    console.error(`\n❌ ${fail} 个门禁未通过 — 禁止发布。请回退到对应步骤修复后重跑门禁，再重新执行发布。`);
    process.exit(1);
  }
  if (warn > 0) {
    console.warn(`⚠️ ${warn} 个警告（宽松模式）— 可继续发布，但建议检查对应门禁。`);
  }
  if (quiet) {
    console.log("✅ 全部门禁复核通过，可以执行发布。");
  } else {
    console.log("✅ 全部门禁复核通过，可以执行发布。");
  }
  process.exit(0);
}

// 保存参数供 finish 重跑详情
let _lastCover, _lastDetail, _lastStrict, _lastMaxAge;

// ---- CLI 入口 ----
const isCli =
  typeof import.meta.url === "string" &&
  import.meta.url === pathToFileURL(process.argv[1] || "").href;
if (isCli) {
  const args = parseCli(process.argv.slice(2));
  if (!args.cover || !args.detail) {
    console.error('❌ 用法: node check-gates.mjs --cover <封面图路径> --detail <详情zip路径> [--strict] [--quiet]\n  运行 node check-gates.mjs --help 查看完整用法。');
    process.exit(2);
  }
  // 默认成功静默（--verbose 展开）；失败时自动展开详情
  const cliQuiet = !args.verbose;
  _lastCover = args.cover; _lastDetail = args.detail; _lastStrict = args.strict; _lastMaxAge = args.maxAge * 1000;
  const result = verifyGates({ cover: args.cover, detail: args.detail, strict: args.strict, quiet: cliQuiet, maxAgeMs: args.maxAge * 1000 });
  finish(result.failed, result.warned, cliQuiet);
}