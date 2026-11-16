# CLI Installation Guide

## Install cloudrobo CLI

**There is exactly one supported install path: the aggregate client.**

```bash
pip install hw-cloudrobo-client
```

This installs the aggregate package with every functional module (asset, dataset, train, eval,
infer, robot, dispatch, workspace).

> **Do NOT install the infer module alone** (`pip install hw-cloudrobo-infer`). It pulls
> `cloudrobo-core` + `cloudrobo-infer` only, so `cloudrobo infer` works but the `asset`,
> `resource` and `workspace` command groups this skill's workflow depends on are **absent**:
> `cloudrobo asset list-assets ...` then fails with `Error: No such command asset`, and
> model / pool / workspace resolution cannot proceed. Install the aggregate client instead —
> `hw-cloudrobo-client` already contains the infer module.

If a restricted environment forbids the aggregate package, installing `hw-cloudrobo-infer`
alone is **not** a substitute: add `hw-cloudrobo-asset` (and the `workspace` / `resource`
modules) so the full command groups shown below are registered.

Development install (editable, from the client repo) is equivalent to the aggregate install and
is only for client development:

```bash
git clone <cloudrobo-client-repo>
cd cloudrobo-client
pip install -r requirements-dev-editable.txt
```

## Verify Installation

```bash
# Check CLI is available
cloudrobo --help

# Check the command groups this skill relies on are registered
cloudrobo infer --help
cloudrobo asset --help
cloudrobo resource --help
cloudrobo workspace --help

# Check plugin loading
cloudrobo infer list --help
```

If any of these fails, stop and fix the installation first — do not append parameters or
retry blindly.

| Symptom | Meaning | Fix |
| --------- | ------- | --- |
| `cloudrobo: command not found` | client not installed / PATH | `pip install hw-cloudrobo-client`, re-check PATH |
| `Error: No such command 'infer'` | infer module missing | install the aggregate client |
| `Error: No such command 'asset'` | infer module was installed **alone** (common on `pip install hw-cloudrobo-infer`) | `pip install hw-cloudrobo-client` to add the asset/resource/workspace groups, then re-run `cloudrobo asset --help` |
| `Error: No such command 'resource'` / `'workspace'` | same root cause as above | install the aggregate client |

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

### Persist credentials in the user config (optional)

```bash
# AK/SK are stored encrypted (machine-bound) in ~/.cloudrobo/config.yaml
cloudrobo config set ak <your-ak> sk <your-sk>

# Confirm (values are masked)
cloudrobo config get ak
cloudrobo config get sk
```

### Set default workspace

```bash
cloudrobo workspace list
cloudrobo workspace use --workspace-id <workspace-id>
cloudrobo workspace current
```

## Configuration Precedence

```text
HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK (AK/SK only)  >  ~/.cloudrobo/config.yaml  >  package config.yaml
```

- **Region** has no environment-variable channel in client 0.3.0: read it only from
  `~/.cloudrobo/config.yaml` (`cloudrobo.region`).
- **Endpoint** overrides use `CLOUDROBO_ENDPOINT_<SERVICE>`; proxy/verbose options use the
  matching `CLOUDROBO_*` variables.
- **AK/SK**: `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` take precedence over stored values.

## Region Configuration

`cloudrobo` (0.3.0) has **no region command-line option** — the root command only accepts
`--verbose/-v` (and `--version`). Region comes from the config file only:

```bash
# Persisted to ~/.cloudrobo/config.yaml as cloudrobo.region
cloudrobo config set region cn-north-4

# Confirm
cloudrobo config get region
```

```yaml
# ~/.cloudrobo/config.yaml
cloudrobo:
  region: cn-north-4
```

Default region is `cn-southwest-2`. Do **not** append a region option to `cloudrobo`
commands — that option belongs to `hcloud`/KooCLI only; an unknown option makes `cloudrobo`
exit non-zero.
Endpoint overrides use `CLOUDROBO_ENDPOINT_<SERVICE>` (e.g.
`CLOUDROBO_ENDPOINT_CLOUDROBO_SERVICE`).

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
| `cloudrobo: command not found` | Ensure the client is installed; check PATH |
| `infer subcommand missing` | Ensure the infer module is installed; `pip install hw-cloudrobo-client` (aggregate) and run `cloudrobo --help` |
| `Error: No such command asset` / `resource` / `workspace` | infer module installed alone — `pip install hw-cloudrobo-client` and re-run `cloudrobo asset --help` |
| `401 Unauthorized` | Check AK/SK environment variables |
| `403 Forbidden` | Check workspace_id; verify account access |
| `400 model invalid` | model_id/model_version_id in `--model-json` not found in workspace |
| `Click: Invalid JSON` | malformed `--*-json` param; re-check JSON syntax |
| `list-logs` wrong data | timestamps must be **milliseconds** (13-digit), not seconds |
| `wait-deploy` timeout | service stuck in DEPLOYING; extend `--timeout` or free pool |
| `Connection error` | Check region/endpoint config; verify network/proxy |
