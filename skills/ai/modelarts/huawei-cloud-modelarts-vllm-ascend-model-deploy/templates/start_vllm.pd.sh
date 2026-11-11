#!/bin/bash
# vllm-ascend PD 分离启动模板(Proxy/Prefill/Decode 三角色,VLLM_ROLE 注入 + 节点 master/worker 经 get_master_ip.py 按 group_idx 判定)

set -e

CUR_DIR=$(cd "$(dirname "$0")" && pwd)

# ---------- 环境变量(带默认值,以模型适配文档为准) ----------
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
# 单节点脚本 TP 值缺失时按芯片卡数取值(A2/950DT 8,A3 16)
TP_SIZE="${TP_SIZE:-2}"
# PD 分离 prefill/decode 各自数据并行数(按官网 kv_connector_extra_config 推导;
# 同 TP_SIZE 由模板按 1.2 确认的节点数×卡数/TP 固定填入,不依赖 envs 注入):
#   PREFILL_DP_SIZE = 1 (prefill 单实例承载 P 组全部 prefill 工作)
#   DECODE_DP_SIZE = 部署所需节点数 × 芯片卡数 / TP_SIZE (D 组跨节点 DP)
# DATA_PARALLEL_SIZE 按 VLLM_ROLE 切换:prefill 用 PREFILL_DP_SIZE,decode 用 DECODE_DP_SIZE
PREFILL_DP_SIZE="${PREFILL_DP_SIZE:-1}"
DECODE_DP_SIZE="${DECODE_DP_SIZE:-1}"
# 单节点数据并行数 = 每台推理单元的实例数(PD 分离每节点每角色 1 个实例)
DATA_PARALLEL_SIZE_LOCAL="${DATA_PARALLEL_SIZE_LOCAL:-1}"
# data-parallel 通信端口(master 节点监听)
DATA_PARALLEL_RPC_PORT="${DATA_PARALLEL_RPC_PORT:-13389}"
# 最大上下文长度
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
# 显存利用率
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.9}"
# 精度类型: auto / float16 / bfloat16(昇腾上大模型通常用 bfloat16)
DTYPE="${DTYPE:-bfloat16}"
# 服务监听端口(官网 V8: --port = vllm-start-port + 本地 DP rank i,每实例递增)
# 三角色起始端口已在脚本内按角色内置默认值(proxy=8080/prefill=8080/decode=7100),
# 无需 ModelArts envs 注入 PORT;如需自定义覆盖,可经环境变量 VLLM_START_PORT 传入。
# prefill/decode 各自不同起始端口,避免同节点角色端口冲突;DP_RANK 由脚本从 rank table 推导
VLLM_START_PORT="${VLLM_START_PORT:-8080}"
# decode 角色起始端口与 prefill 不同(脚本按 VLLM_ROLE 自动切换,无需 envs 注入)
# 如需自定义覆盖,可经环境变量 DECODE_START_PORT 传入
DECODE_START_PORT="${DECODE_START_PORT:-7100}"
# 目标芯片型号(仅记录用途: 910B/910C(A3)/310P 等,不同芯片的
# dtype/量化/并行参数可能不同,务必以 vllm-ascend 对应芯片的适配文档为准)
CHIP_MODEL="${CHIP_MODEL:-}"

# PD 服务角色: proxy / prefill / decode
# 由 ModelArts 同一部署单元内 3 个推理单元分别注入(单元 A=proxy、单元 B=prefill、单元 C=decode)。
# proxy: 独立 HTTP 代理进程(运行 load_balance_proxy_server_example.py,不运行 vllm serve,不消耗 NPU 卡)
# prefill: vllm serve kv_producer,master/worker 由 get_master_ip.py 1 读 rank table group 1 判定
# decode: vllm serve kv_consumer,DP 主节点 IP 由 get_master_ip.py 2 读 rank table group 2 获取
# (官网 V2: D 组 --dp-address 指向 D 组自己的第一个 server,不是 prefill 组的 master)
VLLM_ROLE="${VLLM_ROLE:-}"

