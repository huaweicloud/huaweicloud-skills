---
id: huawei-cloud-eip-cost-optimizer
name: huawei-cloud-eip-cost-optimizer
tags: [huawei-cloud, eip, cost-optimization, idle-analysis, audit, monitoring]
description: |
  Huawei Cloud EIP (Elastic IP) cost optimization skill using hcloud CLI (KooCLI).
  1. List and query EIPs across regions with detailed status
  2. Identify idle/unbound EIPs and generate cost optimization reports
  3. Set up idle EIP monitoring with webhook/email alerts
  4. Generate HTML/JSON cost analysis reports
  5. Maintain operation audit logs for compliance
  **Read-only analysis only - NO bandwidth adjustment, tag management, or EIP release/deletion**.
  Triggers include: "EIP cost optimization", "idle EIP analysis", "EIP audit", "cost report", "EIP status query", "EIP list", "EIP monitoring", "EIP alert", "cost analysis", "idle monitoring", "operation audit", "EIP 成本优化", "闲置 EIP 分析", "EIP 审计", "成本报告", "EIP 状态查询", "EIP 查询", "EIP 列表", "EIP 监控", "EIP 告警", "成本分析", "闲置监控", "操作审计"
---

# Huawei Cloud EIP Cost Optimizer

## Overview

This skill provides batch management and cost optimization capabilities for Huawei Cloud Elastic Public IPs (EIPs).

**Architecture**: Shell + hcloud CLI (KooCLI) → EIP Service API → VPC/Bandwidth resources

**Related Skills**: For broader cost optimization across all resource types (ECS, EVS, OBS, etc.), see the archived `huaweicloud-cost-optimizer` skill. This skill focuses exclusively on EIP optimization with deeper functionality and 100% hcloud CLI compliance.

- Periodic cleanup of idle EIPs to reduce holding costs
- Cost analysis and optimization recommendations
- Multi-region unified management
- Automated monitoring and alerting for idle resources
- Operation audit logging for compliance

**Typical Use Cases**:

- "Help me identify idle EIPs and generate an optimization report"
- "Generate an EIP cost analysis report to identify high-cost resources"
- "Set up idle EIP monitoring with automatic alerts via webhook or email"
- "View EIP distribution and status summary across all regions"
- "Show audit logs for EIP operations in the last 30 days"
- "List all EIPs in cn-north-4 with detailed information"

## Prerequisites

### 1. CLI Environment Requirements (MANDATORY)

- **hcloud CLI (KooCLI)** v7.0+ — Huawei Cloud command-line tool
- **jq** — JSON processor for parsing API responses
- **bc** — Arbitrary precision calculator for cost estimation
- **curl** — HTTP client for webhook notifications

**Install hcloud CLI**:

```bash
# Linux/macOS one-click install
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh | bash

# Verify installation
hcloud --version
```

**Install jq, bc, curl**:

```bash
# Ubuntu/Debian
sudo apt install -y jq bc curl

# CentOS/RHEL
sudo yum install -y jq bc curl

# macOS
brew install jq bc curl
```

**Available Shell Scripts**:

- `scripts/config.sh` - Shared configuration (credentials, regions, proxy)
- `scripts/list_eips.sh` - List all EIPs in a region (supports filtering and summary)
- `scripts/analyze_idle_eips.sh` - Analyze idle EIPs and generate optimization reports (read-only)
- `scripts/eip_cost_report.sh` - Generate EIP cost analysis reports (text/HTML/JSON)
- `scripts/monitor_idle_eips.sh` - Monitor idle EIPs with webhook/email alerts and cron support
- `scripts/check_env.sh` - Environment check and validation (hcloud CLI + tools + API)
- `scripts/eip_audit_log.sh` - Operation audit logging (JSONL + CSV/JSON export)

**Note**: All scripts are READ-ONLY. This skill does NOT perform bandwidth adjustment, tag management, or EIP release/deletion.

