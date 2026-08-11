# DevBridge REST API Reference

## API Overview

DevBridge provides a REST API for programmatic tunnel management. The API base URL is region-specific:

```
https://devbridge.<region>.myhuaweicloud.com/v1
```

## Authentication

All API requests require an IAM token in the `X-Auth-Token` header:

```http
GET /v1/tunnels HTTP/1.1
Host: devbridge.cn-north-4.myhuaweicloud.com
X-Auth-Token: <iam-token>
Content-Type: application/json
```

## API Endpoints

### Tunnels

#### Create Tunnel

```http
POST /v1/tunnels
```

**Request body:**

```json
{
  "name": "my-tunnel",
  "description": "Development tunnel",
  "expiration_hours": 24,
  "auto_delete": false
}
```

**Response (201 Created):**

```json
{
  "id": "<tunnelId>",
  "name": "my-tunnel",
  "description": "Development tunnel",
  "expiration_hours": 24,
  "tunnel_expiration": 1700000000,
  "port_count": 0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

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
GET /v1/tunnels
```

**Response (200 OK):**

```json
[
  {
    "id": "<tunnelId>",
    "name": "my-tunnel",
    "description": "Development tunnel",
    "expiration_hours": 24,
    "tunnel_expiration": 1700000000,
    "port_count": 2
  }
]
```

#### Get Tunnel Details

```http
GET /v1/tunnels/{tunnelId}
```

**Response (200 OK):**

```json
{
  "id": "<tunnelId>",
  "name": "my-tunnel",
  "description": "Development tunnel",
  "expiration_hours": 24,
  "tunnel_expiration": 1700000000,
  "port_count": 2,
  "ports": [
    {
      "port": 8080,
      "protocol": "http",
      "anonymous_access": "denied"
    }
  ],
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Tunnel

```http
PATCH /v1/tunnels/{tunnelId}
```

**Request body:**

```json
{
  "name": "updated-name",
  "description": "Updated description",
  "expiration_hours": 48
}
```

**Response (200 OK):** Updated tunnel object.

#### Delete Tunnel

```http
DELETE /v1/tunnels/{tunnelId}
```

**Response (204 No Content):** Empty body.

---

### Ports

#### Create Port

```http
POST /v1/tunnels/{tunnelId}/ports
```

**Request body:**

```json
{
  "port": 8080,
  "protocol": "http",
  "anonymous_access": "denied"
}
```

**Response (201 Created):**

```json
{
  "port": 8080,
  "protocol": "http",
  "anonymous_access": "denied",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List Ports

```http
GET /v1/tunnels/{tunnelId}/ports
```

**Response (200 OK):**

```json
[
  {
    "port": 8080,
    "protocol": "http",
    "anonymous_access": "denied"
  },
  {
    "port": 3000,
    "protocol": "https",
    "anonymous_access": "allowed"
  }
]
```

#### Get Port Details

```http
GET /v1/tunnels/{tunnelId}/ports/{portNumber}
```

#### Update Port

```http
PATCH /v1/tunnels/{tunnelId}/ports/{portNumber}
```

**Request body:**

```json
{
  "protocol": "https",
  "anonymous_access": "allowed"
}
```

#### Delete Port

```http
DELETE /v1/tunnels/{tunnelId}/ports/{portNumber}
```

**Response (204 No Content):** Empty body.

---

### Tokens

#### Issue Tunnel Token

```http
POST /v1/tunnels/{tunnelId}/tokens
```

**Request body:**

```json
{
  "scope": "host",
  "expiration_hours": 1
}
```

**Response (201 Created):**

```json
{
  "token": "<token-value>",
  "scope": "host",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

---

### Host & Connect

#### Start Host

```http
POST /v1/tunnels/{tunnelId}/host
```

**Request body:**

```json
{
  "port": 8080,
  "log_level": "info"
}
```

**Response (200 OK):**

```json
{
  "address": "https://<tunnelId>-<port>.<region>-bridge.myhuaweicloud.com",
  "port": 8080,
  "status": "running"
}
```

#### Start Connect

```http
POST /v1/tunnels/{tunnelId}/connect
```

**Request body:**

```json
{
  "port": 8080,
  "local_port": 8080
}
```

**Response (200 OK):**

```json
{
  "local_port": 8080,
  "remote_port": 8080,
  "status": "connected"
}
```

---

## Error Responses

All errors use a consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Tunnel <tunnelId> not found",
    "request_id": "<requestId>"
  }
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|-----------|-------------|
| 400 | INVALID_REQUEST | Invalid request body or parameters |
| 401 | UNAUTHORIZED | Missing or invalid IAM token |
| 403 | FORBIDDEN | Insufficient IAM permissions |
| 404 | RESOURCE_NOT_FOUND | Tunnel or port not found |
| 409 | CONFLICT | Duplicate resource (e.g., port already exists) |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server-side error |

## Rate Limits

| Resource | Limit |
|----------|-------|
| Create tunnel | 10 per minute |
| List tunnels | 60 per minute |
| Create port | 20 per minute |
| Host/Connect | 5 per minute |
| Other operations | 60 per minute |

Rate limit headers:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1700000060
```
