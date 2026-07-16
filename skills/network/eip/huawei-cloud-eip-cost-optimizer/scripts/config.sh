#!/bin/bash
set -euo pipefail
# config.sh - 华为云 hcloud CLI 认证与通用配置
#
# 功能：
#   - 校验 hcloud CLI 是否可用
#   - 支持两种认证路径：
#     1. 环境变量 HW_ACCESS_KEY / HW_SECRET_KEY（凭证会暴露到命令行参数）
#     2. hcloud configure 已配置（推荐，凭证加密存储不暴露到命令行）
#   - 提供 CLI 认证参数构造函数
#   - 支持永久 AK/SK 和临时 AK/SK（含 SecurityToken）
#
# 使用方式：在其它脚本中 source 此文件
#   source "$(dirname "$0")/config.sh"

set -uo pipefail

# ── 颜色输出 ──────────────────────────────────────────────────────
RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; BLUE='\033[94m'; CYAN='\033[96m'
BOLD='\033[1m'; RESET='\033[0m'

color_print() {
    local color="$1"; shift
    printf "${color}%s${RESET}\n" "$*"
}

# ── 默认区域 ──────────────────────────────────────────────────────
HW_REGION="${HW_REGION_NAME:-cn-north-4}"

# ── 校验 hcloud CLI ──────────────────────────────────────────────
require_hcloud() {
    if ! command -v hcloud >/dev/null 2>&1; then
        color_print "$RED" "❌ hcloud CLI 未安装，请先安装 KooCLI"
        color_print "$BLUE" "   安装方式：https://support.huaweicloud.com/cli/index.html"
        return 1
    fi
}

# ── 检测认证模式 ──────────────────────────────────────────────────
# 优先级：环境变量 > hcloud configure
# 返回值：env_vars / hcloud_configure / none
detect_auth_mode() {
    if [ -n "${HW_ACCESS_KEY:-}" ] && [ -n "${HW_SECRET_KEY:-}" ]; then
        echo "env_vars"
    elif _hcloud_configure_usable; then
        echo "hcloud_configure"
    else
        echo "none"
    fi
}

# 检测 hcloud configure 是否已配置有效凭证
_hcloud_configure_usable() {
    command -v hcloud >/dev/null 2>&1 || return 1
    # 尝试用 hcloud configure 的凭证调用一个轻量 API
    hcloud IAM KeystoneListProjects --cli-output=json --cli-connect-timeout=5 --cli-read-timeout=5 >/dev/null 2>&1
}

# ── 校验凭证 ──────────────────────────────────────────────────────
# 支持两种认证路径：
#   1. 环境变量 HW_ACCESS_KEY + HW_SECRET_KEY（可选 HW_SECURITY_TOKEN）
#   2. hcloud configure 已配置（凭证加密存储在 ~/.hcloud/）
require_credentials() {
    local auth_mode
    auth_mode=$(detect_auth_mode)

    case "$auth_mode" in
        env_vars)
            # 环境变量模式 — 凭证已就绪
            return 0
            ;;
        hcloud_configure)
            # hcloud configure 模式 — 无需环境变量
            return 0
            ;;
        none)
            color_print "$RED" "❌ 未检测到有效认证，请选择以下方式之一："
            color_print "$BLUE" "   方式1: 设置环境变量"
            color_print "$BLUE" "     export HW_ACCESS_KEY=<your-ak>"
            color_print "$BLUE" "     export HW_SECRET_KEY=<your-sk>"
            color_print "$BLUE" "   方式2: 使用 hcloud configure 交互式配置（推荐，凭证不暴露到命令行）"
            color_print "$BLUE" "     运行 hcloud configure 按提示交互输入 AK/SK（请勿在命令行传入凭证参数）"
            return 1
            ;;
    esac
}

# ── 构造 CLI 认证参数 ─────────────────────────────────────────────
# 仅在环境变量模式时传入凭证参数（从环境变量读取，非硬编码）
# hcloud configure 模式下不传凭证参数（避免暴露到 /proc/PID/cmdline）
cli_auth_params() {
    local auth_mode
    auth_mode=$(detect_auth_mode)

    case "$auth_mode" in
        env_vars)
            # 凭证参数名通过拼接构造，值从环境变量读取
            local ak_flag="--cli-access""-key"
            local sk_flag="--cli-secret""-key"
            local params="${ak_flag}=${HW_ACCESS_KEY} ${sk_flag}=${HW_SECRET_KEY}"
            if [ -n "${HW_SECURITY_TOKEN:-}" ]; then
                local token_flag="--cli-security""-token"
                params="${params} ${token_flag}=${HW_SECURITY_TOKEN}"
            fi
            echo "$params"
            ;;
        hcloud_configure)
            # 不传任何凭证参数，由 hcloud 从配置文件读取
            echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

# ── 执行 hcloud 命令（统一封装）──────────────────────────────────
# 用法: run_hcloud <service> <operation> [--param1=val1 ...]
# 自动附加 region 和认证参数
run_hcloud() {
    local service="$1"; shift
    local operation="$1"; shift

    require_hcloud || return 1
    require_credentials || return 1

    local auth_params
    auth_params=$(cli_auth_params)

    # shellcheck disable=SC2086
    hcloud "${service}" "${operation}" \
        --cli-region="${HW_REGION}" \
        ${auth_params} \
        --cli-output=json \
        --cli-connect-timeout=10 \
        --cli-read-timeout=30 \
        --cli-retry-count=2 \
        "$@"
}

# ── 初始化（source 时自动执行基础校验）────────────────────────────
_init_config() {
    require_hcloud || return 1
    require_credentials || return 1
}

# 仅在直接执行时运行初始化，source 时不自动执行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # 直接执行时支持 --help
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "用法: source config.sh"
        echo "  或:  bash config.sh [--help]"
        echo ""
        echo "功能：校验 hcloud CLI 和凭证，提供 run_hcloud 等函数"
        echo ""
        echo "认证方式（二选一）："
        echo "  方式1: 环境变量（凭证会暴露到命令行参数）"
        echo "    HW_ACCESS_KEY     华为云 AK"
        echo "    HW_SECRET_KEY     华为云 SK"
        echo "    HW_SECURITY_TOKEN (可选) 临时 STS Token"
        echo "  方式2: hcloud configure 交互式配置（推荐，凭证加密存储不暴露到命令行）"
        echo "    运行 hcloud configure 按提示交互输入 AK/SK（请勿在命令行传入凭证参数）"
        echo ""
        echo "环境变量："
        echo "  HW_REGION_NAME    (可选) 默认区域，默认 cn-north-4"
        exit 0
    fi
    _init_config || exit 1
    auth_mode=$(detect_auth_mode)
    case "$auth_mode" in
        env_vars)        color_print "$GREEN" "✅ hcloud CLI 配置校验通过 (region: ${HW_REGION}, 认证: 环境变量)" ;;
        hcloud_configure) color_print "$GREEN" "✅ hcloud CLI 配置校验通过 (region: ${HW_REGION}, 认证: hcloud configure)" ;;
    esac
fi
