---
name: huawei-cloud-dws-io-diag
description: |
  DWS cluster I/O overload root cause diagnosis skill, based on KooCLI v3.2.0+ and DWS Autopilot MCP Server.
  Automatically collects I/O metrics, analyzes root causes (customer-side / system-side) via three-stage decision tree, and outputs a standardized diagnosis report.
  Applicable to DWS cluster I/O usage too high, I/O alarms, disk I/O load anomaly scenarios.
  Trigger words: "I/O高", "I/O告警", "I/O诊断", "I/O过载", "IO高", "IO告警", "IO诊断", "IO过载", "磁盘IO负载异常", "util打满", "await高", "high I/O", "I/O alarm", "I/O diagnosis"
tags: [huawei-cloud, dws, io, diagnostics, autopilot]

# ============================================================
# Internal extension fields
# ============================================================
trigger:
  keywords: ["DWS", "I/O高", "I/O告警", "I/O诊断", "I/O过载", "I/O使用率过高", "IO高", "IO告警", "IO诊断", "IO过载", "IO使用率过高", "磁盘I/O负载异常", "磁盘IO负载异常", "util打满", "await高", "节点数据盘I/O利用率超阈值", "high I/O", "I/O alarm", "I/O diagnosis", "I/O overload", "high I/O usage", "disk I/O anomaly", "util saturated", "high await", "I/O utilization exceeds threshold"]
  resource_types: ["DWS::instance_id"]
  hypotheses: ["io_high", "io_warning", "io_overload"]

input_schema:
  required:
    - name: "alarm_serial_number"
      type: "string"
      description: "Alarm serial number"
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
    - name: "project_id"
      type: "string"
      description: "Project ID, used as the project_id parameter for tool calls. If not provided, read from MCP Server config file (conf/dws_config.yaml) project_id field"
    - name: "region_id"
      type: "string"
      description: "Region identifier, used for hcloud --cli-region parameter and report region field. If not provided, read from MCP Server config file (conf/dws_config.yaml) region_id field"
    - name: "node_name"
      type: "string"
      description: "Alert node name (extracted from alarm additionalInformation host_name; empty for cluster-level alarms)"
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

# Huawei Cloud DWS I/O Overload Diagnosis Skill

## Overview

This skill is dedicated to DWS cluster I/O overload root cause diagnosis. When a cluster triggers an I/O usage too high alarm, it automatically collects metric data, analyzes root causes (customer-side / system-side) via a three-stage decision tree, and outputs a standardized diagnosis report.

**Architecture**: KooCLI (hcloud) → DWS Autopilot API → Cluster monitoring metrics; MCP Server (dws_autopilot) → Fallback channel for the same API

**Applicable Scenarios**:
- DWS cluster I/O usage too high alarm
- Disk I/O load anomaly investigation
- User-initiated I/O diagnosis request

**Typical Use Cases**:
- "My DWS cluster I/O usage is very high, help diagnose"
- "Received an I/O alarm, cluster ID is xxx, help analyze the cause"
- "DWS cluster disk util is maxed out, see what's causing it"

**Important Rules**: All diagnosis conclusions must come from actual tool return results. Fabricating or assuming values is prohibited. Output only contains the diagnosis report; adding remediation suggestions, outputting SQL optimization statements, and using emoji are prohibited.

**Background Knowledge**: RAID architecture, I/O key metric thresholds, three major I/O scenario indicator features, and important principles are documented in [I/O Background Knowledge](references/io-background.md). Must read before diagnosis.

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

**Available metric_name**: `IOStat`, `CpuStat`, `cpu_io_diagnose_detail`, `business_concurrency`, `business_query_monitor`, `business_thread_wait`, `bussiness_conflict_lock`

**Time Protocol**: from_ts/to_ts must use Unix millisecond timestamps; all times are in UTC timezone; recommended time window: from 5 minutes before alarm time to alarm time (from_ts = first_alarm_time - 300000).

**Return Format**: Success `{"code": 0, "data": [...]}`; Failure `{"code": -1, "message": "error description"}`. On failure, retry once; if still failing, use degradation path and mark as "unavailable" in the report.

