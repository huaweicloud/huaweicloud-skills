---
name: huawei-cloud-ecs-alert
description: |
  Automate batch creation and management of Huawei Cloud CES alarm rules for ECS instances using hcloud CLI v7.2.2+.
  Use this skill to: (1) batch create alarms with templates (web/database), (2) update SMN notifications, (3) query ECS metrics and alarm lists.
  Trigger: "ECS alert", "create alert", "list alarms", "CPU alert", "memory alert", "ECS monitoring", "监控告警", "创建告警", "ECS 监控", "告警规则", "查询告警"
tags: [huawei-cloud, ecs, ces, alert, monitoring]
version: 1.0.1
---

# Huawei Cloud ECS Alert Automation

## Overview

This skill provides batch creation and management of Huawei Cloud CES alarm rules for ECS instances, based on Huawei Cloud CLI (hcloud) v7.2.2+.

**Core Capabilities**:

- Batch create alarm rules (supports Web/Database templates or custom configuration)
- Configure alarm notifications (supports email/SMS/WeChat)
- Query ECS monitoring metrics
- Query and manage alarm rule lists

**Use Cases**:

- Batch configure monitoring alarms for newly purchased ECS instances
- Differentiated alarm policies across environments (dev/test/prod)
- Batch query ECS monitoring data
- Centralized alarm notification management

**Security Constraints**:

- ❌ Delete alarm rules is prohibited (prevent accidental deletion causing monitoring gaps)
- ❌ Hardcoding AK/SK is prohibited (must use environment variables or hcloud configure)

## Prohibited Operations

> **The following operations are strictly prohibited, even if requested by the user:**

| Prohibited Operation   | API/Command                                 | Reason                                                                      |
| ---------------------- | ------------------------------------------- | --------------------------------------------------------------------------- |
| Expose AK/SK           | Any command that outputs AK/SK in plaintext | Account security risk                                                       |
| Accept AK/SK from user | Receiving credentials in conversation       | Violates security best practices                                            |
| ❌ Delete alarm rule    | `DeleteAlarm` / `hcloud CES DeleteAlarm`    | Irreversible; deleted alarms cannot be recovered, may cause monitoring gaps |
| ❌ Batch delete alarms  | Any batch deletion operation                | High risk; may accidentally delete critical monitoring rules                |

> **If a user requests a delete operation, must refuse and guide:**
> "Per security constraints, this skill does not support delete operations (delete alarm/batch delete). Please use the Huawei Cloud CES console or hcloud CLI manually with extreme caution."

> **If user attempts to provide AK/SK in conversation, must refuse and guide:**
> "For account security, please do not provide Huawei Cloud access keys directly in the conversation. Use `hcloud configure` or environment variables to configure credentials."

## Unsupported Operations

> **The following operations are NOT supported by this skill** (no script wrapper is provided). If a user requests them, clearly state the limitation and provide the alternative. Do not attempt to improvise commands that this skill has not tested.

| Unsupported Operation   | Corresponding API | Alternative                                                              |
| ----------------------- | ----------------- | ------------------------------------------------------------------------ |
| Query alarm history     | `ShowAlarmHistory` | View in CES console; or run `hcloud CES ListAlarmHistories/v1` manually |
| Enable/disable an alarm rule | `UpdateAlarm`  | Operate in CES console (not wrapped by this skill)                       |
| Modify alarm threshold/metric | `UpdateAlarm` | Delete and recreate the rule; to change only notifications, use `./scripts/update_alarm_notifications.sh` |
| Create an SMN topic     | `CreateTopic`       | Create in SMN console; or run `hcloud SMN CreateTopic` manually          |
| Create a monitoring dashboard | `CreateOneDashboard` | Operate in CES console                                              |
| View a single alarm rule detail | `ShowAlarm`    | Use `./scripts/list_alarms.sh --name <pattern>` to filter                 |

