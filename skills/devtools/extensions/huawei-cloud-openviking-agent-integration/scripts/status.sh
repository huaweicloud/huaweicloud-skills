#!/bin/bash
# status.sh — OpenViking integration status entry point
# Usage: ./status.sh [--json] [--agent <name>]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/entrypoint.sh"
# Register agents early so usage()/error paths can list supported agents (ISSUE-006)
registry_init
registry_discover "$SCRIPT_DIR/agents"
JSON_OUTPUT=false
AGENT=""
usage() {
  echo "Usage: $0 [--json] [--agent <name>]"
  echo "Without --agent: shows status for all agents."
  echo "Supported agents: $(ov_supported_agents 2>/dev/null || echo "(none)")"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON_OUTPUT=true; shift ;;
    --agent)
      if [[ $# -lt 2 ]]; then log_error "--agent requires a value"; usage; exit 1; fi
      AGENT="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    # ISSUE-006: reject unknown options (e.g. --all) with the usage line
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
done
agents=()
if [[ -n "$AGENT" ]]; then
  # ISSUE-006: reject unknown agent names with the supported list up front
  # (previously fell through to a generic "dispatch failed" on first use)
  ov_require_supported_agent "$AGENT" || exit 1
  agents=("$AGENT")
else
  while IFS= read -r a; do agents+=("$a"); done < <(registry_list)
fi
check_ov() {
  local resp status version auth_mode
  resp=$("$OV_CURL_BIN" -sf --connect-timeout 5 --max-time 10 "${OV_ENDPOINT}/health" 2>/dev/null) || {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
      echo '{"status":"unreachable","endpoint":"'"$OV_ENDPOINT"'"}'
    else
      echo -e "${RED}✗${NC} OpenViking server unreachable at $OV_ENDPOINT"
    fi
    return 1
  }
  status=$(echo "$resp" | _ov_health parse-field - status 2>/dev/null)
  version=$(echo "$resp" | _ov_health parse-field - version 2>/dev/null)
  auth_mode=$(echo "$resp" | _ov_health parse-field - auth_mode 2>/dev/null)
  if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "{\"status\":\"$status\",\"version\":\"$version\",\"auth_mode\":\"$auth_mode\",\"endpoint\":\"$OV_ENDPOINT\"}"
  else
    echo -e "${GREEN}✓${NC} OpenViking server: $status (v$version, auth=$auth_mode) at $OV_ENDPOINT"
  fi
}
get_agent_json() {
  local a="$1"
  local result s_name s_status s_detail
  result=$(registry_dispatch "$a" status 2>/dev/null || echo "$a|error|dispatch failed")
  IFS='|' read -r s_name s_status s_detail <<< "$result"
  printf '{"agent":"%s","status":"%s","detail":"%s"}' "$s_name" "$s_status" "$s_detail"
}
if [[ "$JSON_OUTPUT" == "true" ]]; then
  # JSON mode — exit code mirrors human mode (non-zero on unreachable / agent errors)
  overall_rc=0
  ov_json=$(check_ov 2>/dev/null) || overall_rc=1
  # Build agents array
  agent_jsons=()
  for a in "${agents[@]}"; do
    local_aj=$(get_agent_json "$a")
    agent_jsons+=("$local_aj")
    [[ "$local_aj" == *'"status":"error"'* ]] && overall_rc=1
  done
  # Emit JSON
  _ov_json merge-agents "$ov_json" "${agent_jsons[@]}"
  exit $overall_rc
else
  # Human-readable mode
  echo "━━━ OpenViking Integration Status ━━━"
  echo ""
  overall_rc=0
  check_ov || overall_rc=1
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
      overall_rc=1
    fi
  done
  exit $overall_rc
fi
