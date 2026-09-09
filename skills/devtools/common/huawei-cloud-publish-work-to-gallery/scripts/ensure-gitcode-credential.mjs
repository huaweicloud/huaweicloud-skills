#!/usr/bin/env node
// ensure-gitcode-credential.mjs — GitCode 凭证排查 + gitcode-oauth skill 安装检测（一键）
//
// 背景:
//   SKILL.md Step 3 内联了 ~12 行 gitcode-oauth 安装/排查逻辑（凭证检测、skill 存在性、
//   安装命令、Windows 兼容性），每次加载 SKILL.md 都付费。本脚本封装为单入口，
//   agent 只跑一条命令，按 stdout 决策。
//
// 用法:
//   node ensure-gitcode-credential.mjs [--work-dir <dir>]
//
// 行为:
//   1. 检测本机已有 GitCode 凭证（git credential fill / ~/.git-credentials / $GITCODE_TOKEN / cmdkey）
//   2. 有凭证 → exit 0，stdout "#credential=found source=<来源>"
//   3. 无凭证 + Linux/macOS → exit 0，stdout "#credential=missing action=manual"（提示用 git credential fill 等）
//   4. 无凭证 + Windows → 检测 gitcode-oauth skill 是否已装
//      - 已装 → exit 0，stdout "#credential=missing skill=installed"（提示用该 skill 扫码登录）
//      - 未装 → exit 1，stdout "#credential=missing skill=absent"，stderr 给安装命令 + Windows 兼容提示
//
// 退出码: 0=有凭证或已有可行路径; 1=需要 agent 介入安装

import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const args = process.argv.slice(2);
let workDir = ".";
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--work-dir") workDir = args[++i];
  else if (args[i] === "-h" || args[i] === "--help") {
    console.log(`ensure-gitcode-credential.mjs — GitCode 凭证排查 + skill 安装检测

用法:
  node ensure-gitcode-credential.mjs [--work-dir <dir>]

退出码:
  0 = 有凭证 / 或已有可行路径（manual 或 skill 已装）
  1 = Windows 无凭证且 gitcode-oauth skill 未装（stderr 含安装命令）`);
    process.exit(0);
  }
}

function tryExec(cmd) {
  try { return execSync(cmd, { encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] }).trim(); }
  catch { return ""; }
}

// ---- 1. 检测本机已有凭证 ----
let credSource = "";

// git credential fill
const fillOut = tryExec('echo -e "protocol=https\\nhost=gitcode.com" | git credential fill 2>/dev/null');
if (fillOut && fillOut.includes("password=")) credSource = "git-credential-fill";

// ~/.git-credentials
if (!credSource) {
  const credFile = path.join(homedir(), ".git-credentials");
  if (existsSync(credFile)) {
    const raw = readFileSync(credFile, "utf8");
    if (raw.includes("gitcode.com")) credSource = "git-credentials-file";
  }
}

// $GITCODE_TOKEN
if (!credSource) {
  const tok = process.env.GITCODE_TOKEN;
  if (tok) credSource = "env-GITCODE_TOKEN";
}

// Windows cmdkey
if (!credSource && process.platform === "win32") {
  const cmdkeyOut = tryExec('cmdkey /list:git:https://gitcode.com 2>nul');
  if (cmdkeyOut) credSource = "cmdkey";
}

if (credSource) {
  console.log(`#credential=found source=${credSource}`);
  process.exit(0);
}

// ---- 2. 无凭证 ----
const isWindows = process.platform === "win32";

if (!isWindows) {
  // Linux/macOS: 凭证助手通常健全，提示手动配置
  console.log(`#credential=missing action=manual`);
  console.error(`未检测到 GitCode 凭证。Linux/macOS 请用以下任一方式配置：
  1. git credential fill（交互输入）
  2. ~/.git-credentials 文件写入 https://<user>:<token>@gitcode.com
  3. export GITCODE_TOKEN=<token>`);
  process.exit(0);
}

// ---- 3. Windows: 检测 gitcode-oauth skill ----
const skillDirs = [
  path.join(homedir(), ".claude", "skills", "gitcode-oauth"),
  path.join(homedir(), ".config", "opencode", "skills", "gitcode-oauth"),
  path.join(process.cwd(), ".agents", "skills", "gitcode-oauth"),
];
const skillInstalled = skillDirs.some((d) => existsSync(d));

if (skillInstalled) {
  console.log(`#credential=missing skill=installed`);
  console.error(`GitCode 凭证未检测到，但 gitcode-oauth skill 已安装。
请用该 skill 扫码登录获取 token（用 Git Bash 执行其脚本）。`);
  process.exit(0);
}

// ---- 4. Windows + 无凭证 + skill 未装 → 输出安装命令 ----
console.log(`#credential=missing skill=absent`);
console.error(`GitCode 凭证未检测到，且 gitcode-oauth skill 未安装。

安装命令（项目级，--copy 避免 Windows 无管理员权限建链接失败）:
  npx skills add https://gitcode.com/zhoucungen/gitcode-oauth.git --skill gitcode-oauth --copy -y

装完按该 skill 的 SKILL.md 扫码登录拿 token。

⚠️ Windows 兼容: gitcode-oauth 脚本是 bash（.sh），原生 PowerShell/cmd 不认，
   登录/轮询必须用 Git Bash 执行（如 & "C:\\Program Files\\Git\\bin\\bash.exe" <script>.sh ...）。`);
process.exit(1);