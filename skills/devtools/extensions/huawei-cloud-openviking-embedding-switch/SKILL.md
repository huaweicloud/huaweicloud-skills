---
name: huawei-cloud-openviking-embedding-switch
description: |
  Switch OpenViking's embedding model to a local llama-server (or any OpenAI-compatible embedding endpoint) running inside a bwrap sandbox managed by job-env-manager. Handles the full lifecycle: detect current config, validate the target embedding endpoint, modify ov.conf, delete incompatible vectordb index when dimension changes, restart the openviking-server process in the sandbox, and verify the new collection dimension.
  Use this skill when the user wants to: (1) switch the OpenViking embedding model, (2) change the embedding dimension, (3) fix EmbeddingRebuildRequiredError after a dimension mismatch, (4) rebuild the vectordb index after an embedding model change, (5) use a local llama-server for OpenViking embeddings.
  Trigger words: "切换OpenViking embedding", "OpenViking embedding模型", "OpenViking向量化模型", "openviking embedding switch", "change openviking embedding model", "配置openviking embedding", "openviking llama embedding", "bge embedding openviking", "切换向量化模型", "OpenViking模型切换".
tags:
  - openviking
  - embedding
  - llama
  - vectordb
  - job-env-manager
---

# OpenViking Embedding Model Switch

## 概述

Switch the embedding model used by OpenViking to a local llama-server or any OpenAI-compatible endpoint, with proper vectordb index rebuild and sandbox-safe restart.

> **⚠️ Single-purpose skill** — all operations go through the job-env-manager REST API (`http://127.0.0.1:8090`). Never run `openviking-server` directly on the host.

OpenViking is an AI context database that uses vector embeddings for semantic search. Its embedding model is configured in `ov.conf` under the `embedding.dense` section. When switching to a different embedding model (especially one with a different vector dimension), the existing vectordb index must be deleted and rebuilt — otherwise OpenViking raises `EmbeddingRebuildRequiredError` on startup.

## Architecture

```
OpenViking Embedding Model Switch
├── Detect current config     (Read ov.conf embedding.dense section)
├── Validate endpoint         (Check llama-server /v1/embeddings)
├── Modify ov.conf            (Update provider, model, api_base, dimension)
├── Delete vectordb index     (If dimension changed: rm -rf vectordb/context)
├── Restart server            (Kill + exec, NOT stop/start)
└── Verify                    (Health + PID + dimension + log check)
```

```
┌─────────────────────────────────────────────────────┐
│                    Host                              │
│                                                      │
│  ┌─────────────┐    REST API   ┌──────────────────┐ │
│  │  Agent       │─────────────▶│  job-env-manager  │ │
│  │  (this skill)│              │  :8090            │ │
│  └─────────────┘              └────────┬─────────┘ │
│                                        │            │
│         ┌──────────────────────────────┼──────┐    │
│         │  bwrap sandbox (openviking)   │      │    │
│         │                               ▼      │    │
│         │  ┌────────────────────────────────┐  │    │
│         │  │  openviking-server :1933       │  │    │
│         │  │  ├── ov.conf (embedding config)│  │    │
│         │  │  ├── vectordb/context/         │  │    │
│         │  │  └── viking/ (metadata)        │  │    │
│         │  └────────────────────────────────┘  │    │
│         └──────────────────────────────────────┘    │
│                                                      │
│         ┌──────────────────────────────────────┐    │
│         │  bwrap sandbox (llama)                │    │
│         │  ┌────────────────────────────────┐  │    │
│         │  │  llama-server :18200           │  │    │
│         │  │  --embeddings --model bge-...  │  │    │
│         │  └────────────────────────────────┘  │    │
│         └──────────────────────────────────────┘    │
│                                                      │
│  Both sandboxes use --share-net, so 127.0.0.1        │
│  endpoints are mutually reachable.                   │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

> **Prerequisite check: job-env-manager running**
> ```bash
> curl -s http://127.0.0.1:8090/api/v1/envs/openviking | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])"
> ```

- **job-env-manager** running on `http://127.0.0.1:8090`
- **OpenViking environment** deployed and running (state = `running`)
- **llama-server** running at `127.0.0.1:{port}` with `--embeddings` flag
- **curl** and **python3** available on the host
- No AK/SK or Huawei Cloud credentials required

## IAM Permission Policies

This skill operates on local bwrap sandboxes via the job-env-manager REST API and does not access Huawei Cloud services — no Huawei Cloud IAM policies required. Equivalent access controls are listed in [references/iam-policies.md](references/iam-policies.md).

## 核心命令 (Core Workflow)

### Task 1: Detect Current Configuration

```bash
SANDBOX_DIR=$(curl -s http://127.0.0.1:8090/api/v1/envs/openviking \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['cwd'])")
```

Read `ov.conf` under the sandbox directory to get the current `embedding.dense` section (provider, model, dimension).

### Task 2: Validate Target Embedding Endpoint

```bash
curl -s http://127.0.0.1:${LLAMA_PORT}/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"${MODEL_NAME}","input":"test"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['data'][0]['embedding']))"
```

If unreachable, **STOP**. The script auto-corrects the dimension if the specified value doesn't match the actual endpoint output.

### Task 3: Modify ov.conf

