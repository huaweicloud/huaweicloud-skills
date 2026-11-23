---
name: huawei-cloud-alarm-bind-inspection
description: |
  Huawei Cloud alarm baseline configuration read and inspection analysis skill. Fetches all alarm rules for the current account via CES SDK and hcloud AOM CLI, extracts CES and AOM baseline metrics/events from the alarm baseline Excel, compares and analyzes alarm binding status, and generates instance-level binding rate reports and remediation suggestions (Excel + HTML).
  Use this skill when the user needs to inspect alarm binding coverage, read alarm baselines, analyze alarm rules, or generate alarm binding reports.
  Triggers include: "告警基线", "告警配置", "告警阈值", "告警巡检", "告警绑定巡检", "alarm bind inspection", "读取告警基线", "生成告警JSON", "分析告警规则", "告警收敛", "CES告警", "AOM告警"
tags: [huawei-cloud, alarm, ces, aom, inspection, baseline, binding-rate]
---

# Alarm Bind Inspection

## Overview

Alarm bind inspection: fetches all alarm rules for the current account via CES (Cloud Eye Service) SDK and hcloud AOM CLI, extracts CES and AOM baseline metrics/events from the alarm baseline Excel, and compares and analyzes alarm binding status. Two merged analysis dimensions (CES + AOM data merged into the same tab, distinguished by a "monitoring system" column):

- **Metric baseline**: analyzes baseline metric binding rate per instance + metric dimension (CES metrics + AOM metrics; AOM services without core instances are skipped)
- **Event baseline**: analyzes baseline event binding rate per instance (CES events + AOM events; AOM services without core instances are skipped)

Uses AK/SK authentication (current account only, no multi-customer mode). AK/SK are read from environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`). Regions are auto-extracted from `core_instances.json` (multi-region supported). Project ID is auto-fetched via `hcloud` CLI per target region — no manual configuration needed.

## Workflow

### Step 1: Check Python Environment and Dependencies

1. **Check Python**: run `python --version`, confirm Python exists and version > 3.9
2. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

Prerequisites:
- Python version > 3.9
- AK/SK configured in environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`)
- `hcloud` CLI available (used to auto-fetch Project ID)
- Third-party dependencies: see `requirements.txt` (includes `huaweicloudsdkces`, `huaweicloudsdkcore`)

### Step 2: Fetch All Instances via RMS API

```bash
python scripts/generate_instance.py
```

Fetches all cloud resource instances via RMS (Resource Management Service) API and converts them directly to `core_instances.json` format. No intermediate `instances.json` file is produced.

**Flow**:
1. `CollectAllResourcesSummary` — get resource overview (which provider+type pairs exist in the account)
2. Intersect with `PROVIDER_TYPES` (indicator-baseline-supported provider+type list)
3. Concurrent `ListAllResources` per provider.type (10 threads, auto-paginate)
4. In-memory convert: map each resource's `(provider, type)` to service short name (e.g. `ecs` → `ECS`, `vpc+publicips` → `EIP`), filter sub-resources (e.g. RDS nodes/proxies), output `{instance_id, raw_service, region}` per instance

**Pre-checks**:
- `hcloud` CLI available and configured with AK/SK
- RMS API accessible in the target region

Output: `<WORKSPACE_DIR>/intermediate/core_instances.json`

Output structure:
- `{"source": "RMS API (generate_instance.py)", "instances": {"ECS": [...], "RDS": [...], ...}, "instance_counts": <total>}`

### Step 3: Enrich Core Instances with metric_dimension

```bash
python scripts/enrich_metric_dimension.py
```

Calls each service's ShowInstance API via hcloud CLI to fetch instance attributes (engine, cache_mode, type, etc.) and infer the most specific metric dimension route. Depends only on Step 2 (core_instances.json) — does not depend on alarm rules or baseline data. Dimension values are sourced from module-level constants (SINGLE_DIM_CONSTANTS, MULTI_DIM_CONSTANTS) and hcloud ShowInstance APIs.

