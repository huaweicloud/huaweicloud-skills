#!/usr/bin/env node
// detect-env.mjs — 输出一次运行环境的平台指纹，SKILL.md 据此分流只读对应平台信息
//
// 用法:
//   node detect-env.mjs           # stdout = JSON，如 {"os":"linux","shell":"bash","distro":"rhel","sandbox":false}
//
// 字段:
//   os      win32 | linux | darwin      （process.platform）
//   shell   powershell | git-bash | bash
//   distro  linux 下: rhel(含 EulerOS/HCE/CentOS) | debian | other；其他平台 n/a
//   sandbox linux 下探测 CodeArts 沙箱（127.0.0.1:19300/healthz == ok）
//
// 使用约定:
//   - win32 → 按 fingerprint-shell 查看定平台文件（work-preparation-windows.md）；跳过 Linux/EulerOS 小节
//   - linux  → 看 work-preparation-linux.md；sandbox=true 再读 codearts-sandbox.md；跳过 Windows 小节

import { execFileSync } from "node:child_process";

function sh(cmd, args, timeout = 3000) {
  try {
    return execFileSync(cmd, args, { encoding: "utf8", timeout, stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

const os = process.platform; // win32 | linux | darwin
let shell = "bash";
let distro = "n/a";
let sandbox = false;

if (os === "win32") {
  // PowerShell 宿主 vs Git Bash / MSYS2（preflight 按 shell 走 sh 或 ps1）
  const msys = /MSYSTEM|GIT_BASH/i.test(process.env.MSYSTEM || "") ||
    /bash|mintty/i.test(process.env.SHELL || "");
  shell = msys ? "git-bash" : "powershell";
} else if (os === "darwin") {
  shell = "bash";
} else {
  shell = "bash";
  const rel = sh("bash", ["-c", "grep -E '^(ID|ID_LIKE|NAME)=' /etc/os-release 2>/dev/null"]);
  distro = /(^|\n)ID=(hce|euler|centos|rhel)/i.test(rel) || /ID_LIKE=.*(rhel|fedora|centos)/i.test(rel)
    ? "rhel"
    : /ID=debian|ID=ubuntu|ID=fedora|ID_LIKE=.*debian/i.test(rel)
      ? "debian"
      : "other";
  sandbox = /ok/i.test(sh("curl", ["--max-time", "3", "-s", "http://127.0.0.1:19300/healthz"]));
}

process.stdout.write(`${JSON.stringify({ os, shell, distro, sandbox })}\n`);