### 2. Authentication Configuration

This skill supports **one authentication path** via environment variables:

#### Environment Variables

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_REGION_NAME=cn-north-4
```

> **Note**: If you have already configured `hcloud configure` interactively (entering credentials via prompts, not command-line arguments), the skill will also detect and use those credentials.

**Environment Variables**:

| Variable | Required | Description |
|----------|----------|-------------|
| `HW_ACCESS_KEY` | Optional | Huawei Cloud Access Key ID (required only if hcloud configure not set) |
| `HW_SECRET_KEY` | Optional | Huawei Cloud Secret Access Key (required only if hcloud configure not set) |
| `HW_REGION_NAME` | Optional | Default region (default: `cn-north-4`) |
| `HW_SECURITY_TOKEN` | Optional | Security token for temporary credentials |

**Security Notes**:

- Never commit credentials to version control
- Never expose AK/SK values in code, conversation, or commands
- Never pass AK/SK values as command-line arguments (exposes credentials in shell history and `ps aux`)
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly
- Use `./scripts/check_env.sh` to validate credentials before running scripts

### 3. Quick Start

```bash
# Step 1: Configure authentication via environment variables
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_REGION_NAME=cn-north-4

# Step 2: Run environment check
bash scripts/check_env.sh

# Step 3: Run scripts
bash scripts/list_eips.sh --region cn-north-4
bash scripts/analyze_idle_eips.sh --idle-days 7
bash scripts/eip_cost_report.sh --format html
```

### 4. IAM Permission Requirements

**Note**: This skill is READ-ONLY for EIP resources. It does NOT perform any write operations.

| API Action                    | Permission        | Purpose                          |
| ----------------------------- | ----------------- | -------------------------------- |
| `vpc:publicIps:list`          | List EIPs         | Query all EIPs and their status  |
| `vpc:publicIps:get`           | Get EIP details   | View individual EIP information  |

## Workflow

### Main Steps
1. **Environment Check** → Verify hcloud CLI, jq, credentials
2. **EIP Query** → List EIPs across regions via hcloud CLI
3. **Idle Analysis** → Identify unbound EIPs exceeding idle threshold
4. **Cost Report** → Generate HTML/JSON cost analysis report
5. **Monitoring Setup** → Configure idle EIP alerts (webhook/email)
6. **Audit Logging** → Record operations for compliance

### EIP Query Workflow
List EIPs across regions, filter by status, output as JSON/table.

### Idle EIP Analysis Workflow
Detect unbound EIPs idle beyond threshold, calculate holding costs, generate optimization report.

### Cost Report Workflow
Aggregate EIP cost data, render as HTML or JSON report with savings recommendations.

### Idle EIP Monitoring Workflow
Periodically check for idle EIPs, send alerts via webhook or email when detected.

### Audit Log Workflow
Record all EIP operations (list/analyze/report/monitor) to audit log file for compliance.

All EIP operations use hcloud CLI commands:

| Python SDK Method | hcloud CLI Command | Description |
|-------------------|-------------------|-------------|
| `EipClient.list_publicips()` | `hcloud EIP ListPublicips/v2 --cli-region=<region>` | List all EIPs |
| `EipClient.show_publicip()` | `hcloud EIP ShowPublicip/v2 --publicip_id=<id>` | Get EIP details |
| `IamClient.keystone_list_projects()` | `hcloud IAM KeystoneListProjects` | List projects |

**Output format**: All commands use `--cli-output=json` for machine-readable output, parsed by `jq`.

## Core Commands

| Command | Description | Backend |
|---------|-------------|---------|
| `list_eips.sh` | List and query EIPs across regions | hcloud CLI |
| `analyze_idle_eips.sh` | Identify idle/unbound EIPs with cost analysis | hcloud CLI |
| `eip_cost_report.sh` | Generate HTML/JSON cost analysis reports | hcloud CLI |
| `monitor_idle_eips.sh` | Set up idle EIP monitoring with alerts | hcloud CLI |
| `eip_audit_log.sh` | Maintain operation audit logs | Shell |
| `check_env.sh` | Verify environment prerequisites | Shell |
| `config.sh` | Load configuration and credentials | Shell |

### EIP Query

```bash
# List all EIPs in a region
bash scripts/list_eips.sh --region cn-north-4

