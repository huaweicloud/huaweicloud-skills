from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "Missing dependency: pyyaml. Install with: pip install pyyaml"
        " or: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from .md_io import read_feedback_md, read_all_feedbacks
    from .models import FeedbackStatus, DeliveryStatus
except ImportError:
    from md_io import read_feedback_md, read_all_feedbacks
    from models import FeedbackStatus, DeliveryStatus

# ====== AtomGit-GO Integration: TOML Parsing ======
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

_ATOMGIT_HOME_ENV = "ATOMCODE_HOME"
_ATOMGIT_DEFAULT_DIR = ".atomcode"
_ATOMGIT_AUTH_FILE = "auth.toml"
# 允许用环境变量提供 token, 避免必须把 token 明文写入 auth.toml(issue #114 问题9)
_ATOMGIT_TOKEN_ENV = "VOD_ATOMGIT_TOKEN"


# ====== Auto-init .vod/ directory ======

_SKILL_DIR = Path(__file__).resolve().parent.parent
_CONFIG_TEMPLATE = _SKILL_DIR / "assets" / "config.yaml"


def _load_config() -> dict:
    """Read config directly from assets/config.yaml."""
    if not _CONFIG_TEMPLATE.exists():
        print(f"[vod_deliver] Config template not found: {_CONFIG_TEMPLATE}", file=sys.stderr)
        return {}

    try:
        text = _CONFIG_TEMPLATE.read_text(encoding="utf-8")
        config = yaml.safe_load(text)
        if config is None:
            print(f"[vod_deliver] Config template is empty or malformed: {_CONFIG_TEMPLATE}", file=sys.stderr)
            return {}
        return config
    except yaml.YAMLError as e:
        print(f"[vod_deliver] YAML parse error: {e}", file=sys.stderr)
        return {}


def _write_text_lf(path: Path, content: str) -> None:
    """Write UTF-8 text with LF line endings on every platform.

    read_text() 读取时会把 CRLF 归一化成 LF; 若再用 write_text() 落盘, Windows 下
    会把整文件转成 CRLF, 于是同一文件在 write-feedback(LF) 与 update-status /
    notify(CRLF) 之间来回转换。固定 LF 可保证跨平台 round-trip 与 git diff 稳定。
    """
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ====== AtomGit-GO Token Auto-discovery ======


def _get_atomgit_auth_path(atomgit_home: str | None = None) -> Path:
    """Get the full path to AtomGit-GO auth.toml.

    Priority: 1) explicit atomgit_home  2) ATOMCODE_HOME env  3) ~/.atomcode
    """
    if atomgit_home:
        base = Path(atomgit_home)
    else:
        env_home = os.environ.get(_ATOMGIT_HOME_ENV)
        if env_home:
            base = Path(env_home)
        else:
            base = Path.home() / _ATOMGIT_DEFAULT_DIR
    return base / _ATOMGIT_AUTH_FILE


def _read_atomgit_token(atomgit_home: str | None = None) -> dict | None:
    """Read AtomGit-GO auth.toml and return token info.

    Returns dict (access_token / refresh_token / expires_in / created_at / user).
    Returns None if file not found or unparseable.

    凭据来源优先级:
      1) 环境变量 ``VOD_ATOMGIT_TOKEN`` — 无需把 token 明文落盘(issue #114 问题9)
      2) AtomGit-GO 的 ``~/.atomcode/auth.toml``

    Windows 兼容(issue #959): 非 POSIX 平台没有 ``os.getuid``, 也没有 POSIX
    属主/权限位语义(st_uid 恒为 0), 因此跳过属主与权限位校验、chmod 收紧以及
    O_NOFOLLOW + fstat 一致性校验; Windows 下的文件保护由系统 ACL 负责。
    """
    # ---- 环境变量优先: 允许不落盘明文 token ----
    env_token = (os.environ.get(_ATOMGIT_TOKEN_ENV) or "").strip()
    if env_token:
        return {
            "access_token": env_token,
            "refresh_token": "",
            "expires_in": None,
            "created_at": None,
            "user": {},
            "_source": f"env:{_ATOMGIT_TOKEN_ENV}",
        }

    if tomllib is None:
        return None

    auth_path = _get_atomgit_auth_path(atomgit_home)
    is_posix = os.name == "posix"

    # ---- 路径安全: 拒绝符号链接 / 非常规文件 / 不安全父目录 ----
    # POSIX 平台: 父目录属主须为当前用户且 group/other 不可写, 防止本地攻击者
    # 替换 auth.toml。Windows 无 os.getuid / 无有效 st_uid, 跳过该分支。
    if is_posix:
        try:
            parent_stat = auth_path.parent.stat()
        except OSError:
            return None
        if parent_stat.st_uid != os.getuid() or (parent_stat.st_mode & 0o022):
            return None

    try:
        lst = os.lstat(auth_path)
    except OSError:
        return None
    if not stat.S_ISREG(lst.st_mode):
        # 符号链接或非常规文件一律拒绝(避免 chmod/读取命中错误目标)
        return None

    # ---- 凭据安全: 读取前先收紧权限为 0600; 无法收紧则拒绝读取 ----
    # 仅 POSIX 平台执行; Windows 无 POSIX 权限位, 由系统 ACL 管理。
    if is_posix:
        try:
            current_mode = lst.st_mode & 0o777
            if current_mode != 0o600:
                os.chmod(auth_path, 0o600)
        except OSError:
            return None

    # ---- O_NOFOLLOW 打开 + fstat 防 TOCTOU(打开后确认仍是同一普通文件) ----
    # Windows 上 st_ino/st_dev 不能用于一致性校验, 且无 O_NOFOLLOW 语义, 跳过。
    try:
        fd = os.open(auth_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    if is_posix:
        try:
            fst = os.fstat(fd)
        except OSError:
            os.close(fd)
            return None
        if (
            fst.st_ino != lst.st_ino
            or fst.st_dev != lst.st_dev
            or not stat.S_ISREG(fst.st_mode)
        ):
            os.close(fd)
            return None

    try:
        with os.fdopen(fd, "rb") as f:
            data = tomllib.load(f)

        if not data.get("access_token"):
            return None

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_in": data.get("expires_in"),
            "created_at": data.get("created_at"),
            "user": data.get("user", {}),
            "_source": str(auth_path),
        }
    except Exception:
        return None


