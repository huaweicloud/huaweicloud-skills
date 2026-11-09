#!/bin/bash
# vllm-ascend 多实例启动模板(实例数 N>1:跨节点 TP/DP 或单节点多实例;副本数 R 由部署副本数承载)
# master/worker 经 get_master_ip.py 0 读 rank table group 0 判定;worker 追加 --headless

set -e

CUR_DIR=$(cd "$(dirname "$0")" && pwd)

# ---------- 环境变量(带默认值,以模型适配文档为准) ----------
# 模型权重挂载路径: ModelArts 从 OBS 挂载的权重目录
MODEL_PATH="${MODEL_PATH:-/home/ma-user/model}"

# 对外暴露的模型名(API 调用时的 model 字段)
MODEL_NAME="${MODEL_NAME:-model}"
# 显式指定使用的 NPU 卡(单机 0,1,2,3...)
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"

# 张量并行度 = 每台推理单元使用的 NPU 卡数(与部署时单副本资源实例数一致)
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-8}"
# 数据并行总数 = rank table 节点数动态推导(ModelArts multi_node 不注入 DP_SIZE envs,
# 与 PD 分离不同;硬编码不符会致 worker 启动 engine rank 与 master 冲突,
# vLLM 报 "HELLO message from remote engine 0, expected it to be local")
DP_SIZE_DEFAULT="$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" --dp-size 2>/dev/null || echo 1)"
DATA_PARALLEL_SIZE="${DATA_PARALLEL_SIZE:-${DP_SIZE_DEFAULT:-1}}"
# 单节点数据并行数 = 每台推理单元的实例数(单引擎形态每节点 1 个实例)
DATA_PARALLEL_SIZE_LOCAL="${DATA_PARALLEL_SIZE_LOCAL:-1}"
# data-parallel 通信端口(master 节点监听)
DATA_PARALLEL_RPC_PORT="${DATA_PARALLEL_RPC_PORT:-13389}"

# 最大上下文长度
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
# 每批次最大 token 数
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-4096}"
# 显存利用率
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.9}"
# 最大并发序列数
MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"
# 精度类型: auto / float16 / bfloat16(昇腾上大模型通常用 bfloat16)
DTYPE="${DTYPE:-bfloat16}"
# 量化方式(如 ascend/w8a8/awq;非量化模型留空)
QUANTIZATION="${QUANTIZATION:-}"
# 服务监听端口(ModelArts 健康检查探针使用同一端口)
PORT="${PORT:-8080}"
# 目标芯片型号(仅记录用途: 910B/910C(A3)/310P 等)
CHIP_MODEL="${CHIP_MODEL:-}"

# hixlep 配置目录(A5 UB 超平面通信所需,跨节点 TP/PD 分离 KV 经 UB 链路传输;
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 读取,
# 详见 references/hixlep-guide.md)
HIXLEP_PATH="${HIXLEP_PATH:-/tmp/hixlep}"
ROUTE_CONF_PATH="${ROUTE_CONF_PATH:-/lib/route.conf}"
HCCL_ROOTINFO_PATH="${HCCL_ROOTINFO_PATH:-/etc/hccl_rootinfo.json}"
# 是否在启动前自动生成 hixlep(默认开启,主机已挂载完整 hixlep 可设 AUTOGEN_HIXLEP=0)
AUTOGEN_HIXLEP="${AUTOGEN_HIXLEP:-1}"
# 离线包目录(随 scripts/a5_hixlep/ 整目录复制到产物目录,
# 无网环境直接使用;generate_ep.py / fix_ub_endpoint.py / gen_route.sh / wheel 全在此目录下)
OFFLINE_PKG_DIR="${OFFLINE_PKG_DIR:-${CUR_DIR}/a5_hixlep}"

export ASCEND_RT_VISIBLE_DEVICES
export TENSOR_PARALLEL_SIZE
export DATA_PARALLEL_SIZE

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

# ---------- 量化参数 × 权重文件交叉校验 ----------
# BF16 原版权重无 quant_model_description.json,误带 --quantization ascend 会启动崩溃
# (ModelSlim Quantization Config Not Found);w8a8 量化版权重含该文件,误漏则推理精度退化
QUANT_DESC="${MODEL_PATH}/quant_model_description.json"
HAS_QUANT_ARG=0
for _a in "${MODEL_ARGS[@]:-}" "${EXTRA_ARGS:-}" "${PD_EXTRA_ARGS:-}"; do
    case "${_a}" in
        --quantization|--quantization=ascend|--quantization=*) HAS_QUANT_ARG=1 ;;
    esac
