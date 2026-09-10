---
name: huawei-cloud-cloudrobo-model-workflow
description: |
  Model development orchestration Skill covering asset query, model training, inference deployment, and real-robot evaluation in any combination. Supports full end-to-end pipeline or partial stages (e.g., train+deploy only, deploy+eval only). When user requirements involve two or more stages, prefer this Skill over individual module Skills.
  Triggers include: "用XX机器人训练XX任务", "so101 插笔", "训练部署", "部署评测", "训练评测部署", "模型开发流程", "端到端训练", "训练推理评测", "只训练不评测", "训练完部署", "model workflow", "end-to-end training", "train and deploy", "deploy and eval".
tags:
  - huawei-cloud-cloudrobo
  - model-workflow
  - training
  - inference
  - evaluation
---

# CloudRobo Model Development Orchestration Workflow

> Orchestrate the pipeline: asset query → model training → inference deployment → real-robot evaluation → result output. **Use CLI commands throughout; Python SDK is prohibited.**

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

---

## Overview

### Pipeline Stages

```
Stage 0: Use Case Parsing      → Extract robot type + task, select model; parse dataset source
Stage 1: Asset Query & Dataset → Query model/algorithm/dataset assets; get default hyperparams and confirm; OpenPI model constructs data.rename_map
Stage 2: Model Training        → CLI create-task creates training task, poll until complete
Stage 3: Inference Deployment  → CLI infer create deploys inference service
Stage 4: Real-Robot Evaluation → CLI dispatch create-task dispatches task to real robot (session_id=workspace_id, no session creation needed)
Stage 5: Result Output         → Output evaluation score and report
```

### Execution Modes

| Mode | User Intent Example | Stages |
|------|-------------------|--------|
| **Full pipeline** | "用 so101 训练插笔任务并评测" | Stage 0→5 |
| **Train+Deploy** | "训练完帮我部署推理服务" | Stage 0→3 |
| **Deploy+Eval** | "我模型训练好了，帮我部署评测" | Stage 3→5 |

> **Stage dependencies cannot be skipped**: Evaluation depends on inference service RUNNING, deployment depends on training FINISHED, training depends on asset info. When starting from an intermediate stage, user must provide preceding output parameters.

### Skip-Stage Input Requirements

| Start Stage | User Must Provide | Prompt |
|-------------|-------------------|--------|
| Stage 2 | `base_model_asset_id`, `dataset_asset_id` | "Please provide base model asset_id and dataset asset_id" |
| Stage 3 | `output_model_asset_id`, `output_model_version_id` | "Please provide training output model asset_id and version_id" |
| Stage 4 | `service_id` | "Please provide inference service service_id" |

### Data Flow Contract

| From → To | Handoff Values |
|-----------|----------------|
| Stage 0 → 1 | `model_keyword`, `dataset_source`, `dataset_value`, `robot_type` |
| Stage 1 → 2 | `base_model_asset_id/version_id`, `algorithm_asset_id/version_id`, `train_method`, `default_hyperparams`, `dataset_asset_id/version_id`, `data.rename_map` (OpenPI only) |
| Stage 2 → 3 | `output_model_asset_id`, `output_model_version_id` |
| Stage 3 → 4 | `service_id` |
| Stage 4 → 5 | `robot_id`, `task_id`, `task_status`, `task_result` |

---

## Prerequisites

1. **cloudrobo CLI** installed and authenticated (`HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK`)
2. **workspace_id** set via `cloudrobo workspace use <id>`
3. Base model assets available in marketplace
4. **User-provided dataset**: registered asset, OBS path, or local directory
5. **Real robot registered** and online

> **Windows/PowerShell note**: PowerShell has issues parsing JSON with `|`, `"` special characters. When passing complex JSON parameters, **write JSON to a temp file and use Python subprocess to call CLI** (this is not SDK, just a Python wrapper for CLI to work around PowerShell encoding issues). See `references/cli-installation-guide.md`.

---

## Workflow

### Stage 0: Use Case Parsing

Extract from user input: robot type, task description, dataset source.

#### Model Selection

**User specifies model** → use directly.

