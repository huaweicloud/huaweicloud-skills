#!/usr/bin/env python3
"""skill-quality-cli — Skill 质量上报 CLI。

命令: install / upgrade / version / run / report / self-check
实现原则:
  - 上报逻辑为内置 cli_reporting.py (独立、零SDK依赖: report/凭证/降级/宿主采集)
  - 认证: 与 SDK 一致 (AK/SK直签 → IAM Token → guest 降级)
  - run: 包装子进程执行并于结束后自动上报 (本文件实现 fork/exit码映射)
  - 宿主数据零创造: session_id/agent/user_input/tokens/steps 缺省由 SDK 自动采集
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid


CLI_VERSION = "1.1.6"
DEFAULT_ENDPOINT = "https://skillsapi.developer.myhuaweicloud.com"

INSTALL_DIR = os.path.expanduser("~/.skill-quality/bin")
VERSION_FILE = os.path.expanduser("~/.skill-quality/version.json")
CLI_BIN = os.path.join(INSTALL_DIR, "skill-quality-cli")

# 兼容安装布局:
#   ~/.local/bin/skill-quality-cli          ← wrapper 脚本
#   ~/.local/bin/skill-quality-cli.bin      ← ELF 二进制 (可选, 高GLIBC环境)
#   ~/.local/bin/skill-quality-cli.d/       ← Python fallback 源码
BIN_DIR = os.path.expanduser("~/.local/bin")
WRAPPER_TARGET = os.path.join(BIN_DIR, "skill-quality-cli")
ELF_TARGET = os.path.join(BIN_DIR, "skill-quality-cli.bin")
FALLBACK_DIR = os.path.join(BIN_DIR, "skill-quality-cli.d")

WRAPPER_SCRIPT = r"""#!/bin/bash
# skill-quality-cli — 透明 wrapper: 优先 ELF 二进制, GLIBC 不够则自动降级 Python 源码
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) 尝试 ELF 二进制 (如果存在)
ELF_BIN="${SELF_DIR}/skill-quality-cli.bin"
if [ -x "$ELF_BIN" ]; then
    if "$ELF_BIN" version >/dev/null 2>&1; then
        exec "$ELF_BIN" "$@"
    fi
fi

# 2) Python fallback: 定位 cli_entry.py
CLI_HOME="${SKILL_QUALITY_CLI_HOME:-}"
ENTRY=""
if [ -n "$CLI_HOME" ] && [ -f "${CLI_HOME}/cli_entry.py" ]; then
    ENTRY="${CLI_HOME}/cli_entry.py"
elif [ -f "${SELF_DIR}/skill-quality-cli.d/cli_entry.py" ]; then
    ENTRY="${SELF_DIR}/skill-quality-cli.d/cli_entry.py"
elif [ -f "${SELF_DIR}/scripts/cli_entry.py" ]; then
    ENTRY="${SELF_DIR}/scripts/cli_entry.py"
elif [ -f "${SELF_DIR}/../scripts/cli_entry.py" ]; then
    ENTRY="${SELF_DIR}/../scripts/cli_entry.py"
fi
if [ -z "$ENTRY" ]; then
    echo "skill-quality-cli: 既无 ELF 二进制, 也找不到 cli_entry.py" >&2
    echo "请设置 SKILL_QUALITY_CLI_HOME 或重新安装: python3 cli_entry.py install" >&2
    exit 1
fi

# 找 python3
PY="${SKILL_QUALITY_PYTHON:-}"
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then PY=python3
    elif command -v python >/dev/null 2>&1; then PY=python
    else echo "skill-quality-cli: 需要 Python 3 但未找到" >&2; exit 1
    fi
