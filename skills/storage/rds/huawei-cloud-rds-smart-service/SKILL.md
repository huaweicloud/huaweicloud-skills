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
hcloud RDS ListEngineFlavors --cli-region=cn-north-4 --instance_id={instance_id} --ha_mode=ha --availability_zone_ids=cn-north-4a

# Show instance quotas
hcloud RDS ShowQuotas --cli-region=cn-north-4
```

### 2. SQL Performance Optimization

```bash
# Query slow SQL logs (within last 30 days)
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z) --end_date=$(date +%Y-%m-%dT%H:%M:%S%z)

# Download slow log file
hcloud RDS DownloadSlowlog --cli-region=cn-north-4 --instance_id={instance_id} \
  --file_name={file_name}

# Query TOP SQL statements
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=10

# Query historical TOP SQL
hcloud RDS ListHistoryTopSqls --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=$(($(date -d '7 days ago' +%s)*1000)) --end_time=$(($(date +%s)*1000))

# Query historical wait events
hcloud RDS ListHistoryWaitEvents --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=$(($(date -d '7 days ago' +%s)*1000)) --end_time=$(($(date +%s)*1000))

# Query top objects (tables/indexes with high load)
hcloud RDS ShowTopObjects --cli-region=cn-north-4 --instance_id={instance_id}

# Set SQL limit (control SQL concurrency)
hcloud RDS CreateSqlLimit --cli-region=cn-north-4 --instance_id={instance_id} --db_name={db_name} --max_concurrency=10 --max_waiting=5
```

### 3. Daily O&M — Instance Management

```bash
# Restart instance
hcloud RDS StartInstanceRestartAction --cli-region=cn-north-4 --instance_id={instance_id} \
  --restart.restart_server=true

# Resize flavor (specification change)
hcloud RDS StartResizeFlavorAction --cli-region=cn-north-4 --instance_id={instance_id} --resize_flavor.spec_code={spec_code}

# Enlarge disk volume
hcloud RDS StartInstanceEnlargeVolumeAction --cli-region=cn-north-4 --instance_id={instance_id} \
  --enlarge_volume.size=200

# Reduce disk volume
hcloud RDS StartInstanceReduceVolumeAction --cli-region=cn-north-4 --instance_id={instance_id} --reduce_volume.size=100 --reduce_volume.is_delay=false

# Primary-standby switchover
hcloud RDS StartFailover --cli-region=cn-north-4 --instance_id={instance_id}

# Set read-only switch
hcloud RDS SetReadOnlySwitch --cli-region=cn-north-4 --instance_id={instance_id} --readonly=true

# Update instance alias
hcloud RDS UpdateInstanceAlias --cli-region=cn-north-4 --instance_id={instance_id} --alias=new_name

# List tasks (async operation status)
hcloud RDS ListTasks --cli-region=cn-north-4 --start_time=$(($(date -d '7 days ago' +%s)*1000)) --end_time=$(($(date +%s)*1000))

# Show task detail
hcloud RDS ShowTaskDetail --cli-region=cn-north-4 --instance_id={instance_id} --workflow_id={workflow_id} --workflow_name={workflow_name}

# Set auto disk expansion policy
hcloud RDS SetAutoEnlargePolicy --cli-region=cn-north-4 --instance_id={instance_id} --switch_option=true --limit_size=500 --trigger_threshold=15

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
  --start_date=$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z) --end_date=$(date +%Y-%m-%dT%H:%M:%S%z)

# Query error logs (v3.1 enhanced)
hcloud RDS ListErrorLogsNew --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z) --end_date=$(date +%Y-%m-%dT%H:%M:%S%z)

# Download error log file
hcloud RDS DownloadErrorlog --cli-region=cn-north-4 --instance_id={instance_id}

# Show replication status (primary-standby)
hcloud RDS ShowReplicationStatus --cli-region=cn-north-4 --instance_id={instance_id}

# Show recovery time window (for point-in-time recovery)
hcloud RDS ShowRecoveryTimeWindow --cli-region=cn-north-4 --instance_id={instance_id}

# List instance diagnosis results
hcloud RDS ListInstanceDiagnosis --cli-region=cn-north-4 --engine=mysql

# List instance diagnosis info
hcloud RDS ListInstancesInfoDiagnosis --cli-region=cn-north-4 --engine=mysql --diagnosis=high_pressure

