# CLI Installation Guide

## hcloud CLI Installation

### Install

```bash
# Linux/macOS — download first, then execute
curl -sSL -o /tmp/hcloud-install.sh https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
bash /tmp/hcloud-install.sh

# Or download from:
# https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
```

### Configure Credentials

```bash
# Interactive configuration (recommended)
hcloud configure

# Or via environment variables — inject at runtime, never hardcode
#   HUAWEI_ACCESS_KEY  — your access key ID
#   HUAWEI_SECRET_KEY  — your secret access key
# In Python: os.environ.get('HUAWEI_ACCESS_KEY'), os.environ.get('HUAWEI_SECRET_KEY')
export HUAWEI_REGION="cn-north-4"
```

### Verify

```bash
hcloud configure list
```

Check that a valid profile exists with AK/SK configured.

## CC Service Notes

- Central Network is a global service in Cloud Connect.
- The `--domain_id` parameter is required for all Central Network commands. Obtain it from IAM → My Credentials → Account ID.
- Use any region where CC is available (e.g., `cn-north-4`) for `--cli-region`.
