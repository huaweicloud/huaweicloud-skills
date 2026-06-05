# Huawei Cloud CLI (KooCLI) Installation Guide

## Prerequisites

- Python 3.6+
- pip3 (Python package manager)
- Internet connection

## Installation Steps

### Step 1: Install KooCLI

```bash
pip3 install --break-system-packages huaweicloudsdkcore huaweicloudsdkces huaweicloudsdksmn
```

### Step 2: Verify Installation

```bash
hcloud version
```

Expected output:
```
KooCLI Version 7.2.2 Copyright(C) 2020-2026 www.huaweicloud.com
```

### Step 3: Configure Credentials

Run the interactive configuration:

```bash
hcloud configure
```

Follow the prompts:
1. **Profile Name**: `default` (press Enter)
2. **AK (Access Key ID)**: Enter your AK
3. **SK (Secret Access Key)**: Enter your SK
4. **Region**: `cn-north-4` (or your preferred region)
5. **Project ID**: Auto-detected or enter manually

### Step 4: Verify Configuration

```bash
hcloud configure list
```

Expected output should show your configuration with masked AK/SK.

## Troubleshooting

### Issue 1: `hcloud: command not found`

**Solution**: Ensure KooCLI is installed and in your PATH:
```bash
which hcloud
```

If not found, reinstall:
```bash
pip3 install --break-system-packages huaweicloudsdkcore
```

### Issue 2: 403 Forbidden

**Solution**: Check IAM permissions. Ensure your account has:
- `CES FullAccess`
- `SMN FullAccess`
- `ECS FullAccess`

### Issue 3: Invalid AK/SK

**Solution**: 
1. Log in to Huawei Cloud Console
2. Go to "My Credentials" → "Access Keys"
3. Verify AK/SK or create new ones

## Security Best Practices

- ✅ **Never** hardcode AK/SK in scripts or configuration files
- ✅ Use `hcloud configure` to store credentials securely (encrypted)
- ✅ Use environment variables for temporary credentials
- ❌ **Do not** share AK/SK in chat, emails, or code repositories

## Related Documents

- [IAM Policies](iam-policies.md)
- [SMN Subscription Guide](smn-subscription-guide.md)
- [Troubleshooting](troubleshooting.md)
