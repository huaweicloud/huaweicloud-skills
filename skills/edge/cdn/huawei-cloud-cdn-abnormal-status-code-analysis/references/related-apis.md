# API and CLI Command Reference

All commands are query-class (GET read-only) unless marked. CDN region:
`cn-north-1` (recommended) or `ap-southeast-1`. Time = ms timestamp, `[start,end)`.

## Step-by-step command map

| Step | Command | Purpose | Key params |
|------|---------|---------|------------|
| 1 | `hcloud CDN ListDomains/v2` | List domains → domain_id | — |
| 1 | `hcloud CDN ShowDomainStats/v2 --action=summary` | Quantify 4xx/5xx | `stat_type=req_num,http_code_2xx,http_code_3xx,http_code_4xx,http_code_5xx` |
| 1 | `hcloud CDN ShowBandwidthCalc` | Bandwidth peak (traffic spike) | `calc_type=bw_peak` |
| 2 | `hcloud CDN ShowDomainStats/v2 --action=detail` | Exact code + time array | `stat_type=status_code_4xx,status_code_5xx` |
| 2 | `hcloud CDN ShowDomainStats/v2 --action=detail` | ★ edge vs origin fork ★ | `stat_type=bs_status_code_4xx,bs_status_code_5xx` |
| 2 | `hcloud CDN ShowDomainStats/v2 --action=summary` | Origin overall health | `stat_type=bs_http_code_2xx,bs_http_code_3xx,bs_http_code_4xx,bs_http_code_5xx` |
| 3 | `hcloud CDN ListDomainClientStats --stat_type=ip_num` | Client IP count (刷量 vs real users) | `--stat_type` |
| 3 | `hcloud CDN ListCdnDomainTopIps/Path/OriginUrl/Refers/Uas` | Top-N (req_num only) | `stat_type=req_num` |
| 4A | `hcloud CDN ShowOriginHost` | 回源HOST | `domain_id` |
| 4A | `hcloud CDN ShowDomainDetail` | Domain/origin detail | `domain_id` |
| 4A | `hcloud CDN ShowHistoryTasks/v2` | Refresh/preheat history | `file_type`, time |
| 4A | `hcloud CDN ListCdnDomainTopOriginUrl` | Top回源URL | `stat_type=req_num` |
| 4B | `hcloud CDN ShowDomainFullConfig/v2` | Full edge config | `domain_name` |
| 4B | `hcloud CDN ShowRefer` | Referer防盗链 | `domain_id` |
| 4B | `hcloud CDN ShowBlackWhiteList` | IP blacklist | `domain_id` |
| 4B | `hcloud CDN ListRuleDetails` | Rule engine | `domain_name` |
| 4B | `hcloud CDN ListBanUrl` | Banned URLs (工单 whitelist) | time range |
| 4B | `hcloud CDN ListAccessControlTask` | Ban/unban tasks (工单 whitelist) | time range |
| 4B | `hcloud CDN ShowResponseHeader` | Response header/error page | `domain_id` |
| 4B | `hcloud CDN ShowCertificatesHttpsInfo/v2 --domain_name=<d>` | HTTPS cert (49x) | `domain_name` |
| 5 | `hcloud CDN ShowLogs/v2` | Log download links (≤30 days, single domain) | `domain_name` |
| 5 | `python scripts/fetch_cdn_log.py` | Fetch+decompress+extract (JSON) | `--url`, `--status` |
| 5 | `hcloud CDN ShowIpInfo/v2` | IP attribution (≤20) | `--ips` |

## stat_type reference

| Side | Summary (segment-level) | Detail (specific-code-level) |
|------|--------------------------|------------------------------|
| Edge | `req_num`, `http_code_2xx/3xx/4xx/5xx` | `status_code_2xx/3xx/4xx/5xx` → `{"200":[..],"403":[..]}` |
| Origin (back-to-source) | `bs_http_code_2xx/3xx/4xx/5xx` | `bs_status_code_2xx/3xx/4xx/5xx` → same |

- `action=summary` ⇒ interval total (single value); `action=detail` ⇒ time array
  (index = time bucket).
- `result` returns keys only for codes that actually occurred.

> `status_code_*` (edge) and `bs_status_code_*` (origin) **cannot be combined
> in one query** — run edge and origin separately.

## interval / time rules

| interval | meaning | max span | point requirement |
|----------|---------|----------|-------------------|
| `300` | 5 min | ≤2 days | 5-min-aligned points |
| `3600` | 1 hour | ≤7 days | hour-aligned points |
| `86400` | 1 day | ≤31 days | **CST 0:00 points** |

