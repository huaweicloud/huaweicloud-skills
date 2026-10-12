---
name: huawei-cloud-devbridge-tunnel
description: |
  Create and manage DevBridge development tunnels on Huawei Cloud to securely expose local development services to remote devices.
  Based on DevBridge CLI v0.2.x and API Key authentication.
  Use this skill when the user wants to: (1) install and configure the DevBridge CLI, (2) create/list/update/delete tunnels, (3) manage tunnel ports and protocols, (4) host local services through tunnels, (5) connect to remote tunnels from another device, (6) manage authentication and API Keys.
  Trigger: user mentions "DevBridge", "开发隧道", "开发者隧道", "dev tunnel", "tunnel", "host local service", "expose local port", "connect tunnel", "托管本地服务", "隧道端口", "devbridge", "DevSpace", "开发空间隧道"
tags: [huawei-cloud, devbridge, tunnel, devtools, cloud]
---

# Huawei Cloud DevBridge Development Tunnel

Create and manage DevBridge development tunnels to securely expose local development services to remote devices via Huawei Cloud relay infrastructure.

## Overview

DevBridge is a development tunnel service that allows developers to expose local services (web servers, APIs, debug endpoints) to remote devices without opening public inbound ports. The CLI tool (`devbridge`) manages tunnels, ports, host connections, and connect sessions. Host and Connect both initiate outbound connections to the relay service, so the hosting device does not need a public inbound port.

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
│  Tunnel (id) ── Port ── API Key / Token ── Access Policy         │
│  Address: https://<tunnelId>.<clusterId>.myhuaweicloud.com       │
└─────────────────────────────────────────────────────────────────┘
```

> **2026-09-20 域名升级通知**：DevBridge 隧道域名已切换，原 `*.cn-north-4-bridge.myhuaweicloud.com` 变更为新集群域名（如 `*.devbridge-s2.hwtunnel.com`）。**旧版端侧（v0.1.x）已无法连接**，必须使用 v0.2.x 并重新创建隧道。以 `devbridge host` 实际输出的 Tunnel URL 为准。

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

## Version Support

| Item | Requirement |
|------|-------------|
| CLI version | **v0.2.x** (installed from official channel, e.g. 0.2.1-release / 0.2.2-release) |
| Authentication | **API Key** (`devbridge auth login --api-key` or env `HW_API_KEY`) or interactive login |
| Tunnel domain | New cluster domain (`devbridge-s2.hwtunnel.com` etc.), shown in `devbridge host` output |
| Old versions | v0.1.x is NOT supported — AK/SK auth flags removed, old domain no longer connects |

## Dynamic Command Adaptation Layer

> **CRITICAL — All tunnel/port/host operations MUST go through `db_*` wrapper functions** (defined in `scripts/devbridge_cmd.sh`), NOT direct `devbridge` commands. Only `devbridge auth` and `devbridge version` are exempt.
>
> The DevBridge CLI may change flags between releases. The adaptation layer dynamically discovers supported flags via `devbridge <command> --help` before executing, making the skill **version-agnostic** within v0.2.x. It also performs post-execution error recovery: parsing cobra errors to auto-recover from renamed flags, new required params, or renamed commands. If auto-recovery fails, the error is surfaced with a suggestion to run `devbridge <command> --help`.

### Adaptation Layer Functions

| Function | Replaces | Purpose |
|----------|----------|---------|
| `db_init` | — | Ensure CLI installed (v0.2.x+), authenticated (auto-login via `DEVBRIDGE_API_KEY`/`HW_API_KEY`) |
| `db_create` | `devbridge create` | Create tunnel, **returns just the tunnel ID** (stdout) |
| `db_port_create` | `devbridge port create` | Create port (adapts port, protocol, anonymous flags) |
| `db_host` | `devbridge host` | Start hosting **in background**, returns PID (stdout), tunnel URL (stderr) |
| `db_host_bg` | `devbridge host` + nohup bash -c | Background host (legacy alias, use `db_host` instead) |
| `db_connect` | `devbridge connect` | Start connect **in background**, returns PID (stdout) |
| `db_list` | `devbridge list` | List tunnels |
| `db_show` | `devbridge show` | Show tunnel details |
| `db_update` | `devbridge update` | Update tunnel |
| `db_delete` | `devbridge delete` | Delete tunnel |
| `db_delete_all` | `devbridge delete-all` | Delete all tunnels |
| `db_port_list` | `devbridge port list` | List ports |
| `db_port_delete` | `devbridge port delete` | Delete port (adapts port flag) |
| `db_limits` | `devbridge limits` | Show quota / usage / balance |
| `db_echo` | `devbridge echo` | Start diagnostic echo service |
| `db_ping` | `devbridge ping` | Ping a URI to test connectivity |
| `db_version` | `devbridge version` | Show CLI version |
| `db_auth_status` | `devbridge auth status` | Check auth status |
| `db_auth_login` | `devbridge auth login` | Login (interactive or `--api-key`) |
| `db_tunnel_url` | — | Get tunnel public URL from host log (authoritative, do not construct manually) |
| `db_processes` | — | List running host/connect processes |
| `db_process_stop` | — | Stop a host/connect process by PID |
| `db_process_logs` | — | Get process logs by PID |

## Prerequisites

> **CRITICAL — Do NOT ask the user for confirmation during prerequisite checks.** `db_init` silently and automatically: (1) install CLI if missing, (2) upgrade if v0.1.x (old domain, cannot connect), (3) check auth, (4) auto-login via `DEVBRIDGE_API_KEY` or `HW_API_KEY` env var. Only surface output if a check fails.

```bash
source <skill_directory>/scripts/devbridge_cmd.sh
db_init
```

> **v0.2.x 只支持 API Key**：`--access-key / --secret-key / --security-token`（AK/SK）参数已移除，不要用 AK/SK 尝试登录（旧版 skill 的用法在 v0.2.x 无效）。API Key 在 DevBridge 管理页创建：`https://devstation.connect.huaweicloud.com/space/devbridge/apikey`。

