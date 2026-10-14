# KooCLI Installation and Authentication Guide

This Skill uses the Huawei Cloud KooCLI (`hcloud`) command-line tool.

## Installation

### Linux / macOS

```bash
# Download the KooCLI release package from the official Huawei Cloud OBS bucket
curl -fL -o hcloud.tar.gz https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz

# Verify integrity with SHA256 (compare against the checksum published in the
# official release notes: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html)
sha256sum hcloud.tar.gz

tar -xzf hcloud.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/

# Verify
hcloud version
```

> Note: always verify the downloaded package checksum before installing; never
> pipe remote scripts straight into a shell.

Official reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

## Authentication

### Option A: hcloud CLI profile (recommended)

```bash
hcloud configure set --cli-region=cn-north-4 \
  --access-key={AK} --secret-key={SK}
hcloud configure show          # verify
```

### Option B: environment variables (agent-friendly)

```bash
export HUAWEI_ACCESS_KEY={AK}
export HUAWEI_SECRET_KEY={SK}
# or
export HUAWEICLOUD_SDK_AK={AK}
export HUAWEICLOUD_SDK_SK={SK}
```

The Kubernetes CLI automatically picks up these environment variables.

## Verification

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1
```

If this returns the server list (or an empty list), the CLI is authenticated and working.

## Notes

- Upgrade KooCLI when commands are missing: `hcloud update -y`
- Service name is `ECS` (metadata key `ecs`); operation names are PascalCase.