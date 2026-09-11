# Test Report — huawei-cloud-deployment-task-management

Test environment: KooCLI hcloud 7.2.12, region `cn-north-4`, AK/SK from environment variables
(shared skills test account, domain `074c26ae7f0025b10fd7c0159cb576a0`).
Executed: 2026-09-08

## Summary

| Result | Count |
|--------|-------|
| PASS | 15 |
| FAIL | 0 |
| Total | 15 |

## Per-Case Results

| ID | Case | Type | Result | Evidence |
|----|------|------|--------|----------|
| TC-01 | `ListAllApp --help` | syntax | ✅ PASS | Description "Querying the Application List in a Project"; required: `--page`/`--project_id`/`--size`; optional: `--group_id`/`--sort_by`/`--sort_name`/`--states.[N]` — exactly as documented |
| TC-02 | `ListAllApp` live | query | ✅ PASS* | API reachable with valid creds; returns `Deploy.00016902 项目不存在` because the IAM project is not a CodeArts (DevCloud) project — expected error semantics, documented in SKILL.md |
| TC-03 | `ListDeployTasks --help` | syntax | ✅ PASS | 4 required params (region, page, project_id, size ≤ 100) — matches docs |
| TC-04 | `ListDeployTasks` live | query | ✅ PASS* | Same expected `Deploy.00016902` (project scope limitation) |
| TC-05 | `ShowDeployTaskDetail --help` | syntax | ✅ PASS | required: `--task_id` + region — matches docs |
| TC-06 | `ShowDeployTaskDetail` live (dummy id) | query | ✅ PASS* | Returns `DEV-12-50002 task_id参数异常` (param validation) — negative-style probe proves CLI wiring |
| TC-07 | `ListDeployTaskHistoryByDate --help` | syntax | ✅ PASS | 7 required incl. `--id`, `--start_date`, `--end_date`, `--page`, `--size` — matches docs |
| TC-08 | `CheckIsDuplicateAppName --help` | syntax | ✅ PASS | required: `--name`, `--project_id` — matches docs |
| TC-09 | `CreateApp --help` | syntax | ✅ PASS | 5 required incl. `--create_type`/`--is_draft`/`--name`/`--project_id` — matches docs |
| TC-10 | `CreateDeployTaskByTemplate --help` | syntax | ✅ PASS | 5 required incl. `--project_id`/`--project_name`/`--task_name`/`--template_id` — matches docs |
| TC-11 | `StartDeployTask --help` | syntax | ✅ PASS | required: `--task_id` + region; optional `--params.[N]`/`--record_id`/`--trigger_source` — matches docs |
| TC-12 | `DeleteDeployTask --help` | syntax | ✅ PASS | required: `--task_id` + region — matches docs |
| TC-13 | `hcloud CloudDeploy` (wrong service name) | negative | ✅ PASS | `[USE_ERROR]Unsupported service: CloudDeploy.` — proves the service-name trap; `CodeArtsDeploy` is correct |
| TC-14 | `ListAllApp --page=0` | negative | ✅ PASS | `DEV-12-50002 page参数异常，仅支持数字（1~99999）` — validation error as expected |
| TC-15 | `hcloud obs ls obs://...` | syntax | ✅ PASS | obsutil passthrough wiring confirmed (URL format validation reached); real bucket/object needed in live scenario |

\* TC-02/04/06 are live read-only probes against the shared test account whose IAM project is not
bound to CodeArts Deploy, so API-level "project/task not found" errors are the **expected and
documented** outcome (see Prerequisites and negative-test semantics in the skill docs). They prove
CLI + credential wiring end to end.

## Resource Lifecycle Notes

- **No resources were created, modified, or deleted** during testing: R2/R1 write operations
  (CreateApp, CreateDeployTaskByTemplate, StartDeployTask, DeleteDeployTask) are preview+confirm
  by design and were only checked for syntax (`--help`), never executed live. No cleanup needed.

## Remaining Gaps (require a real CodeArts project)

1. Live positive-path verification of `ListAllApp`/`ListDeployTasks` returning real application/task
   lists (needs a CodeArts Deploy-enabled project).
2. Live `StartDeployTask` execution and failure root-cause validation (needs target hosts with the
   CloudDeploy agent and an OBS artifact).
3. Full R2/R1 lifecycle (create app → create task → start → delete) with user confirmation.