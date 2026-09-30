---
name: huawei-cloud-cce-chaos-experiment
description: "Huawei Cloud CCE AZ power outage chaos experiment — end-to-end fault drill: discover clusters and node AZ distribution, validate cross-AZ capacity, shut down all CCE nodes in one AZ to simulate a power failure, observe Pod eviction and rescheduling to surviving AZs, then start nodes back and verify recovery, and optionally analyze logs for an impact report. Use this skill when the user wants to run or prepare a CCE fault drill / chaos experiment / AZ outage drill. Triggers: CCE, 故障演练, 混沌演练, AZ断电, 演练, 故障注入, chaos experiment, AZ power outage, fault drill, chaos drill."
triggers: ["CCE", "故障演练", "混沌演练", "AZ断电", "演练", "故障注入", "chaos experiment", "AZ power outage", "fault drill", "chaos drill"]
---
# Huawei Cloud CCE AZ Power Outage Chaos Experiment

## Overview

End-to-end CCE AZ power outage chaos experiment in three phases:

```
Phase 1: Prepare          Phase 2: Execute           Phase 3: Log Analysis
─────────────             ──────────────             ──────────────────
Discover clusters    →    Pre-check (nodes Ready)  → Load experiment context
Select cluster            Shutdown (BatchStop)       Discover dependencies
Discover node AZs         Monitor (Node/Pod)         Collect logs (LTS + Pod)
Select target AZ          Wait (duration)            Analyze error patterns
Validate compatibility    Rollback (BatchStart)      Generate analysis report
Generate + deploy config  Verify + report
```

**Scenario**: Shut down all CCE nodes in one AZ → Kubernetes marks nodes NotReady → Pods
evicted and rescheduled to other AZs → start nodes back → verify recovery. Tests cluster
HA under AZ-level failure.

## Prerequisites

- **hcloud CLI** — installed and configured with AK/SK (ECS + CCE permissions)
- **kubectl** — installed and configured for CCE cluster access
- **Python 3** — for discovery, validation, execution, and analysis scripts
- **Environment variables**: `HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_REGION_NAME` (optional, defaults to cn-north-4 if unset)

Run environment check:
```bash
bash scripts/check_env.sh
```

If kubectl is missing, `check_env.sh` auto-installs it. Manual install:
```bash
ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
curl -fsSL "https://dl.k8s.io/release/v1.28.0/bin/linux/${ARCH}/kubectl" -o /tmp/kubectl_download
sleep 1 && mv /tmp/kubectl_download /usr/local/bin/kubectl && chmod 755 /usr/local/bin/kubectl
```

## Phase 1: Prepare (故障演练准备)

> Generates experiment configuration. Does NOT start the experiment.

### Step 1.1: Environment Check
```bash
bash scripts/check_env.sh
```

### Step 1.2: Determine Region [INTERACTIVE]

Check `HW_REGION_NAME` environment variable:
- **Set** → use that region (confirm with user: "Region is <region>, correct?").
- **Not set** → **ask the user** which region to use. Do NOT silently default to `cn-north-4`.

```bash
echo $HW_REGION_NAME
```

Region is used in all subsequent `--region` parameters and `hcloud --cli-region` calls.

### Step 1.3: Discover CCE Clusters
```bash
python3 scripts/discover_cce.py --region <region>
```
Output: JSON with all clusters (ID, name, status, flavor, version).

### Step 1.4: User Selects Cluster [INTERACTIVE]

Present discovered clusters in a table. **Ask the user to choose** — never auto-select.
- Only `Available` clusters can be selected directly.
- `Hibernation` clusters must be awakened first.

### Step 1.5: Get Credentials & Discover Node AZ Distribution
```bash
# Obtain kubeconfig
hcloud CCE CreateKubernetesClusterCert --cluster_id=<id> --cli-region=<region> --duration=30 --cli-output=json > /root/.kube/config

# Discover node AZ distribution
KUBECONFIG=/root/.kube/config kubectl get nodes --show-labels
```
Present node-to-AZ mapping to the user.

### Step 1.6: User Selects Target AZ [INTERACTIVE]

Present AZ distribution. **Ask the user to choose** the target AZ.
- Show node count per AZ.
- Warn if cluster has only one AZ (no cross-AZ redundancy).
- Never auto-select.

### Step 1.7: Create Experiment Directory

Create the experiment directory before running discovery and validation, so all
artifacts (discovery.json, validation.json, experiment.json, logs, reports) live
inside one directory.

```bash
EXP_DIR="./experiments/$(date -u +%Y%m%d-%H%M%S)-cce-az-power-$(echo <az> | tr -d '-')"
mkdir -p "$EXP_DIR"
echo "$EXP_DIR"
```

All subsequent steps use `$EXP_DIR` as the output path.

### Step 1.8: Discover Nodes & Pods in Target AZ
```bash
KUBECONFIG=/root/.kube/config python3 scripts/discover_cce.py \
    --region <region> --cluster-id <id> --az <az> \
    --include-pods --output "$EXP_DIR/discovery.json"
```

### Step 1.9: Validate Compatibility [CRITICAL GATE]
```bash
KUBECONFIG=/root/.kube/config python3 scripts/validate_targets.py \
    --discovery-file "$EXP_DIR/discovery.json" \
    --cluster-id <id> --az <az> --region <region> \
    --output "$EXP_DIR/validation.json"
```

Validation rules (see `references/cce-validation-rules.md`):
1. All target nodes must be Ready
2. Cross-AZ capacity sufficient for rescheduling
3. PDB constraints checked (warnings only for AZ outage — shutdown bypasses eviction API)
4. Workload replicas ≥ 2 (warning)
5. Single-AZ cluster risk (error)

**Decision**: errors → stop and fix. warnings only → proceed to generate.

### Step 1.10: Generate, Deploy & Report
```bash
# Generate experiment configuration (use --experiment-dir to reuse $EXP_DIR)
python3 scripts/generate_experiment.py \
    --discovery-file "$EXP_DIR/discovery.json" --validation-file "$EXP_DIR/validation.json" \
    --cluster-id <id> --az <az> --region <region> \
    --duration 300 --experiment-dir "$EXP_DIR"

# Deploy experiment (local mode, generates emergency rollback script)
bash scripts/deploy_experiment.sh --experiment-dir "$EXP_DIR/"
```

Experiment is prepared but **NOT started**. Proceed to Phase 2 when ready.

### Phase 1 References
- `references/cce-az-power-scenario.md` — scenario definition, fault impact chain, API mapping
- `references/cce-validation-rules.md` — validation rules with rationale and decision matrix
- `references/experiment-template-guide.md` — experiment.json schema with full example

## Phase 2: Execute (故障演练执行)

> Performs actual node shutdown. Target CCE nodes will be stopped.

### Step 2.1: Environment Check
```bash
bash scripts/check_env.sh
```

### Step 2.2: Execute Experiment [Core Step]
```bash
# Normal execution
python3 scripts/execute_experiment.py --experiment-dir "$EXP_DIR/"

# Dry Run (simulate without API calls)
python3 scripts/execute_experiment.py --experiment-dir "$EXP_DIR/" --dry-run

# Auto-rollback on shutdown failure
python3 scripts/execute_experiment.py --experiment-dir "$EXP_DIR/" --auto-rollback
```

### 6 Execution Phases

| Phase | Operation | Description |
|---|---|---|
| 1. Pre-check | `kubectl get nodes` | All target nodes must be Ready |
| 2. Shutdown | `hcloud ECS BatchStopServers` | Execute fault injection |
| 3. Monitor | Poll Node + Pod status | Wait for NotReady + Pod rescheduling |
| 4. Wait | `sleep(duration)` | Experiment duration |
| 5. Rollback | `hcloud ECS BatchStartServers` | Start all target nodes |
| 6. Verify | Poll Node + Pod status | Confirm Ready + Running + replicas met |

Produces `execution-log.json` with complete timeline.

### Step 2.3: Generate Report
```bash
python3 scripts/generate_report.py --log-file "$EXP_DIR/execution-log.json"
```

### Emergency Rollback
```bash
python3 scripts/rollback_experiment.py --experiment-dir "$EXP_DIR/"
# Or specify instance IDs directly
python3 scripts/rollback_experiment.py --ids "id1,id2" --region <region>
```

### Phase 2 References
- `references/execution-workflow.md` — 6-phase details, execution-log.json format, safety mechanisms
- `references/monitoring-guide.md` — Node/Pod state machines, polling mechanism

### CCE Resource State Machine

```
Node:  Ready ──关机──→ NotReady ──开机──→ Ready
Pod:   Running → Terminating → Pending → Running (on new node in other AZ)
```

## Phase 3: Log Analysis (生成日志分析报告)

> Collects and analyzes application/CCE logs within the experiment time window.

### Step 3.1: Environment Check
```bash
bash scripts/check_env.sh
```

### Step 3.2: Load Experiment Context & Analyze Logs
```bash
python3 scripts/analyze_logs.py --experiment-dir "$EXP_DIR/" \
    --output-dir "$EXP_DIR/log-analysis"
```
Auto-detects mode:
- `execution-log.json` exists → post-hoc analysis (事后分析)
- Only `experiment.json` exists → real-time monitoring (实时监控)

### Step 3.3: Discover Affected Services
```bash
# Extract affected node names from discovery.json or use known nodes
python3 scripts/discover_dependencies.py \
    --nodes "192.168.0.49,..." \
    --output "$EXP_DIR/log-analysis/dependencies.json"
```
Scans Service/Ingress/ConfigMap references to identify directly impacted services.
Note: `discover_dependencies.py` queries the cluster directly via kubectl, not from discovery.json. Pass the affected node names with `--nodes`.

> **Tip**: Step 3.2 (`analyze_logs.py`) already calls `discover_dependencies.py` internally, so this step is optional — use it only for standalone dependency discovery.

### Step 3.4: Collect Logs
```bash
python3 scripts/collect_logs.py --experiment-dir "$EXP_DIR/" \
    --output-dir "$EXP_DIR/log-analysis/collected_logs"
```
Collects within experiment time window:
- CCE Pod logs: `kubectl logs --since-time`
- LTS logs: `hcloud LTS ListLogs`
- Kubernetes Events: `kubectl get events`

### Step 3.5: Generate Analysis Report
```bash
python3 scripts/generate_analysis_report.py \
    --analysis "$EXP_DIR/log-analysis/analysis-result.json" \
    --context "$EXP_DIR/log-analysis/dependencies.json" \
    --output "$EXP_DIR/log-analysis/analysis-report.md"
```
Output: Markdown report with:
- Experiment overview & affected services
- Pod rescheduling timeline
- Error pattern statistics (ERROR/Exception/Connection refused/Timeout/5xx)
- Business impact assessment
- Improvement recommendations

### Phase 3 References
- `references/analysis-workflow.md` — 6-step analysis workflow, error pattern classification table
- `references/managed-service-logs.md` — kubectl logs, LTS, CES commands, best practices

### Error Pattern Classification

| Pattern | Keywords | Severity | Description |
|---|---|---|---|
| ERROR | error | High | Application error |
| Exception | exception, stacktrace | High | Exception stack trace |
| Connection refused | connection refused | High | Service unavailable |
| Timeout | timeout, deadline exceeded | Medium | Timeout |
| 5xx HTTP | 500, 502, 503, 504 | High | Server error |
| Reconnect | reconnect, reconnected | Low | Reconnected successfully |
| Degraded | degrad | Medium | Degraded mode |
| Recovered | recover, restored | Low | Recovered |

## Script Reference

