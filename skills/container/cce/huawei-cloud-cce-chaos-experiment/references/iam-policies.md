# IAM Policies — Required Permissions

## Overview

This skill covers the full CCE AZ power outage experiment lifecycle (prepare → execute → analyze). Each phase requires different permissions: Phase 1 needs CCE/ECS read; Phase 2 adds ECS write (stop/start); Phase 3 adds LTS read and Kubernetes API access.

## Permissions by Phase

### Phase 1: Prepare — CCE Read + ECS Read

| API | Action | Purpose |
|---|---|---|
| `CCE.ShowCluster` | `cce:cluster:get` | Query CCE cluster details (status, version, flavor) |
| `CCE.CreateKubernetesClusterCert` | `cce:cluster:create` | Obtain kubeconfig for kubectl access |
| `ECS.ListServersDetails` | `ecs:servers:list` | Query ECS instances to map private IP → ECS instance ID |

### Phase 2: Execute — ECS Read + Write

| API | Action | Purpose |
|---|---|---|
| `ECS.ListServersDetails` | `ecs:servers:list` | Query instance status (pre-check, monitoring, verification) |
| `ECS.BatchStopServers` | `ecs:servers:stop` | Execute shutdown fault injection on target AZ nodes |
| `ECS.BatchStartServers` | `ecs:servers:start` | Rollback / recovery after experiment |

> Kubernetes API access (via kubeconfig from `CreateKubernetesClusterCert`) is also required for:
> - `kubectl get nodes` — pre-check and monitoring
> - `kubectl get pods` — Pod status tracking
> - `kubectl get events` — Kubernetes event collection

### Phase 3: Analyze — ECS Read + LTS Read

| API | Action | Purpose |
|---|---|---|
| `ECS.ListServersDetails` | `ecs:servers:list` | Query target ECS instance details |
| `LTS.ListLogGroups` | LTS read | List LTS log groups for CCE cluster log collection |
| `LTS.ListLogStream` | LTS read | List log streams within a group |
| `LTS.ListLogs` | `lts:logs:search` | Query application logs within experiment time window |

> Kubernetes API access is also required for:
> - `kubectl logs` — Pod log collection
> - `kubectl get events` — Kubernetes event analysis

## Sample IAM Policy (JSON — Full Lifecycle)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cce:cluster:get",
                "cce:cluster:create"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:servers:list",
                "ecs:servers:stop",
                "ecs:servers:start"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lts:logs:search"
            ],
            "Resource": "*"
        }
    ]
}
```

## Permission Scope Recommendations

| Scope | Permissions | Use Case |
|---|---|---|
| **Prepare only** | `cce:cluster:get`, `cce:cluster:create`, `ecs:servers:list` | Discovery + validation, no execution |
| **Full experiment** (prepare + execute) | Add `ecs:servers:stop`, `ecs:servers:start` | Full shutdown + rollback cycle |
| **Full lifecycle** (all phases) | Add `lts:logs:search` | Includes log analysis |

## CCE Cluster RBAC

In addition to IAM policies, the Kubernetes cluster has its own RBAC. The kubeconfig obtained via `CreateKubernetesClusterCert` grants cluster-admin privileges by default, which is sufficient for:

- Reading nodes, pods, services, configmaps, events
- Executing `kubectl logs`

For production environments with restricted RBAC, ensure the kubeconfig user has at minimum:
- `get`, `list`, `watch` on `nodes`, `pods`, `events`, `services`, `configmaps`
- `get`, `list` on `pod/logs`

## Notes

- AK/SK credentials should be passed via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`), never hardcoded in scripts.
- The kubeconfig file (`/root/.kube/config`) contains a short-lived token (default 30 days). Re-run `CreateKubernetesClusterCert` if expired.
- Phase 3 (Analyze) is **read-only** — it queries resources and collects logs but does not modify any cloud resources.
- Deployment is local mode: `deploy_experiment.sh` generates the emergency rollback script locally; no COC dependency.
