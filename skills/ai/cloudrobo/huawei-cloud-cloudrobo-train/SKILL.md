---
name: huawei-cloud-cloudrobo-train
description: >
  Manage CloudRobo model training tasks and simulation reinforcement learning (SimRL) tasks —
  create pretrain (TRAIN_FROM_SCRATCH) and finetune (MODEL_TUNING) tasks with FFT/SFT/LORA/QLORA/DEEPSPEED
  methods; manage the full task lifecycle (create/read/update/delete/stop/restart/resume/draft);
  save and resubmit draft configs; count tasks by status; monitor execution stages, resource usage,
  training logs, signed URLs, and events; diagnose failures. SimRL tasks (simulation reinforcement
  learning) are managed via the same CLI with a --sim-rl flag and cover the same CRUD + lifecycle +
  monitoring surface (except resume, which is train-only).
  Triggers include: model training, fine-tuning, pretraining, training task, training stages,
  resource usage, training logs, training events, draft task, restart training,
  stop training, resume training, task stats, simulation reinforcement learning, SimRL, 仿真强化学习,
  模型训练, 模型微调, 训练任务, 训练阶段, 资源使用, 训练日志, 训练事件, 草稿任务,
  重启训练, 克隆训练, 停止训练, 续训训练, 任务统计.
tags:
  - huawei-cloud-cloudrobo
  - train
  - model-training
  - fine-tuning
  - pretraining
  - task-management
  - resource-monitoring
  - failure-diagnosis
  - simulation-reinforcement-learning
  - sim-rl
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview

Manages the full lifecycle of CloudRobo model training tasks and SimRL tasks. Two training modes
(MODEL_TUNING / TRAIN_FROM_SCRATCH), five methods (FFT/SFT/LORA/QLORA/DEEPSPEED). Covers creation,
monitoring, diagnosis, drafts, stats, resume, and pipeline orchestration.

**Two task surfaces (switchable via `--sim-rl`):**

| Surface | API prefix | CLI switch | SDK methods | Resume |
| ------- | ---------- | ---------- | ----------- | ------ |
| Regular training | `/v1/training/train-tasks` | (default) | 19 `train_*` | Yes |
| SimRL | `/v1/training/rl-tasks/simulation` | `--sim-rl` | 16 `sim_rl_*` | No |

**Scenarios:** Fine-tuning, pretraining, simulation RL, draft save/resubmit, monitoring (stages/
resource/events), failure diagnosis, stats. Training runs for hours/days; poll at 30-60s intervals.

```text
Agent → CLI (`cloudrobo train <command> [--sim-rl]`) or SDK (`TrainClient`)
      → cloudrobo-service (REST API)
```

All operations target `cloudrobo-service` and require a `workspace_id`. Model/dataset discovery
calls `cloudrobo-asset-manager` via `cloudrobo asset`.

## Prerequisites

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
workspace configuration. All training operations require a valid `workspace_id`.

**Workspace auto-resolution**: The SDK and CLI automatically resolve `workspace_id` in this order:
1. Explicit `--workspace-id` parameter (if provided)
2. Configured default workspace (via `cloudrobo workspace use --workspace-id <id>`)
3. Auto-query: if no workspace is configured, the SDK queries `cloudrobo workspace list`, picks the
   first available workspace, saves it as the default, and uses it

If auto-query fails (no workspaces found), the error message guides the user to create a workspace.
To manually set the default workspace: `cloudrobo workspace use --workspace-id <id>`.

## Workflow

### Create Task Based on Existing Task

Scenario: user says "按照已有任务创建一个训练任务", "复制之前的任务", "create same task again",
or references an existing task name. **Do NOT walk through the full Task Creation Workflow.** Instead,
reuse the existing task's config directly.

1. **Find the existing task** — if user provides a task name (not ID), use
   `cloudrobo train list-tasks` to find it by name. If user provides task_id, skip to step 2.
2. **Query the existing task config** — `cloudrobo train show-task --task-id <id>` → extract the full
   task config (train_mode, train_method, algorithm, input_models, datasets, spec, cluster_id,
   worker_num, parameters, env, output_models).
3. **Identify what to change** — ask the user in ONE question what to modify (usually just the task
   name). Common changes: `name`, `output_models[].model_name`, `parameters` values.
4. **Auto-fix conflicts** — if creating a task with the same output model name, append a suffix
   (e.g., `-2`, `-3`, or date) to avoid "输出模型已存在" error. Check via `list-tasks` if needed.
5. **Build new config** — copy the existing config, apply user's changes. Keep all other fields
   identical (algorithm, datasets, spec, cluster_id, etc.).
6. **Submit** — `cloudrobo train create-task --config '<new-json>'` (CLI preferred).
   With `--verbose/-v`, show a user-friendly summary first.
7. **Poll status** — 30s interval until terminal state.

> **Key principle**: When the user references an existing task, the agent MUST first query that
> task's config via `show-task` and reuse it, NOT walk through model/dataset/method selection again.
> The user has already made those decisions; they just want a new task with the same config.

### Task Creation Workflow

> **Shortcut**: If the user references an existing task ("按照已有任务创建", "复制之前的任务",
> "create same task again"), skip this workflow and use [Create Task Based on Existing Task](#create-task-based-on-existing-task) instead.

This unified workflow drives both MODEL_TUNING and TRAIN_FROM_SCRATCH task creation. The agent
orchestrates discovery across cloudrobo-asset / cloudrobo-resource, presents options filtered by
what the cloud actually supports, then submits silently (add `--verbose/-v` on the CLI call to
print a user-friendly summary first and submit, no yes/no prompt).

#### Step 1 — Default Task Name

- Default: `Train-{YYYYMMDD-HHMMSS}` (e.g. `Train-20260812-143000`)
- Agent offers the default; user may rename. Proceed with default if user says "ok".

#### Step 2 — Choose Training Method

Ask exactly one question (use a single AskUserQuestion call, NEVER duplicate):
- A) 模型调优 (MODEL_TUNING) — has a base model, finetune via FFT/SFT/LORA/QLORA/DEEPSPEED
- B) 无基模型训练 (TRAIN_FROM_SCRATCH) — three sub-paths (see Step 3b)

> **No-repeat rule**: Each step in this workflow asks the user AT MOST ONE question. Never call
> AskUserQuestion twice in parallel for the same topic. If a step requires multiple inputs
> (e.g. model_name + model_type), combine them into a single question with default options.

