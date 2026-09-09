#!/usr/bin/env node
// strip-git-credential.mjs — git 仓库 URL 凭证剥离门禁（fail-stop）
//
// 背景:
//   `git remote get-url origin` 可能返回内嵌 OAuth/用户凭证的 URL（如
//   `https://oauth2:TOKEN@gitcode.com/<ns>/<repo>.git`）。若不经剥离就随发布把自己打进作品陈列馆，token 会泄露。
//   本脚本把 `<user>:<pass>@`（或仅 `<token>@`）段剥离，并做硬校验：
//     * 剥离后不得再含 `@`（宿主形式）
//     * 必须 `https://` 开头、`.git` 结尾
//   不满足任一条件 → exit 1（调用方必须停手，禁止带凭证继续发布）。
// 用法、退出码详见 node strip-git-credential.mjs --help。

if (process.platform === "win32") {
  process.stdout.setDefaultEncoding?.("utf8");
  process.stderr.setDefaultEncoding?.("utf8");
}

const input = process.argv.length > 2
  ? process.argv[2]
  : (await new Promise((resolve) => {
      let d = "";
      process.stdin.on("data", (c) => (d += c));
      process.stdin.on("end", () => resolve(d.trim()));
    }));

function fail(msg) {
  console.error(`❌ strip-git-credential: ${msg}`);
  process.exit(1);
}

if (input === "-h" || input === "--help") {
  console.log(`strip-git-credential.mjs — git 仓库 URL 凭证剥离门禁（fail-stop）

用法:
  node strip-git-credential.mjs "<gitUrl>"
  echo "$rawUrl" | node strip-git-credential.mjs

行为:
  - 剥离 URL 中的 user:pass@ / token@ 凭证段
  - 硬校验: 剥离后不含 @、https:// 开头、.git 结尾
  - stdout 输出剥离后的安全 URL

退出码: 0=校验通过; 1=校验失败（fail-closed）
`);
  process.exit(0);
}

if (!input) fail("未收到 git URL（支持参数或 stdin）");

// 去掉开头的 user:pass@ / token@（不区分 https 大小写）
let stripped = input.replace(/^https?:\/\/[^/@\s]+@/, "https://");

// 二次剥离（幂等，防止形如 https://a:b:c@ 的残留）
stripped = stripped.replace(/^https?:\/\/[^/@\s]+@/, "https://");

if (stripped.includes("@")) {
  fail(`剥离后 URL 仍含凭证符 '@'（user:pass@host 形态）：${stripped}. URL 应从 git remote get-url 直接产出，而不是手工拼写。`);
}
if (!/^https:/i.test(stripped)) {
  fail(`剥离后必须 https:// 开头，实际：${stripped}`);
}
if (!/\.git$/i.test(stripped)) {
  fail(`git URL 必须以 .git 结尾，实际：${stripped}`);
}
if (!/^[\x21-\x7e]+$/.test(stripped)) {
  fail(`URL 含非 ASCII 字符，请核验：${stripped}`);
}

console.log(stripped);
process.exit(0);