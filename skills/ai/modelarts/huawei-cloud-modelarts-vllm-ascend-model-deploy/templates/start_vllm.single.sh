#!/bin/bash
# vllm-ascend 单节点启动模板(单机单卡/多卡 TP;内置权重挂载自检)
# 多副本由 ModelArts 部署副本数承载,模板无需 --data-parallel-size

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ---------- 环境变量(带默认值) ----------
# 模型权重挂载路径: ModelArts 从 OBS 挂载的权重目录
MODEL_PATH="${MODEL_PATH:-/home/ma-user/model}"
# 对外暴露的模型名(API 调用时的 model 字段)
MODEL_NAME="${MODEL_NAME:-model}"
# 张量并行度 = NPU 卡数(禁从 ASCEND_RT_VISIBLE_DEVICES 动态推导,可能只给单卡导致显存不足)
TP_SIZE="${TP_SIZE:-2}"
# 最大上下文长度
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
# 显存利用率
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.9}"
# 精度类型: auto / float16 / bfloat16(昇腾上大模型通常用 bfloat16)
DTYPE="${DTYPE:-bfloat16}"
# 显式指定使用的 NPU 卡(单机 0,1,2,3...)
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0,1}"
# 服务监听端口(ModelArts 健康检查探针使用同一端口)
PORT="${PORT:-8080}"
# 目标芯片型号(仅记录用途: 910B/910C(A3)/310P 等,不同芯片的
# dtype/量化/并行参数可能不同,务必以 vllm-ascend 对应芯片的适配文档为准)
CHIP_MODEL="${CHIP_MODEL:-}"

# hixlep 配置目录(A5 UB 超平面通信所需,单机多卡 TP 经 UB 链路跨卡通信;
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 读取,
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

# ---------- 昇腾环境变量(默认值仅供参考,以模型适配文档为准) ----------
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}"
export HCCL_BUFFSIZE="${HCCL_BUFFSIZE:-512}"
export OMP_PROC_BIND="${OMP_PROC_BIND:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
# 视模型/版本按需启用:
# export VLLM_USE_V1="${VLLM_USE_V1:-1}"
# export TASK_QUEUE_ENABLE="${TASK_QUEUE_ENABLE:-1}"
# export VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-true}"
# export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2
# 950DT 超平面通信(UBC 协议)自动配置,作为镜像无 hixl 自动生成功能时的兜底
export ASCEND_LOCAL_COMM_RES="${ASCEND_LOCAL_COMM_RES:-{\"version\":\"1.3\"}}"

# ---------- hixlep 自检与按需生成(A5 单机多卡 TP>1 跨卡 UB 通信必需) ----------
# 仅 A5(950DT/950PR/950) 系列且 TP>1 时触发;A2/A3 走 RoCE 跳过,A5 单机单卡 TP=1 无跨卡通信跳过
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
    # A5 单机单卡 TP=1 无跨卡通信,跳过
    if [ "${TP_SIZE}" -le 1 ]; then
        echo "[hixlep] TP_SIZE=${TP_SIZE}(单卡),无跨卡 UB 通信,跳过 hixlep 生成"
        return 0
    fi
    local existing
    existing=$(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)
    if [ "${existing}" -ge 1 ]; then
        echo "[hixlep] ${HIXLEP_PATH} 已有 ${existing} 个 endpoint 文件,跳过生成"
        return 0
    fi
    echo "[hixlep] ${HIXLEP_PATH} 缺失,使用 skill 内置离线包生成(A5 单机多卡 UB 通信必需)"

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
    #    -s: server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡
    local gen_ep="${SCRIPT_DIR}/generate_ep.py"
    if [ ! -f "${gen_ep}" ]; then
        echo "[ERROR] ${gen_ep} 不存在,无法生成 hixlep(产物生成时应从 scripts/ 一并复制)" >&2
        exit 1
    fi
    ( cd "${SCRIPT_DIR}" && python3 generate_ep.py -s ) || {
        echo "[ERROR] generate_ep.py 执行失败,检查 ${HCCL_ROOTINFO_PATH} 与 ${ROUTE_CONF_PATH} 是否匹配本机拓扑" >&2
        exit 1
    }

    echo "[hixlep] 生成完成,endpoint 文件数: $(ls "${HIXLEP_PATH}"/ub_endpoint_npu_*.json 2>/dev/null | wc -l)"
}

# 单机多卡(A5 + TP>1)触发
generate_hixlep

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

# ---------- 启动 vllm-ascend OpenAI 兼容服务 ----------
exec vllm serve "${MODEL_PATH}" \
    --served-model-name "${MODEL_NAME}" \
    --tensor-parallel-size "${TP_SIZE}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --dtype "${DTYPE}" \
    --port "${PORT}" \
    --trust-remote-code \
    "${MODEL_ARGS[@]}"
