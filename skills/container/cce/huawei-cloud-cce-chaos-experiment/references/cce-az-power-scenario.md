# CCE AZ Power Outage Scenario

## Overview

The AZ power outage scenario simulates an entire Availability Zone losing power by
shutting down all CCE (Cloud Container Engine) nodes in the specified AZ. This tests
the cluster's ability to maintain service availability through cross-AZ pod rescheduling.

## Scenario Definition

| Item | Value |
|---|---|
| Scenario Type | `cce-az-power-outage` |
| Category | `az-power` |
| Fault Level | Node (CCE) |
| Huawei API | `ECS.BatchStopServers` / `ECS.BatchStartServers` |
| COC Attack Scenario | 资源运维-关机 |

## Fault Impact Chain

```
AZ Power Outage (simulated)
    ↓
CCE Nodes in AZ shut down (ACTIVE → SHUTOFF)
    ↓
Kubernetes marks nodes NotReady
    ↓
Pods on affected nodes are evicted (Running → Terminating)
    ↓
Pods rescheduled to nodes in other AZs (Pending → Running)
    ↓
Services remain available if cross-AZ replicas exist
```

### Timeline of Events

| Time | Event | Duration |
|---|---|---|
| T+0 | BatchStopServers API called | — |
| T+10~60s | Nodes become NotReady | 10-60s |
| T+30~120s | Pods enter Terminating state | 20-60s after node NotReady |
| T+60~180s | Pods rescheduled to other AZ (Pending) | 30-120s after eviction |
| T+120~300s | Pods Running on new nodes | 60-180s after rescheduling |
| T+duration | BatchStartServers API called | — |
| T+duration+30~120s | Nodes become Ready again | 30-120s |
| T+duration+60~180s | Pods may rebalance back | Optional |

## API Mapping

### Discovery APIs

| Operation | Command | Purpose |
|---|---|---|
| List CCE clusters | `hcloud CCE ListClusters` | Find target cluster |
| Get cluster credential | `hcloud CCE ShowCluster` | Obtain kubeconfig |
| List nodes | `kubectl get nodes -o json` | Discover nodes and AZ labels |
| List pods on node | `kubectl get pods --field-selector spec.nodeName=<node>` | Find affected pods |
| List workloads | `kubectl get deploy,sts --all-namespaces` | Check replica counts |
| List PDBs | `kubectl get pdb --all-namespaces` | Check eviction constraints |

### Execution APIs

| Operation | Command | Purpose |
|---|---|---|
| Shutdown nodes | `hcloud ECS BatchStopServers` | Fault injection |
| Start nodes | `hcloud ECS BatchStartServers` | Rollback |
| Monitor nodes | `kubectl get nodes -o json` | Track Ready/NotReady |
| Monitor pods | `kubectl get pods -A -o json` | Track rescheduling |

## Parameters

### AZ Selection

| Parameter | Description | Example |
|---|---|---|
| `--az` | Target availability zone | `cn-north-4a` |
| `--region` | Huawei Cloud region | `cn-north-4` |

Available AZs in cn-north-4: `cn-north-4a`, `cn-north-4b`, `cn-north-4g`

### Shutdown Mode

| Mode | Description | Use Case |
|---|---|---|
| `SOFT` | Graceful shutdown — OS receives shutdown signal | Recommended for experiments |
| `HARD` | Force shutdown — equivalent to power-off | Simulate abrupt power loss |

### Duration

| Parameter | Default | Range | Description |
|---|---|---|---|
| `--duration` | 300s (5min) | 60-3600s | Time to keep nodes shut down |

Duration should be long enough to observe:
- Pod rescheduling completion (typically 2-5 minutes)
- Application recovery behavior
- Monitoring/alerting response

## Node AZ Label

CCE nodes are assigned AZ information via Kubernetes labels:

- `topology.kubernetes.io/zone` (preferred, Kubernetes standard)
- `failure-domain.beta.kubernetes.io/zone` (legacy, deprecated)

The discovery script checks both labels to determine node AZ membership.
