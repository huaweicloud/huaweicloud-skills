# DevBridge CLI Command Reference

This document provides a complete reference for all DevBridge CLI commands, including command structure, flags, and usage examples. Use this as a lookup when constructing DevBridge commands.

## Command Structure

```
devbridge [command] [subcommand] [flags]
```

## Global Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-h, --help` | Show help | - |
| `-j, --json` | Output in JSON format | false |
| `-v, --verbose` | Verbose output | false |
| `--region` | Huawei Cloud region | From config |
| `--debug` | Debug mode | false |

## Commands

### `auth` — Authentication Management

#### `devbridge auth login`

Log in to Huawei Cloud.

```bash
# Interactive login (browser)
devbridge auth login

# AK/SK login
devbridge auth login --access-key <AK> --secret-key <SK>

# Temporary credentials (STS)
devbridge auth login --access-key <AK> --secret-key <SK> --security-token <TOKEN>
```

| Flag | Description | Required |
|------|-------------|----------|
| `--access-key` | Access Key ID | No |
| `--secret-key` | Secret Access Key | No |
| `--security-token` | Security token (STS) | No |

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
| `-e, --expiration` | Expiration in hours | 24 | No |
| `--auto-delete` | Auto-delete on expiration | false | No |

**Example:**

```bash
devbridge create my-tunnel -d "Development tunnel" -e 48
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
Description:          Development tunnel
Tunnel Expiration:    24 hours
```

---

### `list` — List Tunnels

List all tunnels for the current account.

```bash
devbridge list [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-j, --json` | JSON output | false |

**Example:**

```bash
devbridge list
devbridge list -j
```

---

### `show` — Show Tunnel Details

Display detailed information about a specific tunnel.

```bash
devbridge show <tunnelId>
```

**Example:**

```bash
devbridge show abc123
```

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
devbridge update abc123 -n new-name -d "Updated description"
```

---

### `delete` — Delete Tunnel

Delete a tunnel and all its ports.

```bash
devbridge delete <tunnelId>
```

**Example:**

```bash
devbridge delete abc123
```

---

### `port` — Port Management

#### `devbridge port create`

Add a port to an existing tunnel.

```bash
devbridge port create <tunnelId> [flags]
```

| Flag | Description | Default | Required |
|------|-------------|---------|----------|
| `-p, --port` | Port number | - | Yes |
| `--protocol` | Protocol: `http`, `https`, `tcp` | http | No |
| `--anonymous` | Allow anonymous access | false | No |

**Example:**

```bash
devbridge port create abc123 -p 8080 --protocol http
devbridge port create abc123 -p 3000 --protocol https --anonymous
```

#### `devbridge port list`

List all ports for a tunnel.

```bash
devbridge port list <tunnelId>
```

#### `devbridge port show`

Show details of a specific port.

```bash
devbridge port show <tunnelId> -p <portNumber>
```

#### `devbridge port update`

Update a port's configuration.

```bash
devbridge port update <tunnelId> -p <portNumber> [flags]
```

| Flag | Description |
|------|-------------|
| `--protocol` | New protocol |
| `--anonymous` | Enable/disable anonymous access |

#### `devbridge port delete`

Remove a port from a tunnel.

```bash
devbridge port delete <tunnelId> -p <portNumber>
```

---

### `host` — Host Local Service

Start hosting a local service through a tunnel.

```bash
devbridge host <tunnelId> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--port` | Specific port to host | All ports |
| `--log-level` | Log level: `debug`, `info`, `warn`, `error` | info |

**Example:**

```bash
devbridge host abc123
devbridge host abc123 --port 8080 --log-level debug
```

**Output:**

```text
Hosting port: 8080
Tunnel URL: https://<tunnelId>-8080.cn-north-4-bridge.myhuaweicloud.com
Ready to accept connections
Auto reconnect: enabled
```

---

### `connect` — Connect to Tunnel

Connect to a tunnel from a remote device, establishing local port mapping.

```bash
devbridge connect <tunnelId> [flags]
```

| Flag | Description | Default |
|------|-------------|---------|
| `--port` | Specific port to connect | All ports |
| `--local-port` | Local port to map to | Same as tunnel port |

**Example:**

```bash
devbridge connect abc123
devbridge connect abc123 --port 8080 --local-port 9090
```

---

### `token` — Issue Tunnel Token

Issue an access token for a tunnel (for programmatic access).

```bash
devbridge token <tunnelId> [flags]
```

| Flag | Description | Default | Required |
|------|-------------|---------|----------|
| `-s, --scope` | Token scope: `host`, `connect`, `admin` | - | Yes |
| `-e, --expiration` | Token expiration in hours | 24 | No |

**Example:**

```bash
devbridge token abc123 -s host -e 24
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
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Authentication error |
| 4 | Network error |
| 5 | Permission denied |
| 6 | Resource not found |
| 7 | Rate limited |
