# Acceptance Criteria

## Functional Criteria

### Asset Query (cross-package)

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-01 | Can query built-in algorithms via `list-publication-assets --type algorithm` | Returns non-empty JSON array |
| AC-02 | Can query custom algorithms via `list-assets --type algorithm` | Returns JSON array |
| AC-03 | Can query datasets via `list-assets --type dataset` | Returns JSON array with dataset_asset_id |
| AC-04 | Can query base models via `list-assets --type model` | Returns JSON array with model_asset_id |

### Task Creation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-05 | Can submit finetune task (MODEL_TUNING) via `create-task --config` | task_id returned, status non-terminal |
| AC-06 | Can submit pretrain task (TRAIN_FROM_SCRATCH) via `create-task --config` | task_id returned, status non-terminal |
| AC-07 | Can validate params before submission via `save-draft` + `show-task` | task_id with status DRAFT |
| AC-08 | Can create task from config file via `--config-file` | task_id returned, status non-terminal |
| AC-09 | Can save task config as draft | task_id returned, status DRAFT |
| AC-10 | Can create task from full JSON via `create-task` | task_id returned, status non-terminal |
| AC-11 | Rejects invalid spec format | 400 error on non-Ascend format |
| AC-12 | Rejects invalid train_method (lowercase) | 400 error on lowercase method |

### Task Management

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-13 | Can list training tasks | JSON array returned |
| AC-14 | Can filter tasks by train_mode | Filtered results match mode |
| AC-15 | Can filter tasks by status | Filtered results match status |
| AC-16 | Can show task detail via `show-task` | Task object with full fields |
| AC-17 | Can stop a running task | status → STOPPING → STOPPED |
| AC-18 | Can restart a task | Task resubmits, leaves non-terminal |
| AC-19 | Can resume a train task via `resume-task` | Task resumed (train-only) |
| AC-20 | Can delete tasks via `delete-tasks` (batch POST) | Tasks removed |
| AC-22 | Can update task via `update-task` | Field updated in subsequent show |
| AC-23 | Can count tasks by status via `stats` | Counts per status returned |

### Monitoring

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-24 | Can get execution stages | 4-stage flow (SCHEDULING/PREPARING/RUNNING/END) |
| AC-25 | Stages include sub_stages | Sub-stage details returned |
| AC-26 | Can get resource usage with --metric/--start/--end | CPU/GPU/NPU utilization returned |
| AC-27 | Can get events with --start-time/--end-time | Event list with level/time/message |
| AC-28 | Events include Info/Warning/Error levels | level enum correct |

### Log Management

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-29 | Can get log content via `get-logs --file-name` | Log text returned |
| AC-30 | Can get log content by `--log-name-pre` prefix | Log text returned |
| AC-31 | Can get log signed URL via `get-signed-url --file-source --file-name` | OBS temp URL returned |
| AC-32 | Can list observations (SDK only) | File list returned via SDK |

### Draft Workflow

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-33 | Can save draft with minimal config (name+workspace_id) | task_id returned, status DRAFT |
| AC-34 | Can resubmit draft via `restart-task` | Task leaves DRAFT, enters CREATING |
| AC-35 | Can resubmit draft with edited config (SDK) | Task uses edited config |

### SimRL (Simulation Reinforcement Learning)

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-36 | Can count SimRL tasks by status via `stats --sim-rl` | Counts per status returned |
| AC-37 | Can list SimRL tasks via `list-tasks --sim-rl` | JSON array of SimRL tasks |
| AC-38 | Can create SimRL task via `create-task --sim-rl` | SimRL task_id returned |
| AC-39 | Can save SimRL draft via `save-draft --sim-rl` | SimRL task_id, status DRAFT |
| AC-40 | Can show SimRL task via `show-task --sim-rl` | SimRL task object |
| AC-41 | Can update SimRL task via `update-task --sim-rl` | Field updated |
| AC-42 | Can delete SimRL task via `delete-tasks --sim-rl` (DELETE) | SimRL task removed |
| AC-43 | Can stop SimRL task via `stop-task --sim-rl` | status → STOPPING → STOPPED |
| AC-44 | Can restart SimRL task via `restart-task --sim-rl` | Task resubmits |
| AC-45 | Can clone SimRL task via `clone-task` | New SimRL task_id returned |
| AC-46 | Can monitor SimRL: get-resource-usage/get-events/get-logs/get-signed-url with `--sim-rl` (no get-stages — SimRL has no stages endpoint) | Monitoring data returned |
| AC-47 | `resume-task --sim-rl` correctly rejected | Error (resume is train-only) |

### Status Enum

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-48 | Status enum has 16 states | All states documented and observed |
| AC-49 | Terminal states correctly identified | FINISHED/FAILED/RUN_FAILED/etc. stop polling |
| AC-50 | Non-terminal states continue polling | DRAFT/CREATING/WAITING/RUNNING/etc. |

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
| NFR-10 | All file extensions in allowed list | .md/.sh/.json/.yaml/.yml/.py/.txt/.png/.svg etc. |
| NFR-11 | spec documented as string format | grep for Ascend format pattern |
| NFR-12 | train_method documented as uppercase enum | grep for SFT/LORA/QLORA/DEEPSPEED |
| NFR-13 | --sim-rl flag documented on 15 commands | grep '--sim-rl' in SKILL.md |
| NFR-14 | Required params documented (metric/start/end, start-time/end-time, file-source/file-name) | grep in SKILL.md |

## Test Cases Summary

| Case Type | Count | Coverage |
| ----------- | ------- | ---------- |
| Asset query | 4 | AC-01 ~ AC-04 |
| Task creation | 8 | AC-05 ~ AC-12 |
| Task management | 11 | AC-13 ~ AC-23 |
| Monitoring | 5 | AC-24 ~ AC-28 |
| Log management | 4 | AC-29 ~ AC-32 |
| Draft workflow | 3 | AC-33 ~ AC-35 |
| SimRL | 12 | AC-36 ~ AC-47 |
| Status enum | 3 | AC-48 ~ AC-50 |
| **Total** | **50** | Full coverage |
