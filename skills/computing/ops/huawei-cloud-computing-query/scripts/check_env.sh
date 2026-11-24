#!/bin/bash
# 华为云资源查询 - 环境检查前置脚本
#
# 默认轻量模式：只做 Python 版本、脚本语法、SDK 可导入性和凭证存在性检查；
# 不创建 venv、不安装依赖、不调用云 API。缺少 AK/SK 时打印 SKIP 并以 0 退出，
# 因此可以安全地在无凭证裸机或评测环境中作为文档主推命令。
# 严格模式：--full，安装依赖并调用 IAM 校验凭证；缺凭证 exit 2，网络/镜像不可达 exit 3。

MODE="light"
ARGS=()

usage() {
    echo "Usage: bash scripts/check_env.sh [--full] [--force] [--ttl <seconds>] [--upgrade]"
    echo "Default: lightweight static check; works without credentials and exits 0."
    echo "  --full     strict check: install dependencies and validate credentials"
    echo "  --force    ignore the cached environment-check result"
    echo "  --ttl <s>  cache TTL in seconds (0 disables the cache)"
}

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --full) MODE="full" ;;
        --light) MODE="light" ;;
        *) ARGS+=("$arg") ;;
    esac
done

echo ""
if [ "$MODE" = "full" ]; then
    echo "  （严格模式：安装依赖并校验凭证）"
else
    echo "  （轻量模式：不创建 venv、不安装依赖；严格校验请使用 --full）"
fi

# 步骤 1：检查 Python 是否存在
echo ""
echo "[1/3] 检查 Python 环境"

PYTHON_CMD=""

# 优先使用项目 .venv 中的 Python
if [ -n "${BASH_SOURCE:-}" ]; then
    SCRIPT_PATH="${BASH_SOURCE[0]}"
else
    SCRIPT_PATH="$0"
fi
SCRIPT_DIR=$(cd "$(dirname "$SCRIPT_PATH")" >/dev/null 2>&1 && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
else
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            test_ver=$("$cmd" --version 2>&1)
            if echo "$test_ver" | grep -q "^Python [0-9]"; then
                PYTHON_CMD="$cmd"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "FAIL: 未检测到可用的 Python"
    echo ""
    echo "请先安装 Python 3.6+，根据当前系统参考："
    echo "  macOS   : brew install python"
    echo "  Ubuntu  : apt-get install python3 python3-pip（以管理员身份执行）"
    echo "  CentOS  : yum install python3（以管理员身份执行）"
    exit 1
fi

echo "OK: 找到 Python: ${PYTHON_CMD}"

# 步骤 2：检查 Python 版本
echo ""
echo "[2/3] 检查 Python 版本"

PYTHON_VERSION=$(${PYTHON_CMD} --version 2>&1 | awk '{print $2}')

if [ -z "${PYTHON_VERSION}" ]; then
    echo "FAIL: 无法获取 Python 版本"
    exit 1
fi

echo "  当前版本: ${PYTHON_VERSION}"

MAJOR=$(echo "${PYTHON_VERSION}" | cut -d'.' -f1)
MINOR=$(echo "${PYTHON_VERSION}" | cut -d'.' -f2)

if [ -z "${MAJOR}" ] || [ -z "${MINOR}" ]; then
    echo "FAIL: 无法解析 Python 版本: ${PYTHON_VERSION}"
    exit 1
fi

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 6 ]; }; then
    echo "FAIL: Python 版本过低 ($PYTHON_VERSION)，需要 >= 3.6"
    echo ""
    echo "请升级 Python 后重试。"
    exit 1
fi

echo "OK: Python ${PYTHON_VERSION} >= 3.6"

# 步骤 3：调用 Python 详细检查
# 总超时（秒）：轻量/严格模式统一兜底，分步超时与可读报错由 ensure_env.py 负责
TOTAL_TIMEOUT="${HW_ENV_CHECK_TIMEOUT:-120}"
case "${TOTAL_TIMEOUT}" in
    ''|*[!0-9]*) TOTAL_TIMEOUT=120 ;;
