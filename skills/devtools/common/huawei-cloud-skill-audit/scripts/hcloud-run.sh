#!/bin/bash
# hcloud-run.sh — 所有 hcloud 调用的强制包装器（质量上报统一入口）
# 用法: bash scripts/hcloud-run.sh <Service> <Operation> [--param=value ...]
# 等价于执行: skill-quality-cli run --skill-name <name> -- hcloud "$@"（总是先经 CLI 上报）
#
# 载体: 唯一载体 skill-quality-cli（由 scripts/ensure_cli.sh 幂等就绪）。
#   不保留内嵌 CLI 副本（已按 C6 清理），也不保留裸 hcloud 降级路径：
#   CLI 不可用即失败退出（exit 1），避免"静默无上报"的假成功。
#
# skill 名可通过 SKILL_QUALITY_SKILL_NAME 覆盖，默认 huawei-cloud-skill-audit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="${SKILL_QUALITY_SKILL_NAME:-huawei-cloud-skill-audit}"

# 1. 确保 skill-quality-cli 已安装（幂等）
bash "$SCRIPT_DIR/ensure_cli.sh" >/dev/null 2>&1 || true

# ensure_cli.sh 装到 ~/.local/bin：确保其可被发现（该目录可能不在 PATH 中）
export PATH="$HOME/.local/bin:$PATH"

# 2. 单一载体校验：缺失即失败退出（不降级为裸 hcloud）
if ! command -v skill-quality-cli >/dev/null 2>&1; then
    echo "❌ ERROR: skill-quality-cli 不可用（唯一 hcloud 载体）。请先执行 bash \"$SCRIPT_DIR/ensure_cli.sh\"（或手动 skill-quality-cli install）后重试；本次调用已终止，未执行 hcloud。" >&2
    exit 1
fi

exec skill-quality-cli run --skill-name "$SKILL_NAME" -- hcloud "$@"