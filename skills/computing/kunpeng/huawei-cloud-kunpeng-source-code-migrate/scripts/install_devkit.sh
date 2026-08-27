#!/bin/bash
set -euo pipefail
# ============================================================================
# Kunpeng DevKit CLI Installation Script
# ============================================================================
# Automates the complete installation of Kunpeng DevKit CLI on a Linux machine.
# Can be run locally or on a remote server via SSH (using ssh_client.py).
#
# Usage:
#   Local install:
#     bash install_devkit.sh
#
#   Remote install (via ssh_client.py):
#     1) python <skill_dir>/scripts/ssh_client.py put <script> /tmp/install_devkit.sh
#     2) python <skill_dir>/scripts/ssh_client.py exec "bash /tmp/install_devkit.sh"
#
# Options:
#   --version=VERSION   Specify DevKit version (default: auto-detect latest stable)
#   --prefix=PATH       Install prefix (default: /usr/local)
#   --no-sudo           Install to user home directory without sudo
#   --skip-deps         Skip dependency installation step
#   --offline=FILE      Install from a local tar.gz file (no download needed)
#   --yes               Skip all confirmation prompts
#
# Exit codes:
#   0 - Success
#   1 - General error (unsupported OS, download failed, etc.)
#   2 - Dependency installation failed
#   3 - Download failed
#   4 - Installation failed
#   5 - Verification failed
# ============================================================================

# ---- Configuration ----
DEVKIT_MIRROR_BASE="https://mirrors.huaweicloud.com/kunpeng/archive/DevKit/Packages/Kunpeng_DevKit"
DEFAULT_VERSION="26.1.RC1"
INSTALL_PREFIX="/usr/local"
INSTALL_DIR="${INSTALL_PREFIX}/devkit"
TMP_DIR="/tmp/devkit-install"
SKIP_DEPS=false
NO_SUDO=false
OFFLINE_FILE=""
AUTO_YES=false

# ---- Color output ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- Parse arguments ----
parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --version=*)
                DEFAULT_VERSION="${arg#*=}"
                ;;
            --prefix=*)
                INSTALL_PREFIX="${arg#*=}"
                INSTALL_DIR="${INSTALL_PREFIX}/devkit"
                ;;
            --no-sudo)
                NO_SUDO=true
                INSTALL_DIR="$HOME/devkit"
                ;;
            --skip-deps)
                SKIP_DEPS=true
                ;;
            --offline=*)
                OFFLINE_FILE="${arg#*=}"
                ;;
            --yes)
                AUTO_YES=true
                ;;
            *)
                log_warn "Unknown argument: $arg"
                ;;
        esac
    done
}

# ---- Step 1: Detect OS and Architecture ----
detect_os() {
    log_info "Step 1/6: Detecting OS and architecture..."

    ARCH=$(uname -m)
    OS_INFO=$(cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo "")

    # Determine architecture suffix for DevKit package
    case "$ARCH" in
        x86_64)
            PKG_ARCH="x86-64"
            ;;
        aarch64)
            PKG_ARCH="Kunpeng"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH (only x86_64 and aarch64 are supported)"
            exit 1
            ;;
    esac

    # Determine OS type for package manager selection
    OS_TYPE="unknown"
    PKG_MANAGER="unknown"

    if echo "$OS_INFO" | grep -qi "openEuler"; then
        OS_TYPE="openEuler"; PKG_MANAGER="yum"
    elif echo "$OS_INFO" | grep -qi "CentOS\|Red Hat"; then
        OS_TYPE="CentOS"; PKG_MANAGER="yum"
    elif echo "$OS_INFO" | grep -qi "EulerOS"; then
        OS_TYPE="EulerOS"; PKG_MANAGER="yum"
    elif echo "$OS_INFO" | grep -qi "Ubuntu"; then
        OS_TYPE="Ubuntu"; PKG_MANAGER="apt"
    elif echo "$OS_INFO" | grep -qi "Debian"; then
        OS_TYPE="Debian"; PKG_MANAGER="apt"
    elif echo "$OS_INFO" | grep -qi "Kylin"; then
        OS_TYPE="Kylin"; PKG_MANAGER="apt"
    elif echo "$OS_INFO" | grep -qi "UOS"; then
        OS_TYPE="UOS"; PKG_MANAGER="apt"
    elif echo "$OS_INFO" | grep -qi "NeoKylin"; then
        OS_TYPE="NeoKylin"; PKG_MANAGER="yum"
    elif echo "$OS_INFO" | grep -qi "SUSE\|SLES"; then
        OS_TYPE="SUSE"; PKG_MANAGER="zypper"
    fi

    log_ok "Architecture: $ARCH (package suffix: $PKG_ARCH)"
    log_ok "OS Type: $OS_TYPE"
    log_ok "Package Manager: $PKG_MANAGER"

    if [ "$OS_TYPE" = "unknown" ]; then
        log_error "Unsupported OS. DevKit supports: openEuler, CentOS, EulerOS, Ubuntu, Debian, Kylin, UOS, NeoKylin, SUSE"
        log_error "OS info: $OS_INFO"
        exit 1
    fi
}