> **If a user requests one of these operations**, respond:
> "This skill does not support <operation>. Use the Huawei Cloud CES/SMN console, or the equivalent hcloud CLI command manually: <alternative>. You may also request an enhancement via the skill's issue tracker."

## Workflow

The standard workflow of this skill is as follows:

```text
1. Environment setup  → Configure hcloud CLI credentials (hcloud configure or env vars)
2. Query resources    → ./scripts/list_ecs.sh to get ECS instance list
3. Create alarms      → ./scripts/create_alert_rules.sh --template web --ecs-ids <ids>
4. Configure notify   → ./scripts/manage_notifications.sh --action create ...
5. Verify results     → ./scripts/list_alarms.sh to confirm alarm rules created
6. Continuous monitor → ./scripts/batch_query_metrics.sh to query metrics
```

> **Write operation confirmation**: Step 3 (create alarms), Step 4 (create/delete subscriptions), update notification config, and other write operations require user confirmation of operation content and target resources before execution.

## Core Commands

### Query Commands (read-only, no confirmation needed)

```bash
# List ECS instances
./scripts/list_ecs.sh [--name <filter>] [--format json]

# List alarm rules
./scripts/list_alarms.sh [--name <filter>] [--format json]

# List SMN topics and subscriptions
./scripts/list_subscriptions.sh [--topics | --subscriptions]

# Batch query monitoring metrics
./scripts/batch_query_metrics.sh --ecs-ids <ids> --metric cpu_util --period 1h
```

### Create Commands (write operations, require user confirmation)

```bash
# Batch create alarm rules (WARNING: confirm target ECS and alarm template)
./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001,ecs-002

# Create SMN subscription (WARNING: confirm subscription endpoint and topic)
./scripts/manage_notifications.sh --action create --protocol email --endpoint user@example.com --topic-urn <URN>
./scripts/create_email_subscription.sh --email user@example.com --topic-urn <URN>
```

### Update/Delete Commands (write operations, require user confirmation)

```bash
# Update alarm notification config (WARNING: confirm alarm ID and notification topic)
./scripts/update_alarm_notifications.sh --action add --alarm-id <id> --smn-topic-urn <URN>

# Delete SMN subscription (WARNING: confirm subscription URN)
./scripts/manage_notifications.sh --action delete --subscription-urn <URN>
```

## Architecture

```bash
Huawei Cloud CES Alert Management
├── CreateAlertRules       (Batch create alarm rules, supports templates/custom)
├── ConfigureNotifications  (Configure alarm notifications, supports email/SMS/WeChat)
├── QueryMetrics           (Batch query monitoring data, supports multiple ECS)
└── ListAlarmRules         (List alarm rules and details)

```

## Prerequisites

> **Prerequisite 1: Huawei Cloud CLI (hcloud / KooCLI) >= 7.2.2**
> Run `hcloud version` to verify version >= 7.2.2. If not installed or version is too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version

```

> **Prerequisite 2: Huawei Cloud Credentials Configured**
> Check if CLI configuration contains valid credentials (AK/SK, IAM, etc.).
>
> ```bash
> hcloud configure list
> 
> ```
>
> **Credential Configuration Methods (choose one):**
>
> 1. **hcloud CLI configuration (recommended)**: `hcloud configure` interactive setup, credentials encrypted and stored in `~/.hcloud/config.json`
> 2. **Per-call AK/SK**: pass `--cli-access-key=<AK> --cli-secret-key=<SK>` on each command (for automation; note: appears in process list)
>
> > **⚠️ IMPORTANT**: hcloud (KooCLI) authenticates ONLY via `~/.hcloud/config.json` (from `hcloud configure`) or the `--cli-access-key`/`--cli-secret-key` arguments. It does **NOT** read `HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, or `HUAWEI_CLOUD_SECURITY_TOKEN` environment variables — such variables are silently ignored (hcloud falls back to config.json). Do not instruct users to export these env vars as a way to authenticate hcloud.
>
> **Credential source for this skill's scripts**: The bundled Shell scripts are thin wrappers around hcloud CLI. They read the region from `HW_REGION_NAME`/`HUAWEI_CLOUD_REGION` (or default to `cn-north-4`) to set `--cli-region`, but **authentication always comes from `hcloud configure`**. Configure credentials once with `hcloud configure`, then the scripts work.