done
if [ -n "${QUANTIZATION:-}" ]; then
    HAS_QUANT_ARG=1
fi
if [ "${HAS_QUANT_ARG}" -eq 1 ] && [ ! -f "${QUANT_DESC}" ]; then
    echo "[ERROR] 启用了 --quantization ascend 但权重目录无 quant_model_description.json" >&2
    echo "       权重版本与启动参数不匹配: 当前权重未量化(BF16 原版),应移除 --quantization ascend" >&2
    echo "       quant_model_description.json 仅 w8a8/w8a8-mxfp8/w8a8c8-mxfp8 等量化版权重包含" >&2
    echo "--- content of ${MODEL_PATH} ---" >&2
    ls -la "${MODEL_PATH}" >&2 2>/dev/null || true
    exit 1
fi
if [ "${HAS_QUANT_ARG}" -eq 0 ] && [ -f "${QUANT_DESC}" ]; then
    echo "[WARN] 权重目录含 quant_model_description.json(量化版权重)但未启用 --quantization ascend" >&2
    echo "      量化版权重不启用 ascend 量化路径会精度退化,核对模型文档是否应加 --quantization ascend" >&2
fi

# ---------- 网络配置: 根据 POD_IP 反查网卡名 ----------
# ModelArts 多机部署注入 POD_IP 环境变量(当前节点 Pod IP)。
# 根据 POD_IP 用 ifconfig 反查其所在网卡名,绑定 HCCL/Gloo/TP 通信
# 到正确网卡(多网卡场景不绑定会导致跨节点通信失败)。
# POD_IP 未注入时(单机退化),网卡绑定跳过。
NIC_NAME=""
if [ -n "${POD_IP:-}" ]; then
    NIC_NAME=$(ifconfig | grep -B1 "${POD_IP}" | grep -o '^\w*')
fi

# ---------- master/worker 角色判定 ----------
# multi_node 形态 DATA_PARALLEL_SIZE>1(N>1,模板按 master+worker 实例数固定填入);
# 调用同目录 get_master_ip.py 0 从全局 rank table group 0 取 master IP
# (master 推理单元实例数只能为 1,group 0 只有 1 个 server);
# get_master_ip.py 内部轮询等待 status=completed。
# POD_IP 与 master_ip 比较判定角色:
#   相等 → master 节点,提供 API 服务
#   不等 → worker 节点,是否追加 --headless 取决于 DP LB 模式(见下)
MASTER_IP=""
DP_START_RANK=0
if [ "${DATA_PARALLEL_SIZE:-1}" -gt 1 ] && [ -f "${CUR_DIR}/get_master_ip.py" ]; then
    MASTER_IP=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" 0)
    DP_START_RANK=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" --dp-rank 2>/dev/null || echo 0)
fi

WORKER_OPTS=""
if [ -n "${POD_IP:-}" ] && [ -n "${MASTER_IP}" ] && [ "${POD_IP}" != "${MASTER_IP}" ]; then
    echo "[multi_node] Current node is WORKER (POD_IP=${POD_IP}, master=${MASTER_IP})"
    # vLLM 0.23.0 默认非 external/hybrid DP LB 模式: worker **必须**追加 --headless
    # (报 RuntimeError: Remote engine N must use --headless unless in external or
    # hybrid dp lb mode);worker 加 --headless 后不监听 API,readiness 探针改探 master /health
    # (health_check.sh 经 DATA_PARALLEL_SIZE>1 + get_master_ip.py 探 master;禁占位 http server
    # 占用 8080——会与 vLLM --master-port DP 通信冲突,worker 卡在 distributed_init)。
    # vLLM ≥ v0.30.0rc1 启用 external/hybrid DP LB 模式时,worker 禁 --headless(报反向错误);
    # 通过环境变量 DP_LB_MODE=external|hybrid 显式声明模式,worker 不加 --headless。
    DP_LB_MODE="${DP_LB_MODE:-none}"
    if [ "${DP_LB_MODE}" = "external" ] || [ "${DP_LB_MODE}" = "hybrid" ]; then
        echo "[multi_node] ${DP_LB_MODE}-dp-lb: worker runs full API server, no --headless"
    else
        echo "[multi_node] default-dp-lb: worker with --headless (no placeholder http server)"
        export DATA_PARALLEL_SIZE=2
        WORKER_OPTS="--headless"
    fi
