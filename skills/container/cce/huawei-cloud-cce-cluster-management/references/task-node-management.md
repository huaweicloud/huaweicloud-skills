# Node Management Task Details

## Overview

Cluster node lifecycle management, including creation, querying, cordon, uncordon, drain, and deletion operations. Node scheduling operations (`cordon`, `uncordon`, `drain`, `status`) run via **kubectl cce** plugin (no cluster EIP or manual kubeconfig needed).

## Create Node Parameters

### Required Parameters

| Parameter | Description | Example Value |
|------|------|-------|
| `region` | Huawei Cloud region | `cn-north-4` |
| `cluster_id` | Cluster ID | `xxx` |
| `flavor` | Node specification | `c7.large.2` |
| `availability_zone` | Availability zone | `cn-north-4a` |
| `root_volume_size` | System disk size (GB) | `40` |
| `root_volume_type` | System disk type | `GPSSD` |

### Login Authentication — Three-Level Priority

The node login credential is resolved with the following priority:

1. **`ssh_key` parameter** — SSH key pair name (preferred when available).
2. **`password` parameter** — raw node login password (8–26 chars, ≥3 of: uppercase / lowercase / digits / special).
3. **`CCE_NODE_PASSWORD` environment variable** — used when neither `ssh_key` nor `password` is provided.
4. **Auto-generated random password** — when none of the above is supplied.

> ⚠️ **The auto-generated password is NEVER returned in the tool response.** To access the node afterwards, reset the password via the CCE console or the ECS API. The success message only contains a hint to reset the password.

The script automatically performs SHA-512 salted encryption + base64 encoding on the password — no manual processing required.

```bash
# Option A: ssh_key (preferred)
export ... ssh_key=KeyPair-dev   # as a parameter

# Option B: password env var
export CCE_NODE_PASSWORD="your_password"

# Option C: omit both — the skill auto-generates a strong password
#           (the response will tell you to reset it to access the node)
```

### Data Volumes (data_volumes)

Some node specifications (non-local disk types) **must configure data volumes**:

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor Compatibility

Nodes in Turbo (ENI network) clusters must use flavors that support ENI (such as the `c7` series); `s6`, `c6`, etc. do not support ENI.

### Optional Parameters

| Parameter | Description | Default Value |
|------|------|-------|
| `node_count` | Number of nodes to create | `1` |
| `os_type` | Operating system | `EulerOS` |
| `subnet_id` | Subnet ID | Uses cluster subnet |

## Scheduling Management Parameters

| Parameter | Description | Required |
|------|------|-----|
| `region` | Huawei Cloud region | Yes |
| `cluster_id` | Cluster ID | Yes |
| `node_name` | Node name (k8s node name) | Yes |
| `confirm` | Confirm dangerous operations | Required for cordon/uncordon/drain |

> kubectl operations identify nodes by their **k8s node name** (`node_name`), not the CCE node UID. Use `huawei_list_cce_nodes` to find the node name.
>
> **Important:** The k8s node name is typically in **IP format** (e.g., `192.168.3.15`), not the CCE node display name. Always use `huawei_list_cce_nodes` to retrieve the actual k8s node name before calling cordon/uncordon/drain/status.

## Node Scheduling Status

| Status | Description |
|------|------|
| Schedulable | Schedulable, new Pods can be assigned to this node |
| Unschedulable | Unschedulable, new Pods will not be assigned to this node |

## Operation Description

| Operation | Function | Risk Level | Requires Confirmation |
|------|------|---------|-------|
| Create Node | Add node | 🟢 Low | No |
| Query Node List | Get all nodes | 🟢 Low | No |
| Query Node Status | Get scheduling status (via `kubectl get node`) | 🟢 Low | No |
| cordon | Mark as unschedulable (via `kubectl cordon`) | 🟡 Medium | Yes |
| uncordon | Restore schedulable (via `kubectl uncordon`) | 🟡 Medium | Yes |
| drain | Cordon + evict all Pods respecting PDB (via `kubectl drain`) | 🟠 High | Yes |
| delete | Delete node | 🟠 High | Yes |

### Create Node (Turbo Cluster)

```bash
# Option A: ssh_key
python3 huawei-cloud.py huawei_create_cce_node \
    region=cn-north-4 \
    cluster_id=xxx \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]' \
    ssh_key=KeyPair-dev

# Option B: password env var
export CCE_NODE_PASSWORD="your_password"
python3 huawei-cloud.py huawei_create_cce_node \
    region=cn-north-4 \
    cluster_id=xxx \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]'
```

### Node Maintenance Process (kubectl drain semantics)

`huawei_cce_node_drain` follows standard **kubectl drain** semantics: it first **cordons** the node (so no new pods are scheduled), then **evicts** all resident pods while respecting `PodDisruptionBudget` (PDB). The underlying command is:

```
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --grace-period=30 --timeout=120s
```

DaemonSet pods and emptyDir data are evicted automatically; PDB-governed workloads may block the drain until evictable.

```bash
# 1. Mark node as unschedulable (kubectl cordon)
python3 huawei-cloud.py huawei_cce_node_cordon \
  region=cn-north-4 cluster_id=xxx node_name=<node-name> confirm=true

# 2. Cordon + evict all pods respecting PDB (kubectl drain)
python3 huawei-cloud.py huawei_cce_node_drain \
  region=cn-north-4 cluster_id=xxx node_name=<node-name> confirm=true

# 3. Perform maintenance operations...

# 4. Restore node scheduling (kubectl uncordon)
python3 huawei-cloud.py huawei_cce_node_uncordon \
  region=cn-north-4 cluster_id=xxx node_name=<node-name> confirm=true
```

> Note: `drain` already cordons the node, so steps 1 and 2 are alternatives depending on whether you want to evict pods. To preview the pods that would be affected by a drain, call `huawei_cce_node_drain` without `confirm=true` — the response includes an `affected_pods` list.
