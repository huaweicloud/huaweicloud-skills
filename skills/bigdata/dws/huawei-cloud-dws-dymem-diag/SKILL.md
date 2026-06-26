---
name: huawei-cloud-dws-mem-diag
description: |
  DWS cluster memory high root cause diagnosis skill, based on KooCLI v3.2.0+ and DWS Autopilot MCP Server.
  Automatically collects memory metrics, analyzes root causes (customer-side / system-side), and outputs a standardized diagnosis report.
  Applicable to DWS cluster memory usage too high, memory alarms, OOM scenarios.
  Trigger words: "内存高", "内存告警", "内存诊断", "内存使用率过高", "内存不足", "OOM", "内存溢出", "动态内存使用率超阈值", "high memory", "memory alarm", "memory diagnosis"
tags: [huawei-cloud, dws, memory, diagnostics, autopilot]

# ============================================================
# Internal extension fields
# ============================================================
trigger:
  keywords: ["DWS", "内存高", "内存告警", "内存不足", "内存使用率", "内存诊断", "OOM", "内存溢出", "内存使用率过高", "DWS集群节点动态内存使用率超阈值", "动态内存使用率超阈值", "动态内存使用率", "high memory", "memory alarm", "insufficient memory", "memory usage", "memory diagnosis", "OOM", "memory overflow", "high memory usage", "dynamic memory usage exceeds threshold"]
  resource_types: ["DWS::instance_id"]
  hypotheses: ["memory_high", "memory_warning", "memory_oom"]

input_schema:
  required:
    - name: "alarm_serial_number"
      type: "string"
      description: "Alarm serial number"
    - name: "project_id"
      type: "string"
      description: "Project ID, used as the project_id parameter for tool calls"
    - name: "cluster_id"
      type: "string"
      description: "Cluster unique ID (instance ID), corresponding to the alarm resourceId"
    - name: "first_alarm_time"
      type: "integer"
      description: "First alarm time, Unix millisecond timestamp (UTC timezone), used directly for tool from_ts/to parameters"
    - name: "alarm_name"
      type: "string"
      description: "Alarm name"
  optional:
    - name: "region_id"
      type: "string"
      description: "Region identifier, used for hcloud --cli-region parameter"
    - name: "node_name"
      type: "string"
      description: "Alert node name (extracted from alarm additionalInformation host_name; empty for cluster-level alarms)"
    - name: "instance_name"
      type: "string"
      description: "Instance name (extracted from alarm moi field instance_name=xxx; may be empty)"
    - name: "cluster_name"
      type: "string"
      description: "Cluster name"
    - name: "alarm_severity"
      type: "integer"
      description: "Alarm severity (1=Critical, 2=Major, 3=Minor, 4=Info)"

output_schema:
  - name: "diagnosis_summary"
    type: "string"
    description: "Diagnosis result summary"
  - name: "diagnosis_report"
    type: "string"
    description: "Diagnosis report in HTML format"

allowed-tools:
  - dws_autopilot_get_clusters
  - dws_autopilot_get_metric
  - dws_autopilot_get_hosts
---

# Huawei Cloud DWS Memory High Diagnosis Skill

## Overview

This skill is dedicated to DWS cluster memory high root cause diagnosis. When a cluster triggers a memory usage too high alarm, it automatically collects metric data, analyzes root causes (customer-side / system-side), and outputs a standardized diagnosis report.

**Architecture**: KooCLI (hcloud) → DWS Autopilot API → Cluster monitoring metrics; MCP Server (dws_autopilot) → Fallback channel for the same API

**Applicable Scenarios**:
- DWS cluster memory usage too high alarm
- Memory insufficient / OOM investigation
- User-initiated memory diagnosis request

**Typical Use Cases**:
- "My DWS cluster memory usage is very high, help diagnose"
- "Received a memory alarm, cluster ID is xxx, help analyze the cause"
- "DWS cluster has OOM, see what's causing it"

**Important Rules**: All diagnosis conclusions must come from actual tool return results. Fabricating or assuming values is prohibited. Output only contains the diagnosis report; adding remediation suggestions, outputting SQL optimization statements, and using emoji are prohibited.

**Background Knowledge**: Memory usage formulas, CN/DN instance distinction, memory_pool analysis, memory thresholds, and important principles are documented in [Memory Background Knowledge](references/memory-background.md). Must read before diagnosis.

## Prerequisites

### 1. CLI Requirements

- KooCLI (hcloud) >= 3.2.0
- Verify installation: `hcloud version`
- If not installed or version too low, see [CLI Installation Guide](references/cli-installation-guide.md)

