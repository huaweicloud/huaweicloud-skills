# Verification Method

## Verification Levels

### Level 1: CLI Smoke Test

Verify the CLI is installed and authenticated:

```bash
# Should return JSON list (possibly empty)
cloudrobo train list-tasks

# Should return algorithm list (for pretrain)
cloudrobo asset list-publication-assets --type algorithm

# Should return model list (for finetune base model)
cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type model

# Should return task counts by status
cloudrobo train stats --workspace-id <workspace-id>

# SimRL equivalents
cloudrobo train list-tasks --sim-rl
cloudrobo train stats --workspace-id <workspace-id> --sim-rl
```

**Pass criteria**: Command exits 0, returns valid JSON.

### Level 2: Task Lifecycle Test (Fine-tuning)

End-to-end test of a finetune task:

```bash
# 1. Query base model
cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type model
# → Extract asset_id, version_id

# 2. Query dataset
cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type dataset
# → Extract dataset_asset_id, version_id, url_path

# 3. Create task (user must confirm) — method/model/dataset/spec are expressed
#    inside the --config JSON (train_mode MODEL_TUNING, method LORA, etc.)
cloudrobo train create-task --config '<task-json>'
# → Returns task_id

# 5. Poll status (30-60s interval)
cloudrobo train show-task --task-id <task-id>
# → Repeat until FINISHED or FAILED

# 6. Verify stages
cloudrobo train get-stages --task-id <task-id>
# → Returns SCHEDULING → PREPARING → RUNNING → END

# 7. Verify resource usage (requires metric/start/end, timestamps in seconds)
cloudrobo train get-resource-usage --task-id <task-id> --metric cpu_util --start <start-timestamp-seconds> --end <end-timestamp-seconds>
# → Returns CPU/GPU/NPU utilization

# 8. Verify events (requires start-time/end-time, timestamps in milliseconds)
cloudrobo train get-events --task-id <task-id> --start-time <start-timestamp-milliseconds> --end-time <end-timestamp-milliseconds>
# → Returns event list

# 9. View logs
cloudrobo train get-logs --task-id <task-id> --file-name <log-file>
# → Returns log content

# 10. Get signed URL (requires file-source/file-name)
cloudrobo train get-signed-url --task-id <task-id> --file-source TRAIN --file-name <log-file>
# → Returns OBS temp download URL

# 11. Clean up (user must confirm)
cloudrobo train delete-tasks --task-id <task-id>
```

**Pass criteria**: Task reaches FINISHED, stages show 4-phase flow, resource usage returns data, events/logs accessible.

### Level 3: Draft Lifecycle Test

Test the draft save & resubmit flow:

```bash
# 1. Save draft (only name + workspace_id required)
cloudrobo train save-draft --config '{"name":"verify-draft","workspace_id":"<ws-id>"}'
# → Returns task_id, status = DRAFT

# 2. Verify DRAFT status
cloudrobo train show-task --task-id <draft-id>
# → status = DRAFT

# 3. Resubmit via restart (CLI resubmits existing config by default)
cloudrobo train restart-task --task-id <draft-id>
# → Task leaves DRAFT, enters CREATING

# 4. To edit config before resubmit, use CLI --config:
#    cloudrobo train restart-task --task-id <draft-id> --config '{"spec":"Ascend: 2 * SNT9B2"}'
# Or use SDK for full body control:
#    client.restart_train_task(task_id, req)
```

**Pass criteria**: Draft saved with DRAFT status, restart transitions task out of DRAFT.

### Level 4: Failure Diagnosis Test

Test diagnosis on a FAILED/RUN_FAILED task:

```bash
# 1. Get task detail to confirm failure
cloudrobo train show-task --task-id <failed-task-id>

# 2. Get stages to identify failed stage
cloudrobo train get-stages --task-id <failed-task-id>
# → Identify which stage: SCHEDULING/PREPARING/RUNNING/END

# 3. Get Error events (requires start-time/end-time in milliseconds)
cloudrobo train get-events --task-id <failed-task-id> --start-time <start-timestamp-milliseconds> --end-time <end-timestamp-milliseconds> --level Error
# → Filter for level=Error

# 4. Get logs
cloudrobo train get-logs --task-id <failed-task-id>
# → Detailed error output
```

**Pass criteria**: Failed stage identified, Error events accessible, logs contain error details.

### Level 5: SimRL Lifecycle Test

Test the SimRL task surface via `--sim-rl`:

```bash
# 1. Count SimRL tasks by status
cloudrobo train stats --workspace-id <ws-id> --sim-rl

# 2. List SimRL tasks
cloudrobo train list-tasks --sim-rl

# 3. Create SimRL task (user must confirm)
cloudrobo train create-task --config '<sim-rl-json>' --sim-rl
# → Returns task_id

# 4. Show SimRL task
cloudrobo train show-task --task-id <task-id> --sim-rl

# 5. Monitor (same required params as train; no get-stages — SimRL has no stages endpoint)
cloudrobo train get-resource-usage --task-id <task-id> --metric cpu_util --start <ts-seconds> --end <ts-seconds> --sim-rl
cloudrobo train get-events --task-id <task-id> --start-time <ts-milliseconds> --end-time <ts-milliseconds> --sim-rl
cloudrobo train get-logs --task-id <task-id> --sim-rl
cloudrobo train get-signed-url --task-id <task-id> --file-source TRAIN --file-name <name> --sim-rl

# 6. Lifecycle (user must confirm)
cloudrobo train stop-task --task-id <task-id> --sim-rl
cloudrobo train restart-task --task-id <task-id> --sim-rl
cloudrobo train clone-task --task-id <task-id>
cloudrobo train update-task --task-id <task-id> --config '<update-json>' --sim-rl
cloudrobo train delete-tasks --task-id <task-id> --sim-rl

# 7. Verify resume-task rejects --sim-rl
cloudrobo train resume-task --task-id <task-id> --sim-rl
# → Expected: error (resume is train-only)
```

**Pass criteria**: SimRL task created/monitored/lifecycle-managed via `--sim-rl`; `resume-task --sim-rl` correctly rejected.

## Expected Results Matrix

| Test Case | Input | Expected Output |
| ----------- | ------- | ---------------- |
| TC-01: List tasks | `list-tasks` | JSON array of tasks |
| TC-02: Query models | `list-assets --type model` | JSON array with asset_id |
| TC-03: Query datasets | `list-assets --type dataset` | JSON array with dataset_asset_id |
| TC-04: Create finetune | `create-task --config '<task-json>'` (MODEL_TUNING) | task_id returned, status CREATING/WAITING |
| TC-05: Create pretrain | `create-task --config '<task-json>'` (TRAIN_FROM_SCRATCH) | task_id returned, status CREATING/WAITING |
| TC-06: Poll status | task_id | status transitions to terminal (FINISHED/FAILED) |
| TC-07: Get stages | task_id | 4-stage flow with sub_stages |
| TC-08: Get resource usage | task_id + metric + start + end | CPU/GPU/NPU utilization data |
| TC-09: Get events | task_id + start-time + end-time | event list with level/time/message |
| TC-10: Get logs | task_id + file-name | log content |
| TC-11: Get signed URL | task_id + file-source + file-name | OBS temp URL |
| TC-12: Save draft | draft config | task_id returned, status DRAFT |
| TC-13: Restart task | task_id | task leaves DRAFT/non-terminal, resubmits |
| TC-14: Stop task | running task_id | status → STOPPING → STOPPED |
| TC-15: Clone SimRL task | task_id | new SimRL task_id returned |
| TC-16: Delete tasks | task_id(s) | tasks removed (batch POST for train) |
| TC-17: Stats | workspace_id | counts by status |
| TC-18: Resume task | task_id | task resumed (train-only) |
| TC-19: SimRL list | `--sim-rl` | JSON array of SimRL tasks |
| TC-20: SimRL create | `create-task --sim-rl` | SimRL task_id returned |

## Common Verification Failures

| Failure | Likely Cause | Fix |
| --------- | ------------- | ----- |
| 401 Unauthorized | AK/SK missing or wrong | Set HUAWEI_CLOUD_AK/SK env vars |
| 400 spec invalid | spec not matching Ascend format | Use `Ascend: N * Model \| vCPUs vCPUs \| GiB GiB` |
| 400 train_method invalid | lowercase method | Use uppercase: SFT/LORA/QLORA/DEEPSPEED |
| 400 missing metric/start/end | get-resource-usage requires all three | Pass `--metric`, `--start`, `--end` |
| 400 missing start-time/end-time | get-events requires both | Pass `--start-time`, `--end-time` |
| 400 missing file-source/file-name | get-signed-url requires both | Pass `--file-source`, `--file-name` |
| CREATE_FAILED | spec/cluster_id/resource issue | Check spec format, cluster capacity |
| RUN_FAILED | algorithm/dataset/OOM | Check image_url, dataset access, spec memory |
| Task stuck in WAITING | Resource pool full | Check cluster capacity, reduce worker_num |
| Stages incomplete | Task failed before END | Check which stage failed via get-stages |
| `resume-task --sim-rl` error | resume is train-only | Remove `--sim-rl` or use `restart-task --sim-rl` |
