# Verification Method

## Overview

This document describes how to verify the successful deployment of DeepSeek Harness (dsh) on Huawei Cloud Flexus X instances.

Deployment topology:
```
Local machine (ssh -L 3080:127.0.0.1:3080 root@<public_ip>)
    -> SSH tunnel (port 22) -> dsh web (127.0.0.1:3080, systemd service 'dsh')
```

**Important:** dsh web intentionally binds to 127.0.0.1 only (the CLI rejects `--host 0.0.0.0`). Remote access goes through an **SSH local port-forwarding tunnel** — the security group only needs port 22 open for your IP. Ports 80/3080 are never exposed publicly.

## Prerequisites

Before verification, ensure you have:
1. Completed deployment using the skill
2. Configured the security group rule (TCP 22 from your IP)
3. Recorded the public IP address of the deployed server

## Verification Steps

### Step 1: Verify Server Status

Check if the ECS instance is in ACTIVE state:

✅ **Correct Example**:
```bash
# Use the skill's built-in status check
python3 deploy_dsh.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --region cn-north-4 \
  --status <server_id_or_name>

# Or use Huawei Cloud CLI
hcloud ECS ListServers --cli-region=cn-north-4 --limit=10

# Expected output should show:
# "status": "ACTIVE"
```

Alternatively, check in Huawei Cloud console:
1. Navigate to ECS → Elastic Cloud Server
2. Verify the server status is "Running"

### Step 2: Verify Security Group Configuration

Ensure security group rules are correctly configured:

✅ **Correct Example**:
```bash
# Check security group rules
hcloud VPC ListSecurityGroupRules --cli-region=cn-north-4 --security-group-id sg-id

# Expected rules (added manually by user):
# - Port 22, source_ip: your_ip/32  <- REQUIRED for SSH tunnel
# (No port 80/443/3080 rules needed - dsh is accessed via SSH tunnel only)
```

❌ **Error Example**:
```bash
# DO NOT allow 0.0.0.0/0
# - Port 80, source_ip: 0.0.0.0/0  <- This is a security risk! dsh must not be public
# - Port 3080, source_ip: 0.0.0.0/0 <- This exposes dsh directly - forbidden!
```

### Step 3: SSH Access Verification

Verify SSH access to the server:

✅ **Correct Example**:
```bash
ssh root@<public_ip>

# Expected: Login successful with the root password
```

❌ **Error Example**:
```bash
ssh root@<public_ip>
# Connection refused - security group rules not configured
```

### Step 4: dsh Service Verification

#### 4.1 Check dsh systemd Service

✅ **Correct Example**:
```bash
# SSH into the server
ssh root@<public_ip>

# Check dsh service
systemctl status dsh

# Expected output:
# ● dsh.service - DeepSeek Harness (dsh) Web UI
#    Loaded: loaded (/etc/systemd/system/dsh.service; enabled; vendor preset: enabled)
#    Active: active (running) since Tue 2026-08-18 09:00:00 UTC; 5min ago
```

#### 4.2 Check dsh Loopback Port

✅ **Correct Example**:
```bash
# dsh binds to 127.0.0.1 only - verify loopback
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:3080

# Expected: HTTP 200 or 302 (dsh Web UI responding)
```

#### 4.3 Check Node.js and dsh Versions

✅ **Correct Example**:
```bash
node -v
# Expected: v22.x.x (Node.js 22 LTS)

dsh -V
# Expected: version information (e.g. 0.1.0-rc.7)
```

#### 4.4 Check dsh Logs

✅ **Correct Example**:
```bash
journalctl -u dsh -n 50 --no-pager

# Expected: No fatal errors, dsh started successfully
```

### Step 5: Nginx Reverse Proxy Verification

#### 5.1 Check Nginx Config

✅ **Correct Example**:
```bash
# SSH into the server
nginx -t
# Expected: syntax is ok / test is successful

systemctl status nginx
# Expected: active (running)
```

#### 5.2 Check Web UI via SSH Tunnel (Recommended Access)

✅ **Correct Example**:
```bash
# From your local machine - establish the SSH tunnel (keep window open)
ssh -L 3080:127.0.0.1:3080 root@<public_ip>

# In another terminal, verify the tunneled Web UI
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:3080

# Expected: HTTP 200 or 302 with dsh Web UI
```

Open `http://127.0.0.1:3080` in a browser (while the tunnel is active) — you should see the dsh Web UI.

> 💡 If local port 3080 is busy, use another local port, e.g. `ssh -L 18080:127.0.0.1:3080 root@<public_ip>` and open `http://127.0.0.1:18080`.

> 💡 macOS background tunnel: `ssh -f -N -L 3080:127.0.0.1:3080 root@<public_ip>`; close with `pkill -f "ssh -f -N"`.

### Step 6: Deployment Log Verification

