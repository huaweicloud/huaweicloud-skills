---
name: huawei-cloud-cloudrobo-inference-adapter
description: >
  Guides adapting a VLA model's inference server interface to the CloudRobo
  standard interface/protocol. Use this skill when the user wants to create a
  compatible inference interface protocol for a model, or make a model
  compatible with the CloudRobo client library. Trigger conditions:
  "adapt inference interface", "inference service compatibility",
  "flattened interface", or any request to make a model server compatible
  with an external inference client library.
---

# Inference Interface Adapter

## Overview

This skill guides converting a VLA model's inference interface into an
inference server that uses a **flattened linear format**, adapting to the
CloudRobo client library.

Core idea: the model's own inference interface format differs from the
CloudRobo standard communication format. Instead of modifying the model's
inference logic, add a thin adapter layer that converts between the
flattened linear format and the model's internal format.

### Fixed Protocol Contract

| Item | Convention |
|---|---|
| Transport | WSS (WebSocket over TLS) |
| Certificate | Self-signed certificate generated at runtime (cryptography lib, RSA 3072) |
| Serialization | msgpack (+ numpy extension) |
| Observation format | Flat dot-notation dict |
| Observation keys | `observation.images.{key}` (key derived from the model config, **not hardcoded**), `observation.state` (fixed field), `task` (fixed field) |
| Action response | `{"action": (T, D) float32}`, fixed field |
| Handshake | First frame after connect sends the metadata contract |
| Error | Send `traceback.format_exc()` string, close with `INTERNAL_ERROR` |

**Observation request example:**

```python
{
    "observation.state": np.ndarray,              # (D,) float32
    "observation.images.front": np.ndarray,   # (H, W, 3) uint8
    "observation.images.wrist_left": np.ndarray,    # (H, W, 3) uint8
    "task": str,
}
```

**Action response example:**

```python
{
    "action": np.ndarray,                         # (T, D) float32
    "server_timing": {"infer_ms": ..., "prev_total_ms": ...},
}
```

## Prerequisites

1. **The model's existing inference interface** — a predict/infer method,
   model metadata (action_dim, state_dim, image_keys, action_chunk_size),
   and normalization access (how to get/set denormalization parameters).
2. **Training outputs (for the entry point)** — the final weights from the
   standard layout plus `dataset_statistics.json` (required for action
   denormalization).
3. **Python packages** — `numpy`, `msgpack` (serialization with the
   `__ndarray__`/`__npgeneric__` numpy extension), `websockets` (server +
   client), and `cryptography` (self-signed certificates). `Pillow` is
   optional (loading images from disk in the test client).

## Built-in Scripts

This skill ships two reusable scripts in `scripts/`:

- **`test_client.py`** — a generic WSS test client that auto-discovers the
  server's I/O contract from the handshake metadata. Supports random images
  or loading from disk, single/multiple inferences, and performance
  benchmarking. Used to end-to-end verify any adapter server. Run
  `python scripts/test_client.py` after starting the server.

- **`verify_adapter.py`** — a unit-testing tool for the adapter layer. Tests
  **only through `adapter.infer(obs)`** (no model API assumptions),
  covering observation conversion, image-key validation, state-dimension
  validation, and the metadata property — all without running a server or
  loading a model. Run
  `python scripts/verify_adapter.py --adapter /path/to/adapter.py --class-name MyAdapter`.
  - If the adapter depends on a specific model API (e.g. GR00T's
    `get_action(observation)` with nested observations), pass a model stub
    file (defining a `make_model_stub()` factory function) via
    `--stub-module`:
    `python scripts/verify_adapter.py --adapter gr00t_adapter.py --class-name Gr00tProtocolAdapter --stub-module stub_gr00t.py`

## 4-Component Pattern

Every inference interface adaptation follows the same architecture. The
model's inference logic stays untouched — all protocol-related logic lives
in separate files you create.

