# DevBridge REST API Reference

## API Overview

DevBridge provides a REST API for programmatic tunnel management. The public API service base URL (v1) is:

```
https://hdspace-partner.cn-north-4.myhuaweicloud.com/open-api-public/v1/relay
```

> **Response envelope**: all responses wrap the payload in `{error_code, error_msg, result}`. Success code is `0000`.

## Authentication

Authenticate with an **API Key** (AK/SK is no longer supported in v0.2.x):

```http
GET /open-api-public/v1/relay/tunnels HTTP/1.1
Host: hdspace-partner.cn-north-4.myhuaweicloud.com
X-Api-Key: <api-key>
Content-Type: application/json
```

Create and manage API Keys at `https://devstation.connect.huaweicloud.com/space/devbridge/apikey`.

## Response Envelope

```json
{
  "error_code": "0000",
  "error_msg": "success",
  "result": { }
}
```

| Field | Description |
|-------|-------------|
| `error_code` | `0000` = success; non-zero = error code (e.g. `HD.98310001`, `HD.98300005`, `HD.98320078`) |
| `error_msg` | Human-readable message |
| `result` | Operation payload (depends on endpoint) |

## API Endpoints

> The exact request/response schemas below reflect the CLI behavior documented for v0.2.x; verify field names against the live API (CLI source or `devbridge -v` debug logs) before building integrations.

### Tunnels

#### Create Tunnel

```http
POST /open-api-public/v1/relay/tunnels
```

**Request body:**

```json
{
  "name": "my-tunnel",
  "description": "Development tunnel",
  "expiration_hours": 72
}
```

**Response (result):** tunnel ID, name, description, expiration.

**✅ Correct request (valid name and description):**

```json
{
  "name": "my-tunnel",
  "description": "前端开发环境",
  "expiration_hours": 8
}
```

**❌ Incorrect request (spaces in description):**

```json
{
  "name": "my-tunnel",
  "description": "frontend dev env",
  "expiration_hours": 8
}
```

#### List Tunnels

```http
GET /open-api-public/v1/relay/tunnels
```

**Response (result):** list of tunnels (ID, name, description, expiration, port count).

#### Get Tunnel Details

```http
GET /open-api-public/v1/relay/tunnels/{tunnelId}
```

**Response (result):** tunnel details including ports, connection counts, and traffic stats.

#### Update Tunnel

```http
PATCH /open-api-public/v1/relay/tunnels/{tunnelId}
```

**Request body:**

```json
{
  "name": "updated-name",
  "description": "Updated description",
  "expiration_hours": 48
}
```

#### Delete Tunnel

```http
DELETE /open-api-public/v1/relay/tunnels/{tunnelId}
```

### Ports

#### Create Port

```http
POST /open-api-public/v1/relay/tunnels/{tunnelId}/ports
```

**Request body:**

```json
{
  "port": 8080,
  "protocol": "auto",
  "anonymous_access": "denied"
}
```

Protocol: `http`, `https`, `auto` (default `auto`). Anonymous access defaults to `denied`; use `allowed` only for explicitly public content.

#### List Ports

```http
GET /open-api-public/v1/relay/tunnels/{tunnelId}/ports
```

#### Get Port Details

```http
GET /open-api-public/v1/relay/tunnels/{tunnelId}/ports/{portNumber}
```

#### Update Port

```http
PATCH /open-api-public/v1/relay/tunnels/{tunnelId}/ports/{portNumber}
```

**Request body:**

```json
{
  "anonymous_access": "allowed"
}
```

> Protocol cannot be changed in place — delete and recreate the port.

#### Delete Port

```http
DELETE /open-api-public/v1/relay/tunnels/{tunnelId}/ports/{portNumber}
```

### Tokens

#### Issue Tunnel Token

```http
POST /open-api-public/v1/relay/tunnels/{tunnelId}/tokens
```

**Request body:**

```json
{
  "scope": "host"
}
```

Scope: `host` or `connect`. Tokens have a fixed short lifetime.

## Error Codes

Errors use the outer envelope with non-zero `error_code`. Known codes (from changelog):

| Code | Description |
|------|-------------|
| `0000` | Success |
| `HD.98310001` | Check the error message and handle accordingly |
| `HD.98300005` | Check the error message and handle accordingly |
| `HD.98320078` | Check the error message and handle accordingly |

Verify full code semantics against the live API / error message text before building automations.

## Host & Connect via API

Programmatic Host/Connect is normally done through the CLI (`devbridge host` / `devbridge connect`). The CLI supports:

- `--api-key` / `-k` — API Key auth, skip Token issuance
- `--token` / `-t` — JWT token auth, skip API and port lookup (tunnel ID required)

For detailed behavior, see [cli-command-reference.md](cli-command-reference.md).