#!/usr/bin/env node
// api.mjs — 统一平台 REST 调用（fail-fast，跨平台，无第三方依赖）
//
// 背景:
//   平台仅有的 API（camps 查询 / works 发布）此前在 SKILL.md 里以
//   curl 双份内联重复，易失配、胶水代码冗长。
//   本脚本收敛为单一入口：host/协议可配置（见下方 HOST/PROTOCOL）/连接超时 3s，支持 GET 与 multipart POST。
//
// 约定（无需每次传）:
//   host/protocol = 见下方 HOST / PROTOCOL 配置（切换环境仅改该处）
//   connectTimeout = 3000ms
//   ─ 凭证注入：--creds-file 或 STS_AK/STS_SK/STS_TOKEN 任一来源的凭证会自动注入
//     X-Tmp-Ak / X-Tmp-Sk / X-Security-Token 三个请求头；若同时显式传了这些头，以显式为优先。
//
// 401 自动刷新（--auto-refresh）:
//   收到 401 GALLERY.AUTH.UNAUTHORIZED 时，若 creds 文件含 _refresh 元数据
//   （accountId, agencyUrn, region），自动调 hcloud STS AssumeAgency 重新生成
//   临时凭证、更新 creds 文件、用新凭证重试请求（仅重试一次）。
//   无 _refresh 元数据或刷新失败 → 原样返回 401（向后兼容）。
//
// 用法、选项、退出码详见 node api.mjs --help。stdout = 平台原样响应体（首行 #status=<code>）。

import http from "node:http";
import https from "node:https";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

// ===== 发布环境配置 =====
// 优先使用环境变量 GALLERY_API_HOST；未设置时回退到测试平台默认域名。
// 生产环境请通过环境变量覆盖。
const HOST = process.env.GALLERY_API_HOST || "gallery.developer.huaweicloud.com";
const PROTOCOL = (process.env.GALLERY_API_PROTOCOL || "https").toLowerCase();
const PORT = PROTOCOL === "https" ? 443 : 80;
const transport = PROTOCOL === "https" ? https : http;
// ========================================================

const CONNECT_TIMEOUT = 3000;

const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".zip": "application/zip",
  ".pdf": "application/pdf",
};

function printHelp() {
  console.log(`api.mjs — 统一平台 REST 调用（fail-fast，跨平台，无第三方依赖）

用法:
  node api.mjs GET  <path> [--query "k=v&k2=v2"] [--header "Name: value"]...
  node api.mjs POST <path> [--query "k=v"] [--header "Name: value"]...
                        [--form "field=value"]... [--file "image=/abs/path.png"]...
                        [--idempotency-key "key"]
  node api.mjs -h | --help

参数:
  <method>             GET 或 POST
  <path>               API 路径（如 /v1/gallery/camps，自动加前缀，默认 /open-api-public，
                       可用 --prefix 切换为 /open-api-guest）

选项:
  --query "k=v"        查询参数（可叠加）
  --header "N: v"      请求头（可叠加，支持 = 或 : 分隔）
  --form "f=v"         multipart 表单字段（可叠加）
  --file "n=@/path"    multipart 文件字段（@ 前缀可选）
  --idempotency-key    幂等键（发布时必填）
  --prefix <name>      API 前缀：open-api-public（默认，需 STS 凭证）或 open-api-guest
                       （无需凭证，如公告接口 /v1/gallery/announcements/current）
  --creds-file <json>  从文件读 STS 凭证（推荐）：{accessKeyId, secretAccessKey, securityToken}
                       或 hcloud 输出风格 {access_key_id, secret_access_key, security_token}；
                       JSON 文件内任一 key 名均可。自动注入 X-Tmp-Ak/X-Tmp-Sk/X-Security-Token 头。
                       若 JSON 含 _refresh {accountId, agencyUrn, region} 元数据，
                       配合 --auto-refresh 可在 401 时自动刷新凭证。
  --auto-refresh       401 GALLERY.AUTH.UNAUTHORIZED 时自动刷新 STS 凭证并重试（仅一次）。
                        需 --creds-file 且文件含 _refresh 元数据。
  --fields <list>      响应字段投影（仅 GET JSON 列表生效）：逗号分隔字段名，
                        如 --fields "id,name,status,startsAt,endsAt"，
                        只输出 data.items[] 中指定字段，减少大响应的 token 消耗。
                        非 JSON / 非 items 数组时忽略，原样输出。
  -h, --help           显示本帮助

约定:
  host = ${HOST}  连接超时 ${CONNECT_TIMEOUT}ms  stdout = 响应体（首行 #status=<code>）
  凭证也可经环境变量 STS_AK / STS_SK / STS_TOKEN 传入（与 /tmp/sts-creds.sh 兼容）
  HTTPS 非 2xx → exit 1
`);
}

