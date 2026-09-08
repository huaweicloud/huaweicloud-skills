# IAM Policies 权限模型

## Credential Model 认证模型

CloudRobo uses **APIG HMAC-SHA256 signing** with AK/SK credentials, not IAM role-based
policies. The signing implementation is in
`cloudrobo_core.sdk.apig_sdk_auth`.

## Least-Privilege Principle 最小权限原则

The AK/SK used for resource operations should have access **only** to the following:

| Resource | Operation | Endpoint |
|----------|-----------|----------|
| `cloudrobo-service` | Read access to `/v1/resources/quotas` | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-service` | Read access to `/v1/resources/pools` | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-service` | Read access to `/v1/resources/pools/{pool_id}` | `https://cloudrobo.{region}.myhuaweicloud.com` |

## Required Endpoints 必需端点

```yaml
cloudrobo:
  endpoints:
    cloudrobo-service: "https://cloudrobo.{region}.myhuaweicloud.com"
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

## Server-Side Auth Model 服务端认证模型

The common-server uses Huawei Wushan framework for authentication:

- `@EnableAuth` on controllers + `@IamAuthMetaV5` per method
- **Domain-level operations** (quota list, pool list, pool show): `authLevel = IamAuthLevel.NO_INSTANCE`,
  `authContextInitializer = DomainIamAuthContextInitializer`
- **ABAC-protected operations**: quota list and pool list require ABAC resource check
- **Pool detail**: Domain-level auth only, **no ABAC** required
- `@CtsLog` records CTS audit logs for all operations

### ABAC Actions 权限动作

| Action | Description | Applicable Operations |
|--------|-------------|----------------------|
| `cloudrobo:resource:listQuota` | List quotas | `list-quotas` |
| `cloudrobo:resource:listPool` | List resource pools | `list-pools` |

### ABAC vs No-ABAC Classification ABAC校验分类

| Operation | ABAC Required | Auth Level |
|-----------|---------------|------------|
| Quota list (`list-quotas`) | Yes | Domain-level |
| Resource pool list (`list-pools`) | Yes | Domain-level |
| Resource pool detail (`show-pool`) | **No** | Domain-level only |

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
