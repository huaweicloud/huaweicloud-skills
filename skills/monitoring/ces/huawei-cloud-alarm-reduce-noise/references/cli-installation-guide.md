# Huawei Cloud KooCLI Installation Guide

## Overview
Huawei Cloud KooCLI (hcloud) is the official Huawei Cloud command-line tool that supports managing 100+ cloud services. This skill uses hcloud to:
- Auto-fetch Project ID via `hcloud IAM KeystoneListProjects`
- Fetch CES alarm histories via `hcloud CES ListAlarmHistories`
- Fetch CES alarm rules via `hcloud CES ListAlarmRules`
- Fetch AOM alarm rules via `hcloud AOM ListMetricOrEventAlarmRule`

This guide provides complete installation, configuration, and verification processes.

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

```

### Verify Installation
```bash
# Check version
hcloud version
# Expected output: Current KooCLI version: 7.x.x

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

#### Step-by-Step Installation
```bash
# AMD 64-bit system
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
mv hcloud /usr/local/bin/  # requires write permission

# ARM 64-bit system
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz"
tar -zxvf huaweicloud-cli-linux-arm64.tar.gz
mv hcloud /usr/local/bin/  # requires write permission
```

### 2. macOS Systems

#### Detect System Architecture
```bash
uname -a
# x86_64: AMD 64-bit system (Intel chips)
# arm64: ARM 64-bit system (Apple Silicon)
```

#### Step-by-Step Installation
```bash
# Intel chips (AMD 64-bit)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz"
tar -zxvf huaweicloud-cli-mac-amd64.tar.gz
mv hcloud /usr/local/bin/  # requires write permission

# Apple Silicon (ARM 64-bit)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-arm64.tar.gz"
tar -zxvf huaweicloud-cli-mac-arm64.tar.gz
mv hcloud /usr/local/bin/  # requires write permission
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

### 4. Docker Environment

#### Using Official Image
```bash
docker run --rm -it swr.cn-north-4.myhuaweicloud.com/huawei-cloud/koocli:latest version
```

#### Custom Image
```dockerfile
FROM ubuntu:latest
RUN apt-get update -y && apt-get install curl -y
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/hcloud"]
```

## Post-installation Configuration

### AK/SK Configuration
This skill reads AK/SK from environment variables. Configure hcloud with the same credentials:

```bash
# Method 1: Interactive configuration
hcloud configure init

# Method 2: Environment variables (recommended for this skill)
export HW_ACCESS_KEY=your_ak
export HW_SECRET_KEY=your_sk

# Method 3: Use --cli-profile with named profile
hcloud configure init --cli-profile alarm-reduce-noise
```

### Multi-environment Configuration
```bash
# Create named profiles for different environments
hcloud configure init --cli-profile dev
hcloud configure init --cli-profile prod

# Use default profile (or add --cli-profile=<name> for a named profile)
hcloud CES ListAlarmHistories --cli-region=cn-north-4
```

## Verification for This Skill

After installation, verify hcloud can access the APIs used by this skill:

```bash
# Test CES alarm history access
hcloud CES ListAlarmHistories --cli-region=cn-north-4 --limit=1

# Test CES alarm rule access
hcloud CES ListAlarmRules --cli-region=cn-north-4 --limit=1

# Test AOM alarm rule access
hcloud AOM ListMetricOrEventAlarmRule --cli-region=cn-north-4 --limit=1

# Test IAM project list (for Project ID auto-fetch)
hcloud IAM KeystoneListProjects --cli-region=cn-north-4
```

## Troubleshooting

### Common Installation Issues

#### Insufficient Permissions
```bash
bash ./hcloud_install.sh  # requires write permission
```

#### Command Not Found
```bash
# Check PATH
which hcloud
export PATH=$PATH:/usr/local/bin
```

#### sha256sum Command Not Found
```bash
# Ubuntu/Debian:
apt-get install coreutils  # requires write permission
# CentOS/RHEL:
yum install coreutils  # requires write permission
```

### Network Issues
```bash
# Test connectivity to OBS download endpoint
ping cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com
```

## Updates and Maintenance

### Update KooCLI
```bash
hcloud update
```

### Uninstall KooCLI
```bash
# Linux/macOS:
rm -f /usr/local/bin/hcloud  # requires write permission
rm -rf /usr/local/hcloud/  # requires write permission
rm -rf ~/.hcloud/
```

### Clean Cache
```bash
rm -rf ~/.hcloud/cache/
```

## Best Practices

- Use fixed versions for production environments
- Store AK/SK in environment variables, never in plaintext config files
- Regularly update KooCLI to get the latest CES and AOM API support
- Use `--cli-region` to specify region for each hcloud command call

## References

- KooCLI Official Documentation: https://support.huaweicloud.com/wtsnew-hcli/index.html
- KooCLI Download: https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
