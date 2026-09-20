#!/bin/bash
set -euo pipefail
# ---
# DevKit System Migration Scan Script
#
# Execution mode: manual (local script, runs on DevKit server).
# No hcloud CLI/SDK/API equivalent — this is a custom bash script for
# executing DevKit sys-mig scan commands and renaming reports.
#
# Layer 2 script — runs ON the DevKit server (uploaded to ${DEVKIT_HOME}/).
# Supports 4 scan modes: stmt, sbom, mvn_analyse, container_mig

# Usage: bash scan_devkit.sh --mode <mode>

# ---

SCAN_MODE=""
SHOW_HELP="false"

usage() {
    echo "DevKit System Migration Scan Script"
    echo ""
    echo "Usage: bash $0 --mode <mode>"
    echo ""
    echo "Scan Modes:"
    echo "  stmt          Statement info collection (CSV)"
    echo "  sbom          System component info collection (HTML/JSON)"
    echo "  mvn_analyse   Maven project source migration analysis (HTML, standalone only)"
    echo "  container_mig Container image migration (HTML/JSON, standalone only)"
    echo ""
    echo "Scan targets are read from nodes.conf."
}

parse_args() {
    # Map long options to single-letter options, then parse via getopts.
    local mapped=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --mode)
                shift
                if [ $# -gt 0 ]; then mapped+=("-m" "$1"); shift; else echo "--mode requires a value" >&2; usage >&2; exit 1; fi
                ;;
            --mode=*) mapped+=("-m" "${1#--mode=}"); shift ;;
            --help|-h) mapped+=("-h"); shift ;;
            --) shift; break ;;
            *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
        esac
    done
    # ${mapped[@]+...} guard: safe for empty arrays under "set -u" on bash 4.2 (CentOS 7).
    set -- ${mapped[@]+"${mapped[@]}"}

    local opt
    while getopts ":m:h" opt; do
        case "${opt}" in
            m) SCAN_MODE="${OPTARG}" ;;
            h) SHOW_HELP="true" ;;
            \?) echo "Unknown argument: -${OPTARG}" >&2; usage >&2; exit 1 ;;
            :) echo "Option -${OPTARG} requires a value (e.g. --mode <mode>)" >&2; usage >&2; exit 1 ;;
        esac
    done
}
parse_args "$@"
if [ "${SHOW_HELP}" = "true" ]; then
    usage
    exit 0
fi
DEVKIT_HOME="${DEVKIT_HOME:-/home}"
DEVKIT_PKG_DIR=""
NODES_CONF=""
REPORT_DIR="${DEVKIT_HOME}/report"

# ---
# 1. Logging & Output Utilities
# ---