**Key Fields per Metric**:
- **IOStat**: ctime, host_id, disk_name, io_data{util, await, r_await, w_await, r_s, w_s, read_iops, write_iops, rMB_s, wMB_s, read_throughput, write_throughput, avgrq_sz, avgqu_sz} → core I/O metrics
- **CpuStat**: ctime, host_id, cpu_data{usr, sys, idle, iowait} → iowait > 30% indicates significant I/O pressure
- **cpu_io_diagnose_detail**: ctime, host_id, active_queries[{query, query_id, userName, cpu_rate, state, inst_name, duration_ms}], io_stats{read_iops, write_iops, read_throughput, write_throughput} → I/O diagnosis details + active queries
- **business_concurrency**: ctime, concurrency_value, active_connections → business concurrency
- **business_query_monitor**: ctime, query, query_id, username, duration_ms, host_id → historical real-time queries
- **business_thread_wait**: ctime, wait_event, count, username, host_id → wait events (wait wal sync, WALWriteLock, etc.)
- **bussiness_conflict_lock**: ctime, lock_type, blocker, waiter, username, host_id → lock conflicts

For query differences per step, see [Metric Reference](references/metric-reference.md).

### Pagination Specification

**All tool calls (MCP and hcloud) must use paginated queries** to prevent single responses from being too large and exceeding token limits.

**Pagination Rules**:
- Use `limit=200` uniformly (do not use 800 or other large values)
- First page `offset=0`; if returned data count = 200, then `offset+=200` and continue querying
- Repeat until returned data count < 200, then merge all paginated data
- When merging, concatenate all page data arrays into a complete dataset

**MCP Call Example** (using IOStat):
```
Page 1: dws_autopilot_get_metric(project_id, cluster_id, metric_name="IOStat", from_ts, to_ts, limit=200, offset=0)
If returned data length = 200:
Page 2: dws_autopilot_get_metric(project_id, cluster_id, metric_name="IOStat", from_ts, to_ts, limit=200, offset=200)
If returned data length < 200: Stop pagination, merge page 1 + page 2 data
```

**hcloud Call Example** (using IOStat):
```
Page 1: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=IOStat --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>
If returned data count = 200:
Page 2: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=IOStat --project_id=<pid> --offset=200 --limit=200 --from=<from_ts> --to=<to_ts>
If returned data count < 200: Stop pagination, merge data
```

## Workflow

Before diagnosis, create an execution plan based on Steps 0-7, then execute sequentially. For tool selection strategy, see the "KooCLI Command Format Standard" section; subsequent steps will not repeat this. All MCP tool calls follow the "Pagination Specification" section; subsequent steps will not repeat pagination details.

### Step 0: Environment Detection & Parameter Resolution

**Parameter Resolution**: If `project_id` or `region_id` is not provided by the user, read from MCP Server config file `conf/dws_config.yaml`:
- When `project_id` is missing: Execute `python -c "import yaml; c=yaml.safe_load(open('conf/dws_config.yaml')); print(c.get('project_id',''))"` to obtain it
- When `region_id` is missing: Execute `python -c "import yaml; c=yaml.safe_load(open('conf/dws_config.yaml')); print(c.get('region_id',''))"` to obtain it
- If the corresponding field in the config file is also empty, prompt the user to provide the parameter

Execute `hcloud version`; version >= 3.2.0 → tool_mode=hcloud, otherwise tool_mode=mcp.

**hcloud Network Availability Probe**: If tool_mode=hcloud, execute a lightweight API call (e.g., `hcloud DWS ListClusters --cli-region=<region> --project_id=<project_id> --offset=0 --limit=1`) to verify network connectivity:
- Returns normal or business error (e.g., insufficient permissions, parameter error) → Network available, keep tool_mode=hcloud
- Returns NETWORK_ERROR → Network unavailable, fall back to tool_mode=mcp
- After fallback, if MCP is also unavailable → Terminate execution, prompt user to check KooCLI network configuration or MCP Server configuration

### Step 1: Query IOStat

Call metric query with metric_name="IOStat", time window: from_ts=`first_alarm_time - 300000`, to_ts=`first_alarm_time`. In MCP mode, use limit=200 paginated query.

**Autopilot Unavailable Determination**: Returns 50201/RDS.9999 error → Skip Steps 1-6, mark all metrics as "unavailable", proceed directly to Step 7.

**Parsing**: Group by host_id and disk_name, find the latest I/O data for each disk on each node. Extract util, await, r_await, w_await, r_s, w_s, read_iops, write_iops, rMB_s, wMB_s, read_throughput, write_throughput, avgrq_sz, avgqu_sz for each disk.