# hixlep 配置目录(A5 UB 超平面通信所需,P↔D KV cache 经 UB 链路传输;
# vllm-ascend 通过 kv_connector_extra_config.ascend_local_comm_res_path 读取,
# 详见 references/hixlep-guide.md)
HIXLEP_PATH="${HIXLEP_PATH:-/tmp/hixlep}"
ROUTE_CONF_PATH="${ROUTE_CONF_PATH:-/lib/route.conf}"
HCCL_ROOTINFO_PATH="${HCCL_ROOTINFO_PATH:-/etc/hccl_rootinfo.json}"
# 是否在启动前自动生成 hixlep(默认开启,主机已挂载完整 hixlep 可设 AUTOGEN_HIXLEP=0)
AUTOGEN_HIXLEP="${AUTOGEN_HIXLEP:-1}"
# a5_hixlep 脚本目录(随 scripts/a5_hixlep/ 整目录复制到产物目录;
# generate_ep.py / fix_ub_endpoint.py / gen_route.sh 均在此目录,均可离线直接使用)
OFFLINE_PKG_DIR="${OFFLINE_PKG_DIR:-${CUR_DIR}/a5_hixlep}"

export ASCEND_RT_VISIBLE_DEVICES

# ---------- proxy 角色: 独立 HTTP 代理,不运行 vllm serve(须在权重自检前 exec 退出) ----------
# 官网 load_balance_proxy_server_example.py: 接收客户端请求,路由到 prefiller/decoder
# proxy 不消耗 NPU 卡,实例数只能为 1
# proxy 参数从 rank table 自动推导: prefiller = group 1 全部 server:PORT;decoder = group 2 全部 server:PORT
if [ "${VLLM_ROLE}" = "proxy" ]; then
    PROXY_PORT="${PROXY_PORT:-8080}"
    PREFILLER_START_PORT="${PREFILLER_START_PORT:-8080}"
    DECODER_START_PORT="${DECODER_START_PORT:-7100}"
    PREFILLER_HOSTS=""
    PREFILLER_PORTS=""
    DECODER_HOSTS=""
    DECODER_PORTS=""
    if [ -f "${CUR_DIR}/get_master_ip.py" ] && [ -n "${GLOBAL_RANK_TABLE_FILE_PATH:-}" ]; then
        _prefill_master=$(PYTHONUNBUFFERED=1 python3 -c "
import json,os
with open(os.getenv('GLOBAL_RANK_TABLE_FILE_PATH')) as f: rt=json.load(f)
print(rt['server_group_list'][1]['server_list'][0]['server_ip'])
" 2>/dev/null)
        _decode_ips=$(PYTHONUNBUFFERED=1 python3 -c "
import json,os
with open(os.getenv('GLOBAL_RANK_TABLE_FILE_PATH')) as f: rt=json.load(f)
servers=rt['server_group_list'][2]['server_list']
print(' '.join(s['server_ip'] for s in servers))
" 2>/dev/null)
        PREFILLER_HOSTS="${_prefill_master}"
        DECODER_HOSTS="${_decode_ips}"
        PREFILLER_PORTS="${PREFILLER_START_PORT}"
        _d_idx=0
        for _ip in ${_decode_ips}; do
            DECODER_PORTS="${DECODER_PORTS} $((DECODER_START_PORT + _d_idx))"
            _d_idx=$((_d_idx + 1))
        done
        DECODER_PORTS=$(echo "${DECODER_PORTS}" | xargs)
    fi
    PREFILLER_HOSTS="${PREFILLER_HOSTS:-${PREFILLER_HOSTS_ENV:-}}"
    PREFILLER_PORTS="${PREFILLER_PORTS:-${PREFILLER_PORTS_ENV:-}}"
    DECODER_HOSTS="${DECODER_HOSTS:-${DECODER_HOSTS_ENV:-}}"
    DECODER_PORTS="${DECODER_PORTS:-${DECODER_PORTS_ENV:-}}"
    if [ -z "${PREFILLER_HOSTS}" ] || [ -z "${DECODER_HOSTS}" ]; then
        echo "[ERROR] proxy 角色无法从 rank table 推导 PREFILLER_HOSTS/DECODER_HOSTS,也无 envs 注入" >&2
        exit 1
    fi
    echo "[pd-proxy] Starting load_balance_proxy_server on port ${PROXY_PORT}"
    echo "[pd-proxy] prefiller=${PREFILLER_HOSTS}:${PREFILLER_PORTS} decoder=${DECODER_HOSTS}:${DECODER_PORTS}"
    exec python3 "${CUR_DIR}/load_balance_proxy_server_example.py" \
        --host 0.0.0.0 \
        --port "${PROXY_PORT}" \
        --prefiller-hosts ${PREFILLER_HOSTS} \
        --prefiller-ports ${PREFILLER_PORTS} \
        --decoder-hosts ${DECODER_HOSTS} \
        --decoder-ports ${DECODER_PORTS}
fi

# ---------- 模型权重挂载自检(必做,规避晦涩报错) ----------
# 若 MODEL_PATH 下无 config.json,vllm/transformers 会把本地路径当作 HuggingFace
# repo id 处理,报错形如: OSError: Repo id must be in the form 'repo_name' or 'namespace/repo_name'
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

# ---------- PD 服务角色分支 ----------
if [ -z "${VLLM_ROLE}" ]; then
    echo "[ERROR] PD 分离部署必须设置 VLLM_ROLE=proxy|prefill|decode(ModelArts 3 个推理单元分别注入)" >&2
    exit 1
fi
export VLLM_ROLE
# DATA_PARALLEL_SIZE 按 VLLM_ROLE 切换: prefill=PREFILL_DP_SIZE, decode=DECODE_DP_SIZE
# (proxy 不运行 vllm serve,DATA_PARALLEL_SIZE 不参与启动命令)
case "${VLLM_ROLE}" in
    prefill) DATA_PARALLEL_SIZE="${PREFILL_DP_SIZE}" ;;
    decode)  DATA_PARALLEL_SIZE="${DECODE_DP_SIZE}" ;;
    *)       DATA_PARALLEL_SIZE="${PREFILL_DP_SIZE}" ;;