## status-code → first-guess root cause map

| Code | First-guess root cause | Edge/Origin | Primary query interfaces |
|------|------------------------|------------|---------------------------|
| 400 | Bad request syntax (client) | edge | `ShowLogs` |
| 401 | URL auth failed | edge | `ShowDomainFullConfig.url_auth` |
| 403 (edge) | auth/referer/IP-blacklist/UA/ban/rate-limit/CC | edge | `ShowDomainFullConfig`+`ShowRefer`+`ShowBlackWhiteList`+`ListRuleDetails`+`ListBanUrl`+`ListDomainClientStats`+`ShowBandwidthCalc` |
| 403/404 (origin) | 回源HOST wrong / origin permission or resource missing | origin | `bs_status_code`+`ShowOriginHost`+`ShowDomainDetail`+`ListCdnDomainTopOriginUrl` |
| 404 (edge MISS) | origin has no resource / 回源HOST wrong | origin | `ShowOriginHost`+`ListCdnDomainTopOriginUrl`+`ShowLogs` |
| 405 | method not allowed | origin | `ShowDomainDetail`+`ShowLogs` |
| 416 | range request invalid | edge | `ShowDomainFullConfig.cache_rules` |
| 429 | rate-limited (rare for CDN) | edge | `ListDomainClientStats`+`ShowBandwidthCalc` |
| 499 | client closed (often slow/large file) | edge | `ShowLogs`(rt)+`ShowBandwidthCalc` |
| 495/496 | TLS/cert error | edge | `ShowCertificatesHttpsInfo`+`ShowDomainFullConfig.https` |
| 500 | origin internal error | origin | `bs_status_code`+`ShowDomainDetail` |
| 502 | origin connection failed / unreachable / 回源HOST wrong | origin | `bs_status_code`+`ShowOriginHost`+`ShowDomainDetail.sources`+`ShowHistoryTasks` |
| 503 | origin overload / origin timeout / edge rate-limit | edge or origin | `origin_receive_timeout`+`ShowHistoryTasks`+`ListDomainClientStats`+`ShowBandwidthCalc` |
| 504 | origin timeout | origin | `ShowDomainFullConfig.origin_receive_timeout`+`ShowDomainDetail` |
| 530 | origin DNS / connection error | origin | `ShowDomainDetail.sources`+`ShowOriginHost` |

## fetch_cdn_log.py output schema

```json
{
  "url": "<link>",
  "http_status": 200,
  "byte_size": 4375,
  "status_filter": [403],
  "rows": [
    {"status": 403, "client_ip": "120.46.140.45", "url": "/index.html",
     "cache_status": "HIT", "user_agent": "curl/8.2.1",
     "edge_node_ip": "39.136.130.12", "time": "[10/Aug/2026:15:55:13 +0800]"}
  ],
  "count": 1,
  "duration_ms": 420,
  "error": null
}
```

**`rows[]` field mapping** — each row is parsed from the Huawei Cloud official
14-field CDN log format (see
[通过日志分析恶意访问地址](https://support.huaweicloud.com/intl/zh-cn/bestpractice-cdn/cdn_01_0252.html)):

| rows[] field | Log field # | Official name | Note |
|--------------|-------------|---------------|------|
| `time` | 1 | 日志生成时间 | `[10/Aug/2026:15:55:13 +0800]` — **contains a space**, kept as one token |
| `client_ip` | 2 | 访问 IP 地址 | end-user source IP |
| `url` | 8 | 请求路径 | e.g. `/index.html` |
| `status` | 9 | HTTP 状态码 | 3-digit number |
| `cache_status` | 11 | 缓存命中状态 | HIT / MISS |
| `user_agent` | 12 | UA 信息 | quoted; contains spaces, kept together |
| `edge_node_ip` | 14 | CDN 服务端响应 IP | serving CDN node |

Full official field order: `[time] client_ip rt referer protocol method host url
status size cache_status user_agent range edge_node_ip`.

`error.reason` codes: `connect_timeout`, `connect_failed`, `http_error`,
`bad_gzip`, `invalid_url`, `invalid_timeout`, `invalid_max_lines`,
`invalid_status`, `missing_library`.

## Important Notes

- All hcloud commands use `--cli-region=cn-north-1` and `--key=value`.
- Top-N `stat_type` supports only `flux`/`req_num` (no status code) — always
  cross-reference with `ShowDomainStats`/`ShowLogs`.
- `ListBanUrl` / `ListAccessControlTask` may return `CDN.0004` (not in
  whitelist); they remain query-class — record and proceed, do not bypass.
