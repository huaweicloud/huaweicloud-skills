# Prerequisites

## Table of Contents

- [1. hcloud CLI (KooCLI)](#1-hcloud-cli-kocli)
- [2. Python Environment](#2-python-environment)
- [3. Environment Variables](#3-environment-variables)
- [4. IAM Permissions](#4-iam-permissions)
- [5. Network](#5-network)
- [6. DevKit ECS Requirements](#6-devkit-ecs-requirements)
- [Windows GUI Environment Variable Setup](#windows-gui-environment-variable-setup)

---

## 1. hcloud CLI (KooCLI)

**Version Requirement**: >= 7.2.2

```bash
# Check if already installed
hcloud version

# If not installed or version too low, see installation guide
# See [CLI Installation Guide](cli-installation-guide.md)
```

**Verify AK/SK Configuration**:
```bash
hcloud configure list
```

If not configured ? see [CLI Installation Guide](cli-installation-guide.md) Section 4.

---

## 2. Python Environment

**Version Requirement**: Python 3.8+

```bash
python3 --version
# Expected: Python 3.8.x or higher
```

### Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| `paramiko` | Layer 1 SSH connection (Agent ? DevKit ECS) | `pip install "paramiko>=3.0.0"` |

```bash
# Install dependencies (using Huawei Cloud mirror for acceleration)
pip install "paramiko>=3.0.0" -i https://repo.huaweicloud.com/repository/pypi/simple

# Verify
python3 -c "import paramiko; print('paramiko installed successfully')"
```

---

## 3. Environment Variables

### Required Environment Variables

| Variable | Required | Purpose | Detection Order |
|----------|----------|---------|-----------------|
| `DEVKIT_ECS_USER` | Yes | DevKit ECS SSH login username | User ? Machine (NOT Process) |
| `DEVKIT_ECS_PASSWORD` | Yes | DevKit ECS SSH login password | User ? Machine (NOT Process) |

### Optional Environment Variables

| Variable | Purpose | Note |
|----------|---------|------|
| `HUAWEI_ACCESS_KEY` | Huawei Cloud AK | User configures via `hcloud configure set` themselves (AI never executes) |
| `HUAWEI_SECRET_KEY` | Huawei Cloud SK | User configures via `hcloud configure set` themselves (AI never executes) |
| `HW_SECURITY_TOKEN` | Temporary security token | Only needed for temporary AK/SK |

### Verify Environment Variables

**Linux/macOS**:
```bash
python3 -c 'import os,sys;_u="DEVKIT_ECS_USER";_p="DEVKIT_ECS_PASSWORD";ok=_u in os.environ and _p in os.environ;print("Env vars configured OK" if ok else "ERROR: DEVKIT_ECS_USER/DEVKIT_ECS_PASSWORD not set");sys.exit(0 if ok else 1)'
```

**Windows (PowerShell)**:
```powershell
python -c "import os,sys;_u='DEVKIT_ECS_USER';_p='DEVKIT_ECS_PASSWORD';ok=_u in os.environ and _p in os.environ;print('Env vars configured OK' if ok else 'ERROR: DEVKIT_ECS_USER/DEVKIT_ECS_PASSWORD not set');sys.exit(0 if ok else 1)"
```

> **Note**: `DEVKIT_ECS_EIP` is not an environment variable; it is automatically obtained via hcloud query.

### Password Complexity Requirements

`DEVKIT_ECS_PASSWORD` must comply with Huawei Cloud ECS password rules:
- 8?26 characters
- At least 3 character types: uppercase letters, lowercase letters, digits, special characters `!@#$%^&*_-+=`
- Must not contain the username

---

## 4. IAM Permissions

The IAM user needs ECS/VPC/EIP/IMS related permissions. See [IAM Permission Policies](iam-policies.md) for details.

**Quick Verification**:
```bash
hcloud ECS ListCloudServers --cli-region=cn-north-4 --limit=1
```

If 403 is returned ? insufficient permissions, see [IAM Permission Policies](iam-policies.md).

---

## 5. Network

### Security Group Port Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH login |


### Network Connectivity

- Agent local machine must be able to access Huawei Cloud API (hcloud CLI)
- Agent local machine must be able to SSH to DevKit ECS EIP
- DevKit ECS must be able to access the internet (to download DevKit installation package)
- DevKit ECS must be able to SSH to target servers defined in nodes.conf

---

## 6. DevKit ECS Requirements

| Requirement | Value |
|-------------|-------|
| Architecture | x86_64 (fixed) |
| OS | CentOS 7.6 or Ubuntu 20.04 |
| Disk Space | >= 40GB (system disk) |
| Memory | >= 8GB |
| Access | root permission |

---

## Windows GUI Environment Variable Setup

### Steps

1. Open **System Properties** ? **Advanced** ? **Environment Variables**
   - Shortcut: `Win + R` ? enter `sysdm.cpl` ? **Advanced** tab ? **Environment Variables**

2. In the **User variables** section, click **New**

3. Add `DEVKIT_ECS_USER`:
   - Variable name: `DEVKIT_ECS_USER`
   - Variable value: `<your_username>` (e.g., `root`)

4. Add `DEVKIT_ECS_PASSWORD`:
   - Variable name: `DEVKIT_ECS_PASSWORD`
   - Variable value: `<your_password>`

5. Click **OK** to save

6. **Restart terminal/PowerShell** to make environment variables take effect

7. Verify:
   ```powershell
   echo $env:DEVKIT_ECS_USER
   # Should output the username
   ```

> **?? Avoid `setx`**: `setx` records credentials in command history. Always use GUI to set environment variables.

### PowerShell Verification (does not display password value)

```powershell
# Only check if set (does not output value)
$user = [System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_USER", "User")
$pass = [System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "User")
if ($user -and $pass) {
    Write-Host "Environment variables configured OK"
} else {
    Write-Host "ERROR: DEVKIT_ECS_USER or DEVKIT_ECS_PASSWORD not set"
}
```

---

## Related Documents

- [CLI Installation Guide](cli-installation-guide.md) ? hcloud installation and configuration
- [Security Rules](rules.md) ? Environment variable detection rules and security constraints
- [IAM Permission Policies](iam-policies.md) ? Required permissions list
- [Troubleshooting](troubleshooting.md) ? Common issues and solutions
