#!/bin/bash
# ModelArts 健康检查脚本(startup/liveness/readiness 三类探针)
# 多节点场景按是否存在同目录 get_master_ip.py 自然区分

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PORT="${PORT:-8080}"
PROBE_TYPE="${1:-readiness}"   # startup / liveness / readiness

# vllm 的 OpenAI 兼容服务 /health 返回 200 OK 即健康
check_health() {
    local target_ip="127.0.0.1"
    # 多节点场景: 调用同目录 get_master_ip.py 取 master IP,探 master 的 /health
    if [ -f "${SCRIPT_DIR}/get_master_ip.py" ]; then
        target_ip=$(PYTHONUNBUFFERED=1 python3 "${SCRIPT_DIR}/get_master_ip.py" 2>/dev/null || echo "127.0.0.1")
    fi
    curl -sf --max-time 5 "http://${target_ip}:${PORT}/health" >/dev/null 2>&1
}

# vllm 进程存活检查(worker 与 startup/liveness 共用)
check_process() {
    pgrep -f "vllm serve" >/dev/null 2>&1 || pgrep -f "vllm.entrypoints.openai.api_server" >/dev/null 2>&1
}

case "${PROBE_TYPE}" in
    startup|liveness)
        # 启动初期与运行期均查进程,避免 /health 未就绪或偶发抖动杀实例
        check_process
        exit $?
        ;;
    readiness)
        # 单节点探本地 /health;多节点探 master /health(统一入口)
        check_health
        exit $?
        ;;
    *)
        echo "[ERROR] 未知探针类型: ${PROBE_TYPE}(应为 startup/liveness/readiness)" >&2
        exit 1
        ;;
esac
