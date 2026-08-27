#!/usr/bin/env bash
# config.sh — Centralized configuration for Huawei Cloud Skill Tester
# All hardcoded defaults are collected here. Override any value via environment variable.
set -euo pipefail

# Standalone execution: parse args via getopts (no-op when sourced by other scripts)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  while getopts ":h" opt; do
    case $opt in
      h) echo "用法: source $(basename "$0")  # 作为库 source；直接执行仅打印配置"; exit 0 ;;
      \?) exit 1 ;;
    esac
  done
fi

# ── Region ──
# Default Huawei Cloud region for CLI/SDK operations
HUAWEI_REGION="${HUAWEI_REGION:-cn-north-4}"

# ── SDK defaults ──
# Default SDK API version (some services use v1, v3, etc.)
HUAWEI_SDK_VERSION="${HUAWEI_SDK_VERSION:-v2}"

# ── CLI ──
# Path to hcloud CLI executable
HCLOUD_CLI="${HCLOUD_CLI:-hcloud}"

# ── Paths ──
# Skill install directory — where the agent runtime stores installed skills.
# Resolution order (first non-empty wins):
#   1. $SKILL_INSTALL_DIR          (new canonical env var)
#   2. $SKILL_PATH_HERMES          (legacy env var, kept for back-compat)
#   3. $HOME/.agents/skills        (preferred new convention, if exists)
#   4. $HOME/.hermes/skills        (legacy convention, if exists)
#   5. $HOME/.agents/skills        (final default)
if [ -z "${SKILL_INSTALL_DIR:-}" ]; then
  if [ -n "${SKILL_PATH_HERMES:-}" ]; then
    SKILL_INSTALL_DIR="$SKILL_PATH_HERMES"
  elif [ -d "$HOME/.agents/skills" ]; then
    SKILL_INSTALL_DIR="$HOME/.agents/skills"
  elif [ -d "$HOME/.hermes/skills" ]; then
    SKILL_INSTALL_DIR="$HOME/.hermes/skills"
  else
    SKILL_INSTALL_DIR="$HOME/.agents/skills"
  fi
fi
# Backward-compat alias (older scripts that still read SKILL_PATH_HERMES)
SKILL_PATH_HERMES="$SKILL_INSTALL_DIR"
# Where huawei-cloud skills live (subdir of install dir by default)
SKILL_PATH_HCLOUD="${SKILL_PATH_HCLOUD:-$SKILL_INSTALL_DIR/huawei-cloud}"
# hcloud CLI config file path
HCLOUD_CONFIG="${HCLOUD_CONFIG:-$HOME/.hcloud/config.json}"

# ── Skill install command (Phase 0 install/uninstall for remote skills) ──
# Auto-detect agent runtime: hermes / npx / opencode.
# Override via SKILL_INSTALL_CMD env var. Set to "" to skip real installation.
# Note: ${VAR-default} (no colon) lets an empty string disable the command,
# distinct from the unset case which uses the default.
if [ -z "${SKILL_INSTALL_CMD:-}" ]; then
  if command -v hermes >/dev/null 2>&1; then
    SKILL_INSTALL_CMD="hermes skills"
  elif command -v npx >/dev/null 2>&1; then
    SKILL_INSTALL_CMD="npx skills"
  else
    SKILL_INSTALL_CMD=""
  fi
fi

# ── Timeouts (seconds) ──
TIMEOUT_CLI="${TIMEOUT_CLI:-30}"
TIMEOUT_SDK="${TIMEOUT_SDK:-60}"
TIMEOUT_RESEARCH="${TIMEOUT_RESEARCH:-10}"
TIMEOUT_FULL_FLOW_CLI="${TIMEOUT_FULL_FLOW_CLI:-30}"
TIMEOUT_FULL_FLOW_SDK="${TIMEOUT_FULL_FLOW_SDK:-60}"

# ── Phase topology ──
# Total number of pipeline phases (0-based: 0..PHASE_COUNT-1)
PHASE_COUNT=7
# Phase display names in order
declare -A PHASE_NAMES=(
  [0]="install-check"
  [1]="skill-analysis"
  [2]="tech-research"
  [3]="test-case-generation"
  [4]="test-execution"
  [5]="orchestration"
  [6]="full-flow"
)

