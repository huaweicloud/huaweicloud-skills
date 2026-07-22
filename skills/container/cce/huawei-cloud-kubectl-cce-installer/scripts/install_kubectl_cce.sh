#!/usr/bin/env bash
set -euo pipefail

PLUGIN_VERSION="0.1.0"
PLUGIN_REPOSITORY="pancake0001/kubectl-cce-plugin"
PLUGIN_RELEASE_BASE_URL="https://gitee.com/${PLUGIN_REPOSITORY}/releases/download"
KUBERNETES_REPOSITORY="https://github.com/kubernetes/kubernetes.git"
PLUGIN_SOURCE_REPOSITORY="https://gitee.com/${PLUGIN_REPOSITORY}.git"
BIN_DIR="/usr/local/bin"
MODE="plan"
OBS_BASE_URL="https://cce-north-4.obs.cn-north-4.myhuaweicloud.com"
CONNECT_TIMEOUT="${KUBECTL_CCE_CONNECT_TIMEOUT:-10}"
DOWNLOAD_TIMEOUT="${KUBECTL_CCE_DOWNLOAD_TIMEOUT:-300}"
SOURCE_CLONE_TIMEOUT="${KUBECTL_CCE_SOURCE_CLONE_TIMEOUT:-600}"
SOURCE_BUILD_TIMEOUT="${KUBECTL_CCE_SOURCE_BUILD_TIMEOUT:-900}"

usage() {
  cat <<'EOF'
Usage: install_kubectl_cce.sh [--check] [--execute] [--bin-dir <directory>]

Without --execute, print the installation plan only. --execute installs missing
executables and must be used only after user confirmation.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --execute) MODE="execute" ;;
    --bin-dir)
      BIN_DIR="${2:?--bin-dir requires a directory}"
      shift
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

validate_timeout() {
  local name="$1"
  local value="$2"
  [[ "$value" =~ ^[1-9][0-9]*$ ]] || {
    echo "${name} must be a positive integer in seconds" >&2
    exit 2
  }
}

download_file() {
  local url="$1"
  local output="$2"
  curl --fail --show-error --location \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$DOWNLOAD_TIMEOUT" \
    "$url" -o "$output"
}

download_stdout() {
  curl --fail --show-error --location --silent \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$DOWNLOAD_TIMEOUT" \
    "$1"
}

run_with_timeout() {
  local timeout_seconds="$1"
  shift
  "$@" &
  local command_pid=$!
  (
    sleep "$timeout_seconds"
    if kill -0 "$command_pid" 2>/dev/null; then
      echo "Command timed out after ${timeout_seconds}s: $1" >&2
      kill -TERM "$command_pid" 2>/dev/null || true
      sleep 5
      kill -KILL "$command_pid" 2>/dev/null || true
    fi
  ) &
  local watchdog_pid=$!
  local status=0
  if wait "$command_pid"; then
    :
  else
    status=$?
  fi
  kill "$watchdog_pid" 2>/dev/null || true
  wait "$watchdog_pid" 2>/dev/null || true
  return "$status"
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "amd64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) echo "unsupported" ;;
  esac
}

install_file() {
  local source="$1"
  local destination="$2"
  cp "$source" "$destination"
  chmod 0755 "$destination"
}

install_latest_kubectl_from_obs() {
  local listing="$WORK_DIR/obs-kubectl-list.xml"
  local object_key package_file="$WORK_DIR/obs-kubectl.tgz" extract_dir="$WORK_DIR/obs-kubectl-extract" binary
  [[ "$OS" == "Linux" ]] || return 1
  download_file "${OBS_BASE_URL}/?list-type=2&prefix=package/kubectl/" "$listing"
  object_key="$(python3 - "$listing" "$ARCH" <<'PY'
import re, sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
arch = sys.argv[2]
items = []
for node in root.findall('{*}Contents/{*}Key'):
    key = node.text or ''
    match = re.fullmatch(r'package/kubectl/kubectl-(\d+)\.(\d+)\.(\d+)(-arm64)?\.tgz', key)
    if not match:
        continue
    if (arch == 'arm64') != bool(match.group(4)):
        continue
    items.append((tuple(map(int, match.group(1, 2, 3))), key))
if not items:
    raise SystemExit(1)
print(sorted(items)[-1][1])
PY
 )" || return 1
  echo "Selected latest OBS package: ${object_key}"
  download_file "${OBS_BASE_URL}/${object_key}" "$package_file"
  mkdir -p "$extract_dir"
  tar -xzf "$package_file" -C "$extract_dir"
  binary="$(find "$extract_dir" -type f -name kubectl -print -quit)"
  [[ -n "$binary" ]] || return 1
  chmod +x "$binary"
  install_file "$binary" "$BIN_DIR/kubectl"
}

build_kubectl_from_source() {
  local version="$1"
  local source_dir="$WORK_DIR/kubernetes"
  require_command git
  require_command go
  echo "Official kubectl download failed; building kubectl ${version} from the Kubernetes source tag."
  run_with_timeout "$SOURCE_CLONE_TIMEOUT" git clone --depth 1 --branch "$version" "$KUBERNETES_REPOSITORY" "$source_dir"
  run_with_timeout "$SOURCE_BUILD_TIMEOUT" bash -c '
    source_dir="$1"
    output="$2"
    cd "$source_dir"
    go build -o "$output" ./cmd/kubectl
  ' _ "$source_dir" "$WORK_DIR/kubectl"
  install_file "$WORK_DIR/kubectl" "$BIN_DIR/kubectl"
}

