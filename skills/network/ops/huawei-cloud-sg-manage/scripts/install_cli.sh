#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md Step 0 / references 指引）;
#       业务脚本不调用本文件。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

set -e

API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"
OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

# 版本元数据先落盘再解析（不把远端响应直接接进解释器；失败链路显式可控）
VERSION_JSON=$(mktemp)
V=""
if curl -fsS -o "${VERSION_JSON}" "${API_URL}" 2>/dev/null; then
    V=$(python3 -c 'import sys,json;print(json.load(open(sys.argv[1]))["version"])' "${VERSION_JSON}" 2>/dev/null) || V=""
fi
rm -f "${VERSION_JSON}"
if [ -z "$V" ]; then
    echo "无法获取 skill-quality-cli 最新版本" >&2
    exit 1
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR}"' EXIT

ARCHIVE="${TMPDIR}/sqc.tar.gz"
ARCHIVE_URL="${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz"
if ! curl -fsSL -o "${ARCHIVE}" "${ARCHIVE_URL}"; then
    echo "错误: 下载 skill-quality-cli v${V} (linux-${ARCH}) 失败: ${ARCHIVE_URL}" >&2
    exit 1
fi
if [ ! -s "${ARCHIVE}" ]; then
    echo "错误: 下载的 skill-quality-cli 安装包为空: ${ARCHIVE_URL}" >&2
    exit 1
fi
if ! tar xzf "${ARCHIVE}" -C "${TMPDIR}"; then
    echo "错误: 解压 skill-quality-cli 安装包失败: ${ARCHIVE}" >&2
    exit 1
fi
if [ ! -f "${TMPDIR}/skill-quality-cli" ]; then
    echo "错误: 安装包中缺少 skill-quality-cli 可执行文件: ${ARCHIVE}" >&2
    exit 1
fi

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null

echo "skill-quality-cli v${V} 安装完成（手动触发）"
