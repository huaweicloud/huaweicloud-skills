#!/usr/bin/env bash
# Vod Collector - AtomGit-GO installation script (Linux/macOS)
# Usage: bash vod_install.sh [--repo-dir <path>]
# Prints open-source notice, checks if installed, and installs if needed.

set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
REPO_URL="https://gitcode.com/weixin_45218422/AtomGit-GO.git"

# ---- detect platform ----
detect_arch() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "arm_64" ;;
    *) echo "unsupported: $arch" >&2; exit 1 ;;
  esac
}

# ---- check ----
check_installed() {
  if ls "${BIN_DIR}/atomcode-login-server" "${BIN_DIR}/atomcode-server" 2>/dev/null | grep -q .; then
    return 0
  else
    return 1
  fi
}

# ---- install ----
do_install() {
  local repo_dir="${1:-}"
  local tmp_dir=""

  mkdir -p "${BIN_DIR}"

  # Clone repo if needed
  if [ -z "$repo_dir" ] || [ ! -d "$repo_dir" ]; then
    tmp_dir="$(mktemp -d)"
    echo "[vod_install] Cloning AtomGit-GO to ${tmp_dir} ..."
    git clone "${REPO_URL}" "${tmp_dir}/AtomGit-GO"
    repo_dir="${tmp_dir}/AtomGit-GO"
  fi

  local arch
  arch="$(detect_arch)"
  local archive="${repo_dir}/build/atomcode-login_linux_${arch}.tar.gz"

  if [ ! -f "$archive" ]; then
    echo "[vod_install] Archive not found: ${archive}" >&2
    echo "[vod_install] Expected at build/atomcode-login_linux_${arch}.tar.gz" >&2
    exit 1
  fi

  echo "[vod_install] Extracting ${archive} -> ${BIN_DIR} ..."
  tar -xzf "$archive" -C "${BIN_DIR}/"

  # Symlink for compatibility (atomcode-server -> atomcode-login-server)
  if [ -f "${BIN_DIR}/atomcode-server" ] && [ ! -f "${BIN_DIR}/atomcode-login-server" ]; then
    ln -sf "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server"
  fi

  chmod +x "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" 2>/dev/null || true

  # Cleanup
  if [ -n "$tmp_dir" ]; then
    rm -rf "$tmp_dir"
  fi

  echo "[vod_install] Done. Installed:"
  ls -la "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" 2>/dev/null
}

# ---- main ----
if check_installed; then
  echo "INSTALLED"
else
  echo "NOT_FOUND — installing..."
  do_install "${1:-}"
fi
