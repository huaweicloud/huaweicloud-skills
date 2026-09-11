# Verification Method — huawei-cloud-waf-aad-rule-management

How to verify this skill end-to-end. All read-only checks can run automatically (R3); write
operations require preview + user confirmation (R2/R1).

## 1. Environment checks

```bash
hcloud version                       # >= 7.2.12
hcloud WAF --help | head -30         # WAF service + operations list
hcloud AAD --help | head -30         # AAD service + operations list
hcloud configure list                # authenticated profile
```

## 2. Read-only verification (R3 — runs automatically)

| Case | Command | Expected |
|------|---------|----------|
| List WAF instances | `hcloud WAF ListInstance --cli-region=<region> --project_id=<project_id>` | HTTP 200 JSON list (may be empty if no dedicated instance) |
| List protected domains | `hcloud WAF ListCompositeHosts --cli-region=<region> --project_id=<project_id>` | JSON list of hosts with CNAME/access status |
| List policies | `hcloud WAF ListPolicy --cli-region=<region> --project_id=<project_id>` | JSON list of policies |
| List custom rules | `hcloud WAF ListCustomRules --cli-region=<region> --project_id=<project_id> --policy_id=<policy_id>` | JSON list of rules |
| List IP black/white rules | `hcloud WAF ListWhiteblackipRule ...` | JSON list |
| List CC rules | `hcloud WAF ListCcRules ...` | JSON list |
| List geo rules | `hcloud WAF ListGeoipRule ...` | JSON list |
| Show composite host | `hcloud WAF ShowCompositeHost --cli-region=<region> --project_id=<project_id> --host_id=<host_id>` | JSON detail with CNAME |
| List AAD instances | `hcloud AAD ListInstance --cli-region=<region>` | JSON list of instances |
| List AAD packages | `hcloud AAD ListPackage --cli-region=<region>` | JSON list of packages |
| List protected IPs | `hcloud AAD ListProtectedIp --cli-region=<region>` | JSON list of EIPs |
| List unbound IPs | `hcloud AAD ListUnboundProtectedIp --cli-region=<region> --package_id=<package_id>` | JSON list of unbound EIPs |

**Negative check (mandatory):** the following commands MUST fail — they prove the skill does not
fabricate AAD instance management:

```bash
hcloud AAD CreateInstance --help    # [USE_ERROR] Operation CreateInstance is not supported.
hcloud AAD DeleteInstance --help    # [USE_ERROR] Operation DeleteInstance is not supported.
```

## 3. Diagnostic verification (R3)

- `huawei_analyze_waf_cname_status`: given `ListCompositeHosts` output, for each host compare the
  `cname` value with the actual DNS record (e.g. `dig +short <domain> CNAME`). Report
  "protected / unprotected" per domain and warn when DNS points to the origin IP instead of the
  WAF endpoint.
- `huawei_analyze_waf_rule_order`: for each policy, merge lists of rules by `priority`
  (small = evaluated first). Flag block rules (`action => block`) ordered above log/allow rules,
  and overlapping conditions (false-positive risk).
- `huawei_analyze_aad_protection`: cross-check `ListInstance` packages (Standard = single IP,
  Enterprise = 网段) against `ListProtectedIp` coverage; flag public EIPs returned by
  `ListUnboundProtectedIp` as unprotected.

## 4. Write-operation verification (R2/R1 — requires confirmation)

> Never execute these in an automated test against production. Use a TEST policy / scratch account,
> and always preview the exact command to the user first.

1. **Create custom rule** — run `BatchCreateCustomRule` with `--action.category=log`
   (report mode), then `ListCustomRules` to confirm the rule appears with the expected action.
2. **Create IP blacklist** — `BatchCreateWhiteblackipRule --white=0 --addr=<test-ip>`, confirm via
   `ListWhiteblackipRule`.
3. **Create CC rule** — `BatchCreateCcRule --mode=0 --action.category=log ...`, confirm via
   `ListCcRules`.
4. **Create geo rule** — `BatchCreateGeoIpRule --geoip=<code> --white=2` (log), confirm via
   `ListGeoipRule`.
5. **Delete rule** — capture `rule_id` from the matching list command, then run the corresponding
   `Delete*Rule` and confirm the list no longer contains the rule.
6. **Cleanup** — delete every test rule created in steps 1–4.

## 5. AAD instance create/delete (console-only)

Purchase/unsubscribe cannot be verified via CLI. Verification path:
`hcloud AAD ListPackage` before/after console purchase — package count/state must change. Record
the console operation ID in the report.
