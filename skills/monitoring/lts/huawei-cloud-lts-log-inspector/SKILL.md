---
name: huawei-cloud-lts-log-inspector
description: >
  Huawei Cloud LTS (Log Tank Service) log traffic statistics, log context query,
  host group and access config inspection, collection status patrol, and OBS transfer
  management for batch log export. Covers log histogram query, TOP-N traffic statistics,
  timeline traffic statistics, single-log context retrieval, host group listing,
  access config query, host collection status inspection, OBS transfer create/list/delete,
  and diagnostic workflows for traffic surge, collection break, and log flooding.
  Triggers include: 日志流量异常排查, 日志采集故障巡检, 故障深度定位, 日志批量导出,
  LTS流量统计, 日志上下文查询, 采集断流, 日志刷屏, log traffic anomaly,
  collection inspection, log context, LTS patrol, log flooding diagnose,
  offline log export, OBS transfer.
tags: [huawei-cloud lts log traffic inspection diagnostic]
---

# Huawei Cloud LTS Log Traffic and Collection Inspector

## Overview

This Skill provides a comprehensive toolkit for Huawei Cloud LTS (Log Tank Service)
log traffic analysis, collection health inspection, and batch log export management.
It is designed for four primary scenarios:

1. **Log traffic anomaly troubleshooting** - When log traffic surges, use TOP-N statistics
   to identify which log stream is flooding.
2. **Fault deep-dive positioning** - Given an abnormal log ID, automatically pull before/after
   context log stacks to reconstruct the fault scene.
3. **Collection fault patrol** - Check host group collection reporting status to locate
   collection breakage.
4. **Batch log export** - Create OBS transfer tasks to export large volumes of historical
   logs to an OBS bucket for download.

### Architecture

```
User Trigger -> Skill Workflow -> hcloud CLI LTS Commands -> Structured Output
                                    |-- Traffic Stats (Histogram / TOP-N / Timeline)
                                    |-- Log Context Query
                                    |-- Collection Inspection (HostGroup / Host / AccessConfig)
                                    |-- OBS Transfer (Create / List / Delete)
                                    +-- Diagnostic Report (Aggregated)
```

### Important Limitations

| Feature | Status | Explanation |
|---------|--------|-------------|
| Consumer group query (F8) | Unavailable | LTS consumer group is in invitation-only beta; only Java/Go SDK, no REST API or CLI |
| Consumer group cursor update (F11) | Unavailable | Same as above |
| Offline download task (F9/F10/F12) | Alternative | LTS console offline download is whitelist-only with no public API. OBS transfer (CreateTransfer) is used as the alternative. |

### Constraints

- Creating an OBS transfer task **must output a traffic and storage cost risk warning** before execution.
- **Bulk export of all logs is prohibited** - always specify a log group and stream scope.
- This Skill **does not modify** log group/stream TTL, index configurations, or alarm rules.
- This Skill **does not create or delete** log groups or log streams.
- Context log queries return **concise fragments** (default 100 lines before/after, max 500)
  to avoid oversized text output.

## Prerequisites

1. **hcloud CLI** installed and authenticated with a valid AK/SK profile.
   - Installation guide: see `references/cli-installation-guide.md`
   - Verify: `hcloud configure list` shows a valid profile
2. **IAM permissions**: LTS read permissions for query operations; LTS transfer write
   permissions for OBS transfer create/delete. See `references/iam-policies.md`.
3. **Region**: LTS must be available in the target region (e.g., `cn-north-4`).
4. **OBS bucket** (for transfer only): A pre-existing OBS bucket is required when creating
   an OBS transfer task.

## Workflow

### Scenario 1: Log Traffic Anomaly Troubleshooting

```
1. ListTopnTrafficStatistics -> Identify TOP-N log streams by write traffic (descending)
2. ListTimeLineTrafficStatistics -> Check traffic trend over the time window
3. ListLogHistogram -> Drill down into the suspect log stream histogram
4. Output: Structured traffic anomaly report
```

### Scenario 2: Fault Deep-Dive Positioning

```
1. ListLogs -> Search for the target log by keyword/time range to get line_num
2. ListLogContext -> Pull context logs (before/after) using line_num
3. Output: Concise context log fragments (max 500 lines each direction)
```

