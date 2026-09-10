# Fault Recovery Guide

## Training Failure

```bash
cloudrobo train get-stages --task-id <id>     # Locate failed stage
cloudrobo train get-events --task-id <id> --start-time <ms> --end-time <ms> --level Error  # View error events
```

### Common Causes

| Error | Cause | Fix |
|-------|-------|-----|
| `ResourceConflictError` | Task name / model name already exists | Use timestamp suffix |
| `CREATE_FAILED` + "数据集未就绪" | Dataset version not RELEASE | `update-version --status RELEASE` |
| `CREATE_FAILED` + "Invalid parameter" | Missing required fields in request body | Check required fields: algorithm, output_models, etc. |
| `CREATE_FAILED` + "data.rename_map does not match pattern" | value not wrapped in single quotes, or JSON contains spaces | Use `json.dumps(map, separators=(',',':'))` to generate compact JSON and wrap with `'` |
| `SUBMIT_FAILED` | `spec` format issue or resource unavailable | Check `spec` is a string, check resource availability |
| OOM | Out of memory | Reduce `batch_size` or increase spec |

## Inference Deployment Failure

```bash
cloudrobo infer show --service-id <id>  # Check details
cloudrobo infer list-logs --service-id <id> --start-time <ms> --end-time <ms> --limit 50 --is-desc  # View logs
cloudrobo infer start --service-id <id>  # Retry FAILED service deployment (FAILED → DEPLOYING)
```

### Common Causes

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid parameter: pool_id` | pool_id format error | `--pool-id` must use `pool-<uuid>` format (with `pool-` prefix) |
| `Invalid parameter: pool_id` | pool_type case error | `--pool-type` must use uppercase `DEDICATED`/`SHARED` |
| `Invalid parameter: pool_id` | Resource pool doesn't support MODEL_DEPLOYMENT | Use `resource list-pools` to find pools with `MODEL_DEPLOYMENT` in `usages` |
| Service created but immediately FAILED (1-2s) | pool_id missing `pool-` prefix | Use `pool-<uuid>` format |
| Service created but immediately FAILED | Missing `model_ext_metadata` | Pass via `--model-ext-metadata` |
| Service created but immediately FAILED | Gripper mapping error | Gripper must use `end_effector_states.position`, not `joint_states.position` |
| Service created but immediately FAILED | `chunk_size` mismatch | Must match training `model.action-horizon` |
| Service created but immediately FAILED | Contains `model_type` field | Remove `model_type` from ext_metadata |
| `Invalid parameter: skill_config` | `strict:true` + empty `skills:[]` | Use `strict:false` or provide at least one skill |
| Resource pool full | No available resources | Wait for release or switch pool_id |

> `infer start` can retry deployment of FAILED services without deleting and recreating.

## Real-Robot Evaluation Failure

```bash
cloudrobo dispatch show-task --session-id <workspace_id> --task-id <task_id>  # Check task status
cloudrobo dispatch show-task-result --session-id <workspace_id> --task-id <task_id> --limit 50  # View execution logs
cloudrobo infer show --service-id <service_id>  # Confirm inference service still RUNNING
cloudrobo robot list --workspace-id <workspace_id>  # Confirm robot still ONLINE
```

### Common Causes

| Error | Cause | Fix |
|-------|-------|-----|
| `Server error 500: CloudRobo.00010028 Internal error` | Inference service missing `skill_config` or empty `skills` | Create inference service with `--skill-config-json` containing non-empty skills |
| `Server error 500: CloudRobo.00010028 Internal error` | Inference service only has `internet` predict_url | Do not pass `--internet-access-enable`; platform auto-assigns intranet URL |
| `Server error 500: CloudRobo.00010028 Internal error` | Inference service stopped | `infer show` confirm RUNNING, else `infer start` restart |
| `Server error 500: CloudRobo.00010028 Internal error` | Robot offline | `robot list` confirm `status=ONLINE`; if offline, guide user through onboarding (see `references/robot-selection-guide.md`) |
| `Invalid parameter: skill_config` | skill_config format error or `strict:true` + empty `skills` | Fix format or provide skills |
| Task `FAILED` | Model inference error or robot execution exception | Check `show-task-result` logs |
| Task `CANCELLED` | Manually cancelled | Recreate task |

> After fixing, create a new task to retry (`create-task` auto-executes).
