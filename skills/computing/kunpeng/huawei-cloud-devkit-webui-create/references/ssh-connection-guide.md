# SSH Connection Guide - Python paramiko SSH

> **This guide replaces the old COC passwordless login and password-based SSH methods.**
>
> The old methods are **prohibited** because:
> - `--server.adminPass` in `hcloud ECS CreateServers` exposes passwords in `ps -ef`
> - `$env(DEVKIT_ECS_PASSWORD)` is readable by other processes on the same host
> - `sshpass -p <password>` exposes passwords in `ps -ef`
> - COC passwordless login requires UniAgent (chicken-and-egg problem) and third-party skill dependency
>
> The new method uses **Python paramiko** to SSH into the ECS. The password is decrypted from KMS
> in Python process memory and passed to `SSHClient.connect(password=...)` — it never appears
> in `ps -ef`, shell variables, or command-line arguments.

## Table of Contents

- [1. How It Works](#1-how-it-works)
- [2. Prerequisites](#2-prerequisites)
- [3. Usage](#3-usage)
- [4. Security Design](#4-security-design)
- [5. Handling Rules When SSH Is Unreachable](#5-handling-rules-when-ssh-is-unreachable)
- [6. Prohibited Methods](#6-prohibited-methods)

---

## 1. How It Works

```
Agent Machine                          Target ECS
┌─────────────────┐                   ┌──────────────────┐
│ Python process   │                   │                  │
│                  │  paramiko SSH     │  SSH server      │
│ KMS decrypt ────┼───password=───►───┼── port 22        │
│ (in memory only) │  (never in ps)    │                  │
│                  │                   │  install scripts │
│ SFTP upload ─────┼──────────────────►│  /tmp/           │
│                  │                   │                  │
│ exec_command ────┼──────────────────►│  bash install.sh │
│                  │                   │                  │
│ del password ────│                   │                  │
│ KMS delete key ──│                   │                  │
└─────────────────┘                   └──────────────────┘
```

The `create_ecs_and_setup_devkit.py install` command:
1. Decrypts password from KMS (in Python process memory)
2. Connects to ECS via paramiko `SSHClient.connect(password=decrypted)`
3. Uploads install scripts via SFTP
4. Executes `install_devkit_webui.sh` on remote ECS
5. Executes `verify_devkit.sh` on remote ECS
6. Deletes password variable (`del password`)
7. Schedules KMS key deletion (7 days)

---

## 2. Prerequisites

- Python 3.8+ with paramiko + Huawei Cloud Python SDK (ECS + KMS) installed:
  ```bash
  # Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
  PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
  pip install $PIP_INDEX huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkkms paramiko
  ```
- EIP bound to target ECS (via hcloud CLI)
- Security group ports 22 and 8086 open
- `kms_key_id` and `kms_cipher_text` from Phase 1 (create)

---

## 3. Usage

```bash
# After EIP is bound and security group is configured:
python scripts/create_ecs_and_setup_devkit.py install \
  --region cn-north-4 \
  --eip <EIP_ADDRESS> \
  --kms-key-id <kms_key_id> \
  --kms-cipher-text-file <kms_cipher_text_file> \
  --devkit-url "https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz"
```

Optional parameters:
- `--install-path` — Custom DevKit installation path
- `--install-port` — Custom DevKit WebUI port

---

## 4. Security Design

### Why paramiko is secure

| Aspect | paramiko (Secure) | CLI SSH (Insecure) |
|--------|-------------------|---------------------|
| Password transmission | `SSHClient.connect(password=var)` — Python function argument, not visible in `ps -ef` | `sshpass -p PWD` or `ssh ... && echo PWD` — visible in `ps -ef` |
| Password storage | Python variable in process memory | Shell variable or env var, readable by `/proc/pid/environ` |
| Password lifetime | `del password` after use — garbage collected | Persists in shell history, env vars |
| Script upload | SFTP via paramiko channel — no CLI | `scp` with password on CLI — visible in `ps -ef` |
| Command execution | `exec_command()` via SSH channel — no CLI | `ssh user@host "cmd"` with password — visible in `ps -ef` |

### Password lifecycle

```
1. KMS decrypt → Python variable (in memory only)
2. paramiko connect(password=var) → SSH session established
3. SFTP upload + exec_command → DevKit installed
4. del password → variable garbage collected
5. KMS key scheduled for deletion → password ceases to exist after 7 days
```

---

## 5. Handling Rules When SSH Is Unreachable

When the SSH connection fails (port 22 is unreachable), ask the user again to choose a security group rule configuration method (manual or automatic). Do not skip this step.

> **⚠️ When SSH is unreachable, do NOT auto-modify security group rules.**
>
> Prompt the user to manually add rules in the Huawei Cloud console:
> - Port 22 (TCP) — SSH access
> - Port 8086 (TCP) — DevKit WebUI access

---

## 6. Prohibited Methods

| Method | Reason |
|--------|--------|
| `hcloud --server.adminPass="$DEVKIT_ECS_PASSWORD"` | Password visible in `ps -ef` |
| `expect` + `$env(DEVKIT_ECS_PASSWORD)` | Environment variable readable by other processes |
| `sshpass -p <password>` | Password visible in `ps -ef` |
| `sshpass -e` + `SSHPASS` | Environment variable readable by other processes |
| `ssh -o PasswordAuthentication` with password on CLI | Password visible in `ps -ef` |
| Hardcoded password in scripts | Password stored in plaintext |
| Printing password in any output | Password must only exist in Python process memory and KMS |
| COC passwordless login | Requires UniAgent (chicken-and-egg); adds third-party skill dependency |
