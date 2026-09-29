---
name: huawei-cloud-cdn-universal-query
description: |
  Comprehensive CDN query reference skill using hcloud CLI. Covers all 44 GET read-only CDN APIs organized by category: domain management, statistics & analytics, refresh/log/export, template/rule/tag/account. Provides command templates, parameter guidance, and validated pitfalls for any CDN query scenario.

  **This is a fallback skill for CDN queries. Use this when other CDN-specific skills (cdn-traffic-anomaly-analysis, cdn-502-troubleshooting, etc.) are not applicable.**

  **Do NOT use this skill for:** write/modify/delete CDN operations (POST/PUT/DELETE are always refused), non-CDN cloud service queries, or scenarios already covered by a dedicated CDN skill (e.g., cdn-traffic-anomaly-analysis, cdn-502-troubleshooting).

  Use this skill when the user wants to: (1) query CDN domain configuration, (2) check domain statistics or traffic data, (3) view refresh/preheat task history, (4) download CDN logs or export reports, (5) inspect CDN templates, rules, tags, or account quotas, (6) diagnose DNS, certificates, origin, or domain ownership, (7) look up any CDN hcloud CLI command usage.
  Triggers include: CDN查询, CDN接口, CDN CLI, 域名查询, 域名配置, 流量统计, 带宽查询, 刷新预热, 日志下载, 证书查询, 回源配置, 缓存规则, 域名归属, CDN query, CDN API reference, CDN CLI usage, domain config, traffic statistics, bandwidth query, refresh preheat, log download, certificate query, origin config
tags:
  - cdn
  - query
  - reference
  - hcloud
  - domain
  - statistics
version: 1.0.0
updated: 2026-08-31
owner: cdn-ops
---

# CDN Query Reference

## Overview

This skill is a comprehensive reference for all 44 GET read-only CDN APIs available via hcloud CLI. It serves as a fallback skill for agents to look up the correct command syntax, required parameters, and known pitfalls when querying any CDN information.

**Key Features:**

- Complete coverage of 44 GET CDN APIs (all validated end-to-end)
- Organized by 4 functional categories: Domain Management (14), Statistics & Analytics (12), Refresh/Log/Export (8), Template/Rule/Tag/Account (10)
- Command templates with parameter guidance
- 12 validated pitfalls and troubleshooting notes
- Test domain references for validation
- Explicit declaration of all 55 prohibited non-GET operations (see [references/prohibited-operations.md](references/prohibited-operations.md))

**Tool**: hcloud CLI (KooCLI v7.2.12)
**Scope**: Read-only GET operations only
**Region**: Recommended to use `--cli-region=<region>` for CDN APIs

## Triggers

**Chinese triggers:** CDN查询, CDN接口, CDN CLI, 域名查询, 域名配置, 流量统计, 带宽查询, 刷新预热, 日志下载, 证书查询, 回源配置, 缓存规则, 域名归属
**English triggers:** CDN query, CDN API reference, CDN CLI usage, domain config, traffic statistics, bandwidth query, refresh preheat, log download, certificate query, origin config

**Example user phrases (中/EN):**

- "查一下我这个域名的 CDN 配置" / "Check the CDN configuration of my domain"
- "看看昨天域名的流量和带宽" / "Show yesterday's traffic and bandwidth"
- "刷新预热任务的历史记录" / "List refresh/preheat task history"
- "帮我下载 CDN 日志 / 导出统计报表" / "Download CDN logs or export statistics"
- "这个 IP 是不是华为云 CDN 的节点" / "Check if this IP belongs to Huawei Cloud CDN"
- "查一下账户的 CDN 配额" / "Query the CDN account quota"

## Near-miss / Do NOT Use

**Fallback skill:** this is a read-only CDN query reference — prefer a dedicated
skill when one covers the scenario (`cdn-traffic-anomaly-analysis`,
`cdn-502-troubleshooting`, or any other applicable CDN skill).

**Do NOT use for:**

| Scenario | Action |
|----------|--------|
| Create/modify/delete CDN resources (POST/PUT/DELETE) | **Refuse** — strictly read-only (see [references/prohibited-operations.md](references/prohibited-operations.md)) |
| Non-CDN Huawei Cloud queries (ECS, OBS, VPC, etc.) | Use the corresponding service skill |
| CDN console operations / account management | Direct the user to the Huawei Cloud CDN console |
| Queries beyond read-only reference | Out of scope; query reference only |