#### Step 3a — MODEL_TUNING sub-flow

1. **Model source**: 具身广场-模型 (Gallery, `PUBLIC_MODEL_ASSET`) / 空间资产-模型 (Workspace, `CUSTOM_MODEL_ASSET`)
   - CLI: `cloudrobo asset list-publication-assets --type model` (Gallery) /
     `cloudrobo asset list-assets --type model` (Workspace)
   - List output must show: model name + `latest_version_id` (user selects from this list)
   - **Critical**: When listing workspace models, **filter results for `status == "DRAFT"`** before
     presenting to user. Only `DRAFT` status models are ready for use. Models in `CREATING` status
     will cause `CREATE_FAILED` with error `"输入模型未就绪"`. If no `DRAFT` models exist, warn the
     user and suggest using a Gallery model instead. Gallery models are typically all ready.
   - **Gallery model** (default path): Steps 2-5 below apply — algorithm comes from model's `actions` array
   - **Workspace model** (custom path): Skip Steps 2-5; algorithm config only needs `algorithm_asset_id`
     and `algorithm_version_id` (2-field format). The backend auto-resolves engine/command from the
     algorithm asset. Top-level `inputs`/`outputs` arrays are required. See [Workspace Model Sub-flow](#step-3a-ws--workspace-model-sub-flow) below.
2. **Select model** → extract `asset_id` + `latest_version_id` from the selected model's list entry.
   **Do NOT ask user for version again** — auto-use `latest_version_id`. Only ask if user explicitly
   wants a non-latest version.
3. **Query model version detail** `GET /v1/assets/{asset_id}/versions/{version_id}` → get `actions`
   array. Each action: `{action, algorithm:{asset_id, version_id}, status}`
4. **Show ONLY available training actions** — filter `actions` where `status == "ENABLE"` AND
   `action` is training-related (e.g., "FFT", "SFT", "LORA", "QLORA", "DEEPSPEED"). Exclude
   non-training actions like "ONLINE_DEPLOYMENT". The `action` field value becomes the
   `train_method` in the request body. Do NOT offer actions the model does not advertise.
5. **User picks method** → extract matched action's `action` value (this is `train_method`) and
   `algorithm.asset_id` + `algorithm.version_id`. **Do NOT ask user for algorithm version** —
   it comes directly from the action. Auto-extract and proceed.
6. **Query algorithm version detail** `GET /v1/assets/{algo_asset_id}/versions/{algo_version_id}` →
   get `ext_metadata`. Extract from exact fields:
   - **Hyperparams**: `ext_metadata.hyperparams` → `[{name, default, constraint, description}]`
   - **Environment variables**: `ext_metadata.environment_variables` → `[{name, default, description}]`
   - **Resource constraints**: `ext_metadata.resource` → `[{key, values, operator, constraints?}]`
     - `flavor_type.values`: required flavor type (e.g., `["Ascend"]`) — must match pool flavors
     - `device_distributed_mode.constraints`: `{step, range:[min, max], default}` — min/max NPU
       cards per worker; `default` is the recommended card count
     - `host_distributed_mode.values`: `"singular"` (single host, `worker_num=1`) or `"multiple"`
   - Note: `ext_metadata.env` may exist but is deprecated; always use `environment_variables`
7. **Show env + hyperparams** — present two tables:
   - Hyperparams table: `| 参数名 | 默认值 | 说明 | 约束 |`
   - Env vars table: `| 变量名 | 默认值 | 说明 |`
   User can modify values. Build `parameters` JSON string: each item
   `{key, desc, value, constraint}` (pass ALL hyperparams, required or not). Build `env` JSON string
   from `environment_variables` (default `"[]"` if empty or missing).
8. **Dataset selection** — three sources, each with different required fields:
   - **Gallery (具身广场)**: `source_type: "PUBLIC_DATASET_ASSET"` + `dataset_asset_id` +
     `version_id` + `dataset_name`
   - **Workspace (空间资产)**: `source_type: "CUSTOM_DATASET_ASSET"` + `dataset_asset_id` +
     `version_id` + `dataset_name`. **Filter for `status == "DRAFT"`** — same as models, only
     DRAFT datasets are ready for use.
   - **OBS (对象存储)**: `source_type: "OBS"` + `url_path` only (e.g.,
     `"obs://bucket-name/dataset/"`). **No** `dataset_asset_id`/`version_id`/`dataset_name` needed.

   > **Critical**: Workspace datasets use `CUSTOM_DATASET_ASSET` (NOT `DATASET`). Using the wrong
   > source_type causes RUN_FAILED with exitCode 1 in <2 minutes.
9. **Resource selection** — Before choosing the pool, **check `data_read` permission** for all
   input assets (models and datasets) that use Gallery source types (`PUBLIC_MODEL_ASSET_OFFICIAL`,
   `PUBLIC_MODEL_ASSET_COMMUNITY`, `PUBLIC_DATASET_ASSET`):
   ```
   cloudrobo asset check-permission --asset-id <id> --version-id <ver> --permissions data_read
   ```
   - If any asset returns `data_read: deny` → DEDICATED pools will fail with
     `"专属资源池需要输入资产的可读权限"` → **must use SHARED pool**
   - If all assets return `data_read: allow` → DEDICATED and SHARED pools both work
   - Workspace assets (`CUSTOM_*`) and OBS datasets don't need this check

   Then query pools: `cloudrobo resource list-pools --resource-type MODELARTS`
   (Note: `--usages MODEL_TRAINING` filter may cause 504 proxy timeout in some environments;
   if it fails, omit the filter and manually select pools with `MODEL_TRAINING` in `usages` array).
   For each pool, read `config.flavor.ASCEND[]`
   (list of spec strings like `"1 * SNT9B2 | 24 vCPUs | 192 GiB"`). **Filter flavors using
   `ext_metadata.resource` constraints from Step 3a.6**:
   - Parse the NPU count from each spec (the number before `*`, e.g., `"2 * SNT9B2..."` → 2)
   - Only show flavors where NPU count >= `device_distributed_mode.constraints.range[0]` (minimum)
     and <= `range[1]` (maximum). E.g., `range: [2, 8]` filters out 1-card flavors.
   - Default selection: the flavor matching `constraints.default` (e.g., `default: 2` →
     `"2 * SNT9B2 | 48 vCPUs | 384 GiB"`). User can pick a different valid flavor.
   - `worker_num`: 1 if `host_distributed_mode` is `"singular"`; ask user if `"multiple"`.
   → select pool → `cluster_id` (with `pool-` prefix). Spec: `Ascend: <n> * <model> | <vCPUs> vCPUs | <GiB> GiB`
10. **Output model** — ask save_mode once:
    - `NEW_MODEL`: ask `model_name` + `model_type` in one question; auto-generate `version_name` as
      `"0.0.1"` (user can override). **Do NOT ask each field separately.**
      Fields: `save_mode` + `model_name` + `version_name` + `model_type` + `strict:false`
    - `NEW_VERSION`: ask which existing model + `version_name` in one question. List existing models
      with their latest version; user picks and provides new version_name.
      Fields: `save_mode` + `model_asset_id` + `model_name` + `version_id` + `version_name` + `model_type`
    - `NOT_SAVE`: skip remaining output model fields.
      Fields: `save_mode` only — `{"save_mode": "NOT_SAVE"}`
    - **Clone/Replicate task warning**: If user requests to create task "based on existing task",
      "replicate previous task", or "create same task again", the output model name **MUST** be
      different from the original task. Check existing output model names via
      `list-tasks` or `show-task` before submission. If conflict detected, prompt user for new name.
      Error on conflict: `"输出模型已存在，请更换模型名称"` (Output model already exists, please
      change model name).
11. **Submit** — `cloudrobo train create-task --config '<json>'` (CLI) or `client.create_train_task(req)` (SDK).
    Default: silent submit (no output). With `--verbose/-v`, show a user-friendly summary first.
    **NEVER print raw JSON or code.** Then submit directly — no yes/no prompt.
12. **Poll status** — 30s interval, report state changes until terminal state
13. **On completion:** FINISHED → suggest export/deploy; FAILED/RUN_FAILED/CREATE_FAILED → offer logs/events for diagnosis

#### Step 3a-WS — Workspace model sub-flow (空间资产模型)

When the user selects a **workspace model** (`CUSTOM_MODEL_ASSET`) in Step 3a.1, the algorithm
cannot be resolved from a model `actions` array. Instead, it must be fully configured from the
workspace model's algorithm metadata. This sub-flow replaces Steps 2-5 of the Gallery path.
Steps 6-13 (ext_metadata, hyperparams, dataset, resource, output model, submit, poll) are shared.

1. **Select workspace model** → extract `asset_id` + `latest_version_id` from the list entry.
   **Do NOT ask user for version again.**
   > **Critical**: Workspace model must have `status == "DRAFT"`. Models in `CREATING`
   > status cannot be used as input and will cause `CREATE_FAILED` with error `"输入模型未就绪"`.
   > If no DRAFT models exist in the workspace, inform the user and suggest using a Gallery model instead.
2. **Query model version detail** → get `ext_metadata` for algorithm config (engine, image, code_dir,
   command, etc.). The workspace model's algorithm info is embedded in the model itself, not in a
   separate algorithm asset's `actions` array.
3. **Build algorithm config** — only 2 fields needed. The backend auto-resolves engine/command from
   the algorithm asset. Do NOT include `algorithm_source_type`, `engine`, `code_dir`, `command`,
   `image_asset_id`, or `image_version_id`:
   ```json
   {
     "algorithm_asset_id": "<algo-asset-id>",
     "algorithm_version_id": "<algo-version-id>"
   }
   ```
4. **Build input_models** — use `source_type: "CUSTOM_MODEL_ASSET"` (not `PUBLIC_MODEL_ASSET`):
   ```json
   [{"source_type": "CUSTOM_MODEL_ASSET", "model_asset_id": "...", "version_id": "...", ...}]
   ```
5. **Build inputs/outputs arrays** — workspace models require top-level `inputs` and `outputs`:

   **inputs** format (each item's fields depend on source_type):
   ```json
   "inputs": [{
     "name": "<display-name>",
     "url_path": "obs://bucket/path/",
     "source_type": "CUSTOM_MODEL_ASSET",
     "access_method": "env",
     "local_dir": "<name>=/home/ma-user/cloudrobo/inputs/<name>_0"
   }]
   ```
   - `access_method`: `"env"` (环境变量) or `"parameter"` (超参)
   - `local_dir`: env mode → `"<name>=<container-path>"`, parameter mode → `"--<name>=<container-path>"`

   **outputs** format (simpler — no source_type, always OBS path):
   ```json
   "outputs": [{
     "name": "<output-name>",
     "url_path": "obs://bucket/output-path/",
     "access_method": "parameter",
     "local_dir": "--<name>=/home/ma-user/cloudrobo/outputs/<name>_0"
   }]
   ```

6. **Continue with Steps 6-13** of the Gallery path (ext_metadata hyperparams, env vars, resource
   constraints, dataset selection, resource selection, output model, submit, poll). `log_path` is
   optional for MODEL_TUNING.

> **Key difference from Gallery model**: workspace model uses `CUSTOM_MODEL_ASSET` source_type,
> 2-field algorithm format (same as Gallery), and requires top-level `inputs`/`outputs` arrays.
> Gallery model uses `PUBLIC_MODEL_ASSET` and does not require inputs/outputs arrays.

#### Step 3b — TRAIN_FROM_SCRATCH sub-flow

Ask which sub-path:
- A) 预制算法 (Gallery algorithm)
- B) 空间资产-算法 (Workspace algorithm)
- C) 现配置算法 (Custom config, no preset algorithm)

