---
name: huawei-cloud-cdn-dns-resolution-diagnosis
description: |
  Diagnose CDN domain DNS resolution issues using hcloud CLI and Python DNS probes. Query the CDN domain detail to obtain the expected CNAME, probe the actual DNS resolution of the domain
via scripts/dns_resolve.py (dnspython) to collect resolved IP addresses, and verify the IP attribution against Huawei Cloud CDN via ShowIpInfo/v2 to determine whether the domain has been
correctly resolved to Huawei Cloud CDN.
  Use this skill when the user wants to: (1) diagnose CDN DNS resolution failures, (2) check why a domain is not resolved to Huawei Cloud CDN, (3) verify DNS configuration for CDN domain
access, (4) troubleshoot DNS anomaly or resolution timeout issues.
  Triggers include: "DNS解析诊断", "DNS异常", "域名解析失败", "CDN解析异常", "DNS配置", "DNS diagnosis", "resolution diagnosis".
  User utterance examples: "域名解析不到华为云CDN", "CNAME 配置了但没生效", "DNS 解析超时了", "解析出来的 IP 不是华为云的", "域名没解析到 CDN".
  Do NOT use for: HTTPS certificate errors, origin-pull failures, domain ownership verification, or any CDN/DNS configuration change (this skill is strictly read-only).
version: 1.0.0
owner: cdn-ops
tags:
  - cdn
  - dns
  - resolution
  - diagnosis
  - hcloud
---

# CDN DNS Resolution Diagnosis

## Overview

This skill diagnoses CDN domain DNS resolution issues. It queries the CDN domain detail via hcloud CLI to obtain the expected CNAME, probes the actual DNS resolution of the domain via
`scripts/dns_resolve.py` (dnspython) to collect the IP list, and verifies the IP attribution via ShowIpInfo/v2 to determine whether the domain has been correctly resolved to Huawei Cloud
CDN, helping users identify the root cause of DNS configuration anomalies, resolution not taking effect, false positives, and other issues.

**Key Features:**

- Domain permission validation and CNAME retrieval (ShowDomainDetailByName)
- DNS resolution probing to obtain the IP list (`python scripts/dns_resolve.py`, JSON output with `data.resolved_ips` inside the `{result, data, error_msg}` envelope)
- IP attribution check (ShowIpInfo/v2, up to 20 IPs)
- False positive identification (partial resolution scenarios prompt multi-region probing)
- Structured diagnosis report with remediation suggestions

**Tools**: hcloud CLI (KooCLI) + `python scripts/dns_resolve.py` (dnspython >= 2.1)
**Probe Timeout**: 10 seconds (enforced by `dns_resolve.py --timeout 10`)
**IP Query Limit**: 20 IPs
**Core Principle**: Read-only diagnosis, no configuration changes

## Scope

**In scope**: This skill diagnoses only **DNS resolution** issues for CDN domains, including:

- Validating that the domain belongs to the current account and retrieving the expected CNAME (`ShowDomainDetailByName`)
- Probing the actual A-record resolution of the domain (`python scripts/dns_resolve.py`, dnspython)
- Verifying whether the resolved IPs belong to Huawei Cloud CDN (`ShowIpInfo/v2`, up to 20 IPs per call)
- Detecting "partial resolution / false positive" scenarios and producing a structured diagnosis report with remediation suggestions

**Out of scope**:

- ❌ No write/modify/delete operations (this skill is read-only; see the 55 prohibited operations in ⛔ Prohibited Operations)
- ❌ No DNS record changes, no CDN configuration changes, no cache refresh/preheat
- ❌ No diagnosis of other directions: HTTPS certificate, origin-pull failures, domain ownership verification (hand off via the Related Skills section)
- ❌ No handling of requests that require configuration changes (refuse and direct the user to the console or manual hcloud CLI usage)

**Applicable scenarios**:

- DNS resolution failure / CNAME not taking effect / resolution timeout
- Domain resolving to non-Huawei-Cloud IPs / resolution result not matching the expected CNAME
- DNS configuration anomaly troubleshooting, false-positive investigation (partial regional switchover)

## Triggers

**Trigger phrases**: "DNS解析诊断", "DNS异常", "域名解析失败", "CDN解析异常", "DNS配置", "DNS diagnosis", "resolution diagnosis", "CDN 域名解析", "DNS resolution issue".

**User utterance examples** — use this skill when the user says something like:

1. "帮我看看 www.example.com 为什么解析不到华为云 CDN" (Why is www.example.com not resolving to Huawei Cloud CDN?)
2. "CNAME 配置了但没生效，域名还是没解析到 CDN" (CNAME is configured but not taking effect; the domain still does not resolve to CDN)
3. "DNS 解析超时了，怎么排查" (DNS resolution timed out; how do I troubleshoot?)
4. "解析出来的 IP 不是华为云的，是什么问题" (The resolved IPs are not Huawei Cloud's; what is wrong?)
5. "这个域名 DNS 解析异常，帮我诊断一下" (This domain has a DNS resolution anomaly; please diagnose it)

If the user's request matches a Near-miss scenario (certificate / origin / ownership / configuration change), hand off to the corresponding skill or refuse — see [Near-miss / Do NOT
use](#near-miss--do-not-use).

## Near-miss / Do NOT use

Do **not** use this skill in the following scenarios; handle them as shown:

| User request | Correct handling |
|--------------|------------------|
| HTTPS certificate errors / expired or invalid certificate / HTTPS access failure (DNS resolves correctly) | Hand off to `huawei-cloud-cdn-certificate-diagnosis` |
| Page returns 502/504 / origin-pull failures (already resolved to Huawei Cloud CDN) | Hand off to `huawei-cloud-cdn-origin-diagnosis` |
| Domain cannot be added/onboarded to CDN / ownership verification failure | Hand off to `huawei-cloud-cdn-domain-ownership-verification` |
| User asks to modify CDN configuration, delete domains, refresh/preheat cache, or perform any other write operation | **Refuse** (this skill is read-only) and direct the user to the CDN console or manual hcloud CLI |
| User asks to modify DNS records (CNAME/A records) | **Refuse** and direct the user to the DNS service console |

> For multi-direction diagnosis with the other skills, see [Related Skills](#related-skills-multi-direction-diagnosis); the three related skills are independent and read-only, and can be
> chained in any order.

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly forbids all non-GET (write/modify/delete) CDN operations, regardless of user requests.**

**Total: 55 prohibited operations** (24 POST + 25 PUT + 6 DELETE).

For the complete list of all 55 prohibited non-GET operations with risk descriptions, see [references/prohibited-operations.md](references/prohibited-operations.md).

**Representative prohibited operations (full list in the reference doc):**

| Prohibited Operation | API/Command | Reason |
|----------------------|-------------|--------|
| ❌ Create domain | `CreateDomain` (v1/v2), `CreateDomainByDuplicate` | Write operation; creates production resource |
| ❌ Delete domain | `DeleteDomain` (v1/v2) | Irreversible; removes domain from CDN |
| ❌ Modify domain config | `UpdateDomainFullConfig` (v1/v2), `UpdateDomainOrigin`, `UpdateCacheRules`, etc. | Write operations; may affect production traffic |
| ❌ Enable/Disable domain | `EnableDomain` (v1/v2), `DisableDomain` (v1/v2) | Affects production traffic |
| ❌ Modify billing mode | `SetChargeModes` | Financial impact; requires explicit authorization |
| ❌ Create refresh/preheat tasks | `CreateRefreshTasks` (v1/v2), `CreatePreheatingTasks` (v1/v2) | Write operations; affects edge cache |
| ❌ Modify DNS configuration | Any DNS write operation (e.g., `nsupdate`) | Write operation; may affect global resolution |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is for DNS resolution diagnosis only. Please use the Huawei Cloud CDN console, DNS service
> console, or run hcloud CLI manually for configuration changes. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

## Architecture

```
CDN DNS Resolution Diagnosis
├── hcloud configure list              (Credential validation)
├── ShowDomainDetailByName             (Domain permission validation + obtain CNAME)
├── python scripts/dns_resolve.py      (DNS resolution probe, JSON output)
│      --domain <domain_name>
│      [--timeout 10]
│   ├── data.resolved_ips non-empty     → Continue to Step 3
│   └── data.resolved_ips empty / error → Not resolved, generate report
├── ShowIpInfo/v2 --ips=<IP1,IP2>      (IP attribution check, up to 20 IPs)
│   ├── All belongs=true               → Resolved to Huawei Cloud
│   ├── All belongs=false              → Not resolved to Huawei Cloud
│   └── Mixed belongs                  → Partial resolution + false positive prompt
└── Generate diagnosis report
```

### API Call Budget

| Step | API/Command | Rate Limit | Est. Duration |
|------|-------------|------------|---------------|
| 1 | `hcloud configure list` | — | <1s |
| 2 | `ShowDomainDetailByName` | — | <2s |
| 3 | `python scripts/dns_resolve.py` | — | ≤10s |
| 4 | `ShowIpInfo/v2` | — | <2s |

**Total Est. Duration**: < 15 seconds

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=<region> [--parameter=value ...]
```

**Format Rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowDomainDetailByName`, `ShowIpInfo/v2`)
- **Region parameter**: `--cli-region=<region>` (recommended, use cn-north-1 for CDN)
- **Parameter format**: `--key=value` (equals sign, no space)

**Examples:**

```bash
# Correct
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=www.example.com

# Incorrect (space-separated)
hcloud CDN ShowDomainDetailByName --cli-region <region>
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify the version. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
hcloud version
```

> **Prerequisite check: Python >= 3.8 and dnspython >= 2.1 available**
> The DNS resolution probe runs via `python scripts/dns_resolve.py`, which depends on the
> `dnspython` library (>= 2.1). If the import fails, the probe exits with code 2 and an
> `data.error.reason = "missing_library"` JSON output. Install with `pip install dnspython>=2.1`.
> See [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
python -c "import dns.resolver; print('dnspython ok')"
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
> ✅ Correct: `hcloud CDN ShowDomainDetailByName --cli-region=<region>`
>
> ❌ Incorrect: `hcloud CDN ShowDomainDetailByName --cli-region <region>`

> **⚠️ CDN API region requirements**
>
> CDN APIs only support two regions: `cn-north-1` (Beijing) and `ap-southeast-1` (Singapore).
> Query results are region-independent (CDN is a global service).
> **Recommended: use `cn-north-1`**.

> **⚠️ IP query limit**
>
> `ShowIpInfo/v2` queries at most 20 IPs per call. If `dns_resolve.py` returns more than 20 IPs in `data.resolved_ips`, only the first 20 are taken and noted in the report.

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
>
> - **Politely refuse** and return the following message:
>
> ```
> For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
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

- `cdn:domain:get` — Query domain details
- `cdn:ip:info` — Query IP attribution information (if the IAM policy can be split)

> The actual minimum permissions are subject to the CDN service policy. Typically `cdn:domain:get` covers the read-only queries of ShowDomainDetailByName and ShowIpInfo/v2.

---

## Core Commands

Quick reference for all hcloud CDN commands and probe commands used in this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud configure list` | Check credential configuration | None |
| `hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>` | Validate domain permission + obtain CNAME | `--domain_name` |
| `python scripts/dns_resolve.py --domain <domain_name> [--timeout 10]` | DNS resolution probe; emits JSON in `{result, data, error_msg}` envelope with `data.resolved_ips`, `data.duration_ms`, `data.error` | `--domain` (required), `--timeout` (default 10) |
| `hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<IP1,IP2>` | Query IP attribution (up to 20 IPs) | `--ips` |

**Notes:**

- All hcloud commands should use `--cli-region=<region>`
- `dns_resolve.py` enforces a 10-second timeout via `--timeout 10` (default); returns a single JSON object on stdout (wrapped in `{result, data, error_msg}`; business fields are inside `data`)
- The `--ips` parameter of ShowIpInfo/v2 takes multiple IPs separated by English commas, up to 20 IPs
- If `dns_resolve.py` returns more than 20 IPs in `data.resolved_ips`, only query the first 20 and note this in the report

## Parameter Confirmation

Before executing the diagnosis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | CDN accelerated domain to diagnose | None | `www.example.com` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User Confirmation Checklist:**

- [ ] Target domain provided
- [ ] User understands this is a read-only diagnosis operation
- [ ] User understands the `dns_resolve.py` probe enforces a 10-second timeout
- [ ] User understands the IP attribution query limit is 20 IPs

---

## Core Workflows

### Step 1: Credential Validation and Domain Permission Check

Check hcloud credential availability, and validate the domain belongs to the current account via ShowDomainDetailByName while obtaining the CNAME.

📄 Detailed steps → [references/task-permission-check.md](references/task-permission-check.md)

### Step 2: DNS Resolution Probe

Resolve the domain via `python scripts/dns_resolve.py --domain <domain_name> [--timeout 10]` and parse the JSON `data.resolved_ips` field (inside the `{result, data, error_msg}` envelope) to
obtain the actual IP list.

📄 Detailed steps → [references/task-dns-resolve.md](references/task-dns-resolve.md)

### Step 3: IP Attribution Check

Query IP attribution via `ShowIpInfo/v2` to determine whether the domain has been resolved to Huawei Cloud CDN.

📄 Detailed steps → [references/task-ip-attribution.md](references/task-ip-attribution.md)

### Step 4: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report.

📄 Detailed steps → [references/task-report-generation.md](references/task-report-generation.md)

### Step 5: Deliver Report and Remediation Suggestions

Output the diagnosis report to the user, and provide specific remediation suggestions based on the status (e.g., configure CNAME, wait for DNS to take effect, multi-region probing, etc.).

---

## Related Skills (Multi-Direction Diagnosis)

> This skill focuses on **DNS resolution** diagnosis. The same CDN domain may have issues in other directions. When this skill's diagnosis is complete, or when the user's problem involves
> one of the following directions, refer to the corresponding skill to run a **synchronized diagnosis** of the other directions:

| Direction | Related Skill | When to Use |
|-----------|---------------|-------------|
| 🔒 HTTPS certificate | `huawei-cloud-cdn-certificate-diagnosis` | DNS resolves correctly but the browser reports certificate errors, expired/invalid certificate, or HTTPS access fails |
| ✅ Domain ownership verification | `huawei-cloud-cdn-domain-ownership-verification` | Domain cannot be added/accessed via CDN, or ownership verification fails (DNS TXT / verification file) |
| 🔄 Origin (回源) | `huawei-cloud-cdn-origin-diagnosis` | DNS resolves to Huawei Cloud CDN but the page returns 502/504 or origin-pull failures |

**Usage flow**: After the DNS diagnosis report is delivered, if the user's issue
also matches any row above (e.g., HTTPS access fails, domain ownership cannot be
verified, or origin pull errors), invoke the corresponding skill for that
direction **before** concluding the diagnosis. The three skills are independent
and read-only; they can be chained in any order.

**Note on cross-references**:

- `dns_resolve.py` in this skill uses the host's system DNS resolver and does not expose a `--resolver` argument — for targeted resolver testing, switch the system DNS resolver (e.g.,
  8.8.8.8 / 114.114.114.114) and re-run `python scripts/dns_resolve.py --domain <domain_name> --timeout 10`, as noted in
  [references/task-ip-attribution.md](references/task-ip-attribution.md).
- The skills referenced above are separate skill packages; do not call their internal scripts directly from this skill — invoke the skill itself.

---

## FAQ (Frequently Asked Questions)

> Full troubleshooting guide: [references/troubleshooting.md](references/troubleshooting.md).

| Issue | Quick resolution |
|-------|------------------|
| Q1: "Credentials not configured" | Run `hcloud configure` interactively, or set the environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`, then verify with `hcloud configure list` |
| Q2: ShowDomainDetailByName returns 404 / CDN.0171 | The domain is not under the current account or not onboarded to CDN; check the spelling and account, or list onboarded domains with `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100` |
| Q3: 403 permission denied | Verify the IAM user has `cdn:domain:get` / `cdn:ip:info`; contact the primary account administrator to grant permissions if needed (see references/iam-policies.md) |
| Q4: dns_resolve.py returns dns_timeout | Check local network and DNS configuration; switch the system DNS resolver (e.g., 8.8.8.8 / 114.114.114.114) and retry `python scripts/dns_resolve.py --domain <domain> --timeout 10` |
| Q5: missing_library (exit code 2) | Install dnspython: `pip install dnspython>=2.1` (preferred: `python -m pip install dnspython>=2.1`) and retry |

### Known limitations

- `dns_resolve.py` does not expose a `--resolver` argument: multi-region / multi-DNS-server probing requires switching the system DNS resolver and re-running (see troubleshooting.md)
- Only A records are probed: AAAA is not resolved, CNAME chains are not queried directly
- `ShowIpInfo/v2` queries at most 20 IPs per call; excess IPs are truncated and noted in the report
- CDN APIs support only two regions: `cn-north-1` and `ap-southeast-1`; query results are region-independent, `cn-north-1` is recommended

### Error code quick reference

| Error code / error.reason | Meaning | Handling |
|----------------------------|---------|----------|
| 200 | Success | Continue to the next step |
| 403 | Permission denied | Abort and prompt for authorization (see Q3) |
| 404 / CDN.0171 | Domain not under the current account | Abort and prompt to confirm ownership (see Q2) |
| `dns_nxdomain` | Domain does not exist | Report NXDOMAIN; check the spelling and authoritative DNS |
| `dns_no_answer` | No A records | Report "no A records"; check A/CNAME configuration |
| `dns_timeout` | Probe timeout | Mark as timeout and return partial results (see Q4) |
| `missing_library` | dnspython missing | Abort and prompt to install (see Q5) |

---

## Failure Modes

> Per-step exception handling details are in the corresponding task documents; the following is a full-flow summary of failure modes and recovery strategies.

| # | Failure mode | Detection point | Recovery strategy |
|---|--------------|-----------------|-------------------|
| 1 | Credentials not configured / expired | Step 1 `hcloud configure list` | Abort; guide the user to `hcloud configure` or environment variables, then retry |
| 2 | Domain not found (404 / CDN.0171) | Step 1 `ShowDomainDetailByName` | Abort; prompt to confirm domain ownership |
| 3 | Permission denied (403) | Step 1 `ShowDomainDetailByName` | Abort; prompt to contact the administrator to grant `cdn:domain:get` |
| 4 | API call failure (500 / network error) | Step 1 / Step 3 | **Degrade**: output probe results only and note "API query failed; verify IP attribution manually" in the report |
| 5 | Domain not resolved (`data.resolved_ips` empty) | Step 2 JSON | Skip Step 3; report "domain not resolved" + CNAME remediation suggestion |
| 6 | Probe timeout (`dns_timeout`) | Step 2 JSON | Mark "probe timeout"; return partial results; suggest switching the DNS resolver and retrying |
| 7 | NXDOMAIN / NoAnswer | Step 2 JSON | Generate the corresponding conclusion report; check the domain spelling and A-record configuration |
| 8 | dnspython missing (`missing_library`, exit 2) | Step 2 import self-check | Abort; prompt to install `dnspython>=2.1` |
| 9 | More than 20 IPs | Before Step 2 → Step 3 | Query only the first 20 and note "Actually resolved to N IPs; only the first 20 are verified" in the report |
| 10 | Mixed attribution (partial `belongs=true`) | Step 3 `ShowIpInfo/v2` | Conclude "partially resolved / suspected false positive"; prompt multi-region verification |
| 11 | Step 3 returns empty `cdn_ips` | Step 3 response | Defensive conclusion "not resolved to Huawei Cloud"; report Fail and prompt manual verification |

**Self-check**: before generating the final report, verify that all required fields are present (Analysis Time / Target Domain / Expected CNAME / DNS Resolution / Diagnosis Items /
Conclusion / Suggestion); see [references/verification-method.md](references/verification-method.md) for the verification method.

---

## Output Format

**Final output**: a structured text diagnosis report. Full report template, field mapping, sample output, and examples: [references/task-report-generation.md](references/task-report-generation.md).

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>
Expected CNAME: <CDN expected CNAME>

--- DNS Resolution ---
Resolved IPs: <IP1, IP2, ...>
IP Count: <count>

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
[DNS Resolution Probe]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
  Resolved IPs: <IP list>
[IP Attribution Check]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <X/Y IPs belong to Huawei Cloud CDN>

--- Conclusion ---
Status: <overall status>
Suggestion: <remediation suggestion>
```

**Required fields**:

| Field | Description |
|-------|-------------|
| Analysis Time | ISO 8601 (e.g., `2026-08-12T10:00:00+08:00`) |
| Target Domain | The domain being diagnosed (entered by the user) |
| Expected CNAME | The CDN expected CNAME retrieved in Step 1 |
| DNS Resolution | IP list and count from `dns_resolve.py` `data.resolved_ips` |
| Diagnosis Items | Diagnosis items in step order: name + status + detail |
| Conclusion / Suggestion | Overall conclusion and concrete remediation suggestion |

**Status enum**:

| Mark | Meaning | Usage scenario |
|------|---------|----------------|
| ✅ Pass | Passed | Probe result meets expectations |
| ❌ Fail | Failed | Probe result does not meet expectations |
| ⚠️ Warning | Warning | Timeout, partial result, or suspected false positive |
| N/A | Not applicable | Step not executed (e.g., IP attribution check skipped when the domain is not resolved) |

**Probe JSON contract (output structure)**: `dns_resolve.py` emits a single JSON object on stdout wrapped in the `{result, data, error_msg}` envelope; business fields are inside `data.*`
(`data.resolved_ips` / `data.duration_ms` / `data.error`). `data.error.reason` enum: `dns_nxdomain` / `dns_no_answer` / `dns_timeout` / `missing_library` / `invalid_domain` /
`invalid_timeout` / `unexpected_probe_error`. See [references/task-dns-resolve.md](references/task-dns-resolve.md).

**Forbidden content**: the report must NEVER include AK/SK or any plaintext credentials, must never expose other customers' domains, and must never include internal URLs / API internals;
only diagnosis conclusions and remediation suggestions are allowed.

---

## Version History (Changelog)

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-08-12 | Initial version: CDN domain DNS resolution diagnosis (permission check + DNS probe + IP attribution check + diagnosis report) |

- **Owner**: cdn-ops
- **Versioning policy**: major behavioral changes (commands, output contract, workflow adjustments) bump the minor version and are recorded here; pure documentation fixes bump the patch version.

---

## References

| Document | Description |
|----------|-------------|
| [task-permission-check.md](references/task-permission-check.md) | Step 1: Credential validation and domain permission check |
| [task-dns-resolve.md](references/task-dns-resolve.md) | Step 2: DNS resolution probe |
| [task-ip-attribution.md](references/task-ip-attribution.md) | Step 3: IP attribution check |
| [task-report-generation.md](references/task-report-generation.md) | Step 4: Generate diagnosis report |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification method |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