**User does not specify model** → query marketplace preset models, use question tool to ask user:

```bash
cloudrobo asset list-publication-assets --type model
```

- List all available preset models for user selection, recommended model marked "(Recommended)"
- Do not silently select recommended model — user may want ACT, DP, or other models

#### Robot → Recommended Model Mapping

| Robot | Recommended Model |
|------|-------------------|
| so101 / jaka / franka / general | `LeRobot_PI05-Base` |

#### Dataset Source Parsing

| User Input | Type | Processing |
|-----------|------|-----------|
| Asset name/asset_id | `user_specified` | Stage 1 search this asset |
| OBS path `obs://` | `obs_path` | Stage 1 register as asset |
| Local directory path | `local_path` | Stage 1 upload to OBS and register |
| Not specified | `need_ask` | **Must ask user** |

### Stage 1: Asset Query & Dataset Processing

#### Step 1.1: Query Base Model + Extract Algorithm Info

```bash
cloudrobo asset search-assets --keyword "<model_keyword>"
```

Extract from results:
- `id` → `base_model_asset_id`
- `latest_version_id` → `base_model_version_id`
- `actions[].action` → `train_method` (e.g., `FFT`, `LORA`)
- `actions[].algorithm.asset_id` → `algorithm_asset_id`
- `actions[].algorithm.version_id` → `algorithm_version_id`

> **train_method** comes from model `actions[].action` (e.g., `FFT`, `LORA`), not `SFT`/`QLORA`. Default `FFT`; use `LORA` when user requests LoRA.

#### Step 1.1b: Query Algorithm Asset Details (Get Default Hyperparams)

```bash
cloudrobo asset show-asset --asset-id <algorithm_asset_id>
```

Extract default hyperparams from `ext_metadata.hyperparams`. Each hyperparam has `name`, `default`, `constraint.type`, `constraint.editable`, `description`.

#### Step 1.1c: Hyperparameter Confirmation & Customization (Must Execute)

After getting default hyperparams, **must use question tool to ask user** whether to modify:

1. Display default hyperparams as table (name, default, description)
2. Provide options: "Use default hyperparams" (Recommended) / "Customize some hyperparams"
3. If user chooses custom, use defaults as base, override specified keys, keep rest as default

> **Critical**: This step cannot be skipped. Even if user chooses defaults, must explicitly confirm.
> **Fabricating parameter keys is prohibited**: All keys must come from algorithm `ext_metadata.hyperparams` `name` field.

#### Step 1.1d: OpenPI Model data.rename_map Construction (OpenPI Only)

> **Applicable**: Execute when base model is `Physical-Intelligence_PI0-Base` or `Physical-Intelligence_PI05-Base`. Skip for other models.

See `references/openpi-rename-map.md` for full construction details.

#### Step 1.2: Process User Dataset

**Case A: Registered Asset**

```bash
cloudrobo asset search-assets --keyword "<dataset_name_or_id>"
```

Extract `id` → `dataset_asset_id`, `latest_version_id` → `dataset_version_id`.

**Case B: OBS Path**

```bash
cloudrobo workspace current  # Get asset_catalog_id
cloudrobo asset create-asset --catalog-id <catalog_id> --name "<dataset_name>" --type dataset --ext-metadata '{"annotation_status":true}'
cloudrobo asset create-version --asset-id <asset_id> --url "<obs_path>"
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

**Case C: Local Directory**

```bash
cloudrobo workspace current  # Get asset_catalog_id
cloudrobo asset import-asset --catalog-id <catalog_id> --type dataset --local-path <local_dir_path> --name <dataset_name>
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

> **Critical**: `import-asset` requires local directory to contain `README.md` with YAML frontmatter containing `ext_metadata.annotation_status: true`.
> **Critical**: After `import-asset`, dataset version status is `CREATING`; must manually publish as `RELEASE`, otherwise training reports "dataset not ready".

**Case D: Not Specified** — Use question tool to ask user for dataset source.

### Stage 2: Model Training

> **Use CLI throughout**. `cloudrobo train create-task --config <JSON>` accepts full config JSON.
> **Naming uniqueness**: `name` and `output_models[0].model_name` must be globally unique; use timestamp suffix.

