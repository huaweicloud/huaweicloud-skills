# Pipeline Templates & Quick Reference

---

## Use Case Mapping

### Robot to Recommended Model

| Robot | Recommended Model | Dataset Format | Needs rename_map |
|------|-------------------|----------------|-----------------|
| so101 / jaka / franka / general | `LeRobot_PI05-Base` | LeRobot v3 | No |
| User-specified OpenPI | `Physical-Intelligence_PI05-Base` | Requires mapping | Yes |

### Dataset Source Processing

| Source | Processing |
|--------|-----------|
| Registered asset | `cloudrobo asset search-assets --keyword "<name>"` |
| OBS path | `cloudrobo asset create-asset` + `create-version` + `update-version --status RELEASE` |
| Local directory | `cloudrobo asset import-asset` (requires README.md) + `update-version --status RELEASE` |
| Not specified | **Must ask user** |

---

## Template A: SO101 Pen Insertion (Default Hyperparameters, CLI)

### Stage 0: Parse

```
User input: "I want to train a real-robot task using so101 for pen insertion"
Parse result:
  robot_type:       so101
  task_description: pen insertion into pen holder
  model_keyword:    LeRobot_PI05-Base  (recommended)
  dataset_source:   need_ask (must ask)
```

### Stage 1: Query Assets and Process Dataset

```bash
# Query base model
cloudrobo asset search-assets --keyword "LeRobot_PI05-Base"

# Query algorithm asset details (get default hyperparameters)
cloudrobo asset show-asset --asset-id <algorithm_asset_id>

# Import local directory dataset
cloudrobo asset import-asset --catalog-id <catalog_id> --type dataset --local-path <local_path> --name <dataset_name>

# Publish dataset version (required! otherwise training reports "dataset not ready")
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

Extract: `base_model_asset_id/version_id`, `algorithm_asset_id/version_id`, `train_method`, `dataset_asset_id/version_id`, `default_hyperparams`

### Step 1.1c: Hyperparameter Confirmation

Display default hyperparameters to user, ask whether to modify. After user selects default or custom, construct `parameters` field.

### Stage 2: Training (CLI)

Write config JSON to file, use Python subprocess to call CLI:

```python
import subprocess

config = '{"name":"so101-pen-train-<ts>","train_mode":"MODEL_TUNING","train_method":"FFT","algorithm":{"algorithm_asset_id":"<id>","algorithm_version_id":"<id>"},"input_models":[{"model_asset_id":"<id>","version_id":"<id>","source_type":"PUBLIC_MODEL_ASSET"}],"datasets":[{"source_type":"DATASET","dataset_asset_id":"<id>","version_id":"<id>"}],"output_models":[{"model_name":"so101-pen-output-<ts>","model_type":"vla","save_mode":"NEW_MODEL","strict":false}],"spec":"Ascend: 1 * SNT9B2 | 24 vCPUs | 192 GiB","workspace_id":"<id>","parameters":"[{\"key\":\"batch_size\",\"value\":\"32\"},...]"}'

result = subprocess.run(
    ["cloudrobo", "train", "create-task", "--config", config, "-v"],
    capture_output=True
)
print(result.stdout.decode("utf-8", errors="replace"))
# Returns: {"task_id": "<task_id>"}
```

Polling:
```bash
cloudrobo train show-task --task-id <task_id>
cloudrobo train get-stages --task-id <task_id>
```

Extract output model: Get `model_asset_id` + `version_id` from `show-task` result's `output_models[0]`.

### Stage 3: Inference Deployment (CLI)

```bash
# Query available resource pools
cloudrobo resource list-pools
# Select pool with usages including MODEL_DEPLOYMENT

# Query existing services for reference
cloudrobo infer list --workspace-id <workspace_id>

# Construct model_ext_metadata (required):
# 1. Select r2c template based on robot type (see references/model-ext-metadata.md)
# 2. Read training dataset meta/info.json for feature info (shape, joint names, camera keys)
# 3. Use r2c template as base, dynamically modify input_features/output_features
# 4. OpenPI models: fixed 3-camera keys (front/wrist_left/wrist_right),
#    with 2 cameras copy wrist_left value to wrist_right
# 5. Combine into JSON string, pass via --model-ext-metadata

# Create inference service
cloudrobo infer create --name "so101-pen-infer-<ts>" --flavor "1 * SNT9B2 | 24 vCPUs | 192 GiB" --model-json '{"model_id":"<id>","model_version_id":"<id>"}' --workspace-id <id> --pool-id "pool-<resource_id>" --pool-type DEDICATED --model-ext-metadata '<model_ext_metadata_json>' --skill-config-json '{"strict":true,"skills":[{"name":"<skill_name>","prompt":"<task_description>"}]}' --stop-schedule-json '{"duration":6,"time_unit":"HOURS"}' --deploy-timeout-minutes 30

# Poll status
cloudrobo infer show --service-id <service_id>

# If status is FAILED, call start to retry deployment (FAILED -> DEPLOYING)
cloudrobo infer start --service-id <service_id>
```

### Stage 4: Real-Robot Evaluation (CLI)

```bash
# Query online robots
cloudrobo robot list --workspace-id <workspace_id>

# No need to create session; session_id = workspace_id