**Near-miss handling:** requests that sound like queries but are actually
writes (e.g., "create a refresh task", "update cache rules", "delete a domain")
are prohibited — refuse and inform, never construct or simulate the command.

## ⛔ Prohibited Operations (Security Constraints)

> **This skill is strictly read-only.** All non-GET operations (POST/PUT/DELETE) are prohibited regardless of user request. The skill must refuse and direct the user to the Huawei Cloud CDN console or manual hcloud CLI for any write/modify/delete operation.

**Total: 55 prohibited operations** (24 POST + 25 PUT + 6 DELETE).

For the complete list of all prohibited non-GET operations with risk descriptions, see [references/prohibited-operations.md](references/prohibited-operations.md).

**Representative prohibited operations (full list in the reference doc):**

| Prohibited Operation | API/Command | Reason |
|---------------------|-------------|--------|
| ❌ Create domain | `CreateDomain` (v1/v2), `CreateDomainByDuplicate` | Write operation; requires explicit authorization |
| ❌ Delete domain | `DeleteDomain` (v1/v2) | Irreversible; removes domain from CDN |
| ❌ Modify domain config | `UpdateDomainFullConfig` (v1/v2), `UpdateDomainOrigin`, `UpdateCacheRules`, etc. | Write operations; may affect production traffic |
| ❌ Enable/Disable domain | `EnableDomain` (v1/v2), `DisableDomain` (v1/v2) | Affects production traffic |
| ❌ Modify billing mode | `SetChargeModes` | Financial impact; requires explicit authorization |
| ❌ Create refresh/preheat tasks | `CreateRefreshTasks` (v1/v2), `CreatePreheatingTasks` (v1/v2) | Write operations; affects edge cache |
| ❌ Create/update/delete templates, rules, tags | All write APIs | Write operations; requires explicit authorization |
| ❌ Batch copy domain | `BatchCopyDomain` | POST operation; misclassified in earlier versions as GET — now explicitly prohibited |
| ❌ Verify domain ownership | `VerifyDomainOwner` | POST operation; triggers verification flow |
| ❌ Set statistics config | `SetStatsConfig` | POST operation; affects account-level stats collection |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is read-only for CDN query reference. Please use the Huawei Cloud CDN console (https://console.huaweicloud.com/cdn) or run the hcloud CLI manually for configuration changes. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

### Verifying Unlisted Operations

If you need to use a CDN CLI command **not listed in this skill**, you **must** verify its HTTP method before execution:

```bash
hcloud CDN <Operation> --help
```

Review the help output and locate the `Method:` field to determine the HTTP method.

- **GET** → Allowed to execute. Document the command for future reference.
- **POST / PUT / DELETE** → **Prohibited.** Refuse and inform the user.

> **Note:** `Method:` and its value appear on **separate lines** in the help output. Check the line after `Method:` to find the HTTP method value.

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=<region> [--parameter=value ...]
```

**Format Rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ListDomains` v2, `ShowDomainDetail`, `ShowDomainStats` v2)
- **Region parameter**: `--cli-region=<region>` (recommended: cn-north-1 for CDN)
- **Parameter format**: `--key=value` (equals sign, no space)
- **Indexed parameters**: `--key.1=value1` (for array parameters)

**Examples:**

```bash
# Correct
hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=<page_size>
hcloud CDN ShowDomainStats/v2 --cli-region=<region> --domain_name=<your-domain> --stat_type=<stat_type> --interval=<interval> --start_time=<ms> --end_time=<ms> --action=<action>

# Incorrect (space instead of equals sign)
hcloud CDN ListDomains/v2 --cli-region cn-north-1
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify version >= 3.2.0. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
```

> **Prerequisite check: hcloud credentials configured**
>
> Before performing CDN operations, **you must verify hcloud credentials are configured**:
>
> ```bash
> hcloud configure list
> ```
>
> **If no valid credentials exist, stop and guide the user to configure credentials.**

> **⚠️ hcloud parameter format requirements**
>
> hcloud (KooCLI) **all parameters must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> ✅ Correct: `hcloud CDN ListDomains/v2 --cli-region=<region>`
>
> ❌ Incorrect: `hcloud CDN ListDomains/v2 --cli-region cn-north-1`

