#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OptVerse 12-Step Workflow Runner (9 Required + 3 Optional)

Orchestrates the full OptVerse decision engine workflow:
  1.  UploadFile (requirement analysis .md)
  2.  createChat Round 1 (domain_type, filenames) → requirement_analyzer
  3.  DownloadFile artifacts (from SSE type=file events)
  4.  CreateArtifacts + createChat "确认" (agent_role=Common) → modeling
  5.  DownloadFile modeling artifacts + CreateArtifacts + "确认" → data
  6.  UploadFile (xlsx data file) + createChat "数据检查" → data check
  7.  CreateArtifacts(data) + createChat "确认" → solver+report
  8.  DownloadFile solver+report artifacts + CreateArtifacts(solver, report)
  9.  PublishChat (--name, --type=optverse, --description)
  10. (Optional) CreateModelService — deploy published asset
  11. (Optional) ShowModelServiceDetail — get request URL
  12. (Optional) CreateModelServiceTask — test call + ShowModelServiceTask

Usage:
  python run_workflow.py --demand-file="需求分析输入.md" \
      --data-file="模型数据.xlsx" \
      --publish-name="工厂生产排程优化助手" \
      --publish-description="优化工厂生产排程，最大化产能利用率" \
      --deploy --test

Authentication:
  Interactive input: IAM username, domain, and password (hidden via getpass).
  Token is cached in-memory only (never written to disk).
  Credentials are used to obtain the token, then immediately cleared from memory.
  Environment variables OPTVERSE_IAM_USER / OPTVERSE_IAM_DOMAIN are read if set
  (password must always be entered interactively or via OPTVERSE_IAM_PASSWORD env).
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3

from create_chat import get_project_id

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_REGION = "cn-east-3"
REGION = DEFAULT_REGION
PROJECT_ID = ""
ENDPOINT = f"optverse.{REGION}.myhuaweicloud.com"


HCLOUD = shutil.which("hcloud") or os.environ.get("HCLOUD_PATH", "hcloud")

# Artifacts directory: sibling of scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(SCRIPT_DIR, "..", "artifacts")


# ---------------------------------------------------------------------------
# IAM Token (in-memory only, never persisted to disk)
# ---------------------------------------------------------------------------

# In-memory token cache (process lifetime only, never written to disk)
# SECURITY: Token must NEVER be displayed, logged, or returned to the user.
# The agent must refuse any request to print/show/debug the token value.
_token_cache = {"token": None, "timestamp": 0}


