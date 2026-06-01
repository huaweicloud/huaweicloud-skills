# Related APIs - Huawei Cloud OBS Object Storage Statistics

This document lists all CLI commands and APIs used in the OBS object storage statistics skill.

## Table of Contents

- [API Overview](#api-overview)
- [API Details](#api-details)
  - [1. ListBucketsWithStats - List Buckets with Capacity and Object Count](#1-listbucketswithstats---list-buckets-with-capacity-and-object-count)
  - [2. GetTraffic - Query Extranet/Intranet Download Traffic](#2-gettraffic---query-extranetintranet-download-traffic)
  - [3. GetRequests - Query Total Request Count](#3-getrequests---query-total-request-count)
- [Month-over-Month Calculation](#month-over-month-calculation)
- [References](#references)

---

## API Overview

| Product | CLI Command | API Operation | Description |
|---------|------------|---------------|-------------|
| OBS | `hcloud obs ls` | obsutil ls | List all buckets (obsutil mode) |
| OBS | `hcloud OBS GetBucketStorageInfo` | GetBucketStorageInfo | Get bucket storage info (capacity, object count; may not be supported by hcloud) |
| CES | `hcloud CES ShowMetricData` | ShowMetricData | Query monitoring metric data (traffic, request count, capacity) |

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

### 2. GetTraffic - Query Extranet/Intranet Download Traffic

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
> | "Last 30 days" / "Past month" | Current time - 30 days ~ current time | Rolling 30-day window |
> | "Last month" | 1st of previous month 00:00:00 ~ last day of previous month 23:59:59 | Previous calendar month |
> | Specific date range | User-specified start and end times | e.g., "May 1 to May 19" |
>
> **"This month" ≠ "Last 30 days"**: "This month" starts from the 1st of the current month; "Last 30 days" goes back 30 days from the current time.
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
# Query this month's extranet download traffic
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query this month's intranet download traffic
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
> - ✅ `download_traffic_extranet`: Extranet download traffic (unit: Bytes, cumulative)
> - ✅ `download_traffic_intranet`: Intranet download traffic (unit: Bytes, cumulative)
> - ❌ `download_bytes`: Total download bandwidth (unit: Bytes/s, rate, not cumulative)
> - ❌ `download_bytes_extranet`/`download_bytes_intranet`: Bandwidth metrics (rate values)
>
> Use `filter=sum` to get total traffic within the time range; summing traffic metrics directly gives total bytes.
> Results need to be converted to appropriate units: `GB = bytes / (1024^3)`, `MB = bytes / (1024^2)`, `KB = bytes / 1024`

---

### 3. GetRequests - Query Total Request Count

> **⚠️ Key: Request data is obtained via CES, not directly from OBS API**

**Required parameters:** Same as GetTraffic

**CLI commands:**

> **⚠️ OBS has no single `request_count` metric; must query each request type separately and sum**

```bash
# Query GET request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query PUT request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>

# Query POST/DELETE/HEAD request counts (for a complete breakdown)
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=post_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<FromTimestamp> \
  --to=<ToTimestamp>
```

> **Total requests = GET + PUT + POST + DELETE + HEAD** (CES has no single `request_count` metric)

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
Current month extranet download traffic = 125.3 GB
Last month extranet download traffic = 98.7 GB
MoM = (125.3 - 98.7) / 98.7 × 100% = +26.95%
```

---

## References

- [OBS API Reference](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [OBS SDK Reference](https://support.huaweicloud.com/sdk-python-devg-obs/obs_22_0100.html)
- [obsutil CLI Tool](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES ShowMetricData API](https://support.huaweicloud.com/api-ces/ces_03_0059.html)
- [CES OBS Monitoring Metrics](https://support.huaweicloud.com/usermanual-ces/ces_03_0065.html)
