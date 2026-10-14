#!/usr/bin/env node
// publish-work.mjs — Windows 发布封装：UTF-8 JSON 参数绕开 PowerShell 编码（fail-stop）
// 用法: node publish-work.mjs <utf8-params.json> [--api <api.mjs>]
// JSON: { idempotencyKey, accessKeyId, secretAccessKey, securityToken, trainingCampId,
//         workName, introduction, coverImage, detailZip, gitUrl, gitBranch, envUrl?,
//         _refresh?: {accountId, agencyUrn, region} }
// 说明：由服务端通过最小权限 STS 临时凭证（accessKeyId/secretAccessKey/securityToken）
//       解析调用方身份（domainId）。
//       STS 凭证经请求头 X-Tmp-Ak/X-Tmp-Sk/X-Security-Token 传递（与 /camps 查询一致），而非 multipart 表单字段。
//       接口路径为 /open-api-public/v1/gallery/works（由 api.mjs 自动添加 /open-api-public 前缀）。
//       可选 _refresh 元数据传入后，api.mjs 在 401 时自动刷新 STS 凭证并重试。
// exit 0=成功; 1=简介不达标或发布失败; 2=参数错误
import { readFileSync, existsSync, writeFileSync, unlinkSync } from "node:fs";
import { execFileSync, spawnSync } from "node:child_process";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";
import { verifyGates } from "./check-gates.mjs";

const isWin = process.platform === "win32";
if (isWin) {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const thisDir = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const cli = { json: null, api: path.join(thisDir, "api.mjs"), maxAge: 0 };

const PARAMS_SCHEMA_HELP = `发布参数 JSON（--params）仅识别以下 key（脚本对未知 key 直接拦截：报「参数 JSON 含未知 key: …」并给出正确写法，不会静默忽略）：

{
  "idempotencyKey":  "<gallery-publish-<domainID>-<timestamp>> 幂等键，必填",
  "accessKeyId":     "<STS 临时凭证 AK，Step 1 落盘>             必填",
  "secretAccessKey": "<STS 临时凭证 SK>                          必填",
  "securityToken":   "<STS Security Token（不经 shell 传参）>    必填",
  "trainingCampId":  "<已选活动 ID>                            必填",
  "workName":        "<作品名称>                                 必填",
  "introduction":    "<作品简介，总字符数 15~50（含英文/数字/标点）>        必填",
  "coverImage":      "<封面 PNG 绝对路径>（不是 coverImagePath/imagePath）  必填",
  "detailZip":       "<详情 zip 绝对路径>（不是 detailsZipPath/detailPath） 必填",
  "gitUrl":          "<git clone 地址，https:// 开头 .git 结尾>   必填",
  "gitBranch":       "<分支名>                                   必填",
  "envUrl":          "<隧道访问地址，可空串>                     可选（默认 ""）",
  "_refresh":        "{accountId, agencyUrn, region} STS 刷新元数据 可选（401 自动刷新用）"
}`;

const VALID_PARAM_KEYS = new Set([
  "idempotencyKey", "accessKeyId", "secretAccessKey", "securityToken",
  "trainingCampId", "workName", "introduction", "coverImage", "detailZip",
  "gitUrl", "gitBranch", "envUrl", "_refresh",
]);

for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "-h" || argv[i] === "--help") {
    console.log("用法: node publish-work.mjs <utf8-params.json> [--api <api.mjs>] [--max-age <秒>]");
    console.log(PARAMS_SCHEMA_HELP);
    process.exit(0);
  }
  else if (argv[i] === "--api") cli.api = argv[++i];
  else if (argv[i] === "--params") cli.json = argv[++i];
  else if (argv[i] === "--max-age") cli.maxAge = Number(argv[++i]) || 0;
  else if (!cli.json) cli.json = argv[i];
}
if (!cli.json) { console.error("用法: node publish-work.mjs <utf8-params.json> [--api <api.mjs>] [--max-age <秒>]"); process.exit(2); }

