# CLI Installation Guide - Huawei Cloud OBS Directory Count

This skill needs the `hcloud` (KooCLI) CLI, which bundles the `OBS` module (obsutil).

> **Security-first install.** This guide installs into your **user directory**
> (`~/.local/bin`), never `/usr/local/bin` via `sudo`. Every download is verified by its
> **SHA-256 checksum** before execution. You should always download from the **official
> Huawei Cloud source** and cross-check the checksum against the official release page.

## Table of Contents

- [1. Install hcloud (KooCLI)](#1-install-hcloud-kocli)
- [2. Verify the download (SHA-256)](#2-verify-the-download-sha-256)
- [3. Add to PATH (user-level)](#3-add-to-path-user-level)
- [4. Configure obsutil credentials](#4-configure-obsutil-credentials)
- [5. Verify installation](#5-verify-installation)
- [6. Troubleshooting](#6-troubleshooting)
- [7. Security best practices](#7-security-best-practices)

---

## 1. Install hcloud (KooCLI)

> **Official source only.** Download the KooCLI archive from Huawei Cloud's official
> community tool bucket, never from a third-party mirror. The official KooCLI download
> page and checksums are at: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### Linux / macOS

Choose the archive for your platform and download it to a temporary directory:

```bash
cd ~/Downloads

# --- x86_64 ---
curl -fLO https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz

# --- ARM64 (e.g. Huawei Kunpeng, Apple Silicon via macOS) ---
curl -fLO https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
```

> `-f` makes `curl` fail on HTTP errors instead of saving a broken file; `-L` follows
> the official redirect. `-O` saves with the original filename.

### Windows

```powershell
# Download from the official bucket (PowerShell)
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "$HOME\Downloads\hcloudcli.zip"
```

---

## 2. Verify the download (SHA-256)

**Do not extract or run the downloaded archive until you have verified its checksum.**
The archive is only trustworthy if its SHA-256 matches the official value published on
the Huawei Cloud KooCLI release page
(https://support.huaweicloud.com/qs-hcli/hcli_02_003.html).

### Linux / macOS

```bash
cd ~/Downloads
sha256sum hcloudcli-linux-amd64.tar.gz
# ^ Copy the output and compare it character-by-character with the SHA-256
#   published on the official KooCLI release/download page.
#   NEVER proceed if the values differ.
```

macOS note: use `shasum -a 256 hcloudcli-linux-amd64.tar.gz` if `sha256sum` is absent.

### Windows (PowerShell)

```powershell
Get-FileHash "$HOME\Downloads\hcloudcli.zip" -Algorithm SHA256
# Compare the output with the official checksum; do not proceed if it differs.
```

> **Why this matters:** an unverified download could be replaced in transit
> (supply-chain risk). Always compare the SHA-256 with the value on the official page
> and only continue when they match exactly.

---

## 3. Add to PATH (user-level)

Extract and install into your user home **without** `sudo`:

### Linux / macOS

```bash
cd ~/Downloads
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud

# Install into your user-local bin (create it if needed)
mkdir -p ~/.local/bin
mv hcloud ~/.local/bin/hcloud
chmod +x ~/.local/bin/hcloud

# Add ~/.local/bin to PATH for the current shell (and persist it)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
```

zsh users: append the same line to `~/.zshrc` instead.

### Windows (PowerShell)

```powershell
Expand-Archive "$HOME\Downloads\hcloudcli.zip" -DestinationPath "$HOME\hcloudcli"
# Add "$HOME\hcloudcli" to your user PATH via System Settings > Environment Variables.
```

---

## 4. Configure obsutil credentials

The `hcloud OBS` module uses obsutil, which needs its **own** AK/SK and endpoint. Run
this **in your own terminal** (never paste AK/SK into a chat):

```bash
hcloud obs config -i=<YourAccessKeyId> -k=<YourAccessKeySecret> -e=obs.<region>.myhuaweicloud.com
```

Example (cn-north-4):

```bash
hcloud obs config -i=<YourAccessKeyId> -k=<YourAccessKeySecret> -e=obs.cn-north-4.myhuaweicloud.com
```

Common endpoints:

| Region | Endpoint |
|--------|----------|
| cn-north-1 | `obs.cn-north-1.myhuaweicloud.com` |
| cn-north-4 | `obs.cn-north-4.myhuaweicloud.com` |
| cn-east-3 | `obs.cn-east-3.myhuaweicloud.com` |
| cn-south-1 | `obs.cn-south-1.myhuaweicloud.com` |
| ap-southeast-1 | `obs.ap-southeast-1.myhuaweicloud.com` |

> AK/SK are obtained from the Huawei Cloud console (IAM > My Credentials). Protect them
> as secrets; never share them in chat.

---

## 5. Verify installation

```bash
# hcloud is installed and on PATH
hcloud help

# obsutil OBS module is reachable
hcloud OBS --help

# Credentials are configured (should list buckets instead of the "Please set" warning)
hcloud OBS ls -limit=1
```

Then run a quick count:

```bash
mkdir -p /tmp/dc && cd /tmp/dc
# copy the skill's script, or run it from the skill directory
python3 </path/to/skill>/scripts/count_obs_directories.py --bucket <your-bucket>
```

---

## 6. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `hcloud: command not found` | Not installed or `~/.local/bin` not in PATH | Re-run Step 3 and re-open the shell |
| `Please set ak, sk and endpoint in the configuration file!` | obsutil credentials not configured | Run Step 4 |
| `InvalidAccessKeyId` / `Forbidden` | Invalid credentials or missing IAM read permission | Recheck AK/SK; grant OBS read-only policy (see `iam-policies.md`) |
| `NoSuchBucket` / `Status code: 404` | Bucket or prefix does not exist | Confirm bucket name and prefix |
| SHA-256 mismatch | Downloaded file is corrupt or tampered | Delete the archive, re-download from the official source, re-verify |

---

## 7. Security best practices

1. **Never** provide AK/SK in a conversation; always configure credentials yourself in
   your own terminal.
2. **Always** verify the SHA-256 of a downloaded CLI archive against the official page
   before extracting or running it.
3. Install only into your **user** directory; do not `sudo`-install unverified binaries.
4. Grant the **least privilege** — this skill only needs read access to buckets and
   objects (see `iam-policies.md`).
5. Rotate AK/SK regularly and remove obsolete keys.

---

## References

- Official KooCLI (hcloud) download & checksum page: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- Official obsutil guide: https://support.huaweicloud.com/utiltg-obs/obs_11_0003.html
- OBS regions and endpoints: https://support.huaweicloud.com/devg-obs/obs_03_0110.html