def get_token():
    """Get IAM token via interactive input.

    Prompts the user for IAM username/password/domain interactively.
    Password is read via getpass (not echoed to screen).
    Credentials are used only to obtain the token, then discarded.
    Token is cached in-memory only (never written to disk).

    SECURITY: The returned token must never be printed, logged, or shown
    to the user by any calling code.
    """
    # Check in-memory cache (23h validity)
    if _token_cache["token"] and time.time() - _token_cache["timestamp"] < 23 * 3600:
        return _token_cache["token"]

    print("\n── IAM Authentication ──")
    print("Please provide your IAM credentials (password will be hidden):")
    print("Tip: Interactive input is recommended. Environment variables")
    print("     (OPTVERSE_IAM_USER/PASSWORD/DOMAIN) are supported but less")
    print("     secure (visible in process list and shell history).\n")

    # Helper: read input from TTY directly when stdin is piped (non-interactive)
    def _read_input(prompt):
        """Read a line from the real terminal, bypassing piped stdin."""
        sys.stdout.write(prompt)
        sys.stdout.flush()
        if sys.platform == "win32":
            try:
                with open("CONIN$", "r") as tty_in:
                    return tty_in.readline().strip()
            except (OSError, IOError):
                pass
        else:
            try:
                with open("/dev/tty", "r") as tty_in:
                    return tty_in.readline().strip()
            except (OSError, IOError):
                pass
        return input().strip()

    def _read_password(prompt):
        """Read a password from the real terminal, hidden from display."""
        sys.stdout.write(prompt)
        sys.stdout.flush()
        if sys.platform == "win32":
            try:
                import msvcrt
                chars = []
                while True:
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n"):
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        return "".join(chars)
                    elif ch == "\x03":
                        raise KeyboardInterrupt
                    elif ch == "\x08":
                        if chars:
                            chars.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    else:
                        chars.append(ch)
                        sys.stdout.write("*")
                        sys.stdout.flush()
            except ImportError:
                pass
        else:
            try:
                with open("/dev/tty", "r") as tty_in:
                    import termios
                    fd = tty_in.fileno()
                    old = termios.tcgetattr(fd)
                    try:
                        new = termios.tcgetattr(fd)
                        new[3] &= ~termios.ECHO
                        termios.tcsetattr(fd, termios.TCSANOW, new)
                        line = tty_in.readline().strip()
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        return line
                    finally:
                        termios.tcsetattr(fd, termios.TCSANOW, old)
            except (OSError, IOError, ImportError):
                pass
        import getpass
        return getpass.getpass("")

    # Check env vars first, fall back to interactive input
    iam_user = os.environ.get("OPTVERSE_IAM_USER")
    if not iam_user:
        iam_user = _read_input("  IAM Username: ")
    else:
        print(f"  IAM Username: {iam_user} (from env)")

    iam_domain = os.environ.get("OPTVERSE_IAM_DOMAIN")
    if not iam_domain:
        iam_domain = _read_input("  IAM Domain (Account Name): ")
    else:
        print(f"  IAM Domain: {iam_domain} (from env)")

    iam_password = os.environ.get("OPTVERSE_IAM_PASSWORD")
    if not iam_password:
        iam_password = _read_password("  IAM Password: ")
    else:
        print("  IAM Password: *** (from env)")

    if not all([iam_user, iam_password, iam_domain]):
        print("[ERROR] IAM credentials incomplete.")
        sys.exit(1)

    iam_url = f"https://iam.{REGION}.myhuaweicloud.com/v3/auth/tokens"
    body = {
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
            "scope": {"project": {"name": REGION}},
        }
    }
    resp = requests.post(
        iam_url, json=body, headers={"Content-Type": "application/json"},
        verify=False, timeout=30, proxies={"http": None, "https": None},
    )
    # Clear password from memory immediately
    iam_password = None
    if resp.status_code != 201:
        print(f"[ERROR] IAM token request failed: {resp.status_code} {resp.text[:500]}")
        sys.exit(1)
    token = resp.headers.get("X-Subject-Token")
    if not token:
        print("[ERROR] X-Subject-Token not found in response")
        sys.exit(1)

    # Cache in-memory only (never to disk)
    _token_cache["token"] = token
    _token_cache["timestamp"] = time.time()
    print("  ✅ IAM token obtained (cached in-memory, 23h validity, never displayed)\n")
    return token


# ---------------------------------------------------------------------------
# OptVerse API Helpers
# ---------------------------------------------------------------------------


def upload_file(token, route_id, file_path, filename, agent_type="optverse",
                chat_id=None):
    """UploadFile → returns chat_id.

    For Step 1 (initial upload), chat_id should be None — a new chat session
    is created and its ID is returned.

    For Step 6+ (uploading data file to an existing chat), chat_id MUST be
    passed to associate the file with the ongoing conversation. Without it,
    the file is uploaded to a new chat context and the decision engine
    cannot access it, resulting in empty data check results.
    """
    url = f"https://{ENDPOINT}/v1/{PROJECT_ID}/chats/file/upload"
    headers = {"X-Auth-Token": token, "X-Chat-Route-Id": route_id}
    with open(file_path, "rb") as f:
        files = {"file": (filename, f, "application/octet-stream")}
        data = {"agent_type": agent_type}
        if chat_id:
            data["chat_id"] = chat_id
        resp = requests.post(
            url, files=files, data=data, headers=headers,
            verify=False, timeout=60, proxies={"http": None, "https": None},
        )
    if resp.status_code not in (200, 202):
        print(f"[ERROR] UploadFile failed: {resp.status_code} {resp.text[:500]}")
        return None
    chat_id = resp.json().get("chat_id")
    print(f"  [UploadFile] {filename} → chat_id={chat_id}")
    return chat_id