function parseArgs(argv) {
  if (argv[0] === "-h" || argv[0] === "--help") {
    printHelp();
    process.exit(0);
  }
  const o = {
    method: argv[0] || "GET",
    argPath: argv[1],
    query: "",
    headers: [],
    fields: [],
    files: [], // {name, absPath}
    idempotencyKey: null,
    credsFile: null,
    autoRefresh: false,
    prefix: "open-api-public",
    fieldsList: null,
  };
  const raw = argv.slice(2);
  // kv() 同时支持 `=` 与 `:` 分隔（`: ` 后带空格兼容 REST 头写法）
  // 取最先出现的分隔符，避免值中含 `=`（如 base64 填充的 securityToken）时误切：
  const kv = (v) => {
    const eq = v.indexOf("=");
    const colon = v.indexOf(":");
    let i;
    if (eq === -1) i = colon;
    else if (colon === -1) i = eq;
    else i = Math.min(eq, colon);
    if (i === -1) return [v, ""];
    let value = v.slice(i + 1);
    value = value.trim();
    return [v.slice(0, i).trim(), value];
  };
  for (let k = 0; k < raw.length; k++) {
    const a = raw[k];
    if (a === "-h" || a === "--help") { printHelp(); process.exit(0); }
    else if (a === "--query") o.query = (o.query ? "&" : "") + raw[++k];
    else if (a === "--header") {
      const [n, v] = kv(raw[++k]);
      o.headers.push([n, v]);
    } else if (a === "--form") {
      const [n, v] = kv(raw[++k]);
      o.fields.push([n, v]);
    } else if (a === "--file") {
      const [n, v] = kv(raw[++k]);
      o.files.push([n, v.substr(0, 1) === "@" ? v.slice(1) : v]);
    }     else if (a === "--idempotency-key") o.idempotencyKey = raw[++k];
    else if (a === "--creds-file") o.credsFile = raw[++k];
    else if (a === "--auto-refresh") o.autoRefresh = true;
    else if (a === "--fields") {
      const v = raw[++k];
      if (!v) { console.error("❌ --fields 需要参数"); process.exit(2); }
      o.fieldsList = v.split(",").map((s) => s.trim()).filter(Boolean);
    }
    else if (a === "--prefix") {
      const value = raw[++k];
      if (value !== "open-api-public" && value !== "open-api-guest") {
        console.error(`❌ --prefix 仅支持 open-api-public / open-api-guest，收到: ${value}`);
        process.exit(2);
      }
      o.prefix = value;
    }
    else {
      console.error(`❌ 未知参数: ${a}\n  运行 node api.mjs --help 查看用法。`);
      process.exit(2);
    }
  }
  return o;
}

// ---- STS 凭证解析（规避超长 security_token 经命令行传递被截断）----
// 优先级: --creds-file <json>（含 hcloud 输出风格 key）> 环境变量 STS_AK/STS_SK/STS_TOKEN。
// 解析成功后把这些凭证注入为 X-Tmp-Ak / X-Tmp-Sk / X-Security-Token 头（已有显式同名头则不覆盖）。
// 返回 { injected: boolean }。找不到任何凭证来源 → 不注入（由服务端决定是否 400 缺凭证）。
function resolveCreds(o) {
  let ak, sk, token;
  if (o.credsFile) {
    let raw;
    try {
      raw = readFileSafe(o.credsFile);
    } catch (e) {
      console.error(`❌ 无法读取 --creds-file: ${o.credsFile} — ${e && e.message}`);
      process.exit(2);
    }
    try {
      const c = JSON.parse(raw);
      ak = c.accessKeyId ?? c.access_key_id ?? c.AK;
      sk = c.secretAccessKey ?? c.secret_access_key ?? c.SK;
      token = c.securityToken ?? c.security_token ?? c.token;
    } catch {
      console.error(`❌ --creds-file 不是合法 JSON: ${o.credsFile}`);
      process.exit(2);
    }
  } else {
    ak = process.env.STS_AK;
    sk = process.env.STS_SK;
    token = process.env.STS_TOKEN;
  }
  if (!ak || !sk || !token) return { injected: false };
  // 移除可能已存在的旧 STS 头（刷新后重注入）
  o.headers = o.headers.filter(([n]) => !/^X-Tmp-(Ak|Sk)$/i.test(n) && !/^X-Security-Token$/i.test(n));
  o.headers.push(["X-Tmp-Ak", ak], ["X-Tmp-Sk", sk], ["X-Security-Token", token]);
  return { injected: true };
}

function readFileSafe(p) {
  return fs.readFileSync(p, "utf8");
}

