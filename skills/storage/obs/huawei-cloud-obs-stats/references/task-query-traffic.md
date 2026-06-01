# Task 2: Query Extranet/Intranet Download Traffic (with MoM Comparison)

> **⚠️ Critical: Traffic data is obtained via CES (Cloud Eye Service)**
>
> OBS traffic monitoring metrics are collected and managed by CES (Cloud Eye Service) and must be queried through the CES API.

> **⚠️ Important: Required parameters must be provided by the user**
> When querying traffic, `--region` and the bucket name must be explicitly provided by the user. Guessing is prohibited.

> **⚠️ Critical: Time range must precisely match the user's wording**
>
> Users may use different time expressions; you must strictly distinguish between them:
>
> | User's wording | Time range | Description |
> |---------|---------|------|
> | "this month" | 1st of current month 00:00:00 ~ now | Calendar month |
> | "last 30 days" / "past month" | now - 30 days ~ now | Rolling 30-day window |
> | "last month" | 1st of last month 00:00:00 ~ last day of last month 23:59:59 | Previous calendar month |
> | Specific date range | User-specified start and end times | e.g., "May 1 to May 19" |
>
> **⚠️ "This month" and "last 30 days" are different time ranges!**
> - "This month": starts from the 1st of the current month (e.g., May 1 ~ May 19 = 19 days)
> - "Last 30 days": 30 days before now up to now (e.g., April 19 ~ May 19 = 30 days)
> - The Huawei Cloud OBS console defaults to a "last 30 days" reporting period; if the user references console data, use the last 30 days
>
> **Month-over-month comparison period calculation:**
> - If querying "this month", the comparison period is "last month" (previous calendar month)
> - If querying "last 30 days", the comparison period is the 30 days before that (i.e., 30–60 days ago)
> - If querying a specific date range, the comparison period is the preceding equal-length window

**Step 1: Determine the time range based on the user's wording**

> **Month-over-month formula:**
> `MoM = (Current period value - Comparison period value) / Comparison period value × 100%`

**Step 2: Query extranet download traffic**

> **⚠️ CES ShowMetricData does not support the --User-Agent parameter; do not append it**

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_extranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<StartTimestamp(ms)> \
  --to=<EndTimestamp(ms)>
```

**Step 3: Query intranet download traffic**

```bash
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=download_traffic_intranet \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<StartTimestamp(ms)> \
  --to=<EndTimestamp(ms)>
```

**Step 4: Query comparison period extranet/intranet download traffic (for MoM calculation)**

Replace the time range in Steps 2 and 3 with the comparison period time range and query the extranet and intranet download traffic for that period.

**Step 5: Summary output**

```
OBS Download Traffic Report — Bucket: <BucketName>
══════════════════════════════════════════════════════════
Metric              Current Period  Previous Period  MoM Change
───────────────────────────────────────────────────────────────
Extranet Download   125.3 GB        98.7 GB          +26.95%
Intranet Download   50.2 GB         45.0 GB          +11.56%
Total Download      175.5 GB        143.7 GB         +22.13%
══════════════════════════════════════════════════════════
Period: 2026-05-01 ~ 2026-05-19
```

> **⚠️ CES ShowMetricData parameter reference**
>
> - `--namespace=SYS.OBS`: The CES namespace for OBS
> - `--dim.0=bucket_name,<BucketName>`: Dimension format is `key,value`; the OBS dimension key is `bucket_name`
> - `--period=86400`: Aggregation period of 86400 seconds (1 day), used for daily aggregation and summation
> - `--filter=sum`: Aggregation method is summation
> - `--from`/`--to`: Timestamps in millisecond-level Unix time

> **⚠️ Critical: You must use traffic metrics, not bandwidth metrics**
>
> - ✅ `download_traffic_extranet`: Extranet download traffic (unit: Bytes, cumulative)
> - ✅ `download_traffic_intranet`: Intranet download traffic (unit: Bytes, cumulative)
> - ❌ `download_bytes`: Total download bandwidth (unit: Bytes/s, rate value — not cumulative)
> - ❌ `download_bytes_extranet`/`download_bytes_intranet`: Bandwidth metrics (rate values)
>
> Traffic metrics can be summed directly to get total traffic; bandwidth metrics must be multiplied by the aggregation period to convert, which is error-prone. **Always use traffic metrics.**

**CES OBS traffic metric reference:**

| Metric | Description | Unit |
|--------|------|------|
| `download_traffic_extranet` | Extranet download traffic | Bytes |
| `download_traffic_intranet` | Intranet download traffic | Bytes |

For detailed metric descriptions, see [obs-metrics.md](obs-metrics.md).