**Common steps** (all sub-paths):
- Dataset selection (same as Step 3a.8)
- Resource selection (same as Step 3a.9, using `ext_metadata.resource` constraints; for Custom: no constraints, show all flavors)
- Hyperparams (same as Step 3a.7; for Custom: from scratch, no defaults, build `"[]"` if none)
- Output model (same as Step 3a.10; NEW_MODEL only needs 4 fields: `save_mode`, `model_name`, `version_name`, `model_type`)
- Build request body: `name` (unique, append timestamp), `train_mode: "TRAIN_FROM_SCRATCH"`, `datasets`, `spec`, `worker_num`, `cluster_id`, `parameters`, `env` (default `"[]"`), `output_models`, `log_path` (optional), `enable_jupyter` (optional, DEDICATED only)
- Submit (`cloudrobo train create-task --config '<json>'`, `--verbose` to show summary), poll 30s until terminal state

**Algorithm config differences:**

| Sub-path | Algorithm format                                                                                                                               | Discovery |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| Gallery (预制) | 2 fields: `algorithm_asset_id` + `algorithm_version_id`. Backend auto-resolves engine/image.                                                   | `list-publication-assets --type algorithm` → extract `algorithm_asset_id` + `latest_version_id`. Query `ext_metadata` for hyperparams/env/resource. |
| Workspace (空间资产) | 7 fields: `engine.image_url` + `image_asset_id` + `image_version_id` + `code_dir` + `command` + `algorithm_asset_id` + `algorithm_version_id`. | `list-assets --type algorithm` → extract `algorithm_asset_id` + `latest_version_id`. Query `ext_metadata` for engine/command/code_dir + hyperparams/env/resource. |
| Custom (现配置) | 4 fields: `image_asset_id` + `image_version_id` + `command` + `algorithm_source_type: "TEMP_CONFIGURE_ALGORITHM"`. No `algorithm_asset_id`.    | User provides image asset, startup command, local code dir. No `ext_metadata` available. |