esac
export HW_ENV_CHECK_TIMEOUT="${TOTAL_TIMEOUT}"
export HW_ENV_CHECK_START_TS="${HW_ENV_CHECK_START_TS:-$(date +%s)}"
export PYTHONUNBUFFERED=1

if [ "$MODE" = "full" ]; then
    MODE_ARG="--full"
    echo ""
    echo "[3/3] 执行详细检查"
    echo "  首次执行可能创建虚拟环境并安装依赖，最长等待 ${TOTAL_TIMEOUT}s（可用 HW_ENV_CHECK_TIMEOUT 调整）"
else
    MODE_ARG="--light"
    echo ""
    echo "[3/3] 执行轻量静态检查（不创建 venv、不安装依赖，最长等待 ${TOTAL_TIMEOUT}s）"
fi
echo "--------------------------------------------------"

PYTHON_SCRIPT="${SCRIPT_DIR}/ensure_env.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "FAIL: 未找到检查脚本"
    echo "  预期路径: $PYTHON_SCRIPT"
    echo "  当前目录: $(pwd)"
    exit 1
fi

if command -v timeout >/dev/null 2>&1; then
    # 透传参数（--force 强制重查、--ttl/--upgrade 等），结果默认缓存；
    # 失败/跳过结果使用短 TTL（ensure_env.py 内默认 300s），避免重复全量重跑。
    timeout --signal=TERM "${TOTAL_TIMEOUT}s" "${PYTHON_CMD}" "${PYTHON_SCRIPT}" "${MODE_ARG}" "${ARGS[@]}"
    EXIT_CODE=$?
    TIMED_OUT=0
    if [ "${EXIT_CODE}" -eq 124 ] || [ "${EXIT_CODE}" -eq 137 ] || [ "${EXIT_CODE}" -eq 143 ]; then
        TIMED_OUT=1
    fi
else
    # 没有 timeout 命令时的可移植看门狗
    "${PYTHON_CMD}" "${PYTHON_SCRIPT}" "${MODE_ARG}" "${ARGS[@]}" &
    CHILD_PID=$!
    ( sleep "${TOTAL_TIMEOUT}"; kill -TERM "${CHILD_PID}" 2>/dev/null ) &
    WATCHDOG_PID=$!
    wait "${CHILD_PID}"
    EXIT_CODE=$?
    kill "${WATCHDOG_PID}" 2>/dev/null
    wait "${WATCHDOG_PID}" 2>/dev/null
    TIMED_OUT=0
    if [ "${EXIT_CODE}" -eq 137 ] || [ "${EXIT_CODE}" -eq 143 ]; then
        TIMED_OUT=1
    fi
fi

echo ""
echo "=================================================="

if [ "${TIMED_OUT}" -eq 1 ]; then
    echo "FAIL: 环境检查超时（超过 ${TOTAL_TIMEOUT}s），可能网络或依赖镜像不可达"
    echo "  处理建议: 检查网络/代理后重试，或设置 HW_ENV_CHECK_TIMEOUT=<更大的秒数>"
    exit 3
fi

if [ "$MODE" = "light" ]; then
    if [ "${EXIT_CODE}" -eq 0 ]; then
        echo "✓ 轻量环境检查通过（严格校验请执行 bash scripts/check_env.sh --full）"
        exit 0
    fi
    echo "✗ 轻量环境检查未通过（exit ${EXIT_CODE}），请按上述提示修复"
    exit "${EXIT_CODE}"
fi

if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "✓ 环境检查通过"

    # 读取自动获取的 project_id 并导出
    PROJECT_ID_FILE="${PROJECT_ROOT}/.project_id"
    if [ -f "$PROJECT_ID_FILE" ]; then
        export HW_PROJECT_ID=$(cat "$PROJECT_ID_FILE")
        echo "HW_PROJECT_ID 已设置: $HW_PROJECT_ID"
    fi
    exit 0
elif [ "${EXIT_CODE}" -eq 2 ]; then
    echo "✗ 缺少凭证，请设置 HW_ACCESS_KEY / HW_SECRET_KEY、HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY，或 AKSK=AK/SK 后重试"
    exit 2
else
    echo "✗ 环境未就绪（exit 3），请按上述提示修复"
    exit 3
fi
