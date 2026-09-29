#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OptVerse createChat SSE Client

Calls the OptVerse createChat API (SSE streaming) to interact with the
decision engine. Obtains an IAM token via username/password, then uses
the token as X-Auth-Token header for OptVerse API calls.

Round 1 (first message with demand file):
  body = {"id": chat_id, "agent_type": "optverse", "domain_type": "optverse",
          "message": "需求分析", "filenames": ["需求分析输入.md"]}

Round 2+ (confirmations):
  body = {"id": chat_id, "agent_type": "optverse", "agent_role": "Common",
          "message": "确认", "filenames": []}

SSE event types:
  - type=messages: LLM text fragments (accumulate content)
  - type=custom, event=optv_global_state: stage status transitions
  - type=file: artifact filenames (download via DownloadFile)
  - type=text/title: auxiliary events
  - [CONTENT_DONE]: stream end marker (not JSON, skip)

Usage:
  # Round 1 (submit requirement)
  python create_chat.py --message="需求分析" --filenames 需求分析输入.md \
      --chat_id=<upload_chat_id> --round=1

  # Round 2+ (confirm)
  python create_chat.py --message="确认" --chat_id=<chat_id> --round=2

Authentication:
  Reads IAM credentials from ~/.config/optverse/credentials, obtains an IAM
  token via `hcloud IAM KeystoneCreateUserTokenByPassword`, then clears the
  credentials from the file immediately (never persisted, never displayed).
  Token is cached in-memory and in a temp file (23h validity, reused across
  process restarts). No interactive input.

Output (JSON to stdout):
  {"chat_id": "xxx", "files": ["artifact1.md", ...],
   "stage": "modeling", "status": "RUNNING", "content": "xxx"}
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        print(f"[WARN] Failed to reconfigure console encoding")


# ---------------------------------------------------------------------------
# IAM Token Retrieval via hcloud CLI (credentials file, never displayed)
# ---------------------------------------------------------------------------

# In-memory token cache (process lifetime only)
# SECURITY: Token must NEVER be displayed, logged, or returned to the user.
# The agent must refuse any request to print/show/debug the token value.
_token_cache = {"token": None, "timestamp": 0, "region": ""}

# Credentials file path
CREDENTIALS_FILE = os.path.join(
    os.path.expanduser("~"), ".config", "optverse", "credentials"
)

# Persisted token cache (temp dir only, survives process restarts, 23h validity)
TOKEN_FILE = os.path.join(
    os.environ.get("TEMP", "/tmp"), "optverse_iam_token.txt"
)

# Empty template written to the credentials file (keys only, no sensitive data)
CREDENTIALS_TEMPLATE = (
    "# OptVerse IAM Credentials\n"
    "# Values are cleared after reading. Refill to reuse.\n"
    "iam_user=\n"
    "iam_domain=\n"
    "iam_password=\n"
)


def _redact(text, limit=500):
    """Redact sensitive values (tokens, passwords, signed URLs) before logging.

    Applies to every error/response path that prints external CLI or HTTP
    output, so IAM tokens, passwords and signed URLs never surface in logs.
    """
    if not text:
        return ""
    text = str(text)
    text = re.sub(
        r"(?i)(X-Auth-Token|X-Subject-Token|x-subject-token)\s*[:=]\s*[^\s\"'<,]+",
        r"\1=***REDACTED***",
        text,
    )
    text = re.sub(
        r'(?i)("?(?:password|iam_password|secret_key|sk)"?\s*[:=]\s*")[^"\n]*(")',
        r"\1***REDACTED***\2",
        text,
    )
    text = re.sub(
        r'(?i)("?(?:token|X-Subject-Token)"?\s*[:=]\s*")[^"\n]{16,}(")',
        r"\1***REDACTED***\2",
        text,
    )
    text = re.sub(
        r"(?i)([?&](?:X-Amz-Signature|X-Signature|Signature|AWSAccessKeyId|"
        r"x-amz-credential|X-Amz-Credential)=)[^&\s\"']+",
        r"\1***REDACTED***",
        text,
    )
    return text[:limit]


