#!/usr/bin/env bash
# Vod Collector - AtomGit-GO installation script (Linux/macOS)
# Usage: bash vod_install.sh [--repo-dir <path>] [--sha256 <file>]
# Prints open-source notice, checks if installed, and installs if needed.
#
# 校验策略（按优先级）：
#   1. --sha256 <file>            显式指定的 sha256 校验文件（用户/集成方给定）
#   2. <archive>.sha256           上游随包发布的校验文件（若存在）
#   3. vod_install_checksums.txt  本 skill 维护的已知版本清单（随 skill 分发）
#   4. 都没有                     打印告警后走源码构建兜底（不再直接 exit 1）
# 校验不通过（显式/随包文件不符）仍 fail-closed：拒绝安装该压缩包。
# 清单不符（上游发布了新构建）→ 拒绝该压缩包并回退源码构建，避免静默安装未验证产物。

set -euo pipefail

# 全局临时目录 + EXIT 级统一清理: 任何错误路径(clone/校验/构建失败)都不残留临时文件
CLEANUP_DIR=""
_cleanup() {
  if [ -n "${CLEANUP_DIR:-}" ]; then
    rm -rf "$CLEANUP_DIR"
  fi
}
trap _cleanup EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
REPO_URL="https://gitcode.com/weixin_45218422/AtomGit-GO.git"
CHECKSUM_MANIFEST="${SCRIPT_DIR}/vod_install_checksums.txt"

# ---- detect platform ----
detect_arch() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "arm_64" ;;
    *) printf '%s\n' "unsupported: $arch" >&2; exit 1 ;;
  esac
}

# ---- check ----
check_installed() {
  # 验证三个可执行文件真实存在且可执行(避免悬空符号链接/同名目录/残缺安装误判)
  if [ -x "${BIN_DIR}/atomcode-login" ] && [ -x "${BIN_DIR}/atomcode-login-server" ] && [ -x "${BIN_DIR}/atomcode-server" ]; then
    return 0
  fi
  return 1
}

# ---- checksum helpers ----
# 返回 0=通过 / 1=校验失败(fail-closed) / 2=无可用校验来源 / 3=与已知清单不符
verify_checksum() {
  local file="$1"
  local checksum_file="${file}.sha256"
  local basename_file
  basename_file="$(basename "$file")"

  # 1) 显式 --sha256：最高优先级，失败即拒绝（用户明确要求按该文件校验）
  if [ -n "${SHA256_FILE_ARG:-}" ]; then
    if [ ! -f "$SHA256_FILE_ARG" ]; then
      printf '%s\n' "[vod_install] ERROR: --sha256 file not found: ${SHA256_FILE_ARG}" >&2
      return 1
    fi
    echo "[vod_install] Verifying checksum (explicit: ${SHA256_FILE_ARG}) ..."
    _verify_with_file "$file" "$SHA256_FILE_ARG" || return 1
    echo "[vod_install] Checksum verified."
    return 0
  fi

  # 2) 上游随包 .sha256：存在即必须通过
  if [ -f "$checksum_file" ]; then
    echo "[vod_install] Verifying checksum (${checksum_file}) ..."
    _verify_with_file "$file" "$checksum_file" || return 1
    echo "[vod_install] Checksum verified."
    return 0
  fi

  # 3) 本 skill 维护的已知版本清单
  local expected
  expected="$(_manifest_lookup "$basename_file")"
  if [ -n "$expected" ]; then
    echo "[vod_install] Verifying checksum (manifest: ${CHECKSUM_MANIFEST}) ..."
    local actual
    actual="$(_sha256_of "$file")" || {
      printf '%s\n' "[vod_install] ERROR: no checksum tool (sha256sum/shasum) available; refuse unverified install" >&2
      return 1
    }
    if [ "$(printf '%s' "$actual" | tr 'A-F' 'a-f')" = "$(printf '%s' "$expected" | tr 'A-F' 'a-f')" ]; then
      echo "[vod_install] Checksum verified."
      return 0
    fi
    printf '%s\n' "[vod_install] WARN: archive does not match the known-version manifest (${basename_file})." >&2
    printf '%s\n' "[vod_install] WARN: expected ${expected}, got ${actual}. Refusing this archive." >&2
    return 3
  fi

  # 4) 无任何校验来源：不再直接退出，交由调用方回退源码构建
  printf '%s\n' "[vod_install] WARN: no checksum available for ${basename_file} (no .sha256, no manifest entry, no --sha256)." >&2
  return 2
}

_sha256_of() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    return 1
  fi
}

