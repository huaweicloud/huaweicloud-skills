# Verification Method

Step-by-step verification for each workflow of the embedding model switch skill.

## Prerequisite Checks

| Check | Method |
|-------|--------|
| job-env-manager reachable | `curl -s http://127.0.0.1:8090/api/v1/envs/openviking` returns JSON |
| OpenViking env running | Response `state` equals `running` |
| llama-server reachable | `curl -s http://127.0.0.1:${LLAMA_PORT}/v1/embeddings -d '{"model":"${MODEL_NAME}","input":"test"}'` returns an embedding |
| Host tooling | `curl --version` and `python3 --version` succeed |

## Task 1: Detect Current Configuration

| Check | Method |
|-------|--------|
| Sandbox dir obtained | `cwd` from env response is non-empty |
| Current embedding read | `ov.conf` contains `embedding.dense` with provider/model/dimension fields |

## Task 2: Validate Target Endpoint

| Check | Method |
|-------|--------|
| Endpoint reachable | `/v1/embeddings` returns HTTP 200 |
| Dimension measured | `len(d['data'][0]['embedding'])` returns a positive integer |
| Dimension correction | Warning printed if user-supplied `TARGET_DIMENSION` differs from measured value |

## Task 3: Modify ov.conf

| Check | Method |
|-------|--------|
| Backup created | `ov.conf.bak` exists before modification |
| Fields updated | `provider`, `model`, `api_base`, `dimension` match the target in `embedding.dense` |

## Task 4: Delete Incompatible vectordb Index

| Check | Method |
|-------|--------|
| Conditional deletion | `vectordb/context` removed **only** when dimension changed |
| Unchanged dimension | `vectordb/context` still exists and Task 4 was skipped |

## Task 5: Restart Server

| Check | Method |
|-------|--------|
| Kill method | Old PID killed with SIGTERM (escalate to SIGKILL if port stays busy) |
| Port released | Port 1933 free within ~10s of kill |
| Stale locks cleaned | `.openviking.pid` and vectordb `LOCK` files removed |
| New process started | `exec` API returns success and a new PID appears for port 1933 |

## Task 6: Verify

| Check | Method |
|-------|--------|
| Health OK | `GET /health` returns `healthy=true` within 30s |
| PID changed | New PID differs from old PID (no port-conflict false positive) |
| Dimension OK | `collection_meta.json` `Dimension` equals measured target dimension |
| Log clean | Grep for `Traceback\|Application startup failed\|EmbeddingRebuildRequiredError\|DataDirectoryLocked` returns 0 |
| Rollback executed | On any failure, `ov.conf.bak` restored and process exits non-zero |

## End-to-End Acceptance

1. `switch-embedding-model.sh <model> <port> <dimension>` exits 0
2. `curl http://127.0.0.1:1933/health` shows `healthy=true`
3. `collection_meta.json` Dimension matches the target
4. Embedding search works with the new model (a `search` MCP call returns results)
5. Server restarts (kill + exec) still use the new model without stop/start