> **If output does not contain valid configuration, stop operation and guide user to configure.**
> **hcloud Parameter Format Requirement**
> hcloud (KooCLI) **all parameters must use `--param=value` format** (equals sign connection), does not support space
> separation.
> ✅ Correct: `hcloud CES ListAlarmRules --cli-region=cn-north-4`
> ❌ Incorrect: `hcloud CES ListAlarmRules --cli-region cn-north-4`
>
> This skill provides 8 Shell scripts, encapsulating common hcloud commands, supporting batch operations and formatted
> output.
>
> <details>
> <summary>**Script List and Usage Examples (Click to Expand)**</summary>
>
> | Script                          | Function                                | hcloud Command                        |
> | ------------------------------- | --------------------------------------- | ------------------------------------- |
> | `list_ecs.sh`                   | Query ECS instance list                 | `hcloud ECS ListServersDetails`       |
> | `list_alarms.sh`                | Query alarm rule list                   | `hcloud CES ListAlarmRules`           |
> | `create_alert_rules.sh`         | Batch create alarm rules                | `hcloud CES CreateAlarmRules`       |
> | `batch_query_metrics.sh`        | Batch query monitoring data             | `hcloud CES ShowMetricData`           |
> | `list_subscriptions.sh`         | Query SMN topics and subscriptions      | `hcloud SMN ListTopics/Subscriptions` |
> | `manage_notifications.sh`       | Manage SMN subscriptions                | `hcloud SMN Subscribe/Unsubscribe`    |
> | `update_alarm_notifications.sh` | Update alarm notification configuration | `hcloud CES UpdateAlarmNotifications` |
>
> **Usage Examples:**
>
> ```bash
> 
> # Query ECS instances
> 
> ./scripts/list_ecs.sh                          # Query all ECS
> ./scripts/list_ecs.sh --name ecs-001           # Filter by name
> ./scripts/list_ecs.sh --output json            # Output as JSON
> ./scripts/list_ecs.sh --output ids             # Output only ECS ID list
> 
> # Query alarm rules
> 
> ./scripts/list_alarms.sh                       # Query all alarms
> ./scripts/list_alarms.sh --name-pattern "cpu.*"  # Filter by name pattern
> ./scripts/list_alarms.sh --output ids          # Output only alarm IDs
> 
> # Create alarm rules
> 
> ./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001,ecs-002
> ./scripts/create_alert_rules.sh --metric cpu_util --threshold 80 --ecs-ids ecs-001
> ./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001 --smn-topic-urn
> urn:smn:cn-north-4:xxx:ECS_ALARM_NOTIFY
> ./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001 --dry-run  # Dry run
> 
> ```bash
> 
> </details>

## Core Capabilities

- **Batch Create Alarm Rules**: Support template-based creation (Web/Database scenarios) or custom
  metric/threshold configuration
- **Batch Query Monitoring Data**: Support multi-ECS concurrent query, output CPU/Memory/Disk metrics
- **Notification Configuration**: Support email/SMS/WeChat notification, SMN subscription management
- **Security Compliance**: AK/SK via environment variables or CLI config, never hardcode

## Usage Scenarios

### Scenario 1: Batch Configure Alarms for New ECS

**Background**: Purchased 10 new ECS instances, need to configure CPU/Memory alarm rules for all.

**Steps**:

1. Query ECS instance IDs
2. Batch create alarm rules using web template
3. Configure email notification

