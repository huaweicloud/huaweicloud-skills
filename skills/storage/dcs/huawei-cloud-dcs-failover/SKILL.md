---
name: huawei-cloud-dcs-failover
description: >
  Huawei Cloud DCS master-slave failover (AZ power-off) drill tool. One-click pipeline: prepare (checks + risk assessment) -> execute (failover) -> report.
  Queries DCS master-slave instance, checks IAM permissions, architecture hard-gate (ha + cross-AZ + RUNNING),
  safely executes master-slave failover (ChangeMasterStandby), polls for completion, data consistency check,
  three-dimensional scoring (failover/data/business, written to execution_result.json), generates HTML report.
  prepare phase includes built-in risk assessment (instance health, master-slave nodes, memory/CPU/connections/latency load, backup safety net, etc.).
  Critical risks block failover by default (user must confirm to proceed). Supports Redis master-slave instances.
  Triggers: DCS主备倒换, 主备倒换演练, DCS故障演练, 主备切换, 倒换实验, dcs failover, DCS failover,
  高可用演练, 高可用验证, DCS HA切换, AZ断电演练, 主备互换, DCS switchover, Redis故障演练, DCS容灾演练。
---

# Huawei Cloud DCS Master-Slave Failover (AZ Power-Off) Drill

## Overview

This tool safely performs a DCS (Redis) master-slave failover drill on Huawei Cloud, verifying instance HA capability under AZ power-off (master node failure) scenarios. It runs a three-phase pipeline:

```
prepare (checks + risk assessment) -> execute (failover) -> report (generate report)
```

- **prepare**: query DCS instance, check IAM permissions, **architecture hard-gate** (ha + cross-AZ + RUNNING), generate experiment config directory, and run **risk assessment**
- **execute**: load config, safely execute master-slave failover (`ChangeMasterStandby`), poll for completion, data consistency check
- **report**: read config and execution result, generate comprehensive HTML report (instance info, safety checks, topology change, failover timeline, data consistency check)

## Triggers / Trigger Conditions

Triggered when the user needs to perform a DCS master-slave failover, switchover, fault drill, AZ power-off drill, or failover experiment.

**Triggers**: DCS主备倒换, 主备倒换演练, DCS故障演练, 主备切换, 倒换实验, dcs failover, DCS failover, 高可用演练, 高可用验证, DCS HA切换, AZ断电演练, 主备互换, DCS switchover, Redis故障演练, DCS容灾演练

**Trigger conditions**:
- User mentions DCS master-slave failover or failover operation
- User needs to perform master-slave switchover on a ha-type DCS instance
- User needs a DCS fault drill or HA verification (AZ power-off scenario)
- User needs to swap master-slave or switchover on a DCS instance
- User needs to verify DCS HA / disaster recovery capability

## Prerequisites

| Condition | Description | Verification |
|-----------|-------------|--------------|
| **hcloud CLI** | Installed and authenticated (KooCLI >= 3.0.0) | `hcloud version` |
| **AK/SK** | Configured via hcloud profile. Script only checks if read-only calls succeed; actual auth is handled by hcloud profile | `hcloud DCS ListInstances --cli-region=cn-south-1` |
| **Python 3.8+** | To run scripts | `python3 --version` |
| **Master-slave DCS instance** | A ha-type instance exists in the target region | hcloud CLI |
| **Instance status RUNNING** | Instance must be running before failover | prepare phase auto-checks |

## Configuration

Shared config file `config/config.json`:

```json
{
  "region": "cn-south-1",
  "instance_id": "<your-dcs-instance-id>"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `region` | Yes | Huawei Cloud region ID (e.g. cn-south-1, cn-north-4) |
| `instance_id` | Yes | Target DCS instance ID |

> ⚠️ **You must modify `config/config.json` before running**: replace `region` and `instance_id` with your own region and DCS instance ID.
> The default value is a placeholder; using it directly will fail.

> ℹ️ **No need to adjust hcloud env config**: This skill does not require or recommend modifying hcloud profile (e.g. readTimeout). The script layer uses a sufficiently long subprocess timeout (120s) for CLI calls, and `run_hcloud` detects CLI timeout signatures (`调用API超时` / `context deadline exceeded` / `readTimeout`), applying idempotent protection for synchronous mutation API timeouts (read-only recheck, no command replay). User hcloud env config can stay as-is.

## Parameter Confirmation

### Required Parameters

- **region**: Huawei Cloud region ID (e.g. cn-south-1, cn-north-4), configured in `config/config.json`
- **instance_id**: Target DCS master-slave instance ID, configured in `config/config.json`

### Optional Parameters

- **--phase**: Pipeline phase to run (prepare / execute / report / all), default `all`
- **--force**: Skip critical risk blocking and force failover execution (requires manual confirmation)
- **--config-dir**: Config directory path, default `experiments/`

## Conversational Usage (Recommended)

The user simply says "执行 DCS 主备倒换" (or an equivalent trigger), and the agent guides through the drill automatically. **The user does not need to manually edit any config file.**

### Agent Guidance Flow

1. **Probe instances**: use `hcloud DCS ListInstances --cli-region=<region>` to query instances in the target region; if the user hasn't specified a region, probe by priority (cn-south-1 / cn-north-4 / cn-north-1 / cn-east-3) to find a drillable master-slave instance (ha + cross-AZ + RUNNING)
2. **Confirm target**: show candidate instances to the user, confirm the target (if only one candidate, can confirm directly)
3. **Confirm execution**: confirm user authorizes a real failover (failover is a mutation that swaps master-slave roles, must be confirmed). Options should only revolve around "execute/cancel", **do not offer "prepare-only" options** — the user's goal is to execute failover; prepare is just an internal pipeline phase
4. **Write config**: write the confirmed region / instance_id into `config/config.json`
5. **Execute full pipeline**: internally call `python3 scripts/run.py` to perform the real failover (if user confirms forced drill, internally append `--force`, **no need to expose CLI args to user**)
6. **Present results**: present CLI output as-is to the user, point out the report path

### Questions for Missing Information

| Missing info | Question |
|--------------|----------|
| Target instance | "当前账号下 <区域> 有实例 X，确认用哪个？" |
| Region | "请提供目标区域（如 cn-south-1 华南-广州）" |
| Execution confirmation | "确认对实例 X 执行主备倒换？（会切换主备角色，引起短暂连接中断）" |

> ⚠️ Questions must only revolve around "execute/cancel". **Never offer "prepare-only" or "risk-assessment-only" options** — those are invalid questions that treat internal pipeline phases as standalone goals.

### Key Interaction Rules

- **Failover is a mutation**: must confirm with user before executing, never default-execute
- **Risk disclosure**: when prepare detects risks (including critical), must fully show each risk's impact and suggestion to the user
- **Critical risk二次确认**: when prepare detects critical risks, must show risks and confirm whether to proceed, never auto-proceed. Confirmation options are "**强制演练** / **取消演练**" (after user confirms forced drill, agent internally appends `--force`, not exposed to user), **must not offer "prepare-only" invalid options**
- **DCS.4104 cooldown**: if failover is rejected (instance in recovery), clearly tell the user "in failover cooldown, retry in a few minutes"
- **Idempotent protection**: if instance is already in target state (e.g. already failed over last round), inform user of current role status to avoid redundant failover

## Quick Start

### One-Click Full Pipeline

```bash
# Full pipeline (skill invocation performs real failover)
python3 scripts/run.py
```

### Phase-by-Phase Execution

```bash
# 1. Prepare checks
python3 scripts/run.py --phase prepare

# 2. Execute failover
python3 scripts/run.py --phase execute
# If prepare detected critical risks and user confirmed to proceed, agent internally appends --force (not exposed to user):
#   python3 scripts/execute.py --config-dir experiments --force

# 3. Generate report
python3 scripts/run.py --phase report
```

## Three Phases

### Phase 1: prepare (Preparation Checks)

Query DCS resources and user permissions, generate config directory, and run **architecture hard-gate + risk assessment**.

- Query target DCS instance (ListInstances + ShowInstance to fill in cache_mode, etc.)
- Query master-slave node info (ShowNodesInformation)
- Check IAM permissions (hcloud auth readiness, DCS read/write permissions, failover permission)
- Generate config files (experiment.json, iam_policy.json, monitoring.json)
- **Architecture hard-gate** (11 checks): ha type, RUNNING, master-slave nodes exist, cross-AZ, etc.; required items block on failure
- **Risk assessment** (three-step pipeline):
  - **Detect**: read-only probe of instance status, master-slave node health, backup freshness, CES load metrics (CPU/memory/connections/latency)
  - **Assess**: grade each item by threshold (info/unknown/warning/critical), aggregate overall risk level (low/medium/blocked) with action recommendation
  - **Block**: results written to `risk_assessment.json` and embedded in readiness report; execute phase reads this file, blocks failover by default if critical items exist (user must confirm to proceed)

**Output**: config files and readiness report in `experiments/` directory (including `risk_assessment.json`)

### Phase 2: execute (Failover Execution)

⚠️ **Mutation** — master-slave failover actually swaps master-slave roles.

- Load config, pre-check (instance exists, ha, RUNNING, IAM permissions)
- Read `risk_assessment.json` and show risk assessment results; block failover if critical items exist and user hasn't confirmed
- **Validate risk assessment consistency**: block by default if `risk_assessment.json` region/instance_id doesn't match config.json (prevents "swap instance, use stale assessment to bypass")
- **Real-time recheck before failover**: immediately recheck instance status and node health before failover (prepare snapshot may be stale); block by default if critical anomaly found
- Call `hcloud DCS ChangeMasterStandby` to execute master-slave failover
- Poll node status every 5 seconds, wait for master-slave role swap to complete (timeout 120 seconds)
- Data consistency check (master node moved to slave AZ, node_id change, key count)
- Save execution result to `execution_result.json`

**User interaction**: failover is a real mutation; execute performs a real failover (no dry-run). Critical risks block by default; user must confirm to proceed. User-facing options are only "强制演练 / 取消演练" (internally via `--force`, not exposed to user).

### Phase 3: report (Report Generation)

Read config and execution result, generate comprehensive HTML report.

Report includes: result banner, instance info, safety checks, master-slave topology change, failover timeline, data consistency check.

> 🔒 **HTML encoding requirement (prevent stored XSS)**: all external data from cloud APIs (instance names, node info, check items, etc.) must be HTML-escaped via `html.escape` before insertion. Both `scripts/report.py` and `scripts/prepare.py` apply `esc()` / `_esc()` to all external data.

**Output**: `templates/failover_report_YYYYMMDD_HHMMSS.html` (standalone HTML, open in browser)

## Risk Assessment

The prepare phase runs risk assessment in addition to architecture hard-gate checks. Assessment has three steps: **detect -> assess -> block**.

### Detection Items (Read-Only Real-Time Probe)

| Dimension | Data source (read-only API) | Metric |
|-----------|----------------------------|--------|
| Instance health | `DCS ShowInstance` | Instance status RUNNING |
| Master-slave nodes | `DCS ShowNodesInformation` | Master/slave node existence and status |
| Backup safety net | `DCS ListBackupRecords` | Latest successful backup time, failed tasks in last 7 days |
| Load | `CES ShowMetricData` | CPU/memory/connections/latency average |
| Deployment | `ShowInstance az_codes` | Master-slave cross-AZ |

### Grading Rules (Threshold-Based)

Each detection item is mapped to one of four levels: info / unknown / warning / critical.
Any critical item -> overall risk **blocked**; warning or unknown items -> **medium**; otherwise -> **low**.
Threshold table and business semantics: see [references/risk-model.md](references/risk-model.md).

### Blocking Mechanism

1. **Console**: prepare / execute phases prominently output overall level and each warning's impact and suggestion
2. **Report**: risk section embedded in `readiness_report.html` / `readiness_report.md`
3. **Execution block**: `execute` phase reads `risk_assessment.json`, blocks failover by default if critical items exist (unless user confirms to proceed)
4. **Anti-mismatch**: reject if risk assessment doesn't match the target instance; **anti-stale-snapshot**: real-time recheck of instance and node status before execution

> ⚠️ **Missing data is never misjudged, but not auto-passed**: when an API is unavailable (e.g. no permission, no CES data), the item is marked "unknown" with an explanation,
> never fabricating a critical risk; but unknown items raise overall risk to "medium", prompting manual confirmation before execution.

## CES Monitoring Metrics

During prepare phase risk assessment, the last 1 hour of CES data is queried. The monitoring config defines the following 8 DCS metrics (namespace SYS.DCS, dimension dcs_instance_id):

| Logic name | metric_name | Description | Unit |
|------------|-------------|-------------|------|
| dcs_cpu_util | cpu_usage | CPU usage | % |
| dcs_mem_util | memory_usage | Memory usage | % |
| dcs_conn_usage | connections_usage | Connection usage | % |
| dcs_ops | instantaneous_ops | Instantaneous ops per second | count |
| dcs_connected_clients | connected_clients | Connected clients | count |
| dcs_command_max_rt | command_max_rt | Max command latency | us |
| dcs_in_flow | instantaneous_input_kbps | Instantaneous input flow | KiB/s |
| dcs_out_flow | instantaneous_output_kbps | Instantaneous output flow | KiB/s |

## Composite Scoring

| Dimension | Weight | Basis |
|-----------|--------|-------|
| Failover | 40% | Failover success / duration (>30s deducts 10 per 10s) |
| Data | 30% | Consistency check pass ratio |
| Business | 30% | Default 100 (reserved for CES data deduction) |

Weighted total grade: >=85 excellent / >=70 good / >=60 fair / <60 poor

> 📌 Scoring is computed by the execute phase and written to `execution_result.json` (`scores` field); the HTML report does not currently render a scoring section.

## IAM Permission Requirements

| Permission | Description | Required |
|------------|-------------|----------|
| `dcs:instance:list` | List DCS instances | ✅ |
| `dcs:instance:get` | Get DCS instance detail | ✅ |
| `dcs:instance:getNodes` | Get master-slave node info | ✅ |
| `dcs:instance:modify` | Execute DCS master-slave failover (ChangeMasterStandby) | ✅ |
| `dcs:backup:list` | List backup records (risk assessment) | ✅ |
| `ces:metricData:get` | Query CES metric data | optional |

> 📌 Full IAM policy template (with Resource URN scope) see [references/iam-policies.md](references/iam-policies.md).

## Directory Structure

```
huawei-cloud-dcs-failover/
├── SKILL.md                          # This file
├── config/
│   └── config.json                   # Shared config (region + instance_id)
├── scripts/
│   ├── config.py                     # Config loading + run_hcloud + shared utils
│   ├── prepare.py                    # Phase 1: prepare checks (architecture hard-gate + risk assessment)
│   ├── risk.py                       # Risk assessment core module
│   ├── execute.py                    # Phase 2: execute failover (risk blocking, user confirm to proceed)
│   ├── report.py                     # Phase 3: generate report
│   └── run.py                        # Unified entry point (one-click full pipeline)
├── references/
│   ├── cli-installation-guide.md     # hcloud CLI installation and auth guide
│   ├── iam-policies.md               # IAM policy description
│   ├── acceptance-criteria.md        # Acceptance criteria
│   ├── verification-method.md        # Verification method
│   └── risk-model.md                 # Risk threshold table and business semantics
├── experiments/                      # Intermediate artifacts (auto-cleaned before/after run)
│   ├── experiment.json
│   ├── iam_policy.json
│   ├── monitoring.json
│   ├── execution_result.json
│   ├── risk_assessment.json
│   ├── readiness_report.html
│   └── readiness_report.md
└── templates/                        # Final deliverable directory (HTML report)
    └── failover_report_YYYYMMDD_HHMMSS.html
```

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | hcloud CLI installation and auth config guide |
| [references/iam-policies.md](references/iam-policies.md) | IAM policy template and config description |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Functional acceptance criteria and checklist |
| [references/verification-method.md](references/verification-method.md) | Environment and functional verification, end-to-end flow |
| [references/risk-model.md](references/risk-model.md) | Risk assessment threshold table and business semantics (risk model) |