# List EIPs with status filter
bash scripts/list_eips.sh --region cn-north-4 --status DOWN

# List EIPs across multiple regions
bash scripts/list_eips.sh --region cn-north-4,cn-east-3,cn-south-1
```

### Idle EIP Analysis

```bash
# Analyze idle EIPs (default threshold: 0 days = all unbound)
bash scripts/analyze_idle_eips.sh

# Custom idle threshold (14 days)
bash scripts/analyze_idle_eips.sh --idle-days 14

# Analyze specific region with JSON output
bash scripts/analyze_idle_eips.sh --region cn-north-4 --idle-days 7 --json
```

### Cost Report

```bash
# Generate text cost report (default)
bash scripts/eip_cost_report.sh

# Generate HTML report
bash scripts/eip_cost_report.sh --format html

# Generate JSON report
bash scripts/eip_cost_report.sh --format json

# Custom region
bash scripts/eip_cost_report.sh --region cn-east-3 --format html
```

**Cost Model**: Bandwidth-based pricing (~3 CNY/Mbps/month for cn-north-4 on-demand) + IP retain fee (~0.02 CNY/hour for unbound EIPs). API does not return `charge_mode`, so all estimates use bandwidth billing model.

### Idle EIP Monitoring

```bash
# Monitor idle EIPs (default threshold: 7 days)
bash scripts/monitor_idle_eips.sh

# Custom threshold
bash scripts/monitor_idle_eips.sh --idle-days 14

# Monitor with webhook alert
bash scripts/monitor_idle_eips.sh --idle-days 7 --webhook https://hooks.example.com/alert

# Monitor with email alert
bash scripts/monitor_idle_eips.sh --idle-days 7 --email admin@example.com

# Set up daily cron job (9:00 AM)
bash scripts/monitor_idle_eips.sh --setup-cron

# Remove cron job
bash scripts/monitor_idle_eips.sh --remove-cron
```

### Environment Check

```bash
# Full environment validation (CLI + tools + API)
bash scripts/check_env.sh

# Verbose mode (show versions)
bash scripts/check_env.sh --verbose

# Auto-fix missing dependencies
bash scripts/check_env.sh --fix
```

### Operation Audit Logging

```bash
# Log an EIP list operation
bash scripts/eip_audit_log.sh --action list --detail "Queried all EIPs"

# Log an analyze operation
bash scripts/eip_audit_log.sh --action analyze --detail "Idle EIP analysis for cn-north-4"

# Export audit logs to CSV
bash scripts/eip_audit_log.sh --action list --export csv

# Export audit logs to JSON
bash scripts/eip_audit_log.sh --action list --export json

# Custom log directory
bash scripts/eip_audit_log.sh --action list --log-dir /var/log/eip_audit
```

**Audit Log Entry Format** (JSONL, timezone-aware timestamps):

```json
{
  "timestamp": "2026-07-16T10:30:00+08:00",
  "region": "cn-north-4",
  "action": "list",
  "detail": "Queried all EIPs",
  "user": "root"
}
```


## KooCLI Command Format

```bash
# General format
hcloud <Service> <Operation> --cli-region=<region> --param1=value1 --param2=value2

# EIP list example
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4