```bash
# Step 0: Configure credentials once (hcloud CLI reads ~/.hcloud/config.json; it does NOT read AK/SK env vars)
hcloud configure
# Optional: set region env var consumed by the scripts' --cli-region default
export HUAWEI_CLOUD_REGION=cn-north-4
./scripts/list_ecs.sh --output ids

# 2. Batch create alarm rules
./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001,ecs-002,ecs-003

# 3. Configure notification
./scripts/manage_notifications.sh --action subscribe --topic-urn <SMN_TOPIC_URN> --protocol email --endpoint user@example.com

```

### Scenario 2: Query Monitoring Data for Multiple ECS

**Background**: Need to check CPU utilization for 5 ECS instances over the past hour.

```bash
./scripts/batch_query_metrics.sh \
  --ecs-ids ecs-001,ecs-002,ecs-003,ecs-004,ecs-005 \
  --metric cpu_util \
  --from 2024-01-01T10:00:00Z \
  --to 2024-01-01T11:00:00Z \
  --output table

```

## Input Parameters

- **AK/SK**: Via `hcloud configure` (recommended, stored in `~/.hcloud/config.json`) — hcloud CLI does NOT read AK/SK environment variables
- **Security Token** (optional): For temporary STS credentials, use `hcloud configure --cli-mode=AKSK` + `--cli-security-token` or pass `--cli-security-token=<token>` per command
- **Region**: Via `--cli-region` parameter or `HUAWEI_CLOUD_REGION`/`HW_REGION_NAME` env var (default: cn-north-4)
- **ECS IDs**: Comma-separated ECS instance IDs
- **Alarm IDs**: Comma-separated alarm rule IDs
- **Template**: Alarm template (web/database)
- **Metric**: Monitoring metric name. Host metrics: `cpu_util`, `disk_util_inband` (namespace SYS.ECS); memory metric: `mem_usedPercent` (namespace AGT.ECS)
- **Threshold**: Alarm threshold value
- **SMN Topic URN**: SMN topic URN for notifications

## Parameter Confirmation

> **All write operations (Create / Update / Delete) must explicitly show operation content and obtain user confirmation before execution.**

| Operation Type | Script | Content to Confirm |
|----------------|--------|---------------------|
| Create | `create_alert_rules.sh` | Target ECS ID list, alarm template/metric/threshold |
| Create | `manage_notifications.sh --action create` | Subscription protocol, endpoint address, SMN topic URN |
| Create | `create_email_subscription.sh` | Email address, SMN topic URN |
| Update | `update_alarm_notifications.sh` | Alarm ID, SMN topic URN, operation type |
| Delete | `manage_notifications.sh --action delete` | Subscription URN (irreversible after deletion) |

> Query operations (list_ecs / list_alarms / list_subscriptions / batch_query_metrics) are read-only and do not require confirmation.

## Output Format

- **Table**: Formatted table output (default)
- **JSON**: JSON format for programmatic processing
- **IDs**: Only ID list for scripting

## Verification Method

After executing any operation, verify using the following methods:

1. **List Alarms**: `./scripts/list_alarms.sh --name-pattern <pattern>`
2. **Query Metrics**: `./scripts/batch_query_metrics.sh --ecs-ids <ids> --metric cpu_util`
3. **Check Notifications**: `./scripts/list_subscriptions.sh`

See [references/troubleshooting.md](references/troubleshooting.md) for common verification issues.

## Best Practices

1. **Use Templates for Standard Scenarios**: Web/Database templates cover most use cases
2. **Configure Multiple Notification Channels**: Email + SMS for critical alarms
3. **Set Reasonable Thresholds**: CPU 80%, Memory 85%, Disk 90% recommended
4. **Configure Credentials via `hcloud configure`** (hcloud CLI reads `~/.hcloud/config.json`; it does NOT read AK/SK env vars):
   - ✅ Recommended: `hcloud configure` (encrypted storage in `~/.hcloud/config.json`)
   - ⚠️ Region env var only: `HUAWEI_CLOUD_REGION` / `HW_REGION_NAME` set the script's `--cli-region` default — region only, NOT authentication
   - ❌ Prohibited: Hardcode AK/SK in scripts or configuration files
   - ❌ Misleading: `export HUAWEI_CLOUD_AK/SK` or `export HW_ACCESS_KEY/SECRET_KEY` will NOT authenticate hcloud (env vars are ignored)
