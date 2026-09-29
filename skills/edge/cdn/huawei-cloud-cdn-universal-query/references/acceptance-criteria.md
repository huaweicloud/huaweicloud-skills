# Acceptance Criteria

## Functional Requirements

- [ ] Skill can list all CDN domains via `ListDomains/v2`
- [ ] Skill can get domain details by name via `ShowDomainDetailByName`
- [ ] Skill can get domain_id from domain name
- [ ] Skill can query account billing mode via `ShowChargeModes`
- [ ] Skill can query traffic statistics via `ShowDomainStats/v2` with correct parameters:
  - `--stat_type` (flux, bw, req_num, etc.)
  - `--interval` (300, 3600, 86400)
  - `--action` (detail or summary, REQUIRED)
  - `--start_time` and `--end_time` (millisecond timestamps)
- [ ] Skill can query 95th percentile bandwidth via `ShowBandwidthCalc` with:
  - `--calc_type` (bw_95, bw_peak, bw_95_average)
  - Max 31-day range
  - Single aggregated value (not per-day breakdown)
- [ ] Skill can query top domains, IPs, URLs, User-Agents, Referers
- [ ] Skill can query geographic/ISP distribution via `ShowDomainLocationStats/v2` with:
  - `--stat_type` (REQUIRED)
  - `--action` (location_detail or location_summary)
  - `--group_by` (domain, country, province, isp)
  - `--ip_version` (IPv4 or IPv6, NOT v4/v6)
- [ ] Skill can query refresh/preheat task history via `ShowHistoryTasks/v2` with:
  - `--page_number` and `--page_size` (MUST pass together)
- [ ] Skill can query CDN logs via `ShowLogs/v2`
- [ ] Skill can download statistics Excel via `DownloadStatisticsExcel` with:
  - `--cli-read-timeout=60`
  - Binary Excel output (xlsx/zip format)
- [ ] Skill can query domain templates via `ShowDomainTemplate` with:
  - `--tml_type` (INTEGER: 1=system, 2=user)
- [ ] Skill can check if IPs belong to Huawei Cloud CDN via `ShowIpInfo/v2`
- [ ] Skill can query account quota via `ShowQuota/v2`
- [ ] Skill can query domain tags via `ShowTags/v2` with:
  - `--resource_id` (REQUIRED, domain_id)

## Non-Functional Requirements

- [ ] All API calls should use `--cli-region=cn-north-1`
- [ ] No credential hardcoding (AK/SK read from environment or CLI config)
- [ ] Read-only operations only (no write/delete/modify)
- [ ] Skill directory size ≤ 40 MB
- [ ] File count ≤ 30
- [ ] All hcloud parameters use `--key=value` format
- [ ] No cross-skill direct calls
- [ ] All 12 validated pitfalls documented in troubleshooting

## Output Format

- [ ] JSON responses are properly formatted
- [ ] Error messages are clear and actionable
- [ ] Timestamps are in milliseconds (UTC)
- [ ] Time ranges respect API limits:
  - ShowTopDomainNames: max 1-day span
  - ShowBandwidthCalc: max 31-day range
  - ShowUrlTaskInfo/v2: max 24-hour span
  - ShowDomainStats/v2: interval=86400 max 31-32 days (33 days+ returns CDN.0203); interval=3600 max 7 days; interval=300 max 2 days

## API Coverage

- [ ] Category 1: Domain Management (14 APIs) — all documented
- [ ] Category 2: Statistics & Analytics (12 APIs) — all documented
- [ ] Category 3: Refresh / Log / Export (8 APIs) — all documented
- [ ] Category 4: Template / Rule / Tag / Account (11 APIs) — all documented
- [ ] Total: 45 GET APIs covered

## Pitfall Validation

- [ ] Pitfall #1: ShowTopDomainNames max 1-day span — validated
- [ ] Pitfall #2: ListCdnDomainTopUas group_by/include_ratio mutually exclusive — validated
- [ ] Pitfall #3: ShowDomainLocationStats/v2 ip_version IPv4/IPv6 — validated
- [ ] Pitfall #4: ShowDomainCountryStat action summary/detail; group_by optional (domain/country/province/isp); country optional — corrected per CLI help
- [ ] Pitfall #5: ShowHistoryTasks/v2 page_number/page_size together — validated
- [ ] Pitfall #6: ShowLogs/v2 enterprise project restriction — validated
- [ ] Pitfall #7: DownloadStatisticsExcel timeout and binary output — validated
- [ ] Pitfall #8: ShowDomainTemplate tml_type INTEGER — validated
- [ ] Pitfall #9: ShowUrlTaskInfo/v2 max 24h span — validated
- [ ] Pitfall #10: ListDomains/v2 business_type filter timeout — validated
- [ ] Pitfall #11: ShowBandwidthCalc max 31-day range and single value — validated
- [ ] Pitfall #12: ShowDomainStats/v2 action parameter REQUIRED — validated
- [ ] Pitfall #13: ShowTags/v2 requires resource_id — validated
- [ ] Pitfall #14: ShowDomainLocationStats/v2 and ShowDomainCountryStat require stat_type — validated