# ---- Step 2: Check Existing Installation ----
check_existing() {
    log_info "Step 2/6: Checking existing DevKit installation..."

    if [ -f "${INSTALL_DIR}/devkit" ]; then
        EXISTING_VERSION=$("${INSTALL_DIR}/devkit" --version 2>/dev/null || echo "unknown")
        log_ok "DevKit is already installed: $EXISTING_VERSION at ${INSTALL_DIR}"

        if [ "$AUTO_YES" = false ]; then
            echo -n "Reinstall? [y/N]: "
            read -r REINSTALL
            if [ "$REINSTALL" != "y" ] && [ "$REINSTALL" != "Y" ]; then
                log_info "Skipping installation. Existing DevKit will be used."
                exit 0
            fi
        fi
    else
        log_info "DevKit is not installed. Proceeding with installation."
    fi
}

# ---- Step 3: Install Dependencies ----
install_deps() {
    if [ "$SKIP_DEPS" = true ]; then
        log_info "Step 3/6: Skipping dependency installation (--skip-deps)."
        return 0
    fi

    log_info "Step 3/6: Installing dependencies..."

    SUDO=""
    if [ "$NO_SUDO" = false ] && [ "$(id -u)" -ne 0 ]; then
        SUDO="sudo"
    fi

    case "$PKG_MANAGER" in
        yum)
            $SUDO yum install -y python3 python3-pip curl 2>&1 || {
                log_error "Failed to install dependencies via yum."
                exit 2
            }
            ;;
        apt)
            $SUDO apt-get update -qq 2>&1 || true
            $SUDO apt-get install -y python3 python3-pip curl 2>&1 || {
                log_error "Failed to install dependencies via apt."
                exit 2
            }
            ;;
        zypper)
            $SUDO zypper install -y python3 python3-pip curl 2>&1 || {
                log_error "Failed to install dependencies via zypper."
                exit 2
            }
            ;;
        *)
            log_warn "Unknown package manager: $PKG_MANAGER. Please install python3, pip, curl manually."
            ;;
    esac

    log_ok "Dependencies installed."
}