esac
export TP_SIZE
export DATA_PARALLEL_SIZE

# ---------- 网络配置: 根据 POD_IP 反查网卡名 ----------
# ModelArts 多机部署注入 POD_IP 环境变量(当前节点 Pod IP)。
# 根据 POD_IP 用 ifconfig 反查其所在网卡名,绑定 HCCL/Gloo 通信到正确网卡。
NIC_NAME=""
if [ -n "${POD_IP:-}" ]; then
    NIC_NAME=$(ifconfig | grep -B1 "${POD_IP}" | grep -o '^\w*')
fi

# ---------- 节点 master/worker 角色判定 ----------
# 单副本资源实例数为 1(DP=1)时无 master/worker 区分,直接判 master,跳过
# get_master_ip.py 调用(无 GLOBAL_RANK_TABLE_FILE_PATH 注入也能跑)。
# 多实例(DP>1)时调用同目录 get_master_ip.py <group_idx> 从全局 rank table 取 master IP:
#   prefill: get_master_ip.py 1(group 1 第一个 server = P 组 master,其余 = worker)
#   decode:  get_master_ip.py 2(group 2 第一个 server = D 组 DP 主节点)
# (官网 V2: D 组 --dp-address 指向 D 组自己的第一个 server,不是 prefill 组的 master)
# prefill: POD_IP 与 master IP 比较判定角色(相等→master,不等→worker 加 --headless)
# decode: 所有实例正常启动(不做主从判定,不加 --headless),仅获取 DP 主节点 IP 用于 --data-parallel-address
MASTER_IP=""
DP_START_RANK="${DP_START_RANK:-0}"
WORKER_OPTS=""
if [ "${DATA_PARALLEL_SIZE:-1}" -gt 1 ] && [ -f "${CUR_DIR}/get_master_ip.py" ]; then
    if [ "${VLLM_ROLE}" = "prefill" ]; then
        MASTER_IP=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" 1)
    elif [ "${VLLM_ROLE}" = "decode" ]; then
        MASTER_IP=$(PYTHONUNBUFFERED=1 python3 "${CUR_DIR}/get_master_ip.py" 2)
    fi
fi
# PORT 自增(官网 V8: --port = vllm-start-port + 本地 DP rank i,每实例递增)
# prefill/decode 各自起始端口不同(脚本内按 VLLM_ROLE 内置默认值,无需 envs 注入);
# DP_RANK 由 ModelArts envs 注入(DP_START_RANK)
if [ "${VLLM_ROLE}" = "decode" ]; then
    PORT=$((DECODE_START_PORT + DP_START_RANK))
else
    PORT=$((VLLM_START_PORT + DP_START_RANK))
fi
# prefill: 按 POD_IP 与 master IP 比较判定主从;decode: 不做主从判定,所有实例正常启动
if [ "${VLLM_ROLE}" = "decode" ]; then
    echo "[pd] decode node normal start (POD_IP=${POD_IP:-N/A}, DP_master=${MASTER_IP:-N/A}, no master/worker distinction)"
