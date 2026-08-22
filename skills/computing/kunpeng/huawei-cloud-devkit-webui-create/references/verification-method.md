# Verification Method - Kunpeng DevKit WebUI Mode Installation

This document describes how to verify a successful DevKit installation.

## Table of Contents

- [1. hcloud CLI Verification](#1-hcloud-cli-verification)
- [2. ECS Creation Verification](#2-ecs-creation-verification)
- [3. Service Status Verification](#3-service-status-verification)
- [4. Port Listening Verification](#4-port-listening-verification)
- [5. Installation Directory Verification](#5-installation-directory-verification)
- [6. Plugin Installation Verification](#6-plugin-installation-verification)
- [7. WebUI Access Verification](#7-webui-access-verification)
- [8. End-to-End Verification Script](#8-end-to-end-verification-script)

---

## 1. hcloud CLI Verification

```bash
# Version check
hcloud version
# Expected: >= 3.2.0

# Configuration check
hcloud configure list
# Expected: Contains valid AK/SK

# API connectivity
hcloud ECS ListServersDetails --cli-region=cn-north-4
# Expected: Returns ECS list (may be empty)
```

---

## 2. ECS Creation Verification

```bash
# Check ECS status
hcloud ECS ShowServer --cli-region=$REGION --server_id=$SERVER_ID

# Verify architecture is aarch64
hcloud ECS ShowServer --cli-region=$REGION --server_id=$SERVER_ID | grep "os_ext_arch"

# Verify flavor is Kunpeng
hcloud ECS ShowServer --cli-region=$REGION --server_id=$SERVER_ID | grep "flavor"

# Verify EIP (if bound)
hcloud EIP ShowPublicip --cli-region=$REGION --publicip_id=$EIP_ID
```

---

## 3. Service Status Verification

```bash
systemctl status devkit_nginx --no-pager
# Expected: Active: active (running)

systemctl status gunicorn_framework --no-pager
# Expected: Active: active (running)

systemctl status gunicorn_plugin --no-pager
# Expected: Active: active (running)
```

**Success Criteria**: All three services must be `active (running)`.

---

## 4. Port Listening Verification

```bash
ss -tlnp | grep -E "8086|8002|5001|7996"
```

**Expected Output**:

| Port | Bind Address | Process |
|------|-------------|---------|
| 8086 | `<Server IP>` | nginx |
| 8002 | 127.0.0.1 | nginx |
| 7996 | 127.0.0.1 | gunicorn |
| 50051 | `<Server IP>` | grpc (started on demand; automatically listens when user launches performance analysis or similar tasks from WebUI) |

---

## 5. Installation Directory Verification

```bash
ls -la /opt/DevKit/
```

**Expected Subdirectories**:

| Directory | Description |
|-----------|-------------|
| config | Configuration files |
| devkitframework | Framework code |
| devkitplugins | Plugin code |
| tools | Toolset |
| rsa | Certificates |
| logs | Logs |
| workspace | Workspace |

---

## 6. Plugin Installation Verification

```bash
ls /opt/DevKit/devkitplugins/
```

**Expected Plugin Directories**:

| Plugin | Directory Name |
|--------|---------------|
| Code Migration Advisor | porting |
| Affinity Analyzer | affinity |
| Development Toolkit | devtools |
| Debugger | debugger |
| System Performance Optimization | sys_perf |
| Java Performance Optimization | java_perf |
| System Diagnosis | sys_diagnosis |

---

## 7. WebUI Access Verification

```bash
# Local curl verification of HTTPS port
curl -k https://localhost:8086 -I
# Expected: HTTP/1.1 302 or 200

# Verify certificate
openssl s_client -connect localhost:8086 -showcerts < /dev/null 2>/dev/null | head -10
```

**Browser Access**: `https://<Server IP>:8086`

---

## 8. End-to-End Verification Script

```bash
#!/bin/bash
SERVER_IP="${1:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [[ "$result" == "ok" ]]; then
        echo "  ✅ ${desc}"
        ((PASS++))
    else
        echo "  ❌ ${desc}"
        ((FAIL++))
    fi
}

echo "=== Kunpeng DevKit Installation Verification ==="

echo ""
echo "[1] Service Status"
for svc in devkit_nginx gunicorn_framework gunicorn_plugin; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "unknown")
    check "$svc" "$([ "$status" == "active" ] && echo ok || echo fail)"
done

echo ""
echo "[2] Port Listening"
for port in 8086 8002 7996 50051; do
    result=$(ss -tlnp 2>/dev/null | grep -q ":${port} " && echo ok || echo fail)
    check "Port $port" "$result"
done

echo ""
echo "[3] Installation Directory"
check "/opt/DevKit/" "$([ -d /opt/DevKit/devkitframework ] && echo ok || echo fail)"

echo ""
echo "[4] Plugin List"
for plugin in porting affinity devtools debugger sys_perf java_perf sys_diagnosis; do
    check "$plugin" "$([ -d /opt/DevKit/devkitplugins/$plugin ] && echo ok || echo fail)"
done

echo ""
echo "[5] WebUI Access"
http_code=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:8086 2>/dev/null || echo "000")
check "WebUI (HTTP $http_code)" "$([ "$http_code" == "200" ] || [ "$http_code" == "302" ] && echo ok || echo fail)"

echo ""
echo "========================================="
echo "  Passed: ${PASS}  Failed: ${FAIL}"
if [[ ${FAIL} -eq 0 ]]; then
    echo "  Access URL: https://${SERVER_IP}:8086"
fi
echo "========================================="
```
