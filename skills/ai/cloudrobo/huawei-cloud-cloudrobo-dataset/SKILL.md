---
name: huawei-cloud-cloudrobo-dataset
description: |
  Manage CloudRobo data processing (proc-tasks) and data evaluation (eval-tasks) — query
  algorithms, create/list/show/update/delete/copy tasks; poll task status until
  terminal; retrieve system and job logs; download logs; query task events (normal/warning);
  preview output data and frames;
  discover available algorithms from the asset marketplace; orchestrate processing→evaluation
  pipelines; batch-manage tasks across workspaces; diagnose failures via log analysis; and
  onboard custom data-processing operators (five-phase: deploy mode → code adaptation → image
  build/SWR push or OBS delivery → asset registration → runtime verification).
  Chained evaluation only; standalone simulation evaluation belongs to huawei-cloud-cloudrobo-eval.
  Multi-stage data-cleaning pipelines belong to huawei-cloud-cloudrobo-data-pipeline.
  Triggers include: 数据处理任务, 数据评测任务, 数据处理任务管理, 数据评测任务管理, task copy,
  task status polling, task events, log retrieval for troubleshooting, output data preview,
  algorithm discovery, task pipeline orchestration, batch task management, failure diagnosis,
  custom operator onboarding, dataset, 数据处理(proc-tasks), 数据评测(eval-tasks).
  Also prepare LeRobot manifest.yaml from a local ROS2 bag through terminal
  conversation or the bag2manifest Web workbench. Triggers include bag2manifest,
  ROS2 bag转LeRobot配置, 对话生成manifest.yaml, 启动bag2manifest Web服务, 话题映射.
tags:
  - huawei-cloud-cloudrobo
  - dataset
  - data-processing
  - data-evaluating
  - task-management
  - task-copy
  - task-events
  - log-retrieval
  - algorithm-discovery
  - task-pipeline
  - batch-tasks
  - task-diagnosis
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.
>
> **Windows adaptation pitfalls (verified — avoid these before they cost a run):**
> 1. **`/tmp` is NOT shared between Git Bash and native Python.** Git Bash `/tmp` →
>    `C:/Users/<user>/AppData/Local/Temp`, but Windows Python resolves `/tmp` to `C:\tmp`.
>    A file created by Bash under `/tmp` is invisible to `python`, and vice versa
>    (`FileNotFoundError` on a path that plainly exists in the shell). **Rule:** for any
>    local scratch file consumed by Python, use a directory inside the project
>    (e.g. `.workcheck/`) or a native Windows path (`C:/Users/.../Temp/...`), never bare
>    `/tmp`. The *cloud* paths in this skill (`/tmp/cloudrobo/...`, `/tmp/custom-operator-work-*`)
>    are container paths and are fine — the rule is about the local host.
> 2. **Never inline `python - <<'PY'` heredocs on Windows Git Bash.** The heredoc body can
>    be mangled (CRLF, quoting, backslash escapes) and fails in confusing ways. Write the
>    script to a real `.py` file under the project and run `python <file>`.
> 3. **Backslash paths are escape characters in Bash.** Always use `C:/...` or `/c/...`
>    quoted, never a backslash-separated Windows path.
> 4. **`which` does not exist** on Git Bash — use `command -v ... || echo NOT_FOUND`.
> 5. **Inline JSON on the command line is fragile.** Write `--task-config` / `--result` /
>    `--inputs-file` JSON to a file and pass the file path.
> 6. **`docker` is frequently absent** on Windows hosts. Check `command -v docker` before
>    choosing an image-build path; when it is missing, the only viable deploy mode is
>    OBS-mounted code (no build/push).

## Overview

The `cloudrobo-dataset` skill manages the full lifecycle of CloudRobo data processing
(proc-tasks) and data evaluation (eval-tasks): task CRUD + copy,
status polling, log retrieval (system + job) and download, task event
queries (`get-events`), output data preview and frame extraction,
marketplace algorithm discovery, processing→evaluation pipeline orchestration, batch
management, failure diagnosis, and custom operator onboarding.

**Applicable scenarios:** Task management (CRUD + copy), troubleshooting (log retrieval + error analysis), algorithm discovery, result verification (preview + frames), pipeline orchestration, batch management, analytics.

**Architecture:**

```
Agent / LLM
    │
    ├── CLI  →  cloudrobo dataset proc <command>     (proc-tasks)
    │           cloudrobo dataset eval <command>     (eval-tasks)
    ├── SDK  →  DatasetClient (Python)
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/data-eng/proc-tasks/*
              /v1/data-eng/eval-tasks/*
```

CloudRobo task operations target the `cloudrobo-service` backend and require a `workspace_id`
(default workspace is used unless `--workspace-id` overrides it). Algorithm and dataset discovery is a
cross-package operation that calls the `cloudrobo-asset-manager` service via `cloudrobo asset`.

## Prerequisites