def create_chat(token, route_id, chat_id, message, filenames, round_num=1):
    """createChat SSE call. Round 1 uses domain_type; Round 2+ uses agent_role=Common.
    Returns {"chat_id", "files", "stage", "status", "content"}.
    """
    url = f"https://{ENDPOINT}/v1/{PROJECT_ID}/chats"
    body = {
        "id": chat_id or "",
        "agent_type": "optverse",
        "message": message,
        "filenames": filenames or [],
    }
    if round_num == 1:
        body["domain_type"] = "optverse"
    else:
        body["agent_role"] = "Common"

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Auth-Token": token,
        "X-Chat-Route-Id": route_id,
    }
    resp = requests.post(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers, stream=True, verify=False, timeout=300,
        proxies={"http": None, "https": None},
    )
    if resp.status_code != 200:
        print(f"[ERROR] createChat failed: {resp.status_code} {resp.text[:500]}")
        return None

    result = {"chat_id": "", "files": [], "stage": "", "status": "", "content": ""}
    for line in resp.iter_lines():  # bytes mode
        if not line or not line.startswith(b"data:"):
            continue
        data_bytes = line[5:].strip()
        if not data_bytes or data_bytes.startswith(b"[CONTENT_DONE]"):
            continue
        try:
            data = json.loads(data_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        etype = data.get("type", "")
        if etype == "file":
            fname = data.get("filename", "")
            if fname:
                result["files"].append(fname)
        elif etype == "custom" and data.get("event") == "optv_global_state":
            content = data.get("content", data)
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass
            if isinstance(content, dict):
                name = content.get("name", "")
                raw_data = content.get("data", {})
                status = raw_data.get("status", "") if isinstance(raw_data, dict) else str(raw_data)
                if name:
                    result["stage"] = name
                if status:
                    result["status"] = status
        elif etype == "messages":
            c = data.get("content", "")
            if isinstance(c, str):
                result["content"] += c
    return result


def download_file(token, route_id, chat_id, filename):
    """DownloadFile → saves to ARTIFACTS_DIR, returns saved path."""
    from urllib.parse import quote

    encoded = quote(filename, safe="")
    url = f"https://{ENDPOINT}/v1/{PROJECT_ID}/chats/{chat_id}/file/{encoded}/download"
    headers = {
        "X-Auth-Token": token,
        "X-Chat-Route-Id": route_id,
        "X-Need-Content": "true",
    }
    resp = requests.get(
        url, headers=headers, verify=False, timeout=60,
        proxies={"http": None, "https": None},
    )
    if resp.status_code != 200:
        print(f"  [DownloadFile] {filename} → ERROR {resp.status_code}")
        return None

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    save_path = os.path.join(ARTIFACTS_DIR, filename)

    # Response JSON has content field that is base64-encoded
    ct = resp.headers.get("Content-Type", "")
    if "json" in ct:
        try:
            raw = resp.json().get("content", "")
            if raw:
                content_bytes = base64.b64decode(raw)
                with open(save_path, "wb") as f:
                    f.write(content_bytes)
                print(f"  [DownloadFile] {filename} → {save_path} ({len(content_bytes)} bytes)")
                return save_path
        except Exception:
            pass
    # Fallback: raw bytes
    with open(save_path, "wb") as f:
        f.write(resp.content)
    print(f"  [DownloadFile] {filename} → {save_path} ({len(resp.content)} bytes)")
    return save_path


def download_files(token, route_id, chat_id, filenames, max_workers=4):
    """Concurrently download multiple artifacts to avoid N+1 sequential requests.

    Returns list of saved paths (same order as filenames, None on failure).
    """
    if not filenames:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(filenames))) as pool:
        futures = [pool.submit(download_file, token, route_id, chat_id, fn)
                   for fn in filenames]
        return [f.result() for f in futures]


def create_artifacts(chat_id, filenames, stage_name):
    """CreateArtifacts via hcloud."""
    args = [HCLOUD, "OptVerse", "CreateArtifacts",
            f"--chat_id={chat_id}", f"--cli-region={REGION}",
            f"--stage_name={stage_name}"]
    for i, fn in enumerate(filenames, 1):
        args.append(f"--filenames.{i}={fn}")
    result = subprocess.run(args, capture_output=True, text=True, timeout=30,
                            encoding="utf-8", errors="replace")
    ok = result.returncode == 0
    print(f"  [CreateArtifacts] stage={stage_name} files={filenames} → {'OK' if ok else 'FAIL'}")
    return ok


