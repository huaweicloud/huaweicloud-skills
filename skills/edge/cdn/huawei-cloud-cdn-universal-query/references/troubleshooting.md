# Troubleshooting — 12 Key Pitfalls

> These pitfalls were validated through end-to-end testing of all 45 GET CDN APIs.

## Pitfall #1: ShowTopDomainNames — Max 1-day span

**Symptom**: Error `CDN.0202: time range is incorrect`

**Cause**: `ShowTopDomainNames` only supports a maximum time span of 1 day (24 hours).

**Fix**: Use a single-day time range. For multi-day analysis, make separate queries for each day.

```bash
# Correct: 1-day span
hcloud CDN ShowTopDomainNames --cli-region=cn-north-1 --stat_type=flux --start_time=1786204800000 --end_time=1786291200000

# Incorrect: 7-day span
hcloud CDN ShowTopDomainNames --cli-region=cn-north-1 --stat_type=flux --start_time=1785686400000 --end_time=1786291200000
```

## Pitfall #2: ListCdnDomainTopUas — group_by and include_ratio mutually exclusive

**Symptom**: Error `CDN.0001: unsupport both set group by and include ratio`

**Cause**: `group_by` and `include_ratio` parameters cannot be used together in `ListCdnDomainTopUas`.

**Fix**: Use one or the other, not both.

```bash
# Correct: Use group_by only
hcloud CDN ListCdnDomainTopUas --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=domain

# Correct: Use include_ratio only
hcloud CDN ListCdnDomainTopUas --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --include_ratio=true

# Incorrect: Use both
hcloud CDN ListCdnDomainTopUas --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=domain --include_ratio=true
```

## Pitfall #3: ShowDomainLocationStats/v2 — ip_version values

**Symptom**: Error `CDN.0001: ip version name is incorrect: v4`

**Cause**: `ip_version` parameter values must be `IPv4` or `IPv6`, not `v4` or `v6`.

**Fix**: Use the full format `IPv4` or `IPv6`.

```bash
# Correct
hcloud CDN ShowDomainLocationStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --action=location_detail --group_by=province --ip_version=IPv4

# Incorrect
hcloud CDN ShowDomainLocationStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --action=location_detail --group_by=province --ip_version=v4
```

## Pitfall #4: ShowDomainCountryStat — Parameter combination pitfalls

**Symptom**: Error `CDN.0001: group_by param is incorrect` (when passing an unsupported `group_by` value, or a value not applicable to the query type)

**Cause (corrected per CLI help)**: `ShowDomainCountryStat` `--action` supports `summary`/`detail` (both); `--group_by` is **optional** and supports `domain`/`country`/`province`/`isp`; `--country` is **optional** (`all` or country codes; 访问区域情况数据时只能填 `cn`). `province` is only effective when `country=cn`. Passing a value outside these enums, or an inapplicable combination (e.g., `--group_by=province` without `--country=cn`), returns `CDN.0001`.

**Fix**: Use the exact parameter combination.

```bash
# Correct — summary with country grouping
hcloud CDN ShowDomainCountryStat --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=country --country=all --action=summary

# Correct — detail action is also supported
hcloud CDN ShowDomainCountryStat --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=country --country=all --action=detail

# Correct — province grouping (only effective with country=cn)
hcloud CDN ShowDomainCountryStat --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=province --country=cn --action=summary

# Incorrect: group_by value outside domain/country/province/isp
hcloud CDN ShowDomainCountryStat --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --group_by=unknown
```

## Pitfall #5: ShowHistoryTasks/v2 — Pagination parameters

**Symptom**: Error `CDN.0001: Parameter error`

**Cause**: `page_number` and `page_size` must be passed together. Passing only one causes an error.

**Fix**: Always pass both parameters.

```bash
# Correct
hcloud CDN ShowHistoryTasks/v2 --cli-region=cn-north-1 --page_number=1 --page_size=10

# Incorrect: Missing page_size
hcloud CDN ShowHistoryTasks/v2 --cli-region=cn-north-1 --page_number=1
```

## Pitfall #6: ShowLogs/v2 — Enterprise project restriction

**Symptom**: Error `user has no enterprise project id:{0}`

**Cause**: If the domain belongs to a specific enterprise project, the query may fail. Use a domain that is not in an enterprise project.

**Fix**: Use a different domain or ensure the domain is not tied to an enterprise project.

```bash
# If one domain fails, try another domain
hcloud CDN ShowLogs/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --start_time=<ms> --end_time=<ms>
```

## Pitfall #7: DownloadStatisticsExcel — Timeout and binary output

**Symptom**: Timeout error or binary output that cannot be read as text.

**Cause**: The default `readTimeout` (10s) is too short for large exports. The output is a binary Excel file (xlsx/zip format).

**Fix**: Add `--cli-read-timeout=60` and handle the output as binary.

