# CLI Installation Guide

## Install cloudrobo CLI

### Option 1: Install all packages (recommended)

```bash
pip install hw-cloudrobo-client
```

This installs the aggregate package with all functional modules (asset, dataset, train, eval, infer, robot, dispatch, workspace).

### Option 2: Install only robot package

```bash
pip install hw-cloudrobo-client
```

This installs `cloudrobo-core` (CLI framework) + `cloudrobo-robot`.

### Option 3: Development install (editable)

```bash
git clone <cloudrobo-client-repo>
cd cloudrobo-client
pip install hw-cloudrobo-client
```

## Verify Installation

```bash
# Check CLI is available
cloudrobo --help

# Check robot subcommand is registered
cloudrobo robot --help

# Check plugin loading
cloudrobo robot list --help
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

### Persist credentials via config (optional alternative to env vars)

```bash
# Store AK/SK in ~/.cloudrobo/ config (env vars take precedence when both are set)
cloudrobo config set ak <your-access-key> sk <your-secret-key>
```

### Set default workspace

```bash
# List available workspaces
cloudrobo workspace list

# Set default workspace (avoids passing --workspace-id each time)
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

## robot Subcommands

| Subcommand | Purpose |
| ----------- | --------- |
| `cloudrobo robot create` | Register a new robot |
| `cloudrobo robot list` | List robots (with filters) |
| `cloudrobo robot show` | Show a robot's detail |
| `cloudrobo robot update` | Update a robot's name/description |
| `cloudrobo robot delete` | Delete a robot |
| `cloudrobo robot export-certificate` | Export a robot's certificate |
| `cloudrobo robot show-sdk` | Get robot SDK download info |

## Troubleshooting

| Issue | Solution |
| ------- | ---------- |
| `cloudrobo: command not found` | Ensure `cloudrobo-core` installed; check PATH |
| `robot subcommand missing` | Ensure `cloudrobo-robot` installed; run `cloudrobo --help` |
| `401 Unauthorized` | Check AK/SK environment variables are set correctly |
| `403 Forbidden` | Check workspace_id; ensure account has CloudRobo access |
| `400 type invalid` | Use uppercase enum: HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER |
| `Connection error` | Check region/endpoint config; verify network/proxy settings |
| Certificate export empty file | Check `--robot-id`; ensure `--output` directory exists; filename auto-generated as `cert_config_{name}_{timestamp}.zip` |
