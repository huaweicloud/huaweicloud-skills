#!/usr/bin/env python3
"""concurrent_shard_upload.py - concurrent sharded OBS upload for large datasets.

Default tool for uploading large datasets (> 50 files / > 50MB) to OBS. A serial
``OBSClient.upload_folder`` walk costs ~184 ms per request; sharding across
processes breaks the per-process request ceiling and reaches ~25 req/s with
4 procs x 16 threads.

Authoritative rules: references/custom-operator/custom-operator-workflow.md
section "OBS Upload Guide". Do not hand-roll a replacement - copy this script to
the build/edge host, edit the CONFIG block, and launch one shard per process.

Requirements:
    pip install esdk-obs-python          # provides the `obs` module
    export HUAWEI_CLOUD_AK=<ak> HUAWEI_CLOUD_SK=<sk>

Usage (launch one shard per process, round-robin over the file list):
    for k in 0 1 2 3; do
        nohup python3 concurrent_shard_upload.py --threads 16 \
            --slice-index "$k" --slice-total 4 > /tmp/obs_up_$k.log 2>&1 &
    done
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from obs import ObsClient
except ImportError:  # pragma: no cover
    sys.exit("esdk-obs-python not installed: pip install esdk-obs-python")

# ==== CONFIG (edit before running) =================================================
# SERVER must be reachable - the default obs.{region}.myhuaweicloud.com endpoint
# may return NXDOMAIN on some networks; ask the customer for a reachable endpoint.
SERVER = os.environ.get("OBS_SERVER", "https://obs.cn-southwest-2.myhuaweicloud.com")
BUCKET = os.environ.get("OBS_BUCKET", "<bucket>")
PREFIX = os.environ.get("OBS_PREFIX", "<prefix>")
SRC = os.environ.get("OBS_SRC", "<local-data-dir>")
# ===================================================================================

# Files >= this size use multipart uploadFile; smaller files use putFile.
MULTIPART_THRESHOLD = 10 * 1024 * 1024
PART_SIZE = 10 * 1024 * 1024
TASK_NUM = 8
# OBS-SDK transient byproducts - never upload them.
TRANSIENT_SUFFIXES = (".upload_record", ".upload_tmp", ".tmp")
HEARTBEAT_EVERY = 500


def collect_files(root: str) -> list[Path]:
    files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(TRANSIENT_SUFFIXES):
                continue
            files.append(Path(dirpath) / name)
    files.sort()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent sharded OBS upload")
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument("--slice-index", type=int, default=0)
    parser.add_argument("--slice-total", type=int, default=1)
    parser.add_argument("--server", default=SERVER)
    parser.add_argument("--bucket", default=BUCKET)
    parser.add_argument("--prefix", default=PREFIX)
    parser.add_argument("--src", default=SRC)
    args = parser.parse_args()

    if args.slice_total < 1:
        sys.exit("--slice-total must be >= 1")
    if not (0 <= args.slice_index < args.slice_total):
        sys.exit("--slice-index must be in [0, --slice-total)")

    ak = os.environ.get("HUAWEI_CLOUD_AK")
    sk = os.environ.get("HUAWEI_CLOUD_SK")
    if not ak or not sk:
        sys.exit("HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK are required")

    src = Path(args.src)
    if not src.is_dir():
        sys.exit("source directory not found: %s" % src)

    files = collect_files(str(src))
    # round-robin sharding across processes (index % N)
    shard = [f for i, f in enumerate(files) if i % args.slice_total == args.slice_index]
    total = len(shard)
    prefix = args.prefix.rstrip("/")

    if total == 0:
        print("DONE 0/0 failed=0")
        return 0

    # each process gets its own ObsClient
    client = ObsClient(access_key_id=ak, secret_access_key=sk, server=args.server)
    lock = threading.Lock()
    done = failed = 0
    start = time.time()

    def upload(path: Path) -> None:
        nonlocal done, failed
        key = "%s/%s" % (prefix, path.relative_to(src).as_posix())
        try:
            size = path.stat().st_size
            if size >= MULTIPART_THRESHOLD:
                resp = client.uploadFile(
                    args.bucket, key, str(path), partSize=PART_SIZE, taskNum=TASK_NUM
                )
            else:
                resp = client.putFile(args.bucket, key, str(path))
            if resp is not None and getattr(resp, "status", 200) >= 300:
                raise RuntimeError("status=%s" % getattr(resp, "status", "?"))
            with lock:
                done += 1
                count = done + failed
                if count % HEARTBEAT_EVERY == 0:
                    elapsed = max(time.time() - start, 1e-6)
                    print(
                        "[%s] %d/%d req/s=%.1f"
                        % (time.strftime("%H:%M:%S"), count, total, count / elapsed),
                        flush=True,
                    )
        except Exception as exc:  # noqa: BLE001
            with lock:
                failed += 1
            print("[WARN] %s: %s" % (key, exc), flush=True)

    try:
        with ThreadPoolExecutor(max_workers=args.threads) as pool:
            list(pool.map(upload, shard))
    finally:
        client.close()

    print("DONE %d/%d failed=%d" % (done, total, failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
