---
name: huawei-cloud-rds-smart-service
description: |
  Huawei Cloud RDS (Relational Database Service) full-scenario intelligent service covering all database engines (MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB for MySQL, TaurusDB). Provides six capability domains: (1) Basic intelligent Q&A for RDS product features, best practices, and specifications; (2) SQL statement performance optimization with slow log analysis, top SQL, execution plan guidance, and index recommendations; (3) Database instance daily O&M including health inspection, restart, flavor resize, disk expansion, primary-standby switchover, and read replica management; (4) Online fault localization and troubleshooting via error logs, replication status, connection diagnostics, and recovery time window; (5) Parameter tuning with parameter group management, modification suggestions, and performance parameter adjustment guidance; (6) Backup and recovery guidance including backup policy management, manual backup creation, restore to new/existing instance, and point-in-time recovery. Uses CLI→SDK→API three-level fallback for maximum compatibility. All mutating operations require explicit user confirmation.
  Triggers include: "RDS","关系型数据库","数据库实例","慢SQL","SQL优化","数据库运维","数据库故障","故障排查","参数调优","备份恢复","数据库巡检","RDS诊断","数据库诊断","DBA","数据库性能","主从延迟","连接数","数据库备份","数据恢复","RDS智能服务","database instance","RDS troubleshooting","slow query","SQL performance","database backup","parameter tuning","RDS ops","database diagnose".
version: 1.0.0
tags: [huawei-cloud, rds, database, sql-optimization, backup-recovery]
---

# Huawei Cloud RDS Smart Service

> Full-scenario intelligent service for Huawei Cloud RDS — covering basic Q&A, SQL optimization, daily O&M, fault diagnosis, parameter tuning, and backup recovery across all database engines.

---

## Overview

This skill provides comprehensive intelligent services for Huawei Cloud Relational Database Service (RDS). It supports all database engines (MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB for MySQL, TaurusDB) and covers six major capability domains:

| Domain | Capabilities |
|--------|-------------|
| **Basic Q&A** | Product feature consultation, best practices, specification/version queries, instance listing |
| **SQL Optimization** | Slow log analysis, top SQL queries, execution plan guidance, index optimization suggestions, SQL limit control |
| **Daily O&M** | Health inspection, instance restart, flavor resize, disk expansion, primary-standby switchover, read replica management, auto-scaling policy |
| **Fault Diagnosis** | Error log analysis, replication status, connection diagnostics, recovery time window, instance diagnosis, intelligent session kill |
| **Parameter Tuning** | Parameter group CRUD, parameter apply, instance parameter modification, parameter change history |
| **Backup Recovery** | Backup policy management, manual backup creation/deletion, restore to new/existing instance, point-in-time recovery, backup usage summary |
| **Security** | Security group modification, SSL configuration, audit log management |

### Architecture

```
User Request → Skill Trigger Matching → Capability Domain Routing
  → CLI (hcloud RDS) → [fallback] → SDK (huaweicloudsdkrds.v3) → [fallback] → API (REST)
  → Result Formatting → Intelligent Analysis & Recommendations
```

### Applicable Scenarios

- **Daily inspection**: DBA checks instance health, resource usage, backup status
- **SQL optimization**: Developer/DBA analyzes slow SQL, gets optimization suggestions
- **Fault troubleshooting**: SRE/DBA diagnoses unreachable instances, high latency, connection exhaustion
- **Parameter tuning**: DBA adjusts database parameters for performance
- **Backup recovery**: DBA/Ops manages backup strategy, performs recovery drills
- **Basic Q&A**: Developer/Junior DBA asks about RDS features and best practices

---

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Python 3.8+** with `huaweicloudsdkrds` package — `pip install huaweicloudsdkrds`
3. **Huawei Cloud AK/SK** environment variables (`HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` or `HWC_AK` / `HWC_SK`)
4. **Default region**: `cn-north-4` (override with `--cli-region`)
5. **IAM permissions**: RDS read/write permissions (see `references/iam-policies.md`)

---

## Workflow

### 1. Basic Q&A — Product Knowledge & Instance Query