log_info()  { echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_step()  { echo ""; echo "----"; echo "  $*"; echo "===="; }

print_separator() { echo "  ---"; }

# ---
# 1b. Interactive Mode Detection
# ---

INTERACTIVE=1
if [ ! -t 0 ]; then
    INTERACTIVE=0
fi

safe_read() {
    local prompt="$1"
    local var="$2"
    local default_val="${3:-}"
    if [ "${INTERACTIVE}" -eq 1 ]; then
        read -p "${prompt}" "${var}"
    else
        printf -v "${var}" '%s' "${default_val}"
        log_info "Non-interactive: ${prompt} -> '${default_val}'"
    fi
}

print_report_info() {
    local mode="$1"
    echo ""
    print_separator
    echo "  ${mode} scan complete"
    print_separator
    echo "  Report naming format: ${mode}_<target_server_IP>_<timestamp>"
    echo "  Report path: ${REPORT_DIR}/"
    print_separator
}

# ---
# 2. DevKit Environment Detection
# ---

detect_devkit_install() {
    DEVKIT_PKG_DIR=$(find "${DEVKIT_HOME}/DevKit" -maxdepth 1 -type d -name "DevKit-Sys-Mig-CLI-*" 2>/dev/null | head -1)
    if [ -z "${DEVKIT_PKG_DIR}" ]; then
        log_error "DevKit installation not found under ${DEVKIT_HOME}/DevKit/"
        exit 1
    fi
    log_info "DevKit installation: ${DEVKIT_PKG_DIR}"
}

check_devkit() {
    local devkit_bin="${DEVKIT_PKG_DIR}/devkit"
    if [ ! -x "${devkit_bin}" ]; then
        log_error "devkit binary not found or not executable: ${devkit_bin}"
        exit 1
    fi
    export PATH="${DEVKIT_PKG_DIR}:${PATH}"
    log_info "DevKit binary: ${devkit_bin}"
}

# ---
# 3. nodes.conf Configuration
# ---

detect_nodes_conf() {
    if [ -z "${DEVKIT_PKG_DIR}" ]; then
        return 1
    fi
    NODES_CONF="${DEVKIT_PKG_DIR}/sys-mig/nodes/nodes.conf"
    if [ ! -f "${NODES_CONF}" ]; then
        NODES_CONF=""
        return 1
    fi
    return 0
}

list_nodes_targets() {
    if [ -z "${NODES_CONF}" ]; then
        return
    fi
    log_info "Target servers from nodes.conf:"
    grep -oP '^\d+\.\d+\.\d+\.\d+' "${NODES_CONF}" 2>/dev/null | while read -r ip; do
        log_info "  - ${ip}"
    done
}

prompt_nodes_conf() {
    local nodes_conf_path="${NODES_CONF}"
    if [ -z "${nodes_conf_path}" ] || [ ! -f "${nodes_conf_path}" ]; then
        nodes_conf_path="${DEVKIT_PKG_DIR}/sys-mig/nodes/nodes.conf"
    fi
    echo "  nodes.conf file path: ${nodes_conf_path}"
    echo "  Configuration format example:"
    echo "    [group1]"
    echo "    <target_server_IP>  ssh_pass=<password>  scan_dir=/home"
    echo "    [group1:vars]"
    echo "    ssh_user=root"
    echo "    ssh_port=22"
    safe_read "  Press Enter to continue after configuration, or enter q to quit: " confirm ""
    if [ "${confirm}" = "q" ] || [ "${confirm}" = "Q" ]; then
        log_info "User cancelled scan."
        return 1
    fi
    return 0
}

check_target_ips() {
    local nodes_conf_path="$1"
    local target_ips
    target_ips=$(grep -oP '^\d+\.\d+\.\d+\.\d+' "${nodes_conf_path}" 2>/dev/null || true)
    if [ -z "${target_ips}" ]; then
        log_error "No remote target server node info found in nodes.conf."
        prompt_nodes_conf || return 1
        target_ips=$(grep -oP '^\d+\.\d+\.\d+\.\d+' "${nodes_conf_path}" 2>/dev/null || true)
        if [ -z "${target_ips}" ]; then
            log_error "Still no target server node info in nodes.conf, cannot execute remote scan."
            return 1
        fi
    fi
    log_info "Found remote target servers:"
    echo "${target_ips}" | while read -r ip; do
        log_info "  - ${ip}"
    done
    return 0
}

# ---
# 4. Encryption & SSH Verification
# ---

encrypt_and_verify() {
    local encrypt_script="${DEVKIT_HOME}/encrypt-nodes-verify.sh"
    if [ ! -f "${encrypt_script}" ]; then
        log_info "encrypt-nodes-verify.sh not found, skipping encryption."
        return 0
    fi

    log_info "Checking ssh_pass encryption status..."
    local check_output
    check_output=$(bash "${encrypt_script}" --check 2>&1) || true
    echo "${check_output}"

    if echo "${check_output}" | grep -q "PLAINTEXT_FOUND"; then
        log_info "Plaintext passwords detected, executing encryption replacement and SSH verification..."
        local encrypt_output
        encrypt_output=$(echo "n" | bash "${encrypt_script}" 2>&1) || true
        echo "${encrypt_output}"
    else
        log_info "All passwords encrypted, verifying SSH connectivity..."
        local verify_output
        verify_output=$(echo "n" | bash "${encrypt_script}" 2>&1) || true
        echo "${verify_output}"
    fi
}

# ---
# 5. Remote Scan Preparation & Execution
# ---

prepare_remote_scan() {
    log_info "Please configure target server node info in nodes.conf..."
    prompt_nodes_conf || return 1

    log_info "Reading nodes.conf and checking remote target server node info..."
    detect_nodes_conf
    if [ -z "${NODES_CONF}" ]; then
        log_error "nodes.conf file not found, cannot execute remote scan."
        return 1
    fi

    check_target_ips "${NODES_CONF}" || return 1
    encrypt_and_verify

    mkdir -p "${REPORT_DIR}"
    return 0
}

run_remote_scan() {
    local mode="$1"
    local cmd="devkit sys-mig -c ${mode} -mn all -o ${REPORT_DIR} -l 1"
    log_info "Executing remote scan: ${cmd}"
    devkit sys-mig -c "${mode}" -mn all -o "${REPORT_DIR}" -l 1 || { log_error "${mode} scan failed."; return 1; }
    log_info "${mode} scan complete."
    print_report_info "${mode}"
}

# ---
# 6. Scan Mode Selection
# ---

select_scan_mode() {
    if [ -n "${SCAN_MODE}" ]; then
        case "${SCAN_MODE}" in
            stmt|sbom|mvn_analyse|container_mig)
                log_info "Scan mode (from argument): ${SCAN_MODE}"
                ;;
            *) log_error "Invalid scan mode: ${SCAN_MODE}. Use: stmt|sbom|mvn_analyse|container_mig"; exit 1 ;;
        esac
        return
    fi

    echo ""
    echo "  Please select DevKit system migration scan mode:"
    echo "    1) stmt         - Statement info collection (CSV report)"
    echo "    2) sbom         - System component info collection (HTML/JSON report)"
    echo "    3) mvn_analyse  - Maven project source migration analysis (HTML, standalone only)"
    echo "    4) container_mig- Container image migration (HTML/JSON, standalone only)"
    echo ""
    safe_read "  Enter choice [1-4] (no default, must enter explicitly): " choice ""
    case "${choice}" in
        1) SCAN_MODE="stmt" ;;
        2) SCAN_MODE="sbom" ;;
        3) SCAN_MODE="mvn_analyse" ;;
        4) SCAN_MODE="container_mig" ;;
        *) log_error "Invalid input '${choice}'. No default. Please enter 1-4."; exit 1 ;;
    esac
    log_info "Selected scan mode: ${SCAN_MODE}"
}

