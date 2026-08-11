---
name: huawei-cloud-cdn-traffic-anomaly-analysis
description: |
  Analyze CDN domain traffic anomalies using hcloud CLI. Query billing mode and traffic/bandwidth metrics for specified domains, compare against 3-month baseline and absolute thresholds to identify traffic theft or abuse.
  Use this skill when the user wants to: (1) analyze CDN domain traffic anomalies, (2) check if a domain has traffic theft or abuse, (3) query CDN billing mode and traffic/bandwidth metrics, (4) compare current traffic against historical baseline.
  Triggers include: CDN流量异常, 流量异常分析, 域名流量分析, 流量盗刷, 带宽异常, 95带宽异常, 流量突增, 流量对比, 基准分析, traffic anomaly, bandwidth anomaly, CDN traffic analysis, traffic theft detection, baseline comparison
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

This skill analyzes CDN domain traffic anomalies by querying billing mode and corresponding traffic/bandwidth metrics. It automatically determines the appropriate metric based on the account's billing mode (bw_95, flux, combine_flux, bw, bw_peak), queries historical data over a configurable time range, establishes a 3-month baseline for comparison, and identifies potential traffic theft or abuse using both absolute thresholds and relative baseline deviation.

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

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids the following operations, regardless of user requests:**

| Prohibited Operation | API/Command | Reason |
|---------------------|-------------|--------|
| ❌ Modify domain configuration | `ModifyDomainConfig` / `hcloud CDN UpdateDomain` | Write operation; may affect production traffic |
| ❌ Delete domain | `DeleteDomain` / `hcloud CDN DeleteDomain` | Irreversible; removes domain from CDN |
| ❌ Disable domain acceleration | `DisableDomain` / `hcloud CDN DisableDomain` | Affects production traffic |
| ❌ Modify billing mode | `UpdateBillingMode` | Financial impact; requires explicit authorization |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete operations. This skill is read-only for traffic analysis. Please use the Huawei Cloud CDN console or hcloud CLI manually for configuration changes."

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
│       └── Combined: 1 call (97 days → 90d baseline + 7d current)
└── ThresholdJudgment      (Dual-threshold: absolute + baseline-relative)
    ├── ⚠️ Anomalous: exceeds absolute threshold
    ├── 👀 Watch: exceeds baseline × multiplier (sub-threshold surge)
    └── ✅ Normal: neither threshold triggered
```

### API Call Budget

| Billing Mode | API Calls | Rate Limit | Est. Duration |
|-------------|-----------|------------|---------------|
| bw_95 | 6 (1 billing + 1 domain + 1 current + 3 baseline) | 2/s (ShowBandwidthCalc) | ~3s |
| flux / bw | 3 (1 billing + 1 domain + 1 combined 97d query) | 15/s (ShowDomainStats) | <1s |

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=cn-north-4 [--parameter=value ...]
```

**Format Rules:**
- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowChargeModes`, `ListDomains`, `ShowBandwidthCalc`)
- **Region parameter**: `--cli-region=cn-north-4` (required, always use cn-north-4 for CDN)
- **Parameter format**: `--key=value` (equals sign, no space)
- **Indexed parameters**: `--key.1=value1` (for array parameters)

**Examples:**
```bash
# Correct
hcloud CDN ShowChargeModes --cli-region=cn-north-4 --product_type=base
hcloud CDN ListDomains/v2 --cli-region=cn-north-4 --page_size=100

# Incorrect (space instead of equals sign)
hcloud CDN ShowChargeModes --cli-region cn-north-4
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
> ✅ Correct: `hcloud CDN ShowChargeModes --cli-region=cn-north-4`
>
> ❌ Incorrect: `hcloud CDN ShowChargeModes --cli-region cn-north-4`

