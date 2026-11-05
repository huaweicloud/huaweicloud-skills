#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 复用 scripts/install_cli.sh 完成下载(强制
# SHA256 校验)与安装。任何失败 → 显式警告后退出 0(不阻塞业务)。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成。
#
# 本 skill 的本地修改(修复 issue #929), 与生成版差异仅两点:
#   1) Windows(Git Bash / MSYS2 / Cygwin)不再走 install_cli.sh —— 该脚本只映射
#      linux-x86_64 / linux-arm64, 而官方清单目前只发布 linux-arm64, Windows 下
#      必然失败; 改为委派跨平台 scripts/install_cli.py(仍强制 SHA256 校验,
#      无原生包时安装已校验包中的纯 Python fallback)。
#   2) 强制 UTF-8(PYTHONUTF8 / PYTHONIOENCODING): 官方 cli_entry.py 的 cmd_run 用
#      subprocess.run(..., text=True) 且未指定 encoding, 中文 Windows 下回退 GBK
#      会 UnicodeDecodeError。
set -euo pipefail

# 强制 UTF-8: 见文件头 issue #929 说明。必须在任何 python 调用之前导出。
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 安装目录统一收敛为变量; 检测与安装均基于该目录, 不依赖调用方 PATH
INSTALL_DIR="${HOME}/.local/bin"

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
               *) printf '%s\n' "未知参数: --${OPTARG}" >&2; exit 1 ;;
           esac ;;
        \?) printf '%s\n' "未知参数" >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))
[ $# -eq 0 ] || { printf '%s\n' "错误: 不接受位置参数" >&2; exit 1; }

# 1. 已安装且可用 → 退出
#    优先按安装目录内的可执行文件判断(不依赖 PATH, 保证 ${INSTALL_DIR} 不在 PATH 时也幂等);
#    确认可用后再把安装目录补进 PATH, 后续裸调用可直接命中。
if [ -x "${INSTALL_DIR}/skill-quality-cli" ] && "${INSTALL_DIR}/skill-quality-cli" version >/dev/null 2>&1; then
    case ":$PATH:" in
        *":${INSTALL_DIR}:"*) ;;
        *) export PATH="${INSTALL_DIR}:${PATH}" ;;
    esac
    exit 0
fi
#    兼容: 已通过其他方式安装到 PATH 中
if command -v skill-quality-cli >/dev/null 2>&1 && skill-quality-cli version >/dev/null 2>&1; then
    exit 0
fi

# 2. 安装: 优先复用 install_cli.sh(下载/校验/解压/复制逻辑单一实现, 避免重复维护漂移);
#    失败 → 显式警告后退出 0(不阻塞业务), 可稍后重试或手动执行 install_cli.sh。
#    issue #929: 官方清单当前只发布 linux-arm64, 而 install_cli.sh 的平台映射只覆盖
#    linux-*, 因此 (a) Windows 下必然失败、(b) linux-x86_64 下也找不到包。两种情况都
#    退回跨平台 install_cli.py —— 仍强制 SHA256 校验, 无原生包时安装已校验包中的纯
#    Python fallback。Windows 下直接走跨平台入口, 不再触发 install_cli.sh 的必然失败。
_os="$(uname -s 2>/dev/null || echo unknown)"
_py=""
for _cand in python3 python py; do
    if command -v "${_cand}" >/dev/null 2>&1; then _py="${_cand}"; break; fi
done

_install_via_python() {
    [ -n "${_py}" ] || return 1
    [ -f "${SCRIPT_DIR}/install_cli.py" ] || return 1
    # 显式指定安装目录: 必须与本脚本的就绪检查/自检使用同一个 ${INSTALL_DIR}。
    # 省略 --install-dir 时 install_cli.py 会自行推导(Windows 取 %USERPROFILE%\.local\bin,
    # 或 SQC_INSTALL_DIR), 当 HOME != USERPROFILE 时就变成"装成功但脚本检测不到"→静默降级。
    "${_py}" "${SCRIPT_DIR}/install_cli.py" --install-dir "${INSTALL_DIR}"
}

case "${_os}" in
    MINGW*|MSYS*|CYGWIN*)
        if ! _install_via_python; then
            printf '%s\n' "警告: Windows 下未完成 skill-quality-cli 安装(需要 Python 3 或网络/清单/校验失败, 见 issue #929 跨平台入口 install_cli.py); 本 skill 降级运行, 不影响业务" >&2
            exit 0
        fi
        ;;
    *)
        if ! bash "$SCRIPT_DIR/install_cli.sh"; then
            if ! _install_via_python; then
                printf '%s\n' "警告: skill-quality-cli 安装未完成(网络/清单/校验); 本 skill 降级运行, 可稍后重试或手动执行 install_cli.sh" >&2
                exit 0
            fi
        fi
        ;;
esac

# 3. PATH 校验(不破坏既有 PATH): 安装目录不在 PATH 时提示
case ":$PATH:" in
    *":${INSTALL_DIR}:"*) ;;
    *) cat >&2 <<EOF
提示: ${INSTALL_DIR} 不在 PATH; 如需直接调用, 请先将该目录加入 PATH(export PATH 追加)后重试。
EOF
    ;;
esac
if [ -x "${INSTALL_DIR}/skill-quality-cli" ]; then
    echo "skill-quality-cli 已就绪"
else
    printf '%s\n' "警告: 安装后未检测到 skill-quality-cli(${INSTALL_DIR} 不在 PATH 或安装异常)" >&2
fi
