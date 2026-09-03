# CLI Installation Guide

## hcloud CLI Installation

### Install hcloud

```bash
# Download the official installer script, then execute
curl -sSL -o hcloud_install.sh https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh
```

> **Note:** Do NOT use `pip install hcloud` — the PyPI package `hcloud` is the Hetzner Cloud SDK, not Huawei Cloud KooCLI. Always use the official installer script above.

### Configure Authentication

**Option 1: Interactive configuration (recommended)**
```bash
hcloud configure
```
Follow the prompts to enter AK, SK, and region.

**Option 2: Environment variables**
```bash
# Set AK/SK via secure prompt — never hardcode secrets in scripts
read -rsp "Access Key ID: "     HUAWEI_ACCESS_KEY; echo
read -rsp "Secret Access Key: " HUAWEI_SECRET_KEY; echo
export HUAWEI_ACCESS_KEY HUAWEI_SECRET_KEY
export HUAWEI_REGION="cn-north-4"
```

### Verify Installation

```bash
hcloud configure list
```

Check that a valid profile exists with AK/SK configured.

### Obtain Domain ID

All CC GCB APIs require `--domain_id` (account ID). Obtain it from:

1. Huawei Cloud Console → IAM → My Credentials → Account ID
2. Or via CLI:
   ```bash
   hcloud IAM KeystoneListAuthDomains --cli-region=cn-north-4
   ```

## Reference

- Official guide: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
