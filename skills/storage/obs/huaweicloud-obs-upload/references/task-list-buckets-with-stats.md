# Task 1: List Buckets with Capacity and Object Count

> **⚠️ Important: region must be provided by the user**
> When querying the bucket list, `--region` must be explicitly provided by the user. Do not guess the region.

> **⚠️ Key: hcloud OBS module has no ListAllMyBucketsType command**
>
> Tested hcloud CLI (v7.2.2) OBS module **does not have** the `ListAllMyBucketsType` command. Listing buckets must use obsutil:
> ```bash
> hcloud obs ls
> ```
> You can filter buckets in a specific region via grep:
> ```bash
> hcloud obs ls 2>&1 | grep "cn-south-1"
> ```

**Step 1: List all buckets (using obsutil)**

```bash
hcloud obs ls
```

**Step 2: Query bucket capacity (CES capacity metric recommended, higher efficiency)**

When querying capacity for multiple buckets in batch, it is recommended to use the CES `capacity_total` metric to avoid calling the API per bucket:

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

> **⚠️ Capacity metric uses `filter=average`** (takes the latest sample value), not `filter=sum`.
> The returned `datapoints[-1].average` is the current bucket capacity (Bytes).

**Step 2 (alternative): Query capacity and object count per bucket (via OBS API)**

If exact object count is needed, you can get it via `hcloud OBS GetBucketStorageInfo`:

```bash
hcloud OBS GetBucketStorageInfo \
  --region=<RegionId> \
  --bucket=<BucketName>
```

> **⚠️ Note: GetBucketStorageInfo may not be supported by hcloud**
> If it reports "No such command", the alternative is: `obsutil ls obs://<BucketName> -limit=0 -s`

**Response key fields:**

| Field | Description |
|-------|-------------|
| `size` | Total size of objects in the bucket (bytes) |
| `objectNumber` | Total number of objects in the bucket |

**Output format example:**

```
Bucket               Capacity(GB)  Objects
my-bucket-1          125.3         1024
my-bucket-2          0.5           15
my-bucket-3          2048.0        50000
```

> **⚠️ Note: GetBucketStorageInfo does not apply to unrestored objects in archived buckets**
>
> Archived storage class objects need to be restored before they can be accessed; unrestored objects are not counted.
> If the bucket contains archived storage objects, the returned capacity and object count may not include unrestored archived objects.

> **💡 Practical tip: Quick query for top N buckets by capacity**
>
> When querying the top N buckets by capacity, the process is:
> 1. `hcloud obs ls` to list all bucket names in the target region
> 2. Call CES `capacity_total` metric per bucket to get capacity
> 3. Sort by capacity in descending order, take top N
>
> This approach is far more efficient than calling GetBucketStorageInfo API per bucket.
