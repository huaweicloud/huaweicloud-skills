# Related APIs - Huawei Cloud OBS Object Storage Management

This document lists all CLI commands and APIs used in the OBS object storage management skill.

## Table of Contents

- [API Overview](#api-overview)
- [API Details](#api-details)
  - [1. ListBucketsWithStats - List Buckets with Capacity and Object Count](#1-listbucketswithstats---list-buckets-with-capacity-and-object-count)
  - [2. UploadFile - Upload Local File or Directory to Target Bucket](#2-uploadfile---upload-local-file-or-directory-to-target-bucket)
  - [3. ScheduledUpload - Schedule Periodic Upload of Local Directory to Target Bucket](#3-scheduledupload---schedule-periodic-upload-of-local-directory-to-target-bucket)
- [Official Documentation](#official-documentation)

---

## API Overview

| Product | CLI Command | API Operation | Description |
|---------|------------|---------------|-------------|
| OBS | `hcloud obs ls` | obsutil ls | List all buckets (obsutil mode) |
| OBS | `hcloud OBS GetBucketStorageInfo` | GetBucketStorageInfo | Get bucket storage info (capacity, object count; may not be supported by hcloud) |
| CES | `hcloud CES ShowMetricData` | ShowMetricData | Query monitoring metric data (bucket capacity) |
| OBS | `obsutil cp` | PutObject / UploadPart | Upload file/directory |

---

## API Details

### 1. ListBucketsWithStats - List Buckets with Capacity and Object Count

> **⚠️ Key: region parameter must be provided by the user**
>
> The `--region` parameter **must be explicitly provided by the user**. The Agent **must not guess or use a default value**.
>
> **Pre-check steps:**
> 1. Check whether the user has provided the `--region` parameter
> 2. If region is missing, **immediately ask the user to provide it**:
>    ```
>    Please provide the OBS region, e.g., cn-north-1, cn-north-4, cn-east-2, cn-east-3, cn-south-1, etc.
>    ```
> 3. If the region is obviously invalid (empty string, pure numbers, special characters), **prompt the user**

**Step 1: List all buckets**

> **⚠️ Key: hcloud OBS module has no ListAllMyBucketsType command**
>
> hcloud CLI (v7.2.2 tested) **does not have** the `ListAllMyBucketsType` command; must use obsutil mode:

```bash
# List all buckets
hcloud obs ls

# Filter by specific region
hcloud obs ls 2>&1 | grep "cn-south-1"

# Extract bucket names
hcloud obs ls 2>&1 | awk '/obs:\/\// && /cn-south-1/ {print $1}' | sed 's|obs://||'
```

**Response key fields:**

| Field | Description |
|-------|-------------|
| `Buckets.Bucket[].Name` | Bucket name |
| `Buckets.Bucket[].Location` | Bucket region |
| `Buckets.Bucket[].CreationDate` | Bucket creation time |

**Step 2: Get capacity and object count per bucket**

> **⚠️ Key: CES capacity metric batch query recommended for higher efficiency**
>
> Calling GetBucketStorageInfo per bucket is inefficient; recommended to batch query via CES `capacity_total` metric:
> ```bash
> hcloud CES ShowMetricData \
>   --region=<RegionId> \
>   --namespace=SYS.OBS \
>   --metric_name=capacity_total \
>   --dim.0=bucket_name,<BucketName> \
>   --period=86400 \
>   --filter=average \
>   --from=<TodayMidnightTimestampMs> \
>   --to=<CurrentTimestampMs>
> ```
> The returned `datapoints[-1].average` is the bucket capacity (Bytes).

```bash
hcloud OBS GetBucketStorageInfo \
  --region=<RegionId> \
  --bucket=<BucketName>
```

**GetBucketStorageInfo response key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `size` | long | Total size of objects in the bucket (bytes) |
| `objectNumber` | int | Total number of objects in the bucket |

> **⚠️ Note: hcloud OBS module may not have GetBucketStorageInfo command**
>
> If hcloud does not support `GetBucketStorageInfo`, alternatives:
> - Query bucket info via obsutil: `obsutil ls -bucket=<BucketName> -limit=0 -s`
> - Call OBS API directly: `GET /?storageInfo` to get bucket storage info
>
> If obsutil also does not support this query, you can get it by listing all objects in the bucket and summing their sizes (poor performance, use as fallback only).

**Error handling:**
1. If "Access Denied" is reported, prompt the user to check IAM permissions or bucket policy
2. If bucket count is 0, prompt the user that no buckets exist in the current region; they may need to switch regions
3. If GetBucketStorageInfo errors, skip the bucket and mark "query failed" in the output

---

### 2. UploadFile - Upload Local File or Directory to Target Bucket

> **⚠️ Key: Upload uses obsutil, not hcloud**
>
> hcloud CLI does not support OBS object upload operations; must use obsutil.

> **Pre-check:**
> 1. Check obsutil is installed: `obsutil version`
> 2. Check obsutil credentials are configured: `obsutil ls -limit=1`
> 3. Check local path exists

**Required parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| Local path | File or directory path to upload | `/home/user/data/report.csv` |
| Target bucket name | OBS bucket name | `my-bucket` |
| Target object key (optional) | Object path within bucket | `reports/report.csv` |

**CLI commands:**

```bash
# Upload a single file
obsutil cp <LocalFilePath> obs://<BucketName>/<ObjectKey> -flat

# Upload an entire directory (ask the customer first whether to preserve structure)
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r          # customer: preserve structure
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat    # customer: flatten files

# Upload with specified concurrency (large files/many files)
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -p=10
```

> **⚠️ Key: Ask the customer first for directory uploads**
>
> When the user specifies a directory, you **must** ask whether the source directory itself should be uploaded as a directory layer to OBS (i.e., preserve directory structure) before running the command. Decide `-flat` based on the customer's explicit answer.
> - Customer "Yes" (preserve) → no `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/sub/file.txt`
> - Customer "No" (flatten) → with `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/file.txt`
> - Never default; always ask first.

**Optional parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-flat` | off | Discard local directory structure (for directory uploads, decide by asking the customer first; for single files, can be used directly) |
| `-r` | - | Recursively upload directory |
| `-p` | 5 | Concurrency |
| `-threshold` | 50MB | Multipart upload threshold |
| `-fr` | resume | Resumable upload mode |
| `-v` | off | Verbose log mode |
| `-config` | default config | Specify obsutil config file |

> **⚠️ Large file upload notes**
>
> - Single object max size: 48.8TB
> - Large files automatically use multipart upload, default part size 9MB
> - For unstable networks, reduce concurrency (`-p=3`)
> - Upload interruption supports resumable upload (enabled by default)

**Error handling:**
1. `bucket not exist`: Confirm bucket name is correct; bucket names are globally unique and must match exactly
2. `access denied`: Check obsutil credential configuration and bucket ACL/policy
3. `no such file or directory`: Confirm local path is correct
4. `network timeout`: Reduce concurrency or increase timeout

---

### 3. ScheduledUpload - Schedule Periodic Upload of Local Directory to Target Bucket

> **Based on OS-level scheduled tasks (crontab); no additional daemon process required**

**Required parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| Local directory path | Directory to upload periodically | `/home/user/data/` |
| Target bucket name | OBS bucket name | `my-bucket` |
| Target path prefix (optional) | Path prefix within bucket | `backup/` |
| Schedule period | Execution period | `hourly`, `daily at 8:00`, `*/30 * * * *` |

**Implementation steps:**

**Step 1: Create upload script**

```bash
#!/bin/bash
# OBS scheduled upload script
LOG_FILE="$HOME/obs-scheduled-upload-<BucketName>.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting scheduled upload" >> "$LOG_FILE"
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r >> "$LOG_FILE" 2>&1
RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload succeeded" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload failed, exit code: $RESULT" >> "$LOG_FILE"
fi
```

**Step 2: Set crontab (only after the user has explicitly confirmed the scheduled upload)**

> **⚠️ Confirmation & persistence warning**
>
> - Adding a crontab entry installs a **persistent scheduled task** on the host that continues to upload the local directory to the cloud after the current session ends.
> - **Only write the crontab entry after the user has explicitly confirmed** the local directory, target bucket/prefix, and schedule period.
> - Tell the user how to remove the task later (see "Managing scheduled tasks" below).

| Period description | Crontab expression |
|-------------------|-------------------|
| Every 30 minutes | `*/30 * * * *` |
| Every hour | `0 * * * *` |
| Daily at 8:00 | `0 8 * * *` |
| Monday at 0:00 | `0 0 * * 1` |
| 1st of month at 0:00 | `0 0 1 * *` |

```bash
# Add crontab task (must be explicitly confirmed by the user before running)
(crontab -l 2>/dev/null; echo "<CronExpr> /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -
```

**Step 3: Verify**

```bash
crontab -l
```

> **⚠️ Crontab environment notes**
>
> - Crontab has a minimal PATH environment variable; use the full path to obsutil in the script
> - Recommend adding at the top of the script: `export PATH=/usr/local/bin:$PATH`
> - Confirm the obsutil AK/SK config file path is accessible in the crontab environment

**Managing scheduled tasks:**

```bash
# List all scheduled tasks
crontab -l

# Remove a specific scheduled task (run only after the user confirms removal)
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -

# View upload log
tail -f $HOME/obs-scheduled-upload-<BucketName>.log
```

> **⚠️ `crontab -r` clears ALL scheduled tasks and is never used by this skill.**

---

## Official Documentation

- [OBS API Reference](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [OBS SDK Reference](https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_0100.html)
- [obsutil CLI Tool](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
