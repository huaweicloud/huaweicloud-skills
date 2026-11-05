# hcloud CLI Installation Guide

## Prerequisites

- A Huawei Cloud account with valid AK/SK credentials
- Network access to Huawei Cloud API endpoints

## Install KooCLI (hcloud)

### Linux / macOS

```bash
# One-click install
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh | bash

# Verify
hcloud version
```

### Windows

Download the installer from the official KooCLI website and follow the wizard, or use
the PowerShell one-click install script from the same URL.

### Upgrade

```bash
hcloud update -y
```

## Authentication Configuration

Configure credentials interactively:

```bash
hcloud configure init
```

Or write the configuration file manually (not recommended). Verify configuration:

```bash
hcloud configure list
```

### Environment Variables (optional)

If you prefer environment variables instead of `hcloud configure`, export them in your
shell session (set them outside the skill / conversation):

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key>
export HUAWEICLOUD_SDK_SK=<your-secret-key>
export HUAWEICLOUD_SDK_REGION=cn-north-4
```

Alternatively `HW_ACCESS_KEY` / `HW_SECRET_KEY` are honored by the bundled scripts.

> **Security**: never pass AK/SK as command-line arguments, never commit them, never
> print them in conversations or logs.

## Verify Access

```bash
# Confirm credentials are active
hcloud configure list

# Confirm both services this skill uses are available
hcloud EIP --help
hcloud CES --help
```

If `hcloud configure list` shows no valid profile, obtain AK/SK from the
[Access Keys console](https://console.huaweicloud.com/iam/#/mine/accessKey) and
configure them in your terminal before continuing.