> **⚠️ CDN API region requirements**
>
> CDN APIs only support two regions: `cn-north-1` (Beijing) and `ap-southeast-1` (Singapore).
> Query results are region-independent (CDN is a global service).
> **Recommended: use `cn-north-1`**.

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials required**

> **Security rules (must be followed):**
>
> - **Prohibited** from reading, echoing, or printing AK/SK values
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
> - **Prohibited** from using `hcloud configure set` to pass plaintext credential values
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or configured CLI config files
>
> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
>
> 1. **Stop immediately** - Do not execute any commands
> 2. **Politely refuse** and return the following message:
>    ```
>    For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration (recommended)
>        hcloud configure
>        # Enter AK/SK as prompted, credentials will be securely stored in a local config file
>
>    Method 2: Environment variable configuration
>        export HUAWEICLOUD_SDK_AK=<your-access-key-id>
>        export HUAWEICLOUD_SDK_SK=<your-secret-key>
>
>    After configuration is complete, please retry your request.
>    ```
> 3. **Do not continue** executing any Huawei Cloud operations until credentials are configured
>
> **Check CLI configuration**:
>
> ```bash
>    hcloud configure list
> ```
>
>    Check whether the output contains valid configuration (AK/SK, IAM, etc.).
>
> **If no valid credentials exist, stop here.**

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions for read-only queries:**

- `cdn:*:query*` — All CDN query-class actions used by this skill (the 45 GET APIs)
- `cdn:configuration:queryDomains` — List CDN domains (listed explicitly alongside the wildcard)
- `cdn:configuration:queryChargeMode` — Query the billing mode (listed explicitly alongside the wildcard)
- `cdn:log:*` — CDN log query and download scope
- `cdn:statistics:downloadExcel` — Statistics Excel export

---

## Core Commands

Quick reference for all 44 GET CDN commands organized by category.

