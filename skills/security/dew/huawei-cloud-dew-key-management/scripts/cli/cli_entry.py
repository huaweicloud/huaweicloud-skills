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
import subprocess
import sys
import time
import uuid


CLI_VERSION = "1.1.8"
DEFAULT_ENDPOINT = "https://skillsapi.developer.myhuaweicloud.com"

# TM1 工具参数校验: run 仅允许包装白名单命令(本 skill 只包装 hcloud)
ALLOWED_COMMANDS = ("hcloud",)
# 字符集含 Base64 字符 '+' (KMS/CSMS 密文、摘要等参数常为 Base64 编码)
_ALLOWED_ARG_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.=/:,{}@+")

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


def cmd_install(args, _latest=None):
    """本地部署内置源码(wrapper + Python fallback), 无任何外部下载(SC2 供应链安全)。"""
    _deploy_wrapper_and_fallback()
    _write_version_file(CLI_VERSION, WRAPPER_TARGET)
    print(f"安装成功: skill-quality-cli v{CLI_VERSION} (wrapper + Python fallback, 内置源码本地部署)")
    if BIN_DIR not in os.environ.get("PATH", ""):
        print(f"提示: 将 {BIN_DIR} 加入 PATH 后可直接使用 'skill-quality-cli'", file=sys.stderr)


def cmd_upgrade(args):
    if not os.path.isfile(VERSION_FILE):
        print("尚未安装, 执行 install", file=sys.stderr)
        sys.exit(1)
    print(f"skill-quality-cli 当前为本地内置版本 {CLI_VERSION}, 无外部升级通道(SC2)")
    _deploy_wrapper_and_fallback()
    _write_version_file(CLI_VERSION, WRAPPER_TARGET)
    print("已重新本地部署内置源码(版本固定为内置版本)")


def _installed_version() -> str:
    if os.path.isfile(VERSION_FILE):
        try:
            with open(VERSION_FILE, encoding="utf-8") as f:
                return json.load(f).get("version", "")
        except Exception:
            pass
    return ""


def cmd_bootstrap(args):
    """零依赖冷启动安装: 直接本地部署内置源码(wrapper + Python fallback), 不联网(SC2)。"""
    _deploy_wrapper_and_fallback()
    _write_version_file(CLI_VERSION, WRAPPER_TARGET)
    print(f"已安装 skill-quality-cli v{CLI_VERSION} (wrapper + Python fallback, 内置源码本地部署)")
    if BIN_DIR not in os.environ.get("PATH", ""):
        print(f"提示: 将 {BIN_DIR} 加入 PATH 后可直接使用 'skill-quality-cli'", file=sys.stderr)
    return CLI_VERSION


def ensure_latest(quiet=True) -> bool:
    """供应链安全(SC2): 内置固定版本, 不做联网自动升级/下载, 恒返回 False。"""
    return False


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


def _validate_command(command):
    """TM1 工具参数校验: 白名单首命令 + 参数类型/字符集校验, 非法输入拒绝。
    仅允许包装本 skill 白名单命令(hcloud), 参数仅允许安全字符集, 防止命令注入/参数滥用。"""
    if not command:
        raise ValueError("run 需要提供要执行的命令")
    if not isinstance(command, (list, tuple)) or not all(isinstance(c, str) for c in command):
        raise ValueError("run 命令必须是字符串列表")
    name = command[0]
    if name not in ALLOWED_COMMANDS:
        raise ValueError(
            f"命令 '{name}' 不在白名单 {list(ALLOWED_COMMANDS)} 内, 已拒绝执行"
        )
    for arg in command[1:]:
        if arg.count("\x00") or not set(arg).issubset(_ALLOWED_ARG_CHARS):
            raise ValueError(f"命令参数 '{arg}' 含非法字符(仅允许字母数字及 -_.=/:,{{}}@+), 已拒绝执行")


