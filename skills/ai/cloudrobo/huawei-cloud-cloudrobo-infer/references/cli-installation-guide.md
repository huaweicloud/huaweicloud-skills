# CLI Installation Guide

## Install cloudrobo CLI

### Option 1: Install all packages (recommended)

```bash
pip install hw-cloudrobo-client
```

This installs the aggregate package with all functional modules (asset, dataset, train, eval, infer, robot, dispatch, workspace).

### Option 2: Install only infer package

```bash
pip install hw-cloudrobo-infer
```

This installs `cloudrobo-core` (CLI framework) + `cloudrobo-infer`.

### Option 3: Development install (editable)

```bash
git clone <cloudrobo-client-repo>
cd cloudrobo-client
pip install -r requirements-dev-editable.txt
```

## Verify Installation

```bash
# Check CLI is available
cloudrobo --help

# Check infer subcommand is registered
cloudrobo infer --help

# Check plugin loading
cloudrobo infer list --help
```

## Authentication Configuration

### Set AK/SK environment variables

```bash
export HUAWEI_CLOUD_AK="your-access-key"
export HUAWEI_CLOUD_SK="your-secret-key"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="your-access-key"
$env:HUAWEI_CLOUD_SK="your-secret-key"
```

### Initialize user config (optional)

```bash
cloudrobo setup
```

### Set default workspace

```bash
cloudrobo workspace list
cloudrobo workspace use <workspace-id>
```

## Configuration Precedence

```text
CLOUDROBO_* environment variables  >  ~/.cloudrobo/config.yaml  >  config.yaml defaults
```

## Region Configuration

Default region is `cn-southwest-2`. Override via config:

```yaml
# ~/.cloudrobo/config.yaml
cloudrobo:
  region: cn-north-4
```

## infer Subcommands

| Subcommand | Purpose |
| ----------- | --------- |
| `cloudrobo infer create` | Create an inference service |
| `cloudrobo infer wait-deploy` | Wait for service deployment to complete (CLI convenience) |
| `cloudrobo infer list` | List inference services (with filters) |
| `cloudrobo infer show` | Show service detail |
| `cloudrobo infer start` | Start a service |
| `cloudrobo infer stop` | Stop a service |
| `cloudrobo infer update` | Update service config |
| `cloudrobo infer delete` | Delete a service |
| `cloudrobo infer list-logs` | List service logs (ms timestamps) |

## Troubleshooting

| Issue | Solution |
| ------- | ---------- |
| `cloudrobo: command not found` | Ensure `cloudrobo-core` installed; check PATH |
| `infer subcommand missing` | Ensure `cloudrobo-infer` installed; run `cloudrobo --help` |
| `401 Unauthorized` | Check AK/SK environment variables |
| `403 Forbidden` | Check workspace_id; verify account access |
| `400 model invalid` | model_id/model_version_id in `--model-json` not found in workspace |
| `Click: Invalid JSON` | malformed `--*-json` param; re-check JSON syntax |
| `list-logs` wrong data | timestamps must be **milliseconds** (13-digit), not seconds |
| `wait-deploy` timeout | service stuck in DEPLOYING; extend `--timeout` or free pool |
| `Connection error` | Check region/endpoint config; verify network/proxy |