### 2. MCP Server Configuration (Fallback)

- When KooCLI is unavailable, use MCP Server as an alternative
- See [MCP Installation Guide](references/dws-mcp-installation-guide.md)

### 3. Authentication Configuration

- Valid Huawei Cloud credentials (AK/SK mode or IAM Token)
- **Security Rules**:
  - Never expose AK/SK values in conversations or commands
  - Never ask users to input AK/SK directly in conversation
  - Only use `hcloud configure list` to check credential status

### 4. IAM Permission Requirements

- dws:clusters:get, dws:clusters:list
- dws:metricData:get, dws:hostOverview:get
- See [IAM Policies](references/iam-policies.md)

## KooCLI Command Format Standard

### Command Format

```bash
# Query metric data
hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=<name> --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>

# Query host information
hcloud DWS ListHostOverview --cli-region=<region> --project_id=<pid> --offset=0 --limit=200
```

### Tool Selection Strategy

Choose between KooCLI and MCP Server, preferring KooCLI. Step 0 checks hcloud availability:
- hcloud available (version >= 3.2.0) → Use KooCLI command line calls for subsequent steps
- hcloud unavailable (not installed or version < 3.2.0) → Use MCP Server tool calls for subsequent steps

**Fallback and Termination Strategy**:
- After selecting hcloud, if the first call returns `NETWORK_ERROR` (connection timeout, network unreachable, etc.), automatically fall back to MCP Server and use MCP mode for all subsequent steps
- If hcloud returns NETWORK_ERROR and MCP Server is also unavailable (not configured or returns authentication/connection error), terminate this skill and output: `KooCLI network unavailable and MCP Server connection failed. Please check KooCLI network configuration or DWS Autopilot MCP Server configuration and retry`
- After selecting MCP Server, if the first call returns an authentication error (e.g., 401 Unauthorized), do not fall back to hcloud. Terminate this skill directly and output: `MCP Server authentication failed. Please check DWS Autopilot MCP Server authentication configuration and retry`
- hcloud call failures that are not NETWORK_ERROR (e.g., parameter errors, insufficient permissions) do not trigger fallback; follow existing retry logic

Once a tool is selected, use it throughout without switching (except for NETWORK_ERROR fallback). If a call fails, retry once (maximum 2 attempts). If still failing, mark the metric as "unavailable" and continue to the next step. When all metric queries fail, generate the diagnosis report directly.

### Parameter Mapping

| Common Parameter | hcloud Parameter | MCP Parameter |
|------------------|------------------|---------------|
| Region | --cli-region | (built into MCP connection) |
| Project ID | --project_id | project_id |
| Cluster ID | --cluster_id | cluster_id |
| Metric Name | --metric_name | metric_name |
| Start Time | --from | from_ts |
| End Time | --to | to_ts |
| Pagination Offset | --offset | offset |
| Pagination Limit | --limit | limit |
| Sort Field | (not supported) | order_by |
| Sort Direction | (not supported) | sort_by |

### MCP Tools

| Tool Name | Purpose | Key Parameters |
|-----------|---------|----------------|
| `dws_autopilot_get_clusters` | Query cluster list | project_id, cluster_id, limit, offset |
| `dws_autopilot_get_hosts` | Query host information | project_id, cluster_id, limit, offset |
| `dws_autopilot_get_metric` | Query metric data | project_id, cluster_id, metric_name, from_ts, to_ts, limit, offset, order_by, sort_by |

**metric_data Parameter Notes**: metric_data does not support filtering by instance_name (no such parameter); query returns full cluster data and must be filtered by inst_name field for target instances; metric_data does not support period parameter (sampling period is automatically determined by the platform).

**Available metric_name**: `MemStat`, `InstanceMemory`, `memory_diagnose_detail`

**Time Protocol**: from_ts/to_ts must use Unix millisecond timestamps; all times are in UTC timezone; recommended time window: from 20 minutes before alarm time to alarm time (from_ts = first_alarm_time - 1200000).

**Return Format**: Success `{"code": 0, "data": [...]}`; Failure `{"code": -1, "message": "error description"}`. On failure, retry once; if still failing, use degradation path and mark as "unavailable" in the report.

