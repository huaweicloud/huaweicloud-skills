---
name: huawei-cloud-cloudrobo-dispatch
description: >
  Manage CloudRobo embodied-agent task dispatch (robo-dispatcher) — create embodied tasks
  that drive a robot via an exec/model and constraints, list/show tasks in a session, cancel
  tasks, and retrieve task results. Dispatch orchestrates robots (robot_id from cloudrobo-robot)
  with inference models (exec_model_id from cloudrobo-infer / cloudrobo-asset) inside a session.
  Triggers include: dispatch, dispatcher, task dispatch, embodied task, agent task, run task on
  robot, task scheduling, cancel task, task result, robo-dispatcher, 调度, 智能体调度, 任务下发,
  机器人任务, 取消任务, 任务结果, 会话任务.
tags:
  - huawei-cloud-cloudrobo
  - dispatch
  - agent
  - task-orchestration
  - robo-dispatcher
  - embodied-task
  - task-dispatch
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview

The `cloudrobo-dispatch` skill manages **embodied task dispatch** via the `robo-dispatcher`
service. It lets the agent create a task that runs on a robot (identified by `robot_id`) under
an execution model (`exec_model_id`) inside a session (`session_id`), monitor it, cancel it, and
retrieve the natural-language task result plus log items.

**Applicable scenarios:**

- **Task dispatch** — Create a task on a robot given a natural-language task description; always
  provide a **stop condition** (`exec_constraints`: default `max_run_time=10` min, `max_iter_num=100` steps)
- **Task monitoring** — List/show tasks in a session, filter by status/robot/infer-service
- **Wait for task completion** — **Block** until a dispatched task leaves `RUNNING` without manual
  polling (`wait-task`, the preferred way to wait for a task to finish)
- **Task cancellation** — Cancel a running/pending task
- **Result retrieval** — Get the task result (task + log_items) of a finished task
- **Cross-skill orchestration** — Combine robots (`cloudrobo-robot`) and inference models
  (`cloudrobo-infer` / `cloudrobo-asset`) into concrete robot-executable tasks.

**Architecture:**

```text
Agent / LLM
    │
    ├── CLI  →  cloudrobo dispatch <command>
    └── SDK  →  DispatchClient (Python) — domain RoboDispatcherTaskManagement
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/robo-dispatcher/sessions/{session_id}/tasks*
```

All operations target the `cloudrobo-service` backend, are scoped to a `session_id`, and require
a valid `workspace_id`. A session is a stable execution context; multiple tasks can be created
within one session across time.

> **session_id**: In the current version, `session_id` is **identical to the current workspace's
> `workspace_id`**. You can obtain it by reading the active workspace (`cloudrobo workspace current`)
> or the configured `workspace_id`, and reuse it directly as the `--session-id`. If a caller explicitly
> provides a different `session_id`, prefer confirming it against the current workspace.

## Prerequisites

- See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
  workspace configuration.
- A valid `session_id` for all task operations. **In the current version `session_id` equals the**
  **current workspace's `workspace_id`** — read it via `cloudrobo workspace current` or the configured
  `workspace_id` (there is no separate session-create API).
- A valid `robot_id` (from `cloudrobo-robot`) and `exec_model_id` for the constrained **model service**
  that drives the task. The robot must be **ONLINE** (i.e. its R2C edge client is connected) for a task
  to run — otherwise the backend rejects it with `failure_reason: "Robot offline"`.