# Query historical sessions
hcloud RDS ListHistorySessions --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=$(($(date -d '7 days ago' +%s)*1000)) --end_time=$(($(date +%s)*1000)) --limit=10 --offset=0

# Intelligent kill session (kill problematic sessions)
hcloud RDS CreateIntelligentKillSession --cli-region=cn-north-4 --instance_id={instance_id} --auto_add_sql_limit_rule=false

# Show intelligent kill session history
hcloud RDS ShowIntelligentKillSessionHistory --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=$(($(date -d '7 days ago' +%s)*1000)) --end_time=$(($(date +%s)*1000)) --page_num=1 --page_size=10

# Show second-level monitoring
hcloud RDS ShowSecondLevelMonitoring --cli-region=cn-north-4 --instance_id={instance_id}

# Validate instance connection (RDS for SQL Server only; requires user_info)
hcloud RDS ValidateInstanceConnection --cli-region=cn-north-4 --instance_id={instance_id} \
  --user_info.login_user_name=dbuser --user_info.login_user_password=*** \
  --user_info.server_ip=1.2.3.4 --user_info.server_port=3306
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
  --name=custom_param_group --datastore.type=MySQL --datastore.version=8.0

# Update parameter group
hcloud RDS UpdateConfiguration --cli-region=cn-north-4 --config_id={config_id} \
  --values.max_connections=100

# Apply parameter group to instance (async)
hcloud RDS ApplyConfigurationAsync --cli-region=cn-north-4 --config_id={config_id} \
  --instance_ids.1={instance_id}

# Update instance parameter directly
hcloud RDS UpdateInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id} \
  --values.max_connections=100

# List parameter change history
hcloud RDS ListInstanceParamHistories --cli-region=cn-north-4 --instance_id={instance_id}

# Compare parameter configurations
hcloud RDS CompareConfiguration --cli-region=cn-north-4 --source_id={source_id} --target_id={target_id}
```

### 6. Backup & Recovery

```bash
# Show backup policy
hcloud RDS ShowBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Set backup policy
hcloud RDS SetBackupPolicy --cli-region=cn-north-4 --instance_id={instance_id} \
  --backup_policy.keep_days=7 --backup_policy.start_time=00:00-01:00 --backup_policy.period=1,2,3,4,5,6,7

# Show backup configuration
hcloud RDS ShowBackupConfig --cli-region=cn-north-4 --instance_id={instance_id}

# Change backup configuration
hcloud RDS ChangeBackupConfig --cli-region=cn-north-4 --instance_id={instance_id} --default_backup_method=EBACKUP

# List backups
hcloud RDS ListBackups --cli-region=cn-north-4 --instance_id={instance_id}

# Create manual backup
hcloud RDS CreateManualBackup --cli-region=cn-north-4 \
  --instance_id={instance_id} --name=manual_backup_20240101

# Delete manual backup
hcloud RDS DeleteManualBackup --cli-region=cn-north-4 --backup_id={backup_id}

# Batch delete manual backups
hcloud RDS BatchDeleteManualBackup --cli-region=cn-north-4 --backup_ids.1={backup_id_1} --backup_ids.2={backup_id_2}

# Show backup download link
hcloud RDS ShowBackupDownloadLink --cli-region=cn-north-4 --backup_id={backup_id}

# Restore to new instance
hcloud RDS CreateRestoreInstance --cli-region=cn-north-4 \
  --restore_point.backup_id={backup_id} --name=restored_instance --flavor_ref={flavor_id} \
  --availability_zone=cn-north-4a,cn-north-4g --volume.size=100 --volume.type=CLOUDSSD
# 注意: `--password` 与 KooCLI 系统参数同名冲突,无法直接传参。需用 `echo 'b' |` 管道选择"API参数"绕过,或用 `--cli-jsonInput=jsonFile` 传入整份 JSON body。恢复实例磁盘不能小于源实例(报 DBS.200073)。

# Restore to existing instance
hcloud RDS RestoreToExistingInstance --cli-region=cn-north-4 --target.instance_id={target_instance_id} --source.instance_id={source_instance_id} --source.backup_id={backup_id} --source.type=backup

# Restore tables (table-level recovery)
hcloud RDS RestoreTables --cli-region=cn-north-4 --instance_id={instance_id} --restoreTables.1.database={db_name} --restoreTables.1.tables.1.oldName={old_table} --restoreTables.1.tables.1.newName={new_table} --restoreTime=$(($(date -d '1 day ago' +%s)*1000))