### Scenario 3: Collection Fault Patrol

```
1. ListHostGroup -> List all host groups
2. ListHost --filter.host_status=offline -> Find offline hosts
3. ListHost --filter.host_status=error -> Find error-state hosts
4. ListAccessConfig -> Check collection configs for affected hosts
5. Output: Collection anomaly checklist
```

### Scenario 4: Batch Log Export (via OBS Transfer)

```
1. [Cost risk warning displayed to user]
2. User confirms
3. CreateTransfer -> Create OBS transfer task (log group + stream -> OBS bucket)
4. ListTransfers -> Monitor transfer status
5. User downloads logs from OBS bucket
6. (Optional) DeleteTransfer -> Clean up transfer after download
```

## Core Commands

### 1. Log Traffic Statistics

#### 1.1 Query Log Histogram

```bash
hcloud LTS ListLogHistogram --cli-region={region} \
  --group_id={log_group_id} \
  --stream_id={log_stream_id} \
  --start_time={start_time} \
  --end_time={end_time} \
  --key_word={keyword} \
  --step_interval={step_interval}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--group_id` | Yes | Log group ID |
| `--stream_id` | Yes | Log stream ID |
| `--start_time` | Yes | Start time |
| `--end_time` | Yes | End time |
| `--key_word` | Yes | Search keyword |
| `--step_interval` | Yes | Step interval (integer) |

#### 1.2 Query TOP-N Traffic Statistics

```bash
hcloud LTS ListTopnTrafficStatistics --cli-region={region} \
  --resource_type=log_stream \
  --topn=10 \
  --start_time={start_timestamp_ms} \
  --end_time={end_timestamp_ms} \
  --search_list.1=write \
  --sort_by=write \
  --is_desc=true \
  --filter.log_group_id={log_group_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--resource_type` | Yes | `log_group`, `log_stream`, or `tenant` |
| `--topn` | Yes | Top N, range 1-100 |
| `--start_time` | Yes | Start timestamp (ms), max 30-day range |
| `--end_time` | Yes | End timestamp (ms) |
| `--search_list.1` | Yes | Data type: `index`/`write`/`storage`/`basicTransfer`/`seniorTransfer`/`coldStorage` |
| `--sort_by` | Yes | Sort field, must be in search_list |
| `--is_desc` | Yes | Descending order: `true`/`false` |
| `--filter.{key}` | Yes | Filter conditions (map), e.g., `--filter.log_group_id=xxx` |

#### 1.3 Query Timeline Traffic Statistics

```bash
hcloud LTS ListTimeLineTrafficStatistics --cli-region={region} \
  --resource_type=log_stream \
  --search_type=write \
  --start_time={start_timestamp_ms} \
  --end_time={end_timestamp_ms} \
  --period=1 \
  --timezone=Asia/Shanghai \
  --resource_id={resource_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--resource_type` | Yes | `log_group`, `log_stream`, or `tenant` |
| `--search_type` | Yes | `write`/`index`/`storage`/`basicTransfer`/`seniorTransfer` |
| `--start_time` | Yes | Start timestamp (ms), max 30-day range |
| `--end_time` | Yes | End timestamp (ms) |
| `--period` | Yes | Time interval in hours, range 1-24 |
| `--timezone` | Yes | Timezone string |
| `--resource_id` | No | Specific resource ID for filtering |

### 2. Log Context Query

#### 2.1 Query Log Content

```bash
hcloud LTS ListLogs --cli-region={region} \
  --log_group_id={log_group_id} \
  --log_stream_id={log_stream_id} \
  --start_time={start_time_ms} \
  --end_time={end_time_ms} \
  --keywords={keyword} \
  --limit=100 \
  --is_desc=true
```

#### 2.2 Query Log Context (Before/After)

