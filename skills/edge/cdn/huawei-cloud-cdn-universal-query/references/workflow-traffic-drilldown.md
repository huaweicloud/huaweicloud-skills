# Workflow 3: Traffic Anomaly Drill-Down

> Use this workflow when you detect a traffic anomaly and need to identify the source.

## Prerequisites

- hcloud CLI installed and authenticated
- Time range in millisecond UTC timestamps (max 1 day for `ShowTopDomainNames`)
- Target domain name (for Step 2 onwards)

## Steps

### Step 1: Identify top domains by traffic (single day)

Find which domains are consuming the most traffic in the anomaly window:

```bash
hcloud CDN ShowTopDomainNames --cli-region=cn-north-1 \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank domains by (enum: `flux`, `bw`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Critical:** Max time span is **1 day (24 hours)**. 25+ hours returns `CDN.0202`. See Pitfall #1.

**For multi-day analysis:** Make separate queries for each day.

**Returns:** Top domains ranked by the requested metric (flux/bw/req_num).

### Step 2: Drill down into the anomalous domain

For the domain showing anomaly, query multiple dimensions in parallel:

**Top client IPs:**
```bash
hcloud CDN ListCdnDomainTopIps --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank IPs by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Top URL paths:**
```bash
hcloud CDN ListCdnDomainTopPath --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank URL paths by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Top User-Agents:**
```bash
hcloud CDN ListCdnDomainTopUas --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank User-Agents by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Pitfall:** For `ListCdnDomainTopUas`, do NOT use `--group_by` and `--include_ratio` together. Use only one. See Pitfall #2.

**Top Referers:**
```bash
hcloud CDN ListCdnDomainTopRefers --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank Referers by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Rate limit:** Max 2 calls/second for `ListCdnDomainTopRefers`.

**Top origin URLs:**
```bash
hcloud CDN ListCdnDomainTopOriginUrl --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank origin URLs by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

**Top URLs (v2):**
```bash
hcloud CDN ShowTopUrl/v2 --cli-region=cn-north-1 \
  --domain_name=<your-domain> \
  --stat_type=<stat_type> \
  --start_time=<ms> \
  --end_time=<ms>
```

Where:
- `<stat_type>` — metric to rank URLs by (enum: `flux`, `req_num`)
- `<ms>` — millisecond UTC timestamp

### Step 3: Geographic/ISP distribution

Identify where the traffic is coming from:

**By province (China):**
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

Where:
- `<stat_type>` — metric to query (enum: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`)
- `<ms>` — millisecond UTC timestamp
- `<action>` — detail level (enum: `location_summary`, `location_detail`)
- `<group_by>` — geographic grouping dimension (enum: `province`, `country`, `isp`)
- `<ip_version>` — IP protocol version (enum: `IPv4`, `IPv6`)

**Critical:**
- `--stat_type` is REQUIRED. See Pitfall #14.
- `--ip_version` must be `IPv4` or `IPv6`, NOT `v4` or `v6`. See Pitfall #3.

**By ISP:**
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

Where:
- `<stat_type>` — metric to query (enum: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`)
- `<ms>` — millisecond UTC timestamp
- `<action>` — detail level (enum: `location_summary`, `location_detail`)
- `<group_by>` — geographic grouping dimension (enum: `province`, `country`, `isp`)
- `<ip_version>` — IP protocol version (enum: `IPv4`, `IPv6`)

**By country:**
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

Where:
- `<stat_type>` — metric to query (enum: `flux`, `bw`, `req_num`, `bs_bw`, `bs_flux`, `hit_num`, `bs_num`, `bs_fail_num`, `hit_flux`, `http_code_2xx`, `http_code_3xx`, `http_code_4xx`, `http_code_5xx`)
- `<ms>` — millisecond UTC timestamp
- `<action>` — detail level (enum: `summary`, `detail`)
- `<group_by>` — geographic grouping dimension (enum: `province`, `country`, `isp`)
- `<country>` — country filter (enum: `all`, `cn`)

**Critical:**
- `--group_by` only supports `country` (not `province` or `isp`). See Pitfall #4.
- `--stat_type` is REQUIRED. See Pitfall #14.
- May return empty results for some domains.

## Analysis Patterns

| Observation | Possible Cause |
|-------------|----------------|
| Single IP dominates traffic | Crawling/scraping, potential DDoS |
| Single URL path dominates | Hot content, possible cache miss issue |
| Unknown Referer dominates | Hotlinking / traffic theft |
| Single UA dominates | Bot/crawler traffic |
| Single province dominates | Geographic anomaly, possible regional issue |
| Single ISP dominates | Carrier-specific issue |
| Origin URL traffic high | Cache hit ratio drop, origin pull anomaly |
