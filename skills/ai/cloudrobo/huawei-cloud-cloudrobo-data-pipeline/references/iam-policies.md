# IAM Policies 权限模型

> CloudRobo authenticates requests with APIG HMAC-SHA256 signing (AK/SK) and scopes
> resources by workspace. Sibling skills document server-side ABAC action names only for
> workspace and resource-pool operations; no action names are documented for asset or
> `dataset proc` / `dataset eval` operations. This document therefore lists the **backend
> access** each pipeline stage needs, and quotes action names only where a sibling skill
> documents them.

## Credential Model 认证模型

CloudRobo uses **APIG HMAC-SHA256 signing** with AK/SK credentials, not IAM role-based
policies. The signing implementation is in `cloudrobo_core.sdk.apig_sdk_auth`; every CLI
request is signed per request (no token refresh).

## Access Control Layers 访问控制层

### Layer 1: APIG Signing (Identity) 签名认证

- Only requests with valid AK/SK signatures reach the CloudRobo backend
- The AK/SK must belong to a Huawei Cloud account (or IAM user) authorized to use CloudRobo

### Layer 2: Workspace Isolation (Resource Scope) 工作空间隔离

- Dataset assets, proc tasks and eval tasks are scoped to a `workspace_id`
- The input dataset, every intermediate output asset, and all tasks of one pipeline run
  must belong to the same workspace
- `catalog_id` in create/import and in proc task_config is the workspace's
  `asset_catalog_id` (from `cloudrobo workspace current`), not the operator's catalog

## Least-Privilege Principle 最小权限原则

The AK/SK used for the data pipeline should have access **only** to the following:

