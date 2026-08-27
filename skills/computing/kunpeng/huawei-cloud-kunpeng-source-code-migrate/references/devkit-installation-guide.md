# DevKit Installation Guide

> **⚠️ This guide has been superseded by the automated installation script.**
>
> For all DevKit installations (local or remote), use the `scripts/install_devkit.sh` script instead of following the manual steps below. The script handles OS detection, architecture selection, dependency installation, download with version fallback, hidden file copying, and verification automatically.
>
> **Quick start:**
> ```bash
> # Local install
> bash <skill_dir>/scripts/install_devkit.sh --yes
>
> # Remote install (via SSH + SFTP)
> MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<skill_dir>/scripts/install_devkit.sh" "/tmp/install_devkit.sh"
> python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes" 300
> ```
>
> See [task-install-devkit.md](task-install-devkit.md) for remote install details, or [task-local-devkit.md](task-local-devkit.md) for local install details.

---

This document is retained as a reference for the DevKit installation process. The manual steps below describe what the `install_devkit.sh` script does automatically.

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | openEuler 20.03, CentOS 7.6, Ubuntu 18.04 | openEuler 22.03, CentOS 8.0, Ubuntu 22.04 |
| Architecture | x86_64 or aarch64 | aarch64 (Kunpeng) |
| CPU | 2 cores | 4+ cores |
| Memory | 2 GB | 4+ GB |
| Disk | 500 MB | 1+ GB |
| Python | 3.7+ | 3.9+ |

## Download URL

```
https://mirrors.huaweicloud.com/kunpeng/archive/DevKit/Packages/Kunpeng_DevKit/
```

**Package naming:** `DevKit-CLI-<version>-Linux-<arch>.tar.gz`
- `<arch>`: `x86-64` for Intel/AMD, `Kunpeng` for ARM64

## Manual Installation Steps (Reference Only)

> These steps are what `install_devkit.sh` automates. Use the script instead.

### Step 1: Install Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip curl

# CentOS/RHEL/openEuler/EulerOS
sudo yum install -y python3 python3-pip curl

# SUSE
sudo zypper install -y python3 python3-pip curl
```

### Step 2: Download DevKit CLI

```bash
mkdir -p /tmp/devkit-install && cd /tmp/devkit-install
# x86_64
curl -L -O 'https://mirrors.huaweicloud.com/kunpeng/archive/DevKit/Packages/Kunpeng_DevKit/DevKit-CLI-25.3.0-Linux-x86-64.tar.gz'
# ARM64
curl -L -O 'https://mirrors.huaweicloud.com/kunpeng/archive/DevKit/Packages/Kunpeng_DevKit/DevKit-CLI-25.3.0-Linux-Kunpeng.tar.gz'
```

### Step 3: Extract and Install

```bash
cd /tmp/devkit-install && tar -xzf DevKit-CLI-*.tar.gz
mkdir -p /usr/local/devkit

# CRITICAL: Copy each file explicitly, including hidden .devkit
cp -a /tmp/devkit-install/DevKit-CLI-*/devkit /usr/local/devkit/
cp -a /tmp/devkit-install/DevKit-CLI-*/.devkit /usr/local/devkit/
cp -a /tmp/devkit-install/DevKit-CLI-*/execute.ini /usr/local/devkit/
cp -a /tmp/devkit-install/DevKit-CLI-*/advisor /usr/local/devkit/
cp -a /tmp/devkit-install/DevKit-CLI-*/porting /usr/local/devkit/
cp -a /tmp/devkit-install/DevKit-CLI-*/sys-mig /usr/local/devkit/

chmod +x /usr/local/devkit/devkit
ln -sf /usr/local/devkit/devkit /usr/local/bin/devkit
```

> **⚠️ The `.devkit` hidden file is required.** Missing it causes `execvp failed` error.

### Step 4: Verify

```bash
cd /usr/local/devkit && ./devkit --version
```

## Offline Installation

Use the `--offline` option of the installation script:

```bash
# Download on a machine with internet, then transfer to target server
bash <skill_dir>/scripts/install_devkit.sh --yes --offline=/path/to/DevKit-CLI-25.3.0-Linux-x86-64.tar.gz
```

## Uninstallation

```bash
# Remove DevKit installation (guarded: only proceed if paths exist)
DEVKIT_HOME="/usr/local/devkit"
DEVKIT_BIN="/usr/local/bin/devkit"
if [[ -d "$DEVKIT_HOME" ]]; then
    rm -r "$DEVKIT_HOME"
fi
if [[ -f "$DEVKIT_BIN" ]]; then
    rm "$DEVKIT_BIN"
fi
```
