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

## Required Endpoints 必需端点

```yaml
cloudrobo:
  endpoints:
    cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
    cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
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