**I/O Overload Determination**: Whether any disk has util > 90% or await > 100 or throughput/IOPS reaching upper limit.

**I/O Imbalance Determination**: Whether the deviation of util or await between nodes > 20%.

**TOP Node Filtering**: Find the two nodes with the highest I/O load.

**Phenomenon Distribution Determination**: Whether a node has single disk I/O high or all disks I/O high (used for Step 4 scenario routing).

**High IO Time Points**: From the IOStat time series data, find all ctime points where any disk util > 90% on the top 2 IO nodes. Collect these ctime values as `high_io_ctimes` (list of millisecond timestamps). Also record the ctime with the highest util as `peak_io_ctime`. If no ctime has util > 90%, `high_io_ctimes` is empty and `peak_io_ctime` is the ctime with the highest util value.

**Output**: io_by_host_disk, io_by_host, max_io_hosts, problem_host_id, problem_host_util, problem_host_await, problem_host_avgrq_sz, problem_host_avgqu_sz, cluster_avg_util, is_imbalanced, io_deviation, high_io_nodes, single_disk_high_nodes, all_disk_high_nodes, high_io_ctimes, peak_io_ctime

### Step 2: Get Host Names

Call host information query (MCP mode limit=200 paginated), build host_id → {host_name, ip} mapping table. Only query host information for nodes involved in max_io_hosts from Step 1 output.

**Output**: host_id_to_info_map, problem_host_ip, node_name

### Step 3: Query CpuStat

Call metric query with metric_name="CpuStat". In MCP mode, use limit=200 paginated query.

**Parsing**: Extract iowait for each node. iowait > 30% indicates significant I/O pressure. High iowait but low CPU usage → typical I/O bottleneck.

**Output**: cpu_by_host, high_iowait_nodes

### Step 4: Three-Stage Decision Tree I/O Scenario Determination

Based on Step 1 IOStat data and Step 3 CpuStat data, determine I/O scenario via three-stage decision tree.

**Precondition**: await persistently > 100 and avgqu_sz persistently > 100?
- No → Occasional await/avgqu_sz spikes are normal, no scenario determination needed, mark as normal
- Yes → Enter three-stage determination

**Stage 1: Clear I/O Anomaly** — IOPS and throughput far below minimum specification?
- SSD: rMB/s+wMB_s << 900MB/s and r/s+w/s << 8000/s
- HDD: rMB/s+wMB_s << 250MB/s and r/s+w/s << 1000/s
- Yes → Confirmed **I/O Anomaly** (definite hardware issue)

**Stage 2: Clear I/O Overload** — IOPS or throughput exceeds maximum specification?
- SSD: rMB/s+wMB_s > 3500MB/s or r/s+w/s > 20000/s
- HDD: rMB/s+wMB_s > 800MB/s or r/s+w/s > 2000/s
- Yes → Confirmed **I/O Overload** (distinguish throughput overload/IOPS overload/dual overload)
  - Only throughput exceeds maximum → I/O throughput overload
  - Only IOPS exceeds maximum → IOPS overload
  - Both exceed maximum → Dual overload

**Stage 3: Gray Zone** — I/O close to minimum specification, or exceeds minimum but below maximum?
- Single disk poor performance (high await/high avgqu_sz), other disks normal → Determine as **I/O Anomaly**
- Single disk high I/O volume (high throughput/IOPS), other disks normal → Determine as **I/O Overload**
- All disks perform consistently → Compare with other nodes' I/O
  - Other nodes have I/O pressure but no I/O wait → Determine as this node **I/O Anomaly**
  - Other nodes have I/O pressure and wait / Other nodes have no I/O pressure and no wait → **Cannot definitively determine**, must provide both I/O overload and I/O anomaly full investigation directions
  - Other node data not available → Must suggest user provide other node iostat for comparison, while providing both full investigation directions

**Phenomenon Distribution Determination** (based on Step 1 IOStat data, analyzed by host_id + disk_name dimension):
- **Single node + single disk I/O high**: Only one disk on one node has I/O anomaly, other disks on that node are normal or low → Data skew / disk failure
- **Single node + all disks I/O high (overload type)**: All disks on one node have throughput/IOPS exceeding limits → Prioritize suspicion of node-level anomaly (RAID card read-write strategy degradation / RAID card CC verification / RAID card failure), because DWS data distribution is disk-based and will not cause all disks to be overloaded simultaneously; also provide I/O overload investigation direction as possibility B
- **Single node + all disks I/O high (anomaly type)**: All disks on one node have throughput/IOPS below limits but await is extremely high → Route to I/O anomaly (single node + all disks)
- **Multiple nodes / all nodes + all DN data disks I/O high** → Business-layer overload (full table scan, batch import, etc.)
- **System disk I/O high** → pg_log logs / pg_audit audit logs / system-level tasks

