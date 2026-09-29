# hcloud (KooCLI) Installation & Authentication Guide

This skill executes Huawei Cloud operations through the **hcloud (KooCLI)**
command-line tool against the **CodeArtsPipeline** and **CodeArtsBuild**
services (Huawei Cloud CodeArts 流水线 / 编译构建).

## Install hcloud

See the official quick start: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

```bash
# Download and install (Linux x86_64 shown; see docs for ARM/macOS variants)
curl -sSL https://cn-north-4-hcli.obs.cn-north-4.myhuaweicloud.com/hcli_latest_linux_amd64.tar.gz -o hcli.tar.gz
tar -xzf hcli.tar.gz
./hcloud_install.sh

# Verify
hcloud version
```

For other OS/architectures, follow https://support.huaweicloud.com/qs-hcli/hcli_02_003.html.

## Update KooCLI

```bash
hcloud update -y
```

## Service Names

This skill uses **two** KooCLI services:

| Service | Metadata directory | Notes |
|---------|--------------------|-------|
| `CodeArtsPipeline` | `codeartspipeline` | Pipelines (流水线) — list/detail/run/log/start/delete |
| `CodeArtsBuild` | `codeartsbuild` | Build tasks (构建任务/编译构建) — list/detail/log/start/create/delete |

The name `CloudBuild` is **NOT** accepted by the CLI
(`hcloud CloudBuild ...` reports `[USE_ERROR]不支持的服务名称:CloudBuild`), and
there is no `CLOUDBUILD` service either. Verify with:

```bash
hcloud CodeArtsPipeline --help
hcloud CodeArtsBuild --help
```

## Authentication

### Option 1: hcloud profile (AK/SK)

Use the hcloud configuration command to persist your access key and secret key
into the default profile, along with the default region and project:

```bash
hcloud configure set --cli-profile=default --cli-region=cn-north-4 \
  --cli-access-key=<your-access-key-id> --cli-secret-key=<your-access-key-secret>
hcloud configure list   # verify
```

> Never commit the `configure set` command with real keys into code or
> documents — it is a local machine operation.

### Option 2: Environment variables (auto-detected)

hcloud automatically reads credentials from:

- `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`, or
- `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` (with optional `HUAWEI_SECURITY_TOKEN`)

```bash
export HUAWEICLOUD_SDK_AK={YOUR_ACCESS_KEY}
export HUAWEICLOUD_SDK_SK={YOUR_SECRET_KEY}
```

### Option 3: SSO / other modes

Refer to `hcloud configure --help` for additional modes (e.g. SSO login).

## Region & Project

- All CodeArtsPipeline / CodeArtsBuild APIs are region/project scoped. Pass
  `--cli-region={region}` explicitly.
- `--project_id` is required by most operations. The project must be a
  **CodeArts (DevCloud) project**; a plain IAM project returns
  `pipeline.00060101 项目不存在` from the Pipeline API.
- If `--project_id` is omitted, KooCLI uses `cli-project-id` from the profile or
  the parent project of the region in the authentication information.

## skill-quality-cli (quality telemetry)

Quality telemetry for this skill is collected automatically through
`skill-quality-cli`, ensured idempotently by `scripts/ensure_cli.sh`:

| CLI Tool | Purpose | Installation |
|----------|---------|--------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh   # idempotent: installs only if absent (no auto-upgrade)
skill-quality-cli version    # verify it works
```

## Manual upgrade

CLI no longer auto-upgrades (合规 v1.7+). To upgrade to the latest version, run
manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, install manually from the bundled sources:

```bash
# Deploy the bundled CLI carrier sources to ~/.local/bin/ (offline, no download)
export PATH="$HOME/.local/bin:$PATH"
mkdir -p ~/.local/bin/skill-quality-cli.d
cp scripts/cli/cli_entry.py ~/.local/bin/skill-quality-cli.d/
cp scripts/cli/cli_reporting.py ~/.local/bin/skill-quality-cli.d/
```

Upgrade afterwards with `skill-quality-cli upgrade`.

## Verification

```bash
hcloud CodeArtsPipeline ListPipelines --cli-region=cn-north-4 --project_id={project_id} --offset=0 --limit=10
hcloud CodeArtsBuild ListProjectJobs --cli-region=cn-north-4 --project_id={project_id} --page_index=0 --page_size=10
```

A successful JSON response (or a valid error JSON such as
`pipeline.00060101 项目不存在` for a non-CodeArts project) means the CLI +
credentials are functional.