# List instance backup summary
hcloud RDS ListInstanceBackupSummary --cli-region=cn-north-4

# Show backup usage (by engine)
hcloud RDS ShowBackupUsage --cli-region=cn-north-4 --engine=MySQL
```

### 7. Security Management

```bash
# Set security group
hcloud RDS SetSecurityGroup --cli-region=cn-north-4 --instance_id={instance_id} \
  --security_group_id={sg_id}

# Switch SSL configuration
hcloud RDS SwitchSsl --cli-region=cn-north-4 --instance_id={instance_id} --ssl_option=true

# List audit logs
hcloud RDS ListAuditlogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_time=$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z) --end_time=$(date +%Y-%m-%dT%H:%M:%S%z) --limit=10 --offset=0

# Show audit log policy
hcloud RDS ShowAuditlogPolicy --cli-region=cn-north-4 --instance_id={instance_id}

# Set audit log policy
hcloud RDS SetAuditlogPolicy --cli-region=cn-north-4 --instance_id={instance_id} --keep_days=30 --audit_types.1=CREATE_USER

# Show audit log download link
hcloud RDS ShowAuditlogDownloadLink --cli-region=cn-north-4 --instance_id={instance_id} --ids.1={auditlog_id}
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
| Indexed parameter | `--key.1=value1` | `--instance_ids.1=xxx` |
| Nested object parameter | `--parent.child=value` | `--backup_policy.keep_days=7`, `--datastore.type=MySQL` |

> **注意**: hcloud CLI 的 body/嵌套参数**不支持**整体 JSON 传参(`--param='{"k":"v"}'` 会报 `仅支持参数 X 的值为 {} 或 []`)。必须按 `--parent.child=value` 拆分传参。数组用下标 `--instance_ids.1=xxx`。

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
| `--resize_flavor.spec_code` | Yes (resize) | Target flavor spec code | `rds.mysql.n1.large.4.ha` |
| `--start_date` / `--end_date` | Yes (log ops) | Date range (ISO 8601, only last 30 days) | `$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z)` |
| `--enlarge_volume.size` | Yes (disk ops) | Target disk size in GB | `200` |

### Mutating Operations Requiring User Confirmation

The following operations modify RDS resources and **must** prompt the user for explicit confirmation before execution:

- **Instance**: Restart, Resize, Disk Expand/Reduce, Failover, Stop（删除实例属高风险操作，本技能不支持，请通过华为云控制台操作）
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
- Date format: log commands (`--start_date`/`--end_date`) use ISO 8601 **with timezone offset** (e.g., `2026-08-04T00:00:00+0800`); task commands (`--start_time`/`--end_time`) use **UTC epoch milliseconds**
- **日志/慢SQL 查询仅支持查询当前时间前一个月内的数据**。日期格式使用带时区偏移的 ISO 8601（如 `2026-08-04T00:00:00+0800`），用 `$(date -d '7 days ago' +%Y-%m-%dT00:00:00%z)` 动态生成；**注意不要使用 UTC 的 `Z` 结尾**（`...T00:00:00Z`），实测会导致 `DBS.01010023` 报错。`ListTasks`/`ListHistory*` 等任务类命令的 `--start_time`/`--end_time` 需传 **UTC 毫秒时间戳**（`$(($(date -d '7 days ago' +%s)*1000))`）。**不要照抄过期的静态示例日期**
- Slow log queries are limited to the last 30 days
- The skill supports all RDS engines: MySQL, PostgreSQL, SQL Server, MariaDB, GaussDB(for MySQL), TaurusDB
- **Engine capability limits (MySQL)** — the following read commands return `DBS.280343` (Operation not allowed by the DB engine) on MySQL; they are supported on other engines only, and are not defects in the skill: `ListTopSqls`, `ShowTopObjects`, `ListVolumeInfo`, `ShowAvailableVersion`, `ValidateInstanceConnection` (SQL Server only), `ListHistoryTopSqls`, `ListHistorySessions`, `ListHistoryWaitEvents`. `ShowBackupConfig`/`ShowRecoveryTimeWindow` also return `DBS.280238`/`DBS.280235` on MySQL.
- **Whitelist permission limits** — `ListInstanceBackupSummary`/`ShowBackupUsage` return `DBS.01280003` (domain not in whitelist); these require whitelist activation from Huawei Cloud.
- `ListEngineFlavors` requires single AZ (`--availability_zone_ids=cn-north-4a`); comma-separated multi-AZ returns `DBS.280244`.
