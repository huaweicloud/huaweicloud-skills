---
name: huawei-cloud-waf-aad-rule-management
description: >-
  Manage and diagnose Huawei Cloud WAF (Web Application Firewall / Web应用防火墙) and AAD
  (Anti-DDoS / 抗DDoS) protection via the hcloud CLI. Covers WAF instance and protected-domain
  queries, policy and rule management (custom / precise protection, IP blacklist & whitelist, CC
  rate limiting, geo-blocking), CNAME onboarding diagnostics, rule-order and false-positive
  analysis, plus AAD instance listing and EIP protection-coverage checks. Read-only queries and
  diagnostics run automatically (R3); rule changes require preview + user confirmation (R2); rule
  deletion requires preview + explicit confirmation (R1). NOTE: AAD instance purchase/unsubscribe
  is a console-only (包周期) flow — this skill declares that limitation and offers console guidance.
  Use this skill when the user needs to inspect or change WAF protection, verify CNAME/DNS access
  to a WAF endpoint, review WAF rule order, check whether EIPs are covered by Anti-DDoS, or manage
  WAF rules. Triggers include: WAF, Web应用防火墙, Web Application Firewall, AAD, Anti-DDoS, 抗DDoS,
  DDoS防护, 防火墙, web protection, IP黑名单, IP白名单, blacklist, whitelist, CC防护, CC攻击, 限速,
  rate limiting, 地域封禁, geo rule, CNAME接入, WAF诊断, 规则顺序, 误报, EIP防护, 防护覆盖,
  waf aad, huawei-cloud-waf-aad-rule-management.
tags: [huawei-cloud waf aad security ddos web-firewall]
---

# Huawei Cloud WAF / AAD Skill (huawei-cloud-waf-aad-rule-management)

## Overview

This skill provides AI-Agent capabilities for **Huawei Cloud WAF (Web Application Firewall)** and
**AAD (Anti-DDoS)** via the verified `hcloud` CLI (KooCLI 7.2.12). It helps users answer "what
web/DDoS protection is configured", "is my site actually behind WAF", "are my rules safe and in
the right order", and "is every public EIP covered by Anti-DDoS".

**Scope boundaries:**

- ✅ Query (R3, read-only, auto-execute): WAF instances, protected domain names (composite hosts),
  policies, custom rules, IP black/white-list rules, CC rules, geo rules; AAD instances & packages.
- ✅ Diagnose (R3, read-only, auto-execute): CNAME onboarding status, rule-order & false-positive
  risk, AAD EIP protection coverage.
