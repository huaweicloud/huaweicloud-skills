---
name: huawei-cloud-cdn-origin-diagnosis
description: |
  Diagnose CDN origin server reachability and back-to-source failures using hcloud CLI. Query the origin configuration (origin_addr, origin_type, http_port, https_port, origin_protocol) of a
  CDN domain via ShowDomainFullConfig/v2, then probe origin server connectivity using the Python probe script (scripts/origin_probe.py) to identify the root cause of back-to-source failures,
  origin unreachable errors, and abnormal responses.
  Use when the user wants to: (1) diagnose CDN back-to-source failures, (2) check why origin server is unreachable, (3) troubleshoot origin configuration issues, (4) verify origin
  connectivity from the network perspective, (5) investigate abnormal HTTP responses from the origin.
  Triggers include: '源站诊断', '源站不可达', '回源失败', 'origin diagnosis', 'origin unreachable', '回源异常', '源站配置'
  Do NOT use this skill for configuration changes, cache refresh/preheat, domain lifecycle management, or billing operations — this skill is strictly read-only diagnosis.
tags:
  - cdn
  - origin
  - diagnosis
  - hcloud
  - back-to-source
version: 1.0.0
owner: cdn-ops
---

# CDN Origin Server Diagnosis

## Overview

This skill is used to diagnose CDN back-to-source failures, origin unreachable errors, and other origin-related issues. It queries the CDN domain's origin configuration (origin address,
origin type, back-to-source port, back-to-source protocol) via hcloud CLI, and probes origin server connectivity using the Python probe script (scripts/origin_probe.py), helping users
identify the root cause of back-to-source failures, such as abnormal origin server services, closed ports, or CDN back-to-source IP ranges not whitelisted.

**Key Features:**

- Automatically queries and parses CDN origin configuration (configs.sources)
- Supports connectivity probing for all three back-to-source protocols: http / https / follow
- Parses origin_addr, origin_type, http_port, https_port, origin_protocol
- Structured diagnosis report with IP whitelist prompts and remediation suggestions

**Tool**: hcloud CLI (KooCLI) + Python probe script (`scripts/origin_probe.py`)
**Probe Timeout**: 10 seconds
**Core Principle**: Read-only diagnosis; no configuration changes are performed

## Scope

**What this skill does:**

- Query the CDN domain's origin configuration (`configs.sources`, `origin_protocol`) via `ShowDomainFullConfig/v2`
- Probe origin server connectivity (HTTP/HTTPS) using `scripts/origin_probe.py`
- Generate a structured diagnosis report with IP whitelist prompts and remediation suggestions

**What this skill does NOT do:**

- Does NOT modify, create, or delete any CDN domain or origin configuration (strictly read-only)
- Does NOT perform cache refresh / preheat operations
- Does NOT manage domain lifecycle (enable/disable), billing mode, or account settings
- Does NOT guarantee origin reachability from CDN edge nodes — the probe reflects the execution environment's network perspective

**Use when:**

- The user wants to diagnose back-to-source failures, origin unreachable errors, or abnormal origin responses
- The user wants to verify the origin configuration (origin_addr, origin_type, http_port, https_port, origin_protocol) and origin connectivity
- The user is troubleshooting origin 5xx responses, connection timeouts, or TLS handshake failures on the back-to-source path

## Triggers

Use this skill when the user input matches any of the following intents:

| Intent | Example User Input |
|--------|--------------------|
| Back-to-source failure diagnosis | "Diagnose the CDN back-to-source failure for www.example.com" |
| Origin unreachable | "Why is my origin server unreachable?" |
| Abnormal origin responses | "The origin connection of this domain is abnormal" |
| Origin 5xx / timeout | "The origin keeps returning 502 / back-to-source timeout" |
| Origin configuration check | "Check the origin configuration of this domain" |

**Trigger keywords:** origin diagnosis, origin unreachable, back-to-source failure, back-to-source timeout, origin connectivity, origin configuration check

## Near-miss / Do NOT Use

Do NOT use this skill for the following requests — they are out of scope and will be refused:

- ❌ Modifying / creating / deleting CDN domains or origin configuration (configuration changes) → use the CDN console or manual hcloud CLI
- ❌ Cache refresh / preheat (`CreateRefreshTasks` / `CreatePreheatingTasks` are prohibited here)
- ❌ Domain lifecycle management (enable/disable), billing mode changes, or account-level operations
- ❌ Querying traffic statistics, cache hit ratios, or access logs (not origin-connectivity diagnosis)
- ❌ Generic network connectivity tests outside the CDN back-to-source path

