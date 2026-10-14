#!/usr/bin/env node
// read-git-info.mjs — 读取作品目录 git 仓库信息（gitUrl/gitBranch，含仓库自检 + 凭证剥离 + 远端分支核对）
// 共享脚本：本文件（huawei-cloud-publish-work-to-gallery）为源；huawei-cloud-publish-ict-work 为 vendored 副本
// （头部带 sync-src），改动须同步同源两端。
//
// 背景:
//   SKILL.md Step 3 原由 agent 手动跑 `git -C <workDir> remote get-url origin` / `branch --show-current`，
//   再另跑 strip-git-credential.mjs 剥离凭证、手动拼 gitUrl。本脚本一步封装：
//     * git 仓库完整性自检（非 git 仓库 → exit 1）
//     * 读 origin 与当前分支
//     * 剥离内嵌凭证 + 硬校验（https://、.git 结尾、无 @）——复用 strip-git-credential 语义内联
//     * 远端分支核对（2026-09-25 新增，见下）
//
// 用法:
//   node read-git-info.mjs <workDir>
//   node read-git-info.mjs --help
//
// stdout:
//   #gitUrl=<绝对或规范 clone URL，https:// 开头、.git 结尾、无凭证>
//   #gitBranch=<HEAD 当前分支名>
//
// 退出码: 0=成功; 1=workDir 非 git 仓库 / url 校验失败 / 远端不存在该分支(#branchAbsent=1); 2=参数错误
//
// 远端分支核对（2026-09-25）:
//   gitBranch 取的是本地当前分支名，不保证远端真有该分支（常见分叉：本地 git init 默认 master、
//   GitCode 建仓默认 main，反之亦然——用户无需在远端手动改分支即可出现）。用
//   `git ls-remote --heads origin` 拉远端分支清单（一次网络调用）核对：
//     * 含 refs/heads/{branch} → 分支存在，放行
//     * 不含 → exit 1 #branchAbsent=1，并按 SHA 给唯一处置：
//         - 远端某分支 == 本地 HEAD（推送时被映射成远端默认分支名的典型场景）→ 直接 checkout 该分支后重跑，无损
//         - 无 SHA 一致（远端空壳/本地有未推提交）→ 先 git push 再重跑（切过去会提交旧代码）
//     * 网络不通/私有仓库暂无凭证 → 无法判定，stderr 警告后放行——提交/发布时后端
//       仍会以 info/refs 探测做分支存在性强校验（2026-09-25 对齐现网作品发布），此处只做提前拦截

import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const workDir = process.argv[2];
if (!workDir || workDir === "-h" || workDir === "--help") {
  console.log(`read-git-info.mjs — 读取作品目录 git 仓库信息（gitUrl + gitBranch）

用法:
  node read-git-info.mjs <workDir>

stdout:
  #gitUrl=<https://… .git>
  #gitBranch=<分支名>

退出码: 0=成功; 1=非 git 仓库 / url 校验失败 / 远端不存在该分支(#branchAbsent=1); 2=参数错误`);
  process.exit(workDir ? 0 : 2);
}

function git(args) {
  return execFileSync("git", ["-C", workDir, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}

/** 远端 heads 映射 { 分支名: sha }；null=网络/凭证原因无法判定（不拦截） */
function remoteHeads() {
  try {
    const out = execFileSync(
      "git",
      ["-C", workDir, "ls-remote", "--heads", "origin"],
      {
        encoding: "utf8",
        timeout: 10000,
        // 非交互：终端提示/GUI 凭证管理器一律禁用——私有仓库无凭证时快速失败走 unknown，不挂起
        env: { ...process.env, GIT_TERMINAL_PROMPT: "0", GIT_ASKPASS: "echo", GCM_INTERACTIVE: "Never" },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    const heads = {};
    for (const line of out.split("\n")) {
      const m = line.trim().match(/^([0-9a-f]{40,64})\trefs\/heads\/(.+)$/);
      if (m) heads[m[2]] = m[1];
    }
    return heads;
  } catch {
    return null;
  }
}

let rawUrl;
let branch;
try {
  rawUrl = git(["remote", "get-url", "origin"]);
  branch = git(["branch", "--show-current"]);
} catch (e) {
  console.error(
    `❌ workDir 不是有效 git 仓库（或缺少 origin）：${workDir}\n${(e.stderr?.toString() || e.message || "").trim() || ""}`,
  );
  process.exit(1);
}

// 凭证剥离 + 硬校验（与 strip-git-credential 同语义）：
//   剥离 <scheme>://<user>:<pass>@（或 <scheme>://<token>@）→ 不得再含 @、必须 https:// 开头、.git 结尾
let safeUrl = rawUrl.replace(/^(https?:\/\/)[^/@]+@/, "$1");
if (!safeUrl.startsWith("https://") || !safeUrl.endsWith(".git") || safeUrl.includes("@")) {
  console.error(`❌ gitUrl 不合规（须 https:// 开头、.git 结尾、无内嵌凭证）: ${safeUrl}`);
  process.exit(1);
}

if (!branch) {
  console.error(`❌ 当前 HEAD 无分支名（detached HEAD？），请先 checkout 到具名分支: ${workDir}`);
  process.exit(1);
}

const heads = remoteHeads();
if (heads === null) {
  console.error(`⚠️ 无法核对远端分支「${branch}」（网络/凭证受限，不拦截；提交时后端会再次校验分支存在性）`);
} else if (!heads[branch]) {
  // 分支不存在：按内容（SHA）而非名字给唯一处置——远端某分支与本地当前提交一致 → 切换即无损；
  // 否则（远端空壳/本地有未推提交）切过去提交的是旧代码，必须先推送
  let headSha = null;
  try { headSha = git(["rev-parse", "HEAD"]) || null; } catch { headSha = null; }
  const same = headSha ? Object.keys(heads).find((name) => heads[name] === headSha) : undefined;
  console.error(`❌ 远端仓库不存在分支「${branch}」: ${safeUrl}`);
  console.error(`   本地分支名与远端实际分支不一致（常见：本地 git init 默认 master、远端建仓默认 main，反之亦然）。`);
  if (same) {
    console.error(`   ✓ 远端分支「${same}」与你本地当前提交完全一致，切换后重跑即可（无需推送）: git checkout ${same}`);
  } else {
    console.error(`   请先推送本地分支到远端: git push -u origin ${branch}`);
  }
  console.error(`   远端现有分支: ${Object.keys(heads).join("、") || "（空仓库）"}`);
  console.error(`#branchAbsent=1`);
  process.exit(1);
}

console.log(`#gitUrl=${safeUrl}`);
console.log(`#gitBranch=${branch}`);
process.exit(0);
