# Task Config Reference

## TrainTaskDto (create training task request body)

Required fields: `name`, `algorithm`, `spec`, `workspace_id`

| Field | Type | Required | Description | Example |
| ------- | ------ | ---------- | ------------- | --------- |
| `name` | string | Yes | Task name (1-64 chars, CN/EN/digit/-/_) | `my-finetune-v1` |
| `algorithm` | Algorithm | Yes | Algorithm config object | see [Algorithm](#algorithm-field-mapping) |
| `spec` | string | Yes | Resource spec (Ascend format) | `"Ascend: 1 * Ascend-910B \| 24 vCPUs \| 96 GiB"` |
| `workspace_id` | string (UUID) | Yes | Workspace ID | `w1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8` |
| `train_mode` | string enum | No | MODEL_TUNING (finetune) / TRAIN_FROM_SCRATCH (pretrain) | `MODEL_TUNING` |
| `train_method` | string enum | No | SFT / LORA / QLORA / DEEPSPEED | `LORA` |
| `datasets` | array[Dataset] | No | Data input (max 1 item) | `[{"source_type":"CUSTOM_DATASET_ASSET",...}]` |
| `input_models` | array[ModelInfo] | No | Input models (max 1, for finetune base model) | `[{"source_type":"PUBLIC_MODEL_ASSET","model_asset_id":"..."}]` |
| `output_models` | array[ModelInfo] | No | Output models (max 1) | `[{"save_mode":"NEW_MODEL","model_name":"..."}]` |
| `parameters` | string | No | Training params (JSON array string) | `'[{"key":"batch_size","value":"32"}]'` |
| `env` | string | No | Env vars (JSON array string) | `'[{"key":"CUDA_VISIBLE_DEVICES","value":"0"}]'` |
| `worker_num` | int | No | Compute nodes (1-1000, default 1) | `1` |
| `run_user` | int | No | Custom image run user (0-65535, default 1000) | `1000` |
| `description` | string | No | Task description (max 256) | `Training task for ...` |
| `priority` | int | No | Task priority (1-3, default 1) | `1` |
| `cluster_id` | string | No | Target cluster ID | `cluster-123` |
| `inputs` | array[IOConfig] | No | Input config (max 10, for workspace models) | `[{"name":"input-model",...}]` |
| `outputs` | array[IOConfig] | No | Output config (max 5, for workspace models) | `[{"name":"output-model",...}]` |
| `log_path` | string | No | OBS path for training logs (optional, can be omitted) | `"obs://bucket/train-logs/<task-name>/"` |
| `enable_jupyter` | boolean | No | Enable JupyterLab access during training (optional, **DEDICATED pools only** — SHARED/public pools do not support JupyterLab) | `true` |

## IOConfig fields (for workspace model and custom algorithm scenarios)

When using a workspace model (`CUSTOM_MODEL_ASSET`) for MODEL_TUNING, or a workspace/custom algorithm
for TRAIN_FROM_SCRATCH, top-level `inputs` and `outputs` arrays may be required.

### inputs structure

`inputs` support **4 `source_type` values** mixed together in the same array:

```json
[
  {
    "name": "<input-name>",
    "url_path": "obs://bucket/path/",
    "source_type": "PUBLIC_DATASET_ASSET",
    "asset_id": "<dataset-asset-uuid>",
    "asset_name": "<dataset-name>",
    "version_id": "<version-uuid>",
    "access_method": "env",
    "local_dir": "<name>=/home/ma-user/cloudrobo/inputs/<name>_0"
  },
  {
    "name": "<obs-input-name>",
    "url_path": "obs://bucket/obs-data/",
    "source_type": "OBS",
    "access_method": "parameter",
    "local_dir": "--<name>=/home/ma-user/cloudrobo/inputs/<name>_0"
  },
  {
    "name": "<workspace-dataset-name>",
    "url_path": "obs://bucket/path/",
    "source_type": "CUSTOM_DATASET_ASSET",
    "asset_id": "<dataset-asset-uuid>",
    "asset_name": "<dataset-name>",
    "version_id": "<version-uuid>",
    "access_method": "env",
    "local_dir": "<name>=/home/ma-user/cloudrobo/inputs/<name>_0"
  },
  {
    "name": "<workspace-model-name>",
    "url_path": "obs://bucket/path/",
    "source_type": "CUSTOM_MODEL_ASSET",
    "asset_id": "<model-asset-uuid>",
    "asset_name": "<model-name>",
    "version_id": "<version-uuid>",
    "version_name": "<version-name>",
    "access_method": "env",
    "local_dir": "<name>=/home/ma-user/cloudrobo/inputs/<name>_0"
  }
]
```

| Field           | Type | Description |
|-----------------| ---- | ----------- |
| `name`          | string | Input name |
| `url_path`      | string | OBS path for the input |
| `source_type`   | string enum | `PUBLIC_DATASET_ASSET` / `OBS` / `CUSTOM_DATASET_ASSET` / `CUSTOM_MODEL_ASSET` |
| `asset_id`      | string | Asset ID (for PUBLIC_DATASET_ASSET, CUSTOM_DATASET_ASSET, CUSTOM_MODEL_ASSET — NOT needed for OBS) |
| `asset_name`    | string | Asset name (same as above) |
| `version_id`    | string | Version ID (same as above; CUSTOM_MODEL_ASSET also has `version_name`) |
| `version_name`  | string | Version name (only for CUSTOM_MODEL_ASSET) |
| `access_method` | string enum | `"env"` (环境变量) or `"parameter"` (超参) |
| `local_dir`     | string | Container mount path. env: `"<name>=<container-path>"`, parameter: `"--<name>=<container-path>"` |

### outputs structure

`outputs` are simpler — no `source_type` field, always OBS path:

```json
[
  {
    "name": "<output-name>",
    "url_path": "obs://bucket/output-path/",
    "access_method": "parameter",
    "local_dir": "--<name>=/home/ma-user/cloudrobo/outputs/<name>_0"
  }
]
```

| Field           | Type | Description |
|-----------------| ---- | ----------- |
| `name`          | string | Output name |
| `url_path`      | string | OBS path for the output |
| `access_method` | string enum | `"env"` (环境变量) or `"parameter"` (超参) |
| `local_dir`     | string | Container mount path. env: `"<name>=<container-path>"`, parameter: `"--<name>=<container-path>"` |

> `inputs`/`outputs` are NOT needed for Gallery model (`PUBLIC_MODEL_ASSET`) MODEL_TUNING scenarios
> or Gallery algorithm (`PUBLIC_ALGORITHM_ASSET`) TRAIN_FROM_SCRATCH scenarios. They are required
> for workspace models, workspace algorithms, and custom config algorithms.

## spec resource format string

`spec` is a **string** (not a JSON object) matching the regex:

```text
^Ascend:\s*\d+\s*\*\s*[A-Za-z0-9-]{1,128}\s*\|\s*\d+\s*vCPUs\s*\|\s*\d+\s*GiB$
```

Format: `Ascend: <count> * <model> | <vCPUs> vCPUs | <memory> GiB`

Examples:

```text
"Ascend: 1 * Ascend-910B | 24 vCPUs | 96 GiB"
"Ascend: 2 * Ascend-910B | 48 vCPUs | 192 GiB"
"Ascend: 8 * Ascend-910A | 192 vCPUs | 768 GiB"
```

> **Important**: The legacy skill documented `spec` as `{"flavor":"gpu.1","epochs":10}` — this is **incorrect**. The API field is a string in the Ascend format above. The CLI `--spec` accepts JSON for convenience but the canonical API field is the string.

## Algorithm field mapping

The `algorithm` object format differs by train_mode and model/algorithm source:

### MODEL_TUNING — Gallery model (具身广场模型)

Only 2 fields needed. The algorithm is resolved from the model's `actions` array:

```json
{
  "algorithm_asset_id": "<from model action.algorithm.asset_id>",
  "algorithm_version_id": "<from model action.algorithm.version_id>"
}
```

### MODEL_TUNING — Workspace model (空间资产模型)

Full algorithm config required, with `algorithm_source_type: "CUSTOM_ALGORITHM_ASSET"`:

```json
{
  "algorithm_asset_id": "<algo-asset-id>",
  "algorithm_version_id": "<algo-version-id>",
  "algorithm_source_type": "CUSTOM_ALGORITHM_ASSET",
  "engine": {
    "image_url": "<image-url>"
  },
  "image_asset_id": "<image-asset-id>",
  "image_version_id": "<image-version-id>",
  "code_dir": "<obs://code-dir>",
  "command": "<start-command>",
  "local_code_dir": "<local-path>"
}
```

> **Note**: `image_url` goes inside `engine.image_url`. `image_asset_id` and `image_version_id` are
> **top-level** fields, not inside `engine`. Workspace model also requires top-level `inputs` and
> `outputs` arrays (see IOConfig fields above).

### TRAIN_FROM_SCRATCH — Gallery algorithm (预制算法)

Simplified format (3 fields). The backend auto-resolves `image_url`, `command`, `engine` from the
algorithm asset:

```json
{
  "algorithm_asset_id": "<algo-asset-id>",
  "algorithm_version_id": "<algo-version-id>",
  "algorithm_source_type": "PUBLIC_ALGORITHM_ASSET"
}
```

**Do NOT include** `image_url`, `command`, `engine`, `algorithm_asset_name`, `boot_file`, or
`hidden_main_info` — the backend auto-resolves these from the algorithm asset.

### TRAIN_FROM_SCRATCH — Workspace algorithm (空间资产算法)

Full config (9 fields), with `algorithm_source_type: "CUSTOM_ALGORITHM_ASSET"`:

```json
{
  "engine": {
    "image_url": "<image-url>"
  },
  "image_asset_id": "<image-asset-id>",
  "image_version_id": "<image-version-id>",
  "code_dir": "<obs://code-dir>",
  "command": "<start-command>",
  "local_code_dir": "<local-path>",
  "algorithm_asset_id": "<algo-asset-id>",
  "algorithm_version_id": "<algo-version-id>",
  "algorithm_source_type": "CUSTOM_ALGORITHM_ASSET"
}
```

> **Note**: `image_url` goes inside `engine.image_url`. `image_asset_id` and `image_version_id` are
> **top-level** fields. May also require top-level `inputs` and `outputs` arrays.

### TRAIN_FROM_SCRATCH — Custom config (现配置算法)

For users bringing their own code/image — no preset algorithm. 5 fields, with
`algorithm_source_type: "TEMP_CONFIGURE_ALGORITHM"`:

```json
{
  "image_asset_id": "<image-asset-id>",
  "image_version_id": "<image-version-id>",
  "command": "<start-command>",
  "local_code_dir": "<local-path>",
  "algorithm_source_type": "TEMP_CONFIGURE_ALGORITHM"
}
```

> **Note**: No `algorithm_asset_id`/`algorithm_version_id` (no preset algorithm selected). No
> `engine.image_url` (image comes from `image_asset_id`/`image_version_id`). No `code_dir` (no OBS
> source code path). May require top-level `inputs` and `outputs` arrays.

### algorithm_source_type enum

| Value | Description | Use case |
| ----- | ----------- | -------- |
| `PUBLIC_ALGORITHM_ASSET` | Gallery algorithm (预制算法) | TRAIN_FROM_SCRATCH with preset algorithm from 具身广场 |
| `CUSTOM_ALGORITHM_ASSET` | Workspace algorithm (空间资产算法) | TRAIN_FROM_SCRATCH or MODEL_TUNING with workspace algorithm |
| `TEMP_CONFIGURE_ALGORITHM` | Custom config (现配置算法) | TRAIN_FROM_SCRATCH with user's own code/image, no preset algorithm |

> **Note**: Algorithm info is dynamically fetched; do not hardcode. For MODEL_TUNING Gallery models,
> the algorithm comes from the model's `actions` array (each action has
> `algorithm: {asset_id, version_id}`). For MODEL_TUNING workspace models, the algorithm must be
> fully configured with engine, image, code_dir, command, etc.