See [references/prohibited-operations.md](references/prohibited-operations.md) for the full list of 55 prohibited non-GET operations.

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
| ❌ Modify origin config | `UpdateDomainOrigin`, `UpdateOriginHost`, `UpdatePrivateBucketAccess` (v1/v2) | Write operations; may affect back-to-source traffic |
| ❌ Enable/Disable domain | `EnableDomain` (v1/v2), `DisableDomain` (v1/v2) | Affects production traffic |
| ❌ Modify billing mode | `SetChargeModes` | Financial impact; requires explicit authorization |
| ❌ Create refresh/preheat tasks | `CreateRefreshTasks` (v1/v2), `CreatePreheatingTasks` (v1/v2) | Write operations; affects edge cache |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is for origin connectivity diagnosis only. Please use the Huawei Cloud CDN console or run
> hcloud CLI manually for configuration changes. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

## Architecture

```

CDN Origin Server Diagnosis
├── hcloud configure list                   (credential check)
├── ShowDomainDetailByName                  (domain permission check + basic info)
├── ShowDomainFullConfig/v2                 (origin configuration query)
│   ├── configs.sources empty       → report "origin not configured"
│   └── configs.sources non-empty   → parse origin_addr / origin_type / http_port / https_port / origin_protocol
├── python scripts/origin_probe.py          (origin connectivity probe, JSON output in {result, data, error_msg})
│   ├── origin_protocol=http      → origin_probe.py --scheme http --host <origin_addr> --port <http_port>
│   ├── origin_protocol=https     → origin_probe.py --scheme https --host <origin_addr> --port <https_port>
│   └── origin_protocol=follow    → probe both http and https
└── generate diagnosis report
```

### API Call Budget

| Step | API/Command | Rate Limit | Est. Duration |
|------|-------------|------------|---------------|
| 1 | `hcloud configure list` | — | <1s |
| 2 | `ShowDomainDetailByName` | — | <2s |
| 3 | `ShowDomainFullConfig/v2` | — | <2s |
| 4 | `python scripts/origin_probe.py` | — | ≤10s |

**Total estimated duration**: < 15 seconds

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=<region> [--parameter=value ...]
```

**Format Rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowDomainDetailByName`, `ShowDomainFullConfig/v2`)
- **Region parameter**: `--cli-region=<region>` (recommended; use cn-north-1 for CDN)
- **Parameter format**: `--key=value` (equals sign, no space)

**Examples:**

```bash
# Correct
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=www.example.com

# Incorrect (space separator)
hcloud CDN ShowDomainFullConfig/v2 --cli-region <region>
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify the version. If not installed or the version is too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
hcloud version
```

> **Prerequisite check: Python >= 3.8 required**
> Python is used for the origin connectivity probe script (`scripts/origin_probe.py`).

```bash
python --version
```

> **Prerequisite check: Python library `requests >= 2.25` available**
> The `scripts/origin_probe.py` probe depends on the `requests` library.

```bash
python -c "import requests; assert requests.__version__ >= '2.25'; print('ok')"
```

> **Prerequisite check: hcloud credentials configured**
>
> Before performing CDN operations, **you must verify that hcloud credentials are configured**:
>
> ```sh
> hcloud configure list
> ```
>
> **If no valid credentials exist, stop and guide the user to configure credentials.**

> **hcloud parameter format requirements**
>
> hcloud (KooCLI) **all parameters must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> Correct: `hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region>`
>
> Incorrect: `hcloud CDN ShowDomainFullConfig/v2 --cli-region <region>`

> **CDN API region requirements**
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
>
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
>
> - **Prohibited** from using `hcloud configure set` to pass plaintext credentials
>
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or configured CLI config files
>
> **Important: Handling user-provided credentials**
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
> ```sh
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

- `cdn:*:query*` — All CDN query-class actions used by this skill (`ListDomains/v2`, `ShowDomainDetailByName`, `ShowDomainFullConfig/v2`)
- `cdn:configuration:queryDomains` — List CDN domains (listed explicitly alongside the wildcard)

---

## Core Commands

Quick reference for all hcloud CDN commands and probe commands used in this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud configure list` | Check credential configuration | None |
| `hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>` | Validate domain permission + get basic info | `--domain_name` |
| `hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<domain>` | Query origin configuration (configs.sources, origin_protocol) | `--domain_name` |
| `python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>` | Origin connectivity probe (HTTP) | `--timeout 10` (10s timeout) |
| `python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>` | Origin connectivity probe (HTTPS) | `--timeout 10` (10s timeout) |

**Notes:**

- All hcloud commands should use `--cli-region=<region>`
- `scripts/origin_probe.py` enforces `--timeout 10` (10-second timeout, default 10)
- `scripts/origin_probe.py` emits a single JSON object on stdout wrapped in `{result, data, error_msg}` (fields inside `data`: `scheme`, `host`, `port`, `connected`, `http_status`,
  `is_private_address`, `duration_ms`, `error`)
- The probe protocol is selected based on origin_protocol (http / https / follow)

## Parameter Confirmation

Before executing the diagnosis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | CDN accelerated domain to diagnose | None | `www.example.com` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User Confirmation Checklist:**

- [ ] Target domain provided
- [ ] User understands this is a read-only diagnosis operation
- [ ] User understands that probe commands have a 10-second timeout
- [ ] User understands that probes send HTTP/HTTPS requests to the origin server (HEAD preferred, GET fallback on 405; read-only, no side effects)

---

## Core Workflows

> **Target domain is required before any diagnosis step.**
>
> - If the user did not provide a target domain, ask the user for the domain name and wait for the reply before starting.
> - Only if the user does not know the domain or asks you to look it up, list the account's domains via `hcloud CDN ListDomains/v2` and ask the user to choose one.
> - Never start the diagnosis without an explicit user-provided domain: do not guess a domain, do not fall back to an example/default domain, and do not pick a domain from the list yourself.

### Step 1: Credential Check and Domain Permission Validation

Check hcloud credential availability, and validate that the domain belongs to the current account via ShowDomainDetailByName.

Detailed steps → [references/task-permission-check.md](references/task-permission-check.md)

### Step 2: Query Origin Configuration

Retrieve the CDN domain's origin configuration (configs.sources, origin_protocol) via ShowDomainFullConfig/v2.

Detailed steps → [references/task-origin-config-query.md](references/task-origin-config-query.md)

### Step 3: Origin Connectivity Probe

Select the probe protocol based on origin_protocol, and probe origin server connectivity via `scripts/origin_probe.py`, parsing the JSON output inside the `{result, data, error_msg}`
envelope (`data.http_status`, `data.connected`, `data.is_private_address`, `data.error`).

Detailed steps → [references/task-origin-probe.md](references/task-origin-probe.md)

### Step 4: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report with IP whitelist prompts and remediation suggestions.

Detailed steps → [references/task-report-generation.md](references/task-report-generation.md)

---

## FAQ

**Q1: What should I do when "Credentials not configured" is reported?**
A: Run `hcloud configure` to configure AK/SK interactively, or set the environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`, then verify with `hcloud configure list`.

**Q2: `ShowDomainDetailByName` returns 404 / CDN.0171?**
A: The domain does not exist or does not belong to the current account. Check the domain spelling and account ownership; use `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100`
to list onboarded domains.

**Q3: 403 insufficient permissions?**
A: Ensure the IAM user has the CDN query permission (`cdn:*:query*`, plus `cdn:configuration:queryDomains`); contact the primary account administrator to grant them. See
[references/iam-policies.md](references/iam-policies.md) for details.

**Q4: Probe timeout (`error.reason=connect_timeout`)?**
A: Return partial results and note "Origin probe timed out. Manual verification recommended."; check local network connectivity, the origin address/port, and whether the origin firewall
allows CDN back-to-source IP ranges.

**Q5: `connect_failed` / `tls_handshake_failed`?**
A: `connect_failed` = connection refused / network unreachable / DNS resolution failure; `tls_handshake_failed` = TCP reachable but HTTPS certificate abnormal (the script never bypasses
certificate validation). Both are handled as "origin unreachable" with an IP whitelist prompt.

**Q6: `missing_library`?**
A: The `requests` library is missing; install `requests>=2.25` following [references/cli-installation-guide.md](references/cli-installation-guide.md) and retry.

**Q7: Origin configuration query shows empty `sources`?**
A: Report "Origin not configured", skip the probe step, and prompt the user to
configure the origin in the CDN console.

**Known Limitations:**

- CDN APIs only support two regions: `cn-north-1` and `ap-southeast-1`
- Probe results reflect the execution environment's network perspective only, not the CDN edge node's back-to-source path
- With `origin_protocol=follow`, both http and https must be probed

**Error Code Quick Reference:**

| Error Code | Meaning | Handling |
|------------|---------|----------|
| 401 | Invalid or expired AK/SK | Reconfigure credentials |
| 403 | Insufficient permissions | Grant `cdn:*:query*` (+ `cdn:configuration:queryDomains`) |
| 404 / CDN.0171 | Domain does not exist or not owned by the current account | Confirm domain ownership |
| `connect_timeout` | TCP connect exceeded the 10s budget | Check network / firewall / origin address and port |
| `connect_failed` | Connection refused / network unreachable / DNS resolution failure | Check the origin service and network |
| `tls_handshake_failed` | TLS handshake failed (invalid / expired certificate, protocol mismatch) | Check the origin certificate (never bypass validation) |
| `missing_library` | `requests` library missing | Install `requests>=2.25` per cli-installation-guide.md |
| `invalid_scheme` / `invalid_host` / `invalid_port` / `invalid_timeout` | Argument validation failure (exit code 2) | Fix the argument and retry |

See [references/troubleshooting.md](references/troubleshooting.md) for the full troubleshooting guide.

## Failure Modes

**Known failure modes and recovery:**

| # | Failure Mode | Trigger Condition | Handling / Recovery |
|---|--------------|-------------------|---------------------|
| 1 | Credentials not configured | `hcloud configure list` shows no valid AK/SK | Abort; guide the user to `hcloud configure` or environment variables |
| 2 | Domain does not exist | `ShowDomainDetailByName` returns 404 / CDN.0171 | Abort; prompt to confirm domain ownership |
| 3 | Insufficient permissions | 403 returned | Abort; prompt to contact the administrator for authorization |
| 4 | API call failed | `ShowDomainFullConfig/v2` returns non-200 | Degrade: report "Origin configuration query failed"; recommend manual confirmation |
| 5 | Origin not configured | `configs.sources` empty or missing | Report "Origin not configured"; skip the probe step |
| 6 | Probe timeout | `error.reason=connect_timeout` | Return partial results ⚠️; recommend manual verification |
| 7 | Connection failed | `error.reason=connect_failed` | Report origin unreachable ❌ + IP whitelist prompt |
| 8 | TLS handshake failed | `error.reason=tls_handshake_failed` | Report TLS failure (never bypass certificate validation) |
| 9 | Missing library | `error.reason=missing_library` | Abort the probe; prompt to install `requests>=2.25` per cli-installation-guide.md |

**Self-check before output:** Before emitting the diagnosis report, verify it contains the 6 mandatory blocks (analysis time / target domain / origin configuration / diagnosis items /
conclusion / remediation suggestion); complete any missing block before output (see [references/acceptance-criteria.md](references/acceptance-criteria.md)).

**Failure propagation:** When any preceding step (Step 1-3) fails and aborts, mark subsequent steps as N/A (do not execute), set the report Conclusion status to "Cannot Diagnose", and
provide a clear next action (authorization / credential configuration / manual verification, etc.).

## Output Format

**Probe JSON output (`scripts/origin_probe.py`):** A single JSON object on stdout, wrapped in the `{result, data, error_msg}` envelope; business fields are inside `data`:

| Field | Type | Required | Description |
|-------|------|:---:|-------------|
| `result` | string | Yes | Enum: `success` / `failed` |
| `data.scheme` | string | Yes | `http` / `https` |
| `data.host` | string | Yes | Origin host (IP literal or domain) |
| `data.port` | integer | Yes | Origin port (1-65535) |
| `data.connected` | boolean | Yes | Whether an HTTP response was received |
| `data.http_status` | integer \| null | Yes | HTTP status code; `null` when no response |
| `data.is_private_address` | boolean | Yes | Whether the origin is a private / loopback / link-local address |
| `data.duration_ms` | integer | Yes | Probe duration in milliseconds |
| `data.error` | object \| null | Yes | `null` on success; `{reason, message}` on failure |
| `error_msg` | string | Yes | Error reason (empty on success) |

**Status enums:**

- `result ∈ {success, failed}`
- `data.error.reason ∈ {connect_timeout, connect_failed, tls_handshake_failed, missing_library, invalid_scheme, invalid_host, invalid_port, invalid_timeout}`
- Report `Status ∈ {Pass, Fail, Partial Pass, Cannot Diagnose}`
- Diagnosis item markers ∈ {✅ Pass, ❌ Fail, ⚠️ Warning, N/A}

**Diagnosis report template:** The full template (separator line `====`, section headers `--- xxx ---`, diagnosis item list, conclusion and remediation suggestion, IP whitelist prompt rules)
and example reports are defined in [references/task-report-generation.md](references/task-report-generation.md).

**Prohibited content:** The report and any output must NEVER include AK/SK, account credentials, or other sensitive information; must NOT fabricate probe data — reflect the `data.*` fields truthfully.

## References

| Document | Description |
|----------|-------------|
| [task-permission-check.md](references/task-permission-check.md) | Step 1: Credential check and domain permission validation |
| [task-origin-config-query.md](references/task-origin-config-query.md) | Step 2: Query origin configuration |
| [task-origin-probe.md](references/task-origin-probe.md) | Step 3: Origin connectivity probe |
| [task-report-generation.md](references/task-report-generation.md) | Step 4: Generate diagnosis report |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification method |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |

---

## Changelog

| Version | Date | Description | Owner |
|---------|------|-------------|-------|
| 1.0.0 | 2026-08-12 | Initial release: origin configuration query + origin connectivity probe + diagnosis report generation; read-only; all 55 non-GET operations prohibited | cdn-ops |
