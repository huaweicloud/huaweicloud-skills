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

---

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Huawei Cloud AK/SK** configured via hcloud or environment variables
3. **ModelArts service** enabled in the target region
4. **IAM permissions** — See [references/iam-policies.md](references/iam-policies.md)

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

### Step 3: Handle Write Operations

For all write operations (Create/Update/Delete/Start/Stop/Attach/Detach/Register/Sync/Renew), **prompt the user for confirmation before execution**.

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
- `--project_id` is auto-resolved from credentials if omitted
- All write operations (Create/Update/Delete/Start/Stop/Attach/Detach/Register/Sync/Renew) require user confirmation before execution
- API paths verified from SDK source `_http_info` `resource_path` — no inferred endpoints
