# Node Management Task Details

## Overview

Cluster node lifecycle management, including creation, querying, cordon, uncordon, drain, and deletion operations.

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
| `ssh_key` or password | Login authentication (one required) | `KeyPair-dev` or `CCE_NODE_PASSWORD` environment variable |

### Login Authentication

Either `ssh_key` or password is required (mutually exclusive):
- `ssh_key`: SSH key pair name
- Password: passed via `CCE_NODE_PASSWORD` environment variable (8-26 characters, must contain at least three of: uppercase, lowercase, digits, special characters)

> **Important: The password is read from the `CCE_NODE_PASSWORD` environment variable, and the script automatically performs SHA-512 salted encryption + base64 encoding, no manual processing required.**

```bash
export CCE_NODE_PASSWORD="your_password"
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
| `node_id` | Node ID | Yes |
| `confirm` | Confirm dangerous operations | Required for dangerous operations |

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
| Query Node Status | Get scheduling status | 🟢 Low | No |
| cordon | Mark as unschedulable | 🟡 Medium | Yes |
| uncordon | Restore schedulable | 🟡 Medium | Yes |
| drain | Evict all Pods | 🟠 High | Yes |
| delete | Delete node | 🟠 High | Yes |

### Create Node (Turbo Cluster)

```bash
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

### Node Maintenance Process

```bash
# 1. Mark node as unschedulable
python3 huawei-cloud.py huawei_cce_node_cordon \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true

# 2. Evict Pods on the node
python3 huawei-cloud.py huawei_cce_node_drain \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true

# 3. Perform maintenance operations...

# 4. Restore node scheduling
python3 huawei-cloud.py huawei_cce_node_uncordon \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true
```