**I/O Type Determination** (for overload scenario routing):
- wMB/s >> rMB/s → Write I/O dominant
- rMB/s >> wMB/s → Read I/O dominant

**Output**: io_scenario, io_type, phenomenon_distribution, is_gray_zone, gray_zone_result

### Step 5: Query Business Concurrency and I/O Diagnosis Details

**5a: Query Business Concurrency**

Call metric query with metric_name="business_concurrency". In MCP mode, use limit=200 paginated query.

**Output**: max_concurrency, avg_concurrency, is_high_concurrency

**5b: Query I/O Diagnosis Details for Top 2 Nodes**

Call `dws_service_autopilot_metric_data`, parameters same as Step 3, `metric_name` changed to "cpu_io_diagnose_detail". **Note: metric_data does not support filtering by host_id; query returns full cluster data, then filter by the host_id of the top 2 IO nodes.**

**Paginated Query**: This metric has the largest data volume (multi-node × multi-instance × multi-timepoint × multi-query), a single page of 800 may not be enough. First page offset=0, limit=800; if returned data count = 800, then offset+=800 and continue querying, until returned data < 800, then merge all paginated data.

**High IO Time Period Filtering**: From the returned data, only keep sampling points where `ctime ∈ {{steps.iostat_metrics.output.high_io_ctimes}}`, excluding irrelevant queries from normal time periods. If high_io_ctimes is empty (no high IO time points), take the data from the time point with the highest util, annotate as "IO did not persistently exceed threshold, the following is query reference at the highest IO moment".

Parse returned data, extract for each node:
- Active query statement list (SQL)
- Execution user (userName)
- Query duration (duration_ms)
- IO consumption per SQL (io_read, io_write, collected by pidstat -t -d)
- IO statistics (io_stats: read_iops, write_iops, read_throughput, write_throughput)
- Lock wait status

**Spill to Disk Determination Rule**: Infer based on active statement characteristics, mark `spill_detected=true` if any of the following conditions is met:
- SQL statement contains multi-table JOIN + sort (ORDER BY) / aggregation (GROUP BY/DISTINCT) operations, and write IO is significantly higher than read IO (when io_data_available=true, io_write >> io_read, or io_stats.write_throughput abnormally high)
- business_thread_wait contains `wait file write` wait event
- Record matched SQL in `full_scan_queries` (reuse this field to record spill SQL), spill_info records details of the first spill SQL

**Full Table Scan Determination Rule**: Infer based on active statement characteristics, mark `full_scan_detected=true` if the following condition is met:
- SQL statement is a large table SELECT */COUNT(*)/MAX/MIN etc. aggregation query, and WHERE condition filtering is poor (no WHERE or only non-equivalence conditions)
- Record matched SQL in `full_scan_queries`

**Data Skew Inference Rule**: Infer based on IOStat inter-node IO deviation, non-confirmatory judgment:
- If IOStat shows a node's util is significantly higher than other nodes (deviation > 20%), and active queries on that node are concentrated on a few tables, then `is_data_skewed=true`
- skew_info records the two nodes with the largest deviation and deviation percentage, description annotated as "Inferred from inter-node IO deviation, possible data skew, recommend checking table distribution columns"

