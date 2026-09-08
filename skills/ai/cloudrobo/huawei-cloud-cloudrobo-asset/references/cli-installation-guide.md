# CLI Installation Guide CLI安装指南

## Installation 安装

### Prerequisites 前置条件

- Python 3.8+
- pip package manager
- CloudRobo Cloud account with AK/SK credentials

### Install cloudrobo-core (CLI framework) 安装核心包

```bash
pip install hw-cloudrobo-client
```

This provides the `cloudrobo` main CLI entry point.

### Install cloudrobo-asset (asset commands) 安装资产包

```bash
pip install hw-cloudrobo-client
```

This registers the `asset` command group via entry points.

### Install all packages (recommended) 安装全部包

```bash
pip install hw-cloudrobo-client
```

The root `pyproject.toml` (`cloudrobo-client`) installs all sub-packages.

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

### Configure OBS endpoint (for import/export) 配置OBS端点

Import/export operations require the `cloudrobo-obs` endpoint. Verify configuration:

```bash
cloudrobo config show | grep obs
```

```powershell
# PowerShell
cloudrobo config show | Select-String obs
```

If not configured or DNS is unreachable, confirm the correct OBS endpoint with the user. Do not
guess the endpoint.

Set via environment variable:

```bash
export CLOUDROBO_ENDPOINT_cloudrobo-obs="https://obs.<region>.myhuaweicloud.com"
```

Or in config:

```yaml
cloudrobo:
  endpoints:
    cloudrobo-asset-manager: "https://cloudrobo-gallery.{region}.myhuaweicloud.com"
    cloudrobo-obs: "https://obs.{region}.myhuaweicloud.com"
```

## Verification 验证

```bash
# Check CLI is installed
cloudrobo --help

# Check asset command group is registered
cloudrobo asset --help

# Verify credentials are set
cloudrobo asset list-repositories
```

## Troubleshooting 故障排查

| Issue | Solution |
|-------|----------|
| `command not found: cloudrobo` | Reinstall: `pip install hw-cloudrobo-client` |
| `asset command not found` | Reinstall: `pip install hw-cloudrobo-client` |
| `HTTP 401/403` | Check AK/SK credentials in environment or config |
| `HTTP 404` | Check service endpoint in `~/.cloudrobo/config.yaml` |
| `OBS upload failed` | Check `cloudrobo-obs` endpoint configuration and DNS reachability |
| `FileNotFoundError` | `import-asset` requires `local_path` to exist |
| `No versions found` | `export-asset` requires at least one version |
| SSL verification errors | Set `CLOUDROBO_VERIFY_SSL=false` (debug only) |

## Environment Variables 环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `HUAWEI_CLOUD_AK` | Access key ID | — |
| `HUAWEI_CLOUD_SK` | Secret access key | — |
| `CLOUDROBO_SERVICE_CONFIG` | Custom config file path | `~/.cloudrobo/config.yaml` |
| `CLOUDROBO_ENDPOINT_cloudrobo-asset-manager` | Override asset service endpoint | — |
| `CLOUDROBO_ENDPOINT_cloudrobo-obs` | Override OBS endpoint (import/export) | — |
| `CLOUDROBO_HTTP_PROXY` | HTTP proxy | — |
| `CLOUDROBO_HTTPS_PROXY` | HTTPS proxy | — |
| `CLOUDROBO_VERIFY_SSL` | SSL verification (true/false) | false |
| `CLOUDROBO_LOG_TRAFFIC` | Traffic logging (true/false) | false |
| `CLOUDROBO_DEBUG` | Verbose error output (1/0) | 0 |