```
┌───────────────────────────────────────────────────┐
│  1. Entry point (CLI)                              │
│     - parse args, assemble components              │
├───────────────────────────────────────────────────┤
│  2. Transport server                               │
│     - WSS + msgpack, handshake, request loop,      │
│       error handling                               │
├───────────────────────────────────────────────────┤
│  3. Protocol adapter                               │
│     - convert observations: flat format -> model   │
│       format                                       │
│     - convert actions: model format -> flat format │
├───────────────────────────────────────────────────┤
│  4. Model inference interface (existing, reused)   │
│     - predict / get_action -> actions              │
│     - metadata, normalization                      │
├───────────────────────────────────────────────────┤
│  5. Model + weights (existing, untouched)          │
└───────────────────────────────────────────────────┘
```

Layers 4-5 already exist in the codebase. You create layers 1-3.

### Generality Layering (Reuse vs Customize)

The components differ greatly in generality — **do not blindly copy
templates**:

| Component | Generality | Handling |
|---|---|---|
| Transport server (`server_template.py`) | **High** — WSS/msgpack/handshake/error contract are model-agnostic | can copy and use directly |
| Test client (`scripts/test_client.py`) | **High** — auto-discovers contract from handshake metadata | can copy and use directly |
| Protocol adapter (`adapter_template.py`) | **Low** — the model's observation format/action output varies by model | reference the skeleton only; customize the `_derive_*` methods and conversion logic per model |
| Adapter verification (`verify_adapter.py`) | **Low** — depends on the model API | test `adapter.infer()` via "contract injection", without depending on the model API |

**Key judgment**: if the model's inference interface differs greatly from
the template's assumptions, **rewrite the adapter + write your own
verification**, reusing only the transport server and test client.

## Workflow

### Step 1: Identify the Model's Inference Interface

Find the existing inference interface in the codebase. It usually exposes:

- A predict/infer method — takes an example dict, returns actions
  (typically batched `(B, T, D)`, possibly already denormalized)
- Model metadata — action_dim, state_dim, image_keys, action_chunk_size
- Normalization access — how to get/set denormalization parameters

Record the model's internal format:
- Does the model take a **flat example** (`{"image": ..., "state": ...,
  "lang": ...}`) or **nested observations** (`{"video": {...}, "state":
  {...}, "language": {...}}`)?
- What does the model return? (`(B, T, D)` ndarray? multiple action keys?
  already denormalized?)
- Which image keys does the model expect? **Derive them from the model's
  config or framework, don't hardcode.** Different models use different
  camera names (`cam_high` vs `base_0_rgb` vs `camera_head`).

### Step 2: Create the Protocol Adapter

The adapter is the heart of the adaptation. It converts between the flat
wire format and the model's internal format. Create a class that wraps the
model's inference interface. **See `references/adapter_template.py` for the
full template** — after copying it to the project, you only need to
implement the five `_derive_*` methods (deriving image keys, state dim,
state keys, action dim, and action chunk size from the model
config/metadata). `__init__` calls all of them, so every attribute the
`metadata` property reads is initialized before the handshake.

The adapter exposes two core interfaces:

```python
class ProtocolAdapter:
    def __init__(self, model, **kwargs): ...      # derive and cache the model I/O contract
    def infer(self, obs: dict) -> dict:            # convert -> infer -> convert
        model_input = self._obs_to_example(obs)    # flat example or nested observation
        result = self._model.predict(examples=[model_input])
        return self._result_to_response(result, obs)
    @property
    def metadata(self) -> dict: ...                # handshake contract, see below
```