**IO Contribution TopN Statistics Rule** (time window aggregation, aligned with DMS monitoring item logic):
- **Data Availability Determination**: Check io_read/io_write fields of all active_queries, if all are 0 or fields do not exist, then `io_data_available=false`. **Note: io_data_available=true is a rare scenario** (only when cluster nodes have deployed pidstat collection plugin and collection is normal, io_read/io_write will have non-zero values, in most cases this field is 0), therefore io_data_available=false is the norm
- **Filter Threshold** (aligned with DMS plugin filter logic, io_read/io_write unit is kB/s): Only when `cpu_rate < 20%` AND `io_read < 1024` AND `io_write < 1024`, filter out that row (AND relationship, all three below threshold to filter, any one exceeding threshold is retained), retained rows participate in TopN statistics
- **Ruby User Filtering**: Rows with userName "Ruby" do not participate in TopN sorting (aligned with DMS monitoring item logic), Ruby's IO consumption is reflected in system-side root cause description
- **Cross-Sampling Point Aggregation**: Group by query_id, aggregate across multiple sampling points in high IO time period (io_read/io_write are rate values kB/s):
  - **Total IO**: Σ(io_read + io_write), reflects cumulative IO contribution within time window
  - **Total CPU**: Σ(cpu_rate), reflects cumulative CPU contribution within time window
  - **Appearance Frequency**: Number of sampling points where this SQL appears / total sampling points in high IO time period, e.g. 3/3, reflects persistence
- **TopN SQL IO Contribution**:
  - When io_data_available=true: From aggregated per-SQL rows (lwtid non-empty and userName not "Ruby"), sort by Total IO DESC take Top3, secondary sort Appearance Frequency DESC. Extract query_preview, query_id, userName, total_io_read, total_io_write, frequency, cpu_rate, io_characteristic
  - When io_data_available=false: From aggregated per-SQL rows (lwtid non-empty and userName not "Ruby"), sort by Total CPU DESC take Top3, secondary sort Appearance Frequency DESC. Extract query_preview, query_id, userName, total_cpu_rate, frequency, cpu_rate, io_characteristic. Annotate as "IO消耗数据不可用，按CPU占用排序作为参考"
- **TopN User IO Contribution**:
  - When io_data_available=true: From aggregated per-user rows (lwtid empty and userName non-empty and userName not "Ruby"), sort by Total IO DESC take Top3, secondary sort Appearance Frequency DESC. Extract userName, total_io_read, total_io_write, frequency
  - When io_data_available=false: From aggregated per-user rows (lwtid empty and userName non-empty and userName not "Ruby"), sort by Total CPU DESC take Top3, secondary sort Appearance Frequency DESC. Extract userName, total_cpu_rate, frequency. Annotate as "IO消耗数据不可用，按CPU占用排序作为参考"

**Time Annotation Rule**: `ctime` returned by `cpu_io_diagnose_detail` is the Autopilot collection snapshot time, not the actual SQL start time. If active_queries contains `duration_ms` field, then SQL start time = ctime - duration_ms, annotated as "start time"; if `duration_ms` is unavailable, use ctime directly, annotated as "collection time" (do not annotate collection time as "start time").

**Active User Statistics Rule**: Only count users and connections with state=active; idle state not counted. Group by userName and count active query numbers, identify top users.

**Output (steps.top_node_io_diagnose.output)**:
```
io_query_details:           # Node IO query details [{host_id, queries, io_stats}]
spill_detected:             # Whether spill to disk is detected (boolean)
spill_info:                 # Spill information {query, query_id, username, host_id, io_write_rate}
full_scan_detected:         # Whether full table scan is detected (boolean)
full_scan_queries:          # Full table scan query list [{query, query_id, username, host_id, duration_ms}]
is_data_skewed:             # Whether data skew is possible (inferred from IOStat inter-node deviation, non-confirmatory) (boolean)
skew_info:                  # Skew inference information {max_deviation_node, min_deviation_node, deviation_pct, description} (inferred from IOStat inter-node IO deviation, marked when deviation > 20%, cannot confirm specific table names)
topn_sql_io:                # Top3 SQL IO contribution (time window aggregation) [{query_preview, query_id, user_name, total_io_read, total_io_write, frequency, cpu_rate, io_characteristic}]
topn_user_io:               # Top3 User IO contribution (time window aggregation) [{user_name, total_io_read, total_io_write, frequency}]
io_data_available:          # Whether io_read/io_write data is available (boolean)
peak_io_ctime:              # Highest util time point ctime in high IO time period
```

**5c: Query Wait Events and Lock Conflicts**

Call metric query with metric_name="business_thread_wait" and metric_name="bussiness_conflict_lock". In MCP mode, use limit=200 paginated query.

**Parsing**: Identify I/O-related wait events (e.g., wait wal sync, WALWriteLock, I/O wait). Identify lock conflicts causing I/O anomalies.

**Output**: wait_events, io_wait_detected, lock_conflicts, lock_conflict_detected

### Step 6: Analyze Diagnosis Results

