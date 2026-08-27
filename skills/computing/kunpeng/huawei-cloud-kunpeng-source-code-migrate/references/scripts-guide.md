# Built-in Scripts Guide

This document describes the built-in scripts included in this skill and their usage.

## Table of Contents

- [SSH Client Script](#ssh-client-script)
- [Server Provisioning Script](#server-provisioning-script)
- [DevKit Installation Script](#devkit-installation-script)

---

## SSH Client Script

This skill includes a **single unified SSH client script** (`scripts/ssh_client.py`) that handles ALL SSH operations across different platforms (Linux, macOS, Windows). It consolidates the former `ssh_setup.sh`, `ssh_helper.py`, and `_run_ssh.py` into one cross-platform Python script. **All remote command execution, file upload, and connection verification MUST use this script** instead of manually constructing SSH commands, to ensure portability and security.

**Script location:** `scripts/ssh_client.py`

**Features:**
- **Unified cross-platform** — works identically on Windows, Linux, and macOS (Python only, no .ps1/.sh wrappers)
- **No Huawei Cloud region dependency** — remote server can be on any cloud or on-premises
- **No hcloud CLI dependency** for SSH operations
- Reads password from `MIGRATE_SSH_PASS` environment variable (never passed via argv, so `ps -ef` cannot see it; wiped from `os.environ` immediately after each connection is established)
- Reads connection info from environment variables (`KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT`, `KUNPENG_SERVER_USER`)
- **Windows user-level registry fallback** via `winreg` — picks up env vars set via GUI / `SetEnvironmentVariable` even when the AI child process does not inherit them
- Never stores or logs any password
- Supports subcommands: `test` (verify connection), `exec` (run command), `put` (upload file), `put-dir` (upload directory), `get` (download file), `get-dir` (download directory), `get-report` (download DevKit report), `save-env` (save connection info)
- **MSYS2 path detection** — when MSYS2/Git Bash converts a Unix path (e.g., `/tmp/foo`) to a Windows path (e.g., `C:/Users/.../Temp/2/foo`), the script detects it and directs the caller to use the paramiko SFTP API directly. See [SFTP-First File Transfer](#sftp-first-file-transfer) below.
- No `sshpass`, no COC, no UniAgent dependency, no ControlMaster, no key injection

**Usage:**

```bash
# Verify SSH connection (runs 'echo SSH_OK && uname -a' on remote)
python <skill_dir>/scripts/ssh_client.py test

# Execute a remote command via SSH (paramiko reads MIGRATE_SSH_PASS from env)
python <skill_dir>/scripts/ssh_client.py exec "<remote_command>" [timeout]

# Upload a local file to remote server via SFTP
# IMPORTANT: On Windows (MSYS2/Git Bash), set MSYS_NO_PATHCONV=1 to prevent
# the shell from converting Unix-style remote paths (e.g. /tmp/foo) to Windows paths.
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<local_path>" "<remote_path>"

# Upload a local directory recursively to remote server via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put-dir "<local_dir>" "<remote_dir>"

# Download a remote file to local via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get "<remote_path>" "<local_path>"

# Download a remote directory recursively to local via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-dir "<remote_dir>" "<local_dir>"

# Download DevKit migration report (convenience command with defaults)
# Defaults: remote=/tmp/devkit-report, local=C:\devkit-report (Windows) or /home/devkit-report (Linux)
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-report
# Or with custom paths:
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py get-report "/tmp/devkit-report" "C:/devkit-report"

# Save connection info (host/port/user) to a temp env file (no password saved)
python <skill_dir>/scripts/ssh_client.py save-env

# Show help
python <skill_dir>/scripts/ssh_client.py --help

# Examples:
python scripts/ssh_client.py test
python scripts/ssh_client.py exec "uname -a" 30
python scripts/ssh_client.py exec "cat /etc/os-release"
python scripts/ssh_client.py exec "cd /usr/local/devkit && ./devkit --version"

# Upload DevKit install script to remote server (Windows example):
MSYS_NO_PATHCONV=1 python scripts/ssh_client.py put "C:\path\to\install_devkit.sh" "/tmp/install_devkit.sh"
```

**Subcommands:**

| Subcommand | Description | Required Args |
|------------|-------------|---------------|
| `test` | Verify SSH connection by running `echo SSH_OK && uname -a` | None |
| `exec` | Execute a shell command on the remote server | `<command>` (required), `[timeout]` (optional, default 120) |
| `put` | Upload a single file via SFTP | `<local_path>` (required), `<remote_path>` (required) |
| `put-dir` | Upload a directory recursively via SFTP | `<local_dir>` (required), `<remote_dir>` (required) |
| `get` | Download a single file via SFTP | `<remote_path>` (required), `<local_path>` (required) |
| `get-dir` | Download a directory recursively via SFTP | `<remote_dir>` (required), `<local_dir>` (required) |
| `get-report` | Download DevKit migration report files (filtered by `Code_Porting_*.{html,json,csv,txt}` pattern) | `[remote_dir]` (optional, default `/tmp/devkit-report`), `[local_dir]` (optional, default `C:\devkit-report` on Windows, `/home/devkit-report` on Linux/macOS) |
| `save-env` | Save connection info (host/port/user) to a temp env file (no password) | None |
| `--help` | Show help message | None |

**Environment variables (all required except where noted):**

| Variable | Description | Default |
|----------|-------------|---------|
| `KUNPENG_SERVER_HOST` | Remote server IP address or hostname | (required) |
| `KUNPENG_SERVER_PORT` | SSH port | `22` |
| `KUNPENG_SERVER_USER` | SSH username | `root` |
| `MIGRATE_SSH_PASS` | SSH password (read by paramiko, never in argv) | (required) |

**Important:**
- The `MIGRATE_SSH_PASS` environment variable must be set; the password is read from `os.environ` (or Windows user-level registry as fallback), never passed via argv, and wiped from `os.environ` immediately after each connection is established
- The script uses paramiko for all operations — no `ssh`/`scp` commands, no ControlMaster, no key injection
- For long-running commands (e.g., DevKit scan), set a larger timeout value (e.g., 120 or 180)
- The script returns the remote command's stdout, stderr, and exit code
- **Windows MSYS2 path conversion:** When using `put`, `put-dir`, `get`, `get-dir`, or `get-report` on MSYS2/Git Bash, the shell may convert Unix-style remote paths to Windows paths. The script detects this and directs you to use the paramiko SFTP API directly. See [SFTP-First File Transfer](#sftp-first-file-transfer) below.

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments / missing env var |
| 2 | paramiko not installed |
| 3 | SSH connection failed |
| -1 | Command timeout or runtime error |

### SFTP-First File Transfer

**Rule: For file transfer, always use paramiko SFTP API directly, not `ssh_client.py` CLI subcommands.**

On Windows + MSYS2/Git Bash, the shell converts Unix paths in command arguments to Windows paths before Python sees them (e.g., `/tmp/foo` → `C:/Users/.../Temp/2/foo`). This is an MSYS2 runtime behavior that cannot be fixed from within Python's `sys.argv`.

Instead of trying to work around this, **use the paramiko SFTP API directly from Python**. Paths are Python strings — no shell involved, no conversion, no quoting issues:

```python
import os, paramiko

host = os.environ.get('KUNPENG_SERVER_HOST')
port = int(os.environ.get('KUNPENG_SERVER_PORT', '22'))
user = os.environ.get('KUNPENG_SERVER_USER', 'root')
password = os.environ.get('MIGRATE_SSH_PASS')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=port, username=user, password=password, timeout=30)
sftp = client.open_sftp()

# Upload
sftp.put(r'C:\local\install_devkit.sh', '/tmp/install_devkit.sh')
sftp.chmod('/tmp/install_devkit.sh', 0o755)

# Download
sftp.get('/tmp/devkit-report/report.json', r'C:\devkit-report\report.json')

sftp.close()
client.close()
```

**Why SFTP, not `exec`:**

| SFTP (`put`/`get`) | `exec` with shell commands |
|--------------------|-----------------------------|
| Paths are Python strings — no shell conversion | Shell converts paths before Python sees them |
| Binary-safe byte stream | Needs base64 encoding for binary |
| No quoting needed | Multi-level quoting (local bash → paramiko → remote bash) |
| No length limits | Command-line length limits |

**AI agent workflow:**

1. **File transfer** → paramiko SFTP API directly (see above)
2. **Command execution** → `ssh_client.py exec "<cmd>"` (short commands only)
3. **Script execution** → upload via SFTP, then `exec "bash /tmp/script.sh"`

---

## Server Provisioning Script

This skill includes a built-in provisioning script (`scripts/provision_kunpeng_server.sh`) that automates the creation of a Kunpeng ECS instance on Huawei Cloud for migration assessment.

**Script location:** `scripts/provision_kunpeng_server.sh`

**Provisioned server specification:**

| Item | Value |
|------|-------|
| Region | cn-southwest-2 (Guiyang 1) |
| Flavor | kc1.2xlarge.2 (Kunpeng ARM64, 2C4G) |
| Image | Huawei Cloud EulerOS 2.0 Standard 64 bit for ARM |
| System Disk | 40GB High IO (GPSSD) |
| Network | New VPC + Subnet + EIP (300 Mbit/s BGP) |
| Security Group | SSH (TCP 22) inbound from agent IP only, all outbound |

**Usage:**

```bash
# Interactive mode (with confirmation prompt)
bash <skill_dir>/scripts/provision_kunpeng_server.sh

# Automated mode (skip confirmation, for skill-driven execution)
bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm

# Specify SSH source CIDR (recommended for security)
bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm --ssh-source=203.0.113.50/32
```

**Script options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--confirm` | Skip confirmation prompt | Off (interactive) |
| `--ssh-source=<CIDR>` | Restrict SSH inbound to this CIDR | Auto-detect agent IP /32 |

> **⚠️ Security: SSH source CIDR must NEVER be set to `0.0.0.0/0` (allow-all).** The script auto-detects the agent's public IP and restricts SSH to `<IP>/32`. If auto-detection fails, the script aborts and requires `--ssh-source` to be specified explicitly.

> **⚠️ SCP permission handling:** If the IAM account's SCP restricts `vpc:securityGroupRules:create`, the script cannot add SSH inbound rules via CLI. In this case, it prints clear instructions for the user to add the rule manually in the Huawei Cloud console.

> **⚠️ Cost warning:** The provisioned server incurs charges. At the end of the workflow, provide cleanup instructions as TEXT ONLY. **AI MUST NEVER auto-execute delete commands.**
> **⚠️ The script MUST NOT be executed without user confirmation.** Always ask the user before provisioning.
> **⚠️ The script MUST NOT delete any resources.** It only creates resources. Deletion is the user's responsibility.

**What the script does (AI MUST NOT replicate these steps manually):**
1. Pre-flight checks (hcloud installed, authenticated)
2. Auto-detects agent public IP for SSH source restriction (never 0.0.0.0/0)
3. Creates VPC with CIDR 192.168.0.0/16 via `hcloud VPC CreateVpc --vpc.name=... --vpc.cidr=...`
4. Waits for VPC to become ACTIVE
5. Creates Subnet with CIDR 192.168.1.0/24, gateway 192.168.1.1, DNS 100.125.1.250/100.125.21.250 via `hcloud VPC CreateSubnet --subnet.vpc_id=... --subnet.name=... --subnet.cidr=... --subnet.gateway_ip=... --subnet.dnsList.1=... --subnet.dnsList.2=...`
6. Waits for Subnet to become ACTIVE
7. Creates Security Group via `hcloud VPC CreateSecurityGroup --security_group.name=...`
8. Adds SSH inbound rule (TCP 22, restricted to agent IP /32) via `hcloud VPC CreateSecurityGroupRule` with correct v3 API parameters (`--security_group_rule.security_group_id`, `--security_group_rule.direction`, `--security_group_rule.protocol`, `--security_group_rule.multiport`, `--security_group_rule.remote_ip_prefix`, `--security_group_rule.ethertype`, `--security_group_rule.action`, `--security_group_rule.priority`)
9. Finds Huawei Cloud EulerOS 2.0 Standard 64 bit for ARM image ID via `hcloud IMS ListImages --__imagetype=gold --__os_type=Linux` and filtering for "Standard 64 bit for ARM" (excluding BareMetal images)
10. Creates EIP via `hcloud EIP CreatePublicip --publicip.type=5_bgp --bandwidth.name=... --bandwidth.size=300 --bandwidth.charge_mode=traffic --bandwidth.share_type=PER`
11. Creates ECS instance with a randomly generated password (for cloud-init only) via `hcloud ECS CreateServers --cli-jsonInput=<temp-file>`. The full request body (including `server.adminPass`) is built in a temporary JSON file (mode 0600) and passed via `--cli-jsonInput` to avoid leaking the password via `ps -ef`. The temp file is securely deleted with `shred -u` after the call. **The password is saved to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600) for use by `ssh_client.py`.**
12. Waits for ECS job to reach SUCCESS status
13. Saves connection info (EIP address, port, user, instance ID, region, AND `MIGRATE_SSH_PASS`) to `/tmp/kunpeng_server_env.sh` (chmod 600)

> **⚠️ Password policy:** The script generates a random password for cloud-init and saves it to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600, only readable by the current user). The password is NEVER printed to the user. SSH is configured by running the built-in `ssh_client.py test` subcommand after provisioning, which verifies the paramiko password connection (password read from `MIGRATE_SSH_PASS` environment variable, never passed via argv, wiped from `os.environ` immediately after each connection). After the source code scan completes (Task 3), the AI presents the Resource Cleanup Reminder — see [task-scan-source-code.md Step 6](task-scan-source-code.md#step-6-post-scan-reminders-after-assessment-completes). No password rotation reminder is needed.

**After provisioning, load the environment variables:**

```bash
source /tmp/kunpeng_server_env.sh
```

This sets `KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT`, `KUNPENG_SERVER_USER`, `KUNPENG_SERVER_ID`, `KUNPENG_SERVER_REGION`, AND `MIGRATE_SSH_PASS` automatically.

**Then verify SSH by running the built-in `ssh_client.py test` subcommand (unified paramiko: password connection test):**

```
→ Run: python <skill_dir>/scripts/ssh_client.py test
→ The script reads the server password from MIGRATE_SSH_PASS environment variable
  (never passed via argv, wiped from os.environ immediately after each connection)
→ All subsequent SSH operations use ssh_client.py subcommands:
    python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]
    python <skill_dir>/scripts/ssh_client.py put <local> <remote>
    python <skill_dir>/scripts/ssh_client.py put-dir <local_dir> <remote_dir>
    python <skill_dir>/scripts/ssh_client.py get <remote> <local>
    python <skill_dir>/scripts/ssh_client.py get-dir <remote_dir> <local_dir>
    python <skill_dir>/scripts/ssh_client.py get-report [remote_dir] [local_dir]
```

**Prerequisites for provisioning:**
- hcloud (KooCLI) >= 3.2.0 installed and authenticated
- Sufficient account balance and ECS quota in cn-southwest-2 region
- IAM permissions: `ECS FullAccess`, `VPC FullAccess`, `EIP FullAccess` (or equivalent)

---

## DevKit Installation Script

This skill includes a built-in installation script (`scripts/install_devkit.sh`) that automates the complete DevKit CLI installation process. **AI MUST use this script instead of manually executing step-by-step commands from markdown documents, to avoid errors and ensure consistency.**

**Script location:** `scripts/install_devkit.sh`

**What the script does (automatically):**
1. Detects OS type and architecture (x86_64 / aarch64)
2. Checks if DevKit is already installed (skips if satisfactory)
3. Installs system dependencies (python3, pip, curl) using the correct package manager
4. Downloads the correct DevKit package (auto-detects latest stable version, with fallback)
5. Extracts and installs to `/usr/local/devkit` (copies all files including hidden files like `.devkit` if present)
6. Verifies installation (version check, help check, src-mig check)

**Usage — Local install:**

```bash
# Standard local install (with sudo)
bash <skill_dir>/scripts/install_devkit.sh

# Install without sudo (to ~/devkit)
bash <skill_dir>/scripts/install_devkit.sh --no-sudo

# Skip all prompts
bash <skill_dir>/scripts/install_devkit.sh --yes

# Install specific version
bash <skill_dir>/scripts/install_devkit.sh --version=25.3.0

# Offline install (from a pre-downloaded tar.gz)
bash <skill_dir>/scripts/install_devkit.sh --offline=/path/to/DevKit-CLI-25.3.0-Linux-x86-64.tar.gz
```

**Usage — Remote install (via SSH + SFTP):**

```bash
# Step 1: Upload install script to remote server via SFTP
# IMPORTANT: On Windows (MSYS2/Git Bash), prefix with MSYS_NO_PATHCONV=1
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<skill_dir>/scripts/install_devkit.sh" "/tmp/install_devkit.sh"

# Step 2: Execute the install script on remote server
python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh --yes" 300
```

> **⚠️ Do NOT use stdin redirection** (`python ssh_client.py exec "cat > /tmp/x.sh" < local.sh`) — it does not work with paramiko. Always use the `put` SFTP subcommand for file upload.

**Script options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--version=VERSION` | DevKit version to install | Auto-detect latest stable |
| `--prefix=PATH` | Install prefix directory | `/usr/local` |
| `--no-sudo` | Install to `~/devkit` without root privileges | Off |
| `--skip-deps` | Skip dependency installation step | Off |
| `--offline=FILE` | Install from a local tar.gz file (no download) | Off |
| `--yes` | Skip all confirmation prompts | Off |

**Script exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Installation successful |
| 1 | Unsupported OS or architecture |
| 2 | Dependency installation failed |
| 3 | Download failed |
| 4 | Installation (extract/copy) failed |
| 5 | Verification failed |

> **⚠️ AI execution rule:** When installing DevKit (either locally or remotely), ALWAYS use `install_devkit.sh` instead of manually running individual commands. The script handles OS detection, architecture selection, hidden file copying, version fallback, and verification — all of which are error-prone when done step-by-step by AI.
