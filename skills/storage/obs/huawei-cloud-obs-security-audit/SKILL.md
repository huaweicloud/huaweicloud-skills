---
name: huawei-cloud-obs-security-audit
description: |
  Audit Huawei Cloud OBS bucket security configuration: ACL permissions, Block Public Access (BPA), encryption (SSE-KMS/SSE-OBS/SSE-C), versioning, cross-region replication, HTTPS enforcement (SecureTransport), bucket logging, Referer anti-hotlinking, CORS rules, and object naming patterns. Generates a security score report with risk items and remediation recommendations.
  Use when the user wants to: perform a security audit on an OBS bucket, check bucket ACL permissions, verify BPA status, review encryption configuration, check versioning and replication, audit HTTPS enforcement, review logging and anti-hotlinking, inspect CORS rules, detect sequential object naming patterns, or generate a comprehensive OBS security assessment report.
  Triggers include: "OBS安全审计", "OBS安全配置", "桶安全检查", "安全评分", "ACL权限审计", "BPA状态", "桶加密检查", "多版本控制", "跨区域复制", "HTTPS强制传输", "桶日志", "防盗链", "CORS规则", "对象命名", "OBS security audit", "bucket security", "security score", "BPA status", "encryption check", "versioning check", "replication check", "HTTPS enforcement", "bucket logging", "anti-hotlinking", "Referer check", "CORS check", "naming pattern".
tags: ["huawei-cloud", "obs", "security", "audit", "object-storage"]
---

# Huawei Cloud OBS Security Audit Skill

> Audit OBS bucket security configuration across 10 dimensions: ACL, BPA, encryption, versioning, replication, HTTPS enforcement, logging, anti-hotlinking, CORS, and object naming patterns. Outputs a security score report with risk items and remediation recommendations.

## Overview

This skill performs a **comprehensive read-only security audit** of an OBS (Object Storage Service) bucket. It checks 10 security configuration dimensions, assigns a weighted score (0–100), and generates a report with risk severity levels and prioritized remediation recommendations.

```text
User Request
  └── Action Router
       ├── Single Check (R3)  → audit one specific security dimension
       └── Full Audit (R3)    → run all 10 checks → security score + risk report
```

All operations are **read-only (R3)** — no mutations to bucket configuration or objects.

### Capability Matrix

| # | Action | Capability | Mode | Severity |
|---|--------|-----------|------|----------|
| 1 | `huawei_audit_obs_acl` | Query bucket ACL permissions (private / public-read / public-read-write) | CLI | R3 Query |
| 2 | `huawei_audit_obs_bpa` | Query Block Public Access (BPA) status | CLI | R3 Query |
| 3 | `huawei_audit_obs_encryption` | Query bucket encryption config (SSE-KMS / SSE-OBS / SSE-C) | CLI | R3 Query |
| 4 | `huawei_audit_obs_versioning` | Query multi-version control status | CLI | R3 Query |
| 5 | `huawei_audit_obs_replication` | Query cross-region replication rules | CLI | R3 Query |
| 6 | `huawei_audit_obs_https` | Query HTTPS enforcement (SecureTransport condition in bucket policy) | CLI | R3 Query |
| 7 | `huawei_audit_obs_logging` | Query bucket logging status | CLI | R3 Query |
| 8 | `huawei_audit_obs_referer` | Query Referer anti-hotlinking configuration | CLI | R3 Query |
| 9 | `huawei_audit_obs_cors` | Query CORS rules | CLI | R3 Query |
| 10 | `huawei_audit_obs_naming` | Check object naming patterns (sequential vs random prefix) | CLI | R3 Query |
| 11 | `huawei_audit_obs_full` | Execute full security audit (all 10 checks) → score report | CLI | R3 Analysis |

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

### Security Score Model

