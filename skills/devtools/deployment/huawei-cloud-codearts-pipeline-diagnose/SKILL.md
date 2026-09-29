---
name: huawei-cloud-codearts-pipeline-diagnose
description: |
  Huawei Cloud CodeArts Pipeline (流水线) and CodeArts Build (编译构建/构建任务)
  management, monitoring and failure diagnosis using the KooCLI hcloud
  command-line client. Covers pipeline and build-task listing/detail, build log
  retrieval, build failure diagnosis (log fetch → error classification → root
  cause: network/parameter/load), pipeline anomaly diagnosis (orchestration
  errors / execution errors), log error extraction and categorization, plus
  pipeline/build-task create, start and delete. Query and Analyze actions run
  automatically (R3); Create/Start actions require preview and user confirmation
  (R2); Delete requires explicit confirmation (R1). Supports AK/SK credentials
  and local hcloud profile authentication.
  Triggers include: "CodeArts", "流水线", "CodeArts Pipeline", "pipeline",
  "构建任务", "构建", "build task", "build job", "编译构建", "CodeArts Build",
  "pipeline failure", "流水线失败", "build failure", "构建失败", "构建日志",
  "build log", "日志错误", "log error", "流水线异常", "pipeline diagnose",
  "构建诊断", "CI/CD", "持续集成", "持续交付".
tags: [huawei-cloud, codearts, pipeline, build, devops]
---

# Huawei Cloud CodeArts Pipeline & Build Diagnosis

<!-- cli-install-version: 7.2.12 -->
## Step 0: Ensure skill-quality-cli (idempotent)

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
```

> The script installs the bundled `scripts/cli/` sources to `~/.local/bin/` when
> `skill-quality-cli` is not found (offline, no external download), re-exports
> PATH for the current session and persists it into `~/.bashrc` / `~/.profile`;
> it never blocks. If still not found, call the absolute path:
> `~/.local/bin/skill-quality-cli`.

## Overview

This skill operates Huawei Cloud CodeArts (CodeArts Pipeline / CodeArts Build /
编译构建) through the `hcloud` CLI. CodeArts Pipeline orchestrates build, deploy
and release tasks as pipelines (`流水线`); CodeArts Build compiles source code
into artifacts as build tasks (`构建任务`). The skill covers:

| Category | Capabilities |
|----------|--------------|
| **Query** | List pipelines (`huawei_list_pipelines`), list build tasks (`huawei_list_build_tasks`), get pipeline detail (`huawei_get_pipeline`), get build task detail (`huawei_get_build_task`), get build log (`huawei_get_build_log`) |
| **Analyze** | Build failure diagnosis (`huawei_diagnose_build_failure` — log fetch → error classification → root cause: network/parameter/load), pipeline failure diagnosis (`huawei_diagnose_pipeline_failure` — orchestration/execution error analysis), build log error extraction (`huawei_extract_build_log_errors`) |
| **Manage** | Create pipeline (`huawei_create_pipeline`), create build task (`huawei_create_build_task`), start pipeline (`huawei_start_pipeline`), start build task (`huawei_start_build_task`), delete pipeline (`huawei_delete_pipeline`), delete build task (`huawei_delete_build_task`) |

> **Always run `hcloud CodeArtsPipeline <Operation> --cli-region={region} --help`
> or `hcloud CodeArtsBuild <Operation> --cli-region={region} --help` before
> constructing a command** to discover the exact parameter names and required
> flags for the current KooCLI version. Do not answer from general knowledge —
> follow the procedures in this document.

**Dependency**: Quality telemetry is collected automatically via
`skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

### Critical Warnings

