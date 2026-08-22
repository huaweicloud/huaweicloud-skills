# CLI Installation Guide - Kunpeng DevKit WebUI Mode

This skill requires hcloud (KooCLI) for creating Kunpeng ECS instances.

## Table of Contents

- [hcloud (KooCLI) Installation](#hcloud-kocli-installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

---

## hcloud (KooCLI) Installation

### Auto Install (Recommended)

```bash
bash skills/hcloud-cli/scripts/install.sh
```

**Features:**
- Auto-detect OS and CPU architecture (x86_64/aarch64)
- No sudo required, installs to `~/.local/bin/`
- Downloads latest version from Huawei Cloud official OBS

**Configure PATH after installation:**

```bash
export PATH="$PATH:$HOME/.local/bin"

# Permanent addition to ~/.bashrc
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

### macOS

```bash
# Install via Homebrew
brew install hcloudcli

# Or download directly
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-macos-amd64.tar.gz
tar -xzf hcloudcli-macos-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### One-Click Install (Download-Verify-Execute)

> **⚠️ Security**: Never pipe remote URLs directly into a shell interpreter. Always download first, verify integrity, then execute.

```bash
# Step 1: Download the install script to a local file
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh

# Step 2: Verify the script integrity (SHA256 checksum)
sha256sum ./hcloud_install.sh
# Optionally review the script content before execution:
head -50 ./hcloud_install.sh

# Step 3: Execute the verified script
bash ./hcloud_install.sh -y
```

---

## Credential Configuration

### Method 1: Interactive configuration (recommended)

```bash
hcloud configure set
# Enter as prompted:
# - Access Key ID (AK)
# - Secret Access Key (SK)
# - Default region (e.g., cn-north-4)
```

### Method 2: Environment variables

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
```

### Method 3: Non-interactive configuration

```bash
hcloud configure set \
  --cli-profile=default \
  --region=cn-north-4 \
  --access-key-id=<AK> \
  --secret-access-key=<SK>
```

> **Security warning**: Method 3 will expose AK/SK in command history; only use in secure environments.

> **Prohibited actions:**
> - Do not ask the user to provide AK/SK directly in the conversation
> - Do not extract AK/SK from hcloud config files (credentials are encrypted)
> - Do not use `hcloud configure set` with plaintext AK/SK values in conversation

---

## Verify Installation

```bash
# First run: agree to privacy policy
echo "y" | hcloud version

# Check version
hcloud version
# Expected: >= 3.2.0

# Check configuration
hcloud configure list

# Test API connectivity
hcloud IAM KeystoneListRegions --cli-region=cn-north-4
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | Not installed or not in PATH | Install hcloud or add `~/.local/bin` to PATH |
| `authentication failed` | Invalid or expired credentials | Reconfigure credentials via `hcloud configure set` |
| `insufficient permissions` | Insufficient IAM permissions | Add required IAM policies (see iam-policies.md) |
| `region not found` | Incorrect region ID | Use correct region ID (e.g., cn-north-4, cn-south-1) |
| Privacy policy prompt | First-time run | Run `echo "y" \| hcloud version` to auto-accept |

---

## Security Best Practices

1. **Do not provide AK/SK directly in conversation** - Always use interactive configuration or environment variables
2. **Rotate AK/SK regularly** - Recommended every 90 days
3. **Use IAM temporary credentials** - Prefer IAM agency delegation or temporary credentials
4. **Least privilege principle** - Grant only the minimum required permissions for ECS/VPC/IMS operations

---

## Official Documentation

- [KooCLI Installation Guide](https://support.huaweicloud.com/qs-hcli/hcli_02_003_02.html)
- [KooCLI Configuration Guide](https://support.huaweicloud.com/productdesc-hcli/hcli_01_0001.html)
