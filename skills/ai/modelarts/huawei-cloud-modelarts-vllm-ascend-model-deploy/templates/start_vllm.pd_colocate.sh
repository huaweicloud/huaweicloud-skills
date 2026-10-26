#!/bin/bash
# vllm-ascend PD 共置启动模板(单引擎 DP 形态,无需 VLLM_ROLE)
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

# hixlep 配置目录(A5 UB 超平面通信所需,PD 共置单引擎 DP 形态跨节点 UB 链路通信;
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 读取,
# 详见 references/hixlep-guide.md)
HIXLEP_PATH="${HIXLEP_PATH:-/etc/hixlep}"
ROUTE_CONF_PATH="${ROUTE_CONF_PATH:-/lib/route.conf}"
HCCL_ROOTINFO_PATH="${HCCL_ROOTINFO_PATH:-/etc/hccl_rootinfo.json}"
# 是否在启动前自动生成 hixlep(默认开启,主机已挂载完整 hixlep 可设 AUTOGEN_HIXLEP=0)
AUTOGEN_HIXLEP="${AUTOGEN_HIXLEP:-1}"
# 离线包目录(随 scripts/generate_ep.py 与 scripts/offline_pkgs/ 一并复制到产物目录,
# 无网环境直接使用)
OFFLINE_PKG_DIR="${OFFLINE_PKG_DIR:-${CUR_DIR}/offline_pkgs}"

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
#   不等 → slave 节点,是否追加 --headless 取决于 DP LB 模式(见下)
MASTER_IP=""
DP_START_RANK=0
SLAVE_OPTS=""
if [ -f "${CUR_DIR}/get_master_ip.py" ]; then
    MASTER_IP=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py")
    DP_START_RANK=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" --dp-rank)
fi
if [ -n "${POD_IP:-}" ] && [ -n "${MASTER_IP}" ] && [ "${POD_IP}" != "${MASTER_IP}" ]; then
    echo "[pd_co] Current node is SLAVE (POD_IP=${POD_IP}, master=${MASTER_IP})"
    # vLLM 0.23.0 默认非 external/hybrid DP LB 模式: slave **必须**追加 --headless
    # (报 RuntimeError: Remote engine N must use --headless unless in external or
    # hybrid dp lb mode);slave 加 --headless 后不监听 API,需占位 http server 承接探针。
    # vLLM ≥ v0.30.0rc1 启用 external/hybrid DP LB 模式时,slave 禁 --headless(报反向错误);
    # 通过环境变量 DP_LB_MODE=external|hybrid 显式声明模式,slave 不加 --headless。
    DP_LB_MODE="${DP_LB_MODE:-none}"
    if [ "${DP_LB_MODE}" = "external" ] || [ "${DP_LB_MODE}" = "hybrid" ]; then
        echo "[pd_co] ${DP_LB_MODE}-dp-lb: slave runs full API server, no --headless"
    else
        echo "[pd_co] default-dp-lb: slave with --headless + placeholder http server"
        nohup python -m http.server 8080 > http_server.log 2>&1 &
        SLAVE_OPTS="--headless"
    fi
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
# 950DT 超平面通信(UBC 协议)自动配置,作为镜像无 hixl 自动生成功能时的兜底
export ASCEND_LOCAL_COMM_RES="${ASCEND_LOCAL_COMM_RES:-{\"version\":\"1.3\"}}"

# ---------- hixlep 自检与按需生成(PD 共置单引擎 DP 形态跨节点 UB 通信必需) ----------
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 显式读取;
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
    echo "[hixlep] ${HIXLEP_PATH} 缺失,使用 skill 内置离线包生成(PD 共置 UB 通信必需)"

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
    #    -s: server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡;多机 PD 共置沿用同模板
    local gen_ep="${CUR_DIR}/generate_ep.py"
    if [ ! -f "${gen_ep}" ]; then
        echo "[ERROR] ${gen_ep} 不存在,无法生成 hixlep(产物生成时应从 scripts/ 一并复制)" >&2
        exit 1
    fi
    ( cd "${CUR_DIR}" && python3 generate_ep.py -s ) || {
        echo "[ERROR] generate_ep.py 执行失败,检查 ${HCCL_ROOTINFO_PATH} 与 ${ROUTE_CONF_PATH} 是否匹配本机拓扑" >&2
        exit 1
    }

    # 4) 多机 net_instance_id 一致性核验(多节点必须一致,否则跨节点 UB 建链失败)
    local nid
    nid=$(grep -h net_instance_id "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | sort -u)
    if [ -n "${nid}" ] && [ "$(echo "${nid}" | wc -l)" -gt 1 ]; then
        echo "[WARN] 检测到多个 net_instance_id,多机场景必须一致,请人工核验:" >&2
        echo "${nid}" >&2
    fi
    echo "[hixlep] 生成完成,endpoint 文件数: $(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)"
}

# PD 共置单引擎 DP 形态必触发(跨节点 UB 通信)
generate_hixlep

# ---------- 模型特有参数(bash 数组,JSON 用单引号包裹) ----------
# 必须用数组: 字符串展开会丢失 JSON 引号导致 argparse 报错
# ⚠️ 角色专属参数(仅 master 命令有、slave 命令没有,如 --api-server-count /
#   --nnodes / --node-rank / --master-addr / --master-port)禁止加入此数组——
#   所有节点共享此数组,slave 会与自动追加的 --headless 冲突导致 vllm 校验崩溃
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
#   slave 节点按 DP LB 模式追加 --headless(默认 vLLM 0.23.0 加,slave 仅参与分布式计算;
#   DP_LB_MODE=external|hybrid 时不加,slave 也运行 API server);master 始终提供 API
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
