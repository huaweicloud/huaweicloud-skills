#!/bin/bash
# scaffold-quality-cli.sh — 为创建的 skill 集成 CLI 质量上报（Phase 3 必做，幂等）
# 用法: bash scripts/scaffold-quality-cli.sh -p <skill-path> [-n <skill-name>]
#   -p <skill-path>  目标 skill 目录（必填）
#   -n <skill-name>  上报 skill 名（缺省取目录名; 运行时可用 SKILL_QUALITY_SKILL_NAME 覆盖）
#   写入: scripts/ensure_cli.sh, scripts/cli/{cli_entry.py,cli_reporting.py}（in-skill 载体）,
#         scripts/hcloud-run.sh（强制 hcloud 入口, skill 名内置）
#   兼容旧式位置参数调用: scaffold-quality-cli.sh <skill-path> [skill-name]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_PATH=""
SKILL_NAME=""

usage() {
    echo "用法: bash scripts/scaffold-quality-cli.sh -p <skill-path> [-n <skill-name>]" >&2
}

while getopts "p:n:h" opt; do
    case "$opt" in
        p) SKILL_PATH="$OPTARG" ;;
        n) SKILL_NAME="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# 兼容旧式位置参数调用(scaffold-quality-cli.sh <skill-path> [skill-name])
if [ -z "$SKILL_PATH" ] && [ "$#" -ge 1 ]; then
    SKILL_PATH="$1"
fi
if [ -z "$SKILL_NAME" ] && [ "$#" -ge 2 ]; then
    SKILL_NAME="$2"
fi

if [ -z "$SKILL_PATH" ] || [ ! -d "$SKILL_PATH" ]; then
    echo "错误: skill-path 无效或不存在: ${SKILL_PATH:-<空>}" >&2
    usage
    exit 1
fi
SKILL_NAME="${SKILL_NAME:-$(basename "$SKILL_PATH")}"

mkdir -p "$SKILL_PATH/scripts/cli"
cp "$SCRIPT_DIR/ensure_cli.sh"       "$SKILL_PATH/scripts/ensure_cli.sh"
cp "$SCRIPT_DIR/cli/cli_entry.py"    "$SKILL_PATH/scripts/cli/cli_entry.py"
cp "$SCRIPT_DIR/cli/cli_reporting.py" "$SKILL_PATH/scripts/cli/cli_reporting.py"

cat > "$SKILL_PATH/scripts/hcloud-run.sh" <<RUNEOF
#!/bin/bash
set -euo pipefail
# hcloud-run.sh — 本 skill 所有 hcloud 调用的强制包装器（质量上报统一入口）
# 由 huawei-cloud-skill-creator scripts/scaffold-quality-cli.sh 生成；请勿手动修改
# 载体优先级: PATH skill-quality-cli -> in-skill cli_entry.py -> 裸 hcloud + 警告
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="\${SKILL_QUALITY_SKILL_NAME:-$SKILL_NAME}"

bash "\$SCRIPT_DIR/ensure_cli.sh" >/dev/null 2>&1 || true

if command -v skill-quality-cli >/dev/null 2>&1; then
    exec skill-quality-cli run --skill-name "\$SKILL_NAME" -- hcloud "\$@"
elif [ -f "\$SCRIPT_DIR/cli/cli_entry.py" ]; then
    exec python3 "\$SCRIPT_DIR/cli/cli_entry.py" --no-auto-upgrade run --skill-name "\$SKILL_NAME" -- hcloud "\$@"
else
    echo "⚠️ WARNING: skill-quality-cli 与 in-skill 载体均不可用, 降级裸 hcloud (本次无上报)" >&2
    exec hcloud "\$@"
fi
RUNEOF
chmod +x "$SKILL_PATH/scripts/hcloud-run.sh"
echo "✔ scaffold-quality-cli: $SKILL_PATH/scripts/{ensure_cli.sh, cli/, hcloud-run.sh} (skill=$SKILL_NAME) 就绪"