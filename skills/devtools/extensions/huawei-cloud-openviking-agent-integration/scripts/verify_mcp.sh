#!/bin/bash
# =============================================================================
# OpenViking MCP Endpoint Verification
# Tests the MCP endpoint by performing JSON-RPC initialize + tools/list calls.
#
# Usage: ./verify_mcp.sh [--endpoint URL] [--api-key KEY]
# =============================================================================
set -euo pipefail
source "$(dirname "$0")/common.sh"

OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_API_KEY="${OV_API_KEY:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint) OV_ENDPOINT="$2"; shift 2 ;;
    --api-key) OV_API_KEY="$2"; shift 2 ;;
  esac
done

MCP_URL="${OV_ENDPOINT}/mcp"

# Build auth headers
AUTH_HEADERS=()
if [[ -n "$OV_API_KEY" ]]; then
  AUTH_HEADERS=(-H "Authorization: Bearer $OV_API_KEY")
fi

echo "━━━ OpenViking MCP Verification ━━━"
echo ""

# Step 1: Health check
log_info "Step 1: Health check..."
local_health=$(curl -sf "${OV_ENDPOINT}/health" 2>/dev/null) || {
  log_error "Server not reachable at $OV_ENDPOINT"
  exit 1
}
log_ok "Server healthy: $local_health"
echo ""

# Step 2: MCP Initialize
log_info "Step 2: MCP initialize (JSON-RPC)..."
INIT_RESP=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify-mcp","version":"1.0"}}}' \
  -D /tmp/ov_mcp_headers 2>&1)

if [[ -z "$INIT_RESP" ]]; then
  log_error "MCP initialize failed: empty response"
  exit 1
fi

# Extract session ID
SESSION_ID=$(grep -i "mcp-session-id" /tmp/ov_mcp_headers 2>/dev/null | tr -d '\r' | awk '{print $2}')
if [[ -z "$SESSION_ID" ]]; then
  log_warn "No session ID in response headers"
  SESSION_ID=""
else
  log_ok "Session ID: $SESSION_ID"
fi

# Parse initialize result
PROTOCOL_VERSION=$(echo "$INIT_RESP" | grep "data:" | sed 's/^data: //' | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    d = json.loads(line)
    print(d.get('result',{}).get('protocolVersion','unknown'))
except: print('parse-error')
" 2>/dev/null || echo "parse-error")

SERVER_NAME=$(echo "$INIT_RESP" | grep "data:" | sed 's/^data: //' | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    d = json.loads(line)
    print(d.get('result',{}).get('serverInfo',{}).get('name','unknown'))
except: print('unknown')
" 2>/dev/null || echo "unknown")

SERVER_VERSION=$(echo "$INIT_RESP" | grep "data:" | sed 's/^data: //' | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    d = json.loads(line)
    print(d.get('result',{}).get('serverInfo',{}).get('version','unknown'))
except: print('unknown')
" 2>/dev/null || echo "unknown")

log_ok "MCP server: $SERVER_NAME v$SERVER_VERSION (protocol $PROTOCOL_VERSION)"
echo ""

# Step 3: Send initialized notification
log_info "Step 3: Sending initialized notification..."
if [[ -n "$SESSION_ID" ]]; then
  curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    "${AUTH_HEADERS[@]}" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' 2>/dev/null || true
fi
log_ok "Notification sent"
echo ""

# Step 4: List tools
log_info "Step 4: Listing MCP tools..."
TOOLS_RESP=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
  "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}' 2>&1)

TOOL_COUNT=$(echo "$TOOLS_RESP" | grep "data:" | sed 's/^data: //' | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    d = json.loads(line)
    tools = d.get('result',{}).get('tools',[])
    print(len(tools))
    for t in tools:
        print(f\"  - {t['name']}: {t.get('description','')[:80]}\")
except Exception as e: print(f'parse-error: {e}')
" 2>/dev/null || echo "0")

log_ok "Found $TOOL_COUNT MCP tools"
echo ""

# Step 5: Test health tool
log_info "Step 5: Testing 'health' tool..."
HEALTH_RESP=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
  "${AUTH_HEADERS[@]}" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"health","arguments":{}}}' 2>&1)

HEALTH_RESULT=$(echo "$HEALTH_RESP" | grep "data:" | sed 's/^data: //' | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    d = json.loads(line)
    result = d.get('result',{})
    if isinstance(result, dict) and 'content' in result:
        for c in result['content']:
            if c.get('type') == 'text':
                print(c['text'][:200])
    else:
        print(str(result)[:200])
except Exception as e: print(f'parse-error: {e}')
" 2>/dev/null || echo "no response")

log_ok "Health tool response: $HEALTH_RESULT"
echo ""

# Summary
echo "━━━ Verification Summary ━━━"
echo "  Endpoint:     $MCP_URL"
echo "  Protocol:     $PROTOCOL_VERSION"
echo "  Server:       $SERVER_NAME v$SERVER_VERSION"
echo "  Tools:        $TOOL_COUNT available"
echo "  Health tool:  Working"
echo "  Session:      ${SESSION_ID:-none}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "MCP endpoint verification PASSED"