// 定位 hcloud（KooCLI）可执行文件：
// 优先级 ① _refresh.hcloudExe（Step 1 生成凭证时落盘的实际路径，401 自动刷新优先复用）
//        ② HCLOUD_EXE 环境变量
//        ③ PATH 上的 hcloud
//        ④ Windows 常见安装目录（$PWD\hcloud-cli、$USERPROFILE 下等，与 SKILL.md Step 7a 指引一致）
// 找不到时返回 "hcloud"，由 execFileSync 自然报错，不阻断逻辑。
function findHcloudBin(refresh) {
  if (refresh && refresh.hcloudExe) return refresh.hcloudExe;
  if (process.env.HCLOUD_EXE) return process.env.HCLOUD_EXE;
  if (process.platform !== "win32") return "hcloud";
  const candidates = [
    path.join(process.cwd(), "hcloud-cli", "hcloud.exe"),
    path.join(os.homedir(), "hcloud-cli", "hcloud.exe"),
    path.join(os.homedir(), ".huawei", "hcloud.exe"),
    path.join(os.homedir(), ".huawei", "bin", "hcloud.exe"),
    path.join(os.homedir(), "hcloud", "hcloud.exe"),
  ];
  for (const c of candidates) {
    try {
      if (fs.existsSync(c)) return c;
    } catch {
      /* ignore */
    }
  }
  return "hcloud";
}

// ---- 401 自动刷新：调 hcloud 重新生成 STS 临时凭证 ----
// 读取 creds 文件中的 _refresh 元数据（accountId, agencyUrn, region），
// 调 hcloud STS AssumeAgency 重新生成凭证，更新 creds 文件（保留 _refresh）。
// 成功返回 true，失败返回 false。
function refreshStsCreds(credsFile) {
  if (!credsFile || !fs.existsSync(credsFile)) return false;
  let credsObj;
  try {
    credsObj = JSON.parse(readFileSafe(credsFile));
  } catch {
    return false;
  }
  const refresh = credsObj._refresh;
  if (!refresh || !refresh.accountId || !refresh.agencyUrn || !refresh.region) {
    return false;
  }

  // 查找 hcloud 可执行文件（Windows: hcloud 可能在 $PWD\hcloud-cli\ 等目录，
  // 未加入 PATH 时须显式扫描，与 SKILL.md Step 7a 的 Windows 指引保持一致；
  // 优先复用 Step 1 落盘在 _refresh.hcloudExe 的实际路径，避免刷新时 ENOENT）
  const hcloudBin = findHcloudBin(refresh);
  const policy = JSON.stringify({
    Version: "5.0",
    Statement: [{ Effect: "Allow", Action: ["sts::GetCallerIdentity", "iam::listAuthDomains"], Resource: ["*"] }],
  });
  const sessionName = `publish-refresh-${Date.now()}`;

  let stdout;
  try {
    stdout = execFileSync(hcloudBin, [
      "STS", "AssumeAgency",
      `--cli-region=${refresh.region}`,
      `--agency_urn=${refresh.agencyUrn}`,
      `--agency_session_name=${sessionName}`,
      "--duration_seconds=900",
      `--policy=${policy}`,
    ], { encoding: "utf8", timeout: 15000, stdio: ["ignore", "pipe", "pipe"] });
  } catch (e) {
    console.error(`⚠️ STS 凭证刷新失败（hcloud 调用出错）: ${e && e.message}`);
    return false;
  }

  let newCreds;
  try {
    newCreds = JSON.parse(stdout).credentials;
  } catch {
    console.error("⚠️ STS 凭证刷新失败（hcloud 返回非 JSON）");
    return false;
  }

  // 更新 creds 文件（保留 _refresh 元数据）
  const updated = {
    accessKeyId: newCreds.access_key_id,
    secretAccessKey: newCreds.secret_access_key,
    securityToken: newCreds.security_token,
    _refresh: refresh,
  };
  try {
    fs.writeFileSync(credsFile, JSON.stringify(updated, null, 2), "utf8");
  } catch (e) {
    console.error(`⚠️ STS 凭证刷新失败（无法写入 creds 文件）: ${e && e.message}`);
    return false;
  }

  console.error("ℹ️ STS 凭证已自动刷新（检测到 401，凭证可能已过期）");
  return true;
}

function buildBody(o) {
  if (o.files.length === 0) {
    return { headers: {}, body: null };
  }
  const boundary = "----FormBoundary" + Date.now();
  const chunks = [];
  const CRLF = "\r\n";
  const add = (c) => chunks.push(Buffer.from(c, "utf8"));
  for (const [n, v] of o.fields) {
    add(`--${boundary}${CRLF}`);
    add(`Content-Disposition: form-data; name="${n}"${CRLF}${CRLF}`);
    add(`${v}${CRLF}`);
  }
  for (const [n, file] of o.files) {
    const abs = path.resolve(file);
    add(`--${boundary}${CRLF}`);
    add(`Content-Disposition: form-data; name="${n}"; filename="${path.basename(abs)}"${CRLF}`);
    const ext = path.extname(abs).toLowerCase();
    const ctype = MIME[ext] || "application/octet-stream";
    add(`Content-Type: ${ctype}${CRLF}${CRLF}`);
    chunks.push(fs.readFileSync(abs));
    add(CRLF);
  }
  add(`--${boundary}--${CRLF}`);
  return {
    headers: { "Content-Type": `multipart/form-data; boundary=${boundary}` },
    body: Buffer.concat(chunks),
  };
}

// ---- 发送 HTTP 请求并返回 { statusCode, text }（Promise）----
function sendRequest(o) {
  return new Promise((resolve, reject) => {
    const { headers, body } = buildBody(o);
    const query = o.query ? "?" + o.query : "";
    const url = `/${o.prefix}${o.argPath}${query}`;

    const reqH = transport.request(
      {
        host: HOST,
        port: PORT,
        path: url,
        method: o.method.toUpperCase(),
        headers: {
          ...headers,
          ...(o.idempotencyKey ? { "Idempotency-Key": o.idempotencyKey } : {}),
          ...Object.fromEntries(o.headers),
        },
      },
      (res) => {
        const data = [];
        res.on("data", (c) => data.push(c));
        res.on("end", () => {
          const text = Buffer.concat(data).toString("utf8");
          resolve({ statusCode: res.statusCode, text });
        });
      }
    );
    const connectTimer = setTimeout(() => {
      reqH.destroy(new Error(`连接 ${HOST} 超时（${CONNECT_TIMEOUT}ms）`));
    }, CONNECT_TIMEOUT);
    reqH.on("socket", (socket) => {
      socket.on("connect", () => clearTimeout(connectTimer));
    });
    reqH.on("response", () => clearTimeout(connectTimer));
    reqH.on("error", (e) => {
      reject(e);
    });
    reqH.write(body || "");
    reqH.end();
  });
}

async function main() {
  const o = parseArgs(process.argv.slice(2));
  if (!o.argPath) {
    console.error('❌ 用法: node api.mjs <GET|POST> <path> [--query ".."] [--header "N: v"] [--form "f=v"] [--file "n=@/path"] [--idempotency-key "k"] [--creds-file <json>] [--auto-refresh]\n  运行 node api.mjs --help 查看完整用法。');
    process.exit(2);
  }
  resolveCreds(o);

  let result;
  try {
    result = await sendRequest(o);
  } catch (e) {
    console.error(`❌ api.mjs 请求失败: ${e && e.message}`);
    process.exit(1);
  }

  // ---- 401 自动刷新 + 重试 ----
  if (
    result.statusCode === 401 &&
    result.text.includes("GALLERY.AUTH.UNAUTHORIZED") &&
    o.autoRefresh &&
    o.credsFile
  ) {
    const refreshed = refreshStsCreds(o.credsFile);
    if (refreshed) {
      // 重新解析凭证（会替换 o.headers 中的旧 STS 头）
      resolveCreds(o);
      try {
        result = await sendRequest(o);
      } catch (e) {
        console.error(`❌ api.mjs 重试请求失败: ${e && e.message}`);
        process.exit(1);
      }
    }
  }

  // ---- 输出响应 ----
  process.stdout.write(`#status=${result.statusCode}\n`);
  // 字段投影：对 GET JSON 列表响应（data.items[]）只输出指定字段，减少 token 消耗
  if (o.fieldsList && result.statusCode >= 200 && result.statusCode < 300) {
    try {
      const resp = JSON.parse(result.text);
      if (resp?.data?.items && Array.isArray(resp.data.items)) {
        const projected = resp.data.items.map((item) => {
          const out = {};
          for (const f of o.fieldsList) if (f in item) out[f] = item[f];
          return out;
        });
        const summary = { success: resp.success, code: resp.code, data: { items: projected, total: resp.data.total, pageNo: resp.data.pageNo, pageSize: resp.data.pageSize } };
        if (resp.data.resolvedIdentity) summary.data.resolvedIdentity = resp.data.resolvedIdentity;
        process.stdout.write(JSON.stringify(summary));
        if (result.statusCode === undefined || result.statusCode < 200 || result.statusCode >= 300) {
          process.exitCode = 1;
        }
        return;
      }
    } catch {
      // 非 JSON 或结构不匹配，回退到原样输出
    }
  }
  process.stdout.write(result.text);
  if (result.statusCode === undefined || result.statusCode < 200 || result.statusCode >= 300) {
    process.exitCode = 1;
  }
}

main();
