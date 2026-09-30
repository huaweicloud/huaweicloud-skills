# CCE Resource Monitoring Guide

## Node State Machine

```
Ready ──shutdown──→ NotReady ──startup──→ Ready
```

- **Ready**: Node is healthy and can schedule Pods
- **NotReady**: Node is unavailable, Pods are evicted/rescheduled
- **Unknown**: Node is unreachable (kubelet cannot communicate)

### Polling Mechanism
- Interval: 5 seconds
- Timeout: 120 seconds (waiting for Node to transition to NotReady)
- Command: `kubectl get nodes -o json`

## Pod State Machine

```
Running ──Node NotReady──→ Terminating ──eviction complete──→ Pending ──scheduled to new Node──→ Running
```

- **Running**: Pod is running normally
- **Terminating**: Pod is being evicted/terminated
- **Pending**: Pod is waiting to be scheduled to a new node
- **Running (new node)**: Pod has restarted on a node in another AZ

### Polling Mechanism
- Interval: 5 seconds
- Timeout: 300 seconds (waiting for Pod to complete rescheduling)
- Command: `kubectl get pods -A -o json`

## Pod Rescheduling Monitoring

### Key Observations
1. Pod is evicted from the original AZ node (NotReady)
2. Pod enters Pending state waiting for scheduling
3. Pod restarts as Running on a node in another AZ
4. Calculate rescheduling duration (time difference from Terminating to Running)

### Detection Logic
- Record Pod nodeName changes
- Compare the AZ of the original node and the new node (via node label `topology.kubernetes.io/zone`)
- Generate rescheduling_events records

## CES Alarm Stop Conditions

- All target nodes recovered to Ready
- All Pods recovered to Running
- Workload replica count reaches expected value
- Or maximum monitoring timeout reached (600 seconds)

## Monitoring Data Collection

### Node Status
```bash
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, status: .status.conditions[] | select(.type=="Ready") | .status, zone: .metadata.labels["topology.kubernetes.io/zone"]}'
```

### Pod Status
```bash
kubectl get pods -A -o json | jq '.items[] | {name: .metadata.name, namespace: .metadata.namespace, phase: .status.phase, node: .spec.nodeName}'
```

### Workload Replica Count
```bash
kubectl get deployments -A -o json | jq '.items[] | {name: .metadata.name, namespace: .metadata.namespace, replicas: .status.readyReplicas, desired: .spec.replicas}'
```
