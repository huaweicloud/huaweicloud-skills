# ov.conf Embedding Configuration Reference

## Full ov.conf Structure (Relevant Sections)

```json
{
  "storage": {
    "workspace": "/workspace/data"
  },
  "embedding": {
    "dense": {
      "provider": "openai",
      "model": "bge-small-zh-v1.5",
      "api_key": "not-needed",
      "api_base": "http://127.0.0.1:18200/v1",
      "dimension": 512,
      "batch_size": 64
    },
    "max_concurrent": 3,
    "max_retries": 5
  },
  "vlm": {
    "provider": "openai",
    "model": "glm-5.2",
    "api_base": "https://tokenhub.developer.huaweicloud.com/v2",
    "temperature": 0.0,
    "max_retries": 5,
    "api_key": "..."
  },
  "server": {
    "host": "127.0.0.1",
    "port": 1933
  }
}
```

## embedding.dense Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Embedding provider type. Use `"openai"` for any OpenAI-compatible endpoint (including llama-server). |
| `model` | string | Yes | Model name as recognized by the endpoint. For llama-server, this must match the `--model` flag or the model filename (without `.gguf`). |
| `api_key` | string | Yes | API key for authentication. For local llama-server, use any non-empty string (e.g. `"not-needed"`). |
| `api_base` | string | Yes | Base URL of the embedding API. For llama-server: `http://127.0.0.1:{port}/v1`. For TokenHub: `https://tokenhub.developer.huaweicloud.com/v2`. |
| `dimension` | integer | Yes | Vector dimension of the model. **Must match the actual model output dimension**, otherwise vector operations will fail. |
| `batch_size` | integer | No | Number of texts to embed in a single API call. Default 64. Reduce if the embedding server has memory constraints. |

## embedding Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_concurrent` | integer | 3 | Maximum concurrent embedding API calls. |
| `max_retries` | integer | 5 | Maximum retries on embedding API failure. |

## server Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `127.0.0.1` | Server bind address. |
| `port` | integer | 1933 | Server bind port. |

## Dimension Change Impact

When `dimension` changes:

| Component | Affected | Action Required |
|-----------|----------|----------------|
| `vectordb/context/collection_meta.json` | Yes — stores `Dimension` field | Delete (will be recreated on server start) |
| `vectordb/context/index/default/index_meta.json` | Yes — stores `VectorIndex.Dimension` | Delete (will be recreated) |
| `vectordb/context/store/` | Yes — RocksDB store with old-dimension vectors | Delete (will be recreated) |
| `vectordb/context/index/default/versions/` | Yes — index version data | Delete (will be recreated) |
| `viking/` metadata | No — user/session metadata is dimension-independent | Preserve |

**Simplest approach:** `rm -rf ${SANDBOX_DIR}/data/vectordb/context` — deletes everything under context, server recreates from scratch.

## start.sh Override Behavior

The `start.sh` script in the sandbox's `process_dir/` has logic that can overwrite `ov.conf` on environment start/restart:

| Condition | What gets overwritten |
|-----------|---------------------|
| `JOB_ENV_MODEL_API_KEY` env var is set | `embedding.dense.api_key`, `embedding.dense.api_base`, `vlm.api_key`, `vlm.api_base` |
| `AK` + `SK` env vars are set (no `JOB_ENV_MODEL_API_KEY`) | Fetches from TokenHub: `embedding.dense.api_key`, `embedding.dense.api_base`, `embedding.dense.model`, `vlm.api_key`, `vlm.api_base` |
| Neither set | **ov.conf preserved as-is** |

To check what env vars the openviking environment has:

```bash
curl -s http://127.0.0.1:8090/api/v1/env-templates/openviking | python3 -m json.tool
```