Based on data collected in Steps 1-5, combined with Step 4 three-stage decision tree result and phenomenon distribution, route to corresponding scenario and execute full investigation direction analysis.

**Time Formatting**: All Unix millisecond timestamps (first_alarm_time, ctime, etc.) are in UTC timezone. In the report, they must be converted to Beijing time (UTC+8) string `YYYY-MM-DD HH:MM:SS`. Can use `python -c "from datetime import datetime,timezone,timedelta; print(datetime.fromtimestamp({ms}/1000,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'))"`. Do not mentally calculate timestamp values.

**User Identity Judgment** (based on database user, i.e., cpu_io_diagnose_detail username):
- Database user is "omm" or "Ruby" → **System cause**
- Database user is not "omm" nor "Ruby" → **Customer-side cause**

#### Scenario Routing and Full Investigation Directions

Based on Step 4's `io_scenario` and `phenomenon_distribution`, route to the corresponding scenario and execute full investigation. **Must read [IO_DIAGNOSIS_REF.md](references/IO_DIAGNOSIS_REF.md) for the complete scenario routing table, investigation direction list, customer-side/system cause descriptions and output examples; do not analyze based solely on the scenario overview below.**

**Scenario Overview**:
- **Scenario 1: I/O Throughput Overload** → Route by read I/O / write I/O, sub-scenarios route by phenomenon distribution
- **Scenario 2: IOPS Overload** → Route by read I/O / write I/O, fragmented I/O investigation (avgrq_sz<30), sub-scenarios route by phenomenon distribution
- **Scenario 3: I/O Anomaly** → Hardware-layer investigation (RAID card / I/O scheduler), does not depend on active statements
- **Scenario 4: Dual Overload** → Merge Scenario 1 and Scenario 2 investigation directions, deduplicate overlapping directions
- **Gray Zone** → Output both I/O overload and I/O anomaly complete investigation directions simultaneously

**Comprehensive Judgment Rules**:
| Condition | Marker |
|-----------|--------|
| problem_host_util > 90% | Disk utilization too high |
| problem_host_await > 100 | I/O response time too long |
| io_deviation > 20% | Cluster I/O load imbalanced, possible data skew |
| is_high_concurrency = true and spill_detected = true | High concurrency spill to disk causing high I/O |
| full_scan_detected = true | Full table scan causing high I/O, specific statement identified |
| io_wait_detected = true | I/O-related wait events detected |
| lock_conflict_detected = true | Lock conflict affecting I/O performance |

**Statistics and Aggregation Requirements**:
1. **When io_data_available=true**: Use Step 5b time window aggregation results (aggregate by query_id across high IO time period sampling points, primary sort Σ(io_read+io_write) DESC, secondary sort appearance frequency DESC), take Top3 SQL and Top3 user IO contribution respectively. Filter threshold (AND relationship): only when cpu_rate<20% AND io_read<1024kB/s AND io_write<1024kB/s, filter out that row. Ruby user does not participate in TopN sorting, its IO consumption is reflected in system-side root cause description (e.g., "System user Ruby's autovacuum task causing high IO"). Output 【IO Contribution Top3 SQL】 and 【IO Contribution Top3 User】 in report, including total IO (kB, converted to MB in report) and appearance frequency. TopN SQL entries include IO characteristics (spill/full table scan/high IO wait etc. qualitative description), no separate 【IO Related Anomalous Queries】 section to avoid same SQL appearing twice
2. **When io_data_available=false** (io_read/io_write all 0 or non-existent): Use Step 5b time window aggregation results, but sort by Σ(cpu_rate) DESC instead of Total IO, take Top3 SQL and Top3 user contribution. Filter threshold: only when cpu_rate<20%, filter out that row. Ruby user does not participate in TopN sorting. Output 【IO Contribution Top3 SQL】 and 【IO Contribution Top3 User】 in report, annotated as "IO消耗数据不可用，按CPU占用排序作为参考". TopN SQL entries include query_preview, query_id, userName, total_cpu_rate, frequency, cpu_rate, io_characteristic. TopN User entries include userName, total_cpu_rate, frequency. Additionally, describe detected IO-related phenomena as investigation directions: spill characteristics, full table scan characteristics, IO wait events. These are possibility inferences rather than quantitative evidence of IO consumption, annotate as "investigation direction"
3. gaussdb process IO overhead is merged into the corresponding root cause description, not listed as an independent statement

