# CCE AZ Power Outage Experiment — Execution Workflow

## 6-Phase Workflow Details

### Phase 1: Pre-check
- **Input**: experiment.json
- **Action**: Load experiment config, confirm all target nodes are currently Ready via kubectl
- **Output**: Pre-check result (pass/fail + reason)
- **Error handling**: If any node is not Ready, abort experiment and prompt user to check cluster status

### Phase 2: Shutdown
- **Input**: Target node ECS ID list, shutdown mode (SOFT/HARD)
- **Action**: Call hcloud ECS BatchStopServers for batch shutdown
- **Output**: Shutdown request result
- **Error handling**: If shutdown request fails, auto-rollback (start all nodes) or prompt user for manual intervention

### Phase 3: Monitor
- **Input**: Target node list, monitoring timeout
- **Action**: Poll `kubectl get nodes` and `kubectl get pods -A`, record Node state changes (Ready→NotReady) and Pod state changes (Running→Terminating→Pending→Running)
- **Output**: node_timeline, pod_timeline, rescheduling_events
- **Error handling**: If NotReady nodes still detected after timeout, log warning but continue experiment

### Phase 4: Wait
- **Input**: Experiment duration (duration)
- **Action**: sleep(duration)
- **Output**: None
- **Error handling**: On interrupt signal (Ctrl+C), immediately enter rollback phase

### Phase 5: Rollback
- **Input**: Target node ECS ID list
- **Action**: Call hcloud ECS BatchStartServers for batch startup
- **Output**: Startup request result
- **Error handling**: If startup request fails, log error and prompt user to manually start nodes

### Phase 6: Verify
- **Input**: Target node list, expected Pod replica count
- **Action**: Confirm all nodes recovered to Ready, all Pods recovered to Running, replica count met
- **Output**: Verification result (pass/fail + details)
- **Error handling**: If verification fails, log failure details and suggest user inspect the cluster

### Phase 7: Log Analysis Recommendation

> **This phase is automatically triggered after experiment execution completes. No actual API calls are involved.**

- **Input**: Experiment directory path, execution-log.json
- **Action**:
  1. `execute_experiment.py` automatically prints a log analysis recommendation prompt after experiment completion
  2. `generate_report.py` includes a "Log Analysis Recommendation" section at the end of the generated Markdown report
  3. Recommends the user proceed with Phase 3 (log analysis) using the same skill's analysis scripts
- **Output**: Console recommendation prompt + log analysis recommendation section in report
- **Recommendation content**:
  - Pod rescheduling timeline and impact assessment
  - Error pattern detection in application logs (ERROR/Exception/timeout/5xx)
  - Business impact assessment and RTO analysis
  - Improvement recommendations (PDB config, replica distribution, etc.)
- **Next phase**: Phase 3 — Log Analysis (analyze_logs.py + generate_analysis_report.py)

## execution-log.json Format Definition

```json
{
  "experiment_name": "cce-az-power-outage",
  "start_time": "2026-01-01T10:00:00Z",
  "end_time": "2026-01-01T10:05:30Z",
  "duration_seconds": 300,
  "status": "completed",
  "az": "cn-north-4a",
  "cluster": "cce-cluster-xxx",
  "node_timeline": [
    {
      "node": "node-xxx",
      "timestamp": "2026-01-01T10:00:05Z",
      "old_status": "Ready",
      "new_status": "NotReady"
    }
  ],
  "pod_timeline": [
    {
      "pod": "app-pod-xxx",
      "namespace": "default",
      "timestamp": "2026-01-01T10:00:10Z",
      "old_status": "Running",
      "new_status": "Terminating"
    },
    {
      "pod": "app-pod-xxx",
      "namespace": "default",
      "timestamp": "2026-01-01T10:00:15Z",
      "old_status": "Pending",
      "new_status": "Running",
      "new_node": "node-yyy"
    }
  ],
  "rescheduling_events": [
    {
      "pod": "app-pod-xxx",
      "namespace": "default",
      "old_node": "node-xxx",
      "new_node": "node-yyy",
      "reschedule_time": "2026-01-01T10:00:15Z"
    }
  ],
  "verification": {
    "nodes_ready": true,
    "pods_running": true,
    "replicas_met": true
  }
}
```

## Safety Mechanisms

- **dry-run**: Simulate execution flow only, no actual shutdown/startup
- **auto-rollback**: Automatically start all nodes if shutdown fails
- **Standalone rollback script**: rollback_experiment.py can run independently for emergency recovery
- **Full logging**: execution-log.json records complete timeline for post-hoc analysis

## Complete Workflow Chain

```
Phase 1: Prepare
    ↓ generates experiment.json
Phase 2: Execute
    ↓ generates execution-log.json + execution-report.md
    ↓ auto-recommends log analysis
Phase 3: Log Analysis
    → generates comprehensive-analysis-report.md
```
