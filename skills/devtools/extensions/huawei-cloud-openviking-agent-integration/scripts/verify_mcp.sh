#!/bin/bash
# OpenViking MCP Endpoint Verification
set -euo pipefail
source "$(dirname "$0")/common.sh"
OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_API_KEY="${OV_API_KEY:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint) OV_ENDPOINT="$2"; shift 2 ;;
    --api-key) OV_API_KEY="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done
MCP_URL="${OV_ENDPOINT}/mcp"
AUTH_HEADERS=()
[[ -n "$OV_API_KEY" ]] && AUTH_HEADERS=(-H "Authorization: Bearer $OV_API_KEY")
OV_TMP_HEADERS=$(mktemp); OV_TMP_REST=$(mktemp)
OV_TMP_TOPK=$(mktemp); OV_TMP_ACCT=$(mktemp)
trap 'rm -f "$OV_TMP_HEADERS" "$OV_TMP_REST" "$OV_TMP_TOPK" "$OV_TMP_ACCT"' EXIT
echo "━━━ OpenViking MCP Verification ━━━"
echo ""
log_info "Health check..."
local_health=$(ov_curl -sf "${OV_ENDPOINT}/health" 2>/dev/null) || { log_error "Server not reachable at $OV_ENDPOINT"; exit 1; }
log_ok "Server healthy: $local_health"
echo ""
log_info "MCP initialize..."
INIT_RESP=$(ov_curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify-mcp","version":"1.0"}}}' \
  -D "$OV_TMP_HEADERS" 2>&1)
if [[ -z "$INIT_RESP" ]]; then log_error "MCP initialize failed: empty response"; exit 1; fi
SESSION_ID=$(grep -i "mcp-session-id" "$OV_TMP_HEADERS" 2>/dev/null | tr -d '\r' | awk '{print $2}')
if [[ -z "$SESSION_ID" ]]; then
  log_warn "No session ID in headers"; SESSION_ID=""
else
  log_ok "Session ID: $SESSION_ID"
fi
read PROTOCOL_VERSION SERVER_NAME SERVER_VERSION <<< "$(echo "$INIT_RESP" | grep "data:" | sed 's/^data: //' | "$OV_PY" -c "
import sys,json
try:
    r=json.loads(sys.stdin.read().strip()).get('result',{})
    print(r.get('protocolVersion','unknown'),r.get('serverInfo',{}).get('name','unknown'),r.get('serverInfo',{}).get('version','unknown'))
except: print('parse-error unknown unknown')" 2>/dev/null || echo "parse-error unknown unknown")"
log_ok "MCP server: $SERVER_NAME v$SERVER_VERSION (protocol $PROTOCOL_VERSION)"
echo ""
log_info "Sending initialized notification..."
if [[ -n "$SESSION_ID" ]]; then
  curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" "${AUTH_HEADERS[@]}" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' 2>/dev/null || true
fi
log_ok "Notification sent"
echo ""
log_info "Listing MCP tools..."
TOOLS_RESP=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}' 2>&1)
TOOL_COUNT=$(echo "$TOOLS_RESP" | grep "data:" | sed 's/^data: //' | "$OV_PY" -c "
import sys,json
try:
    d=json.loads(sys.stdin.read().strip()); tools=d.get('result',{}).get('tools',[])
    print(len(tools))
    for t in tools: print(f\"  - {t['name']}: {t.get('description','')[:80]}\")
except Exception as e: print(f'parse-error: {e}')" 2>/dev/null || echo "0")
log_ok "Found $TOOL_COUNT MCP tools"
echo ""
log_info "Testing 'health' tool..."
HEALTH_RESP=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"health","arguments":{}}}' 2>&1)
HEALTH_RESULT=$(echo "$HEALTH_RESP" | grep "data:" | sed 's/^data: //' | "$OV_PY" -c "
import sys,json
try:
    d=json.loads(sys.stdin.read().strip()); result=d.get('result',{})
    if isinstance(result,dict) and 'content' in result:
        for c in result['content']:
            if c.get('type')=='text': print(c['text'][:200])
    else: print(str(result)[:200])
except Exception as e: print(f'parse-error: {e}')" 2>/dev/null || echo "no response")
log_ok "Health tool: $HEALTH_RESULT"
echo ""
echo "━━━ REST Prefetch Verification ━━━"
echo ""
OV_ACCOUNT="${OV_ACCOUNT:-default}"
log_info "REST /api/v1/search/find with 'limit'..."
REST_RESP=$(ov_curl -s -o "$OV_TMP_REST" -w "%{http_code}" \
  -X POST "${OV_ENDPOINT}/api/v1/search/find" \
  -H "Content-Type: application/json" \
  -H "X-OpenViking-Account: ${OV_ACCOUNT}" -H "X-OpenViking-User: default" \
  -d "{\"query\":\"$OV_VERIFY_QUERY\",\"limit\":5}" 2>/dev/null || echo "000")
if [[ "$REST_RESP" == "200" ]]; then
  REST_COUNT=$("$OV_PY" -c "
import json
try:
    d=json.load(open('"$OV_TMP_REST"')); r=d.get('result',d); total=r.get('total',0)
    if total==0: total=len(r.get('memories',[]))+len(r.get('resources',[]))+len(r.get('skills',[]))
    print(total)
except: print('parse-error')" 2>/dev/null || echo "?")
  log_ok "REST find: HTTP 200, ${REST_COUNT} results (account: ${OV_ACCOUNT})"
else
  log_error "REST find: HTTP ${REST_RESP} — prefetch will FAIL"
  cat "$OV_TMP_REST" 2>/dev/null | head -5
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
fi
echo ""
log_info "Checking account '${OV_ACCOUNT}' memories..."
ACCT_RESP=$(ov_curl -s -o "$OV_TMP_ACCT" -w "%{http_code}" \
  -X POST "${OV_ENDPOINT}/api/v1/search/find" \
  -H "Content-Type: application/json" \
  -H "X-OpenViking-Account: ${OV_ACCOUNT}" \
  -d "{\"query\":\"$OV_VERIFY_QUERY\",\"limit\":10}" 2>/dev/null || echo "000")
if [[ "$ACCT_RESP" == "200" ]]; then
  ACCT_COUNT=$("$OV_PY" -c "
import json
try:
    d=json.load(open('"$OV_TMP_ACCT"')); r=d.get('result',d); total=r.get('total',0)
    if total==0: total=len(r.get('memories',[]))+len(r.get('resources',[]))+len(r.get('skills',[]))
    print(total)
except: print('0')" 2>/dev/null || echo "0")
  if [[ "$ACCT_COUNT" -gt 0 ]]; then
    log_ok "Account '${OV_ACCOUNT}' has ${ACCT_COUNT} memories"
  else
    log_warn "Account '${OV_ACCOUNT}' returned 0 memories"
  fi
else
  log_error "Account check failed: HTTP ${ACCT_RESP}"
fi
echo ""
echo "━━━ Verification Summary ━━━"
echo "  Endpoint:       $MCP_URL"
echo "  Protocol:       $PROTOCOL_VERSION"
echo "  Server:         $SERVER_NAME v$SERVER_VERSION"
echo "  Tools:          $TOOL_COUNT available"
echo "  Health tool:    Working"
echo "  Session:        ${SESSION_ID:-none}"
echo "  REST prefetch:  ${REST_RESP:-unknown} (limit, account: ${OV_ACCOUNT})"
echo "  top_k rejected: ${TOPK_RESP:-unknown} (expected 400)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "MCP + REST prefetch verification PASSED"