// 兼容 UTF-8 BOM：PowerShell `Set-Content -Encoding UTF8`（5.1）会写 BOM，
// readFileSync utf8 会把它带进字符串 → JSON.parse 报 "Unexpected token ﻿"（Windows 常见）。
let paramsRaw = readFileSync(cli.json, "utf8");
if (paramsRaw.charCodeAt(0) === 0xfeff) paramsRaw = paramsRaw.slice(1);
const p = JSON.parse(paramsRaw);
const { idempotencyKey, accessKeyId, secretAccessKey, securityToken, trainingCampId, workName, introduction,
  coverImage, detailZip, gitUrl, gitBranch, envUrl = "", _refresh } = p;

const unknownKeys = Object.keys(p).filter((k) => !VALID_PARAM_KEYS.has(k));
if (unknownKeys.length) {
  console.error(`❌ 参数 JSON 含未知 key: ${unknownKeys.join(", ")}（合法 key 是 coverImage/detailZip；勿用 coverImagePath/detailsZipPath/imagePath/detailPath 等别名；domainId 不作为参数，仅拼进 Idempotency-Key）`);
  console.error(PARAMS_SCHEMA_HELP);
  process.exit(2);
}
const REQUIRED_FIELDS = ["idempotencyKey", "accessKeyId", "secretAccessKey", "securityToken", "trainingCampId",
  "workName", "introduction", "coverImage", "detailZip", "gitUrl", "gitBranch"];
const missingParams = REQUIRED_FIELDS.filter((k) => !p[k] || (k === "introduction" && typeof p[k] !== "string"));
if (missingParams.length) {
  console.error(`❌ 参数 JSON 缺少必要字段: ${missingParams.join(", ")}`);
  console.error(PARAMS_SCHEMA_HELP);
  process.exit(2);
}

// ---- 发布前强制门禁复核（fail-stop，程序性防线） ----
// 即使 agent 忘了 Step 8.5 的手动 check-gates 调用，发 HTTP 前也会被这里拦住：
// 校验 font-gate-ok / utf8-gate-ok / screenshot-gate-ok 标记（ok=true + gate 字段 + 新鲜度）
// 与封面/详情产物大小，任一未通过即 exit 1，不发送发布请求。
// --max-age <秒> 开启标记新鲜度校验，拦截上次会话残留的旧标记。
console.log("校验发布门禁（check-gates）...");
const gateResult = verifyGates({
  cover: coverImage,
  detail: detailZip,
  strict: true,
  quiet: false,
  maxAgeMs: cli.maxAge * 1000,
});
if (gateResult.failed > 0) {
  console.error(`\n❌ ${gateResult.failed} 个门禁未通过 — 禁止发布。请回退到对应步骤修复后重跑门禁，再重新执行 publish-work.mjs。`);
  process.exit(1);
}
if (gateResult.warned > 0) {
  console.warn(`⚠️ ${gateResult.warned} 个警告（宽松项）— 将在发布请求中继续，建议检查对应门禁。`);
}
console.log("✅ 发布门禁复核通过，开始准备发布请求。");

// 简介长度校验（与服务端 validateIntroductionLength 同口径：总 Unicode 码点数 15~50，含英文/数字/标点/emoji）
// 与 count-cjk.mjs（Step 5）一致——判定只看总字符数，中文字符数仅作信息输出，禁止只统计 CJK。
let cjk = 0;
for (const ch of introduction) {
  const cp = ch.codePointAt(0);
  if ((cp >= 0x4e00 && cp <= 0x9fff) || (cp >= 0x3400 && cp <= 0x4dbf) || (cp >= 0xf900 && cp <= 0xfaff)) cjk++;
}
const introLength = Array.from(introduction).length;
if (introLength < 15 || introLength > 50) {
  console.error(`简介总字符数 ${introLength}（中文字符数 ${cjk}）超出 15~50，与服务端校验同口径`);
  process.exit(1);
}

for (const [label, f] of [["封面", coverImage], ["详情zip", detailZip]]) {
  if (!f || !existsSync(f)) { console.error(`${label}文件不存在: ${f}`); process.exit(2); }
}