> **How to obtain `exec_model_id` (important)** — `exec_model_id` is the **execution-model handle**
> that drives the task. Do **not** put the raw model/asset id (e.g. `8b804b51-…`) into it; the backend
> cannot resolve the asset id and the task will fail.
>
> **Two kinds of `exec_model_id` (verified 2026-08 on this platform):**
> 1. **User-created inference services** (deployed via `cloudrobo infer create` in `cloudrobo-infer`):
>    `exec_model_id` **equals the inference service's `service_id`** — i.e. the `id` returned by
>    `cloudrobo infer create` and by `cloudrobo infer list`. Practical derivation: run `cloudrobo infer
>    list`, pick the service you deployed (e.g. `so101-real-demo-0828`), and use its `id`
>    (`<uuid>`) directly as `exec_model_id`. No separate "model-service
>    UUID" lookup is needed for user-deployed services.
> 2. **Platform prebuilt / external model-services** show an `ext_`-prefixed opaque handle, e.g.
>    `ext_2dcc1539e72040c78650c554102debaf` (name e.g. `Claude-3.5-Updated`) or
>    `ext_1ee0bcc7…` (name e.g. `cloudrobo-real-rl-model-…`). These are NOT infer-list services; obtain
>    them from an existing task's `constraints.model.exec_model_id`.
>
> At any time you can confirm the exact value against an **existing successful task** in the same
> session: `cloudrobo dispatch list-tasks --session-id <sid> --content-match "<skill prompt>"` and read
> its `constraints.model.exec_model_id` (the returned `exec_model_name` equals the source service name).

## Workflow

### Natural-Language-First Principle

Every workflow below starts from a user intent (1-2 sentences), not from manual CLI/SDK
orchestration. The skill then drives the matching command chain and reports state feedback.

### Task Dispatch Workflow (module + robot + model + workspace)

Scenario: "Tell robot A to go pick up the red cube and place it in the bin."

1. **Resolve session** — read `session_id` from the current workspace: in the current version
   `session_id == workspace_id` (obtain via `cloudrobo workspace current` / configured `workspace_id`).
2. **Resolve robot & model** — obtain `robot_id` (from robot registration) and `exec_model_id`.
   `exec_model_id` is the **execution-model handle** that drives the task — for a service you deployed,
   it is simply that service's `service_id` (see the "How to resolve `exec_model_id`" note below). Both
   are required in `constraints`.
3. **Verify robot reachable** — the target robot must be **ONLINE** (r2c edge client connected).
   A dispatch task on an offline/unconnected robot fails with a `Robot offline` failure reason.
   See `cloudrobo-r2c` to bring a (dummy/real) robot online before dispatching.
