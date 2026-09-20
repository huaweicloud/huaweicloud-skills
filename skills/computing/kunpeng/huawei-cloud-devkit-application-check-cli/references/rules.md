# SSH Authentication & Credential Rules

## Core Principle

DevKit server login credentials (username and password) are obtained **ONLY** from environment variables. EIP for remote login is obtained **ONLY** by querying hcloud for the created devkit server. No additional password is set at any stage of the workflow ? neither during server creation nor after creation.

---

## Two-Layer SSH Architecture

This policy governs **Layer 1** (Agent ? DevKit server). Layer 2 (DevKit server ? nodes.conf targets) is handled by shell scripts on the DevKit server and is documented in [DevKit Operations Guide](devkit-operations-guide.md).

| Layer | Transport | Connects | Governed by |
|-------|-----------|----------|-------------|
| **Layer 1** | `paramiko` (`devkit_remote.py`) | Agent local ? DevKit ECS | This policy (env vars + hcloud EIP) |
| **Layer 2** | DevKit server `ssh`/`sshpass` | DevKit ECS ? nodes.conf targets | `encrypt-nodes-verify.sh` (nodes.conf credentials) |

> **?? paramiko is Layer 1 ONLY.** It connects to the DevKit server and nothing else. Target-server connectivity (nodes.conf) is always performed by the DevKit server's own SSH binaries in Layer 2.

---

## EIP Source Rules

### EIP Resolution

`DEVKIT_ECS_EIP` (DevKit server EIP) is obtained **ONLY** by querying hcloud CLI for the created devkit server:

```bash
hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION} --limit=500   # Find devkit-ecs-* server
hcloud ECS ShowServer --cli-region=${HUAWEI_REGION} --server_id=${SERVER_ID}  # Extract floating IP
```

### Prohibited EIP Sources

| Prohibited Action | Reason |
|-------------------|--------|
| Reading `DEVKIT_ECS_EIP` from User/Machine/Process env vars | EIP must come from hcloud query only, never from env vars |
| Writing `DEVKIT_ECS_EIP` to User/Machine/Process env vars | EIP is auto-resolved at runtime, must not persist in env |
| Hardcoding EIP address | Violates no-hardcoding rule |
| Accepting EIP from command-line arguments as primary source | EIP must be auto-resolved from hcloud |

> **?? FORBIDDEN**: `DEVKIT_ECS_EIP` must NOT be read from or written to any environment variable level (User, Machine, or Process). It is obtained ONLY by querying hcloud for the created devkit server.

---

## Environment Variables

| Variable | Purpose | Detection Order |
|----------|---------|-----------------|
| `HUAWEI_ACCESS_KEY` | Huawei Cloud AK | No (user configures via `hcloud configure set` themselves, AI never executes) |
| `HUAWEI_SECRET_KEY` | Huawei Cloud SK | No (user configures via `hcloud configure set` themselves, AI never executes) |
| `HW_SECURITY_TOKEN` | Temporary credential token (optional) | No |
| `DEVKIT_ECS_USER` | SSH login username (ONLY source, no default) | User ? Machine (NOT Process) |
| `DEVKIT_ECS_PASSWORD` | SSH login password (ONLY source, no default) | User ? Machine (NOT Process) |
| `DEVKIT_ECS_EIP` | DevKit server EIP | **?? hcloud query ONLY** (NOT from env vars) |

Detection is performed via PowerShell:

```powershell
[System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_USER", "User")
[System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_USER", "Machine")
```

> **Process-level env vars are explicitly excluded** ? only User and Machine levels are checked, ensuring values persist across sessions and are not transient.

> **Note**: Region is NOT an environment variable. User must explicitly select a region each time (4 options: cn-north-4, cn-east-3, cn-south-1, cn-southwest-2). No default, no cache, no memory of previous selection.

---

## Parameter Confirmation Rule

> **?? CRITICAL**: Before executing ANY command or API call, ALL parameters MUST be explicitly confirmed by the user. NO defaults. NO implicit assumptions. NO execution without explicit user approval.

### Parameters Requiring Confirmation

| Category | Parameters | When to Confirm |
|----------|-----------|-----------------|
| Region | `HUAWEI_REGION` | Step 2 ? each time, no cache |
| Network | VPC name, Subnet name, Security Group name, CIDR | Step 3 ? before create/reuse |
| ECS | Instance name, Flavor, OS image, adminPass source | Step 5 ? before creation |
| Credentials | `DEVKIT_ECS_USER`, `DEVKIT_ECS_PASSWORD` | Before any SSH connection |
| Scan | Scan mode, scan path, report path, log level | Step 8 ? before execution |
| Report | Local download path | Step 9 ? user provides explicitly |

