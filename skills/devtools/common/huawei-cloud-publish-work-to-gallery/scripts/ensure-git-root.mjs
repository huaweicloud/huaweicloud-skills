#!/usr/bin/env node
// ensure-git-root.mjs — 检测 workDir 自身是否为 git 仓库根（fail-stop）
//
// 背景:
//   `git -C <workDir> remote get-url origin` 在 workDir 无 .git 时会向上递归
//   找到父仓库的 .git，返回父仓库的 remote/branch——这是错误的，会把父仓库
//   URL 当作作品 gitUrl 推送。本脚本硬检测 workDir 自身是否为仓库根：
//     `git -C <workDir> rev-parse --git-dir` 必须返回 `.git`（相对路径）
//   否则 exit 1，提示用户手动提供 gitUrl + gitBranch 或 git init。
// 用法、退出码详见 node ensure-git-root.mjs --help。

import { execFileSync } from "node:child_process";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const args = process.argv.slice(2);
if (args.includes("-h") || args.includes("--help")) {
  console.log(`ensure-git-root.mjs — 检测 workDir 自身是否为 git 仓库根（fail-stop）

用法:
  node ensure-git-root.mjs <workDir>

行为:
  - 运行 \`git -C <workDir> rev-parse --git-dir\`
  - 输出 \`.git\`（相对）= 仓库根 → exit 0，stdout \#git-root=ok
  - 输出绝对路径或向上递归 → exit 1，提示手动提供 gitUrl/gitBranch 或 git init

退出码: 0=workDir 是 git 仓库根; 1=不是（fail-closed）
`);
  process.exit(0);
}

const workDir = args[0];
if (!workDir) {
  console.error("❌ ensure-git-root: 缺少 <workDir> 参数");
  process.exit(2);
}

let gitDir;
try {
  gitDir = execFileSync("git", ["-C", workDir, "rev-parse", "--git-dir"], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
} catch (e) {
  console.error(`❌ ensure-git-root: workDir 不是 git 仓库（且父目录也无 .git）：${workDir}`);
  console.error("   请手动提供 gitUrl + gitBranch，或在 workDir 执行 git init 并推到远端。");
  process.exit(1);
}

if (gitDir === ".git") {
  console.log("#git-root=ok");
  process.exit(0);
}

console.error(`❌ ensure-git-root: workDir 自身不是 git 仓库根，git 向上递归到了父仓库。`);
console.error(`   workDir=${workDir}`);
console.error(`   git-dir=${gitDir}（非 .git，说明是父仓库的 .git）`);
console.error(`   若直接执行 \`git -C <workDir> remote get-url origin\` 会返回父仓库的 remote，导致推送错误 gitUrl。`);
console.error("   请手动提供 gitUrl + gitBranch，或在 workDir 执行 git init 并推到远端。");
process.exit(1);