### Category 1: Domain Management (14 APIs)

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=<page_size>` | List all CDN domains | `--page_size`, `--page_number`, `--domain_status`, `--service_area`, `--show_tags` |
| `hcloud CDN ShowDomainDetail --cli-region=<region> --domain_id=<id>` | Get domain details by ID | `--domain_id` (required) |
| `hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>` | Get domain details by name | `--domain_name` (required); returns `domain_id` |
| `hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<domain>` | Get full domain configuration | `--domain_name`; includes HTTPS/TLS, origin, cache, etc. |
| `hcloud CDN ShowOriginHost --cli-region=<region> --domain_id=<id>` | Get origin host configuration | `--domain_id` |
| `hcloud CDN ShowCacheRules --cli-region=<region> --domain_id=<id>` | Get cache rules | `--domain_id` |
| `hcloud CDN ShowResponseHeader --cli-region=<region> --domain_id=<id>` | Get response header rules | `--domain_id` |
| `hcloud CDN ShowRefer --cli-region=<region> --domain_id=<id>` | Get referer validation config | `--domain_id` |
| `hcloud CDN ShowHttpInfo --cli-region=<region> --domain_id=<id>` | Get HTTPS certificate details | `--domain_id` |
| `hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<domain>` | Get HTTPS cert binding info | `--domain_name` |
| `hcloud CDN ShowBlackWhiteList --cli-region=<region> --domain_id=<id>` | Get IP black/white list | `--domain_id` |
| `hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<domain>` | Get domain ownership verification | `--domain_name` |
| `hcloud CDN ListDomainConfigs --cli-region=<region> --item=<item> --domain_names=<domain>` | Get specific config items | `--item`, `--domain_names` |
| `hcloud CDN ShowTags/v2 --cli-region=<region> --resource_id=<domain_id>` | Get tags for a specific domain | `--resource_id` (required, domain_id) |

📄 Detailed usage → [references/api-domain-management.md](references/api-domain-management.md)

### Category 2: Statistics & Analytics (12 APIs)

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ShowChargeModes --cli-region=<region> --product_type=<product_type>` | Get account billing mode | `--product_type` (required), `--service_area` |
| `hcloud CDN ShowDomainStats/v2 --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --interval=<interval> --start_time=<ms> --end_time=<ms> --action=<action>` | Get domain statistics | `--domain_name`, `--stat_type`, `--interval`, `--start_time`, `--end_time`, `--action` (REQUIRED) |
| `hcloud CDN ShowBandwidthCalc --cli-region=<region> --calc_type=<calc_type> --domain_name=<domain> --start_time=<ms> --end_time=<ms>` | Get bandwidth calculation | `--calc_type`, `--domain_name`, `--start_time`, `--end_time`; max 31-day range |
| `hcloud CDN ShowTopDomainNames --cli-region=<region> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms> --limit=10` | Get top domains by metric | `--stat_type`, `--start_time`, `--end_time`, `--limit`; max 1-day span |
| `hcloud CDN ListCdnDomainTopIps --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top IPs | `--domain_name`, `--stat_type`, `--start_time`, `--end_time` |
| `hcloud CDN ListCdnDomainTopPath --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top URL paths | `--domain_name`, `--stat_type`, `--start_time`, `--end_time` |
| `hcloud CDN ListCdnDomainTopUas --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top User-Agents | `--domain_name`, `--stat_type`, `--start_time`, `--end_time` |
| `hcloud CDN ListCdnDomainTopRefers --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top Referers | `--domain_name`, `--stat_type`, `--start_time`, `--end_time`; max 2 calls/s |
| `hcloud CDN ListCdnDomainTopOriginUrl --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top origin URLs | `--domain_name`, `--stat_type`, `--start_time`, `--end_time` |
| `hcloud CDN ShowTopUrl/v2 --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>` | Get top URLs (v2) | `--domain_name`, `--stat_type`, `--start_time`, `--end_time` |
| `hcloud CDN ShowDomainLocationStats/v2 --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms> --action=<action> --group_by=<group_by>` | Get geo/ISP stats | `--domain_name`, `--stat_type`, `--start_time`, `--end_time`, `--action`, `--group_by`, `--ip_version` (IPv4/IPv6) |
| `hcloud CDN ShowDomainCountryStat --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms> --action=<action> --group_by=<group_by> --country=<country>` | Get country stats | `--domain_name`, `--stat_type`, `--start_time`, `--end_time`, `--action`, `--group_by`, `--country`; may return empty |

📄 Detailed usage → [references/api-statistics.md](references/api-statistics.md)

### Category 3: Refresh / Log / Export (8 APIs)

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ShowHistoryTasks/v2 --cli-region=<region> --page_number=<page_number> --page_size=<page_size>` | Get refresh/preheat task history | `--page_number`, `--page_size` (MUST pass together) |
| `hcloud CDN ShowHistoryTaskDetails/v2 --cli-region=<region> --history_tasks_id=<id>` | Get task details | `--history_tasks_id` (required) |
| `hcloud CDN ShowUrlTaskInfo/v2 --cli-region=<region> --start_time=<ms> --end_time=<ms> --limit=10` | Get URL task info | `--start_time`, `--end_time`, `--limit`; time span ≤ 24 hours |
| `hcloud CDN ListBanUrl --cli-region=<region> [--start_time=<ms> --end_time=<ms> --url=<url> --page_number=<n> --page_size=<n>]` | Get banned URL list | All 5 filter params optional: `--start_time`, `--end_time`, `--url`, `--page_number`, `--page_size` |
| `hcloud CDN ShowLogs/v2 --cli-region=<region> --domain_name=<domain> --start_time=<ms> --end_time=<ms>` | Get CDN logs | `--domain_name`, `--start_time`, `--end_time`; domain must NOT belong to enterprise project |
| `hcloud CDN ListExportTasks --cli-region=<region> --task_id=<id> --task_name=<name> --limit=10` | Get export task list | `--task_id`, `--task_name` (both required); `--limit`, `--offset` |
| `hcloud CDN DownloadStatisticsExcel --cli-region=<region> --domain_name=<domain> --start_time=<ms> --end_time=<ms> --excel_type=<type> --cli-read-timeout=60` | Download statistics Excel | `--domain_name`, `--start_time`, `--end_time`, `--excel_type` (required: `excel_type_usage`/`excel_type_access`/`excel_type_origin`/`excel_type_http_code`); `--enterprise_project_id`, `--excel_language`, `--interval`, `--service_area` (optional); binary Excel (xlsx); needs `--cli-read-timeout=60` |
| `hcloud CDN DownloadRegionCarrierExcel --cli-region=<region> --domain_name=<domain> --start_time=<ms> --end_time=<ms> --excel_type=<type> --cli-read-timeout=60` | Download region/carrier Excel | `--domain_name`, `--start_time`, `--end_time`, `--excel_type` (required: `excel_type_usage`/`excel_type_access`/`excel_type_region`/`excel_type_carrier`/`excel_type_country`/`excel_type_top_url`); `--carrier`, `--country`, `--region`, `--enterprise_project_id`, `--excel_language`, `--interval` (optional, with dependency rules); binary Excel; needs `--cli-read-timeout=60` |

