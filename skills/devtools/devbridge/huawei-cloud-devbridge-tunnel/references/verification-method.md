# Verification Method

This document provides step-by-step verification procedures for DevBridge CLI (v0.2.x) installation, authentication, tunnel creation, port management, and host/connect functionality.

## Verification Checklist

| # | Verification Item | Command | Expected Result |
|---|------------------|---------|-----------------|
| 1 | CLI installation (v0.2.x) | `devbridge version` | Displays version 0.2.x |
| 2 | Authentication | `devbridge auth status` | Shows logged-in status |
| 3 | Tunnel creation | `devbridge create test-tunnel -e 1` | Returns tunnel ID |
| 4 | Tunnel list | `devbridge list` | Shows test tunnel |
| 5 | Port creation (deny anon default) | `devbridge port create <id> -p 8080 --protocol auto` | Port created successfully |
| 6 | Port list | `devbridge port list <id>` | Lists port 8080 |
| 7 | Limits | `devbridge limits` | Shows quota/usage |
| 8 | Host | `devbridge host <id>` | Host running, displays new-format address |
| 9 | Connect | `devbridge connect <id>` | Local port mapping established |
| 10 | Cleanup | `devbridge delete <id>` | Tunnel deleted |

## Step 1: Verify CLI Installation

```bash
devbridge version
```

**✅ Correct output:**

```text
0.2.2-release
```

**❌ Incorrect output (not installed):**

```text
command not found: devbridge
```

**❌ Incorrect output (old version):**

```text
0.1.x-...
```

> v0.1.x clients can no longer connect after the 2026-09-20 domain switch. Upgrade to v0.2.x via the official installer (see [CLI Installation Guide](cli-installation-guide.md)).

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
```

**Expected output (not logged in):**

```text
Not logged in. Run 'devbridge auth login' to authenticate.
```

**If not logged in:**

```bash
# Personal: interactive login
devbridge auth login

# Automation: API Key login
export HW_API_KEY="<your-api-key>"
devbridge auth login --api-key "$HW_API_KEY"
```

## Step 3: Verify Tunnel Creation

```bash
devbridge create verify-test -d "验证测试隧道" -e 1
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
- Check quota: `devbridge limits`.
- Check network connectivity: `devbridge ping <uri>`.

## Step 4: Verify Tunnel List

```bash
devbridge list
```

**Expected output:**

```text
Tunnel ID    Name          Description                   Tunnel Expiration    Port Count
<tunnelId>   verify-test   验证测试隧道                  1 hours              0
```

> v0.2.x removed the `--json` output flag from `list`. Use the text table; parse with `awk`/`grep` if needed.

## Step 5: Verify Port Creation

```bash
devbridge port create <tunnelId> -p 8080 --protocol auto
```

Port protocol defaults to `auto`; anonymous access defaults to **deny** (do not pass `-a` unless you explicitly want anonymous access).

**Expected output:**

```text
Port added: TunnelId=<tunnelId>, Port=8080
```

To allow anonymous access (only for explicitly public content):

```bash
devbridge port create <tunnelId> -p 8081 --protocol http -a
```

## Step 6: Verify Port List

```bash
devbridge port list <tunnelId>
```

**Expected output:**

```text
Port    Protocol    Anonymous Access
8080    auto        denied
```

## Step 7: Verify Limits

```bash
devbridge limits
```

**Expected output:** quota and usage info (traffic quota/usage, tunnel limits, bandwidth limits, rate limits).

## Step 8: Verify Host

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
Tunnel URL: https://<tunnelId>.<clusterId>.myhuaweicloud.com
Ready to accept connections
Auto reconnect: enabled
```

**Verification:**
- Access the tunnel URL from a browser (behavior depends on the port's anonymous policy).
- The URL should use the **new cluster domain** (e.g. `*.devbridge-s2.hwtunnel.com`), never the old `cn-north-4-bridge` domain.

## Step 9: Verify Connect

On another device with DevBridge CLI installed and authenticated:

```bash
devbridge connect <tunnelId>
```

**Expected output:**

```text
Connecting to tunnel <tunnelId>...
Forwarding localhost:8080 -> tunnel port: 8080

Connect is running. Press Ctrl+C to stop.
```

**Verification:**
- Access `http://localhost:8080` on the remote device.
- Should return the hosted service's response.

## Step 10: Cleanup

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
devbridge port create "$TUNNEL_ID" -p 8080 --protocol auto

echo "=== Step 6: Port List ==="
devbridge port list "$TUNNEL_ID"

echo "=== Step 7: Limits ==="
devbridge limits

echo "=== Step 10: Cleanup ==="
devbridge delete "$TUNNEL_ID"

echo "=== Verification Complete ==="
```