# ---
# 7. Scan Mode Implementations
# ---

scan_stmt() {
    log_step "Scanning: Statement Info Collection (stmt)"
    echo ""
    print_separator
    echo "  stmt scan mode selection"
    print_separator
    echo "    1) Default scan — remote scan of all servers in nodes.conf"
    echo "    2) Command-line scan — local scan"
    echo ""

    safe_read "  Select [1-2] (no default, must enter explicitly): " choice "1"

    case "${choice}" in
        1)
            log_info "Selected default scan (remote scan)"
            prepare_remote_scan || return 1
            run_remote_scan stmt
            ;;
        2)
            safe_read "  Scan file directory (-d, multiple dirs separated by space): " scan_path ""
            safe_read "  Source directory (-src, multiple dirs separated by space): " src_path ""
            safe_read "  Report output directory (-o): " report_dir "${REPORT_DIR}"
            safe_read "  Log level (-l): " log_level "1"
            mkdir -p "${report_dir}"
            local cmd="devkit sys-mig -c stmt -d ${scan_path} -src ${src_path} -o ${report_dir} -l ${log_level}"
            echo ""
            print_separator
            echo "  Command to execute:"
            echo "    ${cmd}"
            print_separator
            safe_read "  Confirm execution? (y/n, no default): " confirm "y"
            if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
                log_info "Scan cancelled."
                return 1
            fi
            devkit sys-mig -c stmt -d "${scan_path}" -src "${src_path}" -o "${report_dir}" -l "${log_level}" || { log_error "stmt scan failed."; return 1; }
            log_info "stmt scan complete."
            print_report_info stmt
            ;;
        *)
            log_error "Invalid input '${choice}', no default. Please enter 1 or 2."; exit 1
            ;;
    esac
}

