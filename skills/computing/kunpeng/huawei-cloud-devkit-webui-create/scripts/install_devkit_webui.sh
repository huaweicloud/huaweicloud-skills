#!/bin/bash
# Kunpeng DevKit WebUI Mode - One-Click Installation Script
# Usage: bash install_devkit_webui.sh <download_url> [install_path] [port]
#
# Examples:
#   Default:    bash install_devkit_webui.sh "https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz"
#   Custom path: bash install_devkit_webui.sh "<URL>" /data/devkit
#   Custom port: bash install_devkit_webui.sh "<URL>" /opt 9090
#
# Signature verification:
#   The script automatically downloads the .p7s digital signature from the same
#   OBS path as the package (package_url + ".p7s") and verifies the package
#   integrity using OpenSSL CMS/SMIME before extraction.
#   If signature verification fails, the script aborts to prevent tampered packages.

set -e

DEVKIT_URL="${1:?Usage: $0 <download_url> [install_path] [port]}"
CUSTOM_INSTALL_PATH="${2:-}"
CUSTOM_INSTALL_PORT="${3:-}"
DEVKIT_PKG=$(basename "${DEVKIT_URL}")
DEVKIT_DIR=$(echo "${DEVKIT_PKG}" | sed 's/.tar.gz$//')
WORK_DIR="/tmp/devkit_install_$$"
# Derive signature URL from package URL (same path + .p7s suffix)
DEVKIT_SIG_URL="${DEVKIT_URL}.p7s"

echo "=== [1/6] Environment Check ==="
ARCH=$(uname -m)
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
    echo "Error: Current architecture is ${ARCH}, DevKit only supports aarch64"
    exit 1
fi

SUPPORTED_OS=false
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    case "${ID}" in
        openeuler) [[ "${VERSION_ID}" == "24.03"* ]] && SUPPORTED_OS=true ;;
        centos) [[ "${VERSION_ID}" == "7"* ]] && SUPPORTED_OS=true ;;
        ubuntu) [[ "${VERSION_ID}" == "18.04"* ]] && SUPPORTED_OS=true ;;
        kylin) [[ "${VERSION_ID}" == "V10"* || "${VERSION_ID}" == "10"* ]] && SUPPORTED_OS=true ;;
        uos) [[ "${VERSION_ID}" == "20"* ]] && SUPPORTED_OS=true ;;
    esac
fi
if [[ "${SUPPORTED_OS}" != "true" ]]; then
    echo "Warning: Current OS is not compatibility-verified. Supported: openEuler 24.03 LTS / CentOS 7.6 / Ubuntu 18.04 / Kylin V10 / UOS 20"
fi

AVAILABLE_SPACE=$(df / | awk 'NR==2{print $4}')
if [[ ${AVAILABLE_SPACE} -lt 2097152 ]]; then
    echo "Error: Available disk space is less than 2GB"
    exit 1
fi

TOTAL_MEM=$(free | awk '/Mem:/{print $2}')
if [[ ${TOTAL_MEM} -lt 4000000 ]]; then
    echo "Warning: Memory is less than 4GB, installation may fail"
fi

echo "Architecture: ${ARCH} ✓"
echo "OS: ${PRETTY_NAME:-unknown} $([ "${SUPPORTED_OS}" == "true" ] && echo '✓' || echo '(unverified)')"
echo "Disk space: ${AVAILABLE_SPACE}KB ✓"
echo "Memory: ${TOTAL_MEM}KB"

echo ""
echo "=== [2/6] Install Dependencies ==="
if command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
elif command -v apt-get &>/dev/null; then
    PKG_MANAGER="apt-get"
else
    echo "Error: Neither yum nor apt-get package manager found"
    exit 1
fi
echo "Package manager: ${PKG_MANAGER}"

if [[ "${PKG_MANAGER}" == "yum" ]]; then
    echo "Refreshing yum cache..."
    yum makecache 2>&1 | tail -3
    echo "Installing framework dependencies..."
    yum install -y file which hostname procps iproute make acl gcc-c++ gcc glibc openssl sqlite wget lsof unzip gzip expect libcap rpm-build e2fsprogs crontabs pcre pcre-devel zlib zlib-devel openssl-devel 2>&1 | tail -5

    echo "Installing plugin dependencies..."
    yum install -y unzip make expect perf gcc-c++ gcc glibc openssl util-linux binutils dmidecode sysstat numactl sqlite perl logrotate curl zip libffi-devel pcre pcre-devel zlib zlib-devel libunwind openssl-devel graphviz psmisc strace pciutils lsscsi procps initscripts policycoreutils ethtool smartmontools kmod net-tools rsyslog gzip iputils traceroute tcpdump fio ipmitool man bc crontabs libaio-devel numactl-devel 2>&1 | tail -5
