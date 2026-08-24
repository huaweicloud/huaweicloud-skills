#!/bin/bash
# =============================================================================
# status.sh — OpenViking integration status entry point (thin)
# =============================================================================
# OO architecture: sources lib/ framework, discovers agent subclasses from
# agents/, dispatches to agent_<name>_status via the registry.
#
# Usage: ./status.sh [--json] [--agent <name>]
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
JSON_OUTPUT=false
AGENT=""

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON_OUTPUT=true; shift ;;
    --agent) AGENT="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--json] [--agent <name>]"
      echo "Without --agent: shows status for all agents."
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Discover agents ──────────────────────────────────────────────────────────
registry_init
registry_discover "$SCRIPT_DIR/agents"

# ── Determine target agents ──────────────────────────────────────────────────
agents=()
if [[ -n "$AGENT" ]]; then
  agents=("$AGENT")
else
  while IFS= read -r a; do agents+=("$a"); done < <(registry_list)
fi

# ── Check OpenViking server ──────────────────────────────────────────────────
check_ov() {
  local resp status version auth_mode
  resp=$(curl -sf "${OV_ENDPOINT}/health" 2>/dev/null) || {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
      echo '{"status":"unreachable","endpoint":"'"$OV_ENDPOINT"'"}'
    else
      echo -e "${RED}✗${NC} OpenViking server unreachable at $OV_ENDPOINT"
    fi
    return 1
  }
  status=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null)
  version=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version','unknown'))" 2>/dev/null)
  auth_mode=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('auth_mode','unknown'))" 2>/dev/null)
  
  if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "{\"status\":\"$status\",\"version\":\"$version\",\"auth_mode\":\"$auth_mode\",\"endpoint\":\"$OV_ENDPOINT\"}"
  else
    echo -e "${GREEN}✓${NC} OpenViking server: $status (v$version, auth=$auth_mode) at $OV_ENDPOINT"
  fi
}

# ── Get agent status as JSON object ──────────────────────────────────────────
get_agent_json() {
  local a="$1"
  local result s_name s_status s_detail
  result=$(registry_dispatch "$a" status 2>/dev/null || echo "$a|error|dispatch failed")
  IFS='|' read -r s_name s_status s_detail <<< "$result"
  printf '{"agent":"%s","status":"%s","detail":"%s"}' "$s_name" "$s_status" "$s_detail"
}

# ── Output ───────────────────────────────────────────────────────────────────
if [[ "$JSON_OUTPUT" == "true" ]]; then
  # JSON mode
  ov_json=$(check_ov 2>/dev/null || echo '{"status":"unreachable"}')
  
  # Build agents array
  agent_jsons=()
  for a in "${agents[@]}"; do
    agent_jsons+=("$(get_agent_json "$a")")
  done
  
  # Emit JSON
  python3 -c "
import json, sys
ov = json.loads('''$ov_json''')
agent_strs = sys.argv[1:]
agents = [json.loads(s) for s in agent_strs]
print(json.dumps({'openviking': ov, 'agents': agents}, indent=2))
" "${agent_jsons[@]}"
else
  # Human-readable mode
  echo "━━━ OpenViking Integration Status ━━━"
  echo ""
  check_ov || true
  echo ""
  echo "━━━ Agent Integration Status ━━━"
  for a in "${agents[@]}"; do
    result=$(registry_dispatch "$a" status 2>/dev/null || echo "$a|error|dispatch failed")
    s_name="${result%%|*}"
    rest="${result#*|}"
    s_status="${rest%%|*}"
    s_detail="${rest#*|}"
    if [[ "$s_status" == "integrated" ]]; then
      echo -e "  ${GREEN}✓${NC} $s_name: $s_detail"
    elif [[ "$s_status" == "not_integrated" ]]; then
      echo -e "  ${RED}✗${NC} $s_name: $s_detail"
    else
      echo -e "  ${YELLOW}?${NC} $s_name: $s_detail"
    fi
  done
fi