📄 Detailed usage → [references/api-refresh-log-export.md](references/api-refresh-log-export.md)

### Category 4: Template / Rule / Tag / Account (10 APIs)

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ShowDomainTemplate --cli-region=<region> --tml_type=<tml_type> --limit=10` | Get domain templates | `--tml_type` (INTEGER: 1=system, 2=user), `--limit` |
| `hcloud CDN ShowAppliedTemplateRecord --cli-region=<region> --limit=10` | Get applied template records | `--limit`, `--offset`, `--tml_id`, `--tml_name`, `--operator_id` (all optional) |
| `hcloud CDN ListRuleDetails --cli-region=<region> --domain_name=<domain>` | Get rule details | `--domain_name` |
| `hcloud CDN ListShareCacheGroups --cli-region=<region> --limit=10` | Get shared cache groups | `--limit` |
| `hcloud CDN ListSubscriptionTasks --cli-region=<region> --limit=10` | Get subscription tasks | `--limit` |
| `hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<ip1,ip2,...>` | Check if IPs belong to Huawei Cloud CDN | `--ips` (≤20 IPs, comma-separated) |
| `hcloud CDN ShowQuota/v2 --cli-region=<region>` | Get account quota | None |
| `hcloud CDN ShowSpecialUser --cli-region=<region>` | Get special user config | None |
| `hcloud CDN ListSpecialConfiguration --cli-region=<region> --domain_name=<domain>` | Get special configurations | `--domain_name` (required); `--page_number`, `--page_size` (optional) |
| `hcloud CDN ShowStatsConfigs --cli-region=<region> --config_type=<type> --limit=10` | Get statistics config | `--config_type` (required, INTEGER: 0=热点统计, 1=ces上报); `--limit`, `--offset` |

📄 Detailed usage → [references/api-template-rule-tag-account.md](references/api-template-rule-tag-account.md)

---

## Parameter Confirmation

Before executing queries, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Depends on API | Target CDN domain | None | `<your-domain>` |
| `domain_id` | Depends on API | Domain ID (get from `ShowDomainDetailByName`) | None | `<domain_id>` |
| `start_time` | Depends on API | Start timestamp (millisecond UTC) | None | `<ms>` |
| `end_time` | Depends on API | End timestamp (millisecond UTC) | None | `<ms>` |
| `stat_type` | Depends on API | Statistics type | None | `<stat_type>` |
| `interval` | Depends on API | Time interval (seconds) | None | `<interval>` |
| `action` | Depends on API | Action parameter (REQUIRED for some APIs) | None | `<action>` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User Confirmation Checklist:**

- [ ] Target domain name or ID provided (if needed)
- [ ] Time range confirmed (if needed)
- [ ] Statistics type confirmed (if needed)
- [ ] User understands this is a read-only query operation

---

## Core Workflows

### Workflow 1: Query Domain Configuration

When you need to inspect a domain's full configuration:

```bash
# Step 1: Get domain_id from domain name
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<your-domain>

# Step 2: Get full configuration
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<your-domain>

# Step 3: Get specific configurations (using domain_id from Step 1)
hcloud CDN ShowOriginHost --cli-region=<region> --domain_id=<id>
hcloud CDN ShowCacheRules --cli-region=<region> --domain_id=<id>
hcloud CDN ShowResponseHeader --cli-region=<region> --domain_id=<id>
hcloud CDN ShowRefer --cli-region=<region> --domain_id=<id>
hcloud CDN ShowHttpInfo --cli-region=<region> --domain_id=<id>
hcloud CDN ShowBlackWhiteList --cli-region=<region> --domain_id=<id>
```

📄 Detailed steps → [references/workflow-domain-config.md](references/workflow-domain-config.md)

### Workflow 2: Query Traffic Statistics

When you need to analyze domain traffic:

```bash
# Step 1: Query account billing mode
hcloud CDN ShowChargeModes --cli-region=<region> --product_type=<product_type>

