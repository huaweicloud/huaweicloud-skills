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
triggers: ["WAF", "Web应用防火墙", "Web Application Firewall", "AAD", "Anti-DDoS", "抗DDoS", "DDoS防护", "防火墙", "web protection", "IP黑名单", "IP白名单", "blacklist", "whitelist", "CC防护", "CC攻击", "限速", "rate limiting", "地域封禁", "geo rule", "CNAME接入", "WAF诊断", "规则顺序", "误报", "EIP防护", "防护覆盖", "waf aad", "huawei-cloud-waf-aad-rule-management"]
---

# Huawei Cloud WAF / AAD Skill (huawei-cloud-waf-aad-rule-management)

<!-- cli-install-version: 3.7.3 -->
## 第一步：安装 skill-quality-cli（幂等，已安装则跳过）

```bash
source scripts/ensure_cli.sh
```

> 脚本自动检测 `skill-quality-cli` 是否可用（PATH 或 CLI 安装目录双通道检测）。已安装则直接可用；未安装时不执行任何运行时下载，仅提示按 `references/cli-installation-guide.md` 的「安装 skill-quality-cli（固定版本 v1.1.6，SHA256 校验）」手动安装（固定版本 + SHA256 校验，禁止未校验的运行时下载）。CLI 缺失或网络不可用时跳过质量上报，不阻塞业务执行。
> 用 `source` 执行可让 CLI 安装目录自动加入当前会话 PATH；若环境不支持 source，改用 `bash scripts/ensure_cli.sh`，随后命令报 `command not found` 时先执行 `export PATH="$HOME/.local/bin:$PATH"` 再调用 `skill-quality-cli`。

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

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

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
   - a **local hcloud profile** (user-managed): check existence with `hcloud configure list`; the
     skill/agent **never** writes credentials (`hcloud configure set` is forbidden inside the skill
     or any script). If no profile is configured, ask the user to configure one themselves with
     `hcloud configure init` (or export AK/SK env vars) and confirm before continuing — credentials
     are read from the environment or the user's own local profile only (do not hardcode them anywhere).
3. **Region & project**: WAF operations take `--project_id` (path parameter) plus `--cli-region`.
   KooCLI automatically uses the default project of the authenticated profile when `--project_id` is
   omitted (verified on KooCLI 7.2.12), so the command examples in this skill omit it; multi-project
   accounts may append `--project_id=<project_id>` explicitly. To list projects, see the console
   (*My Credentials → Projects*).
4. **IAM permissions** (least privilege, see `references/iam-policies.md`):
   - Read/query: `waf:instance:list`, `waf:host:list`, `waf:policy:list`, `waf:rule:list`,
     `antiddos:instance:list`, `antiddos:ip:list`, `antiddos:package:list`, and `eps:*:get`.
   - Write (rule create/delete): `waf:rule:create`, `waf:rule:delete`.
5. **AAD package context**: AAD is region-based (`cn-north-4`, `ap-southeast-1`, ...). Use
   `hcloud AAD ListPackage` to see purchased packages before checking protection coverage.
6. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

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
5. Output -> structured JSON result + readable summary (quality telemetry is reported automatically via the `skill-quality-cli run` wrapper)
```

## Core Commands

All commands below were verified against KooCLI 7.2.12 (`hcloud <service> <Operation> --help`);
parameter names are taken verbatim from the CLI metadata. `--cli-region` is required for every
command. For WAF, `--project_id` is a path parameter of the API; KooCLI automatically uses the
default project of the authenticated profile when it is omitted, so the examples below omit it
(multi-project accounts may append `--project_id=<project_id>` explicitly — see Parameter
Confirmation).

Each command is shown in two forms:

- the **bare `hcloud ...` command** (canonical CLI form, used by tooling and automated tests), and
- the **quality-reporting form** `skill-quality-cli run --skill-name ... -- <command>` (the
  mandated execution form at runtime).

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- ` — bare `hcloud` calls are strictly forbidden.**
> **⚠️ 强制要求：Agent/脚本运行时执行本 skill 的任何 hcloud 命令，必须用 `skill-quality-cli run` 包裹，禁止裸调 hcloud（Core Commands 中展示的裸命令仅为规范化 CLI 形式，供工具/测试流水线提取与校验；实际执行一律使用其上方对应的包裹形式）。**

> **可测试性约定（2026-09-17）**: 仅「无业务参数依赖」的查询命令给出裸命令形式，供测试流水线
> 自动提取并执行（此类命令不传业务 ID 即可真实查询）。依赖 `--policy_id` / `--host_id` /
> `--package_id` 等业务参数的查询，以及全部写操作（R2/R1），只给出 `skill-quality-cli run`
> 包裹形式 —— 它们需要真实资源 ID 或显式确认，测试流水线不应自动执行。

### 1. WAF — Instances & Protected Domains (R3)

```bash
# Dedicated WAF instances
hcloud WAF ListInstance --cli-region={region}   # 分页参数为--page/--pagesize, 该接口不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListInstance --cli-region={region}

# Protected domain names (composite hosts) + CNAME onboarding status
hcloud WAF ListCompositeHosts --cli-region={region}   # 分页参数为--page/--pagesize, 该接口不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListCompositeHosts --cli-region={region}

# Detail of one protected domain (CNAME, protocol, protection status) — needs --host_id (业务参数)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ShowCompositeHost --cli-region={region} --host_id={host_id}
```

### 2. WAF — Policies (R3)

```bash
# WAF policies of the current account
hcloud WAF ListPolicy --cli-region={region}   # 分页参数为--page/--pagesize, 该接口不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListPolicy --cli-region={region}

```

### 3. WAF — Rule Queries (R3)

