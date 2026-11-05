#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────────────────────
# switch-embedding-model.sh
# Switch OpenViking's embedding model to a local llama-server.
# Usage: bash switch-embedding-model.sh <model_name> <llama_port> <dimension>
# Example: bash switch-embedding-model.sh bge-small-zh-v1.5 18200 512
# ────────────────────────────────────────────────────────────

if [ $# -ne 3 ]; then
  echo "Usage: $0 <model_name> <llama_port> <dimension>"
  echo "Example: $0 bge-small-zh-v1.5 18200 512"
  exit 1
fi

MODEL_NAME="$1"
LLAMA_PORT="$2"
TARGET_DIMENSION="$3"
JEM_BASE="http://127.0.0.1:8090/api/v1"
SERVER_PORT=1933
HEALTH_TIMEOUT=30  # seconds to wait for server health

# Look up the PID listening on a given TCP port (host netns; sandboxes share-net)
# Reverse lookup via 'ss' (primary) with 'fuser' fallback — no reliance on a
# brittle process-name glob like 'vsbin-openviking-server'.
get_pid_on_port() {
  local port="$1" line pid=""
  line=$(ss -tlnp 2>/dev/null | awk -v p=":${port} " 'index($0,p){print $NF}' | head -1 || true)
  pid=$(echo "$line" | grep -oP 'pid=\K[0-9]+' | head -1 || true)
  if [ -z "$pid" ] && command -v fuser >/dev/null 2>&1; then
    # fuser output looks like "1933/tcp: 1234  5678"; keep only standalone ints
    pid=$(fuser "${port}/tcp" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | head -1 || true)
  fi
  echo "$pid"
}

echo "=== OpenViking Embedding Model Switch ==="
echo "  Model:    $MODEL_NAME"
echo "  Port:     $LLAMA_PORT"
echo "  Dimension: $TARGET_DIMENSION"
echo ""

# ── Step 1: Detect sandbox directory ──
echo "[1/6] Detecting OpenViking sandbox..."
ENVS_RESP=$(curl -s "${JEM_BASE}/envs/openviking")
OV_STATE=$(echo "$ENVS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
SANDBOX_DIR=$(echo "$ENVS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['cwd'])")

if [ "$OV_STATE" != "running" ]; then
  echo "ERROR: OpenViking environment state is '$OV_STATE', expected 'running'."
  echo "Start it first: curl -X POST ${JEM_BASE}/envs/openviking/start"
  exit 1
fi
echo "  Sandbox: $SANDBOX_DIR (state=$OV_STATE)"

# Show current config
echo "  Current embedding config:"
python3 -c "
import json
with open('${SANDBOX_DIR}/process_dir/ov.conf') as f:
    d = json.load(f)
e = d['embedding']['dense']
print(f\"    model={e['model']}, api_base={e['api_base']}, dim={e['dimension']}\")
"

# ── Step 2: Validate target endpoint ──
echo ""
echo "[2/6] Validating embedding endpoint at 127.0.0.1:${LLAMA_PORT}..."
EMBED_RESP=$(curl -s --max-time 10 "http://127.0.0.1:${LLAMA_PORT}/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_NAME}\",\"input\":\"test\"}" 2>&1) || true

ACTUAL_DIM=$(echo "$EMBED_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(len(d['data'][0]['embedding']))
except:
    print('error')
" 2>/dev/null) || ACTUAL_DIM="error"

if [ "$ACTUAL_DIM" = "error" ]; then
  echo "ERROR: Cannot reach embedding endpoint or invalid response."
  echo "  Response: $EMBED_RESP"
  exit 1
fi
echo "  Endpoint OK, actual dimension: $ACTUAL_DIM"

if [ "$ACTUAL_DIM" != "$TARGET_DIMENSION" ]; then
  echo "WARNING: Specified dimension ($TARGET_DIMENSION) != actual ($ACTUAL_DIM)"
  echo "  Using actual dimension: $ACTUAL_DIM"
  TARGET_DIMENSION="$ACTUAL_DIM"
fi

# ── Step 3: Modify ov.conf ──
echo ""
echo "[3/6] Modifying ov.conf..."

# BUG-5 fix: backup original config for rollback
cp "${SANDBOX_DIR}/process_dir/ov.conf" "${SANDBOX_DIR}/process_dir/ov.conf.bak"

python3 -c "
import json
conf_path = '${SANDBOX_DIR}/process_dir/ov.conf'
with open(conf_path, encoding='utf-8') as f:
    data = json.load(f)
dense = data['embedding']['dense']
dense['provider'] = 'openai'
dense['model'] = '${MODEL_NAME}'
dense['api_key'] = 'not-needed'
dense['api_base'] = 'http://127.0.0.1:${LLAMA_PORT}/v1'
dense['dimension'] = ${TARGET_DIMENSION}
with open(conf_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('  ov.conf updated (backup at ov.conf.bak)')
"

# ── Step 4: Delete incompatible vectordb index ──
echo ""
echo "[4/6] Checking vectordb index compatibility..."
COLLECTION_META="${SANDBOX_DIR}/data/vectordb/context/collection_meta.json"
if [ -f "$COLLECTION_META" ]; then
  CURRENT_DIM=$(python3 -c "import json; print(json.load(open('$COLLECTION_META'))['Dimension'])")
  if [ "$CURRENT_DIM" != "$TARGET_DIMENSION" ]; then
    echo "  Dimension mismatch: $CURRENT_DIM → $TARGET_DIMENSION"
    echo "  Deleting vectordb/context..."
    rm -rf "${SANDBOX_DIR}/data/vectordb/context"
    echo "  Deleted."
  else
    echo "  Dimensions match ($CURRENT_DIM), no deletion needed."
  fi
else
  echo "  No existing collection_meta.json, skipping."
fi

# ── Step 5: Restart openviking-server ──
echo ""
echo "[5/6] Restarting openviking-server..."

# 5a. Kill old process and wait for port release (BUG-1 fix)
# Locate the old server by port 1933 reverse lookup (NOT by process-name glob).
OLD_PID=$(get_pid_on_port "$SERVER_PORT")
if [ -n "$OLD_PID" ]; then
  echo "  Killing old server (PID $OLD_PID)..."
  kill "$OLD_PID" 2>/dev/null || true

  # Poll for port release (up to 10 seconds)
  for i in $(seq 1 10); do
    if ! ss -tlnp 2>/dev/null | grep -q ":${SERVER_PORT} "; then
      echo "  Port $SERVER_PORT released after ${i}s"
      break
    fi
    [ "$i" = "10" ] && {
      echo "  SIGTERM didn't release port, using SIGKILL..."
      kill -9 "$OLD_PID" 2>/dev/null || true
      sleep 2
    }
    sleep 1
  done
else
  # ISSUE-002: never silently skip — surface the empty-PID case explicitly.
  echo "  WARNING: no server process found on :${SERVER_PORT} (port reverse lookup) — nothing to kill."
  echo "          If another process later binds :${SERVER_PORT}, the new server may fail to start."
fi

# BUG-3 fix: clean up stale lock files
rm -f "${SANDBOX_DIR}/data/.openviking.pid" 2>/dev/null
find "${SANDBOX_DIR}/data/vectordb" -name "LOCK" -delete 2>/dev/null
echo "  Cleaned up lock files"

# 5b. Start new server via exec API
echo "  Starting new server via exec API..."
EXEC_BODY_FILE=$(mktemp)
EXEC_HTTP=$(curl -s --max-time 15 -o "$EXEC_BODY_FILE" -w "%{http_code}" \
  -X POST "${JEM_BASE}/envs/openviking/exec" \
  -H 'Content-Type: application/json' \
  -d '{"cmd":["bash","-c","nohup /root/runtime/openviking/venv/bin/openviking-server --config /workspace/process_dir/ov.conf > /workspace/process_dir/openviking-server.log 2>&1 & sleep 2 && echo started"]}' 2>/dev/null || true)
EXEC_BODY=$(cat "$EXEC_BODY_FILE" 2>/dev/null || true)
rm -f "$EXEC_BODY_FILE"

# ISSUE-004: validate exec HTTP status + JSON body (ok/success), not just grep "error".
EXEC_OK="no"
if [[ "$EXEC_HTTP" =~ ^2[0-9][0-9]$ ]]; then
  EXEC_OK=$(echo "$EXEC_BODY" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    ok = d.get('ok') if d.get('ok') is not None else d.get('success')
    print('yes' if ok is True or str(ok).lower() in ('true','yes') else 'no')
except Exception:
    print('bad-json')
" 2>/dev/null || echo "bad-json")
fi

if [[ ! "$EXEC_HTTP" =~ ^2[0-9][0-9]$ ]] || [ "$EXEC_OK" != "yes" ]; then
  echo "  ❌ exec API failed: HTTP=$EXEC_HTTP ok=$EXEC_OK"
  echo "  Response body: ${EXEC_BODY:-<empty>}"
  echo "  Rolling back config (ov.conf.bak)..."
  cp "${SANDBOX_DIR}/process_dir/ov.conf.bak" "${SANDBOX_DIR}/process_dir/ov.conf"
  echo "  Check log: ${SANDBOX_DIR}/process_dir/openviking-server.log"
  exit 1
fi
echo "  ✅ exec API accepted (HTTP $EXEC_HTTP)"

# ── Step 6: Verify ──
echo ""
echo "[6/6] Verifying..."

# BUG-2 fix: poll health endpoint with retry loop instead of fixed sleep
echo "  Waiting for server to become healthy (timeout ${HEALTH_TIMEOUT}s)..."
HEALTHY="False"
for i in $(seq 1 "$HEALTH_TIMEOUT"); do
  HEALTH=$(curl -s --max-time 3 "http://127.0.0.1:${SERVER_PORT}/health" 2>/dev/null || echo "")
  if [ -n "$HEALTH" ]; then
    HEALTHY=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('healthy',False))" 2>/dev/null || echo "False")
    if [ "$HEALTHY" = "True" ]; then
      echo "  ✅ Server healthy after ${i}s"
      break
    fi
  fi
  sleep 1
done

if [ "$HEALTHY" != "True" ]; then
  echo "  ❌ Server not healthy after ${HEALTH_TIMEOUT}s"
  echo "  Rolling back config..."
  cp "${SANDBOX_DIR}/process_dir/ov.conf.bak" "${SANDBOX_DIR}/process_dir/ov.conf"
  echo "  Check log: ${SANDBOX_DIR}/process_dir/openviking-server.log"
  exit 1
fi

# 6b. Verify the running server PID is NEW (BUG-1 fix, ISSUE-002: port-based lookup)
# No matter whether OLD_PID was empty, the new server MUST be bound on :1933 and
# its PID must differ from the old one — otherwise the health check may have hit
# a stale/foreign process (false positive).
NEW_PID=""
for i in $(seq 1 15); do
  NEW_PID=$(get_pid_on_port "$SERVER_PORT")
  [ -n "$NEW_PID" ] && break
  sleep 1
done

if [ -z "$NEW_PID" ]; then
  echo "  ❌ No new server process is bound to port $SERVER_PORT after restart — restart failed!"
  echo "  Rolling back config..."
  cp "${SANDBOX_DIR}/process_dir/ov.conf.bak" "${SANDBOX_DIR}/process_dir/ov.conf"
  echo "  Check log: ${SANDBOX_DIR}/process_dir/openviking-server.log"
  exit 1
fi

if [ -n "$OLD_PID" ] && [ "$NEW_PID" = "$OLD_PID" ]; then
  echo "  ❌ Server PID unchanged ($OLD_PID) — old server still running, config not applied!"
  echo "  Rolling back config..."
  cp "${SANDBOX_DIR}/process_dir/ov.conf.bak" "${SANDBOX_DIR}/process_dir/ov.conf"
  exit 1
fi
echo "  ✅ New server PID: $NEW_PID bound on :${SERVER_PORT} (was: ${OLD_PID:-none})"

# 6c. Collection dimension — retry until generated; missing/mismatch fails the switch (ISSUE-003)
if [ -f "$COLLECTION_META" ] && [ "${CURRENT_DIM:-}" = "$TARGET_DIMENSION" ]; then
  echo "  ✅ Collection dimension unchanged: $CURRENT_DIM"
else
  echo "  Waiting for new collection_meta.json to be generated (up to 15s)..."
  NEW_DIM="unknown"
  for i in $(seq 1 15); do
    if [ -f "$COLLECTION_META" ]; then
      NEW_DIM=$(python3 -c "import json; print(json.load(open('$COLLECTION_META'))['Dimension'])" 2>/dev/null || echo "unknown")
      [ "$NEW_DIM" = "$TARGET_DIMENSION" ] && break
    fi
    sleep 1
  done
  if [ "$NEW_DIM" != "$TARGET_DIMENSION" ]; then
    echo "  ❌ collection_meta.json missing or dimension mismatch ($NEW_DIM, expected $TARGET_DIMENSION) — index rebuild failed!"
    echo "  Rolling back config..."
    cp "${SANDBOX_DIR}/process_dir/ov.conf.bak" "${SANDBOX_DIR}/process_dir/ov.conf"
    echo "  Check log: ${SANDBOX_DIR}/process_dir/openviking-server.log"
    exit 1
  fi
  echo "  ✅ Collection dimension: $NEW_DIM"
fi

# 6d. Log errors — precise pattern to avoid false positives (BUG-4 fix)
# Only match actual Python errors, not "Retrying" info messages
ERROR_COUNT=$(grep -ci "Traceback\|ERROR.*Application startup failed\|EmbeddingRebuildRequiredError\|DataDirectoryLocked" "${SANDBOX_DIR}/process_dir/openviking-server.log" 2>/dev/null || true)
if [ "$ERROR_COUNT" = "0" ] || [ -z "$ERROR_COUNT" ]; then
  echo "  ✅ No errors in log"
else
  echo "  ⚠️  $ERROR_COUNT error-related lines in log:"
  grep -i "Traceback\|ERROR.*Application startup failed\|EmbeddingRebuildRequiredError\|DataDirectoryLocked" "${SANDBOX_DIR}/process_dir/openviking-server.log" 2>/dev/null | head -5
fi

# Cleanup backup
rm -f "${SANDBOX_DIR}/process_dir/ov.conf.bak"

echo ""
echo "=== Switch Complete ==="
echo "  OpenViking is now using: $MODEL_NAME ($TARGET_DIMENSION-dim) at 127.0.0.1:${LLAMA_PORT}"