| Audit Item | Weight | Max Score | Scoring Rule |
|-----------|--------|-----------|-------------|
| ACL permissions | High | 15 | private=15, public-read=5, public-read-write=0 |
| BPA status | High | 15 | enabled=15, disabled=0 |
| Bucket encryption | High | 15 | SSE-KMS=15, SSE-OBS=12, SSE-C=10, none=0 |
| Versioning | Medium | 10 | enabled=10, disabled/suspended=0 |
| Cross-region replication | Medium | 10 | configured=10, not configured=0 |
| HTTPS enforcement | High | 15 | policy has SecureTransport=true=15, otherwise=0 |
| Bucket logging | Medium | 10 | enabled=10, disabled=0 |
| Anti-hotlinking (Referer) | Medium | 5 | configured=5, not configured=0 |
| CORS rules | Low | 5 | no wildcard *=5, has wildcard=2, no CORS=5 (no cross-domain need) |
| Object naming pattern | Low | 10 | random prefix=10, partial sequential=5, fully sequential=0 |

**Total: 110 points** | **Grades**: 99–110 Excellent | 77–98 Good | 55–76 Fair | 0–54 High Risk

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | Installed and authenticated. See `references/cli-installation-guide.md` |
| **KooCLI version** | `>= 3.2.0` (verify with `hcloud version`) |
| **obsutil** | `>= 5.5.0` — the hcloud OBS module maps 1:1 to obsutil commands (verify with `obsutil version`) |
| **obsutil credentials** | Configured via `hcloud obs config` (interactive, prompts for AK/SK/endpoint) or `obsutil config`; or via `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` env vars. AK/SK are **never** hardcoded in this skill or its scripts |
| **IAM permissions** | Read-only OBS bucket query permissions (least-privilege policy in `references/iam-policies.md`) |
| **Python 3.8+** | Required for `scripts/obs_security_auditor.py` |

> **Region note:** with the obsutil passthrough mode, the region is part of the endpoint (`obs.{region}.myhuaweicloud.com`), not a `--cli-region` flag. Choose the endpoint matching the bucket's region (e.g. `obs.cn-north-4.myhuaweicloud.com`).
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

### Full Security Audit (R3) — read-only, agent may run automatically

```text
1. (optional) skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls -limit=1  → list buckets, pick one
2. python3 scripts/obs_security_auditor.py audit --bucket {bucket}  → run all 10 checks → score + report
3. Present findings: total score, grade, per-item results, risk list, remediation recommendations
```

### Single Dimension Check (R3) — read-only, agent may run automatically

```text
1. User specifies which dimension to check (e.g. "check ACL of bucket X")
2. Run the corresponding hcloud obs command (see Core Commands)
3. Present the raw configuration + security assessment for that item
```

## Core Commands

### 1. Bucket Metadata & ACL (via obsutil stat)

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- ` — bare `hcloud` calls are strictly forbidden.**

# Get bucket metadata: ACL, versioning status, storage class, location, etc.
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs stat obs://{bucket} -acl

# The stat output includes:
#   - ACL (private / public-read / public-read-write)
#   - Versioning status (Enabled / Suspended / None)
#   - Storage class, location, creation date
```

### 2. Bucket Policy (for HTTPS SecureTransport analysis)

```bash
# Get bucket policy JSON — analyze for SecureTransport condition
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get
```

### 3. CORS Rules

```bash
# Get CORS configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs cors obs://{bucket} -method=get
```

### 4. Object Listing (naming pattern analysis)

```bash
# List objects (brief mode) for naming pattern detection
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls obs://{bucket} -limit={limit} -s
```

### 5. Encryption, BPA, Replication, Logging, Referer (via obsutil passthrough)

```bash
# Bucket encryption configuration
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs encryption obs://{bucket} -method=get

# Block Public Access (BPA) — dedicated obsutil subcommand (with bucket policy fallback)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs get-public-access-block obs://{bucket}
# Fallback: analyze bucket policy for explicit public-access deny statements
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Cross-region replication — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Bucket logging — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get

# Referer anti-hotlinking — parsed from bucket policy JSON (no dedicated obsutil subcommand)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs bucketpolicy obs://{bucket} -method=get
```

