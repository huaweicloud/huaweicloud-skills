---
name: huawei-cloud-cce-cluster-management
description: |
  Huawei Cloud CCE (Cloud Container Engine) cluster lifecycle management skill using Python SDK v3.
  Use this skill when the user wants to: (1) create, delete, hibernate, or awake CCE clusters, (2) list clusters and query cluster/node/nodepool/addon information, (3) manage node pools (create, delete, resize), (4) manage nodes (create, delete, cordon, uncordon, drain), (5) manage addons (install, uninstall, update), (6) bind/unbind cluster EIP for public access, (7) get cluster kubeconfig.
  Trigger: user mentions "CCE cluster", "create cluster", "delete cluster", "node pool", "node management", "hibernate cluster", "awake cluster", "addon", "kubeconfig", "EIP binding", "CCE 集群", "创建集群", "删除集群", "节点池", "节点管理", "休眠集群", "唤醒集群", "插件", "kubeconfig", "EIP 绑定"
tags: [cce, kubernetes, cluster-management, nodepool, addon]
version: 1.0.0
---

# Huawei Cloud CCE Cluster Management

## Overview

Manage CCE (Cloud Container Engine) cluster lifecycle, including cluster creation/deletion/hibernation/awakening, node pool management, node scheduling control, and addon management.

## ⛔ Security Constraints

### Dangerous Operation Confirmation Mechanism

> **This skill strictly enforces a two-step confirmation mechanism for all dangerous operations to prevent accidental service disruption or data loss.**

All dangerous operations require `confirm=true` parameter to execute. Otherwise, they return a preview and confirmation prompt.

#### Operations Requiring Confirmation

| Tool | Operation Type | Risk Level | Description |
|------|---------------|------------|-------------|
| `huawei_delete_cce_cluster` | Delete | 🔴 Critical | Deletes entire CCE cluster, irreversible |
| `huawei_hibernate_cce_cluster` | Hibernate | 🟠 High | Stops all workloads, pauses control plane billing |
| `huawei_awake_cce_cluster` | Awake | 🟠 High | Resumes cluster from hibernation |
| `huawei_resize_cce_nodepool` | Scale | 🟡 Medium | Adjusts node pool size, affects capacity |
| `huawei_delete_cce_nodepool` | Delete | 🟠 High | Deletes node pool, affects business capacity |
| `huawei_delete_cce_node` | Delete | 🟠 High | Removes node from cluster, affects scheduling |
| `huawei_uninstall_cce_addon` | Uninstall | 🟠 High | Removes addon, may affect cluster functionality |
| `huawei_cce_node_cordon` | Cordon | 🟡 Medium | Marks node unschedulable, new pods won't be assigned |
| `huawei_cce_node_uncordon` | Uncordon | 🟡 Medium | Marks node schedulable, new pods may be assigned immediately |
| `huawei_cce_node_drain` | Drain | 🟠 High | Evicts all pods from node, affects running workloads |

#### Workflow

**Step 1: Preview Operation** - Call without `confirm` parameter

```bash
# Example: Preview cluster deletion
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx
```

Returns: operation preview, risk warning, confirmation example

**Step 2: Confirm Execution** - Call with `confirm=true`

```bash
# Example: Confirm and execute deletion
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```

### Credential Security

✅ **This skill strictly follows these security rules:**

1. **No persistent credential storage** - Never saves AK/SK, tokens, or certificates to disk
2. **No long-term memory cache** - AK/SK exists only during API call, released afterward
3. **Only project ID memory cache** - Non-sensitive project ID cached in process memory
4. **No credential leakage** - Never includes AK/SK in logs, responses, or errors
5. **Temporary file cleanup** - If temporary cert files are created, they are deleted immediately after use

AK/SK usage methods:

- Environment variables `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_REGION_NAME` (process-level, not saved)
- Per-call parameter (valid only for that call)

---

## Prerequisites

### Python Environment

- Python 3.8+
- Install SDKs: `pip install huaweicloudsdkcce huaweicloudsdkcore`
- Optional for node operations: `pip install kubernetes`

### Environment Variables (Recommended)

```bash
export HW_ACCESS_KEY="your-access-key-id"
export HW_SECRET_KEY="your-secret-access-key"
export HW_REGION_NAME="cn-north-4"
```

### IAM Permission Policies

Ensure the IAM user has the minimum required permissions:

| Permission | Description |
|------------|-------------|
| `cce:cluster:list` | List clusters |
| `cce:cluster:get` | Get cluster details |
| `cce:cluster:create` | Create clusters |
| `cce:cluster:delete` | Delete clusters |
| `cce:cluster:update` | Update clusters (hibernate/awake/bind EIP) |
| `cce:node:list` | List nodes |
| `cce:node:get` | Get node details |
| `cce:node:create` | Create nodes |
| `cce:node:delete` | Delete nodes |
| `cce:node:update` | Update nodes (cordon/uncordon/drain) |
| `cce:nodepool:list` | List node pools |
| `cce:nodepool:create` | Create node pools |
| `cce:nodepool:delete` | Delete node pools |
| `cce:nodepool:update` | Update node pools (resize) |
| `cce:addon:list` | List addons |
| `cce:addon:get` | Get addon details |
| `cce:addon:create` | Install addons |
| `cce:addon:update` | Update addons |
| `cce:addon:delete` | Uninstall addons |

---

## Core Commands

### Cluster Query

| Tool | Function | Parameters |
|------|----------|------------|
| `huawei_list_cce_clusters` | List all CCE clusters in region | `region` |
| `huawei_get_cce_nodes` | Get detailed node information | `region`, `cluster_id`, `node_id` |
| `huawei_get_cce_kubeconfig` | Get cluster kubeconfig | `region`, `cluster_id`, `duration` |

