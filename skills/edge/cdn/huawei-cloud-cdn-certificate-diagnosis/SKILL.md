---
name: huawei-cloud-cdn-certificate-diagnosis
version: 1.1.0
owner: cdn-ops
description: |
  Triggers include: "certificate diagnosis", "certificate expiry", "HTTPS certificate", "certificate configuration", "SSL certificate", "cert expiry check".
  Diagnose CDN HTTPS certificate configuration and expiration status using hcloud CLI. Query the certificate configuration via ShowCertificatesHttpsInfo/v2, probe the actual certificate served by the CDN edge via a Python TLS probe script (scripts/cert_probe.py), and compute days remaining until expiration to identify certificate misconfiguration, impending expiry, or already-expired certificates.
  Use this skill when the user wants to: (1) diagnose CDN HTTPS certificate issues, (2) check certificate expiration status, (3) verify SSL/TLS certificate configuration on a CDN domain, (4) troubleshoot HTTPS certificate deployment failures.
  Do NOT use this skill for certificate configuration changes (upload/update/delete/renew), CDN domain management, or non-CDN domains — this is a read-only diagnosis skill.
tags:
  - cdn
  - certificate
  - https
  - diagnosis
  - hcloud
---

# CDN Certificate Diagnosis

## Overview

This skill diagnoses CDN domain HTTPS certificate configuration and expiration status. It queries the certificate configuration on CDN via hcloud CLI (`ShowCertificatesHttpsInfo/v2`), probes
the actual certificate served by the CDN edge node via a Python TLS probe script (`python scripts/cert_probe.py`), and computes days remaining until expiration via a Python script, helping
users identify issues such as certificate not configured, configuring, impending expiry, or already expired.

**Key Features:**

- Automatically identifies certificate configuration status (not configured / configuring / configured)
- Retrieves the certificate name and expiration time configured on CDN
- Probes the actual served certificate chain via `scripts/cert_probe.py` (expiration time, issuer, CN, SAN; JSON output)
- Computes days remaining via Python (normal / warning / expired)
- Structured diagnosis report with a mandatory **Certificate Summary** block that explicitly prints the certificate's common info (name, status, issuer, CN, SAN, validity period, days
  remaining) to the user
- Fix recommendations

**Tool**: hcloud CLI (KooCLI) + Python >= 3.8 (stdlib `ssl` + `socket` for the probe; no third-party dependency)
**Probe Timeout**: 10 seconds (enforced by `cert_probe.py` via `--timeout`, default 10, range 1-30)
**Core Principle**: Read-only diagnosis; no configuration changes are performed

## Scope

This skill is scoped to **CDN HTTPS certificate diagnosis only** — one class of problem.

**In scope:**

- Querying CDN domain certificate configuration via `ShowCertificatesHttpsInfo/v2` (https_status, cert_name, expiration_time)
- Probing the certificate actually served by the CDN edge via `scripts/cert_probe.py` (issuer, CN, SAN, validity period)
- Computing days remaining until expiration via `scripts/cert_expiry_check.py`
- Generating a structured certificate diagnosis report with conclusion and fix recommendations

**Out of scope (do not attempt):**

- Certificate configuration changes (upload / update / delete / renew)
- CDN domain management (create / delete / enable / disable / origin / cache-rule / billing changes)
- TLS/HTTPS inspection of non-CDN domains or general websites
- Any non-GET CDN operation — see the Prohibited Operations section below

**Applicable scenarios**: the user asks to diagnose CDN HTTPS certificate issues,
check certificate expiration status, verify SSL/TLS certificate configuration on
a CDN domain, or troubleshoot HTTPS certificate deployment failures.

## Triggers

Use this skill when the user's request matches any of the following:

- "diagnose the HTTPS certificate of www.example.com"
- "is the certificate expired?"
- "how many days until the certificate expires?"
- "check the certificate configuration of a CDN domain"
- "certificate diagnosis", "certificate expiry", "HTTPS certificate", "certificate configuration", "SSL certificate"

## Near-miss / Do NOT use

Do NOT use this skill when:

- The user wants to **configure, update, delete, or renew** a certificate — refuse and direct to the Huawei Cloud CDN console or manual hcloud CLI (see the Prohibited Operations section below)
- The domain is **not a CDN-accelerated domain** — `cert_probe.py` only probes CDN-accelerated domains via a TLS handshake
- The user wants **CDN domain management** (create/delete/enable/disable domains, origin, cache rules, billing)
- The user wants general **port scanning or network diagnostics** — this skill performs a single TLS handshake against `<domain>:443` only
- The user wants CDN **traffic statistics or monitoring**

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
| ❌ Modify certificate config | `UpdateDomainMultiCertificates` (v1/v2), `UpdateHttpsInfo` | Write operations; may interrupt HTTPS service |
| ❌ Create refresh/preheat tasks | `CreateRefreshTasks` (v1/v2), `CreatePreheatingTasks` (v1/v2) | Write operations; affects edge cache |

> **If a user requests a prohibited operation, you must refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is read-only for certificate diagnosis. Please use the Huawei Cloud CDN console or run
> hcloud CLI manually for certificate configuration changes. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

## Architecture

```
CDN Certificate Diagnosis
├── hcloud configure list              (credential validation)
├── ShowDomainDetailByName             (domain permission validation + basic info)
├── ShowCertificatesHttpsInfo/v2       (certificate configuration query)
│   ├── Match https[] element by domain_name (response is wrapped in total/https)
│   ├── https_status=0                 → certificate not configured; stop and report
│   ├── https_status=2                 → certificate configuring; prompt to wait
│   └── https_status=3                 → certificate configured; continue probing
├── python scripts/cert_probe.py         (actual certificate status probe)
│   ├── Parse JSON: data.tls.subject_cn, data.tls.issuer_cn, data.tls.not_before, data.tls.not_after, data.tls.san_list (wrapped in {result, data, error_msg})
│   └── Compare data.tls.not_after against API-returned expiration_time
├── python scripts/cert_expiry_check.py  (days remaining calculation)
│   ├── data.days_remaining > 30       → normal
│   ├── 0 < data.days_remaining ≤ 30   → warning
│   └── data.days_remaining ≤ 0        → expired
└── Generate diagnosis report
```

### API Call Budget

| Step | API/Command | Rate Limit | Est. Duration |
|------|-------------|------------|---------------|
| 1 | `hcloud configure list` | — | <1s |
| 2 | `ShowDomainDetailByName` | — | <2s |
| 3 | `ShowCertificatesHttpsInfo/v2` | — | <2s |
| 4 | `python scripts/cert_probe.py --domain <domain> --timeout 10` | — | ≤10s |
| 5 | `python scripts/cert_expiry_check.py` | — | <1s |

**Total est. duration**: < 16 seconds

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=<region> [--parameter=value ...]
```

**Format Rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowDomainDetailByName`, `ShowCertificatesHttpsInfo/v2`)
- **Region parameter**: `--cli-region=<region>` (recommended; CDN uses cn-north-1)
- **Parameter format**: `--key=value` (equals sign, no space)

**Examples:**

```bash
# Correct
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=www.example.com

# Incorrect (space-separated)
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region <region>
```

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 required**
> Run `hcloud version` to verify the version. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
hcloud version
```

> **Prerequisite check: Python >= 3.8 available**
> Python is required to run the certificate probe script `scripts/cert_probe.py`
> and the days-remaining calculation script `scripts/cert_expiry_check.py`.
> The probe uses only the Python standard library (`ssl`, `socket`),
> so no third-party packages need to be installed.

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
> ✅ Correct: `hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region>`
>
> ❌ Incorrect: `hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region <region>`

> **⚠️ CDN API region requirements**
>
> CDN APIs only support two regions: `cn-north-1` (Beijing) and `ap-southeast-1` (Singapore).
> Query results are region-independent (CDN is a global service).
> **Recommended: use `cn-north-1`**.

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials**

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
> 1. **Stop immediately** - Do not execute any commands
> 2. **Politely refuse** and return the following message:
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

- `cdn:*:query*` — All CDN query-class actions used by this skill (`ListDomains/v2`, `ShowDomainDetailByName`, `ShowCertificatesHttpsInfo/v2`)
- `cdn:configuration:queryDomains` — List CDN domains (listed explicitly alongside the wildcard)

---

## Core Commands

Quick reference for all hcloud CDN commands, probe commands, and calculation commands used in this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud configure list` | Check credential configuration | None |
| `hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>` | Validate domain permission + get basic info | `--domain_name` |
| `hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<domain>` | Query certificate configuration | `--domain_name` |
| `python scripts/cert_probe.py --domain <domain_name> --timeout 10` | Probe actual certificate status (TLS handshake, JSON output) | `--domain`, `--timeout` (default 10, range 1-30) |
| `python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>` | Compute days remaining until expiration | `--expiration_time` |

**Notes:**

- All hcloud commands should use `--cli-region=<region>`
- `cert_probe.py` enforces a 10-second timeout by default (configurable via `--timeout`, range 1-30) and emits a single JSON object on stdout with the TLS certificate metadata
- The Python probe uses stdlib `ssl` + `socket` only; no third-party dependency needs to be installed
- The Python script handles only the days-remaining calculation logic; it does not handle business flow. Its output is wrapped in the platform standard `{result, data, error_msg}` envelope —
  read `data.days_remaining` / `data.status`
- When `expiration_time` is empty, the Python script outputs `{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}`

## Parameter Confirmation

Before executing the diagnosis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | CDN accelerated domain to diagnose | None | `www.example.com` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User Confirmation Checklist:**

- [ ] Target domain provided
- [ ] User understands this is a read-only diagnosis operation
- [ ] User understands the probe command has a 10-second timeout
- [ ] User understands this skill does not perform certificate configuration changes

---

## Core Workflows

> **Target domain is required before any diagnosis step.**
>
> - If the user did not provide a target domain, ask the user for the domain name and wait for the reply before starting.
> - Only if the user does not know the domain or asks you to look it up, list the account's domains via `hcloud CDN ListDomains/v2` and ask the user to choose one.
> - Never start the diagnosis without an explicit user-provided domain: do not guess a domain, do not fall back to an example/default domain, and do not pick a domain from the list yourself.

### Step 1: Credential Validation and Domain Permission Validation

Check hcloud credential availability, and validate via ShowDomainDetailByName that the domain belongs to the current account.

📄 Detailed steps → [references/task-permission-check.md](references/task-permission-check.md)

### Step 2: Query Certificate Configuration

Retrieve the certificate status, certificate name, and expiration time configured on CDN via ShowCertificatesHttpsInfo/v2.

📄 Detailed steps → [references/task-cert-config-query.md](references/task-cert-config-query.md)

### Step 3: Probe Actual Certificate Status

Probe the certificate chain information (expiration time, issuer, CN, SAN) actually served by the CDN edge node via `python scripts/cert_probe.py --domain <domain_name> --timeout 10`. The
script emits a single JSON object on stdout wrapped in the `{result, data, error_msg}` envelope, with business fields inside `data`: `data.domain`, `data.connected`, `data.tls`
(`subject_cn`, `issuer_cn`, `not_before`, `not_after`, `san_list`), `data.duration_ms`, and `data.error` (`{reason, message}` on failure).

📄 Detailed steps → [references/task-cert-probe.md](references/task-cert-probe.md)

### Step 4: Compute Days Remaining

Call `python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>` to compute the days remaining until certificate expiration.

📄 Detailed steps → [references/task-expiry-check.md](references/task-expiry-check.md)

### Step 5: Generate Diagnosis Report

Aggregate the query and probe results to generate a structured text diagnosis report. The report MUST include a mandatory **Certificate Summary (Common Info)** block that explicitly prints
the certificate's commonly used information (certificate name, status, issuer, CN, SAN, Valid From / Expires On, days remaining) directly to the user.

📄 Detailed steps → [references/task-report-generation.md](references/task-report-generation.md)

---

## FAQ

### Q1: Credentials not configured

**Symptom**: `hcloud configure list` shows no AK/SK; hcloud commands return an authentication error.
**Fix**: Run `hcloud configure` interactively, or export `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`, then re-verify with `hcloud configure list`.

### Q2: Domain not found (404 / CDN.0171)

**Symptom**: `ShowDomainDetailByName` returns 404 or `error_code: CDN.0171`.
**Fix**: Check the domain spelling; confirm the domain is onboarded to CDN under the current account; run `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100` to list onboarded domains.

### Q3: Insufficient permission (403)

**Symptom**: `ShowDomainDetailByName` or `ShowCertificatesHttpsInfo/v2` returns 403.
**Fix**: Ensure the IAM user has `cdn:*:query*` (plus `cdn:configuration:queryDomains`); contact the primary account administrator to grant them (see [iam-policies.md](references/iam-policies.md)).

### Q4: cert_probe.py times out or cannot connect

**Symptom**: `data.error.reason == "connect_timeout"` / `"connect_failed"`.
**Fix**: Return partial results annotated "Certificate probe timed out"; check TCP 443 egress and confirm the CNAME is in effect; re-run the probe manually.

### Q5: https_status=0 (certificate not configured)

**Symptom**: `ShowCertificatesHttpsInfo/v2` returns `https_status=0`.
**Fix**: Report "This domain has no HTTPS certificate configured"; skip probe and calculation; recommend configuring a certificate in the CDN console.

**Known limitations:**

- The probe checks only TCP 443 (`<domain>:443`); non-standard ports and HTTP-only domains are not probed
- CDN APIs support only two regions: `cn-north-1` and `ap-southeast-1` (recommended: `cn-north-1`)
- Probe results and the API may differ temporarily due to cache or sync latency

**Common error codes:**

| Error | Meaning | Handling |
|-------|---------|----------|
| 404 / CDN.0171 | Domain not found or not under the current account | Stop; confirm domain ownership |
| 403 | Insufficient permission | Stop; grant `cdn:*:query*` + `cdn:configuration:queryDomains` |
| connect_timeout | Probe timed out (10s default) | Return partial results; annotate timeout |
| tls_handshake_failed | TLS handshake failed (expired/revoked/untrusted cert) | Report real deployment state; do NOT relax verification |

Full Q&A troubleshooting guide: [references/troubleshooting.md](references/troubleshooting.md)

## Failure Modes

| Failure Mode | Detection | Recovery Strategy |
|--------------|-----------|-------------------|
| Credentials not configured | `hcloud configure list` empty / auth error | Stop; guide `hcloud configure` or environment variables |
| Domain not found | `ShowDomainDetailByName` 404 / CDN.0171 | Stop; confirm domain ownership |
| Insufficient permission | 403 from domain/certificate query | Stop; request `cdn:*:query*` + `cdn:configuration:queryDomains` |
| API call failed | Non-200 from `ShowCertificatesHttpsInfo/v2` | Retry once; if still failing, degrade to probe results only, annotated "API query failed" |
| Probe timeout | `data.error.reason == "connect_timeout"` | Return partial results; annotate timeout; recommend manual verification |
| TLS handshake failure | `data.error.reason == "tls_handshake_failed"` | Report the real deployment state; cross-check API `expiration_time`; never relax verification |
| expiration_time empty | API returns no valid `expiration_time` | Do not calculate; report "Expiration time unknown"; expose the raw API response |
| Python unavailable | `python --version` fails or < 3.8 | Install Python >= 3.8, or calculate days remaining manually from the ms timestamp |

**Self-check before report output**: verify the mandatory Certificate Summary block (name / status / issuer / CN / SAN / Valid From / Expires On / Days Remaining) is complete, and `N/A` is
used only for genuinely unavailable fields; never present a probe failure as a success.

**Failure propagation**: each failure is surfaced as `data.error.reason` in the `{result, data, error_msg}` envelope and reflected in the report's Diagnosis Items with ✅/❌/⚠️ markers; no
failure is silently dropped.

## Output Format

All machine-readable outputs use the platform standard envelope:

```json
{"result": "success|failed", "data": {...}, "error_msg": ""}
```

**JSON schema:**

| Script | `data` fields | Status enum |
|--------|---------------|-------------|
| `scripts/cert_probe.py` | `domain`, `connected`, `tls` (`subject_cn`, `issuer_cn`, `not_before`, `not_after`, `san_list`), `duration_ms`, `error` (`reason`, `message`) | `error.reason`: `connect_timeout` / `connect_failed` / `tls_handshake_failed` / `unexpected_probe_error` / `invalid_domain` / `invalid_timeout` |
| `scripts/cert_expiry_check.py` | `days_remaining` (int\|null) | `normal` \| `warning` \| `expired` \| `unknown` |

**Diagnosis report template** (generated in Step 5):

```text
==================== CDN Certificate Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>

--- Certificate Summary (Common Info) ---
Certificate Name: <cert_name> / N/A
Certificate Status: <not configured | configuring | configured>
Issuer: <data.tls.issuer_cn>
CN: <data.tls.subject_cn>
SAN: <data.tls.san_list, joined with ", ">
Valid From: <data.tls.not_before>
Expires On: <data.tls.not_after> (API expiration_time: <readable date>)
Days Remaining: <data.days_remaining> (<data.status>)

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass / ❌ Fail / ⚠️ Warning
[Certificate Configuration Status]: ✅ Pass / ❌ Fail / ⚠️ Warning
[Actual Certificate Probe]: Pass / Fail / Warning / N/A
[Days Remaining Calculation]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A

--- Conclusion ---
Status: <overall status>
Suggestion: <fix recommendation>
```

**Status markers**: ✅ Pass (normal) / ❌ Fail (failed or expired) / ⚠️ Warning (about to expire, configuring, timed out, partial) / N/A (step not involved). Full decision table and example reports: [references/task-report-generation.md](references/task-report-generation.md).

**Prohibited in output (never include)**: AK/SK or any credential material; raw DER/PEM certificate bytes or private keys; raw millisecond timestamps as the primary display (convert to
readable dates); internal URLs or tokens.

**Sample output** (normal certificate): see [references/verification-method.md](references/verification-method.md) Expected Output.

## Test Cases

### Example 1 — Typical: certificate configured and valid

```bash
python scripts/cert_probe.py --domain www.example.com --timeout 10
```

**Expected output**: `result == "success"`, `data.connected == true`, `data.tls.subject_cn` / `issuer_cn` / `not_before` / `not_after` non-empty, `data.tls.san_list` present (may be empty),
`data.error == null`.

### Example 2 — Edge case: expiration_time empty

```bash
python scripts/cert_expiry_check.py --expiration_time ""
```

**Expected output**: `{"result": "success", "data": {"days_remaining": null, "status": "unknown"}, "error_msg": ""}`; no calculation performed; report "Certificate expiration time unknown".

### Example 3 — Failure case: invalid domain argument

```bash
python scripts/cert_probe.py --domain "bad domain" --timeout 10
```

**Expected output**: exit code 2; JSON with `data.error.reason == "invalid_domain"`; no probe attempted.

Full verification procedure (6 steps with expected JSON and report samples): [references/verification-method.md](references/verification-method.md) · Acceptance checklist: [references/acceptance-criteria.md](references/acceptance-criteria.md)

## Changelog

| Version | Date | Owner | Changes |
|---------|------|-------|---------|
| v1.0.0 | 2026-08-29 | cdn-ops | Initial version: CDN certificate configuration query + TLS probe + days-remaining calculation |
| v1.1.0 | 2026-08-31 | cdn-ops | Migrated the TLS probe from the legacy HTTP-based implementation to `scripts/cert_probe.py` (stdlib `ssl`/`socket`, zero third-party dependency); added `scripts/cert_expiry_check.py`; introduced the `{result, data, error_msg}` JSON contract; IAM scope unchanged |

**Deprecation notice**: the legacy HTTP-based probe (v1.0.0) is **deprecated** and must not be used; all diagnosis must run through the Python probe scripts.

## References

| Document | Description |
|----------|-------------|
| [task-permission-check.md](references/task-permission-check.md) | Step 1: Credential validation and domain permission validation |
| [task-cert-config-query.md](references/task-cert-config-query.md) | Step 2: Query certificate configuration |
| [task-cert-probe.md](references/task-cert-probe.md) | Step 3: Probe actual certificate status |
| [task-expiry-check.md](references/task-expiry-check.md) | Step 4: Compute days remaining |
| [task-report-generation.md](references/task-report-generation.md) | Step 5: Generate diagnosis report |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification method |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
