> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## OBS Upload Guide 上传数据到 OBS 指南

### Contents 目录

- Overview 概述
- Measured Performance Model 实测性能模型
- Mandatory Rules 强制规则
- Concurrent Upload Template 并发上传模板
- Verification 上传验证
- Boundary Conditions 边界情况
- Relationship to 代码放 OBS、运行时挂载 Code Delivery 代码放 OBS、运行时挂载 代码交付

### Overview 概述

This skill touches OBS in two places:

1. **代码放 OBS、运行时挂载 code delivery** — upload the generated `entrypoint.py` / `src/` /
   `requirements.txt` (a handful of files) to the operator's OBS path
2. **Phase 4 Source ① data upload** — get the customer's raw dataset onto OBS so the
   skill can auto-create a dataset asset (can be **thousands of files**)

This guide is the authoritative reference for **how fast OBS uploads actually run**
and **how to upload large file sets without the multi-minute crawl** that a naive
serial upload produces.

### Measured Performance Model 实测性能模型

Measured against a regional OBS endpoint (`obs.{region}.myhuaweicloud.com`) with a 717MB / 14441-file
dataset (pika-umi):

| Metric | Measured value | Implication |
|--------|----------------|-------------|
| Per-request latency (small `putFile`) | **~184 ms / request** | Upload time ≈ **file count × per-request latency** when requests cannot run in parallel |
| Single-connection bandwidth (50MB multipart, 8 segments) | **~9.2 MB/s** | Bandwidth is **NOT** the bottleneck for small files |
| Single-process concurrency ceiling | ~6.5 req/s (8 and 32 threads give the same rate) | The client/endpoint throttles requests per process — adding threads alone does NOT help |
| **Multi-process sharding** (4 procs × 16 threads) | **~25 req/s (4× speedup)** | Sharding across processes breaks the per-process ceiling |

**Rule of thumb:** upload wall-time ≈ `file_count / total_req_s`. A serial upload of
14441 files takes ~44 min; the sharded 4×16 approach finished the same set in
~10 min.

### Mandatory Rules 强制规则

1. **Never serial-upload a large dataset with `OBSClient.upload_folder`** — it walks
   files one by one (~184ms per request). Fine for a handful of code files
   (代码放 OBS、运行时挂载), **unacceptable** for large datasets (Phase 4 Source ①).
   Threshold: **> 50 files or > 50MB → use the concurrent approach below.**
   **The default tool is `../../scripts/concurrent_shard_upload.py` — copy it to the
   target host, edit its CONFIG (`SERVER`/`BUCKET`/`PREFIX`/`SRC`), and run it as the
   script's Usage block describes. Do NOT hand-roll a new concurrent implementation,
   do NOT fall back to a serial `upload_folder` walk, and do NOT substitute another
   tool (e.g. `obsutil`) unless the customer explicitly chooses one.**
2. **Before uploading, size the job first:** `du -sh <dir>` and
   `find <dir> -type f | wc -l` — this tells you the expected wall-time
   (`file_count / 25` seconds) and whether to warn the customer about the duration.
3. **Small files (`< 10MB`) → `putFile` from multiple threads.** One request per file.
4. **Large files (`≥ 10MB`) → `uploadFile` multipart** (`partSize=10MB, taskNum=8`),
   which parallelizes segments and reaches ~9MB/s per object.
5. **Shard across processes, not just threads** — each process gets its own
   `ObsClient` and its own share of files (`index % N` round-robin). 4 processes ×
   16 threads is the tested sweet spot; do not exceed ~8 processes.
6. **Never run two uploaders against the same target prefix at the same time** —
   they fight over bandwidth and produce `*.upload_record`/`*.upload_tmp` leftovers.
   Check `ps aux | grep -i upload` first; stop the competing job (after user
   confirmation) before starting a new one.
7. **Filter transient files when collecting** — skip `*.upload_record`,
   `*.upload_tmp`, `*.tmp`, and other OBS-SDK byproducts before counting/uploading.
8. **Verify after upload** — count objects under the target prefix with
   `listObjects` (paged) and compare with the local file count; spot-check sizes.
   A 0-byte `.../uploadTest/` directory placeholder object is normal.