5. **Use Environment Check Script**: Run `./scripts/check_env.sh` before first use to verify configuration

## Common Issues

### Issue 1: hcloud Command Not Found

**Solution**: Install KooCLI, see [references/cli-installation-guide.md](references/cli-installation-guide.md)

### Issue 2: 403 Forbidden

**Solution**: Check IAM permissions, ensure `CES FullAccess` and `SMN FullAccess` policies are granted. See
[references/iam-policies.md](references/iam-policies.md)

### Issue 3: Alarm Creation Fails

**Solution**: Check metric name and threshold range. CPU/Memory thresholds should be 0-100.

### Issue 4: No Monitoring Data

**Solution**: Check ECS instance status and metric collection interval. Data may have 5-minute delay.

See [references/troubleshooting.md](references/troubleshooting.md) for more troubleshooting guides.

## Important Notes

> **CLI Version Requirement**: Must use hcloud CLI v7.2.2 or later. Older versions may not support certain API parameter formats.

> **Region Consistency**: All operations must specify the same region (`--cli-region` or `HUAWEI_CLOUD_REGION` environment variable). Cross-region operations will fail.

> **Alarm Threshold Range**: CPU/memory utilization thresholds must be between 0-100. Disk usage threshold is recommended to be set between 80-95.

> **Monitoring Data Delay**: CES monitoring data typically has a 5-minute delay. Querying real-time data may return empty results.

> **SMN Subscription Creation**:
>
> - ✅ **Recommended**: Use `./scripts/create_email_subscription.sh` script, which automatically uses hcloud CLI configured credentials (no need to manually set environment variables)
> - ✅ **Alternative**: Use Huawei Cloud Console (SMN → Topics → Subscribe) for subscription creation
> - ⚠️ **Note**: Email/SMS subscriptions require confirmation before receiving notifications. Check your email and click the confirmation link.
>
> See [references/smn-subscription-guide.md](references/smn-subscription-guide.md) for detailed guide.

> **Batch Operation Limits**: Single batch creation is recommended for no more than 20 ECS instances. Too many instances may cause API timeout.

> **Credential Security**:
>
> - ✅ Recommended: Use `hcloud configure` — credentials stored encrypted in `~/.hcloud/config.json`, which is the ONLY credential source hcloud CLI reads
> - ⚠️ Region env var only (NOT auth): `HUAWEI_CLOUD_REGION` / `HW_REGION_NAME` set the scripts' `--cli-region` default
> - ❌ Misleading: `export HW_ACCESS_KEY/HW_SECRET_KEY` or `export HUAWEI_CLOUD_AK/HUAWEI_CLOUD_SK` do NOT authenticate hcloud (env vars are ignored)
> - ❌ Prohibited: Hardcode AK/SK in scripts or configuration files
>
> **Authentication**: hcloud CLI authenticates ONLY via `~/.hcloud/config.json` (from `hcloud configure`) or `--cli-access-key`/`--cli-secret-key` per-command arguments. Environment variables for AK/SK/token are silently ignored. Do not document env-var export as a working authentication method.

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md)
- [IAM Policies](references/iam-policies.md)
- [Related APIs](references/related-apis.md)
- [Troubleshooting](references/troubleshooting.md)
- [SMN Subscription Guide](references/smn-subscription-guide.md)
- [Common Commands](references/common-commands.md)
- [Memory Monitoring Guide](references/memory-monitoring-guide.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
