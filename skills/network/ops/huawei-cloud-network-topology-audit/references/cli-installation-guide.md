# CLI Installation Guide

## Installing hcloud (KooCLI)

```bash
# Download and install
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh

# Verify installation
hcloud version
```

## Configuring Authentication

```bash
# Configure with AK/SK
hcloud configure set --cli-access-key=YOUR_ACCESS_KEY --cli-secret-key=YOUR_SECRET_KEY --cli-region=cn-north-4

# Or use environment variables
export HUAWEICLOUD_SDK_AK=YOUR_ACCESS_KEY
export HUAWEICLOUD_SDK_SK=YOUR_SECRET_KEY
```

## Verifying Authentication

```bash
# Test with a simple VPC query
hcloud VPC ListVpcs --cli-region=cn-north-4 --limit=1
```

## Notes

- This skill primarily relies on query skills (path A) and Python SDK scripts (path B). The
  hcloud CLI is only needed for CCE queries via the CCE cluster management skill.
- For most resource types (VPC, ELB, EIP, NAT, ECS, RDS), the Python SDK is used via query
  skills, not the CLI directly.