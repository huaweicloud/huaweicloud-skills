# Related APIs - Huawei Cloud OBS Object Storage Management

This document lists all CLI commands and APIs used in the OBS object storage management skill.

## Table of Contents

- [API Overview](#api-overview)
- [API Details](#api-details)
  - [1. ListBucketsWithStats - List Buckets with Capacity and Object Count](#1-listbucketswithstats---list-buckets-with-capacity-and-object-count)
  - [2. UploadFile - Upload Local File or Directory to Target Bucket](#2-uploadfile---upload-local-file-or-directory-to-target-bucket)
  - [3. ScheduledUpload - Schedule Periodic Upload of Local Directory to Target Bucket](#3-scheduledupload---schedule-periodic-upload-of-local-directory-to-target-bucket)
  - [4. GetMonthlyTraffic - Query Monthly External/Internal Download Traffic](#4-getmonthlytraffic---query-monthly-externalinternal-download-traffic)
  - [5. GetMonthlyRequests - Query Monthly Total Request Count](#5-getmonthlyrequests---query-monthly-total-request-count)
- [Month-over-Month Calculation](#month-over-month-calculation)
- [Official Documentation](#official-documentation)

---

## API Overview

| Product | CLI Command | API Operation | Description |
|---------|------------|---------------|-------------|
| OBS | `hcloud obs ls` | obsutil ls | List all buckets (obsutil mode) |
| OBS | `hcloud OBS GetBucketStorageInfo` | GetBucketStorageInfo | Get bucket storage info (capacity, object count; may not be supported by hcloud) |
| CES | `hcloud CES ShowMetricData` | ShowMetricData | Query monitoring metric data (traffic, request count, capacity) |
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

# Upload an entire directory (preserves directory structure by default)
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r

# Upload with specified concurrency (large files/many files)
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -p=10
```

> **⚠️ Key: Do NOT use `-flat` for directory uploads by default**
>
> When the user specifies a directory, the entire directory should be uploaded as-is (preserving structure).
> Only add `-flat` if the user **explicitly requests** flattening.
> - Without `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/sub/file.txt` (structure preserved)
> - With `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/file.txt` (structure lost)

**Optional parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-flat` | off | Discard local directory structure (only use for single files or if user explicitly requests) |
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

**Step 2: Set crontab**

| Period description | Crontab expression |
|-------------------|-------------------|
| Every 30 minutes | `*/30 * * * *` |
| Every hour | `0 * * * *` |
| Daily at 8:00 | `0 8 * * *` |
| Monday at 0:00 | `0 0 * * 1` |
| 1st of month at 0:00 | `0 0 1 * *` |

```bash
# Add crontab task
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

# Remove a specific scheduled task
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -

# View upload log
tail -f $HOME/obs-scheduled-upload-<BucketName>.log
```

---

### 4. GetMonthlyTraffic - Query Monthly External/Internal Download Traffic

> **⚠️ Key: Traffic data is obtained via CES, not directly from OBS API**
>
> The OBS service itself does not provide traffic statistics APIs; traffic data is collected by CES (Cloud Eye Service).

**Required parameters:**

| Parameter | hcloud parameter | Description | Example |
|-----------|-----------------|-------------|---------|
| Region | `--region` | Bucket region | `cn-south-1` |
| Bucket name | `--dim.0` | Dimension `bucket_name,<BucketName>` | `bucket_name,my-bucket` |

**Time range calculation:**

> **⚠️ Key: Time range must precisely match the user's expression**
>
> | User expression | Time range | Description |
> |----------------|-----------|-------------|
> | "This month" | 1st of current month 00:00:00 ~ current time | Calendar month |
> | "Last month" / "Last 30 days" | Current time - 30 days ~ current time | Rolling 30-day window |
> | "Previous month" | 1st of previous month 00:00:00 ~ last day of previous month 23:59:59 | Previous calendar month |
> | Specific date range | User-specified start and end times | e.g., "May 1 to May 19" |
>
> **"This month" ≠ "Last month"**: "This month" starts from the 1st of the current month; "Last month" goes back 30 days from the current time.
> Huawei Cloud OBS console defaults to "Last 30 days".

**Month-over-month comparison period calculation:**

| Query period | Comparison period |
|-------------|------------------|
| This month (calendar month) | Previous month (previous calendar month) |
| Last 30 days | 30 days prior (days 31-60) |
| Specific date range | Previous equal-length period |

```
# This month
Start: 1st of current month 00:00:00 → Unix timestamp (ms)
End: Current time → Unix timestamp (ms)

# Last 30 days
Start: Current time - 30 days → Unix timestamp (ms)
End: Current time → Unix timestamp (ms)

# Previous month (comparison period)
Start: 1st of previous month 00:00:00 → Unix timestamp (ms)
End: Last day of previous month 23:59:59 → Unix timestamp (ms)
```

**CLI commands:**

> **⚠️ CES ShowMetricData does not support --User-Agent parameter; do not append it**

```bash
# Query this month's external download traffic
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query this month's internal download traffic
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_intranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>
```

**CES ShowMetricData parameter description:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--namespace` | Yes | Fixed value `SYS.OBS` |
| `--metric_name` | Yes | Metric name |
| `--dim.0` | Yes | Dimension, format `bucket_name,<BucketName>` |
| `--period` | Yes | Aggregation period, `86400` (1 day) |
| `--filter` | Yes | Aggregation method, `sum` (sum) |
| `--from` | Yes | Start time (millisecond timestamp) |
| `--to` | Yes | End time (millisecond timestamp) |

**Response key fields:**

| Field | Description |
|-------|-------------|
| `datapoints[].average` | Average value within the aggregation period |
| `datapoints[].sum` | Sum value within the aggregation period |
| `datapoints[].timestamp` | Data point timestamp |

> **⚠️ Key: Must use traffic metrics, not bandwidth metrics**
>
> - ✅ `download_traffic_extranet`: External download traffic (unit: Bytes, cumulative)
> - ✅ `download_traffic_intranet`: Internal download traffic (unit: Bytes, cumulative)
> - ❌ `download_bytes`: Total download bandwidth (unit: Bytes/s, rate, not cumulative)
> - ❌ `download_bytes_extranet`/`download_bytes_intranet`: Bandwidth metrics (rate values)
>
> Use `filter=sum` to get total traffic within the time range; summing traffic metrics directly gives total bytes.
> Results need to be converted to appropriate units: `GB = bytes / (1024^3)`, `MB = bytes / (1024^2)`, `KB = bytes / 1024`

---

### 5. GetMonthlyRequests - Query Monthly Total Request Count

> **⚠️ Key: Request data is obtained via CES, not directly from OBS API**

**Required parameters:** Same as GetMonthlyTraffic

**CLI commands:**

```bash
# Query this month's total request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query this month's GET request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query this month's PUT request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>
```

> **⚠️ Note: OBS request billing relevance**
>
> - GET-type requests (GetObject, HeadObject, ListObjects, etc.)
> - PUT-type requests (PutObject, CopyObject, CreateMultipartUpload, etc.)
> - Different request types have different billing rates; see OBS pricing page for details

---

## Month-over-Month Calculation

**Formula:**

```
MoM (%) = (Current Month Value - Last Month Value) / Last Month Value × 100%
```

**Special cases:**

| Case | Handling |
|------|---------|
| Last month value = 0, current month value > 0 | Display "New (last month was 0)" |
| Last month value = 0, current month value = 0 | Display "N/A" |
| Last month value > 0 | Calculate MoM percentage, rounded to 2 decimal places |

**Example:**

```
Current month external download traffic = 125.3 GB
Last month external download traffic = 98.7 GB
MoM = (125.3 - 98.7) / 98.7 × 100% = +26.95%
```

---

## Official Documentation

- [OBS API Reference](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [OBS SDK Reference](https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_0100.html)
- [obsutil CLI Tool](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