| Trap | Why |
|------|-----|
| **Build service is `CodeArtsBuild`, not `CloudBuild`/`CLOUDBUILD`** | `hcloud CloudBuild <op>` and `hcloud CLOUDBUILD <op>` report `[USE_ERROR]不支持的服务名称` (unsupported service). The real KooCLI service name is `CodeArtsBuild` (metadata directory `codeartsbuild`) — confirm with the service help output. |
| **Pipeline APIs are project-scoped** | Every CodeArtsPipeline operation requires `--project_id` of a **CodeArts (DevCloud) project**. A plain IAM project or wrong project returns `pipeline.00060101 项目不存在` or an auth error. Omit `--project_id` only if your hcloud profile has a default project set. |
| **Log download endpoints return raw/compressed content** | `DownloadBuildLog` returns the full log for a `record_id`; for a running build use `DownloadBuildRealTimeLog` (`job_id` + `build_no` + `--size`). `DownloadBuildFullLog` adds `--compress`/`--log_level`. Match the operation to the run state. |
| **record_id ≠ job_id ≠ build_no** | Build APIs use three distinct identifiers: `job_id` (task id, 32 chars), `build_no` (per-build increment starting at 1), `record_id` (36-char build record uuid). Do not substitute one for another — the API rejects mismatched ids. |
| **Create operations are complex** | `CreatePipelineNew` needs a JSON `--definition` (best copied from an existing pipeline via `ShowPipelineDetail`); `CreateBuildJob` needs `--steps.N.module_id`/`--steps.N.name` for each build step. Prefer template-based creation (`CreatePipelineByTemplate`) for pipelines in production. |
| **Concurrent runs may be rejected** | Starting a pipeline that is already running returns a conflict error unless the run policy permits concurrency. Check the latest run state (`ShowPipelineRunDetail`) before `RunPipeline`/`RunJob`. |
| **Security baseline** | Never hardcode AK/SK or pipeline parameters with plaintext credentials in build steps/scripts. Use IAM roles where possible and encrypt sensitive parameters (KooCLI keeps secrets in the local profile; env-var credentials never appear in commands). |

## Triggers

Use this skill when the user asks about CodeArts Pipeline / CodeArts Build
operations, pipeline or build-task management, build logs, or CI/CD failure
troubleshooting.

**Trigger phrases**: "CodeArts", "流水线", "CodeArts Pipeline", "pipeline",
"构建任务", "构建", "build task", "build job", "编译构建", "CodeArts Build",
"pipeline failure", "流水线失败", "build failure", "构建失败", "构建日志",
"build log", "日志错误", "log error", "流水线异常", "pipeline diagnose",
"构建诊断", "CI/CD", "持续集成", "持续交付".

**User utterance examples**:

1. "列出我项目下的流水线/构建任务" (list pipelines / build tasks in my project)
2. "这条流水线/构建任务失败了，帮我诊断一下原因" (this pipeline/build failed — diagnose the root cause)
3. "帮我提取构建日志里的错误信息" (extract error info from the build log)
4. "创建一个流水线/构建任务并启动它" (create and start a pipeline / build task)
5. "删除这个流水线/构建任务" (delete this pipeline / build task)

## Prerequisites

1. **hcloud CLI** installed and authenticated — see `references/cli-installation-guide.md`
2. **Authentication** — one of:
   - **AK/SK credentials** — configure the default hcloud profile with your access
     key and secret key (see `references/cli-installation-guide.md`, section
     "Authentication"), or
   - Environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (or
     `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`) — hcloud auto-detects them
3. **IAM permissions** — `CodeArts Pipeline ReadOnlyAccess` + `CodeArts Build
   ReadOnlyAccess` (or equivalent read actions) for query/analyze; write actions
   listed in `references/iam-policies.md` for create/start/delete
4. **Region & project**: CodeArts Pipeline/Build APIs are region/project scoped.
   Pass `--cli-region={region}` and `--project_id={project_id}`. The project must
   be a CodeArts (DevCloud) project — a plain IAM project returns "项目不存在".
5. **CodeArts project** — pipelines and build tasks belong to a CodeArts
   (DevCloud) project; create one from the CodeArts console if missing.
