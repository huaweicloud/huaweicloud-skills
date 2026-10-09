#!/bin/bash
# integrate.sh — OpenViking integration entry point
# Usage: ./integrate.sh --agent <name>|--all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/entrypoint.sh"
export OV_API_KEY="${OV_API_KEY:-}"
# Register agents early so usage()/error paths can list supported agents (ISSUE-006)
registry_init
registry_discover "$SCRIPT_DIR/agents"
OV_MCP_URL="${OV_ENDPOINT}/mcp"
DRY_RUN=false
AUTO_YES=false
AGENT=""
ALL_AGENTS=false
usage() {
  echo "Usage: $0 --agent <name>|--all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]"
  echo "Supported agents: $(ov_supported_agents 2>/dev/null || echo "(none)")"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)
      if [[ $# -lt 2 ]]; then log_error "--agent requires a value"; usage; exit 1; fi
      AGENT="$2"; shift 2 ;;
    --api-key)
      if [[ $# -lt 2 ]]; then log_error "--api-key requires a value"; usage; exit 1; fi
      OV_API_KEY="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --endpoint)
      if [[ $# -lt 2 ]]; then log_error "--endpoint requires a value"; usage; exit 1; fi
      OV_ENDPOINT="$2"; OV_MCP_URL="${OV_ENDPOINT}/mcp"; shift 2 ;;
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
check_ov_health || exit 1
rc=0
for a in "${agents[@]}"; do
  display="${a//_/-}"
  log_info "Processing agent: $display"
  # ISSUE-007: fail loudly instead of silently "completing" when the sandbox is missing
  agent::clear_meta
  reg_fn="agent_${a}_register"
  declare -f "$reg_fn" &>/dev/null && "$reg_fn"
  if [[ "$DRY_RUN" != "true" ]] && [[ -n "${AGENT_META[sandbox_pattern]:-}" ]] && ! ov_require_agent_sandbox; then
    log_error "Agent $display: integration aborted (sandbox missing)"
    rc=1
    continue
  fi
  # ISSUE-004: capture the dispatch exit code explicitly — errexit is disabled
  # inside if-conditions, so `if dispatch; then` masked real failures
  ( registry_dispatch "$a" integrate ); dsp_rc=$?
  if [[ $dsp_rc -eq 0 ]]; then
    log_ok "Agent $display: integration complete"
  else
    log_error "Agent $display: integration failed"
    rc=1
  fi
done
# ISSUE-003: fail loudly when --api-key was requested but never consumed
if [[ -n "$OV_API_KEY" ]] && ! ov_api_key_was_consumed; then
  log_warn "--api-key provided but never consumed by any agent configuration — authentication may fail at runtime"
fi
if [[ $rc -ne 0 ]]; then
  log_warn "Some integrations failed or were skipped. Review output above."
fi
exit $rc