**Notes:**
- `algorithm_source_type` NOT needed for Gallery/Workspace (auto-inferred from `algorithm_asset_id`); only required for Custom (no asset_id).
- Workspace algorithm also requires top-level `inputs`/`outputs` arrays (same format as Step 3a-WS).
- Custom config requires `inputs`/`outputs` arrays. `inputs` support 4 `source_type` values: `PUBLIC_DATASET_ASSET`, `CUSTOM_DATASET_ASSET`, `OBS`, `CUSTOM_MODEL_ASSET`. See Step 3a-WS for format.
- On failure (RUN_FAILED with exitCode 1 in <2 minutes, no log files): likely dataset format incompatibility. Check `source_type` and algorithm compatibility.

### SimRL Workflow (Simulation Reinforcement Learning)

SimRL tasks use a **different config schema** from regular training tasks: `config_mode` +
`task_set` + `simple_params`/`rl_config_content` instead of `algorithm` + `parameters`. SimRL
tasks share the same CLI command surface via the `--sim-rl` flag. There is no `resume` for SimRL.

#### Step 1 — Model Discovery

Ask model source:

- **具身广场模型** (Gallery): `cloudrobo asset list-publication-assets --type model
  --action-status ENABLE --actions LIBERO_SPATIAL,LIBERO_OBJECT,LIBERO_GOAL,LIBERO_10
  --actions-operator OR` → pick model →
  extract `model_asset_id` + `latest_version_id`. `source_type: "PUBLIC_MODEL_ASSET"`.
  **Do NOT ask user for version again** — auto-use `latest_version_id`.
  **Critical**: The `--actions` and `--action-status` filters are REQUIRED — without them, the query
  returns ALL Gallery models, not just SimRL-compatible ones. Only models with ENABLED LIBERO_*
  actions can be used for SimRL tasks.
- **空间资产模型** (Workspace): `cloudrobo asset list-assets --type model` → pick model →
  extract `model_asset_id` + `latest_version_id`. `source_type: "CUSTOM_MODEL_ASSET"`.

Query model version detail `GET /v1/assets/{asset_id}/versions/{version_id}` → get `actions`
array. Each action represents a **task set** (e.g., `LIBERO_SPATIAL`, `LIBERO_GOAL`).

#### Step 2 — Select Task Set

From the `actions` array, show available task sets to the user. Extract the `action` field value
(e.g., `"LIBERO_SPATIAL"`) → this becomes `task_set` in the request body.

Query the selected task set detail (action detail) to get:
- `ext_metadata.hyperparams` → for SIMPLE mode parameter defaults
- `ext_metadata.environment_variables` → for SIMPLE mode env vars
- `ext_metadata.yaml_config` → for ADVANCED mode (full YAML config template)
- `ext_metadata.resource` → resource constraints (flavor type, NPU card count)

#### Step 3 — Config Mode Selection

Ask user which parameter configuration mode:

- **快速配置 (SIMPLE)**: `config_mode: "SIMPLE"`, uses `simple_params` (JSON string array).
  Show hyperparams table from `ext_metadata.hyperparams`, user can modify values.
  Default RL_ALGO is `ppo`.
  ```json
  "simple_params": "[{\"key\":\"RL_ALGO\",\"value\":\"ppo\",\"desc\":\"强化学习算法\"},{\"key\":\"MAX_EPOCHS\",\"value\":\"100\",\"desc\":\"训练轮数\"},...]"
  ```
  Each item: `{key, value, desc}`. `simple_params` accepts either a JSON string or an array; the SDK auto-serializes arrays to JSON strings.

- **YAML配置 (ADVANCED)**: `config_mode: "ADVANCED"`, uses `rl_config_content` (full YAML string).
  Pre-fill with `ext_metadata.yaml_config` content, user can adjust.
  ```json
  "rl_config_content": "runner:\n  task_type: embodied\n  max_epochs: 100\n  ..."
  ```

#### Step 4 — Resource Pool Selection

