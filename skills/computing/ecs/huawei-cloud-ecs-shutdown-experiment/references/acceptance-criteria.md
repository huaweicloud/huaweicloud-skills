# Acceptance Criteria — ECS Shutdown Experiment Skill

## Overview

These criteria define the minimum quality bar for the full lifecycle skill (prepare → execute → analyze) to be considered production-ready. **Scope: standalone ECS instances in any availability zone (non-CCE).**

## Phase 1: Prepare — Functional Criteria

### Discovery
- [ ] `discover_ecs.py` queries ECS instances via `hcloud ECS ListServersDetails` with `--cli-region` parameter
- [ ] Supports filtering by AZ, name pattern, instance IDs, and status
- [ ] Uses batch-query pattern (single API call + local filtering, no N+1)

### Validation
- [ ] `validate_targets.py` checks instance status is ACTIVE
- [ ] Flags spot/bidding instances as warnings
- [ ] Checks AS group association via batch query (single `ListScalingInstances` call)
- [ ] Detects single-AZ deployment risk
- [ ] Returns clear `recommendation` field

### Generation
- [ ] `generate_experiment.py` creates `experiment.json` with correct schema
- [ ] Creates `README.md` with experiment overview and instructions
- [ ] `safety.require_confirmation` is set to `true`

### Deployment
- [ ] `deploy_experiment.sh` deploys in local config mode
- [ ] Generates `rollback_experiment.sh` in local mode
- [ ] Uses `set -euo pipefail` for error safety
- [ ] Uses named argument parsing

## Phase 2: Execute — Functional Criteria

### Experiment Execution
- [ ] `execute_experiment.py` loads `experiment.json` and executes 6-phase workflow
- [ ] Supports `--dry-run` (simulates without API calls)
- [ ] Supports `--auto-rollback` (rollback on shutdown failure)
- [ ] Pre-check validates all instances are ACTIVE before proceeding
- [ ] Generates `execution-log.json` with complete timeline

### Monitoring
- [ ] `monitor_instances.py` polls instance status at configurable intervals
- [ ] Uses batch query pattern with paging (`ListServersDetails` with `--limit` + `--offset`)
- [ ] Records state transitions with timestamps
- [ ] Supports CES alarm-based stop conditions
- [ ] Detects ERROR state and triggers immediate stop

### Rollback
- [ ] `rollback_experiment.py` executes emergency BatchStartServers
- [ ] Can work from `--experiment-dir` or direct `--ids`
- [ ] Verifies recovery to ACTIVE after rollback

### Report Generation
- [ ] `generate_report.py` produces Markdown report from execution log
- [ ] Report includes: overview, target instances, phase timeline, state changes, conclusions
- [ ] No network/API calls — reads only from local JSON log file

## Phase 3: Analyze — Functional Criteria

### Experiment Context Loading
- [ ] `analyze_logs.py` loads `execution-log.json` (post-hoc) or `experiment.json` (real-time)
- [ ] Auto-detects mode based on file availability
- [ ] Real-time mode computes time window as `now → now + duration + 3min`

### Log Collection
- [ ] `collect_logs.py` queries LTS logs via `hcloud LTS ListLogs` with `--cli-region`
- [ ] `analyze_logs.py` requires `--log-group-id` for real analysis (allowed to omit only with `--dry-run`)
- [ ] Time window covers experiment start to end + 3 minutes buffer

### CES Metrics Collection
- [ ] `collect_ces_metrics.py` queries 5 SYS.ECS metrics + 1 AGT.ECS metric via `hcloud CES ShowMetricData`
- [ ] Uses `period=300` for SYS.ECS (5-min aggregation)
- [ ] Summarizes metrics by experiment phase (pre-shutdown / during-shutdown / post-recovery)
- [ ] Extends query window +10 min before start and +10 min after end

### Error Pattern Analysis
- [ ] Matches 7 error patterns: ERROR/Exception, connection refused, timeout, HTTP 5xx, reconnect, degrade, recovery
- [ ] Categorizes by severity (high, medium, info)
- [ ] All pattern matching is local (no network calls during analysis)

### Analysis Report
- [ ] `generate_analysis_report.py` creates Markdown report from analysis result JSON
- [ ] Report includes: experiment overview, affected instances, LTS log sources, instance timeline, CES monitoring metrics, error pattern statistics, error event timeline, assessment, suggestions
- [ ] No network calls in report generation

## Scope Constraints (non-CCE)

- [ ] No kubectl dependency anywhere in the pipeline
- [ ] No CCE cluster scanning / dependency discovery
- [ ] LTS log group is user-provided via `--log-group-id`, not auto-discovered from cluster IDs
- [ ] No CCE permissions required in IAM policy examples

## Security Criteria

- [ ] No hardcoded credentials in any file
- [ ] AK/SK read from environment variables by individual name via `os.environ.get("HW_ACCESS_KEY")`
- [ ] Subprocess environment built from explicit whitelist, never full `os.environ` inheritance
- [ ] No direct references to other skill names in scripts (no cross-skill invocation)

## Documentation Criteria

- [ ] SKILL.md has YAML frontmatter with `name`, `description`, `tags`
- [ ] SKILL.md covers all three phases with workflow steps
- [ ] All command examples use `--cli-region` parameter
- [ ] Reference documents exist: `cli-installation-guide.md`, `iam-policies.md`, `ecs-validation-rules.md`, `experiment-template-guide.md`, `execution-workflow.md`, `monitoring-guide.md`, `analysis-workflow.md`, `managed-service-logs.md`, `verification-method.md`, `acceptance-criteria.md`

## Code Quality Criteria

- [ ] All shell scripts use `set -euo pipefail` right after shebang
- [ ] All shell scripts use named argument parsing (not positional `$1`/`$2`)
- [ ] All Python scripts use `argparse` for named arguments
- [ ] No N+1 network call patterns (batch query + local filter)
- [ ] No `__pycache__` or `.pyc` files committed
- [ ] No empty files
