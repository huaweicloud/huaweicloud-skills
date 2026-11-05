# CLI Installation Guide

This skill requires **hcloud (KooCLI)** and the **obsutil** tool (bundled with KooCLI's OBS module or installed standalone).

## Table of Contents

- [Install hcloud](#install-hcloud)
- [Install obsutil](#install-obsutil)
- [Configure OBS Credentials (obsutil)](#configure-obs-credentials-obsutil)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

---

## Install hcloud

> **Supply-chain safety:** always download from the official Huawei Cloud download bucket, verify the downloaded
> archive with the official SHA256 checksum before installing (from the release notes or checksum file on the
> official download page), and install to the **current user's** directory. System-wide `sudo` installation is
> optional and only needed when the administrator explicitly requires access for all users.

### Consult the official release page first

Download URLs and SHA256 checksums are published on the official Huawei Cloud CLI download page:
<https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>. Always verify the archive against the checksum
published there before executing it.

### Linux (x86_64) — user-level install

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
sha256sum hcloudcli-linux-amd64.tar.gz
# Compare the output against the SHA256 checksum on the official hcloud download page;
# abort if it does not match.
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
mkdir -p ~/.local/bin
mv hcloud ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc to persist
```

### Linux (ARM64) — user-level install

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
sha256sum hcloudcli-linux-arm64.tar.gz
# Compare the output against the SHA256 checksum on the official hcloud download page;
# abort if it does not match.
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
mkdir -p ~/.local/bin
mv hcloud ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc to persist
```

### Optional system-wide install (sudo)

Only if a shared system installation is truly required (e.g. managed multi-user hosts), the user may copy the
verified binary to a system location. This requires an administrator and is **not** needed for this skill to work:

```bash
# After the same download + SHA256 verification steps above:
sudo mv hcloud /usr/local/bin/
```

### macOS

```bash
brew install hcloudcli
```

### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
# Verify the zip's SHA256 against the official hcloud download page before expanding.
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

### Node.js / npm (alternative)

```bash
npm install -g @huaweicloud/hcloud
```

---

## Install obsutil

The `hcloud OBS` module is backed by obsutil. With a recent KooCLI the bundled obsutil works out of the box; if it is missing, install standalone obsutil.

> **Supply-chain safety:** the same rules apply — download from the official Huawei Cloud bucket and verify the
> SHA256 checksum from the official obsutil download page before installing.

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
sha256sum obsutil_linux_amd64.tar.gz
# Compare the output against the SHA256 checksum on the official obsutil download page;
# abort if it does not match.
tar -xzf obsutil_linux_amd64.tar.gz
chmod +x obsutil_linux_amd64_*/obsutil
mkdir -p ~/.local/bin
mv obsutil_linux_amd64_*/obsutil ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc to persist
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
sha256sum obsutil_linux_arm64.tar.gz
# Compare the output against the SHA256 checksum on the official obsutil download page;
# abort if it does not match.
tar -xzf obsutil_linux_arm64.tar.gz
chmod +x obsutil_linux_arm64_*/obsutil
mkdir -p ~/.local/bin
mv obsutil_linux_arm64_*/obsutil ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc or ~/.zshrc to persist
```

---

## Configure OBS Credentials (obsutil)

> **Important:** OBS credentials do **not** inherit from the KooCLI account credentials. The `hcloud OBS ls` command reads AK/SK/endpoint from the obsutil config file (`~/.obsutilconfig`).

**Credentials are configured by the user in their own terminal only.** The agent never asks for, collects, or
stores AK/SK — never paste AK/SK into a conversation. Run the following in your own terminal:

```bash
hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.<Region>.myhuaweicloud.com
```

Example (cn-north-4):

```bash
hcloud obs config -i=<YourAK> -k=<YourSK> -e=obs.cn-north-4.myhuaweicloud.com
```

Common Endpoints:

| Region | Endpoint |
|--------|----------|
| cn-north-4 | `obs.cn-north-4.myhuaweicloud.com` |
| cn-east-3 | `obs.cn-east-3.myhuaweicloud.com` |
| cn-south-1 | `obs.cn-south-1.myhuaweicloud.com` |
| cn-southwest-2 | `obs.cn-southwest-2.myhuaweicloud.com` |

AK/SK can be obtained from the Huawei Cloud console "My Credentials" page.

---

## Verify Installation

```bash
hcloud version
hcloud OBS ls -s -limit=1
```

A successful run prints `Bucket number: N` with bucket names prefixed by `obs://`.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `Please set ak, sk and endpoint in the configuration file!` | obsutil credentials not configured — run `hcloud obs config` in your own terminal as above |
| `InvalidAccessKeyId` | Wrong AK/SK or expired key — reconfigure credentials |
| `command not found: hcloud` | hcloud not in PATH — install to `~/.local/bin` or add to PATH |
| `command not found: obsutil` | obsutil not installed — install standalone obsutil or upgrade KooCLI |
| `NoSuchBucket` | The bucket does not exist or the AK/SK has no access to it — verify bucket name and IAM policy |