# Acceptance Criteria

Criteria for a successful embedding model switch.

## Pre-Switch

- [ ] OpenViking environment state is `running` (checked via job-env-manager API)
- [ ] Target llama-server responds to `/v1/embeddings`
- [ ] Dimension measured from the endpoint (not assumed from user input)

## Switch Execution

- [ ] `switch-embedding-model.sh <model_name> <llama_port> <dimension>` exits 0
- [ ] `ov.conf.bak` created before modification
- [ ] `ov.conf` `embedding.dense` matches target: provider, model, api_base, dimension
- [ ] If dimension changed: `vectordb/context` deleted before restart
- [ ] Restart used kill + exec, not stop/start
- [ ] Stale locks (`.openviking.pid`, vectordb `LOCK`) cleaned

## Post-Switch

- [ ] `GET /health` returns `healthy=true` (within 30s)
- [ ] New server PID differs from old PID
- [ ] `collection_meta.json` `Dimension` equals target
- [ ] Log shows no `Traceback`, `Application startup failed`, `EmbeddingRebuildRequiredError`, or `DataDirectoryLocked`
- [ ] A semantic search call returns results with the new model

## Rollback Behavior (if verification fails)

- [ ] `ov.conf.bak` restored
- [ ] Script exits with non-zero code
- [ ] Error reason reported clearly (health / PID / log / dimension)