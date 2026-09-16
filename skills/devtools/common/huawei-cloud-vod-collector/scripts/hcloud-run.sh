#!/bin/bash
# hcloud-run.sh — 所有 hcloud 调用的强制包装器（质量上报统一入口）
# 用法: bash scripts/hcloud-run.sh <Service> <Operation> [--param=value ...]
# 等价于执行: hcloud "$@" ，但总是先经 skill-quality-cli 上报（脚本级强制，不依赖 agent 自觉包装）
#
# 载体优先级（与 SKILL.md「Quality Reporting (Unified CLI)」一致）:
#   ① PATH 中的 skill-quality-cli → run 包裹执行（自动上报）
#   ② in-skill 源码 scripts/cli/cli_entry.py（零依赖，无需下载）→ run 包裹执行
#   ③ 均不可用 → 裸 hcloud 执行并打印警告（不阻塞业务）
#
# skill 名可通过 SKILL_QUALITY_SKILL_NAME 覆盖，默认 huawei-cloud-skill-creator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="${SKILL_QUALITY_SKILL_NAME:-huawei-cloud-vod-collector}"

# 1. 确保 skill-quality-cli 已安装（幂等；失败静默，不阻塞）
bash "$SCRIPT_DIR/ensure_cli.sh" >/dev/null 2>&1 || true

# ensure_cli.sh 装到 ~/.local/bin：确保其可被发现（该目录可能不在 PATH 中）
export PATH="$HOME/.local/bin:$PATH"

# 2. 选择载体并执行
if command -v skill-quality-cli >/dev/null 2>&1; then
    exec skill-quality-cli run --skill-name "$SKILL_NAME" -- hcloud "$@"
elif [ -f "$SCRIPT_DIR/cli/cli_entry.py" ]; then
    exec python3 "$SCRIPT_DIR/cli/cli_entry.py" --no-auto-upgrade run --skill-name "$SKILL_NAME" -- hcloud "$@"
else
    echo "⚠️ WARNING: skill-quality-cli 与 in-skill 载体均不可用，降级为裸 hcloud（本次无质量上报）" >&2
    exec hcloud "$@"
fi