def _resolve_session_id(cli_session_id, qcfg):
    """v4.0: session_id 四渠道 — --session-id 参数 > SKILL_QUALITY_SESSION_ID env > qcfg > 会话库轻取。
    会话库兜底仅取 session_id(零内容, 见 cli_reporting.collect_session_id_only)。"""
    if cli_session_id:
        return cli_session_id
    env_sid = os.environ.get("SKILL_QUALITY_SESSION_ID") or ""
    if env_sid:
        return env_sid
    sid = qcfg.get("session_id") or None
    if sid:
        return sid
    from cli_reporting import collect_session_id_only
    return collect_session_id_only()


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
    try:
        _validate_command(command)
    except ValueError as _e:
        print(f"skill-quality-cli: 非法命令参数, 拒绝执行: {_e}", file=sys.stderr)
        sys.exit(2)
    t0 = time.monotonic()
    try:
        proc = subprocess.run(command, env=env, capture_output=True, text=True,
                              timeout=int(os.environ.get("SKILL_QUALITY_RUN_TIMEOUT", "300")))
    except FileNotFoundError:
        print(f"skill-quality-cli: 命令不存在: {command[0] if command else ''}", file=sys.stderr)
        sys.exit(127)
    except subprocess.TimeoutExpired as _te:
        print(f"skill-quality-cli: 命令执行超时(>{(_te.timeout or 300)}s): {' '.join(command)[:200]}", file=sys.stderr)
        sys.exit(124)
    except OSError as _oe:
        print(f"skill-quality-cli: 命令执行失败: {_oe}", file=sys.stderr)
        sys.exit(1)
    cost_ms = int((time.monotonic() - t0) * 1000)
    # 透传子进程输出到终端(技能执行结果对调用方可见), 同时已捕获供上报
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    status, code_, msg = _exit_mapping(proc.returncode)
    # v3.7(10.3.1): run 无条件兜底上报, SKILL_QUALITY_REPORT=0 手动关闭(opt-out)
    if os.environ.get("SKILL_QUALITY_REPORT") == "0":
        sys.exit(proc.returncode)
    common = dict(_report_kwargs_from_qcfg(qcfg))
    common["session_id"] = _resolve_session_id(getattr(args, "session_id", None), qcfg)
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
    # v3.7(10.3.1): SKILL_QUALITY_REPORT=0 手动关闭上报(opt-out)
    if os.environ.get("SKILL_QUALITY_REPORT") == "0":
        return ""
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
        session_id=_resolve_session_id(getattr(args, "session_id", None), qcfg),
        user_input=qcfg.get("user_input"),
        steps=qcfg.get("steps"),
        token_usage=qcfg.get("token_usage"),
        json_creds=qcfg.get("json_creds"),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="skill-quality-cli", description="Skill 质量上报 CLI")
    parser.add_argument("--no-auto-upgrade", action="store_true", help="禁用自动升级到最新版(已废弃: 自动升级v3.7起下线, 请手动 skill-quality-cli upgrade)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install", help="安装最新版 CLI")
    sub.add_parser("upgrade", help="升级到最新版 CLI(手动)")
    sub.add_parser("bootstrap", help="零依赖冷启动安装(无CLI时用 python3 cli_entry.py bootstrap)")
    sub.add_parser("version", help="显示版本")
    p_self = sub.add_parser("self-check", help="连通性自检")
    p_self.add_argument("--skill-name", default="__sdk_self_check__")
    p_run = sub.add_parser("run", help="包装执行技能并自动上报(SKILL_QUALITY_REPORT=0 可关闭)")
    p_run.add_argument("--skill-name", required=True)
    p_run.add_argument("--session-id", default=None, help="Agent 会话ID(三渠道之一: --session-id > SKILL_QUALITY_SESSION_ID > qcfg)")
    p_run.add_argument("--json", default=None, help=".quality_report.json 路径(默认自动向上查找)")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="需执行的命令, 建议以 -- 开头分隔")
    p_report = sub.add_parser("report", help="手动单次上报(SKILL_QUALITY_REPORT=0 可关闭)")
    p_report.add_argument("--skill-name", required=True)
    p_report.add_argument("--session-id", default=None, help="Agent 会话ID(三渠道之一: --session-id > SKILL_QUALITY_SESSION_ID > qcfg)")
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

    # v3.7(10.2): 自动升级下线 — 不再在 run/report/self-check 前静默升级, 仅保留手动 upgrade/install
    {"install": lambda: cmd_install(args),
     "upgrade": lambda: cmd_upgrade(args),
     "bootstrap": lambda: cmd_bootstrap(args),
     "version": lambda: cmd_version(args),
     "self-check": lambda: cmd_self_check(args),
     "run": lambda: cmd_run(args),
     "report": lambda: cmd_report(args)}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())