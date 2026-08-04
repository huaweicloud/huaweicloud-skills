# CCE hcloud Operation Reference

## Overview

This reference documents how the skill maps tool names to **hcloud (KooCLI)** operations and **kubectl cce** commands, the JSON-input convention used for complex request bodies, the SDK fallback for two operations, and the kubectl-cce connection method for node operations.

All Huawei Cloud API calls go through `hcloud`; Kubernetes node scheduling operations go through `kubectl cce` (the kubectl-cce plugin). See [SKILL.md](../SKILL.md) for the high-level architecture.

## Tooling Installation

```bash
# hcloud (KooCLI 7.2+) — Huawei Cloud API calls
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh

# kubectl cce — Kubernetes node operations (cordon/uncordon/drain/status)
#   install per https://kubernetes.io/docs/tasks/tools/

# Python SDK retained ONLY for create-cluster / create-nodepool fallback
pip install huaweicloudsdkcce huaweicloudsdkcore passlib pyyaml
```

## Authentication

hcloud credentials are resolved by `hcloud_runner.resolve_credentials` in this priority: per-call params > environment variables.

| Env Var | Purpose |
|---------|---------|
| `HW_ACCESS_KEY` | Access key ID (permanent or temporary) |
| `HW_SECRET_KEY` | Secret access key (permanent or temporary) |
| `HW_SECURITY_TOKEN` | Security token — **required for temporary AK/SK** (e.g., IAM federated / STS tokens). Omit for permanent AK/SK. |
| `HW_PROJECT_ID` | Optional project ID. Auto-fetched via `hcloud IAM KeystoneListProjects` when missing. |

Every hcloud invocation is built with `--cli-access-key`, `--cli-secret-key`, optional `--cli-security-token`, optional `--cli-project-id`, and `--cli-region`. Project ID is cached in process memory only.

## Tool → hcloud / kubectl Operation Map

| Tool | Service | Operation / Command | Notes |
|------|---------|---------------------|-------|
| `huawei_list_vpc` | VPC | `ListVpcs` | |
| `huawei_list_vpc_subnets` | VPC | `ListSubnets` | |
| `huawei_list_cce_clusters` | CCE | `ListClusters` | |
| `huawei_create_cce_cluster` | (SDK) | `CreateCluster` via Python SDK | **hcloud defect — SDK fallback**. Uses `hcloud VPC ShowSubnet` to resolve `neutron_subnet_id` for Turbo (eni) clusters. |
| `huawei_delete_cce_cluster` | CCE | `DeleteCluster` | confirm required |
| `huawei_hibernate_cce_cluster` | CCE | `HibernateCluster` | confirm required |
| `huawei_awake_cce_cluster` | CCE | `AwakeCluster` | |
| `huawei_bind_cce_cluster_eip` | CCE | `UpdateClusterEip` + `ShowCluster` | 2-call: bind then read external endpoint |
| `huawei_unbind_cce_cluster_eip` | CCE | `UpdateClusterEip` | action=unbind |
| `huawei_get_cce_kubeconfig` | CCE | `CreateKubernetesClusterCert` | Returns cert-based kubeconfig data |
| `huawei_list_cce_nodes` / `huawei_get_cce_nodes` | CCE | `ListNodes` | |
| `huawei_create_cce_node` | CCE | `CreateNode` via `--cli-jsonInput` | Uses `resolve_node_login` |
| `huawei_delete_cce_node` | CCE | `DeleteNode` | confirm required |
| `huawei_list_cce_nodepools` | CCE | `ListNodePools` | |
| `huawei_create_cce_nodepool` | (SDK) | `CreateNodePool` via Python SDK | **hcloud defect — SDK fallback**. Uses `resolve_node_login`. |
| `huawei_resize_cce_nodepool` | CCE | `ListNodePools` → `ScaleNodePool` | Resolves nodepool name→UID, then scales. confirm required. |
| `huawei_delete_cce_nodepool` | CCE | `ListNodePools` → `DeleteNodePool` | Resolves name→UID, then deletes. confirm required. |
| `huawei_list_cce_addons` | CCE | `ListAddonInstances` | |
| `huawei_get_cce_addon_detail` | CCE | `ShowAddonInstance` | |
| `huawei_install_cce_addon` | CCE | `CreateAddonInstance` via `--cli-jsonInput` | |
| `huawei_update_cce_addon` | CCE | `UpdateAddonInstance` via `--cli-jsonInput` | |
| `huawei_uninstall_cce_addon` | CCE | `DeleteAddonInstance` | confirm required. Uses addon **UID**, not name. |

