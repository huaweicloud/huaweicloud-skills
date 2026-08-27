# Task 2: Install DevKit CLI Tool (Remote Server)

Install Kunpeng DevKit CLI on the remote server using the built-in `install_devkit.sh` script.

> **⚠️ IMPORTANT: Use the installation script, NOT manual step-by-step commands.**
>
> The `scripts/install_devkit.sh` script automates the entire installation process (OS detection, dependency installation, download, extraction, hidden file handling, verification). AI MUST use this script to avoid common errors such as missing the `.devkit` hidden file, wrong architecture package, or incorrect package manager.
>
> All `remote_exec` calls in this document MUST be replaced with the built-in `ssh_client.py` script:
> ```bash
> python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]
> ```
> The `ssh_client.py` script uses **unified paramiko-based SSH** (password from `MIGRATE_SSH_PASS` environment variable, no ControlMaster, no key injection). No `sshpass` is needed. The password is read from `os.environ` (or Windows user-level registry as fallback), never passed via argv, and wiped from `os.environ` immediately after each connection is established.

## Table of Contents

- [Overview](#overview)
- [Step 1: Check Existing DevKit Installation](#step-1-check-existing-devkit-installation)
- [Step 2: Upload and Execute Installation Script](#step-2-upload-and-execute-installation-script)
- [Step 3: Verify Installation](#step-3-verify-installation)
- [Error Handling](#error-handling)

---

## Overview

Kunpeng DevKit is a command-line tool for source code migration analysis. This task installs it on the remote server using the automated `install_devkit.sh` script.

**Supported OS and architectures:**

| Operating System | x86_64 | ARM64 (aarch64) |
|-----------------|--------|-----------------|
| openEuler 20.03/22.03 | Yes | Yes |
| CentOS 7.6/8.0 | Yes | Yes |
| EulerOS 2.8/2.9 | Yes | Yes |
| Ubuntu 18.04/20.04/22.04 | Yes | Yes |
| Kylin V10 | Yes | Yes |
| NeoKylin V7 | Yes | Yes |
| UOS 20 | Yes | Yes |
| SUSE 12 | Yes | Yes |
| Debian 10/11 | Yes | Yes |

---

## Step 1: Check Existing DevKit Installation

Before installing, check if DevKit is already installed on the remote server:

```bash
python <skill_dir>/scripts/ssh_client.py exec "cd /usr/local/devkit && ./devkit --version 2>/dev/null || echo 'DevKit not installed'" 30
```

**If DevKit is already installed and version is satisfactory:**

```
DevKit is already installed: <version>
Skipping installation.
```

**If DevKit is not installed, proceed to Step 2.**

---

## Step 2: Upload and Execute Installation Script

Upload the `install_devkit.sh` script to the remote server and execute it.

### Method A: Upload script via SFTP and execute (recommended)

```bash
# Upload the script to the remote server via SFTP
# IMPORTANT: On Windows (MSYS2/Git Bash), prefix with MSYS_NO_PATHCONV=1
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<skill_dir>/scripts/install_devkit.sh" "/tmp/install_devkit.sh"

# Execute the script on the remote server
python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes" 300
```

### Method B: If Method A doesn't work (base64-encoded inline)

```bash
# Read the script content and pass it as a base64-encoded command
SCRIPT_B64=$(base64 -w0 <skill_dir>/scripts/install_devkit.sh)
python <skill_dir>/scripts/ssh_client.py exec "echo '$SCRIPT_B64' | base64 -d > /tmp/install_devkit.sh && chmod +x /tmp/install_devkit.sh && bash /tmp/install_devkit.sh --yes" 300
```

### Script options for remote install:

| Option | When to use |
|--------|-------------|
| `--yes` | Always use for automated/skill-driven execution (skips prompts) |
| `--version=25.3.0` | Specify a particular DevKit version |
| `--skip-deps` | If dependencies are already installed or you want to install them separately |
| `--no-sudo` | If the SSH user doesn't have sudo (installs to ~/devkit) |
| `--offline=/tmp/DevKit-CLI-xxx.tar.gz` | If the package was pre-uploaded to the remote server |

### What the script does automatically:

1. **Detects OS and architecture** — Determines the correct package manager and DevKit package
2. **Checks existing installation** — Skips if DevKit is already installed
3. **Installs dependencies** — python3, pip, curl via yum/apt/zypper
4. **Downloads DevKit** — Auto-detects latest stable version, with fallback to known versions
5. **Extracts and installs** — Copies ALL files including the critical `.devkit` hidden file
6. **Verifies installation** — Runs `devkit --version`, `devkit --help`, `devkit porting src-mig --help`

> **⚠️ The script handles the critical `.devkit` hidden file automatically.** This is the #1 cause of installation failure when done manually — the `cp -r *` glob misses hidden files.

---

## Step 3: Verify Installation

After the script completes, verify the installation:

```bash
# Check version
python <skill_dir>/scripts/ssh_client.py exec "cd /usr/local/devkit && ./devkit --version" 30

# Check src-mig subcommand
python <skill_dir>/scripts/ssh_client.py exec "cd /usr/local/devkit && ./devkit porting src-mig --help" 30
```

**Expected output:**
```
devkit version 25.3.0
```

**If verification fails**, check:
1. `.devkit` hidden file exists: `ls -la /usr/local/devkit/.devkit`
2. DevKit binary has execute permission
3. System dependencies are installed (libstdc++, glibc)

---

## Error Handling

### Script exit code 1: Unsupported OS

**Problem:** Remote server OS is not in the supported list.

**Solution:** Install DevKit manually following the official guide at https://www.hikunpeng.com/document/detail/zh/kunpengdevps/install/installguide/KunpengDevKitCli_0003.html

### Script exit code 2: Dependency installation failed

**Problem:** Could not install python3, pip, or curl.

**Solution:**
```bash
# Install dependencies manually based on OS
# CentOS/RHEL/openEuler
python <skill_dir>/scripts/ssh_client.py exec "sudo yum install -y python3 python3-pip curl" 60

# Ubuntu/Debian
python <skill_dir>/scripts/ssh_client.py exec "sudo apt-get update" 60
python <skill_dir>/scripts/ssh_client.py exec "sudo apt-get install -y python3 python3-pip curl" 60

# Then re-run with --skip-deps
python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes --skip-deps" 300
```

### Script exit code 3: Download failed

**Problem:** Could not download DevKit package from Huawei Cloud mirror.

**Solution:**
1. Check internet connectivity on the remote server
2. Try a specific version: `--version=25.3.0`
3. Download manually and use `--offline`:
   ```bash
   # Download on local machine, then upload
   python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes --offline=/tmp/DevKit-CLI-25.3.0-Linux-x86-64.tar.gz" 300
   ```

### Script exit code 4: Installation failed

**Problem:** Extraction or file copy failed.

**Solution:**
1. Check disk space: `df -h /tmp /usr/local`
2. Check if `.devkit` hidden file exists in the extracted package
3. Try with `--no-sudo` if permission issues

### Script exit code 5: Verification failed

**Problem:** DevKit installed but verification checks failed.

**Solution:**
```bash
# Check .devkit hidden file
python <skill_dir>/scripts/ssh_client.py exec "ls -la /usr/local/devkit/.devkit" 30

# Check dependencies
python <skill_dir>/scripts/ssh_client.py exec "ldd /usr/local/devkit/.devkit 2>/dev/null | grep 'not found'" 30

# Install missing libraries
# CentOS/RHEL: sudo yum install -y libstdc++ glibc
# Ubuntu/Debian: sudo apt-get install -y libstdc++6 libc6
```

### execvp Failed After Install

**Problem:** `error: execvp failed: No such file or directory`

**Cause:** The `.devkit` hidden file was not copied (should not happen with the script, but may occur with manual install).

**Solution:**
```bash
python <skill_dir>/scripts/ssh_client.py exec "ls -la /usr/local/devkit/.devkit" 30
# If missing, re-run the installation script
```