> **⚠️ CDN API region requirements**
>
> CDN APIs support multiple regions. It is recommended to use `cn-north-4`, but the APIs are not limited to this region only.
> Query results are region-independent (CDN is a global service).
> **Recommended: Always use `cn-north-4`**.

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials required**

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing AK/SK values
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
> - **Prohibited** from using `hcloud configure set` to pass plaintext credential values
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or configured CLI config files
>
> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
> 1. **Stop immediately** - Do not execute any commands
> 2. **Politely refuse** and return the following message:
>    ```
>    For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration (recommended)
>        hcloud configure
>        # Enter AK/SK as prompted; credentials will be securely stored in a local config file
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
> ```bash
>    hcloud configure list
> ```
>    Check whether the output contains valid configuration (AK/SK, IAM, etc.).
>
> **If no valid credentials exist, stop here.**

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions:**
- `cdn:domain:list` — List CDN domains
- `cdn:domain:get` — Get domain details
- `cdn:statistics:get` — Get traffic/bandwidth statistics
- `cdn:billing:get` — Get billing mode information

---

## Core Commands

Quick reference for all hcloud CDN commands used in this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud CDN ShowChargeModes --cli-region=cn-north-4 --product_type=base` | Query account billing mode | `--service_area` (optional) |
| `hcloud CDN ListDomains/v2 --cli-region=cn-north-4 --page_size=100` | List all CDN domains | `--page_size`, `--page_number` |
| `hcloud CDN ShowBandwidthCalc --cli-region=cn-north-4 --domain_name=<domain> --calc_type=bw_95 --start_time=<ms> --end_time=<ms>` | Query 95th percentile bandwidth (current 7 days or baseline 30 days) | `--service_area` |
| `hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-4 --domain_name=<domain> --stat_type=flux --interval=86400 --start_time=<ms> --end_time=<ms> --action=detail` | Query daily traffic statistics (combined 97d query for flux/bw paths) | `--stat_type`, `--interval`, `--service_area` |

**Notes:**
- All commands require `--cli-region=cn-north-4`
- Timestamps must be in milliseconds (e.g., `1785081600000`)
- Use `scripts/cdn_timestamp.py` to calculate timestamps
- Use `scripts/cdn_timestamp.py --baseline` for 3×30-day baseline windows
- **ShowBandwidthCalc**: max 31-day range, single aggregate value (no per-day breakdown), rate limit 2 calls/s
- **ShowDomainStats/v2**: supports ≥365-day range, one data point per day at interval=86400, rate limit 15 calls/s

## Parameter Confirmation

Before executing the analysis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | Target CDN domain to analyze | None | `example.com` |
| `--days` | No | Number of days for current window analysis | `7` | `14` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-4` | `cn-north-4` |

**User Confirmation Checklist:**
- [ ] Target domain name provided or selected from domain list
- [ ] Analysis time range confirmed (default: past 7 days for current window)
- [ ] User understands this is a read-only analysis operation
- [ ] User understands the baseline comparison spans past 3 months

---

## Core Workflows

### Step 1: Query Account Billing Mode

Query billing mode via hcloud CLI to determine which metric to analyze.

📄 Detailed steps → [references/task-show-charge-modes.md](references/task-show-charge-modes.md)

### Step 2: List All CDN Domains

Get all online CDN domains under the current account.

> **If the user did not provide a domain, or the provided domain is not in the list, you must list all available domains for the user to choose from.**

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
- **flux / bw**: The same `ShowDomainStats/v2` call from Step 5 covers both current and baseline windows (97 days total). Split the first 90 daily values as baseline, last 7 as current window.

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

## References

| Document | Description |
|----------|-------------|
| [task-show-charge-modes.md](references/task-show-charge-modes.md) | Step 1: Query billing mode |
| [task-list-domains.md](references/task-list-domains.md) | Step 2: List all domains |
| [task-domain-validation.md](references/task-domain-validation.md) | Step 3: Domain validation |
| [task-timestamp-calculation.md](references/task-timestamp-calculation.md) | Step 4: Timestamp calculation |
| [task-query-metrics.md](references/task-query-metrics.md) | Step 5-6: Query current + baseline metrics |
| [task-threshold-judgment.md](references/task-threshold-judgment.md) | Step 7: Dual-threshold judgment + report |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Output format and verification |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and best practices |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |