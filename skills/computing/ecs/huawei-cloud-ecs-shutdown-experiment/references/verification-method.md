# Verification Method — How to Verify Experiment Results

## Overview

After running each phase of the ECS shutdown experiment, verify that all outputs are correct and complete before proceeding to the next phase.

## Phase 1: Prepare — Verification

### 1.1 Discovery Output

Verify `discover_ecs.py` output:
- JSON is valid and parseable
- `total` field matches the number of returned instances
- Each instance has required fields: `id`, `name`, `status`, `availability_zone`, `flavor_id`, `charging_mode`
- Filters applied correctly (e.g., `--az` filter returns only instances in that AZ)

### 1.2 Validation Output

Verify `validate_targets.py` output:
- `all_compatible` is `true` (or review warnings if `false`)
- Each instance result has `checks`, `warnings`, and `errors` arrays
- `az_risk_check` is present (null if fewer than 2 instances)

**Key validation points**:
- All target instances have status `ACTIVE`
- No spot/bidding instances in targets (or warnings acknowledged)
- AS group associations identified (or AS check skipped)
- Single-AZ risk flagged if all targets in same AZ

### 1.3 Experiment Configuration Files

#### experiment.json
- `schema_version` is `"1.0"`
- `region` matches the `--cli-region` parameter
- `targets.instance_ids` contains all specified target IDs
- `targets.count` matches the length of `instance_ids`
- `actions.shutdown.duration_seconds` matches the `--duration` parameter
- `safety.require_confirmation` is `true`

#### rollback_experiment.sh
- Generated and is executable
- Contains correct `hcloud ECS BatchStartServers` command with all target IDs

```bash
# Validate experiment.json structure
EXPERIMENT_JSON=./experiments/{dir}/experiment.json python3 -c "
import json, os
with open(os.environ['EXPERIMENT_JSON']) as f:
    exp = json.load(f)
    assert exp['schema_version'] == '1.0'
    assert len(exp['targets']['instance_ids']) == exp['targets']['count']
    assert exp['safety']['require_confirmation'] == True
    print('experiment.json: VALID')
"

# Check all files exist
ls -la ./experiments/{dir}/
```

## Phase 2: Execute — Verification

### 2.1 Dry Run Validation

Before actual execution, run with `--dry-run`:

```bash
python3 scripts/execute_experiment.py \
    --experiment-dir ./experiments/xxx/ \
    --cli-region cn-north-4 --dry-run
```

Verify:
- All 6 phases are executed (pre_check → shutdown → monitor → wait → rollback → verify)
- Each phase shows `[DRY RUN]` prefix
- `execution-log.json` is generated with `dry_run: true`
- No actual API calls were made

### 2.2 Execution Log (execution-log.json)

```bash
python3 -c "
import json
with open('./experiments/xxx/execution-log.json') as f:
    log = json.load(f)
    assert log['overall_result'] in ('success', 'dry_run_complete', 'failed_pre_check',
        'failed_shutdown', 'failed_shutdown_auto_rollback', 'failed_rollback', 'failed_verify')
    phases = log.get('phases', {})
    for p in ['pre_check', 'shutdown', 'monitor', 'wait', 'rollback', 'verify']:
        assert p in phases, f'missing phase: {p}'
    print(f'Overall result: {log[\"overall_result\"]}')
    print(f'Timeline events: {len(log.get(\"instance_timeline\", []))}')
"
```

**Key validation points**:
- `overall_result` is `success` (all instances stopped and recovered)
- Each phase has `started_at`, `completed_at`, and `result` fields
- `instance_timeline` contains state transition records with timestamps

### 2.3 Instance State Transitions

| Phase | Expected Transitions |
|---|---|
| Shutdown | ACTIVE → STOPPING → SHUTOFF |
| Rollback | SHUTOFF → STARTING → ACTIVE |

### 2.4 Execution Report

Check `execution-report.md`:
- Experiment overview table is complete (name, region, instance count, timestamps)
- Phase timeline table lists all 6 phases with start/end times and results
- Instance state change table has entries for each transition
- Conclusions section matches the `overall_result`

## Phase 3: Analyze — Verification

### 3.1 Experiment Context Loading

Verify `analyze_logs.py` correctly loads experiment context:
- **Post-hoc mode**: `execution-log.json` found, mode = "post-hoc"
- **Real-time mode**: `experiment.json` found, mode = "real-time"
- Experiment name, region, time window, and instance IDs are populated

### 3.2 Log Collection

Verify log collection results:
- LTS logs: `success` is `true`, `count` > 0 (or confirm empty time window if 0)
- Log entries have `timestamp`, `level`, `message`, `source` fields
- Time window covers experiment start to end + 3 minutes buffer

### 3.3 CES Metrics Collection

Verify CES metrics results:
- All 6 metrics have `success: true` and `datapoints` with data
- SYS.ECS metrics use `period=300` (5-min aggregation)
- Phase summary has `pre_shutdown`, `during_shutdown`, `post_recovery` segments

### 3.4 Error Pattern Analysis

Verify:
- `total_errors` is consistent with `by_pattern` counts
- `by_severity` counts sum to `total_errors`
- Error events have valid `pattern`, `label`, `severity`, `message` fields

### 3.5 Analysis Report

Check `log-analysis-report.md`:
- Report contains all sections: Experiment Overview, Affected Instances, LTS Log Sources, Instance State Timeline, CES Metrics, Error Pattern Statistics, Error Event Timeline, Application Behavior Assessment, Improvement Suggestions
- Tables are properly formatted (Markdown)
- Assessment text is consistent with error counts

```bash
# Validate analysis result JSON structure
python3 -c "
import json
with open('./experiments/xxx/log-analysis-result.json') as f:
    r = json.load(f)
    assert r['mode'] in ('post-hoc', 'real-time')
    assert len(r['affected_instances']) > 0
    assert 'log_analysis' in r
    la = r['log_analysis']
    assert la['total_errors'] == sum(la['by_severity'].values())
    print('log-analysis-result.json: VALID')
"
```
