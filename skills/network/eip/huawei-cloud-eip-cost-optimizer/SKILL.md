---
id: huawei-cloud-eip-cost-optimizer
name: huawei-cloud-eip-cost-optimizer
description: |
  Huawei Cloud EIP (Elastic IP) cost optimization skill using Python SDK v2.
  Use this skill when the user wants to: (1) list and query EIPs across regions with detailed status, (2) identify idle/unbound EIPs and generate cost optimization reports, (3) set up idle EIP monitoring with webhook/email alerts, (4) generate HTML/JSON cost analysis reports, (5) maintain operation audit logs for compliance. **Read-only analysis only - NO bandwidth adjustment, tag management, or EIP release/deletion**.
  Trigger: user mentions "EIP cost optimization", "idle EIP analysis", "EIP audit", "cost report", "EIP status query", "EIP list", "EIP monitoring", "EIP alert", "cost analysis", "idle monitoring", "operation audit", "EIP 成本优化", "闲置 EIP 分析", "EIP 审计", "成本报告", "EIP 状态查询", "EIP 查询", "EIP 列表", "EIP 监控", "EIP 告警", "成本分析", "闲置监控", "操作审计"
---

# Huawei Cloud EIP Cost Optimizer

## Overview

This skill provides batch management and cost optimization capabilities for Huawei Cloud Elastic Public IPs (EIPs).

**Architecture**: Python SDK v2 → EIP Service API → VPC/Bandwidth/Tag resources

**Related Skills**: For broader cost optimization across all resource types (ECS, EVS, OBS, etc.), see the archived `huaweicloud-cost-optimizer` skill. This skill focuses exclusively on EIP optimization with deeper functionality and 100% Python SDK compliance.

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

### 1. Python Environment Requirements (MANDATORY)

- Python 3.8+
- Install SDKs: `pip install huaweicloudsdkeip huaweicloudsdkcore`
- **All scripts use Python SDK v2 exclusively**

**Available Python Scripts**:

- `scripts/analyze_idle_eips.py` - Analyze idle EIPs and generate optimization reports (read-only, no release capability)
- `scripts/monitor_idle_eips.py` - Monitor idle EIPs with webhook/email alerts and cron support
- `scripts/eip_cost_report.py` - Generate EIP cost analysis reports (HTML/JSON formats)
- `scripts/list_eips.py` - List all EIPs in a region (supports filtering and multi-region summary)

**Available Shell Wrappers**:

- `scripts/eip_audit_log.sh` - Operation audit logging (standalone, no SDK dependency)

**Note**: All scripts are READ-ONLY. This skill does NOT perform bandwidth adjustment, tag management, or EIP release/deletion.

- Valid Huawei Cloud credentials (AK/SK mode)
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**Configuration Method** (Environment Variables Only):

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 2. IAM Permission Requirements

**Note**: This skill is READ-ONLY for EIP resources. It does NOT perform any write operations (update, delete, tag management).

| API Action                    | Permission        | Purpose                          |
| ----------------------------- | ----------------- | -------------------------------- |
| `vpc:publicIps:list`          | List EIPs         | Query all EIPs and their status  |
| `vpc:publicIps:get`           | Get EIP details   | View individual EIP information  |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Python SDK API Format Standard

All EIP operations use the Python SDK v2 format:

### EIP Service API (v2 SDK)

```python
from huaweicloudsdkeip.v2 import EipClient, ListPublicipsRequest, ShowPublicipRequest
from huaweicloudsdkeip.v2.region.eip_region import EipRegion
from huaweicloudsdkcore.auth.credentials import BasicCredentials

# Initialize client
credentials = BasicCredentials(ak, sk)
client = EipClient(credentials, EipRegion.value_of(region))

# List all EIPs
request = ListPublicipsRequest()
request.limit = 100
response = client.list_publicips(request)

# Show EIP details
request = ShowPublicipRequest()
request.publicip_id = "<eip-id>"
response = client.show_publicip(request)
```

### Tag Management API