# Create and execute task (create-task simultaneously creates AND executes)
cloudrobo dispatch create-task --session-id <workspace_id> --name "<task_name>" --task "<task_description>" --constraints-json '{"model":{"exec_model_id":"<service_id>"},"robot_id":"<robot_id>","exec_constraints":{"max_iter_num":60,"max_run_time":5}}'

# Poll status (command is show-task, not get-task-status)
cloudrobo dispatch show-task --session-id <workspace_id> --task-id <task_id>

# View execution logs and results
cloudrobo dispatch show-task-result --session-id <workspace_id> --task-id <task_id> --limit 50
```

### Stage 5: Output Results

Summarize score, report, and full pipeline IDs.

---

## Template B: Custom Hyperparameters

In Stage 2, when constructing parameters, use default hyperparameters as base, override with user-specified values:

```python
# User specifies: policy.optimizer_lr=0.0001, batch_size=16, steps=50000
custom_overrides = {"policy.optimizer_lr": "0.0001", "batch_size": "16", "steps": "50000"}

parameters = [
    {"key": hp.name, "value": custom_overrides.get(hp.name, str(hp.default))}
    for hp in hyperparams
]
```

Other stages are the same as Template A.

---

## Template C: OpenPI Model + data.rename_map

User input: "Train so101 pen insertion task with Physical-Intelligence_PI05-Base"

Stage 1 queries `Physical-Intelligence_PI05-Base`, extracts FFT algorithm info from its `actions`.

### Step 1.1d: Construct data.rename_map

See `references/openpi-rename-map.md` for full construction details.

### Stage 2: Training (with data.rename_map)

parameters includes `data.rename_map`, value is single-quote-wrapped compact JSON:

```json
{"key": "data.rename_map", "value": "'{\"observation.images.front\":\"observation.images.front\",\"observation.images.wrist_left\":\"observation.images.wrist_left\",\"observation.images.wrist_right\":\"observation.images.wrist_right\",\"observation.state\":\"observation.state\",\"action\":\"actions\"}'"}
```

---

## Template D: LoRA Training

Stage 1 selects algorithm info with `action=LORA` from model `actions`. Stage 2 uses `train_method=LORA`. Can pass LoRA-specific hyperparameters in parameters (e.g., `lora_rank`, `lora_alpha`, per algorithm hyperparams).

---

## Common Hyperparameter Reference

> The following are default hyperparameter examples for LeRobot PI05 FFT algorithm. Actual values are subject to `show-asset` query results.

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `batch_size` | `32` | Integer | Batch size |
| `steps` | `100000` | Integer | Training steps |
| `save_freq` | `10000` | Integer | Save frequency |
| `policy.chunk_size` | `50` | Integer | Action sequence length |
| `policy.n_action_steps` | `50` | Integer | Execution action steps |
| `policy.n_obs_steps` | `1` | Integer | Observation steps |
| `policy.dtype` | `bfloat16` | String | Precision (`bfloat16`/`float32`) |
| `policy.optimizer_lr` | `2.5e-05` | Float | Initial learning rate |
| `policy.scheduler_decay_lr` | `2.5e-06` | Float | Decay learning rate |
| `policy.scheduler_warmup_steps` | `1000` | Integer | Warmup steps |
| `policy.scheduler_decay_steps` | `30000` | Integer | Decay steps |
| `data.rename_map` | `'{"observation.images.front":"observation.images.front",...,"action":"actions"}'` | String | Field remapping (OpenPI only, single-quote-wrapped compact JSON) |

> Fabricating parameter keys is prohibited — all keys must come from `cloudrobo asset show-asset` returned `ext_metadata.hyperparams[].name`.

---

## Resource Specifications

| Spec | spec String | Applicable Scenario |
|------|------------|---------------------|
| Single card | `Ascend: 1 * SNT9B2 \| 24 vCPUs \| 192 GiB` | Recommended |
| Dual card | `Ascend: 2 * SNT9B2 \| 48 vCPUs \| 384 GiB` | Large model/dataset |

> `spec` is a plain string. Inference service `flavor` format is the same but without `Ascend:` prefix.

---

## Training Method Selection

| Method | action Name | Resource Usage | Applicable Scenario |
|--------|-----------|---------------|---------------------|
| Full fine-tuning | `FFT` | High | Best quality |
| LoRA fine-tuning | `LORA` | Medium | Faster training, lower resources |

> `train_method` comes from model `actions[].action`, not `SFT`/`QLORA`.

---

## Pipeline State Tracking Template

```json
{
  "use_case": "so101 pen insertion real-robot task",
  "current_stage": 2,
  "workspace_id": "<id>",
  "train_task_id": "<task_id>",
  "output_model": {"asset_id": "<id>", "version_id": "<id>"},
  "service_id": null,
  "robot_id": null,
  "session_id": null,
  "eval_task_id": null
}
```

---

## Polling Interval Reference

| Stage | CLI Command | Interval | Terminal State | Timeout |
|-------|-----------|----------|---------------|---------|
| Training | `cloudrobo train show-task --task-id <id>` | 30min | `FINISHED`/`FAILED` | 72h |
| Inference | `cloudrobo infer show --service-id <id>` | 30min | `RUNNING`/`FAILED` | 2h |
| Evaluation | `cloudrobo dispatch show-task --session-id <id> --task-id <id>` | 30min | `COMPLETED`/`FAILED`/`CANCELLED` | 1h |
