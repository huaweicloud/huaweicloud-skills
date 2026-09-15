#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 可用，不存在则自动安装（幂等）
# 由 huawei-cloud-skill-quality-cli-inject v3.6.0 自动生成，请勿手动修改

# 0. 将安装目录 ~/.local/bin 加入 PATH（当前 shell 生效）；这样在脚本内及
#    后续同 shell 命令中可直接使用裸命令 skill-quality-cli，避免 command not found (127)。
#    若本脚本由调用方以 `bash scripts/ensure_cli.sh` 运行，子 shell 的 export
#    不会传播到父 shell —— 调用方应在同一会话执行:
#        export PATH="$HOME/.local/bin:$PATH"
#    （search-skills.py 内部也会回退到绝对路径 ~/.local/bin/skill-quality-cli 或
#      内置 scripts/cli/cli_entry.py 源码直跑，即使 PATH 未包含该目录也能上报。）
export PATH="$HOME/.local/bin:$PATH"

CLI_BIN="$HOME/.local/bin/skill-quality-cli"

# 1. 检查是否已安装且可用（PATH 未包含 ~/.local/bin 时也能识别绝对路径）
if command -v skill-quality-cli &>/dev/null && skill-quality-cli version &>/dev/null 2>&1; then
    exit 0
fi
if [ -x "$CLI_BIN" ] && "$CLI_BIN" version &>/dev/null 2>&1; then
    exit 0
fi

# 2. 未安装 → 下载 tar.gz 包（含 wrapper + ELF + Python fallback, 兼容低 GLIBC）
API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"
OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

V=$(curl -s -H 'Content-Type: application/json' "${API_URL}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -z "$V" ]; then
    echo "警告: 无法获取 skill-quality-cli 最新版本，跳过安装" >&2
    exit 0
fi

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

TMPDIR=$(mktemp -d)
curl -fsSL -o "${TMPDIR}/sqc.tar.gz" \
    "${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz" 2>/dev/null
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
echo "skill-quality-cli v${V} 安装完成（自动）"

# 3. 安装后自检：裸命令可用性（export PATH 已在步骤 0 生效）
if command -v skill-quality-cli &>/dev/null; then
    echo "已就绪: $(command -v skill-quality-cli)"
else
    echo "提示: 将 ~/.local/bin 加入 PATH 后可直接使用 'skill-quality-cli':" >&2
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
fi
