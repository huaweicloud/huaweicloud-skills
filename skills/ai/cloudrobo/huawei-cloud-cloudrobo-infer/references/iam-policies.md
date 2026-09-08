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

### Layer 2: Workspace Isolation (Resource Scope)

- All inference services are scoped to a `workspace_id`
- A service created in workspace A is invisible to workspace B
- The deployed model must belong to the same workspace

### Minimal Access for infer skill

| Capability | Required Permission |
| ----------- | ------------------- |
| List inference services | Read access to `cloudrobo-service` (`GET /v1/infer-services`) |
| Create service | Write access to `cloudrobo-service` (`POST /v1/infer-services`) |
| Show service detail | Read access to `cloudrobo-service` (`GET /v1/infer-services/{service_id}`) |
| Update service | Write access to `cloudrobo-service` (`PUT /v1/infer-services/{service_id}`) |
| Delete service | Delete access to `cloudrobo-service` (`DELETE /v1/infer-services/{service_id}`) |
| Start / stop service | Write access to `cloudrobo-service` (`POST /v1/infer-services/{service_id}/start`, `.../stop`) |
| List service logs | Read access to `cloudrobo-service` (`POST /v1/infer-services/{service_id}/logs`) |
| Query model asset (deploy source) | Read access to `cloudrobo-asset-manager` model assets |

## Service Endpoints

```yaml
# From cloudrobo-core config.yaml
endpoints:
  cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
  cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
```

| Service | Used For | API Prefix |
| --------- | ---------- | ----------- |
| `cloudrobo-service` | inference service CRUD, start/stop, logs | `/v1/infer-services/` |
| `cloudrobo-asset-manager` | model asset lookup (deploy source) | `/v1/asset/` |

## Security Constraints

- **No hardcoded credentials**: AK/SK must come from environment variables or `~/.cloudrobo/config.yaml`
- **No credential logging**: The HttpClient masks AK/SK in traffic logs
- **Workspace boundary**: model asset and inference service must be in the same workspace
- **Write operations require user confirmation**: Create / Start / Stop / Update / Delete
- **Compute consumption awareness**: Deploying/starting a service consumes pool compute — confirm before executing
- **Sensitive env masking**: `envs`/`cmd`/service-invoke may contain secrets; mask in runbooks
- **Internet access OFF by default**: only enable via `internet_access_enable` with explicit user consent
- **Path traversal protection**: `service_id` passes through `validate_safe_id`
- **Irreversible operations**: Service deletion is irreversible; confirm `service_id`

## Environment Variable Reference

| Variable | Overrides | Purpose |
| ---------- | ----------- | --------- |
| `HUAWEI_CLOUD_AK` | `cloudrobo.auth.ak` | Access key for signing |
| `HUAWEI_CLOUD_SK` | `cloudrobo.auth.sk` | Secret key for signing |
| `CLOUDROBO_ENDPOINT_CLOUDROBO-SERVICE` | endpoints | Override service endpoint |
| `CLOUDROBO_VERIFY_SSL` | `debug.verify_ssl` | SSL verification toggle |
| `CLOUDROBO_LOG_TRAFFIC` | `debug.log_traffic` | Traffic logging toggle |