**Key Fields per Metric**:
- **MemStat**: ctime, host_id, mem_total, mem_free, mem_available, cached, buffers, swap_total, swap_free, watermark_high, watermark_min → memory usage = (mem_total - mem_free - cached - buffers) / mem_total * 100%
- **InstanceMemory**: ctime, host_id, inst_name, dynamic_used_memory, max_dynamic_memory, dynamic_peak_memory, process_used_memory, max_process_memory, shared_used_memory, max_shared_memory, comm_used_memory, max_comm_memory, cstore_used_memory, max_cstore_memory, topsql_used_memory, max_topsql_memory, other_used_memory, udf_reserved_memory, mmap_used_memory, storage_compress_memory, pooler_conn_memory, pooler_freeconn_memory → dynamic memory usage = (dynamic_used_memory / max_dynamic_memory) * 100%; process memory usage = (process_used_memory / max_process_memory) * 100%
- **memory_diagnose_detail**: ctime, host_id, instance_name, active_sessions[{query, query_id, userName, mem_used, state, duration_ms, plan_type}], memory_pool{work_mem_used/total, shared_pool_used/total}

For query differences per step, see [Metric Reference](references/metric-reference.md).

### Pagination Specification

**All tool calls (MCP and hcloud) must use paginated queries** to prevent single responses from being too large and exceeding token limits.

**Pagination Rules**:
- Use `limit=200` uniformly (do not use 800 or other large values)
- First page `offset=0`; if returned data count = 200, then `offset+=200` and continue querying
- Repeat until returned data count < 200, then merge all paginated data
- When merging, concatenate all page data arrays into a complete dataset

**MCP Call Example** (using MemStat):
```
Page 1: dws_autopilot_get_metric(project_id, cluster_id, metric_name="MemStat", from_ts, to_ts, limit=200, offset=0)
If returned data length = 200:
Page 2: dws_autopilot_get_metric(project_id, cluster_id, metric_name="MemStat", from_ts, to_ts, limit=200, offset=200)
If returned data length < 200: Stop pagination, merge page 1 + page 2 data
```

**hcloud Call Example** (using MemStat):
```
Page 1: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=MemStat --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>
If returned data count = 200:
Page 2: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=MemStat --project_id=<pid> --offset=200 --limit=200 --from=<from_ts> --to=<to_ts>
If returned data count < 200: Stop pagination, merge data
```

## Workflow

Before diagnosis, create an execution plan based on Steps 0-7, then execute sequentially. For tool selection strategy, see the "KooCLI Command Format Standard" section; subsequent steps will not repeat this. All MCP tool calls follow the "Pagination Specification" section; subsequent steps will not repeat pagination details.

### Step 0: Environment Detection

Execute `hcloud version`; version >= 3.2.0 → tool_mode=hcloud, otherwise tool_mode=mcp.

**hcloud Network Availability Probe**: If tool_mode=hcloud, execute a lightweight API call (e.g., `hcloud DWS ListClusters --cli-region=<region> --project_id=<project_id> --offset=0 --limit=1`) to verify network connectivity:
- Returns normal or business error (e.g., insufficient permissions, parameter error) → Network available, keep tool_mode=hcloud
- Returns NETWORK_ERROR → Network unavailable, fall back to tool_mode=mcp
- After fallback, if MCP is also unavailable → Terminate execution, prompt user to check KooCLI network configuration or MCP Server configuration

### Step 1: Query MemStat

Call metric query with metric_name="MemStat", time window: from_ts=`first_alarm_time - 1200000`, to_ts=`first_alarm_time`. In MCP mode, use limit=200 paginated query.

**Autopilot Unavailable Determination**: Returns 50201/RDS.9999 error → Skip Steps 1-6, mark all metrics as "unavailable", proceed directly to Step 7.

**Parsing**: Group by host_id, find the latest memory data for each node. Memory usage = (mem_total - mem_free - cached - buffers) / mem_total * 100%. Determine if too high (> 80%), globally high (all > 70%), imbalanced (deviation > 30%). Find the two nodes with highest memory and TOP3.

**Node Scope Classification** (based on high_mem_nodes count):
- All nodes memory high: Most nodes have high memory (reference: high memory node ratio >= 80%) → Tends toward business-side causes (high concurrency, complex SQL)
- Single node memory high: High memory node count = 1 → Tends toward data skew, connection skew, abnormal process
- Partial nodes memory high: 1 < high memory node count < most nodes → Tends toward new/old node differences, head DN skew, local data skew

**Output**: mem_by_host, max_mem_hosts, problem_host_id, problem_host_mem_usage, problem_host_used, problem_host_total, problem_host_available, top3_mem_nodes, cluster_avg_mem, is_imbalanced, is_global_high, mem_deviation, high_mem_nodes, mem_scope

