#!/bin/bash
# unbind.sh — OpenViking unbinding entry point
# Usage: ./unbind.sh --agent <name>|--all [--dry-run] [--yes]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/entrypoint.sh"
OV_MCP_URL="${OV_ENDPOINT}/mcp"
# Register agents early so usage()/error paths can list supported agents (ISSUE-006)
registry_init
registry_discover "$SCRIPT_DIR/agents"
DRY_RUN=false
AUTO_YES=false
AGENT=""
ALL_AGENTS=false
usage() {
  echo "Usage: $0 --agent <name>|--all [--dry-run] [--yes]"
  echo "Supported agents: $(ov_supported_agents 2>/dev/null || echo "(none)")"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)
      if [[ $# -lt 2 ]]; then log_error "--agent requires a value"; usage; exit 1; fi
      AGENT="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) AUTO_YES=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
done
if [[ "$ALL_AGENTS" == "true" && -n "$AGENT" ]]; then
  log_error "--agent and --all are mutually exclusive — specify exactly one"
  exit 1
fi
agents=()
if [[ "$ALL_AGENTS" == "true" ]]; then
  while IFS= read -r a; do agents+=("$a"); done < <(registry_list)
elif [[ -n "$AGENT" ]]; then
  # ISSUE-006: reject unknown agent names with the supported list up front
  ov_require_supported_agent "$AGENT" || exit 1
  agents=("$AGENT")
else
  log_error "Specify --agent <name> or --all"
  usage; exit 1
fi
# ISSUE-001: never "successfully" unbind against an unreachable server — state the
# health gate up front so a dead endpoint cannot produce false success reports.
# (Dry-run previews also need live state, so the gate applies to both modes.)
check_ov_health || exit 1
rc=0
for a in "${agents[@]}"; do
  display="${a//_/-}"
  log_info "Processing agent: $display"
  # ISSUE-004: capture the dispatch exit code explicitly — errexit is disabled
  # inside if-conditions, so `if dispatch; then` masked real failures
  ( registry_dispatch "$a" unbind ); dsp_rc=$?
  if [[ $dsp_rc -eq 0 ]]; then
    log_ok "Agent $display: unbinding complete"
  else
    log_error "Agent $display: unbinding failed"
    rc=1
  fi
done
if [[ $rc -ne 0 ]]; then
  log_warn "Some unbindings failed. Review output above."
fi
exit $rc