> The model call inside `infer()` varies by model shape: flat-example
> models use `model.predict(examples=[...])`; nested-observation models
> (e.g. GR00T's `get_action(observation)`) call `model.get_action(model_input)`
> directly. See "Two Shapes of Model-Internal Observations" below for both
> shapes.

**Why hierarchical metadata**: groups related fields together (action,
state, images, task) instead of a flat list. This makes the contract
self-documenting, and clients can parse only the parts they need.

**Observation conversion `_obs_to_example`** — the most critical part. The
wire format uses flat dot-notation keys that directly encode field paths,
avoiding nested ambiguity. The conversion does three things:

1. **Images** — extract from the `observation.images.{key}` prefix, ordered
   by the model's expected image_keys; a missing required image key raises
   `KeyError` immediately.
2. **Language** — `task` → `lang`, using a fallback instruction when
   empty.
3. **State** — `observation.state` → `(1, D)`, validating the dimension
   against `state_dim`; omitted when the model has no state input.

**Action conversion `_result_to_response`** — usually just squeeze the
batch dimension: the model returns `(B, T, D)`, validate batch=1, squeeze
to `(T, D)`, and output `{"action": actions}`.

**Key decisions:**

- **Flat dot-notation wire format** — use flat keys like
  `observation.images.{key}`. It avoids ambiguity and makes the wire
  contract easier to evolve.
- **Image keys derived, not hardcoded** — derive from the model's
  DataConfig (e.g. `video_keys` minus the `video.` prefix), not from a
  non-existent `framework.image_keys`. If unavailable, allow a CLI override
  via `--image_keys`.
- **State validation** — prevents silent garbage output from dimension
  mismatches.
- **No `server_timing` in the adapter** — the transport server adds
  timing because it is per-connection state. The adapter should be testable
  without a server.
- **Batch squeeze** — the model returns `(B, T, D)` but the protocol
  expects `(T, D)`. Always squeeze and validate batch is 1.
- **Model-internal field names configurable** — the action field name in
  the model's return differs by model (`action`, `actions`,
  `pred_actions`, etc.); specify it via the `model_action_key` parameter,
  default `"action"`. The wire field name stays fixed as `action`, never
  affected.
- **Multi-action-key concatenation** — some models (e.g. GR00T) return
  multiple action keys (`{"x": ..., "y": ..., "z": ...}`). Concatenate
  them per the model's action key order with
  `np.concatenate([...], axis=-1)` into `(T, D)`, then output as `action`.

#### Two Shapes of Model-Internal Observations

The template assumes the model takes a **flat example dict**
(`{"image": ..., "state": ..., "lang": ...}`). But many VLA models take
**nested observations** (GR00T's `get_action` needs
`{"video": {...}, "state": {...}, "language": {...}}`). `_obs_to_example`
must implement the matching conversion per the model shape:

| Shape | Model-side input | `_obs_to_example` produces |
|---|---|---|
| Flat example | `{"image": (1,H,W,3), "state": (1,D), "lang": str}` | assemble directly |
| Nested observation | `{"video": {"cam": (B,T,H,W,C)}, "state": {"k": (B,T,D)}, "language": {key: [[str]]}}` | assemble a nested dict from wire flat keys |

The wire side (`observation.images.{key}` / `observation.state` /
`task`) stays **identical for both shapes**; only the adapter-internal
conversion differs.

#### Contract Derivation Reference Table (derive from model config/statistics, don't hardcode)

> ⚠️ **Verification note**: GR00T behavior is measured/verified; the rest
> are **example references** — each framework's config/statistics structure
> changes with version, so **follow the actual model's config structure**,
> don't copy paths blindly.

| Framework/Model | image_keys source | state/action dim source |
|---|---|---|
| example1 | `policy.modality_configs['video'].modality_keys` | `policy.processor.state_action_processor.statistics` (sum of dims per key) |
| example2 | video keys in config | `stats.json` |
| example3 | video items in `meta/modality.json` | `meta/stats.json` / `relative_stats.json` |
| Other | search config for camera key lists | search stats files containing `mean`/`std`/`min`/`max`/`q01` |

> Derivation principle: use the **sum of the actual statistics dims** for
> `state_dim`/`action_dim`, not the padded dims of the model's input layer,
> otherwise normalization index mismatches occur.

### Step 3: Create the Transport Server

The transport server implements the WSS communication loop. It contains no
inference logic — it just moves bytes. **See
`references/server_template.py` for the full template.**

At startup the server **generates a self-signed certificate at runtime**
with the `cryptography` library (RSA 3072 + x509), builds an
`ssl.SSLContext(PROTOCOL_TLS_SERVER)` (TLSv1.2+, restricted to secure
cipher suites), then calls `serve(..., ssl=ssl_context)` to enable TLS. The
certificate files are deleted immediately after being loaded into the
SSLContext.

The fixed shape of the communication loop (5 steps):

