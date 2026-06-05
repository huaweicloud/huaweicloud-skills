# Cluster Management Task Details

## Overview

CCE cluster lifecycle management operations, including creation, deletion, hibernation, awakening, and EIP binding.

## Key Parameters

| Parameter | Description | Required |
|------|------|-----|
| `region` | Huawei Cloud region | Yes |
| `cluster_id` | Cluster ID | Yes (except for creation) |
| `cluster_name` | Cluster name | Required for creation |
| `cluster_version` | K8s version | Required for creation |
| `flavor_id` | Cluster specification | Required for creation |
| `vpc_id` | VPC ID | Required for creation |
| `subnet_id` | Subnet ID | Required for creation |
| `cluster_type` | Cluster type | Optional for creation |
| `container_network_type` | Container network type | Optional for creation |
| `eip_id` | EIP ID | Required for binding/unbinding |
| `confirm` | Confirm executing dangerous operations | Required for dangerous operations |

## Operation Classification

| Operation | Risk Level | Requires Confirmation |
|------|---------|-------|
| Create cluster | 🟢 Low | No |
| Delete cluster | 🔴 Extremely High | Yes |
| Hibernate cluster | 🟠 High | Yes |
| Awaken cluster | 🟠 High | Yes |
| Bind EIP | 🟢 Low | No |
| Unbind EIP | 🟡 Medium | No |

## Example

### Create a Standard Cluster

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=my-cluster \
  cluster_version=v1.28 \
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

### Create a Turbo Cluster

Turbo clusters use ENI container networking, suitable for high-performance scenarios. When creating, set `cluster_type=VirtualMachine` and `container_network_type=eni`; the API will automatically set `spec.category` to `Turbo`.

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=dev-turbo-cluster \
  cluster_version=v1.28 \
  cluster_type=VirtualMachine \
  container_network_type=eni \
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

> **Note: Turbo cluster node pools must use ENI-compatible flavors (e.g., `c7.large.2`), and typically require configuring data volumes.**

### Delete a Cluster (Requires Double Confirmation)

```bash
# Preview deletion
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx

# Confirm deletion
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```

### Hibernate a Cluster

```bash
python3 huawei-cloud.py huawei_hibernate_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```

### Awaken a Cluster

```bash
python3 huawei-cloud.py huawei_awake_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```