```bash
# List all RDS instances
hcloud RDS ListInstances --cli-region=cn-north-4

# List instances filtered by engine type
hcloud RDS ListInstances --cli-region=cn-north-4 --datastore_type=MySQL

# List available flavors for a specific engine
hcloud RDS ListFlavors --cli-region=cn-north-4 --database_name=MySQL --version_name=8.0

# List available database versions
hcloud RDS ListDatastores --cli-region=cn-north-4 --database_name=MySQL

# Show available upgrade versions for an instance
hcloud RDS ShowAvailableVersion --cli-region=cn-north-4 --instance_id={instance_id}

# List engine flavors (available flavors for resizing)
hcloud RDS ListEngineFlavors --cli-region=cn-north-4 --instance_id={instance_id}

# Show instance quotas
hcloud RDS ShowQuotas --cli-region=cn-north-4
```

### 2. SQL Performance Optimization

```bash
# Query slow SQL logs (within last 30 days)
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-31T23:59:59Z

# Download slow log file
hcloud RDS DownloadSlowlog --cli-region=cn-north-4 --instance_id={instance_id} \
  --file_name={file_name}

# Query TOP SQL statements
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=10

# Query historical TOP SQL
hcloud RDS ListHistoryTopSqls --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-31T23:59:59Z

# Query historical wait events
hcloud RDS ListHistoryWaitEvents --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-31T23:59:59Z

# Query top objects (tables/indexes with high load)
hcloud RDS ShowTopObjects --cli-region=cn-north-4 --instance_id={instance_id}

# Set SQL limit (control SQL concurrency)
hcloud RDS CreateSqlLimit --cli-region=cn-north-4 --instance_id={instance_id} --sql_limit_rule='{"max_concurrency":10}'
```

### 3. Daily O&M — Instance Management

```bash
# Restart instance
hcloud RDS StartInstanceRestartAction --cli-region=cn-north-4 --instance_id={instance_id}

# Resize flavor (specification change)
hcloud RDS StartResizeFlavorAction --cli-region=cn-north-4 --instance_id={instance_id} \
  --flavor_ref={flavor_id}

# Enlarge disk volume
hcloud RDS StartInstanceEnlargeVolumeAction --cli-region=cn-north-4 --instance_id={instance_id} \
  --volume_size=200

# Reduce disk volume
hcloud RDS StartInstanceReduceVolumeAction --cli-region=cn-north-4 --instance_id={instance_id} \
  --volume_size=100

# Primary-standby switchover
hcloud RDS StartFailover --cli-region=cn-north-4 --instance_id={instance_id}

# Set read-only switch
hcloud RDS SetReadOnlySwitch --cli-region=cn-north-4 --instance_id={instance_id} --readonly=true

# Update instance alias
hcloud RDS UpdateInstanceAlias --cli-region=cn-north-4 --instance_id={instance_id} --alias=new_name

# List tasks (async operation status)
hcloud RDS ListTasks --cli-region=cn-north-4 --start_time=2024-01-01T00:00:00Z --end_time=2024-01-31T23:59:59Z

# Show task detail
hcloud RDS ShowTaskDetail --cli-region=cn-north-4 --instance_id={instance_id} --task_id={task_id}

# Set auto disk expansion policy
hcloud RDS SetAutoEnlargePolicy --cli-region=cn-north-4 --instance_id={instance_id} \
  --switch_status=ON --limit_size=500 --trigger_threshold=90

# Show auto disk expansion policy
hcloud RDS ShowAutoEnlargePolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Show storage used space
hcloud RDS ShowStorageUsedSpace --cli-region=cn-north-4 --instance_id={instance_id}

# List volume info
hcloud RDS ListVolumeInfo --cli-region=cn-north-4 --instance_id={instance_id}
```

### 4. Fault Diagnosis & Troubleshooting

