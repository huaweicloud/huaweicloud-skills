# Troubleshooting - Huawei Cloud OBS Object Storage Statistics

## Table of Contents

- [hcloud CLI Issues](#hcloud-cli-issues)
- [CES Monitoring Data Issues](#ces-monitoring-data-issues)
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

### 3. hcloud CES ShowMetricData parameter format issue

**Problem:**
CES ShowMetricData dimensions parameter format is incorrect.

**Correct format:**
```bash
--dim.0=bucket_name,my-bucket
```

**Common errors:**
```bash
# ❌ Incorrect: SDK format, not supported by hcloud
--dimensions.0.name=bucket_name --dimensions.0.value=my-bucket

# ❌ Incorrect: dimensions index starts from 1
--dim.1=bucket_name,my-bucket

# ❌ Incorrect: dimension key is wrong
--dim.0=bucket,my-bucket
```

> **hcloud CES uses `--dim.N=key,value` format**, with index starting from 0.

### 4. hcloud credential configuration issues

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

## CES Monitoring Data Issues

### 1. CES query returns empty data

**Problem:**
CES ShowMetricData returns an empty datapoints array.

**Possible causes and solutions:**

1. **Incorrect bucket name**
   - Confirm dim.0 uses the correct bucket name

2. **No data in time range**
   - Bucket has no corresponding operations in the time period (e.g., no download traffic, no requests)
   - Try expanding the time range to verify

3. **CES data collection delay**
   - CES metric data typically has a 1-5 minute delay
   - If querying data from the last few minutes, it may not have been collected yet

4. **Incorrect namespace or metric name**
   - Confirm namespace is `SYS.OBS` (not `OBS` or `SYS.OBJECT_STORAGE`)
   - Confirm metric_name is correct (e.g., `download_traffic_extranet` not `download_flow`)

5. **period parameter mismatch**
   - Data granularity must match period
   - OBS monitoring metrics default collection period is 5 minutes
   - For long-term queries, set period to 86400 (1 day)

### 2. CES ShowMetricData parameter format errors

**Key parameter reference:**

| Parameter | Correct Value | Common Error |
|-----------|--------------|-------------|
| `--namespace` | `SYS.OBS` | `OBS`, `SYS.OBJECT_STORAGE` |
| `--metric_name` | `download_traffic_extranet` | `downloadBytes`, `download_flow` |
| `--dim.0` | `bucket_name,my-bucket` | `bucket,my-bucket`, `bucketName,my-bucket` |
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

## References

- [obsutil Troubleshooting](https://support.huaweicloud.com/utiltg-obs/obs_11_0006.html)
- [OBS Error Codes Reference](https://support.huaweicloud.com/api-obs/obs_04_0115.html)
