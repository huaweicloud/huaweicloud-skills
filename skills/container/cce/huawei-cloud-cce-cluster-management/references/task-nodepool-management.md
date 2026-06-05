# Node Pool Management Task Details

## Overview

Node pool lifecycle management, including creating node pools, querying node pool lists, and adjusting node counts.

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
| `ssh_key` or `password` | Login authentication (one required) | `KeyPair-dev` or `MyPass123!` |

### Login Authentication

One of `ssh_key` and `password` is required; they are mutually exclusive:
- `ssh_key`: SSH key pair name
- `password`: Node login password (8-26 characters, must contain at least three of: uppercase, lowercase, digits, special characters)

> **Important: The script automatically performs SHA-512 salted encryption + base64 encoding on the password. No manual processing is needed. However, if calling the CCE API directly, you must encrypt it yourself.**

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
| `nodepool_id` | Node pool ID | Yes |
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