```bash
# Query error logs
hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-31T23:59:59Z

# Query error logs (v3.1 enhanced)
hcloud RDS ListErrorLogsNew --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-31T23:59:59Z

# Download error log file
hcloud RDS DownloadErrorlog --cli-region=cn-north-4 --instance_id={instance_id} \
  --file_name={file_name}

# Show replication status (primary-standby)
hcloud RDS ShowReplicationStatus --cli-region=cn-north-4 --instance_id={instance_id}

# Show recovery time window (for point-in-time recovery)
hcloud RDS ShowRecoveryTimeWindow --cli-region=cn-north-4 --instance_id={instance_id}

# List instance diagnosis results
hcloud RDS ListInstanceDiagnosis --cli-region=cn-north-4

# List instance diagnosis info
hcloud RDS ListInstancesInfoDiagnosis --cli-region=cn-north-4

# Query historical sessions
hcloud RDS ListHistorySessions --cli-region=cn-north-4 --instance_id={instance_id}

# Intelligent kill session (kill problematic sessions)
hcloud RDS CreateIntelligentKillSession --cli-region=cn-north-4 --instance_id={instance_id}

# Show intelligent kill session history
hcloud RDS ShowIntelligentKillSessionHistory --cli-region=cn-north-4 --instance_id={instance_id}

# Show second-level monitoring
hcloud RDS ShowSecondLevelMonitoring --cli-region=cn-north-4 --instance_id={instance_id}

# Validate instance connection
hcloud RDS ValidateInstanceConnection --cli-region=cn-north-4 --instance_id={instance_id}
```

### 5. Parameter Tuning

```bash
# List all parameter groups
hcloud RDS ListConfigurations --cli-region=cn-north-4

# Show parameter group details
hcloud RDS ShowConfiguration --cli-region=cn-north-4 --config_id={config_id}

# Show instance parameter configuration
hcloud RDS ShowInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id}

# Create parameter group
hcloud RDS CreateConfiguration --cli-region=cn-north-4 \
  --name=custom_param_group --datastore={\"type\":\"MySQL\",\"version\":\"8.0\"}

# Update parameter group
hcloud RDS UpdateConfiguration --cli-region=cn-north-4 --config_id={config_id} \
  --values='{"key":"value"}'

# Apply parameter group to instance (async)
hcloud RDS ApplyConfigurationAsync --cli-region=cn-north-4 --config_id={config_id} \
  --instance_ids='["{instance_id}"]'

# Update instance parameter directly
hcloud RDS UpdateInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id} \
  --values='{"key":"value"}'

# List parameter change history
hcloud RDS ListInstanceParamHistories --cli-region=cn-north-4 --instance_id={instance_id}

# Compare parameter configurations
hcloud RDS CompareConfiguration --cli-region=cn-north-4 \
  --source_config_id={source_id} --target_config_id={target_id}
```

### 6. Backup & Recovery

```bash
# Show backup policy
hcloud RDS ShowBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Set backup policy
hcloud RDS SetBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id} \
  --backup_policy='{"keep_days":7,"start_time":"00:00-01:00","period":"1,2,3,4,5,6,7"}'

# Show backup configuration
hcloud RDS ShowBackupConfig --cli-region=cn-north-4 --instance_id={instance_id}

# Change backup configuration
hcloud RDS ChangeBackupConfig --cli-region=cn-north-4 --instance_id={instance_id} \
  --backup_config='{"keep_days":30}'

# List backups
hcloud RDS ListBackups --cli-region=cn-north-4 --instance_id={instance_id}

# Create manual backup
hcloud RDS CreateManualBackup --cli-region=cn-north-4 \
  --instance_id={instance_id} --name=manual_backup_20240101

# Delete manual backup
hcloud RDS DeleteManualBackup --cli-region=cn-north-4 --backup_id={backup_id}

# Batch delete manual backups
hcloud RDS BatchDeleteManualBackup --cli-region=cn-north-4 \
  --backup_ids='["{backup_id_1}","{backup_id_2}"]'

# Show backup download link
hcloud RDS ShowBackupDownloadLink --cli-region=cn-north-4 --backup_id={backup_id}

# Restore to new instance
hcloud RDS CreateRestoreInstance --cli-region=cn-north-4 \
  --backup_id={backup_id} --name=restored_instance --flavor_ref={flavor_id}

# Restore to existing instance
hcloud RDS RestoreToExistingInstance --cli-region=cn-north-4 \
  --instance_id={instance_id} --backup_id={backup_id}

# Restore tables (table-level recovery)
hcloud RDS RestoreTables --cli-region=cn-north-4 --instance_id={instance_id} \
  --restore_tables='{"database":"db1","tables":["t1","t2"]}'

# List instance backup summary
hcloud RDS ListInstanceBackupSummary --cli-region=cn-north-4

# Show backup usage
hcloud RDS ShowBackupUsage --cli-region=cn-north-4 --instance_id={instance_id}
```

