#!/bin/bash
# 华为云资源查询 - 环境检查前置脚本

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
    echo "  Ubuntu  : apt update && apt install -y python3 python3-pip"
    echo "  CentOS  : yum install -y python3"
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
echo ""
echo "[3/3] 执行详细检查"
echo "--------------------------------------------------"

PYTHON_SCRIPT="${SCRIPT_DIR}/ensure_env.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "FAIL: 未找到检查脚本"
    echo "  预期路径: $PYTHON_SCRIPT"
    echo "  当前目录: $(pwd)"
    exit 1
fi

"${PYTHON_CMD}" "${PYTHON_SCRIPT}"
EXIT_CODE=$?

echo ""
echo "=================================================="

if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "✓ 环境检查通过"
    exit 0
else
    echo "✗ 环境未就绪，请按提示修复"
    exit 1
fi