# EIP show detail
hcloud EIP ShowPublicip/v2 --cli-region=cn-north-4 --publicip_id=<id>
```

| Feature | Description | Example |
|---------|-------------|---------||
| Service name | Uppercase PascalCase | `EIP`, `VPC`, `IAM` |
| Operation name | PascalCase with version | `ListPublicips/v2`, `ShowPublicip/v2` |
| Region param | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple param | `--key=value` | `--publicip_id=xxx` |
| Output format | `--cli-output=json` | JSON output for programmatic parsing |
## Parameters

### Shell Script Parameters

| Script | Parameter | Required/Optional | Description | Default |
|--------|-----------|-------------------|-------------|---------|
| `list_eips.sh` | `--region` | Optional | Region(s), comma-separated | `HW_REGION_NAME` or `cn-north-4` |
| `list_eips.sh` | `--status` | Optional | Filter by status (ACTIVE/DOWN/ERROR) | All |
| `analyze_idle_eips.sh` | `--region` | Optional | Target region | `HW_REGION_NAME` or `cn-north-4` |
| `analyze_idle_eips.sh` | `--idle-days` | Optional | Idle threshold in days | `0` (all unbound) |
| `analyze_idle_eips.sh` | `--json` | Optional | Output JSON format report | `false` |
| `eip_cost_report.sh` | `--region` | Optional | Target region | `HW_REGION_NAME` or `cn-north-4` |
| `eip_cost_report.sh` | `--format` | Optional | Output format: text/html/json | `text` |
| `monitor_idle_eips.sh` | `--region` | Optional | Target region | `HW_REGION_NAME` or `cn-north-4` |
| `monitor_idle_eips.sh` | `--idle-days` | Optional | Idle threshold in days | `7` |
| `monitor_idle_eips.sh` | `--webhook` | Optional | Webhook alert URL | - |
| `monitor_idle_eips.sh` | `--email` | Optional | Alert email address | - |
| `monitor_idle_eips.sh` | `--setup-cron` | Optional | Set up cron monitoring | - |
| `monitor_idle_eips.sh` | `--remove-cron` | Optional | Remove cron monitoring | - |
| `check_env.sh` | `--verbose` | Optional | Show detailed check info | `false` |
| `check_env.sh` | `--fix` | Optional | Auto-fix missing dependencies | `false` |
| `eip_audit_log.sh` | `--action` | Required | Operation type (list/query/analyze/monitor/report) | - |
| `eip_audit_log.sh` | `--detail` | Optional | Operation detail description | - |
| `eip_audit_log.sh` | `--export` | Optional | Export format: csv/json | - |
| `eip_audit_log.sh` | `--log-dir` | Optional | Log directory path | `./eip_audit_logs` |

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `HW_ACCESS_KEY` | Optional* | Huawei Cloud AK (required only if hcloud configure not set) | - |
| `HW_SECRET_KEY` | Optional* | Huawei Cloud SK (required only if hcloud configure not set) | - |
| `HW_REGION_NAME` | Optional | Default region | `cn-north-4` |
| `HW_SECURITY_TOKEN` | Optional | Temporary credential token | - |

*\*When `hcloud configure` is already set up, `HW_ACCESS_KEY` and `HW_SECRET_KEY` are not needed. Environment variables take precedence when both are configured.*

## Output Format

### EIP List Output

```text
========================================
Huawei Cloud EIP List (Region: cn-north-4)
========================================
EIP ID: eip-xxx1, IP: 123.45.67.89, BW: 5 Mbps, Status: BOUND (ECS: ecs-xxx)
EIP ID: eip-xxx2, IP: 98.76.54.32, BW: 10 Mbps, Status: UNBOUND ⚠️
========================================
Total: 2 EIPs, Idle: 1
```

### Cost Report Output

Generated by `scripts/eip_cost_report.sh` — includes:
- Summary statistics (total EIPs, idle, active, total bandwidth, costs)
- Per-EIP detail table with cost estimates
- Available in text, HTML, and JSON formats

**Pricing Model**: Bandwidth-based (~3 CNY/Mbps/month + 0.02 CNY/hr IP retain fee for unbound EIPs)

## Verification

### Environment Compliance Check

```bash
# Run full environment check (CLI + tools + API)
bash scripts/check_env.sh

