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
hcloud configure set --cli-region=cn-north-7
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
      "region": "cn-north-7"
    }
  ]
}
```

## 3. OptVerse-Specific Setup

### 3.1 Verify OptVerse Service Access

```bash
# Dryrun to verify endpoint is accessible
hcloud OptVerse ListArtifacts --dryrun --cli-region=cn-north-7 --chat_id=test
```

Expected: Request URL containing `optverse.cn-north-7.myhuaweicloud.com`

### 3.2 Configure IAM Credentials File

The `createChat` SSE endpoint requires an IAM token. The scripts obtain it via `hcloud IAM KeystoneCreateUserTokenByPassword`, reading credentials from a config file:

```bash
# Windows: C:\Users\<user>\.config\optverse\credentials
# Linux/macOS: ~/.config/optverse/credentials

iam_user=<your_iam_username>
iam_domain=<your_iam_domain>
iam_password=<your_iam_password>
```

The scripts auto-create this file as an empty template (keys only) on first run — you only need to fill in the three values. The script reads the file in-process and ALWAYS clears the values immediately after use (never displayed, never persisted), even when a cached token is returned. The agent must never read or display this file.

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
| SSL certificate error | Self-signed cert in cn-north-7 | Set `skipSecureVerify: true` via `hcloud configure set` |
| `OPTVERSE_AK not set` | Environment variable missing | Set `OPTVERSE_AK` and `OPTVERSE_SK` env vars |
| `requests module not found` | Missing Python dependency | Run `pip install requests` |
