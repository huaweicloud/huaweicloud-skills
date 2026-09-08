---
name: huawei-cloud-cloudrobo-dataset
description: >
  Manage CloudRobo data processing (proc-tasks) and data evaluation (eval-tasks) — query
  algorithms, create/list/show/update/delete/restart tasks; poll task status until
  terminal; retrieve system and job logs; download logs; preview output data and frames;
  discover available algorithms from the asset marketplace; orchestrate processing→evaluation
  pipelines; batch-manage tasks across workspaces; diagnose failures via log analysis.
  Triggers include: data processing task management, data evaluation task management, task
  status polling, log retrieval for troubleshooting, output data preview, algorithm discovery,
  task pipeline orchestration, batch task management, failure diagnosis, dataset, proc-tasks,
  eval-tasks.
tags:
  - huawei-cloud-cloudrobo
  - dataset
  - data-processing
  - data-evaluating
  - task-management
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
(proc-tasks) and data evaluation (eval-tasks). It covers algorithm query, task CRUD operations,
status polling, log retrieval (system + job) and download, output data preview, frame extraction,
algorithm discovery from the asset marketplace, processing→evaluation pipeline orchestration,
batch task management, and failure diagnosis.

**Applicable scenarios:** Task management (CRUD + restart), troubleshooting (log retrieval + error analysis), algorithm discovery, result verification (preview + frames), pipeline orchestration, batch management, analytics.

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

All operations target the `cloudrobo-service` backend and require a `workspace_id` (default
workspace is used unless `--workspace-id` overrides it). Algorithm and dataset discovery is a
cross-package operation that calls the `cloudrobo-asset-manager` service via `cloudrobo asset`.

## Prerequisites

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
workspace configuration. All dataset operations require a valid `workspace_id` (default or
explicit `--workspace-id`).

## Workflow

### Interactive Task Creation

All interactive creation workflows follow the **Interaction Rules**: at most one tool call per turn, display query results before asking the next question.

**Proc-Task Creation** (10 steps): Task name → Description → Algorithm type (PRESET_ASSETS/WORKSPACE_ASSETS/OBS_ASSETS) → Algorithm configuration with field mapping → Environment variables → Job type and resources (CCE/K8S or CCE_RAY/RAY, resource pool, instance spec) → Dynamic storage (public pool only) → Input datasets (multi-dataset loop) → Output configuration → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

**Eval-Task Creation** (7 steps): Task name → Description → Resource pool and instance spec → Evaluation algorithm → Dataset (single) → Robot config → Confirm and submit. See `references/interactive-workflow.md` for detailed steps.

### Task Polling and Result Handling

1. **Poll status** — `dataset proc wait-task` (recommended 15s interval), report each state change to
   user, until terminal state (SUCCEEDED/FAILED/DELETED)
2. **On completion:**
   - SUCCEEDED: view processing result via `get-preview`, output system log
   - FAILED: ask user whether to view logs, output system and job logs

**Eval tasks:** After SUCCEEDED, extract report path from `target_report_path` in task detail, use `dataset eval get-preview --task-id <task-id> --file-name <obs-path-without-bucket>` to get OBS temporary link.

### Pipeline Workflow (Task Orchestration)

Scenario: data conversion → data evaluation → download artifact

1. Run processing task, wait for SUCCEEDED
2. Extract `target_path` and `target_asset_id` from task detail
3. Construct `dataset_configs` entry with `obs_path` = `target_path`, `asset_id` = `target_asset_id`
4. Create evaluation task, wait for SUCCEEDED
5. Get report: `dataset eval get-preview --file-name <path-from-target_report_path>` (remove `obs://<bucket>/` prefix)
6. Download artifacts via `download-asset`

### Batch Workflow (Batch Tasks)

Scenario: run same algorithm across multiple datasets

1. Get dataset list (`asset list-assets --type dataset`)
2. Create processing task per dataset (reuse algorithm/resource config from first; only input dataset differs)
3. Collect task_ids, poll status
4. Summarize success/failure/in-progress counts
5. For failed tasks: view logs or restart
6. Batch delete: `proc delete-task --task-id id1,id2,id3`

### Diagnosis Workflow (Failure Diagnosis)

Scenario: task FAILED → analyze logs, suggest fixes

1. Get system and user logs
2. Analyze error patterns: OOM → increase `worker_spec.memory`; path not found → check `dataset_configs`; image pull failure → check `image`; parameter error → check `algo_entrance`/`envs`; access denied → check `catalog_id`/permissions
3. Output diagnosis and fix suggestions
4. After confirmation, modify via `update-task` or restart via `restart-task`

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
| Dry-run | `--dry-run` (where supported) | Preview without executing |
| Boolean flag | `--is-system true` | `--is-system true` |
| Comma list | `--task-ids id1,id2,id3` | `--task-ids aaa,bbb` |

## Core Commands

### Task Management (proc-tasks)

#### Create a data processing task

```bash
cloudrobo dataset proc create-task --name <task-name> --algo-type PRESET_ASSETS --task-config '<json-config>' [--workspace-id <id>] [--wait] [--timeout 1800] [--dry-run]
```

