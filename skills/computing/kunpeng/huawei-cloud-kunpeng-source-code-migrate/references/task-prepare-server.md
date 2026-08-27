# Task 0: Detect Local OS and Prepare Environment

This is the FIRST task executed when the skill is activated. It detects the agent's local OS, determines if DevKit can be installed locally, and guides the user through the appropriate installation path.

## Table of Contents

- [Overview](#overview)
- [Step 1: Detect Local OS](#step-1-detect-local-os)
- [Step 2: Classify Local OS](#step-2-classify-local-os)
- [Step 3: Ask User Where to Install DevKit](#step-3-ask-user-where-to-install-devkit)
- [Step 3a: Local Install Path](#step-3a-local-install-path)
- [Step 3b: Remote Install — Ask About Server](#step-3b-remote-install--ask-about-server)
- [Step 3c: User Has Remote Server — Guide SSH Env Vars](#step-3c-user-has-remote-server--guide-ssh-env-vars)
- [Step 3d: User Has No Server — Provision ECS](#step-3d-user-has-no-server--provision-ecs)
- [Step 4: Verify Connectivity (Remote Path Only)](#step-4-verify-connectivity-remote-path-only)
- [Error Handling](#error-handling)

---

## Overview

Before installing DevKit and scanning source code, the skill must:

1. **Detect the agent's local OS** to determine if DevKit can be installed locally
2. **If local OS is supported**: Offer the user a choice between local install and remote install
3. **If local OS is not supported**: Guide the user to use a remote server (existing or new)

This task is the entry point for the entire workflow and MUST be executed before any other task.

**Workflow decision tree:**

```
Detect Local OS
├── Supported OS (openEuler, CentOS, Ubuntu, Kylin, UOS, etc.)
│   ├── User chooses "Local Install" → Install DevKit locally → Scan local source
│   └── User chooses "Remote Install"
│       ├── Has remote server → Guide SSH env vars → Connect → Install DevKit remotely
│       └── No remote server → Provision ECS → Connect → Install DevKit remotely
└── Unsupported OS (Windows, macOS, etc.)
    ├── Has remote server → Guide SSH env vars → Connect → Install DevKit remotely
    └── No remote server → Provision ECS → Connect → Install DevKit remotely
```

---

## Step 1: Detect Local OS

Detect the agent machine's operating system and architecture using the built-in `detect_os.py` script.

**One-command detection (cross-platform):**

```bash
python <skill_dir>/scripts/detect_os.py
```

**Output format (key=value per line):**

```
os_type=Windows
os_name=Windows Server 2019 Standard
os_version=10.0.17763
arch=x86_64
local_install_supported=False
```

| Output Field | Description |
|-------------|-------------|
| `os_type` | Classified OS type: `Windows`, `macOS`, `openEuler`, `CentOS`, `Ubuntu`, `Kylin`, `UOS`, `EulerOS`, `Debian`, `SUSE`, `NeoKylin`, or `unsupported` |
| `os_name` | Full OS product name (e.g., "Windows Server 2019 Standard", "openEuler 22.03 LTS") |
| `os_version` | OS version string |
| `arch` | Normalized architecture: `x86_64` or `aarch64` |
| `local_install_supported` | `True` if DevKit can be installed locally, `False` otherwise |

> **⚠️ AI MUST use `detect_os.py` instead of manually running `uname -m`, `cat /etc/os-release`, PowerShell `[System.Environment]::OSVersion`, `$env:OS`, etc.** The script uses Python `platform` module internally, works on all platforms (Windows/Linux/macOS) without external dependencies, and produces consistent, parseable output.

> **⚠️ Important:** The OS detection MUST be performed on the agent machine (where the skill is running), NOT on any remote server. Use local commands only.

---

## Step 2: Classify Local OS

The `detect_os.py` script already classifies the OS and outputs `local_install_supported=True/False`. Parse the output to determine the workflow path:

```bash
# Run detect_os.py and parse output
DETECT_OUTPUT=$(python <skill_dir>/scripts/detect_os.py)
OS_TYPE=$(echo "$DETECT_OUTPUT" | grep '^os_type=' | cut -d= -f2)
LOCAL_INSTALL_SUPPORTED=$(echo "$DETECT_OUTPUT" | grep '^local_install_supported=' | cut -d= -f2)
```

**DevKit-supported OS list for local installation:**

| OS | Minimum Version | Architecture | Package Suffix |
|----|----------------|-------------|----------------|
| openEuler | 20.03 LTS | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| CentOS | 7.6 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| Ubuntu | 18.04 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| Kylin | V10 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| UOS | 20 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| EulerOS | 2.8 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| Debian | 10 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| SUSE | 12 | x86_64, aarch64 | `x86-64` or `Kunpeng` |
| NeoKylin | V7 | x86_64, aarch64 | `x86-64` or `Kunpeng` |

**NOT supported for local DevKit installation:**
- Windows (any version)
- macOS (any version)
- Other Linux distributions not in the list above

---

## Step 3: Ask User Where to Install DevKit

### If Local OS IS Supported (`LOCAL_INSTALL_SUPPORTED=true`)

Use the `ask_followup_question` tool:

**Question:** "检测到本机操作系统为 {OS_TYPE} ({ARCH})，支持本地安装DevKit。您希望在哪里安装DevKit进行源码迁移评估？"

**Options:**
1. "本地安装" → Go to Step 3a
2. "远程服务器安装" → Go to Step 3b

### If Local OS is NOT Supported (`LOCAL_INSTALL_SUPPORTED=false`)

Use the `ask_followup_question` tool:

**Question:** "本机操作系统不支持DevKit本地安装，需要在远程Linux服务器上安装。您是否已有远程Linux服务器？"

**Options:**
1. "有，我已有远程Linux服务器" → Go to Step 3c
2. "没有，请帮我在华为云上购买一台鲲鹏服务器" → Go to Step 3d

> **⚠️ This step MUST NOT be skipped.** The user must explicitly choose the installation path.

---

## Step 3a: Local Install Path

When the user chooses to install DevKit locally:

### Step 3a.1: Check if DevKit is already installed

```bash
cd /usr/local/devkit && ./devkit --version 2>/dev/null || echo "DevKit not installed"
```

If already installed, skip to Step 3a.3.

### Step 3a.2: Install DevKit locally

Use the built-in installation script:

```bash
bash <skill_dir>/scripts/install_devkit.sh --yes
```

The script automatically: detects OS/architecture, installs dependencies, downloads the correct DevKit package, extracts and installs (including the critical `.devkit` hidden file), and verifies the installation.

For details and options, see [task-local-devkit.md](task-local-devkit.md).

### Step 3a.3: Ask user for local source code path

Use the `ask_followup_question` tool:

**Question:** "请提供本地源码的路径（例如 /home/user/project）："

### Step 3a.4: Verify source code path

```bash
test -d "<source_path>" && echo "Path exists" || echo "Path not found"
find "<source_path>" -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.java' -o -name '*.py' -o -name '*.go' \) | wc -l
```

### Step 3a.5: Run DevKit scan locally

```bash
mkdir -p /tmp/devkit-report
cd /usr/local/devkit && ./devkit porting src-mig -i "<source_path>" -o /tmp/devkit-report -s '<languages>' -r all
```

> **Note:** When using local install path, Task 1 (ConnectServer) and Task 2 (InstallDevKit on remote) are SKIPPED. Proceed directly to scanning.

📄 Detailed local install guide → [task-local-devkit.md](task-local-devkit.md)

---

## Step 3b: Remote Install — Ask About Server

When the user chooses remote install (on a supported local OS), ask about the remote server:

Use the `ask_followup_question` tool:

**Question:** "您是否已有可用的远程Linux服务器？"

**Options:**
1. "有，我已有远程Linux服务器" → Go to Step 3c
2. "没有，请帮我在华为云上购买一台鲲鹏服务器" → Go to Step 3d

---

## Step 3c: User Has Remote Server — Configure SSH via paramiko

### Ask for Server Connection Info

Use the `ask_followup_question` tool:

**Question:** "请设置远程服务器的连接环境变量（在您自己的终端中设置，AI 不会看到这些值）：KUNPENG_SERVER_HOST（服务器IP）、KUNPENG_SERVER_PORT（端口，默认22）、KUNPENG_SERVER_USER（用户名，默认root）、MIGRATE_SSH_PASS（密码）。设置完成后，我将通过 built-in ssh_client.py test 验证 paramiko 密码连接。"

**Options:**
1. "我已设置好环境变量，请验证连接" → Run `ssh_client.py test` to verify SSH via paramiko
2. "我需要帮助设置环境变量" → Show cross-platform env var setup instructions

### Configure SSH via paramiko

After the user sets the environment variables, run the built-in `ssh_client.py test` subcommand. The script reads the server password from the `MIGRATE_SSH_PASS` environment variable (never passed via argv, so `ps -ef` cannot see it; wiped from `os.environ` immediately after each connection):

```
→ Run: python <skill_dir>/scripts/ssh_client.py test
→ The script handles:
  1. Resolve env vars from current process env OR Windows user-level registry (winreg)
  2. Pre-flight checks (validates MIGRATE_SSH_PASS and KUNPENG_SERVER_HOST are set, paramiko available)
  3. paramiko password connection test (reads MIGRATE_SSH_PASS from env var)
  4. Runs 'echo SSH_OK && uname -a' to verify command execution
→ After setup, use ssh_client.py subcommands for all remote operations:
    python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]
    python <skill_dir>/scripts/ssh_client.py put <local> <remote>
    python <skill_dir>/scripts/ssh_client.py put-dir <local_dir> <remote_dir>
```

### Set Environment Variables

If the user needs help, guide them to set the connection info in their own terminal:

```bash
# Linux / macOS:
export KUNPENG_SERVER_HOST="<remote-server-ip>"
export KUNPENG_SERVER_PORT="22"
export KUNPENG_SERVER_USER="root"
export MIGRATE_SSH_PASS="<password>"

# Windows PowerShell:
$env:KUNPENG_SERVER_HOST="<remote-server-ip>"
$env:KUNPENG_SERVER_PORT="22"
$env:KUNPENG_SERVER_USER="root"
$env:MIGRATE_SSH_PASS="<password>"
```

After setup, proceed to Step 4.

---

## Step 3d: User Has No Server — Provision ECS

> **⛔ CRITICAL RULE: AI MUST use `provision_kunpeng_server.sh` script to create ALL cloud resources.**
>
> **NEVER manually call hcloud APIs to create VPC, Subnet, Security Group, EIP, or ECS individually.** The script handles everything with correct parameters, proper error handling, dependency waiting, and SSH readiness checks. Manual step-by-step creation has repeatedly caused the following issues:
>
> | Problem | Root Cause | How Script Avoids It |
> |---------|-----------|---------------------|
> | Wrong API parameter names | hcloud API uses dot-notation (e.g., `--subnet.vpc_id` not `--vpc_id`) | Script uses correct parameter names for each API |
> | Missing required parameters | Subnet needs `--subnet.gateway_ip`, `--subnet.dnsList.1/2`; ECS needs `--server.availability_zone` | Script includes all required parameters |
> | Random password SSH failure | AI-generated random passwords may not meet cloud-init requirements or get incorrectly injected | Script uses Python `secrets` module to generate a 20-character alphanumeric password that meets Huawei Cloud complexity rules |
> | VPC/Subnet not ready | Creating ECS immediately after VPC/Subnet creation fails | Script waits for VPC/Subnet ACTIVE status before proceeding |
> | SSH not available | ECS needs time for cloud-init and SSH daemon startup | Script polls SSH availability with paramiko before saving env vars |
> | Environment variables not set | AI forgets to set KUNPENG_SERVER_* after manual creation | Script saves all connection info to `/tmp/kunpeng_server_env.sh` |
>
> **The ONLY correct way to provision a server is:**
> ```bash
> bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm
> ```

### Step 3d.1: Check hcloud CLI Installation

```bash
hcloud version 2>/dev/null || echo "hcloud not installed"
```

If not installed, install it following the [CLI installation guide](cli-installation-guide.md).

### Step 3d.2: Check hcloud Authentication

```bash
hcloud ECS ListServersDetails --cli-region=cn-southwest-2 --limit=1 2>&1 | head -5
```

If authentication fails (output contains "authentication", "unauthorized", "credential", or "配置文件中不存在"), guide the user to run:
```bash
hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<AK> --cli-secret-key=<SK>
```

> **⚠️ Security:** Do NOT ask the user to provide AK/SK in the conversation. Guide them to use the `hcloud configure set` command directly in their terminal.

### Step 3d.3: Confirm Provisioning with User

Present the server specification and ask for explicit confirmation:

```
将在华为云贵阳一区域 (cn-southwest-2) 创建以下资源：

  服务器规格:  鲲鹏 KC1 (ARM64, 2C4G)
  操作系统:    Huawei Cloud EulerOS 2.0 Standard 64 bit for ARM
  系统盘:      40GB 高IO (GPSSD)
  网络:        新建VPC + 子网 + 弹性公网IP (300 Mbit/s BGP)
  安全组:      允许SSH (TCP 22) 入站，全部出站

⚠️ 注意：创建的服务器将产生费用，使用完毕后请及时删除。
⚠️ **删除资源是高危不可逆操作，AI 不会自动执行删除命令。** 用户需手动执行删除命令。

是否确认购买？(yes/no)
```

**Do NOT proceed without explicit user confirmation.**

### Step 3d.3.5: 🚫 Resource Deletion Policy (CRITICAL)

> **⛔ HIGH-RISK: Resource deletion is IRREVERSIBLE. AI MUST NEVER auto-delete cloud resources.**

**After migration assessment is complete, AI MUST:**
1. **NOT** proactively execute any `hcloud ... Delete*` commands
2. **NOT** run cleanup scripts that delete resources without user reviewing the resource list first
3. Provide cleanup instructions as **TEXT ONLY** (in a code block for user to copy and execute manually)
4. List all resource IDs clearly so the user can verify before deleting
5. Warn the user that deletion is irreversible

**AI is PROHIBITED from executing these commands directly:**
```bash
hcloud ECS DeleteServers ...           # ❌ AI MUST NOT execute
hcloud VPC DeleteVpc ...               # ❌ AI MUST NOT execute
hcloud VPC DeleteSubnet ...            # ❌ AI MUST NOT execute
hcloud VPC DeleteSecurityGroup ...     # ❌ AI MUST NOT execute
hcloud VPC DeletePublicip ...          # ❌ AI MUST NOT execute
```

**Correct behavior:** AI provides the commands as text, user executes manually.

### Step 3d.4: Execute Provisioning Script

> **⛔ This is the ONLY step that creates cloud resources. Do NOT manually call hcloud APIs.**

```bash
bash <skill_dir>/scripts/provision_kunpeng_server.sh --confirm
```

**What the script does internally (for reference only — AI MUST NOT replicate these steps):**

| Step | Script Function | hcloud Command | Key Parameters |
|------|----------------|----------------|----------------|
| 1 | `preflight_check()` | `hcloud ECS ListServersDetails` | Verifies hcloud installed and authenticated |
| 2 | `detect_agent_ip()` | `curl ifconfig.me` | Auto-detects agent IP for SSH source restriction |
| 3 | `create_vpc()` | `hcloud VPC CreateVpc` | `--vpc.name=kunpeng-devkit-vpc-XXXX --vpc.cidr=192.168.0.0/16` |
| 4 | (wait) | `hcloud VPC ShowVpc` | Polls until VPC status = ACTIVE |
| 5 | `create_subnet()` | `hcloud VPC CreateSubnet` | `--subnet.vpc_id=... --subnet.name=... --subnet.cidr=192.168.1.0/24 --subnet.gateway_ip=192.168.1.1 --subnet.dnsList.1=100.125.1.250 --subnet.dnsList.2=100.125.21.250` |
| 6 | (wait) | `hcloud VPC ShowSubnet` | Polls until Subnet status = ACTIVE |
| 7 | `create_security_group()` | `hcloud VPC CreateSecurityGroup` | `--security_group.name=kunpeng-devkit-sg-XXXX` |
| 8 | (add rule) | `hcloud VPC CreateSecurityGroupRule` | `--security_group_rule.security_group_id=... --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=22 --security_group_rule.remote_ip_prefix=<AGENT_IP>/32 --security_group_rule.ethertype=IPv4 --security_group_rule.action=allow --security_group_rule.priority=1` |
| 9 | `get_image_id()` | `hcloud IMS ListImages` | `--__imagetype=gold --__os_type=Linux --limit=50`, then filters for "Standard 64 bit for ARM" excluding "BareMetal" |
| 10 | `create_eip()` | `hcloud EIP CreatePublicip` | `--publicip.type=5_bgp --bandwidth.name=kunpeng-devkit-bw --bandwidth.size=300 --bandwidth.charge_mode=traffic --bandwidth.share_type=PER` |
| 11 | `create_ecs()` | `hcloud ECS CreateServers --cli-jsonInput=<temp-file>` | Builds request body in a temporary JSON file. A random password is generated for cloud-init and saved to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600). Non-sensitive fields: `server.name=kunpeng-devkit-server`, `server.imageRef=...`, `server.flavorRef=kc1.2xlarge.2`, `server.vpcid=...`, `server.nics[0].subnet_id=...`, `server.publicip.id=...`, `server.root_volume.volumetype=GPSSD`, `server.root_volume.size=40`, `server.security_groups[0].id=...`, `server.availability_zone=cn-southwest-2a`. The temp file is securely deleted (`shred -u`) after use. |
| 12 | `wait_for_ecs()` | `hcloud ECS ShowJob` | Polls until job status = SUCCESS |
| 13 | `save_connection_info()` | Write to file | Saves `KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT`, `KUNPENG_SERVER_USER`, `KUNPENG_SERVER_ID`, `KUNPENG_SERVER_REGION`, AND `MIGRATE_SSH_PASS` to `/tmp/kunpeng_server_env.sh` (chmod 600) |

> **⚠️ Password note:** The script generates a random password for cloud-init and saves it to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600, only readable by the current user). The password is NEVER printed to the user. SSH is configured by running the built-in `ssh_client.py test` subcommand in Step 3d.6, which verifies the paramiko password connection (password read from `MIGRATE_SSH_PASS` environment variable, never passed via argv, wiped from `os.environ` immediately after each connection).

### Step 3d.5: Load Environment Variables

```bash
source /tmp/kunpeng_server_env.sh
```

This sets `KUNPENG_SERVER_HOST`, `KUNPENG_SERVER_PORT`, `KUNPENG_SERVER_USER`, `KUNPENG_SERVER_ID`, `KUNPENG_SERVER_REGION`, AND `MIGRATE_SSH_PASS` automatically.

### Step 3d.6: Verify SSH via paramiko

Run the built-in `ssh_client.py test` subcommand to verify SSH connection to the newly provisioned ECS. The script reads the server password from the `MIGRATE_SSH_PASS` environment variable (never passed via argv, so `ps -ef` cannot see it; wiped from `os.environ` immediately after each connection):

```
→ Run: python <skill_dir>/scripts/ssh_client.py test
→ The script handles:
  1. Resolve env vars from current process env OR Windows user-level registry (winreg)
  2. Pre-flight checks (validates MIGRATE_SSH_PASS is set, paramiko available)
  3. paramiko password connection test (reads MIGRATE_SSH_PASS from env var)
  4. Runs 'echo SSH_OK && uname -a' to verify command execution
→ After setup, use ssh_client.py subcommands for all remote operations:
    python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]
    python <skill_dir>/scripts/ssh_client.py put <local> <remote>
    python <skill_dir>/scripts/ssh_client.py put-dir <local_dir> <remote_dir>
```

### Step 3d.7: Verify SSH Connectivity

```bash
python <skill_dir>/scripts/ssh_client.py exec "echo 'SSH connection successful'" 30
```

If successful, proceed to Step 4.

---

## Step 4: Verify Connectivity (Remote Path Only)

For remote install paths (Step 3c or 3d), verify the server is accessible via paramiko-based SSH:

```bash
# Test SSH connection (paramiko reads MIGRATE_SSH_PASS from env)
python <skill_dir>/scripts/ssh_client.py test

# Get server info
python <skill_dir>/scripts/ssh_client.py exec "uname -a && cat /etc/os-release" 30
```

After successful verification, proceed to Task 1 (ConnectServer) for detailed server information gathering, then Task 2 (InstallDevKit) and Task 3 (ScanSourceCode).

> **Note:** For local install path (Step 3a), this step is not needed — proceed directly to scanning.

---

## Error Handling

### Local OS Detection Failed

**Problem:** Cannot determine the local OS type.

**Solution:**
1. Try alternative detection methods:
   ```bash
   # Alternative 1: lsb_release
   lsb_release -a 2>/dev/null

   # Alternative 2: redhat-release
   cat /etc/redhat-release 2>/dev/null

   # Alternative 3: issue
   cat /etc/issue 2>/dev/null
   ```
2. If all methods fail, treat as unsupported OS and guide user to remote install

### DevKit Installation Failed on Local Machine

**Problem:** DevKit fails to install locally.

**Solution:**
1. Check the script exit code for specific error:
   - Exit 1: Unsupported OS → use remote install
   - Exit 2: Dependency failed → install manually, then re-run with `--skip-deps`
   - Exit 3: Download failed → try `--version=25.3.0` or use `--offline` with pre-downloaded package
   - Exit 4: Install failed → try `--no-sudo` for user-directory install
   - Exit 5: Verify failed → check `.devkit` hidden file and system libraries
2. Try installing as non-root user: `bash <skill_dir>/scripts/install_devkit.sh --yes --no-sudo`
3. Fall back to remote install if local install continues to fail

### hcloud Not Installed

**Problem:** `hcloud: command not found`

**Solution:** Install hcloud following [cli-installation-guide.md](cli-installation-guide.md).

### hcloud Authentication Failed

**Problem:** `authentication failed` or `unauthorized`

**Solution:**
1. Run `hcloud configure` to set credentials interactively
2. Or set environment variables `HUAWEICLOUD_SDK_AK` and `HUAWEICLOUD_SDK_SK`

### Insufficient ECS Quota

**Problem:** `Quota exceeded` during ECS creation

**Solution:**
1. Check current ECS instances: `hcloud ECS ListServersDetails --region=cn-southwest-2`
2. Delete unused instances or request quota increase

### Insufficient Account Balance

**Problem:** `Account balance insufficient`

**Solution:** Recharge account balance through Huawei Cloud console.

### ECS Creation Failed

**Problem:** ECS creation job status is `FAIL`

**Solution:**
1. Check the fail reason: `hcloud ECS ShowJob --region=cn-southwest-2 --job_id=<id>`
2. Try a different availability zone or flavor

### SSH Not Available After Provisioning

**Problem:** Cannot SSH to the newly created server

**Solution:**
1. Wait a few more minutes — the server may still be initializing
2. Check security group rules — ensure TCP 22 is allowed
3. Check EIP assignment — verify the EIP is bound to the ECS

### Cleanup After Failed Provisioning

> **🚫 HIGH-RISK: AI MUST NOT auto-execute these delete commands.** 
> These commands are provided for the USER to execute manually after reviewing the resource list.
> AI should only display these commands as text, never execute them directly.

**Step 1: List resources (AI can execute list commands — they are read-only):**
```bash
# List resources (read-only, safe for AI to execute)
hcloud ECS ListServersDetails --region=cn-southwest-2
hcloud VPC ListVpcs --region=cn-southwest-2
hcloud VPC ListPublicips --region=cn-southwest-2
```

**Step 2: Delete resources (USER MUST EXECUTE MANUALLY — AI MUST NOT execute):**
```bash
# ⚠️ HIGH-RISK IRREVERSIBLE OPERATIONS — USER MUST EXECUTE MANUALLY
# AI MUST NOT execute these commands. Provide as text only.
# Delete resources in reverse order
hcloud ECS DeleteServers --region=cn-southwest-2 --servers.1.id=<server_id>
hcloud VPC DeletePublicip --region=cn-southwest-2 --publicip_id=<eip_id>
hcloud VPC DeleteSubnet --region=cn-southwest-2 --vpc_id=<vpc_id> --subnet_id=<subnet_id>
hcloud VPC DeleteSecurityGroup --region=cn-southwest-2 --security_group_id=<sg_id>
hcloud VPC DeleteVpc --region=cn-southwest-2 --vpc_id=<vpc_id>
```

---

## Resource Cleanup Reminder (After Scan Completes)

> **⚠️ CRITICAL: The Resource Cleanup Reminder is presented AFTER the source code scan completes (Task 3), NOT immediately after server provisioning.**

The reminder is defined in [task-scan-source-code.md Step 6](task-scan-source-code.md#step-6-post-scan-reminders-after-assessment-completes). The AI presents it as the final step of the workflow, after the migration report is shown to the user.

**Key points:**
- **Provisioning path (Step 3d)**: Present the Resource Cleanup Reminder after the scan completes. No password rotation reminder is needed — the password in `MIGRATE_SSH_PASS` is wiped from `os.environ` after each paramiko connection is established. No SSH keys are injected, no ControlMaster sockets are left open.
- **Existing server path (Step 3c)**: No reminders needed — the user provided their own server. No SSH keys are injected and no ControlMaster sockets are left open (unified paramiko approach).
- **Local install path (Step 3a)**: No reminders needed — DevKit was installed locally.

The `provision_kunpeng_server.sh` script does NOT print any password rotation reminder — the password is saved only to `/tmp/kunpeng_server_env.sh` (chmod 600) and never output. The `ssh_client.py` script reads `MIGRATE_SSH_PASS` from `os.environ` (or Windows user-level registry as fallback) for each connection and wipes it immediately after connect. No SSH keys are injected, no ControlMaster sockets are left open.