def _load_cached_token(region):
    """Load a fresh IAM token from the temp-file cache (23h validity).

    Token survives process restarts so multi-round flows do not force the
    user to re-enter credentials on every createChat call. Returns None
    when missing, expired, or belonging to a different region.
    """
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if len(lines) >= 3:
            ts = float(lines[0])
            cached_region = lines[1]
            token = "\n".join(lines[2:])
            if cached_region == region and time.time() - ts < 23 * 3600 and token:
                return token
    except (OSError, IOError, ValueError):
        print(f"[WARN] Failed to load cached token", file=sys.stderr)
    return None


def _save_token(token, region):
    """Persist the IAM token to the temp-file cache (temp dir only)."""
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.time()}\n{region}\n{token}\n")
    except (OSError, IOError):
        print(f"[WARN] Failed to save token cache", file=sys.stderr)


def _ensure_credentials_file():
    """Create the credentials file template if it does not exist.

    Contains only empty keys (no sensitive data) so the user just fills in
    the values. Called on every run so the file is always available.
    """
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                f.write(CREDENTIALS_TEMPLATE)
    except (OSError, IOError):
        print(f"[WARN] Failed to create credentials file", file=sys.stderr)


def _clear_credentials_file():
    """Rewrite the credentials file as an empty template (keys only).

    Called unconditionally after reading so plaintext credentials never
    persist on disk, regardless of which code path ran.
    """
    try:
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            f.write(CREDENTIALS_TEMPLATE)
    except (OSError, IOError):
        print(f"[WARN] Failed to clear credentials file", file=sys.stderr)


