#!/bin/bash
# =============================================================================
# lib/ui.sh — UI services: logging, authorization, dry-run, i18n
# Part of the OO refactoring. Sourced by lib/base.sh and entry points.
# =============================================================================
# NOTE: set -euo pipefail is set by the entry point, not here.

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ── Logging ───────────────────────────────────────────────────────────────────
log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Authorization ─────────────────────────────────────────────────────────────
# Globals used: AUTO_YES, DRY_RUN
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

# ── i18n: detect language ─────────────────────────────────────────────────────
# Returns "zh" for Chinese, "en" for English.
# Detection order: OV_LANG env var > LANG/LC_ALL/LANGUAGE env vars > default "zh"
ov_detect_lang() {
  if [[ -n "${OV_LANG:-}" ]]; then
    echo "${OV_LANG}"
    return
  fi
  for var in LANG LC_ALL LANGUAGE; do
    val="${!var:-}"
    if [[ "$val" == zh* ]]; then
      echo "zh"
      return
    fi
  done
  echo "zh"
}