#### Step 2.1: Construct Training Config JSON

Write config JSON to temp file (avoid PowerShell special character issues):

```json
{
  "name": "so101-pen-train-<timestamp>",
  "train_mode": "MODEL_TUNING",
  "train_method": "FFT",
  "algorithm": {
    "algorithm_asset_id": "<algorithm_asset_id>",
    "algorithm_version_id": "<algorithm_version_id>"
  },
  "input_models": [{
    "model_asset_id": "<base_model_asset_id>",
    "version_id": "<base_model_version_id>",
    "source_type": "PUBLIC_MODEL_ASSET"
  }],
  "datasets": [{
    "source_type": "CUSTOM_DATASET_ASSET",
    "dataset_asset_id": "<dataset_asset_id>",
    "version_id": "<dataset_version_id>", 
    "dataset_name": "<dataset_name>"
  }],
  "output_models": [{
    "model_name": "so101-pen-output-<timestamp>",
    "model_type": "vla",
    "save_mode": "NEW_MODEL",
    "strict": false
  }],
  "spec": "Ascend: 1 * SNT9B2 | 24 vCPUs | 192 GiB",
  "cluster_id": "<cluster_id_from_stage1>",
  "workspace_id": "<workspace_id>",
  "parameters": "[{\"key\":\"batch_size\",\"desc\":\"批次大小\",\"value\":\"64\",\"constraint\":{\"type\":\"Integer\",\"editable\":true,\"required\":true,\"sensitive\":false}},{\"key\":\"steps\",\"desc\":\"训练步数\",\"value\":\"100000\",\"constraint\":{\"type\":\"Integer\",\"editable\":true,\"required\":true,\"sensitive\":false}},...]", 
  "env": "[]"
}
```

**Required fields**: `name` (unique), `train_mode` (fixed `MODEL_TUNING`), `train_method` (from model actions), `algorithm`, `input_models[0].source_type` (`PUBLIC_MODEL_ASSET`), `output_models[0].model_name` (unique), `output_models[0].model_type` (fixed `vla`), `spec` (string), `cluster_id` (pool ID with `pool-` prefix), `parameters` (JSON array string with full format from Step 1.1c).

**parameters construction**: From algorithm `ext_metadata.hyperparams`, construct full-format array preserving `desc` and `constraint` from the asset query:

```python
parameters = [
    {
        "key": hp["name"],
        "desc": hp.get("desc") or hp.get("description", ""),
        "value": str(custom_overrides.get(hp["name"], hp["default"])),
        "constraint": hp.get("constraint", {})
    }
    for hp in hyperparams
]
# Serialize to JSON string for the config
parameters_str = json.dumps(parameters, ensure_ascii=False)
```

> **Full format mandatory**: Each parameter item must include `key`, `desc`, `value`, and `constraint`. The `desc` and `constraint` come directly from the algorithm asset `ext_metadata.hyperparams` query results — do not fabricate or omit them.
> **OpenPI `data.rename_map`**: The `default` value is already single-quote-wrapped JSON string format. Use `default` value directly. For custom mapping, see `references/openpi-rename-map.md`.

**Resource specs**: Single card `Ascend: 1 * SNT9B2 | 24 vCPUs | 192 GiB`; Dual card `Ascend: 2 * SNT9B2 | 48 vCPUs | 384 GiB`. Use `SNT9B2` chip, not `Ascend-910B`.

#### Step 2.2: Submit Training Task

```python
import subprocess
with open("train_config.json", "r", encoding="utf-8") as f:
    config = f.read().strip()
result = subprocess.run(
    ["cloudrobo", "train", "create-task", "--config", config, "-v"],
    capture_output=True
)
print(result.stdout.decode("utf-8", errors="replace"))
```

Returns `{"task_id": "<task_id>"}`.

#### Step 2.3: Query Training Status

```bash
cloudrobo train show-task --task-id <task_id>
```

