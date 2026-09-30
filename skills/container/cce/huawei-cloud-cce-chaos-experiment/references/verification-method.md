# Verification Method — How to Verify Experiment Results

## Overview

After running each phase of the CCE AZ power outage experiment, verify that all outputs are correct and complete before proceeding to the next phase.

## Phase 1: Prepare — Verification

### 1.1 Discovery Output (discovery.json)

Verify `discover_cce.py` output:
- JSON is valid and parseable
- `cluster_count` matches the number of returned clusters
- Each cluster has required fields: `id`, `name`, `status`, `flavor`, `version`
- When `--include-pods` is used:
  - `target_nodes[].pods` array is populated for each node in the target AZ
  - `target_node_count` matches the number of nodes in the target AZ
  - Each pod has: `name`, `namespace`, `phase`, `node`, `workload_kind`, `workload_name`
  - `instance_id` field contains the real ECS server ID (not the CCE-internal node ID)

```bash
python3 -c "
import json
with open('discovery.json') as f:
    d = json.load(f)
    assert d['cluster_count'] == len(d['clusters'])
    for n in d.get('target_nodes', []):
        assert n.get('instance_id'), f'Node {n[\"name\"]} missing ECS instance_id'
        assert n.get('pods') is not None, f'Node {n[\"name\"]} missing pods array'
    print('discovery.json: VALID')
"
```

### 1.2 Validation Output (validation.json)

Verify `validate_targets.py` output:
- `all_compatible` is `true` (or review warnings)
- `error_count` is `0` (errors block proceeding; warnings are informational)
- Each check has `rule`, `passed`, and `message` fields

**Key validation points**:
- All target nodes have status `Ready`
- Cross-AZ capacity is sufficient (`other_az_cpu` >= `target_az_cpu`)
- PDB constraints are checked (warnings only for AZ outage — shutdown bypasses eviction API)
- Single-AZ cluster risk flagged if only one AZ exists

```bash
python3 -c "
import json
with open('validation.json') as f:
    v = json.load(f)
    assert v['error_count'] == 0, f'{v[\"error_count\"]} validation errors'
    assert v['all_compatible'] == True, 'Not all compatible'
    print(f'validation.json: VALID ({v[\"warning_count\"]} warnings)')
"
```

### 1.3 Experiment Configuration Files

#### experiment.json
- `region` matches the `--region` parameter
- `targets.nodes[]` contains all target node names with `instance_id` and `az`
- `actions.shutdown.duration_seconds` matches the `--duration` parameter
- `safety.require_confirmation` is `true`

#### rollback_experiment.sh
- Generated and is executable
- Contains correct `hcloud ECS BatchStartServers` command with all target ECS instance IDs

```bash
python3 -c "
import json
with open('./experiments/{dir}/experiment.json') as f:
    exp = json.load(f)
    assert exp['region'], 'missing region'
    assert len(exp['targets']['nodes']) > 0, 'no target nodes'
    for n in exp['targets']['nodes']:
        assert n['instance_id'], f'node {n[\"name\"]} missing instance_id'
    print('experiment.json: VALID')
"
```

## Phase 2: Execute — Verification

### 2.1 Dry Run Validation

Before actual execution, run with `--dry-run`:

```bash
python3 scripts/execute_experiment.py \
    --experiment-dir ./experiments/xxx/ --dry-run
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
    assert log['result'] in ('success', 'dry_run_complete', 'failed')
    assert 'phases' in log or 'timeline' in log
    print(f'Result: {log[\"result\"]}')
"
```

**Key validation points**:
- `result` is `success` (all nodes stopped and recovered)
- Timeline contains all 6 phases with timestamps
- Node state transitions recorded: Ready → NotReady → Ready
- Pod state transitions recorded: Running → Unknown → Pending (rescheduling attempts)

### 2.3 Node State Transitions

| Phase | Expected Transitions |
|---|---|
| Shutdown (BatchStop) | Node: Ready → NotReady (typically 30–60s) |
| Rollback (BatchStart) | Node: NotReady → Ready (typically 30–60s) |

### 2.4 Pod Rescheduling

During the experiment window, affected Pods should show:
- `Running` → `Unknown` (node becomes NotReady)
- `Unknown` → `Pending` (Kubernetes attempts rescheduling)
- `Pending` → `Running` (scheduled on surviving AZ nodes, or back on recovered node)

Pods may remain `Pending` if surviving AZ nodes lack sufficient resources — this is a valid finding, not a failure.

### 2.5 Execution Report

Check `execution-report.md`:
- Experiment overview table is complete (name, region, target AZ, node count, timestamps)
- Phase timeline table lists all 6 phases with start/end times and results
- Node status change table has entries for Ready→NotReady and NotReady→Ready
- Pod status change table records rescheduling attempts
- Conclusion section matches the `result` field

## Phase 3: Analyze — Verification

### 3.1 Experiment Context Loading

Verify `analyze_logs.py` correctly loads experiment context:
- **Post-hoc mode**: `execution-log.json` found, mode = "post-hoc"
- **Real-time mode**: `experiment.json` found, mode = "real-time"
- Experiment name, region, time window, and affected nodes are populated

### 3.2 Log Collection

Verify log collection results:
- Kubernetes Events: `count > 0` (filtered from total events in time window)
- Pod logs: collected for alive pods; deleted pods are skipped with `[SKIP]` message
- LTS logs: may show "No LTS log groups found" if LTS is not configured — this is informational, not an error

### 3.3 Error Pattern Analysis

Verify:
- `total_errors` is consistent with event counts
- FailedScheduling events are captured with their failure reasons (Insufficient CPU, Insufficient memory, untolerated taints)
- TaintManagerEviction events are captured (normal Kubernetes behavior)
- NodeNotReady / NodeReady events are captured

### 3.4 Analysis Report

Check `analysis-report.md`:
- Report contains all sections: Experiment Overview, Affected Resources, Pod Rescheduling Timeline, Node Status Changes, Error Pattern Statistics, Business Impact Assessment, Improvement Recommendations
- Tables are properly formatted (Markdown)
- Assessment text is consistent with error counts
- Improvement recommendations address findings (e.g., resource constraints, single-replica components)

```bash
python3 -c "
import json
with open('analysis-result.json') as f:
    r = json.load(f)
    assert r['mode'] in ('post-hoc', 'real-time')
    assert len(r['affected_pods']) > 0 or len(r.get('affected_nodes', [])) > 0
    print('analysis-result.json: VALID')
"
```
