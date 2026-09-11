#!/bin/bash
# unbind.sh — OpenViking unbinding entry point
# Usage: ./unbind.sh --agent <name>|--all [--dry-run] [--yes]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/ui.sh"
source "$SCRIPT_DIR/lib/json.sh"
source "$SCRIPT_DIR/lib/plugins.sh"
source "$SCRIPT_DIR/lib/base.sh"
source "$SCRIPT_DIR/lib/registry.sh"
OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_MCP_URL="${OV_ENDPOINT}/mcp"
DRY_RUN=false
AUTO_YES=false
AGENT=""
ALL_AGENTS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) AUTO_YES=true; shift ;;
    --help|-h)
      echo "Usage: $0 --agent <name>|--all [--dry-run] [--yes]"
      echo "Agents: $(registry_discover "$SCRIPT_DIR/agents" >/dev/null 2>&1; registry_list | tr '\n' ',' | sed 's/,$//')"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done
registry_init
registry_discover "$SCRIPT_DIR/agents"
agents=()
if [[ "$ALL_AGENTS" == "true" ]]; then
  while IFS= read -r a; do agents+=("$a"); done < <(registry_list)
elif [[ -n "$AGENT" ]]; then
  agents=("$AGENT")
else
  log_error "Specify --agent <name> or --all"
  exit 1
fi
rc=0
for a in "${agents[@]}"; do
  display="${a//_/-}"
  log_info "Processing agent: $display"
  if registry_dispatch "$a" unbind; then
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
