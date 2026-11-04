# IAM Policies 权限模型

## Credential Model 认证模型

CloudRobo uses **APIG HMAC-SHA256 signing** with AK/SK credentials, not IAM role-based
policies. The signing implementation is in
`cloudrobo_core.sdk.apig_sdk_auth`.

## Least-Privilege Principle 最小权限原则

The AK/SK used for dataset operations should have access **only** to the following:

| Resource | Operation | Endpoint |
|----------|-----------|----------|
| `cloudrobo-service` | Full access to `/v1/data-eng/proc-tasks/*` | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-asset-manager` (optional) | Read-only access to publication assets (for algorithm discovery) | `https://cloudrobo-gallery.{region}.myhuaweicloud.com` |
| `cloudrobo-asset-manager` (custom-operator onboarding — write) | Create assets: `POST /v1/assets` (type=image + type=algorithm + type=dataset); Get asset: `GET /v1/assets/{id}`; Update asset: `PUT /v1/assets/{id}`; Create version: `POST /v1/assets/{id}/versions` | `https://cloudrobo-gallery.{region}.myhuaweicloud.com` |
| SWR (custom-operator Mode A image push) | docker login, docker build, docker push (image upload) — **Mode A only** | `swr.{region}.myhuaweicloud.com` |
| OBS (custom-operator Mode B `code_dir` / Source ① data upload) | **Read + write** to the workspace-bound bucket: the customer uploads the code themselves, or the skill uploads the generated files on the customer's choice; the platform reads it at runtime | reachable OBS endpoint (e.g. `obs.cn-southwest-2.myhuaweicloud.com`; the default `obs.{region}.myhuaweicloud.com` may not resolve) |

## Required Endpoints 必需端点

```yaml
cloudrobo:
  endpoints:
    cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
    cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
    swr: "swr.{region}.myhuaweicloud.com"          # custom-operator Mode A only
    cloudrobo-obs: "https://obs.{region}.myhuaweicloud.com"  # optional, Mode B code_dir / dataset upload
```

## Credential Configuration 认证配置

### Environment Variables (Recommended)

```bash
export HUAWEI_CLOUD_AK="<your-ak>"
export HUAWEI_CLOUD_SK="<your-sk>"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="<your-ak>"
$env:HUAWEI_CLOUD_SK="<your-sk>"
```

### Config File 配置文件

`~/.cloudrobo/config.yaml`:

```yaml
cloudrobo:
  auth:
    ak: "<your-ak>"
    sk: "<your-sk>"
```

## Security Notes 安全说明

- **No hardcoding** — AK/SK must be read from environment variables or config file, never
  hardcoded in scripts or documents
- **Signing mechanism** — APIG HMAC-SHA256 signs each request with a timestamp to prevent
  replay attacks
- **Proxy support** — Optional HTTP/HTTPS proxy can be configured for network isolation
- **SSL verification** — Can be disabled for debugging (`CLOUDROBO_VERIFY_SSL=false`) but
  should be enabled in production
- **Traffic logging** — `CLOUDROBO_LOG_TRAFFIC=true` enables request/response logging for
  debugging; disable in production to avoid credential leakage in logs
- **Credential renewal (custom-operator)** — AK/SK expire or get revoked over time. When
  the customer has never configured AK/SK, or an API returns `401` / docker login returns
  `unauthorized`, the skill **proactively reminds the customer to configure / update the
  AK/SK** (regenerate in IAM, refresh `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` or
  `~/.cloudrobo/config.yaml`) — never continue silently with stale credentials
- **docker logout (custom-operator)** — After SWR push, run
  `docker logout swr.{region}.myhuaweicloud.com` to clear credentials from the local
  Docker config
- **Work copy security (custom-operator)** — The work copy (`/tmp/custom-operator-work-*`)
  contains adapted operator code (may include sensitive logic). In production, set
  `workdir_retention=false` to auto-clean; file permission `~/.cloudrobo/config.yaml` must
  be `600` (owner read/write only)

## Endpoint Override 端点覆盖

For non-default regions or private endpoints:

```bash
export CLOUDROBO_ENDPOINT_cloudrobo-service="https://cloudrobo.cn-southwest-2.myhuaweicloud.com"
```

Or in config:

```yaml
cloudrobo:
  endpoints:
    cloudrobo-service: "https://cloudrobo.cn-southwest-2.myhuaweicloud.com"
```

## Comparison with Huawei Cloud IAM 与华为云IAM对比

| Aspect | CloudRobo | Huawei Cloud IAM |
|--------|-----------|------------------|
| Auth method | AK/SK HMAC-SHA256 signing | IAM token / AK/SK signing |
| Policy model | Endpoint-level access control | Fine-grained RBAC policies |
| Scope | Service endpoint | Resource-level (ARN) |
| Management | Cloud console / config file | IAM console / CLI |
