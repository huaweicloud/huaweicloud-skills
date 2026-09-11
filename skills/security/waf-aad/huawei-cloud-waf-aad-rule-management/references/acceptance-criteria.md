# Acceptance Criteria — huawei-cloud-waf-aad-rule-management

Maps the 17 `huawei_*` actions from GitCode issue #474 to acceptance checks.

## Query actions (R3 — read-only, auto-execute)

| # | Action | Acceptance check |
|---|--------|------------------|
| 1 | `huawei_list_waf_instances` | Runs `WAF ListInstance` (+ `ListCompositeHosts`) with region/project; returns instance/host list |
| 2 | `huawei_list_waf_policies` | Runs `WAF ListPolicy`; returns policy list |
| 3 | `huawei_list_waf_custom_rules` | Runs `WAF ListCustomRules --policy_id`; returns custom rules |
| 4 | `huawei_list_waf_whiteblackip_rules` | Runs `WAF ListWhiteblackipRule --policy_id`; returns IP rules |
| 5 | `huawei_list_waf_cc_rules` | Runs `WAF ListCcRules --policy_id`; returns CC rules |
| 6 | `huawei_list_waf_geo_rules` | Runs `WAF ListGeoipRule --policy_id`; returns geo rules |
| 7 | `huawei_list_aad_instances` | Runs `AAD ListInstance` + `AAD ListPackage`; returns instance/package list |

## Diagnose actions (R3 — read-only, auto-execute)

| # | Action | Acceptance check |
|---|--------|------------------|
| 8 | `huawei_analyze_waf_cname_status` | For each composite host, compares `cname` vs DNS record; flags CNAME not pointing to WAF endpoint |
| 9 | `huawei_analyze_waf_rule_order` | Sorts rules by priority per policy; flags block-above-log / overlapping conditions (false-positive risk) |
| 10 | `huawei_analyze_aad_protection` | Cross-checks package type (Standard single-IP / Enterprise 网段) vs protected/unbound IPs; flags unprotected EIPs |

## Manage actions (R2 / R1 — preview + confirmation)

| # | Action | Acceptance check |
|---|--------|------------------|
| 11 | `huawei_create_waf_custom_rule` | Preview exact `BatchCreateCustomRule` command → confirm → execute → verify via `ListCustomRules`; default action=log (report mode) first |
| 12 | `huawei_create_waf_ip_blacklist_rule` | Same flow via `BatchCreateWhiteblackipRule`; verify via `ListWhiteblackipRule` |
| 13 | `huawei_create_waf_cc_rule` | Same flow via `BatchCreateCcRule`; verify via `ListCcRules` |
| 14 | `huawei_create_waf_geo_rule` | Same flow via `BatchCreateGeoIpRule`; verify via `ListGeoipRule` |
| 15 | `huawei_create_aad_instance` | **No CLI** — skill must return console purchase guidance + `AAD ListPackage` verification; MUST NOT fabricate a CLI command |
| 16 | `huawei_delete_waf_rule` | Resolve `rule_id` → preview exact `Delete*Rule` → explicit confirmation → execute → verify rule gone |
| 17 | `huawei_delete_aad_instance` | **No CLI** — skill must return console unsubscribe guidance; MUST NOT fabricate a CLI command |

## Global acceptance

- [ ] SKILL.md conforms to GitCode Skill registration spec (frontmatter, required sections, ≤ 500 lines)
- [ ] 17 `huawei_*` actions are all documented and routable to the verified CLI operations above
- [ ] `hcloud WAF` / `hcloud AAD` dependencies correctly declared (KooCLI 7.2.12)
- [ ] R3 read-only actions auto-execute; R2/R1 manage actions require preview + confirmation
- [ ] AAD create/delete limitation declared; console guidance + `ListPackage` diagnostic path provided
- [ ] Critical Warnings present: CNAME redirect, premium instance, Standard vs Enterprise, rule order, report-mode-first
- [ ] Both AK/SK env credentials and local hcloud profile authentication documented
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md` present; quality SDK vendored; no hardcoded credentials
