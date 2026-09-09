#!/usr/bin/env python3
"""gen_sts.py — 生成最小权限 STS 临时凭证（SELF_VERIFY 自委托 AssumeAgency）

契约（与 api.mjs --creds-file / --auto-refresh 对齐）：
  - 输出 sts-creds.json（camelCase）与 sts-creds.sh（STS_AK/STS_SK/STS_TOKEN）。
  - _refresh 写入 { accountId, agencyUrn, region, hcloudExe }，供 api.mjs 401 时自动刷新。

用法:
  python gen_sts.py --account <账号ID> [--hcloud <绝对路径>] \\
      [--region cn-north-4] [--dur 900] [--session publish-<ts>] \\
      [--creds-out <json>] [--sh-out <sh>]
  AK/SK/TOKEN 由 hcloud 读取（HUAWEICLOUD_SDK_AK/SK[/SECURITY_TOKEN] 或 hcloud 已配置）。
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REGION = "cn-north-4"
DURATION_SECONDS = 900
POLICY = {
    "Version": "5.0",
    "Statement": [{"Effect": "Allow", "Action": ["sts::GetCallerIdentity", "iam::listAuthDomains"], "Resource": ["*"]}],
}


def resolve_hcloud(explicit: str) -> str:
    if explicit:
        p = Path(explicit).resolve()
        if p.exists():
            return str(p)
        sys.exit(f"❌ --hcloud 指定路径不存在: {p}")

    # shutil.which covers PATH-based discovery (e.g. /usr/local/bin/hcloud)
    _which = shutil.which("hcloud")
    candidates = [
        Path("/usr/local/bin/hcloud"),
        Path.home() / ".local" / "bin" / "hcloud",
        Path.cwd() / "hcloud-cli" / "hcloud.exe",
        Path.cwd() / "hcloud" / "hcloud.exe",
    ]
    if _which:
        candidates.insert(0, Path(_which))
    for c in candidates:
        if c.exists():
            return str(c)
    sys.exit("❌ 未找到 hcloud（~/.local/bin/hcloud / hcloud-cli/hcloud.exe 均无）。请安装 KooCLI 或传 --hcloud <绝对路径>")


def main():
    ap = argparse.ArgumentParser(
        prog="gen_sts.py",
        description="生成最小权限 STS 临时凭证（写 sts-creds.json + sts-creds.sh）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--account", required=True, help="华为云账号 ID（Domain ID）")
    ap.add_argument("--hcloud", default="", help="hcloud 可执行文件绝对路径")
    ap.add_argument("--region", default=REGION, help=f"区域（默认 {REGION}）")
    ap.add_argument("--dur", type=int, default=DURATION_SECONDS, help=f"凭证有效期秒数（默认 {DURATION_SECONDS}）")
    ap.add_argument("--session", default=f"publish-{int(time.time() * 1000)}", help="会话名")
    ap.add_argument("--creds-out", default="", help="凭证 JSON 输出路径（默认 tmpdir/sts-creds.json）")
    ap.add_argument("--sh-out", default="", help="凭证 sh 输出路径（默认 tmpdir/sts-creds.sh）")
    args = ap.parse_args()

    hcloud_exe = resolve_hcloud(args.hcloud)
    agency_urn = f"iam::{args.account}:agency:SELF_VERIFY"
    creds_out = args.creds_out or str(Path(tempfile.gettempdir()) / "sts-creds.json")
    sh_out = args.sh_out or str(Path(tempfile.gettempdir()) / "sts-creds.sh")

    cmd = [
        hcloud_exe, "STS", "AssumeAgency",
        f"--cli-region={args.region}",
        f"--agency_urn={agency_urn}",
        f"--agency_session_name={args.session}",
        f"--duration_seconds={args.dur}",
        f"--policy={json.dumps(POLICY)}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = result.stdout
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "").strip() or str(e)
        sys.exit(f"❌ hcloud STS AssumeAgency 失败: {msg}\n请检查 AK/SK/账号 ID，或按 references/troubleshooting.md 排查。")

    try:
        c = json.loads(out)
        if "credentials" not in c:
            raise ValueError("响应缺 credentials 字段")
    except (json.JSONDecodeError, ValueError) as e:
        sys.exit(f"❌ 解析 hcloud 输出失败（{e}）。原始输出：{out[:300]}")

    camel = {
        "accessKeyId": c["credentials"]["access_key_id"],
        "secretAccessKey": c["credentials"]["secret_access_key"],
        "securityToken": c["credentials"]["security_token"],
        "_refresh": {"accountId": args.account, "agencyUrn": agency_urn, "region": args.region, "hcloudExe": hcloud_exe},
    }
    Path(creds_out).write_text(json.dumps(camel, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(sh_out).write_text(
        f"export STS_AK='{c['credentials']['access_key_id']}'\n"
        f"export STS_SK='{c['credentials']['secret_access_key']}'\n"
        f"export STS_TOKEN='{c['credentials']['security_token']}'\n",
        encoding="utf-8",
    )
    print(f"[gen-sts] 已写入 {creds_out}（+ {sh_out}），_refresh 含 hcloudExe={hcloud_exe}")


if __name__ == "__main__":
    main()
