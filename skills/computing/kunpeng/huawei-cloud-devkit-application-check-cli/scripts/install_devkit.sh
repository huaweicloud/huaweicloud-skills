#!/bin/bash
set -euo pipefail
# ---
# DevKit CLI Compress (tar.gz) Installation Script
#
# Execution mode: manual (local script, runs on DevKit server).
# No hcloud CLI/SDK/API equivalent — this is a custom bash script for
# downloading and installing Kunpeng DevKit CLI from the Kunpeng repository.
#
# Install mode: Compress only (tar.gz)
# Supports both x86_64 and aarch64 (Kunpeng) architectures
# Usage: bash install_devkit.sh [--version <version> | --check-maven]
#   If --version is omitted, defaults to 26.1.RC1
#   Package is downloaded from Kunpeng repository based on detected architecture
#   --check-maven: Only check and install Maven environment (for mvn_analyse scan)
# Reference: https://www.hikunpeng.com/document/detail/zh/kunpengdevps/install/installguide/KunpengDevKitCli_0004.html
# Maven reference: https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/systemmigration/KunpengDevKitCli_0105.html
# ---

DEVKIT_VERSION="26.1.RC1"
CHECK_MAVEN_ONLY="false"
SHOW_HELP="false"

usage() {
    echo "Usage: bash $0 [--version <version> | --check-maven]"
    echo "  If --version is omitted, defaults to 26.1.RC1"
    echo "  --version <version>: DevKit version to download (e.g. 26.1.RC1)"
    echo "  --check-maven: Only check and install Maven environment (for mvn_analyse scan)"
}

parse_args() {
    # Map long options to single-letter options, then parse via getopts.
    local mapped=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --check-maven) mapped+=("-c"); shift ;;
            --version)
                shift
                if [ $# -gt 0 ]; then mapped+=("-v" "$1"); shift; else echo "--version requires a value" >&2; usage >&2; exit 1; fi
                ;;
            --version=*) mapped+=("-v" "${1#--version=}"); shift ;;
            --help|-h) mapped+=("-h"); shift ;;
            --) shift; break ;;
            *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
        esac
    done
    # ${mapped[@]+...} guard: safe for empty arrays under "set -u" on bash 4.2 (CentOS 7).
    set -- ${mapped[@]+"${mapped[@]}"}

    local opt
    while getopts ":v:ch" opt; do
        case "${opt}" in
            v) DEVKIT_VERSION="${OPTARG}" ;;
            c) CHECK_MAVEN_ONLY="true" ;;
            h) SHOW_HELP="true" ;;
            \?) echo "Unknown argument: -${OPTARG}" >&2; usage >&2; exit 1 ;;
            :) echo "Option -${OPTARG} requires a value (e.g. --version <version>)" >&2; usage >&2; exit 1 ;;
        esac
    done
}
parse_args "$@"
if [ "${SHOW_HELP}" = "true" ]; then
    usage
    exit 0
fi
DEVKIT_HOME="${DEVKIT_HOME:-/home}"
DEVKIT_DIR="${DEVKIT_HOME}/DevKit"
DEVKIT_COMPRESS_PKG=""
DEVKIT_PKG_DIR=""

DEVKIT_DOWNLOAD_BASE="https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%20${DEVKIT_VERSION}"
DEVKIT_X86_URL="${DEVKIT_DOWNLOAD_BASE}/DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-x86-64.tar.gz"
DEVKIT_ARM_URL="${DEVKIT_DOWNLOAD_BASE}/DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-Kunpeng.tar.gz"

MAVEN_VERSION="3.8.8"
MAVEN_TARBALL="apache-maven-${MAVEN_VERSION}-bin.tar.gz"
MAVEN_URL="https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/${MAVEN_TARBALL}"
MAVEN_INSTALL_DIR="${DEVKIT_HOME}/maven"
MAVEN_HOME="${MAVEN_INSTALL_DIR}/apache-maven-${MAVEN_VERSION}"

# ---
# 1. Logging Utilities
# ---

