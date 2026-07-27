# Huawei Cloud KooCLI Installation Guide

## Overview
Huawei Cloud KooCLI (hcloud) is the official Huawei Cloud command-line tool that supports managing 100+ cloud services. This guide provides complete installation, configuration, and verification processes for SWR image automation operations.

## Version Requirements
- **Minimum version**: One major version before the latest major version (e.g., if current is 7.x.x, then not lower than 6.x.x)
- **Latest version**: Refer to https://support.huaweicloud.com/wtsnew-hcli/index.html
- **Verification command**: `hcloud version`
- **Update command**: `hcloud update`

## Quick Installation (All Platforms)

### One-click Installation
```bash
# Download and run official installation script (interactive)
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh

# Non-interactive installation (skip confirmation)
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Verify Installation
```bash
# Check version
hcloud version
# Expected output: Current KooCLI version: 7.2.2

# Check help
hcloud --help
```

## Installation Methods for Each Platform

### 1. Linux Systems

#### Detect System Architecture
```bash
echo $HOSTTYPE
# x86_64: AMD 64-bit system
# aarch64: ARM 64-bit system
```

#### Step-by-step Installation
```bash
# AMD 64-bit system
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# ARM 64-bit system
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz"
tar -zxvf huaweicloud-cli-linux-arm64.tar.gz
sudo mv hcloud /usr/local/bin/
```

### 2. macOS Systems

#### Detect System Architecture
```bash
uname -a
# x86_64: AMD 64-bit system (Intel chips)
# arm64: ARM 64-bit system (Apple Silicon)
```

#### Step-by-step Installation
```bash
# Intel chips (AMD 64-bit)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz"
tar -zxvf huaweicloud-cli-mac-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Apple Silicon (ARM 64-bit)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-arm64.tar.gz"
tar -zxvf huaweicloud-cli-mac-arm64.tar.gz
sudo mv hcloud /usr/local/bin/
```

### 3. Windows Systems

#### Installation Steps
1. Download: https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip
2. Extract ZIP file to get `hcloud.exe`
3. Add the directory containing `hcloud.exe` to PATH environment variable

#### Verify Installation
```cmd
hcloud version
```

## Credential Configuration

### Mode A — Long-term AK/SK (permanent access)
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

### Mode B — Temporary AK/SK + SecurityToken (recommended for temporary or delegated access)
```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

> When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication.

### Security Rules
- Never expose AK/SK/SecurityToken values in code, conversation, or commands
- Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
- Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, `HUAWEI_CLOUD_SECURITY_TOKEN`
- Prefer IAM users over root account for cloud operations
- Enable MFA for sensitive operations

## SWR-Specific Verification

```bash
# Verify SWR service is available
hcloud SWR --help

# Test read operation
hcloud SWR ListSyncRegions --cli-region=cn-north-4

# Test namespace query
hcloud SWR ShowNamespaceAuth --namespace=<your-namespace> --cli-region=cn-north-4
```
