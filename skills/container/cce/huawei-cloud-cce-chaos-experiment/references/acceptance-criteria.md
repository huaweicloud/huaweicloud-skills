# Acceptance Criteria — CCE AZ Power Outage Experiment Skill

## Overview

These criteria define the minimum quality bar for the full lifecycle skill (prepare → execute → analyze) to be considered production-ready. **Scope: CCE cluster nodes in a specified availability zone, simulating AZ power outage via ECS BatchStopServers.**

## Phase 1: Prepare — Functional Criteria

### Discovery
- [ ] `discover_cce.py` queries CCE clusters via `hcloud CCE ShowCluster` with `--cli-region` parameter
- [ ] Supports two modes: cluster discovery (no `--cluster-id`) and node/pod discovery (with `--cluster-id` + `--az`)
- [ ] `--include-pods` flag adds Pod listing for each target node
- [ ] ECS instance IDs are obtained via `hcloud ECS ListServersDetails` (private-IP → ECS-ID mapping), not from `spec.providerID`
- [ ] Uses `KUBECONFIG` environment variable for kubectl access

### Validation
- [ ] `validate_targets.py` checks all target nodes are `Ready`
- [ ] Cross-AZ capacity check: compares target AZ CPU capacity vs surviving AZ allocatable CPU
- [ ] PDB constraints checked (warnings only — AZ shutdown bypasses eviction API)
- [ ] Workload replica count check (warning if single-replica workloads found on target nodes)
- [ ] Single-AZ cluster detection (error if cluster has only one AZ)
- [ ] CPU/memory parsing handles `m`, `Ki`, `Mi`, `Gi` suffixes

### Generation
- [ ] `generate_experiment.py` creates `experiment.json` with correct schema
- [ ] Creates `README.md` with experiment overview and rollback instructions
- [ ] `safety.require_confirmation` is set to `true`

### Deployment
- [ ] `deploy_experiment.sh` attempts COC API first, falls back to local config mode
- [ ] Generates `rollback_experiment.sh` in local mode
- [ ] Uses `set -euo pipefail` for error safety
- [ ] Uses named argument parsing

## Phase 2: Execute — Functional Criteria

### Experiment Execution
- [ ] `execute_experiment.py` loads `experiment.json` and executes 6-phase workflow
- [ ] Supports `--dry-run` (simulates without API calls)
- [ ] Supports `--auto-rollback` (rollback on shutdown failure)
- [ ] Pre-check validates all target nodes are `Ready` before proceeding
- [ ] Uses `hcloud ECS BatchStopServers` with flat parameter format (`--os-stop.servers.N.id`)
- [ ] Uses `hcloud ECS BatchStartServers` with flat parameter format (`--os-start.servers.N.id`)
- [ ] Generates `execution-log.json` with complete timeline

### Monitoring
- [ ] `monitor_resources.py` polls Node and Pod status at configurable intervals
- [ ] Records Node state transitions: Ready → NotReady, NotReady → Ready
- [ ] Records Pod state transitions: Running → Unknown → Pending
- [ ] Detects NotReady state and proceeds to wait phase

### Rollback
- [ ] `rollback_experiment.py` executes emergency BatchStartServers
- [ ] Can work from `--experiment-dir` or direct `--ids`
- [ ] Verifies recovery to Ready after rollback

### Report Generation
- [ ] `generate_report.py` produces Markdown report from execution log
- [ ] Report includes: overview, target AZ, phase timeline, node status changes, pod status changes, conclusions
- [ ] No network/API calls — reads only from local JSON log file

## Phase 3: Analyze — Functional Criteria

### Experiment Context Loading
- [ ] `analyze_logs.py` loads `execution-log.json` (post-hoc) or `experiment.json` (real-time)
- [ ] Auto-detects mode based on file availability
- [ ] Extracts time window, affected nodes, and affected pods from context

### Dependency Discovery
- [ ] `discover_dependencies.py` scans Services, Ingresses, and ConfigMaps
- [ ] Maps affected Pods to their owning workloads (ReplicaSet, DaemonSet, StatefulSet, Deployment)
- [ ] Identifies Services that route to affected Pods

### Log Collection
- [ ] `collect_logs.py` collects Pod logs via `kubectl logs --since-time`
- [ ] Handles deleted Pods gracefully (skip with message, try alive substitute)
- [ ] Collects Kubernetes Events via `kubectl get events`
- [ ] Queries LTS logs via `hcloud LTS` APIs (informational if no LTS groups configured)
- [ ] Time window covers experiment start to end

### Error Pattern Analysis
- [ ] Analyzes Kubernetes Events: FailedScheduling, TaintManagerEviction, NodeNotReady, NodeReady
- [ ] Analyzes Pod container logs for error patterns (ERROR, Exception, Connection refused, Timeout, 5xx)
- [ ] Categorizes findings by severity (high, medium, info)
- [ ] All pattern matching is local (no network calls during analysis)

### Analysis Report
- [ ] `generate_analysis_report.py` creates Markdown report from analysis result JSON
- [ ] Report includes: experiment overview, affected resources, pod rescheduling timeline, node status changes, error pattern statistics, business impact assessment, improvement recommendations
- [ ] No network calls in report generation

## Scope Constraints (CCE)

- [ ] Requires kubectl with CCE cluster access (not standalone ECS)
- [ ] Targets CCE managed nodes via ECS BatchStopServers (nodes are ECS instances managed by CCE)
- [ ] Pod rescheduling behavior is observed (Kubernetes scheduler, not just instance state)
- [ ] PDB warnings are informational (ECS shutdown bypasses Kubernetes eviction API)
- [ ] COC API integration is optional (local config mode as fallback)

## Security Criteria

- [ ] No hardcoded credentials in any file
- [ ] AK/SK read from environment variables via `os.environ.get("HW_ACCESS_KEY")`
- [ ] No hardcoded region values in SKILL.md command examples (use `<region>` / `<az>` placeholders)
- [ ] Region determined interactively (Step 1.2) — never silently default
- [ ] kubeconfig obtained fresh per session via `CreateKubernetesClusterCert`

## Documentation Criteria

- [ ] SKILL.md has YAML frontmatter with `name`, `description`, `tags`
- [ ] SKILL.md covers all three phases with workflow steps
- [ ] All command examples use `<region>` / `<az>` placeholders (no hardcoded `cn-north-4`)
- [ ] Interactive steps marked `[INTERACTIVE]` (cluster selection, AZ selection, region determination)
- [ ] Reference documents exist: `cli-installation-guide.md`, `iam-policies.md`, `cce-validation-rules.md`, `experiment-template-guide.md`, `execution-workflow.md`, `monitoring-guide.md`, `analysis-workflow.md`, `managed-service-logs.md`, `verification-method.md`, `acceptance-criteria.md`

## Code Quality Criteria

- [ ] All shell scripts use `set -euo pipefail` right after shebang
- [ ] All shell scripts use named argument parsing (not positional `$1`/`$2`)
- [ ] All Python scripts use `argparse` for named arguments
- [ ] Python scripts use `os.environ.get("HW_REGION_NAME", "cn-north-4")` as fallback default
- [ ] No `__pycache__` or `.pyc` files committed
- [ ] No runtime artifacts committed (discovery.json, validation.json, experiments/, log-analysis-output/)
- [ ] No empty files
