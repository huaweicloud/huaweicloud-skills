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

### Install cloudrobo-dataset (dataset commands) 安装数据集包

```bash
pip install hw-cloudrobo-client
```

This registers the `dataset` command group via entry points.

### Install cloudrobo-asset (algorithm discovery, optional) 安装资产包

```bash
pip install hw-cloudrobo-client
```

Required for `list-algorithms` (cross-package algorithm discovery).

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

### Set default workspace 设置默认工作空间

```bash
cloudrobo workspace use --workspace-id <workspace-id>
```

This stores the default workspace in `~/.cloudrobo/workspace.json`.

## Verification 验证

```bash
# Check CLI is installed
cloudrobo --help

# Check dataset command group is registered
cloudrobo dataset --help

# Verify credentials are set
cloudrobo dataset proc list-tasks
```

## Troubleshooting 故障排查

| Issue | Solution |
|-------|----------|
| `command not found: cloudrobo` | Reinstall: `pip install hw-cloudrobo-client` |
| `dataset command not found` | Reinstall: `pip install hw-cloudrobo-client` |
| `缺少 workspace_id 参数` | Run `cloudrobo workspace use --workspace-id <id>` |
| `HTTP 401/403` | Check AK/SK credentials in environment or config |
| `HTTP 404` | Check service endpoint in `~/.cloudrobo/config.yaml` |
| SSL verification errors | Set `CLOUDROBO_VERIFY_SSL=false` (debug only) |

## Environment Variables 环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `HUAWEI_CLOUD_AK` | Access key ID | — |
| `HUAWEI_CLOUD_SK` | Secret access key | — |
| `CLOUDROBO_SERVICE_CONFIG` | Custom config file path | `~/.cloudrobo/config.yaml` |
| `CLOUDROBO_ENDPOINT_cloudrobo-service` | Override service endpoint | — |
| `CLOUDROBO_HTTP_PROXY` | HTTP proxy | — |
| `CLOUDROBO_HTTPS_PROXY` | HTTPS proxy | — |
| `CLOUDROBO_VERIFY_SSL` | SSL verification (true/false) | false |
| `CLOUDROBO_LOG_TRAFFIC` | Traffic logging (true/false) | false |
| `CLOUDROBO_DEBUG` | Verbose error output (1/0) | 0 |