elif [ -n "${POD_IP:-}" ] && [ -n "${MASTER_IP}" ] && [ "${POD_IP}" != "${MASTER_IP}" ]; then
    echo "[pd] Current node is WORKER (POD_IP=${POD_IP}, master=${MASTER_IP}, VLLM_ROLE=${VLLM_ROLE})"
    # vLLM 0.23.0 默认非 external/hybrid DP LB 模式: worker **必须**追加 --headless
    # (报 RuntimeError: Remote engine N must use --headless unless in external or
    # hybrid dp lb mode);worker 加 --headless 后不监听 API,readiness 探针改探 master /health
    # (health_check.sh 经 DATA_PARALLEL_SIZE>1 + get_master_ip.py 探 master;禁占位 http server
    # 占用 PORT——会与 vLLM --master-port PP/DP 通信冲突,worker 卡在 distributed_init)。
    # vLLM ≥ v0.30.0rc1 启用 external/hybrid DP LB 模式时,worker 禁 --headless(报反向错误);
    # 通过环境变量 DP_LB_MODE=external|hybrid 显式声明模式,worker 不加 --headless。
    DP_LB_MODE="${DP_LB_MODE:-none}"
    if [ "${DP_LB_MODE}" = "external" ] || [ "${DP_LB_MODE}" = "hybrid" ]; then
        echo "[pd] ${DP_LB_MODE}-dp-lb: worker runs full API server, no --headless"
    else
        echo "[pd] default-dp-lb: worker with --headless (no placeholder http server)"
        export DATA_PARALLEL_SIZE=2
        WORKER_OPTS="--headless"
    fi
else
    echo "[pd] Current node is MASTER (POD_IP=${POD_IP:-N/A}, master=${MASTER_IP:-N/A}, VLLM_ROLE=${VLLM_ROLE})"
fi

echo "[pd] master_ip=${MASTER_IP}, local_ip=${POD_IP:-N/A}, nic=${NIC_NAME}, dp_rank=${DP_START_RANK}, VLLM_ROLE=${VLLM_ROLE}, PORT=${PORT}, TP=${TP_SIZE}, DP=${DATA_PARALLEL_SIZE}"

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
# 是否设置、取何值一律以用户确认模型的适配文档为准:
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}"
export HCCL_BUFFSIZE="${HCCL_BUFFSIZE:-512}"
export OMP_PROC_BIND="${OMP_PROC_BIND:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
# 多机通信超时与就绪容忍(多节点大模型首启慢,需放宽,以官方适配文档为准):
export VLLM_RPC_TIMEOUT="${VLLM_RPC_TIMEOUT:-360000}"
export VLLM_EXECUTE_MODEL_TIMEOUT_SECONDS="${VLLM_EXECUTE_MODEL_TIMEOUT_SECONDS:-3000}"
export HCCL_EXEC_TIMEOUT="${HCCL_EXEC_TIMEOUT:-200}"
export HCCL_CONNECT_TIMEOUT="${HCCL_CONNECT_TIMEOUT:-120}"
export VLLM_ENGINE_READY_TIMEOUT_S="${VLLM_ENGINE_READY_TIMEOUT_S:-1200}"
# 950DT 超平面通信(UBC 协议)自动配置,作为镜像无 hixl 自动生成功能时的兜底
export ASCEND_LOCAL_COMM_RES="${ASCEND_LOCAL_COMM_RES:-{\"version\":\"1.3\"}}"

