#!/usr/bin/env node
// scan-projects.mjs — 扫描当前工作目录下的项目根，输出编号候选列表
//
// 背景:
//   SKILL.md Step 1 内联了项目根扫描逻辑（glob README.md → 检查指示文件 → 排除规则），
//   排除规则有 6 条，agent 易漏排或误排。本脚本封装为单入口。
//
// 用法:
//   node scan-projects.mjs [--dir <searchDir>] [--max-depth <n>]
//
// 行为:
//   1. 递归搜索 README.md（含 readme.md，大小写不敏感）
//   2. 父目录含指示文件（package.json/pom.xml/requirements.txt/pyproject.toml/setup.py/
//      Cargo.toml/go.mod/index.html/Dockerfile/Makefile/.git/）即项目根
//   3. 排除: skills/ / node_modules/ / .git/ / dist/ / build/ / references/ / docs/ / tests/
//      （除非有指示文件）；/root/.ai-shell/SkillHub
//   4. CodeArts 沙箱: 扫描 /root/job-envs/sandboxes/codearts-*/ 下
//   5. stdout: 每行 `#project <n> <absPath> <type>`；无候选时 exit 1
//
// 退出码: 0=有候选; 1=无候选; 2=参数错误

import fs from "node:fs";
import path from "node:path";

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const args = process.argv.slice(2);
let searchDir = process.cwd();
let maxDepth = 8;
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--dir") searchDir = args[++i];
  else if (args[i] === "--max-depth") maxDepth = parseInt(args[++i], 10) || 8;
  else if (args[i] === "-h" || args[i] === "--help") {
    console.log(`scan-projects.mjs — 扫描项目根，输出编号候选列表

用法:
  node scan-projects.mjs [--dir <searchDir>] [--max-depth <n>]

指示文件: package.json / pom.xml / requirements.txt / pyproject.toml / setup.py /
          Cargo.toml / go.mod / index.html / Dockerfile / Makefile / .git/
排除目录: skills/ / node_modules/ / .git/ / dist/ / build/ / references/ / docs/ / tests/
          /root/.ai-shell/SkillHub

退出码: 0=有候选; 1=无候选; 2=参数错误`);
    process.exit(0);
  }
}

const INDICATORS = [
  ["package.json", "Node.js"],
  ["pom.xml", "Java/Maven"],
  ["build.gradle", "Java/Gradle"],
  ["requirements.txt", "Python"],
  ["pyproject.toml", "Python"],
  ["setup.py", "Python"],
  ["Cargo.toml", "Rust"],
  ["go.mod", "Go"],
  ["Dockerfile", "Container"],
  ["Makefile", "C/C++"],
];

const EXCLUDE_DIRS = new Set([
  "skills", "node_modules", ".git", "dist", "build",
  "references", "docs", "tests", "__pycache__",
  ".opencode", ".codeartsdoer", ".vscode", ".idea",
]);

const EXCLUDE_PATHS = [
  "/root/.ai-shell/SkillHub",
];

const HTML_INDICATOR_RE = /^index\.html?$/i;

function isProjectRoot(dir) {
  // .git 目录
  if (fs.existsSync(path.join(dir, ".git"))) return ["Git", true];
  // 指示文件
  for (const [file, type] of INDICATORS) {
    if (fs.existsSync(path.join(dir, file))) return [type, true];
  }
  // index.html 在根或 public/
  if (fs.existsSync(path.join(dir, "index.html"))) return ["Static", true];
  const publicHtml = path.join(dir, "public", "index.html");
  if (fs.existsSync(publicHtml)) return ["Static", true];
  return [null, false];
}

function shouldExclude(dirPath, name) {
  // 排除目录无条件跳过（即使含指示文件也不算候选）
  if (EXCLUDE_DIRS.has(name)) return true;
  for (const ep of EXCLUDE_PATHS) {
    if (dirPath.startsWith(ep)) return true;
  }
  return false;
}

const candidates = [];

function walk(dir, depth) {
  if (depth > maxDepth) return;
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const fullPath = path.join(dir, entry.name);
    if (shouldExclude(fullPath, entry.name)) continue;
    // 检查是否是项目根
    const [type, isRoot] = isProjectRoot(fullPath);
    if (isRoot) {
      // 检查是否含 README.md
      const hasReadme = fs.existsSync(path.join(fullPath, "README.md")) ||
        fs.existsSync(path.join(fullPath, "readme.md"));
      candidates.push({ path: fullPath, type, hasReadme });
    }
    // 继续递归（项目根下可能有子项目）
    walk(fullPath, depth + 1);
  }
}

// 1. 扫描主目录
walk(searchDir, 0);

// 2. CodeArts 沙箱目录
const sandboxBase = "/root/job-envs/sandboxes";
if (fs.existsSync(sandboxBase)) {
  try {
    for (const entry of fs.readdirSync(sandboxBase, { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name.startsWith("codearts-")) {
        const sandboxDir = path.join(sandboxBase, entry.name);
        const [type, isRoot] = isProjectRoot(sandboxDir);
        if (isRoot) {
          candidates.push({ path: sandboxDir, type, hasReadme: true });
        }
      }
    }
  } catch {}
}

// 3. 去重 + 输出
const seen = new Set();
const unique = candidates.filter((c) => {
  if (seen.has(c.path)) return false;
  seen.add(c.path);
  return true;
});

if (unique.length === 0) {
  console.error("未扫描到项目根目录。请手动指定 workDir。");
  process.exit(1);
}

unique.forEach((c, i) => {
  console.log(`#project ${i + 1} ${c.path} ${c.type}${c.hasReadme ? "" : " (无README)"}`);
});
process.exit(0);