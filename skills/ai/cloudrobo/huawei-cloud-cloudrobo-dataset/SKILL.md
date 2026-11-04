---
name: huawei-cloud-cloudrobo-dataset
description: >
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
  Triggers include: data processing task management, data evaluation task management, task copy,
  task status polling, task events, log retrieval for troubleshooting, output data preview,
  algorithm discovery, task pipeline orchestration, batch task management, failure diagnosis,
  custom operator onboarding, dataset, proc-tasks, eval-tasks.
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

## Workflow

### Interactive Task Creation

All interactive creation workflows follow the **Interaction Rules**: at most one tool call per turn, display query results before asking the next question.

**Proc-Task Creation** (10 steps): Task name → Description → Algorithm type (PRESET_ASSETS/WORKSPACE_ASSETS/OBS_ASSETS) → Algorithm configuration with field mapping → Environment variables (+ operator `inputs` when declared) → Job type and resources (CCE/K8S or CCE_RAY/RAY, resource pool, instance spec) → Dynamic storage (public pool only) → Input datasets (multi-dataset loop) → Output configuration → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

**Eval-Task Creation** (7 steps): Task name → Description → Resource pool and instance spec → Evaluation algorithm (+ operator `inputs` when declared) → Dataset (single) → Robot config → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

### Task Polling and Result Handling

1. **Poll status** — `dataset proc wait-task` / `dataset eval wait-task` (recommended 15s interval),
   report each state change to user, until terminal state (SUCCEEDED/FAILED/DELETED). If
   `wait-task` times out while the task is still non-terminal, re-run `wait-task` — do not
   create a new task
2. **On completion:**
   - SUCCEEDED: view processing result via `get-preview`, output system log
   - FAILED: ask user whether to view logs, output system and job logs

**Eval tasks:** After SUCCEEDED, extract report path from `target_report_path` in task detail, use `dataset eval get-preview --task-id <task-id> --file-name <obs-path-without-bucket>` to get OBS temporary link.

### Pipeline Workflow (Task Orchestration)

Scenario: data conversion → data evaluation → download artifact

1. Run processing task, wait for SUCCEEDED
2. Extract `target_path` and `target_asset_id` from task detail
3. For the eval task, set top-level `dataset_type`/`dataset_id`(=target_asset_id)/`dataset_name`/`dataset_path`(=target_path) on the task-config
4. Create evaluation task, wait for SUCCEEDED (`dataset eval wait-task --task-id <eval-task-id>`)
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

**Custom operator failures** → fetch `job-std-output.log` and apply the P0-P3 patterns in `references/custom-operator/custom-operator-workflow.md` §Failure Analysis Guide.

### Analytics Workflow (Data Analysis)

Aggregate task stats by status, algorithm ranking, time trend, failure rate. Output analysis report with root-cause suggestions.

### Long-Running Task Workflow

Start `wait-task` with timeout. On timeout, report status and elapsed time; user decides: continue / view logs / terminate.

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
>   runtime failure. Applies to Mode A (`image_source=custom`) **and** Mode B 空间资产-算法
>   (`image_source=custom`, algorithm asset links the image asset) — NOT Mode-A-only.
> - `PRESET_ASSETS` — references a platform preset algorithm via `algo_id` (required).
> - `OBS_ASSETS` — mounts the customer OBS code directly (`algo_path` + `job_local_path`
>   required; `algo_id` optional). This is Mode B OBS算法.
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

