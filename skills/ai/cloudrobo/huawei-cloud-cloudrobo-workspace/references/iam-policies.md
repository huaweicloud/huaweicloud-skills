# IAM Policies 权限模型

## Credential Model 认证模型

CloudRobo uses **APIG HMAC-SHA256 signing** with AK/SK credentials, not IAM role-based
policies. The signing implementation is in
`cloudrobo_core.sdk.apig_sdk_auth`.

## Least-Privilege Principle 最小权限原则

The AK/SK used for workspace operations should have access **only** to the following:

| Resource | Operation | Endpoint |
|----------|-----------|----------|
| `cloudrobo-service` | Full access to `/v1/workspaces/*` | `https://cloudrobo.{region}.myhuaweicloud.com` |

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

## Server-Side Auth Model (Wushan) 服务端认证模型

The common-server uses Huawei Wushan framework for authentication:

- `@EnableAuth` on controllers + `@IamAuthMetaV5` per method
- **Domain-level operations** (create, list, overview): `authLevel = IamAuthLevel.NO_INSTANCE`,
  `authContextInitializer = DomainIamAuthContextInitializer`
- **Workspace-level operations** (show, update, delete, member CRUD):
  `authLevel = IamAuthLevel.INSTANCE`, `needAbacResourceCheck = true`,
  `authContextInitializer = WorkspaceIamAuthContextInitializer`
- ABAC actions are constants in `constant/ActionConstant.java`
- `@CtsLog` records CTS audit logs for all operations
- `@BetaTagCheck` / `CloudRoboAuth` for beta gating and access control

### ABAC Actions 权限动作

| Action | Description |
|--------|-------------|
| `cloudrobo:workspace:create` | Create workspace |
| `cloudrobo:workspace:get` | Show workspace |
| `cloudrobo:workspace:list` | List workspaces |
| `cloudrobo:workspace:update` | Update workspace |
| `cloudrobo:workspace:delete` | Delete workspace |
| `cloudrobo:workspace:createMember` | Add workspace member |
| `cloudrobo:workspace:listMember` | List workspace members |
| `cloudrobo:workspace:updateMember` | Update workspace member |
| `cloudrobo:workspace:deleteMember` | Delete workspace member |
| `cloudrobo:workspace:showOverview` | Show workspace overview |

### Additional Server-Side Checks 服务端额外校验

- **Frozen check**: `authService.checkUserAndSkuFrozen()` before workspace creation
- **Ownership check**: Only root user or workspace owner can delete
- **Default workspace protection**: Cannot delete or modify members of default workspace
- **Member validation**: Root users cannot be added as members; owner cannot be deleted/updated

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
- **workspace.json permissions** — File created with `0o600` (owner read/write only)

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
