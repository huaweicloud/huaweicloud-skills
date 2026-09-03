# Acceptance Criteria

## Functional Requirements

- [ ] Skill can check credentials via `hcloud configure list`
- [ ] Skill can list domains and obtain `domain_id` via `ListDomains/v2`
- [ ] When credentials are invalid, abort with a clear "configure credentials" message
- [ ] Skill can quantify 4xx/5xx volume and ratio via `ShowDomainStats/v2 --action=summary`
- [ ] Skill can drill to the exact status code + time bucket via `--action=detail --stat_type=status_code_4xx,status_code_5xx`
- [ ] Skill can run the edge/origin fork via `--stat_type=bs_status_code_4xx,bs_status_code_5xx`; empty ⇒ edge, non-empty ⇒ origin
- [ ] Skill can compute client IP count via `ListDomainClientStats` (刷量 vs real users)
- [ ] Skill runs Top-N family with `stat_type=req_num` only and cross-references status codes via logs/stats (does not claim Top-N carries status)
- [ ] Edge branch: `ShowDomainFullConfig/v2`, `ShowRefer`, `ShowBlackWhiteList`, `ListRuleDetails`, `ListBanUrl`, `ListAccessControlTask`, `ShowResponseHeader`, `ShowCertificatesHttpsInfo`
- [ ] Origin branch: `ShowOriginHost`, `ShowDomainDetail`, `ShowHistoryTasks/v2`, `ListCdnDomainTopOriginUrl`
- [ ] Skill obtains log links via `ShowLogs/v2` and extracts abnormal rows via `python scripts/fetch_cdn_log.py`
- [ ] `fetch_cdn_log.py` returns JSON with `rows[]`/`count`/`error`; soft failures exit 0 with `error.reason`, arg/library errors exit 2
- [ ] `rows[]` fields follow the Huawei Cloud official 14-field CDN log format: `time`(#1, bracketed with timezone, kept as one token), `client_ip`(#2), `url`(#8), `status`(#9), `cache_status`(#11), `user_agent`(#12, quoted, may contain spaces), `edge_node_ip`(#14) — no field misalignment on real log lines
- [ ] Skill attributes IPs via `ShowIpInfo/v2`

## Security Constraints

- [ ] Skill is read-only; prohibits Create/Update/Delete/Refresh/Preheat/VerifyDomainOwner/Set*/ExportStatsOpen
- [ ] On a write-op request, refuse with "this skill performs read-only diagnosis only"
- [ ] Prohibit reading/echoing/printing AK/SK
- [ ] Prohibit asking users to input credentials in chat; on paste, stop and emit the secure setup template
- [ ] iam-policies.md contains only read permissions (`cdn:domain:get` + read-only scope); no write actions
- [ ] `ListBanUrl`/`ListAccessControlTask` blocked by `CDN.0004` are recorded, not bypassed
- [ ] references/prohibited-operations.md lists all 55 prohibited non-GET operations (24 POST + 25 PUT + 6 DELETE)

## Output Format

- [ ] Report contains `====================` separator and `--- xxx ---` section headers
- [ ] Report contains analysis time, target domain, region
- [ ] Report contains summary, distribution, root cause, conclusion, remediation boundary
- [ ] Each claimed cause has evidence; each unconfirmed item marked honestly

## Command Format

- [ ] All hcloud commands use `--cli-region=cn-north-1`
- [ ] All hcloud commands use `--key=value`
- [ ] `status_code_*` and `bs_status_code_*` are never mixed in one query
- [ ] Top-N uses `--stat_type=req_num` (not a status code)

## File Constraints

- [ ] Directory contains SKILL.md + references/ + scripts/ + templates/
- [ ] references/ contains iam-policies.md and cli-installation-guide.md
- [ ] Total file count ≤ 30; total size ≤ 40 MB; SKILL.md ≤ 500 lines
- [ ] SKILL.md frontmatter name is `huawei-cloud-cdn-abnormal-status-code-analysis`, matching the directory name
- [ ] SKILL.md description contains "Triggers include:"
- [ ] SKILL.md contains Overview, Prohibited Operations, Architecture, Prerequisites, Authentication, IAM Permission Policies, Core Commands, Parameter Confirmation, Core Workflows, References sections
- [ ] All file extensions are in the allowlist (.md/.py/.json/.sh)