`metric_dimension` is a single-value string representing the instance's most specific dimension route, e.g. `"dcs_instance_id,dcs_cluster_redis_node"`. `bind_analysis.py` uses **exact matching**: a baseline dimension must exactly equal the instance's `metric_dimension` to be a hit (e.g. `dcs_instance_id` matches only instances with `metric_dimension == "dcs_instance_id"`, not `"dcs_instance_id,dcs_cluster_redis_node"`).

Service coverage (46 baseline services):

| Category | Services | Approach | API Calls |
|---|---|---|---|
| B single-dimension | 22 | Read unique dimension from module-level constants | 0 |
| C multi-dim + ShowInstance | 18 | Call hcloud ShowInstance to infer | 1 per instance |
| D multi-dim + indirect | 2 | GAUSSDB/ROMA indirect query or fallback | 1 per instance |
| A no hcloud | 4 | OBS uses bucket_name; MaaS not available | 0 |

Verified services:
- **DCS**: engine=Redis + cache_mode=ha → `dcs_instance_id,dcs_cluster_redis_node` (22 baseline metrics)
- **ELB**: ShowLoadBalancer/v3 includes `listeners[]` and `pools[]` — no extra API needed
- **VPC/EIP**: ShowPublicip/v3 includes `bandwidth` object — no extra API needed
- **EG**: ShowDetailOfChannel does not include subscription info — sub-dimensions need extra API
- **GAUSSDB**: hcloud only has GaussMySql API, cannot query openGauss — fallback handling
- **ROMA**: ListMqsInstance requires `include_internal` param — fallback on 0 instances

Output: updates `<WORKSPACE_DIR>/intermediate/core_instances.json`

### Step 4: Extract Alarm Baseline from Excel

```bash
python scripts/generate_alarm_baseline.py
```

Extracts two types of baseline data from the alarm baseline Excel:

1. `CES指标基线` sheet: filter by `指标级别=底线指标`, exclude records containing "环比" in column R (comparison relation), extract 19 columns (including column F "指标维度" and column AG "备注")
2. `CES事件基线` sheet: filter by `事件级别=底线事件`, extract 8 columns (B/C/D/E/F/G/H/I)

Output:
- `<WORKSPACE_DIR>/intermediate/indicator_baseline.json` — CES metric baseline
- `<WORKSPACE_DIR>/intermediate/event_baseline.json` — CES event baseline
- `<WORKSPACE_DIR>/intermediate/aom_indicator_baseline.json` — AOM metric baseline (CCE 21 records + other services 36 records = 57 records)
- `<WORKSPACE_DIR>/intermediate/aom_event_baseline.json` — AOM event baseline (Modelarts 12 records + other services 15 records = 27 records)

AOM baselines extracted from 4 additional sheets:
3. `AOM指标基线-CCE` sheet: filter `指标级别=底线指标`, PromQL structure (18 columns)
4. `AOM指标基线-其他服务` sheet: filter `指标级别=底线指标` (22 columns, IoTDA/CCI/Modelarts)
5. `AOM-Modelarts事件` sheet: filter `指标级别=底线指标` (15 columns, PromQL event structure)
6. `AOM事件基线-其他服务` sheet: filter `事件级别=底线事件` (13 columns)

### Step 5: Fetch Online Alarm Rules

Fetches all alarm rules for the current account in the specified region(s) via CES SDK (AK/SK auth). CES alarm rules include resource dimension info and notification config — no separate notification rule fetch needed.

**Project ID auto-fetch**: `config.py`'s `fetch_project_id(region)` calls `hcloud IAM KeystoneListProjects --cli-region=<region>` and matches the region name to auto-fetch the corresponding Project ID. If `HW_PROJECT_ID` env var is explicitly set, it takes priority.
- **SSL verification**: CES SDK HTTPS certificate verification is enabled (`ignore_ssl_verification=False`). If your environment uses a self-signed certificate (e.g. internal proxy), you may set it to `True` in `config.py`, but document the reason and security risk here.

```bash
python scripts/main_alarm.py
```

Auto-reads all regions from `core_instances.json`, calls CES `ListAlarmRules` per region, and merges results. Each rule is tagged with a `region` field. For every rule with non-empty, non-wildcard dimensions, calls CES `ListAlarmRuleResources` (concurrent, 10 threads) to resolve actual instance IDs into a `resource_ids` array. Finally, splits event-type rules (EVENT.SYS / EVENT.CUSTOM) into a separate file.

A single region failing is tolerated (it is logged and skipped). If **every** region fails or is unsupported, the script writes nothing and exits `1` instead of emitting an empty rule set — an empty report must never be mistaken for a tenant that has nothing to alarm on.

Output:
- `<WORKSPACE_DIR>/intermediate/online_alarm_rules.json` — metric alarm rules only (with resource dimensions, resource_ids, policy metrics, notification config)
- `<WORKSPACE_DIR>/intermediate/online_notification_rules.json` — event-type alarm rules only (with resource_ids)

#### Step 5b: Fetch AOM Alarm Rules

```bash
python scripts/main_aom_alarm.py
```

Fetches AOM metric-type and event-type alarm rules separately via hcloud AOM `ListMetricOrEventAlarmRule`. Multi-region supported (regions auto-extracted from `core_instances.json`).

Output:
- `<WORKSPACE_DIR>/intermediate/aom_alarm_rules.json` — AOM metric alarm rules
- `<WORKSPACE_DIR>/intermediate/aom_notification_rules.json` — AOM event alarm rules

### Step 7: Compare and Analyze Alarm Binding Rates

#### 7a: Metric Baseline Binding Analysis (CES + AOM Unified)

```bash
python scripts/bind_analysis.py \
  --aom-baseline intermediate/aom_indicator_baseline.json \
  --aom-rules intermediate/aom_alarm_rules.json
```

Reads core instance list, **both** CES and AOM metric baselines, and **both** CES and AOM alarm rules. Routes each service to the correct monitoring system (CES for 44 services, AOM for CCE/CCI/IoTDA/Modelarts), compares baseline metrics with online rules, and calculates binding rates.

Core logic:
- CES baseline grouped by `(service_short_name, metric_dimension)` two-level grouping
- AOM baseline grouped by `(云服务简称, 指标维度)` with Chinese dimension names
- CES alarm rule dimensions extracted from `resources[].dimensions[].name`
- AOM alarm rules matched by metric ID in PromQL text
- **Dimension matching uses exact matching**: instance `metric_dimension` must exactly equal baseline dimension
- Each instance record includes a `monitor_system` field ("CES" or "AOM")
- Output at `(instance, metric_dimension)` granularity, unified into a single report

Output: `<WORKSPACE_DIR>/intermediate/indicator_bind_report.json` (unified CES + AOM)

#### 7b: Event Baseline Binding Analysis (CES + AOM Unified)

```bash
python scripts/event_bind_analysis.py \
  --aom-baseline intermediate/aom_event_baseline.json \
  --aom-rules intermediate/aom_notification_rules.json
```

Reads **both** CES and AOM event baselines and alarm rules. Compares baseline events with events in alarm rules, and calculates binding rates. Each instance record includes a `monitor_system` field.

Output: `<WORKSPACE_DIR>/intermediate/event_bind_report.json` (unified CES + AOM)

### Step 8: Generate Reports

#### 8a: Metric Baseline Excel Report

```bash
python scripts/generate_excel_report.py
```

Output: `<WORKSPACE_DIR>/indicator_bind_report.xlsx` (unified CES + AOM metric sheet)

#### 8b: Event Baseline Excel Report

```bash
python scripts/generate_event_excel_report.py
```

Output: `<WORKSPACE_DIR>/event_bind_report.xlsx` (unified CES + AOM event sheet)

#### 8c: Merged HTML Suggestion Report

```bash
python scripts/generate_suggestion.py
```

Output: `<WORKSPACE_DIR>/suggestion_report.html`

HTML report includes:
- **[Metric Baseline]** overview, per-service + metric-dimension statistics, remediation details (CES + AOM merged, monitoring system column distinguishes source)
- **[Event Baseline]** overview, per-service statistics, remediation details (CES + AOM merged, monitoring system column distinguishes source)
- Automation feasibility conclusion

### Step Dependencies

```
Step 1 ─→ Step 2 ─┬→ Step 5 ──────────┐
              │   └→ Step 5b ──────┐   │
              │   ┌→ Step 3 ───────┼───┼→ Step 7a ─→ Step 8a ─┐
              │   │                │   └→ Step 7b ─→ Step 8b ─┤
              └→ Step 4 ──────────┼──────────────────────────→ ├─→ Step 8c
                               Step 5b ─→ Step 7c ─→ Step 8a ──┤
                               Step 5b ─→ Step 7d ─→ Step 8b ──┘
```

- Step 1 is an environment prerequisite, must execute before all other steps
- Steps 2 and 4 are independent, can run in parallel (Step 2 uses RMS API, Step 4 reads Excel baseline)
- Step 5 depends on Step 2 (auto-extracts region list from core_instances.json, multi-region supported; outputs both metric rules and event rules, disabled rules excluded)
- Step 3 depends only on Step 2 (reads core_instances.json), does not depend on alarm rules or baseline data; can run in parallel with Step 5/5b after Step 2 completes
- Step 5b depends on Step 2 (extracts regions from core_instances.json; outputs both metric and event rules, disabled rules excluded)
- Step 7a depends on outputs of Steps 4, 3, 2, 5
- Step 7b depends on outputs of Steps 5, 3, 2
- Step 7c depends on Step 4 (AOM metric baseline), Step 5b (AOM alarm rules), Step 2 (core instances)
- Step 7d depends on Step 4 (AOM event baseline), Step 5b (AOM event alarm rules), Step 2 (core instances)
- Steps 7a, 7b, 7c, 7d can run in parallel
- Step 8a depends on 7a+7c, 8b depends on 7b+7d, 8c depends on 7a+7b+7c+7d
- Steps 8a, 8b can run in parallel

## Working Directory

Output files are written to a timestamped working directory managed by `workspace.py`. The directory uses a two-level structure separating final deliverables from intermediate data:

- **Base path**: `/root/workspace/`
- **Directory format**: `alarm-bind-inspection-workspace_YYYYMMDD_HHMMSS`
- **Directory structure**:
  - `<WORKSPACE_DIR>/` — final output files (`.xlsx`, `.html`), i.e. user deliverables
  - `<WORKSPACE_DIR>/intermediate/` — intermediate files (`.json`), passed between steps, not directly user-facing
- **Sharing mechanism**: all scripts in a single run share the same directory via the `ALARM_WORKSPACE_DIR` environment variable

Usage:

```bash
# Option 1: explicitly set shared directory (recommended for multi-script runs)
export ALARM_WORKSPACE_DIR="/root/workspace/alarm-bind-inspection-workspace_$(date +%Y%m%d_%H%M%S)"
python scripts/generate_instance.py
python scripts/main_alarm.py
# ... all scripts output to the same directory

# Option 2: no env var set (single-script standalone run auto-creates a timestamped directory)
python scripts/generate_instance.py
```

`<WORKSPACE_DIR>` in the workflow steps above refers to the directory root level; intermediate file paths are `<WORKSPACE_DIR>/intermediate/`.

Relative paths given to `bind_analysis.py` / `event_bind_analysis.py` are resolved against `<WORKSPACE_DIR>` first, then `<INTERMEDIATE_DIR>` for bare filenames; if neither exists, the original path is returned as-is (may be relative to CWD). This is why the examples above can pass `intermediate/aom_alarm_rules.json`. For `--output`: a relative output path is always created under `<WORKSPACE_DIR>` (parent directories are created as needed), never relative to the current working directory — even though the file does not exist yet.

## Data Sources

### Core Instance List

- **Source**: RMS API via `generate_instance.py`
- **API calls**:
  - `hcloud RMS CollectAllResourcesSummary` — resource overview (provider + type + region + count)
  - `hcloud RMS ListAllResources` — full resource listing per provider.type (concurrent, auto-paginate)
- **Provider-to-service mapping**: `generate_instance.py` maps RMS `(provider, type)` to service short name (e.g. `ecs` → `ECS`, `vpc+publicips` → `EIP`, `nosql` → `GeminiDB`), filtering sub-resources (RDS nodes/proxies, DCS nodes, DMS *_nodes, etc.)

### Metric Baseline

- **File**: `assets/华为云租户面监控告警基线-V26.01-beta.xlsx`
- **Sheet**: `CES指标基线`
- **Filter condition**:
  - `指标级别` = 底线指标
- **Extracted columns** (B/C/D/E/F/G/H/I/K/L/M/P/Q/R/S/T/U/V/AG)

### Event Baseline

- **File**: `assets/华为云租户面监控告警基线-V26.01-beta.xlsx`
- **Sheet**: `CES事件基线`
- **Filter condition**:
  - `事件级别` = 底线事件
- **Extracted columns** (B/C/D/E/F/G/H/I)

### AOM Metric Baseline

- **File**: `assets/华为云租户面监控告警基线-V26.01-beta.xlsx`
- **Sheets**:
  - `AOM指标基线-CCE` (18 columns, PromQL structure) — filter `指标级别=底线指标`
  - `AOM指标基线-其他服务` (22 columns, IoTDA/CCI/Modelarts) — filter `指标级别=底线指标`

### AOM Event Baseline

- **File**: `assets/华为云租户面监控告警基线-V26.01-beta.xlsx`
- **Sheets**:
  - `AOM-Modelarts事件` (15 columns, PromQL event structure) — filter `指标级别=底线指标`
  - `AOM事件基线-其他服务` (13 columns) — filter `事件级别=底线事件`

### CES Authentication Config

- **Environment variables**:
  - `HW_ACCESS_KEY` — Huawei Cloud AK
  - `HW_SECRET_KEY` — Huawei Cloud SK
  - `HW_SECURITY_TOKEN` — Security token (optional, for temporary AK/SK scenarios)
  - `HW_PROJECT_ID` — Project ID (optional, auto-fetched if not set)
- **Region**: auto-extracted from `core_instances.json` (multi-region); can override to single region with `--region`
- **Project ID auto-fetch**: when `HW_PROJECT_ID` is not set, `config.py` auto-queries the corresponding Project ID via `hcloud IAM KeystoneListProjects --cli-region=<region>`
- **SSL verification**: CES SDK HTTPS certificate verification is enabled (`ignore_ssl_verification=False`). If your environment uses a self-signed certificate (e.g. internal proxy), you may set it to `True` in `config.py`, but document the reason and security risk here.

## Resources

### scripts/
- `generate_alarm_baseline.py` — Extract CES metric/event baseline and AOM metric/event baseline JSON from Excel
- `main_alarm.py` — Fetch all CES alarm rules (ListAlarmRules) + resolve resource IDs (ListAlarmRuleResources) + split event-type rules (multi-region, unified)
- `main_aom_alarm.py` — Fetch AOM alarm rules via hcloud AOM (metric + event, multi-region)

- `generate_instance.py` — Fetch all instances via RMS API and convert to core_instances.json (no intermediate instances.json)
- `enrich_metric_dimension.py` — Enrich core instances with metric_dimension (infer via hcloud ShowInstance, 10-thread concurrent)
- `bind_analysis.py` — Compare and analyze metric baseline binding rate (CES + AOM unified, outputs `indicator_bind_report.json`)
- `event_bind_analysis.py` — Compare and analyze event baseline binding rate (CES + AOM unified, outputs `event_bind_report.json`)
- `generate_excel_report.py` — Generate metric baseline Excel report
- `generate_event_excel_report.py` — Generate event baseline Excel report
- `generate_suggestion.py` — Generate merged HTML suggestion report (metric + event)
- `alarm_api.py` — CES SDK API wrapper
- `config.py` — CES client config (AK/SK from env vars, Project ID auto-fetch, region list)
- `workspace.py` — Working directory management (timestamped output dir, intermediate files in `intermediate/` subdir, final outputs at root level, shared via `ALARM_WORKSPACE_DIR` env var)
- `diagnose_event.py` — Event-type alarm rule diagnostic tool

