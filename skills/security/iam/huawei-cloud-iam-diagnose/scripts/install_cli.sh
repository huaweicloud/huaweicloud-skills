#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md Step 0 / references 指引）;
#       业务脚本不调用本文件。
# 安全(供应链): 固定版本 + SHA256 白名单校验, 未命中白名单一律拒绝安装。
# 用法:
#   bash scripts/install_cli.sh [--version V] [--arch ARCH] [--sha256 HASH] [--help]
set -euo pipefail

OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

usage() {
    cat <<'EOF' >&2
用法: bash scripts/install_cli.sh [选项]
  -h, --help            显示本帮助
  -v, --version VERSION 指定固定版本 (默认: SQCLI_PINNED_VERSION 或 1.1.8)
  -a, --arch ARCH       指定目标架构 (x86_64|arm64, 默认: uname -m)
  -s, --sha256 HASH     指定 tar.gz 的 SHA256 校验和 (白名单外时显式提供)
EOF
}

# 解析命名参数 (getopt: 支持长选项; 未传参时保持默认行为)
PARSED=$(getopt -o hv:a:s: --long help,version:,arch:,sha256: -n "$(basename "$0")" -- "$@") || { usage; exit 1; }
eval set -- "$PARSED"

while true; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        -v|--version) PINNED_VERSION="$2"; shift 2 ;;
        -a|--arch) ARCH_OVERRIDE="$2"; shift 2 ;;
        -s|--sha256) SHA256_OVERRIDE="$2"; shift 2 ;;
        --) shift; break ;;
        *) usage; exit 1 ;;
    esac
done

# 固定版本 + SHA256 白名单（可信发布渠道 = OBS 官方桶 + 本文件声明的哈希）。
#    VERSION 升级时, 由维护者同步更新 PINNED_VERSION 与对应架构的 SHA256。
PINNED_VERSION="${PINNED_VERSION:-${SQCLI_PINNED_VERSION:-1.1.8}}"
# 官方发布通道当前仅提供 linux-arm64 构建 (OBS 桶中无 x86_64 包 → 403)。
# x86_64 用户可通过 --sha256 显式提供可信校验和后自行托管安装包走本脚本安装。
PINNED_SHA256_ARM64="1a73773831c0f52542f5591cd9e5126b0c160b8dd36b67f9f833edb0c06a03d5"

ARCH="${ARCH_OVERRIDE:-$(uname -m)}"
case "$ARCH" in
    x86_64|amd64)
        LINUX_ARCH="x86_64"
        if [ -n "${SHA256_OVERRIDE:-}" ]; then
            EXPECTED_SHA256="$SHA256_OVERRIDE"
        elif [ -n "${SQCLI_SHA256_X86_64:-}" ]; then
            EXPECTED_SHA256="$SQCLI_SHA256_X86_64"
        else
            echo "错误: skill-quality-cli 官方发布通道当前仅提供 linux-arm64 构建" >&2
            echo "       x86_64 平台暂无法自动安装; 如已有可信安装包与校验和," >&2
            echo "       请使用 --sha256 <HASH> 显式提供后重试" >&2
            exit 1
        fi
        ;;
    aarch64|arm64)
        LINUX_ARCH="arm64"
        EXPECTED_SHA256="${SHA256_OVERRIDE:-${SQCLI_SHA256_ARM64:-$PINNED_SHA256_ARM64}}"
        ;;
    *)
        echo "错误: 不支持的架构 ${ARCH}" >&2
        exit 1
        ;;
esac

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PKG_URL="${OBS_BASE}/v${PINNED_VERSION}/skill-quality-cli-v${PINNED_VERSION}-linux-${LINUX_ARCH}.tar.gz"
if ! curl -fsSL --max-time 30 --connect-timeout 5 -o "${TMPDIR}/sqc.tar.gz" "$PKG_URL"; then
    echo "错误: 下载 skill-quality-cli 失败(${LINUX_ARCH}), 请检查网络或稍后重试" >&2
    exit 1
fi

# SHA256 校验（不通过 → 拒装, 防供应链投毒）
GOT_SHA256=$(sha256sum "${TMPDIR}/sqc.tar.gz" | awk '{print $1}')
if [ "$GOT_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "错误: skill-quality-cli 校验和不匹配(期望 ${EXPECTED_SHA256}, 实际 ${GOT_SHA256}), 可能被篡改, 已拒绝安装" >&2
    exit 1
fi

tar xzf "${TMPDIR}/sqc.tar.gz" -C "${TMPDIR}" --no-same-owner

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ || true
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ || true
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ || true
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ || true
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin || true

echo "skill-quality-cli v${PINNED_VERSION} 安装完成（手动触发）"