Same permission check (`data_read` for Gallery assets) and pool query as [Step 3a.9](#step-3a--model_tuning-sub-flow).
Filter flavors by `ext_metadata.resource` constraints. SimRL-specific rules:

- **SHARED (公共) pool**: `enable_jupyter` must be `false` (JupyterLab not supported)
- **DEDICATED (专属) pool**: `enable_jupyter` can be `true` or `false` (user's choice)
- `spec` format: `"ASCEND: <n> * <model> | <vCPUs> vCPUs | <GiB> GiB"` (uppercase `ASCEND`)

#### Step 5 — Output Model

Ask save_mode:

- **NEW_MODEL** (新模型): 7 fields:
  ```json
  {"save_mode": "NEW_MODEL", "model_name": "<name>", "version_name": "0.0.1", "model_type": "vla",
   "model_asset_id": null, "version_id": null, "strict": false, "skills": []}
  ```
- **NEW_VERSION** (已有模型新版本): 8+ fields:
  ```json
  {"save_mode": "NEW_VERSION", "model_name": "<existing-model-name>", "version_name": "<new-version>",
   "model_type": "vla", "model_asset_id": "<existing-model-asset-id>", "version_id": "",
   "strict": false, "skills": [{"name": "<skill-name>", "prompt": "<skill-prompt>"}]}
  ```
  `version_id` is empty string `""` (not null). `skills` array can contain skill definitions.

#### Step 6 — Build SimRL Config

Construct JSON with:
- `name`: unique task name
- `description`: optional
- `workspace_id`: auto-injected by SDK
- `input_models`: `[{source_type, model_asset_id, model_name, version_id, version_name}]`
  (`PUBLIC_MODEL_ASSET` for Gallery, `CUSTOM_MODEL_ASSET` for Workspace)
- `task_set`: from Step 2 (e.g., `"LIBERO_SPATIAL"`)
- `config_mode`: `"SIMPLE"` or `"ADVANCED"` from Step 3
- `simple_params`: JSON string (SIMPLE mode only)
- `rl_config_content`: YAML string (ADVANCED mode only)
- `spec`: `"ASCEND: <n> * <model> | <vCPUs> vCPUs | <GiB> GiB"`
- `cluster_id`: pool ID with `pool-` prefix
- `worker_num`: typically 1
- `output_models`: from Step 5
- `enable_jupyter`: `false` for SHARED pool; `true`/`false` for DEDICATED pool

**Note**: SimRL does NOT use `algorithm`, `datasets`, `parameters`, `env`, or `log_path` fields.

#### Step 7 — Submit and Monitor

1. **Create SimRL task** — `train create-task --config '<json>' --sim-rl` (or `save-draft --sim-rl`
   to save a draft first). SDK: `client.create_sim_rl_task(req)`.
2. **Poll status** — `train show-task --task-id <id> --sim-rl` or `train list-tasks --sim-rl`
3. **Monitor** — `get-resource-usage --metric ... --start ... --end ... --sim-rl`,
   `get-events --start-time ... --end-time ... --sim-rl`, `get-logs --sim-rl`,
   `get-signed-url --file-source ... --file-name ... --sim-rl`
4. **Lifecycle** — `stop-task --sim-rl`, `restart-task --sim-rl`, `clone-task`,
   `delete-tasks --sim-rl` (per-id DELETE), `update-task --sim-rl`
5. **Stats** — `train stats --workspace-id <id> --sim-rl`

### Draft Workflow (Save & Resubmit)

Scenario: user wants to save a task config without executing immediately, then edit and submit later.

1. **Prepare task config** — only `name` + `workspace_id` required for draft; `algorithm`/`spec`
   optional
2. **Save draft** — `train save-draft --config '<draft-json>'` (or `--sim-rl` for SimRL draft) →
   returns `task_id`, task status = `DRAFT`
3. **Later, edit config and resubmit:**
   - **SDK (recommended for draft submit)**: `restart_train_task(task_id, req)` with full TrainTaskDto body — restart endpoint edits and resubmits
   - **CLI**: `train restart-task --task-id <draft-id>` resubmits with existing config; use SDK to pass edited config. For SimRL, `restart-task --sim-rl` resubmits
4. **After resubmit**, task leaves DRAFT state → CREATING → WAITING → RUNNING → terminal

> **Inference note**: `save-draft` (POST /train-tasks/draft) returns task_id in DRAFT status; `restart` (POST /train-tasks/{id}/restart) accepts full TrainTaskDto body and edits/resubmits the task.

### Monitoring Workflow (In-Progress Task)

Scenario: task is RUNNING, track progress and resource usage.

1. **Poll status** — `show-task --task-id <id>` (30s interval)
2. **Query execution stages** — `get-stages --task-id <id>` → returns SCHEDULING → PREPARING →
   RUNNING → END with sub-stages and timestamps
3. **Query resource usage** — `get-resource-usage --task-id <id> --metric <m> --start <ts> --end <ts>`
   → CPU/GPU/NPU utilization, sample points
4. **Query events** — `get-events --task-id <id> --start-time <ts> --end-time <ts>` →
   INFO/WARNING/ERROR/DEBUG events with timestamps
5. **Report progress** to user; on WARNING/ERROR events, proactively alert

### Diagnosis Workflow (Failure Diagnosis)

Scenario: task FAILED / RUN_FAILED / CREATE_FAILED → auto-analyze, locate cause, suggest fixes.

1. **Get task detail** to confirm failure status, failure stage, and exit code
2. **Get execution stages** to identify which stage failed (SCHEDULING/PREPARING/RUNNING/END)
3. **Get events** filtered by level=Error to find error events
4. **Get logs** — try multiple approaches (logs may not be available if task failed quickly):
   - `get-logs --task-id <id>` (CLI)
   - SDK: `list_observations(task_id)` to list available log files
   - SDK: `get_log_signed_url(task_id, file_source, file_name)` to get download URL
   - If all return empty/500: task may have failed before generating logs
5. **Analyze key error patterns:**
   - CREATE_FAILED → check `spec` format, `cluster_id`, resource availability, **input model status**
   - **Input model not ready** → error: `"输入模型未就绪"` (input model not ready). Occurs when
     `input_models[].source_type` is `CUSTOM_MODEL_ASSET` but the model `status` is `CREATING` (not
     `DRAFT`). Fix: wait for model to reach `DRAFT` status, or use a Gallery model
     (`PUBLIC_MODEL_ASSET`) instead. Check model status via `cloudrobo asset show-asset --asset-id <id>`
   - **Task name conflict** → error: "Resource has already existed" (409 Conflict). Fix: use unique
     task name (append timestamp suffix like `Train-YYYYMMDD-HHMMSS`)
   - Resource scheduling failure → check `spec` and `worker_num`, cluster capacity
   - Image pull failure → check `algorithm.image_url` (for MODEL_TUNING) or algorithm asset config (for TRAIN_FROM_SCRATCH)
   - Dataset access denied → check `datasets[].dataset_asset_id` and workspace permissions
   - **Dataset format incompatibility** → RUN_FAILED with exitCode 1 in <2 minutes, no log files.
     Occurs when dataset format doesn't match algorithm expectations (e.g., LeRobot algorithm expects
     specific dataset format) or when `source_type` is wrong (using `DATASET` instead of
     `CUSTOM_DATASET_ASSET`). Fix: verify dataset `source_type` is correct
     (`CUSTOM_DATASET_ASSET` for workspace, NOT `DATASET`); try using Gallery dataset
     (`PUBLIC_DATASET_ASSET`) instead; check algorithm documentation for required dataset format
   - OOM → check `spec` memory, `worker_num`, reduce `batch_size` in parameters
   - Algorithm error → check `algorithm.command`, `boot_file`, `parameters`
   - Output model exists → error: "输出模型已存在，请更换模型名称". For clone/restart, the SDK auto-increments version_name by querying the latest version from the asset service. For create-task, use unique model name (append suffix like `-2`, `-3`, or timestamp)
   - Dedicated pool asset permission → error: "专属资源池需要输入资产的可读权限". Occurs when
     using DEDICATED pool without proper asset permissions. Fix: switch to SHARED pool or grant
     read/write/usage permissions on all involved assets (input_models, algorithm, datasets)
   - **Logs unavailable** (API returns 500 or empty list): task failed too quickly, logs not generated.
     Check task execution time and exit code from events. If exitCode 1 and runtime <2 min, likely
     dataset format or training script error. Suggest trying different dataset or checking algorithm
     documentation for required dataset format.
6. **Output diagnosis conclusion** and fix suggestions
7. **After user confirmation**, fix config and `restart-task` or save-draft + create-task

### Long-Running Task Workflow

1. Training tasks can run for hours/days; after creating, set a reasonable polling interval (60s+)
2. On each poll, report: current status, current stage, elapsed time, latest events
3. On timeout (user-defined), output current status and suggest: continue / view logs / view
   resource usage / stop

## CLI Command Format

```bash
cloudrobo train <command> [OPTIONS] [--sim-rl]
```

- Subcommands: kebab-case (`create-task`, `list-tasks`, `get-stages`, etc.)
- `--sim-rl` routes to SimRL API surface; `--workspace-id <id>` overrides on `stats`
- JSON params via `--config '<json>'`; optionally from file via `--config-file`
- Output: JSON to stdout

> CloudRobo CLI is a self-developed Click-based tool (not `hcloud`/KooCLI). SDK exposes 33 methods
> (12 `train_*` + 15 `sim_rl_*` + 6 unprefixed); CLI exposes 20 commands. `list_observations` is
> SDK-only; `resume` and checkpoint methods are train-only. See
> `references/task-config-catalog.md` for the coverage matrix.

## Core Commands

> **CLI First**: Always prefer CLI commands (`cloudrobo train <command>`) over direct SDK calls.
> Use Python SDK (`TrainClient`) only when: (a) CLI doesn't support the needed operation (e.g.,
> `list_observations` is SDK-only), (b) cross-package queries (e.g., querying asset version detail
> via asset service), or (c) CLI fallback for dynamic JSON assembly. Full SDK templates in
> [SDK Quick Start](references/sdk-quickstart.md).
>
> **workspace_id auto-resolution**: All commands that need `workspace_id` (create-task,
> save-draft, restart-task, list-tasks, stats) automatically resolve it from: (1) explicit
> `--workspace-id` param, (2) configured default workspace (`cloudrobo workspace use`), or (3) auto-query.
> You do NOT need to include `workspace_id` in the `--config` JSON body — the SDK injects it automatically.
>
> **SDK-level validation**: SDK methods (`create_train_task`, `create_sim_rl_task`, `save_draft`,
> `create_sim_rl_task_draft`, `restart_train_task`, `restart_sim_rl_task`, `copy_sim_rl_task`,
> `register_train_checkpoint`) validate required fields before making HTTP calls. Missing fields
> raise `ValueError`. CLI automatically converts these to user-friendly `click.UsageError` messages.
> Use SDK directly when you need programmatic error handling.

