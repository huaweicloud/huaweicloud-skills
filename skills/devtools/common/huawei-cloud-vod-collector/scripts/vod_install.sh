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

# ---- verify checksum ----
verify_checksum() {
  local file="$1"
  local checksum_file="${file}.sha256"
  if [ ! -f "$checksum_file" ]; then
    echo "[vod_install] WARNING: No checksum file found at ${checksum_file}, skipping verification" >&2
    return 0
  fi
  echo "[vod_install] Verifying checksum..."
  (cd "$(dirname "$file")" && sha256sum -c "$(basename "$checksum_file")") || {
    echo "[vod_install] ERROR: Checksum verification failed!" >&2
    return 1
  }
  echo "[vod_install] Checksum verified."
  return 0
}

# ---- install from pre-built archive ----
install_from_archive() {
  local archive="$1"
  verify_checksum "$archive" || {
    echo "[vod_install] Aborting due to checksum failure." >&2
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

  # Try pre-built archive first, fall back to source build
  if [ -f "$archive" ]; then
    install_from_archive "$archive"
  else
    echo "[vod_install] Pre-built archive not found: ${archive}" >&2
    echo "[vod_install] Falling back to building from source..." >&2
    if command -v go > /dev/null 2>&1; then
      install_from_source "$repo_dir"
    else
      echo "[vod_install] ERROR: Go toolchain not found and no pre-built archive available." >&2
      echo "[vod_install] Install Go (https://go.dev/dl/) or provide a pre-built archive." >&2
      if [ -n "$tmp_dir" ]; then
        rm -rf "$tmp_dir"
      fi
      exit 1
    fi
  fi

  # Symlink for compatibility (atomcode-server -> atomcode-login-server)
  if [ -f "${BIN_DIR}/atomcode-server" ] && [ ! -f "${BIN_DIR}/atomcode-login-server" ]; then
    ln -sf "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server"
  fi

  chmod +x "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" "${BIN_DIR}/atomcode-login-server" 2>/dev/null || true

  # Cleanup
  if [ -n "$tmp_dir" ]; then
    rm -rf "$tmp_dir"
  fi

  echo "[vod_install] Done. Installed:"
  ls -la "${BIN_DIR}/atomcode-login" "${BIN_DIR}/atomcode-server" 2>/dev/null
}

# ---- parse args ----
REPO_DIR_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo-dir)
      REPO_DIR_ARG="$2"
      shift 2
      ;;
    --repo-dir=*)
      REPO_DIR_ARG="${1#--repo-dir=}"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# ---- main ----
if check_installed; then
  echo "INSTALLED"
else
  echo "NOT_FOUND — installing..."
  do_install "${REPO_DIR_ARG}"
fi
