# CLI Installation Guide

## Overview

This skill performs Huawei Cloud operations via local `hcloud` CLI (KooCLI) and Python dispatcher. The only entry point is:

```bash
python3 scripts/devkit_remote.py --region ${HUAWEI_REGION} check
```

Never bypass the dispatcher to directly call SDK, curl requests, manual IAM signing, or other cloud CLIs.

## 1. Python Environment Installation

### Linux/macOS
```bash
# Check Python version
python3 --version

# If not installed, use package manager
# Ubuntu/Debian
apt update
apt install python3 python3-pip -y

# CentOS/RHEL
yum install python3 python3-pip -y

# macOS (with Homebrew)
brew install python3
```

### Windows (PowerShell)
```powershell
python --version
# If not installed, download from https://www.python.org/downloads/
```

### Verify Installation
```bash
python3 --version
# Expected output: Python 3.8.x or higher
```

## 2. Dependency Installation

The only Python dependency is `paramiko` (Layer 1 SSH connection):

```bash
pip install "paramiko>=3.0.0" -i https://repo.huaweicloud.com/repository/pypi/simple
```

### Verify Installation
```bash
python3 -c "import paramiko; print('paramiko installed successfully')"
```

## 3. Huawei Cloud KooCLI Installation

### Linux (x86_64)
```bash
Invoke-WebRequest -Uri https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -OutFile ./hcloud_install.sh && bash ./hcloud_install.sh
```
Downloads to `/usr/local/hcloud/` directory by default and moves to `/usr/local/bin/`. To skip interactive mode, add `-y`:
```bash
Invoke-WebRequest -Uri https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -OutFile ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Windows (PowerShell)
```powershell
Invoke-WebRequest -Uri "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

### Verify Installation
```bash
hcloud version
# Expected output: KooCLI version: 7.2.2 or higher
```

## 4. AK/SK Configuration

### Obtain AK/SK

1. Log in to Huawei Cloud console: https://console.huaweicloud.com/
2. Click avatar in upper right corner → My Credentials
3. Select Access Keys from the left panel
4. Click Create Access Key
5. Download CSV file (contains AK and SK)

### Check AK/SK Configuration Status

After installing hcloud, must check whether AK/SK is configured:

```bash
hcloud configure list
```

If the output does not contain `access-key` and `secret-key`, AK/SK is not configured. Follow the steps below to configure.

### Configuration Methods

> **🔴 AI NEVER executes `hcloud configure set` on behalf of the user. AI NEVER reads AK/SK from env vars and writes them into hcloud profile. AI only performs `hcloud configure list` existence checks. Credential configuration is the user's responsibility.**

> **🔴 Environment Detection**: AI MUST detect the current OS environment (Windows/Linux) and display ONLY the corresponding platform's configuration methods below. **NEVER** display both Windows and Linux configurations at the same time. **NEVER** display the "Windows Environment" or "Linux Environment" heading to the user.

When AK/SK is not configured, AI displays: "For security constraints, AK/SK cannot be received in conversation. Please configure AK/SK following the steps below:"

#### Windows Environment

**Method 1: Configure Environment Variables**

1. Open System Properties --> Advanced --> Environment Variables --> System Variables --> New
2. Add two variables:
   - Variable name: `HUAWEI_ACCESS_KEY`, Value: your Huawei Cloud Access Key ID
   - Variable name: `HUAWEI_SECRET_KEY`, Value: your Huawei Cloud Secret Access Key
3. After saving, restart this program (or open a new terminal window)

**Method 2: hcloud Configuration**

1. Open terminal, use hcloud to configure AK/SK

hcloud configuration template:
```bash
hcloud configure set --cli-profile=default --cli-region=<your_region> --cli-access-key=<your_ak> --cli-secret-key=<your_sk>
```

> If you don't have AK/SK yet, create them in Huawei Cloud console --> My Credentials --> Access Keys

#### Linux Environment

**Method 1: Configure Environment Variables**

1. Configure permanent environment variables via shell config file:

```bash
echo 'export HUAWEI_ACCESS_KEY="your Huawei Cloud Access Key ID"' >> /etc/profile
echo 'export HUAWEI_SECRET_KEY="your Huawei Cloud Secret Access Key"' >> /etc/profile
source /etc/profile
```

2. Or define temporary environment variables directly in shell terminal:

```bash
export HUAWEI_ACCESS_KEY="your Huawei Cloud Access Key ID"
export HUAWEI_SECRET_KEY="your Huawei Cloud Secret Access Key"
```

