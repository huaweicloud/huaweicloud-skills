#!/bin/bash
set -euo pipefail
# hcloud-run.sh — 所有 hcloud 调用的强制包装器（质量上报统一入口）
# 用法: bash scripts/hcloud-run.sh <Service> <Operation> [--param=value ...]
# 等价于执行: hcloud "$@" ，但总是先经 skill-quality-cli 上报（脚本级强制，不依赖 agent 自觉包装）
#
# 载体优先级（与 SKILL.md「Quality Reporting (Unified CLI)」一致）:
#   ① PATH 中的 skill-quality-cli → run 包裹执行（自动上报）
#   ② 不可用 → 裸 hcloud 执行并打印警告（不阻塞业务）
#   (in-skill 载体 scripts/cli/ 已删除)
#
# 区域: 通过 HW_CLI_REGION 环境变量注入 KooCLI 全局参数 --cli-region
#       (未设置 HW_CLI_REGION 或命令已含 --cli-region[=..] 时不追加)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="${SKILL_QUALITY_SKILL_NAME:-huawei-cloud-vod-collector}"
INSTALL_DIR="${HOME}/.local/bin"

# 0. ensure_cli.sh 的目标目录: 先加入 PATH, 否则该目录不在 PATH 时
#    ensure_cli 每次都会误判未安装而重复下载, 破坏幂等
export PATH="${INSTALL_DIR}:${PATH}"

# 1. 确保 skill-quality-cli 已安装（幂等；失败静默，不阻塞）
bash "$SCRIPT_DIR/ensure_cli.sh" >/dev/null 2>&1 || true

# 2. 可选: 注入 KooCLI 全局参数 --cli-region（通过 HW_CLI_REGION 指定）
#    遍历 "$@" 精确匹配参数项，避免业务参数值里出现 --cli-region 字样时误判
if [ -n "${HW_CLI_REGION:-}" ]; then
    _has_region=false
    for _arg in "$@"; do
        case "$_arg" in
            --cli-region|--cli-region=*) _has_region=true; break ;;
        esac
    done
    if ! $_has_region; then
        set -- "$@" --cli-region="${HW_CLI_REGION}"
    fi
fi

# 3. 选择载体并执行
#    载体可用性: 不仅要求命令存在, 还要 version 可执行(避免损坏/残缺安装阻断 hcloud 调用)
if command -v skill-quality-cli >/dev/null 2>&1 && skill-quality-cli version >/dev/null 2>&1; then
    exec skill-quality-cli run --skill-name "$SKILL_NAME" -- hcloud "$@"
else
    printf '%s\n' "⚠️ WARNING: skill-quality-cli 不可用或版本校验失败，降级为裸 hcloud（本次无质量上报）" >&2
    exec hcloud "$@"
fi