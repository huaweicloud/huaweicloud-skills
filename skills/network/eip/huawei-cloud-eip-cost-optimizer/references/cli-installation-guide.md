# CLI Installation Guide - hcloud (KooCLI)

## Overview

This guide covers installing and configuring Huawei Cloud KooCLI (`hcloud`), which is the sole CLI backend for the EIP Cost Optimizer skill.

## Prerequisites

- Linux (x86_64 / ARM64), macOS, or Windows
- Internet access to `hwcloudcli.obs.cn-north-4.myhuaweicloud.com`
- Huawei Cloud account with AK/SK credentials

## Installation

### Method 1: Automatic (Recommended)

Run the environment check script with `--fix` flag:

```bash
bash scripts/check_env.sh --fix
```

This will:
1. Download the official installer to a temporary file
2. Validate the script contains hcloud installer signature
3. Execute the installer
4. Clean up the temporary file

### Method 2: Manual Installation

```bash
curl -sSL -o /tmp/hcloud_install.sh https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash /tmp/hcloud_install.sh
rm -f /tmp/hcloud_install.sh
```

### Method 3: Package Manager

```bash
# CentOS/RHEL/EulerOS
yum install -y hcloud

# Ubuntu/Debian (if available in repo)
apt-get install -y hcloud
```

## Post-Installation Verification

```bash
# Check version (accept privacy statement on first run)
hcloud --version
# Expected: >= 7.0.0

# Verify installation path
which hcloud
# Expected: /usr/local/bin/hcloud
```

## Authentication Configuration

### Option A: Environment Variables (Recommended for CI/CD)

```bash
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"
export HW_REGION_NAME="cn-north-4"

# Optional: Temporary credentials
export HW_SECURITY_TOKEN="your-security-token"
```

### Option B: hcloud configure (Recommended for Interactive Use)

```bash
# Interactive configuration - enter credentials via prompts, not command-line arguments
hcloud configure
```

Verify configuration:

```bash
hcloud configure list
```

**Security Note**: Option B stores credentials in `~/.hcloud/` config file with restricted permissions, which avoids exposing AK/SK in `/proc/PID/cmdline`. Prefer this method on shared hosts.

### Option C: IAM Agency (Recommended for ECS Instances)

When running on an ECS instance with an IAM agency bound, hcloud can automatically obtain temporary credentials. No manual configuration needed.

```bash
# Verify agency-based auth works
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4
```

## Connectivity Test

```bash
# Test with a read-only API call
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4

# Expected: JSON output with "publicips" array (may be empty)
# If error: check AK/SK, region, and network connectivity
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `command not found: hcloud` | Not in PATH | Add `/usr/local/bin` to PATH or reinstall |
| `CLI.0501` | Privacy statement not accepted | Run `hcloud --version` and accept |
| `IAME.0501` | Invalid AK/SK | Verify credentials in IAM console |
| `IAME.0503` | AK/SK expired | Generate new AK/SK in IAM console |
| Timeout errors | Network/firewall | Allow outbound HTTPS to `*.myhuaweicloud.com` |
| `VPC.0501` | Region not activated | Activate VPC service in the target region |

## Upgrade

```bash
# Re-run installer (overwrites existing version)
curl -sSL -o /tmp/hcloud_install.sh https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash /tmp/hcloud_install.sh
rm -f /tmp/hcloud_install.sh

# Verify new version
hcloud --version
```

## Uninstall

```bash
rm -f /usr/local/bin/hcloud
rm -rf ~/.hcloud
```

## Related Documentation

- [KooCLI Official Documentation](https://support.huaweicloud.com/cli/index.html)
- [KooCLI Download Page](https://support.huaweicloud.com/cli/reference.html)
- [IAM AK/SK Management](https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html)
