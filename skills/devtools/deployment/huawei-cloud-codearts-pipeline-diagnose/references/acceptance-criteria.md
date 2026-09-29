# Acceptance Criteria — huawei-cloud-codearts-pipeline-diagnose

## 1. Registration & Structure

- [ ] `SKILL.md` exists under `skills/{category}/{subcategory}/huawei-cloud-codearts-pipeline-diagnose/` with:
  - [ ] YAML frontmatter: `name: huawei-cloud-codearts-pipeline-diagnose` matches directory name; `description` contains feature summary and trigger words; `tags` ≤ 5; **no** `version` field
  - [ ] Required sections: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents, KooCLI Command Format Standard (V3 light embedding: telemetry embedded via Overview dependency + Prerequisites `skill-quality-cli` ensure line + `skill-quality-cli run` wrapping)
  - [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all file extensions allowed
- [ ] `references/iam-policies.md`, `references/cli-installation-guide.md`, `references/verification-method.md`, `references/dataflow-diagram.md`, `references/acceptance-criteria.md`, `references/build-error-classification.md` exist and use kebab-case filenames
- [ ] `scripts/ensure_cli.sh` exists (idempotent skill-quality-cli installer)
- [ ] No hardcoded credentials; no literal AK/SK or `hcloud configure set` with real values

## 2. Action Coverage (14 huawei_* actions)

| Action | Risk | Execution | Acceptance |
|--------|------|-----------|------------|
| `huawei_list_pipelines` | R3 | auto | `ListPipelines` returns pipeline list JSON |
| `huawei_list_build_tasks` | R3 | auto | `ListProjectJobs` returns build task list JSON |
| `huawei_get_pipeline` | R3 | auto | `ShowPipelineDetail` / `ShowPipelineRunDetail` returns pipeline JSON |
| `huawei_get_build_task` | R3 | auto | `ShowBuildDetails` / `ShowBuildRecord` returns build record JSON |
| `huawei_get_build_log` | R3 | auto | `DownloadBuildLog` / `DownloadBuildRealTimeLog` returns log content |
| `huawei_diagnose_build_failure` | R3 | auto | Log fetched and classified (network/parameter/load/code/dependency/permission) with root cause + advice |
| `huawei_diagnose_pipeline_failure` | R3 | auto | Run detail + log analyzed; orchestration vs execution error distinguished |
| `huawei_extract_build_log_errors` | R3 | auto | Error lines extracted, deduplicated and categorized |
| `huawei_create_pipeline` | R2 | preview+confirm | Pipeline created only after confirmation (template or definition JSON) |
| `huawei_create_build_task` | R2 | preview+confirm | Build task created only after confirmation |
| `huawei_start_pipeline` | R2 | preview+confirm | Pipeline run started only after confirmation; no concurrent-run conflict |
| `huawei_start_build_task` | R2 | preview+confirm | Build started only after confirmation |
| `huawei_delete_pipeline` | R1 | preview+explicit confirm | Pipeline deleted only after explicit second confirmation |
| `huawei_delete_build_task` | R1 | preview+explicit confirm | Build task deleted only after explicit second confirmation |

## 3. Critical Warnings (must be preserved)

- [ ] Build service name is `CodeArtsBuild` — `CloudBuild`/`CLOUDBUILD` unsupported
- [ ] Pipeline service name is `CodeArtsPipeline`
- [ ] Pipeline/Build APIs are CodeArts-project scoped (`pipeline.00060101 项目不存在` for non-CodeArts projects)
- [ ] Identifier disambiguation: `job_id` (32-char) / `build_no` (int ≥ 1) / `record_id` (36-char UUID) are NOT interchangeable
- [ ] Log download ops differ by run state: `DownloadBuildLog` (finished, by record_id) vs `DownloadBuildRealTimeLog` (running, job_id+build_no+size)
- [ ] Create ops are complex — prefer template/definition reuse (`CreatePipelineByTemplate`, copy `definition` from `ShowPipelineDetail`)
- [ ] Concurrent runs may be rejected — check run state before start
- [ ] Security baseline — no plaintext credentials in pipeline definitions or build parameters

## 4. CLI Correctness

- [ ] Every `hcloud CodeArtsPipeline <Operation>` / `hcloud CodeArtsBuild <Operation>` uses PascalCase operation names and includes `--cli-region`
- [ ] All required parameters from `--help` (KooCLI 7.2.12) are present in command examples
- [ ] Parameter names match `--help` output verbatim (e.g. `--steps.1.module_id`, `--flow.stage_1.job_1`, `--status.1=failed`, `--scm.build_commit_id`)
- [ ] `ListBuildInfoRecordByJobId` documents required `--start_time`/`--end_time`; `DownloadBuildRealTimeLog` documents required `--size`

## 5. Security

- [ ] No credentials in files; output masking of AK/SK-like values
- [ ] No cross-skill direct calls (no named references to other skill directories)
- [ ] Write actions require explicit user confirmation (R2 preview+confirm, R1 double confirm)
- [ ] Security audit (gitleaks/markdownlint/spec check) passes with no ERROR/CRITICAL findings