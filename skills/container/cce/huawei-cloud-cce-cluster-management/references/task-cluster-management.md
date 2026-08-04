# Cluster Management Task Details

## Overview

CCE cluster lifecycle management operations, including creation, deletion, hibernation, awakening, and EIP binding.

## Key Parameters

| Parameter | Description | Required |
|------|------|-----|
| `region` | Huawei Cloud region | Yes |
| `cluster_id` | Cluster ID | Yes (except for creation) |
| `cluster_name` | Cluster name | Required for creation |
| `cluster_version` | K8s version | Optional — **omit for latest**; specify only when a specific version is required |
| `flavor_id` | Cluster specification | Required for creation |
| `vpc_id` | VPC ID | Required for creation |
| `subnet_id` | Subnet ID | Required for creation |
| `cluster_type` | Cluster type | Optional for creation |
| `container_network_type` | Container network type | Optional — default `eni` (Turbo) |
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
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

> `cluster_version` is omitted so the API picks the latest supported Kubernetes version. `container_network_type` defaults to `eni` (Turbo).

### Create a Turbo Cluster

Turbo clusters use ENI container networking, suitable for high-performance scenarios. `container_network_type=eni` is the default; the API will automatically set `spec.category` to `Turbo`.

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=dev-turbo-cluster \
  cluster_type=VirtualMachine \
  container_network_type=eni \
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

> **Note: Turbo cluster node pools must use ENI-compatible flavors (e.g., `c7.large.2`), and typically require configuring data volumes.**

> **Note:** `huawei_create_cce_cluster` uses the Python SDK fallback due to a known hcloud `CreateCluster` metadata parsing defect. See [cce-api-guide.md](cce-api-guide.md#hcloud-defect-createcluster--createnodepool-sdk-fallback).

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
