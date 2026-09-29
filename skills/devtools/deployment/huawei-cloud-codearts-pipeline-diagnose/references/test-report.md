# Test Report — huawei-cloud-codearts-pipeline-diagnose

Test environment: KooCLI hcloud 7.2.12, region `cn-north-4`, AK/SK from
environment variables (shared skills test account). Executed: 2026-09-28.

## Summary

| Result | Count |
|--------|-------|
| PASS (CLI verified) | 16 |
| PASS (expected rejection) | 1 |
| Manual (live probe — needs CodeArts project + valid account) | 3 |
| Total | 19 |

> NOTE on the auto-generated report: `test-cli-commands.sh` flags a `--help`
> run as "failed" when the help text contains `error|failed|denied|unauthorized|
> not found` (its `run_cli_test` grep). `ListPipelines` and `ListPipelineRuns`
> help legitimately list the status enum value `FAILED:失败。`, which trips that
> grep — the command exits 0 and prints the full help. Those cases are counted
> as PASS (CLI verified) below with the reason recorded.

## Per-Case Results

| ID | Case | Type | Result | Evidence |
|----|------|------|--------|----------|
| TC-01 | `ListPipelines --help` | syntax | ✅ PASS | exit 0, full help; harness grep false-positive on the status enum `FAILED:失败。` |
| TC-02 | `ListPipelines` live | query | ⛔ manual | Needs a real CodeArts project + valid account AK/SK (project-scoped probe) |
| TC-03 | `ShowPipelineDetail --help` | syntax | ✅ PASS | required: `--pipeline_id` + `--project_id` (path) — matches docs |
| TC-04 | `ShowPipelineRunDetail --help` | syntax | ✅ PASS | required: `--pipeline_id` + `--project_id`; optional `--pipeline_run_id`/`--pipeline_run_number` — matches docs |
| TC-05 | `ListPipelineRuns --help` | syntax | ✅ PASS | exit 0, full help; harness grep false-positive on the status enum `FAILED:失败。` |
| TC-06 | `ShowPipelineLog --help` | syntax | ✅ PASS | required: `--pipeline_id`/`--project_id`/`--pipeline_run_id`/`--job_run_id` (path) + `--limit` (body); optional `--step_run_id` — matches docs |
| TC-07 | `ListProjectJobs --help` | syntax | ✅ PASS | required: `--project_id` (path) + `--page_index`/`--page_size`; optional `--build_status`/`--search` — matches docs |
| TC-08 | `ListProjectJobs` live | query | ⛔ manual | Needs a real CodeArts project + valid account AK/SK (project-scoped probe) |
| TC-09 | `ShowBuildRecord --help` | syntax | ✅ PASS | required: `--record_id` (36-char UUID path) — matches docs |
| TC-10 | `ShowBuildRecord` live (dummy id) | query | ⛔ manual | Needs a valid account AK/SK (auth-gated probe); dummy record id → not-found error expected |
| TC-11 | `DownloadBuildLog --help` | syntax | ✅ PASS | required: `--record_id`; optional `--log_level` (INFO\|DEBUG) — matches docs |
| TC-12 | `ListBuildInfoRecordByJobId --help` | syntax | ✅ PASS | required: `--job_id` (path) + `--start_time`/`--end_time` (query) — matches docs |
| TC-13 | `CreatePipelineNew --help` | syntax | ✅ PASS | required: `--name`/`--definition`/`--is_publish` (body) + `--project_id` (path) — matches docs |
| TC-14 | `CreateBuildJob --help` | syntax | ✅ PASS | required: `--arch`/`--job_name`/`--project_id`/`--steps.[N].module_id`/`--steps.[N].name` — matches docs |
| TC-15 | `RunPipeline --help` | syntax | ✅ PASS | required: `--pipeline_id` + `--project_id`; optional `--choose_stages.[N]`/`--choose_jobs.[N]` — matches docs |
| TC-16 | `RunJob --help` | syntax | ✅ PASS | required: `--job_id` (body); optional `--parameter.[N].*`/`--scm.*` — matches docs |
| TC-17 | `DeletePipeline --help` | syntax | ✅ PASS | required: `--pipeline_id` + `--project_id` — matches docs |
| TC-18 | `DeleteBuildJob --help` | syntax | ✅ PASS | required: `--job_id` (path) — matches docs |
| TC-19 | `hcloud CloudBuild` (wrong service name) | negative | ✅ PASS | `[USE_ERROR]不支持的服务名称:CloudBuild` — proves the service-name trap; `CodeArtsBuild` is correct |

## Resource Lifecycle Notes

- **No resources were created, modified, or deleted** during testing: R2/R1 write
  operations (CreatePipelineNew, CreateBuildJob, RunPipeline, RunJob,
  DeletePipeline, DeleteBuildJob) are preview+confirm by design and were only
  checked for syntax (`--help`), never executed live. No cleanup needed.

## Remaining Gaps (require a real CodeArts project + valid account)

1. Live positive-path verification of `ListPipelines`/`ListProjectJobs`
   returning real pipeline/build-task lists (needs a CodeArts Pipeline/Build
   enabled project and account AK/SK with the required permissions).
2. Live `DownloadBuildLog` content shape (plain text vs download link) with a
   real failed build record.
3. Full R2/R1 lifecycle (create pipeline → start → failure diagnose → delete)
   with user confirmation.