_verify_with_file() {
  local file="$1"
  local checksum_file="$2"
  local sum_cmd=""
  # 转绝对路径：--sha256 可能相对当前目录传入，而校验在 archive 目录下执行
  case "$checksum_file" in
    /*) : ;;
    *) checksum_file="$(cd "$(dirname "$checksum_file")" && pwd)/$(basename "$checksum_file")" ;;
  esac
  if command -v sha256sum >/dev/null 2>&1; then
    sum_cmd="sha256sum -c"
  elif command -v shasum >/dev/null 2>&1; then
    sum_cmd="shasum -a 256 -c"   # macOS 默认无 sha256sum
  else
    printf '%s\n' "[vod_install] ERROR: no checksum tool (sha256sum/shasum) available; refuse unverified install" >&2
    return 1
  fi
  (cd "$(dirname "$file")" && $sum_cmd "$checksum_file") || {
    printf '%s\n' "[vod_install] ERROR: Checksum verification failed!" >&2
    return 1
  }
}

_manifest_lookup() {
  local name="$1"
  [ -f "$CHECKSUM_MANIFEST" ] || return 0
  awk -v want="$name" '
    /^[[:space:]]*#/ { next }
    NF >= 2 {
      hash = $1
      file = $2
      sub(/^\*/, "", file)
      n = split(file, parts, "/")
      if (parts[n] == want) { print hash; exit }
    }
  ' "$CHECKSUM_MANIFEST"
}

# ---- install from pre-built archive ----
# 返回 0=已安装 / 2=无校验来源 / 3=与清单不符（后两者由调用方回退源码构建）
install_from_archive() {
  local archive="$1"
  local rc=0
  verify_checksum "$archive" || rc=$?
  case "$rc" in
    0) : ;;
    *) return "$rc" ;;
  esac
  echo "[vod_install] Extracting ${archive} -> ${BIN_DIR} ..."
  tar -xzf "$archive" -C "${BIN_DIR}/"
  return 0
}

# ---- install from source ----
install_from_source() {
  local repo_dir="$1"
  echo "[vod_install] Building from source in ${repo_dir} ..."
  pushd "$repo_dir" > /dev/null
  if ! go build -ldflags "-s -w" -o "${BIN_DIR}/atomcode-server" .; then
    popd > /dev/null
    printf '%s\n' "[vod_install] ERROR: source build failed (atomcode-server)." >&2
    printf '%s\n' "[vod_install] Upstream go.mod requires Go >= 1.22; install a newer Go (<https://go.dev/dl/>) or provide a trusted archive via --sha256 <file>." >&2
    return 1
  fi
  if [ -f "main.go" ]; then
    if ! go build -ldflags "-s -w" -o "${BIN_DIR}/atomcode-login" ./main.go; then
      popd > /dev/null
      printf '%s\n' "[vod_install] ERROR: source build failed (atomcode-login)." >&2
      return 1
    fi
  fi
  popd > /dev/null
  return 0
}

_install_source_or_fail() {
  local repo_dir="$1"
  if command -v go > /dev/null 2>&1; then
    printf '%s\n' "[vod_install] Falling back to building from source..."
    install_from_source "$repo_dir" || exit 1
  else
    printf '%s\n' "[vod_install] ERROR: Go toolchain not found and no verified pre-built archive available." >&2
    printf '%s\n' "[vod_install] Options: install Go >= 1.22 (https://go.dev/dl/), or pass --sha256 <file> with a trusted checksum file." >&2
    exit 1
  fi
}

