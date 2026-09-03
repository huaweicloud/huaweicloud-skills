---
name: huawei-cloud-lts-manage
description: >
  Huawei Cloud LTS (Log Tank Service) full lifecycle management via hcloud CLI.
  Covers log groups, log streams, indexes, transfer tasks, keyword/SQL alarm rules,
  and log search. Supports Query (list/show logs, alarms, transfers, indexes),
  Create (log groups/streams, indexes, transfers, alarms), Update (TTL, index,
  transfer, alarm config), Delete (log resources, alarm rules), and Diagnose
  (search logs to locate faults). Delete operations require explicit user confirmation;
  batch deletion of all LTS resources is prohibited.
  Triggers include: LTS, 云日志服务, log group, log stream, 日志组, 日志流, 日志检索,
  日志转储, 日志告警, 索引配置, log transfer, log alarm, log index, 日志运维,
  故障排查, log search, structured log, SQL alarm, keyword alarm.
tags: [huawei-cloud lts log management query create update delete]
---

# Huawei Cloud LTS Log Service Management

## Overview

This skill manages Huawei Cloud LTS (Log Tank Service / 云日志服务) resources through hcloud CLI.
It covers the full lifecycle of log groups, log streams, indexes, transfer tasks, and alarm rules,
plus log search for fault diagnosis and security event response.

**Capabilities:**

| Category | Operations |
|----------|-----------|
| **Query** | List log groups, log streams, indexes, transfers, alarm rules, alarm history; search logs (keyword, structured, context, histogram) |
| **Create** | Create log groups, log streams, full-text indexes, OBS transfer tasks, keyword alarm rules, SQL alarm rules |
| **Update** | Update log group TTL, log stream TTL/storage, transfer config, alarm rules, alarm status, struct config |
| **Delete** | Delete log groups, log streams, transfers, alarm rules (⚠️ requires confirmation) |
| **Diagnose** | Search logs by keyword/time to locate faults; query log context; view log distribution histogram |

## Prerequisites

1. **hcloud CLI** installed and authenticated — see `references/cli-installation-guide.md`
2. **Huawei Cloud AK/SK** configured via `hcloud configure` (CLI profile)
3. **IAM permissions** — see `references/iam-policies.md` for least-privilege policy
4. **Region**: LTS is region-specific. Use `--cli-region` to specify the target region (e.g., `cn-north-4`, `ap-southeast-1`)

## Workflow

```
1. Identify target log group/stream (ListLogGroups → ListLogStreams)
2. Query or manage resources based on user intent:
   ├── Query: list/show logs, indexes, transfers, alarms
   ├── Create: create log group/stream/index/transfer/alarm
   ├── Update: modify TTL/index/transfer/alarm config
   ├── Delete: remove resources (⚠️ confirmation required)
   └── Diagnose: search logs with keywords/time range
3. Return results (query returns JSON; mutations return resource config snapshot)
```

## Core Commands

### Query — Log Groups & Streams

```bash
# List all log groups
hcloud LTS ListLogGroups --cli-region={region} --project_id={project_id}

# List log streams under a group
hcloud LTS ListLogStreams --cli-region={region} --project_id={project_id} \
  --log_group_name={log_group_name}

# Query index configuration for a log stream
hcloud LTS ListLogStreamIndex --cli-region={region} --project_id={project_id} \
  --group_id={group_id} --stream_id={stream_id}
```

### Query — Transfer Tasks

```bash
# List all transfer tasks
hcloud LTS ListTransfers --cli-region={region} --project_id={project_id}

# Filter by transfer type (OBS/DIS/DMS)
hcloud LTS ListTransfers --cli-region={region} --project_id={project_id} \
  --log_transfer_type=OBS
```

### Query — Alarm Rules & History

```bash
# List keyword alarm rules
hcloud LTS ListKeywordsAlarmRules --cli-region={region} --project_id={project_id}

# List SQL alarm rules
hcloud LTS ListSqlAlarmRules --cli-region={region} --project_id={project_id}

# Query active or history alarms (type: active_alert/history_alert)
# --whether_custom_field=false requires --time_range (minutes); true requires --start_time/--end_time (ms)
hcloud LTS ListActiveOrHistoryAlarms --cli-region={region} --project_id={project_id} \
  --domain_id={domain_id} --type=history_alert --whether_custom_field=false --time_range=30 --limit=10
```

