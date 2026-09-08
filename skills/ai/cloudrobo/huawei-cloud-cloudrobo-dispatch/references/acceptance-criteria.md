# Acceptance Criteria

## Functional Criteria

### Task Creation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-01 | Can create a dispatch task with valid params | task_id returned, status non-terminal |
| AC-02 | Can dry-run validate create params | `[DRY-RUN]` message, no task created |
| AC-03 | Requires robot_id in constraints | 400 error when robot_id missing |
| AC-04 | Requires exec_model_id | 400 error when exec_model_id missing |
| AC-04a | `exec_model_id` is the execution-model handle (for a user-deployed infer service it **equals the service's `service_id`**; platform prebuilt/external ones use `ext_`-prefixed handles) — not the asset id | Doc explains it is NOT the asset id; for user-deployed services `exec_model_id == service_id` from `cloudrobo infer list`. A known-good value is verifiable via `list-tasks --content-match "<prompt>"` → `constraints.model.exec_model_id` |
| AC-04c | Create request must NOT include `exec_model_name` | Passing `exec_model_name` in `constraints.model` yields HTTP 400 `Invalid parameter: exec_model_name`; doc warns it is response-only |
| AC-04b | Robot must be ONLINE to run a task | Doc/agent notes an offline robot yields `failure_reason: "Robot offline"` and guides bringing the robot online via `cloudrobo-r2c` first |
| AC-05 | Accepts exec_constraints JSON | task_id returned with constraints applied |

### Task Query

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-06 | Can list tasks in a session | JSON array returned |
| AC-07 | Can filter tasks by status | Filtered results match status |
| AC-08 | Can filter tasks by robot_id | Filtered results match robot |
| AC-09 | Can filter tasks by infer_service_id | Filtered results match infer service |
| AC-10 | Can filter by content-match | Filtered results match task text |
| AC-11 | Can paginate with --limit/--offset | Pagination respected |

### Task Detail

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-12 | Can show task detail | Task object with full fields |
| AC-13 | Detail includes robot/model/status | Fields present in show |

### Task Cancellation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-14 | Can cancel a running task | Task moves to cancelled state |
| AC-15 | Can dry-run validate cancel | `[DRY-RUN]` message, no cancellation |

### Task Result

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-16 | Can retrieve task result | Returns task + log_items |
| AC-17 | Result supports inverse/limit/offset | Pagination respected |
| AC-18 | Natural-language task result returned | task.result present |

### Wait for Completion

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-18a | Can wait for a task to finish | `wait-task` blocks and returns once status leaves `RUNNING` (COMPLETED/FAILED/CANCELLED) |
| AC-18b | `wait-task` needs an existing task | `create-task` first; wait-task on an unknown task errors |
| AC-18c | `--timeout` respected (default 600s, max 3600s) | Long `--timeout` or explicit value does not return early; timeout raises `TimeoutError`/CLI exits 1 |

### Safety / Validation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-19 | Path traversal rejected via validate_safe_id | Error on `../` session_id/task_id |
| AC-20 | Deprecated interfaces not exposed | No create-session/exec_task in skill |
| AC-21 | Missing session_id rejected | 400 error |

## Non-Functional Criteria

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| NFR-01 | No hardcoded credentials | grep SKILL.md and references for AK/SK patterns |
| NFR-02 | All mutating operations prompt user confirmation | SKILL.md documents confirmation requirement |
| NFR-03 | No cross-skill invocation | grep for other skill names |
| NFR-04 | All object storage paths use `obs://` | grep for `s3://` (should be none) |
| NFR-05 | SKILL.md frontmatter has name + description + tags | YAML frontmatter check |
| NFR-06 | description includes `Triggers include:` | grep 'Triggers include:' |
| NFR-07 | references/ files use kebab-case | filename regex `^[a-z0-9-]+\.md$` |
| NFR-08 | Total files <= 30 | find -type f \| wc -l |
| NFR-09 | Total size <= 40MB | du -sh |
| NFR-10 | Deprecated session interfaces documented as removed | grep for deprecated note in SKILL.md |
| NFR-11 | Wait-for-completion documented via `wait-task` (5s polling, no manual 20-30s loop) | grep for wait-task in SKILL.md & verification-method.md |
| NFR-12 | Resource IDs documented as dynamic | grep for no hardcoded robot_id/session_id |

## Test Cases Summary

| Case Type | Count | Coverage |
| ----------- | ------- | ---------- |
| Task creation | 7 | AC-01 ~ AC-05 (incl. AC-04a, AC-04b) |
| Task query | 6 | AC-06 ~ AC-11 |
| Task detail | 2 | AC-12 ~ AC-13 |
| Task cancellation | 2 | AC-14 ~ AC-15 |
| Task result | 3 | AC-16 ~ AC-18 |
| Wait for completion | 3 | AC-18a ~ AC-18c |
| Safety / validation | 3 | AC-19 ~ AC-21 |
| **Total** | **26** | Full coverage |
