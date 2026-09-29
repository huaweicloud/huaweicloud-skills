#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 执行一次安装(载体=全局 ~/.local/bin)。
# PATH 修复: ~/.local/bin 常不在默认 PATH, 本脚本在 CLI 就绪后会将其软链到
#            PATH 中第一个可写目录(如 /usr/local/bin), 保证裸命令
#            `skill-quality-cli` 可直接调用; 无一可写时打印 export 指引。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。失败静默, 不阻塞业务。
# 安全(供应链): 固定版本 + SHA256 白名单校验, 未命中白名单一律拒绝安装;
#               所有网络请求均设置超时, 避免阻塞业务流程。
# 用法:
#   bash scripts/ensure_cli.sh [--version V] [--arch ARCH] [--sha256 HASH] [--help]
set -euo pipefail

OBS_BASE="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli"
# 安装目录: 默认 ~/.local/bin; 可用环境变量 SKILL_QUALITY_INSTALL_DIR 覆盖。
INSTALL_DIR="${SKILL_QUALITY_INSTALL_DIR:-$HOME/.local/bin}"

# 校验安装目录合法性(白名单枚举+类型检查), 防止删除/复制/建目录等工具参数被
# 外部环境变量 SKILL_QUALITY_INSTALL_DIR 恶意注入(目录穿越/通配符/根目录等)。
_validate_install_dir() {
    # 必须为绝对路径
    case "$INSTALL_DIR" in
        /*) ;;
        *) return 1 ;;
    esac
    # 不能是根目录
    [ "$INSTALL_DIR" = "/" ] && return 1
    # 不能包含目录穿越、通配符、空白、shell 元字符
    case "$INSTALL_DIR" in
        *..*|*'*'*|*'?'*|*'['*|*']'*|*[[:space:]]*|*'"'*|*"'"*|*'$'*|*'`'*|*';'*|*'|'*|*'&'*|*'<'*|*'>'*)
            return 1 ;;
    esac
    return 0
}
if ! _validate_install_dir; then
    echo "警告: SKILL_QUALITY_INSTALL_DIR 非法(需为安全的绝对路径), 跳过安装" >&2
    exit 0
fi

# 固定版本 (维护者升级时同步更新 SHA256 白名单与发布包)。
PINNED_VERSION="${PINNED_VERSION:-${SQCLI_PINNED_VERSION:-1.1.8}}"

usage() {
    cat <<'EOF' >&2
用法: bash scripts/ensure_cli.sh [选项]
  -h, --help            显示本帮助
  -v, --version VERSION 指定固定版本 (默认: SQCLI_PINNED_VERSION 或 1.1.8)
  -a, --arch ARCH       指定目标架构 (x86_64|arm64, 默认: uname -m)
  -s, --sha256 HASH     指定 tar.gz 的 SHA256 校验和 (白名单外时显式提供)
EOF
}

# 0. 解析命名参数 (getopt: 支持长选项; 未传参时保持默认行为)
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

# PATH 修复: 保证 skill-quality-cli 可通过裸命令调用。
# 若能通过裸命令成功运行 version 则立即返回; 否则在 PATH 中第一个可写目录
# 创建 shim(真实解析到 ~/.local/bin); 全部不可写时打印一次性 export 指引。
ensure_on_path() {
    if command -v skill-quality-cli >/dev/null 2>&1 \
       && skill-quality-cli version >/dev/null 2>&1; then
        return 0
    fi
    local src="${INSTALL_DIR}/skill-quality-cli"
    [ -x "$src" ] || return 0
    local dir target
    for dir in $(printf '%s' "$PATH" | tr ':' '\n'); do
        [ -n "$dir" ] || continue
        [ -w "$dir" ] || continue
        target="$dir/skill-quality-cli"
        # 用 shim 脚本而非 symlink: 原始 wrapper 依 dirname "$0" 定位
        # skill-quality-cli.bin / skill-quality-cli.d/, symlink 会使 $0
        # 指向链接目录而找不到 cli_entry.py, 报"找不到 cli_entry.py"。
        rm -f "$target" 2>/dev/null
        if printf '#!/bin/sh\nexec "%s" "$@"\n' "$src" > "$target" 2>/dev/null; then
            chmod +x "$target" 2>/dev/null
            echo "提示: 已在 $target 创建 shim, 保证 skill-quality-cli 可被直接调用" >&2
            return 0
        fi
    done
    echo "提示: skill-quality-cli 已安装到 $src, 但不在 PATH 中。" >&2
    echo "      请执行: export PATH=\"${INSTALL_DIR}:\$PATH\"" >&2
    return 0
}

# 写入安装版本元数据(与 cli_entry.py 的 ~/.skill-quality/version.json 一致),
# 否则 `skill-quality-cli version` 显示 (installed unknown), upgrade 报"尚未安装"。
ensure_version_meta() {
    local vf="$HOME/.skill-quality/version.json"
    [ -f "$vf" ] && return 0
    mkdir -p "$HOME/.skill-quality"
    printf '{"version": "%s", "installed_at": %s, "path": "%s"}\n' \
        "$PINNED_VERSION" "$(date +%s)" "${INSTALL_DIR}/skill-quality-cli" > "$vf"
}

# 1. 已安装且可用 → 退出（PATH 可能不含 ~/.local/bin, 同时检查绝对路径）
CLI_BIN=""
if command -v skill-quality-cli >/dev/null 2>&1; then
    CLI_BIN="skill-quality-cli"
elif [ -x "${INSTALL_DIR}/skill-quality-cli" ]; then
    CLI_BIN="${INSTALL_DIR}/skill-quality-cli"
fi
if [ -n "$CLI_BIN" ] && "$CLI_BIN" version >/dev/null 2>&1; then
    ensure_version_meta
    ensure_on_path
    exit 0
fi

# 2. SHA256 白名单（可信发布渠道 = OBS 官方桶 + 本文件声明的哈希）。
#    VERSION 升级时, 由维护者同步更新 PINNED_VERSION 与对应架构的 SHA256,
#    并发布到可信渠道, 禁止绕过校验安装。
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
            echo "警告: skill-quality-cli 官方发布通道当前仅提供 linux-arm64 构建" >&2
            echo "       x86_64 平台暂无法自动安装; 如已有可信安装包与校验和," >&2
            echo "       请使用 --sha256 <HASH> 显式提供后重试" >&2
            exit 0
        fi
        ;;
    aarch64|arm64)
        LINUX_ARCH="arm64"
        EXPECTED_SHA256="${SHA256_OVERRIDE:-${SQCLI_SHA256_ARM64:-$PINNED_SHA256_ARM64}}"
        ;;
    *)
        echo "警告: 不支持的架构 ${ARCH}, 跳过安装" >&2
        exit 0
        ;;
esac

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PKG_URL="${OBS_BASE}/v${PINNED_VERSION}/skill-quality-cli-v${PINNED_VERSION}-linux-${LINUX_ARCH}.tar.gz"
if ! curl -fsSL --max-time 30 --connect-timeout 5 -o "${TMPDIR}/sqc.tar.gz" "$PKG_URL"; then
    echo "警告: 下载 skill-quality-cli 失败(${LINUX_ARCH}), 跳过安装" >&2
    exit 0
fi

# 3. SHA256 校验（不通过 → 拒装, 防供应链投毒）
GOT_SHA256=$(sha256sum "${TMPDIR}/sqc.tar.gz" | awk '{print $1}')
if [ "$GOT_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "警告: skill-quality-cli 校验和不匹配(期望 ${EXPECTED_SHA256}, 实际 ${GOT_SHA256}), 拒绝安装" >&2
    exit 0
fi

tar xzf "${TMPDIR}/sqc.tar.gz" -C "${TMPDIR}" --no-same-owner

mkdir -p "${INSTALL_DIR}/skill-quality-cli.d"

# 关键文件(主程序/.bin/.d 模块)必须全部复制成功并赋可执行权限; 任一失败即
# 清理半成品并警告退出(不阻塞业务), 避免留下残缺 CLI 却仍提示"已就绪"。
if ! cp "${TMPDIR}/skill-quality-cli" "${INSTALL_DIR}/" \
   || ! cp "${TMPDIR}/skill-quality-cli.bin" "${INSTALL_DIR}/" \
   || ! cp "${TMPDIR}/skill-quality-cli.d/cli_entry.py" "${INSTALL_DIR}/skill-quality-cli.d/" \
   || ! cp "${TMPDIR}/skill-quality-cli.d/cli_reporting.py" "${INSTALL_DIR}/skill-quality-cli.d/" \
   || ! chmod +x "${INSTALL_DIR}/skill-quality-cli" "${INSTALL_DIR}/skill-quality-cli.bin"; then
    echo "警告: 安装 skill-quality-cli 失败(复制或赋权出错), 跳过安装" >&2
    # 精确回滚本次安装落盘的固定文件(白名单), 避免递归强制删除的滥用风险
    rollback_bin="${INSTALL_DIR}/skill-quality-cli"
    rollback_raw="${INSTALL_DIR}/skill-quality-cli.bin"
    rollback_entry="${INSTALL_DIR}/skill-quality-cli.d/cli_entry.py"
    rollback_report="${INSTALL_DIR}/skill-quality-cli.d/cli_reporting.py"
    rm -f "$rollback_bin" "$rollback_raw" "$rollback_entry" "$rollback_report"
    rmdir "${INSTALL_DIR}/skill-quality-cli.d" 2>/dev/null || true
    exit 0
fi

echo "skill-quality-cli v${PINNED_VERSION} 已就绪"
ensure_version_meta
ensure_on_path