```bash
hcloud LTS ListLogContext --cli-region={region} \
  --log_group_id={log_group_id} \
  --log_stream_id={log_stream_id} \
  --line_num={line_num} \
  --backwards_size=100 \
  --forwards_size=100
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--log_group_id` | Yes | Log group ID |
| `--log_stream_id` | Yes | Log stream ID |
| `--line_num` | No | Log line sequence number (nanosecond timestamp), from ListLogs result |
| `--backwards_size` | No | Lines before (context above), range [0, 500], default 100 |
| `--forwards_size` | No | Lines after (context below), range [0, 500], default 100 |
| `--scroll_id` | No | Pagination scroll ID from previous query |

> **Note**: To get `line_num`, first call `ListLogs` to search for the target log,
> then use the returned `line_num` value in `ListLogContext`.

### 3. Collection Inspection

#### 3.1 List Host Groups

```bash
hcloud LTS ListHostGroup --cli-region={region} \
  --filter.host_group_type=linux
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--filter.host_group_type` | No | `windows` or `linux` |
| `--filter.host_group_name_list.1` | No | Host group name filter |
| `--host_group_id_list.1` | No | Host group ID filter |

#### 3.2 List Hosts (Collection Status)

```bash
hcloud LTS ListHost --cli-region={region} \
  --filter.host_status=offline
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--filter.host_status` | No | Host status: `uninstall`, `running`, `offline`, `error`, `plugin error`, `installing`, `install-fail`, `upgrading`, `upgrade-fail`, `uninstalling`, `authentication error` |
| `--filter.host_name_list.1` | No | Host name filter |
| `--filter.host_ip_list.1` | No | Host IP filter |
| `--host_id_list.1` | No | Host ID filter |

> **Collection status meanings**:
> - `running` - Agent running normally, logs being collected
> - `offline` - Host offline, **collection broken**
> - `error` / `plugin error` - Agent error, **collection may be broken**
> - `uninstall` - Agent not installed
> - `authentication error` - Auth failure, **collection broken**

#### 3.3 List Access Configs (Collection Configs)

```bash
hcloud LTS ListAccessConfig --cli-region={region} \
  --access_config_name_list.1={config_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--access_config_name_list.1` | No | Access config name filter |
| `--host_group_name_list.1` | No | Host group name filter |
| `--log_group_name_list.1` | No | Log group name filter |
| `--log_stream_name_list.1` | No | Log stream name filter |

### 4. OBS Transfer (Batch Log Export Alternative)

> **Cost Risk Warning**: Creating an OBS transfer task will incur OBS storage costs
> and LTS transfer fees based on the actual log transfer volume. Always confirm with
> the user before creating a transfer task.

#### 4.1 Create OBS Transfer

```bash
hcloud LTS CreateTransfer --cli-region={region} \
  --log_group_id={log_group_id} \
  --log_streams.1.log_stream_id={log_stream_id} \
  --log_transfer_info.log_transfer_type=OBS \
  --log_transfer_info.log_transfer_mode=cycle \
  --log_transfer_info.log_transfer_status=ENABLE \
  --log_transfer_info.log_storage_format=RAW \
  --log_transfer_info.log_transfer_detail.obs_bucket_name={obs_bucket} \
  --log_transfer_info.log_transfer_detail.obs_period=5 \
  --log_transfer_info.log_transfer_detail.obs_period_unit=min
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--log_group_id` | Yes | Source log group ID |
| `--log_streams.1.log_stream_id` | Yes | Source log stream ID |
| `--log_transfer_info.log_transfer_type` | Yes | `OBS`, `DIS`, or `DMS` |
| `--log_transfer_info.log_transfer_mode` | Yes | `cycle` (periodic) or `realTime` |
| `--log_transfer_info.log_transfer_status` | Yes | `ENABLE`, `DISABLE`, or `EXCEPTION` |
| `--log_transfer_info.log_storage_format` | Yes | `RAW` or `JSON` |
| `--log_transfer_info.log_transfer_detail.obs_bucket_name` | Yes | Target OBS bucket name |
| `--log_transfer_info.log_transfer_detail.obs_period` | Yes | Transfer period: 1,2,3,5,6,12,30 |
| `--log_transfer_info.log_transfer_detail.obs_period_unit` | Yes | `min` or `hour` |

#### 4.2 List Transfers

```bash
hcloud LTS ListTransfers --cli-region={region} \
  --log_transfer_type=OBS
```

#### 4.3 Delete Transfer

