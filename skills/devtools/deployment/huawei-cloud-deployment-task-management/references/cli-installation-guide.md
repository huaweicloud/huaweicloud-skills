# hcloud (KooCLI) Installation & Authentication Guide

This skill executes Huawei Cloud operations through the **hcloud (KooCLI)** command-line tool
against the **CodeArtsDeploy** service (Huawei Cloud CloudDeploy).

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

## Service Name

The CloudDeploy service is exposed by KooCLI under the name **`CodeArtsDeploy`** (metadata
directory `codeartsdeploy`). The name `CloudDeploy` is NOT accepted by the CLI
(`hcloud CloudDeploy ...` reports "Unsupported service"). Verify with:

```bash
hcloud CodeArtsDeploy --help
```

## Authentication

### Option 1: hcloud profile (AK/SK)

Use the hcloud configuration command to persist your access key and secret key into the default
profile, along with the default region and project:

```bash
hcloud configure set --cli-profile=default --cli-region=cn-north-4 \
  --cli-access-key=<your-access-key-id> --cli-secret-key=<your-access-key-secret>
hcloud configure list   # verify
```

> Never commit the `configure set` command with real keys into code or documents —
> it is a local machine operation.

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

- All CodeArtsDeploy APIs are region/project scoped. Pass `--cli-region={region}` explicitly.
- `--project_id` is required by most operations. The project must be a **CodeArts (DevCloud)
  project**; a plain IAM project returns `Deploy.00016902 项目不存在` from the Deploy API.
- If `--project_id` is omitted, KooCLI uses `cli-project-id` from the profile or the parent project
  of the region in the authentication information.

## OBS Artifact Check (obsutil)

`huawei_analyze_clouddeploy_artifact` verifies that the OBS object referenced by a deployment task
exists. hcloud forwards OBS commands to **obsutil** (`hcloud obs <command>`). Initialize it once:

```bash
# Configures the endpoint (per region) and reuses the same AK/SK as hcloud
hcloud obs config -i={access_key} -k={secret_key} -e=https://obs.cn-north-4.myhuaweicloud.com
```

Then check objects:

```bash
hcloud obs ls obs://{artifact_bucket}/{artifact_object_path}
```

> `-i`/`-k` are provided from your credentials at runtime; never store them in files in the skill
> directory. `obsutil` object URLs use the `obs://` scheme — `s3://` is rejected with `cloud_url
> is not in well format`.

## Verification

```bash
hcloud CodeArtsDeploy ListAllApp --cli-region=cn-north-4 --project_id={project_id} --page=1 --size=10
```

A successful JSON response (or a valid error JSON such as `Deploy.00016902` for a non-CodeArts
project) means the CLI + credentials are functional.