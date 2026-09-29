# Verification Method for huawei-cloud-codearts-pipeline-diagnose

This document defines how to verify each action class of the skill.

## Prerequisites for Verification

- hcloud CLI ≥ 7.x installed and authenticated (see
  `cli-installation-guide.md`)
- A CodeArts (DevCloud) project in a region where you have at least read access
  to CodeArts Pipeline and CodeArts Build
- For manage actions: an existing pipeline/build task (or a template for
  creation) and the CodeArts project membership

## Query Actions (R3) — Verification

| Action | Verification Command | Expected Result |
|--------|---------------------|-----------------|
| `huawei_list_pipelines` | `hcloud CodeArtsPipeline ListPipelines --cli-region={region} --project_id={project_id} --offset=0 --limit=10` | JSON with pipeline list (may be empty for a new project) |
| `huawei_list_build_tasks` | `hcloud CodeArtsBuild ListProjectJobs --cli-region={region} --project_id={project_id} --page_index=0 --page_size=10` | JSON with build task list (may be empty) |
| `huawei_get_pipeline` | `hcloud CodeArtsPipeline ShowPipelineDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}` | JSON with pipeline detail or a clear not-found error |
| `huawei_get_build_task` | `hcloud CodeArtsBuild ShowBuildRecord --cli-region={region} --record_id={record_id}` | JSON with the build record or a clear not-found error |
| `huawei_get_build_log` | `hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id}` | Log content (plain text or download link) or a clear error |

**Error semantics:** empty lists are valid results. A non-zero exit or error
JSON indicates auth, scope, or parameter problems. For a non-CodeArts project,
`pipeline.00060101 项目不存在` is expected.

## Analyze Actions (R3) — Verification

- `huawei_diagnose_build_failure`: run
  `ListBuildInfoRecordByJobId --job_id={job_id} --start_time={start_time}
  --end_time={end_time}` (or `ShowBuildRecord --record_id={record_id}`), then
  `DownloadBuildLog` on the failed record, and classify using
  `references/build-error-classification.md`:
  1. network → check connectivity/DNS/timeout
  2. parameter → check build params/scm refs/config
  3. load → check flavor/limits/timeout
  4. code/dependency/permission → fix source / repo creds / IAM
- `huawei_diagnose_pipeline_failure`: run `ShowPipelineRunDetail` (latest or
  specific `--pipeline_run_id`) plus `ListPipelineRuns
  --status.1=failed`; for a failed job, run `ShowPipelineLog --pipeline_id=
  {pipeline_id} --pipeline_run_id={pipeline_run_id} --job_run_id={job_run_id}
  --limit=500` and classify orchestration vs execution error.
- `huawei_extract_build_log_errors`: run `DownloadBuildLog --record_id=
  {record_id} --log_level=INFO`, extract `error|fail|exception` lines, match
  the catalog, and report category + counts + first failing step.

## Manage Actions (R1/R2) — Verification

Always preview the exact command and wait for explicit user confirmation before
execution.

| Action | Verification After Execution |
|--------|------------------------------|
| `huawei_create_pipeline` | `ListPipelines` shows the new pipeline (prefer reusing an existing definition/template) |
| `huawei_create_build_task` | `ListProjectJobs` shows the new task |
| `huawei_start_pipeline` | `ShowPipelineRunDetail` shows a new run for the pipeline |
| `huawei_start_build_task` | `ListBuildInfoRecordByJobId` / `ShowBuildDetails` shows a new build for the job |
| `huawei_delete_pipeline` | `ListPipelines` no longer contains the deleted pipeline |
| `huawei_delete_build_task` | `ListProjectJobs` no longer contains the deleted task |

**Resource lifecycle note:** deleting a pipeline does not delete its build
tasks; deleting a build task keeps build records but prevents new runs.

## Negative Tests

1. Missing `--project_id` (ListPipelines) → error; confirm the parameter is
   required.
2. Wrong service name `hcloud CloudBuild ListProjectJobs` → `[USE_ERROR]不支持
   的服务名称:CloudBuild` (use `CodeArtsBuild`; also `CLOUDBUILD` fails).
3. `ListBuildInfoRecordByJobId` without `--start_time`/`--end_time` →
   missing-required-parameter error.
4. `DownloadBuildRealTimeLog` without `--size` → missing required `--size` error.
5. `ShowBuildRecord` with a non-36-char `--record_id` → parameter format
   validation error.
6. `DeleteBuildJob` on a nonexistent `job_id` → not-found error JSON (expected,
   not a skill defect).
7. `RunPipeline` on an already-running non-concurrent pipeline → concurrent-run
   conflict error (expected behavior; check run state first).

## Pass Criteria

All positive commands return valid JSON; all negative tests fail with a clear
error; no read-only command requires user confirmation; write actions require
confirmation (R2 preview+confirm, R1 preview + explicit second confirmation).