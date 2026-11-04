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

### Docker Engine 24+ (custom-operator Mode A only) 安装Docker

The custom-operator onboarding pipeline builds and pushes operator images with the
local Docker Engine (Mode A image-inbuilt). Docker is **not** required for normal
proc/eval task management.

**Linux:**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sudo bash
sudo systemctl start docker
sudo usermod -aG docker $USER  # Avoid sudo for docker commands

# Verify
docker --version  # Must be 24+
docker info       # Daemon must be running
```

**Windows (Docker Desktop):**

```powershell
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
docker --version
docker info
```

**Verify Docker is running:**

```bash
docker info > /dev/null 2>&1 && echo "Docker is running" || echo "Docker daemon not available"
```

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

### Operator Code Structure (custom-operator) 算子代码结构

The custom-operator onboarding pipeline expects the user's operator code directory to
have the following structure (single `.py` files and existing CLI projects are also
supported and adapted in Phase 1):

```
my-operator/
├── src/
│   ├── __init__.py          # Package init
│   └── user_operator.py    # Must contain process(input_path: str) -> str|bytes
├── requirements.txt         # Python dependencies (e.g., numpy, opencv-python)
└── operator_config.yaml     # Operator metadata (see custom-operator/custom-operator-reference.md)
```

The skill generates `entrypoint.py` in the work copy — users **do not write this file**.
It reads the `SOURCE_DATASET_PATH` env var, resolves input/output directories, calls the
user's `process()` for each input item, and writes results to the output directory.

### Feature Flag Configuration (custom-operator) 功能开关

`~/.cloudrobo/config.yaml` supports feature flags for the custom-operator pipeline:

```yaml
features:
  custom_operator:
    enabled: true              # Master switch: false → skill returns "feature disabled"
    skip_push: false           # Skip image push (Phase 2 degradation)
    skip_create: false         # Skip asset creation (Phase 3 degradation)
    dry_run_only: false        # Preview only, no execution
    workdir_retention: true    # Default: auto-clean on success, retain on failure for --reuse-workdir
    workdir_cleanup_interval: 3600  # Auto-cleanup sweep interval (seconds)
    max_workdir_count: 10      # Max retained work copies (oldest swept first)
```

### Multi-Region Setup 多局点配置

```bash
# Environment variables take priority over config.yaml (HCS / HCSO overrides)
export CLOUDROBO_REGION=cn-east-3
export CLOUDROBO_ENDPOINTS_APIG=https://cloudrobo-gallery.cn-east-3.myhuaweicloud.com
export CLOUDROBO_ENDPOINTS_SWR=swr.cn-east-3.myhuaweicloud.com
export CLOUDROBO_ENDPOINTS_OBS=obs.cn-east-3.myhuaweicloud.com
export CLOUDROBO_SWR_NAMESPACE=cloudrobo
export CLOUDROBO_REGISTRY=swr.cn-east-3.myhuaweicloud.com  # HCS override
```

**OBS endpoint reachability (custom-operator Mode B):** the default
`cloudrobo-obs` endpoint `obs.{region}.myhuaweicloud.com` may **not be resolvable**
from the build environment (observed: NXDOMAIN). Before any OBS operation (Mode B code
delivery or dataset upload), verify it:

```bash
python3 -c "import socket; print(socket.gethostbyname('obs.cn-southwest-2.myhuaweicloud.com'))"
# NXDOMAIN → ask the customer for a reachable endpoint, e.g. obs.{region}.myhuaweicloud.com
# Override per-run: cfg.endpoints['cloudrobo-obs'] = 'obs.cn-southwest-2.myhuaweicloud.com'
# or via env: export CLOUDROBO_ENDPOINTS_OBS=obs.cn-southwest-2.myhuaweicloud.com
```

If the endpoint cannot be resolved, **ask the customer for a reachable one** — never
guess an endpoint. OBS paths still use `obs://` protocol and must start with the
workspace `default_obs_path`.

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
| `docker: command not found` / daemon not available (custom-operator) | Install Docker Engine 24+ and start the daemon (`sudo systemctl start docker` / Docker Desktop) |
| `SWR login: unauthorized` / `Authenticate Error` (custom-operator) | **Auto-credential generation or login failed.** Classify the reason and fix in order: ① **AK/SK invalid/expired** → remind the customer to update `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` (or `~/.cloudrobo/config.yaml`); ② **SWR not enabled / IAM permission missing** (e.g. `Tenant Guest`, `no permission`) → enable SWR in the console and grant SWR access to the AK/SK account; ③ **region mismatch** → ensure `swr.<region>.myhuaweicloud.com` matches `CLOUDROBO_REGION`; ④ **network/proxy/docker daemon** → check connectivity. The skill auto-generates the login command from AK/SK (`docker login -u <region>@<AK> -p <HMAC-SHA256(AK,SK)> swr.<region>.myhuaweicloud.com`); after the fix, re-run it — if it still fails, ask the customer for a full command and only proceed once output shows `Login Succeeded` |
| `POST /v1/assets: 403 Forbidden` (custom-operator) | **Remind the customer to update the AK/SK permissions** — verify AK/SK has `cloudrobo:assets:create` permission |

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