# ---- Step 4: Download DevKit Package ----
download_devkit() {
    log_info "Step 4/6: Downloading DevKit CLI package..."

    # If offline file is specified, use it
    if [ -n "$OFFLINE_FILE" ]; then
        log_info "Using offline package: $OFFLINE_FILE"
        mkdir -p "$TMP_DIR"
        cp "$OFFLINE_FILE" "$TMP_DIR/"
        log_ok "Offline package copied to $TMP_DIR"
        return 0
    fi

    # Determine version to download
    DEVKIT_VERSION="$DEFAULT_VERSION"

    mkdir -p "$TMP_DIR"

    # Try to list available versions from mirror
    log_info "Checking available versions from mirror..."
    AVAILABLE_VERSIONS=$(curl -sL "${DEVKIT_MIRROR_BASE}/" 2>/dev/null | grep -oP "DevKit-CLI-[^\"]+Linux-${PKG_ARCH}[^\"]+\\.tar\\.gz" | sort -V | tail -5 || echo "")

    if [ -n "$AVAILABLE_VERSIONS" ]; then
        # Extract the latest stable version (prefer non-RC)
        LATEST_STABLE=$(echo "$AVAILABLE_VERSIONS" | grep -v "RC" | tail -1 || echo "")
        if [ -n "$LATEST_STABLE" ]; then
            DEVKIT_VERSION=$(echo "$LATEST_STABLE" | grep -oP 'DevKit-CLI-\K[0-9]+\.[0-9]+\.[0-9]+' || echo "$DEFAULT_VERSION")
            log_ok "Latest stable version detected: $DEVKIT_VERSION"
        else
            log_warn "No stable version found, using default: $DEVKIT_VERSION"
        fi
    else
        log_warn "Could not fetch version list from mirror. Using default: $DEVKIT_VERSION"
    fi

    # Construct download URL
    DEVKIT_URL="${DEVKIT_MIRROR_BASE}/DevKit-CLI-${DEVKIT_VERSION}-Linux-${PKG_ARCH}.tar.gz"
    DEVKIT_PKG="DevKit-CLI-${DEVKIT_VERSION}-Linux-${PKG_ARCH}.tar.gz"

    log_info "Downloading: $DEVKIT_URL"
    cd "$TMP_DIR"
    curl -L -O "$DEVKIT_URL" 2>&1 || {
        log_error "Download failed. Trying alternative versions..."

        # Fallback: try a few known versions
        for FALLBACK_VERSION in "25.3.0" "25.1.0" "26.1.RC1"; do
            if [ "$FALLBACK_VERSION" = "$DEVKIT_VERSION" ]; then
                continue  # Skip the one we already tried
            fi
            FALLBACK_URL="${DEVKIT_MIRROR_BASE}/DevKit-CLI-${FALLBACK_VERSION}-Linux-${PKG_ARCH}.tar.gz"
            log_info "Trying fallback version: $FALLBACK_VERSION"
            if curl -L -O "$FALLBACK_URL" 2>&1; then
                DEVKIT_VERSION="$FALLBACK_VERSION"
                DEVKIT_PKG="DevKit-CLI-${DEVKIT_VERSION}-Linux-${PKG_ARCH}.tar.gz"
                break
            fi
        done
    }

    # Verify download
    if [ ! -f "$TMP_DIR/$DEVKIT_PKG" ]; then
        log_error "Download failed. No package file found."
        log_error "Please download manually from: ${DEVKIT_MIRROR_BASE}/"
        log_error "Then re-run with: --offline=/path/to/DevKit-CLI-xxx.tar.gz"
        exit 3
    fi

    FILE_SIZE=$(stat -c%s "$TMP_DIR/$DEVKIT_PKG" 2>/dev/null || stat -f%z "$TMP_DIR/$DEVKIT_PKG" 2>/dev/null || echo "0")
    if [ "$FILE_SIZE" -lt 1024 ]; then
        log_error "Downloaded file is too small (${FILE_SIZE} bytes). Likely a 404 error page."
        log_error "Please check available versions at: ${DEVKIT_MIRROR_BASE}/"
        exit 3
    fi

    log_ok "Downloaded: $DEVKIT_PKG (${FILE_SIZE} bytes)"
}

