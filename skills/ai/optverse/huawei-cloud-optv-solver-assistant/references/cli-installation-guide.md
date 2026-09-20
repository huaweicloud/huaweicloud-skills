# CLI Installation Guide

## Overview

This document describes how to install, configure, and verify Huawei Cloud KooCLI (hcloud) for the OptVerse Solver Assistant skill.

## 1. Installation

### 1.1 Download KooCLI

Download the latest KooCLI from the official page:

```
https://support.huaweicloud.com/quickstart-hcli/hcli_01.html
```

### 1.2 Windows Installation

```bash
# Extract to a permanent directory (e.g., C:\<your-install-dir>\huaweicloud-cli\)
# Add the directory to system PATH:
setx PATH "%PATH%;C:\<your-install-dir>\huaweicloud-cli"
```

### 1.3 Linux/macOS Installation

```bash
# Extract and add to PATH
tar -xzf hcloud-linux-amd64.tar.gz -C /usr/local/bin/
chmod +x /usr/local/bin/hcloud
```

## 2. Configuration

### 2.1 Accept Privacy Agreement (First Run)

```bash
# First run requires accepting the privacy agreement
printf "y\n" | hcloud version
```

### 2.2 Configure AK/SK

```bash
# Set AK and SK (must be set together)
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>

# Set default region
hcloud configure set --cli-region=cn-east-3
```

### 2.3 Verify Configuration

```bash
hcloud configure list
```

Expected output:

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AKSK",
      "accessKeyId": "DIE****BNX",
      "secretAccessKey": "****",
      "region": "cn-east-3"
    }
  ]
}
```

## 3. OptVerse-Specific Setup

### 3.1 Verify OptVerse Service Access

```bash
# Dryrun to verify endpoint is accessible
hcloud OptVerse ListArtifacts --dryrun --cli-region=cn-east-3 --chat_id=test
```

Expected: Request URL containing `optverse.cn-east-3.myhuaweicloud.com`

### 3.2 Set Environment Variables for create_chat.py

The `createChat` SSE endpoint requires IAM username/domain/password via the Python script:

```bash
# Windows CMD
set OPTVERSE_IAM_USER=<your_iam_username>
set OPTVERSE_IAM_DOMAIN=<your_iam_domain>
set OPTVERSE_IAM_PASSWORD=<your_iam_password>

# Linux/macOS
export OPTVERSE_IAM_USER=<your_iam_username>
export OPTVERSE_IAM_DOMAIN=<your_iam_domain>
export OPTVERSE_IAM_PASSWORD=<your_iam_password>
```

### 3.3 Python Dependencies

```bash
# Python >= 3.8 required
python --version

# Install requests library
pip install requests
```

## 4. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | PATH not configured | Add hcloud directory to PATH |
| `[USE_ERROR]参数--version的格式错误` | Wrong flag format | Use `hcloud version` (not `--version`) |
| SSL certificate error | Self-signed cert in cn-east-3 | Set `skipSecureVerify: true` via `hcloud configure set` |
| `OPTVERSE_AK not set` | Environment variable missing | Set `OPTVERSE_AK` and `OPTVERSE_SK` env vars |
| `requests module not found` | Missing Python dependency | Run `pip install requests` |
