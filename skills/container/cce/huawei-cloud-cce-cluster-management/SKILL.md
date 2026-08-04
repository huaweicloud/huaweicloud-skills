---
name: huawei-cloud-cce-cluster-management
description: |
  Huawei Cloud CCE (Cloud Container Engine) cluster lifecycle management skill using hcloud CLI (KooCLI) for Huawei Cloud API calls and kubectl cce plugin for Kubernetes node operations (cordon/uncordon/drain/status).
  Use this skill when the user wants to: (1) create, delete, hibernate, or awake CCE clusters, (2) list clusters and query cluster/node/nodepool/addon information, (3) manage node pools (create, delete, resize), (4) manage nodes (create, delete, cordon, uncordon, drain), (5) manage addons (install, uninstall, update), (6) bind/unbind cluster EIP for public access, (7) get cluster kubeconfig.
  Trigger: user mentions "CCE cluster", "create cluster", "delete cluster", "node pool", "node management", "hibernate cluster", "awake cluster", "addon", "kubeconfig", "EIP binding", "CCE 集群", "创建集群", "删除集群", "节点池", "节点管理", "休眠集群", "唤醒集群", "插件", "kubeconfig", "EIP 绑定"
tags: [cce, kubernetes, cluster-management, nodepool, addon]
version: 2.0.0
---

# Huawei Cloud CCE Cluster Management

## Overview

Manage CCE (Cloud Container Engine) cluster lifecycle, including cluster creation/deletion/hibernation/awakening, node pool management, node scheduling control, and addon management.

The skill executes Huawei Cloud API calls through **hcloud (KooCLI)** and Kubernetes node operations (cordon/uncordon/drain/status) through **kubectl cce** (the kubectl-cce plugin). The plugin connects to the CCE API Gateway using AK/SK credentials — no cluster EIP or manual kubeconfig required. Two operations (create cluster, create node pool) fall back to the Python SDK because of a known hcloud metadata parsing defect — see [cce-api-guide.md](references/cce-api-guide.md).

**Dependency**: This skill requires `kubectl` and the `kubectl-cce` plugin. Install them via the [huawei-cloud-kubectl-cce-installer](../huawei-cloud-kubectl-cce-installer/SKILL.md) skill.

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
| `huawei_cce_node_drain` | Drain | 🟠 High | Cordons + evicts all pods from node, affects running workloads |

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
5. **Temporary file cleanup** - Temporary kubeconfig files are deleted immediately after use
6. **Config-first credential passing** - If hcloud CLI config has credentials, AK/SK are **not** passed as CLI arguments (avoids `ps aux` exposure). Environment variables are only set for subprocesses if not already present in the parent environment.

Credentials are resolved from parameters or environment variables (process-level, never written to disk):

- **Permanent credentials**: `HW_ACCESS_KEY` + `HW_SECRET_KEY`
- **Temporary credentials** (recommended for CI/CD / IAM temporary access keys): `HW_ACCESS_KEY` + `HW_SECRET_KEY` + `HW_SECURITY_TOKEN`
- `HW_PROJECT_ID` is optional — auto-fetched via `hcloud IAM KeystoneListProjects` when not provided (only for hcloud API calls; kubectl-cce node operations do not need it)
- Per-call `ak` / `sk` parameters override the environment variables for that single call

**Security hardening tip**: Set `HW_ACCESS_KEY` / `HW_SECRET_KEY` in the parent process environment (e.g., `~/.bashrc` or systemd environment file) so they are inherited by subprocesses without explicit passing. The skill detects existing env vars and skips passing AK/SK as CLI arguments to hcloud, preventing credential exposure in process listings (`ps aux`). kubectl-cce reads these env vars directly from the process environment.

```bash
# Permanent
export HW_ACCESS_KEY="your-access-key-id"
export HW_SECRET_KEY="your-secret-access-key"
export HW_REGION_NAME="cn-north-4"

# Temporary (add security token)
export HW_SECURITY_TOKEN="your-security-token"
```

### Node Login Password Security

When creating nodes or node pools, the login credential is resolved with the following **three-level priority**:

1. **`ssh_key` parameter** — SSH key pair name (preferred when available). Mutually exclusive with password.
2. **`password` parameter** — raw node login password passed per call (8–26 chars, ≥3 of: uppercase / lowercase / digits / special).
3. **`CCE_NODE_PASSWORD` environment variable** — used when neither `ssh_key` nor `password` is provided.
4. **Auto-generated random password** — when none of the above is supplied, the skill generates a strong random password automatically.

> ⚠️ **The auto-generated password is NEVER returned in the tool response** (not in `data`, not in `message`, not in logs). To access the node afterwards, the user must **reset the node password** via the CCE console or the ECS API. The success message only contains a hint instructing the user to reset the password.

The raw password is never sent to the CCE API directly; the skill applies SHA-512 salted encryption + base64 encoding internally (see [cce-cluster-parameters.md](references/cce-cluster-parameters.md)).

---

## Prerequisites

### CLI Tools

- **`hcloud`** (Huawei Cloud KooCLI 7.2+) — drives all Huawei Cloud API calls. Install:

  ```bash
  curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh
  hcloud version   # verify install
  ```

  **`kubectl` + `kubectl-cce` plugin** — required for node scheduling operations (cordon/uncordon/drain/status). Install via the [huawei-cloud-kubectl-cce-installer](../huawei-cloud-kubectl-cce-installer/SKILL.md) skill:

  ```bash
  # Check if already installed
  bash ../huawei-cloud-kubectl-cce-installer/scripts/install_kubectl_cce.sh --check

  # Install (after confirming the plan)
  sudo bash ../huawei-cloud-kubectl-cce-installer/scripts/install_kubectl_cce.sh --execute --bin-dir /usr/local/bin
  ```

  The `kubectl cce` plugin connects through the CCE API Gateway using AK/SK credentials — no cluster EIP or manual kubeconfig needed.

### Python Environment

- Python 3.8+
- Install SDK packages (retained for create-cluster / create-nodepool fallback) and helpers:

  ```bash
  pip install huaweicloudsdkcce huaweicloudsdkcore huaweicloudsdkiam passlib pyyaml
  ```

  `passlib` provides SHA-512 salting. `huaweicloudsdkcce` + `huaweicloudsdkcore` + `huaweicloudsdkiam` are used by the two SDK fallback functions (create cluster, create node pool) and IAM project-ID resolution. `pyyaml` parses hcloud JSON output.

### Environment Variables

The skill detects existing environment variables before passing credentials to subprocesses:

- **hcloud CLI calls**: if `HW_ACCESS_KEY`/`HW_SECRET_KEY` are already in `os.environ`, the skill skips passing `--cli-access-key`/`--cli-secret-key` as CLI arguments, preventing exposure in `ps aux`.
- **kubectl-cce calls**: the plugin reads `HW_ACCESS_KEY`/`HW_SECRET_KEY` from the process environment directly. If these variables are already set, the subprocess inherits them naturally — the skill does not set them again.

> **🔒 Security Tip:** Set `HW_ACCESS_KEY`/`HW_SECRET_KEY` at the system or session level (e.g., in `~/.bashrc` or a systemd environment file) so the skill never needs to pass them as explicit CLI arguments. This eliminates the risk of credential exposure in process listings (`ps aux`) and shell history.

