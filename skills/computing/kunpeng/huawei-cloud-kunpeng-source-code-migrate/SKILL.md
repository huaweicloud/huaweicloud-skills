---
name: huawei-cloud-kunpeng-source-code-migrate
description: |
  Analyze the migrability of C/C++/ASM/Fortran/Go/Java/Python/Scala source code to Kunpeng (ARM64) platform using Huawei DevKit CLI tool. Connect to the source server via SSH, install DevKit, scan source code, and generate a migration assessment report.
  If the user does not have a remote server, this skill can automatically provision a Kunpeng ECS instance on Huawei Cloud (Guiyang Region 1) using hcloud CLI.
  Use this skill when the user wants to: (1) assess source code portability/migrability to Kunpeng ARM platform, (2) scan C/C++/ASM/Fortran/Go/Java/Python/Scala code for migration issues, (3) generate a Kunpeng migration report for their software project, (4) check source code compatibility with ARM64/Kunpeng architecture, (5) provision a Kunpeng server on Huawei Cloud for migration assessment.
  Trigger: user mentions "鲲鹏移植", "鲲鹏迁移", "Kunpeng migration", "Kunpeng porting", "源码迁移", "源码移植", "ARM64迁移", "ARM移植评估", "DevKit", "可迁移性分析", "migrability", "porting assessment", "migration report", "鲲鹏评估", "购买鲲鹏服务器", "鲲鹏云服务器", "Kunpeng ECS"
---

# Kunpeng Source Code Migration Assessment

Analyze the migrability of C/C++/ASM/Fortran/Go/Java/Python/Scala source code to Kunpeng (ARM64) platform using Huawei DevKit CLI tool.

## Overview

This skill assesses source code migrability to the Kunpeng (ARM64) platform using Huawei DevKit CLI. It connects to a source server via SSH (or installs locally), installs DevKit, scans source code, and generates a migration assessment report. If the user has no remote server, it can automatically provision a Kunpeng ECS instance on Huawei Cloud (Guiyang Region 1) via hcloud CLI.

**Architecture:** Local detection + remote execution + SFTP transfer. All SSH operations use the unified `scripts/ssh_client.py` (paramiko + password env var), cross-platform consistent. See the Architecture section below for the full tree.

**Applicable scenarios:**
- Assess source code portability/migrability to Kunpeng ARM platform
- Scan C/C++/ASM/Fortran/Go/Java/Python/Scala code for migration issues
- Generate a Kunpeng migration assessment report for a software project
- Check source code compatibility with ARM64/Kunpeng architecture
- Provision a Kunpeng server on Huawei Cloud for migration assessment

**Report save path (fixed unless user explicitly requests otherwise):** Windows → `C:\devkit-report\`, Linux/macOS → `/home/devkit-report/`.

## Prerequisites

**CLI version requirements:**

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.x | Run `ssh_client.py`, `detect_os.py`, paramiko dependency |
| paramiko | latest stable | SSH connection (`pip install paramiko`) |
| hcloud (KooCLI) | >= 3.2.0 | Only needed for provisioning path (Step 3d) |
| DevKit CLI | auto-installed by `install_devkit.sh` | Source code migration scan |

**Authentication:**
- **SSH credentials (existing server, Step 3c):** User must set env vars `KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT` (default 22), `KUNPENG_SERVER_USER` (default root), `MIGRATE_SSH_PASS` in their own terminal. AI must NEVER ask for or echo these values.
- **Huawei Cloud AK/SK (provisioning path, Step 3d):** User must run `hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<your-ak> --cli-secret-key=<your-sk>` in their own terminal. AI must NEVER ask for AK/SK.

**IAM permissions (Step 3d only):** Required for provisioning a Kunpeng ECS on Huawei Cloud. Minimum set: ECS create/list/delete, VPC create/get/delete, Subnet, SecurityGroup, EIP create/delete, IMS list, IAM projects list. See [references/iam-policies.md](references/iam-policies.md) for the full policy JSON and setup instructions.

**OS support:** DevKit local install supports openEuler/CentOS/Ubuntu/Kylin/UOS/EulerOS/Debian/SUSE/NeoKylin. Windows and macOS are NOT supported for local install — must use a remote Linux server.

## Core Commands

**1. Local OS detection:**
```bash
python <skill_dir>/scripts/detect_os.py
```

**2. SSH connection & remote execution (unified paramiko client):**
```bash
python <skill_dir>/scripts/ssh_client.py test                              # Test SSH connection
python <skill_dir>/scripts/ssh_client.py exec "uname -a" 30                # Execute remote command
python <skill_dir>/scripts/ssh_client.py put <local> <remote>              # SFTP upload single file
python <skill_dir>/scripts/ssh_client.py put-dir <local_dir> <remote_dir>  # SFTP upload directory
python <skill_dir>/scripts/ssh_client.py get-report                        # Download migration report
```

**3. DevKit installation:**
```bash
bash <skill_dir>/scripts/install_devkit.sh --yes
```

**4. Source code migration scan (DevKit CLI):**
```bash
# C/C++ project (with build command):
devkit porting src-mig -i /home/project -s 'c, c++, asm' -b make -c 'make all' -p gcc9.3.0 -o /tmp/devkit-report -r all

