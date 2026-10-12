# DevBridge CLI Installation Guide

## Overview

DevBridge CLI is a command-line tool for creating and managing development tunnels on Huawei Cloud. It allows developers to securely expose local services to remote devices without opening public inbound ports. **Target version: v0.2.x.**

> **Important (2026-09-20)**: DevBridge tunnel domain switched from `*.cn-north-4-bridge.myhuaweicloud.com` to the new cluster domain (`*.devbridge-s2.hwtunnel.com`). Old clients (v0.1.x) can no longer connect. Always install/upgrade to the latest v0.2.x.

## System Requirements

| Requirement | Details |
|-------------|---------|
| Operating System | Linux, macOS, Windows |
| Architecture | x86-64 or ARM64 |
| Shell | Bash and `curl`, or PowerShell 5.1+ |
| Disk Space | ~50 MB for the CLI binary |
| Network | Access to the DevBridge installation source |

## Installation

### Linux / macOS (Bash + curl)

Choose any one of the three official channels:

**GitHub:**

```bash
curl -fsSL https://github.com/huaweicloud/devspace-devbridge/releases/latest/download/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh
```

**GitCode:**

```bash
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh
```

**OBS:**

```bash
curl -fsSL https://tools-artifact.developer.huaweicloud.com/sharedata/devbridge/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh
```

### Headless / non-interactive environments

> **CRITICAL** — In automation/CI/headless environments, always add the silent flag `-s`. Without it, when the CLI is already present the script reads `/dev/tty` for an "overwrite?" prompt and fails with `unbound variable` where no terminal exists.

```bash
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh -s
```

Specify a version explicitly:

```bash
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh -s -v 0.2.2-release
```

### Windows (PowerShell)

```powershell
irm https://github.com/huaweicloud/devspace-devbridge/releases/latest/download/install.ps1 | iex
```

### Manual Installation

If the installation script is unavailable, download the binary directly:

1. Download the binary for your platform from the DevBridge distribution source.
2. Place the binary at `~/.huawei/bin/devbridge` (Linux/macOS) or `%USERPROFILE%\.huawei\bin\devbridge.exe` (Windows).
3. Grant execute permission (Linux/macOS): `chmod +x ~/.huawei/bin/devbridge`
4. Add `~/.huawei/bin` to PATH.

## PATH Configuration

### Verify PATH

```bash
which devbridge
```

If the command is not found, manually add the bin directory to PATH:

**Linux (bash):**

```bash
echo 'export PATH="$HOME/.huawei/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Linux/macOS (zsh):**

```bash
echo 'export PATH="$HOME/.huawei/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**

```powershell
$env:Path += ";$env:USERPROFILE\.huawei\bin"
```

## Verification

After installation, verify the CLI is working:

```bash
# Check version
devbridge version

# Check help
devbridge --help
```

**✅ Correct installation:**

```bash
$ devbridge version
0.2.2-release
```

**❌ Installation failure (command not found):**

```bash
$ devbridge version
bash: devbridge: command not found
# Fix: run 'source ~/.bashrc' or add ~/.huawei/bin to PATH
```

**❌ Old version (will not connect after 2026-09-20 domain switch):**

```bash
$ devbridge version
0.1.x-...
# Upgrade: rerun the official install script
```

## Directory Structure

After installation, the following directories are created:

```
~/.huawei/
├── bin/
│   └── devbridge          # CLI binary
└── devbridge/
    ├── config             # Authentication and configuration
    └── tunnels            # Tunnel state and metadata
```

## Upgrade

To upgrade to the latest version, rerun the installation script (use `-s` in headless environments):

```bash
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh -s
```

The script detects existing installations; in silent mode it compares SHA256 hashes and skips if already up to date.

## Uninstall

Remove DevBridge CLI:

```bash
# Delete the binary
rm -f ~/.huawei/bin/devbridge

# Delete configuration (optional — also removes auth credentials)
rm -rf ~/.huawei/devbridge
```

## Troubleshooting

### Command not found after installation

If `devbridge` is not found after installation:

1. Check if the binary exists: `ls -la ~/.huawei/bin/devbridge`
2. Check PATH: `echo $PATH | tr ':' '\n' | grep huawei`
3. Manually add to PATH (see PATH Configuration above).
4. Restart the terminal or run `source ~/.bashrc`.

### Permission denied

```bash
chmod +x ~/.huawei/bin/devbridge
```

### Install script fails with "unbound variable" / "/dev/tty: No such device"

The script is prompting interactively but there is no terminal. Re-run with the silent flag:

```bash
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh -s
```

### Download failed

- Verify network connectivity to the installation source.
- Check if a proxy is needed: `echo $http_proxy`
- Retry with an explicit proxy: `curl --proxy <proxy-url> -fsSL <install-url> -o /tmp/devbridge_install.sh\nbash /tmp/devbridge_install.sh`