log_info()  { echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_step()  { echo ""; echo "----"; echo "  $*"; echo "===="; }

# ---
# 2. OS & Architecture Detection
# ---

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${ID}-${VERSION_ID}"
    else
        log_error "Cannot detect OS: /etc/os-release not found."
        exit 1
    fi
}

check_os() {
    log_step "[1/5] Checking OS Compatibility"
    local os_id
    os_id=$(detect_os)
    log_info "Detected OS: ${os_id}"

    case "${os_id}" in
        centos-7|CentOS-7)
            log_info "OS check passed: CentOS 7.6"
            ;;
        ubuntu-20.04|Ubuntu-20.04)
            log_info "OS check passed: Ubuntu 20.04"
            ;;
        *)
            log_error "Unsupported OS: ${os_id}. DevKit server only supports CentOS 7.6 and Ubuntu 20.04."
            exit 1
            ;;
    esac
}

detect_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)
            log_info "Detected architecture: x86_64"
            DEVKIT_COMPRESS_PKG="DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-x86-64.tar.gz"
            DEVKIT_PKG_DIR="${DEVKIT_DIR}/DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-x86-64"
            ;;
        aarch64)
            log_info "Detected architecture: aarch64 (Kunpeng)"
            DEVKIT_COMPRESS_PKG="DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-Kunpeng.tar.gz"
            DEVKIT_PKG_DIR="${DEVKIT_DIR}/DevKit-Sys-Mig-CLI-${DEVKIT_VERSION}-Linux-Kunpeng"
            ;;
        *)
            log_error "Unsupported architecture: $arch. DevKit requires x86_64 or aarch64."
            exit 1
            ;;
    esac
}

# ---
# 3. DevKit Installation
# ---

install_deps() {
    log_step "[2/5] Installing Dependencies"
    local os_id
    os_id=$(detect_os)
    log_info "Detected OS: $os_id"

    case "$os_id" in
        centos-7|CentOS-7)
            yum install -y wget curl tar gzip 2>/dev/null || true
            ;;
        ubuntu-20.04|Ubuntu-20.04)
            apt-get update -y 2>/dev/null || true
            apt-get install -y wget curl tar gzip 2>/dev/null || true
            ;;
        *)
            log_error "Unsupported OS: $os_id. DevKit server only supports CentOS 7.6 and Ubuntu 20.04."
            exit 1
            ;;
    esac
    log_info "Dependencies installed."
}

download_package() {
    log_step "[3/5] Downloading DevKit Package"
    mkdir -p "${DEVKIT_DIR}"

    local pkg_path="${DEVKIT_DIR}/${DEVKIT_COMPRESS_PKG}"

    if [ -f "${pkg_path}" ] && tar -tzf "${pkg_path}" >/dev/null 2>&1; then
        log_info "Valid package already exists: ${DEVKIT_COMPRESS_PKG}, skipping download."
        return 0
    fi

    if [ -f "${pkg_path}" ]; then
        log_info "Existing package is corrupted, removing ..."
        rm -f "${pkg_path}"
    fi

    local download_url
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64) download_url="${DEVKIT_X86_URL}" ;;
        aarch64) download_url="${DEVKIT_ARM_URL}" ;;
    esac

    log_info "Downloading: ${download_url}"
    log_info "Target: ${pkg_path}"

    if command -v wget >/dev/null 2>&1; then
        wget -q -O "${pkg_path}" "${download_url}"
    elif command -v curl >/dev/null 2>&1; then
        curl -fL -o "${pkg_path}" "${download_url}"
    else
        log_error "Neither wget nor curl is available. Cannot download package."
        exit 1
    fi

    if [ ! -f "${pkg_path}" ] || [ ! -s "${pkg_path}" ]; then
        log_error "Download failed or file is empty: ${pkg_path}"
        rm -f "${pkg_path}"
        exit 1
    fi

    if ! tar -tzf "${pkg_path}" >/dev/null 2>&1; then
        log_error "Downloaded package is corrupted: ${DEVKIT_COMPRESS_PKG}"
        rm -f "${pkg_path}"
        exit 1
    fi

    log_info "Download complete: ${DEVKIT_COMPRESS_PKG} ($(du -h "${pkg_path}" | cut -f1))"
}