# Step 2: Query daily traffic (flux) for past 7 days
hcloud CDN ShowDomainStats/v2 --cli-region=<region> --domain_name=<your-domain> --stat_type=<stat_type> --interval=<interval> --start_time=<ms> --end_time=<ms> --action=<action>

# Step 3: Query daily peak bandwidth (bw) for past 7 days
hcloud CDN ShowDomainStats/v2 --cli-region=<region> --domain_name=<your-domain> --stat_type=<stat_type> --interval=<interval> --start_time=<ms> --end_time=<ms> --action=<action>

# Step 4: Query 95th percentile bandwidth (bw_95) for a single day
hcloud CDN ShowBandwidthCalc --cli-region=<region> --calc_type=<calc_type> --domain_name=<your-domain> --start_time=<ms> --end_time=<ms>
```

📄 Detailed steps → [references/workflow-traffic-stats.md](references/workflow-traffic-stats.md)

### Workflow 3: Traffic Anomaly Drill-Down

When you detect traffic anomaly and need to drill down:

```bash
# Step 1: Get top domains by traffic (single day)
hcloud CDN ShowTopDomainNames --cli-region=<region> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms> --limit=10

# Step 2: For the anomalous domain, drill down multiple dimensions in parallel
hcloud CDN ListCdnDomainTopIps --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>
hcloud CDN ListCdnDomainTopPath --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>
hcloud CDN ListCdnDomainTopUas --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>
hcloud CDN ListCdnDomainTopRefers --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>
hcloud CDN ListCdnDomainTopOriginUrl --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms>
# action for ShowDomainLocationStats/v2: location_summary (汇总) / location_detail (详情)
hcloud CDN ShowDomainLocationStats/v2 --cli-region=<region> --domain_name=<domain> --stat_type=<stat_type> --start_time=<ms> --end_time=<ms> --action=<action> --group_by=<group_by>
```

📄 Detailed steps → [references/workflow-traffic-drilldown.md](references/workflow-traffic-drilldown.md)

### Workflow 4: Download Logs and Reports

When you need to download CDN logs or export reports:

```bash
# Step 1: Query CDN logs (domain must NOT belong to enterprise project)
hcloud CDN ShowLogs/v2 --cli-region=<region> --domain_name=<your-domain> --start_time=<ms> --end_time=<ms>

# Step 2: Download statistics Excel (binary xlsx file)
# excel_type: excel_type_usage / excel_type_access / excel_type_origin / excel_type_http_code
hcloud CDN DownloadStatisticsExcel --cli-region=<region> --domain_name=<domain> --start_time=<ms> --end_time=<ms> --excel_type=<excel_type> --cli-read-timeout=60

# Step 3: Download region/carrier Excel (binary xlsx file)
# excel_type: excel_type_usage / excel_type_access / excel_type_region / excel_type_carrier / excel_type_country / excel_type_top_url
# Note: excel_type_region requires --country=cn
hcloud CDN DownloadRegionCarrierExcel --cli-region=<region> --domain_name=<domain> --start_time=<ms> --end_time=<ms> --excel_type=<excel_type> --country=<country> --cli-read-timeout=60
```

📄 Detailed steps → [references/workflow-logs-reports.md](references/workflow-logs-reports.md)

### Workflow 5: Diagnose Domain Issues

When you need to diagnose DNS, certificate, origin, or ownership issues:

```bash
# Step 1: Get domain_id
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<your-domain>

# Step 2: Check domain ownership
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<your-domain>
hcloud CDN ListDomainConfigs --cli-region=<region> --item=<item> --domain_names=<your-domain>

# Step 3: Check DNS (if IPs belong to Huawei Cloud CDN)
hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<ip1>,<ip2>

# Step 4: Check certificate
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<your-domain>
hcloud CDN ShowHttpInfo --cli-region=<region> --domain_id=<id>

