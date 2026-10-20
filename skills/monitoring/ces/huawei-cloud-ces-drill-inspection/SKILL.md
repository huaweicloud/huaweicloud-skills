---
name: huawei-cloud-ces-drill-inspection
description: >-
  Fault drill steady-state inspection tool. Collects instance status and CES monitoring metrics across
  Huawei Cloud multi-region ECS/RDS/DCS(Redis) and 19 cloud services via hcloud CLI, compares against
  expected steady-state baseline, and generates an interactive HTML inspection report (with AZ topology
  graph, status overview table, metric detail cards, Chart.js line charts). Applicable after AZ power-off,
  network injection, primary/standby switchover and other fault drills. Read-only queries only, no cloud
  resource modifications.
  Triggers: drill inspection, steady-state inspection, steady-state metrics, post-drill inspection,
  AZ power-off drill, availability zone outage, ECS/RDS/Redis status check, CES metric collection,
  hcloud inspection.
---

# Fault Drill - Steady-State Metric Inspection

## Overview

After completing a fault drill on Huawei Cloud (e.g. AZ power-off, network injection, primary/standby switchover), quickly inspect steady-state metrics of affected resources, determine whether each service instance has recovered, and generate a visual HTML report.

**Read-only**: queries only, no cloud resource modifications, no fault injection, no alerts.

## Prohibited Operations

本技能为只读稳态巡检工具，不支持任何云资源写操作：

- 创建/删除/修改云资源（ECS/RDS/DCS/ELB 等）
- 重启/启停/变更规格实例
- 注入故障、发送告警
- 配置或修改 IAM 权限

若用户提出此类请求，请明确拒绝，说明本技能只读，引导用户到对应服务控制台或 API 操作。

## User Actions

The user only needs to fill in one config file: `references/input.json`. See [Configuration Guide](#configuration-guide) below.

Supported services and metric list: `references/metrics-reference.md`.

## Prerequisites

- hcloud (KooCLI) installed and configured with AK/SK, read-only permissions for each region
- Python 3.10+

## Quick Start

```bash
cd scripts/

# 1. Connectivity check
python inspect_cli.py smoke ../references/input.json

# 2. Inspect (status collection + metric collection + HTML report)
python inspect_cli.py inspect ../references/input.json

# 3. Initialize config template
python inspect_cli.py init-config --output my_config.json
```

Reports are output to `templates/` by default, keeping only the latest 10 copies.

## Core Workflow/Process

### Step 1: Load and Validate Configuration

Load `references/input.json` and validate drill phases, inspection targets (service/region/instance_ids/metrics). Auto-infer unspecified fields (drill window, region list, expected status table, runtime params).

```bash
python scripts/inspect_cli.py init-config --output my_config.json  # generate config template
```

### Step 2: Connectivity Check

Verify hcloud CLI connectivity to all target regions before starting inspection.

```bash
python scripts/inspect_cli.py smoke references/input.json
```

### Step 3: Instance Status Collection (Parallel)

Collect instance status across all target services and regions in parallel via hcloud CLI. Each instance is marked ✅ (normal), ⚠️ (warning), or ❌ (abnormal) based on expected steady-state status.

```bash
# status_collector.py queries instance status via hcloud for 19 cloud services in parallel
hcloud ECS ListServersDetails --region=<region-id>
hcloud RDS ListInstances --region=<region-id>
hcloud DCS ListInstances --region=<region-id>
```

### Step 4: Steady-State Judgment (Status)

Judge whether each instance has recovered to steady state based on its status field (e.g. ECS=ACTIVE, RDS=ACTIVE+primary role=master, DCS=RUNNING). Abnormal instances (❌/⚠️) are excluded from metric collection — "异常实例不采指标" (no metrics for abnormal instances, since they have no meaningful metrics to compare).

### Step 5: Metric Collection (Normal Instances Only, Parallel)

For instances marked ✅ in Step 3, collect CES monitoring metrics across all drill phases (baseline, fault, recovery) in parallel. Only normal instances are queried.

```bash
# metric_collector.py queries CES metrics via hcloud in parallel
hcloud CES ShowMetricData --region=<region-id> --namespace=<ns> --metric_name=<metric> --dim.0=<dim> --period=60 --filter=average --from=<ts> --to=<ts>
```

### Step 6: Steady-State Judgment (Metrics)

Compare collected metrics across drill phases. Determine whether metrics in the inspection phase have recovered to baseline levels. Each metric is marked ✅ (normal) or ❌ (anomalous).

### Step 7: Topology Build and Report Generation

Build AZ resource topology graph data and generate an interactive HTML report:

```bash
python scripts/inspect_cli.py inspect references/input.json
```

Report includes: AZ topology graph (region→AZ→instance, three-color status), instance status overview table, per-instance metric detail cards, Chart.js monitoring line charts (inline, offline-capable), and inspection conclusion with anomaly count and recommendations. Output to `templates/` directory, keeping only the latest 10 copies.

## Post-Execution Output (Important)

After the inspection command completes, the CLI directly outputs the report file path and a brief conclusion, e.g.:

```
✅ Inspection complete! Report generated: /path/to/templates/inspection_report_xxx.html
   Duration: 1.0s | Found 12 anomalies across 3 services (ecs, rds, redis), immediate investigation recommended.
```

**Present the CLI stdout as-is to the user. Do NOT do the following:**

- ❌ Do not parse the generated HTML file to extract summaries or tables
- ❌ Do not use Python/grep or other tools to post-process report content
- ❌ Do not manually aggregate instance status or metric details into a text summary
- ❌ Do not screenshot or open the HTML report

**Reason**: The HTML report is the final deliverable, containing the complete AZ topology graph, status overview table, metric detail cards, and monitoring line charts. The CLI output path and conclusion are sufficient for the user to locate the report and understand the inspection results. Post-processing wastes time and produces redundant information.

The user can open the HTML file in a browser to view the full report.

## Configuration Guide

The user fills in the following 4 items in `references/input.json`; all other fields are auto-inferred:

```json
{
  "drill_name": "Fault Drill Inspection",
  "phases": [
    { "key": "baseline", "name": "Pre-fault Baseline", "start": "2026-10-14 09:30:00", "end": "2026-10-14 10:00:00" },
    { "key": "fault", "name": "During Fault", "start": "2026-10-14 10:00:00", "end": "2026-10-14 10:30:00" },
    { "key": "recovery", "name": "Post-recovery Inspection", "start": "2026-10-14 10:30:00", "end": "2026-10-14 11:00:00" }
  ],
  "inspect_phase": "recovery",
  "targets": [
    {
      "service": "ecs",
      "region": "your-region",
      "instance_ids": [],
      "metrics": ["ECS CPU使用率", "ECS入方向带宽", "ECS出方向带宽"]
    }
  ]
}
```

### Field Reference

| Field | Required | Description |
|------|------|------|
| `drill_name` | ✅ | Drill name, used in report title |
| `phases` | ✅ | Drill phase list, each with `key`/`name`/`start`/`end`, any count, may overlap (supports multi-fault scenarios) |
| `inspect_phase` | ✅ | Inspection phase, a `key` from `phases` |
| `targets` | ✅ | Inspection target list, each with `service`/`region`/`instance_ids`/`metrics` |
| `targets[].service` | ✅ | Cloud service name (e.g. `ecs`, `rds`, `redis`), full list in `references/metrics-reference.md` |
| `targets[].region` | ✅ | Region (e.g. `your-region`) |
| `targets[].instance_ids` | ✅ | Instance ID list, empty `[]` means all instances in that region |
| `targets[].metrics` | ✅ | Inspection metric list, use metric display names (e.g. `"ECS CPU使用率"`), see `references/metrics-reference.md` |
| `targets[].engine` | DMS required | Only when `service` is `dms`, specifies message engine: `kafka`, `rabbitmq`, or `rocketmq`; different engines have different metrics |

### Auto-inferred Fields

| Field | Inference Method |
|------|----------|
| Drill start/end | Earliest phase start / inspection phase start |
| Region list | Extracted and deduplicated from targets |
| Service toggles | Enabled if present in targets |
| Expected status | Built-in default table for 19 services |
| RDS primary role | Fixed "master" |
| Runtime params | All built-in defaults (timezone +8, CES period 60s, concurrency 10/8, etc.) |

### Multi-Fault Scenario Example

```json
"phases": [
  { "key": "baseline", "name": "Pre-fault Baseline", "start": "...", "end": "..." },
  { "key": "fault_a", "name": "Fault A - Network Latency", "start": "10:00", "end": "10:20" },
  { "key": "fault_b", "name": "Fault B - Disk Full", "start": "10:10", "end": "10:35" },
  { "key": "recovery", "name": "Post-recovery Inspection", "start": "10:35", "end": "11:05" }
]
```

Phases may overlap or have gaps, supporting cascading faults, concurrent faults, etc.

### DMS (Message Queue) Configuration Example

DMS requires an additional `engine` parameter:

```json
{
  "service": "dms",
  "region": "your-region",
  "instance_ids": [],
  "engine": "kafka",
  "metrics": ["DMS Kafka Broker CPU使用率", "DMS Kafka Broker 内存使用率"]
}
```

`engine` options: `kafka`, `rabbitmq`, `rocketmq`, each corresponding to different metric sets in `metrics-reference.md`.

## Supported Services

19 cloud services, 238 metrics. Full list in `references/metrics-reference.md`.

| Service | Code | Metrics |
|------|------|--------|
| ECS Elastic Cloud Server | ecs | 7 |
| RDS Relational Database | rds | 32 |
| DCS Distributed Cache | redis | 31 |
| ELB Load Balancer | elb | 12 |
| EIP Elastic Public IP | eip | 4 |
| NAT Gateway | nat | 11 |
| VPCEP VPC Endpoint | vpcep | 4 |
| EVS Cloud Disk | evs | 7 |
| CCE Cloud Container Engine | cce | 8 |
| CSS Search Service | css | 11 |
| DDS Document Database | dds | 1 |
| DWS Data Warehouse | dws | 11 |
| DC Direct Connect | dc | 4 |
| ER Enterprise Router | er | 2 |
| SFS Turbo File System | efsturbo | 9 |
| APIG API Gateway | apig | 1 |
| TaurusDB Distributed Database | taurusdb | 18 |
| GeminiDB Cloud-native NoSQL | geminidb | 20 |
| DMS Message Queue | dms | 33 |

## Steady-State Judgment

| Service | Expected Status | Additional Checks |
|------|----------|----------|
| ECS | ACTIVE | — |
| RDS | ACTIVE | Primary role = master |
| Redis | RUNNING | — |
| ELB | ACTIVE | — |
| EIP | ACTIVE | — |
| Others | See built-in default table | — |

Judgment hierarchy: instance-level (✅/⚠️/❌) → service-level → global conclusion

## Report Structure

1. **Report header**: drill name + inspection time + duration + data item stats
2. **Summary cards**: total metrics / total instances / per-service status
3. **AZ resource topology**: Region→AZ→Instance, three-color status + RDS primary/standby markers
4. **Instance status overview table**: grouped by service
5. **Per-instance metric details**: one card per instance, per-metric ✅/❌
6. **Monitoring line charts**: Chart.js time-series (inline, offline-capable), with min/max/avg stats
7. **Inspection conclusion**: anomaly count + affected services + recommendation

## Module Reference

| Script | Responsibility |
|------|------|
| `inspect_cli.py` | CLI entry, subcommand dispatch |
| `config_loader.py` | Config loading, simple config expansion, validation |
| `hcloud_executor.py` | hcloud CLI wrapper with parallel execution |
| `status_collector.py` | Instance status collection (19 services) |
| `metric_collector.py` | Monitoring metric collection (CES, metrics.json-driven) |
| `steady_state_judge.py` | Steady-state judgment engine |
| `topology_builder.py` | AZ topology graph data construction |
| `report_builder.py` | HTML report generation (with history cleanup) |
| `html_template.py` | HTML template and styles (Chart.js inline) |

## Directory Structure

```
├── references/          # Reference files
│   ├── input.json       # User config (← user only edits this)
│   ├── metrics.json     # Metric metadata (built-in, do not modify)
│   └── metrics-reference.md  # Supported services and metric list (for reference)
├── scripts/             # Source code
├── templates/           # Generated HTML reports (auto-output)
├── assets/              # Static assets (Chart.js, etc.)
└── SKILL.md
```
