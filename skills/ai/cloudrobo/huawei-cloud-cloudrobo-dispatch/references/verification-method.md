# Verification Method — cloudrobo-dispatch

## Scope

This document defines the layered verification method for the `dispatch` skill
(`cloudrobo dispatch` commands). It validates the 6 dispatcher operations
(create-task / list-tasks / show-task / cancel-task / show-task-result / wait-task) plus
safety and error handling.

## Verification Principles

- Follow the order Level 1 → Level 5 and stop at first failure.
- Every **mutating** operation (create-task, cancel-task) **must be user-confirmed**
  before execution.
- Never hardcode `session_id` / `task_id` / `robot_id` / `exec_model_id` — obtain them
  dynamically from the user or prior command output. In the current version `session_id` equals
  the current workspace's `workspace_id` (`cloudrobo workspace current`).
- To wait for a task to finish, **prefer `wait-task`** (it polls internally every 5 seconds and
  returns once the status leaves `RUNNING`). Do not write manual `show-task` polling loops.

## Level 1 — CLI Smoke Test

Verify installation, auth, and command availability.

| Test | Command | Expected |
| ------ | ------- | ---------- |
| CLI installed | `cloudrobo --version` | Version printed |
| Auth configured | `cloudrobo dispatch list-tasks --session-id <sid> --limit 1` (or a read-only query) | Authenticated response (HTTP 200 or meaningful error, no 401) |
| Help available | `cloudrobo dispatch --help` | Lists 6 subcommands |

## Level 2 — Task Full Lifecycle

Uses an existing `session_id`. Best run against a real test robot + exec model.

| Test | Command | Expected |
| ------ | ------- | ---------- |
| Create task | `cloudrobo dispatch create-task --session-id <sid> --name "test-task" --task "<a simple task>" --constraints-json '{"model":{"exec_model_id":"<mid>"},"robot_id":"<rid>","exec_constraints":{"max_run_time":10,"max_iter_num":100}}'` | Returns `task_id` (with stop condition) |
| List tasks | `cloudrobo dispatch list-tasks --session-id <sid>` | `task_id` appears in list |
| List by status | `cloudrobo dispatch list-tasks --session-id <sid> --status RUNNING` | Filters to RUNNING only |
| Show task | `cloudrobo dispatch show-task --session-id <sid> --task-id <tid>` | Returns task detail with status |
| Wait for completion | `cloudrobo dispatch wait-task --session-id <sid> --task-id <tid> [--timeout 600]` | **Blocks** (polling every 5s), returns once status leaves `RUNNING` |
| Show result | `cloudrobo dispatch show-task-result --session-id <sid> --task-id <tid>` | Returns `task` + `log_items` |

## Level 3 — Task Cancellation

| Test | Command | Expected |
| ------ | ------- | ---------- |
| Cancel task | `cloudrobo dispatch cancel-task --session-id <sid> --task-id <tid>` | Task transitions to CANCELLED / terminal state |
| Verify cancellation | `cloudrobo dispatch show-task --session-id <sid> --task-id <tid>` | Status reflects cancelled state |

## Level 4 — Result Fetcing & Pagination

| Test | Command | Expected |
| ------ | ------- | ---------- |
| Paginated result | `cloudrobo dispatch show-task-result --session-id <sid> --task-id <tid> --limit 100 --offset 0` | Returns page of log items |
| Inverse order | `cloudrobo dispatch show-task-result --session-id <sid> --task-id <tid> --inverse` | Reverse ordering respected |

## Level 5 — Error Handling & Safety

| Test | Command | Expected |
| ------ | ------- | ---------- |
| Path traversal | `cloudrobo dispatch show-task --session-id <sid> --task-id '../etc/passwd'` | Blocked by `validate_safe_id` — error raised |
| Missing session_id | `cloudrobo dispatch create-task` without `--session-id` | CLI requires the parameter; clear usage error |
| Invalid session_id | `cloudrobo dispatch list-tasks --session-id 'nonexistent'` | Appropriate not-found / validation error |
| Dry-run create | `cloudrobo dispatch create-task --... --dry-run` | Shows what would be created; no task submitted |
| Dry-run cancel | `cloudrobo dispatch cancel-task --session-id <sid> --task-id <tid> --dry-run` | Shows what would be cancelled; no action taken |
| Confirm gate | create-task / cancel-task without confirmation | Agent prompts user before execution |

## Expected Results Matrix

| Command | Success Result | Typical Failure |
| --------- | ---------------- | ----------------- |
| `create-task` | JSON with `task_id`, status = `PENDING` | Invalid robot/exec model, invalid session, dry-run no-op |
| `list-tasks` | JSON array of tasks | Invalid session_id |
| `show-task` | JSON task detail + status | `task_id` not found / path traversal |
| `wait-task` | JSON task dict once status != `RUNNING` | Timeout (raises `TimeoutError`, CLI exits 1), unknown task |
| `cancel-task` | JSON reflecting terminal (cancelled) state | Already terminal, invalid id |
| `show-task-result` | JSON `{task, log_items}` | Task still running / no result yet |

## Common Verification Failures

- **Stale results**: The user warned that subagents can reuse old cache/IDs. If a task
  id or session id returns stale data, wait (up to 60+ minutes) and re-query.
- **`session_id` wrong**: All dispatcher ops are session-scoped; a wrong session yields
  empty/absent data — verify the session id.
- **Deprecated commands**: Do NOT use `create-session` / `exec-task` / `create_session_task` —
  use the 6 current commands.
- **Task not finished**: `show-task-result` may be empty while task is RUNNING; wait with
  `wait-task` (or `show-task`) until the status leaves `RUNNING` before fetching the result.
- **`wait-task` timeout**: On a long-running task, `wait-task` may hit its `--timeout` (default
  600s, max 3600s). Re-check state with `show-task` and report the outcome.
- **Robot offline**: A task may stay PENDING if the target robot is offline; verify robot
  status via `cloudrobo robot show`.

## Completing Verification

After all levels pass, report:

1. Command(s) run and output summary (mask sensitive ids)
2. Whether the task reached a terminal state and result was fetched
3. Any errors encountered and their resolution

For comprehensive end-to-end verification beyond these checks, run the commands from
SKILL.md manually against a live environment.
