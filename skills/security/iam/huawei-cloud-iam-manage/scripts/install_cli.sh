#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md Step 0 / references 指引）;
#       业务脚本不调用本文件。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改
# （SKI-1517 修复: 增加 ~/.local/bin 的 PATH 兜底与持久化，兼容非 login shell）

set -e

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

API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"
OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

V=$(curl -s "${API_URL}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -z "$V" ]; then
    echo "无法获取 skill-quality-cli 最新版本" >&2
    exit 1
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

TMPDIR=$(mktemp -d)
curl -fsSL -o "${TMPDIR}/sqc.tar.gz" "${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz"
tar xzf "${TMPDIR}/sqc.tar.gz" -C "${TMPDIR}"

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null

rm -rf "${TMPDIR}"
echo "skill-quality-cli v${V} 安装完成（手动触发）; PATH 已写入 ~/.bashrc / ~/.profile，新会话直接可用"