#!/bin/bash
# vllm-ascend PD 分离启动模板(Prefill/Decode 双角色,VLLM_ROLE 注入)

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ---------- 环境变量(带默认值) ----------
# 模型权重挂载路径: ModelArts 从 OBS 挂载的权重目录
MODEL_PATH="${MODEL_PATH:-/home/ma-user/model}"
# 对外暴露的模型名(API 调用时的 model 字段)
MODEL_NAME="${MODEL_NAME:-model}"
# 显式指定使用的 NPU 卡(单机 0,1,2,3...;单机 PD 时 Prefill/Decode
# 各单元按角色分配卡,如 Prefill 用 0-3、Decode 用 4-7,以模型文档为准)
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
# 各组内张量并行度(从模型适配文档提取的固定值;
# 禁止从 ASCEND_RT_VISIBLE_DEVICES 动态推导——ModelArts 注入该变量
# 可能只给单卡,推导为 TP=1,大模型权重装不进单卡显存 → 启动崩溃)
TP_SIZE="${TP_SIZE:-2}"
# 最大上下文长度
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
# 显存利用率
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.9}"
# 精度类型: auto / float16 / bfloat16(昇腾上大模型通常用 bfloat16)
DTYPE="${DTYPE:-bfloat16}"
# 服务监听端口(Prefill 与 Decode 可分别设置,由 ModelArts 部署单元注入)
PORT="${PORT:-8080}"
# 目标芯片型号(仅记录用途: 910B/910C(A3)/310P 等)
CHIP_MODEL="${CHIP_MODEL:-}"

# PD 角色: prefill / decode
# 由 ModelArts 两个部署单元分别注入(单元 A=prefill、单元 B=decode),
# 非用户手动输入。注意: 与 get_master_ip.py(节点主从)维度不同——
# master/worker 是同一分布式任务的分工(可自动判定);prefill/decode 是
# 两个独立 vLLM 服务实例(端口/KV 传输参数不同),实例本身无法自我判定
# 角色,必须由部署单元注入。
VLLM_ROLE="${VLLM_ROLE:-}"

export ASCEND_RT_VISIBLE_DEVICES

# ---------- 模型权重挂载自检(必做,规避晦涩报错) ----------
# 若 MODEL_PATH 下无 config.json,vllm/transformers 会把本地路径当作 HuggingFace
# repo id 处理,报错形如:
if [ ! -f "${MODEL_PATH}/config.json" ]; then
    echo "[ERROR] ${MODEL_PATH}/config.json not found. Check ModelArts model mount config (存储地址精确到模型目录、挂载路径与 MODEL_PATH 一致、OBS 认证凭据已配置)." >&2
    echo "--- content of $(dirname "${MODEL_PATH}") ---" >&2
    ls -la "$(dirname "${MODEL_PATH}")" >&2 2>/dev/null || true
    echo "--- content of ${MODEL_PATH} ---" >&2
    ls -la "${MODEL_PATH}" >&2 2>/dev/null || true
    exit 1
fi

# ---------- PD 角色分支 ----------
if [ -z "${VLLM_ROLE}" ]; then
    echo "[ERROR] PD 分离部署必须设置 VLLM_ROLE=prefill 或 decode(ModelArts 两个实例组分别注入)" >&2
    exit 1
fi
export VLLM_ROLE
echo "[pd] VLLM_ROLE=${VLLM_ROLE}, PORT=${PORT}, TP_SIZE=${TP_SIZE}"

# ---------- 昇腾环境变量(以模型适配文档为准,按需启用) ----------
# 是否设置、取何值一律以用户确认模型的适配文档为准:
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}"
export HCCL_BUFFSIZE="${HCCL_BUFFSIZE:-512}"
export OMP_PROC_BIND="${OMP_PROC_BIND:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
# 视模型/版本按需启用:
# export VLLM_USE_V1="${VLLM_USE_V1:-1}"
# export TASK_QUEUE_ENABLE="${TASK_QUEUE_ENABLE:-1}"
# export VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-true}"
# export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2

# ---------- 模型特有参数(bash 数组,JSON 用单引号包裹) ----------
# 必须用数组: 字符串展开会丢失 JSON 引号导致 argparse 报错
MODEL_ARGS=(
    # PD 专用参数(如 --deployment-config、Mooncake KV 传输、负载均衡)按
    # 模型页面/社区 PD 方案设置,直接追加到本数组
)

# 追加的普通参数(空格分隔,勿含 JSON;JSON 参数请直接加进上面的数组)
if [ -n "${EXTRA_ARGS:-}" ]; then
    read -r -a EXTRA_ARGS_ARR <<< "${EXTRA_ARGS}"
    MODEL_ARGS+=("${EXTRA_ARGS_ARR[@]}")
fi
# PD 专用普通参数(无 JSON 时可用;含 JSON 请加进 MODEL_ARGS 数组)
if [ -n "${PD_EXTRA_ARGS:-}" ]; then
    read -r -a PD_EXTRA_ARGS_ARR <<< "${PD_EXTRA_ARGS}"
    MODEL_ARGS+=("${PD_EXTRA_ARGS_ARR[@]}")
fi

# ---------- 启动 vllm-ascend OpenAI 兼容服务(PD 角色实例) ----------
exec python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --served-model-name "${MODEL_NAME}" \
    --tensor-parallel-size "${TP_SIZE}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --dtype "${DTYPE}" \
    --port "${PORT}" \
    --trust-remote-code \
    "${MODEL_ARGS[@]}"
