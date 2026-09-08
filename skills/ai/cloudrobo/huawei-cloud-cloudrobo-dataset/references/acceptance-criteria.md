# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Task Management 任务管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | `create-task` creates a processing task and returns task_id + status | Run `cloudrobo dataset proc create-task --name test --algo-type PRESET_ASSETS --task-config '{...}'` | ☐ |
| AC-02 | `list-tasks` returns all tasks for the workspace | Run `cloudrobo dataset proc list-tasks` | ☐ |
| AC-03 | `list-tasks` filters by status | Run `cloudrobo dataset proc list-tasks --status RUNNING` | ☐ |
| AC-04 | `show-task` returns task detail | Run `cloudrobo dataset proc show-task --task-id <id>` | ☐ |
| AC-05 | `update-task` modifies task config (SDK) | Call `client.update_task(task_id, {"name": "new"})` | ☐ |
| AC-06 | `delete-task` removes a task (CLI/SDK) | Run `cloudrobo dataset proc delete-task --task-id <id>` or call `client.delete_tasks([task_id])` | ☐ |
| AC-07 | `restart-task` restarts a task | Run `cloudrobo dataset proc restart-task --task-id <id>` | ☐ |

### Task Monitoring 任务监控

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-09 | `wait-task` polls until terminal state | Run `cloudrobo dataset proc wait-task --task-id <id> --timeout 60` | ☐ |
| AC-10 | `wait-task` reports status transitions | Check stdout for `START → RUNNING → SUCCEEDED` | ☐ |
| AC-11 | `get-log --is-system true` lists system log files | Run `cloudrobo dataset proc get-log --task-id <id> --is-system true` | ☐ |
| AC-12 | `get-log --is-system false` lists job log files | Run `cloudrobo dataset proc get-log --task-id <id> --is-system false` | ☐ |
| AC-13 | `get-log --file-name --file-path` returns log content | Run with file_name from AC-11/12 | ☐ |
| AC-14 | `get-log --all` returns full log | Compare with default 64KB tail | ☐ |

### Data Preview 数据预览

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-15 | `get-preview` returns OBS temp download link | Run `cloudrobo dataset proc get-preview --task-id <id> --file-name <file-path>` | ☐ |
| AC-16 | `get-task-frames` returns frame info | CLI: `cloudrobo dataset proc get-frames --task-id <id> --prefix <prefix>` / SDK: `client.get_task_frames(task_id, prefix="...")` | ☐ |

### Algorithm Discovery 算法发现

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-17 | `list-algorithms` returns data_processing algorithms | Run `cloudrobo asset list-publication-assets --type algorithm --sub-type data_processing` | ☐ |
| AC-18 | `list-algorithms` returns data_evaluating algorithms | Run with `--sub-type data_evaluating` | ☐ |
| AC-19 | Each algorithm includes `ext_metadata` with engine info | Check response has `ext_metadata.engine.image_url` | ☐ |

### Evaluation Tasks (eval-tasks) 数据评测任务

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-20 | `eval create-task` creates an evaluation task and returns task_id | Run `cloudrobo dataset eval create-task --name test --task-config '{...}'` | ☐ |
| AC-21 | `eval list-tasks` returns all eval tasks for the workspace | Run `cloudrobo dataset eval list-tasks` | ☐ |
| AC-22 | `eval show-task` returns eval task detail | Run `cloudrobo dataset eval show-task --task-id <id>` | ☐ |
| AC-23 | `eval update-task` modifies eval task config (SDK) | Call `client.update_eval_task(task_id, {"name": "new"})` | ☐ |
| AC-24 | `eval delete-task` removes a single eval task (SDK) | Call `client.delete_eval_task(task_id)` | ☐ |
| AC-25 | `eval get-log --is-system true` lists eval system log files | Run `cloudrobo dataset eval get-log --task-id <id> --is-system true` | ☐ |
| AC-26 | `eval get-log --file-name --file-path` returns eval log content | Run with file_name from AC-25 | ☐ |
| AC-27 | `eval get-preview` returns OBS temp URL for report | Run `cloudrobo dataset eval get-preview --task-id <id> --file-name <n>` | ☐ |
| AC-29 | eval-tasks use `dataset_configs` (same as proc-tasks) | Check task_config field names | ☐ |
| AC-30 | eval-tasks require `robot_config` field | Check task_config has `robot_config` | ☐ |
| AC-31 | eval-tasks deletion is single-granularity (no batch) | Confirm `delete-task` not `delete-tasks` | ☐ |