> 以下规则查询都依赖 `--policy_id`（业务参数，需先 `ListPolicy` 获取真实 policy_id），
> 只给出质量上报包裹形式，不自动执行。

```bash
# Custom / precise protection rules of one policy
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListCustomRules --cli-region={region} --policy_id={policy_id}

# IP blacklist / whitelist rules
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListWhiteblackipRule --cli-region={region} --policy_id={policy_id}

# CC (rate limiting) rules
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListCcRules --cli-region={region} --policy_id={policy_id}

# Geo (regional blocking) rules
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListGeoipRule --cli-region={region} --policy_id={policy_id}
```

### 4. WAF — Rule Creation (R2, preview + confirm)

```bash
# Custom (precise protection) rule — action.category: block|pass|log
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF BatchCreateCustomRule --cli-region={region} --policy_ids.1={policy_id} --name={rule_name} --priority={priority} --action.category=log --time=false --conditions.1.category=url --conditions.1.logic_operation=contain --conditions.1.contents.1=/admin

# IP blacklist rule (white=0 block / 1 allow / 2 log)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF BatchCreateWhiteblackipRule --cli-region={region} --policy_ids.1={policy_id} --name={rule_name} --white=0 --addr=42.123.120.66

# CC (rate limiting) rule — mode=0 standard / 1 advanced; tag_type=ip|cookie|header|other|...
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF BatchCreateCcRule --cli-region={region} --policy_ids.1={policy_id} --name={rule_name} --mode=0 --limit_num=100 --limit_period=60 --tag_type=ip --action.category=log --conditions.1.category=url --conditions.1.logic_operation=contain --conditions.1.contents.1=/

# Geo rule (geoip from ShowPolicyGeoipMap; white=0 block / 1 allow / 2 log)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF BatchCreateGeoIpRule --cli-region={region} --policy_ids.1={policy_id} --geoip={geoip} --white=0

```

### 5. WAF — Rule Deletion (R1, preview + explicit confirm)

```bash
# Delete a custom rule (rule_id from ListCustomRules)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF DeleteCustomRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}

# Delete an IP black/white list rule (rule_id from ListWhiteblackipRule)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF DeleteWhiteBlackIpRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}

# Delete a CC rule (rule_id from ListCcRules)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF DeleteCcRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}

# Delete a geo rule (rule_id from ListGeoipRule)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF DeleteGeoipRule --cli-region={region} --policy_id={policy_id} --rule_id={rule_id}

```

### 6. AAD — Instance & Protection Queries (R3)

```bash
# AAD instances (NOTE: only --cli-region is required; AAD is region-based)
hcloud AAD ListInstance --cli-region={region}   # 该接口不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud AAD ListInstance --cli-region={region}

# Anti-DDoS packages (套餐) — the ONLY supported AAD "package" management entry point
hcloud AAD ListPackage --cli-region={region}   # 该接口不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud AAD ListPackage --cli-region={region}

# EIPs currently protected by a package/policy (optional filters: --package_id={package_id}, --policy_id={policy_id})
hcloud AAD ListProtectedIp --cli-region={region}   # 可选分页参数为--limit/--offset
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud AAD ListProtectedIp --cli-region={region}

# Unbound protected IPs of a package — key input for huawei_analyze_aad_protection;
# needs --package_id (业务参数), wrapper-only (not auto-executed)
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud AAD ListUnboundProtectedIp --cli-region={region} --package_id={package_id}
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

**参数校验（工具参数安全，强制）**: 所有动作参数在拼装 `hcloud` 命令前必须校验，非法输入直接拒绝并向用户说明，禁止把未经校验的参数传入命令执行：

- 枚举类参数按白名单逐一比对：`--action.category` ∈ {block, pass, log, captcha, dynamic_block}、`--white` ∈ {0,1,2}、`--mode` ∈ {0,1}、`--tag_type` ∈ {ip, cookie, header, other, policy, domain, url}、`--ip_type` ∈ {v4, v6, any}、`--time_mode` ∈ {permanent, customize}、`--logic_operation` ∈ {contain, not_contain, equal, not_equal, begin_with, not_begin_with, end_with, not_end_with}；
- 数值/格式类参数做类型与范围校验：`--priority`（整数，0–65535）、`--limit_num`（1–2147483647）、`--limit_period`（1–3600）、`--addr`（合法 IPv4/IPv6/CIDR）、`--policy_id`/`--rule_id`/`--host_id`/`--project_id`（华为云资源 UUID 格式）；
- 所有参数值来自用户输入时，先校验再使用；白名单外或格式非法的值一律拒绝。

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

## Reference Documents

- `references/cli-installation-guide.md` — KooCLI installation, AK/SK & profile authentication
- `references/iam-policies.md` — Least-privilege IAM policies for WAF/AAD read & write
- `references/verification-method.md` — How to verify this skill (read-only checks, dry-run, confirm flows)
- `references/dataflow-diagram.md` — Mermaid data-flow diagram (query / diagnose / manage)
- `references/acceptance-criteria.md` — Acceptance criteria mapped to the 17 actions
- `references/related-commands.md` — Auxiliary commands (`ShowPolicyGeoipMap`, EPS, DNS/EIP context)
- `scripts/ensure_cli.sh` — Idempotent skill-quality-cli installer (see the ⚠️ Mandatory note in Core Commands)

## Related Commands (auxiliary)

```bash
# Query supported geo regions for geo rules (source of {geoip} values)
hcloud WAF ShowPolicyGeoipMap --cli-region={region}   # 无分页参数, 不支持--limit
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ShowPolicyGeoipMap --cli-region={region}

# Confirm the authenticated profile / region
hcloud configure list   # 本地配置查看, 无--limit参数
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud configure list
```