elif [[ "${PKG_MANAGER}" == "apt-get" ]]; then
    echo "Refreshing apt cache..."
    DEBIAN_FRONTEND=noninteractive apt-get update 2>&1 | tail -5
    echo "Installing framework dependencies..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y file hostname procps iproute2 make acl g++ gcc libc-bin openssl sqlite3 wget lsof unzip gzip expect libcap2-bin e2fsprogs cron libpcre3-dev libpcre3 zlib1g zlib1g-dev libssl-dev 2>&1 | tail -5

    echo "Installing plugin dependencies..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      unzip make expect gcc g++ build-essential \
      libc6-dev openssl util-linux binutils dmidecode sysstat numactl sqlite3 perl \
      logrotate curl zip libffi-dev pcregrep libpcre3-dev libpcre2-dev zlib1g-dev \
      libunwind-dev libssl-dev graphviz psmisc strace pciutils lsscsi procps \
      ethtool smartmontools kmod net-tools rsyslog gzip iputils-ping traceroute \
      tcpdump fio ipmitool man bc cron libaio-dev libnuma-dev \
      linux-tools-common linux-tools-generic linux-tools-$(uname -r) 2>&1 | tail -5
fi

echo "Dependencies installed ✓"

echo ""
echo "=== [3/6] Download Install Package ==="
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

if [[ -f "/tmp/${DEVKIT_PKG}" ]]; then
    echo "Found previously downloaded package, copying..."
    cp "/tmp/${DEVKIT_PKG}" "${WORK_DIR}/"
fi

wget -c "${DEVKIT_URL}" -O "${DEVKIT_PKG}" 2>&1 | tail -5
echo "Download complete ✓"

echo ""
echo "=== [3.5/6] Verify Digital Signature (.p7s) ==="
DEVKIT_SIG="${DEVKIT_PKG}.p7s"
wget -c "${DEVKIT_SIG_URL}" -O "${DEVKIT_SIG}" 2>&1 | tail -5
echo "Signature downloaded ✓"

# Verify PKCS#7 detached signature using OpenSSL
# -inform DER: .p7s files are DER-encoded
# -content: the file being signed
# -noverify: skip certificate chain validation (Huawei self-signed cert), still verifies signature-content binding
VERIFY_OK=false
if command -v openssl >/dev/null 2>&1; then
    if openssl cms -verify -inform DER -binary -in "${DEVKIT_SIG}" -content "${DEVKIT_PKG}" -noverify -out /dev/null >/dev/null 2>&1; then
        VERIFY_OK=true
    elif openssl smime -verify -inform DER -binary -in "${DEVKIT_SIG}" -content "${DEVKIT_PKG}" -noverify -out /dev/null >/dev/null 2>&1; then
        VERIFY_OK=true
    fi
fi

if [[ "${VERIFY_OK}" == "true" ]]; then
    echo "Digital signature verification PASSED ✓"
else
    echo "⚠️  Digital signature verification FAILED!"
    echo "The downloaded package may be corrupted or tampered with."
    echo "Package: ${DEVKIT_PKG}"
    echo "Signature: ${DEVKIT_SIG}"
    echo "Aborting installation for safety."
    exit 1
fi

echo ""
echo "=== [4/6] Extract Install Package ==="
mkdir -p DevKit-All
tar -xzf "${DEVKIT_PKG}" -C DevKit-All
echo "Extraction complete ✓"

echo ""
echo "=== [5/6] Execute Installation ==="
cd DevKit-All/${DEVKIT_DIR}

if ! command -v expect &>/dev/null; then
    echo "ERROR: 'expect' command not found. Installing expect..."
    if command -v yum &>/dev/null; then
        yum install -y expect 2>&1 | tail -3
    elif command -v apt-get &>/dev/null; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y expect 2>&1 | tail -3
    else
        echo "Error: Cannot install expect - no supported package manager"
        exit 1
    fi
    if ! command -v expect &>/dev/null; then
        echo "Error: Failed to install expect. Aborting."
        exit 1
    fi
    echo "expect installed successfully ✓"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXPECT_SCRIPT="${SCRIPT_DIR}/auto_install_devkit.expect"

if [[ ! -f "${EXPECT_SCRIPT}" ]]; then
    EXPECT_SCRIPT="/tmp/auto_install_devkit.expect"
    cat > "${EXPECT_SCRIPT}" << 'EXPECTEOF'
