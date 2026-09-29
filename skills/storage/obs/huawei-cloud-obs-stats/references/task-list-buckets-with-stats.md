# Task 1: List Buckets with Capacity and Object Counts

> **⚠️ Important: region must be provided by the user**
> When querying the bucket list, `--region` must be explicitly provided by the user. Guessing the region is prohibited.

> **⚠️ Critical: hcloud OBS module does not have a ListAllMyBucketsType command**
>
> In practice, the hcloud CLI (tested with v7.2.2) OBS module **does not include** the `ListAllMyBucketsType` command. You must use obsutil to list buckets:
> ```bash
> hcloud obs ls
> ```
> You can filter buckets by region using grep:
> ```bash
> hcloud obs ls 2>&1 | grep "cn-south-1"
> ```

**Step 1: List all buckets (using obsutil)**

```bash
hcloud obs ls
```

**Step 2: Query bucket capacity and object count (via CES metrics)**

Query bucket capacity via CES `capacity_total` and object count via CES `object_num_all`. Both use `--filter=average` and read `datapoints[-1].average`:

```bash
# Bucket capacity (Bytes)
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<TodayMidnightTimestamp(ms)> \
  --to=<CurrentTimestamp(ms)>

# Bucket object count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=object_num_all \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<TodayMidnightTimestamp(ms)> \
  --to=<CurrentTimestamp(ms)>
```

> **⚠️ Both metrics use `filter=average`** (to get the latest sampled value), not `filter=sum`.
> The returned `datapoints[-1].average` is the current bucket capacity (Bytes) / object count.
> CES collects these metrics every 30 minutes.

> **⚠️ Do not use `GetBucketStorageInfo`**
>
> The hcloud OBS module does not support `GetBucketStorageInfo`. Use CES `capacity_total` and `object_num_all` metrics instead.
> Do **not** use metric names `standard_object_count` / `cold_object_count` — they do not exist in CES; the correct names follow the `object_num_*` pattern (e.g., `object_num_all`, `object_num_standard`).

**Output format example:**

```
Bucket              Capacity(GB)  Object Count
my-bucket-1         125.3         1024
my-bucket-2         0.5           15
my-bucket-3         2048.0        50000
```

> **⚠️ Note: Unrestored archived objects may not be counted**
>
> Objects in the Archive / Deep Archive storage class must be restored before access; unrestored objects may be excluded from CES capacity and object count metrics. If a bucket contains archived objects, the reported values may be lower than the actual totals.

> **💡 Best Practice: Fast Top-N Bucket Capacity Query**
>
> To find the top N buckets by capacity:
> 1. `hcloud obs ls` to list all bucket names in the target region
> 2. Query CES `capacity_total` metric per bucket to get capacity
> 3. Sort by capacity descending and take the top N
>
> This approach is significantly faster than calling a per-bucket REST API for each bucket.
