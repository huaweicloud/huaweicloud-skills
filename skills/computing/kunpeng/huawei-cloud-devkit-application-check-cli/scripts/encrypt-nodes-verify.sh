#!/bin/bash
set -euo pipefail
# ---
# DevKit nodes.conf Password Encryption & SSH Verification Script
#
# Execution mode: manual (local script, runs on DevKit server).
# No hcloud CLI/SDK/API equivalent — this is a custom bash script for
# password encryption via sys-mig and SSH verification to target servers.
#
# Layer 2 script — runs ON the DevKit server (uploaded to ${DEVKIT_HOME}/).
# Uses the DevKit server's LOCAL ssh/sshpass to connect to target servers
# defined in nodes.conf. Does NOT use paramiko or any Python SSH library.
#
# Functional description and iterative verification flow:
#   See devkit-operations-workflow.md "Encrypt Passwords & Verify SSH Connectivity"
#
# Usage: bash encrypt-nodes-verify.sh [--nodes-conf <path>]
#        bash encrypt-nodes-verify.sh --mask [--nodes-conf <path>]
#        bash encrypt-nodes-verify.sh --check [--nodes-conf <path>]
#   If --nodes-conf is omitted, auto-detects from DevKit installation
#   --mask:  Output nodes.conf with all ssh_pass values masked as *** (safe for chat display)
#   --check: Only check if nodes.conf contains plaintext ssh_pass (no encryption, no SSH verification)
# ---

MASK_MODE="false"
CHECK_MODE="false"
NODES_CONF_ARG=""
SHOW_HELP="false"

usage() {
    echo "Usage: bash $0 [--nodes-conf <path>]"
    echo "       bash $0 --mask [--nodes-conf <path>]"
    echo "       bash $0 --check [--nodes-conf <path>]"
    echo "  If --nodes-conf is omitted, auto-detects from DevKit installation"
    echo "  --mask:  Output nodes.conf with all ssh_pass values masked as *** (safe for chat display)"
    echo "  --check: Only check if nodes.conf contains plaintext ssh_pass (no encryption, no SSH verification)"
}

parse_args() {
    # Map long options to single-letter options, then parse via getopts.
    local mapped=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --mask) mapped+=("-m"); shift ;;
            --check) mapped+=("-c"); shift ;;
            --nodes-conf)
                shift
                if [ $# -gt 0 ]; then mapped+=("-n" "$1"); shift; else echo "--nodes-conf requires a value" >&2; usage >&2; exit 1; fi
                ;;
            --nodes-conf=*) mapped+=("-n" "${1#--nodes-conf=}"); shift ;;
            --help|-h) mapped+=("-h"); shift ;;
            --) shift; break ;;
            *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
        esac
    done
    # ${mapped[@]+...} guard: safe for empty arrays under "set -u" on bash 4.2 (CentOS 7).
    set -- ${mapped[@]+"${mapped[@]}"}

    local opt
    while getopts ":mcn:h" opt; do
        case "${opt}" in
            m) MASK_MODE="true" ;;
            c) CHECK_MODE="true" ;;
            n) NODES_CONF_ARG="${OPTARG}" ;;
            h) SHOW_HELP="true" ;;
            \?) echo "Unknown argument: -${OPTARG}" >&2; usage >&2; exit 1 ;;
            :) echo "Option -${OPTARG} requires a value (e.g. --nodes-conf <path>)" >&2; usage >&2; exit 1 ;;
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
NODES_CONF=""
SYS_MIG_BIN=""
FAILED_LIST=""
SUCCESS_LIST=""
SUCCESS_COUNT=0
FAIL_COUNT=0
VERIFIED_HOSTS_FILE="/tmp/devkit_nodes_verified_hosts"

# ---
# 1. Logging Utilities
# ---

