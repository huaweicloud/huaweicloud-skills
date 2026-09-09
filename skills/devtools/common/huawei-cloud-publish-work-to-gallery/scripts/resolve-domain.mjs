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
import { homedir } from "node:os";
import path from "node:path";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
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
function findHcloud() {
  if (hcloudExe && existsSync(hcloudExe)) return hcloudExe;
  // Windows 常见安装目录
  if (process.platform === "win32") {
    const candidates = [
      path.join(process.cwd(), "hcloud-cli", "hcloud.exe"),
      path.join(homedir(), "hcloud-cli", "hcloud.exe"),
      path.join(homedir(), ".huawei", "bin", "hcloud.exe"),
    ];
    for (const c of candidates) { if (existsSync(c)) return c; }
  }
  return "hcloud"; // 依赖 PATH
}

const hcloud = findHcloud();

function tryExec(cmd) {
  try {
    return execSync(cmd, { encoding: "utf8", timeout: 15000, stdio: ["ignore", "pipe", "pipe"] }).trim();
  } catch (e) {
    return null;
  }
}

// 1. configure set region
const cfgOut = tryExec(`"${hcloud}" configure set --cli-region=${region}`);
if (cfgOut === null) {
  console.error(`❌ hcloud configure set --cli-region=${region} 失败。请检查 hcloud 是否安装且在 PATH 中。`);
  console.error(`   Windows 常见: hcloud.exe 不在 PATH → 传 --hcloud <绝对路径>`);
  console.error(`   安装引导见 references/troubleshooting.md#1-hcloud-not-installed`);
  process.exit(1);
}

// 2. KeystoneListAuthDomains
const domainsOut = tryExec(`"${hcloud}" IAM KeystoneListAuthDomains`);
if (domainsOut === null) {
  console.error(`❌ hcloud IAM KeystoneListAuthDomains 失败。`);
  console.error(`   常见: AK/SK 未配置或过期 → 设环境变量 HUAWEICLOUD_SDK_AK/SK[/SECURITY_TOKEN]`);
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