**Method 2: hcloud Configuration**

1. Open terminal, use hcloud to configure AK/SK

hcloud configuration template:
```bash
hcloud configure set --cli-profile=default --cli-region=<your_region> --cli-access-key=<your_ak> --cli-secret-key=<your_sk>
```

> If you don't have AK/SK yet, create them in Huawei Cloud console --> My Credentials --> Access Keys


### Re-check AK/SK Configuration Status

After user configuration completes, AI re-checks AK/SK (verification only, never executes `hcloud configure set`):

```bash
hcloud configure list
```

- If AK/SK is configured → proceed to next step
- If AK/SK is still not configured → **STOP**, prompt user to reconfigure

❌ **Wrong example**:
```python
# Do NOT hardcode credentials in source code
AK = "AKEXAMPLE123456"  # Security risk!
SK = "SKEXAMPLE789012"  # Security risk!
```

### Credential Priority

1. Explicit tool parameters (`ak=...`, `sk=...`, `region=...`)
2. Active hcloud profile
3. Environment variable fallback (`HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`)

> **🔴 Security**: AK/SK must be passed via environment variables, never exposed in plaintext. SSH credentials come only from `DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` environment variables (User → Machine level). `DEVKIT_ECS_EIP` is obtained only from hcloud query. See [Security Rules](rules.md).

## 5. hcloud Environment Check (Mandatory)

### 5.1 Check hcloud CLI

```bash
hcloud version
```

- Not installed → auto-install (see Section 3)
- Version < 7.2.2 → prompt upgrade

### 5.2 Check AK/SK

```bash
hcloud configure list
```

Not configured → output configuration template and **STOP**.

### 5.3 Verify Connectivity

```bash
hcloud ECS ListCloudServers --cli-region=cn-north-4 --limit=1
```

Failed → warn and **STOP**.

> **Note**: `cn-north-4` is only for connectivity testing, does not determine DevKit server creation region — region is selected by user in Step 2.

## 6. Command Format

Always execute through dispatcher:

```bash
# Check SSH + upload scripts (Step 6.1 + 6.2)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} login

# Install DevKit + Maven (Step 6.3)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} install

# Verify DevKit installation
py scripts/devkit_remote.py --region ${HUAWEI_REGION} verify

# Encrypt nodes.conf passwords & verify SSH to targets
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify

# Check nodes.conf password encryption status (no encryption, no SSH verify)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --check

# Display nodes.conf with passwords masked (safe for chat)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} encrypt-verify --mask

# Execute scan (Step 8)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} scan stmt

# Download reports (Step 9)
py scripts/devkit_remote.py --region ${HUAWEI_REGION} download-report --local-dir ${LOCAL_DIR}
```

## 7. Verification

Execute read-only check:

```bash
py scripts/devkit_remote.py --region ${HUAWEI_REGION} check
```

Expected results:
- `success=true`
- JSON output is parseable
- No plaintext credential values in output
- Region comes from user selection (Step 2, 4 options: cn-north-4 / cn-east-3 / cn-south-1 / cn-southwest-2)
- Account balance checked (warn if balance < 20 CNY)

## 8. FAQ

### Q: pip install failed?

✅ **Solution**:
```bash
# Try with --user flag
pip install --user paramiko

# Or use mirror
pip install -i https://repo.huaweicloud.com/repository/pypi/simple paramiko
```

### Q: hcloud command not found?

✅ **Solution**:
```bash
# Check if hcloud is in PATH
which hcloud

# If not, add to PATH (Linux/macOS)
export PATH=$PATH:~/hcloud/

# Reinstall
Invoke-WebRequest -Uri https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -OutFile ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Q: AK/SK authentication failed?

✅ **Solution**:
```bash
# Verify configuration
hcloud configure list

# Reconfigure
hcloud configure set --cli-profile=default --cli-access-key=<your_ak> --cli-secret-key=<your_sk>

# Test connectivity
hcloud ECS ListCloudServers --cli-region=cn-north-4 --limit=1
```

### Q: Insufficient permissions?

✅ **Solution**:
```bash
# Check file permissions
stat ~/.config/hcloud/

# Fix permissions
chown ~/.config/hcloud/config.json
```

### Q: paramiko import failed?

✅ **Solution**:
```bash
pip install paramiko -i https://repo.huaweicloud.com/repository/pypi/simple
```