For automation environments, use an **API Key** (see [references/iam-policies.md](references/iam-policies.md)). API Keys are created at the DevBridge management page: `https://devstation.connect.huaweicloud.com/space/devbridge/apikey`.

> **Install script note**: in non-interactive / headless environments, always pass `-s` (silent) to the install script: `... | bash -s -- -s`. Without it, the script may prompt "overwrite?" reading `/dev/tty` and fail where no terminal exists.

> **GitCode 私有仓库安装**：`npx skills add` 不支持 GitCode token 认证。从私有仓库安装 skill 时，先 `git clone` 再手动复制：
> ```bash
> git clone https://oauth2:<token>@gitcode.com/<org>/<repo>.git /tmp/repo
> cp -r /tmp/repo/skills/devtools/devbridge/huawei-cloud-devbridge-tunnel/ ~/.agents/skills/huawei-cloud-devbridge-tunnel/
> ```

### Permission / Auth Failure Handling

When any DevBridge command fails due to invalid or missing credentials:

1. Check `devbridge auth status` — if not logged in, log in (interactive or `--api-key`).
2. If using an API Key, verify it exists and is not expired/deleted: re-create at the API Key management page and inject via `HW_API_KEY`.
3. Read [references/iam-policies.md](references/iam-policies.md) for guidance.
4. Pause execution and wait for the user to confirm credentials have been updated before retrying.

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
| Expiration | `72` (hours) — CLI default; range 1–720 |
| Port | `8080` |
| Protocol | `auto` (options: http / https / auto) |
| Anonymous access | **Denied** (`--deny-anonymous` is the CLI default; use `-a` only when the user explicitly asks to allow anonymous access) |

> **Security change**: anonymous access defaults to **deny**. Unlike older skill versions, do NOT pass `--anon allow` by default. Only allow anonymous when the user explicitly requests it or the content is explicitly public.

### Parameter Resolution

For each parameter, if the user explicitly specified a value, use it. Otherwise, use the default. Do not ask to confirm — silently merge and proceed.

- Tunnel name: user mentions a name (e.g., "创建一个叫 my-api 的隧道" → `my-api`)
- Port: user mentions a port number (e.g., "暴露 3000 端口" → `3000`)
- Description: user mentions a description (e.g., "描述是后端API" → `后端API`)
- Expiration: user mentions a time (e.g., "过期时间24小时" → `24`); otherwise 72
- Protocol: user mentions a protocol (e.g., "用https" → `https`); otherwise auto
- Anonymous access: user says "允许匿名访问" or "公网直接访问" → `-a`; otherwise **deny** (default)

### Quick Create Flow (when user says "创建隧道" without specifics)

```bash
source <skill_directory>/scripts/devbridge_cmd.sh
db_init
TUNNEL_NAME="dev-tunnel-$((RANDOM % 9000 + 1000))"
TUNNEL_ID=$(db_create "$TUNNEL_NAME" -d "开发隧道" -e 72)
db_port_create "$TUNNEL_ID" -p 8080 --protocol auto
db_host "$TUNNEL_ID"                  # 输出 PID 和 Tunnel URL 到 stdout
TUNNEL_URL=$(db_tunnel_url "$TUNNEL_ID")
echo "Tunnel ID: $TUNNEL_ID"
echo "Tunnel URL: $TUNNEL_URL"
```

