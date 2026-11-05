# CLI Installation Guide - Huawei Cloud OBS Object Storage Management

This skill requires two CLI tools: hcloud (KooCLI) and obsutil.

## Table of Contents

- [hcloud (KooCLI) Installation](#hcloud-kocli-installation)
- [obsutil Installation](#obsutil-installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

---

## hcloud (KooCLI) Installation

> **⚠️ Security note on installing CLI tools**
>
> - **Always download the installer/package from the official Huawei Cloud site only** (the URLs in this document), and verify the package integrity (SHA256) with the official checksum before executing.
> - **Never pipe a remote script directly into a shell** (e.g. `curl ... | bash`). Download the script first, review it, verify its integrity, and only then run it.
> - **Never run `sudo` commands that elevate an unverified downloaded binary.** Prefer installing to a user-local directory and adding it to `PATH`, or running `sudo` only on a verified package.
> - If you cannot verify the integrity of a download, stop and obtain the tool from the official install channel instead.

### Recommended (Linux / macOS): manual download, integrity check, then install

```bash
# Download the installer script (review it first — do not pipe directly to bash)
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh

# Review the downloaded script (recommended) and verify its write permissions
less ./hcloud_install.sh

# Run the installer after review
bash ./hcloud_install.sh -y
```

> The script auto-detects your OS and architecture, downloads the correct package, and installs `hcloud`. After installation, confirm `hcloud version` works.

### macOS

```bash
# Download directly (AMD64 / Intel), then verify the package checksum against the official value
curl -LO https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz
# (Recommended) verify SHA256 of the tarball with the official checksum before extraction
tar -zxvf huaweicloud-cli-mac-amd64.tar.gz
chmod +x hcloud

# Recommend: install to a user-local directory (no sudo needed) and add to PATH
mkdir -p "$HOME/.local/bin" && mv hcloud "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc

# Alternative: system-wide install (requires sudo, only after verifying the binary)
# sudo mv hcloud /usr/local/bin/

# Or for ARM64 (Apple Silicon)
curl -LO https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-arm64.tar.gz
# (Recommended) verify SHA256 of the tarball with the official checksum before extraction
tar -zxvf huaweicloud-cli-mac-arm64.tar.gz
chmod +x hcloud
mkdir -p "$HOME/.local/bin" && mv hcloud "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
```

> **⚠️ Sudo caution**: only move the binary with `sudo` after you have verified it (official checksum + review). Prefer a user-local `$HOME/.local/bin` install that requires no elevation.

### Linux (x86_64)

```bash
curl -LO https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz
# (Recommended) verify SHA256 of the tarball with the official checksum before extraction
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
chmod +x hcloud
mkdir -p "$HOME/.local/bin" && mv hcloud "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
# System-wide alternative (after verifying the binary): sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -LO https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz
# (Recommended) verify SHA256 of the tarball with the official checksum before extraction
tar -zxvf huaweicloud-cli-linux-arm64.tar.gz
chmod +x hcloud
mkdir -p "$HOME/.local/bin" && mv hcloud "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc
# System-wide alternative (after verifying the binary): sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
# Download and extract
Invoke-WebRequest -Uri "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

---

## obsutil Installation

> **⚠️ Security note**: download obsutil only from the official Huawei Cloud URLs in this document, verify the package integrity with the official checksum, and prefer a user-local install (no `sudo`) where possible.

### macOS

```bash
curl -O https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
# (Recommended) verify SHA256 with the official checksum before extraction
tar -xzf obsutil_darwin_amd64.tar.gz
chmod +x obsutil_darwin_amd64_*/obsutil
mkdir -p "$HOME/.local/bin" && mv obsutil_darwin_amd64_*/obsutil "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
# System-wide alternative (after verifying the binary): sudo mv obsutil_darwin_amd64_*/obsutil /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
# (Recommended) verify SHA256 with the official checksum before extraction
tar -xzf obsutil_linux_amd64.tar.gz
chmod +x obsutil_linux_amd64_*/obsutil
mkdir -p "$HOME/.local/bin" && mv obsutil_linux_amd64_*/obsutil "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
# System-wide alternative (after verifying the binary): sudo mv obsutil_linux_amd64_*/obsutil /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
# (Recommended) verify SHA256 with the official checksum before extraction
tar -xzf obsutil_linux_arm64.tar.gz
chmod +x obsutil_linux_arm64_*/obsutil
mkdir -p "$HOME/.local/bin" && mv obsutil_linux_arm64_*/obsutil "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
# System-wide alternative (after verifying the binary): sudo mv obsutil_linux_arm64_*/obsutil /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip" -OutFile "obsutil.zip"
Expand-Archive obsutil.zip
# Add obsutil.exe to PATH
```

---

## Credential Configuration

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
export HW_ACCESS_KEY=<your-access-key-id>
export HW_SECRET_KEY=<your-access-key-secret>
```

#### Method 3: Non-interactive configuration

```bash
hcloud configure set --cli-profile=default --region=cn-south-1 --access-key-id=<AK> --secret-access-key=<SK>
```

> **⚠️ Security warning**: Method 3 exposes AK/SK on the command line — visible to **shell history, OS process listings, audit logs, terminal recordings**, and any copied documentation. Prefer Method 1 or Method 2. If you must use Method 3, run it in a protected shell and then clear the shell history entry.

### obsutil Credential Configuration

```bash
obsutil config -ak=<AK> -sk=<SK> -e=obs.cn-south-1.myhuaweicloud.com
```

> **⚠️ Security warning**: this command places the AK/SK in plaintext on the command line, exposing them via shell history and process listings. Prefer running it interactively in your own terminal and then clearing the shell history. Ensure the obsutil config file (e.g. `~/.obsutilconfig`) has restricted permissions (`chmod 600 ~/.obsutilconfig`).

> **⚠️ obsutil Endpoint format**
>
> OBS Endpoint format: `obs.<region-id>.myhuaweicloud.com`
>
> Common Endpoints:
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

## Verify Installation

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

## Troubleshooting

### hcloud Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | Not installed or not in PATH | Install hcloud or add path to PATH |
| `authentication failed` | Invalid or expired credentials | Reconfigure credentials |
| `insufficient permissions` | Insufficient IAM permissions | Add required IAM policies |
| `region not found` | Incorrect region ID | Use the correct region ID |

### obsutil Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `obsutil: command not found` | Not installed or not in PATH | Install obsutil or add path to PATH |
| `Status code: 403` | Incorrect AK/SK or insufficient permissions | Re-run `obsutil config` to configure credentials |
| `Status code: 404` | Bucket does not exist | Confirm bucket name is correct |
| `connection timeout` | Network issue or incorrect Endpoint | Check network connection and Endpoint configuration |

---

## Security Best Practices

1. **Do not provide AK/SK directly in conversation** - Always use interactive configuration or environment variables
2. **Avoid plaintext AK/SK on the command line** - Command-line arguments are exposed via shell history, process listings, and audit logs; prefer interactive (`hcloud configure`) or environment variables (`HW_ACCESS_KEY`/`HW_SECRET_KEY`)
3. **Rotate AK/SK regularly** - Recommended every 90 days
4. **Use IAM temporary credentials** - Prefer IAM agency delegation or temporary credentials
5. **Least privilege principle** - Grant only the minimum required permissions
6. **Audit logs** - Enable OBS bucket logging for access request auditing
7. **obsutil credential file permissions** - Ensure obsutil config file permissions are 600
8. **Install from official sources only and verify integrity** - Download CLI tools from the official Huawei Cloud URLs and verify SHA256 checksums before execution; never pipe a remote script directly to a shell

---

## Official Documentation

- [KooCLI Quick Start](https://support.huaweicloud.com/qs-hcli/hcli_02_003.html)
- [KooCLI Installation Overview](https://support.huaweicloud.com/qs-hcli/hcli_02_003_01.html)
- [obsutil Installation Guide](https://support.huaweicloud.com/utiltg-obs/obs_11_0003.html)
- [obsutil Configuration Guide](https://support.huaweicloud.com/utiltg-obs/obs_11_0005.html)