```bash
# Set credentials at session level (the skill detects these and skips
# passing them as explicit CLI arguments to hcloud/kubectl-cce)
export HW_ACCESS_KEY="your-access-key-id"
export HW_SECRET_KEY="your-secret-access-key"
export HW_REGION_NAME="cn-north-4"
# Optional, for temporary credentials:
export HW_SECURITY_TOKEN="your-security-token"
# Optional, for node login when ssh_key is not used:
export CCE_NODE_PASSWORD="your-password"
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

## 参数确认

Before executing any command, confirm the following parameters with the user:

### 认证参数

| Parameter | Env Variable | Required | Description |
|-----------|-------------|----------|-------------|
| Access Key ID | `HW_ACCESS_KEY` | ✅ | Huawei Cloud AK, permanent or temporary credential |
| Secret Access Key | `HW_SECRET_KEY` | ✅ | Huawei Cloud SK, permanent or temporary credential |
| Region | `HW_REGION_NAME` | ✅ | Region, e.g. `cn-north-4` |
| Security Token | `HW_SECURITY_TOKEN` | ❌ | Temporary credential security token, STS only |
| Node Password | `CCE_NODE_PASSWORD` | ❌ | Node login password, auto-generated if not set |

### 集群参数

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `cluster_name` | ✅ | — | Cluster name, recommended `<env>-<app>-cluster` |
| `cluster_type` | ❌ | `Turbo` | Cluster type (Turbo/VirtualMachine) |
| `container_network_type` | ❌ | `eni` | Container network type, `eni` for Turbo clusters |
| `cluster_version` | ❌ | API latest | Kubernetes version, auto-select latest if omitted |
| `vpc_id` | ✅ | — | VPC ID |
| `subnet_id` | ✅ | — | Subnet ID |
| `flavor_id` | ✅ | — | Node flavor, e.g. `c7.large.2` |
| `confirm` | ❌ | `false` | Danger confirmation flag, required `true` for delete/hibernate/resize |

### 节点池参数

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `nodepool_name` | ✅ | — | Node pool name, recommended `<env>-<role>-pool` |
| `node_count` | ❌ | `2` | Initial node count, ≥2 recommended for HA |
| `min_node_count` | ❌ | — | Auto-scaling minimum |
| `max_node_count` | ❌ | — | Auto-scaling maximum |
| `ssh_key` | ❌ | — | SSH key pair name, takes priority over password |
| `root_volume_size` | ❌ | `40` | Root disk size (GB) |
| `data_volume_size` | ❌ | `100` | Data disk size (GB) |

### 其他参数

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `duration` | ❌ | `30` | Kubeconfig validity period (days), pass as integer |
| `eip_id` | ❌ | auto | EIP ID, auto-find or create if not provided |
| `addon_id` | ❌ | — | Addon ID (UID), required for detail query |

## Core Commands

### Cluster Query

| Tool | Function | Parameters |
|------|----------|------------|
| `huawei_list_cce_clusters` | List all CCE clusters in region | `region` |
| `huawei_get_cce_nodes` | Get detailed node information | `region`, `cluster_id` |
| `huawei_get_cce_kubeconfig` | Get cluster kubeconfig | `region`, `cluster_id`, `duration` |

### Cluster Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_create_cce_cluster` | Create CCE cluster | 🟢 Low | No |
| `huawei_delete_cce_cluster` | Delete CCE cluster | 🔴 Critical | **Yes** |
| `huawei_hibernate_cce_cluster` | Hibernate cluster | 🟠 High | **Yes** |
| `huawei_awake_cce_cluster` | Awake cluster | 🟠 High | No |
| `huawei_bind_cce_cluster_eip` | Bind cluster EIP (auto-find/create if no eip_id) | 🟢 Low | No |
| `huawei_unbind_cce_cluster_eip` | Unbind cluster EIP | 🟡 Medium | No |

> **Dynamic EIP Binding:** `huawei_bind_cce_cluster_eip` supports dynamic EIP assignment. If `eip_id` is not provided, the skill automatically: (1) lists existing EIPs and finds an unbound one (status=DOWN), (2) if none available, creates a new EIP (traffic billing, 5Mbps, PER share type), (3) binds it to the cluster. The response includes `eip_created` (true/false), `eip_id`, `eip_address`, and `public_endpoint` (the External API URL).

**Recommended defaults:**

- Cluster type: `Turbo` (best performance with ENI network)
- Container network: `eni` for Turbo clusters (default in this skill)
- Cluster version: **omit `cluster_version` to let the API pick the latest supported version**; specify it only when the user requires a specific Kubernetes version
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
- For Turbo clusters, use ENI-compatible flavors (e.g., `c7.large.2`)

### Node Management

