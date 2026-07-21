#!/usr/bin/env bash
# config.sh — Centralized configuration for Huawei Cloud Skill Tester
# All hardcoded defaults are collected here. Override any value via environment variable.
set -uo pipefail

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
# Where skills are installed (Hermes runtime directory)
SKILL_PATH_HERMES="${SKILL_PATH_HERMES:-$HOME/.hermes/skills}"
# Where hcloud skills are stored
SKILL_PATH_HCLOUD="${SKILL_PATH_HCLOUD:-$SKILL_PATH_HERMES/huawei-cloud}"
# hcloud CLI config file path
HCLOUD_CONFIG="${HCLOUD_CONFIG:-$HOME/.hcloud/config.json}"

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

# ── Services supported by hcloud CLI ──
SERVICES_CLI=(ecs vpc evs eip ims as elb rds dns obs)

# ── Services with SDK support ──
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
)

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