> **Note:** `hcloud obs replication`, `hcloud obs logging`, and `hcloud obs referer` subcommands do **not exist** in obsutil. These checks are performed by fetching the bucket policy JSON (`bucketpolicy -method=get`) and parsing for relevant configuration fields. If the bucket policy does not contain the relevant configuration, the check returns a WARN with 0 score and a "Verify manually via OBS console" recommendation.
>
> **BPA:** The auditor first tries the dedicated `get-public-access-block` subcommand. If unavailable, it falls back to analyzing the bucket policy for explicit `Deny` statements with `Principal: *` (public access denial). If neither is found, the check returns CRITICAL.
>
> If an obsutil command returns 404 or empty response, the configuration is treated as **"not configured"** (not an error). The auditor script handles this gracefully. If a subcommand is not supported by the installed obsutil version, the check degrades to a WARN with 0 score.

### 6. Full Audit (all 10 checks via Python script)

```bash
# Run comprehensive security audit — all 10 dimensions
python3 scripts/obs_security_auditor.py audit --bucket {bucket}

# With optional parameters
python3 scripts/obs_security_auditor.py audit --bucket {bucket} --endpoint obs.{region}.myhuaweicloud.com --output /tmp/report.json --format json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--bucket` | Yes | Bucket name (no `obs://` prefix) |
| `--endpoint` | No | OBS endpoint override (e.g. `obs.cn-north-4.myhuaweicloud.com`) |
| `--output` | No | Output file path for the report |
| `--format` | No | Output format: `text` (default) or `json` |

## KooCLI Command Format Standard

hcloud <Service> <Operation> --cli-region=<region> [--key=value ...] — underlying syntax format.

- **Service name** — exact KooCLI Service name beginning with uppercase/title case (e.g. `OBS`, `ECS`)
- **Operation name** — PascalCase (e.g. `GetBucketEncryption`, `ListServers`)
- **obsutil passthrough mode** — `hcloud obs <subcommand> obs://{bucket} [-method=get]` maps 1:1 to obsutil; region is embedded in the endpoint, not `--cli-region`

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{bucket}` | Yes | Target bucket name | `my-bucket` |
| `{limit}` | No | Max objects to scan for naming pattern (default 1000) | `1000` |
| `{region}` | No | Huawei Cloud region (for endpoint construction) | `cn-north-4` |
| `--endpoint` | No | Full OBS endpoint | `obs.cn-north-4.myhuaweicloud.com` |
| `--format` | No | Report format (text/json) | `json` |

> **Quality telemetry**: every run reports automatically through `skill-quality-cli` (see the **Dependency** note in [Overview](#overview) and the `skill-quality-cli` section of `references/cli-installation-guide.md`). Opt out with `SKILL_QUALITY_REPORT=0`.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|----------|
| U | User input | U01 missing bucket param, U03 bucket not found |
| C | Config | C01 missing AK/SK / obsutil not configured |
| N | Network | N01 timeout, N02 connection failed |
| B | Code bug | B01 exception in auditor |
| P | Platform | P01 scheduler error |

## Authentication

### Mode 1: env-based (recommended for scripts)

```bash
export HUAWEICLOUD_SDK_AK={ak}
export HUAWEICLOUD_SDK_SK={sk}
# obsutil picks these up from its own config; configure once interactively
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs config
```

> **Security rule:** never type or paste AK/SK into the chat, and **never pass AK/SK as plaintext CLI args**. Configure credentials out-of-band (interactive `hcloud obs config` / env vars / shell profile), then re-run.

### Mode 2: obsutil config file (interactive)

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs config -e=obs.{region}.myhuaweicloud.com
# or
obsutil config
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls -limit=1   # verify connectivity
```

## Reference Documents

- `references/cli-installation-guide.md` — hcloud CLI + obsutil install & credential configuration
- `references/iam-policies.md` — Least-privilege IAM policy JSON for security audit (read-only)
- `references/security-check-catalog.md` — Detailed catalog of all 10 security audit items
- `references/related-commands.md` — Command quick reference and official API mapping
- `references/verification-method.md` — Verification steps and acceptance test cases
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria checklist
