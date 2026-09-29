#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 执行一次安装(载体=全局 ~/.local/bin)。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。失败静默, 不阻塞业务。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改
# （SKI-1517 修复: 增加 ~/.local/bin 的 PATH 兜底与持久化，兼容非 login shell）

# 0. PATH 兜底: 安装目录 ~/.local/bin 可能不在 PATH 中(非 login shell 下 `command -v` 会 miss)。
#    启动即导出到当前会话, 并幂等持久化到 ~/.bashrc / ~/.profile。
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

# 1. 已安装且可用 → 退出（优先 PATH, 兜底 ~/.local/bin 绝对路径）
CLI_BIN="$(command -v skill-quality-cli 2>/dev/null || true)"
if [ -z "$CLI_BIN" ] && [ -x "$HOME/.local/bin/skill-quality-cli" ]; then
    CLI_BIN="$HOME/.local/bin/skill-quality-cli"
fi
if [ -n "$CLI_BIN" ] && "$CLI_BIN" version >/dev/null 2>&1; then
    exit 0
fi

# 2. 未安装 → 执行安装(幂等; 载体=全局 CLI; 失败静默不阻塞)
API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"
OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

V=$(curl -s "${API_URL}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -z "$V" ]; then
    echo "警告: 无法获取 skill-quality-cli 最新版本，跳过安装" >&2
    exit 0
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

TMPDIR=$(mktemp -d)
curl -fsSL -o "${TMPDIR}/sqc.tar.gz" "${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz" 2>/dev/null
if [ ! -f "${TMPDIR}/sqc.tar.gz" ]; then
    echo "警告: 下载 skill-quality-cli 失败，跳过安装" >&2
    rm -rf "${TMPDIR}"
    exit 0
fi

tar xzf "${TMPDIR}/sqc.tar.gz" -C "${TMPDIR}"

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null

rm -rf "${TMPDIR}"
echo "skill-quality-cli v${V} 已就绪 (${HOME}/.local/bin 已加入当前会话 PATH 并写入 ~/.bashrc / ~/.profile)"
