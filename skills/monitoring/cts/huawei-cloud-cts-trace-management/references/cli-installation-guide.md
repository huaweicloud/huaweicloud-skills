# hcloud (KooCLI) Installation & Authentication Guide

This skill executes Huawei Cloud operations through the **hcloud (KooCLI)** command-line tool.

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

- Most CTS APIs are scoped to a region and project. Pass `--cli-region={region}` explicitly.
- If `--project_id` is omitted, KooCLI uses `cli-project-id` from the profile or the parent
  project of the region in the authentication information.
- `ListTraceResources` requires `--domain_id` (account ID) instead of `--project_id`.

## Verification

```bash
hcloud CTS ListTrackers --cli-region=cn-north-4 --project_id={project_id}
```

A successful JSON response means CLI + credentials are functional.