# Java/Python project (no build command):
devkit porting src-mig -i /home/project -s 'java, python' -o /tmp/devkit-report -r all
```

**5. Kunpeng ECS auto-provisioning (Step 3d only):**
```bash
bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm
```

**6. hcloud CLI install & configure (Step 3d only):**
```bash
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -xzf huaweicloud-cli-linux-amd64.tar.gz && chmod +x hcloud && sudo mv hcloud /usr/local/bin/
hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<your-ak> --cli-secret-key=<your-sk>
hcloud version   # Expected: >= 3.2.0
```

## Parameter Confirmation

AI must confirm the following parameters with the user before execution.

**SSH connection parameters (env vars, set by user in their own terminal):**

| Parameter | Env Var | Required | Default | Description |
|-----------|---------|----------|---------|-------------|
| Server address | `KUNPENG_SERVER_HOST` | Yes | - | Remote server IP/hostname |
| SSH port | `KUNPENG_SERVER_PORT` | No | `22` | SSH port |
| SSH username | `KUNPENG_SERVER_USER` | No | `root` | SSH login user |
| SSH password | `MIGRATE_SSH_PASS` | Yes | - | Read by paramiko, never in argv, wiped from `os.environ` after each connection |

**DevKit scan parameters (confirm with user before scanning):**

| Parameter | CLI option | Required | Default | Description |
|-----------|-----------|----------|---------|-------------|
| Source path | `-i` | Yes | - | Source code directory (MUST ask user first) |
| Output dir | `-o` | Yes | `/tmp/devkit-report` | Report output dir (must exist) |
| Languages | `-s` | Yes | - | `c, c++, asm, fortran, go, java, python, scala` (lowercase, comma-separated) |
| Build command | `-c` | No | None | e.g. `'make all'` |
| Build tool | `-b` | No | None | `make/cmake/automake/go/bazel/blade` |
| Compiler version | `-p` | No | None | e.g. `gcc9.3.0` |
| Report format | `-r` | No | `all` | `all/json/html/csv` |
| Target OS | `-t` | No | auto-detect | e.g. `openEuler22.03` |
| Concurrency | `-np` | No | `1` | Concurrent processes |

> **⚠️ AI MUST ask the user for the source code path before scanning. Do NOT scan or upload local files without user confirmation.**

## ⛔ Prohibited Operations

| Prohibited Operation | Reason |
|---------------------|--------|
| ❌ Ask user to input SSH credentials in conversation | Credentials must only be read from environment variables |
| ❌ Echo/print SSH password or any credentials | Prevent credential leakage |
| ❌ Store credentials in plain text files | Credentials must only exist in environment variables |
| ❌ Execute destructive commands on remote server (rm -rf, format, etc.) | Prevent irreversible damage |
| ❌ Modify source code without user confirmation | Migration assessment is read-only |
| ❌ Install packages outside DevKit scope | Only DevKit and its dependencies may be installed |
| ❌ Scan without asking the user for the source code path | Must always ask where the source code is |
| ❌ Delete any cloud resources without explicit user confirmation | Resource deletion is irreversible and HIGH-RISK |
| ❌ Execute any `hcloud ... Delete*` command autonomously | All delete operations require explicit user confirmation |

If a user requests a prohibited operation, refuse and inform: "Per security constraints, this skill does not allow [specific operation]. Please perform this operation manually if needed."

## Architecture

```
Kunpeng Source Code Migration Assessment
├── DetectLocalOS     (Detect agent OS → determine DevKit install path)
├── PrepareServer     (Determine where to install DevKit and run scan)
│   ├── LocalInstall  (Install DevKit locally — only if OS is supported)
│   ├── RemoteInstall (Install DevKit on remote server via SSH)
│   │   ├── HasServer (Configure SSH via ssh_client.py: paramiko + password env var)
│   │   └── NoServer  (Install hcloud CLI → Provision Kunpeng ECS → Configure SSH)
│   └── NotSupported  (Local OS not supported → must use remote server)
├── ConnectServer     (SSH connect via paramiko + MIGRATE_SSH_PASS env var)
├── InstallDevKit     (Detect OS and install DevKit CLI tool)
└── ScanSourceCode    (Scan source code → generate report → save to fixed local path)
    └── ReportSave    (Windows: C:\devkit-report\ | Linux/macOS: /home/devkit-report/)