scan_sbom() {
    log_step "Scanning: System Component Info Collection (sbom)"
    echo ""
    print_separator
    echo "  sbom scan mode selection"
    print_separator
    echo "    1) Default scan — remote scan of all servers in nodes.conf"
    echo "    2) Command-line scan — local scan"
    echo ""

    safe_read "  Select [1-2] (no default, must enter explicitly): " choice "1"

    case "${choice}" in
        1)
            log_info "Selected default scan (remote scan)"
            prepare_remote_scan || return 1
            run_remote_scan sbom
            ;;
        2)
            safe_read "  Scan file directory (-d, multiple dirs separated by space): " scan_path ""
            safe_read "  Report output directory (-o): " report_dir "${REPORT_DIR}"
            safe_read "  Log level (-l): " log_level "1"
            mkdir -p "${report_dir}"
            local cmd="devkit sys-mig -c sbom -d ${scan_path} -o ${report_dir} -l ${log_level}"
            echo ""
            print_separator
            echo "  Command to execute:"
            echo "    ${cmd}"
            print_separator
            safe_read "  Confirm execution? (y/n, no default): " confirm "y"
            if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
                log_info "Scan cancelled."
                return 1
            fi
            devkit sys-mig -c sbom -d "${scan_path}" -o "${report_dir}" -l "${log_level}" || { log_error "sbom scan failed."; return 1; }
            log_info "sbom scan complete."
            print_report_info sbom
            ;;
        *)
            log_error "Invalid input '${choice}', no default. Please enter 1 or 2."; exit 1
            ;;
    esac
}

scan_mvn_analyse() {
    log_step "Scanning: Maven Project Source Migration Analysis (mvn_analyse)"
    log_info "WARNING: mvn_analyse is a LOCAL scan, not a remote scan."

    log_info "Checking Maven installation (mvn -v)..."
    if ! mvn -v >/dev/null 2>&1; then
        log_info "Maven is not installed. Installing via install_devkit.sh --check-maven..."
        if ! bash "${DEVKIT_HOME}/install_devkit.sh" --check-maven; then
            log_error "Maven installation failed. Skipping mvn_analyse scan."
            return 1
        fi
        set +u
        source /etc/profile 2>/dev/null || true
        set -u
        if ! mvn -v >/dev/null 2>&1; then
            log_error "Maven verification failed. Skipping mvn_analyse scan."
            return 1
        fi
    fi
    local mvn_ver
    mvn_ver=$(mvn -v 2>&1 | head -1)
    log_info "Maven ready: ${mvn_ver}"

    mkdir -p "${REPORT_DIR}"
    echo ""
    print_separator
    echo "  mvn_analyse scan mode selection"
    print_separator
    echo "    1) Command-line scan — local scan"
    echo ""

    safe_read "  Select [1] (no default, must enter explicitly): " choice "1"

    safe_read "  pom.xml scan file directory (-d): " scan_path ""
    safe_read "  Report output directory (-o): " report_dir "${REPORT_DIR}"
    safe_read "  Log level (-l): " log_level "1"

    mkdir -p "${report_dir}"
    local cmd="devkit sys-mig -c mvn_analyse -d ${scan_path} -o ${report_dir} -l ${log_level}"
    echo ""
    print_separator
    echo "  Command to execute:"
    echo "    ${cmd}"
    print_separator
    safe_read "  Confirm execution? (y/n, no default): " confirm "y"
    if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
        log_info "Scan cancelled."
        return 1
    fi
    devkit sys-mig -c mvn_analyse -d "${scan_path}" -o "${report_dir}" -l "${log_level}" || { log_error "mvn_analyse scan failed."; return 1; }
    log_info "mvn_analyse scan complete."
    print_report_info mvn_analyse

}

