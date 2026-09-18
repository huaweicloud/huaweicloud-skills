# CLI Installation & Configuration Guide

## Install KooCLI

Download from official site: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

| OS | Download Link |
|----|---------------|
| Windows 64-bit | [Download](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip) |
| Linux AMD 64-bit | [Download](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz) |
| macOS AMD 64-bit | [Download](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz) |

## Installation Steps

1. Download the package for your OS
2. Extract to get `hcloud` (Linux/macOS) or `hcloud.exe` (Windows)
3. Add the executable directory to system PATH
4. Verify installation:

```bash
hcloud version
```

## Authentication Configuration

Set environment variables:

```bash
# Set credentials
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
export HUAWEI_SECRET_KEY="<your-secret-access-key>"
export HUAWEI_REGION="<your-region>"
```

> **Security Note**: Never hardcode AK/SK in scripts. Use environment variables or IAM roles.

## Get AK/SK

1. Login to Huawei Cloud Console
2. Go to "Identity and Access Management" → "My Credentials"
3. Click "Add Access Key"

## Verify Configuration

```bash
# Check configured credentials
hcloud configure list

# Test API call
hcloud WAF ListPolicy --page=1 --pagesize=1
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: hcloud` | Check PATH includes KooCLI directory |
| `Authentication failed` | Verify AK/SK is correct |
| `Permission denied` | Check IAM policy |