# ---- install ----
do_install() {
  local repo_dir="${1:-}"
  local os arch arch_os

  # 平台检测提前: 不支持的 OS/arch 直接退出, 避免无谓克隆/构建
  os="$(uname -s)"
  arch="$(detect_arch)"   # detect_arch 在 unsupported 时 exit 1
  case "$os" in
    Linux)  arch_os="linux_${arch}" ;;
    Darwin) arch_os="darwin_${arch}" ;;
    *) printf '%s\n' "[vod_install] ERROR: unsupported OS ${os}" >&2; exit 1 ;;
  esac

  mkdir -p "${BIN_DIR}"

  # Clone repo if needed (临时目录由全局 EXIT trap 统一清理, 任何错误路径不残留)
  if [ -z "$repo_dir" ] || [ ! -d "$repo_dir" ]; then
    CLEANUP_DIR="$(mktemp -d)"
    echo "[vod_install] Cloning AtomGit-GO to ${CLEANUP_DIR} ..."
    git clone "${REPO_URL}" "${CLEANUP_DIR}/AtomGit-GO"
    repo_dir="${CLEANUP_DIR}/AtomGit-GO"
  fi

  # 预编译包按 OS 匹配(darwin 无包时自然回退源码构建)
  local archive="${repo_dir}/build/atomcode-login_${arch_os}.tar.gz"

  # Try pre-built archive first, fall back to source build
  if [ -f "$archive" ]; then
    local rc=0
    install_from_archive "$archive" || rc=$?
    case "$rc" in
      0) : ;;
      2)
        printf '%s\n' "[vod_install] No checksum source for the pre-built archive; skipping it (fail-closed)." >&2
        _install_source_or_fail "$repo_dir"
        ;;
      3)
        printf '%s\n' "[vod_install] Pre-built archive differs from the known-version manifest; skipping it (fail-closed)." >&2
        _install_source_or_fail "$repo_dir"
        ;;
      *)
        printf '%s\n' "[vod_install] Aborting due to checksum failure." >&2
        exit 1
        ;;
    esac
  else
    printf '%s\n' "[vod_install] Pre-built archive not found: ${archive}" >&2
    _install_source_or_fail "$repo_dir"
  fi

  # 兼容符号链接（上游不同 arch 的包内容不一致：arm64 带 atomcode-server，x86_64 带
  # atomcode-login-server）。两个名字缺哪个就从另一个补齐，保证三件套齐全。
  if [ -f "${BIN_DIR}/atomcode-server" ] && [ ! -e "${BIN_DIR}/atomcode-login-server" ]; then
    ln -sf "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server"
  elif [ -f "${BIN_DIR}/atomcode-login-server" ] && [ ! -e "${BIN_DIR}/atomcode-server" ]; then
    ln -sf "${BIN_DIR}/atomcode-login-server" "${BIN_DIR}/atomcode-server"
  fi

  chmod +x "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server" 2>/dev/null || true

  # 校验安装完整性: 三个目标可执行文件均须存在
  for f in atomcode-login atomcode-server atomcode-login-server; do
    if [ ! -x "${BIN_DIR}/$f" ]; then
      printf '%s\n' "[vod_install] ERROR: 安装不完整, 缺少可执行文件 ${BIN_DIR}/$f" >&2
      exit 1
    fi
  done

  echo "[vod_install] Done. Installed:"
  ls -la "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" 2>/dev/null || true
}

# ---- parse args (getopts) ----
REPO_DIR_ARG=""
SHA256_FILE_ARG=""
usage() {
  printf '%s\n' "用法: vod_install.sh [--repo-dir <path>] [--sha256 <file>]" >&2
}
while getopts ":h-:" opt; do
  case "$opt" in
    h) usage; exit 0 ;;
    -)
      case "${OPTARG}" in
        repo-dir)
          if [ $OPTIND -le $# ]; then
            REPO_DIR_ARG="${!OPTIND}"; OPTIND=$((OPTIND + 1))
          else
            printf '%s\n' "错误: --repo-dir 需要参数" >&2; exit 1
          fi
          ;;
        repo-dir=*) REPO_DIR_ARG="${OPTARG#repo-dir=}" ;;
        sha256)
          if [ $OPTIND -le $# ]; then
            SHA256_FILE_ARG="${!OPTIND}"; OPTIND=$((OPTIND + 1))
          else
            printf '%s\n' "错误: --sha256 需要参数" >&2; exit 1
          fi
          ;;
        sha256=*) SHA256_FILE_ARG="${OPTARG#sha256=}" ;;
        help) usage; exit 0 ;;
        *) printf '%s\n' "未知参数: --${OPTARG}" >&2; exit 1 ;;
      esac ;;
    \?) usage; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

# ---- main ----
# --repo-dir / --sha256 白名单校验: 拒绝以 - 开头、含空白/引号/元字符等非法输入
if [ -n "$REPO_DIR_ARG" ]; then
  case "$REPO_DIR_ARG" in
    -*|*[!A-Za-z0-9_./+-]*)
      printf '%s\n' "[vod_install] ERROR: --repo-dir 含非法字符(仅允许字母数字 _ . / + - 且不能以 - 开头)" >&2
      exit 1
      ;;
  esac
fi
if [ -n "$SHA256_FILE_ARG" ]; then
  case "$SHA256_FILE_ARG" in
    -*|*[!A-Za-z0-9_./+-]*)
      printf '%s\n' "[vod_install] ERROR: --sha256 含非法字符(仅允许字母数字 _ . / + - 且不能以 - 开头)" >&2
      exit 1
      ;;
  esac
fi
if check_installed; then
  echo "INSTALLED"
else
  echo "NOT_FOUND — installing..."
  do_install "${REPO_DIR_ARG}"
fi