```

> **⚠️ Task 0 (DetectLocalOS + PrepareServer) MUST be executed first** — it determines the entire workflow path.

## SSH Connection Strategy

All SSH operations use the unified `scripts/ssh_client.py` (paramiko + password from env var). No `ssh`/`scp` commands, no ControlMaster, no key injection, no Huawei Cloud region dependency. Works identically on Windows, Linux, and macOS.

**Environment variables (set by user in their own terminal; AI never sees values):**

| Variable | Description | Default |
|----------|-------------|---------|
| `KUNPENG_SERVER_HOST` | Remote server IP/hostname | (required) |
| `KUNPENG_SERVER_PORT` | SSH port | `22` |
| `KUNPENG_SERVER_USER` | SSH username | `root` |
| `MIGRATE_SSH_PASS` | SSH password (read by paramiko, never in argv, wiped after each connection) | (required) |

**Setting env vars (cross-platform):**

```bash
# Linux / macOS (current session):
export KUNPENG_SERVER_HOST='<your-server-ip>'
export KUNPENG_SERVER_PORT='22'
export KUNPENG_SERVER_USER='root'
export MIGRATE_SSH_PASS='<your-password>'

# Windows PowerShell (current session):
$env:KUNPENG_SERVER_HOST='<your-server-ip>'
$env:KUNPENG_SERVER_PORT='22'
$env:KUNPENG_SERVER_USER='root'
$env:MIGRATE_SSH_PASS='<your-password>'

# Windows (persistent, GUI): Settings > Environment Variables > User > New
# (requires IDE/terminal restart)
```

**Credential resolution priority** (first match wins):
1. Current process env vars (`export` / `$env:`)
2. `/tmp/kunpeng_server_env.sh` (Linux/macOS) or `%TEMP%/kunpeng_server_env.sh` (Windows)
3. Windows user-level registry (`winreg`) — fallback for GUI-set vars
4. Default value

**`ssh_client.py` subcommands:**

| Subcommand | Description |
|------------|-------------|
| `test` | Verify SSH connection (`echo SSH_OK && uname -a`) |
| `exec "<cmd>" [timeout]` | Execute a shell command on the remote server |
| `put <local> <remote>` | Upload a single file via SFTP |
| `put-dir <local_dir> <remote_dir>` | Upload a directory recursively via SFTP |
| `get <remote> <local>` | Download a single file via SFTP |
| `get-dir <remote_dir> <local_dir>` | Download a directory recursively via SFTP |
| `get-report [remote_dir] [local_dir]` | Download DevKit report (filtered by `Code_Porting_*.{html,json,csv,txt}`). Defaults: remote=`/tmp/devkit-report`, local=`C:\devkit-report` (Win) or `/home/devkit-report` (Linux) |
| `save-env` | Save connection info (host/port/user) to a temp env file (no password) |

### 📦 SFTP-First File Transfer (Critical for Windows + MSYS2)

> **⚠️ On Windows + MSYS2/Git Bash, the shell converts Unix paths in command arguments to Windows paths before Python sees them** (e.g., `/tmp/foo` → `C:/Users/.../Temp/2/foo`). This cannot be fixed from within Python's `sys.argv`.

**Rule: For file transfer, always use paramiko SFTP API directly from Python, not `ssh_client.py` CLI subcommands.**

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
sftp.put(r'C:\local\install_devkit.sh', '/tmp/install_devkit.sh')
sftp.chmod('/tmp/install_devkit.sh', 0o755)
sftp.close()
client.close()
```

