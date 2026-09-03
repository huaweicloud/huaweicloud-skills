---
name: huawei-cloud-modelarts-notebook-management
description: |
  Manage Huawei Cloud ModelArts Notebook instances through full lifecycle operations via hcloud CLI. Covers 31 API interfaces across 7 functional domains: instance management (create/list/show/update/delete/start/stop), lease management (show/renew), tag management (show/create/delete), image management (create/list/register/show/delete/sync/group operations), flavor and cluster queries (list flavors/switchable flavors/clusters/features), and dynamic storage management (list/attach/show/detach). All write operations require user confirmation before execution. Triggers include: "ModelArts notebook", "notebook实例", "创建notebook", "查询notebook", "启动notebook", "停止notebook", "删除notebook", "notebook镜像", "notebook规格", "notebook存储", "notebook标签", "notebook租期", "manage notebook", "notebook management", "ModelArts notebook management".
tags: [huawei-cloud, modelarts, notebook, ai, devtools]
---

# Huawei Cloud ModelArts Notebook Management

> Full lifecycle management for ModelArts Notebook instances via hcloud CLI — 31 API interfaces across 7 functional domains.

---

## Overview

This skill enables users to manage Huawei Cloud ModelArts Notebook instances through the `hcloud` CLI. It covers the complete notebook lifecycle including instance CRUD, start/stop, lease renewal, tag management, image management, flavor/cluster queries, feature queries, and dynamic storage management.

### Architecture

```
User Request → Agent → hcloud ModelArts <Operation> --cli-region={region} [--params] → Huawei Cloud ModelArts API
```

### Applicable Scenarios

- **Daily Operations**: List notebooks, check status, view details, query flavors
- **Instance Lifecycle**: Create, start, stop, update, delete notebook instances
- **Image Management**: Save running instance as image, register/list/delete/sync custom images
- **Storage Management**: Dynamically attach/detach storage to notebook instances
- **Lease Management**: Query and renew notebook leases
- **Tag Management**: Create, delete, query notebook tags

### Scope

本 skill **仅支持** ModelArts Notebook 实例管理（31 个 API），涵盖上述 7 个功能域。

**不支持**以下 ModelArts 能力，相关请求请使用对应 skill：
- 推理服务（在线服务、批量服务）— 使用推理服务管理 skill
- DevServer（开发环境）— 使用 DevServer 管理 skill
- 模型管理（导入/导出/发布模型）— 使用模型管理 skill
- 训练作业（创建/管理训练任务）— 使用训练作业管理 skill
- 自动搜索、超参调优 — 使用自动搜索 skill

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
- 🚫 **NEVER** execute `hcloud configure set --cli-access-key=... --cli-secret-key=...` — credential configuration is the *user's responsibility*, done outside the agent session
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

Determine which notebook operation the user needs based on their request:

| User Intent | Operation Category |
|-------------|-------------------|
| Create/list/view/update/delete/start/stop notebook | Instance Management |
| Query/renew lease | Lease Management |
| Create/delete/query tags | Tag Management |
| Save/register/list/delete/sync image | Image Management |
| Query flavors/clusters/features | Flavor & Cluster |
| Attach/detach/list storage | Dynamic Storage |

### Step 2: Execute CLI Command

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

> `{region}` must be replaced with the actual region, e.g., `cn-north-4`. Do NOT hardcode the region.

### Step 2.5: Consult Known Issues (Write Operations Only)

> **Before executing any write operation**, read [references/known-issues.md](references/known-issues.md) and check for known pitfalls, parameter corrections, and required workarounds for the target API.

Common workarounds to apply:

| API | Issue | Workaround |
|-----|-------|------------|
| CreateNotebook (EVS) | CLI rejects `--volume.category=EVS` | Use `--cli-jsonInput` with `{"body":{...}}` wrapper + explicit `--project_id` |
| CreateNotebook | Param name `flavor_id` wrong | Use `--flavor` |
| CreateNotebook | Param name `volume.size` wrong | Use `--volume.capacity` |
| CreateNotebook | `ownership=PRIVATE` invalid | Use `MANAGED` or `DEDICATED` |
| AttachDynamicStorage | STOPPED instance rejected | Ensure instance is `RUNNING` |
| AttachDynamicStorage | `mount_path` format | Must start with `/data/` and end with `/` |
| RegisterImage | `arch` case mismatch | Use uppercase `X86_64`/`AARCH64` |
| RenewLease | `type` case mismatch | Use lowercase `timing`/`idle` |

> This step is **mandatory** for all write operations. Skipping it may result in CLI parameter errors or API failures that are already documented.

### Step 3: Handle Write Operations

For all write operations (Create/Update/Delete/Start/Stop/Attach/Detach/Register/Sync/Renew), **prompt the user for confirmation before execution**. For chargeable operations (CreateNotebook, StartNotebook), **inquire BSS pricing first** to inform the user of costs. See [references/pricing-inquiry.md](references/pricing-inquiry.md) for the pricing inquiry workflow.

> **删除类操作交互指引**：当用户请求删除标签（DeleteNotebookTags）、删除镜像分组（DeleteImageGroup）等操作但**未指定具体对象**时，必须先查询当前对象列表（如 `ShowNotebookTags` / `ListImageGroup`），向用户展示并确认要删除哪个对象，确认后再执行。避免因上下文不明确导致误删。

---

