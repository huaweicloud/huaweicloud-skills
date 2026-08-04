# Acceptance Criteria — huawei-cloud-cce-cluster-management

## 1. Cluster Lifecycle Management

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 1.1 | Create CCE cluster | `huawei_create_cce_cluster` with VPC/subnet/flavor | Cluster status becomes `Available` |
| 1.2 | List clusters | `huawei_list_cce_clusters` | Returns JSON of all clusters in region |
| 1.3 | Hibernate cluster | `huawei_hibernate_cce_cluster` + `confirm=true` | Cluster status becomes `Hibernation` |
| 1.4 | Awake cluster | `huawei_awake_cce_cluster` | Cluster status restored to `Available` |
| 1.5 | Delete cluster | `huawei_delete_cce_cluster` + `confirm=true` | Cluster deleted, no longer in list |
| 1.6 | Unconfirmed dangerous operation | Call delete/hibernate without `confirm=true` | Returns `warning` preview, does not execute |

> **⚠️ Cost & Risk Warnings:**
> - **Create cluster** (1.1): Incurs billing charges for cluster resources (nodes, EIP, etc.). Confirm the estimated cost with the user before proceeding.
> - **Hibernate cluster** (1.3): Stops billing for compute nodes but retains cluster metadata. Data is preserved; billing resumes when awoken.
> - **Delete cluster** (1.5): **Irreversible.** All workloads, configurations, and persistent data are permanently lost. The user must explicitly acknowledge data loss risk before passing `confirm=true`.

## 2. Node Pool Management

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 2.1 | Create node pool | `huawei_create_cce_nodepool` with flavor and node count | Node pool created, node count matches |
| 2.2 | List node pools | `huawei_list_cce_nodepools` | Returns all node pools in cluster |
| 2.3 | Resize node pool | `huawei_resize_cce_nodepool` + `confirm=true` | Node count changed successfully |
| 2.4 | Delete node pool | `huawei_delete_cce_nodepool` + `confirm=true` | Node pool deleted |

> **⚠️ Cost & Risk Warnings:**
> - **Create node pool** (2.1): Adds compute resources; billing charges apply for new nodes.
> - **Resize node pool** (2.3): Scaling down may cause Pod eviction and service disruption. Warn the user about potential workload impact.
> - **Delete node pool** (2.4): All Pods on the node pool are terminated. Ensure workloads are drained or migrated first.

## 3. Node Management

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 3.1 | List nodes | `huawei_list_cce_nodes` | Returns all nodes in cluster |
| 3.2 | Create node | `huawei_create_cce_node` with flavor and data disk | Node created and joins cluster |
| 3.3 | Cordon node | `huawei_cce_node_cordon` + `confirm=true` | Node becomes `Unschedulable` |
| 3.4 | Uncordon node | `huawei_cce_node_uncordon` + `confirm=true` | Node restored to `Schedulable` |
| 3.5 | Drain node | `huawei_cce_node_drain` + `confirm=true` | Node cordoned + Pods evicted |
| 3.6 | Node status query | `huawei_cce_node_status` | Returns node scheduling status |
| 3.7 | Delete node | `huawei_delete_cce_node` + `confirm=true` | Node deleted |

> **⚠️ Cost & Risk Warnings:**
> - **Create node** (3.2): Incurs billing charges for the new compute instance.
> - **Cordon node** (3.3): New Pods will not be scheduled on the node. Existing Pods continue running.
> - **Drain node** (3.5): Evicts all Pods from the node. Stateful workloads may lose data if not properly handled. Warn the user about potential service disruption.
> - **Delete node** (3.7): **Irreversible.** All Pods on the node are terminated. Local data is lost. The user must acknowledge data loss risk before passing `confirm=true`.

## 4. Addon Management

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 4.1 | List addons | `huawei_list_cce_addons` | Returns all addons in cluster |
| 4.2 | Get addon detail | `huawei_get_cce_addon_detail` with addon UID | Returns addon configuration details |
| 4.3 | Install addon | `huawei_install_cce_addon` with template name and params | Addon status becomes `running` |
| 4.4 | Update addon | `huawei_update_cce_addon` with new config | Addon configuration updated |
| 4.5 | Uninstall addon | `huawei_uninstall_cce_addon` + `confirm=true` | Addon removed |

> **⚠️ Risk Warnings:**
> - **Uninstall addon** (4.5): Removing a critical addon (e.g., coredns, everest-csi-driver) may cause cluster malfunction. Warn the user to verify the addon is not required before proceeding.

## 5. Network Management

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 5.1 | Bind cluster EIP | `huawei_bind_cce_cluster_eip` | Cluster obtains public access endpoint |
| 5.2 | Auto-create EIP | `huawei_bind_cce_cluster_eip` without `eip_id` | Auto-creates and binds EIP |
| 5.3 | Unbind cluster EIP | `huawei_unbind_cce_cluster_eip` | EIP unbound from cluster |

> **⚠️ Cost Warning:**
> - **Bind EIP** (5.1, 5.2): EIP incurs bandwidth charges. If auto-creating (5.2), inform the user that a new EIP with traffic billing (5 Mbps) will be created.

## 6. Kubeconfig Retrieval

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 6.1 | Get kubeconfig | `huawei_get_cce_kubeconfig` with `duration=30` | Returns valid kubeconfig JSON |
| 6.2 | Duration as integer | Pass `duration=30` (not `"30d"`) | API returns normally |

## 7. Security & Confirmation Mechanism

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 7.1 | Dangerous operation preview | Call delete/hibernate/resize without `confirm` | Returns warning, does not execute |
| 7.2 | Dangerous operation confirmation | Pass `confirm=true` | Operation executes successfully |
| 7.3 | Node password security | Do not pass password/ssh_key | Auto-generates random password, SHA-512 encrypted |
| 7.4 | Environment variable auth | Set `HW_ACCESS_KEY`/`HW_SECRET_KEY` | All commands work normally |
| 7.5 | Temporary credentials | Set `HW_SECURITY_TOKEN` | STS credential auth succeeds |
| 7.6 | No AK/SK in process args | Check `ps aux` during hcloud/kubectl-cce calls | No `--cli-access-key`/`--cli-secret-key` in process list |
| 7.7 | Env-first credential detection | Set `HW_ACCESS_KEY`/`HW_SECRET_KEY` in parent env | Skill detects existing env vars, skips passing as CLI args |

## 8. Error Handling

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 8.1 | `[USE_ERROR]` detection | hcloud returns `[USE_ERROR]` | Skill identifies and returns friendly error |
| 8.2 | Cluster not found | Operate on non-existent `cluster_id` | Returns clear error message |
| 8.3 | Network unreachable | Invalid VPC/subnet ID | Returns network error message |
| 8.4 | Delete during addon upgrade | Delete addon in `upgrading` status | Returns clear error message |

## 9. CLI Tool Dependencies

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 9.1 | hcloud installed | `hcloud version` | Version ≥ 7.2 |
| 9.2 | kubectl-cce installed | `kubectl cce --help` | Plugin available |
| 9.3 | Python dependencies | `pip install -r requirements.txt` | All dependencies installed successfully |