build_plugin_from_source() {
  local source_dir="$WORK_DIR/kubectl-cce-plugin"
  require_command git
  require_command go
  echo "kubectl-cce Release asset is unavailable; building plugin v${PLUGIN_VERSION} from source."
  run_with_timeout "$SOURCE_CLONE_TIMEOUT" git clone --depth 1 --branch "v${PLUGIN_VERSION}" "$PLUGIN_SOURCE_REPOSITORY" "$source_dir"
  run_with_timeout "$SOURCE_BUILD_TIMEOUT" bash -c '
    source_dir="$1"
    output="$2"
    cd "$source_dir"
    go build -o "$output" ./cmd/kubectl-cce
  ' _ "$source_dir" "$WORK_DIR/kubectl-cce"
  install_file "$WORK_DIR/kubectl-cce" "$BIN_DIR/kubectl-cce"
}

OS="$(uname -s)"
ARCH="$(detect_arch)"
KUBECTL_PRESENT=false
PLUGIN_PRESENT=false
command -v kubectl >/dev/null 2>&1 && KUBECTL_PRESENT=true
command -v kubectl-cce >/dev/null 2>&1 && PLUGIN_PRESENT=true

validate_timeout "KUBECTL_CCE_CONNECT_TIMEOUT" "$CONNECT_TIMEOUT"
validate_timeout "KUBECTL_CCE_DOWNLOAD_TIMEOUT" "$DOWNLOAD_TIMEOUT"
validate_timeout "KUBECTL_CCE_SOURCE_CLONE_TIMEOUT" "$SOURCE_CLONE_TIMEOUT"
validate_timeout "KUBECTL_CCE_SOURCE_BUILD_TIMEOUT" "$SOURCE_BUILD_TIMEOUT"

echo "platform=${OS} arch=${ARCH}"
echo "kubectl_present=${KUBECTL_PRESENT}"
echo "kubectl_cce_present=${PLUGIN_PRESENT}"
echo "bin_dir=${BIN_DIR}"

if [[ "$MODE" == "check" ]]; then
  if "$KUBECTL_PRESENT"; then kubectl version --client 2>/dev/null || true; fi
  if "$KUBECTL_PRESENT"; then kubectl plugin list 2>/dev/null || true; fi
  exit 0
fi

if [[ "$ARCH" == "unsupported" ]]; then
  echo "Unsupported CPU architecture: $(uname -m)" >&2
  exit 1
fi

if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
  echo "This installer supports Linux and macOS only. See references/plugin-usage.md for Windows." >&2
  exit 1
fi

if [[ "$KUBECTL_PRESENT" == false ]]; then
  echo "PLAN: install the latest public OBS kubectl package for Linux ${ARCH} into ${BIN_DIR}."
fi
if [[ "$PLUGIN_PRESENT" == false ]]; then
  echo "PLAN: download kubectl-cce v${PLUGIN_VERSION} for ${OS} ${ARCH} from Gitee Release when available; otherwise build tag v${PLUGIN_VERSION} from source."
fi
if [[ "$KUBECTL_PRESENT" == true && "$PLUGIN_PRESENT" == true ]]; then
  echo "Nothing to install. Run with --check to verify versions and plugin discovery."
  exit 0
fi
if [[ "$MODE" != "execute" ]]; then
  echo "No changes made. Re-run with --execute after user confirmation."
  exit 0
fi

require_command curl
require_command cp
require_command chmod
require_command tar
require_command python3
mkdir -p "$BIN_DIR"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

if [[ "$KUBECTL_PRESENT" == false ]]; then
  KUBECTL_VERSION="$(download_stdout https://dl.k8s.io/release/stable.txt)"
  KUBECTL_OS="$(tr '[:upper:]' '[:lower:]' <<< "$OS")"
  if install_latest_kubectl_from_obs; then
    :
  elif download_file "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${KUBECTL_OS}/${ARCH}/kubectl" "$WORK_DIR/kubectl"; then
    install_file "$WORK_DIR/kubectl" "$BIN_DIR/kubectl"
  else
    build_kubectl_from_source "$KUBECTL_VERSION"
  fi
fi

if [[ "$PLUGIN_PRESENT" == false ]]; then
  if [[ "$OS" == "Linux" ]]; then
    ASSET_NAME="kubectl-cce_${PLUGIN_VERSION}_linux_${ARCH}.tar.gz"
    ASSET_URL="${PLUGIN_RELEASE_BASE_URL}/v${PLUGIN_VERSION}/${ASSET_NAME}"
    if download_file "$ASSET_URL" "$WORK_DIR/$ASSET_NAME" && tar -xzf "$WORK_DIR/$ASSET_NAME" -C "$WORK_DIR" && [[ -f "$WORK_DIR/kubectl-cce" ]]; then
      install_file "$WORK_DIR/kubectl-cce" "$BIN_DIR/kubectl-cce"
    else
      build_plugin_from_source
    fi
  else
    build_plugin_from_source
  fi
fi

echo "Installation complete."
kubectl version --client
kubectl plugin list
kubectl plugin list | grep -q 'kubectl-cce' || {
  echo "kubectl-cce was installed but is not discoverable by kubectl. Verify that ${BIN_DIR} is in PATH." >&2
  exit 1
}