6. **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent,
   skips if present)
   - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
   - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```
1. Identify intent:
   ├── Query (R3 auto): list pipelines / list build tasks / get pipeline / get build task / get build log
   ├── Analyze (R3 auto): build failure diagnosis, pipeline failure diagnosis, log error extraction
   └── Manage (R1/R2): create pipeline / create build task / start pipeline / start build task / delete — preview + confirm
2. Gather scope: region, project_id, pipeline_id / job_id, build_no / record_id, time range (run history)
3. Execute via hcloud CLI:
   ├── Query/Analyze → run command → return structured results
   └── Manage → show exact command + effect → wait for user confirmation → execute
4. Handle traps: wrong service name (CodeArtsBuild), project scope (CodeArts project),
   identifier mismatch (job_id/build_no/record_id), concurrent-run conflict
5. Report results (JSON), masking AK/SK-like values in output
```

**Write-operation rule:** `huawei_create_pipeline`, `huawei_create_build_task`,
`huawei_start_pipeline`, `huawei_start_build_task` (R2) and
`huawei_delete_pipeline`, `huawei_delete_build_task` (R1) MUST NOT execute
without an explicit user confirmation after the exact command and its effect are
previewed. For delete (R1) the user must confirm a second time in plain words
(e.g. "确认删除").

## Core Commands

**Supported services (KooCLI): `CodeArtsPipeline` and `CodeArtsBuild` only.**
`CloudBuild` / `CLOUDBUILD` are **not** supported service names — the hcloud CLI
rejects them with `[USE_ERROR]不支持的服务名称` (unsupported service), which is
the **expected correct-rejection** result. Any command in this skill MUST use
`hcloud CodeArtsPipeline <Operation>` or `hcloud CodeArtsBuild <Operation>`.

