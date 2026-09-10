# Verification Method — CloudRobo Model Workflow

## Pipeline Stage Verification

### Stage 0-1: Asset Query Verification

```bash
# Verify model asset exists
cloudrobo asset search-assets --keyword "<model_keyword>"
# Expected: Returns asset with id and latest_version_id

# Verify algorithm details
cloudrobo asset show-asset --asset-id <algorithm_asset_id>
# Expected: Returns ext_metadata.hyperparams

# Verify dataset is RELEASE
cloudrobo asset show-asset --asset-id <dataset_asset_id>
# Expected: version status is RELEASE
```

### Stage 2: Training Verification

```bash
# Verify training task created
cloudrobo train show-task --task-id <task_id>
# Expected: status is WAITING/RUNNING/PENDING (not CREATE_FAILED)

# Verify training completed
cloudrobo train show-task --task-id <task_id>
# Expected: status is FINISHED

# Verify output model available
cloudrobo train show-task --task-id <task_id>
# Expected: output_models[0] has model_asset_id and version_id
```

### Stage 3: Inference Verification

```bash
# Verify inference service running
cloudrobo infer show --service-id <service_id>
# Expected: status is RUNNING

# Verify pool supports MODEL_DEPLOYMENT
cloudrobo resource list-pools
# Expected: selected pool usages includes MODEL_DEPLOYMENT
```

### Stage 4: Evaluation Verification

```bash
# Verify robot selection confirmation was performed
# Expected: question tool was used to ask user (use online / bring offline online / register new)

# Verify robot is online
cloudrobo robot list --workspace-id <workspace_id>
# Expected: selected robot status is ONLINE (uppercase)

# Verify robot status re-confirmed before dispatch
cloudrobo robot show --robot-id <robot_id>
# Expected: status is ONLINE (uppercase) at time of dispatch

# Verify task completed
cloudrobo dispatch show-task --session-id <workspace_id> --task-id <task_id>
# Expected: status is COMPLETED (uppercase)
```

## End-to-End Verification Checklist

| Check | Verification Method |
|-------|-------------------|
| Execution mode correctly identified | User intent matches selected stages |
| Skip-stage inputs provided | All required preceding parameters provided |
| Hyperparameter confirmation | Step 1.1c showed defaults and asked user |
| data.rename_map (OpenPI) | Step 1.1d executed, value is single-quote-wrapped compact JSON |
| Dataset processing | Local dir uploaded, version RELEASE, training doesn't report "dataset not ready" |
| Asset handoff | Each stage's output ID correctly passed to next stage |
| Training creation | CLI `create-task` returns `task_id`, status not `CREATE_FAILED` |
| Training completion | `show-task` status is `FINISHED` |
| Inference running | `infer show` status is `RUNNING` |
| model_ext_metadata | r2c template selected, dataset meta/info.json read, model_feature_mapping dynamically constructed |
| OpenPI camera handling | 3 fixed camera keys, wrist_right copies wrist_left value |
| Gripper mapping | Uses `end_effector_states.position` |
| chunk_size consistency | Matches training `model.action-horizon` |
| No model_type field | ext_metadata does not contain model_type |
| pool_id format | Uses `pool-<uuid>` format with prefix |
| pool_type case | Uppercase `DEDICATED`/`SHARED` |
| pool supports deployment | usages includes `MODEL_DEPLOYMENT` |
| Evaluation completed | `dispatch show-task` status is `COMPLETED` |
| Robot selection confirmation | Step 4.0 used question tool to ask user; no silent auto-select |
| Robot status re-confirmed | `robot show` confirmed ONLINE right before dispatch |
| session_id | Equals workspace_id |
| constraints-json model.exec_model_id | Is inference service_id, not model asset ID |
| skill_config | Defined with non-empty skills |
| predict_url | Contains intranet type |
| Checkpoint recovery | Pipeline state can resume after session interruption |

## CLI Command Reference

| Stage | CLI Command | Purpose |
|-------|-----------|---------|
| Asset | `cloudrobo asset search-assets` | Query model/dataset assets |
| Asset | `cloudrobo asset show-asset` | Get asset details + hyperparams |
| Asset | `cloudrobo asset list-publication-assets` | List marketplace models |
| Asset | `cloudrobo asset create-asset` | Create dataset asset |
| Asset | `cloudrobo asset create-version` | Create asset version |
| Asset | `cloudrobo asset update-version` | Update version status |
| Asset | `cloudrobo asset import-asset` | Import local dir to OBS |
| Workspace | `cloudrobo workspace current` | Get current workspace |
| Training | `cloudrobo train create-task` | Create training task |
| Training | `cloudrobo train show-task` | Query training status |
| Training | `cloudrobo train get-stages` | Get training stages |
| Training | `cloudrobo train get-events` | Get training events |
| Inference | `cloudrobo infer create` | Create inference service |
| Inference | `cloudrobo infer show` | Query service status |
| Inference | `cloudrobo infer start` | Retry failed deployment |
| Inference | `cloudrobo infer list` | List services |
| Inference | `cloudrobo infer list-logs` | View service logs |
| Resource | `cloudrobo resource list-pools` | List resource pools |
| Resource | `cloudrobo resource show-pool` | Get pool details |
| Robot | `cloudrobo robot list` | List robots |
| Dispatch | `cloudrobo dispatch create-task` | Create and execute task |
| Dispatch | `cloudrobo dispatch show-task` | Query task status |
| Dispatch | `cloudrobo dispatch list-tasks` | List tasks |
| Dispatch | `cloudrobo dispatch show-task-result` | Get task result/logs |
| Dispatch | `cloudrobo dispatch cancel-task` | Cancel task |