- `FINISHED` → proceed to Stage 3
- `FAILED`/`CREATE_FAILED`/`SUBMIT_FAILED` → see `references/fault-recovery.md`
- `WAITING`/`RUNNING`/`PENDING` → continue polling

```bash
cloudrobo train get-stages --task-id <task_id>  # View training stages
```

Stage flow: `scheduling` → `preparing` → `running` → `end`

#### Step 2.4: Extract Training Output Model

`output_models` returns `model_asset_id` and `version_id` at task creation (platform pre-creates). Get from `show-task` result. Model files become available after training FINISHED.

### Stage 3: Inference Deployment

> **Use CLI throughout** `cloudrobo infer create`.
> **Model source policy**: The model deployed here is the **training output — a space asset**
> (空间资产), so the **space-asset / Variant B path** of the `cloudrobo-infer` skill's
> "Model Source → Parameter Policy" table applies: parameters (`model-ext-metadata`,
> `skill-config-json`) are **required** and constructed explicitly.
> This is NOT an embodiment plaza model — do NOT apply the embodiment-plaza "core params only"
> rule here. If a user ever asks to deploy a model straight from the embodiment plaza inside this
> workflow, follow the `cloudrobo-infer` skill's Model Deployment Workflow Variant A instead
> (required core params only). See the `cloudrobo-infer` SKILL.md → "Model Source → Parameter
> Policy" table as the authoritative decision source.

#### Step 3.1: Query Available Resource Pools

```bash
cloudrobo resource list-pools
```

Filter pools where `usages` includes `MODEL_DEPLOYMENT`, `pool_type` is `DEDICATED` (preferred) or `SHARED`, and `nodes[].available_resources` > 0.

```bash
cloudrobo resource show-pool --pool-id <resource_id>
```

> `show-pool`'s `--pool-id` uses `resource_id` (without `pool-` prefix). `infer create`'s `--pool-id` **must use `pool-<uuid>` format** (with `pool-` prefix).

#### Step 3.2: Construct model_ext_metadata (Required)

> Must pass `model_feature_mapping` via `--model-ext-metadata`. Platform does not read asset version's ext_metadata. Not passing causes immediate FAILED.

See `references/model-ext-metadata.md` for full r2c templates and construction steps.

Key points:
1. Select r2c template by robot type
2. Read dataset `meta/info.json` for feature info
3. Dynamically modify `input_features`/`output_features`
4. OpenPI models: fixed 3-camera keys, copy `wrist_left` value to `wrist_right`
5. **Do not include `model_type` field**
6. `chunk_size` must match training `model.action-horizon` (OpenPI default 50)

#### Step 3.3: Create Inference Service

```bash
cloudrobo infer create --name "<infer-service-name>" --flavor "1 * SNT9B2 | 24 vCPUs | 192 GiB" --model-json '{"model_id":"<output_model_asset_id>","model_version_id":"<output_model_version_id>"}' --workspace-id <workspace_id> --pool-id "pool-<resource_id>" --pool-type DEDICATED --model-ext-metadata '<model_ext_metadata_json>' --skill-config-json '{"strict":true,"skills":[{"name":"<skill_name>","prompt":"<task_description>"}]}' --stop-schedule-json '{"duration":6,"time_unit":"HOURS"}' --deploy-timeout-minutes 30
```

> **flavor format**: `1 * SNT9B2 | 24 vCPUs | 192 GiB` (no `Ascend:` prefix).
> **`--pool-id` (required)**: Must use `pool-<uuid>` format. Using `resource_id` without prefix causes immediate FAILED.
> **`--pool-type` (required)**: Must use uppercase `DEDICATED` or `SHARED`.
> **`--model-json` (required)**: The model to deploy — `{"model_id":"<output_model_asset_id>","model_version_id":"<output_model_version_id>"}` (fields from Stage 2 training output).
> **`--model-ext-metadata` (required)**: Pass Step 3.2 constructed JSON. Do not include `model_type`.
> **`--skill-config-json` (important)**: Services for real-robot evaluation **must define skills**, otherwise dispatch `create-task` returns 500. Format: `{"strict":true,"skills":[{"name":"<skill_name>","prompt":"<task_description>"}]}`. `prompt` must match Stage 4 `--task` parameter exactly.
> **Do not pass `--internet-access-enable`**: Causes predict_url to only have `internet` type; dispatch needs `intranet` type URL.
> After creation, auto-enters `DEPLOYING`; no need to call `infer start`. If FAILED, call `infer start` to retry.