# ---------- unofficial-ascend-tools 获取与入口解析 ----------
# 该 wheel 只提供 console script `mindcluster-tools`(entry_points.txt),没有可供 `python3 -m`
# 调用的同名模块;且 rankinfo/main.py 无 `if __name__ == "__main__"` 守卫,不能用 `python3 -m` 调用
# (会 exit 0 且不产出任何文件,把"必然报错"变成"静默失败")。
install_ascend_tools() {
    local wheel="${HCCL_TOOLS_WHEEL:-}"
    if [ -n "${wheel}" ]; then
        # 显式指定了 HCCL_TOOLS_WHEEL 就必须用它: 文件不存在直接报错,禁止静默回落 PyPI
        if [ ! -f "${wheel}" ]; then
            echo "[ERROR] HCCL_TOOLS_WHEEL=${wheel} 不存在,离线安装失败(不会回落到 PyPI),请检查该路径" >&2
            return 1
        fi
        python3 -m pip install --no-index --no-deps --quiet "${wheel}" || {
            echo "[ERROR] 安装 unofficial-ascend-tools 失败(本地 wheel: ${wheel})" >&2
            return 1
        }
        return 0
    fi
    local bundled="${OFFLINE_PKG_DIR}/unofficial_ascend_tools-0.0.7rc4-py3-none-any.whl"
    if [ -f "${bundled}" ]; then
        python3 -m pip install --no-index --no-deps --quiet "${bundled}" || {
            echo "[ERROR] 安装 unofficial-ascend-tools 失败(内置 wheel: ${bundled})" >&2
            return 1
        }
        return 0
    fi
    echo "[hixlep] 未指定 HCCL_TOOLS_WHEEL,从 PyPI 安装 unofficial-ascend-tools==0.0.7rc4"
    python3 -m pip install --quiet "unofficial-ascend-tools==0.0.7rc4" || {
        echo "[ERROR] 安装 unofficial-ascend-tools==0.0.7rc4 失败(PyPI 不可达);离线环境请下载同版本 wheel 后用 HCCL_TOOLS_WHEEL 指定本地路径" >&2
        return 1
    }
}

# 调用 rootinfo 并校验产物: console script 优先,不在 PATH(pip install --user 常见)时回退包入口
run_mindcluster_rootinfo() {
    local out="$1" rc
    # &&/|| 形式避免 set -e 下直接退出,保证能捕获真实退出码
    if command -v mindcluster-tools >/dev/null 2>&1; then
        mindcluster-tools rootinfo --product_type server --output "${out}" && rc=0 || rc=$?
    else
        python3 -c 'from unofficial_ascend_tools.rankinfo.main import main; import sys; sys.exit(main())' \
            rootinfo --product_type server --output "${out}" && rc=0 || rc=$?
    fi
    if [ "${rc}" -ne 0 ]; then
        echo "[ERROR] mindcluster-tools rootinfo 执行失败(rc=${rc}): 入口解析或工具执行异常,请确认 unofficial-ascend-tools 已安装、Ascend HDK 驱动与 npu-smi 可用" >&2
        return "${rc}"
    fi
    # 不只信退出码: 实测 `python3 -m ...` 形式会 exit 0 却不产出文件,必须断言产物存在且非空
    if [ ! -s "${out}" ]; then
        echo "[ERROR] mindcluster-tools rootinfo 退出码 0 但 ${out} 不存在或为空,入口未真正执行" >&2
        return 1
    fi
    return 0
}

# ---------- hixlep 自检与按需生成(PD 分离 P↔D KV 传输必需) ----------
# vllm-ascend 通过 kv_connector_extra_config.ascend_local_comm_res_path 显式读取;
# 若主机侧 /etc/hixlep 缺失(裸机环境或非 cloud_a5:0.5 镜像),使用内置脚本自动生成:
#   - generate_ep.py(随 scripts/a5_hixlep/ 复制到产物 a5_hixlep/ 目录,生成 /etc/hixlep/ub_endpoint_npu_*.json)
#   - unofficial-ascend-tools==0.0.7rc4(运行时从 PyPI 安装,生成 /etc/hccl_rootinfo.json;不随 skill 内置)
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
    echo "[hixlep] ${HIXLEP_PATH} 缺失,使用内置脚本自动生成(PD 分离 UB 通信必需)"

    # 1) hccl_rootinfo.json 缺失则运行时获取 unofficial-ascend-tools 生成
    #    该 wheel 不随 skill 内置(二进制文件不在产物文件类型白名单);运行时从 PyPI 安装同版本,
    #    离线环境可下载同版本 wheel 后用 HCCL_TOOLS_WHEEL 指定本地路径(必须真实存在)。
    if [ ! -s "${HCCL_ROOTINFO_PATH}" ]; then
        echo "[hixlep] ${HCCL_ROOTINFO_PATH} 缺失,获取 unofficial-ascend-tools==0.0.7rc4 生成"
        install_ascend_tools || exit 1
        run_mindcluster_rootinfo "${HCCL_ROOTINFO_PATH}" || exit 1
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
    #    --local --server: 用 server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡;多机 PD 分离沿用同模板
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

