---
name: huawei-cloud-waf-false-alarm-diagnosis
description: |
  Diagnose Huawei Cloud WAF (Web Application Firewall) false positive blocks step by step. Use when a customer reports "normal requests blocked by WAF / returning 418 / page won't open", or asks "why is this interface blocked" — the skill locates the blocking event, judges whether it is a false positive from the payload and rule hit, walks the WAF rule priority chain (false-alarm shield / global whitelist → IP whitelist → IP blacklist → geo-blocking → precise protection → attack punishment → anti-crawler → CC protection → web basic protection) to pinpoint the blocking source, and recommends the safest release method with ready-to-run hcloud commands plus a rollback guide.
  Triggers include: "WAF误报", "误报拦截诊断", "正常请求被拦截", "正常请求被WAF拦截", "返回418", "页面打不开", "接口被拦", "接口被拦截", "被WAF拦了", "误报屏蔽", "全局白名单", "IP白名单放行", "WAF拦截", "WAF误报诊断", "false positive", "WAF block diagnosis", "418 blocked"
tags: [waf, security, false-positive, diagnosis, troubleshooting]
---

# Huawei Cloud WAF False Alarm Diagnosis (huawei-cloud-waf-false-alarm-diagnosis)

## Overview

This skill is a **read-only diagnosis workflow** for Huawei Cloud WAF (Web Application Firewall) false-positive blocking. It follows a standardized path:

**Locate blocking event → Judge whether it is a false positive → Walk the rule priority chain to pinpoint the blocking rule → Recommend the safest release method (with ready-to-run hcloud commands) → Verify by re-querying events → Output conclusion + rollback guide.**

It is designed for troubleshooting scenarios where customers report:

- "Normal requests are blocked by WAF / return HTTP 418 / the page won't open"
- "Why is this API/interface blocked?"
- "A certain request is intercepted by WAF and I want to know which rule hit it"

### Read-Only Principle — STRICTLY ENFORCED

This skill **only performs query/read operations**. It never executes `Create*`, `Update*`, `Delete*`, or any write/mutating WAF operation itself.

| Action | Allowed? |
|--------|----------|
| Query hosts/policies (`ListHost`, `ListCompositeHosts`, `ListPolicy`, `ShowPolicy`) | ✅ YES |
| Query attack events (`ListEvent`, `ShowEvent`) | ✅ YES |
| Query rules across the priority chain (`ListIgnoreRule`, `ListWhiteblackipRule`, `ListGeoipRule`, `ListCustomRules`, `ListPunishmentRules`, `ListAnticrawlerRules`, `ListCcRules`, `ListPolicyProtectRules`, `ListWebBasicProtectionRules`) | ✅ YES |
| Analyze payload / judge false positive (local logic) | ✅ YES |
| Output **ready-to-run hcloud release/rollback commands** for the user to execute themselves | ✅ YES |
| Execute any write command on behalf of the user | ❌ **NEVER** |

> If the user asks the agent to actually apply a whitelist / switch protection mode, tell them the read-only boundary of this skill and hand over the exact command; actual rule changes belong to dedicated WAF rule-management skills (the agent should orchestrate the appropriate one).

### Applicable Scenarios

- Customer reports normal business requests blocked / 418 / page won't open
- Interface / domain returns unexpected block from WAF
- Need to verify which WAF rule caused the interception and decide whether it is a false positive

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | v7.2+ (verified on KooCLI 7.3.12). Run `hcloud version`. |
| **Authentication** | AK/SK configured via `hcloud configure list` (or `hcloud configure set`), with the target region and project ID. |
| **IAM Permissions** | At least the read permissions in `references/iam-policies.md` (`waf:host:list`, `waf:policy:list`, `waf:securityEvents:list`, `waf:rule:list`, etc.). |
| **Region** | Every command takes `--cli-region={region}`; use the region where the complaining domain is protected. |

> **⚠️ Mandatory: when executing any `hcloud` command in this skill, wrap it with `skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- <hcloud 命令>` for quality reporting — bare `hcloud` calls are forbidden. `skill-quality-cli run` is a transparent telemetry bypass: it passes the `hcloud` command through unchanged (verified with `hcloud <Operation> --help`), so all commands in this document are written in canonical `hcloud` form for direct executability and correct parsing.**

