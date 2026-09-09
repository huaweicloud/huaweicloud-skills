# Authentication & Access Control

> Adapted from the official `iam-policies.md` requirement. CloudRobo does not use Huawei Cloud IAM tokens; it uses APIG HMAC-SHA256 request signing with AK/SK credentials, plus workspace-based resource isolation.

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

The `ApigSdkSigner` (in `cloudrobo_core.sdk.apig_sdk_auth`) signs each HTTP request:

- Canonical request construction (method / URI / headers / body hash)
- String-to-sign with HMAC-SHA256 using SK
- `Authorization` header: `SDK-HMAC-SHA256 Access=..., SignedHeaders=..., Signature=...`

## Least-Privilege Model

CloudRobo does not define IAM policy JSON. Access control is enforced at two layers:

### Layer 1: APIG Signing (Identity)

- Only requests with valid AK/SK signatures reach the CloudRobo backend
- AK/SK must correspond to a Huawei Cloud account authorized to access CloudRobo

### Layer 2: Workspace Isolation (Resource Scope)

- All resources (algorithms, datasets, models, training tasks, SimRL tasks) are scoped to a `workspace_id`
- A training task created in workspace A is invisible to workspace B
- Base model and dataset assets must belong to the same workspace

### Minimal Access for train skill

| Capability | Required Permission |
| ----------- | ------------------- |
| Query built-in algorithms | Read access to publication assets |
| Query custom algorithms / datasets / models | Read access to workspace assets |
| Create / stop / restart / resume train-tasks | Write access to `cloudrobo-service` (`/v1/training/train-tasks`) |
| Save draft (train / SimRL) | Write access to `cloudrobo-service` (`/v1/training/train-tasks/draft`, `/v1/training/rl-tasks/simulation/draft`) |
| Update task name/description | Write access to `cloudrobo-service` (`PATCH /v1/training/train-tasks/{id}`, `PATCH /v1/training/rl-tasks/simulation/{id}`) |
| Batch delete train-tasks | Delete access to `cloudrobo-service` (`POST /v1/training/train-tasks/batch-delete`) |
| Delete SimRL task | Delete access to `cloudrobo-service` (`DELETE /v1/training/rl-tasks/simulation/{id}`) |
| View stages / resource-usage / events / logs / signed-url | Read access to task sub-resources |
| Count tasks by status | Read access to `cloudrobo-service` (`/v1/training/train-tasks/stats`, `/v1/training/rl-tasks/simulation/stats`) |
| Checkpoint management (list/register) | Read/Write access to `cloudrobo-service` (`/v1/training/train-tasks/{id}/checkpoints`) |
| SimRL task lifecycle (create/stop/restart/clone) | Write access to `cloudrobo-service` (`/v1/training/rl-tasks/simulation`) |
| Export output model | Read access to `cloudrobo-asset-manager` (model assets) |

## Service Endpoints

```yaml
# From cloudrobo-core config.yaml
endpoints:
  cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
  cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
```

| Service | Used For | API Prefix |
| --------- | ---------- | ----------- |
| `cloudrobo-service` | train-tasks, SimRL tasks, stages, events, logs, resource-usage, stats, resume, batch-delete, checkpoints | `/v1/training/` |
| `cloudrobo-asset-manager` | algorithms, datasets, models, asset download | `/v1/asset/` |

## Security Constraints

- **No hardcoded credentials**: AK/SK must come from environment variables or `~/.cloudrobo/config.yaml` (never in scripts or SKILL.md)
- **No credential logging**: The HttpClient masks AK/SK in traffic logs
- **Workspace boundary**: Base model, dataset, and training task must be in the same workspace
- **Write operations require user confirmation**: Create / Stop / Restart / Delete / Save-draft / Update / Resume must prompt user before execution (Clone is SimRL-only)
- **Irreversible operations**: Task deletion is irreversible; always confirm task IDs before delete
- **Resource consumption awareness**: Training tasks consume compute (Ascend NPU) resources; always confirm before creating long-running tasks

## Environment Variable Reference

| Variable | Overrides | Purpose |
| ---------- | ----------- | --------- |
| `HUAWEI_CLOUD_AK` | `cloudrobo.auth.ak` | Access key for signing |
| `HUAWEI_CLOUD_SK` | `cloudrobo.auth.sk` | Secret key for signing |
| `CLOUDROBO_ENDPOINT_CLOUDROBO-SERVICE` | endpoints | Override service endpoint |
| `CLOUDROBO_VERIFY_SSL` | `debug.verify_ssl` | SSL verification toggle |
| `CLOUDROBO_LOG_TRAFFIC` | `debug.log_traffic` | Traffic logging toggle |
