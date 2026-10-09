#!/bin/bash
# OpenViking MCP Endpoint Verification
# Uses the official MCP Python SDK (streamable_http_client + ClientSession) for a
# single-session handshake: initialize -> initialized -> tools/list -> tools/call(health).
# REST prefetch checks remain as a secondary validation channel.
set -euo pipefail
source "$(dirname "$0")/lib/entrypoint.sh"
: "${OV_PY_DIR:=$(cd "$(dirname "$0")/py" && pwd)}"
OV_API_KEY="${OV_API_KEY:-}"
usage() {
  echo "Usage: $0 [--endpoint URL] [--api-key KEY]"
  echo "  --endpoint URL   OpenViking server base URL (default: \$OV_ENDPOINT)"
  echo "  --api-key KEY    API key for the MCP handshake (default: \$OV_API_KEY)"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint)
      if [[ $# -lt 2 ]]; then log_error "--endpoint requires a value"; usage; exit 1; fi
      OV_ENDPOINT="$2"; shift 2 ;;
    --api-key)
      if [[ $# -lt 2 ]]; then log_error "--api-key requires a value"; usage; exit 1; fi
      OV_API_KEY="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
done
MCP_URL="${OV_ENDPOINT}/mcp"
OV_VERIFY_QUERY="${OV_VERIFY_QUERY:-openviking verification}"
OV_ACCOUNT="${OV_ACCOUNT:-default}"

# P0-2: Pass API key to the SDK script via env var (not CLI args) to avoid ps/proc exposure
if [[ -n "$OV_API_KEY" ]]; then
  export OV_API_KEY
fi

OV_TMP_REST=$(mktemp); OV_TMP_TOPK=$(mktemp); OV_TMP_ACCT=$(mktemp)
trap 'rm -f "$OV_TMP_REST" "$OV_TMP_TOPK" "$OV_TMP_ACCT"' EXIT

echo "━━━ OpenViking MCP Verification ━━━"
echo ""
log_info "Health check..."
local_health=$(ov_curl -sf "${OV_ENDPOINT}/health" 2>/dev/null) || { log_error "Server not reachable at $OV_ENDPOINT"; exit 1; }
log_ok "Server healthy: $local_health"
echo ""
log_info "MCP handshake via official SDK (single session)..."

SDK_RC=0
# Capture SDK stderr into temp file, but do NOT let set -e abort: keep exit code in SDK_RC
SDK_OUT=$("$OV_PY" "$OV_PY_DIR/ov_verify_mcp_sdk.py" "$MCP_URL" 2>"$OV_TMP_REST") || SDK_RC=$?
if [[ ${SDK_RC:-1} -ne 0 ]]; then
  # Surface the SDK's concrete error (HTTP status / JSON-RPC error / unreachable)
  log_error "MCP handshake FAILED (exit ${SDK_RC:-1})"
  cat "$OV_TMP_REST" >&2
  exit 1
fi

SERVER_NAME=""; SERVER_VERSION=""; PROTOCOL_VERSION=""; TOOL_COUNT=""
declare -a TOOL_LINES=()
HEALTH_RESULT=""
while IFS= read -r line; do
  case "$line" in
    SERVER:*) SERVER_NAME="${line#SERVER:}" ;;
    VERSION:*) SERVER_VERSION="${line#VERSION:}" ;;
    PROTOCOL:*) PROTOCOL_VERSION="${line#PROTOCOL:}" ;;
    TOOLS:*) TOOL_COUNT="${line#TOOLS:}" ;;
    TOOL:*) TOOL_LINES+=("${line#TOOL:}") ;;
    HEALTH:*) HEALTH_RESULT="${line#HEALTH:}" ;;
  esac
done <<< "$SDK_OUT"

if [[ -z "$PROTOCOL_VERSION" || -z "$SERVER_NAME" ]]; then
  log_error "MCP initialize handshake failed — SDK returned no server info"
  log_error "Raw output (first 200 chars): ${SDK_OUT:0:200}"
  exit 1
fi
log_ok "MCP server: $SERVER_NAME v$SERVER_VERSION (protocol $PROTOCOL_VERSION)"
log_ok "Found $TOOL_COUNT MCP tools"
for tl in "${TOOL_LINES[@]:0:20}"; do
  name="${tl%%:*}"
  desc="${tl#*:}"
  echo "  - $name: $desc"
