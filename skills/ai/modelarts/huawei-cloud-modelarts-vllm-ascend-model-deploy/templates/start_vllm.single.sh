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
HIXLEP_PATH="${HIXLEP_PATH:-/tmp/hixlep}"
ROUTE_CONF_PATH="${ROUTE_CONF_PATH:-/lib/route.conf}"
HCCL_ROOTINFO_PATH="${HCCL_ROOTINFO_PATH:-/etc/hccl_rootinfo.json}"
# 是否在启动前自动生成 hixlep(默认开启,主机已挂载完整 hixlep 可设 AUTOGEN_HIXLEP=0)
AUTOGEN_HIXLEP="${AUTOGEN_HIXLEP:-1}"
# a5_hixlep 脚本目录(随 scripts/a5_hixlep/ 整目录复制到产物目录;
# generate_ep.py / fix_ub_endpoint.py / gen_route.sh 均在此目录,均可离线直接使用)
OFFLINE_PKG_DIR="${OFFLINE_PKG_DIR:-${SCRIPT_DIR}/a5_hixlep}"

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

# ---------- 量化参数 × 权重文件交叉校验 ----------
# BF16 原版权重无 quant_model_description.json,误带 --quantization ascend 会启动崩溃
# (ModelSlim Quantization Config Not Found);w8a8 量化版权重含该文件,误漏则推理精度退化
QUANT_DESC="${MODEL_PATH}/quant_model_description.json"
HAS_QUANT_ARG=0
for _a in "${MODEL_ARGS[@]:-}" "${EXTRA_ARGS:-}"; do
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

# ---------- hixlep 自检与按需生成(A5 单机多卡 TP>1 跨卡 UB 通信必需) ----------
# 仅 A5(950DT/950PR/950) 系列且 TP>1 时触发;A2/A3 走 RoCE 跳过,A5 单机单卡 TP=1 无跨卡通信跳过
# vllm-ascend 通过 additional-config.ascend_local_comm_res_path 显式读取;
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
    echo "[hixlep] ${HIXLEP_PATH} 缺失,使用内置脚本自动生成(A5 单机多卡 UB 通信必需)"

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
    #    --local --server: 用 server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡
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