Input datasets do not universally require YAML files. Use the selected operator's built-in
`robot` environment/default configuration, existing dataset config, or optional external
config mount as appropriate. Only when a YAML config file is actually needed, apply the
[manifest candidate rules](references/task-config-catalog.md#manifest-config-names);
manifest mode alone does not require an external file or an evaluation config mount.

#### Custom operator onboarding

For **custom data processing operators** (user code that needs containerizing, SWR push,
or OBS delivery + asset registration), follow the five-phase pipeline in
[Custom Operator Onboarding](#custom-operator-onboarding-自定义算子入驻) below.

## Custom Operator Onboarding 自定义算子入驻

Onboard user-developed data-processing operators to CloudRobo in an orchestrated
five-phase pipeline. **Core design principle: never modify the user's original code** —
the skill copies the user's code read-only into a temporary work copy
(`/tmp/custom-operator-work-{timestamp}/`) and generates all adaptation artifacts
(`entrypoint.py`, `Dockerfile`, `operator_config.json`) there only.

```
Phase 0  Deploy Mode + Assets    Phase 1  Code Adaptation    Phase 2  Build & Push       Phase 3  Asset Registration   Phase 4  Runtime Verification   Phase 5  Cleanup & Report
  ├─▶ A = image-inbuilt(custom)    work copy + entrypoint.py  docker build + push (new   image + algorithm assets   WORKSPACE_ASSETS + algo_id     Part 1A server junk (always)
  └─▶ B = OBS-mounted(preset)      code → OBS (deliver)       SKIP (no build)            空间资产-算法: preset image + algo  /log/frames verify          Part 1B platform junk (ask) + report
                                                                                        OBS算法: SKIP (no assets)      空间资产-算法: WORKSPACE_ASSETS+algo_id
                                                                                                                   OBS算法: OBS_ASSETS (no algo_id)
                                                    failure → Failure Analysis Engine (job-std-output.log → pattern → fix)  → after final result, cleanup is MANDATORY
```

**Three mandatory customer choices (never inferred; re-ask until unambiguous — a wrong guess
mis-routes Phase 3 asset registration and the task's `algo_type`, so each choice must be asked):**

- **Deploy mode (asked FIRST)** — Mode A image-inbuilt (`custom`): every submission rebuilds
  + pushes a **new image** (timestamp tag; SWR login auto-generated from AK/SK — on
  auto-credential generation/login failure, classify the cause (AK/SK invalid/expired, SWR
  not enabled / IAM permission missing, region mismatch, network) and ask the user to fix /
  provide a full `docker login` command, see `references/custom-operator/custom-operator-workflow.md`
  §Step 2.0); Mode B
  OBS-mounted (`preset`): code delivered to OBS, **no build/push**, preset image registered
  as an asset (空间资产-算法 only; the algorithm asset links it via `engine.asset_id` +
  `engine.asset_version_id`).
- **Mode B task-creation way (asked when Mode B is chosen)** — **空间资产-算法**:
  `WORKSPACE_ASSETS` + `algo_id` (Phase 3 asset) + `algo_path` (= asset `code_dir`) +
  `job_local_path` + absolute `algo_entrance` (asset linkage, registration runs);
  **Phase 3 算法资产 engine 必须通过 `asset_id` + `asset_version_id` 关联创建的镜像资产
  (空间资产-镜像)，`image_source=custom`（仅 image_url + preset 不会关联镜像资产）**;
  **OBS算法**: `OBS_ASSETS` + `algo_path` + `job_local_path`, no `algo_id`,
  **Phase 3 skipped**. Mandatory; use business names in dialogue.
- **Input-dataset source (Phase 4)** — 按平台数据来源两分（与普通 proc-task 交互
  `references/interactive-workflow.md` §8b/8c 一致）：**空间资产-数据**（`BUILD_IN_ASSET`，
  引用工作空间数据资产 — ① 自动新建数据集资产（`create-asset type=dataset` +
  `create-version` + `update-version RELEASE`）或 ② 复用已有数据资产，one → default /
  multiple → multi-select ≤10）与 **OBS存储**（`UDF_OBS_ASSET`，③ 直接输入 `obs://` 路径，
  `dataset_configs` entry 仅 `obs_path`+`dataset_type` — **不创建、不引用数据资产**）。
  All ever-asked, never inferred（③ = 平台"OBS存储"选项，与普通 proc-task §8c 行为一致）。
  **⚠️ ③ 的自定义 `obs://` 路径必须与当前工作空间绑定的 OBS 路径一致**：bucket 必须等于
  `cloudrobo workspace current` 返回的 `default_obs_path` 的 bucket（仅支持工作空间绑定的
  该 OBS bucket，**不支持其它 OBS bucket**）；交互时先展示 `default_obs_path` 作为参考，
  校验 bucket 不一致则拒绝并再次确认/重问。
  **多数据源（多路径/多选数据集，≤10）必须合并为 `dataset_configs` 多 entry，只创建 1 条任务，
  绝不按数据源拆分任务** —— 仅当用户显式要求批量（每条数据一条任务）且先确认 N 条拆分后才允许
  多任务（Mode A/B 一致）。

> **⚠️ Orchestration flow:** the `cloudrobo` CLI has **no `operator` command group** — the
> pipeline composes real commands (`cloudrobo asset`, `cloudrobo dataset proc`, Docker);
> CLI/SDK/API equivalence & API paths (audit only) in `references/dataflow-diagram.md` §API Path Summary.

**Executable steps live in the operator references** (SKILL.md keeps only this summary):
- [Custom Operator Workflow](references/custom-operator/custom-operator-workflow.md) — Phase 0-5 steps, phase boundaries, failure-pattern matrix (P0-P3), failure analysis engine, OBS sharded upload, cleanup & report, progress heartbeat
- [Custom Operator Reference](references/custom-operator/custom-operator-reference.md) — operator_config catalog, Mode A/B, dialogue control layer, report template

**Key constraints (authoritative detail: workflow §Phase 3/4 + §Failure Analysis Guide):**

1. **Asset names = the dialogue-confirmed operator name** (no silent rename / auto suffix; verify via `show-asset`).
2. **Image asset FIRST, algorithm asset SECOND**; the algorithm MUST link the image asset via `engine.asset_id` + `engine.asset_version_id` + `engine.image_source=custom` (`image_url` alone is NOT linked); never pass `--sub-type` with `--tags`; asset `url` is an OBS path.
3. `envs` MUST exclude platform-injected `SOURCE_DATASET_PATH`; Mode B `algo_entrance` is **absolute** `python3 {job_local_path}/entrypoint.py`.
4. New dataset version MUST be `RELEASE`; every name / `output_name` unique per run (timestamp suffix; duplicates → `400 The asset name is existed`).
5. Mode A registers a **new image every submission**; re-submission = `create-version` + `update-asset` (**never re-`create-asset`**); create tasks **without `--wait`**, poll.
6. **Mode A re-run after a FAILED verification** ⇒ re-submission branch; before `create-task` `show-asset` the algorithm points at the **new** image version + re-validate dataset sources. `create-task` **HTTP 500** after a rebuild ⇒ stale linkage or stuck `DRAFT` output asset — re-point, fresh `output_name`, wait ~30 s, retry once; still 500 → `trace_id` + support (details: workflow §Failure Analysis Guide pattern 5d).
7. **Output layout:** single-dataset conversion writes **flat** into the output root (no nested `{output_name}` subfolder; multi-dataset `{dataset_index}_` prefix only); no `.cloudrobo-tmp` folder left in the output.

### Interaction Guidelines 交互规范

对话逻辑唯一权威定义在 `references/custom-operator/custom-operator-reference.md`（System
Prompt 交互控制层、S1–S16 应答库、测试用例集），话术冲突以该文件为准。核心规则：一次只问
一个；先展示后询问；模糊即确认（Mode A/B、空间资产-算法/OBS算法、数据集来源①②③、上传方式、镜像 URL 必须
重问——替用户臆断会错配资产注册与任务类型，返工代价高）；高危操作二次确认（docker push、OBS 上传、create-asset/version/update、create-task、
删除类）；越域拒绝 + 免责；"继续"从上次成功阶段恢复（`--reuse-workdir`）。

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
- [Edge Cases](references/edge-cases.md) — full edge-case matrix (task logs, resources, operator rules)
- [Custom Operator Workflow](references/custom-operator/custom-operator-workflow.md) — five-phase onboarding + phase boundaries + failure patterns (incl. 5d HTTP 500) + OBS sharded upload + cleanup + progress heartbeat
- [Custom Operator Reference](references/custom-operator/custom-operator-reference.md) — operator_config catalog + Mode A/B + dialogue control layer

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
| Custom operator 必选点 | Deploy mode A/B, Mode B task-creation way (空间资产-算法 = `WORKSPACE_ASSETS` + `algo_id` — Phase 3 asset link, `algo_path` = asset `code_dir`, `job_local_path`, absolute `algo_entrance`; OBS算法 = `OBS_ASSETS` + `algo_path` + `job_local_path`, no `algo_id`), dataset source ①②③ — **always ask, never infer** (guessing mis-routes Phase 3 asset registration and the task's `algo_type`) |
| Custom operator 取消/重发 | Phase 4 任务已创建后取消或改参重发：**必须先确认删除/停止旧任务** — 展示 `{task_id}`（运行中）→ 问「①删除（不可恢复）②保留 ③查看日志」→ 确认①后 `delete-task` + `show-task` 验证 `DELETED`；**未确认删除前禁止创建新任务**（边界 4.11 / S12 / N13） |

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh -s . -e cli
```

### Functional Testing

```bash
# CLI / SDK
bash scripts/test-cli-commands.sh -s . -e {cli|sdk}
```

API-level verification is manual — replay the API paths in
`references/task-config-catalog.md` in
[API Explorer](https://console.huaweicloud.com/apiexplorer/).

### Test Cases

See `templates/test-vars.json` for the full test case list covering proc-tasks, eval-tasks,
algorithm discovery, pipeline, and custom-operator onboarding scenarios.

### Verification Checklist

- After creating a task, poll status (recommended 15s interval), report each state change to user
- On SUCCEEDED: verify output via `get-preview`, output system log
- On FAILED: ask user whether to view logs, fetch system and job logs per the two-step flow
  (list files → get content)
- For pipeline: verify processing exact asset/version/path matches eval top-level fields and `dataset_configs[0]`, then eval
  SUCCEEDED → get-preview returns OBS link
- For eval tasks: verify report preview after SUCCEEDED
- For any task: query `get-events --job-name <name>` to surface warnings/errors
- For custom-operator onboarding: assets `status=available`, Mode A `image_url` / Mode B `code_dir`,
  `[DONE]` log + non-empty frames, user's original code unmodified (details in `references/verification-method.md`)

## Best Practices

- Always discover operators first via `cloudrobo asset list-publication-assets --type algorithm` before creating a task
- Use `--dry-run` with `create-task`/`copy-task` to validate task config before actual execution
- Use `wait-task` with `--timeout` to avoid indefinite polling; report each status transition
- On task failure, retrieve both system logs (`--is-system true`) and job logs (`--is-system false`),
  analyze error patterns (OOM / path not found / image pull failure / OBS access) and suggest fixes
  before re-running via `copy-task`
- For pipeline orchestration, wait for processing SUCCEEDED before creating evaluation task
- Before batch delete, confirm task IDs to avoid irreversible deletion
- Clean up completed/failed tasks with `delete-task` to free resources
- Set `CLOUDROBO_DEBUG=1` for verbose error output during troubleshooting
- Evaluation report links are OBS temporary URLs — save or download promptly
- **Custom-operator**: ask deploy mode A/B, Mode B task-creation way (空间资产-算法 / OBS算法), and dataset source ①②③ FIRST — never infer; **multiple data sources (≤10) → ONE task** (`dataset_configs` N entries, single `create-task`; only an explicit batch request justifies per-dataset tasks after confirmation); **cancel/re-issue after a task is created ⇒ first confirm deletion of the old task (`delete-task` + verify `DELETED`), never silently create a new one**; always `--dry-run`; cleanup scope = only this run's artifacts (never customer images/containers/data). Full rules: `references/custom-operator/custom-operator-workflow.md` + `references/custom-operator/custom-operator-reference.md`