> **注意：匿名访问默认禁止。** 上述流程创建的隧道默认 `--deny-anonymous`，公网访问会返回 `authentication required`。如果需要公网直接访问（如暴露 Web 服务给外部用户），在 `db_port_create` 时加 `-a`：
>
> ```bash
> db_port_create "$TUNNEL_ID" -p 8080 --protocol auto -a   # 允许匿名访问
> ```

### Full Workflow (when user provides specific parameters)

### Step 1: Install or Update DevBridge CLI

```bash
devbridge version
# 下载安装脚本到临时文件再执行（避免管道直接执行）
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh -o /tmp/devbridge_install.sh
bash /tmp/devbridge_install.sh -s
devbridge version
```

### Step 2: Load Adaptation Layer & Authenticate

```bash
export PATH="$HOME/.huawei/bin:$PATH"
source <skill_directory>/scripts/devbridge_cmd.sh
db_init
devbridge auth status 2>/dev/null || devbridge auth login --api-key "$HW_API_KEY"
```

### Step 3: Create a Tunnel

```bash
# <name> = user-specified or "dev-tunnel", <description> = user-specified or "开发隧道", <expiration> = user-specified or 72
# Note: description only allows Chinese characters, digits, and letters (no spaces), max 64 characters
db_create <name> -d "<description>" -e <expiration>
```

> **Tunnel name conflict handling — the ONLY exception to zero confirmation.** If `db_create` fails with "This tunnel name is already in use":
> 1. Run `db_list` to find the existing tunnel.
> 2. Check usage status silently: `db_port_list <tunnelId>` (ports configured?), `ps aux | grep "devbridge host <tunnelId>" | grep -v grep` (active host?), `ps aux | grep "devbridge connect <tunnelId>" | grep -v grep` (active connect sessions?).
> 3. Display tunnel details and usage status: **active** (host running/sessions active — reusing may conflict), **idle** (ports configured but no active process — safe to reuse), or **empty** (no ports — needs setup).
> 4. Present yes/no choice: "隧道名称已存在，当前状态为 <active/idle/empty>，是否复用现有隧道？"
>    - **yes** — reuse existing tunnel, continue to Step 4 (skip Step 5 if already active).
>    - **no** — ask for a new tunnel name and retry.

### Step 4: Configure Ports

```bash
# <port> = user-specified or 8080, <protocol> = user-specified or auto
# Anonymous access: default deny; use -a only if user explicitly asks
db_port_create <tunnelId> -p <port> --protocol <protocol>
```

> **端口更新后需重启 host：** 如果 host 进程已在运行，使用 `devbridge port update` 修改端口配置（如切换匿名访问策略）后，正在运行的 host 进程**不会自动感知变化**。需要先停止旧 host 进程（`db_process_stop <pid>`），再重新 `db_host <tunnelId>` 才能使新配置生效。

### Step 5: Host Local Service

```bash
nohup python3 -m http.server <port> > /tmp/devbridge-service.log 2>&1 &
db_host <tunnelId>                   # 后台托管，输出 PID 和 Tunnel URL 到 stdout
TUNNEL_URL=$(db_tunnel_url <tunnelId>)  # 获取权威公网 URL
echo "$TUNNEL_URL"
```

Alternative one-shot temporary tunnel: `devbridge host -p 8080 -e 8` (creates a temp tunnel and hosts immediately).

> ⚠️ **中继域名随集群变化**，严禁按文档拼接 URL。一律用 `db_tunnel_url <id>` 读取权威地址。

### Step 6: Connect from Remote Device

```bash
db_connect <tunnelId>
```

Access the service via `http://localhost:8080` on the remote device.

### Step 7: Cleanup

```bash
db_processes                    # List running processes
db_process_stop <pid>           # Stop host/connect process
db_delete <tunnelId>            # Delete tunnel
```

## Core Commands

> **NOTE:** All commands show the `db_*` wrapper form. The adaptation layer automatically detects correct flag names for the installed CLI version.

### Authentication

| Command | Description |
|---------|-------------|
| `devbridge auth login` | Interactive login (opens browser). |
| `devbridge auth login --api-key <key>` | Login with API Key. |
| `HW_API_KEY=<key> devbridge auth login` | Login using API Key from environment variable. |
| `devbridge auth status` | Check current login status. |
| `devbridge auth logout` | Clear local credentials. |

