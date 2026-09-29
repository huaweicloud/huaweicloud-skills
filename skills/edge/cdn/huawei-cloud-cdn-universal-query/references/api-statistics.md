# Category 2: Statistics & Analytics APIs (12 APIs)

> All commands should use `--cli-region=cn-north-1`. All operations are read-only (GET).
> Time parameters are millisecond UTC timestamps (denoted as `<ms>` in examples).
> Enum parameters list all valid values in their parameter descriptions.

## API List

### 1. ShowChargeModes — Get account billing mode

```bash
hcloud CDN ShowChargeModes --cli-region=cn-north-1 --product_type=<product_type>
```

**Parameters:**
- `--product_type` (required): Valid values: `base` (实测 CLI 仅支持 `base`)
- `--service_area` (optional): Valid values: `mainland_china`, `outside_mainland_china` (实测 CLI 不支持 `global`)

**Returns:** Charge mode (`flux` for traffic, `bw` for bandwidth) per service area.

**Use:** Determine whether to focus on traffic (flux) or bandwidth (bw) metrics.

---

### 2. ShowDomainStats/v2 — Get domain statistics (time-series)

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --interval=<interval> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action>
```

**Parameters:**
- `--domain_name` (required)
- `--stat_type` (required): Valid values: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx` (状态码类请使用组合指标，如 `http_code_2xx`；不存在裸 `http_code`)
- `--interval` (required): Valid values: `300` (5 min), `3600` (1 hour), `86400` (1 day)
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps
- `--action` (**REQUIRED**): Valid values: `detail`, `summary` — see Pitfall #12

**Pitfall:** `--action` is required. Missing it returns `缺少必填参数:action`.

**Pitfall:** `status_code` 系列与 `bs_status_code` 系列不能同时查询，否则返回参数错误。

**Time alignment:** When `interval=86400`, align `start_time`/`end_time` to UTC+8 midnight.

**Returns:** Time-series array of the requested metric.

---

### 3. ShowBandwidthCalc — Get 95th percentile bandwidth

```bash
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 \
  --calc_type=<calc_type> \
  --domain_name=<your-domain> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:**
- `--calc_type` (required): Valid values: `bw_95`, `bw_peak`, `bw_95_average`
- `--domain_name` (required)
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps

**Pitfall:** Max time range is **31 days**. 32+ days returns `CDN.0202`. For 30-day queries, add `--cli-read-timeout=30` to avoid timeout. See Pitfall #11.

**Output:** Single aggregated value (NOT per-day breakdown).

```json
{
  "bandwidth_calc": {
    "value": 24116,
    "calc_type": "bw_95",
    "time_point": <ms>
  }
}
```

---

### 4. ShowTopDomainNames — Get top domains by metric

```bash
hcloud CDN ShowTopDomainNames --cli-region=cn-north-1 \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:**
- `--stat_type` (required): Valid values: `flux`, `bw`, `req_num`
- `--start_time`, `--end_time` (required): Millisecond UTC timestamps

**Pitfall:** Max time span is **1 day (24 hours)**. 25+ hours returns `CDN.0202`. See Pitfall #1.

**Use:** Identify which domains consume the most traffic/bandwidth.

---

### 5. ListCdnDomainTopIps — Get top client IPs

```bash
hcloud CDN ListCdnDomainTopIps --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`

**Returns:** Top client IPs by the requested metric.

---

### 6. ListCdnDomainTopPath — Get top URL paths

```bash
hcloud CDN ListCdnDomainTopPath --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`

**Returns:** Top URL paths by the requested metric.

---

### 7. ListCdnDomainTopUas — Get top User-Agents

```bash
hcloud CDN ListCdnDomainTopUas --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`
- Optional: `--group_by` (domain) OR `--include_ratio` (true) — **mutually exclusive** (see Pitfall #2)

**Pitfall:** `--group_by` and `--include_ratio` cannot be used together. Use only one.

---

### 8. ListCdnDomainTopRefers — Get top Referers

```bash
hcloud CDN ListCdnDomainTopRefers --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`

**Rate limit:** Max 2 calls/second.

---

### 9. ListCdnDomainTopOriginUrl — Get top origin URLs

```bash
hcloud CDN ListCdnDomainTopOriginUrl --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`

**Returns:** Top origin-pull URLs by the requested metric.

---

### 10. ShowTopUrl/v2 — Get top URLs (v2)

```bash
hcloud CDN ShowTopUrl/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

**Parameters:** `--domain_name`, `--stat_type`, `--start_time`, `--end_time` (all required). Valid values for `--stat_type`: `flux`, `req_num`

**Returns:** Top URLs (v2 format) by the requested metric.

---

### 11. ShowDomainLocationStats/v2 — Get geographic/ISP distribution

```bash
hcloud CDN ShowDomainLocationStats/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action> \
  --group_by=<group_by> \
  --ip_version=<ip_version>
```

**Parameters:**
- `--domain_name`, `--stat_type` (REQUIRED — see Pitfall #14), `--start_time`, `--end_time` (all required)
- `--stat_type` valid values: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`
- `--action` (required): Valid values: `location_detail`, `location_summary`
- `--group_by` (required): Valid values: `domain`, `country`, `province`, `isp`
- `--ip_version` (optional): Valid values: `IPv4`, `IPv6` — NOT `v4`/`v6` (see Pitfall #3)

**Pitfalls:**
- #3: `--ip_version` values must be `IPv4`/`IPv6`, not `v4`/`v6`
- #14: `--stat_type` is required, not just `--action` and `--group_by`

---

### 12. ShowDomainCountryStat — Get country-level stats

```bash
hcloud CDN ShowDomainCountryStat --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms> \
  --action=<action> \
  --group_by=<group_by> \
  --country=<country>
```

**Parameters:**
- `--domain_name`, `--stat_type` (REQUIRED — see Pitfall #14), `--start_time`, `--end_time` (all required)
- `--stat_type` valid values: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`
- `--action` (required): Valid values: `summary`, `detail` (实测 CLI 支持两种)
- `--group_by` (optional): Valid values: `domain`, `country`, `province`, `isp` (实测 CLI 为 optional，默认不分组；多个值可用英文逗号分隔)
- `--country` (optional): Valid values: `all` for all countries, or specific country code (e.g. `cn`); 访问区域情况数据时只能填 `cn`

**Pitfalls:**
- #4: `--group_by` supports `domain`/`country`/`province`/`isp` (not limited to `country`; `province` only effective when country=cn) — corrected per CLI help
- #14: `--stat_type` is required

**Note:** This API may return empty results for some domains.

---

## Common Workflow

```
Step 1: ShowChargeModes → determine billing mode (flux or bw)
Step 2: ShowDomainStats/v2 → query time-series stats with --action=<action>
Step 3: ShowBandwidthCalc → query 95th percentile bandwidth (single value)
Step 4: ShowTopDomainNames → identify top domains by metric
Step 5: For anomalous domain → ListCdnDomainTop* + ShowDomainLocationStats/v2
```