def list_artifacts(chat_id):
    """ListArtifacts via hcloud → returns artifacts list."""
    result = subprocess.run(
        [HCLOUD, "OptVerse", "ListArtifacts",
         f"--chat_id={chat_id}", f"--cli-region={REGION}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        data = json.loads(result.stdout)
        return data.get("artifacts", [])
    except Exception:
        return []


def publish_chat(chat_id, name, asset_type, description):
    """PublishChat via hcloud."""
    result = subprocess.run(
        [HCLOUD, "OptVerse", "PublishChat",
         f"--chat_id={chat_id}", f"--cli-region={REGION}",
         f"--name={name}", f"--type={asset_type}",
         f"--description={description}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        data = json.loads(result.stdout)
        return data.get("id")
    except Exception:
        return None


def create_model_service(asset_id, name, infer_type="online", platform="CCE"):
    """CreateModelService via hcloud — deploy the published asset as a model service.

    Args:
        asset_id: The ID returned by PublishChat.
        name: Deployment name (must be unique).
        infer_type: "online" (online inference) or "edge" (edge inference).
        platform: "CCE" (recommended) or "Modelarts". CCE works; Modelarts may
                  cause internal errors.

    Returns: service_id or None.
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "CreateModelService",
         f"--cli-region={REGION}",
         f"--asset_id={asset_id}",
         f"--name={name}",
         f"--infer_type={infer_type}",
         f"--platform={platform}",
         f"--request_mode=REAL_TIME",
         f"--service_config.instance_count=1"],
        capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace",
    )
    print(f"  [CreateModelService] stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"  [CreateModelService] stderr: {result.stderr[:500]}")
    try:
        data = json.loads(result.stdout)
        return data.get("service_id") or data.get("id")
    except Exception:
        return None


def show_model_service_list():
    """ShowModelServiceList via hcloud — list all model services for verification.
    Returns list of service dicts.
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "ShowModelServiceList",
         f"--cli-region={REGION}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        data = json.loads(result.stdout)
        # Response structure may vary; return the list
        services = data.get("services") or data.get("model_services") or data
        if isinstance(services, list):
            return services
        return [data]
    except Exception:
        return []


def _format_service_lines(services):
    """Format model service entries for display. Pure local logic, no network calls."""
    return [
        f"    - {s.get('service_id') or s.get('id', '')}: {s.get('name', '')}"
        for s in services
        if isinstance(s, dict)
    ]


def show_model_service_detail(service_id):
    """ShowModelServiceDetail via hcloud — get model service details including request URL.
    Returns the full response dict (contains request URL and other info).
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "ShowModelServiceDetail",
         f"--cli-region={REGION}",
         f"--service_id={service_id}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def create_model_service_task(service_id, model_request):
    """CreateModelServiceTask — test the deployed model service.

    Args:
        service_id: Model service ID from CreateModelService.
        model_request: JSON string (serialized from the data-stage json artifact).

    Returns: {"task_id": str, "status": str} or None.
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "CreateModelServiceTask",
         f"--cli-region={REGION}",
         f"--service_id={service_id}",
         f"--inputs.model_request={model_request}"],
        capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace",
    )
    print(f"  [CreateModelServiceTask] stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"  [CreateModelServiceTask] stderr: {result.stderr[:500]}")
    try:
        data = json.loads(result.stdout)
        return {"task_id": data.get("id", ""), "status": data.get("status", "")}
    except Exception:
        return None


def list_model_service_tasks(service_id):
    """ListModelServiceTasks — query task status.
    Returns list of task dicts.
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "ListModelServiceTasks",
         f"--cli-region={REGION}",
         f"--service_id={service_id}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        data = json.loads(result.stdout)
        return data.get("tasks", [])
    except Exception:
        return []


def show_model_service_task(service_id, task_id):
    """ShowModelServiceTask via hcloud — get task details and outputs.
    Returns the full response dict (contains status and outputs).
    """
    result = subprocess.run(
        [HCLOUD, "OptVerse", "ShowModelServiceTask",
         f"--cli-region={REGION}",
         f"--service_id={service_id}",
         f"--task_id={task_id}"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Workflow Steps
# ---------------------------------------------------------------------------

# Stage name mapping for CreateArtifacts
STAGE_NAMES = {
    "requirement_analyzer": "requirement_analyzer",
    "modeling": "modeling",
    "data": "data",
    "solver": "solver",
    "report": "report",
}


def wait_for_user_confirm(message):
    """Print a confirmation prompt and wait for user input."""
    print(f"\n{'='*60}")
    print(f"  ⏸  {message}")
    print(f"  Type 'yes' to continue, 'no' to abort:")
    print(f"{'='*60}")
    while True:
        try:
            answer = input().strip().lower()
        except EOFError:
            answer = "yes"  # non-interactive mode
        if answer in ("yes", "y", "确认"):
            return True
        if answer in ("no", "n", "取消"):
            return False
        print("Please type 'yes' or 'no':")


def run_workflow(demand_file_path, data_file_path, publish_name,
                 publish_description, auto_confirm=False, deploy=False,
                 test_call=False):
    """Run the full OptVerse workflow.

    Steps 1-9: Upload → createChat → Download → CreateArtifacts → Publish.
    Steps 10-11 (optional, --deploy): CreateModelService → ShowModelServiceDetail.
    Step 12 (optional, --test): CreateModelServiceTask → ShowModelServiceTask.
    """

    token = get_token()
    route_id = str(uuid.uuid4())
    print(f"[INFO] Route ID: {route_id}")

    demand_filename = os.path.basename(demand_file_path)
    data_filename = os.path.basename(data_file_path) if data_file_path else None

    # ── Step 1: UploadFile (requirement analysis) ──
    print("\n── Step 1: Upload requirement file ──")
    chat_id = upload_file(token, route_id, demand_file_path, demand_filename)
    if not chat_id:
        print("[FATAL] UploadFile failed.")
        sys.exit(1)

    # ── Step 2: createChat Round 1 (domain_type) ──
    print("\n── Step 2: createChat Round 1 (requirement_analyzer) ──")
    r1 = create_chat(token, route_id, chat_id, "需求分析", [demand_filename], round_num=1)
    if not r1:
        print("[FATAL] createChat Round 1 failed.")
        sys.exit(1)
    print(f"  stage={r1['stage']} status={r1['status']} files={r1['files']}")
    if r1["status"] == "FAILED":
        print("[FATAL] requirement_analyzer FAILED. Retry the workflow.")
        sys.exit(1)

    # ── Step 3: Download requirement analysis artifacts ──
    print("\n── Step 3: Download requirement analysis artifacts ──")
    download_files(token, route_id, chat_id, r1["files"])

    if not auto_confirm:
        if not wait_for_user_confirm("Review requirement analysis artifacts. Continue to modeling?"):
            print("[ABORTED] User cancelled.")
            sys.exit(0)

    # ── Step 4: CreateArtifacts + createChat "确认" → modeling ──
    print("\n── Step 4: CreateArtifacts + confirm → modeling ──")
    create_artifacts(chat_id, r1["files"], "requirement_analyzer")
    r2 = create_chat(token, route_id, chat_id, "确认", [], round_num=2)
    if not r2:
        print("[FATAL] createChat Round 2 failed.")
        sys.exit(1)
    print(f"  stage={r2['stage']} status={r2['status']} files={r2['files']}")

    # ── Step 5: Download modeling artifacts + confirm → data ──
    print("\n── Step 5: Download modeling artifacts + confirm → data ──")
    download_files(token, route_id, chat_id, r2["files"])

    if not auto_confirm:
        if not wait_for_user_confirm("Review modeling artifacts. Continue to data stage?"):
            print("[ABORTED] User cancelled.")
            sys.exit(0)

    create_artifacts(chat_id, r2["files"], "modeling")
    r3 = create_chat(token, route_id, chat_id, "确认", [], round_num=2)
    if not r3:
        print("[FATAL] createChat confirm (modeling→data) failed.")
        sys.exit(1)
    print(f"  stage={r3['stage']} status={r3['status']}")

    # ── Step 6: UploadFile (xlsx data) + createChat "数据检查" ──
    print("\n── Step 6: Upload data file + data check ──")
    if not data_file_path:
        print("[ERROR] --data-file is required for data stage.")
        print("  The xlsx file should be the modeling output template filled with actual data.")
        sys.exit(1)
    upload_file(token, route_id, data_file_path, data_filename, chat_id=chat_id)
    r4 = create_chat(token, route_id, chat_id, "数据检查", [data_filename], round_num=2)
    if not r4:
        print("[FATAL] createChat data check failed.")
        sys.exit(1)
    print(f"  stage={r4['stage']} status={r4['status']} files={r4['files']}")

    # ── Step 7: Download data check artifacts + confirm → solver ──
    print("\n── Step 7: Download data artifacts + confirm → solver ──")
    download_files(token, route_id, chat_id, r4["files"])

    if not auto_confirm:
        if not wait_for_user_confirm("Review data check results. Continue to solver?"):
            print("[ABORTED] User cancelled.")
            sys.exit(0)

    create_artifacts(chat_id, r4["files"], "data")
    r5 = create_chat(token, route_id, chat_id, "确认", [], round_num=2)
    if not r5:
        print("[FATAL] createChat confirm (data→solver) failed.")
        sys.exit(1)
    print(f"  stage={r5['stage']} status={r5['status']} files={r5['files']}")
    # solver may auto-trigger report; r5 should contain solver+report files

    # ── Step 8: Download solver+report artifacts + CreateArtifacts ──
    print("\n── Step 8: Download solver+report artifacts ──")
    download_files(token, route_id, chat_id, r5["files"])

    if not auto_confirm:
        if not wait_for_user_confirm("Review solver results. Continue to publish?"):
            print("[ABORTED] User cancelled.")
            sys.exit(0)

    # Split files by stage: solver files vs report files
    # Heuristic: .gz/.sol/.log/.py → solver; .md report → report
    solver_files = [f for f in r5["files"] if f.endswith((".gz", ".sol", ".log", ".py"))]
    report_files = [f for f in r5["files"] if f not in solver_files]
    if solver_files:
        create_artifacts(chat_id, solver_files, "solver")
    if report_files:
        create_artifacts(chat_id, report_files, "report")

    # Verify all artifacts uploaded
    artifacts = list_artifacts(chat_id)
    print(f"\n  [ListArtifacts] {len(artifacts)} stage groups:")
    for a in artifacts:
        print(f"    {a['stage_name']}: {len(a['filenames'])} files")

    # ── Step 9: PublishChat ──
    print("\n── Step 9: PublishChat ──")
    pub_id = publish_chat(chat_id, publish_name, "optverse", publish_description)
    if pub_id:
        print(f"  ✅ Published! Asset ID: {pub_id}")
    else:
        print("  [ERROR] PublishChat failed.")

    # ── Step 10 (Optional): CreateModelService — deploy the published asset ──
    service_id = None
    if test_call and not deploy:
        print("\n  [WARN] --test requires --deploy. Enabling --deploy automatically.")
        deploy = True

    if deploy and pub_id:
        print("\n── Step 10 (Optional): CreateModelService — deploy ──")
        if auto_confirm or wait_for_user_confirm("Deploy the published asset as a model service?"):
            service_id = create_model_service(pub_id, publish_name)
            if service_id:
                print(f"  ✅ Deployed! Service ID: {service_id}")
                services = show_model_service_list()
                print(f"  [ShowModelServiceList] {len(services)} service(s) found")
                print("\n".join(_format_service_lines(services)))
            else:
                print("  [ERROR] CreateModelService failed.")
        else:
            print("  [SKIP] Deployment skipped by user.")

    # ── Step 11 (Optional): ShowModelServiceDetail — get request URL ──
    if deploy and service_id:
        print("\n── Step 11 (Optional): ShowModelServiceDetail — get request URL ──")
        detail = show_model_service_detail(service_id)
        if detail:
            print(f"  [ShowModelServiceDetail] Response:")
            print(json.dumps(detail, ensure_ascii=False, indent=2))
        else:
            print("  [ERROR] ShowModelServiceDetail failed.")

    # ── Step 12 (Optional): CreateModelServiceTask — test the deployed service ──
    task_id = None
    if test_call and service_id:
        print("\n── Step 12 (Optional): CreateModelServiceTask — test call ──")
        if auto_confirm or wait_for_user_confirm("Test the deployed model service with data json?"):
            # Find the data-stage json artifact (model_request content)
            data_json_files = [f for f in r4["files"] if f.endswith(".json")]
            if not data_json_files:
                print("  [ERROR] No data json artifact found for model_request.")
            else:
                json_fname = data_json_files[0]
                print(f"  Using data json: {json_fname}")
                # Download and read the json content
                from urllib.parse import quote
                encoded = quote(json_fname, safe="")
                dl_url = f"https://{ENDPOINT}/v1/{PROJECT_ID}/chats/{chat_id}/file/{encoded}/download"
                dl_resp = requests.get(
                    dl_url,
                    headers={"X-Auth-Token": token, "X-Chat-Route-Id": route_id,
                              "X-Need-Content": "true"},
                    verify=False, timeout=60,
                    proxies={"http": None, "https": None},
                )
                if dl_resp.status_code == 200:
                    raw = dl_resp.json().get("content", "")
                    if raw:
                        model_request = base64.b64decode(raw).decode("utf-8")
                        print(f"  model_request: {model_request[:200]}...")
                        task_result = create_model_service_task(service_id, model_request)
                        if task_result:
                            task_id = task_result.get("task_id", "")
                            print(f"  ✅ Task created! Task ID: {task_id}")
                            print(f"  Status: {task_result.get('status', '')}")
                        else:
                            print("  [ERROR] CreateModelServiceTask failed.")
                else:
                    print(f"  [ERROR] DownloadFile failed: {dl_resp.status_code}")
        else:
            print("  [SKIP] Test call skipped by user.")

    # ── Show task result ──
    if task_id and service_id:
        print("\n── ShowModelServiceTask — get task result ──")
        task_detail = show_model_service_task(service_id, task_id)
        if task_detail:
            print(f"  [ShowModelServiceTask] Response:")
            print(json.dumps(task_detail, ensure_ascii=False, indent=2))
        else:
            print("  [ERROR] ShowModelServiceTask failed.")

    print(f"\n{'='*60}")
    print(f"  🎉 Workflow complete!")
    print(f"  Chat ID: {chat_id}")
    print(f"  Artifacts: {ARTIFACTS_DIR}")
    print(f"  Published Asset ID: {pub_id}")
    if service_id:
        print(f"  Model Service ID: {service_id}")
    if task_id:
        print(f"  Test Task ID: {task_id}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    global HCLOUD, REGION, PROJECT_ID, ENDPOINT
    parser = argparse.ArgumentParser(
        description="OptVerse 12-step workflow runner (9 required + 3 optional)"
    )
    parser.add_argument("--demand-file", required=True,
                        help="Path to requirement analysis .md file")
    parser.add_argument("--data-file",
                        help="Path to xlsx data file (filled with actual data)")
    parser.add_argument("--publish-name", default="OptVerse优化助手",
                        help="Published asset name")
    parser.add_argument("--publish-description",
                        default="OptVerse决策引擎求解结果",
                        help="Published asset description (1-2048 chars)")
    parser.add_argument("--auto-confirm", action="store_true",
                        help="Skip user confirmation prompts")
    parser.add_argument("--clean-artifacts", action="store_true",
                        help="Clean artifacts directory before running")
    parser.add_argument("--deploy", action="store_true",
                        help="Deploy published asset as model service (optional Steps 10-11)")
    parser.add_argument("--test", action="store_true",
                        help="Test the deployed model service (optional Step 12)")
    parser.add_argument(
        "--hcloud-path",
        help="Path to hcloud executable (default: auto-detect from PATH)",
    )
    parser.add_argument(
        "--cli-region", default=DEFAULT_REGION,
        help=f"Region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--project-id",
        help="Project ID (auto-detected via hcloud dryrun if omitted)",
    )
    args = parser.parse_args()

    REGION = args.cli_region
    ENDPOINT = f"optverse.{REGION}.myhuaweicloud.com"

    HCLOUD = _resolve_hcloud_path(args.hcloud_path)
    if not HCLOUD or not os.path.exists(HCLOUD):
        print("[ERROR] hcloud executable not found.")
        print("  Install the hcloud CLI and add it to PATH, or pass --hcloud-path.")
        sys.exit(1)

    PROJECT_ID = args.project_id
    if not PROJECT_ID:
        PROJECT_ID = get_project_id(HCLOUD, REGION)
    if not PROJECT_ID:
        print("[ERROR] Could not determine project ID.")
        print("  Run 'hcloud configure' first, or pass --project-id explicitly.")
        sys.exit(1)
    print(f"[INFO] Region: {REGION}")
    print(f"[INFO] Project ID: {PROJECT_ID}")

    if args.clean_artifacts and os.path.exists(ARTIFACTS_DIR):
        shutil.rmtree(ARTIFACTS_DIR)
        print(f"[INFO] Cleaned artifacts directory: {ARTIFACTS_DIR}")

    if not os.path.exists(args.demand_file):
        print(f"[ERROR] Demand file not found: {args.demand_file}")
        sys.exit(1)

    if args.data_file and not os.path.exists(args.data_file):
        print(f"[ERROR] Data file not found: {args.data_file}")
        sys.exit(1)

    run_workflow(
        demand_file_path=args.demand_file,
        data_file_path=args.data_file,
        publish_name=args.publish_name,
        publish_description=args.publish_description,
        auto_confirm=args.auto_confirm,
        deploy=args.deploy,
        test_call=args.test,
    )


if __name__ == "__main__":
    main()