| Tool | Function | Risk Level | Requires Confirmation |
|------|----------|------------|----------------------|
| `huawei_list_cce_nodes` | List cluster nodes | 🟢 Low | No |
| `huawei_create_cce_node` | Create nodes directly | 🟢 Low | No |
| `huawei_delete_cce_node` | Delete node | 🟠 High | **Yes** |
| `huawei_cce_node_cordon` | Mark node unschedulable | 🟡 Medium | **Yes** |
| `huawei_cce_node_uncordon` | Mark node schedulable | 🟡 Medium | **Yes** |
| `huawei_cce_node_drain` | Cordon + evict all pods from node | 🟠 High | **Yes** |
| `huawei_cce_node_status` | Query node scheduling status | 🟢 Low | No |

Node scheduling operations (`cordon`, `uncordon`, `drain`, `status`) are executed via **kubectl cce** — the kubectl-cce plugin connects to the CCE API Gateway using AK/SK credentials. **No cluster EIP or manual kubeconfig required**. The plugin handles cordon, eviction, PodDisruptionBudget (PDB) compliance, and DaemonSet pod skipping natively.

`huawei_cce_node_drain` follows **standard drain semantics**: it first cordons the node, then evicts all resident pods (excluding DaemonSet pods) via the k8s Eviction API, which respects `PodDisruptionBudget` (PDB). Pods blocked by PDB will be reported in the `failed_pods` field.

> **Note:** Prefer node pools for managed scaling. Direct node creation is for special cases.

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

> **Addon notes (from E2E verification):**
> - `huawei_get_cce_addon_detail` and `huawei_uninstall_cce_addon` require the addon **UID** (from `huawei_list_cce_addons` → `metadata.uid`), not the addon name.
> - Addon status is in the `status.status` field (e.g., `running`, `upgrading`, `abnormal`), not `spec.status`.
> - After `huawei_update_cce_addon`, the addon may enter `upgrading` state. Wait for it to return to `running` before performing subsequent operations (e.g., uninstall).

### Network Prerequisites

| Tool | Function | Parameters |
|------|----------|------------|
| `huawei_list_vpc` | List VPCs with CIDR info | `region` |
| `huawei_list_vpc_subnets` | List subnets with AZ info | `region`, `vpc_id`(optional) |
| `huawei_list_eips` | List EIPs (shows bound/unbound status) | `region` |
| `huawei_delete_eip` | Delete an EIP (frees public IP) | `region`, `publicip_id` |

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

1. `hcloud version` (should be 7.2+)
2. `kubectl version --client`
3. Verify `HW_ACCESS_KEY` / `HW_SECRET_KEY` env vars are set (add `HW_SECURITY_TOKEN` for temporary credentials)
4. `hcloud CCE ListClusters --cli-region=cn-north-4` (connectivity test)
5. Test dangerous operation preview (call without `confirm=true`)

## Best Practices

- Use environment variables (`HW_ACCESS_KEY` / `HW_SECRET_KEY`) for credentials — avoid hardcoding; add `HW_SECURITY_TOKEN` for temporary credentials
- Always preview dangerous operations before confirming with `confirm=true`
- Prefer Turbo clusters (`container_network_type=eni`) — the default — for high-performance workloads
- Omit `cluster_version` unless the user requires a specific Kubernetes version
- Resize node pools during low-traffic periods to minimize business impact
- Keep node pools at ≥2 nodes for production workloads to ensure redundancy
- Regularly check cluster health via `huawei_list_cce_clusters`

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
| [cce-api-guide.md](references/cce-api-guide.md) | hcloud operation reference |
| [cce-cluster-parameters.md](references/cce-cluster-parameters.md) | Cluster/nodepool creation parameters |

---

## Notes

- Ensure AK/SK (and `HW_SECURITY_TOKEN` for temporary credentials) has correct IAM permissions
- Different regions may have different resource availability
- All dangerous operations require confirmation
- Deletion operations are irreversible
- Hibernate cluster stops all workloads - use during non-business hours
- Node drain uses `kubectl drain` natively: handles cordon + eviction + PDB compliance + DaemonSet skip automatically. Use `--ignore-daemonsets --delete-emptydir-data` flags.
- Turbo clusters recommended for best performance with ENI network
- Create cluster / create node pool use the Python SDK fallback due to a known hcloud metadata parsing defect; all other operations use hcloud CLI