```python
from huaweicloudsdkeip.v2 import UpdatePublicipRequest, UpdatePublicipOption, UpdatePublicipRequestBody
from huaweicloudsdkeip.v2.model.tag import Tag

# Add tags to EIP
option = UpdatePublicipOption()
option.tags = [Tag(key="env", value="prod")]
body = UpdatePublicipRequestBody()
body.publicip = option

request = UpdatePublicipRequest()
request.publicip_id = "<eip-id>"
request.body = body

client.update_publicip(request)
```

### Special Rules

| Rule             | Description                      | Example                            |
| ---------------- | -------------------------------- | ---------------------------------- |
| v2 SDK           | EIP operations use v2 SDK        | `huaweicloudsdkeip.v2`             |
| Region parameter | Use `EipRegion.value_of(region)` | `EipRegion.value_of('cn-north-4')` |
| Credentials      | Use `BasicCredentials(ak, sk)`   | Environment variables preferred    |

## Core Commands

### EIP Query

**Python SDK Method** (Recommended):

```bash
# List all EIPs with bandwidth info
python3 scripts/adjust_eip_bandwidth.py --list

# Analyze idle EIPs and generate report (read-only)
python3 scripts/analyze_idle_eips.py

# Adjust bandwidth for all EIPs
python3 scripts/adjust_eip_bandwidth.py --all --bandwidth 5

# Adjust bandwidth for idle EIPs only
python3 scripts/adjust_eip_bandwidth.py --idle-only --bandwidth 1
```

### 2. jq Dependency (Shell Wrappers Only)

**Required for**: `eip_audit_log.sh`

```bash
# Verify jq installation
jq --version  # Should return "jq-1.x"

# If jq fails or shows "Not Found", diagnose:
which jq
cat $(which jq)  # If this shows text instead of binary, jq is broken

# Fix broken jq (common in WSL):
sudo rm /usr/local/bin/jq  # Remove invalid PATH-prioritized jq
which jq  # Should now show /usr/bin/jq
```

**Note**: jq is only required for Shell wrapper scripts. All Python SDK scripts work without jq.

**Python SDK Method** (Recommended for batch operations):

```bash
# Adjust all EIPs to 5 Mbps
python3 scripts/adjust_eip_bandwidth.py --all --bandwidth 5

# Adjust idle EIPs to 1 Mbps
python3 scripts/adjust_eip_bandwidth.py --idle-only --bandwidth 1

# Adjust specific EIPs
python3 scripts/adjust_eip_bandwidth.py --eip-ids "eip-id1,eip-id2" --bandwidth 10

# View current bandwidth configuration
python3 scripts/adjust_eip_bandwidth.py --list
```

### Tag Management

**Python SDK Method**:

```bash
# Add tags to EIP
python3 scripts/manage_tags.py --action add --tags "env=prod,team=backend" --eip-ids <ID1,ID2>

# Remove tags from EIP
python3 scripts/manage_tags.py --action remove --tags "env" --eip-ids <ID1,ID2>

# List tags for EIP
python3 scripts/list_eips.py --region cn-north-4  # Shows tags in output
```

### Multi-Region Management

**Using Python Scripts** (Recommended):

```bash
# List EIPs in multiple regions (manually specify regions)
python3 scripts/list_eips.py --region cn-north-4
python3 scripts/list_eips.py --region cn-east-3
python3 scripts/list_eips.py --region cn-south-1

# Generate summary report for automation
python3 scripts/list_eips.py --region cn-north-4 --summary
# Output: CSV format (count,idle,bandwidth)
```

**Note**: The `multi_region_manage.sh` wrapper was removed in v3.0.3. Users can achieve the same functionality by running `list_eips.py` for each region individually, or by scripting multiple calls in their own automation.

### Operation Audit Logging

**Using Audit Script**:

```bash
# Log an EIP release operation
bash scripts/eip_audit_log.sh --action release --eip-id eip-xxx --operator admin

# Log a bandwidth adjustment
bash scripts/eip_audit_log.sh --action update_bandwidth --eip-id eip-xxx --details '{"old": 5, "new": 10}'

# Query audit logs for last 30 days
bash scripts/eip_audit_log.sh --query --days 30

# Export audit logs to CSV
bash scripts/eip_audit_log.sh --export --format csv

# Export to HTML report
bash scripts/eip_audit_log.sh --export --format html
```

**Audit Log Entry Format** (JSONL):

```json
{
  "timestamp": "2026-05-25T03:30:00Z",
  "operation": "release",
  "eip_id": "eip-xxx",
  "operator": "admin",
  "region": "cn-north-4",
  "details": {"reason": "idle_cleanup", "cost_saved": "2.5"}
}
```

## Parameter Confirmation

### Python Script Parameters

| Parameter       | Required/Optional         | Description                             | Default                               |
| --------------- | ------------------------- | --------------------------------------- | ------------------------------------- |
| `--region`      | Optional (Python scripts) | Huawei Cloud region ID                  | `HUAWEI_CLOUD_REGION` or `cn-north-4` |
| `--eip-ids`     | Optional (scripts)        | Comma-separated EIP IDs                 | All EIPs                              |
| `--bandwidth`   | Required (adjust script)  | Target bandwidth in Mbps                | N/A                                   |
| `--all`         | Optional                  | Apply to all EIPs                       | `false`                               |
| `--idle-only`   | Optional                  | Apply to idle EIPs only                 | `false`                               |
| `--list`        | Optional                  | List EIPs with bandwidth info           | `false`                               |
| `--summary`     | Optional (`list_eips.py`) | Output CSV stats (count,idle,bandwidth) | `false`                               |
| `--idle-days`   | Optional (scripts)        | Idle threshold in days                  | `7`                                   |
| `--interactive` | Optional (scripts)        | Interactive confirmation mode           | `false`                               |
| `--confirm`     | Optional (release script) | Confirm release operation               | `false`                               |

### Shell Wrapper Parameters

| Script             | Parameter               | Description                             |
| ------------------ | ----------------------- | --------------------------------------- |
| `eip_audit_log.sh` | `--action ACTION`       | Log operation (release, create, update) |
| `eip_audit_log.sh` | `--eip-id ID`           | EIP ID for audit log                    |
| `eip_audit_log.sh` | `--query`               | Query audit logs                        |
| `eip_audit_log.sh` | `--export --format csv` | Export audit logs                       |

## Output Format

### EIP List Output (JSON)

```json
{
  "publicips": [
    {
      "id": "eip-xxx1",
      "public_ip_address": "123.45.67.89",
      "bandwidth": { "size": 5 },
      "status": "ACTIVE",
      "binding_status": "BOUND",
      "associate_instance_type": "ECS",
      "create_time": "2026-04-15T10:30:00Z"
    }
  ]
}
```

### Script Output (Formatted Text)

```text
========================================
Huawei Cloud EIP List (Region: cn-north-4)
========================================
EIP ID: eip-xxx1, IP: 123.45.67.89, BW: 5 Mbps, Status: BOUND (ECS: ecs-xxx)
EIP ID: eip-xxx2, IP: 98.76.54.32, BW: 10 Mbps, Status: UNBOUND ⚠️
========================================
Total: 2 EIPs, Idle: 1
```

### Cost Report Output (HTML)

Generated by `scripts/eip_cost_report.py` — includes statistics cards, idle EIP table, full EIP list, and optimization recommendations.

## Verification

See [Verification Method](references/verification-method.md)

### Compliance Check Script

Before any skill update or release, run the automated compliance check:

```bash
# Run compliance check
python3 scripts/compliance_check.py

# Verbose mode (show all findings)
python3 scripts/compliance_check.py --verbose
```

**Checks performed**:

1. All required Python SDK scripts exist
2. No hardcoded credentials (AK/SK)
3. No hardcoded local paths
4. SKILL.md metadata correctness

**Exit codes**:

- `0` - All checks passed, skill is compliant
- `1` - Compliance issues found, must fix before release

## Best Practices