# ── Output files ──
PHASE_FILE_PREFIX="phase"
PHASE_FILE_SUFFIX="-summary.json"
REPORT_DIR_DEFAULT="reports"
REPORT_JSON="test-report.json"
REPORT_MD="test-report.md"

# ═══════════════════════════════════════════════════════════════════
# Dynamic Service Discovery — hcloud CLI
#
# discover_hcloud_services(): Extracts all services from `hcloud --help`.
# Falls back to SERVICES_CLI_FALLBACK if hcloud is unavailable.
# Result is cached in HCLOUD_SERVICES_CACHE.
# ═══════════════════════════════════════════════════════════════════

# Fallback: comprehensive list of known hcloud CLI services
# Used when hcloud is unavailable or --help parsing fails
SERVICES_CLI_FALLBACK=(
    ecs vpc evs eip ims as elb rds dns obs
    iam nat cdn cce scm ces rfs ucs dcs kps
    bss cfw hss secmaster coc aom cts swr cci
    dds gaussdb ddm drs das dli dws mrs smn
    functiongraph apig vpn dc cc er eg
)

# Cached result
HCLOUD_SERVICES_CACHE=""

# ┌────────────────────────────────────────────────────────────────┐
# │  discover_hcloud_services                                        │
# │  Dynamically discovers all services from `hcloud --help`.       │
# │  Falls back to SERVICES_CLI_FALLBACK if hcloud unavailable.     │
# │  Returns space-separated list of service names.                 │
# └────────────────────────────────────────────────────────────────┘
discover_hcloud_services() {
    # Return cached result
    if [ -n "$HCLOUD_SERVICES_CACHE" ]; then
        echo "$HCLOUD_SERVICES_CACHE"
        return 0
    fi

    # Try to get service list from hcloud --help
    local help_output=""
    if command -v hcloud >/dev/null 2>&1; then
        help_output=$(hcloud --help 2>&1) || true
    fi

    local discovered=()

    if [ -n "$help_output" ]; then
        # Extract service names from "可用服务" or "Available services" section
        # Format: "  ecs   Elastic Cloud Server"
        # We look for lines that have a service code followed by description
        while IFS= read -r line; do
            # Skip if line contains "服务" (service) or "service" as header
            # Only capture actual service lines (typically 2-4 letter codes)
            if echo "$line" | grep -Eq '^\s+[a-z]{2,10}\s+'; then
                # Extract first word (service code)
                local svc
                svc=$(echo "$line" | awk '{gsub(/^[[:space:]]+/,""); print tolower($1)}')
                # Validate: should be 2-10 lowercase letters
                if echo "$svc" | grep -Eq '^[a-z]{2,10}$'; then
                    # Avoid duplicates
                    if [[ ! " ${discovered[*]} " =~ " ${svc} " ]]; then
                        discovered+=("$svc")
                    fi
                fi
            fi
        done <<< "$help_output"
    fi

    # Build output
    if [ ${#discovered[@]} -gt 0 ]; then
        local IFS=' '
        HCLOUD_SERVICES_CACHE="${discovered[*]}"
    else
        # hcloud unavailable → use fallback
        local IFS=' '
        HCLOUD_SERVICES_CACHE="${SERVICES_CLI_FALLBACK[*]}"
    fi

    echo "$HCLOUD_SERVICES_CACHE"
}

# Export comma-joined list for Python scripts
SERVICES_CLI_COMMA="$(
    IFS=','
    echo "${SERVICES_CLI_FALLBACK[*]}"
)"
export SERVICES_CLI_COMMA

# ┌────────────────────────────────────────────────────────────────┐
# │  get_cli_services_as_json                                       │
# │  Returns services list as JSON array string for Python.         │
# └────────────────────────────────────────────────────────────────┘
get_cli_services_as_json() {
    local services
    services=$(discover_hcloud_services)
    local escaped="${services// /\",\"}"
    echo "[\"$escaped\"]"
}

# ── Services (discovered at runtime from hcloud --help) ──
SERVICES_CLI=($(discover_hcloud_services))

# ── Services with SDK support (comprehensive 2025) ──
declare -A SERVICES_SDK=(
  [bss]=BssClient
  [ecs]=EcsClient
  [vpc]=VpcClient
  [evs]=EvsClient
  [eip]=EipClient
  [iam]=IamClient
  [rds]=RdsClient
  [dns]=DnsClient
  [obs]=ObsClient
  [nat]=NatClient
  [cdn]=CdnClient
  [cce]=CceClient
  [ces]=CesClient
  [dcs]=DcsClient
  [dds]=DdsClient
  [mrs]=MrsClient
  [dli]=DliClient
  [rfs]=RfsClient
  [apig]=ApigClient
  [functiongraph]=FunctionGraphClient
  [smn]=SmnClient
  [scm]=ScmClient
  [hss]=HssClient
  [cfw]=CfwClient
  [secmaster]=SecMasterClient
  [aom]=AomClient
  [cts]=CtsClient
  [swr]=SwrClient
  [cci]=CciClient
  [kps]=KpsClient
  [ucs]=UcsClient
  [gaussdb]=GaussDBClient
  [ddm]=DdmClient
  [drs]=DrsClient
  [das]=DasClient
  [dws]=DwsClient
  [vpn]=VpnClient
  [dc]=DcClient
  [cc]=CcClient
  [er]=ErClient
  [eg]=EgClient
  [as]=AsClient
  [elb]=ElbClient
  [ims]=ImsClient
  [coc]=CocClient
)

# Export SDK map as JSON for Python scripts
SERVICES_SDK_MAP_JSON="$(
    IFS=','
    items=()
    for svc in "${!SERVICES_SDK[@]}"; do
        items+=("\"$svc\":\"${SERVICES_SDK[$svc]}\"")
    done
    echo "{$(IFS=','; echo "${items[*]}")}"
)"
export SERVICES_SDK_MAP_JSON