✅ **Correct Example**:
```bash
# SSH into the server
cat /var/log/dsh-bootstrap.log

# Expected: All stages completed successfully
# ===== Stage 0: Configure Domestic Mirrors ===== -> OK
# ===== Stage 1: Install Node.js 22 LTS ===== -> OK
# ===== Stage 2: Install DeepSeek Harness (dsh) ===== -> OK
# ===== Stage 3: Dedicated Service User ===== -> OK
# ===== Stage 4: systemd Service ===== -> OK
# ===== Stage 5: Nginx Reverse Proxy ===== -> OK
# ===== Stage 6: Firewall ===== -> OK
# ===== Stage 7: Start & Verify ===== -> OK
# ✅ DEPLOYMENT SUCCESSFUL
```

### Step 7: dsh Web UI Functionality Verification

After establishing the SSH tunnel and opening the Web UI:

✅ **Correct Example**:
1. Establish tunnel: `ssh -L 3080:127.0.0.1:3080 root@<public_ip>` (keep window open)
2. Open `http://127.0.0.1:3080` in a browser
3. Navigate to **Settings → Models**
4. Enter your DeepSeek API key and save
5. Choose a workspace directory
6. Start a session — the harness should respond

## Automated Verification Script

Create a verification script to check all services at once:

✅ **Correct Example**:
```bash
#!/bin/bash

PUBLIC_IP="<your_public_ip>"
DSH_PORT="${DSH_PORT:-3080}"

echo "=== DeepSeek Harness (dsh) Deployment Verification ==="
echo ""

echo "[1] Checking SSH access..."
ssh -o ConnectTimeout=5 root@$PUBLIC_IP "echo SSH OK" 2>&1 | head -1

echo ""
echo "[2] Checking dsh service..."
ssh root@$PUBLIC_IP "systemctl is-active dsh"

echo ""
echo "[3] Checking dsh loopback port (127.0.0.1:$DSH_PORT)..."
ssh root@$PUBLIC_IP "curl -s -o /dev/null -w 'HTTP Status: %{http_code}\n' http://127.0.0.1:$DSH_PORT"

echo ""
echo "[4] Checking Node.js version..."
ssh root@$PUBLIC_IP "node -v"

echo ""
echo "[5] Checking dsh CLI version..."
ssh root@$PUBLIC_IP "dsh -V"

echo ""
echo "[6] Checking Web UI via SSH tunnel..."
ssh -N -L 3080:127.0.0.1:3080 root@$PUBLIC_IP &
TUNNEL_PID=$!
sleep 3
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:3080
kill $TUNNEL_PID 2>/dev/null

echo ""
echo "[7] Checking deployment log..."
ssh root@$PUBLIC_IP "grep -c 'DEPLOYMENT SUCCESSFUL' /var/log/dsh-bootstrap.log"

echo ""
echo "=== Verification Complete ==="
```

## Expected Results Summary

| Verification Item | Expected Result |
|-------------------|-----------------|
| Server Status | ACTIVE |
| Security Group | sg-dsh with rule TCP 22 from your_ip/32 only |
| SSH Access | Successful login |
| dsh Service | Active (running), enabled |
| dsh Loopback Port | HTTP 200/302 on 127.0.0.1:3080 (via SSH tunnel) |
| Nginx Config | syntax is ok (loopback only) |
| Web UI via SSH Tunnel | HTTP 200/302 on http://127.0.0.1:3080 |
| Node.js | v22.x.x |
| dsh CLI | version output (e.g. 0.1.0-rc.7) |
| Deployment Log | All stages completed, DEPLOYMENT SUCCESSFUL |

## Troubleshooting

### dsh Web UI Not Accessible

| Issue | Solution |
|-------|----------|
| Connection refused | 1) Ensure the SSH tunnel is running: `ssh -L 3080:127.0.0.1:3080 root@<public_ip>`; 2) Check security group rule allows port 22 from your IP |
| `bind: Address already in use` | Local port 3080 is busy — use another local port: `ssh -L 18080:127.0.0.1:3080 root@<public_ip>`, open `http://127.0.0.1:18080` |
| dsh service not running | Check service status: `systemctl status dsh`, logs: `journalctl -u dsh -n 50` |
| dsh failed to start | Check Node.js version: `node -v` (must be >= 22), check dsh binary: `command -v dsh` |
| Nginx not running | Check: `systemctl status nginx`, config: `nginx -t` (only needed for local loopback proxy) |
| Loopback not responding | Check: `curl http://127.0.0.1:3080`, restart: `systemctl restart dsh` |

### API Key Not Working in Web UI

| Issue | Solution |
|-------|----------|
| Key rejected | Verify the key is valid on DeepSeek platform |
| Pre-seeded key not picked up | Check drop-in: `cat /etc/systemd/system/dsh.service.d/10-credentials.conf` (mode 600), restart: `systemctl restart dsh` |
| Want to change key | Set it directly in Web UI: Settings → Models |

### Security Group Issues

| Issue | Solution |
|-------|----------|
| Cannot SSH | Ensure port 22 rule with your_ip/32 exists |
| Cannot access Web UI | Ensure the SSH tunnel is running (port 22 only is needed); do NOT open 80/3080 |
| 0.0.0.0/0 rule | Remove immediately and replace with your_ip/32 |
