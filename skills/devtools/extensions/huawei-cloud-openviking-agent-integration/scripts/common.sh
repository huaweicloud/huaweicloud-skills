#!/bin/bash
# =============================================================================
# Shared functions for OpenViking agent integration scripts.
# Source this file: source "$(dirname "$0")/common.sh"
# =============================================================================
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ── Logging ───────────────────────────────────────────────────────────────────
log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Authorization ─────────────────────────────────────────────────────────────
# Globals used: AUTO_YES
require_confirmation() {
  local action="$1" agent="$2" details="$3"
  if [[ "${AUTO_YES:-false}" == "true" ]]; then return 0; fi
  if [[ "${DRY_RUN:-false}" == "true" ]]; then return 0; fi
  local color="${4:-$YELLOW}"  # optional: use RED for unbind
  echo ""
  echo -e "${color}━━━ Authorization Required ━━━${NC}"
  echo "  Action:   $action"
  echo "  Agent:    $agent"
  echo "  Details:  $details"
  echo -e "${color}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  read -p "Type 'confirm' to proceed: " response
  if [[ "$response" != "confirm" ]]; then
    log_error "Authorization denied. Aborting."
    return 1
  fi
  return 0
}

# ── Dry run ───────────────────────────────────────────────────────────────────
# Globals used: DRY_RUN
dry_run_msg() {
  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    log_warn "[DRY-RUN] $*"
    return 0
  fi
  return 1
}

# ── Sandbox discovery ─────────────────────────────────────────────────────────
find_sandbox() {
  find /root/job-envs/sandboxes/ -maxdepth 1 -type d -name "${1}-*" 2>/dev/null | head -1
}

# ── Backup helper ─────────────────────────────────────────────────────────────
backup_file() {
  local f="$1"
  cp "$f" "${f}.bak.$(date +%s)"
}

# ── JSON MCP check ────────────────────────────────────────────────────────────
# Check if a JSON config file has openviking MCP enabled
# Usage: check_json_mcp <file> → exits 0 if enabled, 1 if not
check_json_mcp() {
  python3 -c "import json; cfg=json.load(open('$1')); exit(0 if cfg.get('mcp',{}).get('openviking',{}).get('enabled') else 1)" 2>/dev/null
}

# ── JSON MCP URL extraction ───────────────────────────────────────────────────
get_json_mcp_url() {
  python3 -c "import json; cfg=json.load(open('$1')); print(cfg.get('mcp',{}).get('openviking',{}).get('url',''))" 2>/dev/null
}

# ── Template injection marker ─────────────────────────────────────────────────
# All template-level injections use this marker for reliable sed-based removal
OV_MARKER="added by huawei-cloud-openviking-agent-integration skill"
OV_MARKER_LEGACY="added by openviking-agent-integration skill"

# Check if a template file has our injection (supports both current and legacy marker)
#
# Bug fix: The "MCP SDK install" comment line (Hermes-only, pip install mcp step)
# also contains OV_MARKER for sed-based removal. Without filtering, has_ov_injection
# returns true when only the pip install step exists — causing integrate.sh to skip
# the actual OpenViking MCP config block injection. We filter out "MCP SDK install"
# lines before checking so only real OV MCP injection blocks are detected.
has_ov_injection() {
  grep -v "MCP SDK install" "$1" 2>/dev/null | grep -q "$OV_MARKER\|$OV_MARKER_LEGACY"
}


# ── OpenViking health check ──────────────────────────────────────────────────
# Globals used: OV_ENDPOINT
check_ov_health() {
  local endpoint="${OV_ENDPOINT:-http://127.0.0.1:1933}"
  local resp
  resp=$(curl -sf "${endpoint}/health" 2>/dev/null) || {
    log_error "OpenViking server not reachable at $endpoint"
    return 1
  }
  local status
  status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
  if [[ "$status" == "ok" ]]; then
    log_ok "OpenViking server healthy at $endpoint"
    return 0
  else
    log_error "OpenViking server unhealthy: $resp"
    return 1
  fi
}
