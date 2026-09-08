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

The `ApigSdkSigner` (in `cloudrobo_core.sdk.apig_sdk_auth`) signs each HTTP request.

## Least-Privilege Model

CloudRobo does not define IAM policy JSON. Access control is enforced at two layers:

### Layer 1: APIG Signing (Identity)

- Only requests with valid AK/SK signatures reach the CloudRobo backend
- AK/SK must correspond to a Huawei Cloud account authorized to access CloudRobo

### Layer 2: Workspace / Session Isolation (Resource Scope)

- Dispatch tasks are scoped to a `workspace_id` and organised under a `session_id`
- A task created in one session/workspace is invisible to another
- The robot and exec model referenced by a task must be valid within the same workspace

### Minimal Access for dispatch skill

| Capability | Required Permission |
| ----------- | ------------------- |
| Create dispatch task | Write access to `cloudrobo-service` (`POST /v1/robo-dispatcher/sessions/{session_id}/tasks`) |
| List tasks | Read access to `cloudrobo-service` (`GET /v1/robo-dispatcher/sessions/{session_id}/tasks`) |
| Show task | Read access to `cloudrobo-service` (`GET /v1/robo-dispatcher/sessions/{session_id}/tasks/{task_id}`) |
| Wait for task (`wait-task`) | Same read access as show-task — `wait-task` is a client-side polling helper that repeatedly `GET`s the task (`GET /v1/robo-dispatcher/sessions/{session_id}/tasks/{task_id}`); no additional permission |
| Cancel task | Write access to `cloudrobo-service` (`DELETE /v1/robo-dispatcher/sessions/{session_id}/tasks/{task_id}`) |
| Show task result | Read access to `cloudrobo-service` (`GET /v1/robo-dispatcher/sessions/{session_id}/tasks/{task_id}/result`) |
| Resolve robot (cross) | Read access to `cloudrobo-service` robot list/show |
| Resolve exec model (cross) | Read access to `cloudrobo-asset-manager` / infer service |

## Service Endpoints

```yaml
# From cloudrobo-core config.yaml
endpoints:
  cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
  cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
```

| Service | Used For | API Prefix |
| --------- | ---------- | ----------- |
| `cloudrobo-service` | dispatch task CRUD, cancel, result | `/v1/robo-dispatcher/` |
| `cloudrobo-asset-manager` | model asset lookup (exec model) | `/v1/asset/` |

## Security Constraints

- **No hardcoded credentials**: AK/SK must come from environment variables or `~/.cloudrobo/config.yaml`
- **No credential logging**: The HttpClient masks AK/SK in traffic logs
- **Session/workspace boundary**: tasks are isolated per session/workspace
- **Write operations require user confirmation**: Create-task / Cancel-task
- **Natural-language task injection protection**: sanitize/escape task content; do not echo raw content into logs unescaped
- **Path traversal protection**: `session_id`/`task_id` pass through `validate_safe_id`
- **Irreversible / side-effecting operations**: Creating a task triggers real robot action; cancelling may abort an in-flight task — always confirm

## Environment Variable Reference

| Variable | Overrides | Purpose |
| ---------- | ----------- | --------- |
| `HUAWEI_CLOUD_AK` | `cloudrobo.auth.ak` | Access key for signing |
| `HUAWEI_CLOUD_SK` | `cloudrobo.auth.sk` | Secret key for signing |
| `CLOUDROBO_ENDPOINT_CLOUDROBO-SERVICE` | endpoints | Override service endpoint |
| `CLOUDROBO_VERIFY_SSL` | `debug.verify_ssl` | SSL verification toggle |
| `CLOUDROBO_LOG_TRAFFIC` | `debug.log_traffic` | Traffic logging toggle |
