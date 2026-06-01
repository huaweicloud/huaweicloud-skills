# Task 3: Query Total Requests (with MoM Comparison)

> **⚠️ Critical: Request data is obtained via CES (Cloud Eye Service)**
>
> OBS request monitoring metrics are collected and managed by CES and must be queried through the CES API.

> **⚠️ Important: Required parameters must be provided by the user**
> When querying request counts, `--region` and the bucket name must be explicitly provided by the user. Guessing is prohibited.

> **⚠️ Critical: Time range must precisely match the user's wording** (same as Task 2)
>
> You must strictly distinguish between "this month" (calendar month) and "last 30 days" (rolling 30-day window), etc.
> See the time range reference table in [task-query-traffic.md](task-query-traffic.md).

**Step 1: Determine the time range based on the user's wording** (same as Task 2)

**Step 2: Query request counts by type**

> **⚠️ CES ShowMetricData does not support the --User-Agent parameter; do not append it**

```bash
# Query GET request count for the period
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<StartTimestamp(ms)> \
  --to=<EndTimestamp(ms)>

# Query PUT request count
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<StartTimestamp(ms)> \
  --to=<EndTimestamp(ms)>

# Query POST/DELETE/HEAD request counts (for a complete breakdown)
hcloud CES ShowMetricData \
  --region=<RegionId> \
  --namespace=SYS.OBS \
  --metric_name=post_request_count \
  --dim.0=bucket_name,<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=<StartTimestamp(ms)> \
  --to=<EndTimestamp(ms)>
```

> **Total requests = GET + PUT + POST + DELETE + HEAD** (CES has no single `request_count` metric)

**Step 3: Query last period's request counts by type (for MoM calculation)**

Replace the time range in Step 2 with the comparison period and query last period's total requests, GET requests, PUT requests, etc.

**Step 4: Summary output**

```
OBS Request Report — Bucket: <BucketName>
══════════════════════════════════════════════════════════
Metric              Current Period  Previous Period  MoM Change
───────────────────────────────────────────────────────────────
Total Requests      1,250,000       980,000          +27.55%
GET Requests        1,000,000       800,000          +25.00%
PUT Requests        200,000         160,000          +25.00%
Other Requests      50,000          20,000           +150.00%
══════════════════════════════════════════════════════════
Period: 2026-05-01 ~ 2026-05-19
```

> **⚠️ Note: MoM special case handling**
>
> - When previous period value is 0, display MoM as "N/A" (cannot be calculated)
> - When previous period value is 0 and current period value > 0, display MoM as "New (previous period was 0)"
> - When both current and previous period values are 0, display MoM as "N/A"

**CES OBS request metric reference:**

| Metric | Description | Unit |
|--------|------|------|
| `get_request_count` | GET-type requests | Count |
| `put_request_count` | PUT-type requests | Count |
| `post_request_count` | POST-type requests | Count |
| `delete_request_count` | DELETE-type requests | Count |
| `head_request_count` | HEAD-type requests | Count |

> **⚠️ Note: OBS has no `request_count` metric**
>
> There is no OBS metric named `request_count` in CES. The total request count must be calculated by summing all request types:
> `Total requests = get_request_count + put_request_count + post_request_count + delete_request_count + head_request_count`

For detailed metric descriptions, see [obs-metrics.md](obs-metrics.md).