# ── SDK version overrides per service (service=version, JSON format for Python) ──
SDK_VERSION_OVERRIDES='{"iam":"v3"}'

# ── CLI error keywords (JSON array, read by Python) ──
CLI_ERROR_PATTERNS='["[use_error]","[error]","use_error","error occurred"]'

# ── Parameter validation error keywords (JSON array) ──
PARAM_ERROR_KEYWORDS='["paramvalidation","parameter","invalidparam","valueerror","typeerror","field required","must be","cannot be none","cannot be empty","invalid value","out of range","limit","400","bad request"]'

# ── Auth error keywords (JSON array) ──
AUTH_ERROR_KEYWORDS='["unauthorized","401","403","forbidden","access denied","auth","credential","ak cannot be none","sk cannot be none"]'

# ── BSS detection keywords (skip CLI check) ──
BSS_KEYWORDS=(bss coupon voucher stored_value card order_coupon 代金券 优惠券 储值卡)

# ── Resource type detection keyword map ──
declare -A RESOURCE_PATTERNS=(
  [ecs]="ecs instance 云服务器 弹性云服务器"
  [vpc]="vpc 虚拟私有云"
  [eip]="eip 弹性公网"
  [evs]="evs clouddvolume 云硬盘"
  [bss_voucher]="voucher coupon 代金券 优惠券"
  [obs]="obs 存储桶 桶"
  [rds]="rds 数据库 mysql"
)

# ── SDK snippet builtin parameter defaults ──
# Used when generating executable Python snippets
SDK_PARAM_DEFAULTS='{"limit":10,"offset":0}'

# ── hcloud CLI profile mode for credential extraction ──
HCLOUD_PROFILE_MODE="${HCLOUD_PROFILE_MODE:-devcloud}"

# ── Skill dev search path (fallback when SKILL_PATH is unset) ──
SKILL_DEV_PATH="${SKILL_DEV_PATH:-./skills}"

# ── Output truncation lengths ──
OUTPUT_TRUNC_CLI=1000
OUTPUT_TRUNC_SDK=2000
OUTPUT_TRUNC_ERR=300
OUTPUT_TRUNC_ERR_DETAIL=200
OUTPUT_TRUNC_SDK_ERR=500
