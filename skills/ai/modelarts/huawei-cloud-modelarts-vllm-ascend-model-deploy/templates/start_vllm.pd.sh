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
# 两个独立 vLLM 服务实例(端口不同),实例本身无法自我判定角色,必须由部署单元注入
# 角色,必须由部署单元注入。
VLLM_ROLE="${VLLM_ROLE:-}"

# hixlep 配置目录(A5 UB 超平面通信所需,P↔D KV cache 经 UB 链路传输;
# vllm-ascend 通过 kv_connector_extra_config.ascend_local_comm_res_path 读取,
# 详见 references/hixlep-guide.md)
HIXLEP_PATH="${HIXLEP_PATH:-/etc/hixlep}"
ROUTE_CONF_PATH="${ROUTE_CONF_PATH:-/lib/route.conf}"
HCCL_ROOTINFO_PATH="${HCCL_ROOTINFO_PATH:-/etc/hccl_rootinfo.json}"
# 是否在启动前自动生成 hixlep(默认开启,主机已挂载完整 hixlep 可设 AUTOGEN_HIXLEP=0)
AUTOGEN_HIXLEP="${AUTOGEN_HIXLEP:-1}"
# 离线包目录(随 scripts/generate_ep.py 与 scripts/offline_pkgs/ 一并复制到产物目录,
# 无网环境直接使用)
OFFLINE_PKG_DIR="${OFFLINE_PKG_DIR:-${SCRIPT_DIR}/offline_pkgs}"

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
# 950DT 超平面通信(UBC 协议)自动配置,作为镜像无 hixl 自动生成功能时的兜底
export ASCEND_LOCAL_COMM_RES="${ASCEND_LOCAL_COMM_RES:-{\"version\":\"1.3\"}}"
# 视模型/版本按需启用:
# export VLLM_USE_V1="${VLLM_USE_V1:-1}"
# export TASK_QUEUE_ENABLE="${TASK_QUEUE_ENABLE:-1}"
# export VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-true}"
# export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2

# ---------- hixlep 自检与按需生成(PD 分离 P↔D KV 传输必需) ----------
# vllm-ascend 通过 kv_connector_extra_config.ascend_local_comm_res_path 显式读取;
# 若主机侧 /etc/hixlep 缺失(裸机环境或非 cloud_a5:0.5 镜像),使用 skill 内置离线包生成:
#   - generate_ep.py(随 scripts/ 复制到产物目录,生成 /etc/hixlep/ub_endpoint_npu_*.json)
#   - offline_pkgs/unofficial_ascend_tools-0.0.7rc4-py3-none-any.whl(生成 /etc/hccl_rootinfo.json)
# route.conf 与拓扑 JSON 需 A5 主机 HDK 驱动自带,缺失时报错明确指引(无网无法现生成)
generate_hixlep() {
    if [ "${AUTOGEN_HIXLEP}" != "1" ]; then
        return 0
    fi
    # 仅 A5(950DT/950PR/950) UB 超平面通信需要 hixlep;A2(910B)/A3(910C) 走 RoCE,跳过
    case "${CHIP_MODEL}" in
        950DT|950PR|950|"") ;;
        *) echo "[hixlep] CHIP_MODEL=${CHIP_MODEL} 非 A5 系列,跳过 hixlep 生成"; return 0 ;;
    esac
    local existing
    existing=$(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)
    if [ "${existing}" -ge 1 ]; then
        echo "[hixlep] ${HIXLEP_PATH} 已有 ${existing} 个 endpoint 文件,跳过生成"
        return 0
    fi
    echo "[hixlep] ${HIXLEP_PATH} 缺失,使用 skill 内置离线包生成(PD 分离 UB 通信必需)"

    # 1) route.conf 必须 A5 主机 HDK 驱动自带,无网无法现生成
    if [ ! -s "${ROUTE_CONF_PATH}" ]; then
        echo "[ERROR] ${ROUTE_CONF_PATH} 不存在。route.conf 由 A5 主机 HDK 驱动安装时自动生成," >&2
        echo "       无网环境无法现生成,请确认主机 HDK 驱动已正确安装,或从已有 A5 主机拷入该文件" >&2
        exit 1
    fi

    # 2) hccl_rootinfo.json 缺失则用内置 unofficial-ascend-tools 离线 wheel 生成
    if [ ! -s "${HCCL_ROOTINFO_PATH}" ]; then
        local wheel="${OFFLINE_PKG_DIR}/unofficial_ascend_tools-0.0.7rc4-py3-none-any.whl"
        if [ ! -f "${wheel}" ]; then
            echo "[ERROR] 离线包 ${wheel} 不存在,无法生成 hccl_rootinfo.json" >&2
            exit 1
        fi
        echo "[hixlep] ${HCCL_ROOTINFO_PATH} 缺失,离线安装 ${wheel##*/} 生成"
        python3 -m pip install --no-index --no-deps --quiet "${wheel}" || {
            echo "[ERROR] 离线安装 unofficial-ascend-tools 失败" >&2
            exit 1
        }
        python3 -m mindcluster_tools.rootinfo --product_type server --output "${HCCL_ROOTINFO_PATH}" || {
            echo "[ERROR] mindcluster-tools rootinfo 生成 hccl_rootinfo.json 失败" >&2
            exit 1
        }
    fi

    # 3) 用内置 generate_ep.py 生成 hixlep endpoint 文件
    #    -s: server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡;多机 PD 分离沿用同模板
    local gen_ep="${SCRIPT_DIR}/generate_ep.py"
    if [ ! -f "${gen_ep}" ]; then
        echo "[ERROR] ${gen_ep} 不存在,无法生成 hixlep(产物生成时应从 scripts/ 一并复制)" >&2
        exit 1
    fi
    ( cd "${SCRIPT_DIR}" && python3 generate_ep.py -s ) || {
        echo "[ERROR] generate_ep.py 执行失败,检查 ${HCCL_ROOTINFO_PATH} 与 ${ROUTE_CONF_PATH} 是否匹配本机拓扑" >&2
        exit 1
    }

    # 4) 多机 net_instance_id 一致性核验(单机可忽略,多机必须一致)
    local nid
    nid=$(grep -h net_instance_id "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | sort -u)
    if [ -n "${nid}" ] && [ "$(echo "${nid}" | wc -l)" -gt 1 ]; then
        echo "[WARN] 检测到多个 net_instance_id,多机场景必须一致,请人工核验:" >&2
        echo "${nid}" >&2
    fi
    echo "[hixlep] 生成完成,endpoint 文件数: $(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)"
}

