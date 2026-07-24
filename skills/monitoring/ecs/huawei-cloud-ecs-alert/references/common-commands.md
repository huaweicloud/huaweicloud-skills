# Common Commands Reference

Quick reference for commonly used commands - avoid duplicating these examples across multiple documents.

## Credential Configuration

```bash
# View current configuration
hcloud configure list

# Configure AK/SK (must set both)
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>

# Configure default region
hcloud configure set --cli-region=cn-north-4

# Interactive configuration (recommended for first-time use)
hcloud configure
```

## Verification Commands

### Basic Verification

```bash
# Check CLI version (should be >= 7.2.2)
hcloud version

# Check credential configuration status
hcloud configure list
```

### API Access Verification

```bash
# Verify ECS API access
hcloud ECS ListServersDetails --cli-region=cn-north-4

# Verify CES API access
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-4

# Verify SMN API access
hcloud SMN ListTopics --cli-region=cn-north-4
```

## Region Configuration

| Region Code | Region Name | Description |
|-------------|-------------|-------------|
| cn-north-4 | Beijing 4 | Recommended for testing |
| cn-north-1 | Beijing 1 | |
| cn-east-3 | Shanghai 1 | |
| cn-east-2 | Shanghai 2 | |
| cn-south-1 | Guangzhou | |
| ap-southeast-1 | Hong Kong | |

> **Note**: CES service is available in all Huawei Cloud regions. Choose the region where your ECS instances are located.

## Common Troubleshooting

### hcloud Command Not Found

```bash
# Linux/macOS - Use official installation script
curl -o hcloud_install.sh https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh

# Or install via pip
pip install hcloud
```

### Authentication Failure (401/403)

```bash
# Clear existing configuration
hcloud configure set --cli-access-key= --cli-secret-key=

# Reconfigure with valid credentials
hcloud configure

# Verify configuration
hcloud configure list
```

### Insufficient Permissions

Add the following policies to the user in IAM:

- `CES FullAccess` (Alarm management)
- `ECS ReadOnlyAccess` (Instance query)
- `SMN FullAccess` (Notification configuration)

## Parameter Format Specification

hcloud requires `--param=value` format (with equals sign), not space-separated:

```bash
# ✅ Correct
hcloud CES ListAlarms --region=cn-north-4

# ❌ Incorrect
hcloud CES ListAlarms --region cn-north-4
```

## Related Documents

- [CLI Installation Guide](cli-installation-guide.md)
- [IAM Policies](iam-policies.md)
- [Troubleshooting](troubleshooting.md)
