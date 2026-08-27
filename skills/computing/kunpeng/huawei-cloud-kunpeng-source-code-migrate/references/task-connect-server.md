# Task 1: Connect to Source Code Server via SSH

Connect to the remote server where the source code resides using **paramiko-based SSH** (password from `MIGRATE_SSH_PASS` environment variable).

## Table of Contents

- [Overview](#overview)
- [Step 1: Verify SSH Configuration](#step-1-verify-ssh-configuration)
- [Step 2: Test SSH Connectivity](#step-2-test-ssh-connectivity)
- [Step 3: Verify Remote Server Information](#step-3-verify-remote-server-information)
- [Error Handling](#error-handling)

---

## Overview

This task establishes an SSH connection to the remote server where the source code to be analyzed is located. The connection uses **unified paramiko-based SSH** (password from `MIGRATE_SSH_PASS` environment variable, no ControlMaster, no key injection).

**Prerequisite:** The built-in `ssh_client.py test` subcommand must have been successfully run before this task. It handles:
- Pre-flight checks (validates `MIGRATE_SSH_PASS` is set, paramiko available)
- paramiko password connection test (reads password from `MIGRATE_SSH_PASS` env var)
- Save connection info to `/tmp/kunpeng_server_env.sh` (no password saved)

**Connection parameters (read from environment variables or provisioning output):**

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `KUNPENG_SERVER_HOST` | Yes | - | Remote server IP address (EIP) |
| `KUNPENG_SERVER_PORT` | No | `22` | SSH port number |
| `KUNPENG_SERVER_USER` | No | `root` | SSH username |
| `MIGRATE_SSH_PASS` | Yes | - | SSH password (read by paramiko, never in argv) |

> **Note:** The password is read from `MIGRATE_SSH_PASS` environment variable by `ssh_client.py` (paramiko mode) for each connection. The password is wiped from `os.environ` immediately after each connection is established.

---

## Step 1: Verify SSH Configuration

Before attempting any SSH connection, verify that SSH has been configured.

**Check environment variables:**

```bash
echo "KUNPENG_SERVER_HOST is set: $([ -n "$KUNPENG_SERVER_HOST" ] && echo 'YES' || echo 'NO')"
echo "KUNPENG_SERVER_PORT is set: $([ -n "$KUNPENG_SERVER_PORT" ] && echo 'YES' || echo 'NO')"
echo "KUNPENG_SERVER_USER is set: $([ -n "$KUNPENG_SERVER_USER" ] && echo 'YES' || echo 'NO')"
echo "MIGRATE_SSH_PASS is set: $([ -n "$MIGRATE_SSH_PASS" ] && echo 'YES' || echo 'NO')"
```

> **⚠️ Security: NEVER echo the actual values of environment variables.** Only check whether they are set (YES/NO).

**If `MIGRATE_SSH_PASS` is not set**, inform the user:

```
MIGRATE_SSH_PASS environment variable is not set. Please set it in your
own terminal (AI must never see the value):

  Linux / macOS:
    export MIGRATE_SSH_PASS='your-password'

  Windows PowerShell:
    $env:MIGRATE_SSH_PASS='your-password'

  Windows CMD:
    set MIGRATE_SSH_PASS=your-password

  Windows GUI (persistent):
    Settings > System > About > Advanced system settings >
    Environment Variables > User variables > New >
    Variable name: MIGRATE_SSH_PASS
    Variable value: <your-password>
    (Then restart VS Code or terminal)
```

**If `KUNPENG_SERVER_HOST` is not set**, inform the user:

```
KUNPENG_SERVER_HOST is not set. Please set it in your own terminal
(AI must never see the value):

  Linux / macOS:
    export KUNPENG_SERVER_HOST='<your-server-ip>'
    export KUNPENG_SERVER_PORT='22'
    export KUNPENG_SERVER_USER='root'

  Windows PowerShell:
    $env:KUNPENG_SERVER_HOST='<your-server-ip>'
    $env:KUNPENG_SERVER_PORT='22'
    $env:KUNPENG_SERVER_USER='root'

If the server was provisioned by provision_kunpeng_server.sh, the connection
info is saved in /tmp/kunpeng_server_env.sh. Load it with:
  source /tmp/kunpeng_server_env.sh

Then verify SSH with:
  python <skill_dir>/scripts/ssh_client.py test
```

---

## Step 2: Test SSH Connectivity

Test the SSH connection to the remote server using the built-in `ssh_client.py test` subcommand (paramiko mode).

**Test SSH connection:**

```bash
# Test SSH connection (paramiko reads MIGRATE_SSH_PASS from env)
python <skill_dir>/scripts/ssh_client.py test
```

**If the connection is successful**, you will see:
```
[OK] SSH connection verified (paramiko + password from env var).
```

**All subsequent remote command execution MUST use ssh_client.py:**

```bash
# Execute command on remote server via ssh_client.py (paramiko mode)
python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]

# Examples:
python <skill_dir>/scripts/ssh_client.py exec "uname -a" 30
python <skill_dir>/scripts/ssh_client.py exec "cat /etc/os-release"
python <skill_dir>/scripts/ssh_client.py exec "cd /usr/local/devkit && ./devkit --version"

# Upload a file via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<local_path>" "<remote_path>"

# Upload a directory recursively via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put-dir "<local_dir>" "<remote_dir>"
```

> **Note:** The `ssh_client.py` script uses unified paramiko-based SSH (password from `MIGRATE_SSH_PASS` environment variable). No `sshpass`, no ControlMaster, no key injection. The password is read from `os.environ` (or Windows user-level registry as fallback), never passed via argv, and wiped from `os.environ` immediately after each connection is established.

---

## Step 3: Verify Remote Server Information

After establishing the SSH connection, gather essential information about the remote server.

**Get OS information:**

```bash
python <skill_dir>/scripts/ssh_client.py exec "cat /etc/os-release"
```

**Get architecture information:**

```bash
python <skill_dir>/scripts/ssh_client.py exec "uname -m"
```

**Get kernel version:**

```bash
python <skill_dir>/scripts/ssh_client.py exec "uname -r"
```

**Get disk space information:**

```bash
python <skill_dir>/scripts/ssh_client.py exec "df -h"
```

**Get available memory:**

```bash
python <skill_dir>/scripts/ssh_client.py exec "free -h"
```

**Determine OS type for DevKit installation:**

Based on the OS information gathered, determine the OS category:

| OS Identifier | OS Category | DevKit Package Suffix |
|--------------|-------------|----------------------|
| `openEuler` | openEuler | `Kunpeng` or `x86-64` |
| `CentOS` | CentOS/RHEL | `Kunpeng` or `x86-64` |
| `Red Hat` | CentOS/RHEL | `Kunpeng` or `x86-64` |
| `EulerOS` | EulerOS | `Kunpeng` or `x86-64` |
| `Ubuntu` | Ubuntu/Debian | `Kunpeng` or `x86-64` |
| `Debian` | Ubuntu/Debian | `Kunpeng` or `x86-64` |
| `SUSE` | SUSE | `Kunpeng` or `x86-64` |
| `Kylin` | Kylin | `Kunpeng` or `x86-64` |
| `UOS` | UOS | `Kunpeng` or `x86-64` |
| `NeoKylin` | NeoKylin | `Kunpeng` or `x86-64` |

**Architecture check:**

| `uname -m` Output | Architecture | DevKit Package Architecture |
|-------------------|-------------|---------------------------|
| `x86_64` | x86_64 (Intel/AMD) | `x86-64` |
| `aarch64` | ARM64 (Kunpeng) | `Kunpeng` |

> **Note:** DevKit can be installed on both x86_64 and aarch64 architectures. The source code migration assessment analyzes code for ARM64 compatibility regardless of the server's current architecture.

---

## Error Handling

### SSH Connection Refused

**Problem:** `Connection refused`

**Cause:** SSH service is not running on the remote server, or the port is incorrect.

**Solution:**
1. Verify the SSH service is running on the remote server
2. Verify the port number in `KUNPENG_SERVER_PORT`
3. Check firewall rules on the remote server

### SSH Authentication Failed

**Problem:** `Authentication failed`

**Cause:** The password in `MIGRATE_SSH_PASS` is incorrect, or the username is wrong.

**Solution:**
1. Verify the `MIGRATE_SSH_PASS` environment variable is set to the correct password
2. Verify the `KUNPENG_SERVER_USER` environment variable is set to the correct username
3. Re-run the built-in `ssh_client.py test` subcommand to verify the connection

### SSH Host Unreachable

**Problem:** `No route to host` or `Network is unreachable`

**Cause:** Network connectivity issue.

**Solution:**
1. Verify the server IP address in `KUNPENG_SERVER_HOST`
2. Check network connectivity: `ping $KUNPENG_SERVER_HOST`
3. Check if the server is powered on and network is configured

### SSH Connection Timeout

**Problem:** `Connection timed out`

**Cause:** Network latency, firewall blocking, or SSH service not responding.

**Solution:**
1. Increase the connection timeout
2. Check firewall rules
3. Verify SSH service status on the remote server

### paramiko Not Installed

**Problem:** `paramiko is not installed`

**Cause:** The `paramiko` Python package is not available in the current environment.

**Solution:**
```bash
pip install paramiko
# or
pip3 install paramiko
```

### MIGRATE_SSH_PASS Not Set

**Problem:** `MIGRATE_SSH_PASS environment variable is not set`

**Cause:** The user has not set the `MIGRATE_SSH_PASS` environment variable in their terminal.

**Solution:**
Inform the user to set the environment variable (see [prerequisites.md](prerequisites.md#how-to-set-migrate_ssh_pass-cross-platform-guide) for cross-platform instructions).
