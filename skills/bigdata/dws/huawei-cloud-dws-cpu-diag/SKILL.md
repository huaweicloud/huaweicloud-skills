---
name: huawei-cloud-dws-cpu-diag
description: |
  DWS cluster CPU high root cause diagnosis skill, based on KooCLI v3.2.0+ and DWS Autopilot MCP Server.
  Automatically collects CPU metrics, analyzes root causes (customer-side / system-side), and outputs a standardized diagnosis report.
  Applicable to DWS cluster CPU usage too high, CPU alarms, CPU load anomaly scenarios.
  Trigger words: "CPU高", "CPU告警", "CPU诊断", "CPU使用率过高", "CPU满", "high CPU", "CPU alarm", "CPU diagnosis"
tags: [huawei-cloud, dws, cpu, diagnostics, autopilot]

# ============================================================
# Internal extension fields
# ============================================================
trigger:
  keywords: ["DWS", "CPU高", "CPU告警", "CPU负载异常", "CPU使用率", "CPU诊断", "CPU使用率过高", "CPU满", "high CPU", "CPU alarm", "CPU overload", "CPU usage", "CPU diagnosis", "high CPU usage", "CPU saturated"] 
  resource_types: ["DWS::instance_id"]
  hypotheses: ["cpu_high", "cpu_warning", "cpu_overload"]

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

# Huawei Cloud DWS CPU High Diagnosis Skill

## Overview

This skill is dedicated to DWS cluster CPU high root cause diagnosis. When a cluster triggers a CPU usage too high alarm, it automatically collects metric data, analyzes root causes (customer-side / system-side), and outputs a standardized diagnosis report.

**Architecture**: KooCLI (hcloud) → DWS Autopilot API → Cluster monitoring metrics; MCP Server (dws_autopilot) → Fallback channel for the same API

**Applicable Scenarios**:
- DWS cluster CPU usage too high alarm
- CPU load anomaly investigation
- User-initiated CPU diagnosis request

**Typical Use Cases**:
- "My DWS cluster CPU usage is very high, help diagnose"
- "Received a CPU alarm, cluster ID is xxx, help analyze the cause"
- "DWS cluster CPU is maxed out, see what's causing it"

**Important Rules**: All diagnosis conclusions must come from actual tool return results. Fabricating or assuming values is prohibited. Output only contains the diagnosis report; adding remediation suggestions, outputting SQL optimization statements, and using emoji are prohibited.

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

| Tool Name | Purpose |
|-----------|---------|
| `dws_autopilot_get_clusters` | Query cluster list, get cluster name, project_id, etc. |
| `dws_autopilot_get_hosts` | Query host information |
| `dws_autopilot_get_metric` | Query metric data |

Available metric_name: `CpuStat`, `business_concurrency`, `cpu_io_diagnose_detail`, `node_process_cpu_top20`, `command_cpu_usage`

For key fields per metric and query differences per step, see [Metric Reference](references/metric-reference.md).

### Pagination Specification

**All tool calls (MCP and hcloud) must use paginated queries** to prevent single responses from being too large and exceeding token limits.

**Pagination Rules**:
- Use `limit=200` uniformly (do not use 800 or other large values)
- First page `offset=0`; if returned data count = 200, then `offset+=200` and continue querying
- Repeat until returned data count < 200, then merge all paginated data
- When merging, concatenate all page data arrays into a complete dataset

**MCP Call Example** (using CpuStat):
```
Page 1: dws_autopilot_get_metric(project_id, cluster_id, metric_name="CpuStat", from_ts, to_ts, limit=200, offset=0)
If returned data length = 200:
Page 2: dws_autopilot_get_metric(project_id, cluster_id, metric_name="CpuStat", from_ts, to_ts, limit=200, offset=200)
If returned data length < 200: Stop pagination, merge page 1 + page 2 data
```