#### Step 3.4: Poll Inference Service Status

```bash
cloudrobo infer show --service-id <service_id>
```

- `RUNNING` → proceed to Stage 4
- `DEPLOYING` → continue polling
- `FAILED` → call `cloudrobo infer start --service-id <service_id>` to retry; see `references/fault-recovery.md`

### Stage 4: Real-Robot Evaluation

> **Timing**: Query robots only after inference service is RUNNING.
> **Key**: dispatch has no `create-session` command; **`session_id` is `workspace_id`**, no need to create session separately.

#### Step 4.0: Query Robots and Confirm Selection

```bash
cloudrobo robot list --workspace-id <workspace_id>
```

Query all robots in the workspace. Separate results into:
- **Online robots**: `status` = `ONLINE` and `type` matches the target robot type (e.g., `ARM`)
- **Offline robots**: `status` = `OFFLINE` or `INACTIVE`

**If online robots found** — use the question tool to ask user to confirm:

| Option | Description |
|--------|-------------|
| Use this online robot (Recommended) | Proceed directly with the selected online robot |
| Select an offline robot to bring online | Export certificate, guide robot-side onboarding, poll until ONLINE |
| Register a new robot | Create new robot, export certificate, guide onboarding, poll until ONLINE |

Display online robot details (name, type, manufacturer, model, status) for user reference. **Do not silently auto-select an online robot.**

**If no online robots found** — present offline robots (if any) and new registration option; ask user to choose(Do not ask whether it is necessary to switch to another workspace.).

> **Critical**: User confirmation is required before proceeding with any robot. Do not auto-select.
> Must pass `--workspace-id`. `status` values are uppercase `ONLINE`/`OFFLINE`/`INACTIVE`.
> For offline-robot onboarding and new-robot registration steps, see `references/robot-selection-guide.md`.

#### Step 4.1: Confirm session_id

**No need to create session**. `session_id = workspace_id`. Use `workspace_id` as `--session-id` directly.

```bash
cloudrobo dispatch list-tasks --session-id <workspace_id> --limit 1  # Verify
```

#### Step 4.2: Create and Execute Task

> **Key**: `create-task` simultaneously creates **and executes** the task. No separate `execute-task` command.

```bash
cloudrobo dispatch create-task --session-id <workspace_id> --name "<task_name>" --task "<task_description>" --constraints-json '{"model":{"exec_model_id":"<service_id>"},"robot_id":"<robot_id>","exec_constraints":{"max_iter_num":60,"max_run_time":5}}'
```

- `--session-id`: **Equals `workspace_id`**
- `--constraints-json` (required): JSON object containing:
  - `model.exec_model_id`: **Inference service ID** (`service_id`), not model asset ID
  - `robot_id`: the selected online robot ID
  - `exec_constraints`: execution limits, e.g. `{"max_iter_num":60,"max_run_time":5}`
- `--task`: Task description/skill prompt; if `skill_config.strict=true`, must exactly match a skill's `prompt`
- On Windows/PowerShell, must use Python subprocess to avoid JSON escaping issues

Extract `id` → `task_id` from response. Task auto-starts (status `RUNNING`).

#### Step 4.3: Poll Task Status

```bash
cloudrobo dispatch show-task --session-id <workspace_id> --task-id <task_id>
```

- `RUNNING` → continue polling
- `COMPLETED` → proceed to Stage 5
- `FAILED`/`CANCELLED` → see `references/fault-recovery.md`

> Status values are **uppercase**. Command is `show-task`, not `get-task-status`.

#### Step 4.4: View Execution Logs and Results

```bash
cloudrobo dispatch show-task-result --session-id <workspace_id> --task-id <task_id> --limit 100
```

### Stage 5: Result Output

