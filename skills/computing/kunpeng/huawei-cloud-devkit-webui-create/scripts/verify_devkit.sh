#!/bin/bash
# Kunpeng DevKit WebUI Mode - Installation Verification Script
# Usage: bash verify_devkit.sh [server_ip]

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
for port in 8086 8002 7996; do
    result=$(ss -tlnp 2>/dev/null | grep -q ":${port} " && echo ok || echo fail)
    check "Port $port" "$result"
done
result_50051=$(ss -tlnp 2>/dev/null | grep -q ":50051 " && echo ok || echo fail)
if [[ "$result_50051" == "ok" ]]; then
    check "Port 50051 (gRPC)" "ok"
else
    echo "  ℹ️ Port 50051 (gRPC) not listening — This is normal; it starts automatically when users launch performance analysis tasks from WebUI"
fi

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
INTERNAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
webui_ok=fail
for target in localhost "${INTERNAL_IP}"; do
    [[ -z "$target" ]] && continue
    http_code=$(curl -k -s -o /dev/null -w "%{http_code}" "https://${target}:8086" 2>/dev/null || echo "000")
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "302" ]]; then
        webui_ok=ok
        echo "  ✅ WebUI via ${target} (HTTP $http_code)"
        break
    else
        echo "  ⚠️ WebUI via ${target} (HTTP $http_code)"
    fi
done
if [[ "$webui_ok" == "fail" ]]; then
    echo "  ❌ WebUI access failed on all endpoints"
    ((FAIL++))
else
    ((PASS++))
fi

echo ""
echo "========================================="
echo "  Passed: ${PASS}  Failed: ${FAIL}"
if [[ ${FAIL} -eq 0 ]]; then
    echo "  Access URL: https://${SERVER_IP}:8086"
fi
echo "========================================="
