#!/bin/bash
# vllm-ascend PD 共置启动模板(单引擎 DP 形态,无需 VLLM_ROLE/Mooncake)
# master/slave 经 get_master_ip.py 读 rank table 判定

set -e

CUR_DIR=$(cd "$(dirname "$0")" && pwd)

# ---------- 环境变量(带默认值,以模型适配文档为准) ----------
# 模型权重挂载路径: ModelArts 从 OBS 挂载的权重目录
MODEL_PATH="${MODEL_PATH:-/home/ma-user/model}"
# 对外暴露的模型名(API 调用时的 model 字段)
MODEL_NAME="${MODEL_NAME:-model}"
# 显式指定使用的 NPU 卡(单机 0,1,2,3...)
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"

# 张量并行度 = 每台推理单元使用的 NPU 卡数(与部署时单副本资源实例卡数一致)
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-8}"
# 数据并行总数 = rank table 全部 server 数(节点数)动态推导。
# PD 共置单引擎形态下每个节点运行 1 个实例,DP = 节点数;禁止硬编码
# 默认值(节点数变化时 --data-parallel-size 与节点数不符会跨节点通信失败)。
# 多副本(DP)由 ModelArts group_configs[].count 承载,模板无需修改。
DP_SIZE_DEFAULT="$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" --dp-size 2>/dev/null || echo 1)"
DATA_PARALLEL_SIZE="${DATA_PARALLEL_SIZE:-${DP_SIZE_DEFAULT:-1}}"
# 单节点数据并行数 = 每台推理单元的实例数(单引擎形态每节点 1 个实例)
DATA_PARALLEL_SIZE_LOCAL="${DATA_PARALLEL_SIZE_LOCAL:-1}"
# data-parallel 通信端口(master 节点监听)
DATA_PARALLEL_RPC_PORT="${DATA_PARALLEL_RPC_PORT:-13389}"
# 每批次最大 token 数
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-4096}"
# 最大并发序列数
MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"
# 量化方式(如 ascend/w8a8/awq;非量化模型留空)
QUANTIZATION="${QUANTIZATION:-}"

# 最大上下文长度
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
# 显存利用率
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.9}"
# 精度类型: auto / float16 / bfloat16(昇腾上大模型通常用 bfloat16)
DTYPE="${DTYPE:-bfloat16}"
# 服务监听端口(仅 master 对外提供 API;ModelArts 健康检查探针使用同一端口)
PORT="${PORT:-8080}"
# 目标芯片型号(仅记录用途: 910B/910C(A3)/310P 等)
CHIP_MODEL="${CHIP_MODEL:-}"

export ASCEND_RT_VISIBLE_DEVICES

# ---------- 模型权重挂载自检 ----------
# 缺失 config.json 时 vllm 会把路径当 HuggingFace repo id,报晦涩 OSError
if [ ! -f "${MODEL_PATH}/config.json" ]; then
    echo "[ERROR] ${MODEL_PATH}/config.json not found. Check ModelArts model mount config (存储地址精确到模型目录、挂载路径与 MODEL_PATH 一致、OBS 认证凭据已配置)." >&2
    echo "--- content of $(dirname "${MODEL_PATH}") ---" >&2
    ls -la "$(dirname "${MODEL_PATH}")" >&2 2>/dev/null || true
    echo "--- content of ${MODEL_PATH} ---" >&2
    ls -la "${MODEL_PATH}" >&2 2>/dev/null || true
    exit 1
fi

# ---------- 网络配置: 根据 POD_IP 反查网卡名 ----------
# ModelArts 多机部署注入 POD_IP 环境变量(当前节点 Pod IP)。
# 根据 POD_IP 用 ifconfig 反查其所在网卡名,绑定 HCCL/Gloo 通信到正确网卡。
NIC_NAME=""
if [ -n "${POD_IP:-}" ]; then
    NIC_NAME=$(ifconfig | grep -B1 "${POD_IP}" | grep -o '^\w*')
fi

# ---------- master/slave 角色判定 ----------
# 调用同目录 get_master_ip.py 从全局 rank table 取 master IP(相对定位,
# 禁止硬编码 /code/ 等绝对路径)。POD_IP 与 master IP 比较判定角色:
#   相等 → master 节点,提供 API 服务
#   不等 → slave 节点,启动占位 http server + --headless 参与分布式计算
MASTER_IP=""
DP_START_RANK=0
SLAVE_OPTS=""
if [ -f "${CUR_DIR}/get_master_ip.py" ]; then
    MASTER_IP=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py")
    DP_START_RANK=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" --dp-rank)
fi
if [ -n "${POD_IP:-}" ] && [ -n "${MASTER_IP}" ] && [ "${POD_IP}" != "${MASTER_IP}" ]; then
    echo "[pd_co] Current node is SLAVE (POD_IP=${POD_IP}, master=${MASTER_IP})"
    nohup python -m http.server 8080 > http_server.log 2>&1 &
    SLAVE_OPTS="--headless"
else
    echo "[pd_co] Current node is MASTER (POD_IP=${POD_IP:-N/A}, master=${MASTER_IP:-N/A})"
fi