```bash
# Correct
hcloud CDN DownloadStatisticsExcel --cli-region=cn-north-1 --domain_name=<your-domain> --start_time=<ms> --end_time=<ms> --excel_type=excel_type_usage --cli-read-timeout=60

# The output will be binary (starts with "PK" header for xlsx/zip)
```

## Pitfall #8: ShowDomainTemplate — tml_type is INTEGER

**Symptom**: Error `integer类型参数tml_type的值不正确`

**Cause**: `tml_type` is an integer type, not a string. Use `1` for system templates and `2` for user templates.

**Fix**: Pass integer values.

```bash
# Correct
hcloud CDN ShowDomainTemplate --cli-region=cn-north-1 --tml_type=1  # system templates
hcloud CDN ShowDomainTemplate --cli-region=cn-north-1 --tml_type=2  # user templates

# Incorrect
hcloud CDN ShowDomainTemplate --cli-region=cn-north-1 --tml_type=system
```

## Pitfall #9: ShowUrlTaskInfo/v2 — Max 24-hour span

**Symptom**: Error or empty results for large time ranges.

**Cause**: `ShowUrlTaskInfo/v2` only supports a maximum time span of 24 hours.

**Fix**: Keep `start_time` and `end_time` within 24 hours.

```bash
# Correct: 24-hour span
hcloud CDN ShowUrlTaskInfo/v2 --cli-region=cn-north-1 --start_time=1786204800000 --end_time=1786291200000

# Incorrect: 7-day span
hcloud CDN ShowUrlTaskInfo/v2 --cli-region=cn-north-1 --start_time=1785686400000 --end_time=1786291200000
```

## Pitfall #10: ListDomains/v2 — business_type filter timeout

**Symptom**: Timeout or slow response when using `--business_type=web`.

**Cause**: The `business_type=web` filter can cause performance issues.

**Fix**: Avoid using `business_type` filter, or use other filters like `domain_status`, `service_area`.

```bash
# Correct: Use other filters
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=100 --domain_status=online

# Avoid: business_type filter
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=100 --business_type=web
```

## Pitfall #11: ShowBandwidthCalc — Max 31-day range and single value

**Symptom**: Error for large time ranges or unexpected single-value output.

**Cause**: 
- Maximum query range is 31 days (32+ days returns `CDN.0202`).
- Multi-day queries return a **single aggregated 95th percentile value**, not per-day breakdown.

**Fix**: 
- Split into per-day queries if daily breakdown is needed.
- Use `--cli-read-timeout=30` for 30-day queries to avoid timeout.

```bash
# Correct: Single day query
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --calc_type=bw_95 --domain_name=<your-domain> --start_time=1786204800000 --end_time=1786291200000

# Correct: 30-day query with extended timeout
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --calc_type=bw_95 --domain_name=<your-domain> --start_time=1783612800000 --end_time=1786291200000 --cli-read-timeout=30

# Incorrect: 32-day query
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --calc_type=bw_95 --domain_name=<your-domain> --start_time=1783526400000 --end_time=1786291200000
```

## Pitfall #12: ShowDomainStats/v2 — action parameter is REQUIRED

**Symptom**: Error `缺少必填参数:action`

**Cause**: The `--action` parameter is required but not obvious from the API name.

**Fix**: Always include `--action=detail` or `--action=summary`.

```bash
# Correct
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --interval=86400 --start_time=<ms> --end_time=<ms> --action=detail

# Incorrect: Missing --action
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --interval=86400 --start_time=<ms> --end_time=<ms>
```

## Additional Pitfall #13: ShowTags/v2 — Requires resource_id

**Symptom**: Error `缺少必填参数:resource_id`

**Cause**: `ShowTags/v2` requires `--resource_id` parameter (domain_id), it's not a standalone list-all-tags API.

**Fix**: Pass the domain_id as `--resource_id`.

```bash
# Correct
hcloud CDN ShowTags/v2 --cli-region=cn-north-1 --resource_id=<domain_id>

# Incorrect: No resource_id
hcloud CDN ShowTags/v2 --cli-region=cn-north-1
```

## Additional Pitfall #14: ShowDomainLocationStats/v2 and ShowDomainCountryStat — stat_type required

**Symptom**: Error `缺少必填参数:stat_type`

**Cause**: Both APIs require `--stat_type` parameter (bw/flux/req_num), not just `--action` and `--group_by`.

**Fix**: Always include `--stat_type`.

```bash
# Correct
hcloud CDN ShowDomainLocationStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --stat_type=flux --start_time=<ms> --end_time=<ms> --action=location_detail --group_by=province

# Incorrect: Missing --stat_type
hcloud CDN ShowDomainLocationStats/v2 --cli-region=cn-north-1 --domain_name=<your-domain> --start_time=<ms> --end_time=<ms> --action=location_detail --group_by=province
```
