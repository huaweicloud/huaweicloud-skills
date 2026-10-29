---
name: huawei-cloud-alarm-reduce-noise
tags: [huawei-cloud, alarm, ces, aom, noise-reduction, alarm-optimization]
triggers: 告警降噪, 告警优化, 告警治理, 告警收敛, 告警风暴, 告警太多, 分析告警, CES告警, AOM告警, 华为云告警, 告警分析报告, 生成告警报告, alarm noise reduction, alarm optimization
description: >
  Huawei Cloud CES+AOM alarm noise reduction analysis skill. Analyzes CES
  (Cloud Eye Service) and AOM (Application Operations Management) alarm data,
  identifies high-frequency alarms, and generates noise reduction recommendations
  and optimization plans. Analysis covers four dimensions: alarm governance,
  alarm convergence, alarm correlation, and long-unresolved alarms. Supports
  core resource filtering and outputs an HTML optimization report. Use this skill
  when the user mentions 告警降噪, 告警优化, 告警治理, 告警收敛, 告警风暴,
  告警太多, 分析告警, CES告警, AOM告警, 华为云告警, 告警分析报告, 生成告警报告,
  or needs to (1) analyze alarm data distribution and trends, (2) identify alarm
  types that need priority handling, (3) generate noise reduction strategies and
  recommendations, (4) output an HTML optimization report.
---

# Huawei Cloud Alarm Reduce Noise

## Overview

This skill analyzes Huawei Cloud CES (Cloud Eye Service) and AOM (Application Operations Management) alarm data, generates noise reduction recommendations across four dimensions, and outputs an HTML report:

1. **Alarm Governance** - Route grouping, deduplication analysis, suppression rules, silence rules (aligned with AOM noise reduction chain's 4 stages)
2. **Alarm Convergence** - Alarm storm identification, route grouping suggestions, alarm temporal correlation analysis
3. **Alarm Correlation** - Root cause analysis, derived alarm identification, suppression rule suggestions
4. **Long-Unresolved Alarms** - Tiered by 7/14/30/90 days, identifies long-unresolved alarms

Regions and core resources are automatically loaded from the key resource marker table (assets/关键资源标记表.xlsx). Only core resource alarms are analyzed.

Authentication: Huawei Cloud AK/SK via environment variables (HW_ACCESS_KEY / HW_SECRET_KEY), using hcloud CLI to call CES and AOM APIs.

Multi-region format: region list is auto-read from the key resource marker table. The HTML report provides a region switcher at the top. Only core resource alarms are analyzed.

## Use Cases & Example Prompts

### Scenario 1: Alarm Noise Reduction & Optimization
Too many alarms, need analysis and noise reduction recommendations.
- "帮我分析告警数据，做降噪优化"
- "告警太多，帮我做告警降噪分析并生成报告"
- "对告警做降噪优化，生成HTML报告"

### Scenario 2: Alarm Data Distribution Analysis
Need to understand the overall alarm distribution (by level, service type, resource, etc.).
- "分析告警数据分布和趋势"
- "告警主要分布在哪些服务和级别？"
- "帮我统计告警概况"

### Scenario 3: High-Frequency Alarms & Alarm Storm Handling
Same resource triggering repeated alarms, need identification and convergence recommendations.
- "有告警风暴，帮我分析根因并给出收敛建议"
- "找出高频重复告警"
- "同一资源反复告警，怎么收敛？"

### Scenario 4: Alarm Threshold & Severity Optimization
Alarm thresholds are unreasonable or severity levels are misconfigured, need adjustment recommendations.
- "告警阈值是否合理？帮我分析一下"
- "检查告警等级设置是否合理"
- "很多低级别告警，如何优化告警等级？"

### Scenario 5: Resource Utilization Analysis & Scaling Recommendations
Frequent alarms due to high resource utilization, need scaling or optimization recommendations.
- "资源使用率告警频繁，帮我分析是否需要扩容"
- "分析资源使用情况，给出优化建议"
- "ECS/RDS资源告警多，需要扩容吗？"

> **Tip**: The more specific the prompt (e.g., specifying region, service type, focus dimension), the more precise the analysis results.

## Commands

This skill executes via Python scripts. Main commands:

| Command | Description | Write Operation |
|---------|-------------|-----------------|
| `python3 scripts/check_env.py` | Check runtime environment (Python version, dependencies, hcloud CLI) | No |
| `python3 scripts/alarm.py --days 7` | Collect CES+AOM alarm data for the last 7 days | No |
| `python3 scripts/analyze_alarm.py` | Analyze alarm data and generate HTML noise reduction report | No |

### Environment Check

```bash
python3 scripts/check_env.py
```

### Collect Alarm Data

```bash
python3 scripts/alarm.py --days 7
```

### Analyze and Generate Report

```bash
python3 scripts/analyze_alarm.py
```

## Quick Start

### Step 1: Check Environment & Dependencies

Run the environment check script to confirm Python version >= 3.10, dependencies installed, and hcloud CLI available:

```bash
python3 scripts/check_env.py
```

If the check fails, install dependencies as prompted:

```bash
pip install -r requirements.txt
```

Also ensure hcloud CLI is installed and AK/SK authentication is configured. Set up the `.env` file in the skill directory:

```bash
HW_ACCESS_KEY=your_AK
HW_SECRET_KEY=your_SK
HW_REGION_NAME=cn-south-1
```

Proceed to subsequent steps only after the environment check passes.

### Step 2: Check Key Resource Marker Table

Before collecting alarm data, verify that the key resource marker table (`assets/关键资源标记表.xlsx`) contains data rows. This table determines which regions to collect alarms from and which resources are considered core business resources.

Check method: read the Excel file and confirm it has at least one data row (beyond the header).

**If the table has data** → proceed to Step 3.

**If the table is empty** → **STOP**. Do NOT attempt to auto-discover or auto-populate resources. Present the table structure to the user and ask them to fill it in:

| Column | Description | Example |
|--------|-------------|---------|
| Region | Resource region | cn-south-1 |
| resource_type | Resource type | ECS, RDS, ELB, CCE... |
| resource_id | Resource ID | 46ef6243-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 是否核心业务 | Mark as core resource | 是 |

Only after the user confirms the table is filled should you proceed to Step 3.

### Step 3: Select Analysis Parameters

Before collecting alarm data, use the `question` tool to ask the user for the analysis time range:

- **question**: "请选择分析的时间范围"
- **header**: "时间范围"
- **options**:
  1. label: "近1天", description: "最近24小时的告警数据（默认）"
  2. label: "近7天", description: "前7天到当前的告警数据（推荐）"
  3. label: "近30天", description: "前30天到当前的告警数据"
  4. label: "自定义日期范围", description: "指定起止日期（如 2026-08-01 到 2026-08-18）"

Determine the time parameter for subsequent commands based on user selection:

- "近1天" → no extra parameter (default behavior)
- "近7天" → add `--days 7`
- "近30天" → add `--days 30`
- "自定义日期范围" → ask for start/end dates, add `--start-date YYYY-MM-DD --end-date YYYY-MM-DD`

> **Regions and core resources**: The region list and core resources are automatically loaded from `assets/关键资源标记表.xlsx` — no manual specification needed. The "Region" column determines which regions to collect from, and rows with "是否核心业务" = "是" determine the analysis scope.

### Step 4: Collect Alarm Data

Use the alarm.py script to fetch alarm data from Huawei Cloud CES and AOM. The region list is auto-read from the key resource marker table — no manual specification needed:

```bash
python3 scripts/alarm.py --days 1
```

The time parameter depends on the Step 3 selection:
- Last 1 day → no parameter (default)
- Last 7 days → `--days 7`
- Last 30 days → `--days 30`
- Custom range → `--start-date YYYY-MM-DD --end-date YYYY-MM-DD`

The script automatically reads the "Region" column from `assets/关键资源标记表.xlsx` to get the region list. For each region, it auto-fetches the corresponding project_id via hcloud CLI's `--cli-region` parameter — no extra configuration needed.

After execution, an `alarm_result.json` file is generated in the workspace directory (default: `/root/workspace/alarm-reduce-noise-workspace_YYYYMMDD_HHMMSS/`, timestamped). The output uses a multi-region structure: `{"alarms": {region_name: {...}}}`. The `ces_alarm_rules.json` file also uses a multi-region structure: `{region_name: [rule_list]}`.

### Step 5: Analyze Alarm Data

Use the Python script to analyze alarm_result.json and generate an HTML report in the workspace directory:

```bash
python3 scripts/analyze_alarm.py
```

The script always loads core resources from `assets/关键资源标记表.xlsx`, filters alarms by region, and only analyzes core resource alarms. The `--input` and `--output` parameters are optional; when omitted, the script defaults to reading `alarm_result.json` from the workspace directory and outputting `alarm-noise-report.html`.

### Input Data Format

The script reads JSON-format alarm data using a multi-region structure:

- `alarms` - a dictionary keyed by region name
- `alarms.<region_name>.username` - region name
- `alarms.<region_name>.time_range` - time range info (contains start, end, label)
- `alarms.<region_name>.alarm_history[]` - alarm history list
- Each alarm contains: alarm_level, metric_name, alarm_trigger_time, service, region, etc.

The CES alarm rules file `ces_alarm_rules.json` also uses a multi-region structure:
- A dictionary keyed by region name, with the value being a list of rules for that region

### Output

Generates an HTML noise reduction optimization report containing:
- Alarm overview statistics (including Minor alarms and core resource alarm stats, if enabled)
- Health score breakdown (5-dimension weighted: alarm volume, critical alarm ratio, alarm convergence rate, long-unresolved alarms, trend)
- Alarm level distribution
- Alarm service type distribution
- TOP10 high-frequency alarms (core resources only, if filtering enabled)
- Daily alarm trend
- Six-dimension analysis results
- Noise reduction recommendation summary (sorted by high/medium/long-term priority)

**Region switcher feature:**
- A searchable region switcher dropdown at the top of the HTML report; switching regions updates all sections dynamically
- Defaults to the first region; supports search filtering

## Workspace Directory

All scripts manage output directories via `scripts/workspace.py` with timestamped directory names, so each run does not overwrite previous results:

- **Base path**: `/root/workspace/`
- **Directory format**: `alarm-reduce-noise-workspace_YYYYMMDD_HHMMSS`
- **Sharing mechanism**: Multiple scripts in a single run share the same directory via the `ALARM_REDUCE_NOISE_WORKSPACE_DIR` environment variable
- `--input`/`--output` parameters are optional; when omitted, the workspace directory is used automatically

Usage:

```bash
# Method 1: Explicitly set shared directory (recommended for multi-script runs)
export ALARM_REDUCE_NOISE_WORKSPACE_DIR="/root/workspace/alarm-reduce-noise-workspace_$(date +%Y%m%d_%H%M%S)"
python scripts/alarm.py --days 7
python scripts/analyze_alarm.py
# All scripts output to the same directory

# Method 2: No env var set (single script standalone run, auto-creates timestamped directory)
python scripts/analyze_alarm.py
```

## Authentication Configuration

This skill uses Huawei Cloud AK/SK authentication, configured via environment variables or a `.env` file:

| Environment Variable | Description | Required | Default |
|---------------------|-------------|----------|---------|
| HW_ACCESS_KEY | Huawei Cloud AK | Yes | - |
| HW_SECRET_KEY | Huawei Cloud SK | Yes | - |
| HW_REGION_NAME | Default region | No | cn-south-1 |
| HW_PROJECT_ID | Project ID | No | Auto-fetched |
| HW_SECURITY_TOKEN | Security token (for temporary AK/SK) | No | - |

## Analysis Dimensions

### 1. Alarm Governance

Aligned with the 4 stages of the AOM alarm noise reduction chain (CES alarms do not go through the AOM noise reduction chain):

- **Route grouping**: Grouping conditions (alarm source / resource type / severity) + merge method + wait parameters (first wait / change wait / repeat wait)
- **Deduplication analysis**: AOM built-in deduplication (automatic, no configuration needed) + CES alarm constraints + duplicate alarm rule statistics
- **Suppression rules**: Severity suppression (critical alarms suppress minor/info) + root cause suppression (root cause metric suppresses derived metrics) + dependency suppression
- **Silence rules**: Test environment silencing + low-priority silencing + maintenance window silencing (filter conditions + silence time period)

### 2. Alarm Convergence

Analysis contents:
- Alarm storm identification (same resource, same metric, high-frequency trigger: >30 times = high risk, >100 times = severe)
- Route grouping suggestions (group high-frequency alarm sources by source + severity, provide AOM grouping parameters)
- Alarm temporal correlation analysis (time-window-based co-occurrence analysis, identify correlation groups)
- Dependency convergence suggestions (host down → silence derived alarms, base service abnormal → silence application alarms, etc.)

### 3. Alarm Correlation

Analysis contents:
- Root cause analysis (same resource, multiple metrics, sorted by frequency to identify root cause)
- Derived alarm identification (silence derived alarms when root cause triggers)
- Suppression rule suggestions (source alarm = root cause metric, suppressed alarm = derived metric)

### 4. Long-Unresolved Alarms

Analysis contents:
- Filter alarms with alarm_status = active
- Tier by duration: >7 days (info), >14 days (info), >30 days (warning), >90 days (danger)
- Unresolved alarm detail list

## Reference

For detailed analysis methodology, see [references/alarm-analysis.md](references/alarm-analysis.md)
