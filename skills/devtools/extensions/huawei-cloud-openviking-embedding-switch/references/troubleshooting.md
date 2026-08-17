# Troubleshooting

## Problem 1: EmbeddingRebuildRequiredError on Server Startup

**Symptom:**
```
openviking.storage.errors.EmbeddingRebuildRequiredError: Existing collection embedding dimension (1024) does not match current configuration (512).
```

**Cause:** `collection_meta.json` still records the old dimension. vectordb index not fully deleted before restart.

**Fix:**
```bash
SANDBOX_DIR=$(curl -s http://127.0.0.1:8090/api/v1/envs/openviking \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['cwd'])")
rm -rf "${SANDBOX_DIR}/data/vectordb/context"
# Then restart the server (Step 5 in SKILL.md)
```

---

## Problem 2: ov.conf Overwritten After Environment Restart

**Symptom:** After `stop` + `start`, `ov.conf` reverts to TokenHub defaults.

**Cause:** `start.sh` overwrites `ov.conf` using `JOB_ENV_MODEL_API_KEY` or `AK`/`SK` env vars.

**Fix:** Do NOT use stop/start. Instead: modify `ov.conf` → kill server from host → start via `exec` API. If stop/start was already used, re-apply Step 3 then Step 5.

---

## Problem 3: exec API "No such process" When Trying to Kill Server

**Symptom:** `kill` via exec API fails with "No such process".

**Cause:** exec API runs in a different PID namespace. Host PID doesn't exist there.

**Fix:** Kill from the host directly:
```bash
SERVER_PID=$(ps aux | grep vsbin-openviking-server | grep -v grep | awk '{print $2}' | head -1)
kill "$SERVER_PID"
```

---

## Problem 4: Server Fails to Bind Port 1933 (Port Conflict)

**Symptom:**
```
uvicorn.error - ERROR - [Errno 98] error while attempting to bind on address ('127.0.0.1', 1933): address already in use
```

**Cause:** Previous server process not fully terminated. SIGTERM + `sleep 3` is insufficient — the port may not be released yet.

**Fix:** The script now polls for port release after kill:
1. `kill $PID` (SIGTERM)
2. Poll `ss -tlnp | grep 1933` for up to 10 seconds
3. If still in use: `kill -9 $PID` (SIGKILL) + wait
4. Verify port is free before starting new server

**Manual fix:**
```bash
pkill -9 -f vsbin-openviking-server
sleep 3
ss -tlnp | grep 1933  # should be empty
```

---

## Problem 5: DataDirectoryLocked on Startup

**Symptom:**
```
openviking.utils.process_lock.DataDirectoryLocked: Another OpenViking process (PID 4) is already using the data directory
```

**Cause:** Stale lock files (`.openviking.pid`, `LOCK`) remain after killing the server.

**Fix:** The script now cleans up lock files before starting the new server:
```bash
SANDBOX_DIR=$(curl -s http://127.0.0.1:8090/api/v1/envs/openviking \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['cwd'])")
rm -f "${SANDBOX_DIR}/data/.openviking.pid"
find "${SANDBOX_DIR}/data/vectordb" -name "LOCK" -delete
```

---

## Problem 6: Health Check Passes But Config Not Applied (False Positive)

**Symptom:** Script reports success, but server is still using old config.

**Cause:** Old server wasn't killed, new server failed to bind port. Health check hit the old server.

**Fix:** The script now verifies the server PID changed after restart:
```bash
OLD_PID=$(ps aux | grep vsbin-openviking-server | grep -v grep | awk '{print $2}' | head -1)
# ... restart ...
NEW_PID=$(ps aux | grep vsbin-openviking-server | grep -v grep | awk '{print $2}' | head -1)
if [ "$NEW_PID" = "$OLD_PID" ]; then
  echo "ERROR: PID unchanged — old server still running"
  # rollback
fi
```

---

## Problem 7: llama-server Embedding Endpoint Returns Error

**Symptom:** `curl` to embedding endpoint returns error or empty response.

**Fix:**
```bash
# Check llama env state
curl -s http://127.0.0.1:8090/api/v1/envs/llama | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])"
# Start if needed
curl -s -X POST http://127.0.0.1:8090/api/v1/envs/llama/start
# Verify --embeddings flag
ps aux | grep llama-server | grep -v grep
```

---

## Problem 8: nsenter Fails with "Operation not permitted"

**Fix:** Do not use `nsenter`. Use the job-env-manager `exec` API instead.

---

## Problem 9: Server Log Shows Constant Retrying to /embeddings

**Symptom:** `INFO Retrying request to /embeddings in 0.48 seconds`

**Cause:** Configured `api_base` endpoint is unreachable (typically TokenHub).

**Fix:** This is the original problem that switching to local llama-server solves. Note: these "Retrying" messages are INFO level and do NOT match the script's error detection pattern, so they won't cause false positives.

---

## Problem 10: exec API Call Hangs Indefinitely

**Symptom:** `curl` to exec API blocks forever when starting server with `nohup`.

**Cause:** The exec session waits for all child processes to exit. `nohup ... &` backgrounds the server, but the exec session may still wait.

**Fix:** Always use `--max-time` on the curl call:
```bash
curl -s --max-time 15 -X POST .../exec \
  -d '{"cmd":["bash","-c","nohup ... & sleep 2 && echo started"]}'
```
The `sleep 2 && echo started` ensures the command returns after giving the server time to start.
