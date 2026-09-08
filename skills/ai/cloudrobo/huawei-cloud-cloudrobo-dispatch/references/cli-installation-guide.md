# cloudrobo-dispatch CLI Installation Guide

## Overview

The `dispatch` command group drives **agent task orchestration** on embodied robots
(`robo-dispatcher` backend). A task is created inside a **session** (identified by
`session_id`) and targets a specific robot via `robot_id` + `exec_model_id`.

> **IMPORTANT**: The previous `create-session` / `exec-task` / `create-session-task`
> interfaces are **DEPRECATED**. The current feature design (FE2026052100144) uses the
> six commands below, all scoped by `--session-id`.

## 1. Install the CLI

```bash
pip install hw-cloudrobo-dispatch
```

The `cloudrobo` entry point is registered. Verify:

```bash
cloudrobo --help
cloudrobo dispatch --help
```

## 2. Authentication (AK/SK)

Set your Huawei Cloud credentials:

```bash
export HUAWEI_CLOUD_AK="<your-access-key>"
export HUAWEI_CLOUD_SK="<your-secret-key>"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="<your-access-key>"
$env:HUAWEI_CLOUD_SK="<your-secret-key>"
```

The CLI signs each APIG request with HMAC-SHA256 and the AK/SK pair.

## 3. Workspace configuration

Dispatch tasks are created within a workspace context. Select a default workspace:

```bash
cloudrobo workspace list
cloudrobo workspace use --workspace-id <workspace-id>
```

Use `--workspace-id` explicitly in create-task when a specific workspace is required.

## 4. Task Command Reference

`cloudrobo dispatch` exposes 6 subcommands:

| Command | Scope | Description |
| ---------- | ------- | --------------- |
| `create-task` | session | Create a dispatcher task in a session |
| `list-tasks` | session | List tasks in a session (filterable/sortable) |
| `show-task` | session+task | Show task detail |
| `wait-task` | session+task | **Wait (block)** for a task to finish; polls every 5s until status leaves `RUNNING` |
| `cancel-task` | session+task | Cancel a task |
| `show-task-result` | session+task | Fetch task result + log items |

**Usage examples:**

```bash
# Create a task targeting robot R1 with exec model M1.
# `--constraints-json` is required and carries model / robot_id / exec_constraints (stop condition).
# Defaults if the user gives none: max_run_time=10 (min), max_iter_num=100 (steps).
cloudrobo dispatch create-task --session-id <sid> --name "pick-red-block" --task "Pick up the red block and place it in the tray" --constraints-json '{"model":{"exec_model_id":"<mid>"},"robot_id":"<rid>","exec_constraints":{"max_run_time":10,"max_iter_num":100}}'

# List RUNNING tasks in a session
cloudrobo dispatch list-tasks --session-id <sid> --status RUNNING

# Show task detail
cloudrobo dispatch show-task --session-id <sid> --task-id <tid>

# Wait for the task to finish (blocks, polls every 5s until status != RUNNING)
cloudrobo dispatch wait-task --session-id <sid> --task-id <tid> [--timeout 600]

# Fetch task result (with pagination)
cloudrobo dispatch show-task-result --session-id <sid> --task-id <tid> --limit 100

# Cancel a task
cloudrobo dispatch cancel-task --session-id <sid> --task-id <tid>
```

## 5. Session context

All dispatcher operations are **scoped by `session_id`**. In the current version,
**`session_id` is identical to the current workspace's `workspace_id`** — there is no
separate session-create API. Obtain it via `cloudrobo workspace current` (or the configured
`workspace_id`) and reuse it directly as `--session-id`. A session is the stable execution
context; use the same `session_id` for `create-task` / `list-tasks` / `show-task` /
`wait-task` / `cancel-task` / `show-task-result`.

When creating a task, **always provide a stop condition** via `constraints.exec_constraints`
(`max_run_time` / `max_iter_num`); if the user does not give values, default to `max_run_time=10`
minutes and `max_iter_num=100` steps so debug tasks do not run unboundedly.

To wait for a task to finish, **prefer `wait-task`** (blocks, polls every 5s, returns once the
status leaves `RUNNING`; `--timeout` default 600 s, max 3600 s). It does **not** create tasks —
call `create-task` first to obtain the `task_id`, then `wait-task` on it.

If the driving inference service was deployed with `skill_config.strict:true`, the `task` text
**must match** one of its predefined skill prompts; a mismatched prompt is rejected.

## 6. Troubleshooting

| Problem | Resolution |
| ---------- | ------------- |
| `curl: error` / HTTP 401 | AK/SK not set or wrong; re-export credentials |
| `session_id` invalid | In current version `session_id == workspace_id`; verify against `cloudrobo workspace current`; use `validate_safe_id`-safe value |
| `robot_id` not found | Verify the target robot; see `cloudrobo robot show` |
| Task stays `PENDING` | Check robot online and exec model registered |
| Empty result / task still running | Wait with `wait-task` (polls every 5s) until status leaves `RUNNING`, then fetch `show-task-result` |
| `wait-task` timeout | Increase `--timeout` (max 3600s) or re-check state with `show-task`; a timeout raises `TimeoutError` and the CLI exits 1 |
| Path traversal error | `session_id` / `task_id` contains `../` — blocked by `validate_safe_id` |
| Deprecated interface used | Ensure you use `create-task`, not old `create-session` / `exec-task` |
