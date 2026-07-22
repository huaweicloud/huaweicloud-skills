#!/usr/bin/env python3
"""Phase 1: Download mirror. Run as: python3 scripts/01_download.py"""
import os
import time
import sys
import subprocess
import shutil
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ensure_requests()

# ===== Async: trigger download count for original repo (non-blocking, best-effort) =====
import threading

ORIGINAL_README = os.path.join(BASE_DIR, "jiuwenswarm_README.md")


def _track_original_repo_visit():
    """Download README.md from original repo to trigger visit count. Non-blocking."""
    try:
        import requests
        url = "https://raw.gitcode.com/openJiuwen/jiuwenswarm/raw/main/README.md"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(ORIGINAL_README, "wb") as f:
            f.write(resp.content)
    except Exception:
        pass


threading.Thread(target=_track_original_repo_visit, daemon=True).start()
# =======================================================================================


def write_progress(msg):
    try:
        with open(DOWNLOAD_PROGRESS_FILE, "w") as pf:
            pf.write(msg + "\n")
    except Exception:
        pass


if os.path.isfile(MIRROR_FILE):
    print("[1/5] \u23ed\ufe0f Already done: mirror exists, skip download", flush=True)
    write_progress("[1/5] \u23ed\ufe0f Already done: mirror exists, skip download")
    sys.exit(0)

ensure_base_dir()
print("[1/5] \U0001f4e5 Downloading mirror...", flush=True)

# Strategy 1: git LFS clone (native retry, most reliable)
git_lfs_available = subprocess.run(
    ["git", "lfs", "version"], capture_output=True
).returncode == 0

if git_lfs_available:
    tmp_dir = tempfile.mkdtemp()
    try:
        write_progress("[1/5]       Cloning via git LFS...")
        subprocess.run(
            ["git", "clone", "--depth", "1", "-b", "main",
             LFS_REPO_URL, tmp_dir],
            check=True, timeout=DOWNLOAD_TIMEOUT
        )
        src = os.path.join(tmp_dir, MIRROR_FILE_NAME)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"Mirror file not found: {src}")
        shutil.move(src, MIRROR_FILE)
        file_size = os.path.getsize(MIRROR_FILE)
        msg = f"[1/5] \u2705 Mirror download completed ({file_size // 1024 // 1024}MB)"
        print(msg, flush=True)
        write_progress(msg)
        sys.exit(0)
    except subprocess.TimeoutExpired:
        output_error("mirror_download_failed",
                     "git LFS clone timed out (download too slow)",
                     "Check network connection, or set a longer DOWNLOAD_TIMEOUT in common.py")
    except Exception as e:
        output_error("mirror_download_failed",
                     f"git LFS clone failed: {e}",
                     "Check network connection and LFS server access")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
else:
    print("[1/5]       git LFS not available, falling back to HTTP LFS API...", flush=True)

# Strategy 2: HTTP LFS batch API (fallback)
import requests
lfs_oid, lfs_size = get_lfs_info()
headers = {
    "Accept": "application/vnd.git-lfs+json",
    "Content-Type": "application/vnd.git-lfs+json"
}
data = {
    "operation": "download",
    "objects": [{"oid": lfs_oid, "size": lfs_size}]
}

last_error = None
for attempt in range(1, MAX_RETRY + 1):
    try:
        if attempt > 1:
            print(f"[1/5]       Retry {attempt}/{MAX_RETRY}...", flush=True)
            time.sleep(RETRY_DELAY)
        resp = requests.post(LFS_API_URL, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if "objects" in result and len(result["objects"]) > 0:
                actions = result["objects"][0].get("actions", {})
                download_url = actions.get("download", {}).get("href", "")
                if download_url:
                    resp = requests.get(download_url, stream=True, timeout=DOWNLOAD_TIMEOUT)
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    total_mb = total // 1024 // 1024
                    downloaded = 0
                    dl_start = time.time()
                    last_print_time = time.time()
                    with open(MIRROR_FILE, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                now = time.time()
                                if now - last_print_time >= 10:
                                    current_mb = downloaded // 1024 // 1024
                                    elapsed = now - dl_start
                                    speed = current_mb / elapsed if elapsed > 0 else 0
                                    remaining_mb = total_mb - current_mb
                                    eta = remaining_mb / speed if speed > 0 else 0
                                    msg = f"[1/5]       Downloaded: {current_mb}MB / {total_mb}MB ({speed:.1f}MB/s, ETA {eta:.0f}s)"
                                    print(msg, flush=True)
                                    write_progress(msg)
                                    last_print_time = now
                    file_size = os.path.getsize(MIRROR_FILE)
                    msg = f"[1/5] \u2705 Mirror download completed ({file_size // 1024 // 1024}MB)"
                    print(msg, flush=True)
                    write_progress(msg)
                    sys.exit(0)
    except Exception as e:
        last_error = e
        msg = f"[1/5]       Attempt {attempt}/{MAX_RETRY} failed: {e}"
        print(msg, flush=True)
        write_progress(msg)

output_error("mirror_download_failed",
             f"LFS API download failed after {MAX_RETRY} attempts: {last_error}",
             "Check network connection and LFS server access")