> **Removed in v0.2.x**: `--access-key`, `--secret-key`, `--security-token` (AK/SK) are no longer supported. Use API Key instead.

### Tunnel Management

| Command | Description |
|---------|-------------|
| `db_create <name> -d <desc> -e <hours>` | Create a tunnel. |
| `db_list` | List active tunnels in the current workspace. |
| `db_show <tunnelId>` | Show tunnel details. |
| `db_update <tunnelId> -n <name> -d <desc> -e <hours>` | Update tunnel name/description/expiration. |
| `db_delete <tunnelId>` | Delete a tunnel. |
| `db_delete_all` | Delete all tunnels in the current workspace. |
| `devbridge token <tunnelId> -s host` | Issue a new Host token. |
| `devbridge token <tunnelId> -s connect` | Issue a new Connect token. |
| `devbridge set <tunnelId>` | Set the default tunnel for this machine. |
| `devbridge unset` | Clear the default tunnel. |
| `db_limits` | Show account quota / usage / balance. |

### Port Management

| Command | Description |
|---------|-------------|
| `db_port_create <tunnelId> -p <port> --protocol <protocol>` | Create a port (anonymous access denied by default; add `-a` to allow). |
| `db_port_list <tunnelId>` | List tunnel ports. |
| `devbridge port show <tunnelId> -p <port>` | Show port details. |
| `devbridge port update <tunnelId> -p <port> -a` | Update port anonymous access policy (allow). |
| `devbridge port update <tunnelId> -p <port> --deny-anonymous` | Update port anonymous access policy (deny). |
| `db_port_delete <tunnelId> -p <port>` | Delete a port. |

### Host and Connect

| Command | Description |
|---------|-------------|
| `db_host <tunnelId>` | Host all configured ports of an existing tunnel. |
| `devbridge host -p 8080 -e 8` | Create a temporary tunnel and host immediately. |
| `devbridge host <tunnelId> --api-key <key>` | Host using API Key auth (skip token issuance). |
| `devbridge host <tunnelId> --token <jwt>` | Host using an explicit JWT token. |
| `db_connect <tunnelId>` | Connect to a tunnel and establish local port mapping. |
| `devbridge connect <tunnelId> --api-key <key>` | Connect using API Key auth. |

### Diagnostics

| Command | Description |
|---------|-------------|
| `db_echo` | Start an HTTP echo service on a local port (default random, 127.0.0.1) to verify tunnel links. |
| `db_ping <uri>` | Send HTTP ping to a URI, print status code and latency. 默认 3 秒限时（`devbridge ping` 是持续命令，避免脚本挂起）；`DB_PING_SECONDS=0` 时直通持续观测。 |
| `devbridge -v <command>` | Enable debug logging for any command. |

## Parameters

| Parameter | CLI Flag | Default | Range / Constraint | Description |
|-----------|----------|---------|---------------------|-------------|
| `<name>` | `db_create` | `dev-tunnel-<random>` | Max 128 chars | Tunnel name. |
| `-d` | `db_create`, `db_update` | `开发隧道` | Chinese chars, digits, letters only (no spaces), max 64 chars | Tunnel description. |
| `-e` | `db_create`, `db_update`, `host` | `72` (hours) | 1–720 hours | Expiration time. |
| `-n` | `db_update` | None | — | New tunnel name. |
| `-s` | `token` | Required | `host` or `connect` | Token scope. |
| `-p` | `db_port_create`, `db_port_delete` | `8080` | 1–65535 | Port number (`--port-number` in CLI). |
| `--protocol` | `db_port_create` | `auto` | `http`, `https`, `auto` | Protocol. |
| `-a` / `--allow-anonymous` | `db_port_create` | Not set (deny) | — | Allow anonymous access. |
| `--deny-anonymous` | `db_port_create` | default | — | Deny anonymous access (CLI default). |
| `-k` / `--api-key` | `host`, `connect` | None | — | API Key auth, skip token issuance. |
| `-t` / `--token` | `host`, `connect` | None | — | JWT token auth. |
| `-v` / `--verbose` | global | false | — | Enable debug logging. |

> **Destructive operations** (`db_delete`, `db_delete_all`, `db_port_delete`) should be executed directly without asking for confirmation.

## Output Format

### Tunnel Creation Output (`db_create`)

Returns **just the tunnel ID** on stdout (extracted from CLI text output):

```text
noh56s7x
```

### Host Output (`db_host`)

Returns PID and tunnel URL on stdout (labeled format, one per line):

