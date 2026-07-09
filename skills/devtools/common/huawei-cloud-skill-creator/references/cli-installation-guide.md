# hcloud CLI Installation & Configuration Guide

> Read this file when a generated sub-Skill user is using it for the first time or CLI is not installed.

## Install hcloud CLI

```bash
# pip install (recommended)
pip install hcloud

# Verify installation
hcloud --version
```

## Authentication Configuration

Credentials are read from environment variables:

```bash
# Set required environment variables before using CLI
#   HUAWEI_ACCESS_KEY - Your access key ID
#   HUAWEI_SECRET_KEY - Your secret access key
export HUAWEI_REGION="cn-north-4"
```

> **Security reminder:** Never hardcode AK/SK in scripts. Use environment variables or IAM roles. Do not pass plaintext credentials via CLI configuration commands.

## Obtain AK/SK

1. Log in to Huawei Cloud console
2. Navigate to "Identity and Access Management" → "My Credentials"
3. Click "Create Access Key"

## Verify Configuration

```bash
hcloud IAM ListUsers --cli-region=cn-north-4
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `command not found: hcloud` | Check PATH, or reinstall |
| `Authentication failed` | Verify AK/SK is correct |
| `Permission denied` | Check IAM permission policies |
| `Region not found` | Use a valid region, e.g., cn-north-4 |
