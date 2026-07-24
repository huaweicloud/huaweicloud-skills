# CLI Installation Guide

## hcloud CLI (KooCLI) Installation

### Linux (x86_64)

```bash
curl -sSL https://obs.cn-north-4.myhuaweicloud.com/hcloud_client/hcloud_install.sh | bash
```

### Linux (ARM64)

```bash
curl -sSL https://obs.cn-north-4.myhuaweicloud.com/hcloud_client/hcloud_install.sh | bash
```

### macOS

```bash
curl -sSL https://obs.cn-north-4.myhuaweicloud.com/hcloud_client/hcloud_install.sh | bash
```

### Windows

Download from: https://obs.cn-north-4.myhuaweicloud.com/hcloud_client/hcloud.exe

Or use PowerShell:

```powershell
Invoke-WebRequest -Uri "https://obs.cn-north-4.myhuaweicloud.com/hcloud_client/hcloud_install.sh" -OutFile "hcloud_install.sh"
bash hcloud_install.sh
```

## Authentication Configuration

### Method 1: Interactive Configuration

```bash
hcloud configure
```

Follow the prompts to enter:
- AK (Access Key ID)
- SK (Secret Access Key)
- Region (e.g., cn-north-4)
- Project ID (optional, auto-detected)

### Method 2: Environment Variables

```bash
export HUAWEI_ACCESS_KEY="your-ak"
export HUAWEI_SECRET_KEY="your-sk"
export HUAWEI_REGION="cn-north-4"
```

Or using alternative variable names:

```bash
export HWC_AK="your-ak"
export HWC_SK="your-sk"
export HWC_REGION="cn-north-4"
```

### Method 3: Configuration File

```bash
hcloud configure set --cli-region=cn-north-4 --cli-access-key=your-ak --cli-secret-key=your-sk
```

## Verification

```bash
# Check CLI version
hcloud --version

# List available RDS commands
hcloud RDS --help

# Test authentication
hcloud RDS ListInstances --cli-region=cn-north-4
```

## Python SDK Installation

```bash
pip install huaweicloudsdkrds
pip install huaweicloudsdkcore
```

### SDK Authentication

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkrds.v3.rds_client import RdsClient
from huaweicloudsdkcore.region.region import Region

credentials = BasicCredentials() \
    .with_ak(os.environ.get('HUAWEI_ACCESS_KEY')) \
    .with_sk(os.environ.get('HUAWEI_SECRET_KEY'))

client = RdsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(Region.value_of("cn-north-4")) \
    .build()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: hcloud` | Add hcloud to PATH: `export PATH=$PATH:~/hcloud/` |
| `Authentication failed` | Verify AK/SK are correct and not expired |
| `Region not found` | Use valid region ID (e.g., cn-north-4, cn-east-3) |
| `Permission denied` | Check IAM policies include RDS permissions |
| `SDK import error` | Install SDK: `pip install huaweicloudsdkrds huaweicloudsdkcore` |