echo "[pd_co] master_ip=${MASTER_IP}, local_ip=${POD_IP:-N/A}, nic=${NIC_NAME}, dp_rank=${DP_START_RANK}, TP=${TENSOR_PARALLEL_SIZE}, DP=${DATA_PARALLEL_SIZE}, PORT=${PORT}"

# ---------- 多机通信环境变量绑定 ----------
if [ -n "${POD_IP:-}" ]; then
    export HCCL_IF_IP="${POD_IP}"
fi
if [ -n "${NIC_NAME}" ]; then
    export GLOO_SOCKET_IFNAME="${NIC_NAME}"
    export TP_SOCKET_IFNAME="${NIC_NAME}"
    export HCCL_SOCKET_IFNAME="${NIC_NAME}"
fi

# ---------- 昇腾环境变量(以模型适配文档为准,按需启用) ----------
# 是否设置、取何值一律以用户确认模型的适配文档为准。
# 以下为 ModelArts 多机 PD 部署 + vllm-ascend 官方适配文档常见环境变量:
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}"
export OMP_PROC_BIND="${OMP_PROC_BIND:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
# 多机通信超时与就绪容忍(多节点大模型首启慢,需放宽,以官方适配文档为准):
export VLLM_RPC_TIMEOUT="${VLLM_RPC_TIMEOUT:-360000}"
export VLLM_EXECUTE_MODEL_TIMEOUT_SECONDS="${VLLM_EXECUTE_MODEL_TIMEOUT_SECONDS:-3000}"
export HCCL_EXEC_TIMEOUT="${HCCL_EXEC_TIMEOUT:-200}"
export HCCL_CONNECT_TIMEOUT="${HCCL_CONNECT_TIMEOUT:-120}"
export VLLM_ENGINE_READY_TIMEOUT_S="${VLLM_ENGINE_READY_TIMEOUT_S:-1200}"
# 视模型/版本按需启用(取消注释或由部署配置注入):
# export HCCL_OP_EXPANSION_MODE="${HCCL_OP_EXPANSION_MODE:-AIV}"
# export TASK_QUEUE_ENABLE="${TASK_QUEUE_ENABLE:-1}"
# export ACL_OP_INIT_MODE="${ACL_OP_INIT_MODE:-1}"
# export CPU_AFFINITY_CONF="${CPU_AFFINITY_CONF:-1}"
# export VLLM_USE_V1="${VLLM_USE_V1:-1}"
# export VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-true}"
# export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2

# ---------- 模型特有参数(bash 数组,JSON 用单引号包裹) ----------
# 必须用数组: 字符串展开会丢失 JSON 引号导致 argparse 报错
MODEL_ARGS=(
    # 在此追加模型文档要求的参数(见上方示例)
)

# 追加的普通参数(空格分隔,勿含 JSON;JSON 参数请直接加进上面的数组)
if [ -n "${EXTRA_ARGS:-}" ]; then
    read -r -a EXTRA_ARGS_ARR <<< "${EXTRA_ARGS}"
    MODEL_ARGS+=("${EXTRA_ARGS_ARR[@]}")
fi

# 量化参数(非量化模型 QUANTIZATION 留空时跳过)
QUANT_OPTS=""
if [ -n "${QUANTIZATION}" ]; then
    QUANT_OPTS="--quantization ${QUANTIZATION}"
fi

# ---------- 启动 vllm-ascend OpenAI 兼容服务(PD 分离 + 多节点) ----------
# 不同模型的参数(如 --quantization, --dtype, --trust-remote-code)以
# vllm-ascend 官方模型适配文档为准;同一模型在不同芯片型号(910B/910C/310P)
# 与不同卡数下的参数也可能不同,请按目标资源规格从适配文档核对后,
# 将模型特有参数追加到上方 MODEL_ARGS 数组中
#
# 多机部署参数(适配 ModelArts 平台,对齐官方 glm_5_2.sh):
#   --data-parallel-size            数据并行总数(总实例数)
#   --data-parallel-size-local      单节点数据并行数(每台推理单元实例数)
#   --data-parallel-start-rank      当前节点在 DP 中的起始 rank(get_master_ip.py --dp-rank)
#   --data-parallel-address         master 节点 IP(get_master_ip.py)
#   --data-parallel-rpc-port        DP 通信端口
#   slave 节点追加 --headless(不提供 API 服务,仅参与分布式计算);
#   master 节点由 vLLM 引擎内部提供 API(--api-server-count 默认 1)
exec vllm serve "${MODEL_PATH}" \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --served-model-name "${MODEL_NAME}" \
    --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}" \
    --data-parallel-size "${DATA_PARALLEL_SIZE}" \
    --data-parallel-size-local "${DATA_PARALLEL_SIZE_LOCAL}" \
    --data-parallel-start-rank "${DP_START_RANK}" \
    --data-parallel-address "${MASTER_IP}" \
    --data-parallel-rpc-port "${DATA_PARALLEL_RPC_PORT}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --max-num-batched-tokens "${MAX_NUM_BATCHED_TOKENS}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --max-num-seqs "${MAX_NUM_SEQS}" \
    --dtype "${DTYPE}" \
    --trust-remote-code \
    ${QUANT_OPTS} \
    ${SLAVE_OPTS} \
    "${MODEL_ARGS[@]}"
