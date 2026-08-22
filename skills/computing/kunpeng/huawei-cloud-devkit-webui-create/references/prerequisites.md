# Prerequisites - Kunpeng DevKit WebUI Installation

This document details all prerequisite checks before starting the DevKit installation workflow.

## Table of Contents

- [Environment Variables for Python SDK Credentials](#environment-variables-for-python-sdk-credentials)
- [hcloud CLI Check](#hcloud-cli-check)
- [Python SDK + paramiko Check](#python-sdk--paramiko-check)
- [Target ECS Requirements](#target-ecs-requirements)

---

## Environment Variables for Python SDK Credentials

The Python SDK scripts (`create_ecs_and_setup_devkit.py`) read credentials from environment variables, **NOT from `hcloud configure list`**. The `hcloud configure list` command shows masked/desensitized AK/SK values (e.g., `HPU****6JZ`) which cannot be used by the Python SDK.

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `HW_ACCESS_KEY` | **Yes** | Huawei Cloud Access Key ID (AK) | `HPUAT5***` (full value, not masked) |
| `HW_SECRET_KEY` | **Yes** | Huawei Cloud Secret Access Key (SK) | Full SK value |
| `HW_SECURITY_TOKEN` | No | Temporary security token | Only needed for temporary AK/SK |
| `HUAWEICLOUD_SDK_PROJECT_ID` | Recommended | Project ID for the target region | `8966ec7b5e3b4bba8609666955971c71` |

### Verification

```bash
# Linux — verify HW_ACCESS_KEY / HW_SECRET_KEY are set (values never printed)
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
# Windows (cmd / PowerShell)
python -c "import os,sys;ak=os.environ.get('HW_ACCESS_KEY','');sk=os.environ.get('HW_SECRET_KEY','');ok=bool(ak) and bool(sk);print('AK/SK configured OK' if ok else 'ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set');sys.exit(0 if ok else 1)"
```

**If verification reports ERROR (variables not set), configure them per OS:**

**Linux:** add `export HW_ACCESS_KEY=...` / `export HW_SECRET_KEY=...` to your shell profile (`~/.bashrc`, `~/.zshrc`) or a secrets manager, then `source` the profile.

**Windows GUI Setup (System environment variables):**

1. Press `Win + R`, type `sysdm.cpl`, press Enter → opens System Properties
2. Switch to the **Advanced** tab → click **Environment Variables...**
3. In the **System variables** section (lower half) → click **New...**
4. Add `HW_ACCESS_KEY`:
   - Variable name: `HW_ACCESS_KEY`
   - Variable value: _<your Access Key ID>_
   - Click OK
5. Click **New...** again, add `HW_SECRET_KEY`:
   - Variable name: `HW_SECRET_KEY`
   - Variable value: _<your Secret Access Key>_
   - Click OK
6. (Optional, temporary credentials only) Add `HW_SECURITY_TOKEN` the same way
7. Click OK on all dialogs to close
8. **Restart your terminal / Python process** — system environment variables are loaded only at process startup
9. Re-run the verification command above

> **Why GUI instead of `setx`?** `setx HW_ACCESS_KEY=...` records the credential in command history (visible via `doskey /history` or PowerShell `Get-History`), risking leakage. The GUI keeps the value out of command history.

> **⚠️ Security rules:**
> - **Never** set these variables in conversation or hardcode them in scripts
> - **Never** print the full AK/SK values
> - For temporary credentials, also set `HW_SECURITY_TOKEN`

---

## hcloud CLI Check

Huawei Cloud CLI (hcloud / KooCLI) >= 3.2.0 is required. **All cloud operations except ECS creation, KMS, and SSH use hcloud CLI.**

```bash
hcloud version
# Expected: >= 3.2.0
```

If not installed or version is too low, see [cli-installation-guide.md](cli-installation-guide.md) for installation guide.

Verify authentication configuration:

```bash
hcloud configure list
# Verify output contains valid AK/SK configuration
```

If no valid credentials exist, stop here and configure authentication first.

---

## Python SDK + paramiko Check

Python 3.8+ and the Huawei Cloud Python SDK (ECS + KMS modules) + paramiko are required for ECS creation, KMS password encryption, and SSH DevKit installation. **The password never leaves the Python process memory.**

```bash
python3 --version
# Expected: >= 3.8

# Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
pip install $PIP_INDEX huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkkms paramiko
```

Verify SDK installation:

```bash
python3 -c "import huaweicloudsdkecs; print('ECS SDK OK')"
python3 -c "import huaweicloudsdkkms; print('KMS SDK OK')"
python3 -c "import paramiko; print('paramiko OK')"
```

> **Why Python SDK for ECS + KMS + paramiko for SSH?**
>
> - **ECS**: The hcloud CLI passes `--server.adminPass` as a command-line argument, which is visible in `ps -ef` output. The Python SDK passes `adminPass` as an API parameter in process memory.
> - **KMS**: Encrypting the password via Python SDK ensures the password never leaves the Python process. Only `kms_key_id` and `kms_cipher_text` are exported.
> - **paramiko SSH**: The password is decrypted from KMS and passed to `SSHClient.connect(password=...)` as a Python function argument. It never appears in `ps -ef`, shell variables, or command-line arguments.
>
> **Other cloud operations (EIP, VPC) use hcloud CLI** — no additional Python SDK packages needed.

---

## Environment Variables for Python SDK Credentials

The Python SDK scripts (`create_ecs_and_setup_devkit.py`) read credentials from environment variables, **NOT from `hcloud configure list`**. The `hcloud configure list` command shows masked/desensitized AK/SK values (e.g., `HPU****6JZ`) which cannot be used by the Python SDK.

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `HW_ACCESS_KEY` | **Yes** | Huawei Cloud Access Key ID (AK) | `HPUAT5***` (full value, not masked) |
| `HW_SECRET_KEY` | **Yes** | Huawei Cloud Secret Access Key (SK) | Full SK value |
| `HW_SECURITY_TOKEN` | No | Temporary security token | Only needed for temporary AK/SK |
| `HUAWEICLOUD_SDK_PROJECT_ID` | Recommended | Project ID for the target region | `8966ec7b5e3b4bba8609666955971c71` |

### Verification

```bash
# Linux — verify HW_ACCESS_KEY / HW_SECRET_KEY are set (values never printed)
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
# Windows (cmd / PowerShell)
python -c "import os,sys;ak=os.environ.get('HW_ACCESS_KEY','');sk=os.environ.get('HW_SECRET_KEY','');ok=bool(ak) and bool(sk);print('AK/SK configured OK' if ok else 'ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set');sys.exit(0 if ok else 1)"
```

**If verification reports ERROR (variables not set), configure them per OS:**

**Linux:** add `export HW_ACCESS_KEY=...` / `export HW_SECRET_KEY=...` to your shell profile (`~/.bashrc`, `~/.zshrc`) or a secrets manager, then `source` the profile.

**Windows GUI Setup (System environment variables):**

1. Press `Win + R`, type `sysdm.cpl`, press Enter → opens System Properties
2. Switch to the **Advanced** tab → click **Environment Variables...**
3. In the **System variables** section (lower half) → click **New...**
4. Add `HW_ACCESS_KEY`:
   - Variable name: `HW_ACCESS_KEY`
   - Variable value: _<your Access Key ID>_
   - Click OK
5. Click **New...** again, add `HW_SECRET_KEY`:
   - Variable name: `HW_SECRET_KEY`
   - Variable value: _<your Secret Access Key>_
   - Click OK
6. (Optional, temporary credentials only) Add `HW_SECURITY_TOKEN` the same way
7. Click OK on all dialogs to close
8. **Restart your terminal / Python process** — system environment variables are loaded only at process startup
9. Re-run the verification command above

> **Why GUI instead of `setx`?** `setx HW_ACCESS_KEY=...` records the credential in command history (visible via `doskey /history` or PowerShell `Get-History`), risking leakage. The GUI keeps the value out of command history.

> **⚠️ Security rules:**
> - **Never** set these variables in conversation or hardcode them in scripts
> - **Never** print the full AK/SK values
> - For temporary credentials, also set `HW_SECURITY_TOKEN`

---

## Target ECS Requirements

| Requirement | Value |
|-------------|-------|
| Architecture | **aarch64** (Kunpeng processor) |
| OS | **CentOS 7.6** or **Ubuntu 18.04** (only these two are compatibility-verified) |
| Disk space | >= 2GB available |
| Memory | >= 4GB |
| Access | root privileges required |
| EIP | Must be bound for paramiko SSH access |
| Security group | Ports 22 and 8086 must be open |
