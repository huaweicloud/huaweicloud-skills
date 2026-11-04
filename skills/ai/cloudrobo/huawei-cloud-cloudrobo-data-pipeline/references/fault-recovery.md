# Fault Recovery Guide 故障恢复指南

Fault handling for selected processing tasks (`dataset proc`) and evaluation tasks
(`dataset eval`), whether preset or workspace algorithms. The numbered conversion and
cleaning examples below describe the optional sim/teleop template; custom workflow
diagnosis follows the failed operator's actual input/output contract and declared DAG.

**Recovery principles 恢复原则:**

- A failed task is never re-run in place. Recovery means: diagnose the logs, fix the cause, then
  **create a new task** after user confirmation.
- A retry gets a new name, `<pipeline_name>-<stage_id>-<MMDDHHmmss>` with a new
  timestamp. Record the new `task_id` in the checkpoint and keep the failed `task_id` for
  the Stage 5 summary.
- Before every resubmission, run `list-publication-assets` again and use the **current**
  operator `image` / `algo_id` / `ext_metadata.command` / `ext_metadata.inputs`. Never reuse
  operator info from the failed attempt.
- Do not work around failures by editing `algo_entrance`. For `PRESET_ASSETS` it stays
  equal to the operator's `ext_metadata.command`. Tune behaviour only via `envs` / `inputs`.

---

## Diagnosis Commands 诊断命令

### Processing tasks (conversion / cleaning)

```bash
cloudrobo dataset proc show-task --task-id <task_id>                       # status, target_path / target_asset_id
cloudrobo dataset proc get-log --task-id <task_id> --is-system true        # list system log files (file_name / file_path)
cloudrobo dataset proc get-log --task-id <task_id> --is-system false       # list user (job) log files
cloudrobo dataset proc get-log --task-id <task_id> --file-name <file_name> --file-path <file_path>        # latest 64KB
cloudrobo dataset proc get-log --task-id <task_id> --file-name <file_name> --file-path <file_path> --all  # full log
cloudrobo dataset proc download-log --task-id <task_id> --file-name <file_name> --file-path <file_path>
```

### Evaluation tasks (quality / diversity)

```bash
cloudrobo dataset eval show-task --task-id <eval_task_id>                  # status, target_report_path
cloudrobo dataset eval get-log --task-id <eval_task_id> --is-system true
cloudrobo dataset eval get-log --task-id <eval_task_id> --is-system false
cloudrobo dataset eval get-log --task-id <eval_task_id> --file-name <file_name> --file-path <file_path> [--all]
cloudrobo dataset eval download-log --task-id <eval_task_id> --file-name <file_name> --file-path <file_path>
```

> List the log files first (`--is-system true|false`) to get `file_name` / `file_path`,
> then fetch the content. System logs show scheduling, image and mount problems. User (job)
> logs show the operator's own errors, such as stack traces and `ValueError`. Logs return
> the latest 64KB by default. Use `--all` or `download-log` for large logs.

---

## Conversion Failure 格式转换失败

Stage `convert-lerobotv3` (`dataset proc`, `fail_fast: true`). A failure stops the
pipeline before cleaning.

### Common Causes

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| Task reports the input dataset is not ready | Version readiness, path, access, or a platform-specific release restriction | Read the exact version with `show-version` and diagnose the returned error. Verified DRAFT inputs can be used on supporting platforms. Publish only after confirmation if RELEASE is explicitly required; do not use publication to mask path/access/format errors |
| Path not found in logs | `dataset_configs[].obs_path` is wrong or hand-built | Use the dataset version's `url` (do not concatenate paths). Check that the stage `operator` matches the data format (`data_source_type` h5 / ros2 / umi) |
| Image pull failure in system log | `image` is stale or mistyped | Re-run discovery. Set `image` = the current `ext_metadata.engine.image_url` |
| Access denied | Wrong `catalog_id` (operator's instead of workspace's) or missing permissions | Use `asset_catalog_id` from `cloudrobo workspace current`. Check `references/iam-policies.md` |
| OOM | `worker_spec.memory` too small for the data | Choose a larger flavor from the pool, then create a new task |