def _check_atomgit_token(token_data: dict | None) -> tuple[bool, str]:
    """Check if AtomGit-GO token is valid.

    Returns (is_valid, message).
    """
    if not token_data:
        return False, "AtomGit-GO token not found (auth.toml missing or unparseable)"

    expires_in = token_data.get("expires_in")
    created_at = token_data.get("created_at")

    # 显式无效值优先: expires_in 显式为 0(0 秒有效)或负值 → 已过期
    # (即便 created_at 同样是 0/缺失, 也不能当无过期处理)
    if expires_in is not None and expires_in <= 0:
        return False, "Token expired (invalid expires_in)"

    # 两者均缺失(读取时保留 None) → 无过期信息, 视为无过期
    if expires_in is None and not created_at:
        return True, "Token valid (no expiry timestamp)"

    # 有 created_at 但缺 expires_in → 无法推算过期时间, 视为无过期
    if expires_in is None:
        return True, "Token valid (no expiry timestamp)"

    if not created_at or created_at <= 0:
        return False, "Token expiry cannot be determined (missing/zero created_at)"

    now = time.time()
    expires_at = created_at + expires_in
    remaining = expires_at - now

    if remaining <= 0:
        return False, f"Token expired ({abs(remaining):.0f}s ago)"
    elif remaining < 300:
        return False, f"Token about to expire ({remaining:.0f}s remaining), re-login needed"
    else:
        return True, f"Token valid ({remaining:.0f}s remaining)"


def _build_atomgit_hint(token_data: dict | None, valid: bool, msg: str) -> dict:
    """Build AtomGit-GO hint for Agent decision-making."""
    hint = {
        "provider": "atomgit-go",
        "status": "available" if (token_data and valid) else "unavailable",
        "message": msg,
    }
    if token_data:
        hint["source"] = token_data.get("_source", "")
        user = token_data.get("user", {})
        if user:
            hint["user"] = user.get("username", user.get("name", ""))
    return hint


def _resolve_atomgit_token(atomgit_home: str | None = None) -> dict:
    """Get token from AtomGit-GO.

    Returns dict:
      - success: {"success": true, "access_token": "...", "atomgit": {...}, "token_path": "..."}
      - needs login: {"success": false, "need_login": true, "action": "atomgit-go-login",
                   "message": "...", "will_save_token": true, "token_path": "...",
                   "atomgit": {...}}
      - unavailable: {"success": false, "need_login": false, "error": "...", "atomgit": {...}}
    """
    if tomllib is None:
        return {
            "success": False, "need_login": False,
            "error": "Missing TOML parser. Install: pip install tomli",
            "atomgit": {"provider": "atomgit-go", "status": "unavailable"},
        }

    token_data = _read_atomgit_token(atomgit_home)
    valid, msg = _check_atomgit_token(token_data)
    hint = _build_atomgit_hint(token_data, valid, msg)
    token_path = str(_get_atomgit_auth_path(atomgit_home))

    if valid and token_data:
        return {
            "success": True,
            "access_token": token_data["access_token"],
            "atomgit": hint,
            "token_path": token_path,
        }

    # Token missing or expired — run auto-login (see SKILL.md Phase 3.1)
    return {
        "success": False,
        "need_login": True,
        "action": "atomgit-go-login",
        "message": msg,
        "will_save_token": True,
        "token_path": token_path,
        "atomgit": hint,
        "hint": "Token will be auto-saved to {} after login. Re-run delivery afterwards.".format(token_path),
    }


# 从自由文本中提取看起来像产品名的 token(仅作兜底启发式)。
# 仅接受字母开头的 word-word(-word)+ 形态, 且排除日期(2024-12-31)、UUID、
# 纯数字请求 ID(req-123456 / id-2024-12-31)、版本号(v1-2-3)等非产品名误匹配。
_PRODUCT_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9-])([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)(?![A-Za-z0-9-])"
)
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(-\d+)+$")


def _extract_product_token(text: str) -> str:
    """Extract a plausible product token from free-form text (or "")."""
    if not text:
        return ""
    for cand in _PRODUCT_TOKEN_RE.findall(text):
        if _UUID_RE.fullmatch(cand):
            continue
        if _REQUEST_ID_RE.fullmatch(cand):
            continue
        # 形如 v1-2-3 / foo-2024-12-31 的版本/时间戳形态不视为产品名
        segs = cand.split("-")
        if len(segs) > 1 and all(seg.isdigit() for seg in segs[1:]):
            continue
        return cand
    return ""


