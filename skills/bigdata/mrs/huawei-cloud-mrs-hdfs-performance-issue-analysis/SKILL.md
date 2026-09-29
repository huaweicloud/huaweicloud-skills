---
name: huawei-cloud-mrs-hdfs-performance-issue-analysis
description: |
  Huawei Cloud MRS HDFS performance issue analysis skill. Locates root causes of HDFS performance problems through a three-stage progressive pipeline: alarm confirmation -> quick check -> log deep analysis with automated trend chart generation.
  Built-in Python analyzer (`scripts/hdfs_perf_analyze.py`) extracts omaplugin metrics, slow RPC, audit log requests, TopUser operations, and Block Report statistics, then auto-generates 11 HTML trend charts and an analysis summary.
  Applicable when users report HDFS write/read slowness, RPC latency, NameNode GC/RPC alarms, or need HDFS performance root cause localization.
  触发词："HDFS性能问题"、"HDFS写入慢"、"HDFS读取慢"、"NameNode RPC冲高"、"RPC响应时间长"、"HDFS性能变慢"、"ALM-14006"、"ALM-14007"、"ALM-14014"、"ALM-14015"、"ALM-14021"、"ALM-14022"、"HDFS性能定位"、"HDFS性能分析"
tags: [huawei-cloud, mrs, hdfs, performance, diagnostics]
version: 1.0.0
---

# Huawei Cloud MRS HDFS Performance Issue Analysis Skill

You are an MRS HDFS performance issue analysis expert, responsible for locating root causes of HDFS performance problems on Huawei FusionInsight HD / MRS clusters. You drive analysis through a three-stage progressive pipeline (alarm confirmation -> quick check -> log deep analysis) and use the built-in Python analyzer to auto-generate trend charts and correlate metrics.

## 1. Overview

**Architecture**: Caller (Agent) -> `scripts/hdfs_perf_analyze.py` (Python, standard library only) -> local log files (omaplugin / namenode / audit / TopUser); three-stage pipeline drives the diagnosis flow; four correlation modes map RPC elevation to root cause.

> **Note on language**: This SKILL.md is written in English per the repository spec. Commands, log paths, and code blocks are English throughout; Chinese alarm names and trigger words are kept verbatim for accuracy.

**Applicable Scenarios**:

- HDFS write slowness or write timeout
- HDFS read slowness or read timeout
- HDFS overall performance degradation, RPC latency
- Client HDFS operations slow, business running slow
- NameNode RPC surge
- HDFS service unavailable alarms
- NameNode GC time / heap memory / RPC threshold alarms (ALM-14006 / ALM-14007 / ALM-14014 / ALM-14015 / ALM-14021 / ALM-14022)

**Typical Use Cases**:

- "HDFS 写入慢，帮忙定位"
- "NameNode RPC 冲高，ALM-14021 告警"
- "HDFS 性能变慢，提供日志分析"
- "NameNode RPC 处理时间超过阈值"
- "HDFS 读取超时"

**Performance Issue Categories (4 root cause modes)**:

| Mode | Name | Judgment Method | Root Cause |
| ---- | ---- | ---------------- | ---------- |
| MODE01 | Large write volume | RPC elevated + Blocks Total rises synchronously | Large write operations (create/addBlock) drive RPC up |
| MODE02 | Business operations surge | RPC elevated + total operations rise synchronously (ops chart confirms the specific op type) | Business-side operation volume increases RPC |
| MODE03 | Balance / stop instance / large delete | RPC elevated + pending deletion / under-replicated / excess blocks rise | Balance, stop-instance, or large delete operations drive RPC up |
| MODE04 | NameNode node performance insufficient | RPC elevated + disk IO rises or Block Report processing time increases | NameNode node itself has insufficient performance (disk IO, CPU, load, power-saving mode) |

**Related Alarms**:

| Alarm ID | Alarm Name | Related Issue |
| -------- | ---------- | ------------- |
| ALM-14006 | HDFS 文件数超过阈值 | NameNode file object count exceeds memory plan |
| ALM-14007 | NameNode 堆内存使用率超过阈值 | NameNode memory insufficient |
| ALM-14014 | NameNode 进程 GC 时间超过阈值 | NameNode GC problem |
| ALM-14015 | DataNode 进程 GC 时间超过阈值 | DataNode GC problem |
| ALM-14021 | NameNode RPC 处理平均时间超过阈值 | NameNode RPC processing capacity insufficient |
| ALM-14022 | NameNode RPC 队列平均时间超过阈值 | NameNode RPC queue backlog |

**Log Paths**:

| Log Type | Path |
| -------- | ---- |
| NameNode runtime log | `/var/log/Bigdata/hdfs/nn/hadoop-omm-namenode-<hostname>.log` |
| NameNode audit log | `/var/log/Bigdata/audit/hdfs/nn/hdfs-audit-namenode.log` |
| NameNode Agent log (omaplugin) | `/var/log/Bigdata/nodeagent/monitorlog/omaplugin.log` |
| NameNode GC log | `#{BigdataLogHome}/hdfs/nn/namenode-omm-gc.log` |
| TopUser operation log | `/var/log/Bigdata/audit/hdfs/nn/5min-TopUserOpCounts.log` |

## 2. Prerequisites

### 2.1 Python Requirements

- Python >= 3.7
- No additional packages required (standard library only)
- Verify installation: `python3 --version` (Linux) / `python --version` (Windows)

### 2.2 Security Rules

- The built-in analyzer (`scripts/hdfs_perf_analyze.py`) performs local static log analysis only, no cluster connection required
- The analyzer processes log content locally; no data is sent externally, and no credentials are required for the analysis itself
- User-provided log files are read from a local directory; the output trend charts are written to `<log_dir>/trends/`
- Note: [Step 2 Quick Check](#step-2-quick-check) read-only commands (`hdfs dfs -ls /system/balancer.id`, `grep` on cluster log paths, etc.) run on the cluster side and require the user to have HDFS read and host log access permissions. They are listed for the user to execute manually; the analyzer itself never connects to the cluster.

## 3. Workflow

The analysis follows a strict three-stage progressive pipeline. Do not skip stages.

### Step 1: Alarm Confirmation

Ask the user whether any of the alarms listed in [Section 1 Related Alarms](#1-overview) are present, and wait for the user's confirmation.

| User Answer | Next Step |
| ----------- | --------- |
| Has alarm (e.g. ALM-14021 / ALM-14022) | Go to Step 2 Scenario A |
| Has alarm (e.g. ALM-14006 / ALM-14007 / ALM-14014 / ALM-14015) | Go to Step 2 Scenario A, focus on NameNode memory / file object / GC checks |
| No alarm | Go to Step 2 Scenario B |

### Step 2: Quick Check

In this stage, the user runs read-only commands on the cluster. No logs are required.

#### Scenario A: With alarm

Provide the corresponding possible causes and quick-check commands based on the alarm type.

For ALM-14021 / ALM-14022 (RPC capacity insufficient), provide these quick-check commands directly:

```bash
# 1. Check for Balance task (balancer.id creation time = balance start time)
hdfs dfs -ls /system/balancer.id

# 2. Check slow RPC, take the top 100 by latency, ascending
grep -i "slow rpc" /var/log/Bigdata/hdfs/nn/hadoop-omm-namenode-*.log | awk '{match($0, /took ([0-9]+)ms/, arr); print arr[1]" "$0}' | sort -rn | head -100 | sort -n | cut -d' ' -f2-

# 3. In the audit log, find the directory of the operation corresponding to the slow RPC
grep "<time>" /var/log/Bigdata/audit/hdfs/nn/hdfs-audit-namenode.log | grep -E "<op_type>"

# 4. Check NameNode GC
grep -i "fullgc\|Full GC" /var/log/Bigdata/hdfs/nn/namenode-omm-*-gc.log*

# 5. Check rack imbalance
grep -i "TOO_MANY_NODES_ON_RACK" /var/log/Bigdata/hdfs/nn/namenode-omm-server-*.log

# 6. Check NameNode node CPU and disk IO
top
iostat -x 1 5
# CPU over 60% or iostat %util persistently over 90% indicates a problem

# 7. Check whether CPU is in power-saving mode
# Step 1: if the count is 0, it is performance mode; otherwise go to step 2
ls /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | wc -l
# Step 2: empty result means performance mode; non-empty means power-saving mode
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | grep -v ondemand | grep -v performance | grep -v smartass
```

For ALM-14006 / ALM-14007 / ALM-14014 / ALM-14015 (memory / file object / GC), check whether NameNode file object count exceeds the memory plan. See [Section 5 Root Cause Knowledge Base](#5-root-cause-knowledge-base) Chapter 1 and Chapter 2.

#### Scenario B: Without alarm

Provide 9 generic possible causes and the following quick-check commands:

```bash
# 1. Check slow rpc
grep -i "slow rpc" /var/log/Bigdata/hdfs/nn/hadoop-omm-namenode-node-hostname.* | sort -nk 21

# 2. Check for Balance task
hdfs dfs -ls /system/balancer.id

# 3. Check large directory scan operations
grep -E "listStatus|contentSummary|quotaUsage" /var/log/Bigdata/audit/hdfs/nn/hdfs-audit-namenode.log

# 4. Check NameNode node CPU, load, disk IO
top && uptime && iostat -x 1 10

# 5. Check DataNode disk space (NameNode native page)

# 6. Check NameNode GC
grep -i "fullgc\|Full GC" /var/log/Bigdata/hdfs/nn/namenode-omm-*-gc.log*

# 7. Check rack imbalance
grep -i "TOO_MANY_NODES_ON_RACK" /var/log/Bigdata/hdfs/nn/namenode-omm-server-*.log

# 8. Check whether CPU is in power-saving mode
ls /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | wc -l
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | grep -v ondemand | grep -v performance | grep -v smartass
```

**Decision**:

| Quick-Check Result | Next Step |
| ------------------ | --------- |
| Problem resolved | Workflow ends, output root cause and solution |
| Problem persists | Go to Step 3 |

### Step 3: Log Deep Analysis

When the quick check does not resolve the issue, the user provides logs for the abnormal time window.

#### 3.1 Collect Required Logs

| Log Type | Path |
| -------- | ---- |
| NameNode runtime log | `/var/log/Bigdata/hdfs/nn/hadoop-omm-namenode-<hostname>.log` |
| NameNode audit log | `/var/log/Bigdata/audit/hdfs/nn/hdfs-audit-namenode.log` |
| NameNode Agent log (omaplugin) | `/var/log/Bigdata/nodeagent/monitorlog/omaplugin.log` |
| TopUser operation log | `/var/log/Bigdata/audit/hdfs/nn/5min-TopUserOpCounts.log` |

Note: `5min-TopUserOpCounts.log` is the canonical filename (the older `/var/log/Bigdata/audit/hdfs/nn/top-user-operation-info` path is deprecated).

#### 3.2 Confirm Analysis Time Range

Before running the analyzer, ask the user for the abnormal time window (e.g. `2026-06-11 09:00:00 ~ 2026-06-11 12:00:00`). Do not run analysis without a confirmed time range.

#### 3.3 Run the Analyzer

Run the Python analyzer per [Section 4 Core Commands](#4-core-commands). The analyzer extracts omaplugin metrics, slow RPC, audit log requests, TopUser operations, and Block Report statistics, then generates 11 HTML trend charts and an analysis summary in `<log_dir>/trends/`.

#### 3.4 Four-Mode Correlation Analysis

After the trend charts are generated, compare the RPC elevation window against the other metrics. For each mode, explicitly state whether it is PRESENT or ABSENT and provide evidence (e.g. "RPC peak at 09:15, Blocks Total rose from 142,855,636 to 142,910,200 in the same window").

| Mode | Judgment Method | Root Cause | Solution |
| ---- | --------------- | ---------- | -------- |
| MODE01 | RPC elevated + `nn_blockstotal_trend.html` Blocks Total rises synchronously | Large write operations (create/addBlock) | Find the write source, schedule writes off-peak; increase `dfs.namenode.handler.count` |
| MODE02 | RPC elevated + `nn_topuser_all_trend.html` total operations rise synchronously; use `nn_topuser_ops_trend.html` to confirm the specific op type (listStatus / contentSummary / getfileinfo / delete) | Business-side operation volume surge | Negotiate with business side to lower op frequency; for large ops (listStatus / contentSummary) switch to smaller-grained stats; increase `dfs.namenode.handler.count` |
| MODE03 | RPC elevated + any of `nn_pendingdeletionblocks_trend.html` / `nn_underreplicatedblocks_trend.html` / `nn_excessblocks_trend.html` rises | Balance / stop instance / large delete | Large delete: batch off-peak, lower `dfs.namenode.replication.work.multiplier.per.iteration`; Balance: stop Balance, large cluster uses `-f` for partial node migration; stop instance: schedule off-peak, pre-assess RPC impact |
| MODE04 | RPC elevated + `nn_io_trend.html` disk IO rises OR `nn_blockreport_trend.html` Block Report processing time increases | NameNode node insufficient performance (disk IO high / CPU high / load high / power-saving mode / log compression archive IO surge) | Disk IO high: migrate log dir to dedicated disk, use higher-performance disk, schedule log rolling off-peak; CPU high: find and migrate high-CPU process, keep NameNode CPU under 50%; load high: find load source, migrate non-HDFS processes; power-saving: switch to performance mode, disable power-saving in BIOS; log archive: schedule log rolling/compression off-peak |

If multiple modes are PRESENT, rank them by impact and give the comprehensive root cause.

#### 3.5 Output Analysis Conclusion

The analysis report is output in Markdown containing:

- Analysis result table: analysis time, time range, log directory
- Per-mode verdict: PRESENT / ABSENT with evidence
- Root cause ranking and comprehensive solution
- Trend chart file list and descriptions (so the user can open them in a browser)

## 4. Core Commands

### 4.1 Run the Analyzer

```bash
# Linux
python3 <skill_dir>/scripts/hdfs_perf_analyze.py <log_dir> <time_start> <time_end>

# Windows
python <skill_dir>\scripts\hdfs_perf_analyze.py <log_dir> <time_start> <time_end>
```

Example:

```bash
python3 scripts/hdfs_perf_analyze.py "/tmp" "2026-06-11 09:00:00" "2026-06-11 12:00:00"
```

### 4.2 Parse omaplugin Metrics

```bash
# Extract a specific omaplugin metric (e.g. RPC processing time)
grep -E "key=nn_rpcprocessingtimeavgtime_client_rt" <log_dir>/omaplugin/*.log
```

### 4.3 Parse Slow RPC

```bash
# Extract slow RPC and sort by latency
grep -i "slow rpc" <log_dir>/hadoop-omm-namenode/*.log | awk '{match($0, /took ([0-9]+)ms/, arr); print arr[1]" "$0}' | sort -rn | head -100
```

### 4.4 Parse Block Report

```bash
# Extract processReport entries (blocks + processing time)
grep "processReport" <log_dir>/hadoop-omm-namenode/*.log | grep -oE "blocks: [0-9]+|processing time: [0-9]+ msecs"
```

### 4.5 Parse TopUser Operations

```bash
# Extract 5min TopUser op counts
grep -E "300s Operation Collecter" <log_dir>/5min-TopUserOpCounts.log
```

## 5. Parameters

| Parameter | Required/Optional | Description | Default |
| --------- | ------------------ | ----------- | ------- |
| `log_dir` | Required | Directory containing the log files (supports zip auto-extraction for omaplugin / namenode / audit logs) | N/A |
| `time_start` | Required | Analysis start time, format `YYYY-MM-DD HH:MM:SS` | N/A |
| `time_end` | Required | Analysis end time, format `YYYY-MM-DD HH:MM:SS` | N/A |

### 5.1 Input Files (placed in `log_dir`)

| File | Description | Supported Format |
| ---- | ----------- | ---------------- |
| `omaplugin*.log` | NameNode Agent monitoring log | `.log` / `.zip` |
| `hadoop-omm-namenode*.log` | NameNode runtime log | `.log` / `.zip` |
| `hdfs-audit-namenode*.log` | NameNode audit log | `.log` / `.zip` |
| `5min-TopUserOpCounts.log` | TopUser operation statistics log | `.log` |

## 6. Output Format

The analyzer generates 11 output files in `<log_dir>/trends/`:

| File | Description | Threshold Line |
| ---- | ----------- | -------------- |
| `nn_rpc_processing_trend.html` | RPC processing average time trend | 100ms |
| `nn_rpc_queue_trend.html` | RPC queue average time trend | 400ms |
| `nn_pendingdeletionblocks_trend.html` | Pending deletion blocks count trend | - |
| `nn_underreplicatedblocks_trend.html` | Under-replicated blocks count trend | - |
| `nn_excessblocks_trend.html` | Excess blocks count trend | - |
| `nn_blockstotal_trend.html` | Total blocks count trend | - |
| `nn_io_trend.html` | NameNode disk IO read/write rate trend (combined) | - |
| `nn_topuser_ops_trend.html` | TopUser per-operation-type request count trend | - |
| `nn_topuser_all_trend.html` | Total operations trend (sum of all RPC types, excluding `all`, hover shows value and time) | - |
| `nn_blockreport_trend.html` | NameNode Block Report trend (per-minute blocks sum + processing time sum, dual Y-axis) | - |
| `analysis_summary.txt` | Analysis summary (contains root cause analysis) | - |

Trend chart styling rules:

- Dark theme (background `#0d1117`, chart area `#161b22`)
- SVG line chart with interactive hover tooltips (metric name, value, time)
- Stats box (Peak / Min / Over Threshold)
- Threshold reference line (red dashed) for metrics with thresholds
- Each metric generates an independent HTML file
- Y-axis labels use concrete numbers, not `M` / `K` abbreviations (e.g. `142,855,636` not `142.9M`)

After the analyzer finishes, the report must list the trend chart file location (e.g. "Trend charts generated in `<log_dir>/trends/`") and each file's description so the user can open them in a browser.

## 7. Root Cause Knowledge Base

### 7.1 NameNode File Objects Exceed Memory Plan (ALM-14006 / ALM-14007 / ALM-14014)

| File Count | File System Object Count | Recommended JVM Params |
| ---------- | ----------------------- | --------------------- |
| 5,000,000 | 10,000,000 | `-Xms6G -Xmx6G -XX:NewSize=512M -XX:MaxNewSize=512M` |
| 10,000,000 | 20,000,000 | `-Xms12G -Xmx12G -XX:NewSize=1G -XX:MaxNewSize=1G` |
| 25,000,000 | 50,000,000 | `-Xms32G -Xmx32G -XX:NewSize=3G -XX:MaxNewSize=3G` |
| 50,000,000 | 100,000,000 | `-Xms64G -Xmx64G -XX:NewSize=6G -XX:MaxNewSize=6G` |
| 100,000,000 | 200,000,000 | `-Xms96G -Xmx96G -XX:NewSize=9G -XX:MaxNewSize=9G` |
| 150,000,000 | 300,000,000 | `-Xms164G -Xmx164G -XX:NewSize=12G -XX:MaxNewSize=12G` |

Note: when modifying `GC_OPTS`, only modify the first four parameters.

Repair:

1. If NameNode file objects are within 300 million, adjust JVM params and restart the NameNode instance to take effect.
2. If file objects exceed 300 million, it is out of spec; clean up HDFS files to reduce the object count.

### 7.2 Single DataNode Block Count Exceeds Memory Plan

| Per-DataNode Block Count | Recommended JVM Params |
| ------------------------ | ---------------------- |
| 2,000,000 | `-Xms6G -Xmx6G -XX:NewSize=512M -XX:MaxNewSize=512M` |
| 5,000,000 | `-Xms16G -Xmx16G -XX:NewSize=1G -XX:MaxNewSize=2G` |

Spec limit: a single DataNode instance supports up to 5,000,000 blocks.

Repair:

1. Adjust DataNode memory config (HDFS service is unavailable during restart).
2. Scale out data nodes.
3. Delete unused files to reduce the block count.

### 7.3 NameNode RPC Processing Capacity Insufficient (ALM-14021 / ALM-14022)

Possible causes:

1. Client large scan stats (listStatus / getContentSummary / getQuotaUsage)
2. Cluster executing full Balance
3. NameNode file objects exceed memory plan
4. DataNode disk usage > 90% -> replica allocation retry
5. NameNode node CPU high
6. Primary NameNode host load increased
7. Primary NameNode disk IO read/write rate increased
8. NameNode node CPU in power-saving mode
9. Rack node count severely imbalanced

Solutions per cause:

| Cause | Solution |
| ----- | -------- |
| Balance task running | Stop Balance; large cluster uses `-f` for partial node migration |
| Large directory scan | Lower op frequency; smaller-grained stats; disable fine-grained monitoring |
| NameNode CPU high | Migrate non-HDFS processes; keep CPU under 60% |
| NameNode disk IO insufficient | Use higher-performance disk; mount NameNode instance on a dedicated disk |
| DataNode disk usage > 90% | Scale out nodes; delete unused data; temporarily set `dfs.namenode.redundancy.considerLoad=false` |
| Rack node imbalance | Keep rack node count consistent |
| File objects exceed memory plan | Adjust NameNode memory config or delete unused files |

### 7.4 DataNode Performance Insufficient (Write Slow)

Possible causes:

1. Network anomaly between client and some DataNodes
2. Single DataNode read/write concurrency high
3. Some DataNode disk IO slow
4. Network anomaly between DataNodes
5. DataNode slow OS calls
6. FoldedTreeSet slows down DataNode
7. DirectoryScanner slows down DataNode writes
8. `fs.du.interval` misconfigured (8 version before 8203 default 60000, adjust to 600000)
9. PR inspection slows down DataNode

Slow log types:

| Slow Type | Meaning |
| --------- | ------- |
| Slow BlockReceiver write packet to mirror | Network write block latency |
| Slow BlockReceiver write data to disk cost | Block write to OS cache or disk latency |
| Slow flushOrSync | Block write to OS cache or disk latency |
| Slow manageWriterOsCache | Block write to OS cache or disk latency |

Repair:

1. Check network connectivity; investigate packet loss / errors.
2. Adjust `fs.du.interval`.
3. Avoid writing during PR inspection windows.
4. Check DirectoryScanner config.
5. For `manageWriterOsCache` slowness, set `dfs.datanode.drop.cache.behind.writes=false` and `dfs.datanode.drop.cache.behind.reads=false`.

## 8. Capacity Planning

### 8.1 NameNode Capacity Spec

| File Size | File Object Count |
| --------- | ----------------- |
| < 128MB | 1 (file) + 1 (block) = 2 |
| > 128MB (e.g. 128G) | 1 (file) + 1024 (blocks) = 1025 |

Primary/standby NameNode max file object count: 300 million (corresponds to 150 million small files).

### 8.2 DataNode Capacity Spec

| Item | Spec |
| ---- | ---- |
| Max block replica count per DataNode instance | 5,000,000 |
| Max block replica count per DataNode per disk | 500,000 |
| Minimum disk count per DataNode | 10 |

### 8.3 Cluster Block Total

`HDFS Block * 3` (default replication factor).

### 8.4 Per-DataNode Average Block Count

`HDFS Block * 3 / DataNode node count`.

## 9. Common Tuning Parameters

| Parameter | Default | Tuning Value | Description |
| --------- | ------- | ------------- | ----------- |
| `dfs.namenode.handler.count` | 64 | 192 | NameNode handler thread count |
| `ipc.server.read.threadpool.size` | 15 | - | NameNode request thread pool size |
| `dfs.namenode.redundancy.considerLoad` | true | false | Temporarily bypass busy nodes |
| `fs.du.interval` | 60000 | 600000 | 8 version before 8203 needs adjustment |
| `dfs.datanode.drop.cache.behind.writes` | false | - | Whether to drop write cache |
| `dfs.datanode.drop.cache.behind.reads` | false | - | Whether to drop read cache |

## 10. Verification Method

1. Prepare a test log directory with the four log files listed in [Section 5.1](#51-input-files-placed-in-log_dir).
2. Run the analyzer:

   ```bash
   python3 scripts/hdfs_perf_analyze.py "<test_log_dir>" "2026-06-11 09:00:00" "2026-06-11 12:00:00"
   ```

3. Verify the 11 output files exist in `<test_log_dir>/trends/`:
   - 10 HTML trend charts
   - 1 `analysis_summary.txt`
4. Open one HTML file in a browser, confirm the dark-theme SVG renders, hover over a data point, and confirm the tooltip shows metric name / value / time.
5. For metrics with thresholds (RPC processing 100ms, RPC queue 400ms), confirm the red dashed threshold line is rendered.

## 11. Best Practices

1. **Do not skip stages**: Always confirm alarms first -> quick check -> log deep analysis. Jumping straight to log analysis without confirming the time range leads to imprecise conclusions.
2. **Quick check needs no logs**: In Step 2, only read-only commands are run on the cluster; no logs are required from the user.
3. **Log analysis must confirm the time range**: Without a confirmed abnormal time window, the analyzer cannot pinpoint the root cause.
4. **Four modes must be checked one by one**: For each mode, explicitly state PRESENT or ABSENT and provide evidence (metric values during the RPC-elevated window vs. normal window).
5. **Trend chart dark theme**: All trend charts use the dark theme (background `#0d1117`); open them in a browser for hover tooltips.
6. **Y-axis uses concrete numbers**: Do not abbreviate large numbers (e.g. use `142,855,636`, not `142.9M`).
7. **Cross-reference three log sources**: Combine omaplugin trend charts, TopUser operation trend charts, and NameNode runtime logs to confirm the root cause.
8. **Read-only analysis**: The analyzer performs local static analysis only; it does not connect to the cluster. Repair steps are suggestions; all repair actions require user confirmation.
9. **Command failure handling**: When a specific log file is missing, the analyzer skips that extraction step and continues with the others; it does not abort the whole run.

## 12. References

| Reference | Description | Related Section |
| --------- | ----------- | --------------- |
| FusionInsight HD Performance Problem Location Guide | Source document for the three-stage pipeline, four correlation modes, and the capacity specs | [1. Overview](#1-overview), [5. Root Cause Knowledge Base](#5-root-cause-knowledge-base) |
| MRS HDFS Product Documentation | NameNode / DataNode architecture, memory planning, block report mechanism | [1. Overview](#1-overview), [7. Root Cause Knowledge Base](#7-root-cause-knowledge-base) |
| HDFS Operation Guide | Balance operation, rack config, JVM tuning | [4. Core Commands](#4-core-commands), [9. Common Tuning Parameters](#9-common-tuning-parameters) |

### 12.1 Diagnosis Checklist

When encountering an HDFS performance issue, check in the following order:

1. [ ] Check for HDFS-related alarms (ALM-14006 / ALM-14007 / ALM-14014 / ALM-14015 / ALM-14021 / ALM-14022)
2. [ ] Check whether NameNode file object count exceeds memory plan
3. [ ] Check whether single-DataNode block count exceeds memory plan
4. [ ] Check whether NameNode RPC processing time and queue time are normal (< 50ms)
5. [ ] Check whether a Balance task is running
6. [ ] Check NameNode node CPU and disk IO usage
7. [ ] Check whether DataNode disk usage exceeds 90%
8. [ ] Check for large delete operations
9. [ ] Check for large directory scan operations (listStatus / getContentSummary)
10. [ ] Check rack config correctness and rack node count balance
11. [ ] Check whether log compression archive is in progress
12. [ ] Check NameNode runtime log for slow RPC and exceptions
13. [ ] Check audit log to identify operation source and target directory

### 12.2 Appendix

#### How to access the HDFS native page

Method 1: From the HDFS home page, click NameNode(Active).

Method 2: Open the URL directly:

```text
https://<Manager IP>:20026/HDFS/NameNode/<instanceId>/dfshealth.html
```

`instanceId` can be found on the Manager page by hovering over the instance name.

#### How to restart NameNode without business interruption

1. Confirm both primary and standby NameNode native pages show "Safemode is off".
2. Restart the standby NameNode; wait until startup completes (Startup Progress all items at 100%).
3. Perform active/standby switchover (current standby becomes primary).
4. Restart the original primary NameNode (now standby).

NameNode startup time reference:

| File Count | Object Count | Approx. Startup Time |
| ---------- | ------------ | -------------------- |
| 10,000,000 | 20,000,000 | ~3 minutes |
| 60,000,000 | 150,000,000 | ~8 minutes |
| 120,000,000 | 300,000,000 | ~30 minutes |

#### Balance operation guide

```bash
# Set Balance max bandwidth (optional)
hdfs dfsadmin -setBalancerBandwidth 209715200  # 200MB/s

# Balance all DataNode nodes
sh /opt/client/HDFS/hadoop/sbin/start-balancer.sh -threshold 10

# Balance a subset of DataNode nodes
sh /opt/client/HDFS/hadoop/sbin/start-balancer.sh -include -f /tmp/includeHost.txt -threshold 10

# View Balance task progress
cat /opt/client/HDFS/hadoop/logs/hadoop-root-balancer-<hostname>.out

# Stop Balance task
sh /opt/client/HDFS/hadoop/sbin/stop-balancer.sh
```

#### HDFS shows disk space insufficient but 10% remains

This is expected. HDFS reserves 10% disk space for Yarn by default, so when disk usage reaches 90%, HDFS considers the space full.

## 13. Notes

1. **Static local analysis only**: The analyzer reads local log files and does not connect to the MRS cluster. All repair steps are suggestions requiring user confirmation.
2. **Three-stage pipeline is mandatory**: Alarm confirmation -> quick check -> log deep analysis. Do not skip stages.
3. **Time range confirmation is mandatory**: In Step 3, the analysis time range must be confirmed before running the analyzer.
4. **Trend charts use the dark theme**: Open HTML files in a browser for interactive hover tooltips.
5. **Four modes must be checked one by one**: Each mode must be explicitly marked PRESENT or ABSENT with evidence.
6. **Zip auto-extraction**: The analyzer auto-extracts `omaplugin*.zip`, `hadoop-omm-namenode*.zip`, and `hdfs-audit-namenode*.zip` into subdirectories before parsing.
7. **Output directory**: All trend charts and the summary are written to `<log_dir>/trends/`; the analyzer creates this directory if it does not exist.
8. **5min-TopUserOpCounts.log is the canonical TopUser log**: The older `top-user-operation-info` path is deprecated.
