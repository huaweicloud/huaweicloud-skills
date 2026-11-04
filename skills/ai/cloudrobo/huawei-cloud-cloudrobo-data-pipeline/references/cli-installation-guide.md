# CLI Installation Guide CLI安装指南

> Install and configure the `cloudrobo` CLI used by every stage of the data pipeline
> (workspace, asset registration, operator discovery, `dataset proc` / `dataset eval`
> tasks). Agent orchestration uses CLI commands; the optional Web backend separately
> uses the Python SDK and the same local authentication configuration. Commands and
> flags in this skill follow the latest `cloudrobo` CLI release (upgrade with
> `pip install -U hw-cloudrobo-client`). Web SDK setup is described in
> [Web Monitor](web-monitor.md#web-sdk-setup).

<a id="environment-preflight"></a>
## Environment Preflight 环境预检

Before the first script, identify the actual shell and locate available launchers. Git
Bash on Windows still uses Bash syntax; it does not imply `python3` or `py` is installed.
The pipeline scripts/Web require Python 3.9+, including when the CLI itself supports an
older Python. Miniconda's `python` is valid. Select one verified launcher for this run and
use it consistently; do not rewrite the machine's PATH or add permanent aliases.

| Shell | Locate candidates | Path / syntax |
|---|---|---|
| Bash / Git Bash | `command -v python3`, `command -v python`, `command -v py` | Quote paths; on Windows use `C:/...` or `/c/...`; continuation `\`; variables `$NAME` |
| PowerShell | `Get-Command python3,python,py -ErrorAction SilentlyContinue` | Quote Windows paths; use one-line commands or backtick continuation; variables `$env:NAME` |

Only execute candidates that exist, then verify they really run Python 3.9+ (a launcher
alias alone is insufficient). For a chosen `python`, use this in either shell:

```text
python -c "import sys; print(sys.executable); print(sys.version); raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
```

If the verified launcher is `python3` or `py -3`, replace `python` accordingly. Examples
elsewhere use `python3` as notation; adapt them before execution. If no suitable runtime
is available, report the missing prerequisite before running authoring/state/Web scripts.

### Git Bash with Miniconda

When the current shell already exposes a verified Miniconda `python`:

```bash
cd 'C:/Users/name/My Project/huawei-cloud-cloudrobo-data-pipeline'
python scripts/pipeline-monitor/server.py --background --open
```

Do not paste an unquoted `C:\Users\...` path into Bash: backslashes are escape characters.
The actual skill directory comes from the user's environment, not the sample above.

### PowerShell

If `python` is the verified launcher:

```powershell
Set-Location 'C:/Users/name/My Project/huawei-cloud-cloudrobo-data-pipeline'
python scripts/pipeline-monitor/server.py --background --open
```

If `py -3` is verified instead, use it throughout. For JSON argv, background service
management and optional tests, see [Windows / PowerShell](web-monitor.md#windows-powershell).

## Installation 安装

### Prerequisites 前置条件

- Python 3.8+
- pip package manager
- Huawei Cloud account with AK/SK credentials

### Install 安装

```bash
pip install hw-cloudrobo-client
```

This single package installs the `cloudrobo` entry point and all command groups used by
this skill: `config`, `workspace`, `asset`, `dataset proc`, `dataset eval`.

```bash
cloudrobo --version
# Expected: cloudrobo, version <x.y.z>
```

## Configuration 配置

### Set credentials 设置认证

Choose one of the two options. The user runs these commands in their own terminal — never
paste AK/SK into the chat, `pipeline.yaml`, scripts, or documents.

**Option 1: CLI config (encrypted storage)**

```bash
cloudrobo config set ak <your-ak> sk <your-sk>
```

AK/SK are stored encrypted (machine-bound) in `~/.cloudrobo/config.yaml`. Check them with
`cloudrobo config get ak` / `cloudrobo config get sk` (masked output: first 4 and last 4
characters only). The values appear in the shell history of the terminal that ran the
command — clear it if your security policy requires.

**Option 2: Environment variables**

```bash
export HUAWEI_CLOUD_AK="<your-ak>"
export HUAWEI_CLOUD_SK="<your-sk>"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="<your-ak>"
$env:HUAWEI_CLOUD_SK="<your-sk>"
```

> **Precedence**: `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` environment variables take
> precedence over the values stored by `cloudrobo config set`.

### Set region 设置区域

For real execution, first inspect the current configuration without changing it:

```bash
cloudrobo config get region
```

This is a local configuration read, not live regional proof. Check its actual output:
some CLI versions return exit 0 even for `region 未设置`. Cross-check the intended region
against available workspace/endpoint information, particularly explicit intranet endpoint
overrides below. An SWR image URL is not an authoritative source of task region.

If the command is unavailable, configuration is missing, or sources conflict, ask the user
before real execution and note the verified region/source in the plan explanation. Do not
dump credentials or silently change configuration. Local drafts may keep region unresolved.

The SDK's default is `cn-southwest-2`; do not present this fallback as a verified user choice.
Only when setting a region is explicitly required and confirmed:

```bash
cloudrobo config set region <region-id>
cloudrobo config get region
```

Operators are published per region. The operators a pipeline needs (conversion, `数据清洗`,
`数据集质量评测-LeRobot`, `数据集多样性评测-LeRobot`) must be returned by
`list-publication-assets` in the configured region — if one is missing, the pipeline stops
and the user is told (see SKILL.md Step 2.1).

### Set default workspace 设置默认工作空间

```bash
# List available workspaces
cloudrobo workspace list

# Set the default workspace (validated against the service, then saved locally)
cloudrobo workspace use --workspace-id <workspace-id>

# Show the saved workspace (local read: workspace_id, name, asset_catalog_id, default_obs_path)
cloudrobo workspace current
```

The saved workspace is stored in `~/.cloudrobo/workspace.json`. Its `asset_catalog_id` is
the `catalog_id` used by `create-asset` / `import-asset` and in proc task_config. Commands
such as `dataset proc|eval create-task` and `list-tasks` also accept `--workspace-id <id>`
to override the default.

### Endpoint override 端点覆盖 (optional)

Default endpoints (`{region}` is replaced by the configured region):

| Service | Default endpoint |
|---------|------------------|
| `cloudrobo-service` (workspace, `dataset proc` / `dataset eval`) | `https://cloudrobo.{region}.myhuaweicloud.com` |
| `cloudrobo-asset-manager` (asset, operator discovery) | `https://cloudrobo-gallery.{region}.myhuaweicloud.com` |
| `cloudrobo-obs` (`import-asset` upload) | `https://obs.{region}.myhuaweicloud.com` |

Override with `CLOUDROBO_ENDPOINT_<SERVICE>` (service name upper-cased, `-` replaced by
`_`):

```bash
export CLOUDROBO_ENDPOINT_CLOUDROBO_SERVICE="https://cloudrobo.<region>.myhuaweicloud.com"
```

`import-asset` uploads to OBS with the same AK/SK; its OBS endpoint can be overridden with
`CLOUDROBO_OBS_ENDPOINT`.
For pipeline local-data uploads, read the `huawei-cloud-cloudrobo-asset` skill and use its
`cloudrobo asset import-asset` workflow. The OBS transfer above is internal to that command;
do not treat it as a prerequisite to install/find a generic OBS CLI or run a separate upload.

## Verification 验证

All commands below are read-only.

```bash
# CLI installed
cloudrobo --version

# Command groups used by the pipeline are registered
cloudrobo dataset proc --help     # create-task, wait-task, show-task, get-log, ...
cloudrobo dataset eval --help     # create-task, wait-task, show-task, get-log, get-preview, ...

# Region and workspace
cloudrobo config get region
cloudrobo workspace current       # Expected: JSON with workspace_id and asset_catalog_id

# Credentials + region: operator discovery
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --limit 5
# Expected: JSON with page_info and data[]; no authentication error

# Credentials + workspace: task listing
cloudrobo dataset proc list-tasks --limit 5
cloudrobo dataset eval list-tasks --limit 5
```

## Windows / PowerShell Notes Windows/PowerShell说明

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Use `py -3` or `python` for local scripts when `python3` is not available.
> - Windows PowerShell 5.1 may alter nested JSON quotes passed to native commands.
>   Use JSON files for the local authoring/state scripts; Web "copy CLI" generates a
>   PowerShell/Python argv bridge on Windows. See [native Windows commands](web-monitor.md#windows-powershell).

## Troubleshooting 故障排查

| Issue | Solution |
|-------|----------|
| `command not found: cloudrobo` | Check `PATH`, or reinstall: `pip install hw-cloudrobo-client` |
| `AK 和 SK 均未配置` / `AK 未配置` / `SK 未配置` | Run `cloudrobo config set ak <your-ak> sk <your-sk>`, or set `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` |
| `AK 解密失败` / `SK 解密失败` | Stored credentials cannot be decrypted on this machine — re-run `cloudrobo config set ak <your-ak> sk <your-sk>` here |
| `认证失败，请检查 AK/SK 是否正确` | Check the AK/SK values; remember environment variables override `config set` values |
| `未配置工作空间` (from `workspace current`) | Run `cloudrobo workspace use --workspace-id <id>` |
| `缺少 workspace_id 参数` | Run `cloudrobo workspace use --workspace-id <id>` or pass `--workspace-id <id>` |
| `工作空间 <id> 不存在` | Check the ID with `cloudrobo workspace list` and the configured region |
| Operator discovery returns `"total": 0` | Check region (`cloudrobo config get region`); if the operator is still not found, stop and tell the user — never substitute another operator |
| `No such command` for a subcommand | Compare with `cloudrobo <group> --help`; upgrade with `pip install -U hw-cloudrobo-client` |

## Environment Variables 环境变量

| Variable | Description | Default |
|----------|-------------|---------|
| `HUAWEI_CLOUD_AK` | Access key ID (overrides `config set ak`) | — |
| `HUAWEI_CLOUD_SK` | Secret access key (overrides `config set sk`) | — |
| `CLOUDROBO_SERVICE_CONFIG` | Custom config file path | — |
| `CLOUDROBO_ENDPOINT_<SERVICE>` | Override a service endpoint (e.g. `CLOUDROBO_ENDPOINT_CLOUDROBO_SERVICE`) | — |
| `CLOUDROBO_OBS_ENDPOINT` | Override the OBS endpoint used by `import-asset` uploads | — |
| `CLOUDROBO_HTTP_PROXY` / `CLOUDROBO_HTTPS_PROXY` | HTTP / HTTPS proxy | — |
| `CLOUDROBO_VERIFY_SSL` | SSL verification (true/false) | from config |
| `CLOUDROBO_LOG_TRAFFIC` | Traffic logging (true/false) — debug only, disable in production | false |
