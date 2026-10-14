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
  hcloud 探测：--hcloud → HCLOUD_EXE → PATH（仅按 PATH，不扫固定目录，工具统一经 ensure-user-bindir.mjs 暴露）。
"""

import argparse
import json
import os
import re
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

    # 探测顺序: --hcloud → HCLOUD_EXE → PATH(shutil.which)。
    # 仅按 PATH 查找，不扫描固定目录——工具统一经 ensure-user-bindir.mjs 目录暴露。
    _exe_env = os.environ.get("HCLOUD_EXE", "").strip()
    if _exe_env:
        p = Path(_exe_env).expanduser().resolve()
        if p.exists():
            return str(p)
    _which = shutil.which("hcloud")
    if _which:
        return str(_which)
    sys.exit("❌ 未找到 hcloud（不在 PATH）。请安装 KooCLI 并确保其目录在 PATH（可经 ensure-user-bindir.mjs），或传 --hcloud <绝对路径>")


def normalize_aksk_env():
    """AK/SK/Token 环境变量归一化：hcloud 只认 HUAWEICLOUD_SDK_AK/SK/SECURITY_TOKEN，
    按优先级回退别名，命中别名时注入 SDK 变量名，供 hcloud 子进程读取。
    仅当 SDK 变量未设置且别名命中时才写，不覆盖用户显式设置的 SDK 变量。"""
    chains = {
        "HUAWEICLOUD_SDK_AK": ["HUAWEICLOUD_AK", "HW_ACCESS_KEY"],
        "HUAWEICLOUD_SDK_SK": ["HUAWEICLOUD_SK", "HW_SECRET_KEY"],
        "HUAWEICLOUD_SDK_SECURITY_TOKEN": ["HUAWEICLOUD_SECURITY_TOKEN", "HW_SECURITY_TOKEN"],
    }
    for sdk, aliases in chains.items():
        if os.environ.get(sdk):
            continue
        for a in aliases:
            if os.environ.get(a):
                os.environ[sdk] = os.environ[a]
                break


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

    normalize_aksk_env()
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
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        raw = result.stdout
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "").strip() or str(e)
        sys.exit(f"❌ hcloud STS AssumeAgency 失败: {msg}\n请检查 AK/SK/账号 ID（HUAWEICLOUD_SDK_AK/SK 或别名 HUAWEICLOUD_AK/SK、HW_ACCESS_KEY/HW_SECRET_KEY），或按 references/troubleshooting.md 排查。")

    # hcloud (KooCLI) 输出含 ANSI 彩色码且可能夹带日志行，需剥离 ANSI 后提取 JSON。
    out = re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()

    try:
        c = json.loads(out)
        if "credentials" not in c:
            raise ValueError("响应缺 credentials 字段")
    except (json.JSONDecodeError, ValueError):
        # hcloud 可能输出非纯 JSON（含日志行），尝试提取首个 JSON 对象
        json_match = re.search(r'\{[\s\S]*\}', out)
        if json_match:
            try:
                c = json.loads(json_match.group(0))
                if "credentials" not in c:
                    raise ValueError("响应缺 credentials 字段")
            except (json.JSONDecodeError, ValueError) as e:
                sys.exit(f"❌ 解析 hcloud 输出失败（{e}）。原始输出：{raw[:300]}")
        else:
            sys.exit(f"❌ 解析 hcloud 输出失败（无 JSON 内容）。原始输出：{raw[:300]}")

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
