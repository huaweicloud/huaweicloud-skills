# Test Data Guide for huawei-cloud-codearts-pipeline-diagnose

How to supply real test data for automated / live verification of this skill.

## Why command examples use placeholders

For security (skill audit rule Q002-project-id-hardcode), this skill never embeds
a real 32-hex project ID / pipeline ID / job ID / record ID / access key in code
or templates. All command examples use `{placeholders}` that must be replaced
with concrete values belonging to the scanned tenant before any **live**
(non `--help`) execution.

The automated test pipeline only backfills a fixed whitelist (`region`,
`cli_region`, `id`, `instance_id`, `server_id`, `vpc_id`, `subnet_id`,
`flavor_id`, `image_id`). Business placeholders such as `{project_id}`,
`{pipeline_id}`, `{job_id}`, `{record_id}`, `{build_no}` and
`{pipeline_run_id}` are intentionally left for the executing environment to fill
in before live runs.

## Placeholders and how to fill them

| Placeholder | Meaning | How to obtain |
| ----------- | ------- | ------------- |
| `{region}` | Region, e.g. `cn-north-4` | `hcloud configure list` |
| `{project_id}` | CodeArts (DevCloud) project ID | CodeArts console project page / `hcloud IAM KeystoneShowProject` |
| `{pipeline_id}` | Pipeline ID | `hcloud CodeArtsPipeline ListPipelines --project_id={project_id}` |
| `{pipeline_run_id}` | Pipeline run instance ID | `hcloud CodeArtsPipeline ShowPipelineRunDetail --pipeline_id={pipeline_id} --project_id={project_id}` |
| `{job_id}` | Build task ID (32 chars) | `hcloud CodeArtsBuild ListProjectJobs --project_id={project_id}` |
| `{build_no}` | Build number (int, from 1) | `hcloud CodeArtsBuild ShowBuildDetails --job_id={job_id} --build_no=1` |
| `{record_id}` | Build record ID (36-char UUID) | `hcloud CodeArtsBuild ListBuildInfoRecordByJobId --job_id={job_id} --start_time=... --end_time=...` |
| `{job_run_id}` / `{step_run_id}` | Pipeline job/step run IDs | `ShowPipelineRunDetail` stage/job detail |
| `{start_time}` / `{end_time}` | Build history window | `yyyy-MM-dd HH:mm:ss` (e.g. `2026-09-01 00:00:00` / `2026-09-08 00:00:00`) |
| `{module_id}` / `{step_name}` | Build step module | CodeArts Build console 构建步骤 library — the module id of the step (e.g. `build-steps-maven`) |

## Backfilling before automated runs

`templates/test-defaults.json` exposes `request_defaults` (currently
`{project_id}` / `{start_time}` / `{end_time}` placeholders). For live
write-path coverage, a test runner must set these to the scan tenant's real
values **in its own test environment** (do not commit real IDs):

```json
{
  "request_defaults": {
    "project_id": "<real-32-hex>",
    "start_time": "<yyyy-MM-dd HH:mm:ss>",
    "end_time": "<yyyy-MM-dd HH:mm:ss>"
  }
}
```

Modifying `templates/test-defaults.json` or `templates/test-vars.json` inside
this skill directory with real IDs would re-trigger the Q002 security rule, so
real values are supplied only by the executing test harness / environment
overrides, never committed to the repo.

## Service-name traps (expected behavior, not a defect)

`hcloud CloudBuild ...` legitimately fails with
`[USE_ERROR]不支持的服务名称:CloudBuild` and `hcloud CLOUDBUILD ...` fails the
same way because CodeArts build is served by KooCLI as `CodeArtsBuild`. A test
harness must treat those "correct rejections" as a **pass** (same semantics as
the negative tests in `verification-method.md`), not as a functional failure.

## Identifier disambiguation

| Identifier | Format | Use in |
|-----------|--------|--------|
| `job_id` | 32-char | ShowBuildDetails, DownloadBuildRealTimeLog, RunJob, DeleteBuildJob, ListBuildInfoRecordByJobId |
| `build_no` | integer ≥ 1 | ShowBuildDetails, DownloadBuildRealTimeLog |
| `record_id` | 36-char UUID | ShowBuildRecord, DownloadBuildLog, ShowBuildRecordFullStages |

Mixing them up (e.g. passing `record_id` where `job_id` is expected) yields a
parameter-format validation error — the rejection is the expected outcome.