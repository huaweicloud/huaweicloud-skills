# CLI Installation Guide

## Installing hcloud CLI

### Prerequisites

- Python 3.8+ or Node.js 16+
- Huawei Cloud account with AK/SK credentials

### Installation

**Official installer (recommended)**
```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

> **Note:** Do NOT use `pip install hcloud` — the PyPI package `hcloud` is the Hetzner Cloud SDK, not Huawei Cloud KooCLI. Always use the official installer script above.

### Authentication

Configure credentials interactively (recommended):
```bash
hcloud configure
```

Or set environment variables:
```bash
# Set HUAWEI_ACCESS_KEY, HUAWEI_SECRET_KEY, and HUAWEI_REGION in your shell
# Example: export HUAWEI_REGION=cn-north-4
```

### Verify Installation

```bash
hcloud configure list
```

Check that a valid profile exists with `accessKeyId` and `secretAccessKey` populated.

### Obtain Domain ID

All CC APIs require `--domain_id` (account ID). Find it at:

**Console → IAM (Identity and Access Management) → My Credentials → Account ID**

The account ID is a string like `0a1234567890abcdef...`. Save it for use in CC commands.
