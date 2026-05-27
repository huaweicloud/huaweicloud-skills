# Troubleshooting - Huawei Cloud OBS Object Storage Management

## Table of Contents

- [hcloud CLI Issues](#hcloud-cli-issues)
- [obsutil Upload Issues](#obsutil-upload-issues)
- [CES Monitoring Data Issues](#ces-monitoring-data-issues)
- [Scheduled Upload Issues](#scheduled-upload-issues)
- [Bucket Capacity Query Issues](#bucket-capacity-query-issues)
- [Month-over-Month Calculation Issues](#month-over-month-calculation-issues)

---

## hcloud CLI Issues

### 1. hcloud OBS module has no ListAllMyBucketsType command

**Problem:**
Running `hcloud OBS ListAllMyBucketsType` returns `Error: No such command: "ListAllMyBucketsType"`.

**Root cause:**
hcloud CLI (v7.2.2 tested) OBS module **does not include** the `ListAllMyBucketsType` command. The hcloud OBS module only provides a limited set of bucket management operations; listing buckets requires the obsutil mode.

**Solution:**
```bash
# List all buckets
hcloud obs ls

# Filter buckets in a specific region
hcloud obs ls 2>&1 | grep "cn-south-1"

# Extract bucket name list
hcloud obs ls 2>&1 | awk '/obs:\/\// && /cn-south-1/ {print $1}' | sed 's|obs://||'
```

### 2. hcloud OBS module has no GetBucketStorageInfo command

**Problem:**
Running `hcloud OBS GetBucketStorageInfo` returns command not found.

**Root cause:**
The hcloud CLI OBS module may not include all OBS API operations; `GetBucketStorageInfo` is a bucket extension API not supported by some hcloud versions.

**Solution:**

**Method 1: Use CES capacity metric (recommended for batch queries)**
```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<TodayMidnightTimestampMs> \
  --to=<CurrentTimestampMs>
```
The returned `datapoints[-1].average` is the bucket capacity (Bytes).

**Method 2: Use obsutil as alternative**
```bash
# Use obsutil to list objects and get statistics
obsutil ls obs://<BucketName> -limit=0 -s
```

**Method 3: Use OBS REST API directly**
```bash
# Call OBS REST API via curl to get bucket storage info
# GET /?storageInfo
curl -X GET "https://<BucketName>.obs.<RegionId>.myhuaweicloud.com/?storageInfo" \
  -H "Date: $(date -u '+%a, %d %b %Y %H:%M:%S GMT')" \
  -H "Authorization: OBS <Signature>"
```

**Method 4: Use OBS SDK**
```python
from obs import ObsClient

obs_client = ObsClient(...)
resp = obs_client.getBucketStorageInfo(bucketName)
print(f"Size: {resp.body.size}, Objects: {resp.body.objectNumber}")
```

### 2. hcloud CES ShowMetricData parameter format issue

**Problem:**
CES ShowMetricData dimensions parameter format is incorrect.

**Correct format:**
```bash
--dimensions.0.name=bucket_name \
--dimensions.0.value=my-bucket
```

**Common errors:**
```bash
# ❌ Incorrect: dimensions index starts from 1
--dimensions.1.name=bucket_name

# ❌ Incorrect: dimension name is incorrect
--dimensions.0.name=bucket

# ❌ Incorrect: missing index
--dimensions.name=bucket_name
```

> **hcloud CES parameter index starts from 0**, not from 1.

### 3. hcloud credential configuration issues

| Error message | Cause | Solution |
|--------------|-------|----------|
| `No valid credential` | AK/SK not configured | Run `hcloud configure` |
| `Access denied` | AK/SK invalid or expired | Reconfigure credentials |
| `Invalid region` | Region ID incorrect | Use the correct region ID |
| `Please set ak, sk and endpoint` | obsutil credentials not configured | Run `hcloud obs config -i=<AK> -k=<SK> -e=obs.<region>.myhuaweicloud.com` |
| `InvalidAccessKeyId` | obsutil configured AK/SK is invalid | Re-run `hcloud obs config` with correct credentials |

> **⚠️ obsutil credential check process**
>
> Before any OBS operation, verify that obsutil credentials are available:
> ```bash
> hcloud obs ls -limit=1
> ```
> If the response is `Please set ak, sk and endpoint in the configuration file!` or `InvalidAccessKeyId`,
> inform the user of the following example command and have them configure it in their terminal:
>
> ```
> obsutil credentials are not configured. Please run the following command in your terminal to configure (AK/SK can be obtained from the Huawei Cloud console "My Credentials" page):
>
>   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<Region>.myhuaweicloud.com
>
> Example (Guangzhou region):
>   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.cn-south-1.myhuaweicloud.com
>
> Common Endpoints:
>   cn-north-4  → obs.cn-north-4.myhuaweicloud.com
>   cn-east-3   → obs.cn-east-3.myhuaweicloud.com
>   cn-south-1  → obs.cn-south-1.myhuaweicloud.com
>   cn-southwest-2 → obs.cn-southwest-2.myhuaweicloud.com
>
> Retry after configuration is complete.
> ```

---

## obsutil Upload Issues

### 1. Upload timeout or slow speed

**Problem:**
Upload of large files or many files times out or is very slow.

**Solution:**

```bash
# Increase concurrency
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -p=10

# Decrease concurrency (for unstable networks)
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -p=3

# Adjust part size (for large file scenarios)
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -threshold=100MB
```

### 2. Resume after upload interruption

**Problem:**
Network interruption or abnormal program exit during upload.

**Solution:**
```bash
# Use resumable upload (enabled by default)
obsutil cp <LocalPath> obs://<BucketName>/<Prefix> -r -fr

# View resumable upload records
obsutil ls -failed -limit=100
```

### 3. Upload reports "access denied"

**Problem:**
Upload returns 403 Access Denied.

**Root cause investigation:**

1. **obsutil credentials not configured or invalid**
   ```bash
   # Check if obsutil credentials are configured: run ls command; if error, not configured
   hcloud obs ls -limit=1
   ```
   
   If not configured, inform the user to run in their terminal:
   ```
   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<Region>.myhuaweicloud.com
   ```
   Example (Guangzhou region):
   ```bash
   hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.cn-south-1.myhuaweicloud.com
   ```
   > AK/SK can be obtained from the Huawei Cloud console "My Credentials" page. Do not ask the user to provide AK/SK directly in the conversation.

2. **Insufficient IAM permissions**
   - Check if IAM policy includes `obs:object:PutObject` permission

3. **Bucket policy restriction**
   - Check if bucket policy restricts upload operations
   - View via OBS console → Bucket → Access Control → Bucket Policy

4. **Bucket ACL restriction**
   - Check if bucket ACL allows the current account to upload

### 4. Upload reports "bucket not exist"

**Problem:**
Upload returns 404 Bucket Not Found.

**Root cause:**
- Bucket name typo (OBS bucket names are globally unique; must match exactly)
- Bucket region does not match the Endpoint configured in obsutil

**Solution:**
```bash
# List buckets first to confirm bucket name and region
obsutil ls -limit=100

# Confirm Endpoint configuration is correct
obsutil config -help
```

---

## CES Monitoring Data Issues

### 1. CES query returns empty data

**Problem:**
CES ShowMetricData returns an empty datapoints array.

**Possible causes and solutions:**

1. **Incorrect bucket name**
   - Confirm dimensions.0.value uses the correct bucket name

2. **No data in time range**
   - Bucket has no corresponding operations in the time period (e.g., no download traffic, no requests)
   - Try expanding the time range to verify

3. **CES data collection delay**
   - CES metric data typically has a 1-5 minute delay
   - If querying data from the last few minutes, it may not have been collected yet

4. **Incorrect namespace or metric name**
   - Confirm namespace is `SYS.OBS` (not `OBS` or `SYS.OBJECT_STORAGE`)
   - Confirm metric_name is correct (e.g., `download_bytes` not `download_flow`)

5. **period parameter mismatch**
   - Data granularity must match period
   - OBS monitoring metrics default collection period is 5 minutes
   - For long-term queries, set period to 86400 (1 day)

### 2. CES ShowMetricData parameter format errors

**Key parameter reference:**

| Parameter | Correct Value | Common Error |
|-----------|--------------|-------------|
| `--namespace` | `SYS.OBS` | `OBS`, `SYS.OBJECT_STORAGE` |
| `--metric_name` | `download_bytes` | `downloadBytes`, `download_flow` |
| `--dimensions.0.name` | `bucket_name` | `bucket`, `bucketName` |
| `--period` | `86400` | `86400000` (milliseconds instead of seconds) |
| `--filter` | `sum` | `SUM`, `total` |
| `--from`/`--to` | Millisecond timestamp (13 digits) | Second timestamp (10 digits) |

### 3. CES ShowMetricData does not support --User-Agent parameter

**Problem:**
Running `hcloud CES ShowMetricData --User-Agent=xxx` returns error `[USE_ERROR]Invalid parameter:User-Agent`.

**Root cause:**
The CES module's ShowMetricData command **does not support** the `--User-Agent` parameter. This parameter is only available in some OBS module commands.

**Solution:**
CES query commands **must not append** the `--User-Agent` parameter.

### 4. Month-over-month with last month data being 0

**Problem:**
Last month traffic or request data is 0, making MoM calculation impossible.

**Possible causes:**
- Bucket was just created last month with no operation data
- CES monitoring was not enabled or data collection did not cover last month
- Time range calculation error

**Handling:**
- Last month=0 and current month>0: Display "New (last month was 0)"
- Last month=0 and current month=0: Display "N/A"

---

## Scheduled Upload Issues

### 1. Crontab scheduled task not executing

**Problem:**
Crontab is set but the upload script does not execute on schedule.

**Troubleshooting steps:**

1. **Check if crontab is set successfully**
   ```bash
   crontab -l
   ```

2. **Check if cron service is running**
   ```bash
   # Linux
   systemctl status cron
   # macOS
   sudo launchctl list | grep cron
   ```

3. **Check script execution permissions**
   ```bash
   ls -la $HOME/obs-scheduled-upload-<BucketName>.sh
   chmod +x $HOME/obs-scheduled-upload-<BucketName>.sh
   ```

4. **Check PATH environment variable**
   ```bash
   # Crontab has minimal PATH; add to script
   # Add at the top of the script:
   export PATH=/usr/local/bin:/usr/bin:/bin:$PATH
   ```

5. **View upload log**
   ```bash
   tail -f $HOME/obs-scheduled-upload-<BucketName>.log
   ```

### 2. Crontab executes but upload fails

**Problem:**
Crontab log shows execution but obsutil upload errors.

**Common causes:**
- obsutil credential file inaccessible in crontab environment
- Network issues
- Insufficient disk space

**Solution:**
```bash
# Use full path to obsutil in the upload script
/usr/local/bin/obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r

# Specify obsutil config file path
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -config=/home/user/.obsutilconfig
```

### 3. Delete scheduled task

```bash
# Delete a specific OBS upload scheduled task
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -

# Clear all scheduled tasks (use with caution!)
# crontab -r
```

---

## Bucket Capacity Query Issues

### 1. Archived bucket capacity display is incomplete

**Problem:**
GetBucketStorageInfo returns capacity and object count less than actual values.

**Root cause:**
Archived storage class objects need to be restored before they can be accessed; unrestored objects are not counted.

**Solution:**
- Archived objects must be restored (RestoreObject) before they can be counted
- For accurate archived object statistics, use CES monitoring metrics `cold_storage_bytes` / `cold_object_count`

### 2. GetBucketStorageInfo performance issues

**Problem:**
Querying capacity for buckets with large numbers of objects (millions+) takes a long time.

**Solution:**
- Use CES monitoring metrics `standard_storage_bytes` / `standard_object_count` as an alternative (slightly less real-time but better performance)
- Set query timeout and retry

---

## Month-over-Month Calculation Issues

### 1. Time range calculation errors

**Correct calculation method:**

```bash
# Current month start time
current_month_start = "$(date +%Y-%m-01)"  # e.g., 2026-05-01
# Convert to millisecond timestamp
from_timestamp = $(date -d "$current_month_start" +%s)000  # e.g., 1746057600000

# Current month end time (current time)
to_timestamp = $(date +%s)000

# Last month start time
last_month_start = "$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-01)"

# Last month end time (last day of previous month 23:59:59)
last_month_end = "$(date -d "$(date +%Y-%m-01) -1 second" +%Y-%m-%dT23:59:59)"
```

### 2. Traffic unit conversion

```
Bytes → KB: / 1024
Bytes → MB: / (1024 * 1024)
Bytes → GB: / (1024 * 1024 * 1024)
Bytes → TB: / (1024 * 1024 * 1024 * 1024)
```

**Recommendation:** Choose an appropriate display unit based on traffic size:
- < 1 MB → Display KB
- < 1 GB → Display MB
- < 1 TB → Display GB
- >= 1 TB → Display TB

---

## Official Documentation

- [obsutil Troubleshooting](https://support.huaweicloud.com/utiltg-obs/obs_11_0006.html)
- [OBS Error Codes Reference](https://support.huaweicloud.com/api-obs/obs_04_0115.html)