## Dataset fields

| Field | Type | Description | Example |
| ------- | ------ | ------------- | --------- |
| `source_type` | string enum | `PUBLIC_DATASET_ASSET` (Gallery) / `CUSTOM_DATASET_ASSET` (Workspace) / `OBS` | `PUBLIC_DATASET_ASSET` |
| `dataset_asset_id` | string | Dataset asset ID (when source_type=PUBLIC_DATASET_ASSET or CUSTOM_DATASET_ASSET) | `e5f6a7b8-...` |
| `dataset_name` | string | Dataset name | `my-dataset` |
| `version_id` | string | Dataset version ID | `f6a7b8c9-...` |
| `version_name` | string | Dataset version name | `v1.0.0` |
| `url_path` | string | Dataset URL (when source_type=OBS, only field needed besides source_type) | `obs://bucket/dataset/` |

**Dataset source_type mapping:**

| Source | source_type | Required fields |
| ------ | ----------- | --------------- |
| Gallery (具身广场) | `PUBLIC_DATASET_ASSET` | `source_type` + `dataset_asset_id` + `version_id` + `dataset_name` |
| Workspace (空间资产) | `CUSTOM_DATASET_ASSET` | `source_type` + `dataset_asset_id` + `version_id` + `dataset_name` |
| OBS (对象存储) | `OBS` | `source_type` + `url_path` only |

