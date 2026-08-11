# DevBridge CLI Installation Guide

## Overview

DevBridge CLI is a command-line tool for creating and managing development tunnels on Huawei Cloud. It allows developers to securely expose local services to remote devices without opening public inbound ports.

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

```bash
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
```

The installation script will:

1. Detect the operating system and architecture.
2. Download the corresponding CLI binary.
3. Install the binary to `~/.huawei/bin/`.
4. Add `~/.huawei/bin` to the system PATH (via `.bashrc` or `.zshrc`).
5. Create the configuration directory `~/.huawei/devbridge/`.

### Windows (PowerShell)

```powershell
irm https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.ps1 | iex
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
0.1.12-release
```

**❌ Installation failure (command not found):**

```bash
$ devbridge version
bash: devbridge: command not found
# Fix: run 'source ~/.bashrc' or add ~/.huawei/bin to PATH
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

To upgrade to the latest version, rerun the installation script:

```bash
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
```

The script detects existing installations and upgrades in place.

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

### Download failed

- Verify network connectivity to the installation source.
- Check if a proxy is needed: `echo $http_proxy`
- Retry with an explicit proxy: `curl --proxy <proxy-url> -fsSL <install-url> | bash`