Region parameter `--cli-region={region}` is required on every command. The
`--project_id` is shown explicitly in examples; omit it only when your hcloud
profile sets a default project. Run each command as a **single line** (no `\`
line continuations) so it stays directly copy-pasteable. Parameter names below
were verified against `hcloud <Service> <Operation> --help` (KooCLI 7.2.12).

> **⚠️ 执行形态**: 下面的每个命令都以**裸 `hcloud <Service> <Operation>` 形式**给出（可直接
> 复制执行，测试流水线也只识别这种形态）。**质量上报形态**是在执行时用
> `skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- ` 包裹
> 该命令（每个命令块下方以 `# 质量上报:` 注释给出完整包裹形态）；裸 `hcloud` 形式
> 是权威可执行形式，包裹形态仅用于质量上报，二者命令参数完全一致。

### Query — Pipelines (R3, auto)

```bash
# List pipelines in a CodeArts project (offset/limit optional; filter by name)
hcloud CodeArtsPipeline ListPipelines --cli-region={region} --project_id={project_id} --offset=0 --limit=100
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ListPipelines --cli-region={region} --project_id={project_id} --offset=0 --limit=100
# Filter by pipeline name
hcloud CodeArtsPipeline ListPipelines --cli-region={region} --project_id={project_id} --name={pipeline_name}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ListPipelines --cli-region={region} --project_id={project_id} --name={pipeline_name}
# Get pipeline detail (definition, stages, sources)
hcloud CodeArtsPipeline ShowPipelineDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ShowPipelineDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# Get the latest run state of a pipeline (optional run_id / run_number)
hcloud CodeArtsPipeline ShowPipelineRunDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ShowPipelineRunDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
```

### Query — Build Tasks & Logs (R3, auto)

```bash
# List build tasks in a CodeArts project (page_index/page_size required)
hcloud CodeArtsBuild ListProjectJobs --cli-region={region} --project_id={project_id} --page_index=0 --page_size=100
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ListProjectJobs --cli-region={region} --project_id={project_id} --page_index=0 --page_size=100
# Filter build tasks by status, e.g. BUILDING / FAILED / SUCCESS
hcloud CodeArtsBuild ListProjectJobs --cli-region={region} --project_id={project_id} --page_index=0 --page_size=100 --build_status=FAILED
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ListProjectJobs --cli-region={region} --project_id={project_id} --page_index=0 --page_size=100 --build_status=FAILED
# Get build task status/percentage/remaining time by job_id + build_no
hcloud CodeArtsBuild ShowBuildDetails --cli-region={region} --job_id={job_id} --build_no={build_no}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ShowBuildDetails --cli-region={region} --job_id={job_id} --build_no={build_no}
# Get build record detail by record_id (status, duration, error message)
hcloud CodeArtsBuild ShowBuildRecord --cli-region={region} --record_id={record_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ShowBuildRecord --cli-region={region} --record_id={record_id}
# Get all build records of a job in a time range (start_time/end_time required, yyyy-MM-dd HH:mm:ss)
hcloud CodeArtsBuild ListBuildInfoRecordByJobId --cli-region={region} --job_id={job_id} --start_time={start_time} --end_time={end_time} --page_index=0 --page_size=20
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ListBuildInfoRecordByJobId --cli-region={region} --job_id={job_id} --start_time={start_time} --end_time={end_time} --page_index=0 --page_size=20
# Download the full build log for a finished build (record_id; optional --log_level=INFO|DEBUG)
hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
# Fetch real-time log of a running build (job_id + build_no + required --size)
hcloud CodeArtsBuild DownloadBuildRealTimeLog --cli-region={region} --job_id={job_id} --build_no={build_no} --size=1000
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DownloadBuildRealTimeLog --cli-region={region} --job_id={job_id} --build_no={build_no} --size=1000
```

### Analyze — Build Failure Diagnosis (R3, auto)

```bash
# Step 1: locate the failed build record (time-windowed history of a job)
hcloud CodeArtsBuild ListBuildInfoRecordByJobId --cli-region={region} --job_id={job_id} --start_time={start_time} --end_time={end_time} --page_index=0 --page_size=20
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ListBuildInfoRecordByJobId --cli-region={region} --job_id={job_id} --start_time={start_time} --end_time={end_time} --page_index=0 --page_size=20
# Step 2: get the failed record detail (status + error info)
hcloud CodeArtsBuild ShowBuildRecord --cli-region={region} --record_id={record_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild ShowBuildRecord --cli-region={region} --record_id={record_id}
# Step 3: download the full log and classify the failure
hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
```

Diagnose the failed build by checking, in order (see
`references/build-error-classification.md` for the full pattern catalog):

1. **Network** — log contains `connection refused` / `timeout` / `Could not
   resolve host` / `Network is unreachable` / `502`/`503`/`504` → check the
   build host network, private repo/endpoint reachability, proxy settings, and
   the source-code repo connectivity.
2. **Parameter/configuration** — `parameter` / `param` / `undefined variable` /
   `找不到` / `No such file or directory` / YAML/JSON parse errors → check build
   parameters, environment variables, working directory, scm branch/tag/commit.
3. **Load/resource** — `OutOfMemoryError` / `内存不足` / `no space left on
   device` / `disk quota` / `timeout (build killed)` → check the build flavor
   (`--flavor`), concurrent builds, and build host resource limits.

### Analyze — Pipeline Failure Diagnosis (R3, auto)

```bash
# Step 1: inspect the failed pipeline run (stages + job status)
hcloud CodeArtsPipeline ShowPipelineRunDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --pipeline_run_id={pipeline_run_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ShowPipelineRunDetail --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --pipeline_run_id={pipeline_run_id}
# Step 2: query the run history to find failed runs / status filter
hcloud CodeArtsPipeline ListPipelineRuns --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --status.1=failed --limit=20
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ListPipelineRuns --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --status.1=failed --limit=20
# Step 3: fetch the failing stage/job log (job_run_id + step_run_id from run detail; limit required)
hcloud CodeArtsPipeline ShowPipelineLog --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --pipeline_run_id={pipeline_run_id} --job_run_id={job_run_id} --step_run_id={step_run_id} --limit=500
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline ShowPipelineLog --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --pipeline_run_id={pipeline_run_id} --job_run_id={job_run_id} --step_run_id={step_run_id} --limit=500
```

Diagnose the failing pipeline by class:

1. **Orchestration error (编排异常)** — stages/jobs not executed, `not executed`
   status, manual-review gate, dependency/order misconfiguration → check the
   pipeline definition (`ShowPipelineDetail`), stage trigger conditions, manual
   gates, and `choose_stages`/`choose_jobs` selection.
2. **Execution error (执行报错)** — a stage/job ran but failed (build, deploy, or
   check step) → drill into that job's log in run detail and apply the build
   failure classification above.

### Analyze — Build Log Error Extraction (R3, auto)

```bash
# Download the full log of a finished build
hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DownloadBuildLog --cli-region={region} --record_id={record_id} --log_level=INFO
# Or fetch a real-time slice of a running build
hcloud CodeArtsBuild DownloadBuildRealTimeLog --cli-region={region} --job_id={job_id} --build_no={build_no} --size=2000
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DownloadBuildRealTimeLog --cli-region={region} --job_id={job_id} --build_no={build_no} --size=2000
```

Extract and categorize errors from the log using the pattern catalog in
`references/build-error-classification.md`, then return:
- each error line (timestamp + message, deduplicated),
- its category (network/parameter/load/code/dependency/permission/other),
- the first-failing step, and
- a suggested next action.

### Manage — Create Pipeline (R2, preview + confirm)

```bash
# Template-based creation (recommended): flow.{*}.{*} and states.{*}.{*} map stages/tasks
# 模板化创建（推荐）: flow.{*}.{*} 和 states.{*}.{*} 映射阶段/任务；--description 可选
# 可选: --description={description}
hcloud CodeArtsPipeline CreatePipelineByTemplate --cli-region={region} --project_id={project_id} --name={pipeline_name} --flow.stage_1.job_1=job --states.stage_1.display_name={stage_name} --states.stage_1.job_id={job_id} --states.stage_1.job_name={job_name} --states.stage_1.is_execute=true
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline CreatePipelineByTemplate --cli-region={region} --project_id={project_id} --name={pipeline_name} --flow.stage_1.job_1=job --states.stage_1.display_name={stage_name} --states.stage_1.job_id={job_id} --states.stage_1.job_name={job_name} --states.stage_1.is_execute=true [--description={description}]
# Or definition-JSON based creation (Copy the definition from ShowPipelineDetail of an existing pipeline)
hcloud CodeArtsPipeline CreatePipelineNew --cli-region={region} --project_id={project_id} --name={pipeline_name} --definition={definition_json} --is_publish=false
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline CreatePipelineNew --cli-region={region} --project_id={project_id} --name={pipeline_name} --definition={definition_json} --is_publish=false
```

> Preview before executing: show the exact command, the pipeline name, and its
> stages, then wait for user confirmation (R2). Generating a valid
> `--definition` is complex — prefer fetching an existing pipeline's definition
> via `ShowPipelineDetail` and editing it, or use `CreatePipelineByTemplate`.

### Manage — Create Build Task (R2, preview + confirm)

```bash
# Create a build task (arch + job_name + project_id + at least one step required)
# 创建构建任务（arch + job_name + project_id + 至少一个 step 必填）；--flavor/--scms 可选
# 可选: --flavor={flavor} --scms.1.scm_type=codehub --scms.1.url={repo_url} --scms.1.branch={branch}
hcloud CodeArtsBuild CreateBuildJob --cli-region={region} --project_id={project_id} --job_name={task_name} --arch=x86_64 --steps.1.module_id={module_id} --steps.1.name={step_name}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild CreateBuildJob --cli-region={region} --project_id={project_id} --job_name={task_name} --arch=x86_64 --steps.1.module_id={module_id} --steps.1.name={step_name} [--flavor={flavor}] [--scms.1.scm_type=codehub --scms.1.url={repo_url} --scms.1.branch={branch}]
```

> Preview before executing: show the exact command, task name, steps and code
> source, then wait for user confirmation (R2). `--flavor` (build resource
> specification) defaults to the project default when omitted.

### Manage — Start Pipeline (R2, preview + confirm)

```bash
# Start a pipeline run (optional: select stages/jobs, add description)
hcloud CodeArtsPipeline RunPipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline RunPipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# Start only selected stages/jobs
hcloud CodeArtsPipeline RunPipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --choose_stages.1={stage_name} --choose_jobs.1={job_name} --description={description}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline RunPipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id} --choose_stages.1={stage_name} --choose_jobs.1={job_name} --description={description}
```

> Preview before executing: show the pipeline, selected stages/jobs, and check
> the latest run state (no concurrent run for a non-concurrent pipeline), then
> wait for user confirmation (R2).

### Manage — Start Build Task (R2, preview + confirm)

```bash
# Start a build task with optional custom parameters
hcloud CodeArtsBuild RunJob --cli-region={region} --job_id={job_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild RunJob --cli-region={region} --job_id={job_id}
# With custom parameters / scm commit
hcloud CodeArtsBuild RunJob --cli-region={region} --job_id={job_id} --parameter.1.name={param_name} --parameter.1.value={param_value} --scm.build_commit_id={commit_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild RunJob --cli-region={region} --job_id={job_id} --parameter.1.name={param_name} --parameter.1.value={param_value} --scm.build_commit_id={commit_id}
```

> Preview before executing: show the task, parameters and commit, check no
> conflicting run is in progress, then wait for user confirmation (R2).
> `ExecuteJob` is an equivalent start operation with the same parameter shape.

### Manage — Delete Pipeline (R1, preview + explicit confirm)

```bash
# Delete a pipeline by pipeline_id
hcloud CodeArtsPipeline DeletePipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsPipeline DeletePipeline --cli-region={region} --project_id={project_id} --pipeline_id={pipeline_id}
```

> R1 delete operation: preview the exact command and the pipeline being deleted,
> then require an explicit second confirmation (e.g. the user typing the
> pipeline name or "确认删除") before execution. Deleting a pipeline does not
> delete its build tasks.

### Manage — Delete Build Task (R1, preview + explicit confirm)

```bash
# Delete a build task by job_id
hcloud CodeArtsBuild DeleteBuildJob --cli-region={region} --job_id={job_id}
# 质量上报: skill-quality-cli run --skill-name huawei-cloud-codearts-pipeline-diagnose -- hcloud CodeArtsBuild DeleteBuildJob --cli-region={region} --job_id={job_id}
```

> R1 delete operation: preview the exact command and the task being deleted,
> then require an explicit second confirmation before execution. Deleting a
> build task does not delete build history records.

## Parameter Confirmation

All parameter names below were verified against
`hcloud CodeArtsPipeline <Operation> --help` and
`hcloud CodeArtsBuild <Operation> --help` (KooCLI 7.2.12). Values in `{}` are
placeholders — replace with real values. **Do not invent parameter names** —
re-run `--help` if in doubt.

> `--cli-region` is required on every command and is omitted from the tables below for brevity.

### CodeArtsPipeline — Query/Analyze

| Operation | Parameter | Required | Description |
|-----------|-----------|----------|-------------|
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--name` | No | Filter by pipeline name |
| | `--offset` / `--limit` | No | Pagination (offset = start index, limit = count) |
| | `--creator_id` / `--executor_ids.[N]` | No | Filter by creator / last executor |
| | `--is_publish` | No | Filter by publish status |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |
| | `--pipeline_run_id` / `--pipeline_run_number` | No | Latest run used when omitted |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |
| | `--status.[N]` | No | Filter by run status, e.g. `failed` |
| | `--start_time` / `--end_time` | No | Run time range |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |
| | `--pipeline_run_id` | Yes | Pipeline run instance ID (path) |
| | `--job_run_id` | Yes | Pipeline job (task) run ID (path) |
| | `--step_run_id` | No | Step run ID (omit for whole job) |
| | `--limit` | Yes | Max log lines (body) |
| | `--level` / `--sort` | No | Log level / sort order |

### CodeArtsPipeline — Manage

| Operation | Parameter | Required | Description |
|-----------|-----------|----------|-------------|
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--name` | Yes | Pipeline name |
| | `--flow.{*}.{*}` | Yes | Stage→job mapping (e.g. `--flow.stage_1.job_1=job`) |
| | `--states.{*}.display_name` | Yes | Stage display name |
| | `--states.{*}.job_id` / `--job_name` | Yes | Job id/name per stage |
| | `--states.{*}.is_execute` / `--is_manual_execution` | Yes | Execute / manual-execution flag |
| | `--states.{*}.dsl_method` / `--execution_mode` | Yes | Task type / serial-or-parallel |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--name` | Yes | Pipeline name |
| | `--definition` | Yes | Pipeline structure definition JSON |
| | `--is_publish` | Yes | `true` to publish / `false` to draft |
| | `--description` / `--group_id` | No | Description / pipeline group |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |
| | `--choose_stages.[N]` / `--choose_jobs.[N]` | No | Selected stages / jobs to run |
| | `--description` | No | Run description (≤ 1024 chars) |
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--pipeline_id` | Yes | Pipeline ID (path) |

### CodeArtsBuild — Query/Analyze

| Operation | Parameter | Required | Description |
|-----------|-----------|----------|-------------|
| | `--project_id` | Yes | CodeArts project ID (path) |
| | `--page_index` | Yes | Page number, ≥ 0 |
| | `--page_size` | Yes | Items per page |
| | `--build_status` | No | Filter by status (e.g. `FAILED`, `BUILDING`, `SUCCESS`) |
| | `--search` | No | Keyword search on task name |
| | `--job_id` | Yes | Build task ID (path) |
| | `--build_no` | Yes | Build number, starts at 1 (path) |
| | `--record_id` | Yes | Record ID, 36-char UUID (path) |
| | `--job_id` | Yes | Build task ID (path) |
| | `--start_time` / `--end_time` | Yes | `yyyy-MM-dd HH:mm:ss` time range |
| | `--page_index` / `--page_size` | No | Pagination |
| | `--record_id` | Yes | Record ID, 36-char UUID (path) |
| | `--log_level` | No | `INFO` or `DEBUG` |
| | `--job_id` | Yes | Build task ID (path) |
| | `--build_no` | Yes | Build number (path) |
| | `--size` | Yes | Bytes to fetch (query) |
| | `--start_offset` / `--end_offset` / `--sort` | No | Offset / sort control |

### CodeArtsBuild — Manage

| Operation | Parameter | Required | Description |
|-----------|-----------|----------|-------------|
| | `--project_id` | Yes | CodeArts project ID (body) |
| | `--job_name` | Yes | Task name (body) |
| | `--arch` | Yes | Machine architecture, e.g. `x86_64` (body) |
| | `--steps.[N].module_id` | Yes | Build module id per step (body) |
| | `--steps.[N].name` | Yes | Build module name per step (body) |
| | `--flavor` | No | Build resource flavor |
| | `--scms.[N].scm_type` / `--url` / `--branch` | No | Code source (e.g. `codehub`) |
| | `--build_config_type` / `--host_type` | No | Build config / host type |
| | `--job_id` | Yes | Build task ID (body) |
| | `--parameter.[N].name` / `--value` | No | Custom build parameters |
| | `--scm.build_commit_id` / `--build_tag` | No | Commit / tag to build |
| | `--job_id` | Yes | Build task ID (path) |

## KooCLI Command Format Standard

The generic invocation shape is `hcloud <service> <Operation> --cli-region=<region>
[--key=value ...]` — this is a **format description only**: `<...>` and
`[--key=value]` are placeholders, never executed verbatim.

| Feature | Rule | Example |
|---------|------|---------|
| Service name | `CodeArtsPipeline` (metadata `codeartspipeline`) / `CodeArtsBuild` (metadata `codeartsbuild`); `CloudBuild`/`CLOUDBUILD` NOT supported | `hcloud CodeArtsBuild ListProjectJobs --cli-region=cn-north-4` |
| Operation name | PascalCase | `ListPipelines`, `ShowBuildRecord`, `DownloadBuildLog` |
| Region parameter | `--cli-region=<value>` always included | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--project_id=xxx` |
| Indexed parameter | `--key.N=value` | `--status.1=failed`, `--steps.1.name=xxx` |
| Nested parameter | `--parent.child=value` | `--scm.build_commit_id=xxx` |
| Array-of-object | `--key.N.sub=value` | `--parameter.1.name=xxx --parameter.1.value=yyy` |
| Verification | Run `--help` first; parameter names come from `--help` output only | `hcloud CodeArtsBuild CreateBuildJob --cli-region=cn-north-4 --help` |

## Tool Parameter Validation (Mandatory)

Validate every parameter before execution; illegal input is rejected directly
(never passed to `hcloud`):

| Validation | Rule |
| ---------- | ---- |
| Whitelist enum | Documented value sets (`--cli-region`, `--build_status`, `--log_level`, `--sort`, `--arch`, ...) must match exactly; anything else → refuse, listing allowed values |
| Type check | Numeric params (`--offset`, `--limit`, `--page_index`, `--page_size`, `--build_no`, `--size`) must be non-negative integers; ID params (`--project_id`, `--pipeline_id`, `--job_id`, `--record_id`) must match their documented format (project_id/job_id 32-char, record_id 36-char UUID); `--is_publish`/`--is_execute` must be boolean |
| Time range | `--start_time`/`--end_time` must be `yyyy-MM-dd HH:mm:ss`; for `ListBuildInfoRecordByJobId` the range should be bounded (e.g. ≤ 31 days) |
| Secret params | Parameter values that look like AK/SK/tokens must never appear in logs/output; only `*`-masked representation is shown |
| Reject unknown | Params absent from `hcloud <Service> <Operation> --help` are rejected before running the command |

### Expected CLI rejections (for verification / boundary cases)

These are **expected error outcomes** — the CLI or API rejects the input and the
rejection itself is the correct result, not a skill defect:

| Input | Expected rejection |
|-------|--------------------|
| Service name `CloudBuild` / `CLOUDBUILD` instead of `CodeArtsBuild` | `[USE_ERROR]不支持的服务名称:CloudBuild` (unsupported service — the supported name is `CodeArtsBuild`) |
| Unknown parameter flag | `[USE_ERROR]不正确的参数:xxx` |
| Non-CodeArts (plain IAM) project id in `--project_id` | `pipeline.00060101 项目不存在` (CodeArts project scope limitation) |
| `ListBuildInfoRecordByJobId` without `--start_time`/`--end_time` | Missing-required-parameter error (`[USE_ERROR]缺少必填参数`) |
| `DownloadBuildRealTimeLog` without `--size` | Missing required `--size` error |
| `ShowBuildRecord` with a non-36-char `--record_id` | Parameter format validation error |
| `RunPipeline` on an already-running non-concurrent pipeline | Concurrent-run conflict error from the API (expected; check run state first) |
| `ListProjectJobs` with `--page_index` < 0 | Parameter validation error |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for CodeArts Pipeline/Build
- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK/profile authentication
- `references/build-error-classification.md` — Build log error pattern catalog (network/parameter/load/code/dependency/permission)
- `references/verification-method.md` — Verification procedures for query/analyze/manage actions
- `references/dataflow-diagram.md` — Mermaid data flow diagrams
- `references/acceptance-criteria.md` — Acceptance criteria for this skill
- `references/test-data-guide.md` — Test-data placeholders and how to backfill them before live runs
- `references/test-report.md` — Test report (syntax + live probes)