> **Addon UID vs Name:** `huawei_get_cce_addon_detail` (`ShowAddonInstance`) and `huawei_uninstall_cce_addon` (`DeleteAddonInstance`) require the addon **UID** (from `ListAddonInstances` → `metadata.uid`), not the addon name. Passing the name will return a "not found" error.
>
> **Addon Status Field:** The addon's current status is in `status.status` (e.g., `running`, `upgrading`, `abnormal`), not `spec.status`. After `huawei_update_cce_addon`, the addon may enter `upgrading` state — wait for it to return to `running` before subsequent operations.
| `huawei_cce_node_cordon` | kubectl cce | `kubectl cce --cluster-id <id> --region <r> --project-id <pid> cordon <node>` | No EIP needed. confirm required. |
| `huawei_cce_node_uncordon` | kubectl cce | `kubectl cce ... uncordon <node>` | confirm required. |
| `huawei_cce_node_drain` | kubectl cce | `kubectl cce ... drain <node> --ignore-daemonsets --delete-emptydir-data --grace-period=30 --timeout=120s` | Native drain: cordon + evict, respects PDB. confirm required. |
| `huawei_cce_node_status` | kubectl cce | `kubectl cce ... get node <node> -o json` | Returns `schedulable`, `ready`, conditions. |

## Request Body Convention: `--cli-jsonInput`

For operations with complex/nested request bodies (`CreateNode`, `CreateAddonInstance`, `UpdateAddonInstance`), the skill uses hcloud's `--cli-jsonInput` flag. The JSON file has the shape:

```json
{
  "path":  { "cluster_id": "xxx", "project_id": "xxx" },
  "query": { "optional_query_param": "value" },
  "body":  { "apiVersion": "v3", "kind": "Node", "metadata": { "...": "..." }, "spec": { "...": "..." } }
}
```

- `path` — path parameters (e.g., `cluster_id`, `addon_id`)
- `query` — query parameters (optional)
- `body` — request body object matching the CCE API schema

The skill writes this JSON to a temporary file, passes it via `--cli-jsonInput <file>`, and deletes the file immediately after the call (see `hcloud_runner.run_with_body`).

### Example: `CreateNode` body

```json
{
  "path": { "cluster_id": "cluster-id", "project_id": "project-id" },
  "body": {
    "apiVersion": "v3",
    "kind": "Node",
    "metadata": { "name": "node-clusterid8" },
    "spec": {
      "flavor": "c7.large.2",
      "az": "cn-north-4a",
      "os": "EulerOS 2.9",
      "count": 1,
      "rootVolume": { "size": 40, "volumetype": "SSD" },
      "dataVolumes": [ { "size": 100, "volumetype": "SSD" } ],
      "login": { "userPassword": { "username": "root", "password": "<sha512-salted-base64>" } }
    }
  }
}
```

> The `login` block is produced by `common.resolve_node_login` — see [SKILL.md](../SKILL.md) "Node Login Password Security" for the three-level priority. The `password` field is always SHA-512 salted + base64 encoded; the raw password is never sent to the API.

### Example: `CreateAddonInstance` body

```json
{
  "body": {
    "kind": "Addon",
    "apiVersion": "v3",
    "metadata": { "annotations": { "addon.install/type": "install" } },
    "spec": {
      "clusterID": "cluster-id",
      "addonTemplateName": "volcano",
      "version": "1.21.7",
      "values": { "basic": { "category": "small", "flavor": 1 }, "custom": { "default_scheduler": true } }
    }
  }
}
```

