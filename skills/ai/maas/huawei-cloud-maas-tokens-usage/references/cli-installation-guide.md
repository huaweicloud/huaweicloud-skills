# Prerequisites Installation Guide

## Python3 + huaweicloudsdkcore

```bash
# Check Python3 version
python3 --version  # Requires >= 3.8

# Install SDK signing library
pip3 install --user huaweicloudsdkcore

# Verify
python3 -c "import huaweicloudsdkcore; print('SDK OK')"
```

## Credentials Configuration

### Method 1: Environment variables (recommended)

```bash
export HW_ACCESS_KEY=<your-access-key-id>
export HW_SECRET_KEY=<your-access-key-secret>
```

### Method 2: Credentials file

Create a file supporting three formats:

```
# One value per line
<AK>
<SK>

# Comma-separated
<AK>,<SK>

# KEY=VALUE format
HW_ACCESS_KEY=<AK>
HW_SECRET_KEY=<SK>
```

Usage: `--credentials-file /path/to/aksk.txt`

> **Security reminder:**
> - Never provide AK/SK directly in conversation
> - Never hardcode AK/SK in scripts

## MaaS Service Regions

| Region | Region ID |
|--------|-----------|
| Southwest-Guiyang-1 | cn-southwest-2 |

> MaaS ShowStatistics API currently only supports Southwest-Guiyang-1 region.
