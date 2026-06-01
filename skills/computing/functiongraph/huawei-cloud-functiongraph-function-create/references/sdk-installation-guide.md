# SDK Installation Guide

This guide provides step-by-step instructions for installing the Huawei Cloud FunctionGraph Python SDK.

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| Operating System | Windows, Linux, or macOS |
| Python | Version 3.9 or higher |
| Network | Internet access to PyPI |
| Account | Huawei Cloud account with appropriate permissions |

## Python Installation

### Windows

```bash
# Download from python.org
# Or use chocolatey
choco install python

# Verify
python --version
pip --version
```

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3-pip

# CentOS/RHEL
sudo yum install python39 python39-pip

# Verify
python3 --version
pip3 --version
```

### macOS

```bash
# Using Homebrew
brew install python@3.9

# Verify
python3 --version
pip3 --version
```

## SDK Installation

```bash
# Install FunctionGraph SDK
pip install huaweicloudsdkfunctiongraph

# Verify installation
python -c "from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient; print('SDK installed successfully')"
```

## Authentication Configuration

### Environment Variables (Recommended)

```bash
# Linux/macOS
export HUAWEI_AK="your-access-key"
export HUAWEI_SK="your-secret-key"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your-project-id"

# Windows (Command Prompt)
set HUAWEI_AK=your-access-key
set HUAWEI_SK=your-secret-key
set HUAWEI_REGION=cn-north-4
set HUAWEI_PROJECT_ID=your-project-id

# Windows (PowerShell)
$env:HUAWEI_AK="your-access-key"
$env:HUAWEI_SK="your-secret-key"
$env:HUAWEI_REGION="cn-north-4"
$env:HUAWEI_PROJECT_ID="your-project-id"
```

### Security Best Practices

- **🚫 NEVER** commit AK/SK to version control
- **🚫 NEVER** hardcode credentials in source code
- **✅ ALWAYS** use environment variables or configuration files
- **✅ Recommend** using IAM user with minimal permissions
- **✅ Enable** MFA for production accounts

## Common Regions

| Region Code | Region Name |
|-------------|-------------|
| cn-north-4 | North China - Beijing 4 |
| cn-north-1 | North China - Beijing 1 |
| cn-east-3 | East China - Shanghai 1 |
| cn-south-1 | South China - Guangzhou |
| ap-southeast-1 | Hong Kong |

## Verification Script

```python
#!/usr/bin/env python3
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion

# Get credentials from environment
ak = os.environ.get('HUAWEI_AK')
sk = os.environ.get('HUAWEI_SK')
region = os.environ.get('HUAWEI_REGION', 'cn-north-4')
project_id = os.environ.get('HUAWEI_PROJECT_ID')

if not all([ak, sk, project_id]):
    print("❌ Missing credentials. Please set HUAWEI_AK, HUAWEI_SK, and HUAWEI_PROJECT_ID")
    exit(1)

# Create credentials
credentials = BasicCredentials(ak, sk, project_id)

# Create client
client = FunctionGraphClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(FunctionGraphRegion.value_of(region)) \
    .build()

print(f"✅ SDK configured successfully for region: {region}")
```

## Troubleshooting

### ImportError

```bash
# If import fails, reinstall SDK
pip uninstall huaweicloudsdkfunctiongraph
pip install huaweicloudsdkfunctiongraph

# Or upgrade pip first
pip install --upgrade pip
pip install huaweicloudsdkfunctiongraph
```

### Authentication Error

- Verify AK/SK are correct
- Check if IAM user has required permissions
- Confirm project_id matches the region

### Network Error

- Check internet connectivity
- Verify firewall allows HTTPS (443) to Huawei Cloud endpoints
- Try using a different region

## Additional Resources

- [Huawei Cloud FunctionGraph Documentation](https://support.huaweicloud.com/productdesc-functiongraph/index.html)
- [Python SDK Reference](https://github.com/huaweicloud/huaweicloud-sdk-python)
