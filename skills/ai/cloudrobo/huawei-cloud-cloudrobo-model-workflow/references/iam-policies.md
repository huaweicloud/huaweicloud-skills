# Authentication & Access Control — CloudRobo Model Workflow

> CloudRobo does not use Huawei Cloud IAM tokens or IAM policy JSON; it uses APIG
> HMAC-SHA256 request signing with AK/SK credentials, plus workspace-based resource
> isolation. There are no `cloudrobo:*` IAM actions — access control is enforced by
> APIG signing (identity) and workspace scoping (resource scope).

## Authentication Model

CloudRobo authenticates requests via **APIG (API Gateway) SDK-HMAC-SHA256 signing**, not IAM tokens.

| Aspect | CloudRobo | Huawei Cloud Official (for contrast) |
| -------- | ----------- | -------------------------------------- |
| Auth method | APIG HMAC-SHA256 signing | IAM Token / BasicCredentials |
| Credentials | AK/SK (Huawei Cloud) | AK/SK + Project ID |
| Signing scope | Per-request signature | SDK-managed credentials |
| Token refresh | None (signature per request) | Token expires, needs refresh |

## Required Credentials

```bash
# Environment variables (preferred, never hardcode)
export HUAWEI_CLOUD_AK="your-access-key"
export HUAWEI_CLOUD_SK="your-secret-key"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="your-access-key"
$env:HUAWEI_CLOUD_SK="your-secret-key"
```

The `ApigSdkSigner` (in `cloudrobo_core.sdk.apig_sdk_auth`) signs each HTTP request.

## Access Control Layers

CloudRobo does not define IAM policy JSON. Access control is enforced at two layers:

### Layer 1: APIG Signing (Identity)

- Only requests with valid AK/SK signatures reach the CloudRobo backend
- AK/SK must correspond to a Huawei Cloud account authorized to access CloudRobo

### Layer 2: Workspace Isolation (Resource Scope)

- Assets, training tasks, inference services, pools, robots, and dispatch tasks are all
  scoped to a `workspace_id`
- Resources created in workspace A are invisible to workspace B
- The model asset, training output, and inference service used in the pipeline must
  belong to the same workspace

## Minimal Access by Pipeline Stage

| Stage | Operations | Backend Access |
|-------|-----------|----------------|
| Stage 0-1: Asset Query | `asset search-assets`, `asset show-asset`, `asset list-publication-assets` | Read access to `cloudrobo-asset-manager` |
| Stage 1: Dataset Processing | `asset create-asset`, `asset create-version`, `asset update-version`, `asset import-asset` | Write access to `cloudrobo-asset-manager` |
| Stage 1: Workspace | `workspace current`, `workspace use` | Read access to `cloudrobo-service` (`/v1/workspaces`) |
| Stage 2: Training | `train create-task`, `train show-task`, `train get-stages`, `train get-events` | Read/write access to `cloudrobo-service` training endpoints |
| Stage 3: Inference | `infer create`, `infer show`, `infer start`, `infer list`, `infer list-logs` | Read/write access to `cloudrobo-service` (`/v1/infer-services`) |
| Stage 3: Resource Pool | `resource list-pools`, `resource show-pool` | Read access to `cloudrobo-service` (`/v1/resources`) |
| Stage 4: Robot | `robot list` | Read access to `cloudrobo-service` (`/v1/robots`) |
| Stage 4: Dispatch | `dispatch create-task`, `dispatch show-task`, `dispatch list-tasks`, `dispatch show-task-result`, `dispatch cancel-task` | Read/write access to `cloudrobo-service` dispatch endpoints |

## Least Privilege Principle

- Only run the pipeline stages the user actually needs — a query-only workflow touches
  only read endpoints
- Write operations (asset create/import, train create-task, infer create/start, dispatch
  create-task/cancel-task) require explicit user confirmation before execution
- AK/SK must come from environment variables or `~/.cloudrobo/config.yaml` — never hardcode
- Keep all pipeline resources within a single workspace to keep the blast radius contained
