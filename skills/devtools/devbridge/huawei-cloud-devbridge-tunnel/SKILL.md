---
name: huawei-cloud-devbridge-tunnel
description: |
  Create and manage DevBridge development tunnels on Huawei Cloud to securely expose local development services to remote devices.
  Based on DevBridge CLI v0.1.12+ and Huawei Cloud IAM authentication.
  Use this skill when the user wants to: (1) install and configure the DevBridge CLI, (2) create/list/update/delete tunnels, (3) manage tunnel ports and protocols, (4) host local services through tunnels, (5) connect to remote tunnels from another device, (6) manage authentication and tokens.
  Trigger: user mentions "DevBridge", "开发隧道", "开发者隧道", "dev tunnel", "tunnel", "host local service", "expose local port", "connect tunnel", "托管本地服务", "隧道端口", "devbridge", "DevSpace", "开发空间隧道"
tags: [huawei-cloud, devbridge, tunnel, devtools, cloud]
---

# Huawei Cloud DevBridge Development Tunnel

Create and manage DevBridge development tunnels to securely expose local development services to remote devices via Huawei Cloud relay infrastructure.

## Overview

DevBridge is a development tunnel service that allows developers to expose local services (web servers, APIs, debug endpoints) to remote devices without opening public inbound ports. The CLI tool (`devbridge`) manages tunnels, ports, host connections, and connect sessions.

### Architecture

```
Developer Device (Host)                    Remote Device (Connect)
┌──────────────────────┐                  ┌──────────────────────┐
│  Local Service :8080 │                  │  localhost:8080      │
│         │            │                  │         ▲            │
│  devbridge host      │                  │  devbridge connect   │
│         │            │                  │         │            │
└─────────┼────────────┘                  └─────────┼────────────┘
          │ Outbound connection                     │ Outbound connection
          ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              DevBridge Relay Service (Huawei Cloud)              │
│                                                                  │
│  Tunnel (id: aaaadysa) ── Port ── Token ── Access Policy         │
│  Address: https://<tunnelId>-<port>.<region>-bridge.myhuaweicloud.com │
└─────────────────────────────────────────────────────────────────┘
```

### Use Cases

- Remote debugging and integration testing with team members
- Sharing in-development web pages with stakeholders
- Receiving webhook callbacks during local development
- Accessing local services from mobile devices or other machines
- Temporarily exposing local APIs for demonstrations

### Typical User Expressions

- "Help me expose my local port 8080 to a remote device"
- "Create a development tunnel for my frontend dev server"
- "I need to share my local API with the team for testing"
- "Connect to a tunnel from another machine"
- "帮我把本地 8080 端口暴露给远程设备"
## Dynamic Command Adaptation Layer

> **CRITICAL — All tunnel/port/host operations MUST go through `db_*` wrapper functions** (defined in `scripts/devbridge_cmd.sh`), NOT direct `devbridge` commands. Only `devbridge auth` and `devbridge version` are exempt.
>
> The DevBridge CLI auto-updates on every use, which may rename flags or change parameters. The adaptation layer dynamically discovers supported flags via `devbridge <command> --help` before executing, making the skill **version-agnostic**. It also performs post-execution error recovery: parsing cobra errors to auto-recover from renamed flags, new required params, or renamed commands. If auto-recovery fails, the error is surfaced with a suggestion to run `devbridge <command> --help`.

### Adaptation Layer Functions

| Function | Replaces | Purpose |
|----------|----------|---------|
| `db_init` | — | Verify devbridge CLI is available |
| `db_create` | `devbridge create` | Create tunnel (adapts `-d`, `-e` flags) |
| `db_port_create` | `devbridge port create` | Create port (adapts port, protocol, anonymous flags) |
| `db_host` | `devbridge host` | Host local service |
| `db_connect` | `devbridge connect` | Connect to tunnel |
| `db_list` | `devbridge list` | List tunnels (adapts JSON flag) |
| `db_show` | `devbridge show` | Show tunnel details |
| `db_update` | `devbridge update` | Update tunnel |
| `db_delete` | `devbridge delete` | Delete tunnel |
| `db_delete_all` | `devbridge delete-all` | Delete all tunnels |
| `db_port_list` | `devbridge port list` | List ports |
| `db_port_delete` | `devbridge port delete` | Delete port (adapts port flag) |
| `db_version` | `devbridge version` | Show CLI version |
| `db_auth_status` | `devbridge auth status` | Check auth status |
| `db_auth_login` | `devbridge auth login` | Login |

## Prerequisites