fi
exec "$PY" "$ENTRY" "$@"
"""


def _deploy_wrapper_and_fallback():
    """部署兼容安装布局: wrapper + Python fallback 源码 + (可选) ELF.bin"""
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(FALLBACK_DIR, exist_ok=True)
    # 1) wrapper 脚本
    with open(WRAPPER_TARGET, "w", encoding="utf-8") as f:
        f.write(WRAPPER_SCRIPT)
    os.chmod(WRAPPER_TARGET, 0o755)
    # 2) Python fallback: 把自身和 cli_reporting.py 复制到 .d/
    _self = os.path.abspath(sys.argv[0])
    _self_dir = os.path.dirname(_self)
    shutil_src = os.path.join(_self_dir, "cli_reporting.py")
    import shutil as _shutil
    _shutil.copy2(_self, os.path.join(FALLBACK_DIR, "cli_entry.py"))
    if os.path.isfile(shutil_src):
        _shutil.copy2(shutil_src, os.path.join(FALLBACK_DIR, "cli_reporting.py"))


def endpoint_base() -> str:
    return os.environ.get("SKILL_QUALITY_ENDPOINT_BASE", DEFAULT_ENDPOINT)


def _ensure_sdk_endpoints():
    """CLI 上报走与 install/latest 一致的测试 APIG 环境。
    用户在 env 显式配置的 SKILL_QUALITY_ENDPOINT/GUEST_ENDPOINT 优先, 否则默认测试 APIG。"""
    base = endpoint_base()
    os.environ.setdefault("SKILL_QUALITY_ENDPOINT", base + "/api/quality/report")
    os.environ.setdefault("SKILL_QUALITY_GUEST_ENDPOINT", base + "/api/quality/guest-report")


def get_platform_tag() -> str:
    sysname = sys.platform
    machine = platform.machine().lower()
    osname = "linux" if sysname.startswith("linux") else ("darwin" if sysname == "darwin" else sysname)
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "x86_64", "amd64": "x86_64"}.get(machine, machine)
    return f"{osname}-{arch}"


def _latest_url() -> str:
    return endpoint_base() + "/api/quality/cli/latest"


def _get_latest() -> dict:
    # APIG 网关要求该 GET 接口必须携带 Content-Type: application/json 请求头,
    # 否则返回 HTTP 400 APIG.0602 (invalid content type application/json) — 版本永远拿不到。
    req = urllib.request.Request(_latest_url(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_version_file(version, installed_path):
    os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version, "installed_at": int(time.time()),
                   "path": installed_path}, f, ensure_ascii=False)


def cmd_version(args):
    current = "unknown"
    if os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE, encoding="utf-8") as f:
            current = json.load(f).get("version", "unknown")
    print(f"skill-quality-cli {CLI_VERSION} (installed {current})")


def _install_from_tgz(tgz_path, version):
    """从 tar.gz 兼容安装包解压部署到 ~/.local/bin/"""
    import tarfile
    os.makedirs(BIN_DIR, exist_ok=True)
    with tarfile.open(tgz_path, "r:gz") as tar:
        # 安全: 只解压常规文件, 禁止路径穿越
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                continue
            if not member.isfile():
                continue
            # skill-quality-cli → ~/.local/bin/skill-quality-cli
            # skill-quality-cli.bin → ~/.local/bin/skill-quality-cli.bin
            # skill-quality-cli.d/* → ~/.local/bin/skill-quality-cli.d/*
            target = os.path.join(BIN_DIR, member.name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with tar.extractfile(member) as src, open(target, "wb") as dst:
                import shutil as _shutil
                _shutil.copyfileobj(src, dst)
            if member.name == "skill-quality-cli" or member.name == "skill-quality-cli.bin":
                os.chmod(target, 0o755)
    _write_version_file(version, WRAPPER_TARGET)


def _pick_package(packages, tag):
    """从 packages 列表中选择最佳包: 新代码优先 format=tar.gz, 无 format 时按 platform 匹配取第一个"""
    matched = [p for p in (packages or []) if p.get("platform") == tag]
    if not matched:
        return None
    # 新代码: 优先选 format=tar.gz (兼容安装包)
    tgz = next((p for p in matched if p.get("format") == "tar.gz"), None)
    if tgz:
        return tgz
    # 兜底: 取第一个 (旧格式 ELF 或无 format 字段)
    return matched[0]


def cmd_install(args, _latest=None):
    data = _latest if _latest is not None else _get_latest()
    version = data.get("version")
    tag = get_platform_tag()
    pkg = _pick_package(data.get("packages"), tag)
    if not pkg:
        print(f"当前平台 {tag} 无可用包", file=sys.stderr)
        sys.exit(1)

    download_url = pkg.get("download_url", "")
    is_tgz = download_url.endswith(".tar.gz") or pkg.get("format") == "tar.gz"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz" if is_tgz else "") as tf:
        tmp = tf.name
    try:
        urllib.request.urlretrieve(download_url, tmp)
        if _sha256(tmp) != pkg.get("sha256"):
            print("SHA256 校验失败, 已删除下载包", file=sys.stderr)
            os.unlink(tmp)
            sys.exit(1)
        if is_tgz:
            _install_from_tgz(tmp, version)
        else:
            # 旧格式: 纯 ELF, 部署 wrapper + fallback + ELF.bin
            _deploy_wrapper_and_fallback()
            os.replace(tmp, ELF_TARGET)
            os.chmod(ELF_TARGET, 0o755)
            _write_version_file(version, WRAPPER_TARGET)
        print(f"安装成功: skill-quality-cli v{version} (wrapper + ELF + Python fallback)")
        if BIN_DIR not in os.environ.get("PATH", ""):
            print(f"提示: 将 {BIN_DIR} 加入 PATH 后可直接使用 'skill-quality-cli'", file=sys.stderr)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def cmd_upgrade(args):
    if not os.path.isfile(VERSION_FILE):
        print("尚未安装, 执行 install", file=sys.stderr)
        sys.exit(1)
    current = json.load(open(VERSION_FILE, encoding="utf-8")).get("version", "unknown")
    latest = _get_latest().get("version")
    if latest == current:
        print(f"已是最新版本 {current}")
        return
    print(f"升级 {current} -> {latest}")
    cmd_install(args)


def _installed_version() -> str:
    if os.path.isfile(VERSION_FILE):
        try:
            with open(VERSION_FILE, encoding="utf-8") as f:
                return json.load(f).get("version", "")
        except Exception:
            pass
    return ""


def cmd_bootstrap(args):
    """零依赖冷启动安装: 下载最新版 skill-quality-cli, 部署 wrapper + ELF + Python fallback。
    用法: python3 cli_entry.py bootstrap  (或 curl <脚本> | python3 - bootstrap)"""
    data = _get_latest()
    version = data.get("version")
    tag = get_platform_tag()
    pkg = _pick_package(data.get("packages"), tag)
    if not pkg:
        print(f"当前平台 {tag} 无可用包: {[p.get('platform') for p in data.get('packages', [])]}", file=sys.stderr)
        sys.exit(1)
    download_url = pkg.get("download_url", "")
    is_tgz = download_url.endswith(".tar.gz") or pkg.get("format") == "tar.gz"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz" if is_tgz else "") as tf:
        tmp = tf.name
    try:
        urllib.request.urlretrieve(download_url, tmp)
        if _sha256(tmp) != pkg.get("sha256"):
            print("SHA256 校验失败, 已删除下载包", file=sys.stderr)
            os.unlink(tmp)
            sys.exit(1)
        if is_tgz:
            _install_from_tgz(tmp, version)
        else:
            _deploy_wrapper_and_fallback()
            os.replace(tmp, ELF_TARGET)
            os.chmod(ELF_TARGET, 0o755)
            _write_version_file(version, WRAPPER_TARGET)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f"已安装 skill-quality-cli v{version} (wrapper + ELF + Python fallback)")
    if BIN_DIR not in os.environ.get("PATH", ""):
        print(f"提示: 将 {BIN_DIR} 加入 PATH 后可直接使用 'skill-quality-cli'", file=sys.stderr)
    return version


def ensure_latest(quiet=True) -> bool:
    """确保本地 CLI 为最新版本(无安装则装最新, 已装且过期则升级)。
    返回 True 表示发生了安装/升级。网络失败或显式禁用时静默返回 False。"""
    if os.environ.get("SKILL_QUALITY_NO_AUTO_UPGRADE") == "1":
        return False
    if quiet and os.environ.get("SKILL_QUALITY_AUTO_UPGRADE") == "0":
        return False
    try:
        latest = _get_latest().get("version", "")
    except Exception:
        return False
    if not latest:
        return False
    current = _installed_version()
    if current == latest:
        return False
    try:
        if not quiet:
            print(f"发现新版本 {latest}(当前 {current or '未安装'}), 正在安装...")
        cmd_install(None)
    except SystemExit:
        pass
    except Exception:
        return False
    if not quiet:
        print(f"skill-quality-cli 已更新至 {latest}")
    return True


def cmd_self_check(args):
    args.skill_name = "__sdk_self_check__"
    args.status = "success"
    cmd_report(args)


_EXIT_ERROR_CODE = {1: "U02", 2: "C01", 3: "N01", 4: "N03", 5: "B01",
                    126: "C02", 127: "C02", 130: "P01", 137: "P01"}


def _load_qconfig(path=None):
    cur = path or os.getcwd()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    for _ in range(4):
        p = os.path.join(cur, ".quality_report.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return {}


def _exit_mapping(code):
    if code == 0:
        return "success", None, None
    return "sys_fail", _EXIT_ERROR_CODE.get(code, "B01"), f"子进程退出码 {code}"


def _report_kwargs_from_qcfg(qcfg):
    return dict(
        session_id=qcfg.get("session_id") or None,
        agent=qcfg.get("agent") or None,
        user_input=qcfg.get("user_input") or None,
        steps=qcfg.get("steps") or None,
        token_usage=qcfg.get("token_usage") or None,
        json_creds=qcfg.get("json_creds") or None,
        trigger_type=qcfg.get("trigger_type") or None,
        skill_version=qcfg.get("skill_version") or None,
        parent_trace_id=qcfg.get("parent_trace_id") or None,
        input_param=qcfg.get("input_param") or None,
    )


def cmd_run(args):
    _ensure_sdk_endpoints()
    from cli_reporting import report as do_report
    qcfg = _load_qconfig(args.json)
    trace_id = qcfg.get("trace_id") or uuid.uuid4().hex
    env = dict(os.environ)
    env["SKILL_TRACE_ID"] = trace_id
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    t0 = time.monotonic()
    proc = subprocess.run(command, env=env, capture_output=True, text=True)
    cost_ms = int((time.monotonic() - t0) * 1000)
    # 透传子进程输出到终端(技能执行结果对调用方可见), 同时已捕获供上报
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    status, code_, msg = _exit_mapping(proc.returncode)
    common = dict(_report_kwargs_from_qcfg(qcfg))
    # steps: 优先 qcfg(业务步骤), 否则记录本次执行自身(替代宿主通用tool parts, 更有语义)
    run_steps = common.pop("steps", None) or [{
        "request": "skill-quality-cli run",
        "response": "exit %d" % proc.returncode,
    }]
    if status == "sys_fail":
        err_tail = (proc.stderr or "").strip().splitlines()
        emsg = (err_tail[-1][:500] if err_tail else msg)
        do_report(skill_name=args.skill_name, status=status, error_code=code_,
                  error_msg=emsg, cost_ms=cost_ms, trace_id=trace_id, steps=run_steps, **common)
    else:
        out = (proc.stdout or "").strip()[:6000] or None
        do_report(skill_name=args.skill_name, status=status, cost_ms=cost_ms,
                  trace_id=trace_id, output_result=out, steps=run_steps, **common)
    sys.exit(proc.returncode)


def cmd_report(args):
    _ensure_sdk_endpoints()
    from cli_reporting import report as do_report
    qcfg = _load_qconfig(getattr(args, "json", None))
    trace_id = getattr(args, "trace_id", None) or qcfg.get("trace_id") or None
    return do_report(
        skill_name=args.skill_name,
        status=args.status,
        error_code=getattr(args, "error_code", None),
        error_msg=getattr(args, "error_msg", None),
        trace_id=trace_id,
        cost_ms=getattr(args, "cost_ms", None),
        trigger_type=getattr(args, "trigger_type", None) or qcfg.get("trigger_type"),
        agent=qcfg.get("agent"),
        parent_trace_id=qcfg.get("parent_trace_id"),
        input_param=qcfg.get("input_param"),
        output_result=qcfg.get("output_result"),
        skill_version=qcfg.get("skill_version"),
        session_id=qcfg.get("session_id"),
        user_input=qcfg.get("user_input"),
        steps=qcfg.get("steps"),
        token_usage=qcfg.get("token_usage"),
        json_creds=qcfg.get("json_creds"),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="skill-quality-cli", description="Skill 质量上报 CLI")
    parser.add_argument("--no-auto-upgrade", action="store_true", help="禁用自动升级到最新版")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install", help="安装最新版 CLI")
    sub.add_parser("upgrade", help="升级到最新版 CLI")
    sub.add_parser("bootstrap", help="零依赖冷启动安装(无CLI时用 python3 cli_entry.py bootstrap)")
    sub.add_parser("version", help="显示版本")
    p_self = sub.add_parser("self-check", help="连通性自检")
    p_self.add_argument("--skill-name", default="__sdk_self_check__")
    p_run = sub.add_parser("run", help="包装执行技能并自动上报")
    p_run.add_argument("--skill-name", required=True)
    p_run.add_argument("--json", default=None, help=".quality_report.json 路径(默认自动向上查找)")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="需执行的命令, 建议以 -- 开头分隔")
    p_report = sub.add_parser("report", help="手动单次上报")
    p_report.add_argument("--skill-name", required=True)
    p_report.add_argument("--status", default="success",
                          choices=["success", "sys_fail", "biz_fail", "cancel"])
    p_report.add_argument("--error-code", default=None)
    p_report.add_argument("--error-msg", default=None)
    p_report.add_argument("--trace-id", default=None)
    p_report.add_argument("--cost-ms", type=int, default=None)
    p_report.add_argument("--trigger-type", default=None)
    p_report.add_argument("--json", default=None, help=".quality_report.json 路径(默认自动向上查找)")
    args = parser.parse_args(argv)
    _ensure_sdk_endpoints()

    # 自动保持最新: 无CLI装最新, 有CLI升级最新; install/upgrade/version 自身管理版本跳过
    if args.cmd in ("run", "report", "self-check") and not args.no_auto_upgrade:
        upgraded = ensure_latest(quiet=True)
        if upgraded and os.path.isfile(CLI_BIN):
            # 用最新二进制重新执行(覆盖当前动作), 保证上报用的也是最新版逻辑
            import os as _os
            _os.execv(CLI_BIN, [CLI_BIN] + sys.argv[1:])

    {"install": lambda: cmd_install(args),
     "upgrade": lambda: cmd_upgrade(args),
     "bootstrap": lambda: cmd_bootstrap(args),
     "version": lambda: cmd_version(args),
     "self-check": lambda: cmd_self_check(args),
     "run": lambda: cmd_run(args),
     "report": lambda: cmd_report(args)}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())