### Query — Log Search (Diagnose)

```bash
# Search logs by keyword and time range
hcloud LTS ListLogs --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_id={log_stream_id} \
  --start_time={start_time} --end_time={end_time} \
  --keywords="ERROR" --limit=50 --is_desc=true --highlight=true

# Get log context around a specific line (for fault diagnosis)
hcloud LTS ListLogContext --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_id={log_stream_id} \
  --__time__={timestamp} --line_num={line_num} \
  --backwards_size=10 --forwards_size=10

# Get log distribution histogram (for trend analysis)
hcloud LTS ListLogHistogram --cli-region={region} --project_id={project_id} \
  --group_id={group_id} --stream_id={stream_id} \
  --start_time={start_time} --end_time={end_time} \
  --key_word="ERROR" --step_interval=3600000

# Query structured logs with SQL expression (requires the log stream to have a struct config)
# Supported SQL: GROUP BY / LIKE / WHERE
hcloud LTS ListQueryStructuredLogs --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_id={log_stream_id} \
  --start_time={start_time} --end_time={end_time} \
  --sql_expression="select * where level like '%ERROR%'"
```

### Create — Log Groups & Streams

```bash
# Create a log group with TTL (days)
hcloud LTS CreateLogGroup --cli-region={region} --project_id={project_id} \
  --log_group_name="my-log-group" --ttl_in_days=30

# Create a log stream under a group
hcloud LTS CreateLogStream --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_name="my-log-stream" --ttl_in_days=30
```

### Create — Index

```bash
# Create full-text index for a log stream
hcloud LTS CreateLogStreamIndex --cli-region={region} --project_id={project_id} \
  --group_id={group_id} --stream_id={stream_id} --logStreamId={stream_id} \
  --fullTextIndex.enable=true --fullTextIndex.caseSensitive=false \
  --fullTextIndex.includeChinese=true --fullTextIndex.tokenizer=" "
```

### Create — Transfer Task (to OBS)

```bash
# Create a transfer task to OBS bucket
hcloud LTS CreateTransfer --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} \
  --log_streams.1.log_stream_id={stream_id} --log_streams.1.log_stream_name={stream_name} \
  --log_transfer_info.log_transfer_type=OBS \
  --log_transfer_info.log_transfer_mode=cycle \
  --log_transfer_info.log_storage_format=RAW \
  --log_transfer_info.log_transfer_status=ENABLE \
  --log_transfer_info.log_transfer_detail.obs_bucket_name={bucket_name} \
  --log_transfer_info.log_transfer_detail.obs_period=5 \
  --log_transfer_info.log_transfer_detail.obs_period_unit=min
```

### Create — Alarm Rules

```bash
# Create a keyword alarm rule
hcloud LTS CreateKeywordsAlarmRule --cli-region={region} --project_id={project_id} \
  --domain_id={domain_id} \
  --keywords_alarm_rule_name="error-alarm" \
  --keywords_alarm_level=Critical \
  --keywords_requests.1.log_group_id={group_id} \
  --keywords_requests.1.log_stream_id={stream_id} \
  --keywords_requests.1.keywords="ERROR" \
  --keywords_requests.1.condition=">=" --keywords_requests.1.number=1 \
  --keywords_requests.1.search_time_range=5 --keywords_requests.1.search_time_range_unit=minute \
  --frequency.type=CRON --frequency.cron_expr="0 */5 * * * *" --notification_frequency=5

# Create a SQL alarm rule (requires sql_requests.[N].search_time_range)
hcloud LTS CreateSqlAlarmRule --cli-region={region} --project_id={project_id} \
  --domain_id={domain_id} \
  --sql_alarm_rule_name="sql-error-alarm" \
  --sql_alarm_level=Major \
  --sql_requests.1.log_group_id={group_id} \
  --sql_requests.1.log_stream_id={stream_id} \
  --sql_requests.1.sql="select count(*) where level='ERROR'" \
  --sql_requests.1.search_time_range=5 --sql_requests.1.search_time_range_unit=minute \
  --condition_expression=">=1" \
  --frequency.type=CRON --frequency.cron_expr="0 */5 * * * *" --notification_frequency=5
```

### Update — TTL & Config

