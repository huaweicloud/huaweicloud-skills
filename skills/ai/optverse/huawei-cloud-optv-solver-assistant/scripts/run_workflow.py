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
  IAM credentials are read from ~/.config/optverse/credentials (values cleared
  after reading, never displayed). The IAM token is obtained via
  `hcloud IAM KeystoneCreateUserTokenByPassword` (shared with create_chat.py)
  and cached in-memory / temp file (23h validity). No interactive input.
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3

from create_chat import _ensure_credentials_file, get_iam_token, get_project_id

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _redact(text, limit=500):
    """Redact sensitive values (tokens, passwords, signed URLs) before logging.

    Shared sanitizer for every path that prints CLI/HTTP output, so IAM
    tokens, passwords and signed URLs never surface in logs.
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

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        print(f"[WARN] Failed to reconfigure console encoding", file=sys.stderr)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_REGION = "cn-north-7"
REGION = DEFAULT_REGION
PROJECT_ID = ""
ENDPOINT = f"optverse.{REGION}.myhuaweicloud.com"


HCLOUD = shutil.which("hcloud") or os.environ.get("HCLOUD_PATH", "hcloud")

# Artifacts directory: sibling of scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(SCRIPT_DIR, "..", "artifacts")


# ---------------------------------------------------------------------------
# IAM Token (via hcloud CLI, credentials from ~/.config/optverse/credentials)
# ---------------------------------------------------------------------------


def get_token():
    """Get IAM token via the hcloud CLI (reads ~/.config/optverse/credentials).

    Delegates to create_chat.get_iam_token() so both scripts share the same
    authentication path: credentials file (read + cleared in-process) and
    `hcloud IAM KeystoneCreateUserTokenByPassword`. No interactive input.

    SECURITY: The returned token must never be printed, logged, or shown
    to the user by any calling code.
    """
    return get_iam_token(REGION)


# ---------------------------------------------------------------------------
# OptVerse API Helpers
# ---------------------------------------------------------------------------


def upload_file(route_id, file_path, filename, agent_type="optverse",
                domain_type="optverse", chat_id=None):
    """UploadFile via hcloud CLI → returns chat_id.

    For Step 1 (initial upload), chat_id should be None — a new chat session
    is created and its ID is returned.

    For Step 6+ (uploading data file to an existing chat), chat_id MUST be
    passed to associate the file with the ongoing conversation. Without it,
    the file is uploaded to a new chat context and the decision engine
    cannot access it, resulting in empty data check results.

    domain_type="optverse" is REQUIRED for the solver assistant — the
    decision engine uses it to route the upload to the correct agent domain
    (hcloud accepts `--domain_type`, default optverse).
    """
    args = [HCLOUD, "OptVerse", "UploadFile",
            f"--cli-region={REGION}",
            f"--X-Chat-Route-Id={route_id}",
            f"--agent_type={agent_type}",
            f"--file={file_path}"]
    if chat_id:
        args.append(f"--chat_id={chat_id}")
    args.append(f"--domain_type={domain_type}")
    result = subprocess.run(args, capture_output=True, text=True, timeout=120,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"[ERROR] UploadFile failed (rc={result.returncode}): "
              f"{_redact(result.stderr or result.stdout, 500)}")
        return None
    try:
        data = json.loads(result.stdout)
        out_chat_id = data.get("chat_id") or data.get("id")
    except Exception:
        out_chat_id = None
    print(f"  [UploadFile] {filename} → chat_id={out_chat_id}")
    return out_chat_id


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
        print(f"[ERROR] createChat failed: {resp.status_code} {_redact(resp.text, 500)}")
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
                    print(f"  [WARN] Failed to parse SSE content as JSON", file=sys.stderr)
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
            print(f"  [WARN] Failed to decode base64 content for {filename}", file=sys.stderr)
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
    print(f"  [CreateModelService] stdout: {_redact(result.stdout, 500)}")
    if result.stderr:
        print(f"  [CreateModelService] stderr: {_redact(result.stderr, 500)}")
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
    print(f"  [CreateModelServiceTask] stdout: {_redact(result.stdout, 500)}")
    if result.stderr:
        print(f"  [CreateModelServiceTask] stderr: {_redact(result.stderr, 500)}")
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


def _extract_download_urls(data):
    """Recursively collect http(s) download URLs from the task response.

    Skips URLs belonging to the OptVerse API domain (ENDPOINT) — those are
    API endpoints, not OBS result links. OBS result links are directly
    fetchable (signed/unsigned) without extra auth.
    """
    exclude = (ENDPOINT.lower(), "iam.")
    urls = []

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str) and obj.startswith(("http://", "https://")):
            low = obj.lower()
            if not any(x in low for x in exclude):
                urls.append(obj)

    walk(data)
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_obs_results(task_detail, dest_dir=None):
    """Download result files from OBS URLs found in the ShowModelServiceTask response.

    Returns list of saved paths (empty if no URLs found or all failed).
    """
    from urllib.parse import unquote, urlparse

    dest_dir = dest_dir or ARTIFACTS_DIR
    os.makedirs(dest_dir, exist_ok=True)
    urls = _extract_download_urls(task_detail)
    saved = []
    for i, url in enumerate(urls, 1):
        try:
            resp = requests.get(
                url, verify=False, timeout=120,
                proxies={"http": None, "https": None},
            )
            if resp.status_code != 200:
                print(f"  [OBS Download] {urlparse(url).netloc} → ERROR {resp.status_code}")
                continue
            name = unquote(os.path.basename(urlparse(url).path)) or f"result_{i}"
            save_path = os.path.join(dest_dir, name)
            base, ext = os.path.splitext(name)
            j = 2
            while os.path.exists(save_path):
                save_path = os.path.join(dest_dir, f"{base}_{j}{ext}")
                j += 1
            with open(save_path, "wb") as f:
                f.write(resp.content)
            print(f"  [OBS Download] {name} → {save_path} ({len(resp.content)} bytes)")
            saved.append(save_path)
        except Exception as e:
            print(f"  [OBS Download] {urlparse(url).netloc} → ERROR {_redact(str(e), 300)}", file=sys.stderr)
    return saved


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
    chat_id = upload_file(route_id, demand_file_path, demand_filename)
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
    upload_file(route_id, data_file_path, data_filename, chat_id=chat_id)
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
            # Poll until terminal status (PENDING/RUNNING → SUCCEEDED/FAILED)
            status = str(task_detail.get("status", ""))
            attempts = 0
            while status in ("PENDING", "RUNNING", "QUEUED") and attempts < 24:
                time.sleep(5)
                attempts += 1
                task_detail = show_model_service_task(service_id, task_id)
                if not task_detail:
                    break
                status = str(task_detail.get("status", ""))
                print(f"  Status: {status} (waiting... {attempts * 5}s)")
                if status in ("SUCCEEDED", "SUCCESS", "FAILED"):
                    break
            if status in ("SUCCEEDED", "SUCCESS"):
                print(f"  Status: {status}")
                saved = download_obs_results(task_detail)
                if saved:
                    print(f"  ✅ Downloaded {len(saved)} result file(s) to {ARTIFACTS_DIR}")
                else:
                    print("  [WARN] No OBS download URLs found in task response.")
            else:
                print(f"  [WARN] Task status is {status}; result files not downloaded.")
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

    # Ensure the credentials template exists (user only fills in the values)
    _ensure_credentials_file()

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