- **SDK:** `client.create_task(task_config: dict)`
- **API:** `POST /v1/data-eng/proc-tasks`

Required task_config fields: `name`, `algo_type` (PRESET_ASSETS / WORKSPACE_ASSETS / OBS_ASSETS, based on Step 3 selection), `algo_name`, `algo_entrance`,
`image`, `algo_id`, `catalog_id` (workspace's), `resource_pool_type`, `cluster_type`,
`task_framework_type`, `dataset_configs` (JSON string array, multi-dataset input),
`output_type`, `output_path`, `output_name`, `head_spec` (must include `cpu`/`memory`/`gpu`/`npu`), `worker_spec` (must include `cpu`/`memory`/`gpu`/`npu`), `worker_num`,
`evs_spec`. See `references/task-config-catalog.md` for full field mapping.

**⚠️ Non-Empty Validation:** Except `description`, all parameters cannot be empty values (empty string `""`, `None`, empty dict `{}`). The SDK validates this before API submission. `head_spec`/`worker_spec` must include all four keys: `cpu`, `memory`, `gpu`, `npu` (value `0` is valid). `dataset_configs` must contain at least 1 dataset entry; empty array `"[]"` is invalid.

#### List tasks

```bash
cloudrobo dataset proc list-tasks [--status RUNNING|SUCCEEDED|FAILED] [--algo-type <type>] [--name <name>] [--order-by start_at|update_at|finish_at] [--order DESC|ASC] [--offset <n>] [--limit <n>] [--user-id <id>] [--algo-name <name>] [--output-name <name>] [--workspace-id <id>]
```

- **SDK:** `client.list_tasks(workspace_id=None, statuses=..., algo_type=..., name=..., order_by=..., ...)`
- **API:** `GET /v1/data-eng/proc-tasks?workspace_id=<id>&statuses=<status>`

#### Show task detail

```bash
cloudrobo dataset proc show-task --task-id <task-id>
```

- **SDK:** `client.get_task_detail(task_id)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}`

#### Update a task (SDK only)

- **SDK:** `client.update_task(task_id, task_config: dict)`
- **API:** `PATCH /v1/data-eng/proc-tasks/{task_id}`

#### Delete tasks (SDK only)

- **SDK:** `client.delete_tasks([task_id_1, task_id_2])`
- **API:** `DELETE /v1/data-eng/proc-tasks?ids=id1,id2`

#### Restart a task

```bash
cloudrobo dataset proc restart-task --task-id <task-id>
```

- **SDK:** `client.restart_task(task_id)`
- **API:** `POST /v1/data-eng/proc-tasks/{task_id}/restart`

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

### Data Preview

#### Preview task output data

Get OBS temporary download link for a dataset file. `file_name` = OBS path excluding bucket name (e.g., `cloudrobo/f91cee72-.../1ddf1498-.../data/chunk-000/file-000.parquet`).

```bash
cloudrobo dataset proc get-preview --task-id <task-id> --file-name <obs-path-without-bucket>
```

- **SDK:** `client.get_task_preview(task_id, file_name)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/preview?file_name=<file_name>`

#### Get task frames

Query directory file list of task input/output datasets. `prefix` = dataset OBS path excluding bucket name (e.g., `cloudrobo/f91cee72-.../1ddf1498-.../`).

```bash
cloudrobo dataset proc get-frames --task-id <task-id> --prefix <obs-path-without-bucket>
```

- **SDK:** `client.get_task_frames(task_id, prefix)`
- **API:** `GET /v1/data-eng/proc-tasks/{task_id}/frames?prefix=<prefix>`

### Evaluation Tasks (eval-tasks)

Evaluation tasks differ from processing tasks in field names, deletion granularity, and supported
operations. See the full comparison table in `references/task-config-catalog.md`.

#### Create an evaluation task

```bash
cloudrobo dataset eval create-task --name <task-name> --task-config '<json-config>' [--workspace-id <id>] [--wait] [--timeout 1800]
```

- **SDK:** `client.create_eval_task(task_config: dict)`
- **API:** `POST /v1/data-eng/eval-tasks`

**task-config field description**:

The eval-task task-config requires **two sets of dataset fields**: top-level single-value fields (`dataset_type`, `dataset_id`, `dataset_name`, `dataset_path`) + `dataset_configs` array (single dataset, format same as proc-task).

Required fields: `name`, `algo_type`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `catalog_id` (workspace's), `cluster_type`, `task_framework_type`, `dataset_type`/`dataset_id`/`dataset_name`/`dataset_path` (top-level), `dataset_configs`, `robot_config`, `resource_pool_type`, `head_spec`, `worker_spec`, `worker_num`, `evs_spec`, `output_type`, `output_path`, `output_name`.

Optional: `description`, `resource_id`, `dedicated_pool_name`.

**⚠️ Key reminders**:
- Both top-level dataset fields and `dataset_configs` array required
- `dataset_name` cannot be empty (extract from OBS path last directory for UDF_OBS_ASSET)
- `dataset_type` values: `BUILD_IN_ASSET` / `UDF_OBS_ASSET`

See `references/task-config-catalog.md` for full field mapping and eval-task field differences.

#### List evaluation tasks

```bash
cloudrobo dataset eval list-tasks [--status <status>] [--name <name>] [--workspace-id <id>]
```

- **SDK:** `client.list_eval_tasks(workspace_id=None, **params)`
- **API:** `GET /v1/data-eng/eval-tasks?workspace_id=<id>`

#### Show evaluation task detail

```bash
cloudrobo dataset eval show-task --task-id <task-id>
```

- **SDK:** `client.get_eval_task_detail(task_id)`
- **API:** `GET /v1/data-eng/eval-tasks/{task_id}`

#### Update an evaluation task (SDK only)

- **SDK:** `client.update_eval_task(task_id, task_config: dict)`
- **API:** `PATCH /v1/data-eng/eval-tasks/{task_id}`

#### Delete an evaluation task (single granularity, SDK only)

- **SDK:** `client.delete_eval_task(task_id)`
- **API:** `DELETE /v1/data-eng/eval-tasks/{task_id}`

**Note:** eval-tasks deletion is single-task granularity (`delete-task`), same as proc-tasks
(`delete-task`). eval-tasks do not support restart.

#### Retrieve evaluation task logs

```bash
# Step 1: List log files
cloudrobo dataset eval get-log --task-id <id> --is-system true
cloudrobo dataset eval get-log --task-id <id> --is-system false

# Step 2: Get log content
cloudrobo dataset eval get-log --task-id <id> --file-name <name> --file-path <path>
```

- **SDK:** `client.list_eval_log_files(task_id, is_system=True)` + `client.get_eval_task_log(task_id, file_name, ...)`
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

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Task Config Reference](references/task-config-catalog.md) — Algorithm field mapping, required fields template, envs format, eval-tasks field differences
- [Interactive Workflow](references/interactive-workflow.md) — Detailed step-by-step interactive creation workflows for proc-tasks and eval-tasks

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Run `cloudrobo workspace use` or use `--workspace-id` |
| Task in non-terminal state | `wait-task` polls until SUCCEEDED/FAILED/DELETED or timeout |
| Log file not found | Falls back to `system-std-output.log` / `job-std-output.log` |
| Large log file | Default 64KB tail; use `--all` or `download-log` |
| Task creation fails | Check algo_type, JSON validity, dataset_configs, resource quota |
| AK/SK not set | Set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| Algorithm not found | Use `--name` fuzzy search or `sub_type` filter |
| eval-task delete | Single delete only; no batch, no restart |
| Pipeline input | Wrap `target_path` into `dataset_configs` entry |
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
| Object storage | Must use `obs://`; `s3://` prohibited |
| API paths | From SDK `_url()` calls, not inferred |
| Cross-skill | No training/inference; use cloudrobo-train/infer |
| Mutating ops | create/update/delete/restart require confirmation |
| Workflow triggers | No params → interactive; complete params → skip to confirm |
| Missing optional fields | Skip if no `environment_variables`; use defaults for `worker_spec`; prompt for `robot_config` in eval |
| Empty field validation | Except `description`, all params must be non-empty; SDK rejects empty strings/None/empty dicts before submission |
| `head_spec`/`worker_spec` | Must include `cpu`, `memory`, `gpu`, `npu` keys (value `0` is valid) |
| `dataset_configs` empty | Must contain at least 1 dataset entry; empty array `"[]"` is invalid |
| Advanced resources | DEDICATED_POOL: query for IDs; Ray: pair cluster/framework types, non-zero head_spec |

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
algorithm discovery, and pipeline scenarios.

### Verification Checklist

- After creating a task, poll status (recommended 15s interval), report each state change to user
- On SUCCEEDED: verify output via `get-preview`, output system log
- On FAILED: ask user whether to view logs, fetch system and job logs per the two-step flow
  (list files → get content)
- For pipeline: verify processing `target_path` is wrapped into `dataset_configs` for the eval task, then eval
  SUCCEEDED → get-preview returns OBS link
- For eval tasks: verify report preview after SUCCEEDED

## Best Practices

- Always run `list-algorithms` first to discover available operators before creating a task
- Use `--dry-run` with `create-task` to validate task config before actual execution
- Use `wait-task` with `--timeout` to avoid indefinite polling; report each status transition
- On task failure, retrieve both system logs (`--is-system true`) and job logs (`--is-system false`),
  analyze error patterns (OOM / path not found / image pull failure / OBS access) and suggest fixes
  before restarting
- For pipeline orchestration, wait for processing SUCCEEDED before creating evaluation task
- Before batch delete, confirm task IDs to avoid irreversible deletion
- Clean up completed/failed tasks with `delete-task` to free resources
- Set `CLOUDROBO_DEBUG=1` for verbose error output during troubleshooting
- Evaluation report links are OBS temporary URLs — save or download promptly
