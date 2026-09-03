---
name: huawei-cloud-modelarts-resource-pool-management
description: "Manage Huawei Cloud ModelArts dedicated resource pools (专属资源池) and node pools through full lifecycle operations via hcloud CLI. Covers 53 operations across 10 functional domains: resource pool management, pool nodes, node pool management, network resources, tag management, plugin management, jobs/tasks, scheduled events, OS configuration, and resource flavor/event queries. Includes BSS on-demand pricing inquiry before chargeable operations (create/expand) to inform users of costs. All write operations require user confirmation.\nTriggers include: \"资源池\", \"专属资源池\", \"resource pool\", \"创建资源池\", \"查询资源池\", \"删除资源池\", \"更新资源池\", \"资源池监控\", \"资源池节点\", \"pool node\", \"节点池\", \"node pool\", \"资源池网络\", \"pool network\", \"资源池标签\", \"pool tags\", \"插件\", \"plugin\", \"工作负载\", \"workload\", \"定时事件\", \"scheduled event\", \"OS配置\", \"规格列表\", \"ModelArts resource pool\", \"manage resource pool\", \"询价\", \"pricing\", \"按需价格\", \"价格查询\".\n"
---

# Huawei Cloud ModelArts Resource Pool Management

> Full lifecycle management for ModelArts dedicated resource pools and node pools via hcloud CLI — 53 operations across 10 functional domains.

---

## Overview

This skill enables users to manage Huawei Cloud ModelArts dedicated resource pools (专属资源池) and node pools through the `hcloud` CLI. It covers the complete lifecycle including resource pool CRUD, node management, node pool management, network resources, tag management, plugin management, workloads, scheduled events, OS configuration, and resource flavor queries. BSS pricing inquiry is included for chargeable operations.

### Architecture

```
User Request → Agent → hcloud ModelArts <Operation> --cli-region={region} [--params] → Huawei Cloud ModelArts API
```

### Applicable Scenarios

- **Resource Pool Management**: Create, list, show, update, delete resource pools; monitor, statistics, node config, order management
- **Pool Node Management**: List/show nodes; batch delete, update, lock, unlock, reboot, reset, resize, migrate, bind
- **Node Pool Management**: Create, list, show, update, delete node pools within a resource pool
- **Network Resources**: Create, list, show, update, delete ModelArts networks; query available IPs
- **Tag Management**: List, show, batch create, batch delete resource pool tags
- **Plugin Management**: List plugin templates; list and create pool plugins
- **Jobs & Workloads**: List workloads, show workload statistics, list jobs
- **Scheduled Events**: List and accept scheduled events
- **OS Configuration**: Show OS user config and quotas
- **Resource Flavors & Events**: List resource flavors, events, node config templates

---

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Huawei Cloud AK/SK** configured via hcloud (see Security & Credential Check below)
3. **ModelArts service** enabled in the target region
4. **IAM permissions** — See [references/iam-policies.md](references/iam-policies.md)

### Security & Credential Check

> **⚠️ CRITICAL: This section defines the agent's security boundary. Follow it strictly.**

#### 🔒 Security Rules (MANDATORY)

- 🚫 **NEVER** read, echo, or print AK/SK values (e.g., `cat ~/.hcloud/config.json`, `echo $HW_ACCESS_KEY` is FORBIDDEN)
- 🚫 **NEVER** read or cat credential files such as `~/.hcloud/config.json` or any file that may contain secrets
- 🚫 **NEVER** ask the user to input AK/SK directly in the conversation or command line
- 🚫 **NEVER** execute `hcloud configure set --cli-access-key=... --cli-secret-key=...` — credential configuration is the **user's responsibility**, done outside the agent session
- 🚫 **NEVER** pass `--cli-access-key`/`--cli-secret-key` on **every API call** — they will be exposed in process listings (`ps aux`) for the entire request duration
- ✅ **ALWAYS** use `hcloud configure list` to check credential status (presence check only, not values)
- ✅ If no valid profile exists, **STOP** and instruct the user to configure credentials outside this session
- ✅ **Recommend** using IAM user with minimal permissions instead of main account