## KooCLI Command Format Standard

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Fixed: `ModelArts` | `ModelArts` |
| Operation name | PascalCase | `ListNotebooks`, `CreateNotebook` |
| Region parameter | `--cli-region={region}` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--id=xxx` |
| Indexed parameter | `--key.1=value1` | `--tags.1.key=env` |
| project_id | Auto-resolved if omitted | Uses configured project ID |

> **Note**: `--project_id` is auto-resolved from authentication credentials if omitted. Include it explicitly only when targeting a specific project.

---

## Core Commands

All 31 CLI command examples across 7 functional domains are documented in a separate reference file.

> **📖 For detailed command syntax, parameters, and examples, read [references/cli-command-examples.md](references/cli-command-examples.md)**

### Quick Index

| # | Domain | APIs | Key Operations |
|---|--------|------|----------------|
| 1 | Instance Management | 8 | CreateNotebook, ListNotebooks, ListAllNotebooks, ShowNotebook, UpdateNotebook, DeleteNotebook, StartNotebook, StopNotebook |
| 2 | Lease Management | 2 | ShowLease, RenewLease |
| 3 | Tag Management | 3 | ShowNotebookTags, CreateNotebookTags, DeleteNotebookTags |
| 4 | Image Management | 9 | CreateImage, ListImage, RegisterImage, ShowImage, DeleteImage, SyncImage, ListImageGroup, DeleteImageGroup, UpdateImageGroup |
| 5 | Flavor and Cluster | 4 | ListFlavors, ShowSwitchableFlavors, ListAuthoringClusters, ShowCluster |
| 6 | Feature Query | 1 | ListFeatures |
| 7 | Dynamic Storage | 4 | ListDynamicStorages, AttachDynamicStorage, ShowDynamicStorage, DetachDynamicStorage |

> When executing any command, always refer to the reference file for exact parameter names, required/optional flags, and usage patterns.

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{region}` | Yes | Huawei Cloud region | `cn-north-4`, `cn-east-3` |
| `{instance_id}` | Yes (most ops) | Notebook instance UUID | `xxx-xxx-xxx` |
| `{image_id}` | Create/List | Image UUID | `xxx-xxx-xxx` |
| `{flavor_id}` | Create | Flavor ID for instance | `modelarts.bm.4xlarge.pro` |
| `{resource_id}` | Tag ops | Resource ID for tagging | `xxx-xxx-xxx` |
| `{cluster_id}` | ShowCluster | Cluster ID | `xxx-xxx-xxx` |
| `{storage_id}` | Storage ops | Storage ID | `xxx-xxx-xxx` |
| `{feature}` | ListFeatures | Feature name | `NOTEBOOK` |
| `{project_id}` | No (auto) | Project ID, auto-resolved if omitted | Omit for default |

---

## SDK Fallback

If a CLI operation fails due to a CLI bug, fall back to SDK:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkmodelarts.v1.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v1.region.modelarts_region import ModelArtsRegion

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
| [references/cli-command-examples.md](references/cli-command-examples.md) | Detailed CLI command syntax and examples for all 31 APIs |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policies |
| [references/verification-method.md](references/verification-method.md) | Verification and testing methods |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
| [references/api-paths.md](references/api-paths.md) | REST API paths from SDK source |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation and authentication guide |
| [references/known-issues.md](references/known-issues.md) | Known issues and workarounds |
| [references/pricing-inquiry.md](references/pricing-inquiry.md) | BSS pricing inquiry guide for chargeable operations |

## Known Issues (Summary)

> Full details: [references/known-issues.md](references/known-issues.md)

| # | Issue | Key Takeaway |
|---|-------|--------------|
| 1 | CLI omits EVS from `volume.category` enum | Use `--cli-jsonInput` with `body` wrapper + explicit `--project_id` |
| 2 | Storage category × ownership matrix | EVS:MANAGED ✅, OBS/OBSFS:DEDICATED ✅, OBS/OBSFS:MANAGED ❌ |
| 3 | DEDICATED ownership requires `pool_id` | Query dedicated pools first, pass top-level `pool_id` |
| 4 | OBS as `data_volume` silently fails | Use OBS as main `volume` or use OBSFS as `data_volume` |
| 5 | Bucket type (POSIX vs OBJECT) irrelevant | Both work with DEDICATED ownership |
| 6 | OBSFS:MANAGED extended storage unsupported | Use DEDICATED for OBSFS |
| 7 | OBS/OBSFS main volume needs `dew_secret_name` | Store AK/SK in DEW/CSMS secret |
| 8 | OBS data volume requires `mount_path` | Always specify valid path |
| 9 | Image/flavor architecture mismatch | Match `arch` field between image and flavor |
| 10 | `--cli-jsonInput` general workaround | Must wrap in `{"body":{...}}` + pass `--project_id` explicitly |
| 11 | `ShowLease` duration is total, not remaining | Calculate: `remaining = (create_at + duration) - current_time` |
| 12 | `ListImageGroup` response field varies with `--limit` | Without limit: `groups` field; with limit: `data` field. Parse both |
| 13 | `AttachDynamicStorage` only supports POSIX buckets | OBJECT buckets rejected with `ModelArts.6772`; use `obsutil stat` to verify |

---

## Notes

- All 31 API interfaces are available via `hcloud ModelArts` CLI
- SDK fallback available via `huaweicloudsdkmodelarts` v1 if CLI encounters issues
- Region is specified via `--cli-region` and should NOT be hardcoded
- `--project_id` is auto-resolved from credentials if omitted (but **must be explicit** when using `--cli-jsonInput`)
- All write operations (Create/Update/Delete/Start/Stop/Attach/Detach/Register/Sync/Renew) require user confirmation before execution
- Chargeable operations (CreateNotebook, StartNotebook) require BSS pricing inquiry to inform users of costs before execution
- API paths verified from SDK source `_http_info` `resource_path` — no inferred endpoints
- No hardcoded AK/SK in any file — credentials managed by hcloud via `hcloud configure list/set`