def _infer_product_name(feedback) -> str:
    if feedback.product_name:
        return feedback.product_name
    for ann in getattr(feedback, "annotations", []) or []:
        if isinstance(ann, str) and ann.startswith("skill:"):
            return ann.split("skill:", 1)[1].strip()
    if feedback.agent_action:
        import re as _re
        m = _re.search(r"(?:call|invoke)\s+(\S+?)(?:\s+skill|$)", feedback.agent_action, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if feedback.error_message:
        token = _extract_product_token(feedback.error_message)
        if token:
            return token
    return ""


def _infer_voice_sources(feedback) -> str:
    """Infer voice source(s) using the same heuristics as product name but
    return all unique candidates joined by comma.
    """
    candidates: list[str] = []

    def _add(value: str | None):
        if not value:
            return
        # split common separators, but preserve multi-word product names like "AI Shell"
        parts = re.split(r"[,;，；\n]+", str(value))
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if p not in candidates:
                candidates.append(p)

    # 1) explicit field from metadata
    _add(getattr(feedback, "voice_source", None))

    # 2) also consider product_name as a possible source
    _add(getattr(feedback, "product_name", None))

    # 3) annotations with skill: prefix
    for ann in getattr(feedback, "annotations", []) or []:
        if isinstance(ann, str) and ann.startswith("skill:"):
            _add(ann.split("skill:", 1)[1].strip())

    # 4) agent action: call/invoke <name>
    if getattr(feedback, "agent_action", None):
        m = re.search(r"(?:call|invoke)\s+(\S+?)(?:\s+skill|$)", feedback.agent_action, re.IGNORECASE)
        if m:
            _add(m.group(1).strip())

    # 5) error message pattern like word-word(-word)+ (guarded: no date/UUID/request-id)
    if getattr(feedback, "error_message", None):
        token = _extract_product_token(feedback.error_message)
        if token:
            _add(token)

    return ", ".join(candidates)


def _build_issue_title(feedback, feedback_file: Path | None = None, product_name: str = "") -> str:
    desc = feedback.problem_description or feedback.error_message or feedback.user_intent or ""
    if not desc:
        desc = feedback.error_type or "VoD Feedback"
    if len(desc) > 60:
        desc = desc[:57] + "..."
    else:
        desc = desc[:60]
    name = product_name or _infer_product_name(feedback)
    if name:
        return f"【{name}】{desc}"
    return desc


def _build_issue_body(feedback, feedback_file: Path) -> str:
    # === Core 3 elements (always shown) ===

    description = (
        feedback.problem_description
        or feedback.error_message
        or feedback.user_intent
        or ""
    )

    occurrence_scenario = feedback.occurrence_scenario or ""

    expected_behavior = feedback.expected_behavior or feedback.user_expected or ""

    # Fallback: build concise steps when scenario is missing
    if not occurrence_scenario:
        steps = []
        if feedback.user_intent:
            steps.append(f"1. User intent: {feedback.user_intent}")
        if feedback.error_type:
            message = feedback.error_message or ""
            steps.append(f"2. Trigger: {feedback.error_type}" + (f" - {message}" if message else ""))
        occurrence_scenario = "\n".join(steps) if steps else ""

    lines = [
        "### 描述问题 (Description)",
        description or "(待补充)",
        "",
        "### 复现步骤 (To Reproduce)",
        occurrence_scenario or "(待补充)",
        "",
        "### 预期行为 (Expected behavior)",
        expected_behavior or "(待补充)",
        "",
    ]

    # Strip out 【问题描述】/【复现场景】/【预期行为】 markers from error_stack
    # because those fields are already shown in their own sections above.
    # Only keep the raw stack trace after 【错误堆栈】.
    clean_stack = _strip_error_stack_markers(feedback.error_stack)
    if clean_stack:
        lines.extend([
            "### 错误堆栈 (Stack Trace)",
            "```",
            clean_stack,
            "```",
            "",
        ])

    # Show all inferred voice sources (preserve explicit metadata if present).
    voice_sources = _infer_voice_sources(feedback)
    if voice_sources:
        lines.extend([
            "### 声音来源 (Voice Source)",
            voice_sources,
            "",
        ])

    if feedback.environment:
        lines.append("### 环境信息 (Environment)")
        for k, v in feedback.environment.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    return "\n".join(lines)


def _strip_error_stack_markers(raw_stack: str | None) -> str | None:
    """Strip markers from error_stack, keeping only the raw stack trace after 【错误堆栈】.

    Returns None if nothing meaningful remains.
    """
    if not raw_stack or not raw_stack.strip():
        return None

    # Look for 【错误堆栈】 marker — keep everything after it
    stack_match = re.search(r"【错误堆栈】\s*\n?(.*)", raw_stack, re.DOTALL)
    if stack_match:
        stack = stack_match.group(1).strip()
        if stack and stack not in ("无", "无堆栈", "None", "N/A", "NA"):
            return stack
        return None

    # No 【错误堆栈】 marker — check if content is just the other markers
    has_other_markers = any(
        marker in raw_stack
        for marker in ["【问题描述】", "【复现场景】", "【预期行为】", "【实际行为】"]
    )
    if has_other_markers:
        # Content is only composed of markers that duplicate main sections — skip
        return None

    # Pure raw stack, show it as-is
    return raw_stack.strip()


def _extract_repo_info(repo_url: str) -> tuple[str, str]:
    patterns = [
        r"https?://[^/]+/([^/]+)/([^/.]+?)(?:\.git)?$",
        r"git@[^:]+:([^/]+)/([^/.]+?)(?:\.git)?$",
    ]
    for p in patterns:
        m = re.match(p, repo_url.strip())
        if m:
            return m.group(1), m.group(2)
    raise ValueError(f"Unable to parse repo URL: {repo_url}")


def _get_gitcode_api_base(repo_url: str) -> str:
    parsed = urllib.parse.urlparse(repo_url)
    return f"https://{parsed.hostname}/api/v5"


def _create_gitcode_issue(
    repo_url: str,
    token: str,
    title: str,
    body: str,
) -> dict:
    owner, repo = _extract_repo_info(repo_url)
    api_base = _get_gitcode_api_base(repo_url)
    url = f"{api_base}/repos/{owner}/{repo}/issues"

    # GitCode API v5 requires access_token as query parameter
    url_with_token = f"{url}?access_token={urllib.parse.quote(token)}"

    data = {
        "title": title,
        "body": body,
    }

    req = urllib.request.Request(
        url_with_token,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "issue_iid": result.get("iid", result.get("number", "")),
                "issue_url": result.get("html_url", result.get("web_url", "")),
                "issue_id": result.get("id", ""),
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        error_body = re.sub(r"access_token=[^&\s]+", "access_token=***", error_body)
        return {
            "success": False,
            "error": f"HTTP {e.code}: {error_body[:200]}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200],
        }


def _update_feedback_delivery_status(
    feedback_file: Path,
    issue_url: str,
    issue_iid: str,
) -> None:
    if not feedback_file.exists():
        return
    content = feedback_file.read_text(encoding="utf-8")
    delivery_section = (
        "\n## Delivery\n"
        f"- **delivery_status**: delivered\n"
        f"- **delivered_at**: {datetime.now().isoformat()}\n"
        f"- **delivery_channel**: gitcode_issue\n"
        f"- **issue_url**: {issue_url}\n"
        f"- **issue_iid**: {issue_iid}\n"
    )
    if "## Delivery" in content:
        lines = content.split("\n")
        new_lines = []
        skip = False
        for line in lines:
            if line.strip() == "## Delivery":
                skip = True
                continue
            if skip and line.strip().startswith("## "):
                skip = False
            if not skip:
                new_lines.append(line)
        content = "\n".join(new_lines)

    content = content.rstrip("\n") + "\n" + delivery_section
    _write_text_lf(feedback_file, content)


# ====== 跨会话去重 (issue #114 问题11 / #116 问题11) ======

_DEDUP_LOOKBACK = 10
_DEDUP_MIN_SCORE = 0.6
_DELIVERED_FEEDBACK_STATUSES = {"promoted", "resolved"}
_DELIVERY_STATUS_RE = re.compile(r"-\s*\*\*delivery_status\*\*:\s*([A-Za-z_]+)")
_NOTIFIED_AT_RE = re.compile(r"-\s*\*\*notified_at\*\*:")
_UUID_RE_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_HEX_ID_RE_TEXT = re.compile(r"\b[0-9a-f]{16,}\b", re.I)
_NUMBER_RE_TEXT = re.compile(r"\b\d+\b")
_PATH_RE_TEXT = re.compile(r"[A-Za-z]:\\[^\s]*|/[^\s]*")


def _normalize_text(text: str | None) -> str:
    """Normalize free text so that two occurrences of the same error compare equal.

    去掉 UUID / 长十六进制 ID / 纯数字(行号、端口、耗时) / 文件路径, 统一小写与空白。
    """
    if not text:
        return ""
    lowered = _UUID_RE_TEXT.sub(" ", text.lower())
    lowered = _HEX_ID_RE_TEXT.sub(" ", lowered)
    lowered = _PATH_RE_TEXT.sub(" ", lowered)
    lowered = _NUMBER_RE_TEXT.sub(" ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _feedback_signature(feedback) -> str:
    """跨会话去重签名: error_type + 归一化后的错误文本。空反馈返回 ""。"""
    error_type = (feedback.error_type or "").strip().lower()
    text = (
        _normalize_text(feedback.error_message)
        or _normalize_text(feedback.error_stack)
        or _normalize_text(feedback.problem_description)
    )
    if not text and not error_type:
        return ""
    return f"{error_type}|{text[:200]}"


def _dedup_score(target, other) -> tuple[float, str]:
    """Deterministic similarity score (0.0-1.0) + human readable reason."""
    score = 0.0
    reasons: list[str] = []

    t_type = (target.error_type or "").strip().lower()
    o_type = (other.error_type or "").strip().lower()
    if t_type and t_type == o_type:
        score += 0.4
        reasons.append(f"error_type 相同({t_type})")

    t_text = " ".join(filter(None, [
        _normalize_text(target.error_message),
        _normalize_text(target.problem_description),
        _normalize_text(target.user_intent),
    ]))
    o_text = " ".join(filter(None, [
        _normalize_text(other.error_message),
        _normalize_text(other.problem_description),
        _normalize_text(other.user_intent),
    ]))
    if t_text and o_text:
        t_tokens = set(t_text.split())
        o_tokens = set(o_text.split())
        if t_tokens and o_tokens:
            overlap = len(t_tokens & o_tokens) / max(1, min(len(t_tokens), len(o_tokens)))
            score += 0.6 * overlap
            if overlap >= 0.8:
                reasons.append("错误文本高度重合")
            elif overlap >= 0.4:
                reasons.append("错误文本部分重合")
        if t_text == o_text:
            reasons.append("错误文本完全相同")

    return round(min(score, 1.0), 2), "; ".join(reasons) or "无显著重合"


def _read_delivery_status(path: Path) -> str:
    """Read ``- **delivery_status**: x`` from a feedback markdown file ("" if absent)."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _DELIVERY_STATUS_RE.search(content)
    return match.group(1).lower() if match else ""


def _is_notified(path: Path) -> bool:
    """True if this feedback was already pushed to a notification channel."""
    try:
        return bool(_NOTIFIED_AT_RE.search(path.read_text(encoding="utf-8")))
    except OSError:
        return False


def _collect_recent_feedbacks(feedbacks_dir: Path, lookback: int) -> list[tuple[Path, object]]:
    """Most recently modified feedback files (newest first), parsed and tolerant of bad files."""
    if not feedbacks_dir.exists():
        return []
    try:
        files = sorted(
            feedbacks_dir.glob("VOD-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[: max(0, lookback)]
    except OSError:
        return []
    result: list[tuple[Path, object]] = []
    for path in files:
        try:
            result.append((path, read_feedback_md(path)))
        except Exception:
            continue
    return result


def _enum_value(value) -> str:
    return getattr(value, "value", str(value))


def _feedback_digest(feedback, path: Path, delivery_status: str = "") -> dict:
    return {
        "id": feedback.feedback_id,
        "file": str(path),
        "session_id": feedback.session_id,
        "feedback_type": _enum_value(feedback.feedback_type),
        "error_type": feedback.error_type or "",
        "status": _enum_value(feedback.status),
        "delivery_status": delivery_status or "pending",
        "recurrence_count": feedback.recurrence_count,
        "title": (feedback.problem_description or feedback.error_message or "")[:160],
        "signature": _feedback_signature(feedback),
    }


def _build_dedup_llm_prompt(target, candidates: list[dict]) -> str:
    if target is None:
        return (
            "No target feedback was supplied. Review the candidate pairs above with the Agent (LLM) "
            "and decide which ones describe the same underlying problem across sessions."
        )
    lines = [
        "Judge whether the target feedback and each candidate describe the SAME underlying problem.",
        f"Target: {target.feedback_id} (session={target.session_id}, error_type={target.error_type or '-'})",
        f"  title: {(target.problem_description or target.error_message or '')[:200]}",
    ]
    for cand in candidates:
        lines.append(
            f"Candidate {cand['id']} (session={cand['session_id']}, status={cand['status']}, "
            f"delivery={cand['delivery_status']}, score={cand['score']}): {cand['title'][:200]}"
        )
    lines.append("Answer with: duplicate / not-duplicate per candidate, then act accordingly.")
    return "\n".join(lines)


def scan_cross_session_duplicates(
    feedbacks_dir: Path,
    feedback_id: str | None = None,
    lookback: int = _DEDUP_LOOKBACK,
) -> dict:
    """Scan recent feedbacks for cross-session duplicates (issue #114/#116 问题11).

    Deterministic pre-filter for the Agent's LLM judgement declared in SKILL.md
    ("Scan 10 recent feedbacks via LLM for duplicates"). Only feedbacks from
    *different* sessions are compared; same-session duplicates are handled by the
    in-session dedup in md_io.py.
    """
    recent = _collect_recent_feedbacks(feedbacks_dir, lookback)
    entries = [(path, fb, _read_delivery_status(path)) for path, fb in recent]

    target_entry = None
    if feedback_id:
        for entry in entries:
            if entry[1].feedback_id == feedback_id:
                target_entry = entry
                break
        if target_entry is None:
            # 目标可能不在最近 N 条内 —— 直接按 ID 读取, 避免漏判
            candidate_path = feedbacks_dir / f"{feedback_id}.md"
            if not candidate_path.exists():
                return {
                    "success": False,
                    "error": f"Feedback file not found: {candidate_path}",
                    "scanned": len(entries),
                    "lookback": lookback,
                    "target": None,
                    "candidates": [],
                    "strong_duplicates": [],
                    "should_deliver": True,
                    "llm_prompt": "",
                }
            try:
                parsed = read_feedback_md(candidate_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read feedback record: {e}",
                    "scanned": len(entries),
                    "lookback": lookback,
                    "target": None,
                    "candidates": [],
                    "strong_duplicates": [],
                    "should_deliver": True,
                    "llm_prompt": "",
                }
            target_entry = (candidate_path, parsed, _read_delivery_status(candidate_path))

    candidates: list[dict] = []
    target = target_entry[1] if target_entry else None

    if target is not None:
        target_sig = _feedback_signature(target)
        for path, other, delivery_status in entries:
            if other.feedback_id == target.feedback_id:
                continue
            if other.session_id == target.session_id:
                continue  # 会话内重复由 md_io 的去重窗口负责
            score, reason = _dedup_score(target, other)
            signature_match = bool(target_sig) and _feedback_signature(other) == target_sig
            if not signature_match and score < _DEDUP_MIN_SCORE:
                continue
            strong = bool(
                signature_match
                and (
                    _enum_value(other.status) in _DELIVERED_FEEDBACK_STATUSES
                    or delivery_status == "delivered"
                )
            )
            candidates.append({
                **_feedback_digest(other, path, delivery_status),
                "signature_match": signature_match,
                "score": score,
                "reason": reason,
                "is_strong_duplicate": strong,
            })
    else:
        # 无目标: 在最近 N 条中找出任意一对跨会话重复
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                path_a, fb_a, ds_a = entries[i]
                path_b, fb_b, ds_b = entries[j]
                if fb_a.session_id == fb_b.session_id:
                    continue
                score, reason = _dedup_score(fb_a, fb_b)
                sig_a, sig_b = _feedback_signature(fb_a), _feedback_signature(fb_b)
                signature_match = bool(sig_a) and sig_a == sig_b
                if not signature_match and score < _DEDUP_MIN_SCORE:
                    continue
                strong = bool(
                    signature_match
                    and (
                        _enum_value(fb_a.status) in _DELIVERED_FEEDBACK_STATUSES
                        or ds_a == "delivered"
                    )
                )
                candidates.append({
                    **_feedback_digest(fb_b, path_b, ds_b),
                    "duplicate_of": fb_a.feedback_id,
                    "signature_match": signature_match,
                    "score": score,
                    "reason": reason,
                    "is_strong_duplicate": strong,
                })

    candidates.sort(key=lambda c: (-(c["score"] or 0), c["id"]))
    strong_duplicates = [c["id"] for c in candidates if c.get("is_strong_duplicate")]

    return {
        "success": True,
        "scanned": len(entries),
        "lookback": lookback,
        "target": _feedback_digest(target_entry[1], target_entry[0], target_entry[2]) if target_entry else None,
        "candidates": candidates,
        "strong_duplicates": strong_duplicates,
        "should_deliver": not strong_duplicates,
        "llm_prompt": _build_dedup_llm_prompt(target, candidates),
    }


# ====== 通知渠道: webhook / email (issue #116 问题12) ======

def _retry_call(func, retry_policy: dict | None):
    """Call func() with exponential backoff; returns (ok, result_or_error)."""
    policy = retry_policy or {}
    max_retries = int(policy.get("max_retries", 3) or 0)
    base = float(policy.get("backoff_base_sec", 2) or 0)
    cap = float(policy.get("backoff_max_sec", 30) or 0)
    attempt = 0
    while True:
        try:
            return True, func()
        except Exception as e:  # noqa: BLE001 - surfaced to the caller as structured error
            if attempt >= max_retries:
                return False, e
            delay = min(cap, base * (2 ** attempt)) if base else 0
            if delay > 0:
                time.sleep(delay)
            attempt += 1


def _send_webhook(webhook_cfg: dict, payload: dict, retry_policy: dict | None) -> dict:
    url = (webhook_cfg or {}).get("url", "")
    if not url:
        return {"success": False, "channel": "webhook", "error": "webhook.url not configured"}

    headers = {"Content-Type": "application/json;charset=UTF-8"}
    for key, value in ((webhook_cfg or {}).get("headers") or {}).items():
        headers[str(key)] = str(value)

    def _post() -> int:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status

    ok, detail = _retry_call(_post, retry_policy)
    if ok:
        return {"success": True, "channel": "webhook", "http_status": detail}
    return {"success": False, "channel": "webhook", "error": str(detail)}


def _send_email(email_cfg: dict, payload: dict, retry_policy: dict | None) -> dict:
    import smtplib
    from email.message import EmailMessage

    cfg = email_cfg or {}
    host = cfg.get("smtp_host", "")
    recipients = [r for r in (cfg.get("recipients") or []) if r]
    if not host or not recipients:
        return {"success": False, "channel": "email", "error": "email.smtp_host / email.recipients not configured"}

    port = int(cfg.get("smtp_port", 587) or 587)
    sender = cfg.get("from") or os.environ.get("VOD_SMTP_FROM") or "vod-collector@localhost"

    message = EmailMessage()
    message["Subject"] = f"[VoD] {payload.get('title') or payload.get('feedback_id') or 'feedback notification'}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(json.dumps(payload, ensure_ascii=False, indent=2))

    def _send() -> str:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            if smtp.has_extn("starttls"):
                smtp.starttls()
                smtp.ehlo()
            user = cfg.get("username") or os.environ.get("VOD_SMTP_USER")
            password = cfg.get("password") or os.environ.get("VOD_SMTP_PASSWORD")
            if user and password:
                smtp.login(user, password)
            smtp.send_message(message)
        return "sent"

    ok, detail = _retry_call(_send, retry_policy)
    if ok:
        return {"success": True, "channel": "email", "status": detail}
    return {"success": False, "channel": "email", "error": str(detail)}


def _build_notification_payload(feedback, path: Path, delivery_status: str) -> dict:
    return {
        "feedback_id": feedback.feedback_id,
        "title": (feedback.problem_description or feedback.error_message or "")[:200],
        "session_id": feedback.session_id,
        "feedback_type": _enum_value(feedback.feedback_type),
        "error_type": feedback.error_type or "",
        "status": _enum_value(feedback.status),
        "delivery_status": delivery_status or "pending",
        "recurrence_count": feedback.recurrence_count,
        "file": str(path),
    }


def _mark_notified(path: Path) -> None:
    """Record ``- **notified_at**`` under ## Delivery so notify stays idempotent."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return
    line = f"- **notified_at**: {datetime.now().isoformat()}"
    if _NOTIFIED_AT_RE.search(content):
        content = re.sub(r"-\s*\*\*notified_at\*\*:.*", line, content)
    elif "## Delivery" in content:
        content = re.sub(r"(## Delivery\n)", r"\1" + line + "\n", content, count=1)
    else:
        content = content.rstrip("\n") + "\n\n## Delivery\n" + line + "\n"
    try:
        _write_text_lf(path, content)
    except OSError:
        return


def _collect_pending_feedbacks(
    feedbacks_dir: Path,
    feedback_id: str | None = None,
) -> list[tuple[Path, object, str]]:
    """Feedbacks not yet delivered and not yet notified, optionally narrowed to one ID."""
    if feedback_id:
        path = feedbacks_dir / f"{feedback_id}.md"
        if not path.exists():
            return []
        try:
            feedback = read_feedback_md(path)
        except Exception:
            return []
        if feedback.status == FeedbackStatus.DISCARDED:
            return []
        delivery_status = _read_delivery_status(path)
        if delivery_status == "delivered" or _is_notified(path):
            return []
        return [(path, feedback, delivery_status)]

    pending: list[tuple[Path, object, str]] = []
    for path, feedback in _collect_recent_feedbacks(feedbacks_dir, 100000):
        if feedback.status == FeedbackStatus.DISCARDED:
            continue
        delivery_status = _read_delivery_status(path)
        if delivery_status == "delivered" or _is_notified(path):
            continue
        pending.append((path, feedback, delivery_status))
    return pending


def notify_feedback(
    feedbacks_dir: Path,
    feedback_id: str | None = None,
    channel: str = "auto",
    dry_run: bool = False,
) -> dict:
    """Push pending feedbacks to the configured notification channel(s).

    顺序很重要(issue #114 问题5): **先**统计待发送反馈, 没有待发送项时立即返回
    空结果 —— 不加载渠道配置、不解析任何凭据、更不会触发登录流程。通知渠道本身
    也不需要 GitCode/AtomGit 凭据。
    """
    pending = _collect_pending_feedbacks(feedbacks_dir, feedback_id)

    if not pending:
        return {
            "success": True,
            "pending": 0,
            "sent": [],
            "channel": channel,
            "message": "No pending feedbacks",
        }

    config = _load_config()
    notification_cfg = (
        config.get("delivery", {}).get("channels", {}).get("notification") or {}
    )
    selected_channel = (channel or "auto").strip().lower()
    if selected_channel == "auto":
        selected_channel = (notification_cfg.get("type") or "webhook").strip().lower()

    if dry_run:
        return {
            "success": True,
            "pending": len(pending),
            "sent": [],
            "dry_run": True,
            "channel": selected_channel,
            "enabled": bool(notification_cfg.get("enabled", False)),
            "items": [_build_notification_payload(fb, path, ds) for path, fb, ds in pending],
        }

    if not notification_cfg.get("enabled", False):
        return {
            "success": False,
            "pending": len(pending),
            "sent": [],
            "channel": selected_channel,
            "error": "Notification channels disabled (delivery.channels.notification.enabled=false)",
        }

    retry_policy = notification_cfg.get("retry_policy") or {}

    results = []
    for path, feedback, delivery_status in pending:
        payload = _build_notification_payload(feedback, path, delivery_status)
        if selected_channel == "webhook":
            result = _send_webhook(notification_cfg.get("webhook") or {}, payload, retry_policy)
        elif selected_channel == "email":
            result = _send_email(notification_cfg.get("email") or {}, payload, retry_policy)
        else:
            result = {"success": False, "error": f"unsupported channel: {selected_channel}"}
        result["feedback_id"] = feedback.feedback_id
        results.append(result)
        if result.get("success"):
            _mark_notified(path)

    return {
        "success": all(r.get("success") for r in results),
        "pending": len(pending),
        "sent": [r["feedback_id"] for r in results if r.get("success")],
        "failed": [r["feedback_id"] for r in results if not r.get("success")],
        "channel": selected_channel,
        "results": results,
    }


def deliver_feedback(
    feedback_id: str,
    feedbacks_dir: Path,
    atomgit_home: str | None = None,
    force: bool = False,
    skip_dedup: bool = False,
) -> dict:
    feedback_file = feedbacks_dir / f"{feedback_id}.md"
    if not feedback_file.exists():
        # 文件存在性检查先于任何凭据解析(issue #114 问题6 / #116 问题8)
        return {"success": False, "error": f"Feedback file not found: {feedback_file}"}

    try:
        feedback = read_feedback_md(feedback_file)
    except Exception as e:
        return {"success": False, "error": f"Failed to read feedback record: {e}"}

    if feedback.status == FeedbackStatus.DISCARDED:
        return {"success": False, "error": "Discarded feedbacks are not delivered"}

    config = _load_config()
    gitcode_cfg = config.get("delivery", {}).get("channels", {}).get("gitcode", {})

    if not gitcode_cfg.get("enabled", False):
        return {"success": False, "error": "GitCode delivery not enabled"}

    repo_url = gitcode_cfg.get("repo_url", "")
    if not repo_url:
        return {"success": False, "error": "GitCode repo URL not configured"}

    # ---- 已投递反馈: 同样在解析凭据之前短路, 避免无谓的登录流程 ----
    existing_delivery = _read_delivery_status(feedback_file)
    if existing_delivery == "delivered" and not force:
        return {
            "success": False,
            "error": "already_delivered",
            "message": "Feedback already delivered; pass --force to deliver again",
            "delivery_status": existing_delivery,
        }

    # ---- 跨会话去重: 投递前先查重(issue #114 问题11 / #116 问题11) ----
    if not skip_dedup:
        dedup = scan_cross_session_duplicates(feedbacks_dir, feedback_id)
        strong_duplicates = [c for c in dedup.get("candidates", []) if c.get("is_strong_duplicate")]
        if strong_duplicates and not force:
            return {
                "success": False,
                "error": "duplicate_suspected",
                "duplicate_of": strong_duplicates[0]["id"],
                "candidates": strong_duplicates,
                "action": "review-dedup-with-llm-then-rerun-with-force",
            }

    title = _build_issue_title(feedback, feedback_file, feedback.product_name or "")
    body = _build_issue_body(feedback, feedback_file)

    # Get token from AtomGit-GO (最后一步才解析凭据)
    resolution = _resolve_atomgit_token(atomgit_home)
    if not resolution["success"]:
        # Attach issue details so caller can try alternative delivery
        # (e.g. devspace-connector MCP gitcode_create_issue tool) before QR-code login
        resolution["repo_url"] = repo_url
        resolution["issue_title"] = title
        resolution["issue_body"] = body
        return resolution  # carries need_login signal or error

    token = resolution["access_token"]
    atomgit_hint = resolution.get("atomgit")

    result = _create_gitcode_issue(repo_url, token, title, body)

    if result.get("success"):
        _update_feedback_delivery_status(
            feedback_file,
            result.get("issue_url", ""),
            str(result.get("issue_iid", "")),
        )
        # If using AtomGit-GO token, attach source info
        if atomgit_hint and atomgit_hint.get("status") == "available":
            result["auth_source"] = "atomgit-go"
            if atomgit_hint.get("user"):
                result["auth_user"] = atomgit_hint["user"]

    return result


def _find_server_binary() -> str | None:
    """Find the atomcode server binary. Checks common locations and names."""
    home = Path.home()
    candidates = [
        # Windows: atomcode-server.exe
        home / ".local" / "bin" / "atomcode-server.exe",
        # Windows: atomcode-login-server.exe
        home / ".local" / "bin" / "atomcode-login-server.exe",
        # Linux/macOS: atomcode-server
        home / ".local" / "bin" / "atomcode-server",
        # Linux/macOS: atomcode-login-server
        home / ".local" / "bin" / "atomcode-login-server",
        # Also search PATH (for systems where ~/.local/bin is in PATH)
    ]
    for c in candidates:
        if c.is_file():
            return str(c)

    # Fallback: search PATH
    found = shutil.which("atomcode-server") or shutil.which("atomcode-login-server")
    if found:
        return found

    return None


def _start_login_server() -> dict:
    """Start the atomcode login server in background.

    Returns dict with pid, binary, or error.
    """
    binary = _find_server_binary()
    if not binary:
        return {
            "success": False,
            "error": (
                "Server binary not found. Install the open-source project AtomGit-GO (MIT license) first.\n"
                "  Repo: https://gitcode.com/weixin_45218422/AtomGit-GO\n"
                "  Linux/macOS: bash <SKILL_DIR>/scripts/vod_install.sh install\n"
                "  Windows:     powershell <SKILL_DIR>/scripts/vod_install.ps1 install"
            ),
        }

    try:
        proc = subprocess.Popen(
            [binary],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        return {
            "success": True,
            "pid": proc.pid,
            "binary": binary,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to start server: {e}",
        }


def _stop_login_server(pid: int) -> dict:
    """Stop the atomcode login server by PID.

    Returns dict with success or error.
    """
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)
        else:
            os.kill(pid, 15)  # SIGTERM
        return {"success": True}
    except ProcessLookupError:
        return {"success": True, "message": "Process already exited"}
    except Exception as e:
        return {"success": False, "error": f"Failed to stop server: {e}"}

def main() -> None:
    parser = argparse.ArgumentParser(description="VoD Feedback Delivery Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    deliver_p = subparsers.add_parser("deliver", help="Deliver single feedback")
    deliver_p.add_argument("--feedback-id", required=True, help="Feedback ID")
    deliver_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")
    deliver_p.add_argument("--atomgit-home", default=None, help="AtomGit-GO config dir (default: ~/.atomcode or $ATOMCODE_HOME)")
    deliver_p.add_argument("--force", action="store_true", help="Deliver even if a cross-session duplicate or an existing delivery is detected")
    deliver_p.add_argument("--skip-dedup", action="store_true", help="Skip the cross-session duplicate scan before delivery")

    dedup_p = subparsers.add_parser("dedup-scan", help="Scan recent feedbacks for cross-session duplicates")
    dedup_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")
    dedup_p.add_argument("--feedback-id", default=None, help="Target feedback ID (default: compare all recent pairs)")
    dedup_p.add_argument("--lookback", type=int, default=_DEDUP_LOOKBACK, help="How many recent feedbacks to scan (default: 10)")
    dedup_p.add_argument("--json", action="store_true", help="Print JSON result (default: JSON)")

    notify_p = subparsers.add_parser("notify", help="Send pending feedbacks via webhook/email")
    notify_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")
    notify_p.add_argument("--feedback-id", default=None, help="Only notify this feedback ID")
    notify_p.add_argument("--channel", default="auto", choices=["auto", "webhook", "email"], help="Notification channel (default: auto)")
    notify_p.add_argument("--dry-run", action="store_true", help="List what would be sent without sending")
    notify_p.add_argument("--json", action="store_true", help="Print JSON result (default: JSON)")

    update_p = subparsers.add_parser("update-status", help="Update feedback delivery status")
    update_p.add_argument("--feedback-id", required=True, help="Feedback ID")
    update_p.add_argument("--status", required=True, choices=["open", "promoted", "resolved", "discarded", "delivered"], help="Delivery status")
    update_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")

    login_p = subparsers.add_parser("login-wait", help="Poll for QR-code authorization and get token")
    login_p.add_argument("--session-id", required=True, help="Login session ID")
    login_p.add_argument("--port", type=int, default=8080, help="server port (default: 8080)")
    login_p.add_argument("--timeout", type=int, default=60, help="Poll timeout in seconds (default: 60)")
    login_p.add_argument("--interval", type=int, default=2, help="Poll interval in seconds (default: 2)")

    # Server management subcommands (low-level, kept for manual use)
    server_start_p = subparsers.add_parser("server-start", help="Start the login server in background")
    server_stop_p = subparsers.add_parser("server-stop", help="Stop the login server by PID")
    server_stop_p.add_argument("--pid", type=int, required=True, help="Server process PID")

    args = parser.parse_args()

    # ── 纯业务执行 ──
    if args.command == "server-start":
        result = _start_login_server()
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "server-stop":
        result = _stop_login_server(args.pid)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "deliver":
        result = deliver_feedback(
            args.feedback_id, args.feedbacks_dir,
            atomgit_home=getattr(args, "atomgit_home", None),
            force=getattr(args, "force", False),
            skip_dedup=getattr(args, "skip_dedup", False),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "dedup-scan":
        result = scan_cross_session_duplicates(
            args.feedbacks_dir,
            getattr(args, "feedback_id", None),
            getattr(args, "lookback", _DEDUP_LOOKBACK),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "notify":
        result = notify_feedback(
            args.feedbacks_dir,
            getattr(args, "feedback_id", None),
            getattr(args, "channel", "auto"),
            getattr(args, "dry_run", False),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "update-status":
        fb_file = args.feedbacks_dir / f"{args.feedback_id}.md"
        if not fb_file.exists():
            print(json.dumps({"error": "Feedback file not found"}, ensure_ascii=False))
            sys.exit(1)
        content = fb_file.read_text(encoding="utf-8")
        now_ts = datetime.now().isoformat()
        if args.status == "delivered":
            new_section = (
                "\n## Delivery\n"
                f"- **delivery_status**: {args.status}\n"
                f"- **delivered_at**: {now_ts}\n"
            )
        else:
            new_section = (
                "\n## Delivery\n"
                f"- **delivery_status**: {args.status}\n"
            )
        if "## Delivery" not in content:
            content = content.rstrip("\n") + new_section
        else:
            content = re.sub(
                r"- \*\*delivery_status\*\*:.*",
                f"- **delivery_status**: {args.status}",
                content,
            )
        _write_text_lf(fb_file, content)
        print(json.dumps({"feedback_id": args.feedback_id, "status": args.status}, ensure_ascii=False))
    elif args.command == "login-wait":
        _poll_login(args.session_id, port=args.port, timeout=args.timeout, interval=args.interval)


def _poll_login(session_id: str, port: int = 8080, timeout: int = 60, interval: int = 2) -> None:
    """Poll atomcode-server /login/poll endpoint, wait for user QR-code authorization.

    On SCAN_SUCCESS → token auto-saved to auth.toml by atomcode-server.
    On timeout → print LOGIN_TIMEOUT.
    """
    import urllib.request as _req
    base = f"http://localhost:{port}"
    poll_url = f"{base}/login/poll?session_id={session_id}"

    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            resp = _req.urlopen(poll_url, timeout=interval + 1)
            raw = resp.read().decode("utf-8")
            print(f"[login-wait] poll response: {raw}")
            data = json.loads(raw)
            if data.get("status") == "authorized":
                print()
                print("SCAN_SUCCESS")
                # token auto-saved to auth.toml by atomcode-server
                return
            if data.get("status") in ("expired", "cancelled", "canceled"):
                print("[login-wait] QR code expired or cancelled")
                return
        except urllib.error.URLError as e:
            print(f"[login-wait] poll attempt {attempt}: connection failed ({e.reason})", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"[login-wait] poll attempt {attempt}: invalid response (not JSON)", file=sys.stderr)
        except Exception as e:
            print(f"[login-wait] poll attempt {attempt}: unexpected error ({e})", file=sys.stderr)
        time.sleep(interval)

    print("LOGIN_TIMEOUT")


if __name__ == "__main__":
    main()