```bash
hcloud version
hcloud configure list
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud version
```
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`
## Workflow

```
Step 1  Confirm domain access & protection status
   └─ ListHost / ListCompositeHosts -> host_id, policy_id, protect_status (block/log/bypass)
Step 2  Retrieve blocking events
   └─ ListEvent (domain + time window + source IP, action=block), ShowEvent for payload detail
Step 3  Judge whether it is a false positive
   └─ Analyze payload + rule hit against business context (select/limit → sqli semantic hit, etc.)
Step 4  Walk the rule priority chain to pinpoint the blocking rule
   └─ ListIgnoreRule → ListWhiteblackipRule → ListGeoipRule → ListCustomRules
      → ListPunishmentRules → ListAnticrawlerRules → ListCcRules → ListPolicyProtectRules
      → ListWebBasicProtectionRules
      (guided by the hit rule/attack type from Step 2; respect the priority chain order)
Step 5  Recommend the safest release method (read-only: output commands, never execute)
   └─ Prefer global whitelist (ignore matched feature) > IP whitelist (fixed source IP)
      > switch to log-only mode first for monitoring
Step 6  Verify by re-querying events + output conclusion & rollback guide
   └─ Re-run ListEvent in the same window; give rollback commands (delete rule / restore protect status)
```

**Rule Priority Chain (WAF blocks/resolves order, from highest to lowest relevance for release decision):**

误报屏蔽/全局白名单 (IgnoreRule) → IP 白名单 (WhiteblackipRule white=1) → IP 黑名单 (WhiteblackipRule white=0) → 地理位置封禁 (GeoipRule) → 精准防护 (CustomRule) → 攻击惩罚 (PunishmentRule) → 动态反爬 (AnticrawlerRule) → CC 防护 (CcRule) → … → Web 基础防护 (ListWebBasicProtectionRules).

When recommending a release method, prefer the **highest** entry in the chain that covers the blocking feature; **never** recommend disabling web basic protection as the first choice.

## Core Commands

> All commands below are query commands. They are written in canonical `hcloud` form and can be executed directly; when actually running them, wrap with `skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- <command>` as shown in the Prerequisites. `{region}` is the customer's WAF region.

### 1. Confirm Domain Access & Protection Status

```bash
hcloud WAF ListHost --cli-region={region} --hostname={hostname} --pagesize=100
hcloud WAF ListCompositeHosts --cli-region={region} --hostname={hostname} --pagesize=100
hcloud WAF ShowHost --cli-region={region} --instance_id={host_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ListHost --cli-region={region} --hostname={hostname} --pagesize=100
```

Extract: `host_id`/`instance_id`, `policy_id`, `protect_status` (1=enabled/block, 0=suspended/log, -1=bypass), `access_code`, WAF mode (CLOUD/PREMIUM/ELB). If the domain has **N/A** protect status or is not listed, the domain may be accessed in another region or not yet protected — report this as a prerequisite finding.

### 2. Retrieve Blocking Events

```bash
hcloud WAF ListEvent --cli-region={region} --domains.1={hostname} --from={from_ms} --to={to_ms} --sip={source_ip} --actions.1=block --pagesize=100
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ListEvent --cli-region={region} --domains.1={hostname} --from={from_ms} --to={to_ms} --sip={source_ip} --actions.1=block --pagesize=100
```

> - `--from`/`--to` are millisecond timestamps; max window is 30 days; **ListEvent caps at 10,000 events** — split long windows into day-by-day chunks (`from=t0 .. to=t0+1d`, then advance) and page through with `--page` until fewer than `--pagesize` events return.
> - Filter options: `--sip`/`--sips.N` (source IP), `--attacks.N` (e.g. `sqli`, `xss`, `cc`, `custom_*`), `--url`/`--urls.N`, `--query_mode=equal|include`, `--sort_key=attack_time|sort_ip|host|geo_str|component|rule|attack`, `--sort_direction=desc|asc`.
> - To inspect the malicious payload of a specific hit, fetch the event detail:

```bash
hcloud WAF ShowEvent --cli-region={region} --eventid={event_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ShowEvent --cli-region={region} --eventid={event_id}
```

Extract per event: `id`, `rule` (hit rule ID), `attack`/`attack_type`, `action`, `url`, `payload` (attack fragment), `sip`, `time`, `host`, `geo`. The `rule`/`attack_type` pair drives Step 3 and Step 4.

### 3. Judge Whether It Is a False Positive

Analyze locally (no extra API): combine `rule` + `attack_type` + `payload` + `url` with the business context the customer describes.

**Patterns that suggest a POSSIBLE FALSE POSITIVE:**

| Pattern | Example | Likely rule family |
|---------|---------|--------------------|
| Normal business parameters hit SQL-injection semantic character groups | URL arg contains `select`+`limit`, `id=1 and 1=1`-like fragments in legit query params | Web basic protection `sqli` |
| Static resources / framework paths look like attack payloads | `/wp-content/`, `.php`, `../`, `alert(` in a legit filename | Web basic `ptr`/`xss`/`rce` |
| Known security/spider User-Agent blocked | scanning UA of a legit monitoring/security component | `robot`/`anticrawler` |
| IP belongs to cloud/vendor ranges the customer uses | office/IDC egress IP matched `iprank` or geo rules | `iprank`/`custom_geoip`/`custom_blackip` |
| A single request action=block but request is normal idempotent API call | `GET /api/order/query` blocked by a `custom_custom` precise rule keyword | `custom_custom` |
| High-frequency legit access rate-limited | bulk data sync / pagination rapid paging | `cc` |

**Output of this step:** verdict `疑似误报 YES / 非误报 NO / 不确定 UNCERTAIN`, the evidence (hit rule + payload + business rationale), and which rule family needs attention.

### 4. Pinpoint the Blocking Rule along the Priority Chain

With `policy_id` and the suspected rule family from Step 3, list the rules in priority-chain order (top to bottom). Query only the families relevant to the hit; when unsure, run all of them:

```bash
hcloud WAF ListIgnoreRule --cli-region={region} --policy_id={policy_id}
hcloud WAF ListWhiteblackipRule --cli-region={region} --policy_id={policy_id}
hcloud WAF ListGeoipRule --cli-region={region} --policy_id={policy_id}
hcloud WAF ListCustomRules --cli-region={region} --policy_id={policy_id}
hcloud WAF ListPunishmentRules --cli-region={region} --policy_id={policy_id}
hcloud WAF ListAnticrawlerRules --cli-region={region} --policy_id={policy_id}
hcloud WAF ListCcRules --cli-region={region} --policy_id={policy_id}
hcloud WAF ListPolicyProtectRules --cli-region={region} --rule_type={rule_type} --policyids={policy_id}
hcloud WAF ListWebBasicProtectionRules --cli-region={region} --protection_type_names={sqli|xss|...}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ListIgnoreRule --cli-region={region} --policy_id={policy_id}
```

> - `--policyids` is a **comma-separated string** (NOT the indexed `--policyids.1=` form): single policy `--policyids={policy_id}`, multiple `--policyids=a,b,c`.
> - `--rule_type` accepts **only** the enum `cc|custom|whiteblackip|privacy|ignore|geoip|antitamper|antileakage|ip-reputation`. There is **no `basic` value** — query Web基础防护 (Web basic protection) built-in rules via the dedicated `ListWebBasicProtectionRules` API (see the command above), filtering by `--protection_type_names` (e.g. `sqli`, `xss`, `cmdi`) as needed.

Optionally confirm the module toggles and default action with the policy detail:

```bash
hcloud WAF ShowPolicy --cli-region={region} --policy_id={policy_id}
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ShowPolicy --cli-region={region} --policy_id={policy_id}
```

Correlate the `rule` ID from Step 2 with the returned rules. For each candidate rule record its name, condition, action, status (0=disabled, 1=enabled), and priority. Determine **which rule actually produced action=block for the reported request**.

### 5. Recommend the Safest Release Method (read-only)

Recommendations are **recommendations only** — the agent must NOT execute write commands. Based on the pinpointed rule and whether the user confirmed it is a false positive:

| Situation | Recommended release (order of preference) | Ready-to-run hcloud command |
|-----------|------------------------------------------|------------------------------|
| Blocked feature can be ignored generally (e.g. a specific URL/keyword false hit) | **Global whitelist (ignore rule)** — ignore the specific matched feature | `hcloud WAF CreateIgnoreRule --cli-region={region} --policy_id={policy_id} --conditions.1.category={category} --conditions.1.logic_operation={logic} --conditions.1.contents.1={content} --rule={rule_id}` |
| Source IP is fixed (office / API client) | **IP whitelist** for that IP/CIDR | `hcloud WAF CreateWhiteblackipRule --cli-region={region} --policy_id={policy_id} --name={name} --white=1 --addr={ip_or_cidr}` |
| Need monitoring before any change | **Switch domain to log-only mode first** (logs events without blocking) | `hcloud WAF UpdateHostProtectStatus --cli-region={region} --instance_id={host_id} --protect_status=0` |
| Not a false positive | Keep blocking; advise security team; do not release | — |

> Recommend the **highest-priority** entry that matches; prefer global whitelist over IP whitelist over mode switching. Always suggest **log-only mode monitoring** before applying a permanent whitelist when confidence is low.

### 6. Verify, Conclude, and Give a Rollback Guide

After the user executes the chosen release command, **re-run the Step 2 event query** in the same domain/IP/time window and compare hit counts before/after:

```bash
hcloud WAF ListEvent --cli-region={region} --domains.1={hostname} --from={from_ms} --to={to_ms} --sip={source_ip} --actions.1=block
# Quality-reporting wrapper (reporting bypass, command unchanged):
#   skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- hcloud WAF ListEvent --cli-region={region} --domains.1={hostname} --from={from_ms} --to={to_ms} --sip={source_ip} --actions.1=block
```

Output the final report: event comparison (before/after), whether release took effect, summary conclusion, and a **rollback guide**:

| Rollback action | Command |
|-----------------|---------|
| Delete the ignore rule | `hcloud WAF DeleteIgnoreRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}` |
| Delete the IP whitelist rule | `hcloud WAF DeleteWhiteBlackIpRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}` |
| Restore protection (from log-only back to enabled/block) | `hcloud WAF UpdateHostProtectStatus --cli-region={region} --instance_id={host_id} --protect_status=1` |

## Parameter Confirmation

| Command | Required (always) | Optional (frequently used) |
|---------|-------------------|----------------------------|
| `hcloud WAF ListHost` | `--cli-region` (`--project_id` auto from profile) | `--hostname`, `--page`, `--pagesize`, `--policyname`, `--enterprise_project_id` |
| `hcloud WAF ListCompositeHosts` | `--cli-region` | `--hostname`, `--page`, `--pagesize`, `--protect_status`, `--waf_type` |
| `hcloud WAF ShowHost` | `--cli-region`, `--instance_id` | `--enterprise_project_id` |
| `hcloud WAF ListEvent` | `--cli-region` | `--from`, `--to`, `--recent`, `--domains.N` (use `--domains.1=`, NOT `--domain=`, which clashes with the KooCLI system parameter), `--hosts.N`, `--sip`, `--sips.N`, `--actions.N`, `--attacks.N`, `--url`, `--page`, `--pagesize`, `--query_mode`, `--sort_key`, `--sort_direction` |
| `hcloud WAF ShowEvent` | `--cli-region`, `--eventid` | `--enterprise_project_id` |
| `hcloud WAF ListIgnoreRule` | `--cli-region`, `--policy_id` | `--page`, `--pagesize` |
| `hcloud WAF ListWhiteblackipRule` | `--cli-region`, `--policy_id` | `--name`, `--page`, `--pagesize` |
| `hcloud WAF ListGeoipRule` | `--cli-region`, `--policy_id` | `--page`, `--pagesize` |
| `hcloud WAF ListCustomRules` | `--cli-region`, `--policy_id` | `--limit`, `--offset`, `--page`, `--pagesize` |
| `hcloud WAF ListPunishmentRules` | `--cli-region`, `--policy_id` | `--limit`, `--offset`, `--page`, `--pagesize` |
| `hcloud WAF ListAnticrawlerRules` | `--cli-region`, `--policy_id` | `--type`, `--limit`, `--offset` |
| `hcloud WAF ListCcRules` | `--cli-region`, `--policy_id` | `--category`, `--tag_type`, `--status`, `--name`, `--page` |
| `hcloud WAF ListPolicyProtectRules` | `--cli-region`, `--rule_type` | `--policyids` (comma-separated), `--page`, `--pagesize` |
| `hcloud WAF ListWebBasicProtectionRules` | `--cli-region` | `--protection_type_names`, `--application_type_names`, `--cve_number`, `--level`, `--risk_level`, `--id`, `--limit`, `--offset` |
| `hcloud WAF ShowPolicy` | `--cli-region`, `--policy_id` | `--enterprise_project_id` |

## CLI Quality Reporting

This skill reports execution quality to the Huawei Cloud skill telemetry. It is fully automatic and does not change business behavior:

1. `scripts/ensure_cli.sh` (idempotent) prepares `skill-quality-cli` — run it once if it is not installed:

```bash
source scripts/ensure_cli.sh
```

2. When executing, `hcloud` business commands are wrapped with the quality-reporting prefix `skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- <command>` (the canonical command is unchanged; each command block shows the wrapper in a comment). Never invoke bare `hcloud` for the business flow of this skill.
3. To disable telemetry: `export SKILL_QUALITY_REPORT=0`.

See `references/cli-installation-guide.md` for installing `skill-quality-cli` at a pinned version with SHA256 verification.

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Diagnosis workflow data-flow diagram (Mermaid) |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policy for this skill |
| [references/verification-method.md](references/verification-method.md) | How to verify the skill works |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for diagnosis results |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Install `hcloud` and `skill-quality-cli` |

## KooCLI Command Format Standard

The canonical form of every command is `hcloud WAF <Operation> --cli-region={region} [--key=value ...]`.
When executing, prefix it with the quality-reporting wrapper: `skill-quality-cli run --skill-name huawei-cloud-waf-false-alarm-diagnosis -- <canonical command>` (the wrapped command is semantically identical).

| Item | Convention |
|------|------------|
| Service name | `WAF` (as detected in KooCLI metadata) |
| Operation name | PascalCase, e.g. `ListEvent`, `ListIgnoreRule`, `ShowEvent` |
| Region | always explicit with `--cli-region={region}` |
| Required path param `--project_id` | auto-filled from profile if omitted |
| Array params | indexed form, e.g. `--actions.1=block`, `--sips.1=1.2.3.4` |

## Troubleshooting

| Symptom | Cause | Handle |
|---------|-------|--------|
| `WAF.00012006 ... not authorized` | IAM 缺少 WAF 读权限 | 检查 `references/iam-policies.md` 并补齐策略 |
| `ListEvent` 只返回部分数据 | 单次只能查询 1 万条 | 将时间窗拆分为多段（如按天），逐段 `--from`/`--to` 查询并合并且分页 |
| Event 有 `action=log` 而非 `block` | 域名处于仅记录模式 | 告诉用户当前是仅记录模式，可能不是该域名的拦截；检查同域名其他保护实例/区域 |
| `ShowEvent` 返回为空 | eventid 不属于当前 region/project | 确认事件所在 region 与 enterprise_project |
| 域名在 `ListHost` 找不到 | 非云模式接入（独享/ELB）或不同 region | 改用 `ListCompositeHosts`，或切换 region |

## Notes

- This skill is **read-only**. All release/rollback commands are delivered as copy-paste-ready text; the agent never executes them.
- Command names and parameter names are taken verbatim from KooCLI 7.3.12 metadata; verify with `hcloud WAF <Operation> --help` if a command seems missing.
- For rule **management** (creating/updating/deleting WAF rules), orchestrate the dedicated WAF rule-management skill; this skill only diagnoses.