1. **Use Python SDK Scripts EXCLUSIVELY**: Always use `scripts/adjust_eip_bandwidth.py`, `scripts/analyze_idle_eips.py`, and `scripts/monitor_idle_eips.py`
2. **Regular Monitoring**: Set up daily cron jobs with `monitor_idle_eips.py --setup-cron` to catch idle EIPs early
3. **Tag Governance**: Use consistent tags (env, team, project) for all EIPs
4. **Bandwidth Policy**: Set minimum bandwidth (1 Mbps) for idle EIPs to reduce costs before release
5. **Interactive Mode**: Always use `--interactive` flag for release operations in production
6. **Audit Logging**: Enable audit logging for all EIP operations using `scripts/eip_audit_log.sh --action <operation> --eip-id <id>`
7. **Multi-Region Management**: Run `list_eips.py` for each region individually, or use `--summary` flag for programmatic access to EIP statistics
8. **Bandwidth Policy**: Set minimum bandwidth (1 Mbps) for idle EIPs to reduce costs before release
9. **Summary Mode for Automation**: Use `list_eips.py --summary` for programmatic access to EIP statistics (returns CSV: count,idle,bandwidth)
10. **Documentation Synchronization**: When updating SKILL.md, ALWAYS update SKILL-CN.md simultaneously to maintain bilingual consistency. Both documents must have identical structure, parameters, and examples.
11. **Shell Wrapper Audit**: After any migration or script deletion, audit ALL Shell wrappers for broken dependencies using `grep -r "<deleted-script>.sh" scripts/`. Test each wrapper before marking compliance complete.
12. **jq Dependency Validation**: Before using audit log or multi-region scripts, verify jq is correctly installed: `jq --version` should return "jq-1.x". If it fails or shows "Not Found", check for broken PATH-prioritized installations at `/usr/local/bin/jq` and remove them.
13. **Use Case Coverage Audit**: Before any skill release, verify typical use cases cover 100% of scripts. Run: `grep -A 20 "Typical Use Cases" SKILL.md | grep -c "^- \""` - should be 9+ for full coverage. Missing use cases indicate undocumented functionality.

## Reference Documents

| Document                                                       | Description                                                                                                                 |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| [IAM Permission Policies](references/iam-policies.md)          | Required permissions and policy JSON                                                                                        |
| [EIP API Guide](references/eip-api-guide.md)                   | EIP API reference (Python SDK v2)                                                                                           |
| [Verification Method](references/verification-method.md)       | Step-by-step verification                                                                                                   |
| [Python SDK Usage Guide](references/python-sdk-usage-guide.md) | Python SDK patterns, common errors, and working examples. **See "Issue 4" for critical bandwidth adjustment API pitfalls.** |

## Notes

- **Cost estimates are for reference only** — based on cn-north-4 on-demand pricing (~¥2-4/Mbps/month). Actual costs may vary by region and billing mode.
- **This skill is READ-ONLY** — it analyzes and reports idle EIPs but does NOT release or delete any resources. Manual action in the console is required to release EIPs.
- **EIP release is irreversible** — if you choose to release idle EIPs based on the analysis report, the public IP address will be reclaimed and cannot be recovered. Always verify before releasing manually.
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables.
- **Python SDK is the only supported method** — all scripts use Python SDK v2 natively.
- **Bandwidth adjustment API**: Uses `BatchModifyBandwidth` API (NOT `UpdatePublicip` or `UpdateBandwidth`).

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall              | Symptom                  | Quick Fix                            |
| -------------------- | ------------------------ | ------------------------------------ |
| jq path issues       | `eip_audit_log.sh` fails | `sudo rm /usr/local/bin/jq`          |
| Wrong bandwidth API  | `VPC.0301` error         | Use `BatchModifyBandwidthRequest`    |
| Missing bandwidth_id | Empty bandwidth ID       | Access `eip.bandwidth_size` directly |
| v3 SDK import error  | No `EipRegion` attribute | Use v2 SDK                           |
| Timestamp parsing    | Unknown idle days        | Handle ISO format                    |

# 