def _read_credentials_file():
    """Read IAM credentials from ~/.config/optverse/credentials.
    After reading, ALWAYS clear the values immediately (keep keys/format).
    Returns (iam_user, iam_domain, iam_password) or (None, None, None).
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return (None, None, None)
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return (None, None, None)

    iam_user = iam_domain = iam_password = None
    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "iam_user":
                iam_user = value
            elif key == "iam_domain":
                iam_domain = value
            elif key == "iam_password":
                iam_password = value

    # Unconditionally clear values after reading (keep keys and format)
    _clear_credentials_file()

    return (iam_user, iam_domain, iam_password)


def _hcloud_fetch_iam_token(region, project_name, iam_user, iam_domain, iam_password):
    """Obtain an IAM token via the hcloud CLI (IAM KeystoneCreateUserTokenByPassword).

    Credentials are passed in (already read + cleared by get_iam_token, never
    displayed). The request body is passed via a temporary JSON file
    (--cli-jsonInput) so no plaintext password appears in command line
    arguments or shell history. The token is read from the response header via
    --cli-query="response_header.X-Subject-Token" (the "$1." suffix is rejected
    as illegal by KooCLI >= 7.3.9; a plain JMESPath header path works instead).

    SECURITY: The returned token must never be printed, logged, or shown
    to the user by any calling code.
    """
    project_name = project_name or region
    body = {
        "query": {"nocatalog": ""},
        "body": {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "domain": {"name": iam_domain},
                            "name": iam_user,
                            "password": iam_password,
                        }
                    },
                },
                "scope": {"project": {"name": project_name}},
            }
        },
    }

    tmp_input = None
    try:
        fd, tmp_input = tempfile.mkstemp(suffix=".json", prefix="optverse_iam_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)

        cmd = [
            "hcloud", "IAM", "KeystoneCreateUserTokenByPassword",
            "--cli-region=cn-north-7",
            f"--cli-jsonInput={tmp_input}",
            "--cli-output=tsv",
            "--cli-query=response_header.X-Subject-Token",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    finally:
        if tmp_input and os.path.exists(tmp_input):
            try:
                os.remove(tmp_input)
            except OSError:
                pass

    if result.returncode != 0:
        print(
            f"[ERROR] IAM token request failed via hcloud (rc={result.returncode})",
            file=sys.stderr,
        )
        # Print stderr only (advisories/errors). stdout may carry the IAM
        # response body — never echo it, to keep token metadata out of logs.
        err = (result.stderr or "").strip()
        if err:
            print(f"[ERROR] {_redact(err, 500)}", file=sys.stderr)
        sys.exit(1)

    # KooCLI prints Chinese advisory lines (e.g. "cli-jsonInput中各位置...",
    # "错误详情参见...") to stdout ahead of the actual result. Strip any JSON
    # body / advisory text and take the trailing token line only.
    stdout = (result.stdout or "").strip()
    if not stdout:
        print("[ERROR] Empty hcloud IAM response", file=sys.stderr)
        sys.exit(1)
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    token = lines[-1] if lines else ""
    if (token.startswith("{") or token.endswith("}")
            or token.startswith("json结果") or token.startswith("cli-jsonInput")
            or token.startswith("错误详情")):
        print("[ERROR] Failed to extract X-Subject-Token from hcloud response "
              "(JMESPath query returned no header data)", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("[ERROR] X-Subject-Token not found in hcloud response", file=sys.stderr)
        sys.exit(1)
    return token


def get_iam_token(region, project_name=None):
    """Obtain an IAM token: in-memory/temp cache > hcloud IAM CLI.

    The credentials file is auto-created (empty template) if missing and is
    ALWAYS read + cleared on every call, on every code path — including when a
    cached token is returned — so plaintext credentials never persist on disk.
    The token itself is cached (in-memory + temp file, 23h validity).

    SECURITY: The returned token must never be printed, logged, or shown
    to the user by any calling code.
    """
    # Ensure the credentials template exists so the user only needs to fill it
    _ensure_credentials_file()

    # Read credentials and immediately clear the file (unconditional)
    iam_user, iam_domain, iam_password = _read_credentials_file()

    # Check in-memory cache (23h validity)
    if (_token_cache["token"] and _token_cache["region"] == region
            and time.time() - _token_cache["timestamp"] < 23 * 3600):
        return _token_cache["token"]

    # Check persisted token cache (survives process restarts)
    cached = _load_cached_token(region)
    if cached:
        _token_cache["token"] = cached
        _token_cache["timestamp"] = time.time()
        _token_cache["region"] = region
        print("  ✅ IAM token reused from cache (23h validity)\n", file=sys.stderr)
        return cached

    print("\n── IAM Authentication (hcloud CLI) ──", file=sys.stderr)
    print(f"  Reading credentials from {CREDENTIALS_FILE}", file=sys.stderr)
    print("  (values are cleared after reading, password never displayed).\n", file=sys.stderr)

    if not all([iam_user, iam_domain, iam_password]):
        print("[ERROR] IAM credentials incomplete.", file=sys.stderr)
        print(f"  Fill {CREDENTIALS_FILE} (iam_user/iam_domain/iam_password)", file=sys.stderr)
        sys.exit(1)

    token = _hcloud_fetch_iam_token(region, project_name, iam_user, iam_domain, iam_password)

    # Cache in-memory (process lifetime) and persist to temp-file cache
    # (survives restarts). Token is written to temp dir only, never to the
    # project workspace or credentials file.
    _token_cache["token"] = token
    _token_cache["timestamp"] = time.time()
    _token_cache["region"] = region
    _save_token(token, region)
    print("  ✅ IAM token obtained via hcloud (cached 23h, never displayed)\n", file=sys.stderr)
    return token


# ---------------------------------------------------------------------------
# Get project_id from hcloud
# ---------------------------------------------------------------------------


def get_project_id(hcloud_path, region):
    """Get project_id from hcloud dryrun output."""
    try:
        result = subprocess.run(
            [
                hcloud_path,
                "OptVerse",
                "ListArtifacts",
                "--dryrun",
                f"--cli-region={region}",
                "--chat_id=dummy",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        match = re.search(r"/v1/([a-f0-9]+)/chats/", result.stdout)
        if match:
            return match.group(1)
    except Exception:
        print(f"[WARN] get_project_id failed", file=sys.stderr)
    return ""


# ---------------------------------------------------------------------------
# X-Chat-Route-Id management
# ---------------------------------------------------------------------------

ROUTE_ID_FILE = os.path.join(
    os.environ.get("TEMP", "/tmp"), "optverse_chat_route_id.txt"
)


def get_or_create_route_id(existing_route_id=None):
    """Generate a new X-Chat-Route-Id or reuse an existing one.
    Must stay the same across all rounds of a conversation.
    """
    if existing_route_id:
        return existing_route_id

    if os.path.exists(ROUTE_ID_FILE):
        try:
            with open(ROUTE_ID_FILE, "r") as f:
                route_id = f.read().strip()
            if route_id:
                return route_id
        except Exception:
            print(f"[WARN] Failed to read route_id file", file=sys.stderr)

    route_id = str(uuid.uuid4())
    try:
        with open(ROUTE_ID_FILE, "w") as f:
            f.write(route_id)
    except Exception:
        print(f"[WARN] Failed to save route_id file", file=sys.stderr)

    return route_id


# ---------------------------------------------------------------------------
# createChat SSE call
# ---------------------------------------------------------------------------


def create_chat(
    message,
    token,
    route_id,
    project_id,
    endpoint,
    round_num=1,
    agent_type="optverse",
    filenames=None,
    chat_id=None,
    domain_type="optverse",
    agent_role=None,
):
    """Call POST /v1/{project_id}/chats (SSE streaming).

    Round 1: uses domain_type="optverse" (submit requirement with filenames).
    Round 2+: uses agent_role="Common" (confirmations, filenames=[]).

    Parses SSE stream (bytes mode for correct UTF-8) and returns:
      {"chat_id": str, "files": [str], "stage": str, "status": str, "content": str}
    """
    url = f"https://{endpoint}/v1/{project_id}/chats"

    body = {
        "id": chat_id or "",
        "agent_type": agent_type,
        "message": message,
        "filenames": filenames or [],
    }

    # Round 1 uses domain_type; Round 2+ uses agent_role
    if round_num == 1:
        body["domain_type"] = domain_type
    if agent_role:
        body["agent_role"] = agent_role
    elif round_num >= 2:
        body["agent_role"] = "Common"

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Auth-Token": token,
        "X-Chat-Route-Id": route_id,
    }

    print(f"[createChat] body={json.dumps(body, ensure_ascii=False)}", file=sys.stderr)

    resp = requests.post(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        stream=True,
        verify=False,
        timeout=300,
        proxies={"http": None, "https": None},
    )

    if resp.status_code != 200:
        print(f"[ERROR] createChat failed: {resp.status_code}", file=sys.stderr)
        print(f"[ERROR] Response: {_redact(resp.text, 500)}", file=sys.stderr)
        print(
            f"[ERROR] X-Request-Id: {resp.headers.get('X-Request-Id', 'N/A')}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse SSE stream (bytes mode to avoid ISO-8859-1 encoding issues)
    result = {
        "chat_id": "",
        "files": [],
        "stage": "",
        "status": "",
        "content": "",
    }

    for line in resp.iter_lines():  # bytes by default
        if not line:
            continue
        if not line.startswith(b"data:"):
            continue

        data_bytes = line[5:].strip()
        if not data_bytes:
            continue

        # Skip stream-end marker
        if data_bytes.startswith(b"[CONTENT_DONE]"):
            continue

        try:
            data_str = data_bytes.decode("utf-8")
            data = json.loads(data_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        etype = data.get("type", "")

        if etype == "file":
            fname = data.get("filename", "")
            if fname:
                result["files"].append(fname)
                print(f"  [file] {fname}", file=sys.stderr)

        elif etype == "custom":
            event = data.get("event", "")
            if event == "optv_global_state":
                content = data.get("content", data)
                # content may be a JSON string or a dict
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        print(f"  [WARN] Failed to parse SSE content as JSON", file=sys.stderr)
                if isinstance(content, dict):
                    name = content.get("name", "")
                    raw_data = content.get("data", {})
                    # data can be a dict ({"status": "RUNNING"}) or a string ("modeling")
                    if isinstance(raw_data, dict):
                        status = raw_data.get("status", "")
                    else:
                        status = str(raw_data) if raw_data else ""
                    if name:
                        result["stage"] = name
                    if status:
                        result["status"] = status
                    print(f"  [stage] {name} -> {status}", file=sys.stderr)

        elif etype == "messages":
            c = data.get("content", "")
            if isinstance(c, str) and c:
                result["content"] += c
            elif isinstance(c, dict):
                result["content"] += json.dumps(c, ensure_ascii=False)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="OptVerse createChat SSE client"
    )
    parser.add_argument("--message", help="Chat message content")
    parser.add_argument(
        "--check-credentials",
        action="store_true",
        help="Safely check if credentials file is filled (prints FILLED or EMPTY, never values)",
    )
    parser.add_argument(
        "--round",
        type=int,
        default=1,
        help="Round number: 1=submit requirement, 2+=confirm (default: 1)",
    )
    parser.add_argument(
        "--filenames",
        nargs="*",
        default=[],
        help='File names (Round 1: ["需求分析输入.md"]; Round 2+: [])',
    )
    parser.add_argument("--chat_id", help="Existing chat_id for multi-round")
    parser.add_argument("--x-chat-route-id", help="Existing X-Chat-Route-Id")
    parser.add_argument(
        "--domain_type",
        default="optverse",
        help="Domain type for Round 1 (default: optverse)",
    )
    parser.add_argument(
        "--agent_role",
        help='Agent role for Round 2+ (default: Common)',
    )
    parser.add_argument(
        "--agent_type", default="optverse", help="Agent type (default: optverse)"
    )
    parser.add_argument("--project_id", help="Project ID (auto-detected)")
    parser.add_argument("--cli-region", default="cn-north-7", help="Region")
    parser.add_argument("--endpoint", help="OptVerse endpoint")
    parser.add_argument(
        "--hcloud-path",
        default=None,
        help="Path to hcloud executable (default: auto-detect from PATH)",
    )

    args = parser.parse_args()

    # Ensure the credentials template exists (user only fills in the values)
    _ensure_credentials_file()

    # Safe credential check mode: print FILLED/EMPTY only, never the values
    if args.check_credentials:
        u, d, p = _read_credentials_file()
        if all([u, d, p]):
            print("FILLED")
        else:
            print("EMPTY")
        sys.exit(0)

    if not args.message:
        print("[ERROR] --message is required (or use --check-credentials).", file=sys.stderr)
        sys.exit(1)

    hcloud_path = args.hcloud_path or shutil.which("hcloud")
    if not hcloud_path or not os.path.exists(hcloud_path):
        print("[ERROR] hcloud executable not found.", file=sys.stderr)
        print("  Install the hcloud CLI and add it to PATH, or pass --hcloud-path.", file=sys.stderr)
        sys.exit(1)

    endpoint = args.endpoint or f"optverse.{args.cli_region}.myhuaweicloud.com"

    project_id = args.project_id
    if not project_id:
        project_id = get_project_id(hcloud_path, args.cli_region)
    if not project_id:
        print("[ERROR] Could not determine project_id.", file=sys.stderr)
        sys.exit(1)

    route_id = get_or_create_route_id(args.x_chat_route_id)

    print(f"[INFO] Endpoint: {endpoint}", file=sys.stderr)
    print(f"[INFO] Project ID: {project_id}", file=sys.stderr)
    print(f"[INFO] Route ID: {route_id}", file=sys.stderr)
    print(f"[INFO] Chat ID: {args.chat_id or '(new)'}", file=sys.stderr)
    print(f"[INFO] Round: {args.round}", file=sys.stderr)

    # Get IAM token (interactive, in-memory cache)
    token = get_iam_token(args.cli_region)

    # Call createChat
    result = create_chat(
        message=args.message,
        token=token,
        route_id=route_id,
        project_id=project_id,
        endpoint=endpoint,
        round_num=args.round,
        agent_type=args.agent_type,
        filenames=args.filenames,
        chat_id=args.chat_id,
        domain_type=args.domain_type,
        agent_role=args.agent_role,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