# PD 分离角色必触发(P↔D 跨卡 UB 通信)
if [ "${VLLM_ROLE}" = "prefill" ] || [ "${VLLM_ROLE}" = "decode" ]; then
    generate_hixlep
fi

# ---------- 模型特有参数(bash 数组,JSON 用单引号包裹) ----------
# 必须用数组: 字符串展开会丢失 JSON 引号导致 argparse 报错
MODEL_ARGS=(
    # PD 专用参数(如 --deployment-config、负载均衡)按
    # 模型页面/社区 PD 方案设置,直接追加到本数组
)

# PD 专用 kv-transfer-config(MooncakeConnectorV1,P↔D KV cache 经 UB 传输)
# kv_role: prefill=kv_producer / decode=kv_consumer,由 VLLM_ROLE 决定
# kv_port: prefill/decode 各自监听端口需不同(默认 prefill=30000 / decode=30100)
# ascend_local_comm_res_path: vllm-ascend 显式读取 /etc/hixlep,优先级高于 ASCEND_LOCAL_COMM_RES 环境变量
#   (来源: 2012labs Qwen3.5 A5 PD分离实战 5.2 启动命令;模型页面若有差异,通过 PD_EXTRA_ARGS 覆盖)
KV_PORT="${KV_PORT:-30000}"
if [ "${VLLM_ROLE}" = "prefill" ]; then
    KV_ROLE="kv_producer"
else
    KV_ROLE="kv_consumer"
fi
if [ "${KV_PORT}" = "30000" ] && [ "${VLLM_ROLE}" = "decode" ]; then
    KV_PORT="30100"
fi
# kv-transfer-config JSON 单独拼装(数组传参时整体作为一个 argv 元素)
KV_TRANSFER_CONFIG="{\"kv_connector\": \"MooncakeConnectorV1\", \"kv_role\": \"${KV_ROLE}\", \"kv_port\": \"${KV_PORT}\", \"kv_buffer_device\": \"npu\", \"kv_connector_extra_config\": {\"prefill\": {\"dp_size\": 1, \"tp_size\": 1}, \"decode\": {\"dp_size\": 1, \"tp_size\": 1}, \"ascend_local_comm_res_path\": \"${HIXLEP_PATH}\"}}"
PD_ARGS=(--kv-transfer-config "${KV_TRANSFER_CONFIG}")

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
exec vllm serve "${MODEL_PATH}" \
    --served-model-name "${MODEL_NAME}" \
    --tensor-parallel-size "${TP_SIZE}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --dtype "${DTYPE}" \
    --port "${PORT}" \
    --trust-remote-code \
    "${MODEL_ARGS[@]}" \
    "${PD_ARGS[@]}"