scan_container_mig() {
    log_step "Scanning: Container Image Migration (container_mig)"
    log_info "WARNING: container_mig is a LOCAL scan, not a remote scan."

    echo ""
    print_separator
    echo "  container_mig scan mode selection"
    print_separator
    echo "    1) Command-line scan — local scan"
    echo ""

    safe_read "  Select [1] (no default, must enter explicitly): " choice "1"

    safe_read "  Image package path (--image, required): " image_path ""
    safe_read "  Dockerfile path (--dockerfile, optional): " dockerfile_path ""
    safe_read "  Report output directory (-o): " report_dir "${REPORT_DIR}"
    safe_read "  Log level (-l): " log_level "1"

    if [ -z "${image_path}" ]; then
        log_error "--image is a required parameter and cannot be empty."
        return 1
    fi

    mkdir -p "${report_dir}"
    local cmd="devkit sys-mig -c container_mig --image ${image_path}"
    if [ -n "${dockerfile_path}" ]; then
        cmd="${cmd} --dockerfile ${dockerfile_path}"
    fi
    cmd="${cmd} -o ${report_dir} -l ${log_level}"
    echo ""
    print_separator
    echo "  Command to execute:"
    echo "    ${cmd}"
    print_separator
    safe_read "  Confirm execution? (y/n, no default): " confirm "y"
    if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
        log_info "Scan cancelled."
        return 1
    fi
    if [ -n "${dockerfile_path}" ]; then
        devkit sys-mig -c container_mig --image "${image_path}" --dockerfile "${dockerfile_path}" -o "${report_dir}" -l "${log_level}" || { log_error "container_mig scan failed."; return 1; }
    else
        devkit sys-mig -c container_mig --image "${image_path}" -o "${report_dir}" -l "${log_level}" || { log_error "container_mig scan failed."; return 1; }
    fi
    log_info "container_mig scan complete."
    print_report_info container_mig

}


# ---
# 8. Report Processing
# ---

detect_scan_mode_from_report() {
    local dir="$1"
    if [ -f "${dir}/stmt.csv" ] || [ -f "${dir}/stmt_en.csv" ]; then
        echo "stmt"
    elif [ -f "${dir}/sbom.html" ] || [ -f "${dir}/sbom.json" ]; then
        echo "sbom"
    elif find "${dir}" -maxdepth 1 -name "mvn_analyse*" -type f 2>/dev/null | grep -q .; then
        echo "mvn_analyse"
    elif find "${dir}" -maxdepth 1 -name "container_mig*" -type f 2>/dev/null | grep -q .; then
        echo "container_mig"
    else
        local basename
        basename=$(basename "${dir}")
        if echo "${basename}" | grep -qi "merged"; then
            echo "sbom"
        else
            echo "stmt"
        fi
    fi
}

