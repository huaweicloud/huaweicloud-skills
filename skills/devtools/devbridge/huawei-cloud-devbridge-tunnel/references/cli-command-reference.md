# DevBridge CLI Command Reference

This document provides a complete reference for all DevBridge CLI commands (v0.2.x), including command structure, flags, and usage examples. Use this as a lookup when constructing DevBridge commands.

## Command Structure

```
devbridge [command] [subcommand] [flags]
```

## Global Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-h, --help` | Show help | - |
| `-v, --verbose` | Enable debug logging | false |

> **Removed**: `-j/--json` global flag, `--region`, `--debug`, `-j` on `list`/`port list`, AK/SK flags (`--access-key`, `--secret-key`, `--security-token`), `--huaweicloud`, `loginType`.

## Commands

### `auth` — Authentication Management

#### `devbridge auth login`

Log in to DevBridge.

```bash
# Interactive login (browser)
devbridge auth login

# API Key login
devbridge auth login --api-key <key>

# API Key via environment variable
export HW_API_KEY="<your-api-key>"
devbridge auth login
```

| Flag | Description | Required |
|------|-------------|----------|
| `--api-key` | API Key | No (alternative to interactive) |

> **v0.2.x change**: AK/SK login (`--access-key`, `--secret-key`, `--security-token`) has been removed. Use API Key or interactive login. API Keys are managed at `https://devstation.connect.huaweicloud.com/space/devbridge/apikey`.

#### `devbridge auth status`

Check current authentication status.

```bash
devbridge auth status
```

#### `devbridge auth logout`

Log out and clear local credentials.

```bash
devbridge auth logout
```

---

### `create` — Create Tunnel

Create a new DevBridge tunnel.

```bash
devbridge create <name> [flags]
```

| Flag | Description | Default | Required |
|------|-------------|---------|----------|
| `-d, --description` | Tunnel description (Chinese chars, digits, letters only, max 64) | - | No |
| `-e, --expiration` | Expiration in hours | 72 | No |

**Example:**

```bash
devbridge create my-tunnel -d "开发隧道" -e 48
```

**✅ Correct usage:**

```bash
# Description with Chinese characters, digits, and letters (no spaces)
devbridge create my-tunnel -d "前端开发环境" -e 8
```

**❌ Incorrect usage:**

```bash
# Error: description contains spaces (not allowed)
devbridge create my-tunnel -d "frontend dev env" -e 8
```

**Output:**

```text
Tunnel ID:            <tunnelId>
Name:                 my-tunnel
Description:          前端开发环境
Tunnel Expiration:    72 hours
```

---

### `list` — List Tunnels

List all active tunnels for the current workspace. v0.2.x has **no `--json` flag** — output is a text table.

```bash
devbridge list
```

**Output:**

```text
Tunnel ID  Name             Description  Tunnel Expiration  Port Count
dwskt2pg   dev-tunnel-5941  开发隧道     3 days             1
```

---

### `show` — Show Tunnel Details

Display detailed information about a specific tunnel.

```bash
devbridge show <tunnelId>
```

Includes tunnel ID, name, description, expiration, Host/Connect connection counts, and upload/download traffic statistics.

---

### `update` — Update Tunnel

Update tunnel properties.

```bash
devbridge update <tunnelId> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-n, --name` | New tunnel name | - |
| `-d, --description` | New description | - |
| `-e, --expiration` | New expiration (hours) | - |

**Example:**

```bash
devbridge update abc123 -n new-name -d "Updated description" -e 48
```

---

### `delete` — Delete Tunnel

Delete a tunnel and all its ports.

```bash
devbridge delete <tunnelId>
```

### `delete-all` — Delete All Tunnels

Delete all tunnels in the current workspace.

```bash
devbridge delete-all
```

---

### `port` — Port Management

#### `devbridge port create`

Add a port to an existing tunnel. **Anonymous access is denied by default**.

```bash
devbridge port create <tunnelId> [flags]
```

| Flag | Description | Default | Required |
|------|-------------|---------|----------|
| `-p, --port-number` | Port number | - | Yes |
| `--protocol` | Protocol: `http`, `https`, `auto` | auto | No |
| `-a, --allow-anonymous` | Allow anonymous access | false | No |
| `--deny-anonymous` | Deny anonymous access | default | No |

**Example:**

```bash
# Deny anonymous access (default)
devbridge port create abc123 -p 8080 --protocol http

# Allow anonymous access
devbridge port create abc123 -p 8080 --protocol http -a

# Default auto protocol
devbridge port create abc123 -p 3000
```

#### `devbridge port list`

