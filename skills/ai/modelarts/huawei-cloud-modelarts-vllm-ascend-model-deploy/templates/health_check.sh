#!/bin/bash
# ModelArts 健康检查脚本(startup/liveness/readiness 三类探针)
# 多节点场景按是否存在同目录 get_master_ip.py 自然区分
# 禁用 set -e: 探针脚本须由探针逻辑控制返回码,curl 失败不应立即退出脚本

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# 端口与启动脚本一致: PD 分离 decode 角色端口 = DECODE_START_PORT(7100) + 本地 DP rank(与 start_vllm.sh 一致),
# 其余角色默认 8080;envs 无需注入 PORT,探针按 VLLM_ROLE + rank table 自动推导
DECODE_START_PORT="${DECODE_START_PORT:-7100}"
if [ -n "${PORT:-}" ]; then
    PORT="${PORT}"
elif [ "${VLLM_ROLE:-}" = "decode" ] && [ -n "${GLOBAL_RANK_TABLE_FILE_PATH:-}" ]; then
    _dp_rank=$(PYTHONUNBUFFERED=1 python3 -c "
import json,os
with open(os.getenv('GLOBAL_RANK_TABLE_FILE_PATH')) as f: rt=json.load(f)
servers=rt['server_group_list'][2]['server_list']
pod_ip=os.getenv('POD_IP','')
for i,s in enumerate(servers):
    if s.get('server_ip')==pod_ip:
        print(i); break
else:
    print(0)
" 2>/dev/null || echo 0)
    PORT=$((DECODE_START_PORT + _dp_rank))
else
    PORT=8080
fi
PROBE_TYPE="${1:-readiness}"   # startup / liveness / readiness

# vllm 的 OpenAI 兼容服务 /health 返回 200 OK 即健康
check_health() {
    local target_ip="127.0.0.1"
    # PD 分离 proxy 角色: 独立 HTTP 代理(运行 load_balance_proxy_server_example.py),不暴露 vllm /health;
    # readiness 探针改为探 proxy 进程存活(与 startup/liveness 一致),不依赖 DATA_PARALLEL_SIZE 条件
    if [ "${VLLM_ROLE:-}" = "proxy" ]; then
        pgrep -f "load_balance_proxy_server_example.py" >/dev/null 2>&1
        return $?
    fi
    # PD 分离/multi_node 多实例探针目标(用 GLOBAL_RANK_TABLE_FILE_PATH 检测多实例场景,
    # VLLM_ROLE 仅 PD 分离注入,multi_node master/worker 均不注入 VLLM_ROLE):
    # - PD 分离 decode(VLLM_ROLE=decode): 每节点独立暴露 API,始终探本地 /health
    # - PD 分离 prefill worker(VLLM_ROLE=prefill,--headless): 探 P0 master /health(group 1 第一个 server)
    # - multi_node worker(VLLM_ROLE 为空,--headless): 探 master /health(group 0 第一个 server)
    # - multi_node master(VLLM_ROLE 为空): target_ip 解析为 group 0 第一个 server=自身 IP,等同探本地 /health
    if [ -n "${GLOBAL_RANK_TABLE_FILE_PATH:-}" ]; then
        local group_idx=0
        case "${VLLM_ROLE:-}" in
            prefill) group_idx=1 ;;
            decode)  group_idx=2 ;;
        esac
        # decode 每节点独立 API,探本地;prefill/multi_node worker 探 master
        if [ "${VLLM_ROLE:-}" != "decode" ]; then
            target_ip=$(PYTHONUNBUFFERED=1 python3 -c "
import json,os
try:
    with open(os.getenv('GLOBAL_RANK_TABLE_FILE_PATH')) as f: rt=json.load(f)
    print(rt['server_group_list'][${group_idx}]['server_list'][0]['server_ip'])
except Exception:
    print('127.0.0.1')
" 2>/dev/null || echo "127.0.0.1")
            # worker 探 master 时,PORT 必须用 master 的 API port(P0=8080),非本地 PORT
            PORT=8080
        fi
    fi
    curl -sf --max-time 5 "http://${target_ip}:${PORT}/health" >/dev/null 2>&1
    return $?
}

# vllm 进程存活检查(startup/liveness 共用);PD 分离 proxy 角色查 load_balance_proxy_server_example.py 进程
check_process() {
    if [ "${VLLM_ROLE:-}" = "proxy" ]; then
        pgrep -f "load_balance_proxy_server_example.py" >/dev/null 2>&1
        return $?
    fi
    pgrep -f "vllm serve" >/dev/null 2>&1 || pgrep -f "vllm.entrypoints.openai.api_server" >/dev/null 2>&1 || pgrep -f "vllm.v1.worker" >/dev/null 2>&1 || pgrep -f "base_worker.py" >/dev/null 2>&1
    return $?
}

case "${PROBE_TYPE}" in
    startup|liveness)
        # 启动初期与运行期均查进程,避免 /health 未就绪或偶发抖动杀实例
        check_process
        exit $?
        ;;
    readiness)
        # PD 分离/multi_node: vllm 首次启动慢(init engine 3-13 分钟),/health 在 Application startup complete 前返回 503
        # readiness 探 HTTP /health,依赖 startup 探针(进程检查)通过后才开始 readiness;startup 延迟 300s + 失败次数 300 窗口覆盖首次启动
        check_health
        exit $?
        ;;
    *)
        echo "[ERROR] 未知探针类型: ${PROBE_TYPE}(应为 startup/liveness/readiness)" >&2
        exit 1
        ;;
esac