# PD 分离角色必触发(P↔D 跨卡 UB 通信)
if [ "${VLLM_ROLE}" = "prefill" ] || [ "${VLLM_ROLE}" = "decode" ]; then
    generate_hixlep
fi

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
# PD 专用普通参数(无 JSON 时可用;含 JSON 请加进 MODEL_ARGS 数组)
if [ -n "${PD_EXTRA_ARGS:-}" ]; then
    read -r -a PD_EXTRA_ARGS_ARR <<< "${PD_EXTRA_ARGS}"
    MODEL_ARGS+=("${PD_EXTRA_ARGS_ARR[@]}")
fi

# PD 专用 kv-transfer-config(MooncakeConnectorV1,P↔D KV cache 经 UB 传输)
# kv_role: prefill=kv_producer / decode=kv_consumer,由 VLLM_ROLE 决定
# kv_port: prefill/decode 各自监听端口需不同;需避开 Mooncake AscendDirectTransport 随机端口范围
#   [20000, 20000 + npu_per_node × 1000): 8 卡 → ≥28000;16 卡 → ≥36000(官网 F4)
KV_PORT="${KV_PORT:-36000}"
if [ "${VLLM_ROLE}" = "prefill" ]; then
    KV_ROLE="kv_producer"
else
    KV_ROLE="kv_consumer"
fi
if [ "${KV_PORT}" = "36000" ] && [ "${VLLM_ROLE}" = "decode" ]; then
    KV_PORT="36100"
fi
# kv-transfer-config JSON 单独拼装(数组传参时整体作为一个 argv 元素)
# kv_connector_extra_config.{prefill,decode}.{tp_size,dp_size} 必须与各角色 vLLM 引擎
# 的 --tensor-parallel-size / --data-parallel-size 一致(描述该角色 KV cache 分片方式):
#   tp_size = TP_SIZE(组内张量并行度)
#   prefill dp_size = PREFILL_DP_SIZE, decode dp_size = DECODE_DP_SIZE(按官网 PD 脚本推导)
# 硬编码为 1 在 TP>1 或 DP>1 时触发 pydantic 校验: conflicting tensor/data parallel size
KV_TRANSFER_CONFIG="{\"kv_connector\": \"MooncakeConnectorV1\", \"kv_role\": \"${KV_ROLE}\", \"kv_port\": \"${KV_PORT}\", \"kv_buffer_device\": \"npu\", \"kv_connector_extra_config\": {\"prefill\": {\"dp_size\": ${PREFILL_DP_SIZE}, \"tp_size\": ${TP_SIZE}}, \"decode\": {\"dp_size\": ${DECODE_DP_SIZE}, \"tp_size\": ${TP_SIZE}}, \"ascend_local_comm_res_path\": \"${HIXLEP_PATH}\"}}"
PD_ARGS=(--kv-transfer-config "${KV_TRANSFER_CONFIG}")

# ---------- 启动 vllm-ascend OpenAI 兼容服务(PD 角色实例) ----------
# 不同模型的参数(如 --quantization, --dtype, --trust-remote-code)以
# vllm-ascend 官方模型适配文档为准;同一模型在不同芯片型号(910B/910C/310P)
# 与不同卡数下的参数也可能不同,请按目标资源规格从适配文档核对后,
# 将模型特有参数追加到上方 MODEL_ARGS 数组中
#
# 无条件传 --data-parallel-* 参数(对齐 A2 成功脚本): DP=1 时也传
# --data-parallel-size 1 --data-parallel-address "${MASTER_IP}"(空字符串),
# vLLM 内部按 DP=1 走单实例退化,master/worker 判定由 POD_IP/MASTER_IP 比较决定。
exec vllm serve "${MODEL_PATH}" \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --served-model-name "${MODEL_NAME}" \
    --tensor-parallel-size "${TP_SIZE}" \
    --data-parallel-size "${DATA_PARALLEL_SIZE}" \
    --data-parallel-size-local "${DATA_PARALLEL_SIZE_LOCAL}" \
    --data-parallel-start-rank "${DP_START_RANK}" \
    --data-parallel-address "${MASTER_IP}" \
    --data-parallel-rpc-port "${DATA_PARALLEL_RPC_PORT}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --dtype "${DTYPE}" \
    --trust-remote-code \
    ${WORKER_OPTS} \
    "${MODEL_ARGS[@]}" \
    "${PD_ARGS[@]}"
