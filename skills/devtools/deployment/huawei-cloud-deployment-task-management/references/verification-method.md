# Verification Method for huawei-cloud-deployment-task-management

This document defines how to verify each action class of the skill.

## Prerequisites for Verification

- hcloud CLI ≥ 7.x installed and authenticated (see `cli-installation-guide.md`)
- A CodeArts (DevCloud) project in a region where you have at least read access to CloudDeploy
- For manage actions: an existing application (for task creation) and online target hosts with the
  CloudDeploy agent (for `huawei_start_clouddeploy_task`)
- For artifact verification: an OBS bucket/object configured as the artifact source

## Query Actions (R3) — Verification

| Action | Verification Command | Expected Result |
|--------|---------------------|-----------------|
| `huawei_list_clouddeploy_apps` | `hcloud CodeArtsDeploy ListAllApp --cli-region={region} --project_id={project_id} --page=1 --size=10` | JSON with application list (may be empty for a new project) |
| `huawei_list_clouddeploy_tasks` | `hcloud CodeArtsDeploy ListDeployTasks --cli-region={region} --project_id={project_id} --page=1 --size=10` | JSON with task list (may be empty) |
| `huawei_get_clouddeploy_task` | `hcloud CodeArtsDeploy ShowDeployTaskDetail --cli-region={region} --task_id={task_id}` | JSON with the task detail or a clear not-found error |

**Error semantics:** empty lists are valid results. A non-zero exit or error JSON indicates auth,
scope, or parameter problems. For a non-CodeArts project, `Deploy.00016902 项目不存在` is expected.

## Analyze Actions (R3) — Verification

- `huawei_analyze_clouddeploy_failure`: run `ListDeployTaskHistoryByDate` with
  `--start_date`/`--end_date` (interval ≤ 30 days) and evaluate the latest failed record:
  1. execution log shows host/agent offline → verify host agent
  2. status `timeout` → check artifact size / task timeout / host resources
  3. artifact error → verify the OBS object (next action)
  4. permission error → check IAM policy and host permissions
- `huawei_analyze_clouddeploy_artifact`: run `ShowDeployTaskDetail` to read the artifact config,
  then `hcloud obs ls obs://{bucket}/{object_path}` (obsutil). Expected: object listed; missing
  object → advise re-upload or fix the task artifact path.

## Manage Actions (R1/R2) — Verification

Always preview the exact command and wait for explicit user confirmation before execution.

| Action | Verification After Execution |
|--------|------------------------------|
| `huawei_create_clouddeploy_app` | `ListAllApp` shows the new application (pre-check with `CheckIsDuplicateAppName` before creating) |
| `huawei_create_clouddeploy_task` | `ListDeployTasks` shows the new task referencing the application |
| `huawei_start_clouddeploy_task` | `ListDeployTaskHistoryByDate` shows a new execution record for the task |
| `huawei_delete_clouddeploy_task` | `ListDeployTasks` no longer contains the deleted task |

**Resource lifecycle note:** deleting a task does not delete the application or deployed resources;
applications are listed/created separately via `huawei_list_clouddeploy_apps` /
`huawei_create_clouddeploy_app`.

## Negative Tests

1. Missing `--project_id` (ListAllApp) → error; confirm the parameter is required.
2. Wrong service name `hcloud CloudDeploy ListAllApp` → "Unsupported service" (use `CodeArtsDeploy`).
3. `--page=0` on ListAllApp → validation error (page must be ≥ 1).
4. `ListDeployTaskHistoryByDate` with start/end interval > 30 days → validation error.
5. CreateApp with a duplicate application name → duplicate-name error (use `CheckIsDuplicateAppName`).
6. `DeleteDeployTask` on a nonexistent task_id → not-found error JSON (expected, not a skill defect).

## Pass Criteria

All positive commands return valid JSON; all negative tests fail with a clear error; no read-only
command requires user confirmation; write actions require confirmation (R2 preview+confirm,
R1 preview + explicit second confirmation).