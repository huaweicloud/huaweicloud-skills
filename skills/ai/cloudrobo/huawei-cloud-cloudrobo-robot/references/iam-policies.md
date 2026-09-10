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

- All robots are scoped to a `workspace_id`
- A robot created in workspace A is invisible to workspace B
- The certificate and SDK access are bound to the robot's owning workspace

### Minimal Access for robot skill

| Capability | Required Permission |
| ----------- | ------------------- |
| Query robots | Read access to `cloudrobo-service` (`GET /v1/robots`) |
| Create robot | Write access to `cloudrobo-service` (`POST /v1/robots`) |
| Show robot detail | Read access to `cloudrobo-service` (`GET /v1/robots/{robot_id}`) |
| Update robot | Write access to `cloudrobo-service` (`PUT /v1/robots/{robot_id}`) |
| Delete robot | Delete access to `cloudrobo-service` (`DELETE /v1/robots/{robot_id}`) |
| Export certificate | Write access to `cloudrobo-service` (`POST /v1/robots/{robot_id}/certificate/export`) |
| Query SDK info | Read access to `cloudrobo-service` (`GET /v1/robots/sdk`) |

## Service Endpoints

```yaml
# From cloudrobo-core config.yaml
endpoints:
  cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
  cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
```

| Service | Used For | API Prefix |
| --------- | ---------- | ----------- |
| `cloudrobo-service` | robot CRUD, certificate export, SDK query | `/v1/robots/` |

Robot operations use only the `cloudrobo-service` backend. Asset queries for cross-module
workflows (e.g., listing a model before an infer deployment) use `cloudrobo-asset-manager`.

## Security Constraints

- **No hardcoded credentials**: AK/SK must come from environment variables or `~/.cloudrobo/config.yaml` (never in scripts or SKILL.md)
- **No credential logging**: The HttpClient masks AK/SK in traffic logs
- **Workspace boundary**: A robot and its certificate are bound to one workspace
- **Write operations require user confirmation**: Create / Update / Delete / Export-certificate must prompt user before execution
- **Certificate password is sensitive**: Never log password; mask in traffic/debug output
- **Path traversal protection**: `robot_id` / resource IDs pass through `validate_safe_id` to prevent path traversal
- **Irreversible operations**: Robot deletion is irreversible; always confirm robot_id before delete

## Environment Variable Reference

| Variable | Overrides | Purpose |
| ---------- | ----------- | --------- |
| `HUAWEI_CLOUD_AK` | `cloudrobo.auth.ak` | Access key for signing |
| `HUAWEI_CLOUD_SK` | `cloudrobo.auth.sk` | Secret key for signing |
| `CLOUDROBO_ENDPOINT_CLOUDROBO-SERVICE` | endpoints | Override service endpoint |
| `CLOUDROBO_VERIFY_SSL` | `debug.verify_ssl` | SSL verification toggle |
| `CLOUDROBO_LOG_TRAFFIC` | `debug.log_traffic` | Traffic logging toggle |