install_compress() {
    log_step "[4/5] Installing DevKit via Compress (tar.gz)"
    cd "${DEVKIT_DIR}"

    if [ -z "${DEVKIT_COMPRESS_PKG}" ] || [ ! -f "${DEVKIT_COMPRESS_PKG}" ]; then
        log_error "Package not found in ${DEVKIT_DIR}/"
        log_error "Expected: ${DEVKIT_COMPRESS_PKG}"
        exit 1
    fi

    if [ -d "${DEVKIT_PKG_DIR}" ]; then
        log_info "Extracted directory already exists: ${DEVKIT_PKG_DIR}, skipping extraction."
    else
        log_info "Extracting ${DEVKIT_COMPRESS_PKG} ..."
        tar -zxvf "${DEVKIT_COMPRESS_PKG}"
    fi

    # Clean up: remove the compress package after extraction (regardless of whether extraction was skipped)
    if [ -f "${DEVKIT_COMPRESS_PKG}" ]; then
        log_info "Removing compress package: ${DEVKIT_COMPRESS_PKG}"
        rm -f "${DEVKIT_COMPRESS_PKG}"
    fi

    if ! grep -q "${DEVKIT_PKG_DIR}" /etc/profile 2>/dev/null; then
        echo "export PATH=${DEVKIT_PKG_DIR}:\$PATH" >> /etc/profile
        log_info "Added DevKit to PATH in /etc/profile"
    fi

    export PATH="${DEVKIT_PKG_DIR}:${PATH}"
    log_info "Compress package extracted and PATH configured."
}

verify_install() {
    log_step "[5/5] Verifying DevKit Installation"
    if [ -n "${DEVKIT_PKG_DIR}" ] && [ -x "${DEVKIT_PKG_DIR}/devkit" ]; then
        "${DEVKIT_PKG_DIR}/devkit" version
    elif command -v devkit >/dev/null 2>&1; then
        devkit version
    else
        log_error "DevKit command not found after installation."
        log_error "Check that ${DEVKIT_PKG_DIR:-<unknown>}/devkit exists and is executable."
        exit 1
    fi
    log_info "DevKit installation verified."
}

# ---
# 4. sshpass Installation
# ---

install_sshpass() {
    log_step "Installing sshpass"

    if command -v sshpass >/dev/null 2>&1; then
        log_info "sshpass is already installed: $(sshpass -V 2>&1 | head -1)"
        return 0
    fi

    local os_id
    os_id=$(detect_os)
    log_info "Detected OS: ${os_id}"

    case "${os_id}" in
        centos-7|CentOS-7)
            log_info "Installing epel-release for sshpass ..."
            yum install -y epel-release >/dev/null 2>&1 || true
            log_info "Installing sshpass via yum ..."
            yum install -y sshpass >/dev/null 2>&1
            ;;
        ubuntu-20.04|Ubuntu-20.04)
            log_info "Installing sshpass via apt-get ..."
            apt-get update -y >/dev/null 2>&1 || true
            apt-get install -y sshpass >/dev/null 2>&1
            ;;
        *)
            log_error "Unsupported OS: ${os_id}. Please install sshpass manually."
            return 1
            ;;
    esac

    if command -v sshpass >/dev/null 2>&1; then
        log_info "sshpass installed successfully: $(sshpass -V 2>&1 | head -1)"
    else
        log_error "Failed to install sshpass. Please install it manually."
        return 1
    fi
}

# ---
# 5. Maven Environment Setup
# ---