### 7. Security Management

```bash
# Set security group
hcloud RDS SetSecurityGroup --cli-region=cn-north-4 --instance_id={instance_id} \
  --security_group_id={sg_id}

# Switch SSL configuration
hcloud RDS SwitchSsl --cli-region=cn-north-4 --instance_id={instance_id} --ssl_option=ON

# List audit logs
hcloud RDS ListAuditlogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=2024-01-01T00:00:00Z --end_time=2024-01-31T23:59:59Z

# Show audit log policy
hcloud RDS ShowAuditlogPolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Set audit log policy
hcloud RDS SetAuditlogPolicy --cli-region=cn-north-4 --instance_id={instance_id} \
  --audit_log_policy='{"keep_days":30}'

# Show audit log download link
hcloud RDS ShowAuditlogDownloadLink --cli-region=cn-north-4 --instance_id={instance_id}
```

---

## KooCLI Command Format Standard

```bash
hcloud RDS <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `RDS` (uppercase) | `hcloud RDS ListInstances` |
| Operation name | PascalCase | `ListInstances`, `ShowBackupPolicy`, `CreateManualBackup` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--instance_id=xxx` |
| JSON parameter | `--key='{"k":"v"}'` | `--backup_policy='{"keep_days":7}'` |
| Indexed parameter | `--key.1=value1` | `--instance_ids.1=xxx` |

### SDK Fallback (Python)

When CLI is unavailable, use the Python SDK:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkrds.v3.rds_client import RdsClient
from huaweicloudsdkrds.v3.model.list_instances_request import ListInstancesRequest

credentials = BasicCredentials() \
    .with_ak(os.environ.get('HUAWEI_ACCESS_KEY')) \
    .with_sk(os.environ.get('HUAWEI_SECRET_KEY')) \
    .with_project_id('{project_id}')

client = RdsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(HwRegion.CN_NORTH_4) \
    .build()

request = ListInstancesRequest()
response = client.list_instances(request)
print(response)
```

### API Fallback (REST)

When both CLI and SDK are unavailable, use REST API directly:

```bash
curl -X GET "https://rds.cn-north-4.myhuaweicloud.com/v3/{project_id}/instances" \
  -H "X-Auth-Token: {token}" \
  -H "Content-Type: application/json"