**AI agent workflow:**
1. **File transfer** → paramiko SFTP API directly (see above)
2. **Command execution** → `ssh_client.py exec "<cmd>"` (short commands only)
3. **Script execution** → upload via SFTP, then `exec "bash /tmp/script.sh"`

When `ssh_client.py put`/`get` detects a mangled Windows path, it exits with an error directing you to use the paramiko SFTP API directly. See [references/scripts-guide.md#sftp-first-file-transfer](references/scripts-guide.md#sftp-first-file-transfer) and [references/troubleshooting.md#7-msys2-path-conversion-error-windows-only](references/troubleshooting.md#7-msys2-path-conversion-error-windows-only).

## Built-in Scripts

**AI MUST use these scripts instead of manually executing step-by-step commands.**

📄 Detailed guide → [references/scripts-guide.md](references/scripts-guide.md)

| Script | Description |
|--------|-------------|
| [detect_os.py](scripts/detect_os.py) | Local OS detection (outputs os_type/arch/local_install_supported) |
| [ssh_client.py](scripts/ssh_client.py) | **Unified cross-platform SSH client** (paramiko + env vars). Subcommands: `test`, `exec`, `put`, `put-dir`, `get`, `get-dir`, `get-report`, `save-env` |
| [install_devkit.sh](scripts/install_devkit.sh) | DevKit CLI installation (auto-detect OS/arch, download, install, verify) |
| [provision_kunpeng_server.sh](scripts/provision_kunpeng_server.sh) | Kunpeng ECS provisioning (Huawei Cloud Guiyang Region 1) |

## Supported Languages

| Language | File Extensions | Migration Concerns |
|----------|----------------|-------------------|
| C | `.c`, `.h` | Inline assembly, platform-specific headers, byte order, pointer size |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp` | Same as C, plus name mangling, ABI compatibility |
| Assembly (ASM) | `.s`, `.S`, `.asm` | Architecture-specific instructions, registers, calling conventions |
| Fortran | `.f`, `.f90`, `.f95`, `.f03` | Compiler intrinsics, MPI library compatibility |
| Go | `.go` | CGO calls, assembly files, architecture-specific build tags |
| Java | `.java` | JNI native libraries, architecture-specific dependencies |
| Python | `.py` | C extensions (Cython, CFFI), native bindings |
| Scala | `.scala` | JNI calls, native library dependencies |

---

## Core Workflows

### Task 0: Detect Local OS and Prepare Environment

**This is the FIRST task.** It detects the agent's local OS and determines the DevKit installation path.

**Step 1: Detect local OS:**

```bash
python <skill_dir>/scripts/detect_os.py
```

Outputs `os_type`, `os_name`, `os_version`, `arch`, `local_install_supported` as key=value pairs. Works on all platforms without external dependencies.

> **⚠️ AI MUST use `detect_os.py`** instead of manually running `uname -m`, `cat /etc/os-release`, PowerShell, etc.

**DevKit-supported local OS list:**

| OS | Minimum Version | Notes |
|----|----------------|-------|
| openEuler | 20.03 LTS | Recommended for Kunpeng |
| CentOS | 7.6 | Also supports 8.0 |
| Ubuntu | 18.04 | Also supports 20.04, 22.04 |
| Kylin | V10 | Domestic OS |
| UOS | 20 | Domestic OS |
| EulerOS | 2.8 | Also supports 2.9 |
| Debian | 10 | Also supports 11 |
| SUSE | 12 | |
| NeoKylin | V7 | Domestic OS |

> **Windows and macOS are NOT supported for local DevKit installation.** DevKit must be installed on a remote Linux server.

**Step 2: Ask user where to install DevKit**

- **If local OS IS supported** (`LOCAL_INSTALL_SUPPORTED=true`): Ask "local install" or "remote server install"
  - "local install" → Step 3a
  - "remote server install" → Step 3b
- **If local OS is NOT supported**: Ask "existing remote Linux server" or "provision Kunpeng server on Huawei Cloud"
  - "existing remote Linux server" → Step 3c
  - "provision Kunpeng server" → Step 3d

**Step 3a: Local Install**

1. Install DevKit: `bash <skill_dir>/scripts/install_devkit.sh --yes`
2. Ask user for local source code path
3. Run DevKit scan locally (no SSH needed)
4. Skip Task 1 — proceed directly to Task 3 with local paths

📄 Details → [references/task-local-devkit.md](references/task-local-devkit.md)

**Step 3b: Remote Install — Ask about remote server**

Ask "existing remote Linux server" or "provision Kunpeng server" → Step 3c or 3d.

**Step 3c: User has remote server — Configure SSH**

User sets `KUNPENG_SERVER_HOST/PORT/USER` and `MIGRATE_SSH_PASS` in their terminal (AI never sees values). Verify:

```bash
python <skill_dir>/scripts/ssh_client.py test
```

> **⚠️ No region dependency:** Remote server can be on any cloud or on-premises. No hcloud CLI needed for SSH.

After verification succeeds, proceed to Task 1.

**Step 3d: User has no server — Provision Kunpeng ECS on Huawei Cloud**

> **⛔ CRITICAL: AI MUST use `provision_kunpeng_server.sh` to create ALL cloud resources. NEVER manually call hcloud APIs individually.**

1. Check hcloud CLI installation and authentication
2. Confirm provisioning with user (present spec and estimated cost)
3. Execute: `bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm`
   - Creates VPC → Subnet → Security Group + SSH rule → EIP → ECS
   - Generates random root password, saves to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600)
4. Load env: `source /tmp/kunpeng_server_env.sh`
5. Verify SSH: `python <skill_dir>/scripts/ssh_client.py test`
6. Proceed to Task 1
7. After scan completes (Task 3): Present Resource Cleanup Reminder

📄 Details → [references/task-prepare-server.md](references/task-prepare-server.md)

### Task 1: Connect to Source Code Server via SSH

Verify connection using `python <skill_dir>/scripts/ssh_client.py test`. All subsequent operations use `ssh_client.py` subcommands (see SSH Connection Strategy above).

📄 Details → [references/task-connect-server.md](references/task-connect-server.md)

### Task 2: Install DevKit CLI Tool

Install DevKit CLI on the target machine using `scripts/install_devkit.sh`. The script auto-detects OS/architecture, installs dependencies, downloads the correct package, and verifies installation.

> **⚠️ AI MUST use `scripts/install_devkit.sh`** instead of manually running step-by-step commands.

📄 Details → [references/task-install-devkit.md](references/task-install-devkit.md)

### Task 3: Scan Source Code and Generate Migration Report

**⚠️ CRITICAL RULES:**
1. **MUST ask user for the source code path before scanning.** Do NOT scan without user confirmation.
2. **MUST NOT scan local source code without permission.**
3. **MUST NOT upload local files to remote server without permission.**
4. **CAN list available source code directories on remote server** to help user choose.

**Report save path (local download):**

| Agent OS | Local Report Save Path |
|----------|----------------------|
| Windows | `C:\devkit-report` |
| Linux / macOS | `/home/devkit-report` |

The skill MUST create the directory if it does not exist. Report files (HTML, JSON, CSV) MUST be saved directly under `<save_path>/` (no project_name subdirectory). This path is fixed unless user explicitly requests a different location.

**Downloading the report:**

```bash
# Download with defaults (remote=/tmp/devkit-report, local=C:\devkit-report on Windows):
python <skill_dir>/scripts/ssh_client.py get-report

# Or specify custom paths:
python <skill_dir>/scripts/ssh_client.py get-report /tmp/devkit-report /home/devkit-report
```

> **⚠️ AI MUST use `get-report` (or paramiko SFTP API) to download the report.** Do NOT use `exec` with base64/cat to download files.

📄 Details → [references/task-scan-source-code.md](references/task-scan-source-code.md)

---

## DevKit CLI Command Reference

The primary tool is **Kunpeng DevKit CLI** (`devkit` command).

**Source migration command:**

```bash
devkit porting src-mig -i <source_path> -o <output_path> -s '<language_list>' [options]
```

**Required parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-i` | Source code directory path | `/home/user/project` |
| `-o` | Output directory for report (must exist) | `/tmp/devkit-report` |
| `-s` | Source language(s), comma-separated | `'c, c++, asm'` |

**Optional parameters:**

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `-c` | Build/compiling command | None | `'make all'` |
| `-b` | Build tool | None | `make`, `cmake`, `automake`, `go`, `bazel`, `blade` |
| `-p` | Compiler version | None | `gcc9.3.0` |
| `-f` | Fortran compiler version | None | `gfortran9` |
| `-t` | Target OS | Auto-detect | `openEuler22.03` |
| `-r` | Report format | `all` | `all`, `json`, `html`, `csv` |
| `-l` | Log level | `1` (INFO) | `0`(DEBUG), `1`(INFO), `2`(WARN), `3`(ERROR) |
| `-np` | Concurrent processes | `1` | `4` |
| `--ignore` | Ignore rules config file | Built-in | `/path/to/ignore_rules.json` |
| `--ignore-path` | Source paths to ignore | None | `/path/to/exclude` |
| `--kp-compatibility` | Kunpeng cross-generation compatibility check | Off | (flag) |

**Language values (`-s`):** `c`, `c++`, `asm`, `fortran`, `go`, `java`, `python`, `scala` (lowercase, comma-separated)

**Compiler versions (`-p`):** `gcc4.8.5`, `gcc7.3.0`, `gcc9.3.0`, `gcc10.3.0`, `gcc12.3.0`, `bisheng compiler3.0.0`, `bisheng compiler4.0.0`, `gcc for openeuler3.0.3`, etc.

**Scan examples:**

```bash
# C/C++ project with make build:
devkit porting src-mig -i /home/project -s 'c, c++, asm' -b make -c 'make all' -p gcc9.3.0 -o /tmp/report -r all

# Java/Python project (interpreted, no build command):
devkit porting src-mig -i /home/project -s 'java, python' -o /tmp/report -r all
```

> **⚠️ The `devkit` binary must be run from its installation directory** (e.g., `cd /usr/local/devkit && ./devkit`), or the directory must be in PATH. The output directory (`-o`) must already exist.

📄 Full CLI reference → [references/devkit-cli-reference.md](references/devkit-cli-reference.md)

---

## References

| Document | Description |
|----------|-------------|
| [scripts-guide.md](references/scripts-guide.md) | Built-in scripts: SSH client, provisioning, DevKit installation |
| [prerequisites.md](references/prerequisites.md) | Prerequisites and authentication |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies for ECS provisioning (Step 3d) |
| [cli-installation-guide.md](references/cli-installation-guide.md) | hcloud (KooCLI) installation guide |
| [task-prepare-server.md](references/task-prepare-server.md) | Task 0: Detect OS, prepare environment |
| [task-local-devkit.md](references/task-local-devkit.md) | Task 0a: Local DevKit install |
| [task-connect-server.md](references/task-connect-server.md) | Task 1: SSH connect to server |
| [task-install-devkit.md](references/task-install-devkit.md) | Task 2: Install DevKit CLI |
| [task-scan-source-code.md](references/task-scan-source-code.md) | Task 3: Scan source code |
| [devkit-cli-reference.md](references/devkit-cli-reference.md) | DevKit CLI command reference |
| [devkit-installation-guide.md](references/devkit-installation-guide.md) | DevKit installation guide |
| [migration-report-guide.md](references/migration-report-guide.md) | Migration report interpretation |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and common issues |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [verification-method.md](references/verification-method.md) | Verification methods |

---

## Resource Cleanup Reminder

> **⚠️ After the scan completes and the report is presented, AI MUST remind the user to clean up provisioned resources** (applies to Step 3d provisioning path only). Present as TEXT ONLY — never execute delete commands.

```
### 🧹 Resource Cleanup Reminder

The following resources were created during this assessment and incur ongoing charges:

| Resource Type | Resource ID | Details |
|---------------|-------------|---------|
| ECS Instance  | <id>        | <IP>, <flavor> |
| VPC           | <id>        | <name> |
| Subnet        | <id>        | <name> |
| EIP           | <id>        | <IP> |
| Security Group| <id>        | <name> |

To delete these resources, execute the following commands manually:

  [delete commands here]

⚠️ WARNING: Deletion is IRREVERSIBLE. Verify resource IDs before executing.
⚠️ AI will NOT execute these commands. Please run them manually.
```

**For Step 3c (existing server) and Step 3a (local install):** No cleanup reminder needed — user provided their own server or installed DevKit locally.
