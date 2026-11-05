#!/usr/bin/env python3
"""skill-quality-cli — Skill 质量上报 CLI。

命令: install / upgrade / version / run / report / self-check
实现原则:
  - 上报逻辑为内置 cli_reporting.py (独立、零SDK依赖: report/凭证/降级/宿主采集)
  - 认证: 与 SDK 一致 (AK/SK直签 → IAM Token → guest 降级)
  - run: 包装子进程执行并于结束后自动上报 (本文件实现 fork/exit码映射)
  - 宿主数据零创造: session_id/agent/user_input/tokens/steps 缺省由 SDK 自动采集

安全闭环 (SC3, 程序级强制拦截):
  - 写操作门控: Create/Update/Delete/Reset/Resize/Reinstall/Detach/Remove/BatchStart/
    BatchStop/BatchReboot/Associate/Attach 等写操作必须携带显式确认 token
    (--confirm-token | SKILL_QUALITY_CONFIRM_TOKEN | qcfg.confirm_token) 才执行真实变更,
    否则拒绝执行。显式加 --dryrun 的写操作视为只读校验, 无需 token 放行。
  - 删除操作技术强制: delete 类操作 (Delete/Remove/Detach/Unbind/Disassociate/
    BatchDelete/NovaDelete) 未携带确认 token 时自动追加 --dryrun 转为校验执行,
    真实删除必须显式确认后才能进行。
  - 输出脱敏: AK/SK/password/token 等凭证字段在输出层自动打码, 不依赖文档约定。
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid


CLI_VERSION = "1.2.0"
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


# ==================== SC3 安全闭环: 写操作门控 / 删除强制 / 凭证脱敏 ====================
# 仅对白名单包装命令(hcloud)的第二段操作名做风险分类, 不影响白名单/字符集校验行为。
_CONFIRM_TOKEN_ENV = "SKILL_QUALITY_CONFIRM_TOKEN"
_CONFIRM_TOKEN_MIN_LEN = 8
# 显式确认 token 不允许的平凡值(防止随手传 "yes" 绕过门控)
_TRIVIAL_CONFIRM_TOKENS = {
    "", "yes", "y", "true", "1", "ok", "okay", "sure", "go", "done", "confirm",
    "confirmed", "confirmation", "proceed", "go-ahead", "do-it", "doit", "run",
    "execute", "delete", "create", "更新", "确认", "同意",
}

# 删除类操作单词(命中即强制 dry-run 门控)
_DELETE_OP_MARKERS = frozenset({
    "delete", "remove", "detach", "unbind", "disassociate",
})
# 只读动词(白名单): 命中即 read, 优先于写标记判定
_READ_OP_VERBS = frozenset({
    "list", "show", "get", "describe", "query",
})
# 写操作单词(Create/Update/Reset/Resize/Reinstall/Start/Stop/Reboot/Attach/Bind/Add/Change/
# Migrate/Revert/Execute/Lock/Unlock/Register/Accept/Post/Set/Modify/Enable/Disable...)
# 未命中任何动词(读白名单之外)的一律按写操作门控, 消除覆盖缺口与只读误判。
_WRITE_OP_MARKERS = frozenset({
    "create", "update", "reset", "resize", "reinstall", "start", "stop", "reboot",
    "associate", "attach", "bind", "add", "set", "change", "modify", "enable",
    "disable", "migrate", "revert", "execute", "lock", "unlock", "register",
    "accept", "post", "import", "export", "update", "replace", "install",
})
_OP_VERBS = _READ_OP_VERBS | _WRITE_OP_MARKERS | _DELETE_OP_MARKERS

# 输出脱敏: 凭证类参数名/JSON 字段名特征
_SENSITIVE_PARAM_RE = re.compile(
    r"(?i)(--[\w.\-]*(?:password|pass|token|secret|ak|sk|credential)[\w.\-]*=)[^\s]+"
)
_SENSITIVE_JSON_RE = re.compile(
    r"(?i)([\"'](?:password|adminPass|new_password|token|secret|access_key|secret_key|"
    r"security_token|ak|sk)[\"']\s*[:=]\s*)([\"'])[^\"'\r\n]{0,2048}([\"'])"
)
_MASK = "******"


def _op_words(op):
    """把 PascalCase 操作名拆成小写单词列表(ListServerVolumeAttachments → [list, server, volume, attachments])。
    仅精确匹配单词, 避免子串误判(ListVolumeAttachments 的 'attach' 不算写操作)。"""
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", op)
    return [w.lower() for w in re.split(r"[^A-Za-z0-9_]+", parts) if w]


def _classify_operation(command):
    """按白名单命令的第二段操作名做风险分类: read / write / delete。

    判定顺序(fail-closed, 未命中读白名单一律按写操作门控):
      1. 删除类标记(Delete/Remove/Detach/Unbind/Disassociate) → delete
      2. 操作名首个动词词性: 以 List/Show/Get/Describe/Query 起始 → read
      3. 其余(含 Migrate/Revert/Execute/Lock/Unlock/Register/Accept 等未枚举动词)
         → write, 一律按写操作确认 token 门控
    """
    if not command or len(command) < 3 or command[0] not in ALLOWED_COMMANDS:
        return "read"
    op = (command[2] or "")
    if not op:
        return "read"
    words = _op_words(op)
    if not words:
        return "read"
    # 1) 删除类标记(任意位置)
    if any(w in _DELETE_OP_MARKERS for w in words):
        return "delete"
    # 2/3) 首个动词位决定 read 或 write(fail-closed)
    #   CinderListQuotas → words=[cinder,list,quotas]: 首个可识别动词 list → read
    #   ListResizeFlavors → words=[list,resize,...]: 首个动词 list → read
    #   MigrateServer → words=[migrate,server]: 首个动词 migrate → write
    for w in words:
        if w in _OP_VERBS:
            return "read" if w in _READ_OP_VERBS else "write"
    return "write"


def _has_dryrun_arg(args):
    """命令中是否已声明 dry-run(--dryrun / --dry_run=true), 此时为只读校验, 不产生实际变更。"""
    for a in args[3:]:
        if a.startswith("--dryrun") or a.startswith("--dry_run"):
            return True
    return False


def _is_valid_confirm_token(token):
    """显式确认 token 校验: 非空、非平凡值、达到最小长度。"""
    if not token or not isinstance(token, str):
        return False
    t = token.strip()
    if len(t) < _CONFIRM_TOKEN_MIN_LEN:
        return False
    if t.lower() in _TRIVIAL_CONFIRM_TOKENS:
        return False
    if t.lower() == t and t.isalpha():
        return False
    return True


def _resolve_confirm_token(args, qcfg):
    """确认 token 来源优先级: --confirm-token 参数 > SKILL_QUALITY_CONFIRM_TOKEN env > qcfg。"""
    tok = getattr(args, "confirm_token", None) or ""
    if not tok:
        tok = os.environ.get(_CONFIRM_TOKEN_ENV, "") or ""
    if not tok and qcfg:
        tok = qcfg.get("confirm_token") or ""
    return (tok or "").strip()


def _security_gate(command, args, qcfg):
    """SC3 安全门控: 返回 (允许执行?, 实际命令, 拒绝/降级原因)。

    - read: 放行
    - write + 显式确认 token: 放行
    - write 无 token: 拒绝
    - delete 无 token: 强制追加 --dryrun 降级为只读校验(不产生真实删除)
    - delete 有 token: 放行(dry-run 校验收到的确认才应携带 token)
    """
    risk = _classify_operation(command)
    if risk == "read":
        return True, command, None
    token = _resolve_confirm_token(args, qcfg)
    if risk == "delete":
        if _has_dryrun_arg(command):
            return True, command, None
        if _is_valid_confirm_token(token):
            return True, command, None
        downgraded = list(command) + ["--dryrun"]
        return True, downgraded, (
            f"删除操作 '{command[2]}' 未携带显式确认 token, 已自动追加 --dryrun 转为只读校验"
            f"(不产生真实删除)。确认校验结果后请携带确认 token 再执行真实删除。"
        )
    # write: 显式 --dryrun 视为只读校验放行; 真实写必须携带确认 token
    if _has_dryrun_arg(command):
        return True, command, None
    if _is_valid_confirm_token(token):
        return True, command, None
    return False, None, (
        f"写操作 '{command[2]}' 未收到显式确认 token, 已拒绝执行。"
        f"确认后请通过 --confirm-token / 环境变量 {_CONFIRM_TOKEN_ENV} / qcfg 提供确认 token;"
        f"或先加 --dryrun 做只读校验。"
    )


def _collect_secrets(qcfg):
    """收集需要脱敏的凭证值: env AK/SK/token + qcfg json_creds/token。"""
    secrets = set()
    for key in (
        "HUAWEICLOUD_SDK_AK", "HUAWEICLOUD_SDK_SK", "HUAWEICLOUD_SDK_SECURITY_TOKEN",
        "HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_SECURITY_TOKEN",
        "SKILL_QUALITY_AK", "SKILL_QUALITY_SK", "SKILL_QUALITY_STS_TOKEN",
        "SKILL_QUALITY_TOKEN", _CONFIRM_TOKEN_ENV,
    ):
        v = os.environ.get(key, "") or ""
        if v and len(v) >= 6:
            secrets.add(v)
    if qcfg:
        for key in ("token", "confirm_token"):
            v = qcfg.get(key) or ""
            if v and len(v) >= 6:
                secrets.add(v)
        jc = qcfg.get("json_creds") or {}
        if isinstance(jc, dict):
            for v in (jc.get("ak"), jc.get("sk"), jc.get("token"),
                      jc.get("sts_token"), jc.get("security_token")):
                if v and len(v) >= 6:
                    secrets.add(str(v))
    return sorted(secrets, key=len, reverse=True)


def _mask_secrets(text, secrets):
    """输出层自动脱敏: 凭证值精确替换 + 凭证参数名/JSON 字段值打码。"""
    text = text or ""
    out = text
    for s in secrets or []:
        if s:
            out = out.replace(s, _MASK)
    out = _SENSITIVE_PARAM_RE.sub(lambda m: m.group(1) + _MASK, out)
    out = _SENSITIVE_JSON_RE.sub(lambda m: m.group(1) + m.group(2) + _MASK + m.group(3), out)
    return out


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

    # SC3 安全闭环: 写操作确认门控 / 删除操作强制 dry-run / 输出脱敏
    allow, gated_cmd, gate_msg = _security_gate(command, args, qcfg)
    if not allow or (gated_cmd is not None and gated_cmd != command):
        command = gated_cmd if gated_cmd else command
        if gate_msg:
            print(f"skill-quality-cli: {gate_msg}", file=sys.stderr)
        if not allow:
            sys.exit(3)
        # 删除操作降级为 dry-run 时继续执行(只读校验)
    secrets = _collect_secrets(qcfg)
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
    # 凭证脱敏: 输出层打码后再透传(不依赖文档约定, 程序级强制)
    stdout_txt = _mask_secrets(proc.stdout or "", secrets)
    stderr_txt = _mask_secrets(proc.stderr or "", secrets)
    if stdout_txt:
        sys.stdout.write(stdout_txt)
    if stderr_txt:
        sys.stderr.write(stderr_txt)
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
        err_tail = stderr_txt.strip().splitlines()
        emsg = (err_tail[-1][:500] if err_tail else msg)
        do_report(skill_name=args.skill_name, status=status, error_code=code_,
                  error_msg=emsg, cost_ms=cost_ms, trace_id=trace_id, steps=run_steps, **common)
    else:
        out = (stdout_txt or "").strip()[:6000] or None
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
    p_run.add_argument("--confirm-token", default=None,
                       help="写操作显式确认 token(SC3 安全门控; 也支持 SKILL_QUALITY_CONFIRM_TOKEN env / qcfg.confirm_token)")
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