> **Note**: Legacy docs used `DATASET` as source_type — this is **incorrect**. Use `CUSTOM_DATASET_ASSET` for workspace datasets.

## ModelInfo fields

| Field | Type | Description |
| ------- | ------ | ------------- |
| `save_mode` | string enum | Output model: `NEW_MODEL` / `NEW_VERSION` / `NOT_SAVE` |
| `model_asset_id` | string | Model ID (required for NEW_VERSION; null/omit for NEW_MODEL) |
| `model_name` | string | Model name (required for NEW_MODEL, NEW_VERSION) |
| `version_id` | string | Model version ID (for NEW_VERSION, the existing model's version) |
| `version_name` | string | Model version name (required for NEW_MODEL, NEW_VERSION) |
| `model_type` | string | Model type e.g. `PyTorch` (required for NEW_MODEL, NEW_VERSION) |
| `url_path` | string | Model URL path |
| `strict` | boolean | Whether to strictly check model name uniqueness. Default `false` (frontend default). Set `true` to enforce uniqueness |
| `skills` | array | Skills list (default `[]`) |

**output_models save_mode formats:**

| save_mode | Required fields | Notes |
| --------- | --------------- | ----- |
| `NEW_MODEL` | `save_mode` + `model_name` + `version_name` + `model_type` + `strict` | Creates new model asset. `model_asset_id`/`version_id` null/omit |
| `NEW_VERSION` | `save_mode` + `model_asset_id` + `model_name` + `version_id` + `version_name` + `model_type` | Adds version to existing model |
| `NOT_SAVE` | `save_mode` only | No output model saved |

> **Note**: Legacy docs used `new: true/false` boolean — this is **incorrect**. Use `save_mode` enum instead.
> For TRAIN_FROM_SCRATCH, `strict` and `skills` can be omitted (backend auto-generates), but for
> MODEL_TUNING, `strict: false` is the frontend default and should be included.

## train_mode and train_method

| train_mode | Description | Requires |
| ----------- | ------------- | ---------- |
| `MODEL_TUNING` | Fine-tuning (finetune) | Base model (input_models or --base-model-asset-id) |
| `TRAIN_FROM_SCRATCH` | Pretraining (pretrain) | Full algorithm config |

| train_method | Description |
| ------------- | ------------- |
| `SFT` | Supervised fine-tuning |
| `LORA` | LoRA fine-tuning |
| `QLORA` | QLoRA fine-tuning |
| `DEEPSPEED` | DeepSpeed training |

> **Important**: `train_method` is uppercase enum. The legacy skill used lowercase `lora` — this is **incorrect**.

## Status enum (16 states)

| Status | Category | Description |
| -------- | ---------- | ------------- |
| `DRAFT` | Non-terminal (draft) | Draft saved, not executing |
| `CREATING` | Non-terminal (active) | CREATING to cluster |
| `WAITING` | Non-terminal (active) | Waiting for resources |
| `RUNNING` | Non-terminal (active) | Training in progress |
| `STOPPING` | Non-terminal (active) | Stop in progress |
| `DELETING` | Non-terminal (active) | Deletion in progress |
| `FINISHED` | Terminal (success) | Training completed |
| `FAILED` | Terminal (failure) | Failed |
| `RUN_FAILED` | Terminal (failure) | Run failed |
| `CREATE_FAILED` | Terminal (failure) | Submit failed |
| `STOPPED` | Terminal (stopped) | Stopped |
| `STOP_FAILED` | Terminal (failure) | Stop failed |
| `DELETED` | Terminal (deleted) | Deleted |
| `DELETE_FAILED` | Terminal (failure) | Delete failed |
| `NOT_EXIST` | Terminal | Does not exist |
| `ABNORMAL` | Terminal (failure) | Abnormal |
| `UNKNOWN` | Unknown | Unknown state |

**Polling rule**: Continue polling while status is non-terminal (DRAFT, CREATING, WAITING, RUNNING, STOPPING, DELETING, UNKNOWN). Stop on all others.

## Execution stages

Main stages (StageInfoWithSub), `stage_order` 1-4:

| stage_order | name | Description |
| ------------- | ------ | ------------- |
| 1 | `SCHEDULING` | Scheduling resources |
| 2 | `PREPARING` | Preparing environment |
| 3 | `RUNNING` | Training running |
| 4 | `END` | Training ended |

Each stage has: `job_id`, `en_message`, `zh_message`, `start_time`, `end_time`, `sub_stages[]`.

Sub-stages have: `name`, `en_message`, `zh_message`, `create_time`.

## Events

Event level enum:

| Level | Description |
| ------- | ------------- |
| `Info` | Information |
| `Warning` | Warning |
| `Error` | Error |

> Note: the v1 API uses `Info`/`Warning`/`Error` (capitalized), not the legacy `INFO`/`WARNING`/`ERROR`.

Event fields: `time` (ISO 8601 +08:00), `level`, `message`, `source`.

## Draft submit flow

1. **Save draft**: `save-draft --config '<DraftTrainTaskDto json>'`
   - DraftTrainTaskDto required: `name`, `workspace_id` (algorithm/spec NOT required for draft)
   - Returns task_id, task status = `DRAFT`
   - SimRL: `save-draft --sim-rl --config '<json>'` → `create_sim_rl_task_draft`
2. **Resubmit**: `restart-task --task-id <draft-id>`
   - Restart endpoint: POST /train-tasks/{id}/restart with optional full TrainTaskDto body
   - Semantics: "编辑并重新提交训练任务" (edit and resubmit)
   - **CLI**: `restart-task --task-id <id>` resubmits existing config; add `--config '<json>'` or `--config-file <path>` to override fields
   - **SDK**: `restart_train_task(task_id, req=None)` accepts partial overrides (merged with original task config)
   - SimRL: `restart-task --sim-rl --task-id <id>` → `restart_sim_rl_task(task_id, req=None, task_detail=None)`
3. After resubmit: DRAFT → CREATING → WAITING → RUNNING → terminal

## Three-layer coverage matrix

SDK (33 methods: 12 `train_*` + 15 `sim_rl_*` + 6 unprefixed) / CLI (20 commands) coverage:

### Regular training tasks

| Operation | SDK method | CLI command | API path |
| ----------- | ------------ | ------------- | ---------- |
| create_train_task | `create_train_task(req)` | `create-task` | `POST /v1/training/train-tasks` |
| list_train_tasks | `list_train_tasks(**params)` | `list-tasks` | `GET /v1/training/train-tasks` |
| show_train_task | `show_train_task(task_id, **params)` | `show-task` | `GET /v1/training/train-tasks/{task_id}` |
| update_train_task | `update_train_task(task_id, req)` | `update-task` | `PATCH /v1/training/train-tasks/{task_id}` |
| batch_delete_train_tasks | `batch_delete_train_tasks(execution_ids)` | `delete-tasks` | `POST /v1/training/train-tasks/batch-delete` |
| count_train_tasks_by_status | `count_train_tasks_by_status(workspace_id, user_id)` | `stats` | `GET /v1/training/train-tasks/stats` |
| resume_train_task | `resume_train_task(task_id)` | `resume-task` | `POST /v1/training/train-tasks/{task_id}/resume` |
| stop_train_task | `stop_train_task(task_id)` | `stop-task` | `POST /v1/training/train-tasks/{task_id}/stop` |
| restart_train_task | `restart_train_task(task_id, req=None)` | `restart-task` | `POST /v1/training/train-tasks/{task_id}/restart` |
| save_draft | `save_draft(req)` | `save-draft` | `POST /v1/training/train-tasks/draft` |
| list_train_stages | `list_train_stages(task_id)` | `get-stages` | `GET /v1/training/train-tasks/{task_id}/stages` |
| show_resource_usage | `show_resource_usage(task_id, metric, start, end, **params)` | `get-resource-usage` | `GET /v1/training/train-tasks/{task_id}/resource-usage` |
| list_observations | `list_observations(task_id, **params)` | (SDK only) | `GET /v1/training/train-tasks/{task_id}/observability` |
| get_log_signed_url | `get_log_signed_url(task_id, file_source, file_name, **params)` | `get-signed-url` | `GET /v1/training/train-tasks/{task_id}/observability/signed-url` |
| get_log_content | `get_log_content(task_id, **params)` | `get-logs` | `GET /v1/training/train-tasks/{task_id}/observability/content` |
| list_events | `list_events(task_id, start_time, end_time, **params)` | `get-events` | `GET /v1/training/train-tasks/{task_id}/events` |
| list_train_checkpoints | `list_train_checkpoints(task_id, **params)` | `list-checkpoints` | `GET /v1/training/train-tasks/{task_id}/checkpoints` |
| register_train_checkpoint | `register_train_checkpoint(task_id, req)` | `register-checkpoint` | `POST /v1/training/train-tasks/{task_id}/checkpoints/register` |

### Simulation reinforcement learning (SimRL) tasks

| Operation | SDK method | CLI command | API path |
| ----------- | ------------ | ------------- | ---------- |
| count_sim_rl_tasks_by_status | `count_sim_rl_tasks_by_status(workspace_id, user_id)` | `stats --sim-rl` | `GET /v1/training/rl-tasks/simulation/stats` |
| list_sim_rl_tasks | `list_sim_rl_tasks(**params)` | `list-tasks --sim-rl` | `GET /v1/training/rl-tasks/simulation` |
| create_sim_rl_task | `create_sim_rl_task(req)` | `create-task --sim-rl` | `POST /v1/training/rl-tasks/simulation` |
| create_sim_rl_task_draft | `create_sim_rl_task_draft(req)` | `save-draft --sim-rl` | `POST /v1/training/rl-tasks/simulation/draft` |
| show_sim_rl_task | `show_sim_rl_task(task_id)` | `show-task --sim-rl` | `GET /v1/training/rl-tasks/simulation/{task_id}` |
| update_sim_rl_task | `update_sim_rl_task(task_id, req)` | `update-task --sim-rl` | `PATCH /v1/training/rl-tasks/simulation/{task_id}` |
| delete_sim_rl_task | `delete_sim_rl_task(task_id)` | `delete-tasks --sim-rl` | `DELETE /v1/training/rl-tasks/simulation/{task_id}` |
| stop_sim_rl_task | `stop_sim_rl_task(task_id)` | `stop-task --sim-rl` | `POST /v1/training/rl-tasks/simulation/{task_id}/stop` |
| copy_sim_rl_task | `copy_sim_rl_task(task_id, req=None, task_detail=None)` | `clone-task` | `POST /v1/training/rl-tasks/simulation/{task_id}/copy` |
| restart_sim_rl_task | `restart_sim_rl_task(task_id, req=None, workspace_id=None, task_detail=None)` | `restart-task --sim-rl` | `POST /v1/training/rl-tasks/simulation/{task_id}/restart` |
| show_sim_rl_task_resource_usage | `show_sim_rl_task_resource_usage(task_id, metric, start, end, **params)` | `get-resource-usage --sim-rl` | `GET /v1/training/rl-tasks/simulation/{task_id}/resource-usage` |
| list_sim_rl_task_events | `list_sim_rl_task_events(task_id, start_time, end_time, **params)` | `get-events --sim-rl` | `GET /v1/training/rl-tasks/simulation/{task_id}/events` |
| list_sim_rl_task_observations | `list_sim_rl_task_observations(task_id, **params)` | (SDK only) | `GET /v1/training/rl-tasks/simulation/{task_id}/observability` |
| show_sim_rl_task_observations_content | `show_sim_rl_task_observations_content(task_id, **params)` | `get-logs --sim-rl` | `GET /v1/training/rl-tasks/simulation/{task_id}/observability/content` |
| show_sim_rl_task_observations_signed_url | `show_sim_rl_task_observations_signed_url(task_id, file_source, file_name, **params)` | `get-signed-url --sim-rl` | `GET /v1/training/rl-tasks/simulation/{task_id}/observability/signed-url` |

> **No resume/checkpoints for SimRL**: `resume-task`, `list-checkpoints`, and `register-checkpoint` are train-only; `--sim-rl` is not accepted on these commands.

**Key notes:**

- `list_observations` / `list_sim_rl_task_observations`: SDK-only (no dedicated CLI command; CLI `get-logs` covers content)
- `resume_train_task`: train-only (SimRL has no resume endpoint)
- **SimRL has no stages endpoint/method** — `get-stages` is train-only (`list_train_stages`); with `--sim-rl` it is not available
- `--sim-rl` flag present on 15 commands; absent on `resume-task`

## Task creation via create-task

There are no dedicated `finetune`/`pretrain` subcommands — all creation goes through
`create-task --config '<json>'` (or `--config-file`), with mode/method/model/dataset/spec
expressed in the JSON body:

- **MODEL_TUNING** (fine-tuning): `train_mode: "MODEL_TUNING"`, `train_method`
  (FFT/SFT/LORA/QLORA/DEEPSPEED), `input_models: [{"model_asset_id": ...}]`,
  `datasets: [{"dataset_asset_id": ...}]`, `spec` (string)
- **TRAIN_FROM_SCRATCH** (pre-training): `train_mode: "TRAIN_FROM_SCRATCH"`, `algorithm`
  (object), `spec` (string), `datasets` (array)

For direct SDK usage, construct the full TrainTaskDto per the schema above.

## SimRL Task Config Schema

SimRL (仿真强化学习) tasks use a **different request schema** from regular training tasks.

### Fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `name` | string | Yes | Task name |
| `workspace_id` | string | Yes | Workspace ID |
| `description` | string | No | Task description |
| `config_mode` | string | Yes | `SIMPLE` (快速配置) or `ADVANCED` (用户自定义YAML) |
| `task_set` | string | Yes | Task set name from model actions (e.g. `LIBERO_SPATIAL`). Applies to both SIMPLE and ADVANCED modes |
| `simple_params` | string (JSON) | Yes (SIMPLE) | JSON string of hyperparameter objects: `[{key, value, desc}]` |
| `rl_config_content` | string | Yes (ADVANCED) | YAML config content for ADVANCED mode. Source: `ext_metadata.yaml_config` from task set detail |
| `input_models` | array | Yes | Input model, see below. Supports both Gallery and Workspace models |
| `output_models` | array | Yes | Output model spec, see below. Supports NEW_MODEL and NEW_VERSION |
| `spec` | string | Yes | Resource spec, e.g. `ASCEND: 1 * SNT9B2 \| 24 vCPUs \| 192 GiB` (uppercase `ASCEND`) |
| `cluster_id` | string | Yes | Resource pool ID with `pool-` prefix (from `cloudrobo resource list-pools`) |
| `worker_num` | int | Yes | Number of workers (typically 1) |
| `enable_jupyter` | boolean | No | Enable JupyterLab access. **DEDICATED pools only** — SHARED/public pools must set `false` |

### input_models structure

```json
[{
    "source_type": "PUBLIC_MODEL_ASSET",  // or "CUSTOM_MODEL_ASSET" for workspace models
    "model_asset_id": "<asset-id>",
    "model_name": "<model-name>",
    "version_id": "<version-id>",
    "version_name": "<version-name>"
}]
```

**Model source:**

| source_type | Source | Discovery |
| ----------- | ------ | --------- |
| `PUBLIC_MODEL_ASSET` | 具身广场 (Gallery) | `cloudrobo asset list-publication-assets --type model` |
| `CUSTOM_MODEL_ASSET` | 空间资产 (Workspace) | `cloudrobo asset list-assets --type model` |

> The `actions` field on the model version detail contains available task sets (e.g., `LIBERO_SPATIAL`).
> Query version detail via `GET /v1/assets/{asset_id}/versions/{version_id}` to get actions.

### output_models structure

**NEW_MODEL (创建新模型):**
```json
[{
    "save_mode": "NEW_MODEL",
    "model_name": "<output-model-name>",
    "version_name": "0.0.1",
    "model_type": "vla",
    "model_asset_id": null,
    "version_id": null,
    "strict": false,
    "skills": []
}]
```

**NEW_VERSION (已有模型的新版本):**
```json
[{
    "save_mode": "NEW_VERSION",
    "model_name": "<existing-model-name>",
    "version_name": "<new-version-name>",
    "model_type": "vla",
    "model_asset_id": "<existing-model-asset-id>",
    "version_id": "",
    "strict": false,
    "skills": [{"name": "<skill-name>", "prompt": "<skill-prompt>"}]
}]
```

> **NEW_MODEL**: `model_asset_id` and `version_id` are `null`. Creates a new model asset.
> **NEW_VERSION**: `model_asset_id` is the existing model's asset ID, `version_id` is empty string `""` (not null). Adds a new version to an existing model.
> `skills` array can contain skill definitions with `name` and `prompt` fields.
> `strict: false` is the frontend default for SimRL.

### simple_params (SIMPLE mode)

Standard PPO hyperparameters:

| Key | Default | Description |
| --- | ------- | ----------- |
| `RL_ALGO` | `ppo` | Reinforcement learning algorithm (ppo / gpro) |
| `MAX_EPOCHS` | `100` | Total training epochs |
| `SAVE_INTERVAL` | `20` | Checkpoint save interval |
| `TOTAL_NUM_TRAIN_ENVS` | `16` | Number of training environments |
| `EVAL_NUM_TRAIN_ENVS` | `500` | Number of evaluation environments |
| `MICRO_BATCH_SIZE` | `64` | Micro batch size |
| `GLOBAL_BATCH_SIZE` | `256` | Global batch size |
| `ROLLOUT_EPOCH` | `2` | Rollout epochs |

> `simple_params` is a **JSON string** (not an array). Use `json.dumps([...])`
> to serialize the parameter list.

### SimRL vs Train task key differences

| Aspect | Train task | SimRL task |
| ------ | ---------- | ---------- |
| Config | `algorithm` + `parameters` | `config_mode` + `task_set` + `simple_params`/`rl_config_content` |
| Input | `datasets` + `input_models` | `input_models` only (Gallery `PUBLIC_MODEL_ASSET` or Workspace `CUSTOM_MODEL_ASSET`) |
| Resource | `cluster_id` optional | `cluster_id` required |
| JupyterLab | `enable_jupyter` optional | `enable_jupyter` — DEDICATED pools only |
| spec format | `Ascend: ...` (mixed case) | `ASCEND: ...` (uppercase) |
| Output | `output_models` | `output_models` with `skills` array |
| Lifecycle | Has `resume` | No `resume` |
| Clone | `copy_train_task` removed | `copy_sim_rl_task` (clone-task --sim-rl) |