### Step 2: Get Host Names

Call host information query (MCP mode limit=200 paginated), build host_id → {host_name, ip} mapping table. Only query host information for nodes involved in max_mem_hosts from Step 1 output.

**Output**: host_id_to_info_map, problem_host_ip, node_name

### Step 3: Query InstanceMemory

Call metric query with metric_name="InstanceMemory", time window same as Step 1. In MCP mode, use limit=200 paginated query. **Note: metric_data does not support filtering by instance_name; query returns full cluster data, must filter by inst_name field for target instances.**

**Parsing**: Extract memory usage for each instance (CN/DN). Dynamic memory usage = (dynamic_used_memory / max_dynamic_memory) * 100%; Process memory usage = (process_used_memory / max_process_memory) * 100%. Find instances with highest memory usage.

**CN/DN Instance Distinction** (based on inst_name field, InstanceMemory has no instance_type field):
- inst_name contains "cn" or "coordinator" → CN instance
- inst_name contains "dn" or "datanode" → DN instance
- CN instance memory high → Focus on connection skew, non-pushdown SQL, parsing pressure
- DN instance memory high → Focus on data skew, computation skew, sort/hash spill

**Memory Type Determination** (based on InstanceMemory dynamic memory vs process memory ratio):
- Dynamic memory proportion relatively high → **Dynamic memory high**, focus on business SQL, work_mem configuration
- Process memory proportion relatively high → **Process memory high**, focus on excessive connections, process leak

**Output**: instance_memory_data, high_memory_instances, instance_type_distribution, top3_dynamic_instances, inst_type, mem_type

### Step 4: Query Memory Diagnose Detail

Call metric query with metric_name="memory_diagnose_detail", time window same as Step 1. **Note: metric_data does not support filtering by instance_name; query returns full cluster data, must filter by max_mem_hosts from Step 1 output.** MCP mode must use limit=200 paginated query (this metric has the largest data volume), until returned count < 200, merge all paginated data before filtering.

**Parsing**: Extract active query statements, execution users (userName), memory usage, session information, SQL-level memory statistics.

**Time Annotation Rule**: ctime in memory_diagnose_detail is the Autopilot collection snapshot time, not the actual SQL start time. If active_sessions contains duration_ms field, SQL start time = ctime - duration_ms, annotated as "start time"; if duration_ms is unavailable, use ctime directly, annotated as "collection time" (do not annotate collection time as "start time").

**Active User Statistics Rule**: Only count users and connections with state=active; idle state not counted. Group by userName and aggregate memory usage to identify top users.

**Output**: user_memory_top5, session_memory_top5, sql_memory_top5, total_memory_by_users, total_memory_by_sqls, high_memory_sql_detected, high_memory_sql_info, high_freq_queries, heavy_queries, memory_pool_data, idle_session_with_high_mem

### Step 5: Analyze Diagnosis Results

Based on data collected in Steps 1-4, combined with user identity for memory high cause analysis.

**Diagnosis Priority**: Look at scope first, then find causes; business anomalies first, configuration and system last.

**Time Formatting**: All Unix millisecond timestamps (first_alarm_time, ctime, etc.) are in UTC timezone. In the report, they must be converted to Beijing time (UTC+8) string `YYYY-MM-DD HH:MM:SS`. Can use `python -c "from datetime import datetime,timezone,timedelta; print(datetime.fromtimestamp({ms}/1000,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'))"`. Do not mentally calculate timestamp values.

**User Identity Judgment** (based on database user, i.e., memory_diagnose_detail active_sessions userName):
- Database user is "omm" or "Ruby" → **System cause**
- Database user is not "omm" nor "Ruby" → **Customer-side cause**

**memory_pool Analysis** (from Step 4 memory_pool_data):
- work_mem usage rate = (work_mem_used / work_mem_total) * 100%, high work_mem indicates SQL sort/hash operations consuming large memory
- shared_pool usage rate = (shared_pool_used / shared_pool_total) * 100%, high shared_pool indicates shared cache pressure
- work_mem usage rate > 80% → Focus on SQL sort/hash spill, work_mem configuration too large
- shared_pool usage rate > 80% → Focus on shared table/index cache pressure, excessive connections

#### Customer-Side Causes