Backs up `ov.conf` to `ov.conf.bak` before modifying. Updates the `embedding.dense` section:

| Field | Description |
|-------|-------------|
| `provider` | Embedding provider name |
| `model` | Model name (e.g., `bge-small-zh-v1.5`) |
| `api_key` | API key for the endpoint (empty for local) |
| `api_base` | Endpoint URL (e.g., `http://127.0.0.1:18200/v1`) |
| `dimension` | Vector dimension (auto-corrected from endpoint) |

### Task 4: Delete Incompatible vectordb Index

> **⚠️ Critical:** If dimensions differ, `rm -rf vectordb/context` is required. Otherwise `EmbeddingRebuildRequiredError` on startup.

If dimension is unchanged, skip this step.

### Task 5: Restart openviking-server Inside the Sandbox

> **⚠️ Pitfall:** `POST /envs/openviking/stop` + `start` re-runs `start.sh`, which overwrites `ov.conf` with TokenHub credentials. **Do not use stop/start.**

Instead:

1. **Kill old process** from host: `kill $PID`, then poll for port 1933 release (up to 10s). If SIGTERM doesn't release the port, escalate to `kill -9`.
2. **Clean up stale lock files**: `.openviking.pid` and vectordb `LOCK` files.
3. **Start new server** via `exec` API with `--max-time 15`:

```bash
curl -s --max-time 15 -X POST http://127.0.0.1:8090/api/v1/envs/openviking/exec \
  -H 'Content-Type: application/json' \
  -d '{"cmd":["bash","-c","nohup /root/runtime/openviking/venv/bin/openviking-server --config /workspace/process_dir/ov.conf > /workspace/process_dir/openviking-server.log 2>&1 & sleep 2 && echo started"]}'
```

### Task 6: Verify

1. **Health check with retry loop** (up to 30s): polls `GET /health` every second until `healthy=true` or timeout
2. **PID change check**: verifies the new server PID differs from the old one (detects port conflict false positives)
3. **Collection dimension check**: reads `collection_meta.json` and confirms `Dimension` matches target
4. **Log error check**: precise grep for `Traceback|ERROR.*Application startup failed|EmbeddingRebuildRequiredError|DataDirectoryLocked` (avoids false positives from "Retrying" info messages)
5. **Rollback on failure**: if health check fails or PID unchanged, restores `ov.conf.bak` and exits with error

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `MODEL_NAME` | Yes | Embedding model name | `bge-small-zh-v1.5` |
| `LLAMA_PORT` | Yes | llama-server port | `18200` |
| `TARGET_DIMENSION` | Yes | Vector dimension (auto-corrected if wrong) | `512` |

```bash
# Usage
bash scripts/switch-embedding-model.sh <model_name> <llama_port> <dimension>
```

## Common Embedding Model Dimensions

| Model | Dimension | Typical Use |
|-------|-----------|-------------|
| `bge-small-zh-v1.5` | 512 | Lightweight Chinese embedding |
| `bge-large-zh-v1.5` | 1024 | High-quality Chinese embedding |
| `bge-small-en-v1.5` | 384 | Lightweight English embedding |
| `bge-base-en-v1.5` | 768 | General-purpose English embedding |
| `Qwen3-Embedding-0.6B` | 1024 | Qwen3 embedding (TokenHub default) |

## Verification

See [references/verification-method.md](references/verification-method.md) for step-by-step checks and end-to-end acceptance criteria.

**Quick verification:**
```bash
# 1. Server healthy
curl -s http://127.0.0.1:1933/health \
  | python3 -c "import sys,json; assert json.load(sys.stdin)['healthy']; print('OK')"

# 2. Collection dimension matches target
python3 -c "import json; d=json.load(open('${SANDBOX_DIR}/data/vectordb/context/collection_meta.json')); assert d['Dimension']==${TARGET_DIMENSION}; print('OK')"

# 3. No errors in log (precise pattern)
grep -ci "Traceback\|Application startup failed\|EmbeddingRebuildRequiredError\|DataDirectoryLocked" \
  "${SANDBOX_DIR}/process_dir/openviking-server.log"
# Expected: 0
```

## Guardrails

See [references/guardrails.md](references/guardrails.md) for the full rules. Key principles:

- **Always run through job-env-manager** — never execute `openviking-server` directly on the host
- **Never use stop/start restart** — `start.sh` overwrites `ov.conf` with TokenHub credentials
- **Validate before modify** — the target endpoint must respond before any config change
- **Rollback on failure** — `ov.conf.bak` is restored if verification fails

## References

| Document | Description |
|----------|-------------|
| [config-reference.md](references/config-reference.md) | ov.conf embedding section field reference |
| [guardrails.md](references/guardrails.md) | Safety rules: sandbox execution, restart sequence, rollback |
| [iam-policies.md](references/iam-policies.md) | Equivalent access controls (no Huawei Cloud IAM needed) |
| [verification-method.md](references/verification-method.md) | Step-by-step verification for each workflow |
| [related-commands.md](references/related-commands.md) | Common job-env-manager and curl commands |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for a successful switch |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting for common failure scenarios |
| [dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [demo/example-input.json](demo/example-input.json) | Example input for the switch workflow |