4. **Describe task** — collect the natural-language `task` text (e.g. "pick up the red cube and
   place it in the bin") and a `name`. **If the inference service was deployed with `strict:true`,
   the `task` text MUST match the predefined skill prompt; otherwise the service rejects it.** (See
   `cloudrobo-infer` for deploying a service with `skill_config.strict`.)
5. **Create task with stop condition** —
   `cloudrobo dispatch create-task --session-id <sid> --name <name> --task "<task>" --constraints-json '<json>'`. The `--constraints-json` is **required** and carries `model`,
   `robot_id`, and the **stop condition** `exec_constraints`. **Always set a stop condition**
   (`max_run_time` and `max_iter_num`) so the task cannot run unboundedly. Defaults if the user does
   not specify: `max_run_time=10` (minutes), `max_iter_num=100` (steps).
   Confirm before submitting (mutating).
6. **Wait for completion (preferred)** — block until the task finishes with
   `cloudrobo dispatch wait-task --session-id <sid> --task-id <task_id> [--timeout <secs>]`.
   This polls internally every **5s** and returns once the task status leaves `RUNNING`
   (i.e. reaches `COMPLETED`/`FAILED`/`CANCELLED` or any non-`RUNNING` state). Prefer `wait-task`
   over manual `show-task` polling — it replaces the old 20-30s manual polling loop.
7. **Get result** — on completion, `cloudrobo dispatch show-task-result --session-id <sid> --task-id <task_id>` to read the natural-language result and log items.

> **Note**: `robot_id` and `exec_model_id` are required inside `constraints`. Do not hardcode them;
> resolve from robot and infer/asset outputs.

> **How to resolve `exec_model_id`** — `exec_model_id` is **NOT the model asset ID** (the
> `8b804b51-...`-style asset UUID from `cloudrobo-asset`). It is the **execution-model handle** the task
> drives. For a service you deployed yourself via `cloudrobo infer create`, `exec_model_id` **equals
> that service's `service_id`** (read it from `cloudrobo infer list` / the `create` response). Platform
> prebuilt / external model-services use an `ext_`-prefixed opaque handle instead. Resolve it by:
> 1. If the target model is one of **your deployed inference services** → `cloudrobo infer list`, take the
>    service `id` as `exec_model_id` (verified equivalent on 2026-08).
> 2. Otherwise, confirm the exact value against an **existing successful task** in the same session:
>    `cloudrobo dispatch list-tasks --session-id <sid> --content-match "<deployed skill prompt>"` and read
>    its `constraints.model.exec_model_id` (`exec_model_name` is the source service name, informational).
> Using the raw asset UUID in `exec_model_id` is a common root cause of dispatch failures.

### Task Monitoring / Lookup Workflow (module + filters)

Scenario: "What tasks are running in my session?"

1. `cloudrobo dispatch list-tasks --session-id <sid> [--status <status>] [--robot-id <rid>] [--infer-service-id <iid>] [--start-time <ms>] [--end-time <ms>] [--content-match <text>]`
   with pagination (`--limit`/`--offset`) and sorting (`--sort-key`/`--sort-dir`).
2. `cloudrobo dispatch show-task --session-id <sid> --task-id <task_id>` for detail.
3. Report task status, robot, model, and content.

### Task Result Retrieval Workflow (module)

Scenario: "Show me the outcome of that pick-and-place task."

1. Wait for the task to finish via `wait-task` (or confirm it is terminal via `show-task`).
2. `cloudrobo dispatch show-task-result --session-id <sid> --task-id <task_id>` — returns the
   task object plus `log_items`. Supports `--inverse`, `--limit`, `--offset` for pagination.

### Task Cancellation Workflow (module)

Scenario: "Abort that task — the robot picked the wrong object."

1. Confirm the task via `show-task`.
2. `cloudrobo dispatch cancel-task --session-id <sid> --task-id <task_id>` (mutating; confirm).
3. Verify via `show-task` that the task moved to a cancelled state.

### Session Context Note

- Tasks are always created under a `session_id`. In the current version `session_id` is the same as
  the current workspace's `workspace_id`; obtain it from `cloudrobo workspace current`. You may
  create many tasks within one session over time.
- **Stop condition**: every task should be created with `constraints.exec_constraints` so it stops
  on time — see the Create a Task section for the required object shape and defaults.
- **strict services**: if the driving inference service was deployed with `skill_config.strict:true`,
  the `task` you pass MUST match one of its predefined skill prompts; a mismatched prompt is rejected.
- The old `create-session` / `exec_task` / `create-session-task` interfaces are **deprecated**
  and must not be used. All operations use `session_id` directly on the task endpoints.

## CLI Command Format Standard

```bash
cloudrobo dispatch <command> [OPTIONS]
```

| Feature | Description |
| --------- | ------------- |
| Command group | `dispatch` |
| Subcommand | kebab-case: `create-task`, `list-tasks`, `show-task`, `cancel-task`, `show-task-result`, `wait-task` |
| Session | `--session-id <id>` (all task operations; equals `workspace_id` in current version) |
| JSON params | `--constraints-json '<object>'` (create-task; required; holds model/robot_id/exec_constraints) |
| Dry-run | `--dry-run` (create-task/cancel-task) |
| Result pagination | `--inverse`, `--limit`, `--offset` (show-task-result) |
| Wait timeout | `--timeout <secs>` (wait-task; default 600, IntRange 1–3600) |

> **Full coverage**: SDK exposes 6 methods, CLI exposes 6 commands (0 gaps).
> See `references/cli-installation-guide.md` and the acceptance criteria for the
> coverage mapping.

## Core Commands

> **SDK Direct Calls**: When CLI is inconvenient (dynamic JSON, cross-package queries), use the
> Python SDK directly. `DispatchClient` (domain RoboDispatcherTaskManagement) exposes the 6
> methods below.

### Create a Task

```bash
cloudrobo dispatch create-task --session-id <session-id> --name <task-name> --task "<natural language task>" --constraints-json '{"model":{"exec_model_id":"<model-id>"},"robot_id":"<robot-id>","exec_constraints":{"max_run_time":10,"max_iter_num":100}}' [--dry-run]
```

> **Stop condition is required in practice** (`constraints.exec_constraints`). If the user does not
> specify values, **default to `max_run_time=10` (minutes) and `max_iter_num=100` (steps)** to avoid
> unbounded/long-running debug tasks. Valid ranges: `max_run_time` 1–300 minutes, `max_iter_num`
> 1–300000 steps.

> **`model` object shape (important)** — in `create-task`'s `constraints.model`, only include
> **`exec_model_id`**. Do **not** add `exec_model_name`: the create API rejects it with
> `400 Invalid parameter: exec_model_name`. `exec_model_name` is a **response-only** field (present in
> `show-task` / `list-tasks` / `show-task-result` output), never a request field. See the "How to
> resolve `exec_model_id`" note for what `exec_model_id` should be.

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_dispatch import DispatchClient

config = Config()
http_client = HttpClient(config)
client = DispatchClient(http_client)

# session_id equals the current workspace_id in the current version
req = {
    "name": "pick-red-cube",
    "task": "pick up the red cube and place it in the bin",
    "constraints": {
        "model": {"exec_model_id": "<mid>"},
        "robot_id": "<robot-id>",
        # stop condition: use the given values, else default max_run_time=10, max_iter_num=100
        "exec_constraints": {"max_run_time": 10, "max_iter_num": 100},
    },
}
task = client.create_dispatcher_task("<session-id>", req)
print(task)  # includes task_id
```

### List Tasks

```bash
cloudrobo dispatch list-tasks --session-id <sid> [--status <status>] [--limit 20] [--offset 0]
```

```python
tasks = client.list_dispatcher_tasks("<session-id>", status="RUNNING")
for t in tasks.get("items", []):
    print(t["id"], t["status"], t["name"])
```

### Show Task Detail

```bash
cloudrobo dispatch show-task --session-id <sid> --task-id <task-id>
```

```python
task = client.show_dispatcher_task("<session-id>", "<task-id>")
print(task["name"], task["status"], task["robot_id"])
```

### Cancel Task

```bash
cloudrobo dispatch cancel-task --session-id <sid> --task-id <task-id> [--dry-run]
```

```python
client.cancel_dispatcher_task("<session-id>", "<task-id>")
```

### Show Task Result

```bash
cloudrobo dispatch show-task-result --session-id <sid> --task-id <task-id> [--inverse] [--limit 100] [--offset 0]
```

```python
result = client.show_dispatcher_task_result("<session-id>", "<task-id>")
print(result["task"]["result"])
for item in result.get("log_items", []):
    print(item)
```

### Wait for Task Completion

**Purpose**: Block until a dispatched task finishes (its status leaves `RUNNING`), so you do not
have to manually poll `show-task` in a loop. This is the **preferred way to wait for a task** in
non-interactive / automation scenarios.

```bash
cloudrobo dispatch wait-task --session-id <sid> --task-id <task-id> [--timeout <seconds>]
```

```python
result = client.wait_dispatcher_task("<session-id>", "<task-id>", timeout=600)
# result is the full task dict once status != "RUNNING" (e.g. COMPLETED / FAILED / CANCELLED)
status = (result.get("task") or {}).get("status")
```

> **Behavior** (authoritative, from source):
> - **Method**: `wait_dispatcher_task(session_id, task_id, timeout=600)`.
> - **Polling**: every **5 seconds** (`POLL_INTERVAL = 5`); it calls `show_dispatcher_task`
>   internally (`GET /v1/robo-dispatcher/sessions/{session_id}/tasks/{task_id}`).
> - **Return condition**: returns the task dict as soon as `data["task"]["status"] != "RUNNING"`
>   — regardless of whether it reached `COMPLETED`, `FAILED`, `CANCELLED`, or another non-`RUNNING`
>   state. Terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.
> - **Default timeout**: **600 seconds**. `--timeout` is an `IntRange(1, 3600)` — **max 3600 s (1 hour)**.
> - **On timeout**: raises `TimeoutError` (client); the CLI prints `[ERROR] <msg>` to stderr and
>   exits with code 1. Always check the return status to distinguish success, failure, and timeout.
> - **No independent REST API**: `wait-task` is a client-side polling helper — it has **no** dedicated
>   backend endpoint and simply wraps `show-task`.
> - **Must create the task first**: `wait-task` does **not** create a task. Call `create-task` to get
>   the `task_id` first, then `wait-task` on it.

**Recommendation (when to use `wait-task`)**:
- Use `wait-task` right after `create-task`, then fetch the outcome with `show-task-result` — this
  replaces the old manual `show-task` polling every 20-30s.
- It is ideal for **non-interactive / automation** flows that should block until a terminal state.
- In **interactive** flows where you want to observe intermediate states, you may still use
  `show-task` to inspect progress — but use `wait-task` when you simply need to wait for the outcome.

## Parameter Confirmation

| Parameter | Source | Required | Confirmation Needed |
| ----------- | -------- | ---------- | --------------------- |
| `--session-id` | Current workspace (`workspace_id`) | Yes (all) | In current version `session_id == workspace_id`; verify against `cloudrobo workspace current` |
| `--task` | User | Yes (create) | Natural-language task description; if strict service, must match predefined skill prompt |
| `--name` | User | Yes (create) | Task name |
| `--constraints-json` | User/derived | Yes (create) | JSON object `{model, robot_id, exec_constraints}`; holds stop condition |
| `exec_constraints` (in `--constraints-json`) | User, else default | Yes in practice (create) | Default `max_run_time=10` (min), `max_iter_num=100` (steps); ranges 1–300 / 1–300000 |
| `--task-id` | User or prior output | Yes (show/cancel/result/wait) | Verify before cancel; must exist (from create-task) before wait-task |
| `--timeout` | Derivable | No (wait) | wait-task timeout in seconds; default 600, IntRange 1–3600 |
| `--dry-run` | — | No | Preview without executing |

**Mutating operations** (create-task / cancel-task) must prompt the user for confirmation before
execution.

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential & access model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria

## Edge Cases

| Scenario | Handling |
| ---------- | ---------- |
| Missing `session_id` | In current version `session_id == workspace_id`; obtain from `cloudrobo workspace current` |
| Missing `robot_id` / `exec_model_id` | create-task requires both inside `constraints`; resolve from robot and the deployed **model service** (not the asset id) |
| `exec_model_id` is wrong (asset id used) | For a service you deployed, `exec_model_id` **equals that service's `service_id`** (read from `cloudrobo infer list`); using the raw asset id (`8b804b51-...`) is a common failure. Prebuilt/external model-services use an `ext_`-prefixed handle. Verify against an existing successful task via `list-tasks --content-match "<prompt>"` |
| `exec_model_name` passed in create request | **Do not include `exec_model_name`** in `constraints.model` — the create API returns `400 Invalid parameter: exec_model_name`. `exec_model_name` is response-only; drop it and retry with only `exec_model_id` |
| Robot offline / not connected | A task on an offline robot fails with `failure_reason: "Robot offline"`. Bring the robot ONLINE first via `cloudrobo-r2c` (dummy/real edge client) before dispatching |
| Missing stop condition | create-task should set `constraints.exec_constraints`; default `max_run_time=10`, `max_iter_num=100` to avoid unbounded tasks |
| Over-long task | Respect ranges: `max_run_time` 1–300 min, `max_iter_num` 1–300000 steps; don't exceed to keep debug tasks bounded |
| strict:true service | If the inference service was deployed with `skill_config.strict:true`, the `task` MUST match a predefined skill prompt; otherwise rejected |
| Task not found | show/cancel/result return `ResourceNotFoundError`; verify `task_id`/`session_id` |
| Path traversal | `validate_safe_id(session_id)` / `validate_safe_id(task_id)` block `../` input |
| Cancelling a finished task | backend rejects; confirm status before cancel |
| Long-running task | Prefer `wait-task` (polls every 5s, returns once status leaves `RUNNING`); use `show-task` only to observe intermediate states, not in a tight manual loop |
| `wait-task` timeout | `--timeout` max is 3600s (1h); on timeout the CLI prints `[ERROR]` and exits 1 — raise/inform the user and re-check with `show-task` |
| `wait-task` on a terminal task | Returns immediately (status already non-`RUNNING`); safe to call after a task finished |
| `wait-task` needs an existing task | It does **not** create a task — call `create-task` first to obtain `task_id`, or it fails on an invalid/unknown task |
| Natural-language task content | Sanitize/inject-protect; do not echo raw content into logs unescaped |
| AK/SK not set | Operations fail at HTTP signing; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| Deprecated interfaces | Do not use old `create-session`/`exec_task`/`create-session-task`/`list-sessions` |
| session_id / task_id / robot_id / exec_model_id | Never hardcoded; resolved dynamically (session_id from current workspace) |
| Cross-skill invocation | This skill does not call other skills; it consumes robot_id (robot) and exec_model_id (infer/asset) and reports task results |
| Mutating operations | create-task / cancel-task should be confirmed by the user |

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh
```

### Functional Testing

```bash
bash scripts/test-cli-commands.sh
```

### Test Cases

See `templates/test-vars.json` for the full test case list covering dispatch, monitoring,
wait-for-completion, cancellation, result retrieval, and safety scenarios.

### Verification Checklist

- After `create-task`, task appears in `list-tasks` with correct status
- The created task carries a stop condition (`exec_constraints.max_run_time` / `max_iter_num`);
  when the user gave none, they default to 10 min / 100 steps
- `session_id` used equals the current workspace's `workspace_id`
- When the inference service is `strict:true`, the `task` matched the predefined skill prompt
- After `wait-task`, the command blocked (polling every 5s) and returned only once status was
  non-`RUNNING`; no manual 20-30s polling loop was used
- `wait-task` with an explicit `--timeout` respects the timeout and reports a clear error on expiry
- `wait-task` was called with a `task_id` already created by `create-task` (it does not create tasks)
- After `show-task`, detail returns the task with robot/model/status
- After `show-task-result`, natural-language result and log_items are returned
- After `cancel-task`, `show-task` reflects the cancelled state
- Path traversal (`../`) is blocked by `validate_safe_id`
- Deprecated interfaces (`create-session`/`exec_task`) are not used
- Mutating operations prompt user confirmation before executing

## Best Practices

- Always resolve `session_id` from the current workspace (`cloudrobo workspace current`; in the
  current version `session_id == workspace_id`), and resolve `robot_id` / `exec_model_id` dynamically;
  never hardcode
- **Always set a stop condition** (`constraints.exec_constraints`) when creating a task; if the user
  gives none, use the defaults `max_run_time=10` (minutes) and `max_iter_num=100` (steps) to keep
  debug tasks bounded (respect ranges 1–300 / 1–300000)
- If the driving inference service was deployed with `strict:true`, make the `task` match the
  predefined skill prompt
- Confirm before `create-task` (it triggers real robot action) and `cancel-task`
- **After `create-task`, wait with `wait-task` instead of manually polling `show-task`** — it blocks
  (polling every 5s) until the status leaves `RUNNING`, then fetch the outcome with `show-task-result`.
  Use `show-task` only to inspect intermediate states when needed. In an agent setting, run `wait-task`
  as a **background process and wait for it to return** (it exits on its own once the task is
  terminal), rather than sleeping + `show-task` in a manual loop.
- Set an explicit `--timeout` on `wait-task` when the task may run long; on timeout, re-check state
  with `show-task` and report the outcome rather than retrying blindly
- **`constraints.model` only takes `exec_model_id`** — never pass `exec_model_name` in the create
  request (400 error); it is a response-only field
- For a model service **you deployed** (`cloudrobo infer create`), `exec_model_id` = that service's
  `service_id` (see `cloudrobo infer list`); only platform prebuilt/external model-services use
  `ext_`-prefixed handles. Prefer `cloudrobo infer list` over guessing when resolving it
- Use `--dry-run` on `create-task`/`cancel-task` to validate params before acting
- Use `list-tasks` filters (`--status`, `--robot-id`, `--infer-service-id`, `--content-match`)
  to quickly locate tasks
- Sanitize natural-language `task` content; do not echo raw content into logs unescaped
- Combine with robot (`cloudrobo robot list/show`) and infer (`cloudrobo infer list`) skills to
  resolve robot/model IDs needed for task creation