1. **Handshake** — send `metadata` as the first frame after connect
2. **Receive observation** — recv + deserialize (no envelope, no routing)
3. **Infer** — call `adapter.infer(obs)`
4. **Attach timing** — write `server_timing` into the response
5. **Send response** — send + serialize

**Key decisions:**

- **`prev_total_time` is a local variable** — reset per connection. The
  first request always has `prev_total_ms == 0`; the second has the total
  time of the first request.
- **No message routing** — a simple recv->infer->send loop. No
  `{type, request_id, payload}` envelope; fundamentally simpler.
- **Error contract fixed** — always send a `traceback.format_exc()`
  string and close with `INTERNAL_ERROR`. Sending another format (e.g. a
  structured dict) makes the client fail to parse.
- **`compression=None, max_size=None`** — the common setting for large
  numpy array payloads. Compression can cause binary-data issues;
  max_size=None allows arbitrarily large messages.

### Step 4: Create the Entry Point

A thin CLI script that assembles the model, adapter, and server:

```python
def main(args):
    # 1. Load the model (existing inference interface)
    model = load_model(args.ckpt_path, device=args.device, **kwargs)

    # 2. Wrap with the protocol adapter
    adapter = ProtocolAdapter(
        model,
        send_state=not args.no_state,
        fallback_instruction=args.fallback_instruction,
        **protocol_specific_kwargs,
    )

    # 3. Log the contract for train/test consistency checks
    contract = adapter.metadata
    logging.warning(
        "Serving on port=%d. Image keys: %s, state_dim: %d, action_dim: %d",
        args.port,
        contract["images"]["keys"],
        contract["state"]["dim"],
        contract["action"]["dim"],
    )

    # 4. Start the transport server
    server = TransportServer(
        adapter, host=args.host, port=args.port, metadata=contract,
    )
    server.serve_forever()
```

**Why log the contract at startup**: if the server's image keys don't match
training, inference will produce garbage output. This catches the most
common deployment error: serving a checkpoint with a mismatched observation
format.

### Step 5: Create the Test Client

Use the built-in **`scripts/test_client.py`** to verify the server
end-to-end. The client auto-discovers the server's I/O contract from the
handshake metadata, so it works with any adapter without code changes. The
client connects via a `wss://` URI and, because the server uses a
self-signed certificate, handshakes with `ssl.CERT_NONE` (skipping
certificate verification).

The test client supports both hierarchical and flat metadata formats. It
verifies:
- Actions shape is `(T, D)` (unbatched)
- First request `server_timing.prev_total_ms == 0`
- Subsequent requests `server_timing.prev_total_ms > 0`

For server-less unit tests of the adapter layer (observation conversion /
image-key validation / state-dimension validation / metadata), use
`scripts/verify_adapter.py`, as described under "Built-in Scripts" above.

## Core Commands

| Command | Purpose |
|---|---|
| `python scripts/verify_adapter.py --adapter /path/to/adapter.py --class-name MyAdapter` | server-less adapter unit tests (observation conversion, image keys, state dim, metadata) |
| `python scripts/verify_adapter.py --adapter gr00t_adapter.py --class-name Gr00tProtocolAdapter --stub-module stub_gr00t.py` | adapter tests with a model stub for model-API-dependent adapters |
| `python scripts/test_client.py --host 127.0.0.1 --port 8000` | smoke test with random images |
| `python scripts/test_client.py --host 127.0.0.1 --port 8000 --image_dir /path/to/images --num_inferences 5 --verbose` | end-to-end test with real images |
| `python scripts/test_client.py --host 127.0.0.1 --port 8000 --benchmark` | performance benchmark |

## Parameter Confirmation

| Parameter | Description |
|---|---|
| `--adapter` / `--class-name` | Adapter Python file path and class name to test (verify_adapter.py) |
| `--stub-module` | Model stub file defining `make_model_stub()` (for model-API-dependent adapters) |
| `--host` / `--port` | Server hostname and port (test_client.py; default `127.0.0.1:8000`) |
| `--image_dir` | Directory of images loaded by key name (falls back to random images) |
| `--image_keys` | Comma-separated camera key names (overrides server metadata) |
| `--prompt` | Language instruction (default "pick up the red cube") |
| `--num_inferences` / `--benchmark` | Number of inference calls; run a performance benchmark |
| `model_action_key` | Model-internal action field name (adapter constructor kwarg, default `"action"`); wire field stays `action` |

