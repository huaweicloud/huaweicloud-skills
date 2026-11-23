#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 查官方 latest 清单, 按本机平台选包下载(带 SHA256 校验)后安装。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。网络/校验失败 → 显式警告后退出 0(不阻塞业务)。
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

# 1. 已安装且可用 → 退出
if command -v skill-quality-cli >/dev/null 2>&1 && skill-quality-cli version >/dev/null 2>&1; then
    exit 0
fi

# 2. 安装(幂等; 失败显式警告, 不阻塞业务)
_install() {
    local manifest v plat url sha actual tmp sum_cmd
    manifest="$(curl -fsSL --connect-timeout 5 --max-time 20 "${API_URL}" 2>/dev/null)" || return 1
    [ -n "$manifest" ] || return 1
    v="$(printf '%s' "$manifest" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null)" || return 1
    # 仅 Linux 发布预编译包: 先判 OS, 避免 macOS 等误下 Linux 包
    case "$(uname -s)" in
        Linux) ;;
        *) echo "警告: 仅支持 Linux 自动安装(当前系统 $(uname -s)), 跳过安装" >&2; return 1 ;;
    esac
    case "$(uname -m)" in
        x86_64|amd64) plat="linux-x86_64" ;;
        aarch64|arm64) plat="linux-arm64" ;;
        *) echo "警告: 不支持的平台 $(uname -m), 跳过安装" >&2; return 1 ;;
    esac
    PICK_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("download_url","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
    url="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$PICK_PY" 2>/dev/null)" || return 1
    [ -n "$url" ] || { echo "警告: latest(${v}) 未发布 ${plat} 安装包, 跳过安装" >&2; return 1; }
    SHA_PY='import sys,json,os; d=json.load(sys.stdin); plat=os.environ["SQC_PLATFORM"]; print(next((p.get("sha256","") for p in d.get("packages",[]) if p.get("platform")==plat), ""))'
    sha="$(printf '%s' "$manifest" | SQC_PLATFORM="$plat" python3 -c "$SHA_PY" 2>/dev/null || true)"
    # 强制校验(fail-closed): 清单必须提供 sha256, 缺省拒绝无校验安装(供应链安全)
    [ -n "$sha" ] || { echo "警告: latest(${v}) 未提供 sha256 校验值, 拒绝无校验安装" >&2; return 1; }
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN
    curl -fsSL --connect-timeout 5 --max-time 60 -o "${tmp}/sqc.tar.gz" "$url" 2>/dev/null || { echo "警告: 下载 skill-quality-cli 失败" >&2; return 1; }
    # 计算实际 SHA256: sha256sum → shasum → python3 hashlib 兜底(不静默跳过)
    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "${tmp}/sqc.tar.gz" 2>/dev/null | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "${tmp}/sqc.tar.gz" 2>/dev/null | awk '{print $1}')"
    else
        actual="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${tmp}/sqc.tar.gz" 2>/dev/null || true)"
    fi
    [ -n "$actual" ] || { echo "警告: 无法计算 SHA256(缺少 sha256sum/shasum/python3), 拒绝安装" >&2; return 1; }
    [ "$actual" = "$sha" ] || { echo "警告: SHA256 校验失败(期望 $sha, 实际 $actual), 跳过安装" >&2; return 1; }

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
        echo "警告: 解压失败或 tar 包含不安全条目, 拒绝安装" >&2
        return 1
    fi
    mkdir -p ~/.local/bin/skill-quality-cli.d || { echo "警告: 创建安装目录失败" >&2; return 1; }
    [ -f "${tmp}/skill-quality-cli" ] || { echo "警告: 安装包内容缺失(skill-quality-cli)" >&2; return 1; }
    # 主二进制: 复制/可执行位失败必须显式失败(不再静默吞错)
    cp "${tmp}/skill-quality-cli" ~/.local/bin/skill-quality-cli || { echo "警告: 复制 skill-quality-cli 失败" >&2; return 1; }
    chmod +x ~/.local/bin/skill-quality-cli || { echo "警告: 设置可执行位失败" >&2; return 1; }
    if [ -f "${tmp}/skill-quality-cli.bin" ]; then
        cp "${tmp}/skill-quality-cli.bin" ~/.local/bin/skill-quality-cli.bin || { echo "警告: 复制 skill-quality-cli.bin 失败" >&2; return 1; }
        chmod +x ~/.local/bin/skill-quality-cli.bin || { echo "警告: 设置 skill-quality-cli.bin 可执行位失败" >&2; return 1; }
    fi
    if [ -d "${tmp}/skill-quality-cli.d" ]; then
        for _f in cli_entry.py cli_reporting.py; do
            if [ -f "${tmp}/skill-quality-cli.d/${_f}" ]; then
                cp "${tmp}/skill-quality-cli.d/${_f}" ~/.local/bin/skill-quality-cli.d/"${_f}" || { echo "警告: 复制 ${_f} 失败" >&2; return 1; }
            fi
        done
    fi
    [ -x ~/.local/bin/skill-quality-cli ] || { echo "警告: 安装产物不可执行(~/.local/bin/skill-quality-cli)" >&2; return 1; }
    return 0
}

if ! _install; then
    echo "警告: skill-quality-cli 安装未完成(网络/清单/校验); 本 skill 降级运行, 可稍后重试或手动执行 install_cli.sh" >&2
    exit 0
fi

# 3. PATH 校验(不破坏既有 PATH): ~/.local/bin 不在 PATH 时提示
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) cat >&2 <<EOF
提示: ${HOME}/.local/bin 不在 PATH; 如需直接调用, 请先将该目录加入 PATH(export PATH 追加)后重试。
EOF
    ;;
esac
if command -v skill-quality-cli >/dev/null 2>&1; then
    echo "skill-quality-cli 已就绪"
else
    echo "警告: 安装后未检测到 skill-quality-cli($HOME/.local/bin 不在 PATH 或安装异常)" >&2
fi
