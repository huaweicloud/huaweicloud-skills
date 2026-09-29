---
name: huawei-cloud-cdn-traffic-anomaly-analysis
version: 1.0.0
updated: 2026-08-09
owner: cdn-ops
description: |
  Analyze CDN domain traffic anomalies using hcloud CLI. Query billing mode and traffic/bandwidth metrics for specified domains, compare against 3-month baseline and absolute thresholds to
  identify traffic theft or abuse.
  Use this skill when the user wants to: (1) analyze CDN domain traffic anomalies, (2) check if a domain has traffic theft or abuse, (3) query CDN billing mode and traffic/bandwidth metrics,
  (4) compare current traffic against historical baseline.
  Triggers include: "CDN流量异常", "流量异常分析", "域名流量分析", "流量盗刷", "带宽异常", "95带宽异常", "流量突增", "流量对比", "基准分析", "traffic anomaly", "bandwidth anomaly", "CDN traffic analysis", "traffic theft
  detection", "baseline comparison"
tags:
  - cdn
  - traffic
  - anomaly
  - bandwidth
  - hcloud
  - baseline
---

# CDN Traffic Anomaly Analysis

## Overview

This skill analyzes CDN domain traffic anomalies by querying billing mode and corresponding traffic/bandwidth metrics. It automatically determines the appropriate metric based on the
account's billing mode (bw_95, flux, combine_flux, bw, bw_peak), queries historical data over a configurable time range, establishes a 3-month baseline for comparison, and identifies
potential traffic theft or abuse using both absolute thresholds and relative baseline deviation.

**Key Features:**

- Automatic billing mode detection and metric selection
- Support for all billing modes: bw_95, flux, combine_flux, bw, bw_peak
- Domain validation and traffic analysis
- **3-month baseline analysis** — detects relative traffic surges against historical norms
- **Dual-threshold anomaly detection** — absolute thresholds + relative baseline comparison
- **Three-tier conclusions**: Normal / Watch (relative surge) / Anomalous (absolute threshold exceeded)
- Comprehensive analysis reports with baseline comparison and daily breakdowns

**Tool**: hcloud CLI (KooCLI)  
**Timestamp Tool**: `scripts/cdn_timestamp.py` (built-in)  
**Analysis Scope**: Past 7 days for current window (configurable); past 3 months for baseline  
**Core Principle**: Query only the metric corresponding to the billing mode; use API capabilities efficiently to cover both current and baseline windows with minimal API calls

## Triggers

Use this skill when the user request matches one of the following patterns (user-level example inputs):

| User Input Example | Trigger Intent |
|-------------|----------|
| "Is example.com's traffic being stolen or abused?" | Traffic theft detection |
| "Analyze whether CDN bandwidth has surged abnormally in the last 7 days" | Bandwidth anomaly analysis |
| "Compare traffic over the past 3 months with the current period for anomalies" | 3-month baseline comparison |
| "Check our account's CDN billing mode and domain list" | Billing mode / domain query |
| "Why is example.com's 95th percentile bandwidth so high?" | 95th percentile bandwidth analysis |
| "traffic anomaly / bandwidth anomaly / CDN traffic analysis" | English triggers |

Also triggered by the trigger phrases listed in the frontmatter `description` (e.g., CDN流量异常, 流量盗刷, 带宽异常, traffic anomaly).

## Near-miss / Do NOT use

**Do NOT use this skill for:**

- ❌ **Any CDN write operation**: create/delete domains, modify domain config, refresh/preheat, enable/disable domains, change billing mode, etc. — this skill is strictly read-only and must
  refuse such requests (see all 55 prohibited operations in [references/prohibited-operations.md](references/prohibited-operations.md))