Summarize and output full pipeline results: use case, base model, training method, hyperparams, dataset ID, training task ID, inference service ID, session ID, robot ID, evaluation score, and report. Partial pipelines output corresponding summary after the last stage completes.

### Long-Running Async Execution Strategy

Full pipeline takes hours to days. Use cronjob polling + checkpoint recovery.

**Polling intervals**: Training 30min/72h timeout; Inference 30min/2h timeout; Evaluation 30min/1h timeout. cronjob minimum interval 30 minutes. Include full pipeline state (all IDs) in prompt for Agent to determine current stage.

**Checkpoint recovery**: After session interruption: read pipeline state → query `current_stage` task status → continue waiting / enter next stage / fault recovery.

See `references/pipeline-templates.md` for pipeline state tracking template.

---

## Core Commands

| Stage | Command | Purpose |
|-------|---------|---------|
| 0 | `cloudrobo asset list-publication-assets --type model` | List marketplace models |
| 1 | `cloudrobo asset search-assets --keyword "<keyword>"` | Query model/dataset assets |
| 1 | `cloudrobo asset show-asset --asset-id <id>` | Get asset details + hyperparams |
| 1 | `cloudrobo asset create-asset` | Create dataset asset |
| 1 | `cloudrobo asset create-version` | Create asset version |
| 1 | `cloudrobo asset update-version --status RELEASE` | Publish version |
| 1 | `cloudrobo asset import-asset` | Import local dir to OBS |
| 1 | `cloudrobo workspace current` | Get current workspace + catalog_id |
| 2 | `cloudrobo train create-task --config <json>` | Create training task |
| 2 | `cloudrobo train show-task --task-id <id>` | Query training status |
| 2 | `cloudrobo train get-stages --task-id <id>` | Get training stages |
| 2 | `cloudrobo train get-events --task-id <id> --start-time <ms> --end-time <ms>` | Get training events (time range required, ms) |
| 3 | `cloudrobo resource list-pools` | List resource pools |
| 3 | `cloudrobo resource show-pool --pool-id <id>` | Get pool details |
| 3 | `cloudrobo infer create` | Create inference service |
| 3 | `cloudrobo infer show --service-id <id>` | Query service status |
| 3 | `cloudrobo infer start --service-id <id>` | Retry failed deployment |
| 3 | `cloudrobo infer list --workspace-id <id>` | List services |
| 3 | `cloudrobo infer list-logs --service-id <id>` | View service logs |
| 4 | `cloudrobo robot list --workspace-id <id>` | List robots |
| 4 | `cloudrobo robot show --robot-id <id>` | Verify robot status (re-confirm ONLINE before dispatch) |
| 4 | `cloudrobo robot create` | Register new robot (when user selects Option C) |
| 4 | `cloudrobo robot export-certificate --robot-id <id>` | Export access config for offline robot onboarding |
| 4 | `cloudrobo dispatch create-task` | Create and execute task |
| 4 | `cloudrobo dispatch show-task` | Query task status |
| 4 | `cloudrobo dispatch list-tasks` | List tasks |
| 4 | `cloudrobo dispatch show-task-result` | Get task result/logs |
| 4 | `cloudrobo dispatch cancel-task` | Cancel task |

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `workspace_id` | Yes | Active workspace ID | Set via `cloudrobo workspace use <id>` |
| `model_keyword` | Yes | Base model name for search | `LeRobot_PI05-Base` |
| `train_method` | Yes | From model actions | `FFT` or `LORA` |
| `spec` | Yes | Resource spec string | `Ascend: 1 * SNT9B2 \| 24 vCPUs \| 192 GiB` |
| `parameters` | Yes | Hyperparameter JSON array string | `[{"key":"batch_size","value":"32"}]` |
| `pool_id` | Yes (Stage 3) | Resource pool ID with `pool-` prefix | `pool-d1cc6d45-...` |
| `pool_type` | Yes (Stage 3) | Pool type uppercase | `DEDICATED` or `SHARED` |
| `model_ext_metadata` | Yes (Stage 3) | Feature mapping JSON string | See `references/model-ext-metadata.md` |
| `skill_config_json` | Yes (Stage 3) | Skill definition for dispatch | `{"strict":true,"skills":[...]}` |
| `service_id` | Yes (Stage 4) | Inference service ID | From `infer create` response |
| `robot_id` | Yes (Stage 4) | Online robot ID | From `robot list` response |
| `task` | Yes (Stage 4) | Task description/prompt | `"Insert the pen into the pen holder"` |

