# CLI Installation Guide - Huawei Cloud OBS Object Storage Statistics

This skill requires two CLI tools: hcloud (KooCLI) and obsutil.

## Table of Contents

- [1. hcloud (KooCLI) Installation](#1-hcloud-kocli-installation)
- [2. obsutil Installation](#2-obsutil-installation)
- [3. Credential Configuration](#3-credential-configuration)
- [4. Verify Installation](#4-verify-installation)
- [5. Troubleshooting](#5-troubleshooting)
- [6. Security Best Practices](#6-security-best-practices)

---

## 1. hcloud (KooCLI) Installation

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

### Windows

```powershell
# Download and extract
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

---

## 2. obsutil Installation

### macOS

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
tar -xzf obsutil_darwin_amd64.tar.gz
chmod +x obsutil_darwin_amd64_*
sudo mv obsutil_darwin_amd64_*/obsutil /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
tar -xzf obsutil_linux_amd64.tar.gz
chmod +x obsutil_linux_amd64_*
sudo mv obsutil_linux_amd64_*/obsutil /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
tar -xzf obsutil_linux_arm64.tar.gz
chmod +x obsutil_linux_arm64_*
sudo mv obsutil_linux_arm64_*/obsutil /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip" -OutFile "obsutil.zip"
Expand-Archive obsutil.zip
# Add obsutil.exe to PATH
```

---

## 3. Credential Configuration

### hcloud Credential Configuration

#### Method 1: Interactive configuration (recommended)

```bash
hcloud configure
# Enter as prompted:
# - Region (e.g., cn-south-1)
# - AK (Access Key ID)
# - SK (Access Key Secret)
```

#### Method 2: Environment variables

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
```

#### Method 3: Non-interactive configuration

```bash
hcloud configure set --cli-profile=default --region=cn-south-1 --access-key-id=<AK> --secret-access-key=<SK>
```

> **⚠️ Security warning**: Method 3 exposes AK/SK in command history; only use in secure environments.

### obsutil Credential Configuration

```bash
obsutil config -ak=<AK> -sk=<SK> -e=obs.cn-south-1.myhuaweicloud.com
```

> **⚠️ obsutil Endpoint format**
>
> OBS Endpoint format: `obs.<region-id>.myhuaweicloud.com`
>
> Common endpoints:
>
> | Region | Endpoint |
> |--------|----------|
> | cn-north-1 | obs.cn-north-1.myhuaweicloud.com |
> | cn-north-4 | obs.cn-north-4.myhuaweicloud.com |
> | cn-east-2 | obs.cn-east-2.myhuaweicloud.com |
> | cn-east-3 | obs.cn-east-3.myhuaweicloud.com |
> | cn-south-1 | obs.cn-south-1.myhuaweicloud.com |
> | ap-southeast-1 | obs.ap-southeast-1.myhuaweicloud.com |

---

## 4. Verify Installation

### Verify hcloud

```bash
# Check version
hcloud version
# Expected: >= 3.2.0

# Test authentication
hcloud obs ls
```

### Verify obsutil

```bash
# Check version
obsutil version
# Expected: >= 5.5.0

# Test authentication (list buckets, limit 1)
obsutil ls -limit=1
```

---

## 5. Troubleshooting

### hcloud Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | Not installed or not in PATH | Install hcloud or add to PATH |
| `authentication failed` | Invalid or expired credentials | Reconfigure credentials |
| `insufficient permissions` | Insufficient IAM permissions | Add required IAM policies |
| `region not found` | Incorrect region ID | Use the correct region ID |

### obsutil Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `obsutil: command not found` | Not installed or not in PATH | Install obsutil or add to PATH |
| `Status code: 403` | AK/SK incorrect or insufficient permissions | Re-run `obsutil config` to configure credentials |
| `Status code: 404` | Bucket does not exist | Confirm bucket name is correct |
| `connection timeout` | Network issue or incorrect endpoint | Check network connection and endpoint configuration |

---

## 6. Security Best Practices

1. **Never provide AK/SK directly in conversation** — always use interactive configuration or environment variables
2. **Rotate AK/SK regularly** — recommended every 90 days
3. **Use IAM temporary credentials** — prefer IAM agency delegation or temporary credentials
4. **Least privilege principle** — grant only the minimum required permissions
5. **Audit logging** — enable OBS bucket logging to record access requests
6. **obsutil credential file permissions** — ensure obsutil config file has 600 permissions

---

## References

- [hcloud Installation Guide](https://support.huaweicloud.com/cli/cli_hcloud_install.html)
- [obsutil Installation Guide](https://support.huaweicloud.com/utiltg-obs/obs_11_0003.html)
- [obsutil Configuration Guide](https://support.huaweicloud.com/utiltg-obs/obs_11_0005.html)
- [OBS Regions and Endpoints](https://support.huaweicloud.com/devg-obs/obs_03_0110.html)
