# Verification Method

This document provides step-by-step verification procedures for DevBridge CLI installation, authentication, tunnel creation, port management, and host/connect functionality.

## Verification Checklist

| # | Verification Item | Command | Expected Result |
|---|------------------|---------|-----------------|
| 1 | CLI installation | `devbridge version` | Displays version number |
| 2 | Authentication | `devbridge auth status` | Shows logged-in status |
| 3 | Tunnel creation | `devbridge create test-tunnel` | Returns tunnel ID |
| 4 | Tunnel list | `devbridge list` | Shows test tunnel |
| 5 | Port creation | `devbridge port create <id> -p 8080` | Port created successfully |
| 6 | Port list | `devbridge port list <id>` | Lists port 8080 |
| 7 | Host | `devbridge host <id>` | Host running, displays address |
| 8 | Connect | `devbridge connect <id>` | Local port mapping established |
| 9 | Cleanup | `devbridge delete <id>` | Tunnel deleted |

## Step 1: Verify CLI Installation

```bash
devbridge version
```

**✅ Correct output:**

```text
0.1.12-release
```

**❌ Incorrect output (not installed):**

```text
command not found: devbridge
```

**If failed:**
- Check if `~/.huawei/bin/devbridge` exists.
- Verify PATH includes `~/.huawei/bin`.
- Refer to [CLI Installation Guide](cli-installation-guide.md) for troubleshooting.

## Step 2: Verify Authentication

```bash
devbridge auth status
```

**Expected output (logged in):**

```text
Logged in as: <account>
Region: <region>
```

**Expected output (not logged in):**

```text
Not logged in. Run 'devbridge auth login' to authenticate.
```

**If not logged in:**

```bash
devbridge auth login
```

## Step 3: Verify Tunnel Creation

```bash
devbridge create verify-test -d "Verification test tunnel" -e 1
```

**Expected output:**

```text
Tunnel ID:            <tunnelId>
Name:                 verify-test
Description:          验证测试隧道
Tunnel Expiration:    1 hours
```

**If failed:**
- Verify authentication status (Step 2).
- Check IAM permissions (see [IAM Policies](iam-policies.md)).
- Check network connectivity.

## Step 4: Verify Tunnel List

```bash
devbridge list
```

**Expected output:**

```text
Tunnel ID    Name          Description                  Expires
<tunnelId>   verify-test   Verification test tunnel      <timestamp>
```

**JSON format:**

```bash
devbridge list -j
```

```json
[
  {
    "id": "<tunnelId>",
    "name": "verify-test",
    "description": "Verification test tunnel",
    "expiration_hours": 1,
    "tunnel_expiration": <epoch>,
    "port_count": 0
  }
]
```

## Step 5: Verify Port Creation

```bash
devbridge port create <tunnelId> -p 8080 --protocol http
```

**Expected output:**

```text
Port added: TunnelId=<tunnelId>, Port=8080
```

## Step 6: Verify Port List

```bash
devbridge port list <tunnelId>
```

**Expected output:**

```text
Port    Protocol    Anonymous Access
8080    http        denied
```

## Step 7: Verify Host

Start a local service in one terminal:

```bash
python3 -m http.server 8080
```

Host the tunnel in another terminal:

```bash
devbridge host <tunnelId>
```

**Expected output:**

```text
Hosting port: 8080
Tunnel URL: https://<tunnelId>-8080.cn-north-4-bridge.myhuaweicloud.com
Ready to accept connections
Auto reconnect: enabled
```

**Verification:**
- Access `https://<tunnelId>-8080.cn-north-4-bridge.myhuaweicloud.com` from a browser.
- Should return the local service's response.

## Step 8: Verify Connect

On another device with DevBridge CLI installed and authenticated:

```bash
devbridge connect <tunnelId>
```

**Expected output:**

```text
Connecting to tunnel <tunnelId>...
Local port mapping established: localhost:8080 -> tunnel port 8080

Connect is running. Press Ctrl+C to stop.
```

**Verification:**
- Access `http://localhost:8080` on the remote device.
- Should return the hosted service's response.

## Step 9: Cleanup

Stop Host and Connect processes with `Ctrl+C`.

Delete the test tunnel:

```bash
devbridge delete <tunnelId>
```

**Expected output:**

```text
Tunnel <tunnelId> deleted.
```

Verify deletion:

```bash
devbridge list
```

The test tunnel should no longer appear in the list.

## Complete Verification Script

```bash
#!/bin/bash
set -e

echo "=== Step 1: CLI Installation ==="
devbridge version

echo "=== Step 2: Authentication ==="
devbridge auth status

echo "=== Step 3: Tunnel Creation ==="
TUNNEL_OUTPUT=$(devbridge create verify-test -d "验证测试" -e 1)
echo "$TUNNEL_OUTPUT"
TUNNEL_ID=$(echo "$TUNNEL_OUTPUT" | grep "Tunnel ID" | awk '{print $3}')
echo "Tunnel ID: $TUNNEL_ID"

echo "=== Step 4: Tunnel List ==="
devbridge list

echo "=== Step 5: Port Creation ==="
devbridge port create "$TUNNEL_ID" -p 8080 --protocol http

echo "=== Step 6: Port List ==="
devbridge port list "$TUNNEL_ID"

echo "=== Step 9: Cleanup ==="
devbridge delete "$TUNNEL_ID"

echo "=== Verification Complete ==="
```