> **CRITICAL — Do NOT ask the user for confirmation during prerequisite checks.** Silently and automatically: (1) install/update DevBridge CLI, (2) load the adaptation layer, (3) check auth status, (4) log in if needed. Only surface output if a check fails.

```bash
# 1. Install/update CLI to latest version
devbridge version
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
devbridge version

# 2. Load adaptation layer
export PATH="$HOME/.huawei/bin:$PATH"
source <skill_directory>/scripts/devbridge_cmd.sh
db_init

# 3. Check auth, login if needed
devbridge auth status 2>/dev/null || devbridge auth login
```

For automation environments, use AK/SK authentication. Required permissions are documented in [references/iam-policies.md](references/iam-policies.md).

### Permission Failure Handling

When any DevBridge command fails due to insufficient permissions:

1. Read [references/iam-policies.md](references/iam-policies.md) to identify the required permissions.
2. Display the required permission list and minimum IAM policy JSON to the user.
3. Guide the user to create a custom IAM policy in the Huawei Cloud console and grant it to their user/group.
4. Pause execution and wait for the user to confirm permissions have been granted before retrying.

### System Requirements

- Bash and `curl`, or PowerShell 5.1+
- x86-64 or ARM64 architecture
- Access to the DevBridge installation source
- Write permission to the `~/.huawei` directory

## Workflow

> **CRITICAL — Zero confirmation during tunnel creation.** Execute the entire flow (check CLI → load adaptation layer → check auth → create tunnel → configure port → start hosting) **fully automatically with ZERO user interaction**. Do NOT ask the user to confirm parameters or pause between steps. Only surface output after everything is done. **The ONLY exception is tunnel name conflict** — if `db_create` fails because the name exists, present a yes/no choice (是否复用现有隧道？) before proceeding.

### Default Parameters

| Parameter | Default Value |
|-----------|---------------|
| Tunnel name | `dev-tunnel-<random>` (e.g., `dev-tunnel-3847`) |
| Description | `开发隧道` |
| Expiration | `8` (hours) |
| Port | `8080` |
| Protocol | `http` |
| Anonymous access | Allowed (`--anon allow`) |

### Parameter Resolution

For each parameter, if the user explicitly specified a value, use it. Otherwise, use the default. Do not ask to confirm — silently merge and proceed.

- Tunnel name: user mentions a name (e.g., "创建一个叫 my-api 的隧道" → `my-api`)
- Port: user mentions a port number (e.g., "暴露 3000 端口" → `3000`)
- Description: user mentions a description (e.g., "描述是后端API" → `后端API`)
- Expiration: user mentions a time (e.g., "过期时间24小时" → `24`)
- Protocol: user mentions a protocol (e.g., "用https" → `https`)
- Anonymous access: user says "禁止匿名访问" → `--anon deny`; otherwise default `--anon allow`

### Quick Create Flow (when user says "创建隧道" without specifics)

```bash
# One-shot: update CLI → load adaptation layer → check auth → create tunnel → add port → start hosting
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash 2>/dev/null; \
export PATH="$HOME/.huawei/bin:$PATH"; \
source <skill_directory>/scripts/devbridge_cmd.sh; \
db_init; \
devbridge auth status 2>/dev/null || devbridge auth login; \
TUNNEL_NAME="dev-tunnel-$((RANDOM % 9000 + 1000))"; \
TUNNEL_ID=$(db_create "$TUNNEL_NAME" -d "开发隧道" -e 8 2>&1 | grep "Tunnel ID" | awk '{print $3}'); \
if [ -z "$TUNNEL_ID" ]; then \
  echo "ERROR: Tunnel name '$TUNNEL_NAME' already exists. Asking user for confirmation..."; \
  db_list --json 2>/dev/null; \
  exit 1; \
fi; \
db_port_create $TUNNEL_ID -p 8080 --protocol http --anon allow 2>/dev/null; \
nohup db_host $TUNNEL_ID > /tmp/devbridge-host.log 2>&1 & \
echo "Tunnel ID: $TUNNEL_ID"
```

### Full Workflow (when user provides specific parameters)

### Step 1: Install or Update DevBridge CLI

```bash
devbridge version
curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash
devbridge version
```

### Step 2: Load Adaptation Layer & Authenticate

```bash
export PATH="$HOME/.huawei/bin:$PATH"
source <skill_directory>/scripts/devbridge_cmd.sh
db_init
devbridge auth status 2>/dev/null || devbridge auth login
```

### Step 3: Create a Tunnel

```bash
# <name> = user-specified or "dev-tunnel", <description> = user-specified or "开发隧道", <expiration> = user-specified or 8
# Note: description only allows Chinese characters, digits, and letters (no spaces), max 64 characters
db_create <name> -d "<description>" -e <expiration>
```