# Exit codes:
#   0 - All checks passed
#   1 - Missing dependencies or API errors
```

## Best Practices

1. **Use Shell Scripts EXCLUSIVELY**: All scripts are Shell + hcloud CLI. No Python SDK dependency.
2. **Regular Monitoring**: Set up daily cron jobs with `monitor_idle_eips.sh --setup-cron` to catch idle EIPs early
3. **Cost Reports**: Generate weekly cost reports with `eip_cost_report.sh --format html` to track optimization progress
4. **Audit Logging**: Enable audit logging for all EIP operations using `eip_audit_log.sh`
5. **Multi-Region Management**: Use comma-separated regions `--region cn-north-4,cn-east-3` for cross-region analysis
6. **Webhook Alerts**: Configure webhooks for real-time idle EIP notifications
7. **Environment Validation**: Always run `check_env.sh` first to verify hcloud CLI and dependencies
8. **Idle Days Consistency**: Both `analyze_idle_eips.sh` and `monitor_idle_eips.sh` use `--idle-days` parameter with consistent timezone handling

## References

| Document | Description |
|----------|-------------|
| [IAM Permission Policies](references/iam-policies.md) | Required permissions and policy JSON |
| [EIP API Guide](references/eip-api-guide.md) | EIP API reference (hcloud CLI) |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud CLI install, configure, troubleshoot |
| [Verification Method](references/verification-method.md) | Step-by-step verification |
| [Acceptance Criteria](references/acceptance-criteria.md) | Production readiness acceptance tests |

## Notes

- **Cost estimates are for reference only** — based on cn-north-4 on-demand pricing (bandwidth model: ~3 CNY/Mbps/month + 0.02 CNY/hr IP retain fee). Actual costs may vary by region and billing mode.
- **API does not return charge_mode** — scripts cannot distinguish bandwidth vs traffic billing; all estimates use bandwidth model.
- **This skill is READ-ONLY** — it analyzes and reports idle EIPs but does NOT release or delete any resources. Manual action in the console is required to release EIPs.
- **EIP release is irreversible** — if you choose to release idle EIPs based on the analysis report, the public IP address will be reclaimed and cannot be recovered.
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`) or `hcloud configure` interactive mode (entering via prompts, not command-line arguments).
- **hcloud CLI is the only supported method** — all scripts use hcloud CLI (KooCLI) natively.
- **Authentication**: Use environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`) as the primary method. If `hcloud configure` is already set up interactively, the skill will detect and use those credentials. Never pass credentials as command-line arguments.
- **Temporary Credentials Supported**: This skill supports temporary AK/SK+Token obtained via IAM STS. Set `HW_SECURITY_TOKEN` when using temporary credentials.
- **Environment Variable Standard**: Uses `HW_*` prefix for consistency with other Huawei Cloud skills.
- **jq is required** for all scripts that parse hcloud CLI JSON output.
- **Idle days calculation is timezone-consistent** — both analyze and monitor scripts use `date` command for epoch calculation, eliminating UTC offset issues.
- **Audit log timestamps are timezone-aware** — format `YYYY-MM-DDTHH:MM:SS+HH:MM` (e.g., `+08:00`), not misleading `Z` suffix.

## Common Pitfalls

| Pitfall | Symptom | Quick Fix |
|---------|---------|-----------|
| hcloud not installed | `command not found: hcloud` | Install KooCLI |
| jq not installed | JSON parse errors | `sudo apt install jq` |
| bc not installed | Cost calculation errors | `sudo apt install bc` |
| AK/SK not set | API 401 / credential error | Export `HW_ACCESS_KEY`/`HW_SECRET_KEY` or configure `hcloud` interactively |
| Wrong region | `❌ API 返回异常` | Use valid region ID (e.g., `cn-north-4`) |
| Invalid format | `❌ 不支持的格式` | Use text/html/json for `--format` |
| API rate limit | `429 Too Many Requests` | Add delay between calls |