| Resource | Operation | Endpoint |
|----------|-----------|----------|
| `cloudrobo-service` | Read `/v1/workspaces/*` | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-service` | Read/write `/v1/data-eng/proc-tasks/*` (conversion, cleaning) | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-service` | Read/write `/v1/data-eng/eval-tasks/*` (quality, diversity evaluation) | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-service` (dedicated pool only) | Read `/v1/resources/pools` | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-asset-manager` | Read `/v1/asset-service/publication-assets` (operator discovery) | `https://cloudrobo-gallery.{region}.myhuaweicloud.com` |
| `cloudrobo-asset-manager` | Read/write `/v1/assets/*` (dataset assets and versions) | `https://cloudrobo-gallery.{region}.myhuaweicloud.com` |
| `cloudrobo-obs` (`source_type: local` only) | Write to the workspace OBS path used by `import-asset` | `https://obs.{region}.myhuaweicloud.com` |

## Permissions by Pipeline Stage 分阶段权限

| Stage | CLI operations | Backend access | Access | Documented action (sibling skills) |
|-------|----------------|----------------|--------|------------------------------------|
| Pre-flight: workspace | `workspace list`, `workspace use --workspace-id <id>` | `cloudrobo-service` `GET /v1/workspaces`, `GET /v1/workspaces/{id}` | Read | `cloudrobo:workspace:list`, `cloudrobo:workspace:get` |
| Pre-flight: workspace | `workspace current` | Local file `~/.cloudrobo/workspace.json` (no request) | — | — |
| Pre-flight: resource pool (`DEDICATED_POOL` only) | `resource list-pools` | `cloudrobo-service` `GET /v1/resources/pools` | Read | `cloudrobo:resource:listPool` |
| Stage 1: existing asset (`source_type: asset`) | `asset list-assets`, `show-asset`, `list-versions`, `show-version` | `cloudrobo-asset-manager` `GET /v1/assets`, `/v1/assets/{id}`, `/v1/assets/{id}/versions[/{vid}]` | Read | Not documented |
| Stage 1: OBS path (`source_type: obs`) | `asset create-asset`, `create-version` | `cloudrobo-asset-manager` `POST /v1/assets`, `POST /v1/assets/{id}/versions` | Write | Not documented |
| Stage 1: local dir (`source_type: local`) | Asset Center skill → `asset import-asset` | `cloudrobo-asset-manager` (asset + version) and OBS transfer inside import-asset with the same AK/SK; no separate OBS CLI upload | Write | Not documented (asset); OBS: see [OBS Access](#obs-access-obs访问) |
| Stage 1 / handoff: publish | `asset update-version --status RELEASE` | `cloudrobo-asset-manager` `PUT /v1/assets/{id}/versions/{vid}` | Write | Not documented |
| Operator discovery (Steps 2.1 / 3.1 / 4.1) | `asset list-publication-assets` (preset); `asset list-assets` (workspace operators) | `cloudrobo-asset-manager` `GET /v1/asset-service/publication-assets`, `GET /v1/assets` | Read | Not documented |
| Stage 2 / 3: conversion, cleaning | `dataset proc create-task` | `cloudrobo-service` `POST /v1/data-eng/proc-tasks` | Write | Not documented |
| Stage 2 / 3: wait, output | `dataset proc wait-task`, `show-task`, `list-tasks` | `cloudrobo-service` `GET /v1/data-eng/proc-tasks[/{id}]` | Read | Not documented |
| Stage 2 / 3: diagnosis | `dataset proc get-log`, `download-log` | `cloudrobo-service` `GET /v1/data-eng/proc-tasks/{id}/logs[/...]` | Read | Not documented |
| Handoff 2→3, 3→4 | `asset list-versions`, `show-version` (+ optional `update-version`) | `cloudrobo-asset-manager` `/v1/assets/{id}/versions[/{vid}]` | Read (write if publishing) | Not documented |
| Stage 4: evaluation | `dataset eval create-task` | `cloudrobo-service` `POST /v1/data-eng/eval-tasks` | Write | Not documented |
| Stage 4: wait, report | `dataset eval wait-task`, `show-task`, `list-tasks`, `get-preview` | `cloudrobo-service` `GET /v1/data-eng/eval-tasks[/{id}]`, `GET /v1/data-eng/eval-tasks/{id}/preview` | Read | Not documented |
| Stage 4: diagnosis | `dataset eval get-log`, `download-log` | `cloudrobo-service` `GET /v1/data-eng/eval-tasks/{id}/logs[/...]` | Read | Not documented |
| Stage 5: summary | (no new requests; uses recorded IDs) | — | — | — |

> A query-only or verification run needs only the **Read** rows. The pipeline never calls
> `delete-task` or `update-task`; single-task maintenance belongs to the
> `huawei-cloud-cloudrobo-dataset` skill.

## OBS Access OBS访问

The pipeline references only `obs://` paths:

| Path | Used by | Needed access |
|------|---------|---------------|
| Raw data `obs_path` (`source_type: obs`) | Stage 1 `create-version --url`, then conversion `dataset_configs` | Readable by the conversion task |
| Upload target of `import-asset` (`source_type: local`) | Stage 1 | Writable by the user's AK/SK (the CLI uploads directly to OBS) |
| Operator `inputs[].url_path` (e.g. config mounts) | Conversion / cleaning / evaluation | Readable by the task |
| Eval config mount `inputs` (e.g. robots.yaml / URDF directory via `ROBOT_CONFIG_PATH`) | Evaluation | Readable by the task |
| Task outputs (`target_path`, `target_report_path`) | Conversion / cleaning / evaluation | Written by the task; read when previewing reports |

Sibling skills do not document OBS IAM action names or bucket-policy requirements for
CloudRobo tasks. Grant the AK/SK read/write access to the workspace OBS bucket paths above
according to your organization's OBS permission model, and confirm the exact OBS
permissions with your administrator before running the pipeline.

## Read-only vs Mutating Operations 只读与变更操作

| Type | Operations | Rule |
|------|------------|------|
| Read-only | `workspace current/list`, `asset list-publication-assets/list-assets/show-asset/list-versions/show-version`, `dataset proc\|eval list-tasks/show-task/wait-task/get-log/download-log`, `dataset eval get-preview`, `resource list-pools` | May run without confirmation |
| Mutating | `asset create-asset`, `asset create-version`, `asset import-asset`, `asset update-version`, `dataset proc create-task`, `dataset eval create-task` | Only after the user confirms the execution plan (SKILL.md "Execution Plan Confirmation") |
| Local config | `config set`, `workspace use` | Run by the user (credentials are never handled by the agent) |

## Credential Configuration 认证配置

See [CLI Installation Guide](cli-installation-guide.md). In short:

```bash
cloudrobo config set ak <your-ak> sk <your-sk>   # encrypted storage in ~/.cloudrobo/config.yaml
# or
export HUAWEI_CLOUD_AK="<your-ak>"
export HUAWEI_CLOUD_SK="<your-sk>"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="<your-ak>"
$env:HUAWEI_CLOUD_SK="<your-sk>"
```

Environment variables take precedence over values stored by `cloudrobo config set`.

## Security Notes 安全说明

- **No hardcoding** — AK/SK are never written into `pipeline.yaml`, task_config, the
  checkpoint file, the pipeline summary, scripts, or documents, and never pasted into chat
- **Signing mechanism** — APIG HMAC-SHA256 signs each request with a timestamp to prevent
  replay attacks
- **Workspace scope** — keep all assets and tasks of a run in one workspace to contain the
  blast radius
- **Confirmation gate** — every mutating operation runs only after plan confirmation
- **`obs://` only** — no other object-storage schemes or public URLs as inputs
- **Report links** — `get-preview` returns temporary OBS links; do not publish them
- **SSL verification** — can be disabled for debugging (`CLOUDROBO_VERIFY_SSL=false`) but
  should be enabled in production
- **Traffic logging** — `CLOUDROBO_LOG_TRAFFIC=true` enables request/response logging for
  debugging; disable in production to avoid credential leakage in logs

## Comparison with Huawei Cloud IAM 与华为云IAM对比

| Aspect | CloudRobo | Huawei Cloud IAM |
|--------|-----------|------------------|
| Auth method | AK/SK HMAC-SHA256 signing | IAM token / AK/SK signing |
| Policy model | Endpoint-level access + workspace scope | Fine-grained RBAC policies |
| Scope | Service endpoint / workspace | Resource-level |
| Management | Cloud console / CLI config | IAM console / CLI |
