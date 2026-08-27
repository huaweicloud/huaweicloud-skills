# Prerequisites and Authentication

This document describes the prerequisites and authentication requirements for using this skill.

## Table of Contents

- [SSH Connection (Unified paramiko + Password Env Var)](#ssh-connection-unified-paramiko--password-env-var)
- [How to Set MIGRATE_SSH_PASS (Cross-Platform Guide)](#how-to-set-migrate_ssh_pass-cross-platform-guide)
- [Huawei Cloud Authentication (for provisioning)](#huawei-cloud-authentication-for-provisioning)
- [Authentication Security Rules](#authentication-security-rules)
- [Handling User-Provided Credentials](#handling-user-provided-credentials)
- [Resource Cleanup Reminder](#resource-cleanup-reminder)

---

## SSH Connection (Unified paramiko + Password Env Var)

This skill uses a **unified paramiko-based SSH** approach for ALL remote operations. The SSH password is read from the `MIGRATE_SSH_PASS` environment variable — never passed as a CLI argument (invisible to `ps -ef`), never printed, never written to disk by the scripts.

**Unified strategy (no ControlMaster, no key injection):**
- All SSH operations use `python + paramiko + password`
- Password is read from `MIGRATE_SSH_PASS` environment variable
- Works identically on Windows, Linux, and macOS
- No `ssh-keygen`, no `authorized_keys` modification, no ControlMaster
- No `sshpass`, no COC, no UniAgent dependency
- Password is wiped from `os.environ` immediately after each connection is established

**Connection setup workflow:**

| Workflow Path | SSH Setup |
|---------------|-----------|
| **User has an existing remote server** (Step 3c) | The user sets `KUNPENG_SERVER_HOST/PORT/USER` and `MIGRATE_SSH_PASS` in their own terminal (AI never sees the values). The built-in `ssh_client.py test` subcommand verifies the paramiko password connection. All subsequent operations use `ssh_client.py` subcommands (`exec`, `put`, `put-dir`). |
| **Provision a new Kunpeng ECS** (Step 3d) | The `provision_kunpeng_server.sh` script creates the ECS, generates a random root password, and saves it to `/tmp/kunpeng_server_env.sh` as `MIGRATE_SSH_PASS` (chmod 600). Then `ssh_client.py test` verifies the paramiko password connection. |

**What the built-in `ssh_client.py test` subcommand does:**

1. **Pre-flight Checks** — Validates `MIGRATE_SSH_PASS` is set and paramiko is available
2. **Connection Test** — Tests paramiko password connection to the remote server (reads password from `MIGRATE_SSH_PASS` env var, wipes it from `os.environ` immediately after connect)
3. **Save Connection Info** — The `save-env` subcommand saves `KUNPENG_SERVER_HOST/PORT/USER` to `/tmp/kunpeng_server_env.sh` (no password saved)

**After setup, all SSH operations use `ssh_client.py` subcommands (paramiko mode):**

```bash
# Execute a remote command
python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]

# Upload a file via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put "<local_path>" "<remote_path>"

# Upload a directory recursively via SFTP
MSYS_NO_PATHCONV=1 python <skill_dir>/scripts/ssh_client.py put-dir "<local_dir>" "<remote_dir>"
```

Each call to `ssh_client.py` opens a new paramiko connection, reads the password from `MIGRATE_SSH_PASS` env var, wipes it from `os.environ` after connect, executes the command, and closes the connection.

**Environment variables:**

| Environment Variable | Description | Example |
|---------------------|-------------|---------|
| `MIGRATE_SSH_PASS` | SSH password (read by paramiko, never in argv) | (set in user's terminal) |
| `KUNPENG_SERVER_HOST` | Remote server IP address | `<your-server-ip>` |
| `KUNPENG_SERVER_PORT` | SSH port | `22` |
| `KUNPENG_SERVER_USER` | SSH username | `root` |
| `KUNPENG_SERVER_ID` | ECS instance ID (informational, from provisioning) | `abc123-def456-...` |
| `KUNPENG_SERVER_REGION` | Huawei Cloud region (informational, from provisioning) | `cn-southwest-2` |

> **⚠️ Security:** The user MUST set `MIGRATE_SSH_PASS` in their own terminal. AI must NEVER ask for the password in conversation, NEVER echo it, and NEVER pass it as a command-line argument. The password is read by Python/paramiko from `os.environ` and wiped immediately after each connection is established.

---

## How to Set MIGRATE_SSH_PASS (Cross-Platform Guide)

The `MIGRATE_SSH_PASS` environment variable must be set by the user in their own terminal before running `ssh_client.py test` or any operation that uses `ssh_client.py` subcommands. AI must NEVER ask for the password in conversation.

### Linux / macOS

**Temporary (current shell session only):**
```bash
export MIGRATE_SSH_PASS='your-password'
```

**Persistent across shell sessions via `/tmp` env file (Recommended for this skill):**

This skill's `ssh_client.py` automatically reads connection info from `/tmp/kunpeng_server_env.sh` (see [Credential Resolution Priority](#credential-resolution-priority) below). By writing all env vars to this file, you achieve persistence across shell sessions AND make them directly usable by `ssh_client.py` without needing to `source` the file in every new terminal.

```bash
# 1. Write all connection info to /tmp/kunpeng_server_env.sh (chmod 600 for security)
cat > /tmp/kunpeng_server_env.sh << 'EOF'
export KUNPENG_SERVER_HOST="<your-server-ip>"
export KUNPENG_SERVER_PORT="22"
export KUNPENG_SERVER_USER="root"
export MIGRATE_SSH_PASS="<your-password>"
EOF
chmod 600 /tmp/kunpeng_server_env.sh

# 2. Load into the current shell session
source /tmp/kunpeng_server_env.sh

# 3. Verify
[ -n "$MIGRATE_SSH_PASS" ] && echo "MIGRATE_SSH_PASS is set" || echo "NOT set"
```

After this setup:
- **New shell sessions**: `ssh_client.py` reads the file directly — no `source` needed. The AI agent's `ssh_client.py` will find the credentials automatically.
- **Current shell**: `source /tmp/kunpeng_server_env.sh` loads the vars for direct use.
- **Security**: `chmod 600` ensures only the current user can read the file.

> **⚠️ Note:** The `/tmp` directory is typically cleared on system reboot. If you need persistence across reboots, use `~/.bashrc` instead (see below). The `/tmp/kunpeng_server_env.sh` file is primarily designed for the "new server" provisioning workflow and for persisting credentials during a single work session.

**Persistent across reboots (via shell profile):**
```bash
# Add to ~/.bashrc (Bash) or ~/.zshrc (Zsh)
echo "export MIGRATE_SSH_PASS='<your-password>'" >> ~/.bashrc
echo "export KUNPENG_SERVER_HOST='<your-server-ip>'" >> ~/.bashrc
echo "export KUNPENG_SERVER_PORT='22'" >> ~/.bashrc
echo "export KUNPENG_SERVER_USER='root'" >> ~/.bashrc
source ~/.bashrc
```

#### Credential Resolution Priority

`ssh_client.py` resolves credentials in the following order (first match wins):

| Priority | Source | Use Case |
|----------|--------|----------|
| 1 | Current process env vars (`export` in current shell) | Existing server workflow — user sets vars manually in the active session |
| 2 | `/tmp/kunpeng_server_env.sh` (Linux/macOS) or `%TEMP%/kunpeng_server_env.sh` (Windows) | New server workflow — `provision_kunpeng_server.sh` writes here; also used when user manually writes to this file for persistence |
| 3 | Windows user-level registry (`winreg`) | Fallback for GUI-set vars on Windows |
| 4 | Default value | If none of the above match |

This means:
- **New server workflow**: After `provision_kunpeng_server.sh` runs, `ssh_client.py` finds the password in `/tmp/kunpeng_server_env.sh` automatically — no manual env var setup needed.
- **Existing server workflow**: You can either `export` vars in your current shell (priority 1) OR write them to `/tmp/kunpeng_server_env.sh` (priority 2) for persistence across sessions.

### Windows PowerShell

**Temporary (current PowerShell session only):**
```powershell
$env:MIGRATE_SSH_PASS='your-password'
```

**Persistent (across sessions, requires IDE/terminal restart):**
```powershell
[Environment]::SetEnvironmentVariable('MIGRATE_SSH_PASS','your-password','User')
# Then restart VS Code or PowerShell
```

### Windows CMD

**Temporary (current CMD session only):**
```cmd
set MIGRATE_SSH_PASS=your-password
```

**Persistent (across sessions, via setx — requires IDE/terminal restart):**
```cmd
setx MIGRATE_SSH_PASS "your-password"
:: Then restart VS Code or CMD
```

### Windows GUI (Persistent, Recommended for Non-Technical Users)

1. Open **Settings** > **System** > **About**
2. Click **Advanced system settings**
3. Click **Environment Variables...**
4. Under **User variables for <username>**, click **New...**
5. Set:
   - **Variable name:** `MIGRATE_SSH_PASS`
   - **Variable value:** `<your-password>`
6. Click **OK** on all dialogs
7. **Restart VS Code or your terminal** for the new variable to take effect

> **⚠️ Important for Windows users:** Environment variables set via GUI, `setx`, or `SetEnvironmentVariable` are NOT immediately available in the current process. You MUST restart your IDE (VS Code) or terminal for the new variable to be loaded into the process environment. AI processes inherit environment variables from their parent process at startup. The `ssh_client.py` script also reads from the Windows user-level registry (winreg) as a fallback, so it can pick up GUI-set vars even without restart in some cases.

### Verifying the Environment Variable is Set

**Linux / macOS:**
```bash
[ -n "$MIGRATE_SSH_PASS" ] && echo "MIGRATE_SSH_PASS is set" || echo "MIGRATE_SSH_PASS is NOT set"
```

**Windows PowerShell:**
```powershell
if ($env:MIGRATE_SSH_PASS) { "MIGRATE_SSH_PASS is set" } else { "MIGRATE_SSH_PASS is NOT set" }
```

**Windows CMD:**
```cmd
if defined MIGRATE_SSH_PASS (echo MIGRATE_SSH_PASS is set) else (echo MIGRATE_SSH_PASS is NOT set)
```

> **⚠️ Security:** NEVER print the actual value of `MIGRATE_SSH_PASS`. Only check whether it is set.

---

## Huawei Cloud Authentication (for provisioning)

For the provisioning path (Step 3d), hcloud CLI must be authenticated with AK/SK:

```bash
hcloud configure set --cli-region=cn-southwest-2 --cli-access-key=<your-ak> --cli-secret-key=<your-sk>
```

> **⚠️ Security:** Do NOT ask the user to provide AK/SK in the conversation. Guide them to use the `hcloud configure set` command directly in their terminal.

The AK/SK is used by the `provision_kunpeng_server.sh` script for ECS provisioning (VPC, Subnet, Security Group, EIP, ECS creation). It is NOT used for SSH setup — SSH is configured via paramiko + `MIGRATE_SSH_PASS` (using `ssh_client.py`).

### IAM Permissions

The AK/SK must belong to a user or agency with the minimum IAM permissions for provisioning. See [iam-policies.md](iam-policies.md) for the complete policy JSON, creation instructions, and verification steps.

**Minimum required actions (provisioning):**

| Service | Actions |
|---------|---------|
| ECS | `ecs:servers:create`, `ecs:servers:list`, `ecs:jobs:get` |
| VPC | `vpc:vpcs:create`, `vpc:vpcs:get`, `vpc:subnets:create`, `vpc:subnets:get`, `vpc:securityGroups:create`, `vpc:securityGroupRules:create` |
| IMS | `ims:images:list` |
| EIP | `eip:publicips:create` |
| IAM | `iam:projects:list` |

**Additional actions for cleanup (manual, after assessment):**

| Service | Actions |
|---------|---------|
| ECS | `ecs:servers:delete` |
| VPC | `vpc:vpcs:delete`, `vpc:subnets:delete`, `vpc:securityGroups:delete` |
| EIP | `eip:publicips:delete` |

---

## Authentication Security Rules

> **Security rules (must be followed):**
> - **Prohibited** from asking the user to input SSH host, port, username, or password directly in the conversation
> - **Prohibited** from echoing, printing, or logging any credential values
> - **Prohibited** from passing SSH password as a command-line argument (must use `MIGRATE_SSH_PASS` env var)
> - **Prohibited** from using `sshpass` or COC-based SSH authentication
> - **Prohibited** from using SSH ControlMaster or key injection (unified paramiko approach only)
> - **Only allowed** to use paramiko-based SSH via the built-in `ssh_client.py` script (password from `MIGRATE_SSH_PASS` env var; subcommands: `test`, `exec`, `put`, `put-dir`, `save-env`)
> - **Only allowed** to read ECS connection info (host, port, user, instance ID, region) from environment variables or the provisioning script output

---

## Handling User-Provided Credentials

If a user attempts to provide SSH credentials directly (e.g., "my server IP is <your-server-ip>, password is xxx"):
1. **Stop immediately** - Do not execute any commands
2. **Politely refuse** and return the following message:
   ```
   For security, please do not provide SSH credentials directly in the conversation.

   This skill uses unified paramiko-based SSH (no ControlMaster, no key injection).
   The password is read from the MIGRATE_SSH_PASS environment variable.

   Please set KUNPENG_SERVER_HOST/PORT/USER and MIGRATE_SSH_PASS
   in your terminal:

     Linux / macOS (option A — temporary, current session only):
       export KUNPENG_SERVER_HOST='<your-server-ip>'
       export KUNPENG_SERVER_PORT='22'
       export KUNPENG_SERVER_USER='root'
       export MIGRATE_SSH_PASS='<your-password>'

     Linux / macOS (option B — persistent via /tmp env file, recommended):
       cat > /tmp/kunpeng_server_env.sh << 'EOF'
       export KUNPENG_SERVER_HOST="<your-server-ip>"
       export KUNPENG_SERVER_PORT="22"
       export KUNPENG_SERVER_USER="root"
       export MIGRATE_SSH_PASS="<your-password>"
       EOF
       chmod 600 /tmp/kunpeng_server_env.sh
       source /tmp/kunpeng_server_env.sh
       (ssh_client.py reads this file automatically in new sessions)

     Windows PowerShell:
       $env:KUNPENG_SERVER_HOST='<your-server-ip>'
       $env:KUNPENG_SERVER_PORT='22'
       $env:KUNPENG_SERVER_USER='root'
       $env:MIGRATE_SSH_PASS='<your-password>'

     Windows CMD:
       set MIGRATE_SSH_PASS=your-password

     Windows GUI (persistent):
       Settings > System > About > Advanced system settings >
       Environment Variables > User variables > New >
       Variable name: MIGRATE_SSH_PASS
       Variable value: <your-password>
       (Then restart VS Code or terminal)

   I will verify SSH connection automatically using paramiko
   (python <skill_dir>/scripts/ssh_client.py test).

   If you need to provision a new Kunpeng ECS server, I can do that for you
   using the provisioning script. After provisioning, MIGRATE_SSH_PASS will
   be set automatically in /tmp/kunpeng_server_env.sh.
   ```
3. **Do not continue** executing any operations until the user provides the server connection info (host/port/user via env vars, not credentials in conversation).

---

## Resource Cleanup Reminder

> **⚠️ IMPORTANT: The Resource Cleanup Reminder is presented AFTER the source code scan completes (Task 3), NOT immediately after server provisioning.**

The reminder is defined in [task-scan-source-code.md Step 6](task-scan-source-code.md#step-6-post-scan-reminders-after-assessment-completes). The AI presents it as the final step of the workflow, after the migration report is shown to the user.

### For the Provisioning Path (Step 3d)

After the scan completes, the AI MUST present the Resource Cleanup Reminder:

```
### 🧹 Resource Cleanup Reminder

The following resources were created during this assessment and incur ongoing charges:

| Resource Type | Resource ID | Details |
|---------------|-------------|---------|
| ECS Instance  | <server_id> | <eip>, <flavor> |
| VPC           | <vpc_id>    | <vpc_name> |
| Subnet        | <subnet_id> | <subnet_name> |
| EIP           | <eip_id>    | <eip> |
| Security Group| <sg_id>     | <sg_name> |

To delete these resources, execute the following commands manually (in reverse order):

  hcloud ECS DeleteServers --cli-region=cn-southwest-2 --servers.1.id=<server_id>
  hcloud VPC DeletePublicip --cli-region=cn-southwest-2 --publicip_id=<eip_id>
  hcloud VPC DeleteSubnet --cli-region=cn-southwest-2 --vpc_id=<vpc_id> --subnet_id=<subnet_id>
  hcloud VPC DeleteSecurityGroup --cli-region=cn-southwest-2 --security_group_id=<sg_id>
  hcloud VPC DeleteVpc --cli-region=cn-southwest-2 --vpc_id=<vpc_id>

⚠️ WARNING: Deletion is IRREVERSIBLE. Verify resource IDs before executing.
⚠️ AI will NOT execute these commands. Please run them manually.
```

**No password rotation reminder is needed** — the password in `MIGRATE_SSH_PASS` is wiped from `os.environ` after each paramiko connection is established. No SSH keys are injected, no ControlMaster sockets are left open.

### For the Existing Server Path (Step 3c) and Local Install Path (Step 3a)

No resource cleanup reminder is needed — the user provided their own server or installed DevKit locally. No SSH keys are injected and no ControlMaster sockets are left open (unified paramiko approach).
