---
name: huawei-cloud-ecs-shutdown-experiment
description: "Full lifecycle ECS shutdown fault injection experiment for Huawei Cloud chaos engineering: prepare → execute → analyze. Phase 1 discovers target ECS instances, validates compatibility, generates experiment configuration. Phase 2 executes BatchStopServers shutdown, polls status, holds for duration, rolls back via BatchStartServers, verifies recovery, generates execution report. Phase 3 collects CES monitoring metrics and LTS application logs, analyzes error patterns, generates analysis report. Key safety: --dry-run, --auto-rollback, mandatory --yes confirmation, independent emergency rollback script. Triggers: ECS故障演练, ECS关机实验, chaos engineering, 故障注入, ECS shutdown experiment, 演练准备, 执行实验, 运行实验, 启动演练, 执行 ECS 关机故障演练, 分析应用日志, 查看应用表现, 应用日志分析, 故障影响分析, experiment prepare, experiment execute, analyze app logs, log analysis."
tags: [huawei-cloud, ecs, chaos-engineering, fault-injection, experiment, log-analysis]
---

# Huawei Cloud ECS Shutdown Chaos Experiment

> **⚠️ This skill performs real ECS shutdown operations in Phase 2. Ensure target instances can tolerate downtime. Emergency rollback is always available.**

## Overview

Full lifecycle ECS shutdown fault injection experiment for Huawei Cloud chaos engineering, covering three phases:

| Phase | Name | Action | Key Output |
|---|---|---|---|
| 1 | Prepare | Discover, validate, generate config | `experiment.json` + `rollback_experiment.sh` |
| 2 | Execute | Shutdown → hold → rollback → verify | `execution-log.json` + `execution-report.md` |
| 3 | Analyze | Collect CES metrics + LTS logs, analyze patterns | `log-analysis-result.json` + `log-analysis-report.md` |

**Scope**: standalone ECS instances in any availability zone (non-CCE).

## Prerequisites

- **hcloud CLI (KooCLI)** — installed and configured with AK/SK. See `references/cli-installation-guide.md`.
- **Python 3** — for discovery, validation, execution, and analysis scripts.
- **Environment variables**: `HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_REGION_NAME` (optional, default `cn-north-4`).
- **IAM permissions**: varies by phase — see `references/iam-policies.md` for the full matrix.
- **Phase 3 only**: LTS log group ID (find via `hcloud LTS ListLogGroups` or LTS console).

Environment check (run before any phase):
```bash
bash scripts/check_env.sh --cli-region <region>
```

## Phase 1: Prepare

> **Does NOT start the experiment.** Only discovers targets, validates compatibility, and generates configuration files.

### Step 1.1: Discover Target ECS Instances

```bash
python3 scripts/discover_ecs.py --cli-region <region>
python3 scripts/discover_ecs.py --cli-region <region> --az cn-north-4a --status ACTIVE
python3 scripts/discover_ecs.py --cli-region <region> --name-pattern "web-"
```

Output: JSON with instance ID, name, status, AZ, flavor, charging mode, and tags.

### Step 1.2: Validate Compatibility [CRITICAL GATE]

```bash
python3 scripts/validate_targets.py --instances-file instances.json --cli-region <region>
```

Validation rules (see `references/ecs-validation-rules.md` for details):
1. **Status must be ACTIVE** — can only shut down running instances
2. **Spot/bidding instance warning** — may be released instead of stopped
3. **AS group association** — shutdown may trigger auto-scaling activity
4. **Single-AZ risk** — no cross-AZ redundancy if all targets in one AZ

**Decision**: errors → stop and fix; warnings only → review with user before proceeding.

### Step 1.3: Generate Experiment Configuration

```bash
python3 scripts/generate_experiment.py \
    --targets "i-xxx,i-yyy" --cli-region <region> --duration 300 --output-dir ./experiments
```

Output directory: `{timestamp}-ecs-shutdown-{slug}/` containing `experiment.json` + `README.md`. See `references/experiment-template-guide.md` for schema.

### Step 1.4: Deploy Experiment

```bash
bash scripts/deploy_experiment.sh --experiment-dir ./experiments/{dir}/ --cli-region <region>
```

Generates `rollback_experiment.sh` (emergency rollback script) in the experiment directory.

### Step 1.5: Review

Experiment is prepared but **NOT started**. Review `experiment.json` and `README.md`, then proceed to Phase 2 when ready.

## Phase 2: Execute

> **Real shutdown operation.** Target ECS instances are stopped. Ensure `experiment.json` from Phase 1 is available.

### Step 2.1: Execute the Experiment

```bash
# Real execution (--yes is mandatory; default refuses without it)
python3 scripts/execute_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region> --yes

# Dry Run (simulated, no API calls)
python3 scripts/execute_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region> --dry-run

# Auto-rollback when shutdown fails
python3 scripts/execute_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region> --auto-rollback --yes
```

6-phase execution flow (see `references/execution-workflow.md` for details):

| Phase | Action | Description |
|---|---|---|
| 1. Pre-check | Query status | All instances must be ACTIVE |
| 2. Shutdown | `BatchStopServers` | Inject the fault |
| 3. Monitor | Poll status | Wait until all reach SHUTOFF |
| 4. Wait | `sleep(duration)` | Hold with stop-condition checks |
| 5. Rollback | `BatchStartServers` | Restore instances |
| 6. Verify | Poll status | Confirm all back to ACTIVE |

Output: `execution-log.json` with full execution timeline and state changes.

### Step 2.2: Generate Execution Report

```bash
python3 scripts/generate_report.py --log-file ./experiments/xxx/execution-log.json
```

Report contains: experiment overview, target instances, phase timeline, state changes, conclusions.

### Emergency Rollback

If the experiment must be terminated early:

```bash
python3 scripts/rollback_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region>
# Or pass instance IDs directly:
python3 scripts/rollback_experiment.py --ids "i-xxx,i-yyy" --cli-region <region>
```

## Phase 3: Analyze

> Collect CES monitoring metrics and LTS application logs to understand how applications respond to the infrastructure failure. Supports post-hoc mode (after experiment) and real-time mode (during experiment).

### Step 3.1: Load Experiment Context

Auto-detect mode: `execution-log.json` found → post-hoc; falls back to `experiment.json` → real-time.

### Step 3.2: Run Full Analysis Pipeline

```bash
python3 scripts/analyze_logs.py \
    --experiment-dir ./experiments/xxx/ \
    --cli-region <region> \
    --log-group-id <lts-group-id>

# Dry run (verify workflow without API calls)
python3 scripts/analyze_logs.py --experiment-dir ./experiments/xxx/ --dry-run
```

The pipeline executes steps 3.3–3.6 automatically. See `references/analysis-workflow.md` for details.

### Step 3.3: Collect CES Monitoring Metrics

Queries 6 metrics via `hcloud CES ShowMetricData` (see `references/managed-service-logs.md` → CES section):

| Namespace | Metric | Label | Requires Agent? |
|---|---|---|---|
| `SYS.ECS` | `cpu_util` | CPU Utilization | No |
| `SYS.ECS` | `network_incoming_bytes_aggregate_rate` | Network Incoming Rate | No |
| `SYS.ECS` | `network_outgoing_bytes_aggregate_rate` | Network Outgoing Rate | No |
| `SYS.ECS` | `disk_read_bytes_rate` | Disk Read Rate | No |
| `SYS.ECS` | `disk_write_bytes_rate` | Disk Write Rate | No |
| `AGT.ECS` | `mem_usedPercent` | Memory Usage | Yes |

Metrics summarized by phase (pre-shutdown / during-shutdown / post-recovery). Query uses `period=300` (5-min aggregation for SYS.ECS).

### Step 3.4: Collect Logs (LTS)

Queries LTS log group within experiment time window. `--log-group-id` is required (find via `hcloud LTS ListLogGroups`). Missing group / empty result = no LTS data, NOT "application unaffected" — check ICAgent config.

### Step 3.5: Analyze Error Patterns

Local pattern matching (no network calls):

| Pattern | Severity |
|---|---|
| ERROR/Exception/Traceback | high |
| Connection refused | high |
| Timeout | high |
| HTTP 5xx | high |
| Reconnect/retry | medium |
| Degrade/circuit breaker | medium |
| Recovery/restored | info |

### Step 3.6: Generate Analysis Report

```bash
python3 scripts/generate_analysis_report.py --result-file ./experiments/xxx/log-analysis-result.json
```

Report contains: experiment overview, affected instances, LTS log sources, instance state timeline, CES monitoring metrics, error pattern statistics, error event timeline, application behavior assessment, improvement suggestions.

## Parameter Confirmation

Before each phase's core operation, confirm with the user:

| Phase | What to Confirm | Mandatory? |
|---|---|---|
| 1 (Generate) | Target instance IDs + names, duration, validation warnings | ✅ Yes |
| 2 (Execute) | Experiment name, target count, duration, dry-run flag | ✅ Yes — `--yes` required for real execution |
| 3 (Analyze) | Experiment directory, detected mode, time window, LTS log group ID | ✅ Yes |

Wait for explicit confirmation ("确认" / "confirm" / "ok") before proceeding.

## Core Commands

> `<region>` = region, defaults to `cn-north-4` (`HW_REGION_NAME` overrides if set). The placeholder may be omitted at runtime — scripts fall back to the default region.

```bash
# Environment check (all phases)
bash scripts/check_env.sh --cli-region <region>

# Phase 1: Prepare
python3 scripts/discover_ecs.py --cli-region <region>
python3 scripts/validate_targets.py --instances-file instances.json --cli-region <region>
python3 scripts/generate_experiment.py --targets "i-xxx,i-yyy" --cli-region <region> --duration 300
bash scripts/deploy_experiment.sh --experiment-dir ./experiments/{dir}/ --cli-region <region>

# Phase 2: Execute
python3 scripts/execute_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region> --yes
python3 scripts/generate_report.py --log-file ./experiments/xxx/execution-log.json
python3 scripts/rollback_experiment.py --experiment-dir ./experiments/xxx/ --cli-region <region>  # emergency

# Phase 3: Analyze
hcloud LTS ListLogGroups --cli-region=<region> --cli-output=json  # find log group
python3 scripts/analyze_logs.py --experiment-dir ./experiments/xxx/ --cli-region <region> --log-group-id <id>
python3 scripts/generate_analysis_report.py --result-file ./experiments/xxx/log-analysis-result.json
```

## KooCLI Command Format Standard

All hcloud CLI commands follow this format:

```
hcloud <Service> <Action> --cli-region=<region> --cli-output=json [--param=value ...]
```

- **`--cli-region=<region>`**: always explicit. KooCLI 7.2.x requires `--param=value` syntax (equals sign); space-separated `--cli-region cn-north-4` is rejected with `[USE_ERROR]`.
- **`--cli-output=json`**: all commands, for machine-parseable output.
- **Batch operations use flat parameters** (not `--body`):
  - Stop: `--os-stop.servers.1.id=<id> --os-stop.type=SOFT`
  - Start: `--os-start.servers.1.id=<id>`
- **Fetch in batch, filter locally**: `ListServersDetails` with `--limit=1000` + paging; no N+1 queries.
- **Credentials via environment variables**: AK/SK passed through `HW_ACCESS_KEY` / `HW_SECRET_KEY`, never hardcoded.

## Script Reference

| Script | Phase | Purpose |
|---|---|---|
| `scripts/check_env.sh` | All | Environment verification |
| `scripts/discover_ecs.py` | 1 | Discover ECS instances |
| `scripts/validate_targets.py` | 1 | Validate target compatibility |
| `scripts/generate_experiment.py` | 1 | Generate experiment config |
| `scripts/deploy_experiment.sh` | 1 | Deploy experiment (local mode) |
| `scripts/execute_experiment.py` | 2 | Main execution script (6-phase flow) |
| `scripts/monitor_instances.py` | 2 | Instance status monitoring |
| `scripts/rollback_experiment.py` | 2 | Emergency rollback |
| `scripts/generate_report.py` | 2 | Generate execution report |
| `scripts/collect_logs.py` | 3 | LTS log collection + ECS endpoint query |
| `scripts/collect_ces_metrics.py` | 3 | CES monitoring metrics collection |
| `scripts/analyze_logs.py` | 3 | Main analysis pipeline orchestrator |
| `scripts/generate_analysis_report.py` | 3 | Generate Markdown analysis report |

## Reference Documents

| Document | Phase | Description |
|---|---|---|
| `references/cli-installation-guide.md` | All | hcloud KooCLI installation and configuration |
| `references/iam-policies.md` | All | IAM permissions by phase |
| `references/ecs-validation-rules.md` | 1 | Validation rules with rationale |
| `references/experiment-template-guide.md` | 1 | experiment.json schema |
| `references/execution-workflow.md` | 2 | Detailed execution workflow (per-phase I/O, exceptions) |
| `references/monitoring-guide.md` | 2 | Monitoring guide (state machine, polling, CES alarms) |
| `references/analysis-workflow.md` | 3 | Detailed analysis workflow |
| `references/managed-service-logs.md` | 3 | Managed-service log reference (CES, LTS, audit) |
| `references/verification-method.md` | All | Verification methodology (all phases) |
| `references/acceptance-criteria.md` | All | Acceptance criteria (all phases) |

## Key Safety Features

1. **Dry Run mode** — `--dry-run` simulates the full flow without API calls (Phase 2 & 3)
2. **Auto-rollback** — `--auto-rollback` starts instances back up when shutdown fails
3. **Independent rollback script** — `rollback_experiment.py` is standalone, does not depend on main script state
4. **Full logging** — `execution-log.json` records per-phase timestamps and state changes
5. **Pre-check gate** — verifies all instances are ACTIVE before execution
6. **Stop-condition early rollback** — CES alarm fires → skip remaining duration → rollback immediately
7. **Mandatory confirmation** — real execution requires explicit `--yes`; otherwise refuses
8. **Environment variable whitelist** — child processes receive only necessary vars, not full `os.environ`

## ECS Instance State Machine

```
Stop:    ACTIVE → STOPPING → SHUTOFF
Start:   SHUTOFF → STARTING → ACTIVE
Abnormal: any → ERROR
```

## Limitations

- Depends on hcloud CLI with sufficient ECS permissions (BatchStopServers, BatchStartServers, ListServersDetails)
- AS group check requires AS API access (skipped if unavailable)
- CES `SYS.ECS` metrics are aggregated at 5-minute granularity (period=300); shorter periods return empty
- CES API may be unreachable in sandboxed environments — see `references/managed-service-logs.md` → CES section
- `AGT.ECS` metrics (memory) require telescope/uniagent Agent installed inside the ECS
- LTS collection requires ICAgent shipping logs to a LTS log group; missing group = no data, not "unaffected"
- Does not support composite scenarios (e.g., multi-action AZ-level interruption) — focused on single ECS shutdown
- In real-time mode `instance_timeline` is unavailable, so recovery-time analysis is skipped
- Error-pattern analysis is based on string matching and may miss unusual log formats