### Task Creation

Training mode (fine-tuning `MODEL_TUNING` vs pre-training `TRAIN_FROM_SCRATCH`), method
(FFT/SFT/LORA/QLORA/DEEPSPEED), base model, dataset, and spec are all expressed through the
`--config` JSON body — there are no dedicated `finetune`/`pretrain` subcommands.

#### Submit a fine-tuning task (MODEL_TUNING)

```bash
cloudrobo train create-task --config '<task-json>'
```

- **SDK:** `client.create_train_task(req)` — req format see [Step 3a](#step-3a--model_tuning-sub-flow)
- **API:** `POST /v1/training/train-tasks`

#### Submit a pretraining task (TRAIN_FROM_SCRATCH)

```bash
cloudrobo train create-task --config '<task-json>'
```

- **SDK:** `client.create_train_task(req)` — req format see [Step 3b](#step-3b--train_from_scratch-sub-flow)
- **API:** `POST /v1/training/train-tasks`
  - `log_path`: **optional** OBS path — can be omitted if user doesn't specify a log path
  - `enable_jupyter`: **optional** boolean — set to `true` for JupyterLab access during training
  - `workspace_id`: auto-injected by SDK

#### Create a task from full JSON config (train or SimRL)

```bash
cloudrobo train create-task --config '<task-json>' [--sim-rl]
```

- **SDK:** `client.create_train_task(req)` / `client.create_sim_rl_task(req)`
- **API:** `POST /v1/training/train-tasks` / `POST /v1/training/rl-tasks/simulation`

#### Save a draft task (train or SimRL)

```bash
cloudrobo train save-draft --config '<draft-json>' [--sim-rl]
```

- **SDK:** `client.save_draft(req)` / `client.create_sim_rl_task_draft(req)`
- **API:** `POST /v1/training/train-tasks/draft` / `POST /v1/training/rl-tasks/simulation/draft`

### Task Management

All accept `--sim-rl` (except `resume-task`, `clone-task` which is SimRL-only). API prefix:
`/v1/training/train-tasks` (train) / `/v1/training/rl-tasks/simulation` (SimRL).

| Command | CLI Syntax | SDK Method | API Suffix |
| ------- | ---------- | ---------- | ---------- |
| List tasks | `list-tasks [--train-mode] [--status] [--offset] [--limit]` | `list_train_tasks` / `list_sim_rl_tasks` | `GET /` |
| Show task | `show-task --task-id <id>` | `show_train_task` / `show_sim_rl_task` | `GET /{task_id}` |
| Update task | `update-task --task-id <id> --config '<json>'` | `update_train_task` / `update_sim_rl_task` | `PATCH /{task_id}` |
| Delete tasks | `delete-tasks --task-id <id> [--task-id <id>...]` | `batch_delete_train_tasks(execution_ids)` / `delete_sim_rl_task(task_id)` | `POST /batch-delete` (train) / `DELETE /{task_id}` (SimRL) |

> **delete-tasks behavior**: For regular training tasks, the CLI auto-resolves `execution_id` from
> the provided `task_id` via `show-task` before calling batch-delete. Users can pass task IDs
> directly — no need to manually look up `execution_id`. For SimRL, task_id is used directly.

| Stop task | `stop-task --task-id <id>` | `stop_train_task` / `stop_sim_rl_task` | `POST /{task_id}/stop` |
| Restart task | `restart-task --task-id <id> [--config '<json>'] [--config-file <path>] [--sim-rl]` | `restart_train_task(task_id, req=None)` / `restart_sim_rl_task(task_id, req=None, task_detail=None)` | `POST /{task_id}/restart` |
| Clone task | `clone-task --task-id <id> [--config '<json>'] [--config-file <path>]` (SimRL-only) | `copy_sim_rl_task(task_id, req=None, task_detail=None)` | `POST /rl-tasks/simulation/{task_id}/copy` |
| Resume task | `resume-task --task-id <id>` (train-only) | `resume_train_task` | `POST /{task_id}/resume` |
| Stats | `stats --workspace-id <id> [--user-id]` | `count_train_tasks_by_status` / `count_sim_rl_tasks_by_status` | `GET /stats` |

> **Restart** = edit & resubmit. CLI supports `--config`/`--config-file` to override fields from the
> original task; SDK's `req` param does the same. Non-DRAFT train tasks cannot modify `name`/`train_mode`/
> `train_method`; SimRL restart requires DRAFT status. SDK's `task_detail` param skips the auto `show` call.
> SDK auto-cleans `input_models`/`output_models` (strips runtime fields), auto-increments `version_name`
> for `save_mode=NEW_MODEL|NEW_VERSION` (queries asset service for latest version), and auto-serializes
> `simple_params`/`rl_config_content` from array/dict to JSON string.
> **Clone** is SimRL-only (train copy API removed). SDK auto-generates a new name with `-copy-{4hex}`
> suffix (e.g., `my-task-copy-a1b2`) unless `req` provides an explicit `name`. **Resume** is train-only.

### Task Monitoring

| Command | Required params | SDK Method | Returns |
| ------- | --------------- | ---------- | ------- |
| `get-stages --task-id <id>` | `--task-id` | `list_train_stages` | 4 stages: SCHEDULING→PREPARING→RUNNING→END |
| `get-resource-usage --task-id <id> --metric <m> --start <s> --end <e>` | `--metric` `--start`(sec) `--end`(sec) | `show_resource_usage` / `show_sim_rl_task_resource_usage` | CPU/GPU/NPU utilization |
| `get-logs --task-id <id> [--file-name] [--log-name-pre]` | `--task-id` | `get_log_content` / `show_sim_rl_task_observations_content` | Log content (`--file-name` not `--file-path`) |
| `get-signed-url --task-id <id> --file-source <s> --file-name <n>` | `--file-source` `--file-name` | `get_log_signed_url` / `show_sim_rl_task_observations_signed_url` | OBS temp download URL |
| `get-events --task-id <id> --start-time <ms> --end-time <ms>` | `--start-time`(**ms**) `--end-time`(**ms**) | `list_events` / `list_sim_rl_task_events` | INFO/WARNING/ERROR/DEBUG events |
| (SDK-only) `list_observations` | `--task-id` | `list_observations` / `list_sim_rl_task_observations` | File listing (CLI `get-logs` covers content) |

> All accept `--sim-rl`. `get-events` uses **milliseconds** (13-digit), `get-resource-usage` uses **seconds** (10-digit).

### Checkpoint Management (train-only, no `--sim-rl`)

```bash
cloudrobo train list-checkpoints --task-id <id> [--status] [--name] [--offset] [--limit] [--order]
cloudrobo train register-checkpoint --task-id <id> --checkpoint-name <name> [--save-mode NEW_VERSION|NEW_MODEL] [--version-name] [--model-name]
```

| Command | SDK Method | API |
| ------- | ---------- | --- |
| `list-checkpoints` | `list_train_checkpoints(task_id, **params)` | `GET /{task_id}/checkpoints` |
| `register-checkpoint` | `register_train_checkpoint(task_id, req)` | `POST /{task_id}/checkpoints/register` |

`register-checkpoint`: `NEW_VERSION` (default) adds to existing model; `NEW_MODEL` creates new model
(requires `--model-name`). Returns WAITING; processed asynchronously.

### Algorithm Discovery

#### List available algorithms

```bash
cloudrobo asset list-publication-assets --type algorithm [--name <fuzzy-name>] [--limit 20]
```

- **SDK (cross-package):** `asset_client.list_publication_assets(type="algorithm", limit=20)`
- **API:** Cross-package — calls the asset service, not the train service directly.

Each algorithm includes `ext_metadata` with `engine.image_url`, `command`, `boot_file` needed for
pretrain task creation.

#### Query asset version detail (model / algorithm / dataset)

- **API:** `GET /v1/assets/{asset_id}/versions/{version_id}` (cloudrobo-asset-manager service)
- **Model version detail** returns: `actions` array, each action has `{action, algorithm:{asset_id, version_id}, status}`. The `action` field (e.g., FFT, LORA, ONLINE_DEPLOYMENT) becomes `train_method`. Filter for training-related actions with `status=="ENABLE"` (exclude ONLINE_DEPLOYMENT etc.)
- **Algorithm version detail** returns: `ext_metadata.hyperparams` (default hyperparameters),
  `ext_metadata.environment_variables` (env vars as `[{name, default, description}]`),
  `ext_metadata.engine.image_url`, `ext_metadata.command`, `ext_metadata.inputs`/`outputs`,
  `ext_metadata.resource` (NPU card constraints — see Step 3a.6)
- **Usage**: For fine-tuning, get algorithm from model actions → query algorithm version detail for hyperparams; for pretraining, query algorithm asset version detail directly for hyperparams and full ext_metadata

## Submission Behavior & Confirmation

**Silent submit by default.** Creation commands (`create-task`/`restart-task`/
`register-checkpoint`/`save-draft`) submit without prompting. The agent **MUST NOT** print raw JSON
or code. With `--verbose/-v`, present a user-friendly grouped summary (tables/lists), then submit
directly — no yes/no.

**Destructive ops** (`stop-task`/`delete-tasks`/`resume-task`): agent confirms `task_id` before acting.
**`restart-task`**: if config edited, show diff briefly then submit; if no edits, submit silently.
**`update-task`**: confirm field changes before PATCH.

### Verbose Display Format

Grouped tables/lists, **NEVER raw JSON**. Sections: 【基本信息】【算法配置】【基础模型】(MODEL_TUNING
only)【超参】(table)【环境变量】(table)【数据集】【资源配置】【训练产物】. Omit inapplicable sections;
print "（无）" for empty env. For `restart-task --verbose`: show task_id + changed fields (diff style).

### Required Parameters (no defaults)

| Command | Required params | Notes |
| ------- | --------------- | ----- |
| `get-resource-usage` | `--metric` `--start` `--end` | seconds (10-digit) |
| `get-events` | `--start-time` `--end-time` | **milliseconds** (13-digit) |
| `get-signed-url` | `--file-source` `--file-name` | file_source from 8-value enum |
| `stats` | `--workspace-id` | — |
| `finetune` | `--method` | Uppercase: FFT/SFT/LORA/QLORA/DEEPSPEED |
| `pretrain`/`finetune` | `--spec` | `Ascend: N * Model \| vCPUs vCPUs \| GiB GiB` |

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Task Config Reference](references/task-config-catalog.md) — TrainTaskDto fields, algorithm mapping, spec format, status enum, stage/event structure, three-layer coverage matrix
- [SDK Quick Start](references/sdk-quickstart.md) — Complete Python SDK call templates: initialization, finetune/pretrain/SimRL full request body examples, draft workflow, polling and monitoring, cross-package queries
- [API Paths](references/api-paths.md) — Full endpoint list with SDK source line references

## Edge Cases

| Scenario | Handling                                                                                                                                                                                                                                                 |
| ---------- |----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Missing `workspace_id` | All commands auto-resolve from config or auto-query; run `cloudrobo workspace use` to set default                                                                                                                                                        |
| Task in non-terminal state | Poll at 30-60s intervals; training can run for hours/days                                                                                                                                                                                                |
| `spec` format | String `Ascend: <n> * <model> \| <vCPUs> vCPUs \| <GiB> GiB`, not JSON. Filter by `ext_metadata.resource` constraints                                                                                                                                    |
| `train_method` / `train_mode` | Uppercase enums: `FFT`/`SFT`/`LORA`/`QLORA`/`DEEPSPEED`; `MODEL_TUNING`/`TRAIN_FROM_SCRATCH`                                                                                                                                                             |
| CREATE_FAILED | Check `spec` format, `cluster_id`, resource availability, task name uniqueness (409 Conflict), **input model status** (must be `DRAFT` for workspace models)                                                                                             |
| RUN_FAILED | Check logs/events; common: OOM, image pull failure, dataset access denied, **dataset format incompatibility** (exitCode 1 in <2 min, no logs)                                                                                                            |
| Resource scheduling failure | Check `spec`, `worker_num`, cluster capacity, and `ext_metadata.resource` min NPU constraint                                                                                                                                                             |
| Stopped task | Use `restart-task` to resubmit; `resume-task` for supported train-only cases                                                                                                                                                                             |
| SimRL resume | Not supported; `--sim-rl` not accepted on `resume-task`                                                                                                                                                                                                  |
| Draft submit via CLI | `restart-task` supports `--config`/`--config-file` to edit fields before resubmit                                                                                                                                                                        |
| Missing required fields | SDK validates before HTTP call; CLI shows `click.UsageError` with the missing field list                                                                                                                                                                 |
| AK/SK not set | Operations fail at HTTP signing step; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK`                                                                                                                                                                            |
| Array size limits | `datasets`, `input_models`, `output_models` — max 1 item each                                                                                                                                                                                            |
| `parameters` format | JSON string; each item: `key`+`desc`+`value`+`constraint`; pass ALL hyperparams                                                                                                                                                                          |
| `env` format | JSON string; pass `"[]"` if no custom env vars                                                                                                                                                                                                           |
| `cluster_id` | Pool ID with `pool-` prefix (e.g., `pool-6872b4ac-...`); SHARED or DEDICATED pool type. SHARED pools require the full `pool_id` (starts with `pool-`); DEDICATED pools use the cluster_id directly. Using DEDICATED pool requires asset read permissions |
| Task status | `status` 10 values: CREATING/RUNNING/FAILED/WAITING/DRAFT/FINISHED/STOPPING/DELETING/ABNORMAL; `detail_status` 15 values (adds CREATE_FAILED/RUN_FAILED/STOP_FAILED/NOT_EXIST/UNKNONW); terminal status: FINISHED/FAILED/STOPPED/ABNORMAL                |
| Task deletion | Irreversible. CLI `delete-tasks --task-id <id>` auto-resolves `execution_id` from task_id for regular training tasks; no manual lookup needed                                                                                                            |
| Algorithm info | Dynamically fetched from `ext_metadata`; do not hardcode asset_ids                                                                                                                                                                                       |
| Object storage | Must use `obs://` protocol; `s3://` prohibited                                                                                                                                                                                                           |
| Cross-skill | Does not call other skills; data processing → `cloudrobo-dataset`, deployment → `cloudrobo-infer`                                                                                                                                                        |
| `--sim-rl` flag | On 14 commands; absent on `pretrain`/`finetune`/`resume-task`/`list-checkpoints`/`register-checkpoint`                                                                                                                                                   |
| `get-logs` file selection | `--file-name` (not `--file-path`); `--log-name-pre` matches by prefix                                                                                                                                                                                    |
| Clone task name conflict | SDK auto-generates `{original-name}-copy-{4hex}` name; pass `--config '{"name":"custom-name"}'` to override                                                                                                                                              |

## Verification & Best Practices

- **Test**: `bash scripts/test-cli-commands.sh` (CLI/SDK/API); see `templates/test-vars.json` for full coverage
- **Polling**: 30-60s intervals; report status + stage changes. On FINISHED → suggest export/deploy; on FAILED → offer logs/events
- **Draft workflow**: save-draft → verify DRAFT → restart-task → verify leaves DRAFT → poll to terminal
- **Monitoring**: `get-stages` (4-stage flow), `get-resource-usage` (CPU/GPU/NPU), `get-events` (filter `--level Error`)
- **SimRL**: repeat monitoring with `--sim-rl` (no `get-stages` — SimRL has no stages endpoint); verify `resume-task` rejects `--sim-rl`
- **Dry-run**: not supported by this CLI; validate params via `save-draft` + `show-task` before
  submitting with `create-task`
- **Drafts**: use SDK `restart_train_task(task_id, req)` to submit with edited config (CLI doesn't accept config body)
- **Stats**: `stats --workspace-id <id>` for status distribution overview
