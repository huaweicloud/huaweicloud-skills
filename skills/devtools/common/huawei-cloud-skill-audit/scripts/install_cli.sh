#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli（不含自动升级）。
# 合规: 本脚本由用户/agent 主动执行（见 SKILL.md Step 0 / references 指引）;
#       业务脚本不调用本文件。
# 供应链安全: 版本号与 sha256 均来自可信源 API(HTTPS) 同一次响应,
#             下载后强制 sha256sum 校验, 防 OBS 包被篡改/中间人替换。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

set -e

API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"
OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"

ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] || ARCH=arm64

# 一次请求同时取版本号和对应架构包的 sha256(可信源声明, 与 SKILL.md 一致)
META=$(curl -s "${API_URL}" | python3 -c "import sys,json;d=json.load(sys.stdin);pl='linux-'+sys.argv[1];p=next((x for x in d.get('packages',[]) if x.get('platform')==pl),{});print(d.get('version',''),p.get('sha256',''))" "$ARCH" 2>/dev/null)
V="${META%% *}"
SHA256="${META#* }"
if [ -z "$V" ] || [ -z "$SHA256" ]; then
    echo "无法获取 skill-quality-cli 最新版本/校验值" >&2
    exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR}"' EXIT

curl -fsSL -o "${TMPDIR}/sqc.tar.gz" "${OBS_BASE}/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz"

echo "${SHA256}  ${TMPDIR}/sqc.tar.gz" | sha256sum -c - >/dev/null 2>&1 || {
    echo "SHA256 校验失败: 下载包与可信源声明不一致, 已中止安装" >&2
    exit 1
}

tar xzf "${TMPDIR}/sqc.tar.gz" -C "${TMPDIR}"

mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${TMPDIR}/skill-quality-cli" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null

echo "skill-quality-cli v${V} 安装完成（手动触发）"