> The JSON keys (e.g., `addonTemplateName`, `clusterID`, `rootVolume`, `dataVolumes`, `primaryNic`) match the public CCE REST API schema directly — use the camelCase names exactly as documented in the CCE API Reference.

## hcloud Defect: CreateCluster / CreateNodePool (SDK Fallback)

`hcloud CCE CreateCluster` and `hcloud CCE CreateNodePool` have a **metadata parsing defect**: the nested `metadata`/`spec` fields of the request body are not parsed correctly by hcloud, causing the API to reject or misinterpret the request.

**Mitigation in this skill:** the two affected tools (`huawei_create_cce_cluster`, `huawei_create_cce_nodepool`) bypass hcloud and call the Python SDK directly via `huaweicloudsdkcce.v3`:

| Tool | SDK call | Why SDK |
|------|----------|---------|
| `huawei_create_cce_cluster` | `CceClient.create_cluster(CreateClusterRequest)` | hcloud CreateCluster metadata defect |
| `huawei_create_cce_nodepool` | `CceClient.create_node_pool(CreateNodePoolRequest)` | hcloud CreateNodePool metadata defect |

The SDK client is constructed with the same AK/SK/(security token)/project-id resolved by `hcloud_runner.resolve_credentials`, so credential handling stays uniform. For Turbo (eni) clusters, `create_cce_cluster` still uses `hcloud VPC ShowSubnet` to resolve the `neutron_subnet_id` before calling the SDK.

All other operations use hcloud and are unaffected.

## kubectl cce Connection Method

Node scheduling tools (`cordon`, `uncordon`, `drain`, `status`) execute via `kubectl cce` — the kubectl-cce plugin connects to the CCE API Gateway using AK/SK credentials. **No cluster EIP, kubeconfig download, or manual cert management needed.**

The `kubectl_cce()` helper in `hcloud_runner.py` builds the command:

```bash
# Environment variables set inline (same shell process)
HW_ACCESS_KEY=<AK> HW_SECRET_KEY=<SK> HW_SECURITY_TOKEN=<token> \
  kubectl cce \
    --cluster-id <cluster_id> \
    --region <region> \
    --project-id <project_id> \
    <subcommand> [args...]
```

### Key Points

- **Environment variables** (`HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`) are set inline in the same shell process — no persistent credential files.
- **`--project-id`** is required for the plugin to resolve the CCE management endpoint.
- **No kubeconfig needed**: the plugin handles authentication internally via the CCE API Gateway.
- `huawei_get_cce_kubeconfig` still wraps `CreateKubernetesClusterCert` for callers who want the raw cert payload (not used by node operations).

## hcloud Error Categories

hcloud tags failures with bracketed error categories in stderr. The skill surfaces them in the `error` field of tool responses:

| Tag | Meaning | Typical Cause |
|-----|---------|---------------|
| `[NETWORK_ERROR]` | Cannot reach the Huawei Cloud API | Network outage, DNS, proxy, wrong region endpoint |
| `[CLI_ERROR]` | hcloud CLI itself failed | Bad CLI args, missing `--cli-jsonInput` file, hcloud not installed |
| `[USE_ERROR]` | Parameter/usage error | Invalid param value, missing required flag |
| `[OPENAPI_ERROR]` | Huawei Cloud OpenAPI returned an error | 4xx/5xx from the service (permissions, quota, state conflict) |
| `[APIE_ERROR]` | API engine / API gateway error | Throttling, gateway-side failure, transient retry candidate |

See [troubleshooting.md](troubleshooting.md) for resolution steps per error category.

## Official Documentation

- [CCE API Reference](https://support.huaweicloud.com/api-cce/cce_02_0082.html)
- [hcloud (KooCLI) Documentation](https://support.huaweicloud.com/zh-cn/cli/index.html)
- [kubectl Documentation](https://kubernetes.io/docs/reference/kubectl/)
- [kubectl-cce Plugin](https://support.huaweicloud.com/engineer/cloudeye/cce_03_0123.html)
- [CCE Password Salting and Encryption](https://support.huaweicloud.com/api-cce/add-salt.html)