// ---- envUrl 可达性健康检查（隧道转发到本地服务，本地挂了 = 503，避免浪费 API 调用）----
// 超时给 10s：隧道首包可达实测需 ~10s，3s 会误判不可达。
function checkEnvUrl(urlString) {
  if (!urlString) return { ok: true, skipped: true };
  const nullDev = isWin ? "NUL" : "/dev/null";
  const r = spawnSync("curl", ["-sf", "--max-time", "10", "-o", nullDev, urlString],
    { encoding: "utf8", timeout: 15000, stdio: ["ignore", "pipe", "pipe"] });
  if (r.error) {
    console.warn(`⚠️ curl 不可用，跳过隧道可达性检查`);
    return { ok: true, skipped: true };
  }
  if (r.status === 0) return { ok: true };
  const err = (r.stderr || "").trim();
  return { ok: false, reason: err || `curl 退出码 ${r.status}` };
}

if (envUrl) {
  console.log(`检查隧道可达性: ${envUrl} ...`);
  const envCheck = checkEnvUrl(envUrl);
  if (!envCheck.ok) {
    console.error(`\n❌ 隧道 URL 不可达（${envCheck.reason}）。请检查本地服务是否运行、隧道进程是否存活。`);
    console.error(`   排查: curl -sf --max-time 10 ${envUrl}`);
    process.exit(1);
  }
  console.log("✅ 隧道可达性检查通过。");
}

// 凭证落盘 → api.mjs --creds-file 传递（不经 argv，彻底规避超长 security_token 截断）
// 若 params 含 _refresh 元数据，一并写入 creds 文件，使 api.mjs --auto-refresh 能在 401 时自动刷新
const credsFile = path.join(os.tmpdir(), `sts-creds-${process.pid}.json`);
const credsObj = { accessKeyId, secretAccessKey, securityToken };
if (_refresh && _refresh.accountId && _refresh.agencyUrn && _refresh.region) {
  credsObj._refresh = _refresh;
}
try {
  writeFileSync(credsFile, JSON.stringify(credsObj), "utf8");
} catch (e) {
  console.error(`无法写临时凭证文件: ${e.message}`); process.exit(2);
}

const args = [cli.api, "POST", "/v1/gallery/works", "--idempotency-key", idempotencyKey,
  "--creds-file", credsFile,
  "--form", `trainingCampId=${trainingCampId}`,
  "--form", `workName=${workName}`, "--form", `introduction=${introduction}`,
  "--file", `image=@${coverImage}`,
  "--file", `detail=@${detailZip}`, "--form", `gitUrl=${gitUrl}`,
  "--form", `gitBranch=${gitBranch}`, "--form", `envUrl=${envUrl}`];

// 若有 _refresh 元数据，启用 401 自动刷新
if (_refresh) args.push("--auto-refresh");

console.log(`发布作品「${workName}」（UTF-8 参数）...`);
try {
  const raw = execFileSync(process.execPath, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  // 成功时截断冗长响应（服务端回显完整 markdown 详情 ~4k token），仅输出关键字段；
  // 失败时原样输出完整响应供排查。
  const nlIdx = raw.indexOf("\n");
  const statusLine = nlIdx >= 0 ? raw.slice(0, nlIdx) : raw;
  const body = nlIdx >= 0 ? raw.slice(nlIdx + 1) : "";
  if (statusLine.includes("201")) {
    try {
      const resp = JSON.parse(body);
      const w = resp?.data?.work;
      const r = resp?.data?.reward;
      console.log(`#status=201`);
      console.log(`workId=${w?.id ?? ""}`);
      console.log(`workName=${w?.name ?? workName}`);
      console.log(`workUrl=${w?.workUrl ?? resp?.data?.workUrl ?? ""}`);
      if (r) console.log(`reward=${r.is_success ? "success" : "failed"} value=${r.value ?? ""} msg=${r.error_msg ?? ""}`);
      else console.log(`reward=none`);
    } catch {
      // JSON 解析失败，回退到原样输出
      process.stdout.write(raw);
    }
  } else {
    // 非 201（409/其他错误）原样输出完整响应
    process.stdout.write(raw);
  }
  try { unlinkSync(credsFile); } catch {}
  process.exit(0);
} catch (e) {
  process.stdout.write((e.stdout?.toString() || "") + (e.stderr?.toString() || ""));
  try { unlinkSync(credsFile); } catch {}
  console.error("\n发布失败（api.mjs 非 2xx 或异常）");
  process.exit(1);
}
