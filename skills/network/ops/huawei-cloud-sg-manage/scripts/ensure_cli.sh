#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 执行一次安装(载体=全局 ~/.local/bin)。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。
# 失败语义: 告警后 exit 0（不阻塞业务），但网络请求硬超时（连接 5s / 单次 30s），
#           无网环境秒级返回，不会静默挂起等待。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

# 1. 已安装且可用 → 退出
if command -v skill-quality-cli &>/dev/null && skill-quality-cli version &>/dev/null 2>&1; then
    exit 0
fi

warn() {
    echo "警告: $* —— 跳过 skill-quality-cli 安装，不影响业务命令执行（如需质量上报请手动运行 install_cli.sh）" >&2
    exit 0
}

# 2. 依赖前置检查（不联网，失败即告警退出）
for dep in curl python3 tar mktemp; do
    command -v "$dep" >/dev/null 2>&1 || warn "缺少依赖 $dep"
done

API_URL="${SQC_API_URL:-https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest}"
OBS_BASE="${SQC_OBS_BASE:-https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli}"
CURL_TIMEOUT=(--connect-timeout 5 --max-time 30)

# 3. 版本元数据先落盘再解析（不把远端响应直接接进解释器）
VERSION_JSON=$(mktemp)
TMP="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP}"
    rm -f "${VERSION_JSON}"
}
trap cleanup EXIT

V=""
if curl -fsS "${CURL_TIMEOUT[@]}" -o "${VERSION_JSON}" "${API_URL}" 2>/dev/null; then
    V=$(python3 -c 'import sys,json;print(json.load(open(sys.argv[1]))["version"])' "${VERSION_JSON}" 2>/dev/null) || V=""
fi
if [ -z "$V" ]; then
    warn "无法获取 skill-quality-cli 最新版本（网络/代理不可达或元数据不含 version）"
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

ARCHIVE="${TMP}/sqc.tar.gz"
if ! curl -fsSL "${CURL_TIMEOUT[@]}" -o "${ARCHIVE}" "${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz" 2>/dev/null; then
    warn "下载 skill-quality-cli v${V} (linux-${ARCH}) 失败"
fi

tar xzf "${ARCHIVE}" -C "${TMP}" || warn "解压 skill-quality-cli 安装包失败"

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMP}/skill-quality-cli" ~/.local/bin/ 2>/dev/null || true
cp "${TMP}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null || true
cp "${TMP}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
cp "${TMP}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null || true

echo "skill-quality-cli v${V} 已就绪"