```bash
hcloud LTS DeleteTransfer --cli-region={region} \
  --log_transfer_id={transfer_id}
```

### 5. Diagnostic Workflows

#### 5.1 Diagnose Traffic Surge

```bash
# Step 1: TOP-N by write traffic (descending)
hcloud LTS ListTopnTrafficStatistics --cli-region={region} \
  --resource_type=log_stream --topn=10 \
  --start_time={start_ms} --end_time={end_ms} \
  --search_list.1=write --sort_by=write --is_desc=true

# Step 2: Timeline trend for the top log stream
hcloud LTS ListTimeLineTrafficStatistics --cli-region={region} \
  --resource_type=log_stream --search_type=write \
  --start_time={start_ms} --end_time={end_ms} \
  --period=1 --timezone=Asia/Shanghai \
  --resource_id={top_stream_id}
```

#### 5.2 Diagnose Collection Break

```bash
# Step 1: Find offline hosts
hcloud LTS ListHost --cli-region={region} --filter.host_status=offline

# Step 2: Find error-state hosts
hcloud LTS ListHost --cli-region={region} --filter.host_status=error

# Step 3: Check access configs
hcloud LTS ListAccessConfig --cli-region={region}
```

#### 5.3 Diagnose Log Flooding

```bash
# TOP-N by write traffic descending to find flooding log stream
hcloud LTS ListTopnTrafficStatistics --cli-region={region} \
  --resource_type=log_stream --topn=5 \
  --start_time={start_ms} --end_time={end_ms} \
  --search_list.1=write --sort_by=write --is_desc=true
```

### 6. Full Patrol Report

The full patrol report aggregates all inspection results:

```bash
# 1. TOP-N traffic
hcloud LTS ListTopnTrafficStatistics --cli-region={region} \
  --resource_type=log_stream --topn=10 \
  --start_time={start_ms} --end_time={end_ms} \
  --search_list.1=write --sort_by=write --is_desc=true

# 2. Timeline traffic
hcloud LTS ListTimeLineTrafficStatistics --cli-region={region} \
  --resource_type=tenant --search_type=write \
  --start_time={start_ms} --end_time={end_ms} \
  --period=1 --timezone=Asia/Shanghai

# 3. Host groups
hcloud LTS ListHostGroup --cli-region={region}

# 4. Abnormal hosts
hcloud LTS ListHost --cli-region={region} --filter.host_status=offline
hcloud LTS ListHost --cli-region={region} --filter.host_status=error

# 5. Access configs
hcloud LTS ListAccessConfig --cli-region={region}
```

Output a structured report with:
- Traffic statistics briefing (TOP-N + timeline)
- Collection anomaly checklist (offline/error hosts + affected configs)

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{region}` | Yes | Huawei Cloud region | `cn-north-4` |
| `{log_group_id}` | Yes | LTS log group ID | `xxxx-xxxx-xxxx` |
| `{log_stream_id}` | Yes | LTS log stream ID | `xxxx-xxxx-xxxx` |
| `{start_time}` / `{end_time}` | Yes | Time range (format depends on command) | `1704067200000` (ms timestamp) |
| `{topn}` | No | TOP-N count, range 1-100 | `10` |
| `{line_num}` | Yes (context) | Log line sequence number | from ListLogs result |
| `{obs_bucket}` | Yes (transfer) | Target OBS bucket name | `my-log-backup` |
| `{keyword}` | No | Search keyword for log query | `error` |

## KooCLI Command Format Standard

```bash
hcloud LTS <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `LTS` (uppercase) | `hcloud LTS ListHostGroup` |
| Operation name | PascalCase | `ListTopnTrafficStatistics` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--topn=10` |
| Indexed parameter | `--key.1=value1` | `--search_list.1=write` |

## Reference Documents

- `references/cli-installation-guide.md` - hcloud CLI installation and configuration
- `references/iam-policies.md` - Least-privilege IAM policies for LTS
- `references/verification-method.md` - Verification and testing methods
- `references/dataflow-diagram.md` - Mermaid data flow diagram
- `references/acceptance-criteria.md` - Acceptance criteria
- `references/lts-api-reference.md` - LTS API command quick reference