### Pipeline & Batch 流水线与批量

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-32 | Pipeline: processing `target_path` feeds eval `dataset_configs` | Create proc task → wait SUCCEEDED → create eval task with target_path wrapped in dataset_configs | ☐ |
| AC-33 | Pipeline: eval SUCCEEDED → get-preview returns OBS link | Complete pipeline and verify preview URL | ☐ |
| AC-34 | Batch: create tasks for multiple datasets, collect IDs | Create 2+ tasks, verify all return task_id | ☐ |
| AC-35 | Batch: SDK `delete_tasks([id1, id2])` removes multiple | Call `client.delete_tasks([id1, id2])`, verify deletion | ☐ |

### Resource Monitoring 资源监控

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-36a | `get-resource-usage` returns CPU metric time series | Run `cloudrobo dataset proc get-resource-usage --task-id <id> --metric CPU_UTIL --start <ts> --end <ts> --step 60` | ☐ |
| AC-36b | `get-resource-usage` rejects invalid metric | Run with `--metric INVALID`, expect error | ☐ |
| AC-36c | `get-resource-usage` enforces step range 10-3600 | Run with `--step 5`, expect rejection | ☐ |

### Log Download 日志下载

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-36 | `download-log` downloads a proc-task log file | Run `cloudrobo dataset proc download-log --task-id <id> --file-name <n> --file-path <p>` | ☐ |
| AC-37 | `download_eval_task_log` downloads an eval-task log file (SDK) | Call `client.download_eval_task_log(task_id, file_name, file_path)` | ☐ |

## Non-Functional Criteria 非功能标准

### Security 安全

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-38 | No hardcoded AK/SK in SKILL.md or scripts | `grep -r "AK\|SK\|ACCESS_KEY\|SECRET" skills/cloudrobo-dataset/` | ☐ |
| AC-39 | Credentials read from environment variables | Check docs reference `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` | ☐ |
| AC-40 | Mutating operations require user confirmation | Check SKILL.md Parameter Confirmation section | ☐ |

### Documentation 文档

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-41 | SKILL.md has valid frontmatter | `grep '^---$' skills/cloudrobo-dataset/SKILL.md` | ☐ |
| AC-42 | Frontmatter has name + description + tags | Check frontmatter fields | ☐ |
| AC-43 | Description includes `Triggers include:` | `grep 'Triggers include:' skills/cloudrobo-dataset/SKILL.md` | ☐ |
| AC-44 | All required sections present | Check Overview/Prerequisites/Workflow/Core Commands/Parameter Confirmation/Reference Documents | ☐ |
| AC-45 | Bilingual section headers | `grep '##.*概述'`, `grep '##.*前置条件'`, etc. | ☐ |
| AC-46 | references/ directory exists with required files | `ls skills/cloudrobo-dataset/references/` | ☐ |
| AC-47 | scripts/test-cli-commands.sh exists | `ls skills/cloudrobo-dataset/scripts/` | ☐ |
| AC-48 | templates/test-vars.json exists | `ls skills/cloudrobo-dataset/templates/` | ☐ |

### Constraints 约束

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-49 | Directory size ≤ 40 MB | `du -sh skills/cloudrobo-dataset/` | ☐ |
| AC-50 | File count ≤ 30 | `find skills/cloudrobo-dataset/ -type f \| wc -l` | ☐ |
| AC-51 | All files have allowed extensions | Check for .md/.sh/.json/.yaml/.py only | ☐ |
| AC-52 | No fabricated API paths | All paths match SDK source `_url()` calls | ☐ |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |
