#!/usr/bin/env node
// resolve-domain.mjs — 解析华为云 IAM Domain ID（hcloud configure + KeystoneListAuthDomains）
//
// 背景:
//   SKILL.md Step 1 内联了两条 hcloud 命令 + JSON 解析逻辑，agent 可能解析错字段。
//   本脚本封装为单入口，自动 configure set region + 调 IAM + 提取 domain_id。
//
// 用法:
//   node resolve-domain.mjs [--region cn-north-4] [--hcloud <path>]
//
// 行为:
//   1. hcloud configure set --region=<region>（exit 0 才继续）
//   2. hcloud IAM KeystoneListAuthDomains
//   3. 从响应 JSON 提取 domain_id（首条 auth domain 的 domain.id）
//   4. stdout: `#domain=<id> name=<domainName>`
//
// 凭证来源（hcloud 自动读取）:
//   env HUAWEICLOUD_SDK_AK/SK[/SECURITY_TOKEN] → hcloud 已配置 → 失败报错引导
//
// 退出码: 0=成功; 1=hcloud 调用失败/解析失败; 2=参数错误

import { execSync } from "node:child_process";
import { existsSync } from "node:fs";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

// AK/SK/Token 环境变量归一化：hcloud 只认 HUAWEICLOUD_SDK_AK/SK/SECURITY_TOKEN，
// 按优先级回退别名，命中别名时注入 SDK 变量名，供 hcloud 子进程读取。
// 仅当 SDK 变量未设置且别名命中时才写，不覆盖用户显式设置的 SDK 变量。
function normalizeAkskEnv() {
  const chains = {
    HUAWEICLOUD_SDK_AK: ["HUAWEICLOUD_AK", "HW_ACCESS_KEY"],
    HUAWEICLOUD_SDK_SK: ["HUAWEICLOUD_SK", "HW_SECRET_KEY"],
    HUAWEICLOUD_SDK_SECURITY_TOKEN: ["HUAWEICLOUD_SECURITY_TOKEN", "HW_SECURITY_TOKEN"],
  };
  for (const [sdk, aliases] of Object.entries(chains)) {
    if (process.env[sdk]) continue;
    for (const a of aliases) {
      if (process.env[a]) { process.env[sdk] = process.env[a]; break; }
    }
  }
}
normalizeAkskEnv();

// Windows 401 专项（KooCLI 7.2.12）：Windows 上 KooCLI 读取 HUAWEICLOUD_SDK_AK/SK env 有缺陷，
// 表现为 env 已设置但 hcloud 签名始终 401。命令行参数优先级最高，绕开 env 读取。
// 有 env AK/SK 时显式拼 --cli-access-key/--cli-secret-key[/--cli-security-token]。
function akskCliArgs() {
  const ak = process.env.HUAWEICLOUD_SDK_AK;
  const sk = process.env.HUAWEICLOUD_SDK_SK;
  const tok = process.env.HUAWEICLOUD_SDK_SECURITY_TOKEN;
  const args = [];
  if (ak) args.push(`--cli-access-key=${ak}`);
  if (sk) args.push(`--cli-secret-key=${sk}`);
  if (tok) args.push(`--cli-security-token=${tok}`);
  return args;
}

const REGION = "cn-north-4";
const args = process.argv.slice(2);
let region = REGION;
let hcloudExe = "";

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--region") region = args[++i] || REGION;
  else if (args[i] === "--hcloud") hcloudExe = args[++i] || "";
  else if (args[i] === "-h" || args[i] === "--help") {
    console.log(`resolve-domain.mjs — 解析华为云 IAM Domain ID

用法:
  node resolve-domain.mjs [--region ${REGION}] [--hcloud <exe路径>]

行为:
  1. hcloud configure set --region=<region>
  2. hcloud IAM KeystoneListAuthDomains
  3. 提取 domain_id

退出码: 0=成功; 1=失败; 2=参数错误`);
    process.exit(0);
  }
}

// 定位 hcloud
// 仅按 PATH（where/which），不扫描固定目录——工具统一经 ensure-user-bindir.mjs 目录暴露。
// --hcloud 显式指定仍优先（供排查/特殊环境绕过）。
function findHcloud() {
  if (hcloudExe && existsSync(hcloudExe)) return hcloudExe;
  if (process.env.HCLOUD_EXE && existsSync(process.env.HCLOUD_EXE)) return process.env.HCLOUD_EXE;
  return "hcloud"; // 依赖 PATH
}

const hcloud = findHcloud();

function tryExec(cmd) {
  // KooCLI 首次运行会交互确认隐私声明；非交互 stdin 下报 [USE_ERROR]，此时补一次管道输入 y 重试
  for (let attempt = 0; attempt < 2; attempt++) {
    const isInteractivePrompt = (out) => /同意并继续使用|USE_ERROR/.test(out);
    try {
      const out = execSync(cmd, {
        encoding: "utf8",
        timeout: 15000,
        stdio: ["pipe", "pipe", "pipe"],
        input: attempt > 0 ? "y\n" : "",
      }).trim();
      // KooCLI 可能在 exit 0 的同时把隐私声明/USE_ERROR 写进 stdout（非交互 stdin），
      // execSync 不抛异常，需按输出内容判断并带 y 重试一次
      if (attempt === 0 && isInteractivePrompt(out)) continue;
      return out;
    } catch (e) {
      const out = `${e.stdout || ""}${e.stderr || ""}`;
      if (attempt === 0 && isInteractivePrompt(out)) continue;
      return null;
    }
  }
  return null;
}

// 1. configure set region
const cfgOut = tryExec(`"${hcloud}" configure set --cli-region=${region} ${akskCliArgs().join(" ")}`);
if (cfgOut === null) {
  console.error(`❌ hcloud configure set --cli-region=${region} 失败。请检查 hcloud 是否安装且在 PATH 中。`);
  console.error(`   Windows 常见: hcloud.exe 不在 PATH → 传 --hcloud <绝对路径>`);
  console.error(`   安装引导见 references/troubleshooting.md#1-hcloud-not-installed`);
  process.exit(1);
}

// 2. KeystoneListAuthDomains
const domainsOut = tryExec(`"${hcloud}" IAM KeystoneListAuthDomains ${akskCliArgs().join(" ")}`);
if (domainsOut === null) {
  console.error(`❌ hcloud IAM KeystoneListAuthDomains 失败。`);
  console.error(`   常见: AK/SK 未配置或过期 → 设环境变量 HUAWEICLOUD_SDK_AK/SK[/SECURITY_TOKEN]（或别名 HUAWEICLOUD_AK/SK、HW_ACCESS_KEY/HW_SECRET_KEY）`);
  console.error(`   排查见 references/troubleshooting.md#2-hcloud-credentials-not-configured`);
  process.exit(1);
}

// 3. 解析 domain_id
let domainId = "";
let domainName = "";
try {
  const data = JSON.parse(domainsOut);
  // 响应结构: { "domains": [{ "id": "...", "name": "...", ... }] } 或数组
  const domains = Array.isArray(data) ? data : (data.domains || data.auth_domains || []);
  if (domains.length > 0) {
    domainId = domains[0].id || domains[0].domain_id || "";
    domainName = domains[0].name || domains[0].domain_name || "";
  }
} catch {
  // hcloud 可能输出非纯 JSON（含日志行），尝试提取 JSON 部分
  const jsonMatch = domainsOut.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const data = JSON.parse(jsonMatch[0]);
      const domains = Array.isArray(data) ? data : (data.domains || data.auth_domains || []);
      if (domains.length > 0) {
        domainId = domains[0].id || domains[0].domain_id || "";
        domainName = domains[0].name || domains[0].domain_name || "";
      }
    } catch {}
  }
}

if (!domainId) {
  console.error(`❌ 无法从 hcloud 响应中提取 domain_id。原始输出（前 300 字符）:`);
  console.error(domainsOut.substring(0, 300));
  console.error(`   排查见 references/troubleshooting.md#3-cannot-resolve-domain-id-automatically`);
  process.exit(1);
}

console.log(`#domain=${domainId} name=${domainName}`);
process.exit(0);