done
if [[ "${#TOOL_LINES[@]}" -gt 20 ]]; then
  echo "  ... and $(( ${#TOOL_LINES[@]} - 20 )) more"
fi
log_info "Testing 'health' tool..."
if [[ -n "$HEALTH_RESULT" ]]; then
  log_ok "Health tool: $HEALTH_RESULT"
else
  log_error "Health tool call returned no result"
  exit 1
fi

echo ""
echo "━━━ REST Prefetch Verification ━━━"
echo ""
# ISSUE-002: every REST check that deviates from contract now flips the overall
# result — a green SDK handshake no longer masks failing REST paths.
OVERALL_RC=0
log_info "REST /api/v1/search/find with 'limit'..."
REST_RESP=$(ov_curl -s -o "$OV_TMP_REST" -w "%{http_code}" \
  -X POST "${OV_ENDPOINT}/api/v1/search/find" \
  -H "Content-Type: application/json" \
  -H "X-OpenViking-Account: ${OV_ACCOUNT}" -H "X-OpenViking-User: default" \
  -d "{\"query\":\"$OV_VERIFY_QUERY\",\"limit\":5}" 2>/dev/null || echo "000")
if [[ "$REST_RESP" == "200" ]]; then
  REST_COUNT=$("$OV_PY" "$OV_PY_DIR/ov_verify_mcp.py" count-results "$OV_TMP_REST" 2>/dev/null || echo "?")
  log_ok "REST find: HTTP 200, ${REST_COUNT} results (account: ${OV_ACCOUNT})"
else
  log_error "REST find: HTTP ${REST_RESP} — prefetch will FAIL"
  cat "$OV_TMP_REST" 2>/dev/null | head -5
  OVERALL_RC=1
fi
echo ""
log_info "Confirming 'top_k' rejected..."
TOPK_RESP=$(ov_curl -s -o "$OV_TMP_TOPK" -w "%{http_code}" \
  -X POST "${OV_ENDPOINT}/api/v1/search/find" \
  -H "Content-Type: application/json" \
  -H "X-OpenViking-Account: ${OV_ACCOUNT}" \
  -d '{"query":"test","top_k":5}' 2>/dev/null || echo "000")
if [[ "$TOPK_RESP" == "400" ]]; then
  log_ok "'top_k' rejected with HTTP 400"
else
  log_warn "'top_k' returned HTTP ${TOPK_RESP} (expected 400)"
  OVERALL_RC=1
fi
echo ""
log_info "Checking account '${OV_ACCOUNT}' memories..."
ACCT_RESP=$(ov_curl -s -o "$OV_TMP_ACCT" -w "%{http_code}" \
  -X POST "${OV_ENDPOINT}/api/v1/search/find" \
  -H "Content-Type: application/json" \
  -H "X-OpenViking-Account: ${OV_ACCOUNT}" \
  -d "{\"query\":\"$OV_VERIFY_QUERY\",\"limit\":10}" 2>/dev/null || echo "000")
if [[ "$ACCT_RESP" == "200" ]]; then
  ACCT_COUNT=$("$OV_PY" "$OV_PY_DIR/ov_verify_mcp.py" count-results "$OV_TMP_ACCT" 2>/dev/null || echo "0")
  if [[ "$ACCT_COUNT" -gt 0 ]]; then
    log_ok "Account '${OV_ACCOUNT}' has ${ACCT_COUNT} memories"
  else
    log_warn "Account '${OV_ACCOUNT}' returned 0 memories"
  fi
else
  log_error "Account check failed: HTTP ${ACCT_RESP}"
  OVERALL_RC=1
fi

echo ""
echo "━━━ Verification Summary ━━━"
echo "  Endpoint:       $MCP_URL"
echo "  Protocol:       $PROTOCOL_VERSION"
echo "  Server:         $SERVER_NAME v$SERVER_VERSION"
echo "  Tools:          $TOOL_COUNT available"
echo "  Health tool:    $HEALTH_RESULT"
echo "  Session:        single-session (official SDK)"
echo "  REST prefetch:  ${REST_RESP:-unknown} (limit, account: ${OV_ACCOUNT})"
echo "  top_k rejected: ${TOPK_RESP:-unknown} (expected 400)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$OVERALL_RC" -eq 0 ]]; then
  log_ok "MCP + REST prefetch verification PASSED"
else
  log_error "MCP + REST prefetch verification FAILED (${OVERALL_RC} REST contract check(s) below expectations)"
fi
exit $OVERALL_RC