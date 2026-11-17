#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md Step 0 / references 指引）;
#       业务脚本不调用本文件。
# 失败语义: 任何一步失败都输出可读中文原因并以非零退出码结束；
#           网络请求硬超时（连接 5s / 单次 30s），无网环境不会静默挂起。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

set -e

API_URL="${SQC_API_URL:-https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest}"
OBS_BASE="${SQC_OBS_BASE:-https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli}"
CURL_TIMEOUT=(--connect-timeout 5 --max-time 30)

fail() {
    echo "错误: $*" >&2
    exit 1
}

# 0) 依赖前置检查（不做任何网络调用，失败 <1s 返回）
for dep in curl python3 tar mktemp; do
    command -v "$dep" >/dev/null 2>&1 \
        || fail "缺少依赖 $dep，无法安装 skill-quality-cli（请先安装 $dep 后重试）"
done

VERSION_JSON=$(mktemp)
TMPDIR=$(mktemp -d)
cleanup() {
    rm -rf "${TMPDIR}"
    rm -f "${VERSION_JSON}"
}
trap cleanup EXIT

# 1) 版本元数据先落盘再解析（不把远端响应直接接进解释器；失败链路显式可控）
if ! curl -fsS "${CURL_TIMEOUT[@]}" -o "${VERSION_JSON}" "${API_URL}"; then
    fail "无法获取 skill-quality-cli 最新版本（${API_URL}）。请在 30 秒内检查网络/代理是否可达，或改用离线包安装"
fi
V=$(python3 -c 'import sys,json;print(json.load(open(sys.argv[1]))["version"])' "${VERSION_JSON}" 2>/dev/null) || V=""
if [ -z "$V" ]; then
    fail "版本元数据无法解析（${API_URL} 返回内容不含 version 字段）"
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

# 2) 下载安装包
ARCHIVE="${TMPDIR}/sqc.tar.gz"
ARCHIVE_URL="${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz"
if ! curl -fsSL "${CURL_TIMEOUT[@]}" -o "${ARCHIVE}" "${ARCHIVE_URL}"; then
    fail "下载 skill-quality-cli v${V} (linux-${ARCH}) 失败: ${ARCHIVE_URL}（检查网络/OBS 可达性）"
fi
if [ ! -s "${ARCHIVE}" ]; then
    fail "下载的 skill-quality-cli 安装包为空: ${ARCHIVE_URL}"
fi

# 3) 解压与落盘
tar xzf "${ARCHIVE}" -C "${TMPDIR}" \
    || fail "解压 skill-quality-cli 安装包失败: ${ARCHIVE}"
if [ ! -f "${TMPDIR}/skill-quality-cli" ]; then
    fail "安装包中缺少 skill-quality-cli 可执行文件: ${ARCHIVE}"
fi

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ 2>/dev/null || true
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null || true
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null || true

if [ ! -x ~/.local/bin/skill-quality-cli ]; then
    fail "安装后未找到可执行的 ~/.local/bin/skill-quality-cli（请确认 ~/.local/bin 可写）"
fi

echo "skill-quality-cli v${V} 安装完成（手动触发）"