#!/usr/bin/env python3
"""Phase 1: Download mirror. Run as: python3 scripts/01_download.py"""
import os
import time
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ensure_requests()


def write_progress(msg):
    """Write progress to file for external polling."""
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

# Download via LFS API
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

try:
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
    output_error("mirror_download_failed",
                 f"LFS API download failed: {e}",
                 "Check network connection and LFS server access")

output_error("mirror_download_failed",
             "LFS API download failed",
             "Check network connection and LFS server access")