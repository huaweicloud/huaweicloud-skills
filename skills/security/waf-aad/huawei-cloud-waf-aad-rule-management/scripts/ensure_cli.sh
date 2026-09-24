#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 可用（存在性检查；缺失时提示手动安装，固定版本 + SHA256 校验）
# 由 huawei-cloud-skill-quality-cli-inject v3.7.3 自动生成，请勿手动修改
# 调用方式: source scripts/ensure_cli.sh (推荐, export PATH 对当前会话生效) 或 bash scripts/ensure_cli.sh
set -euo pipefail

# 安装目录：优先使用环境变量 SKILL_QUALITY_CLI_DIR 指定的目录，缺省为 ${HOME}/.local/bin
CLI_BIN_DIR="${SKILL_QUALITY_CLI_DIR:-${HOME}/.local/bin}"
CLI_BIN="${CLI_BIN_DIR}/skill-quality-cli"

# 确保 CLI 安装目录在当前 PATH 中(已装但 PATH 缺失时调用)
_fix_path() {
    case ":$PATH:" in
        *":${CLI_BIN_DIR}:"*) return 0 ;;
    esac
    export PATH="${CLI_BIN_DIR}:${PATH}"
    echo "已将 ${CLI_BIN_DIR} 加入 PATH"
    # 软链到 PATH 内第一个可写目录(如 /usr/local/bin), 使后续新 shell 也能直接调用
    # 注意: 跳过 CLI_BIN_DIR 自身(export 已保证它在 PATH, 自链接无意义且会失败)
    _ln_dir=""
    IFS=: read -r -a _path_dirs <<< "$PATH"
    for _d in "${_path_dirs[@]}"; do
        if [ -n "$_d" ] && [ "$_d" != "$CLI_BIN_DIR" ] && [ -w "$_d" ]; then
            _ln_dir="$_d"
            break
        fi
    done
    if [ -n "$_ln_dir" ]; then
        ln -sf "${CLI_BIN}" "${_ln_dir}/skill-quality-cli" 2>/dev/null || true
        echo "已创建软链 ${_ln_dir}/skill-quality-cli (新 shell 也可直接用)"
    fi
}

# 结束脚本 — source 时 return 0（退出当前 source），直接执行时 exit 0
# （`return 0 2>/dev/null || exit 0`：直接执行时 return 报错被抑制，落到 exit 0）

# 1. 检查是否已安装且可用 — 双通道: PATH 内 或安装目录兜底(避免 PATH 缺失时误判未装)
if command -v skill-quality-cli &>/dev/null && skill-quality-cli version &>/dev/null 2>&1; then
    return 0 2>/dev/null || exit 0
fi
if [ -x "${CLI_BIN}" ] && "${CLI_BIN}" version &>/dev/null 2>&1; then
    _fix_path
    return 0 2>/dev/null || exit 0
fi

# 2. 未安装 → 提示手动安装。本脚本不执行运行时下载/拉取外部代码；
#    固定版本(v1.1.6) + SHA256 校验的手动安装步骤见 references/cli-installation-guide.md
echo "提示: 未检测到 skill-quality-cli，请按 references/cli-installation-guide.md 的" >&2
echo "      「安装 skill-quality-cli（固定版本 v1.1.6，SHA256 校验）」手动安装后重试。" >&2
echo "      质量上报为可选项：CLI 缺失时跳过上报，不阻塞本 skill 的业务执行。" >&2
return 0 2>/dev/null || exit 0
