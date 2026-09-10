# CloudRobo CLI Installation & Configuration Guide

> This guide is for users who need to install and configure the CloudRobo CLI tool.

## Installation

The CloudRobo CLI (`cloudrobo`) is the command-line interface for interacting with CloudRobo services including asset management, model training, inference deployment, and robot dispatch.

### Prerequisites

- Python 3.8+
- pip package manager
- Huawei Cloud account with AK/SK credentials

### Install

```bash
pip install hw-cloudrobo-client
```

Verify installation:

```bash
cloudrobo --version
```

## Authentication Configuration

The CLI reads authentication from environment variables:

```bash
# Set required environment variables
# ⚠️ NEVER commit real keys. Use a secrets manager or .env file.
export HUAWEI_CLOUD_AK="your-access-key-id"
export HUAWEI_CLOUD_SK="your-secret-access-key"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="your-access-key-id"
$env:HUAWEI_CLOUD_SK="your-secret-access-key"
```

> **Security reminder:** Never hardcode AK/SK in scripts. Use environment variables or IAM roles. Do not pass credentials via CLI configuration commands with plaintext.

## Getting AK/SK

1. Log in to Huawei Cloud Console
2. Navigate to "Identity and Access Management" → "My Credentials"
3. Click "Create Access Key"

## Workspace Configuration

Before running pipeline operations, set the active workspace:

```bash
# List available workspaces
cloudrobo workspace list

# Set active workspace
cloudrobo workspace use <workspace_id>

# Verify current workspace
cloudrobo workspace current
```

## Available Services

```bash
# View all available services
cloudrobo --help

# View operations for a specific service
cloudrobo asset --help
cloudrobo train --help
cloudrobo infer --help
cloudrobo dispatch --help
cloudrobo robot --help
cloudrobo resource --help
```

## Windows/PowerShell Notes

PowerShell has issues parsing JSON containing `|`, `"`, and other special characters. When passing complex JSON parameters:

1. Write the JSON to a temporary file
2. Use Python subprocess to call the CLI (this is not SDK, just a Python wrapper for CLI calls to work around PowerShell encoding issues)

```python
import subprocess
with open("config.json", "r", encoding="utf-8") as f:
    config = f.read().strip()
result = subprocess.run(
    ["cloudrobo", "train", "create-task", "--config", config, "-v"],
    capture_output=True
)
print(result.stdout.decode("utf-8", errors="replace"))
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `command not found: cloudrobo` | Check PATH or reinstall via pip |
| `Authentication failed` | Verify AK/SK environment variables are set correctly |
| `Permission denied` | Check IAM permissions for CloudRobo services |
| `Workspace not set` | Run `cloudrobo workspace use <id>` |
| PowerShell JSON parsing errors | Write JSON to file and use Python subprocess |
