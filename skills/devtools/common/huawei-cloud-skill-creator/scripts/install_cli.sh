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
case "$(uname -s)" in
    Linux) ;;
    *) echo "错误: 仅支持 Linux 安装(当前系统 $(uname -s))" >&2; exit 1 ;;
esac
case "$(uname -m)" in
    x86_64|amd64) plat="linux-x86_64" ;;
    aarch64|arm64) plat="linux-arm64" ;;
    *) echo "不支持的平台 $(uname -m)" >&2; exit 1 ;;
esac
PICK_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("download_url","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
url="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$PICK_PY")"
[ -n "$url" ] || { echo "latest(${v}) 无 ${plat} 安装包" >&2; exit 1; }
SHA_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("sha256","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
sha="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$SHA_PY")"
[ -n "$sha" ] || { echo "错误: latest(${v}) 未提供 sha256 校验值, 拒绝无校验安装" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL --connect-timeout 5 --max-time 60 -o "${tmp}/sqc.tar.gz" "$url"
# 校验必填: 缺 sha / 无法计算 / 不匹配 → 直接失败, 不静默跳过
if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "${tmp}/sqc.tar.gz" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "${tmp}/sqc.tar.gz" | awk '{print $1}')"
else
    actual="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${tmp}/sqc.tar.gz" || true)"
fi
[ -n "$actual" ] || { echo "错误: 无法计算 SHA256(缺少 sha256sum/shasum/python3)" >&2; exit 1; }
[ "$actual" = "$sha" ] || { echo "错误: SHA256 校验失败(期望 $sha, 实际 $actual)" >&2; exit 1; }

    # 安全解压: 拒绝 .. / 绝对路径 / 链接条目, 防恶意 tar 写入任意路径
    if ! python3 - "${tmp}/sqc.tar.gz" "${tmp}" <<'PYX'
import sys, tarfile
try:
    with tarfile.open(sys.argv[1], "r:*") as tf:
        for m in tf.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/"):
                sys.stderr.write("unsafe tar entry: %s\n" % m.name); sys.exit(1)
            if m.issym() or m.islnk():
                sys.stderr.write("unsafe link entry: %s\n" % m.name); sys.exit(1)
        tf.extractall(sys.argv[2])
except Exception as e:
    sys.stderr.write("unsafe extract: %s\n" % e); sys.exit(1)
PYX
    then
        echo "错误: 解压失败或 tar 包含不安全条目, 拒绝安装" >&2
        exit 1
    fi
mkdir -p ~/.local/bin/skill-quality-cli.d
cp "${tmp}/skill-quality-cli" ~/.local/bin/skill-quality-cli || { echo "错误: 复制 skill-quality-cli 失败" >&2; exit 1; }
chmod +x ~/.local/bin/skill-quality-cli || { echo "错误: 设置可执行位失败" >&2; exit 1; }
if [ -f "${tmp}/skill-quality-cli.bin" ]; then
    cp "${tmp}/skill-quality-cli.bin" ~/.local/bin/skill-quality-cli.bin || { echo "错误: 复制 skill-quality-cli.bin 失败" >&2; exit 1; }
    chmod +x ~/.local/bin/skill-quality-cli.bin || { echo "错误: 设置 skill-quality-cli.bin 可执行位失败" >&2; exit 1; }
fi
if [ -d "${tmp}/skill-quality-cli.d" ]; then
    for _f in cli_entry.py cli_reporting.py; do
        if [ -f "${tmp}/skill-quality-cli.d/${_f}" ]; then
            cp "${tmp}/skill-quality-cli.d/${_f}" ~/.local/bin/skill-quality-cli.d/"${_f}" || { echo "错误: 复制 ${_f} 失败" >&2; exit 1; }
        fi
    done
fi
if [ ! -x "${HOME}/.local/bin/skill-quality-cli" ]; then
    echo "错误: 安装产物缺失或不可执行(${HOME}/.local/bin/skill-quality-cli), 请检查下载包内容" >&2
    exit 1
fi
echo "skill-quality-cli v${v} 安装完成(手动触发)"