- ✅ Manage (R2, preview + confirm): create WAF custom / IP blacklist / CC / geo rules.
- ✅ Manage (R1, preview + explicit confirm): delete WAF rules (custom / white-black / CC / geo).
- ❌ Does NOT create or delete AAD instances via CLI — `hcloud AAD` has no `CreateInstance` /
  `DeleteInstance` (verified: KooCLI returns `[USE_ERROR] Operation ... is not supported`). AAD
  package purchase (购买) and unsubscribe (退订) are console-only (包周期) flows; see
  [AAD instance management](#aad-instance-management-console-only).
- ❌ Does NOT configure DNS records (do that at your DNS provider) and does NOT bind/unbind EIPs.

## Critical Warnings

| # | Warning | Why it matters |
|---|---------|----------------|
| 1 | **WAF requires CNAME redirect** | DNS must point to the **WAF endpoint (CNAME)**, not the origin server IP. Pointing DNS at the origin bypasses WAF protection entirely. |
| 2 | **Cloud WAF requires a premium/dedicated instance** | WAF protection domains only work on a paid Cloud WAF (premium/独享) instance; the free tier does not cover all rule types and features. |
| 3 | **AAD Standard vs Enterprise** | **Standard** protects only a **single IP/EIP**; **Enterprise** protects an **entire network segment (网段)**. Selecting the wrong package leaves IPs unprotected. |
| 4 | **Rule order matters** | Within a WAF policy, rules are evaluated **top-to-bottom**. A high priority (small `priority` value) rule listed earlier is applied first; mis-ordering causes false positives / false negatives. |
| 5 | **Rule changes default to report mode first** | For rule-type changes (custom, IP blacklist, CC, geo), first deploy with action `2` (log / report-only mode) to verify impact, then switch to `0` (block) / `1` (allow) once validated — never block production traffic blindly. |
| 6 | **Public-facing apps MUST use WAF** | Any internet-exposed web application must be behind WAF. Public EIPs should also be covered by AAD for DDoS protection. |
| 7 | **Never fabricate AAD instance CLI commands** | `hcloud AAD CreateInstance` / `DeleteInstance` do not exist. Do not invent them; use the console guidance in this skill. |

## Prerequisites

1. **hcloud CLI (KooCLI) 7.2.12+** installed.
   - Installation & configuration: see `references/cli-installation-guide.md`
   - Verify: `hcloud version`
2. **Authentication** — one of:
   - **AK/SK environment variables** (`HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, or `HUAWEI_ACCESS_KEY` /
     `HUAWEI_SECRET_KEY`); or
   - a **local hcloud profile**: `hcloud configure set --cli-access-key=<your-access-key>
     --cli-secret-key=<your-secret-key>` — never run this inside the skill or any script; credentials
     are read from the environment or the local profile only (do not hardcode them anywhere).
3. **Region & project**: WAF operations require `--project_id` (path parameter) plus `--cli-region`.
   Get the project ID from *My Credentials → Projects* in the console, or pass `--cli-project-id`.
4. **IAM permissions** (least privilege, see `references/iam-policies.md`):
   - Read/query: `waf:instance:list`, `waf:host:list`, `waf:policy:list`, `waf:rule:list`,
     `antiddos:instance:list`, `antiddos:ip:list`, `antiddos:package:list`, and `eps:*:get`.
   - Write (rule create/delete): `waf:rule:create`, `waf:rule:delete`.
5. **AAD package context**: AAD is region-based (`cn-north-4`, `ap-southeast-1`, ...). Use
   `hcloud AAD ListPackage` to see purchased packages before checking protection coverage.
6. **Quality reporting environment variables** (optional):

   | Environment Variable | Required | Description |
   |---------------------|----------|-------------|
   | `SKILL_QUALITY_ENDPOINT` | No | Report endpoint; default `https://skillsapi.developer.myhuaweicloud.com/api/quality/report` |
   | `SKILL_QUALITY_NAME` | No | Skill name (auto-detected by default) |
   | `SKILL_QUALITY_DISABLE` | No | Set to `1` to disable reporting (local debugging) |
   | `SKILL_QUALITY_TIMEOUT` | No | Report timeout in seconds (default 3) |

## Action Map (17 actions)

| R-level | Category | Action | Backing CLI operation(s) |
|---------|----------|--------|--------------------------|
| R3 (read-only, auto) | Query | `huawei_list_waf_instances` | `WAF ListInstance`, `WAF ListCompositeHosts`, `WAF ShowCompositeHost` |
| R3 | Query | `huawei_list_waf_policies` | `WAF ListPolicy` |
| R3 | Query | `huawei_list_waf_custom_rules` | `WAF ListCustomRules` |
| R3 | Query | `huawei_list_waf_whiteblackip_rules` | `WAF ListWhiteblackipRule` |
| R3 | Query | `huawei_list_waf_cc_rules` | `WAF ListCcRules` |
| R3 | Query | `huawei_list_waf_geo_rules` | `WAF ListGeoipRule` |
| R3 | Query | `huawei_list_aad_instances` | `AAD ListInstance`, `AAD ListPackage` |
| R3 | Diagnose | `huawei_analyze_waf_cname_status` | `WAF ListCompositeHosts`, `WAF ShowCompositeHost` |
| R3 | Diagnose | `huawei_analyze_waf_rule_order` | `WAF ListCustomRules`, `WAF ListWhiteblackipRule`, `WAF ListCcRules`, `WAF ListGeoipRule` |
| R3 | Diagnose | `huawei_analyze_aad_protection` | `AAD ListInstance`, `AAD ListProtectedIp`, `AAD ListUnboundProtectedIp` |
| R2 (preview + confirm) | Manage | `huawei_create_waf_custom_rule` | `WAF BatchCreateCustomRule` |
| R2 | Manage | `huawei_create_waf_ip_blacklist_rule` | `WAF BatchCreateWhiteblackipRule` |
| R2 | Manage | `huawei_create_waf_cc_rule` | `WAF BatchCreateCcRule` |
| R2 | Manage | `huawei_create_waf_geo_rule` | `WAF BatchCreateGeoIpRule` |
| R2 | Manage | `huawei_create_aad_instance` | **Console-only — no CLI** (see note below) |
| R1 (preview + explicit confirm) | Delete | `huawei_delete_waf_rule` | `WAF DeleteCustomRule` / `DeleteWhiteBlackIpRule` / `DeleteCcRule` / `DeleteGeoipRule` |
| R1 (preview + explicit confirm) | Delete | `huawei_delete_aad_instance` | **Console-only — no CLI** (see note below) |

> **AAD instance creation/deletion (mandatory limitation):** `hcloud AAD` does **not** support
> `CreateInstance` or `DeleteInstance` (verified on KooCLI 7.2.12: `[USE_ERROR]Operation
> CreateInstance is not supported.`). AAD instances are purchased as period packages (包周期) in the
> **console**: *Console → Security → Anti-DDoS → Anti-DDoS Instance → Purchase instance*; to delete,
> unsubscribe/退订 via *Anti-DDoS Instance → More → Unsubscribe*. `huawei_create_aad_instance` and
> `huawei_delete_aad_instance` SHALL NOT be routed to any made-up CLI command. Instead:
>
> - List purchased packages: `hcloud AAD ListPackage --cli-region=<region>` (see Core Commands)
> - Check current coverage: `hcloud AAD ListInstance` + `hcloud AAD ListProtectedIp`

## Workflow

```text
1. Identify context -> region (--cli-region), project_id (--project_id), and the resource to act on
   (WAF instance/host, policy, rule type; or AAD package/EIP)
2. Query phase (R3, auto)   -> list WAF instances/hosts/policies/rules or AAD instances/packages
3. Diagnose phase (R3, auto)
   a. CNAME status  -> ListCompositeHosts, then ShowCompositeHost for each protected domain:
      check cname + protocol/access-status; warn if DNS does not point to the WAF endpoint
   b. Rule order    -> list rules of the target policy, order by priority; flag
      block rules sitting above log/allow rules or conflicting conditions (false-positive risk)
   c. AAD coverage  -> ListInstance, then ListProtectedIp per instance; ListUnboundProtectedIp to
      find unbound public IPs; warn for Standard package (single IP) vs Enterprise (网段)
4. Manage phase (R2/R1, requires confirmation)
   a. CREATE (R2): build the rule intent (policy_id, rule type, action, conditions), PREVIEW the
      exact CLI command + parameters to the user, wait for explicit confirmation, then execute.
      New rules default to action=2 (log/report) first unless the user explicitly requests block.
   b. DELETE (R1): list the exact rule to delete (type + rule_id), PREVIEW the command, wait for
      EXPLICIT confirmation ("yes, delete"), then execute.
5. Output -> structured JSON result + readable summary; report quality metrics (see Quality Reporting)
```

## Core Commands

All commands below were verified against KooCLI 7.2.12 (`hcloud <service> <Operation> --help`);
parameter names are taken verbatim from the CLI metadata. `--cli-region` is required for every
command; WAF commands additionally require `--project_id`.

### 1. WAF — Instances & Protected Domains (R3)

```bash
# Dedicated WAF instances
hcloud WAF ListInstance --cli-region={region} --project_id={project_id}

# Protected domain names (composite hosts) + CNAME onboarding status
hcloud WAF ListCompositeHosts --cli-region={region} --project_id={project_id}

# Detail of one protected domain (CNAME, protocol, protection status)
hcloud WAF ShowCompositeHost --cli-region={region} --project_id={project_id} --host_id={host_id}
```

### 2. WAF — Policies (R3)

```bash
hcloud WAF ListPolicy --cli-region={region} --project_id={project_id}
```

### 3. WAF — Rule Queries (R3)

```bash
# Custom / precise protection rules of one policy
hcloud WAF ListCustomRules --cli-region={region} --project_id={project_id} --policy_id={policy_id}

# IP blacklist / whitelist rules
hcloud WAF ListWhiteblackipRule --cli-region={region} --project_id={project_id} --policy_id={policy_id}

# CC (rate limiting) rules
hcloud WAF ListCcRules --cli-region={region} --project_id={project_id} --policy_id={policy_id}

# Geo (regional blocking) rules
hcloud WAF ListGeoipRule --cli-region={region} --project_id={project_id} --policy_id={policy_id}
```

### 4. WAF — Rule Creation (R2, preview + confirm)

```bash
# Custom (precise protection) rule — action.category: block|pass|log
# time=false -> takes effect immediately (recommended "report first": action.category=log)
hcloud WAF BatchCreateCustomRule --cli-region={region} --project_id={project_id} \
  --policy_ids.1={policy_id} --name={rule_name} --priority={priority} \
  --action.category=log --time=false \
  --conditions.1.category=url --conditions.1.logic_operation=contain --conditions.1.contents.1=/admin

# IP blacklist rule (white=0 block / 1 allow / 2 log)
hcloud WAF BatchCreateWhiteblackipRule --cli-region={region} --project_id={project_id} \
  --policy_ids.1={policy_id} --name={rule_name} --white=0 --addr=42.123.120.66

# CC (rate limiting) rule — mode=0 standard / 1 advanced; tag_type=ip|cookie|header|other|...
hcloud WAF BatchCreateCcRule --cli-region={region} --project_id={project_id} \
  --policy_ids.1={policy_id} --name={rule_name} --mode=0 \
  --limit_num=100 --limit_period=60 --tag_type=ip --action.category=log \
  --conditions.1.category=url --conditions.1.logic_operation=contain --conditions.1.contents.1=/

# Geo rule (geoip from ShowPolicyGeoipMap; white=0 block / 1 allow / 2 log)
hcloud WAF BatchCreateGeoIpRule --cli-region={region} --project_id={project_id} \
  --policy_ids.1={policy_id} --geoip={geoip} --white=0
```

> Batch-create commands add one rule to **multiple policies** at once via `--policy_ids.N`.
> If no policy exists, create one in the console first, or reuse `ListPolicy` output.

### 5. WAF — Rule Deletion (R1, preview + explicit confirm)

```bash
# Delete a custom rule (rule_id from ListCustomRules)
hcloud WAF DeleteCustomRule --cli-region={region} --project_id={project_id} \
  --policy_id={policy_id} --rule_id={rule_id}

# Delete an IP black/white list rule (rule_id from ListWhiteblackipRule)
hcloud WAF DeleteWhiteBlackIpRule --cli-region={region} --project_id={project_id} \
  --policy_id={policy_id} --rule_id={rule_id}

# Delete a CC rule (rule_id from ListCcRules)
hcloud WAF DeleteCcRule --cli-region={region} --project_id={project_id} \
  --policy_id={policy_id} --rule_id={rule_id}

# Delete a geo rule (rule_id from ListGeoipRule)
hcloud WAF DeleteGeoipRule --cli-region={region} --project_id={project_id} \
  --policy_id={policy_id} --rule_id={rule_id}
```

### 6. AAD — Instance & Protection Queries (R3)

```bash
# AAD instances (NOTE: only --cli-region is required; AAD is region-based)
hcloud AAD ListInstance --cli-region={region}

# Anti-DDoS packages (套餐) — the ONLY supported AAD "package" management entry point
hcloud AAD ListPackage --cli-region={region}

# EIPs currently protected by a package/policy (optional filters: --package_id={package_id}, --policy_id={policy_id})
hcloud AAD ListProtectedIp --cli-region={region}

# Unbound protected IPs of a package — key input for huawei_analyze_aad_protection
hcloud AAD ListUnboundProtectedIp --cli-region={region} --package_id={package_id}
```

### AAD Instance Management (Console-only)

`hcloud AAD` does **NOT** support `CreateInstance` / `DeleteInstance` (verified: `[USE_ERROR]
Operation CreateInstance is not supported.`). **Do NOT fabricate CLI commands for these actions.**

| Intent | Supported path |
|--------|----------------|
| Create / purchase an AAD instance (包周期) | **Console**: Security → Anti-DDoS → Anti-DDoS Instance → `Purchase Anti-DDoS Instance`; select Standard (single IP) or Enterprise (whole 网段) package |
| Delete / unsubscribe an AAD instance | **Console**: Anti-DDoS Instance → select instance → More → `Unsubscribe` (退订) |
| Verify packages after purchase | `hcloud AAD ListPackage --cli-region={region}` |
| Verify protection coverage (alternative diagnostic path) | `hcloud AAD ListInstance` + `hcloud AAD ListProtectedIp` + `hcloud AAD ListUnboundProtectedIp` |

## Parameter Confirmation

All parameter names below are verified against `hcloud <service> <Operation> --help` (KooCLI 7.2.12).
`{region}` / `{project_id}` are context values; obtain the project ID from *My Credentials → Projects*.

### WAF List / Show (query, R3)

| Command | Required params | Optional params |
|---------|-----------------|-----------------|
| `ListCompositeHosts` | `--cli-region`, `--project_id` | `--enterprise_project_id`, `--hostname`, `--is_https`, `--page`, `--pagesize`, `--policyname`, `--protect_status`, `--waf_type` |
| `ListInstance` | `--cli-region`, `--project_id` | `--enterprise_project_id`, `--instancename`, `--page`, `--pagesize` |
| `ShowCompositeHost` | `--cli-region`, `--project_id`, `--host_id` | `--enterprise_project_id` |
| `ListPolicy` | `--cli-region`, `--project_id` | `--enterprise_project_id`, `--name`, `--page`, `--pagesize` |
| `ListCustomRules` | `--cli-region`, `--project_id`, `--policy_id` | `--enterprise_project_id`, `--limit`, `--offset`, `--page`, `--pagesize` |
| `ListWhiteblackipRule` | `--cli-region`, `--project_id`, `--policy_id` | `--enterprise_project_id`, `--name`, `--page`, `--pagesize` |
| `ListCcRules` | `--cli-region`, `--project_id`, `--policy_id` | `--category`, `--enterprise_project_id`, `--limit`, `--name`, `--offset`, `--page`, `--pagesize`, `--status`, `--tag_type` |
| `ListGeoipRule` | `--cli-region`, `--project_id`, `--policy_id` | `--enterprise_project_id`, `--page`, `--pagesize` |

### WAF BatchCreate (write, R2 — indexable array params use `.N` suffix)

| Command | Required params | Key optional params |
|---------|-----------------|---------------------|
| `BatchCreateCustomRule` | `--cli-region`, `--project_id`, `--policy_ids.N`, `--name`, `--priority`, `--action.category` (block\|pass\|log), `--time` (bool) | `--conditions.N.category`, `--conditions.N.contents.N`, `--conditions.N.index`, `--conditions.N.logic_operation`, `--conditions.N.value_list_id`, `--action.followed_action_id`, `--description`, `--enterprise_project_id`, `--start`, `--terminal` |
| `BatchCreateWhiteblackipRule` | `--cli-region`, `--project_id`, `--policy_ids.N`, `--name`, `--white` (0 block / 1 allow / 2 log) | `--addr` (IP or CIDR), `--description`, `--enterprise_project_id`, `--ip_group_id`, `--policyids.N`, `--start`, `--terminal`, `--time_mode` (permanent\|customize) |
| `BatchCreateCcRule` | `--cli-region`, `--project_id`, `--policy_ids.N`, `--name`, `--mode` (0 standard / 1 advanced), `--limit_num` (1–2147483647), `--limit_period` (1–3600 s), `--tag_type` (ip\|cookie\|header\|other\|policy\|domain\|url), `--action.category` (captcha\|block\|log\|dynamic_block), `--conditions.N.category`, `--conditions.N.logic_operation` | `--action.detail.response.content`, `--action.detail.response.content_type`, `--cc_priority`, `--conditions.N.contents.N`, `--conditions.N.index`, `--conditions.N.value_list_id`, `--description`, `--domain_aggregation`, `--enterprise_project_id`, `--lock_time`, `--priority`, `--region_aggregation`, `--tag_index`, `--unlock_num` |
| `BatchCreateGeoIpRule` | `--cli-region`, `--project_id`, `--policy_ids.N`, `--geoip`, `--white` (0 block / 1 allow / 2 log) | `--description`, `--enterprise_project_id`, `--ip_type` (v4\|v6\|any), `--name` |

### WAF Delete (write, R1)

| Command | Required params | Optional params |
|---------|-----------------|-----------------|
| `DeleteCustomRule` / `DeleteWhiteBlackIpRule` / `DeleteCcRule` / `DeleteGeoipRule` | `--cli-region`, `--project_id`, `--policy_id`, `--rule_id` | `--enterprise_project_id` |

### AAD (query, R3)

| Command | Required params | Optional params |
|---------|-----------------|-----------------|
| `ListInstance` | `--cli-region` | — |
| `ListPackage` | `--cli-region` | — |
| `ListProtectedIp` | `--cli-region` | `--ip`, `--limit`, `--offset`, `--package_id`, `--policy_id`, `--tag` |
| `ListUnboundProtectedIp` | `--cli-region`, `--package_id` | `--limit`, `--offset` |

> `CreateInstance` / `DeleteInstance` for AAD: **do not exist in the CLI** — see the console-only
> section above. Never guess or fabricate their parameters.

## KooCLI Command Format Standard

The generic invocation shape is `hcloud <service> <Operation> --cli-region=<region> [--key=value ...]`
— this is a **format description only**: `<...>` and `[--key=value]` are placeholders, never executed verbatim.

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `WAF`, `AAD` (as detected from KooCLI 7.2.12 metadata) | `hcloud WAF ...` |
| Operation name | PascalCase | `ListCompositeHosts`, `BatchCreateCcRule` |
| Region parameter | `--cli-region=<value>` (required; profile value used if omitted) | `--cli-region=cn-north-4` |
| Project ID | `--project_id=<value>` (required for WAF) | `--project_id=a1b2...` |
| Simple parameter | `--key=value` | `--policy_id=p1` |
| Indexed parameter (array) | `--key.N=valueN` | `--policy_ids.1=pol1`, `--conditions.1.contents.1=/admin` |

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution quality
reporting. Every run automatically reports trace_id, status (success/biz_fail/sys_fail/cancel),
error code, cost, and masked input/output to the operations console.

### Integration

**Python entry point** — wrap main logic with the `quality_context` context manager:

```python
from skill_quality_sdk import quality_context, QualityError

with quality_context(skill_name="huawei-cloud-waf-aad-rule-management", skill_version="1.0.0") as q:
    q.input = {"action": "huawei_list_waf_policies", "region": "cn-north-4"}
    result = do_something()
    q.output = result
```

**CLI-only Skill** — the SDK is vendored in `scripts/` for future Python wrapper use. Pure CLI
invocations in this skill do not call the SDK directly; the Agent wraps its own execution.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

Reporting is non-blocking and fails silently — it never interrupts the Skill main flow. Disable via
`SKILL_QUALITY_DISABLE=1` for local testing.

## Reference Documents

- `references/cli-installation-guide.md` — KooCLI installation, AK/SK & profile authentication
- `references/iam-policies.md` — Least-privilege IAM policies for WAF/AAD read & write
- `references/verification-method.md` — How to verify this skill (read-only checks, dry-run, confirm flows)
- `references/dataflow-diagram.md` — Mermaid data-flow diagram (query / diagnose / manage)
- `references/acceptance-criteria.md` — Acceptance criteria mapped to the 17 actions
- `references/related-commands.md` — Auxiliary commands (`ShowPolicyGeoipMap`, EPS, DNS/EIP context)

## Related Commands (auxiliary)

```bash
# Query supported geo regions for geo rules (source of {geoip} values)
hcloud WAF ShowPolicyGeoipMap --cli-region={region} --project_id={project_id}

# Confirm the authenticated profile / region
hcloud configure list
```
