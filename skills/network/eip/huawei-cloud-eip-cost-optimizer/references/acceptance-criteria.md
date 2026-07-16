# Acceptance Criteria - EIP Cost Optimizer Skill

## Overview

This document defines the acceptance criteria for the EIP Cost Optimizer skill. All criteria must pass before the skill is considered ready for production use.

## AC-01: Environment Prerequisites

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | hcloud CLI installed | `hcloud --version` | Returns version >= 7.0.0 |
| 2 | jq installed | `jq --version` | Returns version |
| 3 | bc installed | `bc --version` | Returns version |
| 4 | curl installed | `curl --version` | Returns version |
| 5 | AK/SK configured | `env \| grep HW_ACCESS_KEY` | Variable is set (non-empty) |
| 6 | Region configured | `env \| grep HW_REGION_NAME` | Variable is set to valid region ID |

**Automated test**: `bash scripts/check_env.sh` — must show 8 PASS, 0 FAIL.

## AC-02: EIP List Functionality

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | List EIPs without error | `bash scripts/list_eips.sh --region cn-north-4` | Exit code 0, displays EIP table |
| 2 | Correct total count | Compare output count with `hcloud EIP ListPublicips/v2` | Counts match |
| 3 | Idle EIP identification | Output marks unbound EIPs as idle | Status correctly shows IDLE/ACTIVE |
| 4 | JSON output valid | `bash scripts/list_eips.sh --format json` | Valid JSON with `eips` array |

## AC-03: Idle EIP Analysis

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | Analysis runs without error | `bash scripts/analyze_idle_eips.sh --idle-days 0` | Exit code 0 |
| 2 | Idle days calculated | Output shows `idle_days_calculated` for each EIP | Non-negative integer or -1 (unknown) |
| 3 | Cost estimate displayed | Output shows monthly cost estimate | Positive number in CNY |
| 4 | JSON output valid | `bash scripts/analyze_idle_eips.sh --format json` | Valid JSON with `idle_eips` and `summary` |
| 5 | Threshold filtering | `--idle-days 30` only shows EIPs idle > 30 days | No EIP with idle_days < 30 in results |

## AC-04: Cost Report Generation

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | HTML report generated | `bash scripts/eip_cost_report.sh --format html` | Exit code 0, HTML file created |
| 2 | JSON report generated | `bash scripts/eip_cost_report.sh --format json` | Valid JSON with cost breakdown |
| 3 | Cost formula correct | Verify: `bandwidth_cost = bw × 3 CNY/Mbps/month` | Math matches |
| 4 | IP retain fee correct | Verify: `retain_fee = idle_count × 0.02 × 720` | Math matches |
| 5 | Empty region handling | `--region ""` | Returns valid empty JSON/HTML structure, no crash |

## AC-05: Idle EIP Monitoring

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | Monitoring runs without error | `bash scripts/monitor_idle_eips.sh --idle-days 7` | Exit code 0 |
| 2 | Alert triggered when idle | `--idle-days 0` (with idle EIPs) | Alert message displayed |
| 3 | No alert when no idle | `--idle-days 999` | Clean status, no alert |
| 4 | Webhook validation | `--webhook http://evil.com` | Rejected (non-HTTPS or unknown domain) |
| 5 | Crontab setup | `--setup-cron` | Crontab entry added with correct schedule |
| 6 | Crontab removal | `--remove-cron` | Crontab entry removed |

## AC-06: Audit Log

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | Audit record created | `bash scripts/eip_audit_log.sh --action list` | JSONL file appended with valid JSON |
| 2 | Query returns records | `--action query` | Displays audit entries |
| 3 | CSV export | `--export csv` | CSV file with correct headers |
| 4 | JSON export | `--export json` | Valid JSON array |
| 5 | Log directory permissions | Check `eip_audit_logs/` | Directory mode 700 |
| 6 | Path traversal protection | `--log-dir /etc` | Rejected with error message |
| 7 | Timestamp timezone | Check JSONL timestamp field | Ends with `+08:00` |

## AC-07: Security Requirements

| # | Criterion | Verification Method | Pass Condition |
|---|-----------|---------------------|----------------|
| 1 | No hardcoded credentials | `grep -r 'AK.*=' scripts/` | No AK/SK values in code |
| 2 | No credential echo | `grep -r 'echo.*\$HW_ACCESS_KEY' scripts/` | No credential value output |
| 3 | No curl\|bash | `grep -r 'curl.*\|.*bash' scripts/` | No pipe-to-shell patterns |
| 4 | Webhook URL whitelist | Code review of `send_webhook()` | Only known domains allowed |
| 5 | Lock file atomic | Code review of `acquire_lock()` | Uses `set -C` (noclobber) |
| 6 | Audit dir permissions | `stat -c %a eip_audit_logs/` | Mode 700 |
| 7 | Read-only operations | Review all `run_hcloud` calls | No create/update/delete API calls |

## AC-08: Error Handling

| # | Criterion | Test Scenario | Pass Condition |
|---|-----------|---------------|----------------|
| 1 | Invalid region | `--region invalid-region` | Graceful error, no crash |
| 2 | No EIPs in region | Region with 0 EIPs | Displays "0 EIPs", exit 0 |
| 3 | API timeout | Simulate network timeout | Error message, exit non-zero |
| 4 | Invalid credentials | Wrong AK/SK | "认证失败" message, exit 1 |
| 5 | Missing jq | `mv /usr/bin/jq /tmp; run; mv back` | Error message about missing jq |

## AC-09: Output Format Compliance

| # | Criterion | Test Command | Pass Condition |
|---|-----------|-------------|----------------|
| 1 | JSON is valid | Pipe JSON output through `jq .` | Exit code 0 |
| 2 | JSON uses snake_case | Check JSON keys | No camelCase keys |
| 3 | Timestamps ISO-like | Check timestamp fields | Format: `YYYY-MM-DD HH:MM:SS+08:00` |
| 4 | HTML well-formed | Validate HTML tags | Proper open/close tags |
| 5 | CSV has headers | Check first line of CSV export | Column names present |

## Passing Criteria

The skill passes acceptance testing when:

- **AC-01 through AC-06**: All individual criteria pass (functional correctness)
- **AC-07**: All security criteria pass (security compliance)
- **AC-08**: All error handling criteria pass (robustness)
- **AC-09**: All output format criteria pass (interface compliance)

**Minimum pass rate**: 100% for AC-07 (security), >= 90% for all other categories.