**hcloud Call Example** (using CpuStat):
```
Page 1: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=CpuStat --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>
If returned data count = 200:
Page 2: hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=CpuStat --project_id=<pid> --offset=200 --limit=200 --from=<from_ts> --to=<to_ts>
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

### Step 1: Query CpuStat

Call metric query with metric_name="CpuStat", time window: from_ts=`first_alarm_time - 1200000`, to_ts=`first_alarm_time`. In MCP mode, use limit=200 paginated query.

**Autopilot Unavailable Determination**: project_id is empty, or returns 50201/RDS.9999 error → Skip Steps 1-5.5, mark all metrics as "unavailable", proceed directly to Step 6.

**Parsing**: CPU usage = usr + sys. Group by host_id, calculate max CPU usage and average CPU usage (across time window) for each node separately.

**TOP Node Filtering**: Sort nodes by average CPU usage in descending order, select TOP nodes:
- Cluster node count <= 6: Select all nodes
- Cluster node count > 6: Select only TOP 3 nodes

**Node Scope Classification**: All nodes CPU high (high CPU node ratio >= 80%) → all_nodes; Single node CPU high → single_node; Partial nodes → partial_nodes.

**Balance Determination**: For TOP nodes, compare the difference between max CPU and average CPU. If for all TOP nodes, |max - avg| / avg < 20%, then "load balanced"; subsequent steps (Steps 4-5.5) only need to analyze TOP 3 nodes. Otherwise "load unbalanced"; subsequent steps need to analyze all high CPU nodes.

**Output**: cpu_by_host, max_cpu_hosts (TOP node list sorted by average CPU), problem_host_id, problem_host_cpu_usage, cpu_scope, high_cpu_nodes, is_balanced, nodes_to_analyze (list of nodes to analyze in subsequent steps)

### Step 2: Get Host Names

Call host information query (MCP mode limit=200 paginated), build host_id → {host_name, ip} mapping table. Only query host information for nodes involved in nodes_to_analyze from Step 1 output.

**Output**: host_id_to_info_map, problem_host_ip, node_name

### Step 3: Query Business Concurrency

Call metric query with metric_name="business_concurrency". In MCP mode, use limit=200 paginated query until returned count < 200.

**Output**: max_concurrency, avg_concurrency, is_high_concurrency

### Step 4: Query CPU Highest Node Diagnosis Details

Call metric query with metric_name="cpu_io_diagnose_detail". Does not support host_id filtering; query full cluster then filter by nodes_to_analyze from Step 1 output. **MCP mode must use limit=200 paginated query** (this metric has the largest data volume; single page of 800 will exceed token limit), until returned count < 200, merge all paginated data before filtering.

**Parsing**: Extract active queries, users, duration, process information. ctime is collection time, not SQL start time; when duration_ms exists, SQL start time = ctime - duration_ms. Only count users with state=active. inst_name contains "cn" → CN instance; contains "dn" → DN instance.

**Note**: cpu_io_diagnose_detail returns a flat row structure (one query record per row), not a nested active_queries array. Key fields: ctime, host_id, inst_name, username, cpu_rate, count, datname, io_read, io_write, query_id, query, duration_ms, state.

**Output**: single_statement_detected, single_statement_info, high_concurrency_detected, concurrent_stats, inst_type, high_freq_queries, heavy_queries

### Step 5: Query Process CPU Top 20

Call metric query with metric_name="node_process_cpu_top20". In MCP mode, use limit=200 paginated query. Query full cluster then filter by nodes_to_analyze from Step 1 output. **Note: This metric may return null**; in that case, mark as "unavailable" and skip.

**Output**: processes_by_host, top_cpu_process

### Step 5.5: Query Command-Level CPU Usage

Call metric query with metric_name="command_cpu_usage". In MCP mode, use limit=200 paginated query.

**Data Structure**: Each row represents one process on one host at one collection time. Key fields: ctime, host_id, command, args (command_detail), cpu_rate, username. The `command` field differentiates process types: `gaussdb-dn` (datanode main process), `gaussdb-cn` (coordinator main process), `gaussdb` (fenced UDF subprocess), `python3`, `java`, `sh`, `cm_agent`, `gs_gtm`, etc. The `args` field contains the full command detail (e.g., `/DWS/manager/app/bin/gaussdb --datanode ...`). The `username` field is the **OS user** (e.g., Ruby, root), NOT the database user.

**Gaussdb Main Process Definition**: `command` field is `gaussdb-dn` or `gaussdb-cn` → gaussdb main process (its CPU is attributed to SQL statements and root causes, excluded from Top 3 Processes). `command` field is `gaussdb` (fenced UDF master process) → NOT a main process, included in Top 3 Processes.

**Output**: command_by_host, abnormal_process

### Step 6: Analyze Diagnosis Results

**Diagnosis Priority**: Check scope first then find causes; business anomalies come first; configuration and system issues come last.

**CPU Type Determination**: SysCPU/UserCPU >= 1/2 → High SysCPU, otherwise High UserCPU.

**User Identity Judgment**: Database user (userName) is omm/Ruby → System cause, otherwise → Customer-side cause.

**Abnormal Process Identification**: command contains safest/AsiaInfo/aliyundun → Antivirus software; command does not contain gaussdb/postgres/gtm/cm_agent → Non-gaussdb process; command is `gaussdb` (fenced UDF, not `gaussdb-dn`/`gaussdb-cn`) → Subprocess anomaly.

**Customer-Side Causes**: High concurrency (multi-user/single-user), single statement (CPU ratio > 30%), data skew/computation skew. High concurrency and single statement can both be matched simultaneously.

**System Causes**: System internal SQL (VACUUM, etc.), abnormal processes, high SysCPU.

**Statistics**: Calculate three categories of Top 3:
1. **Top 3 Statements** (from cpu_io_diagnose_detail): Sort by cpu_rate descending (cpu_rate is already an instance-level percentage, use directly), output query_id, username, start time, CPU ratio, specific SQL (max 1024 characters). Each row is one query on one instance; do not re-calculate ratio by dividing by global total.
2. **Top 3 Database Users** (from cpu_io_diagnose_detail): Aggregate by username cpu_rate (only state=active), output username and ratio. The username here is the **database user**, NOT the OS user. Ratio = user's total cpu_rate / all users' total cpu_rate × 100%.
3. **Top 3 OS Processes** (from command_cpu_usage): Aggregate by command cpu_rate, gaussdb main process (command is `gaussdb-dn` or `gaussdb-cn`) is excluded; remaining processes sorted by cpu_rate descending, take Top 3. Note: `gaussdb` (fenced UDF) is NOT a main process and should be included. The username field in command_cpu_usage is the **OS user**, which is different from the database user; do not mix them. Ratio = process's total cpu_rate / all non-main-processes' total cpu_rate × 100%.

### Step 7: Generate Diagnosis Report

Generate an HTML report following the template in the "Output Format" section. **After generating the report, save the HTML file to the current working directory (workspace root folder) with the filename `dws_cpu_diagnosis_report_{timestamp}.html`, where `{timestamp}` is the current machine local time formatted as `yyyyMMdd_HHmmss` (e.g., `dws_cpu_diagnosis_report_20260623_150421.html`).**

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
| cluster_name | Optional | Cluster name | Use cluster_id |
| alarm_severity | Optional | Alarm severity | N/A |

## Output Format

**Note**: Strictly output and return according to the template below. Do not analyze or summarize the template content, do not omit any part, do not modify the template structure. The output must be consistent with the template.

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 20px; background: #f5f7fa; color: #1d2129; }
  .report { max-width: 960px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; }
  .header { background: linear-gradient(135deg, #165dff, #0fc6c2); color: #fff; padding: 24px 32px; }
  .header h1 { margin: 0; font-size: 22px; letter-spacing: 1px; }
  .header .subtitle { margin-top: 4px; font-size: 13px; opacity: 0.85; }
  .section { padding: 20px 32px; border-bottom: 1px solid #e5e6eb; }
  .section:last-child { border-bottom: none; }
  .section-title { font-size: 16px; font-weight: 600; color: #165dff; margin: 0 0 12px 0; padding-left: 10px; border-left: 3px solid #165dff; }
  .info-grid { display: grid; grid-template-columns: 120px 1fr; row-gap: 8px; }
  .info-key { color: #86909c; font-size: 14px; text-align: right; padding-right: 12px; }
  .info-val { color: #1d2129; font-size: 14px; font-weight: 500; word-break: break-all; }
  .conclusion-item { padding: 8px 12px; margin-bottom: 6px; background: #fff7e8; border-left: 3px solid #ff7d00; border-radius: 0 4px 4px 0; font-size: 14px; }
  .conclusion-item.normal { background: #e8ffea; border-left-color: #00b42a; }
  .locate-block { margin: 6px 0 6px 16px; padding: 10px 14px; background: #f7f8fa; border-radius: 4px; font-size: 13px; }
  .locate-block .loc-row { display: flex; margin-bottom: 4px; }
  .locate-block .loc-key { width: 80px; color: #86909c; flex-shrink: 0; }
  .locate-block .loc-val { color: #1d2129; word-break: break-all; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { background: #f2f3f5; color: #4e5969; font-weight: 600; text-align: left; padding: 10px 12px; border-bottom: 2px solid #e5e6eb; }
  td { padding: 10px 12px; border-bottom: 1px solid #f2f3f5; vertical-align: top; }
  tr:hover td { background: #f7f8fa; }
  .sql-text { font-family: "Cascadia Code", "Fira Code", "Consolas", monospace; font-size: 12px; color: #4e5969; max-width: 500px; word-break: break-all; white-space: pre-wrap; }
  .pct-bar { display: inline-block; height: 16px; border-radius: 2px; background: linear-gradient(90deg, #165dff, #0fc6c2); vertical-align: middle; }
  .pct-val { margin-left: 6px; font-weight: 600; color: #165dff; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 500; }
  .tag-warn { background: #fff7e8; color: #ff7d00; }
  .tag-danger { background: #ffece8; color: #cb2634; }
  .tag-info { background: #e8f3ff; color: #165dff; }
</style>
</head>
<body>
<div class="report">

  <div class="header">
    <h1>DWS 集群 CPU 诊断报告</h1>
    <div class="subtitle">{region_id} | {resource_name}</div>
  </div>

  <div class="section">
    <div class="section-title">基本信息</div>
    <div class="info-grid">
      <span class="info-key">所属服务</span><span class="info-val">DWS</span>
      <span class="info-key">所属区域</span><span class="info-val">{region_id}</span>
      <span class="info-key">集群名称</span><span class="info-val">{resource_name}</span>
      <span class="info-key">集群ID</span><span class="info-val">{resource_id}</span>
      <span class="info-key">TOP节点</span><span class="info-val">{node_name}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">诊断结论</div>
    {diagnosis_summary}
  </div>

  <div class="section">
    <div class="section-title">CPU贡献 Top3 语句</div>
    <table>
      <tr><th style="width:40px">#</th><th style="width:180px">QueryID</th><th style="width:80px">用户</th><th style="width:80px">CPU占比</th><th style="width:160px">时间</th><th>SQL</th></tr>
      <tr><td>1</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
      <tr><td>2</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
      <tr><td>3</td><td>{query_id}</td><td>{username}</td><td>{pct}%</td><td>{start_time_beijing}</td><td class="sql-text">{query_text}</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">CPU贡献 Top3 用户</div>
    <table>
      <tr><th style="width:40px">#</th><th>用户名</th><th style="width:260px">CPU占比</th></tr>
      <tr><td>1</td><td>{user1}</td><td><span class="pct-bar" style="width:{bar1}px"></span><span class="pct-val">{pct1}%</span></td></tr>
      <tr><td>2</td><td>{user2}</td><td><span class="pct-bar" style="width:{bar2}px"></span><span class="pct-val">{pct2}%</span></td></tr>
      <tr><td>3</td><td>{user3}</td><td><span class="pct-bar" style="width:{bar3}px"></span><span class="pct-val">{pct3}%</span></td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">CPU贡献 Top3 进程（不含gaussdb主进程）</div>
    <table>
      <tr><th style="width:40px">#</th><th>进程名</th><th style="width:260px">CPU占比</th></tr>
      <tr><td>1</td><td>{process1}</td><td><span class="pct-bar" style="width:{bar1}px"></span><span class="pct-val">{pct1}%</span></td></tr>
      <tr><td>2</td><td>{process2}</td><td><span class="pct-bar" style="width:{bar2}px"></span><span class="pct-val">{pct2}%</span></td></tr>
      <tr><td>3</td><td>{process3}</td><td><span class="pct-bar" style="width:{bar3}px"></span><span class="pct-val">{pct3}%</span></td></tr>
    </table>
  </div>

</div>
</body>
</html>
```

**diagnosis_summary Fill Rules**:
- If all metrics are normal → Output `<div class="conclusion-item normal">诊断暂未发现异常</div>`
- Otherwise, output one `<div class="conclusion-item">` per anomaly, content format: `<anomaly_type>: <factual_description>`
- If a specific SQL is identified, append a location sub-block after the anomaly item div:
  ```html
  <div class="conclusion-item"><anomaly_type>: <factual_description></div>
  <div class="locate-block">
    <div class="loc-row"><span class="loc-key">SQL摘要</span><span class="loc-val">{specific_sql} (max 50 characters)</span></div>
    <div class="loc-row"><span class="loc-key">QueryID</span><span class="loc-val">{query_id}</span></div>
    <div class="loc-row"><span class="loc-key">用户名</span><span class="loc-val">{username}</span></div>
    <div class="loc-row"><span class="loc-key">启动时间</span><span class="loc-val">{start_time_beijing}</span></div>
  </div>
  ```
- High concurrency and single statement can both appear as independent anomaly items
- Anomaly items can use tags for readability: System cause uses `<span class="tag tag-warn">系统</span>`, Customer-side cause uses `<span class="tag tag-danger">客户侧</span>`, High concurrency uses `<span class="tag tag-info">高并发</span>`

**Top 3 Statements Fill Rules**:
- Data source: Top 3 statements from cpu_io_diagnose_detail, sorted by cpu_rate descending
- **cpu_rate is already an instance-level percentage** (e.g., 76.5% means this query uses 76.5% CPU on that instance). Use the cpu_rate value directly as the CPU ratio; do NOT re-calculate by dividing by global total or node total
- Each row in cpu_io_diagnose_detail represents one query execution on one instance; treat each row independently when sorting for Top 3
- QueryID: From query_id field; multiple similar SQLs are comma-separated with count annotation (e.g., "73183494456652581等4条")
- Username: From username field
- Time: When duration_ms exists, it is ctime - duration_ms converted to Beijing time, column header shows "启动时间"; When duration_ms is absent, use ctime converted to Beijing time, column header shows "采集时间"
- CPU Ratio: Use cpu_rate field value directly (already a percentage), keep 1 decimal place (e.g., 76.5%)
- SQL: From query field, display up to 1024 characters; truncate with "..." if exceeded
- gaussdb main process is not listed as an independent statement; its CPU overhead is merged into the corresponding root cause description
- If no statement data (e.g., cpu_io_diagnose_detail is empty), fill the table with "无法获取"

**Top 3 Users Fill Rules**:
- Data source: cpu_rate aggregated by username from cpu_io_diagnose_detail
- The username here is the **database user**, NOT the OS user. Do not use the username field from command_cpu_usage
- Only count database users with state=active
- Ratio = user's total cpu_rate / all users' total cpu_rate × 100%
- If fewer than 3 data points, list actual count
- pct-bar width calculation: `width = Math.round(ratio / max_ratio * 200)`, where max_ratio is the top user's ratio

**Top 3 Processes Fill Rules**:
- Data source: cpu_rate aggregated by command from command_cpu_usage
- The username field in command_cpu_usage is the **OS user**, which is different from the database user in cpu_io_diagnose_detail; do not mix the two
- **Gaussdb main process exclusion**: Exclude rows where `command` is `gaussdb-dn` or `gaussdb-cn` (their CPU is attributed to SQL statements and root causes). Do NOT exclude `gaussdb` (fenced UDF master process) — it is a subprocess and should be included in Top 3
- Remaining processes sorted by cpu_rate descending, take Top 3
- Ratio = process's total cpu_rate / all non-main-processes' total cpu_rate × 100%
- Process display name: Use the `command` field value directly (e.g., `gaussdb`, `python3`, `java`, `sh`, `cm_agent`, `gs_gtm`). When multiple entries with the same command have different `args`, they are aggregated under the same command name
- If node_process_cpu_top20 returns null and command_cpu_usage is also empty, fill the table with "无法获取"
- pct-bar width calculation same as Top 3 Users

