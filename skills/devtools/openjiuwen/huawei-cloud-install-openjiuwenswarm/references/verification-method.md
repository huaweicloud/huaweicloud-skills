# Verification Method

## Overview

This document describes the verification steps and methods for the deployment results.

## Verification Steps

### Step 1: Check Service Processes

```bash
ps aux | grep jiuwenswarm
```

Expected Result: jiuwenswarm-related processes should be running.

### Step 2: Check Port Status

```bash
ss -tlnp | grep python
```

Expected Result: JiuwenSwarm service processes should be listening on local ports (check `.env` for specific port values).

### Step 3: Check .env File

```bash
cat /root/.jiuwenswarm/config/.env
```

Expected Result: The file should exist and contain the correct configuration entries.

### Step 4: Access Web Interface

Access in a browser:
```
https://{WEB_PORT}-{devenvd_id}.workspace.developer.huaweicloud.com
```
Replace `{WEB_PORT}` with the value from `.env` (`/root/.jiuwenswarm/config/.env`), and `{devenvd_id}` with the container ID from `$DEVENVD_ID`.

### Step 5: Check Logs

```bash
tail -f /tmp/jiuwenswarm.log
```

Expected Result: There should be no ERROR-level errors in the logs.

## Verification Script

The following script can be used for one-click verification:

```bash
#!/bin/bash

echo "=== JiuwenSwarm Deployment Verification ==="

# Source .env for dynamic port values
ENV_FILE="/root/.jiuwenswarm/config/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi
WEB_PORT=${WEB_PORT:-5173}
GATEWAY_PORT=${GATEWAY_PORT:-19001}
TUI_PORT=${TUI_PORT:-19000}
AGENT_PORT=${AGENT_PORT:-18092}

echo ""
echo "[1/5] Checking service processes..."
ps aux | grep jiuwenswarm | grep -v grep > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Service process is running"
else
    echo "❌ Service process is not running"
    exit 1
fi

echo ""
echo "[2/5] Checking port status..."
for port in $WEB_PORT $GATEWAY_PORT $TUI_PORT $AGENT_PORT; do
    ss -tlnp | grep ":$port" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Port $port is ready"
    else
        echo "❌ Port $port is not ready"
        exit 1
    fi
done

echo ""
echo "[3/5] Checking .env file..."
if [ -f "$ENV_FILE" ]; then
    echo "✅ .env file exists"
else
    echo "❌ .env file does not exist"
    exit 1
fi

echo ""
echo "[4/5] Checking deployment directory..."
if [ -d "/root/tools/jiuwenswarm/jiuwenswarm_runtime/python/bin" ]; then
    echo "✅ Deployment directory exists"
else
    echo "❌ Deployment directory does not exist"
    exit 1
fi

echo ""
echo "[5/5] Verification completed"
echo ""
echo "🎉 JiuwenSwarm deployment verification passed!"
echo "Access URL: https://${WEB_PORT}-${DEVENVD_ID:-unknown}.workspace.developer.huaweicloud.com"
```

## Troubleshooting

| Issue | Check Method | Solution |
|-------|-------------|----------|
| Port not ready | `ss -tlnp` to check port status | Wait for service to start or check logs |
| Service process missing | `ps aux | grep jiuwenswarm` | Re-run install phase scripts |
| .env file missing | `cat /root/.jiuwenswarm/config/.env` | Check if configuration steps executed successfully |
| Web access failure | Check browser console errors | Verify network connection and port configuration |