#### ✅ Agent Credential Check (the ONLY acceptable check)

```bash
# Step 1: Check credential status — presence only, not values
hcloud configure list
```

- ✅ **Expected**: Shows a valid profile with `mode: AKSK`
- ❌ **If empty/invalid** → Guide the user with the 3-step process below:

  **Step-by-step guidance (copy-paste for the user):**

  > *"No valid credentials found. Please follow these 3 steps in your terminal:"*
  >
  > **① Get your AK/SK**
  > Log in to [Huawei Cloud Console](https://console.huaweicloud.com) → IAM → Access Keys. If you don't have one, click "Create Access Key" and save it securely.
  >
  > **② Run this in your terminal (one-time setup):**
  > ```bash
  > hcloud configure set --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK>
  > ```
  > *(Replace `<YOUR_AK>` and `<YOUR_SK>` with the values from step ①)*
  >
  > **③ Come back and tell me "configured"**, I'll verify it works.
  >
  > *Note: The `configure set` command stores your credentials in `~/.hcloud/config.json`. After that, all hcloud commands use them automatically — no need to pass AK/SK again.*
  >
  > *Agent: DO NOT execute any `configure set` command yourself.*

#### 🔧 User's Responsibility (for documentation, NOT agent execution)

The user configures credentials **outside the agent session** (in their own terminal):

```bash
# One-time setup — run this in your terminal, NOT in the agent chat
HISTCONTROL=ignorespace
 hcloud configure set --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK>
```

> ⚠️ **Note**: hcloud CLI does **NOT** read `HW_ACCESS_KEY`/`HW_SECRET_KEY` environment variables (those are for Python SDK only). `hcloud configure set` is the only supported credential configuration method.

---

## Workflow

### Step 1: Identify the Operation

Determine which resource pool operation the user needs based on their request:

| User Intent | Operation Category |
|-------------|-------------------|
| Create/list/show/update/delete resource pools | Resource Pool Management |
| List/show/batch operations on pool nodes | Pool Node Management |
| Create/list/show/update/delete node pools | Node Pool Management |
| Create/list/show/update/delete networks | Network Resources |
| List/show/create/delete pool tags | Tag Management |
| List/create plugins | Plugin Management |
| List workloads, show statistics | Jobs & Workloads |
| List/accept scheduled events | Scheduled Events |
| Show OS config/quotas | OS Configuration |
| List flavors/events/templates | Resource Flavors & Events |

### Step 2: Execute CLI Command

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

> `{region}` must be replaced with the actual region, e.g., `cn-north-4`. Do NOT hardcode the region.

### Step 2.5: ⚠️ Pre-Flight Check (MANDATORY for Write Operations)

> **Before executing ANY write operation** (Create/Update/Delete/Patch/Batch/Accept), you MUST:
>
> 1. **Read [references/known-issues.md](references/known-issues.md)** — Scan the relevant section for the target API
> 2. **Check the Pre-Flight Checklist** at the bottom of that file — Verify all conditions are met
> 3. **Apply documented workarounds** — Especially for the following high-risk operations:
>
> | Operation | Critical Issue | Action Required |
> |-----------|--------------|----------------|
> | PatchPool, PatchNetwork, PatchNodePool | Content-Type must be `application/merge-patch+json` | Use `--cli-jsonInput` with header section |
> | BatchUpdatePoolNodes | `--action` values are not true/false | Use `--cli-jsonInput` with string action |
> | CreatePool | Network name must include project ID suffix | Query ListNetworks for exact name |
> | CreateNodePool | count ≥ 1, maxCount ≤ count | Verify constraints before execution |
> | ShowNetworkAvailableIp | network_id from `status.subnets[0].networkId` | Query ShowNetwork first |
> | ListEvents | `--resource` must be `pools` (plural) | Use plural form |
> | BatchResetPoolNodes | strategy not supported for VM pools | Known limitation, inform user |
> | BatchResizePoolNodes | Only supports hyperinstance nodes | Known limitation, inform user |
> | DeleteNetwork | Fails if network in use by pool | Delete pool first |
>
> **Skipping this step will cause preventable failures.** Every issue in the table was discovered through real API testing.

### Step 3: Handle Write Operations

For all write operations (Create/Update/Delete/Patch/Batch/Accept), **prompt the user for confirmation before execution**. For chargeable operations (CreatePool, CreateNodePool, PatchNodePool, BatchResizePoolNodes, CreateOrderId), **inquire BSS pricing first** to inform the user of costs. See [references/pricing-inquiry.md](references/pricing-inquiry.md) for the pricing inquiry workflow.

---

## KooCLI Command Format Standard

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Fixed: `ModelArts` | `ModelArts` |
| Operation name | PascalCase | `ListPools`, `CreatePool` |
| Region parameter | `--cli-region={region}` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--pool_name=xxx` |
| Indexed parameter | `--key.1=value1` | `--node_name.1=node1` |
| project_id | Auto-resolved if omitted | Uses configured project ID |

> **Note**: `--project_id` is auto-resolved from authentication credentials if omitted. Include it explicitly only when targeting a specific project.

> **Complex parameters**: For complex nested parameters (e.g., `metadata`, `spec`), use `--cli-jsonInput=/path/to/file.json`. The JSON file must wrap body in `{"body": {...}}` envelope.

---

## Core Commands

All 53 CLI command examples across 10 functional domains are documented in a separate reference file.

> **📖 For detailed command syntax, parameters, and examples, read [references/cli-command-examples.md](references/cli-command-examples.md)**

### Quick Index

| # | Domain | APIs | Key Operations |
|---|--------|------|----------------|
| 1 | Resource Pool Management | 11 | ListPools, ShowPool, CreatePool, PatchPool, DeletePool, ShowPoolMonitor/Statistics/RuntimeMetrics/NodeConfig, CreateOrderId, ShowOrder |
| 2 | Pool Node Management | 11 | ListPoolNodes, ShowPoolNode, BatchDelete/Update/Lock/Unlock/Reboot/Reset/Resize/Migrate/Bind |
| 3 | Node Pool Management | 6 | ListNodePools, ShowNodePool, CreateNodePool, PatchNodePool, DeleteNodePool, ListNodePoolNodes |
| 4 | Network Resources | 6 | ListNetworks, ShowNetwork, CreateNetwork, PatchNetwork, DeleteNetwork, ShowNetworkAvailableIp |
| 5 | Tag Management | 4 | ListPoolTags, ShowPoolTags, BatchCreatePoolTags, BatchDeletePoolTags |
| 6 | Plugin Management | 4 | ListPluginTemplates, ShowPluginTemplate, ListPoolPlugins, CreatePoolPlugin |
| 7 | Jobs & Workloads | 3 | ListWorkloads, ShowWorkloadStatistics, ListJobs |
| 8 | Scheduled Events | 2 | ListScheduledEvents, AcceptScheduledEvent |
| 9 | OS Configuration | 2 | ShowOsConfig, ShowOsQuota |
| 10 | Resource Flavors & Events | 4 | ListResourceFlavors, ListEvents, ShowNodeConfigTemplate, ShowPoolNodeConfigTemplate |

> When executing any command, always refer to the reference file for exact parameter names, required/optional flags, and usage patterns.

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{region}` | Yes | Huawei Cloud region | `cn-north-4`, `cn-east-2` |
| `{pool_name}` | Pool ops | Resource pool name | `my-resource-pool` |
| `{node_name}` | Node ops | Pool node name | `node-xxx` |
| `{nodepool_name}` | NodePool ops | Node pool name | `my-nodepool` |
| `{network_name}` | Network ops | Network name | `my-network` |
| `{flavor_id}` | Create/Resize | Resource flavor ID | `modelarts.vm.cpu.16u64g.d` |
| `{project_id}` | No (auto) | Project ID, auto-resolved if omitted | Omit for default |
| `{order_name}` | ShowOrder | Order name | `order-xxx` |

---

## SDK Fallback

If a CLI operation fails due to a CLI bug, fall back to SDK:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkmodelarts.v2.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v2.region.modelarts_region import ModelArtsRegion

credentials = BasicCredentials(ak="{AK}", sk="{SK}", project_id="{project_id}")
client = ModelArtsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(ModelArtsRegion.value_of("{region}")) \
    .build()
```

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/cli-command-examples.md](references/cli-command-examples.md) | Detailed CLI command syntax and examples for all 53 APIs |
| [references/api-paths.md](references/api-paths.md) | REST API paths from SDK source |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policies |
| [references/known-issues.md](references/known-issues.md) | Known issues and workarounds |
| [references/pricing-inquiry.md](references/pricing-inquiry.md) | BSS pricing inquiry guide for chargeable operations |
| [references/verification-method.md](references/verification-method.md) | Verification and testing methods |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation and authentication guide |

---

## Known Issues Summary

> **⚠️ Read [references/known-issues.md](references/known-issues.md) BEFORE any write operation.** All issues below were verified through real API testing.

**Critical (will cause immediate failure):**
- **PATCH operations** (PatchPool/PatchNetwork/PatchNodePool): Must use `--cli-jsonInput` with `Content-Type: application/merge-patch+json` header
- **BatchUpdatePoolNodes**: `--action` values are `openHaRedundant/closeHaRedundant/createTags/deleteTags`, NOT `true/false`; use `--cli-jsonInput`
- **CreatePool**: Network name must be full name with project ID suffix; pool type is `Dedicate` (no trailing d)
- **CreateNodePool**: `count` must be ≥ 1; `maxCount` must be ≤ `count`
- **ShowNetworkAvailableIp**: `--network_id` must come from `status.subnets[0].networkId`, not `spec.subnets[0].id`
- **ListEvents**: `--resource` must be `pools` (plural), not `pool`

**Known API limitations:**
- **BatchResetPoolNodes**: `rollingConfig.strategy` has no valid value for VM pools
- **BatchResizePoolNodes**: Only supports hyperinstance scaling, not regular VM nodes
- **BatchMigratePoolNodes**: Source and target cluster names must differ
- **DeleteNetwork**: Fails if network is in use by a resource pool (delete pool first)

**Data field locations:**
- Node tags: `metadata.annotations["os.modelarts/tms.tags"]` (JSON string, not `metadata.labels`)
- Node lock status: `metadata.annotations["os.modelarts.node/lock.action"]`

> See [references/known-issues.md](references/known-issues.md) for full details, workarounds, and the Pre-Flight Checklist.

---

## Notes

- All write operations (Create/Update/Delete/Patch/Batch/Accept) require user confirmation before execution
- Chargeable operations (CreatePool, CreateNodePool, PatchNodePool, BatchResizePoolNodes, CreateOrderId) require BSS pricing inquiry to inform users of costs before execution
- Region is not hardcoded — uses `{region}` placeholder
- `project_id` is auto-resolved when omitted
- No hardcoded AK/SK in any file — credentials configured via `hcloud configure set` by the user outside the agent session
- Agent must use `hcloud configure list` for credential presence check only — NEVER read/echo AK/SK values
- If no valid credentials found, agent must STOP and guide user through the 3-step configuration process (see Prerequisites section)
- SDK fallback available when CLI encounters bugs
- Complex nested parameters use `--cli-jsonInput` with JSON file
