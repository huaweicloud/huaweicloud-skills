#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 可用（幂等, 离线可用）
# 从技能包内置源码 scripts/cli/ 本地部署, 不再从外网下载脚本/包。
set -euo pipefail

# 0. 定位技能包内置的 CLI 源码（相对本脚本所在目录, 不依赖当前工作目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ENTRY="${SCRIPT_DIR}/cli/cli_entry.py"
BUNDLE_REPORTING="${SCRIPT_DIR}/cli/cli_reporting.py"
if [ ! -f "${BUNDLE_ENTRY}" ] || [ ! -f "${BUNDLE_REPORTING}" ]; then
    echo "错误: 技能包内置 CLI 源码缺失 (${SCRIPT_DIR}/cli/)" >&2
    exit 1
fi

# 1. PATH 兜底: 安装目录 ~/.local/bin 可能不在 PATH(裸命令 exit 127)
#    启动即导出到当前会话, 并幂等持久化到 ~/.bashrc / ~/.profile
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
if ! grep -qsF "$HOME/.local/bin" ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
if ! grep -qsF "$HOME/.local/bin" ~/.profile; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
fi

# 2. 已安装且可用则直接返回（优先 PATH, 兜底绝对路径）
CLI_BIN="$(command -v skill-quality-cli 2>/dev/null || true)"
if [ -z "$CLI_BIN" ] && [ -x "$HOME/.local/bin/skill-quality-cli" ]; then
    CLI_BIN="$HOME/.local/bin/skill-quality-cli"
fi
if [ -n "$CLI_BIN" ] && "$CLI_BIN" version >/dev/null 2>&1; then
    echo "skill-quality-cli 已就绪: $CLI_BIN"
    exit 0
fi

# 3. 未安装 → 用技能包内置源码本地部署 wrapper + Python fallback（无网络下载）
mkdir -p "$HOME/.local/bin/skill-quality-cli.d"
cp "${BUNDLE_ENTRY}" "$HOME/.local/bin/skill-quality-cli.d/cli_entry.py"
cp "${BUNDLE_REPORTING}" "$HOME/.local/bin/skill-quality-cli.d/cli_reporting.py"
cat > "$HOME/.local/bin/skill-quality-cli" <<'EOF'
#!/bin/bash
# skill-quality-cli — 本地 wrapper: 直接执行技能包内置 Python 实现
# 使用技能包内置版本, 关闭运行时自动升级(不产生外部下载)
export SKILL_QUALITY_NO_AUTO_UPGRADE=1
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SELF_DIR}/skill-quality-cli.d/cli_entry.py" "$@"
EOF
chmod +x "$HOME/.local/bin/skill-quality-cli"

echo "skill-quality-cli 安装完成（内置源码部署）: $HOME/.local/bin/skill-quality-cli"
echo "PATH 已导出并持久化(~/.bashrc ~/.profile), 可直接执行: skill-quality-cli ..."