### Concurrent Upload Template 并发上传模板

**The skill uploads datasets (Phase 4 Source ①) by DEFAULT with
`../../scripts/concurrent_shard_upload.py`** — copy the script to the build/edge host,
edit its CONFIG block (`SERVER` / `BUCKET` / `PREFIX` / `SRC`), then launch 4 shards ×
16 threads exactly as its Usage block shows. This is the default for ANY dataset
upload > 50 files / > 50MB; only a customer's explicit alternative choice overrides it.

The script (round-robin sharding, `putFile`/`uploadFile` split at 10MB,
transient-file filtering, progress heartbeat) runs on the build/edge host with
`esdk-obs-python`. Fall back to `cloudrobo_core.sdk.obs_client.OBSClient` only when
the third-party SDK is absent — but then replicate the same sharding logic verbatim
from the script, never a plain serial walk.

```bash
# 1. Size the job & pick the endpoint (default may NXDOMAIN on some networks):
du -sh <data-dir>; find <data-dir> -type f | wc -l
#    reachable endpoint example: https://obs.<region>.myhuaweicloud.com
```

```bash
# 2. Launch shards in the background (4 procs × 16 threads ≈ 25 req/s, tested):
#    edit CONFIG at the top of scripts/concurrent_shard_upload.py first
#    (SERVER / BUCKET / PREFIX / SRC)
export HUAWEI_CLOUD_AK=<ak> HUAWEI_CLOUD_SK=<sk>
for k in 0 1 2 3; do
  nohup python3 scripts/concurrent_shard_upload.py --threads 16 \
    --slice-index "$k" --slice-total 4 > /tmp/obs_up_$k.log 2>&1 &
done
```

```bash
# 3. Verify (rule 8): count objects under the prefix, compare with local count
#    `find <data-dir> -type f | wc -l` — expect the same number (+0-byte dir placeholder).
```

### Verification 上传验证

- **Count parity:** paged `listObjects(prefix=<PREFIX>, marker=..., max_keys=1000)`
  total == local file count (a single 0-byte `<PREFIX>/` placeholder is expected)
- **Spot-check:** compare a few object sizes with `os.path.getsize` of the source
  files
- **Readiness check (代码放 OBS、运行时挂载 / dataset):** confirm `entrypoint.py`/`src/...`/`requirements.txt`
  (code) or the raw data files are present before creating the proc-task — an empty
  path keeps the task in `POD_PENDING`

### Boundary Conditions 边界情况

| Situation | Handling |
|-----------|----------|
| Endpoint `obs.{region}.myhuaweicloud.com` NXDOMAIN | Ask the customer for a reachable endpoint (e.g. `obs.cn-southwest-2.myhuaweicloud.com`) and set it before any OBS call |
| Another uploader running against the same prefix | Check `ps aux | grep -i upload`; **ask the user to stop it first** (competing jobs fight for bandwidth and leave `*.upload_record` files) |
| `*.upload_record` / `*.upload_tmp` leftovers inside the data dir | Filter them when collecting (rule 7); remove stale ones (`find <dir> -name '*.upload_record' -delete`) |
| Interrupted upload | Re-running is idempotent for the same keys (`putFile`/`uploadFile` overwrite in place); restart the shards |
| Dataset larger than ~5000 files | Expected wall-time ≥ ~3 min — inform the customer and show the progress heartbeat |
| `du -sh` / `find | wc -l` fail (path missing) | Ask the customer for the correct data path before uploading |
| Upload verification mismatch | Re-run the shards (idempotent), then re-verify; report the difference |

### Relationship to 代码放 OBS、运行时挂载 Code Delivery 代码放 OBS、运行时挂载 代码交付

代码放 OBS、运行时挂载 delivery is a **small** upload (3 files + `src/`) — the serial
`OBSClient.upload_folder` / `upload_file` is fine there (idempotent overwrite into
the reused operator directory). Apply this guide's concurrent approach **only** when
the payload is large (Phase 4 Source ① datasets, or a customer data set with
> 50 files / > 50MB).

---