#!/usr/bin/expect -f
set timeout 600
set install_path ""
set install_port ""
if {$argc >= 1} { set install_path [lindex $argv 0] }
if {$argc >= 2} { set install_port [lindex $argv 1] }
spawn bash install.sh -a
expect {
    "access mode for your installation" { send "1\r"; exp_continue }
    "Do you want to authorize" { send "y\r"; exp_continue }
    "Do you want to set image sources" { send "y\r"; exp_continue }
    "Enter the installation path" {
        if {$install_path != ""} { send "$install_path\r" } else { send "\r" }
        exp_continue
    }
    "Please enter the installation port" {
        if {$install_port != ""} { send "$install_port\r" } else { send "\r" }
        exp_continue
    }
    "is available, do you want" { send "y\r"; exp_continue }
    "Do you want to continue" { send "y\r"; exp_continue }
    "Do you want to install the dependencies for assembly" { send "y\r"; exp_continue }
    "Enter the serial number of the plug-in" { send "1,2,3,4,5,6\r"; exp_continue }
    "select the number" { send "1\r"; exp_continue }
    "Enter the serial number" { send "1\r"; exp_continue }
    eof
}
EXPECTEOF
    chmod +x "${EXPECT_SCRIPT}"
fi

# Files retained for inspection: ${DEVKIT_DIR}

INSTALL_LOG="/tmp/devkit_install.log"
EXPECT_ARGS=""
if [[ -n "${CUSTOM_INSTALL_PATH}" ]]; then
    EXPECT_ARGS="${CUSTOM_INSTALL_PATH}"
fi
if [[ -n "${CUSTOM_INSTALL_PORT}" ]]; then
    EXPECT_ARGS="${EXPECT_ARGS} ${CUSTOM_INSTALL_PORT}"
fi

PID_FILE="/tmp/devkit_install.pid"
echo "Starting installation (guarded background process), log: ${INSTALL_LOG}"
if [[ -n "${EXPECT_ARGS}" ]]; then
    nohup ${EXPECT_SCRIPT} ${EXPECT_ARGS} > "${INSTALL_LOG}" 2>&1 &
else
    nohup ${EXPECT_SCRIPT} > "${INSTALL_LOG}" 2>&1 &
fi
INSTALL_PID=$!
echo "${INSTALL_PID}" > "${PID_FILE}"
echo "Install process PID: ${INSTALL_PID} (saved to ${PID_FILE})"
echo "  Monitor: tail -f ${INSTALL_LOG}"
echo "  Status:  kill -0 \$(cat ${PID_FILE}) 2>/dev/null && echo RUNNING || echo STOPPED"
echo "  Abort:   kill \$(cat ${PID_FILE})  then  rm -f ${PID_FILE}"

echo ""
echo "=== [6/6] Wait for Installation and Verify ==="
MAX_WAIT=600
WAITED=0
INTERVAL=10
while [[ ${WAITED} -lt ${MAX_WAIT} ]]; do
    if ! kill -0 ${INSTALL_PID} 2>/dev/null; then
        echo "Install process ended (waited ${WAITED}s)"
        break
    fi
    sleep ${INTERVAL}
    WAITED=$((WAITED + INTERVAL))
    echo "Installation in progress... waited ${WAITED}s"
done

if kill -0 ${INSTALL_PID} 2>/dev/null; then
    echo "Warning: Install process still running after ${MAX_WAIT}s timeout"
    echo "Monitor via log: tail -f ${INSTALL_LOG}"
    exit 1
fi

NGINX_STATUS=$(systemctl is-active devkit_nginx 2>/dev/null || echo "unknown")
FW_STATUS=$(systemctl is-active gunicorn_framework 2>/dev/null || echo "unknown")
PLUGIN_STATUS=$(systemctl is-active gunicorn_plugin 2>/dev/null || echo "unknown")

echo "devkit_nginx: ${NGINX_STATUS}"
echo "gunicorn_framework: ${FW_STATUS}"
echo "gunicorn_plugin: ${PLUGIN_STATUS}"

PORT_CHECK=$(ss -tlnp 2>/dev/null | grep -c ":8086 " || echo "0")
echo "Port 8086 listening: $([ "${PORT_CHECK}" -gt 0 ] && echo 'YES' || echo 'NO')"

if [[ "${NGINX_STATUS}" == "active" && "${FW_STATUS}" == "active" ]]; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo ""
    echo "========================================="
    echo "  Kunpeng DevKit installed successfully!"
    echo "  Access URL: https://${SERVER_IP}:8086"
    echo "========================================="
else
    echo ""
    echo "⚠️ Installation may not be fully successful, please check service status"
    echo "Install log: ${INSTALL_LOG}"
fi

# Files retained for inspection:
#   - Work dir: ${WORK_DIR}
#   - Expect script: /tmp/auto_install_devkit.expect