> **Stage 3 parameters context**: `model_ext_metadata` and `skill_config_json` are **required in
> this workflow** because the deployed model is a **space asset** (training output) and real-robot
> evaluation (Stage 4) depends on them. This follows the `cloudrobo-infer` skill's
> **space-asset / Variant B** path of its "Model Source → Parameter Policy" table. When deploying
> an **embodiment plaza model**, use the `cloudrobo-infer` skill's Variant A instead — carry
> required core params only and **do not** pass `model_ext_metadata`/`skill_config_json`.

---

## Reference Documents

- `references/cli-installation-guide.md` — CloudRobo CLI installation and configuration
- `references/iam-policies.md` — Least-privilege IAM policies for CloudRobo
- `references/dataflow-diagram.md` — Mermaid data flow diagrams for pipeline
- `references/pipeline-templates.md` — Quick reference templates and hyperparameter configs
- `references/openpi-rename-map.md` — OpenPI model data.rename_map construction guide
- `references/model-ext-metadata.md` — model_ext_metadata construction with r2c templates
- `references/fault-recovery.md` — Fault recovery for training, inference, and evaluation
- `references/robot-selection-guide.md` — Detailed robot selection, offline onboarding, and new robot registration steps
- `references/constraints.md` — Full constraints and rules list
- `references/verification-method.md` — Verification methods and CLI command reference
- `references/acceptance-criteria.md` — Acceptance criteria for pipeline execution

---

## KooCLI Command Format Standard

```bash
cloudrobo <Service> <Operation> [--params]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | cloudrobo service name | `asset`, `train`, `infer`, `dispatch`, `robot`, `resource`, `workspace` |
| Operation name | Kebab-case operation | `search-assets`, `create-task`, `show-task` |
| Simple parameter | `--key=value` | `--keyword="LeRobot_PI05-Base"` |
| JSON parameter | `--key='<json>'` | `--config '{"name":"..."}'` |
| Region | N/A (cloudrobo uses workspace) | Set via `cloudrobo workspace use <id>` |

> On Windows/PowerShell, complex JSON parameters should be written to file and called via Python subprocess to avoid shell escaping issues.

---

## Verification

- **Execution mode**: Correctly identify user intent and corresponding stage range
- **Skip-stage inputs**: All required preceding parameters provided when starting from intermediate stage
- **End-to-end**: Complete Stage 0-5 — training FINISHED → inference RUNNING → evaluation COMPLETED
- **Hyperparameter confirmation**: Step 1.1c showed defaults and asked user; **data.rename_map**: OpenPI executed Step 1.1d with single-quote-wrapped compact JSON
- **Dataset processing**: Local dir uploaded, version RELEASE, training doesn't report "dataset not ready"
- **Asset handoff**: Each stage output ID correctly passed to next stage
- **Training**: CLI `create-task` returns `task_id`, status not `CREATE_FAILED`; eventually `FINISHED`
- **Inference**: `infer show` status `RUNNING`; `pool_id` uses `pool-<uuid>` format, `pool_type` uppercase, pool supports `MODEL_DEPLOYMENT`; `model_ext_metadata` constructed from r2c template + dataset info, no `model_type` field, `chunk_size` matches `model.action-horizon`, gripper uses `end_effector_states.position`
- **Real-robot evaluation**: Step 4.0 used question tool to confirm robot selection (no silent auto-select); `dispatch show-task` status `COMPLETED`; `session_id` = `workspace_id`; `constraints-json` `model.exec_model_id` is service ID; inference service has `skill_config` with non-empty skills; predict_url includes `intranet` type
- **Checkpoint recovery**: Pipeline state can resume after session interruption

See `references/verification-method.md` and `references/acceptance-criteria.md` for detailed checklists.
