# Task 0a: Install DevKit Locally on Supported Linux

Install Kunpeng DevKit CLI on the local machine using the built-in `install_devkit.sh` script.

> **⚠️ IMPORTANT: Use the installation script, NOT manual step-by-step commands.**
>
> The `scripts/install_devkit.sh` script automates the entire installation process. AI MUST use this script to avoid common errors such as missing the `.devkit` hidden file, wrong architecture package, or incorrect package manager.

## Table of Contents

- [Overview](#overview)
- [Step 1: Verify Local OS Compatibility](#step-1-verify-local-os-compatibility)
- [Step 2: Run Installation Script](#step-2-run-installation-script)
- [Step 3: Verify Installation](#step-3-verify-installation)
- [Step 4: Scan Local Source Code](#step-4-scan-local-source-code)
- [Error Handling](#error-handling)

---

## Overview

When the agent machine runs a DevKit-supported Linux distribution, DevKit can be installed locally using the `install_devkit.sh` script. This eliminates the need for a remote server and SSH connection.

**Advantages of local install:**
- No remote server needed
- No SSH connection setup
- Faster scan (no network latency)
- No server costs

**Supported local OS:**

| OS | Minimum Version |
|----|----------------|
| openEuler | 20.03 LTS |
| CentOS | 7.6 |
| Ubuntu | 18.04 |
| Kylin | V10 |
| UOS | 20 |
| EulerOS | 2.8 |
| Debian | 10 |
| SUSE | 12 |
| NeoKylin | V7 |

**NOT supported:** Windows, macOS

---

## Step 1: Verify Local OS Compatibility

Confirm the local OS is in the supported list:

```bash
OS_INFO=$(cat /etc/os-release 2>/dev/null)
ARCH=$(uname -m)

echo "Architecture: $ARCH"
echo "OS Info: $OS_INFO"

SUPPORTED=false
for os in openEuler CentOS Ubuntu Kylin UOS EulerOS Debian SUSE NeoKylin; do
    if echo "$OS_INFO" | grep -qi "$os"; then
        SUPPORTED=true
        break
    fi
done

if [ "$SUPPORTED" = true ]; then
    echo "PASS: Local OS is supported for DevKit installation"
else
    echo "FAIL: Local OS is NOT supported. Please use remote install instead."
fi
```

---

## Step 2: Run Installation Script

Execute the `install_devkit.sh` script locally:

```bash
# Standard local install (with sudo, auto-detect version)
bash <skill_dir>/scripts/install_devkit.sh --yes

# Install without sudo (to ~/devkit)
bash <skill_dir>/scripts/install_devkit.sh --yes --no-sudo

# Install specific version
bash <skill_dir>/scripts/install_devkit.sh --yes --version=25.3.0

# Offline install (from a pre-downloaded tar.gz)
bash <skill_dir>/scripts/install_devkit.sh --yes --offline=/path/to/DevKit-CLI-25.3.0-Linux-x86-64.tar.gz
```

**What the script does automatically:**
1. Detects OS type and architecture (x86_64 / aarch64)
2. Checks if DevKit is already installed (skips if satisfactory)
3. Installs system dependencies (python3, pip, curl) using the correct package manager
4. Downloads the correct DevKit package (auto-detects latest stable version, with fallback)
5. Extracts and installs to `/usr/local/devkit` (including the critical `.devkit` hidden file)
6. Verifies installation (version check, help check, src-mig check)

**Script exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Installation successful |
| 1 | Unsupported OS or architecture |
| 2 | Dependency installation failed |
| 3 | Download failed |
| 4 | Installation (extract/copy) failed |
| 5 | Verification failed |

---

## Step 3: Verify Installation

After the script completes, verify:

```bash
# Check version
cd /usr/local/devkit && ./devkit --version

# Check src-mig subcommand
cd /usr/local/devkit && ./devkit porting src-mig --help
```

**Expected output:**
```
devkit version 25.3.0
```

---

## Step 4: Scan Local Source Code

After DevKit is installed locally, scan the source code:

```bash
# Ask user for source code path
# SOURCE_PATH="<user_provided_path>"

# Verify source path exists
test -d "$SOURCE_PATH" && echo "Source path exists" || echo "Source path not found"

# Create output directory — use the fixed local report save path
# On Linux/macOS:
mkdir -p /home/devkit-report
LOCAL_REPORT_DIR="/home/devkit-report"

# Run scan
cd /usr/local/devkit && ./devkit porting src-mig \
    -i "$SOURCE_PATH" \
    -o "$LOCAL_REPORT_DIR" \
    -s 'c, c++, asm' \
    -r all

# View results
ls -la /home/devkit-report/
```

> **Note:** When scanning locally, no SSH connection is needed. The scan runs directly on the local machine. The report is saved directly to the fixed local path `/home/devkit-report` (Linux/macOS). No separate download step is needed.

> **⚠️ Fixed Local Report Save Path:** The report MUST be saved to the fixed local directory based on the agent's OS:
> - Windows: `C:\devkit-report` (Note: Windows does not support local DevKit install, so this path is only used when downloading from a remote server)
> - Linux/macOS: `/home/devkit-report`

---

## Error Handling

### Script exit code 1: Unsupported OS

**Problem:** Local OS is not in the DevKit-supported list.

**Solution:** Use remote install instead (Task 0, Step 3b/3c/3d).

### Script exit code 2: Dependency installation failed

**Problem:** Could not install python3, pip, or curl.

**Solution:**
```bash
# Install dependencies manually based on OS
# openEuler/CentOS/EulerOS/NeoKylin
sudo yum install -y python3 python3-pip curl

# Ubuntu/Debian/UOS/Kylin
sudo apt-get update
sudo apt-get install -y python3 python3-pip curl

# SUSE
sudo zypper install -y python3 python3-pip curl

# Then re-run with --skip-deps
bash <skill_dir>/scripts/install_devkit.sh --yes --skip-deps
```

### Script exit code 3: Download failed

**Problem:** Could not download DevKit package.

**Solution:**
1. Check internet connectivity: `curl -I https://mirrors.huaweicloud.com`
2. Try a specific version: `--version=25.3.0`
3. Download manually on another machine, transfer to local, then use `--offline`

### Script exit code 4: Installation failed

**Problem:** Extraction or file copy failed.

**Solution:**
1. Check disk space: `df -h /tmp /usr/local`
2. Try with `--no-sudo`: `bash <skill_dir>/scripts/install_devkit.sh --yes --no-sudo`

### Script exit code 5: Verification failed

**Problem:** DevKit installed but verification checks failed.

**Solution:**
```bash
# Check .devkit hidden file
ls -la /usr/local/devkit/.devkit

# Check dependencies
ldd /usr/local/devkit/.devkit 2>/dev/null | grep "not found"

# Install missing libraries
# openEuler/CentOS: sudo yum install -y libstdc++ glibc
# Ubuntu/Debian: sudo apt-get install -y libstdc++6 libc6
```

### execvp Failed After Install

**Problem:** `error: execvp failed: No such file or directory`

**Cause:** The `.devkit` hidden file was not copied (should not happen with the script).

**Solution:** Re-run the installation script.