log_info()  { echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()  { echo "[WARN]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_step()  { echo ""; echo "----"; echo "  $*"; echo "===="; }

# ---
# 2. DevKit Installation Detection
# ---

detect_devkit_install() {
    local pkg_dir
    pkg_dir=$(find "${DEVKIT_DIR}" -maxdepth 1 -type d -name "DevKit-Sys-Mig-CLI-*" 2>/dev/null | head -1)
    if [ -z "${pkg_dir}" ]; then
        log_error "DevKit installation not found under ${DEVKIT_DIR}/"
        log_error "Please install DevKit first: bash ${DEVKIT_HOME}/install_devkit.sh"
        exit 1
    fi
    log_info "Found DevKit installation: ${pkg_dir}"

    SYS_MIG_BIN="${pkg_dir}/sys-mig/sys-mig"
    if [ ! -x "${SYS_MIG_BIN}" ]; then
        log_error "sys-mig binary not found or not executable: ${SYS_MIG_BIN}"
        exit 1
    fi
    log_info "sys-mig binary: ${SYS_MIG_BIN}"

    if [ -n "${NODES_CONF_ARG}" ]; then
        NODES_CONF="${NODES_CONF_ARG}"
    else
        NODES_CONF="${pkg_dir}/sys-mig/nodes/nodes.conf"
    fi

    if [ ! -f "${NODES_CONF}" ]; then
        log_error "nodes.conf not found: ${NODES_CONF}"
        log_error "Please configure the target server nodes file first."
        log_error "Template path: ${pkg_dir}/sys-mig/nodes/nodes.conf"
        exit 1
    fi
    log_info "nodes.conf: ${NODES_CONF}"
}

# ---
# 3. nodes.conf Parsing
# ---

# parse_nodes_conf: Outputs host entries as "ip|user|pass|port" via stdout.
# WARNING: stdout contains ssh_pass values — ONLY capture via command substitution,
# NEVER display directly in chat or AI thinking. All callers must use
# entries=$(parse_nodes_conf ...) to capture into a variable.
parse_nodes_conf() {
    local conf="$1"
    local filter_hosts="${2:-}"
    local current_group=""
    local current_section=""

    local re_vars='^\[([^]:]+):vars\]$'
    local re_group='^\[([^]:]+)\]$'
    local re_section='^\[.*\]$'
    local re_host='^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'

    declare -A group_user
    declare -A group_port
    declare -A group_pass

    # First pass: collect all group vars from [group:vars] sections
    # This handles the case where [group:vars] appears AFTER [group]
    while IFS= read -r line; do
        line=$(echo "${line}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "${line}" ] && continue
        [[ "${line}" == \#* ]] && continue

        if [[ "${line}" =~ $re_vars ]]; then
            current_group="${BASH_REMATCH[1]}"
            current_section="vars"
            continue
        elif [[ "${line}" =~ $re_group ]]; then
            current_group="${BASH_REMATCH[1]}"
            current_section="hosts"
            continue
        elif [[ "${line}" =~ $re_section ]]; then
            current_group=""
            current_section=""
            continue
        fi

        if [[ "${current_group}" != "" && "${current_section}" == "vars" ]]; then
            if [[ "${line}" =~ ^ssh_user= ]]; then
                group_user["${current_group}"]="${line#ssh_user=}"
            elif [[ "${line}" =~ ^ssh_port= ]]; then
                group_port["${current_group}"]="${line#ssh_port=}"
            elif [[ "${line}" =~ ^ssh_pass= ]]; then
                group_pass["${current_group}"]="${line#ssh_pass=}"
            fi
        fi
    done < "${conf}"

    # Second pass: parse host lines with group vars now available
    current_group=""
    current_section=""
    while IFS= read -r line; do
        line=$(echo "${line}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "${line}" ] && continue
        [[ "${line}" == \#* ]] && continue

        if [[ "${line}" =~ $re_vars ]]; then
            current_group="${BASH_REMATCH[1]}"
            current_section="vars"
            continue
        elif [[ "${line}" =~ $re_group ]]; then
            current_group="${BASH_REMATCH[1]}"
            current_section="hosts"
            continue
        elif [[ "${line}" =~ $re_section ]]; then
            current_group=""
            current_section=""
            continue
        fi

        if [[ "${line}" =~ $re_host ]]; then
            local host_line="${line}"
            local host_ip=$(echo "${host_line}" | awk '{print $1}')
            local ssh_user=""
            local ssh_pass=""
            local ssh_port="22"
            if [[ -n "${current_group}" ]]; then
                ssh_user="${group_user[${current_group}]:-}"
                ssh_pass="${group_pass[${current_group}]:-}"
                ssh_port="${group_port[${current_group}]:-22}"
            fi

            local rest="${host_line#* }"
            for kv in ${rest}; do
                case "${kv}" in
                    ssh_user=*) ssh_user="${kv#ssh_user=}" ;;
                    ssh_pass=*) ssh_pass="${kv#ssh_pass=}" ;;
                    ssh_port=*) ssh_port="${kv#ssh_port=}" ;;
                esac
            done

            if [ -n "${ssh_pass}" ] && [ -n "${ssh_user}" ]; then
                if [ -n "${filter_hosts}" ]; then
                    if echo "${filter_hosts}" | grep -q "|${host_ip}|"; then
                        echo "${host_ip}|${ssh_user}|${ssh_pass}|${ssh_port}"
                    fi
                else
                    echo "${host_ip}|${ssh_user}|${ssh_pass}|${ssh_port}"
                fi
            fi
        fi
    done < "${conf}"
}

# ---
# 4. Password Encryption Utilities
# ---

encrypt_password() {
    local plaintext="$1"
    local encrypted
    encrypted=$(echo "${plaintext}" | "${SYS_MIG_BIN}" -ec 2>/dev/null | grep -i -A1 "encrypted password" | tail -1 | sed 's/^[[:space:]]*//')
    if [ -z "${encrypted}" ]; then
        encrypted=$(printf '%s\n' "${plaintext}" | "${SYS_MIG_BIN}" -ec 2>&1 | grep -i -A1 "encrypted password" | tail -1 | sed 's/^[[:space:]]*//')
    fi
    if [ -z "${encrypted}" ]; then
        log_warn "Failed to encrypt password via sys-mig -ec, trying devkit wrapper..."
        encrypted=$(printf '%s\n' "${plaintext}" | devkit sys-mig -ec 2>&1 | grep -i -A1 "encrypted password" | tail -1 | sed 's/^[[:space:]]*//')
    fi
    echo "${encrypted}"
}

is_encrypted() {
    local val="$1"
    if echo "${val}" | grep -qP '^[A-Za-z0-9+/=]{20,}$'; then
        return 0
    fi
    return 1
}

# ---
# 5. Host Verification State Management
# ---

is_host_verified() {
    local host_ip="$1"
    if [ -f "${VERIFIED_HOSTS_FILE}" ] && grep -q "^${host_ip}$" "${VERIFIED_HOSTS_FILE}"; then
        return 0
    fi
    return 1
}

mark_host_verified() {
    local host_ip="$1"
    echo "${host_ip}" >> "${VERIFIED_HOSTS_FILE}"
}

build_failed_filter_from_file() {
    if [ -z "${FAILED_LIST}" ]; then
        echo ""
        return
    fi
    local filter=""
    local ip
    while IFS= read -r line; do
        ip=$(echo "${line}" | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
        if [ -n "${ip}" ]; then
            filter="${filter}|${ip}|"
        fi
    done <<< "${FAILED_LIST}"
    echo "${filter}"
}

# ---
# 6. SSH Verification
# ---

verify_ssh() {
    # Layer 2: DevKit server → target server (nodes.conf).
    # Uses the DevKit server's LOCAL ssh/sshpass/expect binaries.
    # NEVER use paramiko here — this script runs on the DevKit server, which
    # is the only host with network access to the target servers.
    local host_ip="$1"
    local ssh_user="$2"
    local ssh_pass="$3"
    local ssh_port="$4"
    local timeout=10

    if is_encrypted "${ssh_pass}"; then
        log_info "  ${host_ip}: password already encrypted — SSH was verified before encryption in a prior run, skipping."
        return 0
    fi

    if command -v sshpass >/dev/null 2>&1; then
        SSHPASS="${ssh_pass}" sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -o ConnectTimeout=${timeout} -p "${ssh_port}" "${ssh_user}@${host_ip}" "echo OK" 2>/dev/null
        return $?
    fi

    if command -v expect >/dev/null 2>&1; then
        expect -c "
set timeout ${timeout}
spawn ssh -o StrictHostKeyChecking=no -p ${ssh_port} ${ssh_user}@${host_ip} echo OK
expect {
    \"*assword*\" { send \"${ssh_pass}\r\"; exp_continue }
    \"OK\" { exit 0 }
    timeout { exit 1 }
}
" 2>/dev/null
        return $?
    fi

    log_warn "  ${host_ip}: No sshpass or expect available, skipping SSH verification."
    log_warn "  Install sshpass: yum install -y sshpass (CentOS) or apt install -y sshpass (Ubuntu)"
    return 2
}

verify_all_hosts() {
    local filter_hosts="${1:-}"
    local step_label="${2:-"[2/3] Verifying SSH Connectivity to Target Servers"}"
    log_step "${step_label}"

    local entries
    entries=$(parse_nodes_conf "${NODES_CONF}" "${filter_hosts}")

    if [ -z "${entries}" ]; then
        if [ -n "${filter_hosts}" ]; then
            log_info "No failed host entries to verify."
        else
            log_warn "No host entries found in nodes.conf"
        fi
        return
    fi

    FAILED_LIST=""
    SUCCESS_LIST=""
    SUCCESS_COUNT=0
    FAIL_COUNT=0

    while IFS='|' read -r host_ip ssh_user ssh_pass ssh_port; do
        [ -z "${host_ip}" ] && continue

        if [ -z "${filter_hosts}" ] && is_host_verified "${host_ip}"; then
            log_info "  ${host_ip}: already verified in previous run, skipping."
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            SUCCESS_LIST="${SUCCESS_LIST} ${host_ip}"
            continue
        fi

        log_info "  Testing SSH: ${ssh_user}@${host_ip}:${ssh_port} ..."

        local rc
        rc=0
        verify_ssh "${host_ip}" "${ssh_user}" "${ssh_pass}" "${ssh_port}" || rc=$?

        case ${rc} in
            0)
                log_info "  ${host_ip}: SSH connection SUCCESS."
                mark_host_verified "${host_ip}"
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
                SUCCESS_LIST="${SUCCESS_LIST} ${host_ip}"
                ;;
            2)
                log_warn "  ${host_ip}: SSH verification skipped (no tool available)."
                ;;
            *)
                local reason="Unknown"
                if [ ${rc} -eq 124 ] || [ ${rc} -eq 137 ]; then
                    reason="Connection timeout"
                elif [ ${rc} -eq 5 ]; then
                    reason="Authentication failed (wrong password/user)"
                elif [ ${rc} -eq 255 ]; then
                    reason="SSH connection refused or unreachable"
                else
                    reason="SSH failed (exit code: ${rc})"
                fi
                log_error "  ${host_ip}: SSH connection FAILED — ${reason}"
                FAILED_LIST="${FAILED_LIST}
  ${host_ip} (user=${ssh_user}, port=${ssh_port}): ${reason}"
                FAIL_COUNT=$((FAIL_COUNT + 1))
                ;;
        esac
    done <<< "${entries}"
}

# ---
# 7. nodes.conf Encryption
# ---

encrypt_nodes_conf() {
    local filter_hosts="${1:-}"
    local step_label="${2:-"[1/3] Encrypting Plaintext Passwords in nodes.conf"}"
    log_step "${step_label}"

    local entries
    entries=$(parse_nodes_conf "${NODES_CONF}" "${filter_hosts}")

    if [ -z "${entries}" ]; then
        if [ -n "${filter_hosts}" ]; then
            log_info "No failed host entries to process."
        else
            log_warn "No host entries with ssh_pass found in nodes.conf"
        fi
        return
    fi

    # Phase 1: Collect all plaintext→encrypted password mappings
    declare -A pass_map
    local encrypt_count=0
    local skip_count=0

    while IFS='|' read -r host_ip ssh_user ssh_pass ssh_port; do
        [ -z "${host_ip}" ] && continue

        if is_encrypted "${ssh_pass}"; then
            log_info "  ${host_ip}: password already encrypted, skipping."
            skip_count=$((skip_count + 1))
            continue
        fi

        log_info "  ${host_ip}: encrypting password for user '${ssh_user}'..."
        local encrypted
        encrypted=$(encrypt_password "${ssh_pass}")

        if [ -n "${encrypted}" ]; then
            pass_map["${ssh_pass}"]="${encrypted}"
            log_info "  ${host_ip}: password encrypted."
            encrypt_count=$((encrypt_count + 1))
        else
            log_error "  ${host_ip}: encryption failed! Password left as-is."
        fi
    done <<< "${entries}"

    # Phase 2: Single-pass replacement in nodes.conf
    if [ ${encrypt_count} -gt 0 ]; then
        if [ -z "${filter_hosts}" ]; then
            local backup="${NODES_CONF}.bak.$(date +%Y%m%d%H%M%S)"
            cp "${NODES_CONF}" "${backup}"
            log_info "Backup created: ${backup}"
        fi

        local tmp="${NODES_CONF}.tmp.$$"
        while IFS= read -r line; do
            if [[ "${line}" =~ ^[[:space:]]*ssh_pass= ]]; then
                local current_val="${line#*ssh_pass=}"
                current_val="${current_val%%[[:space:]]*}"
                if [ -n "${pass_map[${current_val}]+x}" ]; then
                    echo "ssh_pass=${pass_map[${current_val}]}"
                else
                    echo "${line}"
                fi
            else
                echo "${line}"
            fi
        done < "${NODES_CONF}" > "${tmp}"
        mv "${tmp}" "${NODES_CONF}"
        log_info "Replaced ${encrypt_count} plaintext password(s) in nodes.conf."
    fi

    log_info "Encryption complete: ${encrypt_count} encrypted, ${skip_count} already encrypted."
}

# ---
# 8. Reporting
# ---

report_results() {
    local round="${1:-1}"
    log_step "[3/3] SSH Verification Results (Round ${round})"

    local total=$((SUCCESS_COUNT + FAIL_COUNT))

    echo ""
    echo "  [---]"
    echo "  │  SSH Connectivity Verification Summary      │"
    echo "  [---]"
    echo "  │  Total:    ${total}"
    echo "  │  Success:  ${SUCCESS_COUNT}"
    echo "  │  Failed:   ${FAIL_COUNT}"
    echo "  [---]"
    echo ""

    if [ ${FAIL_COUNT} -gt 0 ]; then
        echo "  🔴 Failed connections:"
        echo "${FAILED_LIST}"
        echo ""
        echo "  Common reasons and solutions:"
        echo "    - Authentication failed:  Check ssh_user/ssh_pass in nodes.conf"
        echo "    - Connection refused:     Check target server SSH service is running"
        echo "    - Connection timeout:     Check network connectivity and firewall rules"
        echo "    - Host unreachable:       Check target server IP address"
        echo ""
        echo "  🔴 Security Group Configuration Reminder (Important):"
        echo "    If the error is Connection refused / Connection timeout / Host unreachable,"
        echo "    please add an inbound rule in the target server's security group:"
        echo "      - Protocol: TCP"
        echo "      - Port: 22 (SSH)"
        echo "      - Source: <DevKit server EIP> (i.e., this DevKit server's public IP)"
        echo "    Path: Huawei Cloud console → target server's security group → add inbound rule"
        echo ""
        echo "  ⚠️  Please fix the failed agent configurations in nodes.conf."
        echo "  After fixing, re-run this script:"
        echo "    bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --nodes-conf ${NODES_CONF}"
        echo ""
        echo "  Already-verified agents will be SKIPPED (no re-encryption/re-verification)."
        echo "  Only failed agents will be re-encrypted and re-verified."
        echo ""
        echo "  To start fresh (clear all verified records):"
        echo "    rm ${VERIFIED_HOSTS_FILE}"
        echo "    bash ${DEVKIT_HOME}/encrypt-nodes-verify.sh --nodes-conf ${NODES_CONF}"
    else
        echo "  ✅ All ${total} target servers are reachable."
        find "$(dirname "${VERIFIED_HOSTS_FILE}")" -name "$(basename "${VERIFIED_HOSTS_FILE}")" -delete 2>/dev/null || true
        echo ""
        echo "  Ready for scan. Run manually:"
        echo "    bash ${DEVKIT_HOME}/scan_devkit.sh stmt"
    fi
    echo ""
}

# ---
# 9. Mode Functions (--check, --mask)
# ---

check_nodes_conf() {
    log_step "[--check] Checking nodes.conf for Plaintext Passwords"
    detect_devkit_install
    if [ ! -f "${NODES_CONF}" ]; then
        log_error "nodes.conf not found: ${NODES_CONF}"
        exit 1
    fi
    log_info "Path: ${NODES_CONF}"

    local entries
    entries=$(parse_nodes_conf "${NODES_CONF}" "")

    if [ -z "${entries}" ]; then
        log_warn "No host entries with ssh_pass found in nodes.conf"
        echo "ALL_ENCRYPTED"
        return
    fi

    local plaintext_count=0
    local encrypted_count=0
    local total=0

    while IFS='|' read -r host_ip ssh_user ssh_pass ssh_port; do
        [ -z "${host_ip}" ] && continue
        total=$((total + 1))
        if is_encrypted "${ssh_pass}"; then
            encrypted_count=$((encrypted_count + 1))
        else
            plaintext_count=$((plaintext_count + 1))
            log_info "  ${host_ip}: PLAINTEXT password detected (not encrypted)"
        fi
    done <<< "${entries}"

    echo ""
    echo "  [---]"
    echo "  │  Password Encryption Check Summary           │"
    echo "  [---]"
    echo "  │  Total hosts:     ${total}"
    echo "  │  Encrypted:       ${encrypted_count}"
    echo "  │  Plaintext:       ${plaintext_count}"
    echo "  [---]"
    echo ""

    if [ "${plaintext_count}" -gt 0 ]; then
        echo "PLAINTEXT_FOUND: ${plaintext_count}"
        log_warn "Plaintext passwords found. Run encrypt-nodes-verify.sh (without --check) to encrypt before scanning."
    else
        echo "ALL_ENCRYPTED"
        log_info "All passwords are already encrypted. Safe to scan directly."
    fi
}

mask_nodes_conf() {
    log_step "[--mask] Displaying nodes.conf with Passwords Masked"
    detect_devkit_install
    if [ ! -f "${NODES_CONF}" ]; then
        log_error "nodes.conf not found: ${NODES_CONF}"
        exit 1
    fi
    log_info "Path: ${NODES_CONF}"
    log_info "All ssh_pass values are masked as *** (plaintext is NOT shown)."
    echo "----"
    sed -E 's/(ssh_pass=)[^[:space:]]+/\1***/g' "${NODES_CONF}"
    echo "----"
}

# ---
# 10. Main Entry
# ---

main() {
    log_step "DevKit nodes.conf Encryption & SSH Verification"
    detect_devkit_install

    local round=1
    local is_retry="false"

    if [ -f "${VERIFIED_HOSTS_FILE}" ] && [ -s "${VERIFIED_HOSTS_FILE}" ]; then
        local verified_count
        verified_count=$(wc -l < "${VERIFIED_HOSTS_FILE}")
        log_info "Found ${verified_count} previously verified hosts. This is a retry run."
        is_retry="true"
    fi

    if [ "${is_retry}" = "true" ]; then
        log_info "Skipping already-verified agents. Only processing failed agents."
        local failed_filter
        failed_filter=$(build_failed_filter_from_file)
        if [ -z "${failed_filter}" ]; then
            verify_all_hosts "" "[1/3] Verifying SSH Connectivity (full scan, plaintext passwords)"
            encrypt_nodes_conf "" "[2/3] Encrypting Plaintext Passwords (full scan)"
        else
            verify_all_hosts "" "[1/3] Verifying SSH Connectivity (failed agents + already verified skipped, plaintext passwords)"
            encrypt_nodes_conf "${failed_filter}" "[2/3] Encrypting Failed Agents Only"
        fi
    else
        find "$(dirname "${VERIFIED_HOSTS_FILE}")" -name "$(basename "${VERIFIED_HOSTS_FILE}")" -delete 2>/dev/null || true
        verify_all_hosts "" "[1/3] Verifying SSH Connectivity to Target Servers (plaintext passwords)"
        encrypt_nodes_conf "" "[2/3] Encrypting Plaintext Passwords in nodes.conf"
    fi

    report_results "${round}"
}

if [ "${MASK_MODE}" = "true" ]; then
    mask_nodes_conf
elif [ "${CHECK_MODE}" = "true" ]; then
    check_nodes_conf
else
    main
fi