1. **Single SQL causing high memory**: Single SQL memory proportion prominent (reference: proportion > 20%), significant contributor to node memory high. **plan_type auxiliary judgment**: If plan_type is HashJoin/HashAggregate, hash operation is the main memory consumption cause
2. **Multi-user concurrent causing high memory**: Multiple users simultaneously consuming large amounts of memory
   - **concurrent_mode determination rule**: multi_user (multiple different database users with active queries, active user count >= 2); single_user (only one database user but many parallel queries, active user count = 1 and query count large); none (non-high concurrency scenario)
3. **Session leak or long transaction**: Session state is idle but holding large memory (from Step 4 idle_session_with_high_mem), or session running too long (duration_ms exceeds reference value 30 minutes) without memory release
4. **Data skew causing memory imbalance**: Inter-node deviation > 30%

**Note**: Single SQL and multi-user concurrent can both be matched simultaneously, each listed as an independent anomaly item, not mutually exclusive.

#### System Causes

1. **System internal tasks causing high memory**: omm/Ruby users consuming large amounts of memory
2. **Instance memory configuration unreasonable**: Instance memory usage persistently near limit (dynamic memory usage persistently > 80%), combined with memory_pool data to judge work_mem/shared_pool configuration
3. **Memory leak**: MemStat or InstanceMemory time series data shows memory usage persistently monotonically increasing (comparing multiple ctime data points, showing continuous upward trend without fallback), no obvious external queries but memory continues to grow

**Comprehensive Judgment Rules**:
| Condition | Marker |
|-----------|--------|
| All nodes usage > 70% | Cluster memory globally high |
| Inter-node deviation > 30% | Cluster memory load imbalanced, possible data skew |
| Single instance dynamic memory usage significantly abnormal | Single instance memory anomaly |
| high_memory_sql_detected = true | Single SQL causing high memory, specific SQL identified |
| omm/Ruby proportion in user_memory_top5 > 30% | System internal tasks consuming high memory (system-side) |
| MemStat/InstanceMemory time series persistently monotonically increasing | Possible memory leak |
| work_mem usage rate > 80% | work_mem configuration too large or SQL sort/hash spill |
| shared_pool usage rate > 80% | Shared cache pressure, excessive connections |

**Statistics and Aggregation Requirements**:
1. Memory proportion Top3 database users: Group by active_sessions userName and aggregate mem_used (only database users, not process users). Display in "内存贡献 Top3 数据库用户" HTML table section with pct-bar visualization. Ratio = user's total mem_used / all users' total mem_used × 100%. pct-bar width calculation: `width = Math.round(ratio / max_ratio * 200)`, where max_ratio is the top user's ratio. Only count database users with state=active. If fewer than 3 data points, list actual count.
2. Memory proportion Top3 SQL: Sort by mem_used descending from memory_diagnose_detail active_sessions, display in "内存贡献 Top3 语句" HTML table section. Each row represents one query execution; treat each row independently when sorting for Top 3. QueryID from query_id field (multiple similar SQLs comma-separated with count annotation). Username from userName field (database user). Memory proportion from mem_used field, calculate as percentage of total node memory consumption, keep 1 decimal place. Time: when duration_ms exists, use ctime - duration_ms converted to Beijing time (column header "启动时间"); when duration_ms is absent, use ctime converted to Beijing time (column header "采集时间"). SQL from query field, display up to 1000 characters, truncate with "..." if exceeded. gaussdb process is not listed as an independent statement in Top3; its memory overhead is merged into the corresponding root cause description. If no statement data, fill the table with "无法获取".
3. Proportion = (user/SQL memory consumption / node total memory consumption) × 100%

**Output**: root_cause_category, mem_scope, inst_type, mem_type, summary, high_memory_sql_info, session_info, top3_memory_users, top3_memory_statements, high_freq_queries, heavy_queries, memory_pool_summary, concurrent_mode

### Step 6: Get Cluster Name

Prioritize getting cluster name from input parameter cluster_name. If empty, call `dws_autopilot_get_clusters` with project_id and cluster_id to get cluster_name. If call also fails, use cluster_id as resource_name.

**Output**: resource_name, resource_id

### Step 7: Generate Diagnosis Report

Generate an HTML report following the template in the "Output Format" section. **After generating the report, save the HTML file to the current working directory (workspace root folder) with the filename `dws_mem_diagnosis_report_{timestamp}.html`, where `{timestamp}` is the current machine local time formatted as `yyyyMMdd_HHmmss` (e.g., `dws_mem_diagnosis_report_20260623_150421.html`).**

## Core Commands

### Query Cluster List

```bash
# hcloud
hcloud DWS ListClusters --cli-region=<region> --project_id=<pid> --offset=0 --limit=200
# MCP
dws_autopilot_get_clusters(project_id=<pid>)
```