List all ports for a tunnel (no JSON flag in v0.2.x).

```bash
devbridge port list <tunnelId>
```

#### `devbridge port show`

Show details of a specific port.

```bash
devbridge port show <tunnelId> -p <portNumber>
```

#### `devbridge port update`

Update a port's anonymous access policy. **Cannot change protocol — delete and recreate.**

```bash
devbridge port update <tunnelId> -p <portNumber> [flags]
```

| Flag | Description |
|------|-------------|
| `-a, --allow-anonymous` | Allow anonymous access |
| `--deny-anonymous` | Deny anonymous access |

#### `devbridge port delete`

Remove a port from a tunnel.

```bash
devbridge port delete <tunnelId> -p <portNumber>
```

---

### `host` — Host Local Service

Start hosting local service through a tunnel. Runs in the foreground; supports auto-reconnect.

```bash
devbridge host <tunnelId> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-p, --ports` | Local port(s) to host (`-1` = all configured ports) | All ports |
| `-d, --description` | Description when creating a temp tunnel | - |
| `-e, --expiration` | Expiration when creating a temp tunnel (hours) | 72 |
| `-k, --api-key` | Use API Key auth (skip token issuance) | - |
| `-t, --token` | Use JWT token auth (skip API and port lookup) | - |

**Example:**

```bash
# Host all ports of an existing tunnel
devbridge host abc123

# Create a temporary tunnel and host port 8080 immediately (expires in 8h)
devbridge host -p 8080 -d "隧道描述" -e 8

# Host with API Key auth
devbridge host abc123 --api-key <key>
```

**Output:**

```text
Hosting port: 8080
Tunnel URL: https://<tunnelId>.<clusterId>.myhuaweicloud.com
Ready to accept connections
Auto reconnect: enabled
```

---

### `connect` — Connect to Tunnel

Connect to a tunnel from a remote device, establishing local port mapping. Runs in the foreground.

```bash
devbridge connect <tunnelId> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-k, --api-key` | Use API Key auth (skip token issuance) | - |
| `-t, --token` | Use JWT token auth | - |

**Example:**

```bash
devbridge connect abc123
devbridge connect abc123 --api-key <key>
```

**Output:**

```text
Connecting to tunnel abc123...
Forwarding localhost:8080 -> tunnel port: 8080
```

---

### `token` — Issue Tunnel Token

Issue an access token for a tunnel.

```bash
devbridge token <tunnelId> [flags]
```

| Flag | Description | Default | Required |
|------|-------------|---------|----------|
| `-s, --scope` | Token scope: `host`, `connect` | - | Yes |

**Example:**

```bash
devbridge token abc123 -s host
devbridge token abc123 -s connect
```

---

### `limits` — Quota and Balance

Show account quota and current usage.

```bash
devbridge limits
```

Output includes reset time, traffic quota/usage, active tunnel count, limits for tunnels/ports/Host, tunnel bandwidth, single-port HTTP request rate, single-port connection count.

---

### `echo` — Diagnostic Echo Service

Start an HTTP echo service to verify tunnel links.

```bash
devbridge echo [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-p, --port` | Listen port | Random |
| `-i, --interface` | Listen interface | 127.0.0.1 |

---

### `ping` — Connectivity Test

Send HTTP ping to a URI.

```bash
devbridge ping <uri> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-i, --interval` | Interval between messages (ms) | 1000 |

**Example:**

```bash
devbridge ping https://<tunnelId>.<clusterId>.myhuaweicloud.com
# HTTP 200 OK -- 4 ms
```

---

### `set` / `unset` — Default Tunnel

Save or clear the default tunnel for this machine.

```bash
devbridge set <tunnelId>
devbridge unset
```

---

### `version` — Show Version

```bash
devbridge version
```

---

### `completion` — Shell Completion

Generate shell completion script.

```bash
devbridge completion bash    # Bash
devbridge completion zsh     # Zsh
devbridge completion fish    # Fish
devbridge completion powershell  # PowerShell
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error — inspect command output for details |

## Version-Specific Notes (v0.2.x)

- Authentication uses **API Key** (`--api-key` / `HW_API_KEY`) or interactive login; **AK/SK is removed**.
- Tunnel domain switched 2026-09-20: old `*.cn-north-4-bridge.myhuaweicloud.com` no longer works; use v0.2.x client and recreate tunnels.
- `list` and `port list` no longer support `--json` output.
- `host`/`connect` support `--api-key`/`-k` to skip token issuance and `--token`/`-t` for explicit JWT.
- Port protocol default is `auto`; anonymous access default is **deny**.