### data-sources/
- `assets/华为云租户面监控告警基线-V26.01-beta.xlsx` — Baseline data source
- `assets/关键资源标记表.xlsx` — (legacy) Core instance data source, superseded by RMS API in `generate_instance.py`

### output-files/

#### Final outputs (`<WORKSPACE_DIR>/`)
- `<WORKSPACE_DIR>/indicator_bind_report.xlsx` — Metric baseline Excel report (CES + AOM)
- `<WORKSPACE_DIR>/event_bind_report.xlsx` — Event baseline Excel report (CES + AOM)
- `<WORKSPACE_DIR>/suggestion_report.html` — Merged HTML suggestion report (CES + AOM)

#### Intermediate files (`<WORKSPACE_DIR>/intermediate/`)
- `core_instances.json` — Core instance list
- `indicator_baseline.json` — CES baseline metrics JSON
- `event_baseline.json` — CES baseline events JSON
- `ecs_special_events.json` — ECS special events for AI scenarios
- `aom_indicator_baseline.json` — AOM baseline metrics JSON
- `aom_event_baseline.json` — AOM baseline events JSON
- `online_alarm_rules.json` — CES metric alarm rules
- `online_notification_rules.json` — Event-type alarm rules
- `aom_alarm_rules.json` — AOM metric alarm rules
- `aom_notification_rules.json` — AOM event alarm rules
- `indicator_bind_report.json` — CES metric binding rate analysis
- `event_bind_report.json` — CES event binding rate analysis
- `aom_indicator_bind_report.json` — AOM metric binding rate analysis
- `aom_event_bind_report.json` — AOM event binding rate analysis

## Parameter Description

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `HW_ACCESS_KEY` | Huawei Cloud Access Key (AK) | Yes | `AKxxx...` |
| `HW_SECRET_KEY` | Huawei Cloud Secret Key (SK) | Yes | `SKxxx...` |
| `HW_SECURITY_TOKEN` | Security token for temporary AK/SK | No | `token-string` |
| `HW_PROJECT_ID` | Project ID; auto-fetched if not set | No | `0a1b2c3d...` |
| `ALARM_WORKSPACE_DIR` | Shared working directory for multi-script runs | No | `/root/workspace/alarm-bind-inspection-workspace_20260101_120000` |

### CLI Parameters (Python scripts)

| Parameter | Description | Used By | Default |
|-----------|-------------|---------|---------|
| `--region` | Override to single region (skips multi-region auto-extract) | `main_alarm.py`, `main_aom_alarm.py` | None (auto-extract from `core_instances.json`) |

### CLI Parameters (hcloud CLI)

| Parameter | Description | Used By | Example |
|-----------|-------------|---------|---------|
| `--cli-region` | Region ID for hcloud API calls | `enrich_metric_dimension.py`, `main_aom_alarm.py`, `config.py` | `--cli-region=cn-north-4` |

**Note**: `--cli-region` is the hcloud CLI (KooCLI) parameter for specifying the region. It is used internally by scripts when calling hcloud commands such as:

```bash
# AOM alarm rule fetch (inside main_aom_alarm.py)
hcloud AOM ListMetricOrEventAlarmRule --cli-region=cn-north-4

# Instance detail fetch (inside enrich_metric_dimension.py)
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id=<instance_id>

# Project ID auto-fetch (inside config.py)
hcloud IAM KeystoneListProjects --cli-region=cn-north-4
```

## Reference Documents

Refer to documents in the `references/` directory for more information:

- `design.md`: Skill design document — architecture, data flow, and analysis logic
- `cli-installation-guide.md`: hcloud CLI (KooCLI) installation and configuration guide
- `iam-policies.md`: Required IAM permissions and AK/SK configuration
- `verification-method.md`: Skill verification and testing methods
- `acceptance-criteria.md`: Quality standards and acceptance criteria
