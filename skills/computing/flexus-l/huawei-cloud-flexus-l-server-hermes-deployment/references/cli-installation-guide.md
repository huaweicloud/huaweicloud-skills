# CLI Installation Guide

## Overview

This document describes how to install and configure the Huawei Cloud CLI (`hcloud`) required by the Hermes deployment skill. The `hcloud` CLI is used for authentication and API operations.

## Installation Methods

### Method 1: Using curl (Linux / macOS)

```bash
# Download and install
curl -O https://huaweicloud.com/hcloud/cli/latest/hcloud_linux_arm64.tar.gz
tar -xzf hcloud_linux_arm64.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/hcloud

# Verify installation
hcloud --version
```

### Method 2: Using apt (Debian / Ubuntu)

```bash
# Add repository and install
wget -q https://huaweicloud.com/hcloud/cli/latest/hcloud.list -O /tmp/hcloud.list
sudo mv /tmp/hcloud.list /etc/apt/sources.list.d/hcloud.list
sudo apt-get update
sudo apt-get install huaweicloud-cli

# Verify installation
hcloud --version
```

### Method 3: Using yum (CentOS / RHEL)

```bash
# Add repository and install
sudo yum install -y https://huaweicloud.com/hcloud/cli/latest/hcloud_x86_64.rpm

# Verify installation
hcloud --version
```

## Configuration

### Configure AK/SK

```bash
# Interactive configuration
hcloud configure

## Non-interactive Configuration (Environment Variables Recommended)
# Use environment variables to set credentials (safer than CLI arguments):
# export HW_ACCESS_KEY="your_access_key"
# export HW_SECRET_KEY="your_secret_key"
hcloud configure set
```

### Verify Configuration

```bash
# Test authentication
hcloud IAM KeystoneListUsers --cli-region=cn-north-4

# Expected output: API response with user list or confirmation message
```

## Environment Variables (Alternative)

If you prefer not to use `hcloud configure`, you can use environment variables:

```bash
# Set credentials (long-term)
export HW_ACCESS_KEY="your_access_key"
export HW_SECRET_KEY="your_secret_key"

# Or for temporary credentials
export HW_ACCESS_KEY="your_temp_ak"
export HW_SECRET_KEY="your_temp_sk"
export HW_SECURITY_TOKEN="your_security_token"

# Set default region
export HW_REGION="cn-north-4"
```

## Verifying Credentials

```bash
# Test with env vars
hcloud IAM KeystoneListUsers --cli-region=cn-north-4
```

If the command returns a valid JSON response, your credentials are correctly configured.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: hcloud` | Ensure hcloud is installed and in PATH |
| `Authentication failure` | Check AK/SK values and ensure they are active |
| `Region not supported` | Use `--cli-region` with a valid region (e.g., cn-north-4, cn-east-3) |
| `Temporary credential expired` | Refresh temporary credentials via STS service |