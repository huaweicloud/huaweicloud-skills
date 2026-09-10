# Constraints

## General

- **Use CLI commands throughout**; Python SDK is prohibited
- **On Windows/PowerShell**, when passing complex JSON parameters containing `|`/`"`, write JSON to file and use Python subprocess to call CLI
- Agent must first determine execution scope (full/partial pipeline) before starting
- When starting from an intermediate stage, user must provide all required preceding output parameters
- When user does not specify a model, must query marketplace preset models and ask user to choose
- **After getting default hyperparameters, must ask user whether to modify** (Step 1.1c); do not silently use defaults
- `parameters` keys must come from algorithm `ext_metadata.hyperparams`; fabricating keys is prohibited
- Custom hyperparameters override defaults; unspecified ones keep default values
- `name` and `output_models[0].model_name` must be globally unique; use timestamp suffix
- Long-running pipelines must save pipeline state to support checkpoint recovery
- When user does not specify a dataset, must ask; do not assume

## Training

- `train_method` extracted from model `actions[].action` (`FFT`/`LORA`), not `SFT`
- `spec` is a string (`Ascend: 1 * SNT9B2 | 24 vCPUs | 192 GiB`), not JSON
- Use `SNT9B2` chip, not `Ascend-910B`

## Dataset

- **Local directory dataset import-asset requires README.md** (containing `ext_metadata.annotation_status: true`)
- **After import-asset, must manually `update-version --status RELEASE`**, otherwise training reports "dataset not ready"

## Inference Deployment

- **Model source policy (authoritative from `cloudrobo-infer` skill)**: model source decides which `infer create` params to carry. **Space asset / custom models** (incl. training output): run parameter auto-discovery and pass discovered params explicitly (in this workflow `model-ext-metadata` + `skill-config-json` are required). **Embodiment plaza models (具身广场)**: carry **required core params only** (`--name`, `--flavor`, `--model-json`, `--workspace-id`, `--pool-id`, `--pool-type`, `--stop-schedule-json`) and do NOT pass `--cmd`/`--image-swr-url`/`--envs-json`/`--skill-config-json`/`--service-invoke-json`/`--readiness-health-json`/`--model-ext-metadata`/`--model-json.mount_path` — these are pre-configured on the platform for plaza models (不该带的参数不要带). See `cloudrobo-infer` SKILL.md → "Model Source → Parameter Policy"
- Inference service `flavor` format: `1 * SNT9B2 | 24 vCPUs | 192 GiB` (no `Ascend:` prefix)
- `--pool-id` must use `pool-<uuid>` format (with `pool-` prefix); using `resource_id` without prefix causes immediate FAILED
- `--pool-type` must use uppercase `DEDICATED` or `SHARED`; lowercase may cause `Invalid parameter: pool_id`
- Before creating inference service, must use `resource list-pools` to confirm pool `usages` includes `MODEL_DEPLOYMENT`
- Must pass `model_feature_mapping` via `--model-ext-metadata`; platform does not read asset version's ext_metadata
- `model_feature_mapping` is dynamically constructed from r2c template and dataset `meta/info.json`
- **Do not include `model_type` field** in `model_ext_metadata`
- **Gripper (gripper) must use `end_effector_states.position`** mapping; arm joints use `joint_states.position`
- **`chunk_size` must match training hyperparameter `model.action-horizon`** (OpenPI default 50)
- OpenPI models require fixed 3-camera keys (`observation.images.front`/`wrist_left`/`wrist_right`); with 2 cameras, copy `wrist_left` value to `wrist_right`
- `skill_config` with `strict:true` + empty `skills:[]` causes 400 error; use `strict:false` or provide at least one skill
- **Inference services for real-robot evaluation must define `skill_config` with non-empty `skills`**: dispatch system matches tasks via skills; empty skills causes `create-task` to return 500 Internal error
- **Do not pass `--internet-access-enable`** when creating inference services for evaluation: it causes predict_url to only have `internet` type; dispatch system needs `intranet` type URL
- **`model_feature_mapping` image `dtype` should be `uint8`** (not `float32`), matching robot real-time observation data format
- **`wrist_left` value should be `observations.images.color.wrist_left`, `wrist_right` value should be `observations.images.color.wrist_right`**; do not map both to `observations.images.color.wrist`
- After creating inference service, it auto-enters DEPLOYING; if it becomes FAILED, call `infer start` to retry without deleting

## Real-Robot Evaluation

- Robot status must be `ONLINE` (uppercase) to create evaluation tasks
- `robot_id` queried after inference service is RUNNING; must pass `--workspace-id`
- **Do not silently auto-select an online robot**: After querying robots, must use the question tool to ask user whether to use the online robot, bring an offline robot online, or register a new robot (see `references/robot-selection-guide.md`)
- **Bringing offline robot online requires**: export-certificate → robot-side onboarding with `r2c_sdk` → poll until `ONLINE`
- **Registering new robot requires**: user provides name/type/manufacturer/model → robot create → export-certificate → onboarding → poll until `ONLINE`
- **dispatch has no `create-session` command; `session_id` is `workspace_id`**, use `workspace_id` as `--session-id` directly
- **`dispatch create-task` simultaneously creates and executes task**; no separate `execute-task` command
- `dispatch create-task`'s `model.exec_model_id` (inside required `--constraints-json`) is the **inference service ID** (`service_id`), not model asset ID; the JSON also carries `robot_id` and `exec_constraints` (e.g. `{"model":{"exec_model_id":"<service_id>"},"robot_id":"<robot_id>","exec_constraints":{"max_iter_num":60,"max_run_time":5}}`)
- `dispatch create-task`'s `--task` parameter is the task description/skill prompt; if `skill_config.strict=true`, must exactly match a skill's `prompt`
- **dispatch CLI command names**: `show-task` (not `get-task-status`), `show-task-result`, `list-tasks`, `create-task`, `cancel-task`
- **dispatch task status values are uppercase**: `RUNNING`/`COMPLETED`/`FAILED`/`CANCELLED`

## OpenPI Model

- OpenPI models (PI0/PI05-Base) require `data.rename_map` parameter; value format is single-quote-wrapped compact JSON: `'{"key":"value",...}'`
- `data.rename_map` JSON must use `separators=(',',':')` to generate compact format (no spaces), otherwise server-side validation rejects
- `data.rename_map` can be omitted (`required: false`); when omitted, algorithm uses default (all 5 standard keys self-mapped)