- ❌ **Traffic analysis requiring hourly or finer granularity** — this skill works at daily granularity (interval=86400)
- ❌ **Traffic/bandwidth analysis for non-CDN services** (e.g., ECS, ELB, OBS traffic) — this skill only covers CDN domains
- ❌ **Operational tasks** such as domain config changes, certificate management, or anti-hotlink configuration
- ❌ **Scenarios without hcloud credentials or CDN permissions** (complete the credential check in the [Authentication](#authentication) section first)
- ❌ **Cross-border / overseas region analysis** — the CDN CLI only accepts `cn-north-1` and `ap-southeast-1`; other regions return `[USE_ERROR]`

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids all non-GET (write/modify/delete) CDN operations, regardless of user requests.**

**Total: 55 prohibited operations** (24 POST + 25 PUT + 6 DELETE).

For the complete list of all 55 prohibited non-GET operations with risk descriptions, see [references/prohibited-operations.md](references/prohibited-operations.md).

**Representative prohibited operations (full list in the reference doc):**

| Prohibited Operation | API/Command | Reason |
|---------------------|-------------|--------|
| ❌ Create domain | `CreateDomain` (v1/v2), `CreateDomainByDuplicate` | Write operation; creates production resource |
| ❌ Delete domain | `DeleteDomain` (v1/v2) | Irreversible; removes domain from CDN |
| ❌ Modify domain config | `UpdateDomainFullConfig` (v1/v2), `UpdateDomainOrigin`, `UpdateCacheRules`, etc. | Write operations; may affect production traffic |
| ❌ Enable/Disable domain | `EnableDomain` (v1/v2), `DisableDomain` (v1/v2) | Affects production traffic |
| ❌ Modify billing mode | `SetChargeModes` | Financial impact; requires explicit authorization |
| ❌ Create refresh/preheat tasks | `CreateRefreshTasks` (v1/v2), `CreatePreheatingTasks` (v1/v2) | Write operations; affects edge cache |
| ❌ Verify domain ownership | `VerifyDomainOwner` | POST operation; triggers verification flow |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is read-only for traffic analysis. Please use the Huawei Cloud CDN console or run the hcloud
> CLI manually for configuration changes. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

## Architecture

```
CDN Traffic Anomaly Analysis
├── ShowChargeModes        (Query account billing mode)
├── ListDomains/v2         (List all CDN domains)
├── Domain Validation      (Verify target domain exists)
├── TimestampCalculation   (scripts/cdn_timestamp.py)
│   ├── Current window     (default 7 days, UTC+8 midnight)
│   └── Baseline windows   (3 × 30-day windows, non-overlapping)
├── QueryMetrics           (Based on billing mode)
│   ├── bw_95 → ShowBandwidthCalc
│   │   ├── Current: 1 call (7-day single aggregate)
│   │   └── Baseline: 3 calls (30-day aggregates each)
│   └── flux/bw → ShowDomainStats/v2 (stat_type=flux or bw)
│       ├── Current: 1 call (7-day window, interval=86400)
│       └── Baseline: 3 calls (30-day windows each, interval=86400)
└── ThresholdJudgment      (Dual-threshold: absolute + baseline-relative)
    ├── ⚠️ Anomalous: exceeds absolute threshold
    ├── 👀 Watch: exceeds baseline × multiplier (sub-threshold surge)
    └── ✅ Normal: neither threshold triggered
```

### API Call Budget

| Billing Mode | API Calls | Rate Limit | Est. Duration |
|-------------|-----------|------------|---------------|
| bw_95 | 6 (1 billing + 1 domain + 1 current + 3 baseline) | 2/s (ShowBandwidthCalc) | ~3s |
| flux / bw | 6 (1 billing + 1 domain + 1 current + 3 baseline) | 15/s (ShowDomainStats) | ~1s |

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=cn-north-1 [--parameter=value ...]
```

**Format Rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowChargeModes`, `ListDomains`, `ShowBandwidthCalc`)
- **Region parameter**: `--cli-region=cn-north-1` (required, always use cn-north-1 for CDN)
- **Parameter format**: `--key=value` (equals sign, no space)
- **Indexed parameters**: `--key.1=value1` (for array parameters)

**Examples:**

```bash
# Correct
hcloud CDN ShowChargeModes --cli-region=cn-north-1 --product_type=base
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=100

# Incorrect (space instead of equals sign)
hcloud CDN ShowChargeModes --cli-region cn-north-1
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify version >= 3.2.0. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
```

> **Prerequisite check: Python >= 3.8 required (for timestamp calculation)**
> Run `python --version` to verify version >= 3.8.

```bash
python --version
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
> ✅ Correct: `hcloud CDN ShowChargeModes --cli-region=cn-north-1`
>
> ❌ Incorrect: `hcloud CDN ShowChargeModes --cli-region cn-north-1`

> **⚠️ CDN API region requirements**
>
> CDN is a global service (is_global=true). The hcloud CLI for CDN only accepts `cn-north-1` and `ap-southeast-1` (both map to the same endpoint `cdn.myhuaweicloud.com`); `cn-north-4` is
> rejected with `[USE_ERROR]`.
> **Recommended: Always use `cn-north-1`**.

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials required**

> **Security rules (must be followed):**
>
> - **Prohibited** from reading, echoing, or printing AK/SK values
>
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
>
> - **Prohibited** from using `hcloud configure set` to pass plaintext credential values
>
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or configured CLI config files
>
> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
>
> - **Stop immediately** - Do not execute any commands
> - **Politely refuse** and return the following message:
>
> ```
> For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
> Please use one of the following secure methods to configure credentials:
>
> Method 1: Interactive configuration (recommended)
>     hcloud configure
>     # Enter AK/SK as prompted; credentials will be securely stored in a local config file
>
> Method 2: Environment variable configuration
>     export HUAWEICLOUD_SDK_AK=<your-access-key-id>
>     export HUAWEICLOUD_SDK_SK=<your-secret-key>
>
> After configuration is complete, please retry your request.
> ```
>
> - **Do not continue** executing any Huawei Cloud operations until credentials are configured
>
> **Check CLI configuration**:
>
> ```bash
> hcloud configure list
> ```
>
> Check whether the output contains valid configuration (AK/SK, IAM, etc.).
>
> **If no valid credentials exist, stop here.**

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions:**

- `cdn:*:query*` — All CDN query-class actions used by this skill (`ListDomains/v2`, `ShowChargeModes`, `ShowDomainStats/v2`, `ShowBandwidthCalc`)
- `cdn:configuration:queryDomains` — List CDN domains (listed explicitly alongside the wildcard)
- `cdn:configuration:queryChargeMode` — Query the billing mode (listed explicitly alongside the wildcard)

---

## Core Commands

Quick reference for all hcloud CDN commands used in this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ShowChargeModes --cli-region=cn-north-1 --product_type=base` | Query account billing mode | `--service_area` (optional) |
| `hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=100` | List all CDN domains | `--page_size`, `--page_number` |
| `hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --domain_name=<domain> --calc_type=bw_95 --start_time=<ms> --end_time=<ms>` | Query 95th percentile bandwidth (current 7 days or baseline 30 days) | `--service_area` |
| `hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --domain_name=<domain> --stat_type=flux --interval=86400 --start_time=<ms> --end_time=<ms> --action=detail` | Query daily traffic statistics (1 current 7-day + 3×30-day baseline queries for flux/bw paths) | `--stat_type`, `--interval`, `--service_area` |

**Notes:**

- All commands require `--cli-region=cn-north-1`
- Timestamps must be in milliseconds (e.g., `1785081600000`)
- Use `scripts/cdn_timestamp.py` to calculate timestamps
- Use `scripts/cdn_timestamp.py --baseline` for 3×30-day baseline windows
- **ShowBandwidthCalc**: max 31-day range, single aggregate value (no per-day breakdown), rate limit 2 calls/s
- **ShowDomainStats/v2**: interval=86400 (1 day) max query range is 31-32 days — a 97-day single query fails with `CDN.0202`; one data point per day; rate limit 15 calls/s; baseline must be
  split into 3×30-day queries

## Parameter Confirmation

Before executing the analysis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | Target CDN domain to analyze | None | `example.com` |
| `--days` | No | Number of days for current window analysis | `7` | `14` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User Confirmation Checklist:**

- [ ] Target domain name provided or selected from domain list
- [ ] Analysis time range confirmed (default: past 7 days for current window)
- [ ] User understands this is a read-only analysis operation
- [ ] User understands the baseline comparison spans past 3 months

---

## Core Workflows

> **Target domain is required before any analysis step.**
>
> - If the user did not provide a target domain, ask the user for the domain name and wait for the reply before starting.
> - Only if the user does not know the domain or asks you to look it up, list the account's domains via `hcloud CDN ListDomains/v2` (Step 2) and ask the user to choose one.
> - Never start the analysis without an explicit user-provided domain: do not guess a domain, do not fall back to an example/default domain, and do not pick a domain from the list yourself.

### Step 1: Query Account Billing Mode

Query billing mode via hcloud CLI to determine which metric to analyze.

📄 Detailed steps → [references/task-show-charge-modes.md](references/task-show-charge-modes.md)

### Step 2: List All CDN Domains (only when the user asks you to look up the domain)

List all online CDN domains under the current account, then ask the user to choose the target domain from the list.

📄 Detailed steps → [references/task-list-domains.md](references/task-list-domains.md)

### Step 3: Domain Validation

Verify the user-provided domain exists in the domain list.

📄 Detailed steps → [references/task-domain-validation.md](references/task-domain-validation.md)

### Step 4: Timestamp Calculation

Calculate time range for the current window (default 7 days) and 3 baseline windows (30 days each, non-overlapping), aligned to UTC+8 midnight.

📄 Detailed steps → [references/task-timestamp-calculation.md](references/task-timestamp-calculation.md)

### Step 5: Query Current Window Metrics

Query the corresponding metric for the current window (7 days) based on billing mode.

📄 Detailed steps → [references/task-query-metrics.md](references/task-query-metrics.md)

### Step 6: Query Baseline Metrics

Query the corresponding metric for the baseline window (past 3 months) based on billing mode.

- **bw_95**: 3 separate calls to `ShowBandwidthCalc`, each covering one non-overlapping 30-day window (API max range is 31 days). Sleep 0.6s between calls to respect the 2 calls/s rate limit.
- **flux / bw**: 4 separate `ShowDomainStats/v2` calls — 1 for the current 7-day window (from Step 5) plus 3 for the 3×30-day baseline windows (interval=86400, aligned to UTC+8 midnight).
  The API max range for interval=86400 is 31-32 days, so a single 97-day query fails (`CDN.0202`). Compute baseline statistics (mean / P95 / max) from the 3 aggregated 30-day windows,
  consistent with the bw_95 path.

📄 Detailed steps → [references/task-query-metrics.md](references/task-query-metrics.md)

### Step 7: Threshold Judgment

Apply dual-threshold logic: absolute thresholds (hard limits) + relative baseline comparison (surge detection). Generate a three-tier analysis report.

📄 Detailed steps → [references/task-threshold-judgment.md](references/task-threshold-judgment.md)

---

## Threshold Rules Summary

| Billing Mode | Metric | Absolute Threshold | Relative Baseline |
|-------------|--------|-------------------|-------------------|
| `bw_95` | 7-day P95 bandwidth (bit/s) | ≥ 8 Gbps → ⚠️ Anomalous | current > baseline_max × 1.5 → 👀 Watch |
| `flux` / `combine_flux` | Daily traffic (Byte) | Any day > 5 TB → ⚠️ Anomalous | Any day > baseline_P95 × 1.5 → 👀 Watch |
| `bw` / `bw_peak` | Daily peak bandwidth (bit/s) | Any day ≥ 3 Gbps → ⚠️ Anomalous | Any day > baseline_P95 × 1.5 → 👀 Watch |

**Three-tier conclusion:**

- **⚠️ Anomalous** — Absolute threshold exceeded; strong signal of traffic theft
- **👀 Watch** — Does not exceed absolute threshold, but exceeds baseline × 1.5; potential relative surge worth investigating
- **✅ Normal** — Falls within both absolute and relative thresholds

No-data domains (`result: {}` or `value: 0`) are always treated as **Normal**.

---

## Output Format

Every analysis produces a unified CDN traffic anomaly analysis report. The full templates for all three tiers (⚠️ Anomalous / 👀 Watch / ✅ Normal) are in
[references/task-threshold-judgment.md](references/task-threshold-judgment.md) — **follow those templates exactly**.

**Report structure contract (required fields):**

| Field | Required | Description |
|-------|----------|-------------|
| Analysis Time | ✅ | Analysis timestamp |
| Target Domain | ✅ | Analyzed domain |
| Billing Mode | ✅ | bw_95 / flux / combine_flux / bw / bw_peak |
| Metric | ✅ | 7-Day P95 Bandwidth / Daily Traffic / Daily Peak Bandwidth |
| Current Window | ✅ | Analysis period (default 7 days) |
| Baseline Statistics | ✅ | mean / P95 / max / relative limit from past 3 months |
| Current Values | ✅ | Daily values (or single aggregate) with deviation % vs baseline |
| Status | ✅ | One of the three-tier conclusion enum values |
| Conclusion | ✅ | Verdict + recommendation |

**Status enum (must use exactly one):**

| Status | Meaning |
|--------|---------|
| `⚠️ Anomalous` | Absolute threshold exceeded; strong signal of traffic theft |
| `👀 Watch` | Below absolute threshold but above baseline × 1.5; relative surge |
| `✅ Normal` | Within both thresholds |

**Prohibited content in output (NEVER include):**

- ❌ AK/SK, tokens, or any credentials (see Authentication rules)
- ❌ Raw API responses; only parsed/summarized values
- ❌ Domains or data unrelated to the analyzed target domain
- ❌ Speculative claims not backed by the queried data (e.g., "attacker identity")

---

## Failure Modes

| Failure Mode | Trigger Condition | Handling |
|--------------|-------------------|----------|
| No valid credentials | `hcloud configure list` returns empty/invalid config | Stop immediately; guide user through Authentication section |
| Domain not found | Target domain not in ListDomains/v2 online list | Stop; inform user and list available domains (see [task-domain-validation.md](references/task-domain-validation.md)) |
| Permission denied | API returns permission error | Verify IAM policies ([iam-policies.md](references/iam-policies.md)); report failure to user |
| Rate limit exceeded | ShowBandwidthCalc limit 2 calls/s | Add `sleep 0.6` between calls, retry (see [troubleshooting.md](references/troubleshooting.md)) |
| Query range too large | Single query > 31 days (ShowBandwidthCalc) or > 31-32 days (ShowDomainStats interval=86400, `CDN.0202`) | Split into 3×30-day baseline windows; never issue a single 97-day query |
| No traffic data | API returns `result: {}` or `value: 0` | Treat as **Normal**; note the empty-data situation in the report |
| Timestamp misalignment | interval=86400 query not aligned to UTC+8 midnight | Always use `scripts/cdn_timestamp.py`; manual timestamps are error-prone |
| hcloud CLI parameter error | `[USE_ERROR]` (e.g., space-separated params, wrong region) | Verify `--key=value` format and `--cli-region=cn-north-1` |

**Recovery policy per failure mode:** retry (rate limit / transient errors, up to 2 attempts with backoff) → degrade (split query range, use available data) → report failure (stop and
explain to the user). **Never fabricate data or continue with invalid results.**

**Self-check before output:** verify (1) billing mode matches the queried metric, (2) the 3 baseline windows are non-overlapping with the current window, (3) threshold comparison uses the
correct units (bit/s vs Byte) and direction (≥ vs >).

---

## FAQ

| Question | Answer |
|----------|--------|
| Why does ShowBandwidthCalc return only a single value? | This is expected behavior: the API returns a single P95 aggregate value for the query period with no per-day breakdown, and its maximum query range is 31 days. Use ShowDomainStats/v2 for per-day data. |
| Why can't I query 97 days in one call? | ShowDomainStats/v2 with interval=86400 has a maximum query range of 31-32 days; a single 97-day query fails with `CDN.0202`. The baseline must be split into 3 non-overlapping 30-day windows. |
| Is a domain with no traffic data (`result: {}` / `value: 0`) considered anomalous? | No. Domains with no data are always treated as **Normal** (see Threshold Rules Summary); you may note in the report that the domain had no traffic during the query period. |
| Why is `--cli-region=cn-north-1` always recommended? | CDN is a global service; the CLI only accepts cn-north-1 and ap-southeast-1 (both map to the same endpoint), and cn-north-4 is rejected (`[USE_ERROR]`). |
| What if I hit a rate limit error? | ShowBandwidthCalc is limited to 2 calls/s: add `sleep 0.6` between commands; ShowDomainStats is limited to 15 calls/s and usually needs no handling. |
| The domain is not in the account's online domain list? | Stop the analysis and ask the user to verify the domain spelling/status/account (see the Domain Not Found section in [troubleshooting.md](references/troubleshooting.md)). |
| The user requests a write operation (e.g., cache refresh, config change)? | Refuse and explain that this skill is read-only (see [prohibited-operations.md](references/prohibited-operations.md)); direct the user to the CDN console or manual hcloud CLI execution. |

For more questions and troubleshooting, see [references/troubleshooting.md](references/troubleshooting.md).

---

## Changelog / Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-08-09 | Initial version: billing mode query + traffic/bandwidth statistics + 3-month baseline comparison + dual-threshold anomaly detection |

**Owner**: cdn-ops  
**Maintenance**: For major changes, update this table and bump the version number (SemVer). Deprecation/retirement requires review by the cdn-ops team and must be recorded in this table.

---

## References

| Document | Description |
|----------|-------------|
| [task-show-charge-modes.md](references/task-show-charge-modes.md) | Step 1: Query billing mode |
| [task-list-domains.md](references/task-list-domains.md) | Step 2: List all domains |
| [task-domain-validation.md](references/task-domain-validation.md) | Step 3: Domain validation |
| [task-timestamp-calculation.md](references/task-timestamp-calculation.md) | Step 4: Timestamp calculation |
| [task-query-metrics.md](references/task-query-metrics.md) | Step 5-6: Query current + baseline metrics |
| [task-threshold-judgment.md](references/task-threshold-judgment.md) | Step 7: Dual-threshold judgment + report |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Output format and verification |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and best practices |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |