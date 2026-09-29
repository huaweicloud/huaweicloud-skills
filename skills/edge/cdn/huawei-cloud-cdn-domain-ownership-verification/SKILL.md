---
name: huawei-cloud-cdn-domain-ownership-verification
description: |
  Diagnose CDN domain ownership verification failures using hcloud CLI. Query the ownership verification method (DNS TXT or file verification) configured by CDN, probe the actual
  verification record or file, and compare against the expected verify_content to identify the root cause of verification failures.
  Use this skill when the user wants to: (1) diagnose CDN domain ownership verification failures, (2) check why domain ownership verification is not passing, (3) verify DNS TXT record or
  file verification for CDN domain access, (4) troubleshoot domain ownership verification timeout issues.
  Triggers include: 域名归属验证, 归属验证失败, 域名验证, 验证不通过, 域名接入验证, CDN域名接入, 验证文件, TXT记录验证, 验证文件404, 域名验证超时, ownership verification, domain verification, verify domain ownership, TXT record
  verification, verification file.
  Do NOT use this skill for creating/deleting/modifying CDN domains or configurations, triggering the ownership verification flow, or any other write operation — this skill is strictly
  read-only diagnosis.
tags:
  - cdn
  - ownership
  - verification
  - domain
  - hcloud
  - diagnosis
version: 1.0.0
updated: 2026-08-31
owner: cdn-ops
---

# CDN Domain Ownership Verification Diagnosis

## Overview

This skill diagnoses CDN domain ownership verification failures. It queries the ownership verification method required by CDN (DNS TXT record verification or file verification) via hcloud
CLI, and uses Python probe scripts to verify whether the actual verification record or file matches the expected value, helping users identify the root cause of ownership verification
failures.

**Key Features:**

- Automatic verification method detection (DNS TXT record verification / file verification / already passed)
- DNS TXT record probe via `scripts/dns_txt_probe.py` (dnspython)
- File verification probe via `scripts/file_probe.py` (requests)
- Structured JSON probe output for deterministic parsing
- Structured diagnosis report with fix recommendations

**Tools**: hcloud CLI (KooCLI) + Python probe scripts (`scripts/file_probe.py`, `scripts/dns_txt_probe.py`)
**Probe Timeout**: 10 seconds (enforced by each Python script via `--timeout`, default 10)
**Core Principle**: Read-only diagnosis, no configuration changes

## Scope

**This skill is a strictly read-only diagnosis skill for CDN domain ownership verification.**

**In scope:**

- Query the CDN ownership verification method and verification content via `hcloud CDN ShowVerifyDomainOwnerInfo` (GET)
- Probe the actual verification record/file with `scripts/dns_txt_probe.py` and `scripts/file_probe.py` (read-only network probes)
- Compare actual values against `verify_content` and generate a structured diagnosis report with fix recommendations

**Out of scope (refused, never executed even if requested):**

- Creating, deleting, or modifying CDN domains or domain configurations
- Triggering the ownership verification flow (`VerifyDomainOwner` POST is prohibited)
- Creating refresh/preheat tasks, modifying billing mode, or any other write operation (full list: 55 prohibited operations in
  [references/prohibited-operations.md](references/prohibited-operations.md))

**One problem class**: this skill solves the single problem class "CDN domain ownership verification diagnosis" only; configuration changes belong to the Huawei Cloud CDN console or manual hcloud CLI.

## Triggers

Use this skill when the user's request matches any of these example utterances:

- "My CDN domain ownership verification keeps failing / is not passing"
- "Ownership verification failed / domain verification failed"
- "The TXT record has been added, why is verification still failing?"
- "Verification file returns 404 / verification file not found"
- "Domain verification timed out / verification is not taking effect"
- "CDN domain access prompts me to verify domain ownership"

English trigger keywords: "ownership verification", "domain verification", "verify domain ownership", "TXT record verification", "verification file". The description field additionally lists
bilingual (Chinese/English) trigger keywords so that Chinese user queries are matched as well.

## Near-miss / Do NOT use

Do NOT use this skill when:

- **Creating, deleting, or modifying CDN resources** (domains, configurations, cache rules, certificates, billing mode): use the Huawei Cloud CDN console or run hcloud CLI manually. This
  skill refuses all write operations.
- **Triggering the ownership verification flow** (`VerifyDomainOwner`): this skill only queries verification status via the GET `ShowVerifyDomainOwnerInfo`; triggering verification is done
  in the console or via manual hcloud CLI.
- **Ownership verification is not the issue** (e.g., CDN acceleration quality, cache hit ratio, origin pull failures, billing questions): out of scope.
- **The domain is not under the current account / insufficient permission**: the skill aborts with guidance; it never attempts cross-account or elevated operations.

Near-miss examples (NOT handled by this skill — refuse and redirect):

- "Create a CDN domain for me" → refuse, direct to console
- "Trigger the ownership verification for me" → refuse, direct to console
- "Refresh the CDN cache" → refuse, direct to console

## ⛔ Prohibited Operations (Security Constraints)

> **This skill strictly prohibits all non-GET (write/modify/delete) CDN operations, even if requested by the user.**

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
| ❌ Verify domain ownership | `VerifyDomainOwner` | POST operation; triggers verification flow (use `ShowVerifyDomainOwnerInfo` GET to query status instead) |

> **If the user requests a prohibited operation, refuse and inform:**
> "Per security constraints, this skill does not allow write/delete/modify operations. This skill is for ownership verification diagnosis only. Use the Huawei Cloud CDN console or run hcloud
> CLI manually to change configurations. The complete list of 55 prohibited operations is documented in references/prohibited-operations.md."

## Architecture

```

CDN Domain Ownership Verification Diagnosis
├── hcloud configure list          (credential check)
├── ShowVerifyDomainOwnerInfo      (query ownership verification info + domain permission check)
│   ├── dns_verify_type=TXT        → DNS TXT record verification
│   ├── file_verify_url            → file verification
│   └── verification passed        → cache latency prompt
├── python scripts/file_probe.py --url <file_verify_url> [--timeout 10]
│                                  (file verification probe, emits JSON)
├── python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]
│                                  (DNS TXT record verification; name = dns_verify_name.verify_domain_name; emits JSON)
└── generate diagnosis report
```

### API Call Budget

| Step | API/Command | Rate Limit | Estimated Time |
|------|-------------|------------|----------------|
| 1 | `hcloud configure list` | — | <1s |
| 2 | `ShowVerifyDomainOwnerInfo` | — | <2s |
| 3 | `python scripts/file_probe.py` or `python scripts/dns_txt_probe.py` | — | ≤10s |

**Total estimated time**: < 13 seconds

## KooCLI Command Format Standard

All hcloud CDN commands follow this standard format:

```bash
hcloud CDN <Operation> --cli-region=<region> [--parameter=value ...]

```

**Format rules:**

- **Service name**: `CDN` (uppercase)
- **Operation name**: PascalCase (e.g., `ShowVerifyDomainOwnerInfo`)
- **Region parameter**: `--cli-region=<region>` (recommended, CDN uses cn-north-1)
- **Parameter format**: `--key=value` (connected with equals sign, no spaces)

**Examples:**

```bash
# Correct
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=www.example.com

# Incorrect (space-separated)
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region <region>

```

## Prerequisites

> **Pre-check: Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0**
> Run `hcloud version` to verify the version. If not installed or version is too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md).

```bash
hcloud version

```

> **Pre-check: Python >= 3.8 available**
> Python is required by the probe scripts (`scripts/file_probe.py`, `scripts/dns_txt_probe.py`).

```bash
python --version

```

> **Pre-check: Python libraries available**
> The probe scripts depend on `requests >= 2.25` (file_probe.py) and `dnspython >= 2.1` (dns_txt_probe.py). Confirm both are importable before any probe step runs. Missing libraries abort
> the skill with a clear error message naming the missing library.

```bash
python -c "import requests, dns.resolver; print('ok')"

```

Install if missing:

```bash
pip install requests>=2.25 dnspython>=2.1
```

> **Pre-check: hcloud credentials configured**
>
> Before performing CDN operations, **you must verify that hcloud credentials are configured**:
>
> ```bash
> hcloud configure list
> ```
>
> **If no valid credentials are present, stop and guide the user to configure credentials.**

> **⚠️ hcloud parameter format requirement**
>
> All parameters of hcloud (KooCLI) **must use the `--param=value` format** (connected with equals sign); space-separated format is not supported.
>
> ✅ Correct: `hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region>`
>
> ❌ Incorrect: `hcloud CDN ShowVerifyDomainOwnerInfo --cli-region <region>`

> **⚠️ CDN API region requirement**
>
> CDN API supports only two regions: `cn-north-1` (Beijing) and `ap-southeast-1` (Singapore).
> Query results are region-independent (CDN is a global service).
> **Recommended: use `cn-north-1` uniformly.**

---

## Authentication

> **Pre-check: Huawei Cloud credentials**

> **Security rules (must be observed):**
>
> - **Prohibited** from reading, echoing, or printing AK/SK values
>
> - **Prohibited** from requiring users to input AK/SK directly in the conversation
>
> - **Prohibited** from using `hcloud configure set` to pass plaintext credentials
>
> - **Prohibited** from accepting AK/SK provided directly by users in the conversation
> - **Only allowed** to read credentials from environment variables or the configured CLI configuration file
>
> **⚠️ Important: handling user-provided credentials**
>
> If the user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
>
> - **Stop immediately** - do not execute any commands
> - **Politely refuse** and return the following message:
>
> ```
> To protect account security, do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
> Use the following secure methods to configure credentials:
>
> Method 1: Interactive configuration (recommended)
>     hcloud configure
>     # Enter AK/SK as prompted; credentials will be securely stored in the local configuration file
>
> Method 2: Environment variable configuration
>     export HUAWEICLOUD_SDK_AK=<your-access-key-id>
>     export HUAWEICLOUD_SDK_SK=<your-secret-key>
>
> After configuration is complete, please retry your request.
> ```
>
> - **Do not continue** to perform any Huawei Cloud operations until credentials are configured
>
> **Check CLI configuration**:
>
> ```bash
> hcloud configure list
> ```
>
> Check whether the output contains valid configuration (AK/SK, IAM, etc.).
>
> **If no valid credentials are present, stop here.**

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions:**

- `cdn:*:query*` — All CDN query-class actions used by this skill (`ListDomains/v2`, `ShowVerifyDomainOwnerInfo`)
- `cdn:configuration:queryDomains` — List CDN domains (listed explicitly alongside the wildcard)

---

## Core Commands

Quick reference for all hcloud CDN commands and probe commands used by this skill:

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud configure list` | Check credential configuration | None |
| `hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<domain>` | Query ownership verification info (also confirms the domain belongs to the current account) | `--domain_name` |
| `python scripts/file_probe.py --url <file_verify_url> [--timeout 10]` | File verification probe (emits JSON) | `--url`, `--timeout 10` (default 10) |
| `python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]` | DNS TXT record verification (emits JSON; name must be `dns_verify_name.verify_domain_name`) | `--name`, `--resolver`, `--timeout 10` (default 10) |

**Notes:**

- All hcloud commands should use `--cli-region=<region>`
- Python probe scripts enforce a 10-second timeout via `--timeout` (default 10)
- Each probe script emits a single JSON object on stdout wrapped in `{result, data, error_msg}`; parse `data.http_status` / `data.content_preview` from `file_probe.py` and `data.txt_records`
  / `data.resolver` from `dns_txt_probe.py`

## Parameter Confirmation

Before performing the diagnosis, confirm the following parameters with the user:

| Parameter | Required | Description | Default | Example |
|-----------|----------|-------------|---------|---------|
| `domain_name` | Yes | CDN accelerated domain to diagnose | None | `www.example.com` |
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-1` | `cn-north-1` |

**User confirmation checklist:**

- [ ] Target domain provided
- [ ] User understands this is a read-only diagnostic operation
- [ ] User understands probe commands have a 10-second timeout

---

## Core Workflows

> **Target domain is required before any diagnosis step.**
>
> - If the user did not provide a target domain, ask the user for the domain name and wait for the reply before starting.
> - Only if the user does not know the domain or asks you to look it up, list the account's domains via `hcloud CDN ListDomains/v2` and ask the user to choose one.
> - Never start the diagnosis without an explicit user-provided domain: do not guess a domain, do not fall back to an example/default domain, and do not pick a domain from the list yourself.

### Step 1: Credential Validation

Check hcloud credential availability.

📄 Detailed steps → [references/task-permission-check.md](references/task-permission-check.md)

### Step 2: Query Ownership Verification Info

Obtain the ownership verification method and verification content required by CDN via ShowVerifyDomainOwnerInfo. A successful query also confirms the domain belongs to the current account; a
404/CDN.0171 response means the domain is not under this account, and a 403 response means insufficient permission.

📄 Detailed steps → [references/task-verify-info-query.md](references/task-verify-info-query.md)

### Step 3: File Verification Probe

If the verification method is file verification, probe whether the verification file exists and whether its content matches via `python scripts/file_probe.py`. Parse the returned JSON
`data.http_status` and `data.content_preview` fields (inside the `{result, data, error_msg}` envelope) and compare `data.content_preview` against `verify_content`.

📄 Detailed steps → [references/task-file-probe.md](references/task-file-probe.md)

### Step 4: DNS TXT Record Verification

If the verification method is DNS TXT verification, join the query name first (`dns_query_name = f"{dns_verify_name}.{verify_domain_name}"` — the API returns `dns_verify_name` as a bare
label such as `cdn_verification`), then query the TXT record via `python scripts/dns_txt_probe.py --name <dns_query_name>` and check whether the returned `data.txt_records` list contains
`verify_content`.

📄 Detailed steps → [references/task-dns-txt-verify.md](references/task-dns-txt-verify.md)

### Step 5: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report.

📄 Detailed steps → [references/task-report-generation.md](references/task-report-generation.md)

## Failure Modes

Known failure modes and their recovery strategies. Per-step handling details are in the task references; the probe JSON `error.reason` codes are defined in
[references/related-apis.md](references/related-apis.md).

| Failure Mode | Detection | Recovery Strategy |
|--------------|-----------|-------------------|
| Credentials not configured | `hcloud configure list` shows no valid AK/SK | Abort; guide user to `hcloud configure` or environment variables |
| Domain not under current account | `ShowVerifyDomainOwnerInfo` returns 404 / CDN.0171 | Abort; confirm domain ownership |
| Insufficient permission | 403 response | Abort; grant `cdn:*:query*` (+ `cdn:configuration:queryDomains`) (see [references/iam-policies.md](references/iam-policies.md)) |
| API call failed | non-200 response | Degrade to probe-only results; mark "recommend manual confirmation" in the report |
| Python library missing | probe exit code 2, `error.reason == "missing_library"` | Abort; `pip install requests>=2.25 dnspython>=2.1`, verify with `python -c "import requests, dns.resolver; print('ok')"` |
| File probe connection failure | `error.reason == "connect_failed"` | Mark failure; recommend network check |
| File probe TLS handshake failure | `error.reason == "tls_handshake_failed"` | Mark failure; recommend manual certificate check (never bypass TLS) |
| File probe timeout | `error.reason == "connect_timeout"` | Return partial results; mark "File probe timed out, recommend manual verification" |
| DNS NXDOMAIN | `error.reason == "dns_nxdomain"` | Confirm `dns_verify_name` spelling and zone delegation |
| DNS no answer | `error.reason == "dns_no_answer"` | Confirm the TXT record exists; wait for DNS propagation (5-10 min, up to 24 h) |
| DNS timeout | `error.reason == "dns_timeout"` | Return partial results; retry with `--resolver 8.8.8.8` |
| Unexpected probe error | `error.reason == "unexpected_probe_error"` | Capture stderr traceback; report as skill defect |
| Verification already passed but still failing | verification status = passed | Report cache latency; wait 5-10 min and re-query |

**Failure propagation**: each probe emits exactly one JSON object on stdout wrapped in the `{result, data, error_msg}` envelope; tracebacks go to stderr only, never stdout. The report step
consumes `data.error.reason` by name (see [references/task-report-generation.md](references/task-report-generation.md)).

**Self-check**: run the verification procedure in [references/verification-method.md](references/verification-method.md) and the acceptance criteria in
[references/acceptance-criteria.md](references/acceptance-criteria.md) after any change.

## Output Format

**Probe output envelope**: every probe script emits exactly one JSON object on stdout wrapped in the platform standard `{result, data, error_msg}` envelope; business fields are inside
`data`. Parse `data.*`, never the top level. JSON schemas and field tables: [references/related-apis.md](references/related-apis.md); per-step field consumption:
[references/task-file-probe.md](references/task-file-probe.md) and [references/task-dns-txt-verify.md](references/task-dns-txt-verify.md).

- `file_probe.py` → `data.http_status`, `data.content_preview`, `data.duration_ms`, `data.error.reason`
- `dns_txt_probe.py` → `data.txt_records`, `data.resolver`, `data.duration_ms`, `data.error.reason`

**Diagnosis report template** (full template, status marking rules and example reports in [references/task-report-generation.md](references/task-report-generation.md)):

```

==================== CDN Domain Ownership Verification Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
[Verification Method]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <DNS TXT verification / file verification / already passed>
[File Verification Probe]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <HTTP status code + content match result>
[DNS TXT Record Verification]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <TXT record value + match result>

--- Conclusion ---
Status: <overall status>
Suggestion: <fix recommendation>
```

**Status enumeration**: ✅ Pass (matches expectation) | ❌ Fail (does not match) | ⚠️ Warning (timeout / partial result) | N/A (item not involved in this verification method).

**Prohibited output content**: AK/SK values, tokens, cookies, `/etc/resolv.conf` contents, and any `content_preview` matching a credential pattern — redact as `<content redacted: matches
credential pattern>` (mandatory content safety rule, see [references/task-report-generation.md](references/task-report-generation.md)).

## FAQ

Complete troubleshooting guide with step-by-step resolutions: [references/troubleshooting.md](references/troubleshooting.md).

**Q: hcloud reports no credentials configured / authentication failure?**
A: Run `hcloud configure list` to check; if there is no valid configuration, run `hcloud configure` interactively, or set the environment variables `HUAWEICLOUD_SDK_AK` /
`HUAWEICLOUD_SDK_SK` (never provide AK/SK directly in the conversation).

**Q: The query reports the domain does not exist (404 / CDN.0171)?**
A: Check the domain spelling, confirm the domain has been added to CDN under the current account, and confirm you are using the correct account; you can also view the added domains in the CDN console.

**Q: The query returns 403 permission denied?**
A: Confirm the IAM user has the CDN query permission (`cdn:*:query*`, plus `cdn:configuration:queryDomains`); if not, contact the administrator to grant it (see [references/iam-policies.md](references/iam-policies.md)).

**Q: The probe script reports missing_library?**
A: Install the dependencies: `pip install requests>=2.25 dnspython>=2.1`, then verify with `python -c "import requests, dns.resolver; print('ok')"` (see
[references/cli-installation-guide.md](references/cli-installation-guide.md)).

**Q: File verification returns 404 / connection failure?**
A: Confirm the verification file has been uploaded to the origin server as prompted; check the network connectivity from the local machine to the verification file URL (firewall / egress policy).

**Q: DNS TXT verification returns no record / NXDOMAIN?**
A: Confirm the TXT record has been added (host record is the bare label `dns_verify_name`; the full query name must be joined: `dns_query_name = f"{dns_verify_name}.{verify_domain_name}"`);
wait for DNS to take effect (5-10 minutes, up to 24 hours); use `--resolver 8.8.8.8` to rule out local resolver cache.

**Q: The probe timed out?**
A: Return partial results and mark the timeout; check the network; for DNS, retry with an explicit public resolver; you can also run the probe script manually to confirm.

**Q: Ownership verification already passed but still reports failure?**
A: This may be cache latency; wait 5-10 minutes and re-query; if it still fails, contact CDN technical support.

### Known Limitations

- Probes do not follow redirects (`allow_redirects=False`); a 3xx `data.http_status` is reported as-is
- TLS certificate validation is never bypassed (no `-k` equivalent)
- Only the TXT record type is queried (no AXFR, SRV, NS, ANY)
- CDN API supports only two regions: `cn-north-1` and `ap-southeast-1` (recommend `cn-north-1` uniformly)
- `--timeout` accepts values in [1, 30] only; out-of-range values exit with code 2
- `content_preview` is capped at the first 256 bytes (UTF-8, `errors="replace"`)
- Verification file URL schemes are restricted to http/https (no `file://`, `ftp://`, `gopher://`)

## Test Examples

Acceptance checklist: [references/acceptance-criteria.md](references/acceptance-criteria.md); end-to-end verification procedure with expected outputs:
[references/verification-method.md](references/verification-method.md).

### Test Case 1: DNS TXT verification passed (typical)

```bash
python scripts/dns_txt_probe.py --name cdn_verification.example.com
# → {"result": "success", "data": {"name": "cdn_verification.example.com", "resolver": "system",
#    "txt_records": ["verify_xxxxxxx"], "duration_ms": 38, "error": null}, "error_msg": ""}

```

Expected: `data.txt_records` contains `verify_content` → DNS verification passed ✅ → Report Status = "Ownership verification passed".

### Test Case 2: File verification failed (failure scenario)

```bash
python scripts/file_probe.py --url http://www.example.com/verify.txt
# → {"result": "success", "data": {"url": "http://www.example.com/verify.txt", "http_status": 404,
#    "content_length": null, "content_preview": null, "duration_ms": 120, "error": null}, "error_msg": ""}

```

Expected: `data.http_status == 404` → File verification failed ❌ → Report "Verification file does not exist. Please upload the verification file as prompted."

### Test Case 3: Probe timeout (boundary scenario)

```bash
python scripts/file_probe.py --url http://www.example.com/verify.txt --timeout 10
# → {"result": "failed", "data": {"url": "...", "http_status": null,
#    "error": {"reason": "connect_timeout", "message": "..."}}, "error_msg": "connect_timeout"}

```

Expected: `data.error.reason == "connect_timeout"` → return partial results, mark "File probe timed out, recommend manual verification" ⚠️.

### Test Case 4: Invalid argument (boundary scenario)

```bash
python scripts/dns_txt_probe.py --name cdn_verification.example.com --timeout 999

```

Expected: exit code 2, `error.reason == "invalid_timeout"` (message "Timeout must be in range [1, 30], got 999").

### Test Case 5: Domain not under current account (failure scenario)

```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=cn-north-1 --domain_name=not-mine.example.com

```

Expected: 404 / CDN.0171 → abort with "Domain not under current account. Please confirm domain ownership."

### Test Case 6: DNS TXT value mismatch (failure scenario)

```bash
python scripts/dns_txt_probe.py --name cdn_verification.example.com
# → data.txt_records == ["other_value"] (does not contain verify_content)

```

Expected: DNS verification failed ❌ → Report "TXT record value mismatch" with expected and actual values.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-08-31 | Initial version: hcloud CLI `ShowVerifyDomainOwnerInfo` query + Python probe scripts (`file_probe.py`, `dns_txt_probe.py`) replacing former shell-based probe commands; standardized `{result, data, error_msg}` JSON envelope; 55 prohibited non-GET operations with refusal message; structured diagnosis report with status enumeration |

---

## References

| Document | Description |
|----------|-------------|
| [task-permission-check.md](references/task-permission-check.md) | Step 1: Credential validation |
| [task-verify-info-query.md](references/task-verify-info-query.md) | Step 2: Query ownership verification info |
| [task-file-probe.md](references/task-file-probe.md) | Step 3: File verification probe |
| [task-dns-txt-verify.md](references/task-dns-txt-verify.md) | Step 4: DNS TXT record verification |
| [task-report-generation.md](references/task-report-generation.md) | Step 5: Generate diagnosis report |
| [prohibited-operations.md](references/prohibited-operations.md) | All 55 prohibited non-GET operations (POST/PUT/DELETE) |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [related-apis.md](references/related-apis.md) | API and CLI command reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification method |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