check_and_install_maven() {
    log_step "Maven Environment Check (for mvn_analyse)"

    local os_id
    os_id=$(detect_os)

    # Step 1: Check Java, install if not present
    log_info "Checking JDK..."
    if java -version >/dev/null 2>&1; then
        local java_ver
        java_ver=$(java -version 2>&1 | head -1)
        log_info "JDK installed: ${java_ver}"
    else
        log_error "JDK is not installed. Installing OpenJDK..."
        case "${os_id}" in
            centos-7|CentOS-7)
                yum install -y java-1.8.0-openjdk-devel >/dev/null 2>&1 || yum install -y java-devel >/dev/null 2>&1
                ;;
            ubuntu-20.04|Ubuntu-20.04)
                apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq default-jdk >/dev/null 2>&1
                ;;
            *)
                log_error "Unsupported OS: ${os_id}. Please install JDK manually."
                return 1
                ;;
        esac
    fi

    # Step 2: Verify Java version after installation
    log_info "Verifying JDK..."
    if java -version >/dev/null 2>&1; then
        local java_ver
        java_ver=$(java -version 2>&1 | head -1)
        log_info "JDK verified: ${java_ver}"
    else
        log_error "Failed to install JDK. Please install JDK manually before running mvn_analyse."
        return 1
    fi

    # Step 3: Download and install Maven
    log_info "Installing Maven ${MAVEN_VERSION}..."

    mkdir -p "${MAVEN_INSTALL_DIR}"

    if [ -f "${MAVEN_HOME}/bin/mvn" ]; then
        log_info "Maven ${MAVEN_VERSION} already extracted at ${MAVEN_HOME}, configuring environment..."
    else
        log_info "Downloading: ${MAVEN_URL}"
        local tmp_tar="/tmp/${MAVEN_TARBALL}"
        if command -v wget >/dev/null 2>&1; then
            wget -q -O "${tmp_tar}" "${MAVEN_URL}"
        elif command -v curl >/dev/null 2>&1; then
            curl -sSL -o "${tmp_tar}" "${MAVEN_URL}"
        else
            log_error "Neither wget nor curl is available. Cannot download Maven."
            return 1
        fi

        if [ ! -s "${tmp_tar}" ]; then
            log_error "Failed to download Maven from ${MAVEN_URL}"
            return 1
        fi
        log_info "Download complete: ${MAVEN_TARBALL}"

        tar -zxf "${tmp_tar}" -C "${MAVEN_INSTALL_DIR}"
        rm -f "${tmp_tar}"
        log_info "Maven extracted to ${MAVEN_HOME}"
    fi

    local profile_maven="# Maven ${MAVEN_VERSION} for DevKit mvn_analyse"
    if ! grep -q "MAVEN_HOME.*apache-maven-${MAVEN_VERSION}" /etc/profile 2>/dev/null; then
        echo "" >> /etc/profile
        echo "${profile_maven}" >> /etc/profile
        echo "export MAVEN_HOME=${MAVEN_HOME}" >> /etc/profile
        echo 'export PATH=$MAVEN_HOME/bin:$PATH' >> /etc/profile
        log_info "Environment variables added to /etc/profile"
    fi

    export MAVEN_HOME="${MAVEN_HOME}"
    export PATH="${MAVEN_HOME}/bin:${PATH}"
    log_info "Maven environment applied to current shell"

    set +u
    source /etc/profile 2>/dev/null || true
    set -u

    # Step 4: Verify Maven version after installation
    log_info "Verifying Maven installation..."
    local mvn_ver
    mvn_ver=$(mvn -v 2>&1 | head -1)
    log_info "Maven installed successfully: ${mvn_ver}"
}

# ---
# 6. Main Entry
# ---

main() {
    if [ "${CHECK_MAVEN_ONLY}" = "true" ]; then
        check_and_install_maven
        exit $?
    fi

    log_step "DevKit CLI Compress Installation (tar.gz)"
    check_os
    detect_arch
    install_deps
    download_package
    install_compress
    verify_install

    install_sshpass || log_error "sshpass installation failed."

    check_and_install_maven || log_error "Maven installation failed. mvn_analyse scan may not work."

    log_step "DevKit Installation Complete"
    log_info "DevKit version:    ${DEVKIT_VERSION}"
    log_info "Install mode:      compress (tar.gz)"
    log_info "Package:           ${DEVKIT_COMPRESS_PKG}"
    log_info "Install directory: ${DEVKIT_PKG_DIR}"
    log_info "Architecture:      $(uname -m)"
    log_info "OS:                $(detect_os)"
    log_info "Run '${DEVKIT_PKG_DIR}/devkit -h' or 'source /etc/profile && devkit -h' to see available commands."

}

main