**General Fill Rules**: Cluster name prefers cluster_name; if empty, use cluster_id; When node_name is empty, fill "集群级告警"; gaussdb main process (command is `gaussdb-dn` or `gaussdb-cn`) CPU usage is merged into the corresponding root cause description; gaussdb fenced UDF (command is `gaussdb`) is NOT a main process and appears in Top 3 Processes; Multiple similar SQLs are described as "N条同类xxx查询"; All times must be in Beijing time; Statement summary exceeding 50 characters is truncated with "..."; Output is a complete HTML document that can be rendered directly in a browser; `<` `>` `&` in SQL text must be escaped as `&lt;` `&gt;` `&amp;`.

## Best Practices

1. **Timestamp Handling**: first_alarm_time is already a millisecond timestamp; use it directly for tool parameters. Do not convert to time string first and then back to timestamp (to avoid 8-hour offset)
2. **Tool Selection**: Choose between KooCLI and MCP, preferring KooCLI; once selected, use that method throughout
3. **Paginated Queries**: All tool calls uniformly use limit=200 pagination until returned count < 200, then merge all paginated data. cpu_io_diagnose_detail has the largest data volume; pagination is required
4. **Report Time**: All timestamps must be converted to Beijing time (UTC+8). Can use `python -c "from datetime import datetime,timezone,timedelta; print(datetime.fromtimestamp({ms}/1000,tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'))"`
5. **SQL Display**: Top 3 statements show up to 1024 characters of specific SQL; truncate with "..." if exceeded; SQL summary in diagnosis_summary is up to 50 characters
6. **Node Filtering Optimization**: When parsing CpuStat in Step 1, calculate max and average CPU usage per node separately; when cluster node count > 6, only focus on TOP 3 nodes; if TOP nodes' max vs avg difference < 20%, subsequent steps only analyze TOP 3, otherwise analyze all high CPU nodes

