#!/usr/bin/env bash
# Vod Collector - AtomGit-GO installation script (Linux/macOS)
# Usage: bash vod_install.sh [--repo-dir <path>]
# Prints open-source notice, checks if installed, and installs if needed.

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

# ---- verify checksum ----
verify_checksum() {
  local file="$1"
  local checksum_file="${file}.sha256"
  # 强制 fail-closed: 校验文件缺失/校验失败直接拒绝安装(无任何绕过开关)
  if [ ! -f "$checksum_file" ]; then
    printf '%s\n' "[vod_install] ERROR: checksum file missing (${checksum_file}); refuse to install unverified archive" >&2
    return 1
  fi
  echo "[vod_install] Verifying checksum (${checksum_file}) ..."
  local sum_cmd=""
  if command -v sha256sum >/dev/null 2>&1; then
    sum_cmd="sha256sum -c"
  elif command -v shasum >/dev/null 2>&1; then
    sum_cmd="shasum -a 256 -c"   # macOS 默认无 sha256sum
  else
    printf '%s\n' "[vod_install] ERROR: no checksum tool (sha256sum/shasum) available; refuse unverified install" >&2
    return 1
  fi
  (cd "$(dirname "$file")" && $sum_cmd "$(basename "$checksum_file")") || {
    printf '%s\n' "[vod_install] ERROR: Checksum verification failed!" >&2
    return 1
  }
  echo "[vod_install] Checksum verified."
  return 0
}

# ---- install from pre-built archive ----
install_from_archive() {
  local archive="$1"
  verify_checksum "$archive" || {
    printf '%s\n' "[vod_install] Aborting due to checksum failure." >&2
    exit 1
  }
  echo "[vod_install] Extracting ${archive} -> ${BIN_DIR} ..."
  tar -xzf "$archive" -C "${BIN_DIR}/"
}

# ---- install from source ----
install_from_source() {
  local repo_dir="$1"
  echo "[vod_install] Building from source in ${repo_dir} ..."
  pushd "$repo_dir" > /dev/null
  go build -ldflags "-s -w" -o "${BIN_DIR}/atomcode-server" .
  if [ -f "main.go" ]; then
    go build -ldflags "-s -w" -o "${BIN_DIR}/atomcode-login" ./main.go
  fi
  popd > /dev/null
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
    install_from_archive "$archive"
  else
    printf '%s\n' "[vod_install] Pre-built archive not found: ${archive}" >&2
    printf '%s\n' "[vod_install] Falling back to building from source..." >&2
    if command -v go > /dev/null 2>&1; then
      install_from_source "$repo_dir"
    else
      printf '%s\n' "[vod_install] ERROR: Go toolchain not found and no pre-built archive available." >&2
      printf '%s\n' "[vod_install] Install Go (https://go.dev/dl/) or provide a pre-built archive." >&2
      exit 1
    fi
  fi

  # Symlink for compatibility (atomcode-server -> atomcode-login-server)
  if [ -f "${BIN_DIR}/atomcode-server" ] && [ ! -f "${BIN_DIR}/atomcode-login-server" ]; then
    ln -sf "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server"
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
usage() {
  printf '%s\n' "用法: vod_install.sh [--repo-dir <path>]" >&2
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
        help) usage; exit 0 ;;
        *) printf '%s\n' "未知参数: --${OPTARG}" >&2; exit 1 ;;
      esac ;;
    \?) usage; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

# ---- main ----
# --repo-dir 白名单校验: 拒绝以 - 开头、含空白/引号/元字符等非法输入
if [ -n "$REPO_DIR_ARG" ]; then
  case "$REPO_DIR_ARG" in
    -*|*[!A-Za-z0-9_./+-]*)
      printf '%s\n' "[vod_install] ERROR: --repo-dir 含非法字符(仅允许字母数字 _ . / + - 且不能以 - 开头)" >&2
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