**No Anomaly Determination**: When Step 4 three-stage decision tree determines that the I/O scenario is normal (i.e., no scenario determination needed, util far below 90%, await far below 100ms, iowait far below 30%), then `io_scenario=normal`, no scenario routing is needed, and the diagnosis conclusion is "No anomaly detected in diagnosis". In this case:
- `root_cause_category` = "normal", `io_scenario` = "normal", all other flags (spill_detected, full_scan_detected, io_wait_detected, lock_conflict_detected, is_data_skewed) = false
- `io_investigation_info` = empty
- `topn_sql_io` and `topn_user_io` are still calculated per Step 5b TopN statistics rules, annotated as reference information rather than root cause evidence
- The "Problem Node I/O Overview" table in the report should be empty (no rows), since no nodes exceed thresholds
- The "IO Related Anomalous Queries and Investigation Information" section should display current active query reference information (not investigation directions), annotated as "IO未发现异常，以下为当前活跃查询参考信息"
- The "IO Contribution Top3 SQL" and "IO Contribution Top3 User" sections should display current active query/user reference information, following the same io_data_available=true/false rendering rules as the anomaly scenario, but annotated as reference information rather than root cause evidence

**Output**: root_cause_category, io_scenario, phenomenon_distribution, io_type, summary, specific_sql, is_data_skewed, spill_detected, full_scan_detected, io_wait_detected, lock_conflict_detected, io_investigation_info, topn_sql_io, topn_user_io, io_data_available

### Step 7: Generate Diagnosis Report

Generate an HTML report following the template in the "Output Format" section. **After generating the report, save the HTML file to the current working directory (workspace root folder) with the filename `dws_io_diagnosis_report_{timestamp}.html`, where `{timestamp}` is the current machine local time formatted as `yyyyMMdd_HHmmss` (e.g., `dws_io_diagnosis_report_20260623_150421.html`).**

In addition to the HTML report, output `{{diagnosis_json}}` data structure. **Must read [diagnosis_json Format Reference](references/diagnosis-json-format.md) for the complete data structure, content field format rules (io_data_available=true/false), system-side/no-anomaly examples, and Ruby user constraint.**

**Report Section Fill Rules for No Anomaly**:
- When `io_scenario=normal` (diagnosis conclusion is "No anomaly detected"):
  - `diagnosis_summary`: Output `<div class="conclusion-item normal">诊断暂未发现异常</div><div class="conclusion-item normal">诊断时间范围: {from_time} ~ {to_time}</div>`
  - Problem Node I/O Overview table: Output only the header row, no data rows (since no nodes exceed thresholds)
  - `io_investigation_content`: Display current active query reference information, annotated as "IO未发现异常，以下为当前活跃查询参考信息". Follow the same io_data_available=true/false rendering rules as the anomaly scenario, but replace "IO排查方向" with "IO参考信息" and annotate as reference rather than investigation direction
  - `topn_sql_io_content` and `topn_user_io_content`: Follow the same io_data_available=true/false rendering rules as the anomaly scenario, but annotate as reference information rather than root cause evidence
  - `diagnosis_json`: content = `"诊断暂未发现异常"`, addition.advice = `"暂无"`
- When `io_scenario` is not normal (anomaly detected):
  - Problem Node I/O Overview table: Only list nodes with I/O exceeding thresholds, do not list normal nodes
  - `io_investigation_content`: Fill according to io_data_available=true/false rules

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
| cluster_id | Required | Cluster ID | N/A |
| first_alarm_time | Required | First alarm time (millisecond timestamp) | N/A |
| alarm_name | Required | Alarm name | N/A |
| project_id | Optional | Project ID | Read from MCP Server config file (conf/dws_config.yaml) project_id field |
| region_id | Optional | Region identifier | Read from MCP Server config file (conf/dws_config.yaml) region_id field |
| node_name | Optional | Alert node name | Empty (cluster-level alarm) |
| cluster_name | Optional | Cluster name | Use cluster_id |
| alarm_severity | Optional | Alarm severity | N/A |

**Parameter Resolution Rules**: When `project_id` or `region_id` is not provided by the user, read from MCP Server config file `conf/dws_config.yaml`:
- `project_id`: Read the `project_id` field from `conf/dws_config.yaml`
- `region_id`: Read the `region_id` field from `conf/dws_config.yaml`
- How to read: Use `python -c "import yaml; c=yaml.safe_load(open('conf/dws_config.yaml')); print(c.get('project_id',''))"` for project_id, and `python -c "import yaml; c=yaml.safe_load(open('conf/dws_config.yaml')); print(c.get('region_id',''))"` for region_id