## References

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation and configuration |
| [MCP Installation Guide](references/dws-mcp-installation-guide.md) | DWS Autopilot MCP Server installation and configuration |
| [IAM Policies](references/iam-policies.md) | Required permissions and policy JSON |
| [Metric Reference](references/metric-reference.md) | Metric key fields and query differences |

## Notes

- **Security**: Never expose AK/SK values in conversations or commands; never ask users to input AK/SK directly in conversation
- **Time Protocol**: from_ts/to_ts must use millisecond timestamps; report displays Beijing time; when converting Beijing time to timestamp, must append +08:00 timezone suffix; do not mentally calculate timestamp values; do not convert existing millisecond timestamps to time strings and then back
- **Output Constraints**: Strictly output the diagnosis report following the Output Format section template; do not modify template structure, do not omit any part, do not add remediation suggestions, do not output SQL optimization statements, do not use emoji, do not use custom format tags
- **Data Authenticity**: All diagnosis conclusions must come from actual tool return results; when tool returns empty or call fails, mark as "无法获取"; fabricating values is prohibited
- **Known Limitations**: hcloud does not support --order_by and --sort_by parameters; sort by ctime descending locally after query; cpu_io_diagnose_detail does not support host_id filtering; query full cluster then filter locally; cpu_io_diagnose_detail returns flat row structure (one query per row), not nested active_queries array; node_process_cpu_top20 may return null; command_cpu_usage `command` field differentiates `gaussdb-dn`/`gaussdb-cn` (main process, excluded from Top 3) from `gaussdb` (fenced UDF, included)