### Cluster Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_create_cce_cluster` | Create CCE cluster | 🟢 Low | No |
| `huawei_delete_cce_cluster` | Delete CCE cluster | 🔴 Critical | **Yes** |
| `huawei_hibernate_cce_cluster` | Hibernate cluster | 🟠 High | **Yes** |
| `huawei_awake_cce_cluster` | Awake cluster | 🟠 High | **Yes** |
| `huawei_bind_cce_cluster_eip` | Bind cluster EIP | 🟢 Low | No |
| `huawei_unbind_cce_cluster_eip` | Unbind cluster EIP | 🟡 Medium | No |

**Recommended defaults:**

- Cluster type: `Turbo` (best performance with ENI network)
- Container network: `eni` for Turbo clusters
- Naming format: `<env>-<app>-cluster` (e.g., `prod-web-cluster`)

### Node Pool Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_list_cce_nodepools` | List node pools | 🟢 Low | No |
| `huawei_create_cce_nodepool` | Create node pool | 🟢 Low | No |
| `huawei_delete_cce_nodepool` | Delete node pool | 🟠 High | **Yes** |
| `huawei_resize_cce_nodepool` | Resize node pool | 🟡 Medium | **Yes** |

**Recommended defaults:**

- Naming format: `<env>-<role>-pool` (e.g., `prod-worker-pool`)
- Initial node count: 2 for HA, or 0 with autoscaling
- Enable autoscaling for dynamic scaling

### Node Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_list_cce_nodes` | List cluster nodes | 🟢 Low | No |
| `huawei_create_cce_node` | Create nodes directly | 🟢 Low | No |
| `huawei_delete_cce_node` | Delete node | 🟠 High | **Yes** |
| `huawei_cce_node_cordon` | Mark node unschedulable | 🟡 Medium | **Yes** |
| `huawei_cce_node_uncordon` | Mark node schedulable | 🟡 Medium | **Yes** |
| `huawei_cce_node_drain` | Evict all pods from node | 🟠 High | **Yes** |
| `huawei_cce_node_status` | Query node scheduling status | 🟢 Low | No |

**Note:** Prefer node pools for managed scaling. Direct node creation is for special cases.

### Addon Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_list_cce_addons` | List cluster addons | 🟢 Low | No |
| `huawei_get_cce_addon_detail` | Get addon details | 🟢 Low | No |
| `huawei_install_cce_addon` | Install addon | 🟢 Low | No |
| `huawei_uninstall_cce_addon` | Uninstall addon | 🟠 High | **Yes** |
| `huawei_update_cce_addon` | Update addon | 🟡 Medium | No |

**Common addons:**

- `coredns` - DNS service
- `metrics-server` - Monitoring metrics
- `everest` - Storage driver

### Network Prerequisites

| Tool | Function | Parameters |
|------|----------|------------|
| `huawei_list_vpc` | List VPCs with CIDR info | `region` |
| `huawei_list_vpc_subnets` | List subnets with AZ info | `region`, `vpc_id` |

**Use these tools to find VPC/subnet IDs before cluster creation.**

---

## Supported Regions

| Region Code | Region Name |
|-------------|-------------|
| cn-north-4 | North China-Beijing 4 |
| cn-north-1 | North China-Beijing 1 |
| cn-north-2 | North China-Beijing 2 |
| cn-east-3 | East China-Shanghai 1 |
| cn-south-1 | South China-Guangzhou |
| cn-south-2 | South China-Guangzhou Friendly |
| cn-east-4 | East China II |
| cn-southwest-2 | Guiyang 1 |
| ap-southeast-1 | Asia-Pacific-Hong Kong |
| ap-southeast-2 | Asia-Pacific-Bangkok |
| ap-southeast-3 | Asia-Pacific-Singapore |

---

## Output Format

All tools return JSON-formatted results containing:

- `status`: operation result (`success` / `error`)
- `data`: operation-specific response (cluster info, node list, addon details, etc.)
- `message`: human-readable description of the result
- `warning`: risk warning for dangerous operations (preview mode only)

## Verification

See [verification-method.md](references/verification-method.md) for detailed verification steps. Quick checklist:

1. Verify AK/SK credentials are configured via environment variables
2. Run `huawei_list_cce_clusters` to confirm API connectivity
3. Test dangerous operation preview (call without `confirm=true`)
4. Verify Turbo cluster ENI network configuration

## Best Practices

- Use environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY`) for credentials — avoid hardcoding
- Always preview dangerous operations before confirming with `confirm=true`
- Use Turbo clusters (`container_network_type=eni`) for high-performance workloads
- Resize node pools during low-traffic periods to minimize business impact
- Keep node pools at ≥2 nodes for production workloads to ensure redundancy
- Regularly check cluster health via `huawei_list_cce_clusters` and `huawei_show_cce_cluster`

---

## References

| Document | Description |
|----------|-------------|
| [task-cluster-management.md](references/task-cluster-management.md) | Cluster lifecycle operations |
| [task-nodepool-management.md](references/task-nodepool-management.md) | Node pool operations |
| [task-node-management.md](references/task-node-management.md) | Node scheduling operations |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide |
| [cce-api-guide.md](references/cce-api-guide.md) | CCE Python SDK API reference |
| [cce-cluster-parameters.md](references/cce-cluster-parameters.md) | Cluster/nodepool creation parameters |

---

## Notes

- Ensure AK/SK has correct IAM permissions
- Different regions may have different resource availability
- All dangerous operations require confirmation
- Deletion operations are irreversible
- Hibernate cluster stops all workloads - use during non-business hours
- Node drain evicts all pods - ensure sufficient replicas
- Turbo clusters recommended for best performance with ENI network