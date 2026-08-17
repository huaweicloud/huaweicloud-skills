# Related Commands

Common commands for the embedding model switch workflow.

## job-env-manager REST API

| Command | Purpose |
|---------|---------|
| `curl -s http://127.0.0.1:8090/api/v1/envs/openviking` | Get environment details (state, cwd) |
| `curl -s -X POST http://127.0.0.1:8090/api/v1/envs/openviking/start` | Start the OpenViking environment |
| `curl -s -X POST http://127.0.0.1:8090/api/v1/envs/openviking/stop` | **Forbidden for restart** — re-runs start.sh, overwrites ov.conf |
| `curl -s --max-time 15 -X POST http://127.0.0.1:8090/api/v1/envs/openviking/exec -H 'Content-Type: application/json' -d '{"cmd":[...]}'` | Execute a command inside the sandbox |

## Embedding Endpoint

| Command | Purpose |
|---------|---------|
| `curl -s http://127.0.0.1:${PORT}/v1/embeddings -H "Content-Type: application/json" -d '{"model":"${MODEL}","input":"test"}'` | Validate embedding endpoint and measure dimension |

## Server Health and Process

| Command | Purpose |
|---------|---------|
| `curl -s http://127.0.0.1:1933/health` | Check server health |
| `ss -tlnp \| grep 1933` | Check if port 1933 is in use (and which PID) |
| `kill <PID>` / `kill -9 <PID>` | Stop the old server process (SIGTERM then escalate) |

## Data Inspection

| Command | Purpose |
|---------|---------|
| `cat ${SANDBOX_DIR}/process_dir/ov.conf` (or equivalent path) | Inspect current embedding config |
| `python3 -c "import json; d=json.load(open('.../collection_meta.json')); print(d['Dimension'])"` | Check collection dimension |
| `grep -ci "Traceback\|Application startup failed\|EmbeddingRebuildRequiredError\|DataDirectoryLocked" <log>` | Check startup errors (expected: 0) |

## Execution Examples

```bash
# Full switch (model, llama port, dimension)
bash scripts/switch-embedding-model.sh bge-small-zh-v1.5 18200 512

# Execute commands inside the sandbox
curl -s --max-time 15 -X POST http://127.0.0.1:8090/api/v1/envs/openviking/exec \
  -H 'Content-Type: application/json' \
  -d '{"cmd":["bash","-c","ls /workspace/process_dir/ov.conf"]}'
```