```

---

## Core Commands

| Command | Purpose | Mode |
|---------|---------|------|
| `hcloud RDS ListInstances` | List all RDS instances | CLI |
| `hcloud RDS ListFlavors` | List available flavors | CLI |
| `hcloud RDS ListDatastores` | List database versions | CLI |
| `hcloud RDS ListSlowLogs` | Query slow SQL logs | CLI |
| `hcloud RDS ListTopSqls` | Query TOP SQL | CLI |
| `hcloud RDS ListErrorLogs` | Query error logs | CLI |
| `hcloud RDS ShowReplicationStatus` | Check replication status | CLI |
| `hcloud RDS ListInstanceDiagnosis` | Instance diagnosis | CLI |
| `hcloud RDS ListConfigurations` | List parameter groups | CLI |
| `hcloud RDS ShowInstanceConfiguration` | Show instance parameters | CLI |
| `hcloud RDS ListBackups` | List backups | CLI |
| `hcloud RDS ShowBackupPolicy` | Show backup policy | CLI |
| `hcloud RDS CreateManualBackup` | Create manual backup | CLI |
| `hcloud RDS CreateRestoreInstance` | Restore to new instance | CLI |
| `hcloud RDS SetSecurityGroup` | Modify security group | CLI |
| `hcloud RDS SwitchSsl` | Configure SSL | CLI |
| `hcloud RDS ListAuditlogs` | List audit logs | CLI |

---

## 参数确认 (Parameter Confirmation)

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Huawei Cloud region | `cn-north-4` |
| `--instance_id` | Yes (most ops) | RDS instance ID | `rds-xxxxx` |
| `--project_id` | Auto | Project ID (auto from credentials) | Auto |
| `--datastore_type` | No | Filter by engine type | `MySQL` |
| `--config_id` | Yes (param ops) | Parameter group ID | `xxxxx` |
| `--backup_id` | Yes (backup ops) | Backup ID | `xxxxx` |
| `--flavor_ref` | Yes (resize) | Target flavor ID | `rds.mysql.xlarge` |
| `--start_date` / `--end_date` | Yes (log ops) | Date range (ISO 8601) | `2024-01-01T00:00:00Z` |
| `--volume_size` | Yes (disk ops) | Target disk size in GB | `200` |

### Mutating Operations Requiring User Confirmation

The following operations modify RDS resources and **must** prompt the user for explicit confirmation before execution:

- **Instance**: Restart, Resize, Disk Expand/Reduce, Failover, Stop, Delete
- **Backup**: Create Manual Backup, Delete Backup, Restore Instance
- **Parameter**: Create/Update/Delete Configuration, Apply Configuration, Update Instance Parameter
- **Security**: Set Security Group, Switch SSL, Set Audit Log Policy
- **Session**: Intelligent Kill Session

---

## 输出格式 (Output Format)

All command outputs are returned as structured JSON. The skill formats results into readable tables and provides intelligent analysis:

### CLI Output

```json
{
  "instances": [
    {"id": "rds-xxxxx", "name": "my-db", "status": "ACTIVE", "type": "Single", "engine": "MySQL"}
  ]
}
```

### Analysis Output

| Field | Description |
|-------|-------------|
| `status` | Instance health status (ACTIVE/FAILED/BUILD) |
| `recommendation` | Suggested action based on analysis |
| `risk_level` | Risk assessment (low/medium/high) |

---

## 验证方法 (Verification)

- **CLI verification**: Run `hcloud RDS ListInstances --cli-region=cn-north-4` and confirm JSON output
- **SDK verification**: Execute Python SDK snippet and check `response.status_code == 200`
- **API verification**: Send REST request and verify `200 OK` response with valid JSON body
- **End-to-end**: Create a test instance, query its status, then clean up
- **Reference**: See [Verification Method](references/verification-method.md) for detailed test procedures

---

## Reference Documents

- [IAM Policies](references/iam-policies.md) — Least-privilege IAM policies for RDS operations
- [Verification Method](references/verification-method.md) — Verification and testing methodology
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria for the skill
- [CLI Installation Guide](references/cli-installation-guide.md) — CLI installation and configuration
- [API Paths](references/api-paths.md) — REST API paths verified from SDK source
- [RDS Troubleshooting Guide](references/rds-troubleshooting-guide.md) — Common fault diagnosis procedures
- [SQL Optimization Guide](references/sql-optimization-guide.md) — SQL performance optimization methodology

---

## Best Practices

- Always specify `--cli-region` explicitly to avoid region confusion
- Use `--datastore_type` filter when listing instances to narrow results
- For slow log analysis, limit date range to 7 days for performance
- Before resizing, check available flavors with `ListEngineFlavors`
- Before restoring, verify recovery time window with `ShowRecoveryTimeWindow`
- Parameter changes should be tested on non-production instances first
- Backup deletion is irreversible — always verify backup ID before deletion
- Use audit logs for compliance and security investigation

---

## Notes

- All mutating operations (Create/Update/Delete/Restart/Resize/Restore) require explicit user confirmation
- Credentials (AK/SK) are read from environment variables; hardcoding is prohibited
- CLI is the primary execution mode; SDK and API are fallbacks for unavailable CLI commands
- Date format follows ISO 8601: `yyyy-mm-ddThh:mm:ssZ` (e.g., `2024-01-01T00:00:00Z`)
- Slow log queries are limited to the last 30 days
- The skill supports all RDS engines: MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB(for MySQL), TaurusDB
