# Huawei Cloud KooCLI Installation Guide

## Overview
Huawei Cloud KooCLI (hcloud) is the official Huawei Cloud command-line tool that supports managing 100+ cloud services. This guide provides complete installation, configuration, and verification processes.

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
echo $HOSTTYPE
# If empty, use:
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
# Expected output: Current KooCLI version: 7.2.2
```

### 4. Docker Environment

#### Using Official Image
```bash
# Pull and run
docker run --rm -it swr.cn-north-4.myhuaweicloud.com/huawei-cloud/koocli:latest version
```

#### Custom Image
```dockerfile
FROM ubuntu:latest
RUN apt-get update -y && apt-get install curl -y
RUN curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/hcloud"]
```

Build and use:
```bash
# Build image
docker build -t hcloudcli .

# Run command
docker run --rm -it hcloudcli version
```

## Post-installation Configuration

### Auto-completion Configuration
```bash
# Enable auto-completion
hcloud auto-complete on

# Reload shell configuration
# Bash: source ~/.bashrc
# Zsh: source ~/.zshrc
```

### Multi-environment Configuration
```bash
# Create development environment configuration
hcloud configure init --cli-profile dev

# Create test environment configuration
hcloud configure init --cli-profile test

# Create production environment configuration
hcloud configure init --cli-profile prod

# View all configurations
hcloud configure list

# Use specific configuration
hcloud ECS NovaListServers --cli-profile=dev --cli-region=cn-north-4
```

## Troubleshooting

### Common Installation Issues

#### Insufficient Permissions
```bash
# Linux/macOS: Use sudo
sudo bash ./hcloud_install.sh

# Or install to user directory
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -d ~/.local/bin
```

#### Command Not Found
```bash
# Check PATH
echo $PATH
which hcloud

# Manually add to PATH
export PATH=$PATH:/usr/local/bin
# Or
export PATH=$PATH:$(pwd)
```

#### sha256sum Command Not Found
```bash
# Ubuntu/Debian:
sudo apt-get install coreutils

# CentOS/RHEL:
sudo yum install coreutils

# macOS:
brew install coreutils
```

### Network Issues
```bash
# Test network connection
ping cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com

# Use proxy
export http_proxy=http://proxy:port
export https_proxy=http://proxy:port
```

## Updates and Maintenance

### Update KooCLI
```bash
# Interactive update
hcloud update

# Or reinstall latest version
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Uninstall KooCLI
```bash
# Linux/macOS manual uninstallation:
sudo rm -f /usr/local/bin/hcloud
sudo rm -rf /usr/local/hcloud/
rm -rf ~/.hcloud/

# Windows manual uninstallation:
# 1. Delete hcloud.exe file
# 2. Remove relevant directory from PATH
# 3. Delete C:\Users\{username}\.hcloud\ directory
```

### Clean Cache
```bash
# Clean KooCLI cache
rm -rf ~/.hcloud/cache/

# Clean downloaded files
rm -f hcloud_install.sh huaweicloud-cli-*.tar.gz huaweicloud-cli-*.zip
```

## Best Practices

### Version Management
- Use fixed versions for production environments
- Use latest versions for test environments
- Record installed version numbers

### Environment Isolation
- Create independent configurations for different environments
- Use environment variables to store sensitive information
- Regularly backup configuration files

### Automated Deployment
```bash
#!/bin/bash
set -e

# Download installation script
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh

# Install KooCLI
bash ./hcloud_install.sh -y

# Verify installation
hcloud version
```

### Docker Best Practices
```bash
# Use volume to persist configuration
docker run --rm -it \
  -v ~/.hcloud:/root/.hcloud \
  swr.cn-north-4.myhuaweicloud.com/huawei-cloud/koocli:latest \
  version

# Create alias to simplify usage
alias hcloud-docker='docker run --rm -it -v ~/.hcloud:/root/.hcloud swr.cn-north-4.myhuaweicloud.com/huawei-cloud/koocli:latest'
```

### Version Compatibility
- **KooCLI 7.2.2+**: Supports `--cli-x-project-id` parameter
- **KooCLI 6.2.4+**: Supports `--cli-auth-type` parameter
- **KooCLI 5.3.4+**: Supports SSO configuration parameters

---

**Tip**: This guide provides complete KooCLI installation and configuration processes. Please strictly follow security rules to protect credential security.