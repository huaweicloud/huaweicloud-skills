# CLI Installation Guide

## Install cloudrobo CLI

### Option 1: Install all packages (recommended)

```bash
pip install hw-cloudrobo-client
```

This installs the aggregate package with all functional modules (asset, dataset, train, eval, infer, robot, dispatch, workspace).

### Option 2: Install only train package

```bash
pip install hw-cloudrobo-client
```

This installs `cloudrobo-core` (CLI framework) + `cloudrobo-asset` (cross-package dependency for algorithm/dataset/model queries) + `cloudrobo-train`.

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

# Check train subcommand is registered
cloudrobo train --help

# Check plugin loading
cloudrobo train list-tasks --help
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
# Stores AK/SK in ~/.cloudrobo/ config (env vars take precedence when both are set)
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

Or set endpoint explicitly:

```bash
export CLOUDROBO_ENDPOINT_CLOUDROBO-SERVICE="https://cloudrobo.cn-north-4.myhuaweicloud.com"
```

## train Subcommands

| Subcommand | Purpose | --sim-rl |
| ----------- | --------- | ---------- |
| `cloudrobo train create-task` | Create task from full JSON config (TRAIN_FROM_SCRATCH / MODEL_TUNING / SimRL) | Yes |
| `cloudrobo train list-tasks` | List training tasks | Yes |
| `cloudrobo train show-task` | Show task detail | Yes |
| `cloudrobo train update-task` | Update task name/description | Yes |
| `cloudrobo train delete-tasks` | Delete tasks (batch for train, per-id for SimRL) | Yes |
| `cloudrobo train stop-task` | Stop a running task | Yes |
| `cloudrobo train restart-task` | Restart / edit & resubmit a task | Yes |
| `cloudrobo train clone-task` | Clone a SimRL task (SimRL-only) | Yes |
| `cloudrobo train save-draft` | Save task config as draft | Yes |
| `cloudrobo train resume-task` | Resume a train task (train-only) | No |
| `cloudrobo train get-stages` | Get execution stages | Yes |
| `cloudrobo train get-resource-usage` | View resource usage (--metric/--start/--end required) | Yes |
| `cloudrobo train get-logs` | Get training log content | Yes |
| `cloudrobo train get-signed-url` | Get log file download signed URL | Yes |
| `cloudrobo train get-events` | Get training events (--start-time/--end-time required) | Yes |
| `cloudrobo train stats` | Count tasks by status (--workspace-id required) | Yes |

> The `--sim-rl` flag (present on 15 commands) routes the command to the SimRL API surface
> (`/v1/training/rl-tasks/simulation`). It is absent on `pretrain`, `finetune`,
> `resume-task`, `list-checkpoints`, and `register-checkpoint` (train-only).

## Troubleshooting

| Issue | Solution |
| ------- | ---------- |
| `cloudrobo: command not found` | Ensure `cloudrobo-core` installed; check PATH |
| `train subcommand missing` | Ensure `cloudrobo-train` installed; run `cloudrobo --help` to verify plugin loaded |
| `401 Unauthorized` | Check AK/SK environment variables are set correctly |
| `403 Forbidden` | Check workspace_id is correct; ensure account has CloudRobo access |
| `400 spec format invalid` | `spec` must match `Ascend: N * Model \| vCPUs vCPUs \| GiB GiB` |
| `400 train_method invalid` | Use uppercase enum: SFT/LORA/QLORA/DEEPSPEED |
| `CREATE_FAILED` | Check spec, cluster_id, resource availability |
| `Connection error` | Check region/endpoint config; verify network/proxy settings |
| `get-resource-usage` missing params | `--metric`, `--start`, `--end` are all required |
| `get-events` missing params | `--start-time`, `--end-time` are both required |
| `get-signed-url` missing params | `--file-source`, `--file-name` are both required |
| `resume-task --sim-rl` rejected | `resume-task` is train-only; SimRL has no resume endpoint |
