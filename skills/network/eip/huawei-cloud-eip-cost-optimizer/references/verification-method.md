# Verification Method - EIP Cost Optimizer Skill

## Overview

This document defines the verification steps for the EIP Cost Optimizer skill. All scripts are Shell + hcloud CLI (KooCLI). Verification is divided into three levels: environment verification, configuration verification, and functional verification.

## Level 1: Environment Verification

### 1.1 CLI & Dependencies

| Item | Command | Success Criteria |
|------|---------|-----------------|
| hcloud CLI installed | `hcloud --version` | Returns version number >= 7.0 |
| jq installed | `jq --version` | Returns version number (e.g., jq-1.6) |
| bc installed | `bc --version` | Returns version number |
| curl installed | `curl --version` | Returns version number |

### 1.2 hcloud CLI First Run

```bash
# Accept privacy statement (first time only)
printf "y\n" | hcloud --version
```

Expected: Version number displayed without error.

### 1.3 Automated Environment Check

```bash
bash scripts/check_env.sh
```

Expected: All core checks PASS (8/8). Optional warnings for crontab/sendmail are acceptable.

## Level 2: Configuration Verification

### 2.1 Credential Configuration

| Item | Command | Success Criteria |
|------|---------|-----------------|
| Credentials configured | `env \| grep HW_` | Shows HW_ACCESS_KEY, HW_SECRET_KEY, HW_REGION_NAME |
| Region configured | `env \| grep HW_REGION_NAME` | Shows region setting (e.g., cn-north-4) |

✅ **Correct**: Use `env | grep HW_` to verify credentials are set
❌ **Incorrect**: Do NOT use `echo $HW_ACCESS_KEY` to check credentials (security risk)

### 2.2 Connectivity Test

```bash
# Test API connectivity with a read-only operation
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4
```

Expected: Returns JSON with `publicips` array (may be empty) without authentication errors.

## Level 3: Functional Verification

### 3.1 List EIPs

```bash
bash scripts/list_eips.sh --region cn-north-4
```

Expected: Displays formatted EIP list with total and idle counts.

### 3.2 Analyze Idle EIPs

```bash
bash scripts/analyze_idle_eips.sh --idle-days 0
```

Expected: Displays idle EIP analysis report with cost estimates.

### 3.3 Cost Report Generation

```bash
bash scripts/eip_cost_report.sh --format html
bash scripts/eip_cost_report.sh --format json
```

Expected: HTML/JSON report generated with cost breakdown.

### 3.4 Idle EIP Monitoring

```bash
bash scripts/monitor_idle_eips.sh --idle-days 7
```

Expected: Displays monitoring report. No idle EIPs above threshold = clean status.

### 3.5 Audit Log

```bash
bash scripts/eip_audit_log.sh --action query
bash scripts/eip_audit_log.sh --action query --export json
```

Expected: Displays audit log entries and exports JSON file.

## Verification Checklist

| # | Check Item | Command | Status |
|---|-----------|---------|--------|
| 1 | hcloud CLI >= 7.0 | `hcloud --version` | ☐ |
| 2 | jq installed | `jq --version` | ☐ |
| 3 | bc installed | `bc --version` | ☐ |
| 4 | Credentials configured | `env \| grep HW_ACCESS_KEY` | ☐ |
| 5 | API connectivity | `hcloud EIP ListPublicips/v2 --cli-region=cn-north-4` | ☐ |
| 6 | Environment check | `bash scripts/check_env.sh` | ☐ |
| 7 | List EIPs | `bash scripts/list_eips.sh` | ☐ |
| 8 | Analyze idle EIPs | `bash scripts/analyze_idle_eips.sh` | ☐ |
| 9 | Cost report (HTML) | `bash scripts/eip_cost_report.sh --format html` | ☐ |
| 10 | Cost report (JSON) | `bash scripts/eip_cost_report.sh --format json` | ☐ |
| 11 | Monitor idle EIPs | `bash scripts/monitor_idle_eips.sh --idle-days 7` | ☐ |
| 12 | Audit log query | `bash scripts/eip_audit_log.sh --action query` | ☐ |