rename_reports_to_eip() {
    if [ -z "${NODES_CONF}" ]; then
        return
    fi

    log_step "Renaming Reports to <scan_mode>_<nodes_IP>_<timestamp> Format"

    local target_eips
    target_eips=$(grep -oP '^\d+\.\d+\.\d+\.\d+' "${NODES_CONF}" 2>/dev/null | sort -u)

    if [ -z "${target_eips}" ]; then
        log_info "No target IPs found in nodes.conf, skipping rename."
        return
    fi

    local renamed=0

    local dirs
    dirs=$(find "${REPORT_DIR}" -maxdepth 1 -type d -name "sys-mig_*" 2>/dev/null)
    for dir in ${dirs}; do
        local dirname
        dirname=$(basename "${dir}")
        local old_ip
        old_ip=$(echo "${dirname}" | grep -oP 'sys-mig_(\d+\.\d+\.\d+\.\d+)' | sed 's/sys-mig_//')
        if [ -n "${old_ip}" ]; then
            local timestamp
            timestamp=$(echo "${dirname}" | grep -oP '\d{14}' | tail -1)
            local scan_mode
            scan_mode=$(detect_scan_mode_from_report "${dir}")
            local new_dirname="${scan_mode}_${old_ip}_${timestamp}"
            local new_path="${REPORT_DIR}/${new_dirname}"
            if [ ! -e "${new_path}" ]; then
                mv "${dir}" "${new_path}"
                log_info "Renamed: ${dirname} -> ${new_dirname}"
                renamed=$((renamed + 1))
            else
                log_info "Target already exists: ${new_dirname}, merging contents"
                cp -rn "${dir}"/* "${new_path}/" 2>/dev/null || true
                rm -rf "${dir}"
                renamed=$((renamed + 1))
            fi
        fi
    done

    local zips
    zips=$(find "${REPORT_DIR}" -maxdepth 1 -type f -name "sys-mig_*.zip" 2>/dev/null)
    for zip in ${zips}; do
        local zipname
        zipname=$(basename "${zip}")
        local old_ip
        old_ip=$(echo "${zipname}" | grep -oP 'sys-mig_(\d+\.\d+\.\d+\.\d+)' | sed 's/sys-mig_//')
        if [ -n "${old_ip}" ]; then
            local timestamp
            timestamp=$(echo "${zipname}" | grep -oP '\d{14}' | tail -1)
            local scan_mode
            if echo "${zipname}" | grep -qi "merged"; then
                scan_mode="sbom"
            else
                local matched_dir
                matched_dir=$(find "${REPORT_DIR}" -maxdepth 1 -type d -name "*_${old_ip}_${timestamp}" 2>/dev/null | head -1)
                if [ -n "${matched_dir}" ]; then
                    scan_mode=$(echo "$(basename "${matched_dir}")" | grep -oP '^[a-z_]+(?=_)')
                else
                    scan_mode="stmt"
                fi
            fi
            local new_zipname="${scan_mode}_${old_ip}_${timestamp}.zip"
            local new_zippath="${REPORT_DIR}/${new_zipname}"
            if [ ! -e "${new_zippath}" ]; then
                mv "${zip}" "${new_zippath}"
                log_info "Renamed: ${zipname} -> ${new_zipname}"
                renamed=$((renamed + 1))
            fi
        fi
    done

    if [ ${renamed} -gt 0 ]; then
        log_info "Renamed ${renamed} report directories."
    else
        log_info "All reports already use correct naming."
    fi
}

list_reports() {
    log_step "Generated Reports"
    if [ -d "${REPORT_DIR}" ]; then
        find "${REPORT_DIR}" -type f \( -name "*.csv" -o -name "*.html" -o -name "*.json" -o -name "*.zip" \) 2>/dev/null | sort
    else
        log_info "Report directory not found: ${REPORT_DIR}"
    fi
}

# ---
# 9. Usage & Entry Point
# ---


main() {
    if [ "${SCAN_MODE}" = "help" ] || [ "${SCAN_MODE}" = "-h" ] || [ "${SCAN_MODE}" = "--help" ]; then
        usage
        exit 0
    fi

    log_step "DevKit System Migration Scan"

    detect_devkit_install
    check_devkit
    detect_nodes_conf

    if [ -n "${NODES_CONF}" ]; then
        log_info "nodes.conf found — scan targets: remote servers defined in nodes.conf"
        list_nodes_targets
    else
        log_info "No nodes.conf found — proceeding with scan"
    fi

    select_scan_mode

    case "${SCAN_MODE}" in

        stmt)          scan_stmt || log_error "stmt scan failed." ;;
        sbom)          scan_sbom || log_error "sbom scan failed." ;;
        mvn_analyse)   scan_mvn_analyse || log_error "mvn_analyse scan failed." ;;
        container_mig) scan_container_mig || log_error "container_mig scan failed." ;;
        *)             log_error "Unknown scan mode: ${SCAN_MODE}"; exit 1 ;;
    esac

    rename_reports_to_eip || true
    list_reports || true
}

main
