#!/bin/bash
# =============================================================================
# integrate.sh — OpenViking integration entry point (thin)
# =============================================================================
# OO architecture: sources lib/ framework, discovers agent subclasses from
# agents/, dispatches to agent_<name>_integrate via the registry.
#
# Usage: ./integrate.sh --agent <name>|--all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Load OO framework ────────────────────────────────────────────────────────
source "$SCRIPT_DIR/lib/ui.sh"
source "$SCRIPT_DIR/lib/json.sh"
source "$SCRIPT_DIR/lib/plugins.sh"
source "$SCRIPT_DIR/lib/base.sh"
source "$SCRIPT_DIR/lib/registry.sh"

# ── Defaults ─────────────────────────────────────────────────────────────────
OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_API_KEY="${OV_API_KEY:-}"
OV_MCP_URL="${OV_ENDPOINT}/mcp"
DRY_RUN=false
AUTO_YES=false
AGENT=""
ALL_AGENTS=false

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --endpoint) OV_ENDPOINT="$2"; OV_MCP_URL="${OV_ENDPOINT}/mcp"; shift 2 ;;
    --api-key) OV_API_KEY="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) AUTO_YES=true; shift ;;
    --help|-h)
      echo "Usage: $0 --agent <name>|--all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]"
      echo "Agents: $(registry_discover "$SCRIPT_DIR/agents" >/dev/null 2>&1; registry_list | tr '\n' ',' | sed 's/,$//')"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Discover agents ──────────────────────────────────────────────────────────
registry_init
registry_discover "$SCRIPT_DIR/agents"

# ── Determine target agents ──────────────────────────────────────────────────
agents=()
if [[ "$ALL_AGENTS" == "true" ]]; then
  while IFS= read -r a; do agents+=("$a"); done < <(registry_list)
elif [[ -n "$AGENT" ]]; then
  agents=("$AGENT")
else
  log_error "Specify --agent <name> or --all"
  exit 1
fi

# ── Health check ─────────────────────────────────────────────────────────────
check_ov_health || exit 1

# ── Dispatch ─────────────────────────────────────────────────────────────────
rc=0
for a in "${agents[@]}"; do
  log_info "Processing agent: $a"
  if registry_dispatch "$a" integrate; then
    log_ok "Agent $a: integration complete"
  else
    log_error "Agent $a: integration failed"
    rc=1
  fi
done

if [[ $rc -ne 0 ]]; then
  log_warn "Some integrations failed or were skipped. Review output above."
fi
exit $rc