See also [Cross-Stage Failures](#cross-stage-failures-跨阶段故障) for validation errors,
POD_PENDING, timeouts and DELETED.

---

## Cleaning Failure 数据清洗失败

Stage `cleaning` (`dataset proc`, `fail_fast: true`). Its `target_path` is the
TrainingReady data path, so a cleaning failure means no TrainingReady output.

### Common Causes

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| Task reports the input dataset is not ready | Conversion output readiness/path or a platform-specific release restriction | Verify the recorded conversion asset/version with `show-version`, diagnose readiness/path/access, and continue with verified DRAFT when supported. Confirm publication only for an established RELEASE requirement |
| Path not found in logs | `dataset_configs` not built from the conversion output | `obs_path` = conversion `target_path`, `asset_id` = conversion `target_asset_id`, `version_id` from `list-versions`, `asset_name` = conversion `output_name` |
| Custom cleaning config not applied / config path not found | `CURATION_CONFIG_PATH` input missing, wrong or not `obs://` | Copy the operator's current `ext_metadata.inputs[]` element as returned and set only `url_path` to the user's `obs://` directory. Never use an `obs_path` key. If the operator does not declare the input, tell the user |
| Image pull failure / access denied / OOM | Same as conversion | Same fixes as [Conversion Failure](#conversion-failure-格式转换失败) |

> If the cleaning operator exposes a `robot` env, its value must be one of the values
> listed in the current `environment_variables[].description`. If `robot_type` has no
> match, ask the user. Keys in `params.envs` must exist in the operator's
> `environment_variables`.

---

## Evaluation Failure 评测失败

Stage `evaluation` with parallel members `quality-eval` and `diversity-eval`
(`dataset eval`). Evaluation is **advisory** (`fail_fast: false`): a failed or skipped
evaluation does not block the TrainingReady output. Wait for both members to reach a
terminal state before Stage 5.

### Common Causes

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| `ValueError: ROBOT_CONFIG environment variable is not set` | Selected metrics need robot geometry, or this operator version cannot run without it | Verify metric scope and current metadata first. Offer an actual robots.yaml/URDF OBS directory through the declared `inputs` mount (e.g. `ROBOT_CONFIG_PATH`) only when needed; otherwise report the operator limitation. Evaluation is advisory; skip or retry only after the user decides, never make the path universally required |
| CLI/SDK local validation requires `robot_config` | Outdated client; the field has been removed and config files are mounted via `inputs` | Upgrade the CloudRobo SDK/CLI and resubmit. Do not add `robot_config`, invent a path, use the dataset directory, or pass an empty string |
| Pipeline validation: `robot_config 已废弃` | The pipeline YAML still uses the removed field | Move the directory into that evaluation member's `params.inputs` as `{name: <declared input, e.g. ROBOT_CONFIG_PATH>, url_path: obs://...}` |
| CLI validation error naming `dataset_id` | `dataset_type=BUILD_IN_ASSET` without `dataset_id` | Set `dataset_id` = cleaning `target_asset_id`. `dataset_name` = cleaning `output_name`, `dataset_path` = cleaning `target_path` |
| Both eval tasks stay at `POD_PENDING` on the public pool | Parallel group needs 2 × `worker_spec` | Use a smaller flavor (e.g. 2c4g) or a dedicated pool. See [Cross-Stage Failures](#cross-stage-failures-跨阶段故障) |
| `get-preview` fails or returns nothing | `--file-name` passed as the full `obs://` path | Use `target_report_path` from `eval show-task` with the `obs://<bucket>/` prefix removed |
| `get-preview` returns platform 500/502/503/504 | Possibly transient report-read failure | Wait briefly, repeat the same read once. If it fails again, retain task ID, report path and error for diagnosis. Keep task status unchanged; do not resubmit evaluation for a preview error |
| Report link no longer opens | `get-preview` returns a temporary OBS URL | Run `get-preview` again (`--is-download` for a download link) and save the report promptly |
| Image pull failure / OOM | Same as conversion | Re-run discovery for the current image, or choose a larger flavor |

> Retry only the failed member: create one new eval task for it, and keep the other
> member's result. If the user sets `fail_fast: true` on the evaluation stage, treat an
> evaluation failure like a blocking stage failure.

---

## Cross-Stage Failures 跨阶段故障

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| `任务配置校验失败: 缺少必填字段或值为空: <fields>` (before submission) | Required task_config field missing or empty | Fill the fields named in the error (see the required-fields list below). Only `description` may be empty |
| `任务配置校验失败: 字段缺少必要子字段: head_spec.cpu` (or `worker_spec.memory`, etc.) | Spec object missing a key, or `dataset_configs` is `"[]"` | `head_spec` / `worker_spec` must contain `cpu` and `memory` (`0` is valid; templates also set `gpu` / `npu`). `dataset_configs` needs at least one entry |
| `创建任务失败: 缺少 workspace_id 参数` | No default workspace | `cloudrobo workspace use --workspace-id <id>`, or pass `--workspace-id` |
| AK/SK not set, HTTP 401/403 | Credentials missing or invalid | Configure via `cloudrobo config set ak <ak> sk <sk>` or `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK`. See `references/cli-installation-guide.md` |
| Required operator not found | Operator not published in the current region/marketplace, or wrong name | Retry discovery with the documented `--name` fragment and `--tags`. If it is still absent, **stop and tell the user**. Never silently substitute another operator |
| Multiple operators match | Fuzzy `--name` match | Match the exact Chinese `operator` name or `operator_id`. Otherwise ask the user to choose |
| Task stays at `POD_PENDING` on the public pool | Resource contention for the selected flavor | Report status and elapsed time. After confirmation, choose a smaller flavor (e.g. 2c4g `{cpu: 2, memory: 4, gpu: 0, npu: 0}`) or `DEDICATED_POOL` (`resource_id` / `dedicated_pool_name`), then create a new task. Decide with the user whether to delete the stalled task first (`delete-task` is irreversible) |
| `wait-task` returns but status is still `CREATING` / `PENDING` / `RUNNING` | The `--timeout` elapsed. `wait-task` returns the last task detail without waiting further | **Do not resubmit.** Report status and elapsed time, then re-run `wait-task --task-id <same id>`. The user decides: keep waiting / view logs / terminate |
| Task ends in `DELETED` | The task was deleted before it finished | No output to hand off. Confirm with the user. If the stage still has to run, create a new task after confirmation |
| Session interrupted | Agent context lost mid-run | Read `~/.cloudrobo/pipeline-runs/<run_id>/state.json` via `pipeline_state.py show`. For a recorded non-terminal `task_id`, re-run `wait-task` on it. Do not resubmit. Continue from the first stage that is not `SUCCEEDED` |

**Required task_config fields (CLI validator):**

| Task | Required | Conditional |
|------|----------|-------------|
| proc (`dataset proc create-task`) | `name`, `algo_type`, `algo_name`, `algo_entrance`, `image`, `catalog_id`, `resource_pool_type`, `cluster_type`, `task_framework_type`, `dataset_configs`, `output_type`, `output_name`, `head_spec`, `worker_spec`, `worker_num`, `evs_spec` | `algo_id` unless `algo_type=OBS_ASSETS`. `algo_path` + `job_local_path` when `OBS_ASSETS`. `output_path` when `output_type=UDF_OBS_ASSET` |
| eval (`dataset eval create-task`) | `name`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `dataset_type`, `dataset_name`, `dataset_path`, `dataset_configs`, `resource_pool_type`, `worker_spec` | `dataset_id` and nested `version_id` when `dataset_type=BUILD_IN_ASSET`; optional `inputs` config mounts (no `robot_config`) |

---

## Retry / Skip Decision 重试 / 跳过决策

| Stage | `fail_fast` | On `FAILED` / `DELETED` | Options offered to the user |
|-------|-------------|-------------------------|-----------------------------|
| `convert-lerobotv3` | `true` | Pipeline pauses; cleaning and evaluation do not start | **retry** (new task) / **terminate** |
| `cleaning` | `true` | Pipeline pauses; no TrainingReady output | **retry** (new task) / **terminate** |
| `evaluation` (`quality-eval`, `diversity-eval`) | `false` | Pipeline continues to Stage 5 | **retry** the failed member (new eval task) / **skip** (report as ⚠️ in the summary) |

> **skip** is available for `fail_fast: false` stages. A `fail_fast: true` stage can only
> be skipped if the user supplies its output (partial pipeline): an existing
> `target_path` / `target_asset_id` / `version_id` and asset name for the next stage.

**Retry procedure:**

1. Diagnose: `show-task`, then `get-log --is-system true` / `false`, then
   `get-log --file-name ... --file-path ...` (or `download-log`).
2. Identify the cause from the tables above and decide the fix with the user.
3. Re-run operator discovery (`list-publication-assets`) and rebuild the task_config from
   the current result. For handoff inputs, re-read `list-versions` / `show-version`.
4. Show the plan: operator name/id/image, envs, inputs, specs, pool, output name/path and
   the new task name. Get **explicit user confirmation**.
5. Create a new task (`dataset proc create-task --algo-type <...>` or
   `dataset eval create-task`) without `--wait`. Then run
   `wait-task --task-id <new_id> --timeout <seconds>` and `show-task`.
6. Update the checkpoint with the new `task_id`. Keep the failed attempt in the run history
   for the Stage 5 summary.


## Web / Terminal Coordination 网页与终端协同

The shipped [Web Monitor](web-monitor.md) follows these same retry/skip rules. Both
surfaces must reserve the state transaction **before** issuing create-task; use
`pipeline_state.py reserve-task` in the terminal, then `resolve-action` after verifying
its result. On exit 3, reload and distinguish an existing submission transaction, a changed
task/state version, and a terminated run; do not assume every conflict came from the other
surface. Parallel members serialize reserve/create/resolve but may execute concurrently.
Do not create another task before reconciling the existing pending_action.

A missing current preset operator or original task config blocks Web retries. Blocking
tasks already submitted cannot be bypassed. Unsubmitted single-input processing may request verified original-input bypass; advisory skips and processing bypass remain warnings in the summary. Terminating in
the Web UI stops later submissions and leaves existing cloud tasks running. A timed-out
create may already have succeeded: check list-tasks/show-task by the pending task name,
then reconcile through resolve-action; never blindly resubmit or edit the state file.