# Step 5: Check origin configuration
hcloud CDN ShowOriginHost --cli-region=<region> --domain_id=<id>
hcloud CDN ShowBlackWhiteList --cli-region=<region> --domain_id=<id>
```

📄 Detailed steps → [references/workflow-domain-diagnosis.md](references/workflow-domain-diagnosis.md)

---

## Timestamp Calculation

All CDN APIs that accept time range parameters require **millisecond-precision UTC timestamps**.

**Key rules:**

- Timestamps must be in milliseconds (e.g., `<ms>`)
- When `interval=86400`, timestamps must be aligned to UTC+8 midnight
- Different APIs have different time range limits:
  - `ShowDomainStats` (v2): `interval=86400` max 31-32 days (33 days+ returns `CDN.0203`); `interval=3600` max 7 days; `interval=300` max 2 days
  - `ShowBandwidthCalc`: max 31 days
  - `ShowTopDomainNames`: max 1 day
  - `ShowUrlTaskInfo` (v2): max 24 hours

**Use the built-in script** to calculate timestamps:

```bash
# Past 3 days (default) — outputs JSON with start_time and end_time
python scripts/cdn_timestamp.py --days 3

# Past 7 days
python scripts/cdn_timestamp.py --days 7

# Last full month
python scripts/cdn_timestamp.py --month

# Current month (1st to today)
python scripts/cdn_timestamp.py --cur-month