## Output Format

Strictly output and return according to the template in [Output Format](references/output-format.md). Do not analyze or summarize the template content, do not omit any part, do not modify the template structure. The output must be consistent with the template.

## Best Practices

1. **Timestamp Handling**: first_alarm_time is already a millisecond timestamp; use it directly for tool parameters. Do not convert to time string first and then back to timestamp (to avoid 8-hour offset)
2. **Tool Selection**: Choose between KooCLI and MCP, preferring KooCLI; once selected, use that method throughout
3. **Paginated Queries**: All tool calls uniformly use limit=200 pagination until returned count < 200, then merge all paginated data. Exception: cpu_io_diagnose_detail uses limit=800 pagination (due to largest data volume), until returned count < 800, then merge all paginated data
4. **Report Time**: All timestamps must be converted to Beijing time (UTC+8). Can use `python -c "from datetime import datetime,timezone,timedelta; print(datetime.fromtimestamp({ms}/1000,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'))"`
5. **SQL Display**: I/O related anomalous queries show up to 1024 characters of specific SQL; truncate with "..." if exceeded; SQL summary in diagnosis_summary is up to 50 characters
6. **I/O Threshold Judgment**: I/O thresholds are based on RAID group specifications; each sdX device in iostat corresponds to one RAID group; thresholds are already RAID group overall performance specifications, compare directly without multiplying by disk count
7. **Throughput and IOPS Independent Judgment**: Both can be overloaded simultaneously; each must be judged independently. Throughput not overloaded but IOPS overloaded → only IOPS overload, not dual overload
8. **Anomaly Feature**: Throughput and IOPS occasionally maxed out but await persistently high → prioritize I/O anomaly determination over overload

## References

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation and configuration |
| [MCP Installation Guide](references/dws-mcp-installation-guide.md) | DWS Autopilot MCP Server installation and configuration |
| [IAM Policies](references/iam-policies.md) | Required permissions and policy JSON |
| [Metric Reference](references/metric-reference.md) | Metric key fields and query differences |
| [I/O Background Knowledge](references/io-background.md) | RAID architecture, I/O thresholds, scenario features, important principles |
| [Output Format](references/output-format.md) | HTML template and fill rules |
| [diagnosis_json Format](references/diagnosis-json-format.md) | diagnosis_json data structure, content field format rules, Ruby user constraint |
| [I/O Diagnosis Reference](references/IO_DIAGNOSIS_REF.md) | Scenario routing table, investigation directions, and output examples |

## Notes

- **Security**: Never expose AK/SK values in conversations or commands; never ask users to input AK/SK directly in conversation
- **Time Protocol**: from_ts/to_ts must use millisecond timestamps; report displays Beijing time; when converting Beijing time to timestamp, must append +08:00 timezone suffix; do not mentally calculate timestamp values; do not convert existing millisecond timestamps to time strings and then back
- **Output Constraints**: Strictly output the diagnosis report following the Output Format section template; do not modify template structure, do not omit any part, do not add remediation suggestions, do not output SQL optimization statements, do not use emoji, do not use custom format tags
- **Data Authenticity**: All diagnosis conclusions must come from actual tool return results; when tool returns empty or call fails, mark as "无法获取"; fabricating values is prohibited
- **Known Limitations**: hcloud does not support --order_by and --sort_by parameters; sort by ctime descending locally after query; cpu_io_diagnose_detail does not support host_id filtering; query full cluster then filter locally; cpu_io_diagnose_detail returns flat row structure (one query per row), not nested active_queries array; iostat cannot precisely distinguish sequential I/O from random I/O ratio; each sdX device in iostat corresponds to one RAID group, thresholds are RAID group overall performance specifications; io_data_available=false is the norm (io_read/io_write are 0 unless pidstat collection plugin is deployed), TopN sorting is only meaningful when io_data_available=true
- **RAID Architecture**: System disks: 2 disks in RAID1 (mirroring), specifications are already RAID group overall performance; Data disks: 4-6 disks in RAID5 (parity), specifications are already RAID group overall performance; DWS data distribution is disk-based: data skew only causes single disk overload, not all disks overloaded simultaneously