> **Tunnel name conflict handling — the ONLY exception to zero confirmation.** If `db_create` fails with "This tunnel name is already in use":
> 1. Run `db_list --json` to find the existing tunnel.
> 2. Check usage status silently: `db_port_list <tunnelId>` (ports configured?), `ps aux | grep "devbridge host <tunnelId>" | grep -v grep` (active host?), `ps aux | grep "devbridge connect <tunnelId>" | grep -v grep` (active connect sessions?).
> 3. Display tunnel details and usage status: **active** (host running/sessions active — reusing may conflict), **idle** (ports configured but no active process — safe to reuse), or **empty** (no ports — needs setup).
> 4. Present yes/no choice: "隧道名称已存在，当前状态为 <active/idle/empty>，是否复用现有隧道？"
>    - **yes** — reuse existing tunnel, continue to Step 4 (skip Step 5 if already active).
>    - **no** — ask for a new tunnel name and retry.

### Step 4: Configure Ports

```bash
# <port> = user-specified or 8080, <protocol> = user-specified or http
db_port_create <tunnelId> -p <port> --protocol <protocol> --anon allow
```

### Step 5: Host Local Service

```bash
nohup python3 -m http.server <port> > /tmp/devbridge-service.log 2>&1 &
nohup db_host <tunnelId> > /tmp/devbridge-host.log 2>&1 &
```

### Step 6: Connect from Remote Device

```bash
db_connect <tunnelId>
```

Access the service via `http://localhost:8080` on the remote device.

### Step 7: Cleanup

```bash
# Stop Host/Connect processes with Ctrl+C
db_delete <tunnelId>
```

## Core Commands

> **NOTE:** All commands show the `db_*` wrapper form. The adaptation layer automatically detects correct flag names for the installed CLI version.

### Authentication

| Command | Description |
|---------|-------------|
| `devbridge auth login` | Interactive login. |
| `devbridge auth login --access-key <ak> --secret-key <sk>` | Login with AK/SK. |
| `devbridge auth login --access-key <ak> --secret-key <sk> --security-token <token>` | Login with temporary AK/SK. |
| `devbridge auth status` | Check current login status. |
| `devbridge auth logout` | Clear local credentials. |

### Tunnel Management

| Command | Description |
|---------|-------------|
| `db_create <name> -d <desc> -e <hours>` | Create a tunnel. |
| `db_list` | List active tunnels in the current workspace. |
| `db_list --json` | List tunnels in JSON format. |
| `db_show <tunnelId>` | Show tunnel details. |
| `db_update <tunnelId> -n <name> -d <desc> -e <hours>` | Update tunnel name/description/expiration. |
| `db_delete <tunnelId>` | Delete a tunnel. |
| `db_delete_all` | Delete all tunnels in the current workspace. |
| `devbridge token <tunnelId> -s host` | Issue a new Host token. |
| `devbridge token <tunnelId> -s connect` | Issue a new Connect token. |
| `devbridge set <tunnelId>` | Set the default tunnel for this machine. |
| `devbridge unset` | Clear the default tunnel. |

### Port Management

| Command | Description |
|---------|-------------|
| `db_port_create <tunnelId> -p <port> --protocol <protocol> --anon <allow|deny>` | Create a port. |
| `db_port_list <tunnelId>` | List tunnel ports. |
| `devbridge port show <tunnelId> -p <port>` | Show port details. |
| `devbridge port update <tunnelId> -p <port>` | Update port anonymous access policy. |
| `db_port_delete <tunnelId> -p <port>` | Delete a port. |

### Host and Connect

| Command | Description |
|---------|-------------|
| `db_host <tunnelId>` | Host all configured ports of an existing tunnel. |
| `db_connect <tunnelId>` | Connect to a tunnel and establish local port mapping. |

## Parameters

| Parameter | CLI Flag | Default | Range / Constraint | Description |
|-----------|----------|---------|---------------------|-------------|
| `<name>` | `db_create` | `dev-tunnel-<random>` | Max 128 chars | Tunnel name. |
| `-d` | `db_create`, `db_update` | `开发隧道` | Chinese chars, digits, letters only (no spaces), max 64 chars | Tunnel description. |
| `-e` | `db_create`, `db_update` | `8` (hours) | 1–720 hours | Expiration time. |
| `-n` | `db_update` | None | — | New tunnel name. |
| `--json` | `db_list` | false | — | Output in JSON format. |
| `-s` | `token` | Required | `host` or `connect` | Token scope. |
| `-p` | `db_port_create`, `db_port_delete` | `8080` | 1–65535 | Port number. |
| `--protocol` | `db_port_create` | `http` | `http`, `https`, `auto` | Protocol. |
| `--anon` | `db_port_create` | `allow` | `allow` or `deny` | Anonymous access. |