# Specific date
python scripts/cdn_timestamp.py --date 2026-08-11
```

Script options: `--days N` (default 3), `--month`, `--cur-month`, `--date YYYY-MM-DD`

**Usage flow**: Run the script first to get the timestamp values, then manually fill them into the `--start_time` and `--end_time` parameters of the hcloud command.

📄 Detailed steps → [references/task-timestamp-calculation.md](references/task-timestamp-calculation.md)

---

## FAQ (Common Questions)

| # | Question | Answer (detail: Pitfall #N in [references/troubleshooting.md](references/troubleshooting.md)) |
|---|----------|----------|
| Q1 | `ShowTopDomainNames` returns `CDN.0202`? | Max time span is 1 day — split into per-day queries (Pitfall #1) |
| Q2 | Excel download times out / binary output? | Add `--cli-read-timeout=60`; output is binary xlsx/zip (`PK` header), do not parse as text (Pitfall #7) |
| Q3 | `ShowDomainStats/v2` missing `action`? | `--action` is required (`detail`/`summary`) (Pitfall #12) |
| Q4 | `ShowLogs/v2` fails with `user has no enterprise project id`? | Domain belongs to an enterprise project — use a non-EP domain (Pitfall #6) |
| Q5 | `ShowTags/v2` requires `--resource_id`? | Not a list-all API; pass `domain_id` as `--resource_id` (Pitfall #13) |
| Q6 | `ShowDomainTemplate --tml_type=system` fails? | `--tml_type` is INTEGER (1=system, 2=user), not a string (Pitfall #8) |
| Q7 | Location/Country stats report missing `stat_type`? | Both APIs require `--stat_type` in addition to `--action`/`--group_by` (Pitfall #14) |

Full 14 validated pitfalls with correct/incorrect command pairs: [references/troubleshooting.md](references/troubleshooting.md).

## Failure Modes

| Failure Mode | Symptom / Error | Recovery |
|---|---|---|
| Time range exceeds API limit | `CDN.0202` / `CDN.0203` | Split into smaller ranges per API limits (see [Timestamp Calculation](#timestamp-calculation)) |
| Invalid parameter combo / value | `CDN.0001` / `ip version name is incorrect: v4` | Use documented enum values (Pitfalls #2/#3/#4) |
| Missing required parameter | `缺少必填参数:action` etc. | Add required param (Pitfalls #12/#13/#14) |
| Enterprise project restriction | `user has no enterprise project id:{0}` | Use a non-EP domain (Pitfall #6) |
| Export timeout / binary output | Timeout / unreadable output | `--cli-read-timeout=60`; treat as binary (Pitfall #7) |
| Credentials not configured | `hcloud configure list` empty | **Stop**, guide credential config (see [Authentication](#authentication)) |
| Permission denied | IAM authorization error | Check [references/iam-policies.md](references/iam-policies.md); contact admin |
| Rate limiting | `ListCdnDomainTopRefers` 2 calls/s | Throttle between calls |
| Empty results | e.g., `ShowDomainCountryStat` empty | Confirm params; try an alternative query API |

**Failure handling protocol:**

1. Look up the error in `troubleshooting.md` or the table above.
2. Apply the documented fix and retry **once**.
3. If still failing, **stop** and report the exact error — never fabricate results.
4. After each query, self-check against [references/verification-method.md](references/verification-method.md).

## Output Format

hcloud CLI returns JSON; follow this contract when presenting results.

**Key output fields:**

- `ListDomains/v2` → `total`, `domains[]` (`id`, `domain_name`, `domain_status`, `service_area`, `business_type`)
- `ShowDomainStats/v2` → `start_time`, `end_time`, `stat_type`, `action`, `interval`, `result.<stat_type>[]`
- `ShowBandwidthCalc` → `bandwidth_calc.value` (bit/s), `.calc_type`, `.time_point`

Full JSON examples and validation: [references/verification-method.md](references/verification-method.md).

**Key enums:**

- `stat_type`: flux/bw/req_num/bs_bw/bs_flux/hit_num/bs_num/bs_fail_num/hit_flux/http_code_2xx..5xx
- `interval`: 300/3600/86400 · `action`: detail/summary (location: location_detail/location_summary) · `calc_type`: bw_95/bw_peak/bw_95_average
- `domain_status`: online/offline/configuring/configuring_failed · `ip_version`: IPv4/IPv6 (NOT v4/v6)
- `tml_type`: INTEGER 1=system, 2=user · `config_type`: INTEGER 0=热点统计, 1=ces上报

**Units:** traffic Bytes, bandwidth bit/s, timestamps ms (UTC; UTC+8 midnight when interval=86400).

**Prohibited content:** never include AK/SK, plaintext credentials, or other tenants' data in any output.

**Agent answer template:** metric + unit + time range + data source command, e.g.:
> Traffic of `<domain>` from `<start>` to `<end>` (UTC+8): `<value>` Bytes (source: `hcloud CDN ShowDomainStats/v2 ...`).

## References

| Document | Description |
|----------|-------------|
| [api-domain-management.md](references/api-domain-management.md) | Category 1: Domain Management APIs (14 APIs) |
| [api-statistics.md](references/api-statistics.md) | Category 2: Statistics & Analytics APIs (12 APIs) |
| [api-refresh-log-export.md](references/api-refresh-log-export.md) | Category 3: Refresh/Log/Export APIs (8 APIs) |
| [api-template-rule-tag-account.md](references/api-template-rule-tag-account.md) | Category 4: Template/Rule/Tag/Account APIs (10 APIs) |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [workflow-domain-config.md](references/workflow-domain-config.md) | Workflow 1: Query domain configuration |
| [workflow-traffic-stats.md](references/workflow-traffic-stats.md) | Workflow 2: Query traffic statistics |
| [workflow-traffic-drilldown.md](references/workflow-traffic-drilldown.md) | Workflow 3: Traffic anomaly drill-down |
| [workflow-logs-reports.md](references/workflow-logs-reports.md) | Workflow 4: Download logs and reports |
| [workflow-domain-diagnosis.md](references/workflow-domain-diagnosis.md) | Workflow 5: Diagnose domain issues |
| [task-timestamp-calculation.md](references/task-timestamp-calculation.md) | Millisecond timestamp calculation script |
| [troubleshooting.md](references/troubleshooting.md) | 12 key pitfalls and troubleshooting |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Output format and verification |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |

---

## Changelog

| Version | Date | Owner | Changes |
|---------|------|-------|---------|
| 1.0.0 | 2026-08-31 | cdn-ops | Initial release: full coverage of 44 GET CDN APIs (4 categories), 14 validated pitfalls, 55 prohibited non-GET operations, 5 query workflows, `cdn_timestamp.py` timestamp script. Quality revision adds: version metadata, enhanced description with near-miss boundary, Triggers and Near-miss/Do NOT Use sections, FAQ, Failure Modes, and Output Format contract. |

**Not covered (by design):** 13 legacy v1 GET APIs (v2 equivalents documented) and 2 unavailable GET APIs (`ListAccessControlTask`, `ListDomainClientStats`) — see Coverage Notes in [references/prohibited-operations.md](references/prohibited-operations.md).
