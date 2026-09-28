# Huawei Cloud KooCLI Installation and Configuration Guide

This guide details how to install and authenticate KooCLI (`hcloud`) for managing Server Migration Service (SMS) workflows.

## 1. KooCLI Installation

### Linux
Download and execute the installer script for your target site:
```bash
# China Site (cn-north-4):
curl -sSL "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh" -o ./hcloud_install.sh && bash ./hcloud_install.sh -y

# International Site (Singapore ap-southeast-3):
curl -sSL "https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/hcloud_install.sh" -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Windows (PowerShell)
Download the installation package for your target site and add KooCLI to user PATH:
```powershell
# China Site (cn-north-4):
Invoke-WebRequest -Uri "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip" -OutFile "hcloud.zip"

# International Site (Singapore ap-southeast-3):
Invoke-WebRequest -Uri "https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip" -OutFile "hcloud.zip"

# Extract and register to PATH:
Expand-Archive -Path "hcloud.zip" -DestinationPath "$env:LOCALAPPDATA\Programs\KooCLI" -Force
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:LOCALAPPDATA\Programs\KooCLI", [EnvironmentVariableTarget]::User)
```

## 2. Authentication Configuration

KooCLI supports multiple authentication methods. Choose between Profile configuration or Environment variables.

### Method A: Interactive Profile Setup (Recommended)
Run the following interactive command in your terminal. KooCLI will prompt for credentials securely without echoing secrets to the screen or logs:
```bash
hcloud configure
```
Input:
- **Access Key ID**: Your Huawei Cloud AK
- **Secret Access Key**: Your Huawei Cloud SK (entered silently)
- **Region**: Target cloud region identifier:
  - **China Site**: `cn-north-4` (Beijing-4), `cn-east-3` (Shanghai-1), `cn-south-1` (Guangzhou)
  - **International Site**: `ap-southeast-3` (Singapore)

Verify profile status:
```bash
hcloud configure list
```

### Method B: Environment Variables
Set credentials in your environment out-of-band:
```bash
# China Site:
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
export HUAWEI_SECRET_KEY="<your-secret-access-key>"
export HUAWEI_REGION="cn-north-4"

# International Site (Singapore):
# export HUAWEI_REGION="ap-southeast-3"
```

## 3. Verify SMS Operations

Run a read-only query to confirm that credentials and region endpoints are functional:
```bash
# China Site:
hcloud SMS ListServers --cli-region=cn-north-4 --limit=1

# International Site (Singapore):
hcloud SMS ListServers --cli-region=ap-southeast-3 --limit=1
```
A valid response containing `count` and `source_servers` confirms operational readiness.