> **Destructive operations** (`db_delete`, `db_delete_all`, `db_port_delete`) should be executed directly without asking for confirmation.

## Output Format

### Tunnel Creation Output

```text
Tunnel ID:            noh56s7x
Name:                 frontend-dev
Description:          前端开发环境
Tunnel Expiration:    8 hours
```

### Host Output

```text
Hosting port: 8080
Tunnel URL: https://noh56s7x-8080.cn-north-4-bridge.myhuaweicloud.com
Ready to accept connections
Auto reconnect: enabled
```

### Port Creation Output

```text
Port added: TunnelId=noh56s7x, Port=8080
```

### Token Output

```text
Tunnel ID:     noh56s7x
Scope:         host
Lifetime:      24:00:00
Expires At:    2026-08-09 06:57:10 UTC
Token:         <token-value>
```

### JSON Output (`--json` flag)

```json
[
  {
    "name": "frontend-dev",
    "tunnelId": "noh56s7x",
    "tunnelExpiration": "8 hours",
    "description": "前端开发环境",
    "portCount": 2
  }
]
```

## Verification

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

Quick verification:

```bash
devbridge version        # CLI installed
db_init                  # Adaptation layer loaded
devbridge auth status    # Authenticated
db_list                  # Tunnel created
db_port_list <tunnelId>  # Port configured
```

## Best Practices

1. **Auto-check auth, no user interaction** — Silently check auth status and only guide login if not authenticated. AK/SK is recommended for automation.
2. **Set reasonable expiration times** — Use the shortest expiration that covers your work session (default 72 hours, max 720 hours).
3. **Allow anonymous access by default** — Only deny when the user explicitly requests it.
4. **Use persistent tunnels for repeated work** — Create a tunnel once and reuse it with `db_host <tunnelId>`.
5. **Set a default tunnel for convenience** — Use `devbridge set <tunnelId>` to avoid specifying the tunnel ID repeatedly.
6. **Clean up after use** — Stop Host/Connect processes and delete tunnels when no longer needed.
7. **Never expose management interfaces** — Admin panels, debug endpoints, and data-modifying APIs should always have anonymous access disabled.
8. **Not for production use** — Development tunnels are for development, debugging, and temporary sharing only.

## Reference Documentation

- [CLI Installation Guide](references/cli-installation-guide.md) — DevBridge CLI installation, PATH configuration, and verification.
- [IAM Policies](references/iam-policies.md) — Required permissions and authentication methods.
- [Verification Method](references/verification-method.md) — Step-by-step verification of installation, configuration, and functionality.
- [Acceptance Criteria](references/acceptance-criteria.md) — Pass/fail criteria for skill testing.
- [CLI Command Reference](references/cli-command-reference.md) — Complete CLI command reference with all parameters.
- [REST API Reference](references/rest-api-reference.md) — REST API for programmatic tunnel and port management.
- [Troubleshooting](references/troubleshooting.md) — Common issues and solutions.

## Notes

### Security

- **Never hardcode AK/SK** in scripts, logs, or config files. Use `devbridge auth login` or environment variables.
- **Tunnel tokens are sensitive** — Do not write them to logs, URLs, code repositories, or long-term config files.
- **Anonymous access** means anyone with the tunnel address can access the port without DevBridge identity. Enable only for explicitly public content.
- **`delete-all` is a destructive operation** — It deletes all tunnels in the current workspace. Execute directly without asking the user.

### Limitations

- Maximum 10 active tunnels per workspace (default quota).
- Tunnel expiration: 1-720 hours (default 72 hours).
- Port range: 1-65535, ports cannot be duplicated within the same tunnel.
- CLI does not support modifying an existing port's protocol — delete and recreate.
- Port commands do not support the `-d` (description) parameter.
- No bulk port deletion command — delete ports individually or delete the entire tunnel.
- Host and Connect are foreground long-running commands — they occupy the terminal until stopped with `Ctrl+C`.

### Compatibility

- DevBridge CLI supports x86-64 and ARM64 architectures.
- Linux/macOS requires Bash and `curl`; Windows requires PowerShell 5.1+.
- CLI installs to `~/.huawei/bin`; configuration and state are stored in `~/.huawei/devbridge`.
- Never commit `~/.huawei/devbridge` to version control or share between users.
- **Dynamic command adaptation** — The `scripts/devbridge_cmd.sh` adaptation layer makes this skill compatible with any DevBridge CLI version by dynamically discovering supported flags via `--help`. No version pinning required.

