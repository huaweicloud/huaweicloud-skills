# IAM Authentication Guide

## Overview

The Huawei Cloud tenant risk inspection skill uses the `hcloud` CLI to call Huawei Cloud APIs
across three services — Optimization Advisor (OA), Config, and SecMaster.
Authentication is handled through IAM (Identity and Access Management) credentials
and is shared by all scripts in this project.

## Authentication Methods

### Method 1: AK/SK (Recommended)

Use Access Key ID and Secret Access Key — the most common approach for CLI and programmatic access.

**Configure via hcloud CLI:**

```bash
hcloud configure set \
  --cli-access-key=YOUR_AK \
  --cli-secret-key=YOUR_SK \
  --cli-region=cn-north-4
```

**Or via environment variables:**

```bash
export HWCloudAccessKeyID=YOUR_AK
export HWCloudSecretAccessKey=YOUR_SK
export HWCloudRegion=cn-north-4
```

### Method 2: Token-based

> **Conceptual note only.** For scenarios where AK/SK is not available, a temporary token can be obtained from IAM. Passing a password directly on the command line is a security anti-pattern (it can leak via the process list); this skill's scripts do **not** use this authentication path. The recommended approach is always AK/SK + environment variables (see Method 1 above).

## Auto-detecting the Account ID

The inspection scripts resolve the account ID (Domain ID) automatically from the currently authenticated tenant. No `--domain-id` parameter is needed for OA and SecMaster collection:

```bash
hcloud IAM KeystoneListAuthDomains --cli-region=cn-north-4
```

The response's `domains[0].id` is the account ID (Domain ID) of the authenticated tenant.
`config_compliance_inspection.py` invokes this API at startup in normal mode and writes the value into `meta.domain_id` of the output JSON; `merge_report_generator.py` invokes it to fill the username / account fields on the Excel overview page. In `--from-file` debug mode (no hcloud calls), `meta.domain_id` is left as an empty string.

## Scripts and Their Authentication

All five scripts run `hcloud` subprocesses and rely on the configured AK/SK profile:

| Script | Service | Auth usage |
|--------|---------|------------|
| `oa_risk_inspection.py` | OA | hcloud OA APIs; region fixed to the constant `cn-southwest-2` |
| `config_compliance_inspection.py` | Config | hcloud Config APIs; region fixed to the constant `cn-north-4`; resolves domain via `KeystoneListAuthDomains` |
| `secmaster_baseline_inspection.py` | SecMaster | hcloud SecMaster APIs; scans the built-in region list |
| `merge_inspection_results.py` | — (offline merge) | no hcloud calls; pure file conversion |
| `merge_report_generator.py` | IAM (report) | resolves username / account via `KeystoneListAuthDomains` for the Excel overview page |

## Required Permissions

The account must have the following permissions to query the three services:

| Permission | API | Purpose |
|------------|-----|---------|
| `oa:checkItem:list` | OA ShowCheckItemList | Retrieve all OA check items |
| `oa:checkResult:list` | OA ShowCheckItemResult | Retrieve risk resource details per check item |
| `config:complianceRules:list` | Config ListPolicyAssignments | Retrieve assigned compliance policies |
| `config:complianceResources:list` | Config ListResources | Retrieve resource-level compliance evaluation results |
| `secmaster:baseline:list` | SecMaster baseline APIs | Retrieve baseline check results |
| `iam:domains:list` | IAM KeystoneListAuthDomains | Resolve account name / Domain ID |

## Region Configuration

No collection script takes a region parameter; every region is decided inside the script:

```bash
python3 scripts/oa_risk_inspection.py
python3 scripts/config_compliance_inspection.py
python3 scripts/secmaster_baseline_inspection.py
```

- OA is fixed to `cn-southwest-2`, the only region where the OA service was verified available.
- Config is fixed to `cn-north-4`.
- SecMaster scans the region list built into `secmaster_baseline_inspection.py` and collects every instance it finds across those regions, so no instance is missed because the user did not know its region. The list is transcribed from the SecMaster console; a newly launched region is not covered until the list is updated. Each entry carries a verified flag: a region marked unverified (currently `cn-north-11` and `me-east-1`) is still scanned, but its failure is logged as a warning and excluded from the failure count that drives the exit code.

SecMaster calls are throttled to 2 per second by default (`--rate-limit`), because the gateway rejects bursts with a throttling error.

## Security Notes

- **Never** hardcode AK/SK in scripts or configuration files committed to version control.
- Use environment variables or the hcloud profile (stored locally with restricted permissions).
- Rotate AK/SK periodically following your organization's security policy.
- The skill scripts do not store or log credentials; all authentication is delegated to the `hcloud` CLI.