else
    echo "[multi_node] Current node is MASTER (POD_IP=${POD_IP:-N/A}, master=${MASTER_IP:-N/A})"
fi

echo "[multi_node] master_ip=${MASTER_IP}, local_ip=${POD_IP:-N/A}, nic=${NIC_NAME}, dp_rank=${DP_START_RANK}, TP=${TENSOR_PARALLEL_SIZE}, DP=${DATA_PARALLEL_SIZE}"

# ---------- 昇腾环境变量(以模型适配文档为准,按需启用) ----------
# 以下为 ModelArts 多机部署 + vllm-ascend 官方适配文档常见环境变量:
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}"
export HCCL_BUFFSIZE="${HCCL_BUFFSIZE:-512}"
export OMP_PROC_BIND="${OMP_PROC_BIND:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
# 多机通信关键环境变量(POD_IP 注入时绑定):
if [ -n "${POD_IP:-}" ]; then
    export HCCL_IF_IP="${POD_IP}"
fi
if [ -n "${NIC_NAME}" ]; then
    export GLOO_SOCKET_IFNAME="${NIC_NAME}"
    export TP_SOCKET_IFNAME="${NIC_NAME}"
    export HCCL_SOCKET_IFNAME="${NIC_NAME}"
fi
# 超时与就绪容忍(多机大模型首启慢,需放宽):
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
# export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2
# 950DT 超平面通信(UBC 协议)自动配置,作为镜像无 hixl 自动生成功能时的兜底
export ASCEND_LOCAL_COMM_RES="${ASCEND_LOCAL_COMM_RES:-{\"version\":\"1.3\"}}"

# ---------- hixlep 自检与按需生成(跨节点 TP/DP 经 UB 链路通信必需) ----------
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 显式读取;
# 三类文件均在容器内现生成(无需主机预生成或 ModelArts 挂载主机路径):
#   1) hccl_rootinfo.json — unofficial_ascend_tools wheel 离线生成(主机镜像缺失时)
#   2) /lib/route.conf    — 内置 gen_route.sh 直接调用(纯 bash,读 /proc/ascend_ub 驱动接口)
#   3) /etc/hixlep/       — generate_ep.py 生成(读 hccl_rootinfo.json + route.conf)
generate_hixlep() {
    if [ "${AUTOGEN_HIXLEP}" != "1" ]; then
        return 0
    fi
    # 仅 A5(950DT/950PR/950) UB 超平面通信需要 hixlep;A2(910B)/A3(910C) 走 RoCE,跳过
    case "${CHIP_MODEL}" in
        950DT|950PR|950|"") ;;
        *) echo "[hixlep] CHIP_MODEL=${CHIP_MODEL} 非 A5 系列,跳过 hixlep 生成"; return 0 ;;
    esac
    # 无 UB 通信跳过: TP=1(无跨卡 TP) 且 DP=1(无跨节点 DP) 时无任何超平面通信
    if [ "${TENSOR_PARALLEL_SIZE:-1}" -le 1 ] && [ "${DATA_PARALLEL_SIZE:-1}" -le 1 ]; then
        echo "[hixlep] TP=1 且 DP=1,无跨卡/跨节点 UB 通信,跳过 hixlep 生成"
        return 0
    fi
    local existing
    existing=$(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)
    if [ "${existing}" -ge 1 ]; then
        echo "[hixlep] ${HIXLEP_PATH} 已有 ${existing} 个 endpoint 文件,跳过生成"
        return 0
    fi
    echo "[hixlep] ${HIXLEP_PATH} 缺失,容器内三步生成(hccl_rootinfo + route.conf + hixlep)"

    # 1) hccl_rootinfo.json 缺失则用内置 unofficial-ascend-tools 离线 wheel 生成
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

    # 1.5) hccl_rootinfo.json 的 rank_list[].local_id 范围调整:
    #      mindcluster-tools 生成或主机自带的 hccl_rootinfo.json 的 local_id 可能不是 0-7
    #      (实测 950DT 主机 rootinfo 的 local_id 为 48-55,多节点 rank table 全局 ID 可能为 8-15),
    #      而 route.conf 的 dev_id 为 0-7(本地 davinci ID),
    #      generate_ep.py 用 local_id_to_device_id.get(route_conf_dev_id) 查 0-7 在 48-55/8-15 映射表里找不到,
    #      导致 8 个 endpoint 全部 Warning: device_id not found、hixlep 文件数为 0。
    #      修复: 复制 hccl_rootinfo.json 到 /tmp 可写临时文件,按 rank_list 索引重新分配
    #      local_id = 0,1,...,N-1(与 route.conf dev_id 0-7 对齐),与原 local_id 取值范围无关,
    #      兼容 8-15 / 48-55 等任意取值。再用 --local --server --rootinfo-path 指定临时文件调用 generate_ep.py。
    #      (主机 /etc/hccl_rootinfo.json 在 ModelArts 容器内可能只读,需复制到 /tmp 调整)
    local adj_rootinfo="/tmp/hccl_rootinfo_adj.json"
    cp "${HCCL_ROOTINFO_PATH}" "${adj_rootinfo}" || { echo "[ERROR] 复制 ${HCCL_ROOTINFO_PATH} -> ${adj_rootinfo} 失败" >&2; exit 1; }
    HCCL_ROOTINFO_PATH_ADJ="${adj_rootinfo}" python3 -c '
