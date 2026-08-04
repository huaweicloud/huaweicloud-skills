# Node Pool Management Task Details

## Overview

Node pool lifecycle management, including creating node pools, querying node pool lists, and adjusting node counts.

> **Note:** `huawei_create_cce_nodepool` uses the Python SDK fallback due to a known hcloud `CreateNodePool` metadata parsing defect. See [cce-api-guide.md](cce-api-guide.md#hcloud-defect-createcluster--createnodepool-sdk-fallback).

## Create Node Pool Parameters

### Required Parameters

| Parameter | Description | Example Value |
|------|------|-------|
| `region` | Huawei Cloud region | `cn-north-4` |
| `cluster_id` | Cluster ID | `xxx` |
| `nodepool_name` | Node pool name | `dev-worker-pool` |
| `flavor` | Node specification | `c7.large.2` |
| `availability_zone` | Availability zone | `cn-north-4a` |
| `root_volume_size` | System disk size (GB) | `40` |
| `root_volume_type` | System disk type | `GPSSD` |
| `initial_node_count` | Initial node count | `1` |

### Login Authentication — Three-Level Priority

The node login credential is resolved with the following priority:

1. **`ssh_key` parameter** — SSH key pair name (preferred when available). Mutually exclusive with password.
2. **`password` parameter** — raw node login password (8–26 chars, ≥3 of: uppercase / lowercase / digits / special).
3. **`CCE_NODE_PASSWORD` environment variable** — used when neither `ssh_key` nor `password` is provided.
4. **Auto-generated random password** — when none of the above is supplied.

> ⚠️ **The auto-generated password is NEVER returned in the tool response.** To access the nodes afterwards, reset the password via the CCE console or the ECS API. The success message only contains a hint to reset the password.

The script automatically performs SHA-512 salted encryption + base64 encoding on the password — no manual processing required.

### Data Volumes (data_volumes)

Some node specifications (non-local disk types) **must configure data volumes**, otherwise creation will fail with the error:
`Data volume needed for non-local-disk flavor or non-system diskType`

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor Compatibility

Node pools in Turbo (ENI network) clusters must use ENI-compatible flavors. Incompatible flavors will result in the error:
`Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

| Flavor Series | ENI Support | Recommended Scenario |
|-------------|---------|---------|
| `c7` series (e.g., `c7.large.2`) | ✅ Supported | Recommended for Turbo clusters |
| `s7` series | ✅ Supported | Turbo clusters |
| `s6` series (e.g., `s6.large.2`) | ❌ Not supported | Standard clusters only |
| `c6` series (e.g., `c6.large.2`) | ❌ Not supported | Standard clusters only |

### Optional Parameters

| Parameter | Description | Default Value |
|------|------|-------|
| `os_type` | Operating system | `EulerOS` |
| `subnet_id` | Subnet ID | Uses cluster subnet |
| `autoscaling_enabled` | Enable auto-scaling | `false` |
| `min_node_count` | Minimum node count | 0 |
| `max_node_count` | Maximum node count | 0 |

## Scaling Parameters

| Parameter | Description | Required |
|------|------|-----|
| `region` | Huawei Cloud region | Yes |
| `cluster_id` | Cluster ID | Yes |
| `nodepool_id` | Node pool ID **or name** (resolved to UID automatically) | Yes |
| `node_count` | Target node count | Yes |
| `confirm` | Confirm execution | Yes |

## Node Pool States

| State | Description |
|------|------|
| Active | Running normally |
| Scaling | Scaling in progress |
| Deleting | Being deleted |
| Error | Abnormal state |

## Operation Instructions

### Create Node Pool (Standard Cluster)

```bash
python3 huawei-cloud.py huawei_create_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_name=dev-worker-pool \
  flavor=s6.large.2 \
  availability_zone=cn-north-4a \
  root_volume_size=40 \
  root_volume_type=GPSSD \
  initial_node_count=2 \
  ssh_key=KeyPair-dev
```

### Create Node Pool (Turbo Cluster)

```bash
# Option A: ssh_key (preferred)
python3 huawei-cloud.py huawei_create_cce_nodepool \
    region=cn-north-4 \
    cluster_id=xxx \
    nodepool_name=dev-worker-pool \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    initial_node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]' \
    ssh_key=KeyPair-dev

# Option B: password env var
export CCE_NODE_PASSWORD="your_password"
python3 huawei-cloud.py huawei_create_cce_nodepool \
    region=cn-north-4 \
    cluster_id=xxx \
    nodepool_name=dev-worker-pool \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    initial_node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]'

# Option C: omit both — the skill auto-generates a strong password
#           (the response will tell you to reset it to access nodes)
```

### Query Node Pools

```bash
python3 huawei-cloud.py huawei_list_cce_nodepools \
  region=cn-north-4 \
  cluster_id=xxx
```

### Scale Up Node Pool

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=10 \
  confirm=true
```

### Scale Down Node Pool

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=3 \
  confirm=true
```
