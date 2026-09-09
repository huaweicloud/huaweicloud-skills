# CLI Installation Guide CLI安装指南

## Installation 安装

### Prerequisites 前置条件

- Python 3.8+
- pip package manager
- CloudRobo Cloud account with AK/SK credentials

### Install cloudrobo CLI 安装 CloudRobo CLI

```bash
pip install hw-cloudrobo-client
```

`hw-cloudrobo-client` is a meta-package: it installs the core CLI framework, the workspace
command group, and all sub-packages via Python entry points. No separate installation of
individual packages is needed — a single `pip install` is sufficient.

## Configuration 配置

### Initialize user config 初始化用户配置

```bash
cloudrobo setup
```

This creates `~/.cloudrobo/` directory with default config.

### Set credentials 设置认证

```bash
export HUAWEI_CLOUD_AK="<your-ak>"
export HUAWEI_CLOUD_SK="<your-sk>"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="<your-ak>"
$env:HUAWEI_CLOUD_SK="<your-sk>"
```

Or edit `~/.cloudrobo/config.yaml`:

```yaml
cloudrobo:
  auth:
    ak: "<your-ak>"
    sk: "<your-sk>"
  region: cn-southwest-2
```

### Set default workspace 设置默认工作空间

```bash
cloudrobo workspace use --workspace-id <workspace-id>
```

This stores the default workspace in `~/.cloudrobo/workspace.json` with the following fields:
- `workspace_id` — UUID of the active workspace
- `name` — workspace name
- `asset_catalog_id` — asset catalog UUID (used by asset/dataset skills)
- `default_obs_path` — default OBS path (used by dataset/train skills)

## Verification 验证

```bash
# Check CLI is installed
cloudrobo --help

# Check workspace command group is registered
cloudrobo workspace --help

# Verify credentials are set
cloudrobo workspace list

# Verify workspace context is configured
cloudrobo workspace current
```

## Troubleshooting 故障排查

| Issue | Solution |
|-------|----------|
| `command not found: cloudrobo` | Reinstall: `pip install hw-cloudrobo-client` |
| `workspace command not found` | Reinstall: `pip install hw-cloudrobo-client` |
| `未配置工作空间` | Run `cloudrobo workspace use --workspace-id <id>` |
| `HTTP 401/403` | Check AK/SK credentials in environment or config |
| `HTTP 404` | Check service endpoint in `~/.cloudrobo/config.yaml` |
| SSL verification errors | Check CA certificates; set `CLOUDROBO_VERIFY_SSL=false` only for local debugging against trusted endpoints |
| `切换失败: ...` | Workspace ID is invalid or not accessible; verify with `workspace list` |

## Environment Variables 环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `HUAWEI_CLOUD_AK` | Access key ID | — |
| `HUAWEI_CLOUD_SK` | Secret access key | — |
| `CLOUDROBO_SERVICE_CONFIG` | Custom config file path | `~/.cloudrobo/config.yaml` |
| `CLOUDROBO_ENDPOINT_cloudrobo-service` | Override service endpoint | — |
| `CLOUDROBO_HTTP_PROXY` | HTTP proxy | — |
| `CLOUDROBO_HTTPS_PROXY` | HTTPS proxy | — |
| `CLOUDROBO_VERIFY_SSL` | SSL verification (true/false) | true |
| `CLOUDROBO_LOG_TRAFFIC` | Traffic logging (true/false) | false |
| `CLOUDROBO_DEBUG` | Verbose error output (1/0) | 0 |

> **⚠️ Security warning:** SSL/TLS certificate verification is **enabled by default**
> (`CLOUDROBO_VERIFY_SSL=true`). Do **not** disable it in production — setting it to
> `false` skips server certificate checks on all HTTPS requests and exposes your
> HMAC-SHA256-signed API requests to man-in-the-middle attacks. Only set
> `CLOUDROBO_VERIFY_SSL=false` when debugging against a trusted local endpoint.
