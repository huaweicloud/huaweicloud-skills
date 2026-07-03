from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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


# ====== Auto-init .vod/ directory ======

_SKILL_DIR = Path(__file__).resolve().parent.parent
_CONFIG_TEMPLATE = _SKILL_DIR / "assets" / "config.yaml.template"


def _load_config() -> dict:
    """Read config directly from assets/config.yaml.template."""
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
    """
    if tomllib is None:
        return None

    auth_path = _get_atomgit_auth_path(atomgit_home)
    if not auth_path.exists():
        return None

    try:
        with open(auth_path, "rb") as f:
            data = tomllib.load(f)

        if not data.get("access_token"):
            return None

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_in": data.get("expires_in", 0),
            "created_at": data.get("created_at", 0),
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

    expires_in = token_data.get("expires_in", 0)
    created_at = token_data.get("created_at", 0)

    if expires_in <= 0:
        return True, "Token valid (no expiry)"

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


def _infer_product_name(feedback) -> str:
    if feedback.product_name:
        return feedback.product_name
    for ann in feedback.annotations:
        if ann.startswith("skill:"):
            return ann.split("skill:", 1)[1].strip()
    if feedback.agent_action:
        import re as _re
        m = _re.search(r"(?:call|invoke)\s+(\S+?)(?:\s+skill|$)", feedback.agent_action, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if feedback.error_message:
        import re as _re
        m = _re.search(r"(\w+-\w+(?:-\w+)+)", feedback.error_message)
        if m:
            return m.group(1)
    return ""


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
    feedback_file.write_text(content, encoding="utf-8")


def deliver_feedback(
    feedback_id: str,
    feedbacks_dir: Path,
    atomgit_home: str | None = None,
) -> dict:
    config = _load_config()
    gitcode_cfg = config.get("delivery", {}).get("channels", {}).get("gitcode", {})

    if not gitcode_cfg.get("enabled", False):
        return {"success": False, "error": "GitCode delivery not enabled"}

    repo_url = gitcode_cfg.get("repo_url", "")
    if not repo_url:
        return {"success": False, "error": "GitCode repo URL not configured"}

    # Get token from AtomGit-GO
    resolution = _resolve_atomgit_token(atomgit_home)
    if not resolution["success"]:
        return resolution  # carries need_login signal or error

    token = resolution["access_token"]
    atomgit_hint = resolution.get("atomgit")

    feedback_file = feedbacks_dir / f"{feedback_id}.md"
    if not feedback_file.exists():
        return {"success": False, "error": f"Feedback file not found: {feedback_file}"}

    try:
        feedback = read_feedback_md(feedback_file)
    except Exception as e:
        return {"success": False, "error": f"Failed to read feedback record: {e}"}

    if feedback.status == FeedbackStatus.DISCARDED:
        return {"success": False, "error": "Discarded feedbacks are not delivered"}

    title = _build_issue_title(feedback, feedback_file, feedback.product_name or "")
    body = _build_issue_body(feedback, feedback_file)

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


def _build_merged_issue_title(feedbacks: list, feedbacks_dir: Path, product_name: str = "") -> str:
    if len(feedbacks) == 1:
        fb_file = feedbacks_dir / f"{feedbacks[0].feedback_id}.md"
        return _build_issue_title(feedbacks[0], fb_file, product_name)
    first_desc = (
        feedbacks[0].problem_description
        or feedbacks[0].error_message
        or feedbacks[0].user_intent
        or ""
    )
    summary = first_desc[:30] if first_desc else "Batch feedback"
    prefix = f"【{product_name}】" if product_name else ""
    return f"{prefix}VoD Batch ({len(feedbacks)} items): {summary} etc."


def _build_merged_issue_body(feedbacks: list, feedbacks_dir: Path) -> str:
    if len(feedbacks) == 1:
        fb_file = feedbacks_dir / f"{feedbacks[0].feedback_id}.md"
        return _build_issue_body(feedbacks[0], fb_file)

    parts = [f"Total {len(feedbacks)} feedback item(s), submitted together:", ""]
    for i, fb in enumerate(feedbacks, 1):
        desc = fb.problem_description or fb.error_message or fb.user_intent or ""
        scenario = fb.occurrence_scenario or ""
        expected = fb.expected_behavior or fb.user_expected or ""

        parts.append(f"### {i}. {desc or fb.feedback_id}")
        parts.append("")
        if scenario:
            parts.extend(["**To Reproduce**", scenario, ""])
        if expected:
            parts.extend(["**Expected behavior**", expected, ""])
        clean_stack = _strip_error_stack_markers(fb.error_stack)
        if clean_stack:
            parts.extend(["```", clean_stack, "```", ""])
        parts.append("---")
        parts.append("")

    return "\n".join(parts)


def notify(
    feedbacks_dir: Path,
    atomgit_home: str | None = None,
) -> list[dict]:
    config = _load_config()
    gitcode_cfg = config.get("delivery", {}).get("channels", {}).get("gitcode", {})

    if not gitcode_cfg.get("enabled", False):
        return []

    repo_url = gitcode_cfg.get("repo_url", "")
    if not repo_url:
        return [{"success": False, "error": "GitCode repo URL not configured"}]

    # Get token from AtomGit-GO
    resolution = _resolve_atomgit_token(atomgit_home)
    if not resolution["success"]:
        return [resolution]  # carries need_login signal or error

    token = resolution["access_token"]
    atomgit_hint = resolution.get("atomgit")

    all_feedbacks = read_all_feedbacks(feedbacks_dir)
    pending = []
    for fb in all_feedbacks:
        fb_file = feedbacks_dir / f"{fb.feedback_id}.md"
        content = fb_file.read_text(encoding="utf-8") if fb_file.exists() else ""
        if "delivery_status: delivered" in content:
            continue
        if fb.status == FeedbackStatus.DISCARDED:
            continue
        pending.append(fb)

    if not pending:
        return []

    product_name = pending[0].product_name or "" if pending else ""
    title = _build_merged_issue_title(pending, feedbacks_dir, product_name)
    body = _build_merged_issue_body(pending, feedbacks_dir)
    result = _create_gitcode_issue(repo_url, token, title, body)

    results = []
    if result.get("success"):
        for fb in pending:
            fb_file = feedbacks_dir / f"{fb.feedback_id}.md"
            _update_feedback_delivery_status(
                fb_file,
                result.get("issue_url", ""),
                str(result.get("issue_iid", "")),
            )
            entry = {
                "feedback_id": fb.feedback_id,
                "success": True,
                "issue_url": result.get("issue_url", ""),
                "issue_iid": result.get("issue_iid", ""),
            }
            # If using AtomGit-GO token, attach source info
            if atomgit_hint and atomgit_hint.get("status") == "available":
                entry["auth_source"] = "atomgit-go"
                if atomgit_hint.get("user"):
                    entry["auth_user"] = atomgit_hint["user"]
            results.append(entry)
    else:
        for fb in pending:
            results.append({
                "feedback_id": fb.feedback_id,
                "success": False,
                "error": result.get("error", "unknown"),
            })

    return results


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
                "Server binary not found. Install the open-source project AtomGit-GO (MIT license) first:\n"
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

    notify_p = subparsers.add_parser("notify", help="Push undelivered feedbacks")
    notify_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")
    notify_p.add_argument("--atomgit-home", default=None, help="AtomGit-GO config dir (default: ~/.atomcode or $ATOMCODE_HOME)")

    deliver_p = subparsers.add_parser("deliver", help="Deliver single feedback")
    deliver_p.add_argument("--feedback-id", required=True, help="Feedback ID")
    deliver_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="Path to .vod/feedbacks/")
    deliver_p.add_argument("--atomgit-home", default=None, help="AtomGit-GO config dir (default: ~/.atomcode or $ATOMCODE_HOME)")

    update_p = subparsers.add_parser("update-status", help="Update feedback delivery status")
    update_p.add_argument("--feedback-id", required=True, help="Feedback ID")
    update_p.add_argument("--status", required=True, help="Delivery status")
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

    if args.command == "server-start":
        result = _start_login_server()
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "server-stop":
        result = _stop_login_server(args.pid)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "notify":
        results = notify(
            args.feedbacks_dir,
            atomgit_home=getattr(args, "atomgit_home", None),
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "deliver":
        result = deliver_feedback(
            args.feedback_id, args.feedbacks_dir,
            atomgit_home=getattr(args, "atomgit_home", None),
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
        fb_file.write_text(content, encoding="utf-8")
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
