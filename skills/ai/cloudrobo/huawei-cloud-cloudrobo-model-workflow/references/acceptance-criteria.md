# Acceptance Criteria — CloudRobo Model Workflow

## Pipeline Execution Readiness

| # | Criterion | Stage | Status |
|---|-----------|-------|--------|
| 1 | Execution mode correctly identified (full/partial pipeline) | Stage 0 | ⬜ |
| 2 | Robot type and task description extracted from user input | Stage 0 | ⬜ |
| 3 | Model selected (user-specified or from marketplace with user confirmation) | Stage 0 | ⬜ |
| 4 | Dataset source parsed and processed | Stage 1 | ⬜ |
| 5 | Base model asset_id and version_id extracted | Stage 1 | ⬜ |
| 6 | Algorithm asset_id and version_id extracted from model actions | Stage 1 | ⬜ |
| 7 | train_method extracted from model actions (FFT/LORA) | Stage 1 | ⬜ |
| 8 | Default hyperparameters displayed and user confirmed | Stage 1 | ⬜ |
| 9 | data.rename_map constructed for OpenPI models (if applicable) | Stage 1 | ⬜ |
| 10 | Dataset version status is RELEASE | Stage 1 | ⬜ |
| 11 | Training config JSON constructed with all required fields | Stage 2 | ⬜ |
| 12 | name and model_name are globally unique (timestamp suffix) | Stage 2 | ⬜ |
| 13 | Training task created, returns task_id | Stage 2 | ⬜ |
| 14 | Training status is FINISHED | Stage 2 | ⬜ |
| 15 | Output model asset_id and version_id extracted | Stage 2 | ⬜ |
| 16 | Resource pool supports MODEL_DEPLOYMENT | Stage 3 | ⬜ |
| 17 | pool_id uses pool-<uuid> format with prefix | Stage 3 | ⬜ |
| 18 | pool_type is uppercase DEDICATED/SHARED | Stage 3 | ⬜ |
| 19 | model_ext_metadata constructed from r2c template + dataset info | Stage 3 | ⬜ |
| 20 | model_ext_metadata does not contain model_type field | Stage 3 | ⬜ |
| 21 | chunk_size matches training model.action-horizon | Stage 3 | ⬜ |
| 22 | Gripper uses end_effector_states.position | Stage 3 | ⬜ |
| 23 | skill_config defined with non-empty skills | Stage 3 | ⬜ |
| 24 | --internet-access-enable NOT passed | Stage 3 | ⬜ |
| 25 | Inference service status is RUNNING | Stage 3 | ⬜ |
| 26 | Robot status is ONLINE (uppercase) | Stage 4 | ⬜ |
| 27 | Robot selection confirmed by user (no silent auto-select) | Stage 4 | ⬜ |
| 28 | session_id = workspace_id (no create-session) | Stage 4 | ⬜ |
| 29 | create-task constraints-json model.exec_model_id is service_id | Stage 4 | ⬜ |
| 30 | --task matches skill prompt (if strict=true) | Stage 4 | ⬜ |
| 31 | Task status is COMPLETED (uppercase) | Stage 4 | ⬜ |
| 32 | Evaluation results output with full pipeline IDs | Stage 5 | ⬜ |
| 33 | Pipeline state saved for checkpoint recovery | All | ⬜ |

## Quality Gates

| Gate | Must Pass Before |
|------|------------------|
| Stage 0 complete (use case parsed) | Starting Stage 1 |
| Stage 1 complete (assets queried, dataset ready) | Starting Stage 2 |
| Stage 2 complete (training FINISHED) | Starting Stage 3 |
| Stage 3 complete (inference RUNNING) | Starting Stage 4 |
| Stage 4 complete (evaluation COMPLETED) | Starting Stage 5 |
| All stages complete | Pipeline declared done |

## Partial Pipeline Gates

| Mode | Required Inputs | Output |
|------|----------------|--------|
| Train+Deploy | base_model_asset_id, dataset_asset_id | service_id |
| Deploy+Eval | output_model_asset_id, output_model_version_id | task_result |
| Full pipeline | robot_type, task_description | Full evaluation report |
