#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md「Prerequisites」章节与 references/cli-installation-guide.md「5. Quality telemetry」）;
#       业务脚本不调用本文件。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

set -e

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

# PATH 自愈: ~/.local/bin 通常不在默认 PATH 中，否则裸调用 skill-quality-cli 会 command not found
LOCAL_BIN="${HOME}/.local/bin"
case ":${PATH}:" in
    *":${LOCAL_BIN}:"*) ;;
    *) export PATH="${LOCAL_BIN}:${PATH}" ;;
esac
for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
    [ -f "${rc}" ] || continue
    grep -q "skills:skill-quality-cli PATH" "${rc}" 2>/dev/null && continue
    printf '\n# skills:skill-quality-cli PATH\nexport PATH="%s:$PATH"\n' "${LOCAL_BIN}" >> "${rc}"
done
if ! command -v skill-quality-cli >/dev/null 2>&1; then
    echo "提示: 当前终端仍找不到 skill-quality-cli，请执行: export PATH=\"${LOCAL_BIN}:\$PATH\"" >&2
fi

echo "skill-quality-cli v${V} 安装完成（手动触发）"