## File Structure

New files go under `migrate_to_cloudrobo/deployment/` at the project root.
Per the "Generality Layering": **only build the adapter-layer files
yourself**; reuse the skill's templates/built-in scripts for the protocol
layer (either copy or reference them):

```
migrate_to_cloudrobo/deployment/
├── {protocol}_adapter.py              # adapter (Step 2, customized per model)
├── server_{protocol}.py               # entry point (Step 4, assembly)
└── tools/
    ├── {protocol}_server.py            # transport layer (Step 3, copy server_template.py)
    └── (test_client.py directly references the skill's built-in script)
```

Naming convention: replace `{protocol}` with the protocol name (e.g.
`openpi_adapter.py`, `server_openpi.py`, `openpi_server.py`). The test
client directly uses the built-in `scripts/test_client.py` (auto-discovers
the contract from metadata; no need to write one).

## Common Pitfalls

1. **Hardcoded image keys** — different models use different camera names
   (`cam_high` vs `base_0_rgb` vs `camera_head`). Always derive from the
   model's DataConfig (e.g. `video_keys` minus the `video.` prefix). If the
   framework doesn't expose image keys, allow a CLI override via
   `--image_keys`.

2. **Forgetting the handshake metadata** — the client needs the contract
   (state_dim, image_keys, action_dim) to build valid requests. Without
   metadata, the client can only guess the format, causing silent failures.

3. **Wrong error format** — per the contract, send a
   `traceback.format_exc()` string frame on error. Sending another format
   (e.g. a structured error dict) causes the client to fail parsing.

4. **Batch-dimension confusion** — the model returns `(B, T, D)` but the
   protocol expects `(T, D)`. Always squeeze the batch dimension in the
   adapter and validate batch is 1.

5. **Normalization mismatch** — the model interface should handle
   denormalization. The adapter only passes the correct normalization keys.
   Verify the adapter does not double-denormalize (applying statistics in
   both the model and the adapter).

6. **Missing state validation** — if the model was trained with a state
   input, the adapter should validate that the observation contains state
   with the correct dimension. A missing state key should raise a clear
   error rather than silently producing garbage actions.

7. **Incompatible serializers** — the wire serialization must be identical
   on both ends. The skill ships plain `msgpack` with a custom numpy
   extension (`pack_array`/`unpack_array` encoding `__ndarray__` /
   `__npgeneric__` dicts, same as the reference `test_openpi.py`). If the
   project previously used a different codec (e.g. `msgpack-numpy`), replace
   it on both the server and the client so the bytes stay compatible.

8. **BFloat16 → NumPy conversion** — if the model runs in bf16, output
   tensors cannot be converted to NumPy directly
   (`TypeError: Got unsupported ScalarType BFloat16`). Add `.float()`
   before `.numpy()`:
   ```python
   actions = pred_actions.detach().cpu().float().numpy()  # bf16 → f32 → numpy
   ```

9. **websockets_sync_client API mismatch** — `websockets.sync.client.connect()`
   doesn't accept `ping_interval` or `ping_timeout` (those are async-API
   args). Only pass `compression`, `max_size`, `open_timeout`.

10. **Relative imports in test scripts** — if the test client uses relative
    imports (`from . import <helper module>`), it can't run as a script
    directly. Use absolute imports or `sys.path.insert(0, parent_dir)` for
    standalone execution.

## Reference Documents

- `references/adapter_template.py` — protocol adapter template (Step 2,
  customize the `_derive_*` methods per model)
- `references/server_template.py` — transport server template (Step 3,
  WSS/msgpack/handshake/error contract)
- `scripts/test_client.py` — generic WSS test client (auto-discovers the
  contract from handshake metadata)
- `scripts/verify_adapter.py` — server-less adapter unit-test tool
- `references/iam-policies.md` — authentication & access control (no cloud
  credentials required; local server security notes)
