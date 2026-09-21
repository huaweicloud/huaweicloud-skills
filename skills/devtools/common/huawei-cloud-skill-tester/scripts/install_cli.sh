#!/bin/bash
# install_cli.sh — 手动安装 skill-quality-cli(不含自动升级)。
# 合规: 由用户/agent 主动执行(见 SKILL.md / references 指引); 业务脚本不调用本文件。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改
set -euo pipefail

# 参数解析: 本脚本无位置参数; 仅接受 --help(兼容文档 --flag 调用约定)
usage() {
    echo "用法: $(basename "$0") [--help]"
    echo "说明: 无参运行即执行默认行为; --help 显示本帮助。"
    exit 0
}
while getopts "h-:" opt; do
    case "$opt" in
        h) usage ;;
        -) case "${OPTARG}" in
               help) usage ;;
               *) echo "未知参数: --${OPTARG}" >&2; exit 1 ;;
           esac ;;
        \?) echo "未知参数" >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))
[ $# -eq 0 ] || { echo "错误: 不接受位置参数" >&2; exit 1; }

API_URL="https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"

manifest="$(curl -fsSL --connect-timeout 5 --max-time 20 "${API_URL}")"
v="$(printf '%s' "$manifest" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])')"
case "$(uname -m)" in
    x86_64|amd64) plat="linux-x86_64" ;;
    aarch64|arm64) plat="linux-arm64" ;;
    *) echo "不支持的平台 $(uname -m)" >&2; exit 1 ;;
esac
PICK_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("download_url","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
url="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$PICK_PY")"
[ -n "$url" ] || { echo "latest(${v}) 无 ${plat} 安装包" >&2; exit 1; }
SHA_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("sha256","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
sha="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$SHA_PY" || true)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL --connect-timeout 5 --max-time 60 -o "${tmp}/sqc.tar.gz" "$url"
if [ -n "$sha" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "${tmp}/sqc.tar.gz" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "${tmp}/sqc.tar.gz" | awk '{print $1}')"
    else
        actual=""
    fi
    [ -z "$actual" ] || [ "$actual" = "$sha" ] || { echo "SHA256 校验失败" >&2; exit 1; }
fi
tar xzf "${tmp}/sqc.tar.gz" -C "${tmp}"
mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${tmp}/skill-quality-cli" ~/.local/bin/ 2>/dev/null || true
cp "${tmp}/skill-quality-cli.bin" ~/.local/bin/ 2>/dev/null || true
cp "${tmp}/skill-quality-cli.d/cli_entry.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
cp "${tmp}/skill-quality-cli.d/cli_reporting.py" ~/.local/bin/skill-quality-cli.d/ 2>/dev/null || true
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin 2>/dev/null || true
[ ! -x "${HOME}/.local/bin/skill-quality-cli" ] && [ ! -f "${HOME}/.local/bin/skill-quality-cli" ] && {
    echo "错误: 安装产物缺失(未找到 ~/.local/bin/skill-quality-cli), 请检查下载包内容" >&2
    exit 1
}
echo "skill-quality-cli v${v} 安装完成(手动触发)"