# ---- Step 5: Install DevKit ----
install_devkit() {
    log_info "Step 5/6: Installing DevKit CLI..."

    SUDO=""
    if [ "$NO_SUDO" = false ] && [ "$(id -u)" -ne 0 ]; then
        SUDO="sudo"
    fi

    # Extract
    cd "$TMP_DIR"
    tar -xzf DevKit-CLI-*.tar.gz

    # Verify extraction
    EXTRACTED_DIR=$(ls -d "$TMP_DIR"/DevKit-CLI-*/ 2>/dev/null | head -1)
    if [ -z "$EXTRACTED_DIR" ]; then
        log_error "Extraction failed. No DevKit-CLI-* directory found."
        exit 4
    fi

    # Create install directory
    $SUDO mkdir -p "$INSTALL_DIR"

    # Copy ALL files including hidden files using cp -a on the directory itself
    # This ensures hidden files like .devkit are preserved if they exist
    # Some DevKit versions include .devkit, others don't — both are valid
    $SUDO cp -a "${EXTRACTED_DIR}." "$INSTALL_DIR/"

    # Verify the devkit binary was copied
    if [ ! -f "${INSTALL_DIR}/devkit" ]; then
        log_error "devkit binary not found after copy. Package may be corrupted."
        exit 4
    fi

    # Make executable
    $SUDO chmod +x "${INSTALL_DIR}/devkit"

    # Create symlink (only if installing to system prefix)
    if [ "$INSTALL_PREFIX" = "/usr/local" ]; then
        $SUDO ln -sf "${INSTALL_DIR}/devkit" /usr/local/bin/devkit
    else
        log_info "Install prefix is $INSTALL_PREFIX. Add to PATH manually:"
        log_info "  export PATH=${INSTALL_DIR}:\$PATH"
    fi

    log_ok "DevKit installed to: $INSTALL_DIR"
}

# ---- Step 6: Verify Installation ----
verify_installation() {
    log_info "Step 6/6: Verifying installation..."

    # Check version (this is the real verification — if devkit runs, it's installed correctly)
    VERSION_OUTPUT=$(cd "$INSTALL_DIR" && ./devkit --version 2>&1) || {
        log_error "Failed to run devkit --version."
        log_error "Possible causes:"
        log_error "  1. Architecture mismatch (wrong package)"
        log_error "  2. Missing system dependencies (libstdc++, glibc)"
        log_error "  3. Missing .devkit file (some versions require it)"
        exit 5
    }
    log_ok "DevKit version: $VERSION_OUTPUT"

    # Check help
    HELP_OUTPUT=$(cd "$INSTALL_DIR" && ./devkit --help 2>&1) || {
        log_warn "devkit --help returned an error, but installation may still work."
    }

    # Check src-mig subcommand
    SRCMIG_OUTPUT=$(cd "$INSTALL_DIR" && ./devkit porting src-mig --help 2>&1) || {
        log_warn "devkit porting src-mig --help returned an error."
    }

    if echo "$SRCMIG_OUTPUT" | grep -q "src-mig\|source-type\|input"; then
        log_ok "DevKit porting src-mig command is available."
    fi

    # Print summary
    echo ""
    log_ok "============================================"
    log_ok "  DevKit CLI Installation Complete!"
    log_ok "============================================"
    echo ""
    echo "  Install Dir:   ${INSTALL_DIR}"
    echo "  Version:       ${VERSION_OUTPUT}"
    echo "  Architecture:  ${ARCH} (${PKG_ARCH})"
    echo "  OS:            ${OS_TYPE}"
    echo ""

    if [ "$INSTALL_PREFIX" = "/usr/local" ]; then
        echo "  Run DevKit:"
        echo "    cd ${INSTALL_DIR} && ./devkit porting src-mig -i <source_path> -o <output_path> -s 'c, c++, asm'"
        echo ""
        echo "  Or use symlink:"
        echo "    devkit porting src-mig -i <source_path> -o <output_path> -s 'c, c++, asm'"
    else
        echo "  Run DevKit:"
        echo "    export PATH=${INSTALL_DIR}:\$PATH"
        echo "    devkit porting src-mig -i <source_path> -o <output_path> -s 'c, c++, asm'"
    fi

    echo ""
    log_info "Scan example:"
    echo "  cd ${INSTALL_DIR} && ./devkit porting src-mig -i /path/to/source -o /tmp/devkit-report -s 'c, c++, asm' -r all"
    echo ""
}

# ---- Main ----
main() {
    parse_args "$@"

    echo ""
    log_info "============================================"
    log_info "  Kunpeng DevKit CLI Installation Script"
    log_info "============================================"
    echo ""

    detect_os
    check_existing
    install_deps
    download_devkit
    install_devkit
    verify_installation
}

main "$@"