These apply to **executing** task operations. They do not authorize a pre-check: before the
user has said which data and which task, ask the Round-1 question in
[Interactive Task Creation](#interactive-task-creation) — do not run `cloudrobo` queries,
list algorithms/datasets, or inspect directories.

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
workspace configuration. CloudRobo task operations require a valid `workspace_id` (default or
explicit `--workspace-id`).

### Local ROS bag manifest preparation

For local bag profiling or LeRobot `manifest.yaml` preparation, read
[Bag to manifest](references/bag2manifest.md). It covers two modes: terminal conversation
using `scripts/bag2manifest/generate_manifest.py`, and a local Web workbench using
`scripts/bag2manifest/start_web.py`. This stage prepares conversion configuration locally;
it does not create a CloudRobo task or require a workspace. Generate ROS Manifest 2.0
according to [ROS manifest contract](references/ros-manifest-2.0.md). Follow the user’s
automatic or interactive decision preference; Web uses a shared field editor and sampled previews.

## Context budget — read references on demand

This file is the always-loaded core. Everything under `references/` is **not** loaded unless
you open it, so opening one costs context for the rest of the session.

| Situation | Read |
|---|---|
| Onboarding a custom operator | `references/custom-operator/custom-operator-workflow.md` — it is an **index**; open only the part the current phase needs |
| Adapting operator code / deploy mode | `custom-operator/onboarding-phase-0-1.md` |
| Building an image or registering assets | `custom-operator/onboarding-phase-2-3.md` |
| Submitting and verifying a runtime task | `custom-operator/onboarding-phase-4.md` |
| A phase failed, or onboarding finished | `custom-operator/onboarding-post.md` |
| Unsure whether to ask the customer | `custom-operator/phase-boundaries.md` |
| A task FAILED | `custom-operator/failure-analysis-guide.md` |
| Uploading a large dataset to OBS | `custom-operator/obs-upload-guide.md` |
| Cleanup / verification report | `custom-operator/garbage-cleanup-report.md` |
| A step will take many minutes | `custom-operator/progress-feedback.md` |
| Full task_config field tables | `references/task-config-catalog.md` (look up the section) |

Rules:

- **Speed and a simple user interaction come first.** The default path should carry only
  what is needed to act. Do not add pre-checks, extra confirmation rounds, defensive
  validation or tests "just in case" — run the thing, and investigate in depth only after
  something actually fails.
- **Never open more than one reference file in the same step** unless the task genuinely
  needs both. Read the section you need, not the whole file.
- **Do not pre-read** references "just in case". Open them at the moment the step requires.
- If a reference grows past ~400 lines, **split it by topic** and leave a short index behind
  (as `custom-operator-workflow.md` now does) rather than letting it exceed the read limit.
- If context is already tight, prefer a targeted `grep` over a full-file read.

## Workflow

### Interactive Task Creation

**Round 1 is fixed.** When the user's request does not yet state what data to process and
what task to run, do not list algorithms, list datasets, query the workspace, or inspect
directories. Ask only:

> 你要处理哪份数据、跑什么处理或评测？

Only after that answer may you query candidates and derive defaults. Do not re-ask values
the user already supplied.

All interactive creation workflows follow the **Interaction Rules**: display query results
before asking the next question; batch independent questions into one round.

**Proc-Task Creation** (10 steps): Task name → Description → Algorithm type (PRESET_ASSETS/WORKSPACE_ASSETS/OBS_ASSETS) → Algorithm configuration with field mapping → Environment variables (+ operator `inputs` when declared) → Job type and resources (CCE/K8S or CCE_RAY/RAY, resource pool, instance spec) → Dynamic storage (public pool only) → Input datasets (multi-dataset loop) → Output configuration → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

**Eval-Task Creation** (7 steps): Task name → Description → Resource pool and instance spec → Evaluation algorithm (+ operator `inputs` when declared) → Dataset (single) → Optional robot description via the operator's declared `inputs` → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

### Task Polling and Result Handling

> **🎯 Default: Background Polling (non-blocking)** — long-running tasks should
> NOT block the user's window. By default run `wait-task` + result verification
> (`get-preview`/`get-frames`) in the **background** via the Bash tool's
> `run_in_background: true` flag. Only use foreground (blocking) polling when
> the user explicitly asks for "synchronous" / "blocking" / "前台等待" execution.
> See [Background Polling Pattern](#background-polling-pattern-non-blocking) below
> for the exact flow.

1. **Poll status** — `dataset proc wait-task` / `dataset eval wait-task` with `--interval 15 --timeout 1800`,
   report each state change to user, until terminal state (SUCCEEDED/FAILED/DELETED). If
   `wait-task` times out while the task is still non-terminal, re-run `wait-task` — do not
   create a new task. **Use 15s** (balances load vs. responsiveness; shorter floods the API,
   longer delays SUCCEEDED detection).
2. **On completion:**
   - SUCCEEDED: view processing result via `get-preview`, output system log
   - FAILED: ask user whether to view logs, output system and job logs

**Eval tasks:** After SUCCEEDED, extract report path from `target_report_path` in task detail, use `dataset eval get-preview --task-id <task-id> --file-name <obs-path-without-bucket>` to get OBS temporary link.

#### Background Polling Pattern (Non-Blocking)

When a task is created (or when resuming polling after a previous `wait-task` timeout),
**default to launching `wait-task` + post-completion verification (`get-preview` /
`get-frames` + log retrieval) as a single background shell** so the user keeps full
control of the window while the task runs. The flow:

1. **Right after `create-task` returns** (or when re-polling a non-terminal task),
   the agent wraps `wait-task` + verification into one bash script and launches it
   with `Bash(run_in_background: true)`. The agent immediately tells the user:
   - the `task_id`
   - the OBS `target_path` / `output_path`
   - "已转入后台轮询，您可继续其它操作；任务终态（SUCCEEDED/FAILED/DELETED）后我会主动汇报结果"
2. **Inside the background script** (one-shot, exits when terminal):
   ```bash
   # 1. Poll until terminal
   cloudrobo dataset proc wait-task --task-id <task-id> --timeout 1800 --interval 15 \
     > /tmp/wait-task-<task-id>.log 2>&1
   FINAL_STATUS=$(grep -oP '最终状态: \K\w+' /tmp/wait-task-<task-id>.log | tail -1)

   # 2. Branch on terminal state — verification + logs in the SAME background run
   if [ "$FINAL_STATUS" = "SUCCEEDED" ]; then
     echo "=== Output structure (get-frames) ===" >> /tmp/wait-task-<task-id>.log
     cloudrobo dataset proc get-frames \
       --task-id <task-id> \
       --prefix "<obs-output-path-without-bucket>" \
       --max-keys 50 >> /tmp/wait-task-<task-id>.log 2>&1
     echo "=== System log tail ===" >> /tmp/wait-task-<task-id>.log
     cloudrobo dataset proc get-log --task-id <task-id> --is-system true \
       >> /tmp/wait-task-<task-id>.log 2>&1
   elif [ "$FINAL_STATUS" = "FAILED" ]; then
     echo "=== System log (FAILED) ===" >> /tmp/wait-task-<task-id>.log
     cloudrobo dataset proc get-log --task-id <task-id> --is-system true \
       >> /tmp/wait-task-<task-id>.log 2>&1
     echo "=== Job log (FAILED) ===" >> /tmp/wait-task-<task-id>.log
     cloudrobo dataset proc get-log --task-id <task-id> --is-system false \
       >> /tmp/wait-task-<task-id>.log 2>&1
   fi
   ```
   (For eval tasks swap `dataset proc` → `dataset eval` and replace `get-frames` with
   the eval `get-preview` of `target_report_path`.)
3. **When the background task completes**, the agent receives a completion
   notification, reads `/tmp/wait-task-<task-id>.log`, and reports to the user:
   - the terminal status (SUCCEEDED/FAILED/DELETED)
   - for SUCCEEDED: output structure (folders/files) + system log tail
   - for FAILED: full system + job logs + suggested fix patterns
4. **User can keep working** during the wait — they may issue new requests, ask
   questions, or even start other tasks. The agent does NOT hold the window.
5. **Long-running tasks (>30 min):** set `--timeout 3600` (or higher) in the
   background `wait-task` call so a single background run covers the whole job
   without mid-way timeout churn. If a background `wait-task` itself times out
   while the cloud task is still non-terminal, the agent re-launches another
   background `wait-task` (same `task_id`) — never creates a duplicate task.
6. **Multiple concurrent background polls:** each task gets its own
   `/tmp/wait-task-<task-id>.log` file; the agent tracks each background shell
   by its `task_id` and reports each one independently when it completes.

**When to use foreground (blocking) polling instead:**
- User explicitly requests synchronous execution ("前台等待"、"同步等待"、
  "block until done")
- Task is expected to finish within ~2 minutes (e.g. quick dry-run-style validation)
- User is about to chain an immediate dependent step and wants zero latency

In all other cases — **default to background polling** so the user is never
blocked by a long-running cloud task.

### Pipeline Workflow (Task Orchestration)

Scenario: data conversion → data evaluation → download artifact

> **Non-blocking by default:** each `wait-task` step below should run in the
> background per the [Background Polling Pattern](#background-polling-pattern-non-blocking).
> Chain step N+1 inside the same background script as step N's terminal-state
> branch — the agent kicks off the next `create-task`/`wait-task` from within
> the background shell so the user window is never blocked by any wait step.

1. Run processing task, wait for SUCCEEDED (background poll)
2. Extract `target_path` and `target_asset_id` from task detail
3. For the eval task, set top-level `dataset_type`/`dataset_id`(=target_asset_id)/`dataset_name`/`dataset_path`(=target_path) on the task-config
4. Create evaluation task, wait for SUCCEEDED (`dataset eval wait-task --task-id <eval-task-id>`) (background poll)
5. Get report: `dataset eval get-preview --file-name <path-from-target_report_path>` (remove `obs://<bucket>/` prefix)
6. Download artifacts via `download-asset`

### Batch Workflow (Batch Tasks)

Scenario: run same algorithm across multiple datasets

1. Get dataset list (`asset list-assets --type dataset`)
2. Create processing task per dataset (reuse algorithm/resource config from first; only input dataset differs)
3. Collect task_ids, poll status
4. Summarize success/failure/in-progress counts
5. For failed tasks: view logs or re-run by copying the task (`copy-task`)

> ⚠️ **Semantics distinction**: this **Batch Workflow is opt-in** — N tasks, one per dataset,
> only when the user explicitly asks for batch processing. By DEFAULT (including the
> custom-operator Phase 4 flow), **multiple data sources are processed by ONE task via
> `dataset_configs` N entries** (operator consumes the `SOURCE_DATASET_PATH` JSON map).
> Never default to one-task-per-dataset for a multi-source input.

### Diagnosis Workflow (Failure Diagnosis)

Scenario: task FAILED → analyze logs, suggest fixes

1. Get system and user logs
2. Analyze error patterns: OOM → increase `worker_spec.memory`; path not found → check `dataset_configs`; image pull failure → check `image`; parameter error → check `algo_entrance`/`envs`; access denied → check `catalog_id`/permissions
3. Output diagnosis and fix suggestions
4. After confirmation, modify via `update-task` (only `name`/`description`) or re-run via `copy-task`

**Custom operator failures** → fetch `job-std-output.log` and apply the P0-P3 patterns in `references/custom-operator/failure-analysis-guide.md`.

### Analytics Workflow (Data Analysis)

Aggregate task stats by status, algorithm ranking, time trend, failure rate. Output analysis report with root-cause suggestions.

### Long-Running Task Workflow

> **Default to background polling** per the
> [Background Polling Pattern](#background-polling-pattern-non-blocking): start
> `wait-task` with a generous `--timeout` (e.g. 3600s for long jobs) as a
> background shell. The user keeps the window; the agent reports back when the
> background shell completes.

Start `wait-task` with timeout. On timeout, report status and elapsed time; user decides: continue (re-launch another background `wait-task` with same `task_id` — never create a duplicate task) / view logs / terminate.

## CLI Command Format Standard

```bash
cloudrobo dataset proc <command> [OPTIONS]
cloudrobo dataset eval <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Command group | `dataset proc` (proc-tasks), `dataset eval` (eval-tasks) | `cloudrobo dataset proc` |
| Subcommand | kebab-case | `create-task`, `list-tasks`, `show-task` |
| Workspace override | `--workspace-id <id>` | `--workspace-id abc-123` |
| Output format | JSON to stdout | `out(result)` |
| Dry-run | `--dry-run` (create/copy only) | Preview without executing |
| Boolean flag | `--is-system true` / `--all` / `--is-download` | `--is-system true` |
| Event query | `--job-name <name>` | `cloudrobo dataset proc get-events --task-id <id> --job-name <name>` |

> **⚠️ Never pipe CLI output into an inline `python -c "json.load(sys.stdin)"` to extract a field.**
> On failure, `cloudrobo asset create-asset` / `update-version` etc. print a plain
> `错误: ...` line to **stdout**. `json.load` then raises `JSONDecodeError` and masks the real
> error, producing a misleading "shell command failed". Run the command raw first
> (`2>&1 | head -40`), read the actual message, and parse JSON only when the output is
> known to be JSON.

## Core Commands

### Task Management (proc-tasks)

#### Create a data processing task

```bash
cloudrobo dataset proc create-task --name <task-name> --algo-type PRESET_ASSETS --task-config '<json-config>' [--workspace-id <id>] [--wait] [--timeout 1800] [--dry-run]
```

- **SDK:** `client.create_task(req, workspace_id=None)`
- **API:** `POST /v1/data-eng/proc-tasks`

Required task_config fields: `name`, `algo_type` (PRESET_ASSETS / WORKSPACE_ASSETS / OBS_ASSETS, based on Step 3 selection), `algo_name`, `algo_entrance`,
`image`, `algo_id` (required unless `algo_type=OBS_ASSETS`), `catalog_id` (workspace's), `resource_pool_type`, `cluster_type`,
`task_framework_type`, `dataset_configs` (JSON string array, multi-dataset input),
`output_type`, `output_path` (required when `output_type=UDF_OBS_ASSET`), `output_name`, `head_spec` & `worker_spec` (must include `cpu`/`memory`), `worker_num`,
`evs_spec`. For `algo_type=OBS_ASSETS`, `algo_path` and `job_local_path` replace `algo_id`.
Optional: `description`, `envs`, `inputs` (operator input mounts, see
[Operator Inputs](#operator-inputs-ext_metadatainputs)), `resource_id`, `dedicated_pool_name`.
See `references/task-config-catalog.md` for full field mapping.

> **`algo_type` semantics (algorithm reference way — NOT the deploy mode):**
> - `WORKSPACE_ASSETS` — references a **workspace-registered algorithm asset** via `algo_id`
>   (**required**, asset linkage) **and requires** `algo_path` (= asset `code_dir`, mount
>   source) + `job_local_path` (mount path) — verified: omitting them yields `//entrypoint.py`
>   runtime failure. Applies to 把代码打进镜像 (`image_source=custom`) **and** 代码放 OBS、运行时挂载
>   workspace-asset-algorithm (`image_source=custom`, algorithm asset links the image asset)
>   — NOT Mode-A-only.
> - `PRESET_ASSETS` — references a platform preset algorithm via `algo_id` (required).
> - `OBS_ASSETS` — mounts the customer OBS code directly (`algo_path` + `job_local_path`
>   required; `algo_id` optional). This is 代码放 OBS、运行时挂载 OBS algorithm.
> See `references/task-config-catalog.md` for the algo_type-specific field matrix.

**⚠️ Non-Empty Validation:** Except `description`, all parameters cannot be empty values (empty string `""`, `None`, empty dict `{}`). The SDK validates this before API submission. `head_spec`/`worker_spec` must include `cpu` and `memory` (add `gpu`/`npu` as `0` when unused). `dataset_configs` must contain at least 1 dataset entry; empty array `"[]"` is invalid.

#### List tasks

```bash
cloudrobo dataset proc list-tasks [--status RUNNING|SUCCEEDED|FAILED] [--name <name>] [--order-by start_at|update_at|finish_at|create_at] [--order DESC|ASC] [--offset <n>] [--limit <n>] [--user-id <id>] [--algo-name <name>] [--output-name <name>] [--workspace-id <id>]
```

- **SDK:** `client.list_tasks(workspace_id=None, statuses=..., name=..., order_by=..., order=..., offset=..., limit=..., user_id=..., algo_name=..., output_name=...)`
- **API:** `GET /v1/data-eng/proc-tasks?workspace_id=<id>&statuses=<status>`

#### Show task detail

```bash
cloudrobo dataset proc show-task --task-id <task-id>
```

- **SDK:** `client.get_task_detail(task_id)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}`

#### Update a task

```bash
cloudrobo dataset proc update-task --task-id <task-id> --task-config '{"name":"<new-name>"}'
```

Only `name` and `description` can be modified.

- **SDK:** `client.update_task(task_id, task_config: dict)`
- **API:** `PATCH /v1/data-eng/proc-tasks/{task_id}`

#### Delete a task

```bash
cloudrobo dataset proc delete-task --task-id <task-id>
```

- **SDK:** `client.delete_tasks([task_id_1, task_id_2])` (accepts a list; CLI deletes one at a time)
- **API:** `DELETE /v1/data-eng/proc-tasks?ids=id1,id2`

#### Copy a task

```bash
cloudrobo dataset proc copy-task --task-id <task-id> --name <new-name> --output-name <new-output-name> [--task-config '<json>'] [--wait] [--timeout 1800] [--dry-run]
```

`--name` and `--output-name` are required. Other fields are fetched from `show-task`
(`get_task_detail`) and can be overridden via `--task-config`. The new task starts in `PENDING`.
Keep every input's exact `dataset_configs[].version_id`; never replace it with the asset's
latest version. Check the copied task detail retains the original asset/version/path.

- **SDK:** `client.copy_task(task_id, req={"name": ..., "output_name": ...})`
- **API:** `POST /v1/data-eng/proc-tasks/{task_id}/copy`

**Note:** proc-tasks do **not** support restart — to re-run a task, use `copy-task`.

### Task Monitoring

#### Wait for task to reach terminal state

```bash
cloudrobo dataset proc wait-task --task-id <task-id> [--timeout 1800] [--interval 10]
```

Terminal states: `SUCCEEDED`, `FAILED`, `DELETED`

- **SDK:** `client.wait_task(task_id, timeout=1800, interval=10, on_status=callback)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}` (polled)

#### Retrieve task logs

```bash
# Step 1: List log files to get file_path
cloudrobo dataset proc get-log --task-id <id> --is-system true
cloudrobo dataset proc get-log --task-id <id> --is-system false

# Step 2: Get log content (default: latest 64KB tail)
cloudrobo dataset proc get-log --task-id <id> --file-name <name> --file-path <path>

# Get full log (not just tail)
cloudrobo dataset proc get-log --task-id <id> --file-name <name> --file-path <path> --all
```

- **SDK:** `client.list_log_files(task_id, is_system=True)` → `client.get_task_log(task_id, file_name, file_path, start_byte, end_byte)` or `client.get_task_log_tail(task_id, file_name)`
- **API:**
  - `GET /v1/data-eng/proc-tasks/{task_id}/logs?is_system=true|false`
  - `GET /v1/data-eng/proc-tasks/{task_id}/logs/{file_name}?start_byte=&end_byte=&file_path=&job_id=`

#### Download a log file

```bash
cloudrobo dataset proc download-log --task-id <id> --file-name <name> --file-path <path>
```

- **SDK:** `client.download_task_log(task_id, file_name, file_path)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/logs/{file_name}/download`

#### Get task resource usage

```bash
cloudrobo dataset proc get-resource-usage --task-id <task-id> --metric CPU_UTIL|CPU_USED_CORE|MEM_UTIL|MEM_USED_MB|NETWORK_TX_RATE|NETWORK_RX_RATE|DISK_READ_KB|DISK_WRITE_KB --start <unix-ts-sec> --end <unix-ts-sec> --step <10-3600>
```

- **SDK:** `client.get_task_resource_usage(task_id, metric, start, end, step)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/resource-usage?metric=&start=&end=&step=`

#### Get task events

```bash
cloudrobo dataset proc get-events --task-id <task-id> --job-name <job-name>
```

Returns the task's runtime events (NORMAL/WARNING), first/last occurrence time (Unix timestamp), description, and count.

- **SDK:** `client.get_task_events(task_id, job_name)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/events?job_name=<job-name>`

### Data Preview

#### Preview task output data

Get OBS temporary download link for a dataset file. `file_name` = OBS path excluding bucket name (e.g., `cloudrobo/f91cee72-.../1ddf1498-.../data/chunk-000/file-000.parquet`).

```bash
cloudrobo dataset proc get-preview --task-id <task-id> --file-name <obs-path-without-bucket> [--is-download]
```

- **SDK:** `client.get_task_preview(task_id, file_name, is_download=False)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/preview?file_name=<file_name>&is_download=<bool>`

#### Get task frames

Query directory file list of task input/output datasets. `prefix` = dataset OBS path excluding bucket name (e.g., `cloudrobo/f91cee72-.../1ddf1498-.../`). Pagination uses `--max-keys` (≤50) and `--next_marker` (value from the previous response).

```bash
cloudrobo dataset proc get-frames --task-id <task-id> --prefix <obs-path-without-bucket> [--max-keys <1-50>] [--next_marker <marker>]
```

- **SDK:** `client.get_task_frames(task_id, prefix, max_keys=..., next_marker=...)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/frames?prefix=<prefix>&max_keys=&next_marker=`

### Evaluation Tasks (eval-tasks)

Evaluation tasks differ from processing tasks in field names, deletion granularity, and supported
operations. See the full comparison table in `references/task-config-catalog.md`.

#### Create an evaluation task

```bash
cloudrobo dataset eval create-task --name <task-name> --task-config '<json-config>' [--workspace-id <id>] [--wait] [--timeout 1800]
```

- **SDK:** `client.create_eval_task(req, workspace_id=None)`
- **API:** `POST /v1/data-eng/eval-tasks`

**task-config field description**:

The eval-task task-config uses **top-level single-value dataset fields** (`dataset_type`, `dataset_id`, `dataset_name`, `dataset_path`) **plus a single-item `dataset_configs` JSON-array string**. For `BUILD_IN_ASSET`, include the exact input `version_id` in that entry and keep asset/name/path/type consistent with the top-level fields. See [version handoff and cloning](references/task-config-catalog.md#dataset-version-handoff).

Common required fields: `name`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `dataset_type`, `dataset_name`, `dataset_path`, `dataset_configs`, `resource_pool_type`, `worker_spec`. `dataset_id` is additionally required when `dataset_type=BUILD_IN_ASSET`.

Optional: `description`, `resource_id`, `dedicated_pool_name`, `workspace_id`, `envs`, `inputs`
(operator input mounts, see [Operator Inputs](#operator-inputs-ext_metadatainputs)).

**⚠️ Key reminders**:
- Unlike proc-tasks, eval task-config does **not** include `algo_type`, `catalog_id`, `cluster_type`, `task_framework_type`, `head_spec`, `worker_num`, `evs_spec`, or `output_type`/`output_path`/`output_name`
- `worker_spec` must include `cpu` and `memory` keys
- `robot_config` has been removed from eval tasks — never send it. Config files such as the
  robot description (robots.yaml / URDF) are mounted from OBS only through the operator's
  declared `inputs` (e.g. `ROBOT_CONFIG_PATH`). Without a mount, run with the operator's
  built-in/default configuration, including manifest-mode input; explain unavailable
  robot-dependent metrics. Do not ask for a path by default.
- If the CLI/SDK still rejects an eval task for missing `robot_config`, the client is outdated:
  upgrade it; never add the field, invent a path or bypass the client. See
  [config mount guidance](references/task-config-catalog.md#eval-robot-config-compatibility).
- `dataset_name` cannot be empty (extract from OBS path last directory for UDF_OBS_ASSET)
- `dataset_type` values: `BUILD_IN_ASSET` / `UDF_OBS_ASSET`
- `algo_type` is not a field; the algorithm is identified by `algo_id`/`algo_name`/`algo_entrance`/`image`

See `references/task-config-catalog.md` for full field mapping and eval-task field differences.

#### List evaluation tasks

```bash
cloudrobo dataset eval list-tasks [--status <status>] [--name <name>] [--order-by start_at|update_at|finish_at|create_at] [--order DESC|ASC] [--offset <n>] [--limit <n>] [--user-name <name>] [--dataset-name <name>] [--workspace-id <id>]
```

- **SDK:** `client.list_eval_tasks(workspace_id=None, statuses=..., name=..., order_by=..., order=..., offset=..., limit=..., user_name=..., dataset_name=...)` (`--limit` defaults to 20)
- **API:** `GET /v1/data-eng/eval-tasks?workspace_id=<id>`

#### Show evaluation task detail

```bash
cloudrobo dataset eval show-task --task-id <task-id>
```

- **SDK:** `client.get_eval_task_detail(task_id)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}`

#### Update an evaluation task

```bash
cloudrobo dataset eval update-task --task-id <task-id> --task-config '{"name":"<new-name>"}'
```

Only `name` and `description` can be modified.

- **SDK:** `client.update_eval_task(task_id, task_config: dict)`
- **API:** `PATCH /v1/data-eng/eval-tasks/{task_id}`

#### Delete an evaluation task (single granularity)

```bash
cloudrobo dataset eval delete-task --task-id <task-id>
```

- **SDK:** `client.delete_eval_task(task_id)`
- **API:** `DELETE /v1/data-eng/eval-tasks/{task_id}`

**Note:** eval-tasks deletion is single-task granularity (`delete-task`, not batch). eval-tasks do
not support restart — to re-run, use `copy-task`.

#### Copy an evaluation task

```bash
cloudrobo dataset eval copy-task --task-id <task-id> --name <new-name> [--task-config '<json>'] [--wait] [--timeout 1800] [--dry-run]
```

Only `--name` is required (`--output-name` does not apply to eval tasks). Other fields are fetched
from `eval show-task` (`get_eval_task_detail`) and can be overridden via `--task-config`. The new
task starts in `PENDING`.
Keep both top-level dataset identity and single-item `dataset_configs` with the original
exact version. For a historical task without version metadata, follow the
[version handoff rules](references/task-config-catalog.md#dataset-version-handoff) before copying.

- **SDK:** `client.copy_eval_task(task_id, req={"name": ...})`
- **API:** `POST /v1/data-eng/eval-tasks/{task_id}/copy`

#### Wait for evaluation task to reach terminal state

```bash
cloudrobo dataset eval wait-task --task-id <task-id> [--timeout 1800] [--interval 10]
```

Terminal states: `SUCCEEDED`, `FAILED`, `DELETED`. Status changes are printed as they occur.
On timeout the command returns the latest detail while the task may still be running —
re-run `wait-task` instead of creating a new task. To wait for several evaluation tasks in
parallel, create them without `--wait`, record each `task_id`, then run `wait-task` per task.

- **SDK:** `client.wait_eval_task(task_id, timeout=1800, interval=10, on_status=callback)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}` (polled)

#### Retrieve evaluation task logs

```bash
# Step 1: List log files
cloudrobo dataset eval get-log --task-id <id> --is-system true
cloudrobo dataset eval get-log --task-id <id> --is-system false

# Step 2: Get log content (default: latest 64KB tail; --all for full content)
cloudrobo dataset eval get-log --task-id <id> --file-name <name> --file-path <path> [--all]
```

- **SDK:** `client.list_eval_log_files(task_id, is_system=True)` + `client.get_eval_task_log(task_id, file_name, ...)` / `client.get_eval_task_log_tail(...)`
- **API:**
  - `GET /v1/data-eng/eval-tasks/{task_id}/logs?is_system=true|false`
  - `GET /v1/data-eng/eval-tasks/{task_id}/logs/{file_name}?file_path=&job_id=`

#### Get evaluation task preview

`file_name` is the OBS path of the report file (excluding bucket name). Extract from task detail's `target_report_path` by removing `obs://<bucket-name>/` prefix.

For example: if `target_report_path` is `obs://cloudrobo-test-203/eval_task/report/abc-123/diversity_evaluation_report.pdf`, then `file_name` = `eval_task/report/abc-123/diversity_evaluation_report.pdf`.

```bash
cloudrobo dataset eval get-preview --task-id <task-id> --file-name <obs-path-without-bucket> [--is-download]
```

- **SDK:** `client.get_eval_task_preview(task_id, file_name, is_download=False)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}/preview?file_name=<obs-path-without-bucket>&isDownload=`

Returns OBS temporary URL. Use `--is-download` for download link, omit for preview link. Save or download promptly.

#### Download an evaluation log file

```bash
cloudrobo dataset eval download-log --task-id <id> --file-name <name> --file-path <path> [--is-download]
```

- **SDK:** `client.download_eval_task_log(task_id, file_name, file_path)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}/logs/{file_name}/download`

#### Get evaluation task events

```bash
cloudrobo dataset eval get-events --task-id <task-id> --job-name <job-name>
```

Returns the eval task's runtime events (NORMAL/WARNING), first/last occurrence time (Unix timestamp), description, and count.

- **SDK:** `client.get_eval_task_events(task_id, job_name)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}/events?job_name=<job-name>`

**Note:** eval-tasks do **not** support `get-frames` or `get-resource-usage` (proc-tasks only).

### Algorithm Discovery

#### List available algorithms

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" [--name <fuzzy-name>] [--limit 20]
```

- **SDK (cross-package):** `asset_client.list_publication_assets(type="algorithm", sub_type="data_processing", limit=20)`
- **API:** Cross-package — calls the asset service, not the dataset service directly.

Each algorithm includes `ext_metadata` with `engine.image_url`, `command`, and
`environment_variables` needed for task creation. Use `--tags "Data Evaluation"` to discover
evaluation algorithms.

> **Query fresh every time**: re-run `list-publication-assets` before every task submission
> and extract `image`/`command`/`inputs` from the **current** result. Never reuse operator
> info from a previous run — the platform updates algorithm assets (new image versions,
> fixed commands), and a stale image can silently fail (e.g. manifest mounts unsupported in
> the old image).

#### Operator Inputs (`ext_metadata.inputs`)

`ext_metadata.inputs` declares optional/required external inputs (config/model paths)
that the algorithm mounts at task run time. Read `ext_metadata.inputs` from the **current**
query when constructing task_config (proc or eval) and carry the inputs to be mounted in the
task_config `inputs` field:

- `inputs` is a JSON-array **string** field (like `dataset_configs`/`envs`)
- Each provided element is the complete `ext_metadata.inputs[]` element, copied as returned
  by the current query (do not add or strip fields), with `url_path` set to the
  user-selected `obs://` path. Never use `obs_path` as an inputs key.
- `required: true` inputs with a built-in `url_path` need no user action and do not need to
  be listed in `inputs`; `required: true` inputs with an empty `url_path` must be supplied
  by the user and included in `inputs`
- `required: false` inputs are optional — do not prompt by default; omit them (omit the
  whole `inputs` field when nothing needs to be mounted)
- If the operator's current `ext_metadata` has no `inputs`, omit the `inputs` field

```text
"inputs": "[{\"name\":\"<name as returned>\",\"label\":\"<as returned>\",\"required\":false,\"url_path\":\"obs://bucket/config/\",\"input_type\":\"<as returned>\",\"description\":\"<as returned>\",\"access_method\":\"env\"}]"
```

See `references/task-config-catalog.md` → "Operator Inputs Mount" for the full structure,
known operator inputs (reference only), and priority rule.

Input datasets do not universally require YAML files. Default to the selected operator's built-in
`robot` environment/default configuration; fall back to an existing dataset config or optional external
config mount only if the operator declares `ext_metadata.inputs` and the run needs a custom config.
[manifest candidate rules](references/task-config-catalog.md#manifest-config-names);
manifest mode alone does not require an external file or an evaluation config mount.

#### Custom operator onboarding

For **custom data processing operators** (user code that needs containerizing, SWR push,
or OBS delivery + asset registration), follow the five-phase pipeline in
[Custom Operator Onboarding](#custom-operator-onboarding) below.

<a id="custom-operator-onboarding"></a>
## Custom Operator Onboarding

> **术语映射（对用户说话时必须用中文，不要原样搬英文术语）**：
> - "Custom Operator Onboarding" → **自定义算子上云**
> - "onboarding" → **上云**
> - "Phase 0/1/2/3/4/5" → **阶段 0/1/2/3/4/5**
> - "Phase 0: Deploy Mode & Asset Detection" → **阶段 0：部署方式与资产检测**
> - "Phase 1: Code Adaptation" → **阶段 1：代码适配**
> - "Phase 2: Build & Push" → **阶段 2：构建并推送镜像**
> - "Phase 3: Asset Registration" → **阶段 3：资产注册**
> - "Phase 4: Runtime Verification" → **阶段 4：运行时验证**
> - "Phase 5: Cleanup & Report" → **阶段 5：清理并生成报告**
> - "Deploy mode" → **部署方式**
> - 内部代号 "image-inbuilt" → **把代码打进镜像**：把你的代码和依赖一起打进 Docker 镜像，
>   每次提交都重建并推送一个新镜像；环境完全自包含，适合依赖重或难复现的算子
> - 内部代号 "OBS-mounted" → **代码放 OBS、运行时挂载**：代码上传到 OBS，任务运行时挂载进
>   一个已有的运行时镜像；不构建镜像，改代码可秒级重跑，适合小算子或已有合适镜像
>   - 该方式下的两种引用形态：
>     - **注册成空间里的算法资产后引用**：先注册算法资产，任务按资产引用，后续可复用查询
>     - **不注册资产、直接挂载 OBS 代码**：不建任何资产，任务直接挂载代码目录
> - "work copy" → **工作副本**
> - "Failure Analysis Engine" → **失败分析引擎**
> - 本节其余英文是 skill 内部技术文档；对用户呈现时按上表翻译，不要在对话里出现
>   裸英文的 "Phase X: ..."、"onboarding"、"workflow" 等术语或代号。
>   **禁止用 A/B 之类字母代号与用户沟通**——始终用上面描述实际做法的中文短语。

Onboard user-developed data-processing operators to CloudRobo in an orchestrated
five-phase pipeline. **Core design principle: never modify the user's original code** —
the skill copies the user's code read-only into a temporary work copy
(`/tmp/custom-operator-work-{timestamp}/`) and generates all adaptation artifacts
(`entrypoint.py`, `Dockerfile`, `operator_config.json`) there only.

> **⚠️ Back up before copying.** Before creating the work copy, copy the user's source file(s)
> to an explicit backup location with a timestamped name (e.g.
> `<project>/.workcheck/backup/<name>.<timestamp>.py`) and state the backup path in the
> pre-create summary. The work copy is not a backup — it is disposable and cleaned up in
> Phase 5. Never edit the original file in place, even to "fix a small bug"; all changes go
> into the work copy.

> **⚠️ Adaptation must be reported, not just performed.** Phase 1 changes the user's code
> contract. Before uploading anything, state each adaptation in the user's language —
> what changed (input traversal and file filtering, output root layout, dataset-creation
> directory constraints, and any other fix needed for the code to run on the platform) and
> why. A bare "code adapted" is not acceptable.

两条部署路线。**顺序硬约束：先备份 → 建工作副本 → 适配 → 本地试跑（需用户确认）
→ 再问部署方式/镜像/启动命令。** 镜像与启动命令是"代码跑通之后才成立的运行时参数"，
试跑结果未确认前不得询问。

```
路线① 把代码打进镜像：代码和依赖一起构建进 Docker 镜像，每次提交重建并推送新镜像
  阶段1 备份 + 工作副本 + 生成入口 → 本地试跑（用户确认）
  → 阶段0 选部署方式（此时才问镜像/启动命令） → 阶段2 docker build + push
  → 阶段3 注册镜像资产 + 算法资产 → 阶段4 试跑验证 → 阶段5 清理报告

路线② 代码放 OBS、运行时挂载：代码上传 OBS，任务运行时挂载进一个已有的运行时镜像
  阶段1 备份 + 工作副本 + 生成入口 → 本地试跑（用户确认）
  → 阶段0 选部署方式（此时才问镜像/启动命令/OBS 路径） → 阶段2 跳过（不构建镜像）
  → 阶段3 注册算法资产（引用预设镜像）；若选择"不注册资产、直接挂载"，本阶段整体跳过
  → 阶段4 试跑验证 → 阶段5 清理报告

  路线② 的两种引用形态：
    · 注册成空间里的算法资产后引用 → 任务按算法资产引用，后续可复用查询
    · 不注册资产、直接挂载 OBS 代码 → 不建任何资产，任务直接挂载代码目录

失败 → 失败分析引擎（读作业日志定位模式并修复）→ 出结果后必须清理
```

**Decisions: recommend first, ask only when it matters.** The user wants their code running
on the platform, not a platform tutorial. For each decision below, **apply the recommended
default and state it**; ask only when the user's answer would materially change the outcome
or when the choice is genuinely ambiguous. Present at most **one** question round, with
recommendations pre-selected.

| Decision | Recommended default | Ask only when |
|----------|--------------------|---------------|
| **Deploy mode** | **Ask once, in one short line.** Options: (a) platform image asset already in the workspace — user names it; (b) user supplies an SWR image URL; (c) build the image locally (only when Docker exists); (d) mount code from OBS onto an existing runtime. Prefer 把代码打进镜像 when Docker is available (dependencies are installed with the image, most reliable); otherwise 代码放 OBS、运行时挂载. Never pick silently just because Docker is absent locally | Always ask once. Missing Docker is a reason to **ask**, not a reason to decide |
| **Runtime image** | **Never inferred by the Agent.** Take it from the user: a workspace image asset they name, or an SWR URL they paste | Always. Do NOT scan `list-assets --type image`, past runs, or other people's images to find a "suitable" one — a 40-image scan is slow and usually lands on the wrong runtime |
| **代码放 OBS 时的任务引用方式** | **workspace-asset-algorithm** (`WORKSPACE_ASSETS` + `algo_id`) — reusable, appears in later `list-assets`, no per-task code paths | The user explicitly wants code mounted without registering an asset (`OBS_ASSETS`) |
| **Input-dataset source** | **Reuse an existing dataset asset** if one matches; otherwise **auto-create one** (`BUILD_IN_ASSET`) | Multiple datasets are plausible and picking wrong would be costly; or the user supplies an `obs://` path directly |

Do not enumerate all platform options for the user. Ask the deploy mode in **one short
line** (platform image asset / user-provided image URL / build locally / mount code from
OBS), then move on. Never present a pre-made deployment decision as settled.

> **🚫 Do not shop for an image.** Scanning workspace image assets to "recommend" a runtime
> is forbidden unless the user explicitly asks you to look. It burns many rounds and the
> scanned image frequently lacks the operator's dependencies. Ask, then look up only the
> image the user named (`list-assets --type image --name "<name>"` + `show-version`).

> **🚫 不要用历史记忆或旧资产填运行时参数。** 镜像 URL、解释器路径、挂载点这三项，
> 只要不是**用户在本次对话里亲口给出**，就不能作为"建议值"填进表单——包括上一轮会话
> 记忆、`~/.cloudrobo/pipeline-runs/`、旧算法资产的 `ext_metadata`。表单里这三项留空，
> 或写 `<待你填写>`，并明确说"这三项需要你给，我不推断"。把历史值填成"建议值"再让用户
> 说"可以"，等于把推断包装成了用户决策。
>
> **🚫 用户给的值不完整时，问，不要查。** 例如用户贴的镜像地址中间是省略号、缺 tag、
> 缺 namespace——这是**信息缺失**，不是**检索任务**。正确做法是一行话问回去：
> "这个地址中间的 namespace/tag 是什么？" 绝不能为了补全它去 `list-assets --type image`
> 全量扫描、或翻旧算法资产反查。只有用户**点了名**（完整仓库名或算子名）时，
> 才允许 `--name` 精确查那一个。
>
> **判定标准：** 我准备填进表单的这个值，来自用户本次的原话，还是来自"我记得以前用过"？
> 后者一律不填。

> **⚠️ 选择「代码放 OBS、运行时挂载」前先确认依赖：** 挂载的代码不会安装
> `requirements.txt`。请确认目标镜像已包含算子导入的所有第三方包（
> 可询问用户或检查镜像）。若缺少任何一个（`h5py`、`numpy`、
> `Pillow`、`lerobot`、`ray` 等），该方式会在运行时失败并报
> `ModuleNotFoundError`。此时要么改用「把代码打进镜像」（在构建时执行
> `RUN pip install -r requirements.txt`），要么确认用户的镜像已内置这些依赖。

**Default-path details (for the Agent, not for display):**

- **把代码打进镜像（内部代号 image-inbuilt，`custom`）** — only when the default does not fit: every submission
  rebuilds + pushes a **new image** (timestamp tag; SWR login auto-generated from AK/SK — on
  auto-credential failure, classify the cause (AK/SK invalid/expired, SWR not enabled / IAM
  permission missing, region mismatch, network) and ask the user to fix / provide a full
  `docker login` command, see `references/custom-operator/onboarding-phase-2-3.md` §Step 2.0).
- **workspace-asset-algorithm**: `WORKSPACE_ASSETS` + `algo_id` (Phase 3 asset) +
  `algo_path` (= asset `code_dir`) + `job_local_path` + **literal absolute** `algo_entrance`
  (asset linkage, registration runs). **Phase 3 algorithm-asset engine must reference the created
  image asset via `asset_id` + `asset_version_id` (workspace-asset-image),
  `image_source=custom` (image_url + preset alone does not link the image asset).**
- **OBS algorithm**: `OBS_ASSETS` + `algo_path` + `job_local_path`, no `algo_id`,
  **Phase 3 skipped**。
- **Input-dataset source**: **workspace-asset-data** (`BUILD_IN_ASSET` — ① auto-create a
  dataset asset (`create-asset type=dataset` + `create-version` + `update-version RELEASE`)
  or ② reuse an existing data asset; one → default / multiple → multi-select ≤10) and
  **OBS storage** (`UDF_OBS_ASSET` — ③ an `obs://` path directly; the `dataset_configs`
  entry has only `obs_path` + `dataset_type` — **no data asset is created or referenced**).
  **⚠️ An `obs://` path in ③ must use the workspace-bound bucket**: it must equal the bucket
  of `default_obs_path` from `cloudrobo workspace current` (no other bucket is supported);
  reject a mismatch and ask again with `default_obs_path` shown as the reference.
  **Multiple data sources (≤10) merge into multiple `dataset_configs` entries and create
  ONE task — never split by data source**; per-dataset tasks only on an explicit batch
  request with the N-way split confirmed first.

> **⚠️ Orchestration flow:** the `cloudrobo` CLI has **no `operator` command group** — the
> pipeline composes real commands (`cloudrobo asset`, `cloudrobo dataset proc`, Docker);
> CLI/SDK/API equivalence & API paths (audit only) in `references/dataflow-diagram.md` §API Path Summary.

**Executable steps live in the operator references** (SKILL.md keeps only this summary):
- [Custom Operator Workflow](references/custom-operator/custom-operator-workflow.md) — **index** of the onboarding guide; read only the part you need:
  [Phase 0/1](references/custom-operator/onboarding-phase-0-1.md) · [Phase 2/3](references/custom-operator/onboarding-phase-2-3.md) · [Phase 4](references/custom-operator/onboarding-phase-4.md) · [post-onboarding](references/custom-operator/onboarding-post.md) · [phase boundaries](references/custom-operator/phase-boundaries.md) · [cleanup & report](references/custom-operator/garbage-cleanup-report.md) · [progress feedback](references/custom-operator/progress-feedback.md) · [failure analysis](references/custom-operator/failure-analysis-guide.md) · [OBS upload](references/custom-operator/obs-upload-guide.md)
- [Custom Operator Reference](references/custom-operator/custom-operator-reference.md) — **index**: [operator-config-catalog](references/custom-operator/operator-config-catalog.md) · [deploy-mode-comparison](references/custom-operator/deploy-mode-comparison.md) · [interaction-guidelines](references/custom-operator/interaction-guidelines.md) · [verification-report](references/custom-operator/verification-report.md)

**Key constraints (authoritative detail: `custom-operator/onboarding-phase-2-3.md`, `custom-operator/onboarding-phase-4.md`, `custom-operator/failure-analysis-guide.md`):**

1. **Asset names = the dialogue-confirmed operator name** (no silent rename / auto suffix; verify via `show-asset`).
2. **Image asset FIRST, algorithm asset SECOND**; the algorithm MUST link the image asset via `engine.asset_id` + `engine.asset_version_id` + `engine.image_source=custom` (`image_url` alone is NOT linked); never pass `--sub-type` with `--tags`; asset `url` is an OBS path.
   **⚠️ `image_source` is determined by WHERE the image came from, not by convenience:**
   - the user's own uploaded/registered image asset (空间资产-镜像) ⇒ `image_source=custom` + `engine.asset_id` + `engine.asset_version_id` linking that asset. **This is the normal case and must be used whenever the user says they already uploaded an image.**
   - a platform published preset image with no workspace asset ⇒ `image_source=preset` (no asset linkage).
   Never silently switch a user-supplied image to a platform preset image. If the user names their uploaded image asset, resolve it with `cloudrobo asset list-assets --catalog-id <id> --type image --name "<name>"`, then `show-version` for the exact `version_id`, and link it with `custom`. Switching images changes the runtime environment and invalidates the user's confirmed plan — reconfirm first.
3. `envs` MUST exclude platform-injected `SOURCE_DATASET_PATH`; 代码放 OBS、运行时挂载 `algo_entrance` is **absolute and literal**.
   **⚠️ `{job_local_path}` in the docs is a descriptive placeholder, NOT a platform substitution!** The platform does
   NOT replace `{job_local_path}` at runtime — submitting `python3 {job_local_path}/entrypoint.py` fails with
   `python3: can't open file '.../{job_local_path}/entrypoint.py': [Errno 2]`. Before `create-task`, replace
   `{job_local_path}` with the actual value of the task_config `job_local_path` field (e.g. `job_local_path=/opt/operator`
   ⇒ `algo_entrance="python3 /opt/operator/entrypoint.py"`). The same applies to the algorithm asset's
   `ext_metadata.command`.
   **⚠️ Use the task image's own packaged interpreter, not the bare `python3`.** In preset CloudRobo images the
   bundled Python with the operator dependencies lives at `/home/service/opt/cloudroboh5/bin/python`. Bare
   `python3` resolves to the *system* interpreter, which lacks `h5py`/`numpy`/`lerobot`/… and fails with
   `ModuleNotFoundError`. Preferred entrance form:
   `"/home/service/opt/cloudroboh5/bin/python {job_local_path}/entrypoint.py"` (with `{job_local_path}` replaced
   by the real path). Verify the interpreter path for the chosen image before submitting.
4. **Dependencies must be present in the runtime image.** 代码放 OBS、运行时挂载 (OBS-mounted code) does **NOT** install
   `requirements.txt` — it only mounts the code. Every third-party import (`h5py`, `numpy`, `Pillow`, `lerobot`, …) must
   already exist in the image or the task fails with `ModuleNotFoundError: No module named 'xxx'`. If the reused
   image lacks them, either (a) rebuild the image with `RUN pip install -r requirements.txt` (image-inbuilt mode), or
   (b) add an explicit `pip install` step to the generated `entrypoint.py` at runtime (slow, needs network, not
   recommended). Never assume a customer-provided "runtime" image carries the operator's Python dependencies.
5. New dataset version MUST be `RELEASE`; every name / `output_name` unique per run (timestamp suffix; duplicates → `400 The asset name is existed`).
6. 把代码打进镜像 registers a **new image every submission**; re-submission = `create-version` + `update-asset` (**never re-`create-asset`**); create tasks **without `--wait`**, poll.
7. **把代码打进镜像 re-run after a FAILED verification** ⇒ re-submission branch; before `create-task` `show-asset` the algorithm points at the **new** image version + re-validate dataset sources. `create-task` **HTTP 500** after a rebuild ⇒ stale linkage or stuck `DRAFT` output asset — re-point, fresh `output_name`, wait ~30 s, retry once; still 500 → `trace_id` + support (details: `custom-operator/failure-analysis-guide.md` pattern 5d).
8. **Output layout:** single-dataset conversion writes **flat** into the output root (no nested `{output_name}` subfolder; multi-dataset `{dataset_index}_` prefix only); no `.cloudrobo-tmp` folder left in the output.
   **⚠️ Pre-built dataset formats (LeRobot v2.1 / v3) must land directly at the output root**, not in a
   per-file subfolder. The downstream cleaning / evaluation operators mount the output root as the
   dataset root and require `<root>/meta/info.json`. Writing `<root>/<h5-stem>/meta/info.json` makes them
   fail with `FileNotFoundError: .../meta/info.json does not exist: input is not a valid LeRobot v3
   dataset`. Also note `LeRobotDataset.create()` internally calls `root.mkdir(exist_ok=False)`, so it
   needs a path that does not exist yet — but `TARGET_DATASET_PATH` (e.g. `/tmp/target/dataset`) is a
   **platform mount point that already exists and cannot be removed** (`rmdir` → `PermissionError:
   [Errno 13]`). Correct pattern: build into a staging subdirectory under the output root, then **merge
   the produced tree into the root with a recursive file-level copy** (`rglob` + `copy2`) and delete the
   staging dir. Never `shutil.move` a directory into an existing target directory — it nests
   (`<root>/<child>/<child>`) and silently drops files, leaving an incomplete `meta/episodes/`.
9. **MANDATORY pre-create confirmation.** Before the FIRST mutating call that creates the
   operator's assets (`create-asset` for the image, or the algorithm asset, or the OBS code
   upload), present ONE consolidated parameter summary to the user and wait for explicit
   approval. The summary must state, in the user's language:
   - operator name and description
   - **backup path of the original code** and confirmation that the original file stays unmodified
   - **each code adaptation** (input contract, output layout, file filtering, other fixes) and why
   - deploy path in plain words (code on OBS mounted at runtime / code built into image)
   - runtime image, the exact interpreter + entrance command (e.g. `/home/service/opt/cloudroboh5/bin/python /opt/operator/entrypoint.py`)
   - code OBS path (`code_dir`) and mount path (`job_local_path`)
   - dependency status: which packages are required and whether the image is verified to have them
   - resource pool and spec (public pool 4c8g by default)
   Do NOT create assets before the user confirms. After a failure that changes any of these
   values (image, entrance, dependencies, code path), re-confirm the changed values before
   re-submitting. This is a hard gate, distinct from the "one question round" for defaults.
   **When onboarding is triggered by a parent pipeline, this gate is the child-plan approval —
   the parent pipeline's confirmation does not satisfy it.**

### Interaction Guidelines

The single authoritative definition of dialogue logic lives in
`references/custom-operator/interaction-guidelines.md` (System Prompt interaction-control
layer, S1–S16 response library, test cases); when wording conflicts, that file wins.

**Recommend first, ask only when it matters.** Do not walk the user through a platform
tutorial. For every decision:

1. **Apply the recommended default** (代码放 OBS、运行时挂载 / workspace-asset-algorithm / reuse existing
   dataset / public pool 4c8g / derived task name).
2. **State it in one short line** — no enum values, no IDs, no field names.
3. **Ask only when** the answer materially changes the outcome, or the choice is genuinely
   ambiguous (see the decision table in §Custom Operator Onboarding).

Batch all remaining independent questions into **one round**, each with a recommendation
pre-selected. Never split independent questions across turns.

Other core rules: display query results before asking; double-confirm high-risk operations
(docker push, OBS upload, create-asset/version/update, create-task, deletion); refuse
out-of-scope requests and disclaim; "continue" resumes from the last successful phase
(`--reuse-workdir`).

**⛔ No archaeology 不要翻旧资产.** Do not browse existing platform resources unless the
customer asked. No scanning the workspace catalog for a reusable image, no opening old
algorithm assets to copy their `image_url` / `command` / `code_dir` / `envs`, no reading old
tasks or past runs to infer parameters, no `list-assets` without `--exact-name`. Same-name
detection is the **only** sanctioned catalog query, and it is scoped to the exact operator
name.

The values that decide whether a custom operator runs — **runtime image, interpreter and
entrance command, mount path, dependency availability** — belong to the customer. Present
one recommended form with the uncertain items explicitly marked, then let the customer edit
it. Never substitute a value found on someone else's asset for the customer's decision.
Verified failure: an agent listed 57 workspace algorithms, lifted an image and a
`cloudrobov3` interpreter path from unrelated legacy operators, and presented them as
settled; the customer rejected it outright. Fresh operators use fresh names — a name
collision is answered with a new timestamped name, not with a trip through the old asset.

## Reference Documents

- [ROS Manifest 2.0](references/ros-manifest-2.0.md) — ROS-only field contract, mixed actions, and validation rules
- [Bag to Manifest](references/bag2manifest.md) — Local ROS bag profiling, terminal conversation, and Web workbench
- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Task Config Reference](references/task-config-catalog.md) — Algorithm field mapping, required fields template, envs format, eval-tasks field differences
- [Interactive Workflow](references/interactive-workflow.md) — Detailed step-by-step interactive creation workflows for proc-tasks and eval-tasks
- [User-Facing Interaction Rules](../huawei-cloud-cloudrobo-data-pipeline/references/user-facing-interaction.md) — Shared rules for what the user sees: concise plans, one confirmation round, one-line progress, one-page results
- [Edge Cases](references/edge-cases.md) — full edge-case matrix (task logs, resources, operator rules)
- [Custom Operator Workflow](references/custom-operator/custom-operator-workflow.md) — index; five-phase onboarding split into `onboarding-phase-0-1.md` / `onboarding-phase-2-3.md` / `onboarding-phase-4.md` / `onboarding-post.md`, plus `phase-boundaries.md`, `failure-analysis-guide.md` (incl. 5d HTTP 500), `obs-upload-guide.md`, `garbage-cleanup-report.md`, `progress-feedback.md`
- [Custom Operator Reference](references/custom-operator/custom-operator-reference.md) — index: operator_config catalog + 两条部署路线对比 + dialogue control layer + verification report

## Edge Cases

Hard rules that apply to every operation (full edge-case matrix incl. custom-operator items:
[references/edge-cases.md](references/edge-cases.md)):

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Run `cloudrobo workspace use` or use `--workspace-id` |
| Task in non-terminal state | `wait-task` (proc or eval) polls until SUCCEEDED/FAILED/DELETED or timeout |
| `wait-task` timeout | Task may still be running; re-run `wait-task` and report progress — do not create a duplicate task |
| Log file not found | Falls back to `system-std-output.log` / `job-std-output.log` |
| Large log file | Default 64KB tail; use `--all` or `download-log` |
| Task creation fails | Check algo_type, JSON validity, dataset_configs, resource quota |
| AK/SK not set | Set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| Algorithm not found | Use `--name` fuzzy search or `sub_type` filter |
| eval-task delete | Single delete only; no batch |
| proc-task delete | CLI: one task per call; batch via SDK `delete_tasks([...])` / API `?ids=` |
| Re-run a task | `copy-task` (neither proc nor eval supports restart) |
| Task events | `get-events --task-id <id> --job-name <name>` (proc/eval) |
| Pipeline input | For eval, use proc exact asset/version/path in both top-level fields and single-item `dataset_configs` |
| Evaluation report link | OBS temp URL; save/download promptly |
| `envs` format | JSON array string, not object; see task-config-catalog.md |
| `catalog_id` mismatch | Use workspace's, not algorithm's |
| `list-assets` params | Provide `--catalog-id` or `--repository-id`; get from `cloudrobo workspace current` |
| Algorithm source | Built-in: `list-publication-assets`; custom: `list-assets` |
| `dataset_configs` | Use asset's `url` field; don't manually concatenate |
| Log query | Get file list first for `file_path`, then fetch content |
| Task states | Terminal: SUCCEEDED, FAILED, DELETED; non-terminal: CREATING, RUNNING, PENDING, FROZEN |
| Task deletion | Irreversible |
| Algorithm fields | Extract from `ext_metadata`; don't fabricate |
| Object storage | Must use `obs://`; `s3://` prohibited; **user-provided OBS paths (input/output) must use the workspace-bound bucket — the bucket of `default_obs_path` from `cloudrobo workspace current`; other OBS buckets not supported; mismatch → reject & re-ask** |
| API paths | From SDK `_url()` calls, not inferred |
| Cross-skill | No training/inference; use cloudrobo-train/infer; standalone sim evaluation → `huawei-cloud-cloudrobo-eval` |
| Cross-skill (pipelines) | Multi-stage raw→conversion→cleaning→evaluation→TrainingReady pipelines (pipeline.yaml/templates) → `huawei-cloud-cloudrobo-data-pipeline`; this skill covers single proc/eval task operations (CRUD, logs, preview, diagnosis) and a simple proc→eval chain |
| Mutating ops | create/copy/update/delete require confirmation |
| Workflow triggers | No params → interactive; complete params → skip to confirm |
| Missing optional fields | Skip if no `environment_variables`; use defaults for `worker_spec`; never send the removed `robot_config`; omit `inputs` unless a required input has no built-in `url_path` or the user asks for a custom mount |
| Empty field validation | Except `description`, all params must be non-empty; SDK rejects empty strings/None/empty dicts before submission |
| `head_spec`/`worker_spec` | SDK validation requires `cpu` and `memory`; include `gpu`/`npu` (value `0` is valid) |
| `dataset_configs` empty | Must contain at least 1 dataset entry; empty array `"[]"` is invalid |
| eval task-config fields | Use matching top-level dataset fields and a single-item `dataset_configs` JSON string with exact asset `version_id` |
| Advanced resources | DEDICATED_POOL: query for IDs; Ray: pair cluster/framework types, non-zero head_spec |
| Custom operator choices | **Defaults, stated in one line — not questions**: deploy mode = 代码放 OBS、运行时挂载; 该方式下的引用形态 = 注册成空间里的算法资产后引用 (`WORKSPACE_ASSETS` + `algo_id` — Phase 3 asset link, `algo_path` = asset `code_dir`, `job_local_path`, absolute `algo_entrance`); dataset source = reuse a matching asset, else auto-create (`BUILD_IN_ASSET`). Switch to 把代码打进镜像 / 不注册资产、直接挂载 OBS 代码 (`OBS_ASSETS` + `algo_path` + `job_local_path`, no `algo_id`) / ③ OBS存储 (`UDF_OBS_ASSET`) only when the user asks or supplies an `obs://` path. Ask only when several datasets are plausible and a wrong pick is costly |
| Custom operator cancel / re-issue | After a Phase 4 task is created, cancelling or re-issuing with changed params: **you must first confirm deletion/stopping of the old task** — show `{task_id}` (running) → ask "① delete (irreversible) ② keep ③ show logs" → after confirming ①, run `delete-task` + `show-task` to verify `DELETED`; **creating a new task before deletion is confirmed is forbidden** (boundary 4.11 / S12) |

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh -s . -e cli
```

### Functional Testing

```bash
# CLI
bash scripts/test-cli-commands.sh -s . -e cli
# SDK
bash scripts/test-cli-commands.sh -s . -e sdk
```

API-level verification is manual — replay the API paths in
`references/task-config-catalog.md` in
[API Explorer](https://console.huaweicloud.com/apiexplorer/).

### Test Cases

See `templates/test-vars.json` for the full test case list covering proc-tasks, eval-tasks,
algorithm discovery, pipeline, and custom-operator onboarding scenarios.

### Verification Checklist

- After creating a task, **launch `wait-task` + post-completion verification (`get-preview`/`get-frames` + log retrieval) as a single background shell** (Bash `run_in_background: true`) per the [Background Polling Pattern](#background-polling-pattern-non-blocking); immediately tell the user the `task_id` + output path so they can keep working
- On SUCCEEDED: verify output via `get-preview`/`get-frames`, output system log (run inside the same background shell so results are reported when the shell completes)
- On FAILED: ask user whether to view logs, fetch system and job logs per the two-step flow
  (list files → get content)
- For pipeline: verify processing exact asset/version/path matches eval top-level fields and `dataset_configs[0]`, then eval
  SUCCEEDED → get-preview returns OBS link
- For eval tasks: verify report preview after SUCCEEDED
- For any task: query `get-events --job-name <name>` to surface warnings/errors
- For custom-operator onboarding: assets `status=available`, 把代码打进镜像用 `image_url` / 代码放 OBS 用 `code_dir`,
  `[DONE]` log + non-empty frames, user's original code unmodified (details in `references/verification-method.md`)

## Best Practices

- Always discover operators first via `cloudrobo asset list-publication-assets --type algorithm` before creating a task
- Use `--dry-run` with `create-task`/`copy-task` to validate task config before actual execution
- **Default to background polling** — after `create-task` returns, launch `wait-task` + post-completion verification as a single background shell (Bash `run_in_background: true`) per the [Background Polling Pattern](#background-polling-pattern-non-blocking) so the user is never blocked; only use foreground blocking `wait-task` when the user explicitly asks for synchronous execution or the task is expected to finish within ~2 minutes
- Use `wait-task` with `--timeout` to avoid indefinite polling; report each status transition
- On task failure, retrieve both system logs (`--is-system true`) and job logs (`--is-system false`),
  analyze error patterns (OOM / path not found / image pull failure / OBS access) and suggest fixes
  before re-running via `copy-task`
- For pipeline orchestration, wait for processing SUCCEEDED before creating evaluation task
- Before batch delete, confirm task IDs to avoid irreversible deletion
- Clean up completed/failed tasks with `delete-task` to free resources
- Set `CLOUDROBO_DEBUG=1` for verbose error output during troubleshooting
- Evaluation report links are OBS temporary URLs — save or download promptly
- **Custom-operator**: state deploy mode (代码放 OBS、运行时挂载), 代码放 OBS、运行时挂载 task-creation way (注册成空间里的算法资产后引用), and dataset source (复用匹配资产 / 自动新建) as one-line defaults; ask only when the user must choose or several datasets are plausibly correct; **multiple data sources (≤10) → ONE task** (`dataset_configs` N entries, single `create-task`; only an explicit batch request justifies per-dataset tasks after confirmation); **cancel/re-issue after a task is created ⇒ first confirm deletion of the old task (`delete-task` + verify `DELETED`), never silently create a new one**; always `--dry-run`; cleanup scope = only this run's artifacts (never customer images/containers/data). Full rules: `references/custom-operator/custom-operator-workflow.md` + `references/custom-operator/custom-operator-reference.md`
