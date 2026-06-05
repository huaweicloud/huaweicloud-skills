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

**Step 2: Query bucket capacity (CES capacity metric recommended for efficiency)**

When batch-querying the capacity of multiple buckets, prefer the CES `capacity_total` metric to avoid per-bucket API calls:

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=average \
  --from=<TodayMidnightTimestamp(ms)> \
  --to=<CurrentTimestamp(ms)>
```

> **⚠️ Capacity metric uses `filter=average`** (to get the latest sampled value), not `filter=sum`.
> The returned `datapoints[-1].average` is the current bucket capacity (Bytes).

**Step 2 (Alternative): Query capacity and object count per bucket (via OBS API)**

If you need an exact object count, use `hcloud OBS GetBucketStorageInfo`:

```bash
hcloud OBS GetBucketStorageInfo \
  --region=<RegionId> \
  --bucket=<BucketName>
```

> **⚠️ Note: GetBucketStorageInfo may not be supported by hcloud**
> If it returns "No such command", use the alternative: `obsutil ls obs://<BucketName> -limit=0 -s`

**Key response fields:**

| Field | Description |
|------|------|
| `size` | Total size of objects in the bucket (bytes) |
| `objectNumber` | Total number of objects in the bucket |

**Output format example:**

```
Bucket              Capacity(GB)  Object Count
my-bucket-1         125.3         1024
my-bucket-2         0.5           15
my-bucket-3         2048.0        50000
```

> **⚠️ Note: GetBucketStorageInfo does not count unrestored archived objects**
>
> Objects in the Archive storage class must be restored before access; unrestored objects are not counted.
> If a bucket contains archived objects, the returned capacity and object count may exclude unrestored archived objects.

> **💡 Best Practice: Fast Top-N Bucket Capacity Query**
>
> To find the top N buckets by capacity:
> 1. `hcloud obs ls` to list all bucket names in the target region
> 2. Query CES `capacity_total` metric per bucket to get capacity
> 3. Sort by capacity descending and take the top N
>
> This approach is significantly faster than calling GetBucketStorageInfo for each bucket.
