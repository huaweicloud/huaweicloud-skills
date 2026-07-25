# CLI Installation Guide

This guide describes how to install and configure Huawei Cloud KooCLI (hcloud) to support all operations of the UCS cluster onboarding management skill.

## 1. Install KooCLI

### Linux (x86_64 / arm64)

```bash
# Download the latest version
curl -fsSL https://obs.cn-north-4.myhuaweicloud.com/hcloud/client/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

### Verify Installation

```bash
hcloud --version
```

## 2. Configure Authentication Credentials

### Option 1: Interactive Configuration (Recommended)

```bash
hcloud configure
```

Follow the prompts to enter:
- **AK**: Huawei Cloud access key ID
- **SK**: Huawei Cloud secret access key
- **Region**: Default region (e.g., `cn-north-4`)

### Option 2: Environment Variables (for CI/CD)

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_SECURITY_TOKEN=<your-security-token>  # Required for temporary credentials
```

### Option 3: Configuration File

Credentials are stored in `~/.hcloud/config.json` and can be edited directly:

```json
{
  "profiles": {
    "default": {
      "access_key": "your-ak",
      "secret_key": "your-sk",
      "region": "cn-north-4"
    }
  }
}
```

## 3. Verify Credentials

```bash
# Test UCS API connectivity
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

If quota information is returned, credentials are configured correctly.

## 4. Temporary Credentials (STS) Configuration

When using temporary security tokens (Security Token Service), configure `security_token` additionally:

```bash
export HW_ACCESS_KEY=<sts-ak>
export HW_SECRET_KEY=<sts-sk>
export HW_SECURITY_TOKEN=<sts-token>
```

> ⚠️ Temporary credentials have a validity period and must be re-obtained after expiration.

## 5. Common Issues

### Q: `command not found: hcloud`

Ensure the hcloud installation path is in `PATH`. The default installation path is `~/.hcloud/cli/`.

```bash
export PATH="$HOME/.hcloud/cli:$PATH"
```

### Q: `Authentication failed`

- Verify AK/SK are correct
- Check if temporary credentials have expired
- Confirm the account has UCS-related permissions (see [IAM Permission Policies](iam-policies.md))

### Q: `Region not supported`

Confirm a valid region ID is used. Common regions:

| Region | ID |
|--------|-----|
| Beijing 4 | `cn-north-4` |
| Beijing 1 | `cn-north-1` |
| Shanghai 1 | `cn-east-3` |
| Guangzhou | `cn-south-1` |
| Ulanqab | `cn-north-7` |