import json, os
path = os.environ["HCCL_ROOTINFO_PATH_ADJ"]
with open(path) as f:
    data = json.load(f)
rank_list = data.get("rank_list", [])
adjusted = 0
for idx, rank in enumerate(rank_list):
    lid = rank.get("local_id")
    if isinstance(lid, int) and lid != idx:
        rank["local_id"] = idx
        adjusted += 1
if adjusted > 0:
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[hixlep] hccl_rootinfo.json local_id 按 rank_list 索引重排 {adjusted} 个 rank -> 0..{len(rank_list)-1} (临时文件 {path})")
else:
    print(f"[hixlep] hccl_rootinfo.json local_id 无需重排(已是 0..{len(rank_list)-1})")
' || { echo "[ERROR] hccl_rootinfo.json local_id 调整失败" >&2; exit 1; }
    # 从调整后的临时 rootinfo 读 topo_file_path(production 模式硬编码读 /etc/,--local 模式需显式传)
    local topo_path
    topo_path=$(HCCL_TOPO_PATH_READ="${adj_rootinfo}" python3 -c '
import json, os
with open(os.environ["HCCL_TOPO_PATH_READ"]) as f:
    data = json.load(f)
print(data.get("topo_file_path", ""))
') || { echo "[ERROR] 读取 hccl_rootinfo.json topo_file_path 失败" >&2; exit 1; }
    if [ -z "${topo_path}" ]; then
        echo "[ERROR] hccl_rootinfo.json 缺少 topo_file_path 字段" >&2
        exit 1
    fi

    # 2) route.conf 缺失则调用内置 gen_route.sh 生成(纯 bash,读 /proc/ascend_ub 驱动接口)
    #    gen_route.sh 来自 a5_hixlep 目录(scripts/a5_hixlep/gen_route.sh)
    #    直接调 bash 脚本即可生成 /lib/route.conf
    if [ ! -s "${ROUTE_CONF_PATH}" ]; then
        local gen_route="${OFFLINE_PKG_DIR}/gen_route.sh"
        if [ ! -f "${gen_route}" ]; then
            echo "[ERROR] ${gen_route} 不存在,无法生成 route.conf(产物生成时 a5_hixlep 目录未一并复制)" >&2
            exit 1
        fi
        echo "[hixlep] ${ROUTE_CONF_PATH} 缺失,调用内置 gen_route.sh 生成"
        bash "${gen_route}" || {
            echo "[ERROR] gen_route.sh 执行失败,检查 /proc/ascend_ub(或 /proc/asdrv_ub)与 /proc/uda/namespace_node 是否可读" >&2
            echo "       (这两个路径由 A5 主机 HDK 驱动提供,容器需能访问主机 /proc)" >&2
            exit 1
        }
        if [ ! -s "${ROUTE_CONF_PATH}" ]; then
            echo "[ERROR] gen_route.sh 执行后 ${ROUTE_CONF_PATH} 仍未生成,检查脚本日志" >&2
            exit 1
        fi
    fi

    # 3) 用内置 generate_ep.py 生成 hixlep endpoint 文件
    #    --local --server: 用 server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡;多机场景沿用同模板
    #    显式传 --rootinfo-path(调整 local_id 后的临时文件)+ --route-path + --topo-path
    #    (production 模式硬编码读 /etc/hccl_rootinfo.json,--local 模式才接受 --rootinfo-path 参数)
    local gen_ep="${OFFLINE_PKG_DIR}/generate_ep.py"
    if [ ! -f "${gen_ep}" ]; then
        echo "[ERROR] ${gen_ep} 不存在,无法生成 hixlep(产物生成时应整目录复制 scripts/a5_hixlep/ 到产物 a5_hixlep/)" >&2
        exit 1
    fi
    ( cd "${OFFLINE_PKG_DIR}" && python3 generate_ep.py --local --server \
        --rootinfo-path "${adj_rootinfo}" \
        --route-path "${ROUTE_CONF_PATH}" \
        --topo-path "${topo_path}" \
        --output-dir "${HIXLEP_PATH}" ) || {
        echo "[ERROR] generate_ep.py 执行失败,检查 ${adj_rootinfo} 与 ${ROUTE_CONF_PATH} 是否匹配本机拓扑" >&2
        exit 1
    }

    # 4) 多机 net_instance_id 一致性核验(多节点必须一致,否则跨节点 UB 建链失败)
    local nid
    nid=$(grep -h net_instance_id "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | sort -u)
    if [ -n "${nid}" ] && [ "$(echo "${nid}" | wc -l)" -gt 1 ]; then
        echo "[WARN] 检测到多个 net_instance_id,多机场景必须一致,请人工核验:" >&2
        echo "${nid}" >&2
    fi

    # 5) NPU ID ↔ Chip Phy-ID 文件名映射修正(A5 PD 分离 RoCE 场景必需)
    # generate_ep.py 按 hccl_rootinfo.json 的 device_id(可能为 Chip Phy-ID 如 32-39)命名
    # ub_endpoint_npu_<device_id>.json,但 vllm-ascend 按 NPU ID(0-7)索引文件 → 文件名错位
    # fix_ub_endpoint.py 用 npu-smi info -m 建立映射,删除不存在的 + 按 NPU ID 重命名
    # 参考 wiki《A5 带Roce场景参数面部署》PD 分离 1p1d 单机 8 卡方案
    local fix_ep="${OFFLINE_PKG_DIR}/fix_ub_endpoint.py"
    if [ -f "${fix_ep}" ] && command -v npu-smi >/dev/null 2>&1; then
        echo "[hixlep] 调用 fix_ub_endpoint.py 修正 NPU ID ↔ Chip Phy-ID 文件名映射"
        HIXLEP_DIR="${HIXLEP_PATH}" python3 "${fix_ep}" -y 2>&1 | sed 's/^/[hixlep] /' >&2 || {
            echo "[WARN] fix_ub_endpoint.py 执行失败,保留 generate_ep.py 原始文件名" >&2
        }
    fi
    echo "[hixlep] 生成完成,endpoint 文件数: $(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)"
}

# 多节点 TP/DP 必触发(跨节点 UB 通信)
generate_hixlep

# ---------- 模型特有参数(bash 数组,JSON 用单引号包裹) ----------
# 必须用数组: 字符串展开会丢失 JSON 引号导致 argparse 报错
# ⚠️ 角色专属参数(仅 master 命令有、worker 命令没有,如 --api-server-count /
#   --nnodes / --node-rank / --master-addr / --master-port)禁止加入此数组——
#   所有节点共享此数组,worker 会与自动追加的 --headless 冲突导致 vllm 校验崩溃
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

# ---------- 启动 vllm-ascend OpenAI 兼容服务(多节点) ----------
# 无条件传 --data-parallel-* 参数(对齐 A2 成功脚本): DP=1 时也传
# --data-parallel-size 1 --data-parallel-address "${MASTER_IP}"(空字符串),
# vLLM 内部按 DP=1 走单实例退化,master/worker 判定由 POD_IP/MASTER_IP 比较决定。
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
    ${WORKER_OPTS} \
    "${MODEL_ARGS[@]}"