### Confirmation Flow

1. AI collects all parameters for the upcoming command/API call
2. AI presents a **parameter summary** to the user
3. AI asks: "Confirm the above parameters? (yes/no)"
4. **User explicitly says yes** ? Execute
5. **User says no or no response** ? Do NOT execute

> **?? FORBIDDEN**: Executing any command/API call with unconfirmed parameters, assumed defaults, or without explicit user approval.

---

## Password Source Rules

### During ECS Creation (Step 5)

- `--server.adminPass` in `hcloud ECS CreateServers` MUST use `DEVKIT_ECS_PASSWORD` env var value
- This is NOT "setting an additional password" ? it passes the user's existing env var value to set the server's initial login password
- Do NOT hardcode, auto-generate, or derive a password from any other source

### After ECS Creation (Remote Login)

- SSH login uses `DEVKIT_ECS_USER` and `DEVKIT_ECS_PASSWORD` from environment variables
- No password reset or modification is performed after server creation
- The password used for SSH login is the same value that was passed as `adminPass` during creation

---

## Prohibited Actions

The following actions are **strictly forbidden** at all stages:

| Prohibited Action | Reason |
|-------------------|--------|
| `hcloud ECS BatchResetServersPassword` | Modifies server password without user consent |
| Any API call that modifies the DevKit server password | Violates credential-from-env-var-only principle |
| Auto-generating a password | Credentials must come from user-set env vars |
| Hardcoding username or password | Violates no-hardcoding rule |
| Reading credentials from Process-level env vars | Transient, unreliable across sessions |
| Using `adminPass` as a separate credential source | adminPass is just a conduit for the env var value |
| Reading/writing `DEVKIT_ECS_EIP` from/to env vars | EIP must come from hcloud query only, never from env vars |
| Displaying AK/SK, DEVKIT_ECS_PASSWORD, or nodes.conf ssh_pass in chat, thinking, or tool calls | Must always mask as `***` or use placeholders |
| `echo`/`print`/`log`/`Write-Output` of resolved DEVKIT_ECS_PASSWORD value | Hard prohibition ? password value must NEVER be output in any form |
| Showing actual password value in SSH logs, error messages, or debug output | Use `***` or `<your_password>` placeholder instead |
| Passing password as visible CLI arg in chat (e.g., `sshpass -p <actual_value>`) | Use `${DEVKIT_ECS_PASSWORD}` variable reference or redact in chat |
| `cat`/`grep`/`sed`/`head`/`tail` on nodes.conf into chat output | Plaintext ssh_pass would leak ? use `encrypt-nodes-verify.sh --mask` instead |
| Running `devkit sys-mig` scan while nodes.conf has plaintext ssh_pass | MUST run `encrypt-nodes-verify.sh` to encrypt & replace first |

---

## Chat Masking & Encryption Rules

### ?? No Plaintext Passwords in AI Output

AK/SK values, `DEVKIT_ECS_PASSWORD`, and `nodes.conf` plaintext `ssh_pass` values must **NEVER** appear in plaintext anywhere in AI-generated content. This includes:
- **Chat responses** ? all text output to the user
- **Internal thinking / reasoning** ? the AI's internal thought process must never contain actual password values
- **Tool call arguments** ? parameters passed to bash, SSH, paramiko, or any tool must not log password values
- **Command examples** ? use `${DEVKIT_ECS_PASSWORD}` (variable reference) or `<your_password>` (placeholder)
- **Error messages, debug output, status reports** ? mask as `***` or use placeholders

Always mask as `***` or use placeholders like `<your_ak>`, `<your_sk>`, `<your_password>`, `<ssh_pass_value>`.

### ?? DEVKIT_ECS_PASSWORD Plaintext Prohibition

The resolved value of `DEVKIT_ECS_PASSWORD` MUST NEVER appear in plaintext in any AI output ? including chat responses, internal thinking/reasoning, tool call arguments, and log output. This is a **hard prohibition** with no exceptions. Specifically:

- **NEVER** `echo`, `print`, `log`, `Write-Output`, or `console.log` the resolved `DEVKIT_ECS_PASSWORD` value
- **NEVER** include the actual password value in command examples shown to the user ? always use `${DEVKIT_ECS_PASSWORD}` (variable reference) or `<your_password>` (placeholder)
- **NEVER** display the password in SSH connection logs, error messages, debug output, or status reports
- **NEVER** pass the password value as a visible command-line argument (e.g., `sshpass -p <actual_password>`) in chat ? use env var reference or redact
- When SSH auth fails, output guidance using placeholders (`<your_password>`, `<correct_password>`), NEVER the actual resolved value
- The only approved forms in chat: `***`, `<your_password>`, `${DEVKIT_ECS_PASSWORD}` (variable name, not value)

### ?? nodes.conf Safe Display

When the AI needs to show `nodes.conf` content in chat, it MUST run `bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --mask` on the DevKit server (via Layer 1 paramiko). This mode outputs `nodes.conf` with every `ssh_pass` value replaced by `***`. NEVER `cat`/`grep`/`sed` `nodes.conf` directly into chat output ? plaintext passwords would leak. The same rule applies to internal thinking/reasoning: the AI must never think about or reason with actual password values from `nodes.conf`.

### ?? Mandatory Encryption Replacement

Before executing any `devkit sys-mig` scan command, the AI MUST ensure `encrypt-nodes-verify.sh` has been run on the DevKit server to encrypt all plaintext `ssh_pass` values (via `sys-mig -ec`) and replace them in `nodes.conf`. If `nodes.conf` still contains plaintext passwords, **STOP** and run `encrypt-nodes-verify.sh` first. Scanning with plaintext passwords is **FORBIDDEN**.

---

## SSH Authentication Failure Handling

When SSH authentication fails (paramiko `AuthenticationException`), follow this flow:

### Flow

```
SSH Auth Failed
    ?
    ?
[1] Re-detect DEVKIT_ECS_USER and DEVKIT_ECS_PASSWORD
    from User ? Machine levels
    ?
    ??? New values found (different from previous)
    ?       ?
    ?       ?
    ?   Retry SSH with new credentials
    ?       ?
    ?       ??? Success ? Continue workflow
    ?       ??? Fail ? Go to [2]
    ?
    ??? Same values or not found
            ?
            ?
        [2] Ask user to update or add environment variables
            ?
            ?
        STOP ? user must fix env vars before retrying
```

### Implementation (devkit_remote.py)

The `get_ssh_client` function implements this with 3 retries:

1. **Attempt 1**: Use initially resolved env var values
2. **Attempt 2+**: Re-detect env vars from User ? Machine levels; if new values found, use them; otherwise keep previous values
3. **All retries exhausted**: Print clear instructions for user to update/add env vars, then exit

### User Instructions on Failure

If all retries fail, output the following guidance:

```
[ERROR] SSH authentication failed after 3 attempts.
[ERROR] Credentials can ONLY come from environment variables (User -> Machine levels, NOT Process).
[ERROR] NEVER use ECS adminPass or auto-generate/reset password.
[ERROR]
[ERROR] If env vars not set, add them via PowerShell:
[ERROR]   [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_USER", "<username>", "User")
[ERROR]   [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<password>", "User")
[ERROR]
[ERROR] If env vars already set but wrong, update them:
[ERROR]   [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<correct_password>", "User")
```

---

## Password Requirements

When the user sets `DEVKIT_ECS_PASSWORD`, it must comply with Huawei Cloud ECS password rules:

- 8?26 characters
- At least 3 of: uppercase, lowercase, digit, special char `!@#$%^&*_-+=`
- Must NOT contain the username

---

## Credential Resolution (Step 4.3)

```powershell
# Check env vars (User ? Machine priority)
[System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_USER", "User")
[System.Environment]::GetEnvironmentVariable("DEVKIT_ECS_USER", "Machine")
```

If not set ? Ask user to set and **STOP**:

```powershell
[System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_USER", "<your_username>", "User")
[System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<your_password>", "User")
```

---

## Security Design (Tool Separation & Password Lifecycle)

### Tool Separation Principle

This skill adopts a strict tool separation architecture, ensuring passwords and credentials are securely transferred across different layers:

| Tool | Responsibility | Password Exposure Risk |
|------|---------------|----------------------|
| **hcloud CLI** | ECS creation, EIP query, VPC operations | `--server.adminPass` uses environment variable reference, does not expose plaintext |
| **Python paramiko** (`devkit_remote.py`) | Layer 1 SSH: Agent ? DevKit ECS | Password read from environment variable, passed to `SSHClient.connect(password=...)`, only in Python process memory |
| **Shell scripts** (`encrypt-nodes-verify.sh`) | Layer 2 SSH: DevKit ECS ? nodes.conf targets | Uses `sshpass -e` (environment variable), does not use `sshpass -p` (command-line argument) |
| **DevKit CLI** (`devkit sys-mig`) | Scan execution | Uses encrypted passwords in `nodes.conf`, DevKit decrypts internally |

### Password Leakage Risk Elimination

| Risk Vector | Mitigation |
|-------------|-----------|
| `ps -ef` exposes password | `sshpass -e` (environment variable) replaces `sshpass -p` (command-line argument); paramiko password in Python memory |
| Environment variable read by other processes | `DEVKIT_ECS_PASSWORD` only read from User/Machine level (not Process level); `SSHPASS` environment variable only exists during `sshpass` call |
| AI chat/thinking leakage | Hard prohibition: password value never appears in chat, thinking, tool call arguments; always use `***` or placeholders |
| `nodes.conf` plaintext password leakage | Mandatory encryption: must encrypt and replace via `encrypt-nodes-verify.sh` before scan; use `--mask` mode when displaying |
| Command history leakage | Forbidden to pass password directly on command line; use environment variable reference `${DEVKIT_ECS_PASSWORD}` |

---

## Password Lifecycle Management

This skill involves two types of passwords, each with an independent lifecycle management process:

### 1. DevKit ECS Password (`DEVKIT_ECS_PASSWORD`)

```
[1] Generation (User Setup)
    User sets environment variable via PowerShell
    [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<password>", "User")
        ?
        ?
[2] Usage (ECS Creation + SSH Login)
    Step 5: hcloud ECS CreateServers --server.adminPass=${DEVKIT_ECS_PASSWORD}
    Step 6: paramiko SSHClient.connect(password=${DEVKIT_ECS_PASSWORD})
        ?
        ?
[3] Alive (During Workflow)
    Password remains in environment variable, used for subsequent SSH connections
    Password value never appears in ps -ef, chat, logs
        ?
        ?
[4] Cleanup Suggestion (After Workflow)
    After workflow completes, it is recommended that the user clean up environment variables:
    [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", $null, "User")
    Or when DevKit ECS is no longer needed, reset password via ECS console
```

**Security Constraints**:
- **FORBIDDEN** `hcloud ECS BatchResetServersPassword` to modify password
- **FORBIDDEN** auto-generating password (must be set by user)
- **FORBIDDEN** displaying password value in any output
- Password only read from User ? Machine level environment variables (not Process level)

### 2. nodes.conf Target Server Password (`ssh_pass`)

```
[1] Configuration (User Setup)
    User edits nodes.conf on DevKit ECS, fills in target server plaintext password
        ?
        ?
[2] Encryption (encrypt-nodes-verify.sh)
    Encrypt plaintext password using sys-mig -ec
    Encrypted value replaces plaintext in nodes.conf
        ?
        ?
[3] Verification (SSH Connectivity Check)
    Verify SSH connectivity from DevKit ECS to each target server using encrypted password
    All hosts verified ? allow scan
    Some hosts verification failed ? abort scan, prompt user to fix
        ?
        ?
[4] Usage (Scan Execution)
    devkit sys-mig command reads encrypted password from nodes.conf
    DevKit decrypts internally and uses for SSH connection to target servers
        ?
        ?
[5] Cleanup Suggestion (After Workflow)
    Encrypted password remains in nodes.conf (can be reused)
    If cleanup needed: delete nodes.conf or re-edit to remove ssh_pass
    Verified hosts recorded in /tmp/devkit_nodes_verified_hosts, can be manually deleted to reset
```

**Security Constraints**:
- **FORBIDDEN** scanning when nodes.conf contains plaintext password
- **FORBIDDEN** displaying ssh_pass value in AI output (plaintext or encrypted)
- **FORBIDDEN** using `cat`/`grep`/`sed` to directly output nodes.conf to chat
- Displaying nodes.conf content must use `encrypt-nodes-verify.sh --mask`

---

## Relationship to Other References

- [ECS Creation](ecs-creation.md) ? adminPass uses DEVKIT_ECS_PASSWORD env var
- [DevKit Operations Guide](devkit-operations-guide.md) ? SSH login uses env var credentials
- [Troubleshooting](troubleshooting.md) ? Common issues and solutions
- [Prerequisites](prerequisites.md) ? Environment setup requirements
