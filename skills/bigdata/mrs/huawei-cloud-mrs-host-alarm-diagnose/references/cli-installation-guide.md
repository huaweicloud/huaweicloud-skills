# CLI Installation Guide - MRS Alarm Diagnosis

This skill does not use KooCLI (`hcloud`). It calls the LakeWatch API through the bundled Python script `scripts/lakewatch_api_client.py`. This guide covers Python dependency installation, LakeWatch client configuration, and verification.

## Table of Contents

- [Python Installation](#python-installation)
- [Python Dependencies](#python-dependencies)
- [LakeWatch Client Configuration](#lakewatch-client-configuration)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

---

## Python Installation

### Required Version

- Python >= 3.7

### Linux

```bash
# CentOS / EulerOS / RHEL
sudo yum install -y python3 python3-pip

# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# Verify
python3 --version
```

### Windows

Download Python 3.7+ from https://www.python.org/downloads/windows/ and add `python.exe` to PATH.

```powershell
# Verify
python --version
```

> **Note**: On Windows use `python`, on Linux use `python3` for all `lakewatch_api_client.py` calls in this skill.

---

## Python Dependencies

| Dependency | Required On | Purpose | Install |
|------------|-------------|---------|---------|
| `pyyaml` | All platforms | YAML config parsing | `pip3 install pyyaml` |
| `cryptography` | Windows only | AES-256-CBC password encryption | `pip install cryptography` |

> On Linux, password encryption uses CryptoAPI (SCC) provided by the security component; `cryptography` is NOT required.

```bash
# Linux
pip3 install pyyaml

# Windows
pip install pyyaml cryptography
```

---

## LakeWatch Client Configuration

The LakeWatch client reads `scripts/lakewatch_api_config.yaml`. Configure the following before first use.

### 1. Configure the LakeWatch Service Endpoint

Edit `scripts/lakewatch_api_config.yaml`:

```yaml
server:
  host: "<lakewatch_server_ip>"     # LakeWatch service IP
  port: 28950                        # LakeWatch service port
  scheme: "https"
  timeout: 60
```

### 2. Configure the Authentication Account

```yaml
auth:
  username: "<lakewatch_username>"   # LakeWatch account, e.g. adminlakewatch
  # The password MUST be encrypted with --encrypt-password and pasted here.
  # Never store the plaintext password.
  encrypted_password: ""
```

### 3. Encrypt the Password (Interactive, No Echo)

Run the encryption command. It interactively prompts for the password (no echo), so the plaintext password never appears in the process list or command history:

```bash
# Linux
python3 scripts/lakewatch_api_client.py --encrypt-password

# Windows
python scripts/lakewatch_api_client.py --encrypt-password
```

Paste the output ciphertext into `auth.encrypted_password` in `lakewatch_api_config.yaml`.

> **Platform note**: Linux uses CryptoAPI (SCC); Windows uses AES-256-CBC with a local `.aes_key` file. The two ciphertexts are NOT interchangeable; encrypt on the platform where the skill will run. On Windows, the `.aes_key` file must be migrated together to decrypt on another machine.

### 4. SSL Configuration (Optional)

For an intranet environment with a self-signed certificate:

```yaml
crypto:
  verify_ssl: false              # set true to verify; false to skip (self-signed intranet only)
  ca_cert: ""                    # custom CA cert path; empty = system default
```

---

## Verify Installation

### Verify Python

```bash
# Linux
python3 -c "import yaml; print('pyyaml ok')"
# Windows
python -c "import yaml; print('pyyaml ok')"
```

### Verify LakeWatch Client

```bash
# List all available APIs (no authentication required)
python3 scripts/lakewatch_api_client.py --list-apis
```

Expected: a list of API names (`get_token`, `collect_alarm_node_res_data`, `collect_alarm_log_data`, `access_manager_get`, `query_alarm_skill`, etc.).

### Verify Authentication (Functional)

```bash
# Collect node resource data (requires valid credentials + reachable endpoint)
python3 scripts/lakewatch_api_client.py -a collect_alarm_node_res_data \
  -p 'cluster_id=<cluster_id>' \
  -p 'strategy_name=system-load' \
  -p 'node_name=<node_name>'
```

Expected: a JSON response with resource data. If authentication fails, see [Troubleshooting](#troubleshooting).

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'yaml'` | `pyyaml` not installed | `pip3 install pyyaml` |
| `ModuleNotFoundError: No module named 'cryptography'` (Windows) | `cryptography` not installed | `pip install cryptography` |
| `authentication failed` / 401 | Invalid or expired LakeWatch account | Re-check `auth.username` and re-encrypt the password with `--encrypt-password` |
| `connection timeout` | LakeWatch endpoint unreachable or wrong `server.host`/`port` | Check network and `server` config; verify SSL settings |
| `{"message":"Unknown exception","success":false,"code":"500"}` (Windows) | `"` inside a `-p` value not escaped as `"""` | Replace every `"` inside the value with `"""` (including inside `[]` and `{}`) |
| Token cache permission error | Cache dir not writable | Check `%TEMP%\lakewatch_token\` (Win) or `/tmp/lakewatch_token/` (Linux) permissions |
| `alarm_time 格式必须为...` | `alarm_time` format wrong | Use `yyyy/MM/dd HH:mm:ss GMT+X:XX`, e.g. `2026/07/01 20:54:00 GMT+08:00` |

---

## Security Best Practices

1. **Never store the plaintext password** — always use `--encrypt-password` and store only the ciphertext in `lakewatch_api_config.yaml`.
2. **Never input the plaintext password in conversation** — use the interactive `--encrypt-password` flow.
3. **Restrict file permissions** — `lakewatch_api_config.yaml` and `.aes_key` should be readable only by the owner (`chmod 600`).
4. **Rotate credentials regularly** — re-encrypt when the LakeWatch account password changes.
5. **Intranet self-signed certs** — only set `verify_ssl: false` for trusted intranet endpoints; prefer `ca_cert` for production.