### Query Host Information

```bash
# hcloud
hcloud DWS ListHostOverview --cli-region=<region> --project_id=<pid> --offset=0 --limit=200
# MCP
dws_autopilot_get_hosts(project_id=<pid>, cluster_id=<cid>, limit=200, offset=0)
```

### Query Metric Data (General Format)

```bash
# hcloud
hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=<name> --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>
# MCP
dws_autopilot_get_metric(project_id=<pid>, cluster_id=<cid>, metric_name=<name>, from_ts=<from>, to_ts=<to>, limit=200, offset=0, order_by="ctime", sort_by="desc")
```

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| alarm_serial_number | Required | Alarm serial number | N/A |
| project_id | Required | Project ID | N/A |
| cluster_id | Required | Cluster ID | N/A |
| first_alarm_time | Required | First alarm time (millisecond timestamp) | N/A |
| alarm_name | Required | Alarm name | N/A |
| region_id | Optional | Region identifier | N/A |
| node_name | Optional | Alert node name | Empty (cluster-level alarm) |
| instance_name | Optional | Instance name | Empty |
| cluster_name | Optional | Cluster name | Use cluster_id |
| alarm_severity | Optional | Alarm severity | N/A |

## Output Format

Strictly output and return according to the template in [Output Format](references/output-format.md). Do not analyze or summarize the template content, do not omit any part, do not modify the template structure. The output must be consistent with the template.

## Best Practices

1. **Timestamp Handling**: first_alarm_time is already a millisecond timestamp; use it directly for tool parameters. Do not convert to time string first and then back to timestamp (to avoid 8-hour offset)
2. **Tool Selection**: Choose between KooCLI and MCP, preferring KooCLI; once selected, use that method throughout
3. **Paginated Queries**: All tool calls uniformly use limit=200 pagination until returned count < 200, then merge all paginated data. memory_diagnose_detail has the largest data volume; pagination is required
4. **Report Time**: All timestamps must be converted to Beijing time (UTC+8). Can use `python -c "from datetime import datetime,timezone,timedelta; print(datetime.fromtimestamp({ms}/1000,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'))"`
5. **SQL Display**: Memory contribution Top3 statements show up to 1000 characters of specific SQL; truncate with "..." if exceeded
6. **Memory Usage Calculation**: Memory usage = (mem_total - mem_free - cached - buffers) / mem_total * 100%; dynamic memory usage = (dynamic_used_memory / max_dynamic_memory) * 100%; process memory usage = (process_used_memory / max_process_memory) * 100%
7. **CN/DN Instance Distinction**: inst_name contains "cn"/"coordinator" → CN; contains "dn"/"datanode" → DN; CN memory high focuses on connection/parsing, DN memory high focuses on data/computation
8. **Session Leak Detection**: idle state but holding large memory → session leak; duration_ms > 30 minutes without memory release → long transaction

## References

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation and configuration |
| [MCP Installation Guide](references/dws-mcp-installation-guide.md) | DWS Autopilot MCP Server installation and configuration |
| [IAM Policies](references/iam-policies.md) | Required permissions and policy JSON |
| [Metric Reference](references/metric-reference.md) | Metric key fields and query differences |
| [Memory Background Knowledge](references/memory-background.md) | Memory formulas, CN/DN distinction, memory_pool analysis, thresholds |
| [Output Format](references/output-format.md) | HTML template and fill rules |

## Notes

- **Security**: Never expose AK/SK values in conversations or commands; never ask users to input AK/SK directly in conversation
- **Time Protocol**: from_ts/to_ts must use millisecond timestamps; report displays Beijing time; when converting Beijing time to timestamp, must append +08:00 timezone suffix; do not mentally calculate timestamp values; do not convert existing millisecond timestamps to time strings and then back
- **Output Constraints**: Strictly output the diagnosis report following the Output Format section template; do not modify template structure, do not omit any part, do not add remediation suggestions, do not output SQL optimization statements, do not use emoji, do not use custom format tags
- **Data Authenticity**: All diagnosis conclusions must come from actual tool return results; when tool returns empty or call fails, mark as "unavailable"; fabricating values is prohibited
- **Known Limitations**: hcloud does not support --order_by and --sort_by parameters; sort by ctime descending locally after query; memory_diagnose_detail does not support host_id filtering; query full cluster then filter locally; memory_diagnose_detail ctime is collection time, not SQL start time; InstanceMemory has no instance_type field, must determine CN/DN via inst_name