| Script | Phase | Purpose |
|---|---|---|
| `scripts/check_env.sh` | All | Environment verification (shared) |
| `scripts/discover_cce.py` | 1 | Discover CCE clusters and AZ nodes |
| `scripts/validate_targets.py` | 1 | Validate cross-AZ capacity and PDB |
| `scripts/generate_experiment.py` | 1 | Generate experiment config |
| `scripts/deploy_experiment.sh` | 1 | Deploy experiment (local mode, generate rollback script) |
| `scripts/execute_experiment.py` | 2 | Main execution (6 phases) |
| `scripts/monitor_resources.py` | 2 | Monitor Node/Pod status (called by execute) |
| `scripts/rollback_experiment.py` | 2 | Emergency rollback |
| `scripts/generate_report.py` | 2 | Generate Markdown execution report |
| `scripts/analyze_logs.py` | 3 | Main analysis orchestration |
| `scripts/discover_dependencies.py` | 3 | Discover CCE service dependencies |
| `scripts/collect_logs.py` | 3 | Collect LTS + CCE Pod logs |
| `scripts/generate_analysis_report.py` | 3 | Generate Markdown analysis report |

## Key Design Decisions

1. **Interactive cluster and AZ selection** — the agent must present discovered clusters and AZ distributions to the user and let the user choose. Never auto-select.

2. **Validate before generating** — cross-AZ capacity and PDB constraints are checked before any files are produced.

3. **PDB warnings are informational for AZ outage** — PDBs govern voluntary pod eviction, not direct node shutdown via ECS API. PDB violations are warnings, not errors.

4. **Dry Run and auto-rollback** — `--dry-run` simulates without API calls; `--auto-rollback` triggers rollback on shutdown failure.

5. **Local deployment mode** — `deploy_experiment.sh` generates the emergency rollback script locally; the full drill flow is executed by the built-in `scripts/execute_experiment.py` (no external COC dependency).

6. **AZ-scoped targeting** — targets all CCE nodes in a specified AZ, simulating real AZ power outage.

7. **Default duration 5 minutes (300s)** — sufficient for observing pod rescheduling while limiting blast radius.

8. **Two analysis modes** — post-hoc (from execution-log.json) and real-time (from experiment.json during experiment).

9. **All artifacts in one experiment directory** — `$EXP_DIR` is created before discovery; discovery.json, validation.json, experiment.json, execution-log.json, and log-analysis/ all live inside it.

## Known Script Issues & Fixes

1. **`discover_cce.py` — invalid kubeconfig detection**: `hcloud CCE DownloadClusterConfig` returns error with exit code 0 on unsupported versions. Fix: validate config contains `"apiVersion"` or `"clusters"`; use `CreateKubernetesClusterCert` as fallback.

2. **`discover_cce.py` — `get_nodes_by_az` return value**: Returned `[]` instead of `[], []` on kubectl failure, causing ValueError. Fix: return `[], []`.

3. **`validate_targets.py` — CPU millicore parsing**: `float("1930m")` caused ValueError. Fix: `parse_cpu()` / `parse_memory()` helpers handle `m`, `Ki`, `Mi`, `Gi` suffixes.

4. **`discover_cce.py` — wrong ECS instance ID**: Extracted from `spec.providerID` which contains CCE-internal node ID, not ECS server ID. Fix: `get_ecs_instance_map(region)` queries `hcloud ECS ListServersDetails` and builds private-IP → ECS-ID map.

5. **`deploy_experiment.sh` + `execute_experiment.py` + `rollback_experiment.py` — unsupported `--body` parameter**: hcloud KooCLI does not support `--body` for ECS APIs. Fix: use native parameter format `--os-stop.servers.1.id=xxx --os-stop.type=SOFT` and `--os-start.servers.N.id=xxx`.

## Limitations

- Depends on hcloud CLI with ECS and CCE permissions
- Depends on kubectl with CCE cluster access
- Cross-AZ capacity check based on node allocatable resources, not real-time usage
- Pod logs only from currently alive Pods; deleted Pod logs unavailable
- LTS log queries require LTS agent (ICAgent) installed in CCE cluster
- Focused on single AZ power outage — does not handle composite scenarios