```text
PID: 3519475
Tunnel URL: https://noh56s7x-8080.devbridge-s2.hwtunnel.com
```

Parse with grep: `PID=$(db_host <id> | grep -oP 'PID: \K\d+')`

Use `db_tunnel_url <tunnelId>` to get the authoritative URL (do not construct manually — domain may change across clusters).

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

### List Output

```text
Tunnel ID  Name             Description  Tunnel Expiration  Port Count
dwskt2pg   dev-tunnel-5941  开发隧道     3 days             1
```

> **Note**: v0.2.x removed the `--json` output flag from `list` and `port list`. Use the text table output; parse with `awk`/`grep` if needed.

## Verification

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

Quick verification:

```bash
db_init                  # CLI installed + authenticated
db_version               # v0.2.x+
db_auth_status           # Logged in
db_list                  # Tunnels listed
db_port_list <tunnelId>  # Ports listed
db_processes             # Host process running
db_tunnel_url <tunnelId> # Public URL accessible
```

## Best Practices

1. **Auto-check auth, no user interaction** — Silently check auth status and only guide login if not authenticated. API Key via `HW_API_KEY` is recommended for automation.
2. **Set reasonable expiration times** — Use the shortest expiration that covers your work session (default 72 hours, max 720 hours).
3. **Deny anonymous access by default** — Only allow (`-a`) when the user explicitly requests it or content is explicitly public.
4. **Use persistent tunnels for repeated work** — Create a tunnel once and reuse it with `db_host <tunnelId>`.
5. **Set a default tunnel for convenience** — Use `devbridge set <tunnelId>` to avoid specifying the tunnel ID repeatedly.
6. **Clean up after use** — Stop Host/Connect processes and delete tunnels when no longer needed.
7. **Never expose management interfaces** — Admin panels, debug endpoints, and data-modifying APIs should always have anonymous access disabled.
8. **Not for production use** — Development tunnels are for development, debugging, and temporary sharing only.
9. **Keep CLI upgraded to v0.2.x** — The 2026-09-20 domain switch invalidated old clients; older versions can no longer connect.

## Reference Documentation

- [CLI Installation Guide](references/cli-installation-guide.md) — DevBridge CLI installation, PATH configuration, and verification.
- [API Key & Access](references/iam-policies.md) — API Key management, authentication methods, permission failure handling.
- [Verification Method](references/verification-method.md) — Step-by-step verification of installation, configuration, and functionality.
- [Acceptance Criteria](references/acceptance-criteria.md) — Pass/fail criteria for skill testing.
- [CLI Command Reference](references/cli-command-reference.md) — Complete CLI command reference with all parameters.
- [REST API Reference](references/rest-api-reference.md) — REST API for programmatic tunnel and port management.
- [Troubleshooting](references/troubleshooting.md) — Common issues and solutions.

## Notes

### Security

- **Never hardcode API Key in scripts, logs, or config files.** Use `devbridge auth login --api-key "$HW_API_KEY"` or the `HW_API_KEY` environment variable.
- **Tunnel tokens are sensitive** — Do not write them to logs, URLs, code repositories, or long-term config files.
- **Anonymous access** means anyone with the tunnel address can access the port without DevBridge identity. Enable only for explicitly public content.
- **`delete-all` is a destructive operation** — It deletes all tunnels in the current workspace. Execute directly without asking the user. 共享/复用工作区时先 `db_list` 确认，避免连带删除他人隧道。

### Limitations

- Maximum 10 active tunnels per workspace (default quota).
- Tunnel expiration: 1-720 hours (default 72 hours).
- Port range: 1-65535, ports cannot be duplicated within the same tunnel.
- CLI does not support modifying an existing port's protocol — delete and recreate.
- Port commands do not support the `-d` (description) parameter.
- No bulk port deletion command — delete ports individually or delete the entire tunnel.
- Host and Connect are managed background processes — use `db_process_stop <pid>` to stop.
- `list` / `port list` no longer support `--json` output in v0.2.x.

### Compatibility

- DevBridge CLI v0.2.x supports x86-64 and ARM64 architectures.
- Linux/macOS requires Bash and `curl`; Windows requires PowerShell 5.1+.
- CLI installs to `~/.huawei/bin`; configuration and state are stored in `~/.huawei/devbridge`.
- Never commit `~/.huawei/devbridge` to version control or share between users.
- **Dynamic command adaptation** — The `scripts/devbridge_cmd.sh` adaptation layer makes this skill compatible with any DevBridge CLI v0.2.x version by dynamically discovering supported flags via `--help`. No version pinning required.