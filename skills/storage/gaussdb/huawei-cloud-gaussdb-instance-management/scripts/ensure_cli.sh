#!/bin/bash
set -euo pipefail
# ensure_cli.sh — 确保 skill-quality-cli 可用，不存在则将 skill 内置源码本地部署（幂等）
# 由 huawei-cloud-skill-quality-cli-inject v3.9.0 自动生成，请勿手动修改
# 安全约束(SC2 供应链): 禁止运行时从外部 URL 下载 skill-quality-cli 包。
#   改为将仓库内置的 scripts/cli/*.py 源码本地部署为 wrapper + Python fallback，
#   无网络依赖、无外部代码拉取。CLI 版本固定为内置版本(1.1.8)，不做联网升级。

CLI_VERSION="1.1.8"

# 0. PATH 兜底: 安装目录 ~/.local/bin 可能不在 PATH 中(裸命令 exit 127)
#    启动即导出到当前会话, 并幂等持久化到 ~/.bashrc / ~/.profile
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
if ! grep -qsF '$HOME/.local/bin' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
if ! grep -qsF '$HOME/.local/bin' ~/.profile; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
fi

# 1. 定位本脚本所在目录与内置 CLI 源码(同仓库 scripts/cli/)
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="${SELF_DIR}/cli"
CLI_ENTRY_SRC="${BUNDLE_DIR}/cli_entry.py"
CLI_REPORTING_SRC="${BUNDLE_DIR}/cli_reporting.py"

# 2. 检查是否已安装且可用（优先 PATH, 兜底绝对路径）
CLI_BIN="$(command -v skill-quality-cli 2>/dev/null || true)"
if [ -z "$CLI_BIN" ] && [ -x "$HOME/.local/bin/skill-quality-cli" ]; then
    CLI_BIN="$HOME/.local/bin/skill-quality-cli"
fi
if [ -n "$CLI_BIN" ] && "$CLI_BIN" version >/dev/null 2>&1; then
    echo "skill-quality-cli 已就绪: $CLI_BIN"
    exit 0
fi

# 3. 内置源码缺失 → 跳过(仅告警, 不联网、不阻塞业务流)
if [ ! -f "$CLI_ENTRY_SRC" ] || [ ! -f "$CLI_REPORTING_SRC" ]; then
    echo "警告: 未找到内置 CLI 源码(${BUNDLE_DIR})，跳过本地部署" >&2
    exit 0
fi

# 4. 本地部署: 复制内置源码到 ~/.local/bin/skill-quality-cli.d/, 生成 wrapper
mkdir -p "$HOME/.local/bin/skill-quality-cli.d"
cp "$CLI_ENTRY_SRC" "$HOME/.local/bin/skill-quality-cli.d/cli_entry.py"
cp "$CLI_REPORTING_SRC" "$HOME/.local/bin/skill-quality-cli.d/cli_reporting.py"

cat > "$HOME/.local/bin/skill-quality-cli" <<'WRAPPER'
#!/bin/bash
# skill-quality-cli — 透明 wrapper: 执行内置 Python fallback 源码(本地部署, 无外部下载)
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${SKILL_QUALITY_PYTHON:-}"
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then PY=python3
    elif command -v python >/dev/null 2>&1; then PY=python
    else echo "skill-quality-cli: 需要 Python 3 但未找到" >&2; exit 1
    fi
fi
exec "$PY" "${SELF_DIR}/skill-quality-cli.d/cli_entry.py" "$@"
WRAPPER
chmod +x "$HOME/.local/bin/skill-quality-cli"

# 5. 记录版本(固定内置版本, 无联网)
mkdir -p "$HOME/.skill-quality"
python3 - "$HOME/.skill-quality/version.json" "$HOME/.local/bin/skill-quality-cli" <<'PYEOF' || true
import json, sys, time
payload = {"version": "1.1.8", "installed_at": int(time.time()), "path": sys.argv[2]}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(payload, f)
PYEOF

echo "skill-quality-cli v${CLI_VERSION} 安装完成（内置源码本地部署）: $HOME/.local/bin/skill-quality-cli"
echo "PATH 已导出并持久化(~/.bashrc ~/.profile), 可直接执行: skill-quality-cli ..."