# CCE Validation Rules for AZ Power Outage Experiment

## Overview

Before generating experiment configuration, the target CCE nodes and cluster must pass
compatibility validation. This document defines the validation rules and their rationale.

## Validation Rules

### Rule 1: All Target Nodes Must Be Ready

**Check**: All CCE nodes in the target AZ must have `Ready=True` status.

**Rationale**: Shutting down a node that is already NotReady or in an error state produces
meaningless experiment results. The experiment must start from a known-good state.

**On Failure**: The experiment cannot proceed. Fix the node status first.

---

### Rule 2: Cross-AZ Capacity

**Check**: Other AZs must have sufficient allocatable resources (CPU, memory) to
reschedule all pods from the target AZ.

**Rationale**: If other AZs lack capacity, pods will remain in `Pending` state after
eviction, causing service degradation or outage. The experiment should demonstrate
successful rescheduling, not resource exhaustion.

**Calculation**:
```
target_az_cpu = sum(node.allocatable.cpu for node in target_az_nodes)
other_az_cpu = sum(node.allocatable.cpu for node in other_az_nodes if node.ready)
pass if other_az_cpu >= target_az_cpu
```

**On Failure**: The experiment cannot proceed safely. Add nodes to other AZs or reduce
workload density in the target AZ.

---

### Rule 3: PDB (PodDisruptionBudget) Constraints

**Check**: All PodDisruptionBudgets must allow sufficient disruptions to evict all pods
on target nodes.

**Rationale**: PDBs protect workloads from voluntary disruptions. If a PDB has
`disruptionsAllowed=0`, the eviction will be blocked, and the node shutdown may hang
or pods may not be evicted gracefully.

**Check Method**:
```bash
kubectl get pdb --all-namespaces -o json
```

For each PDB, verify `status.disruptionsAllowed > 0`.

**On Warning**: If any PDB has 0 allowed disruptions, a warning is issued. The experiment
may still proceed, but pod eviction may be partially blocked.

---

### Rule 4: Workload Replicas ≥ 2

**Check**: All workloads (Deployments, StatefulSets) should have at least 2 replicas.

**Rationale**: Single-replica workloads will experience complete downtime during the AZ
outage — the pod is evicted and cannot be rescheduled until the node is back. This defeats
the purpose of the experiment, which is to test high availability.

**On Warning**: Single-replica workloads are flagged as warnings. The experiment can proceed,
but the user should be aware that these workloads will experience downtime.

---

### Rule 5: Single-AZ Cluster Risk

**Check**: If the CCE cluster has nodes in only one AZ, flag as critical risk.

**Rationale**: If all nodes are in one AZ, shutting down that AZ will cause total cluster
outage. There is no cross-AZ redundancy to test — the experiment would simply be a
destructive test with no recovery until rollback.

**On Failure**: If the cluster is single-AZ, the experiment is blocked. The cluster must
span at least 2 AZs for a meaningful AZ power outage test.

---

## Validation Result Format

```json
{
  "az": "cn-north-4a",
  "target_node_count": 3,
  "all_compatible": true,
  "error_count": 0,
  "warning_count": 1,
  "checks": [
    {
      "rule": "node_ready",
      "passed": true,
      "message": "Node node-xxx is Ready"
    }
  ],
  "errors": [],
  "warnings": ["Some workloads have single replica — will experience downtime"],
  "recommendation": "Compatible with warnings. Review warnings before proceeding."
}
```

## Decision Matrix

| Errors | Warnings | Result |
|---|---|---|
| 0 | 0 | ✅ Compatible — proceed |
| 0 | >0 | ⚠️ Compatible with warnings — review before proceeding |
| >0 | any | ❌ Not compatible — fix errors first |
