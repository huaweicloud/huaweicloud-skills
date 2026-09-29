# Workflow 2: Query Traffic Statistics

> Use this workflow when you need to analyze domain traffic and bandwidth metrics.

## Prerequisites

- hcloud CLI installed and authenticated
- Target domain name (e.g., `<your-domain>`)
- Time range in millisecond UTC timestamps (aligned to UTC+8 midnight when `interval=86400`)

## Steps

### Step 1: Query account billing mode

Determine whether the account is billed by traffic (flux) or bandwidth (bw):

```bash
hcloud CDN ShowChargeModes --cli-region=cn-north-1 --product_type=<product_type>
```

**Parameter:** `--product_type` (enum: `base`) — CDN product type.

**Why:** The billing mode determines which metric to focus on. For `flux` billing → focus on traffic; for `bw` billing → focus on bandwidth.

**Best practice:** Always query BOTH metrics regardless of billing mode — you need both for complete analysis.

### Step 2: Query daily traffic (flux)

**Parameters:**
- `--stat_type` (enum: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`) — Metric type to query. 状态码类必须用组合指标（如 `http_code_2xx`），不存在裸 `http_code`/`status_code`；`status_code` 系列与 `bs_status_code` 系列不能同时查询。
- `--interval` (enum: `300`, `3600`, `86400`) — Time granularity in seconds (5min, 1hour, 1day).
- `--action` (enum: `detail`, `summary`) — Query result type. `detail` returns per-interval data; `summary` returns aggregated data.

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --interval=<interval> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action>
```

**Critical:** `--action=detail` is REQUIRED. See Pitfall #12.

**Returns:** Daily traffic values in bytes (array of numbers).

### Step 3: Query daily peak bandwidth (bw)

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --interval=<interval> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action>
```

**Returns:** Daily peak bandwidth values in bit/s (array of numbers).

### Step 4: Query 95th percentile bandwidth

**Parameter:** `--calc_type` (enum: `bw_95`, `bw_peak`) — Bandwidth calculation type. `bw_95` = 95th percentile; `bw_peak` = peak bandwidth.

```bash
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 \
  --calc_type=<calc_type> \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Critical:**
- Max time range is **31 days**. 32+ days returns `CDN.0202`. See Pitfall #11.
- Returns a **single aggregated value**, NOT per-day breakdown.
- For 30-day queries, add `--cli-read-timeout=30` to avoid timeout.

**Returns:**
```json
{
  "bandwidth_calc": {
    "value": 24116,  // bit/s
    "calc_type": "bw_95",
    "time_point": 1786289400000
  }
}
```

### Step 5: Query request count (optional)

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --interval=<interval> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action>
```

**Returns:** Daily request counts (array of numbers).

## Time Range Calculation

For "past N days" queries, use UTC+8 midnight alignment:

```python
from datetime import datetime, timedelta, timezone

tz = timezone(timedelta(hours=8))
today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
start = today - timedelta(days=7)  # past 7 days
start_ms = int(start.timestamp() * 1000)
end_ms = int(today.timestamp() * 1000)
```

**Timestamp examples (UTC+8):**
- `2026-08-11 00:00:00 UTC+8` = `1786291200000`
- `2026-08-10 00:00:00 UTC+8` = `1786204800000`
- `2026-08-04 00:00:00 UTC+8` = `1785686400000`

## Common Issues

- **Missing `--action`**: Returns `缺少必填参数:action`. Always include `--action=detail` or `--action=summary`.
- **Time range too large for ShowBandwidthCalc**: Max 31 days. Split into multiple queries if needed.
- **Time not aligned to UTC+8 midnight**: When `interval=86400`, timestamps must be aligned to midnight UTC+8. Non-aligned timestamps may return incomplete results.