```bash
# Update log group TTL (save duration)
hcloud LTS UpdateLogGroup --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --ttl_in_days=60

# Update log stream TTL and storage
hcloud LTS UpdateLogStream --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_id={log_stream_id} \
  --ttl_in_days=60 --whether_log_storage=true

# Update transfer task config
hcloud LTS UpdateTransfer --cli-region={region} --project_id={project_id} \
  --log_transfer_id={transfer_id} \
  --log_transfer_info.log_storage_format=RAW \
  --log_transfer_info.log_transfer_status=ENABLE \
  --log_transfer_info.log_transfer_detail.obs_bucket_name={bucket_name} \
  --log_transfer_info.log_transfer_detail.obs_period=5 \
  --log_transfer_info.log_transfer_detail.obs_period_unit=min

# Enable/disable an alarm rule (status: RUNNING/STOPPING; type: keywords/sql)
hcloud LTS UpdateAlarmRuleStatus --cli-region={region} --project_id={project_id} \
  --alarm_rule_id={alarm_rule_id} --status=STOPPING --type=keywords
```

### Delete — ⚠️ Requires Confirmation

> **CRITICAL**: All Delete operations require explicit user confirmation before execution.
> Batch deletion of all LTS resources is **prohibited**. Each delete must specify a single resource ID.

```bash
# Delete a log group (⚠️ cascades all log streams under it)
hcloud LTS DeleteLogGroup --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id}

# Delete a log stream
hcloud LTS DeleteLogStream --cli-region={region} --project_id={project_id} \
  --log_group_id={log_group_id} --log_stream_id={log_stream_id}

# Delete a transfer task
hcloud LTS DeleteTransfer --cli-region={region} --project_id={project_id} \
  --log_transfer_id={transfer_id}

# Delete a keyword alarm rule
hcloud LTS DeleteKeywordsAlarmRule --cli-region={region} --project_id={project_id} \
  --keywords_alarm_rule_id={alarm_rule_id}

# Delete a SQL alarm rule
hcloud LTS DeleteSqlAlarmRule --cli-region={region} --project_id={project_id} \
  --sql_alarm_rule_id={alarm_rule_id}
```

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Target region | `{your-region}` |
| `--project_id` | Yes | Project ID | Obtained from IAM console |
| `--log_group_id` | For stream/index/transfer ops | Log group ID | `xxx-xxx-xxx` |
| `--log_stream_id` | For index/log search ops | Log stream ID | `xxx-xxx-xxx` |
| `--ttl_in_days` | For create/update group/stream | Log retention in days | `30`, `60`, `365` |
| `--keywords` | For log search | Search keywords | `"ERROR"`, `"Exception"` |
| `--start_time` / `--end_time` | For log search | Time range (ms) | `1700000000000` |
| `--log_transfer_type` | For transfer filter | Transfer type | `OBS`, `DIS`, `DMS` |

### Delete Safety Rules

1. **Single resource deletion only** — each Delete call must specify exactly one resource ID
2. **No wildcard/batch delete** — `DeleteLogGroup` deletes all streams under the group; always confirm the cascade impact
3. **User must explicitly confirm** — reply "确认" / "confirm" / "ok" before any Delete execution
4. **Prohibited**: deleting all log groups or all alarm rules in a single session without individual confirmation

## Reference Documents

- [IAM Policies](references/iam-policies.md) — Least-privilege IAM policy for LTS
- [CLI Installation Guide](references/cli-installation-guide.md) — hcloud CLI setup
- [Verification Method](references/verification-method.md) — How to verify the skill
- [Data Flow Diagram](references/dataflow-diagram.md) — Data flow through the skill
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [LTS Alarm Reference](references/lts-alarm-reference.md) — Alarm rule configuration reference

## KooCLI Command Format Standard

```bash
hcloud LTS ListLogGroups --cli-region={your-region} [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `LTS` (uppercase) | `hcloud LTS ListLogGroups` |
| Operation name | PascalCase | `ListLogGroups`, `CreateTransfer`, `DeleteLogStream` |
| Region parameter | `--cli-region=<value>` | `--cli-region={your-region}` |
| Simple parameter | `--key=value` | `--log_group_name=my-group` |
| Indexed parameter | `--key.1=value` | `--keywords_requests.1.keywords=ERROR` |
