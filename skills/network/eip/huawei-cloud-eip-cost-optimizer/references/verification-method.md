# Verification Method - EIP Management Skill

## Overview

This document defines the verification steps for the EIP management skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 Python SDK Installation

| Item | Command | Success Criteria |
|------|---------|-----------------|
| Python SDK installed | `Python SDK version` | Returns version number >= 7.2.2 |
| jq installed | `jq --version` | Returns version number (e.g., jq-1.6) |
| Python 3 installed | `python3 --version` | Returns version >= 3.6 |

### 1.2 Python SDK First Run

```bash
# Accept privacy statement (first time only)
printf "y\n" | Python SDK version
```

Expected: Version number displayed without error.

## Level 2: Configuration Verification

### 2.1 Credential Configuration

| Item | Command | Success Criteria |
|------|---------|-----------------|
| Credentials configured | `export HUAWEI_CLOUD_AK/SK list` | Shows valid AK/SK configuration (values masked) |
| Region configured | `export HUAWEI_CLOUD_AK/SK list` | Shows cli-region setting |

✅ **Correct**: Use `export HUAWEI_CLOUD_AK/SK list` to verify
❌ **Incorrect**: Do NOT use `echo $HUAWEICLOUD_SDK_AK` to check credentials

### 2.2 Connectivity Test

```bash
# Test API connectivity with a read-only operation
Python SDK EIP ListPublicips/v3 --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and EIP list (may be empty).

## Level 3: Functional Verification

### 3.1 List EIPs

```bash
bash scripts/list_eips.sh
```

Expected: Displays formatted EIP list with total and idle counts.

### 3.2 Find Idle EIPs

```bash
bash scripts/find_idle_eips.sh
```

Expected: Displays idle EIP report with cost estimates.

### 3.3 Cost Report Generation

```bash
python3 scripts/eip_cost_report.py --output /tmp/test-report.html
```

Expected: HTML report generated at `/tmp/test-report.html`.

### 3.4 Multi-Region Management

```bash
bash scripts/multi_region_manage.sh --regions "cn-north-4"
```

Expected: Displays EIP statistics for the specified region.

### 3.5 Audit Log (Query Mode)

```bash
bash scripts/eip_audit_log.sh --query --days 7
```

Expected: Displays audit log entries from the last 7 days (may be empty).

### 3.6 Tag Management (Read-Only)

```bash
# List tags on an EIP (replace with a real EIP ID)
Python SDK EIP ShowPublicipTags/v3 --publicip_id=<eip-id> --cli-region=cn-north-4
```

Expected: Returns tag information for the specified EIP.

## Verification Checklist

| # | Check Item | Command | Status |
|---|-----------|---------|--------|
| 1 | Python SDK version >= 7.2.2 | `Python SDK version` | ☐ |
| 2 | jq installed | `jq --version` | ☐ |
| 3 | Python 3.6+ installed | `python3 --version` | ☐ |
| 4 | Credentials configured | `export HUAWEI_CLOUD_AK/SK list` | ☐ |
| 5 | API connectivity | `Python SDK EIP ListPublicips/v3 --cli-region=cn-north-4` | ☐ |
| 6 | List EIPs script | `bash scripts/list_eips.sh` | ☐ |
| 7 | Find idle EIPs script | `bash scripts/find_idle_eips.sh` | ☐ |
| 8 | Cost report generation | `python3 scripts/eip_cost_report.py --output /tmp/test-report.html` | ☐ |
