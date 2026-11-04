# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Task Management 任务管理

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | `create-task` creates a processing task and returns task_id + status | Run `cloudrobo dataset proc create-task --name test --algo-type PRESET_ASSETS --task-config '{...}'` | ☐ |
| AC-02 | `list-tasks` returns all tasks for the workspace | Run `cloudrobo dataset proc list-tasks` | ☐ |
| AC-03 | `list-tasks` filters by status | Run `cloudrobo dataset proc list-tasks --status RUNNING` | ☐ |
| AC-04 | `show-task` returns task detail | Run `cloudrobo dataset proc show-task --task-id <id>` | ☐ |
| AC-05 | `update-task` modifies task config (modifiable fields: name/description) | Run `cloudrobo dataset proc update-task --task-id <id> --task-config '{"name":"new"}'` | ☐ |
| AC-06 | `delete-task` removes a task (CLI/SDK) | Run `cloudrobo dataset proc delete-task --task-id <id>` or call `client.delete_tasks([task_id])` | ☐ |
| AC-07 | `copy-task` duplicates a task from its detail (`--name`/`--output-name` required) | Run `cloudrobo dataset proc copy-task --task-id <id> --name copy --output-name copy-out` | ☐ |
| AC-53 | `create-task` with `inputs` (complete `ext_metadata.inputs[]` element copied from the current query, `url_path` = user-selected `obs://` path) is accepted | After confirmation, run `cloudrobo dataset proc create-task --name test --algo-type PRESET_ASSETS --task-config '{..., "inputs": "[{...,\"url_path\":\"obs://...\"}]"}'`; verify task_id is returned | ☐ |

### Task Monitoring 任务监控

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-09 | `wait-task` polls until terminal state | Run `cloudrobo dataset proc wait-task --task-id <id> --timeout 60` | ☐ |
| AC-10 | `wait-task` reports status transitions | Check stdout for `START → RUNNING → SUCCEEDED` | ☐ |
| AC-11 | `get-log --is-system true` lists system log files | Run `cloudrobo dataset proc get-log --task-id <id> --is-system true` | ☐ |
| AC-12 | `get-log --is-system false` lists job log files | Run `cloudrobo dataset proc get-log --task-id <id> --is-system false` | ☐ |
| AC-13 | `get-log --file-name --file-path` returns log content | Run with file_name from AC-11/12 | ☐ |
| AC-14 | `get-log --all` returns full log | Compare with default 64KB tail | ☐ |
| AC-14a | `get-events` returns task event list | Run `cloudrobo dataset proc get-events --task-id <id> --job-name <job>` | ☐ |

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
| AC-23 | `eval update-task` modifies eval task config (name/description) | Run `cloudrobo dataset eval update-task --task-id <id> --task-config '{"name":"new"}'` | ☐ |
| AC-24 | `eval delete-task` removes a single eval task | Run `cloudrobo dataset eval delete-task --task-id <id>` | ☐ |
| AC-24a | `eval copy-task` duplicates an eval task (`--name` required) with the same exact asset/version/path | Copy and read back the task; add a newer asset version and confirm another copy still uses the original version | ☐ |
| AC-25 | `eval get-log --is-system true` lists eval system log files | Run `cloudrobo dataset eval get-log --task-id <id> --is-system true` | ☐ |
| AC-26 | `eval get-log --file-name --file-path` returns eval log content | Run with file_name from AC-25 | ☐ |
| AC-27 | `eval get-preview` returns OBS temp URL for report | Run `cloudrobo dataset eval get-preview --task-id <id> --file-name <n>` | ☐ |
| AC-27a | `eval get-events` returns eval event list | Run `cloudrobo dataset eval get-events --task-id <id> --job-name <job>` | ☐ |
| AC-29 | eval task-config uses top-level dataset fields plus matching single-item `dataset_configs` with exact asset `version_id` | Check task_config has `dataset_type`/`dataset_id`/`dataset_name`/`dataset_path` | ☐ |
| AC-54 | `eval wait-task` polls an eval task until terminal state (SUCCEEDED/FAILED/DELETED) or timeout, printing status changes | Run `cloudrobo dataset eval wait-task --task-id <id> --timeout 60 --interval 5` | ☐ |
| AC-30 | Eval task_config never contains the removed `robot_config`; a real OBS robot-description directory is mounted via the operator's declared `inputs` (e.g. `ROBOT_CONFIG_PATH`) only for selected metrics. Manifest mode alone does not require it | Verify omitted/mounted cases and the outdated-client upgrade guidance; no invented paths | ☐ |
| AC-31 | eval-tasks deletion is single-granularity (no batch) | Confirm `delete-task` not `delete-tasks` | ☐ |
| AC-31a | eval-tasks do not support restart | Confirm no restart command; use `copy-task` to re-run | ☐ |

### Pipeline & Batch 流水线与批量

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-32 | Pipeline: processing exact asset/version/path feeds eval top-level fields and single-item dataset_configs | Create proc → verify output version → create eval → read back version metadata → Console clone and compare exact version | ☐ |
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

## Custom Operator Onboarding 验收标准

The following acceptance criteria apply to the **custom operator onboarding** pipeline
(see SKILL.md §Custom Operator Onboarding). Full per-phase criteria live in
`custom-operator/custom-operator-workflow.md` and `custom-operator/custom-operator-workflow.md` §Phase 4.

### Phase 0: Deploy Mode & Asset Detection 部署方式与资产检测

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CO-01 | Deploy mode asked **first** (Mode A image-inbuilt / Mode B OBS-mounted) | Inspect the workflow | Skill asks **A or B** before any build; never infers |
| CO-02 | Mode A: fresh image tag built + pushed on **every** run | Inspect the workflow | Timestamp tag `{YYYYMMDDHHMMSS}`; no "use existing image" question |
| CO-03 | Mode B: OBS path starts with workspace `default_obs_path` | Validate path | Rejected / re-asked otherwise |
| CO-04 | Mode B: code upload mode asked (customer uploads / skill uploads) | Inspect the workflow | Upload mode confirmed (skill upload is a mutation — confirm) |
| CO-05 | Mode B: preset image `swr.{region}.myhuaweicloud.com/...` format | Validate image URL | Passes SWR URL regex |
| CO-06 | Same-name algorithm asset exists → re-submission flag | `list-assets --type algorithm --tags "Data Processing" --exact-name <name>` | Phase 3 runs the re-submission branch |

### Phase 1: Code Adaptation 代码适配

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CO-07 | Work copy created; user's original untouched | `/tmp/custom-operator-work-{ts}/` exists + `git status` on user source | Directory present; no modifications |
| CO-08 | `entrypoint.py` generated from `templates/entrypoint.py` | Check file in work copy | Multi-dataset aggregation (`SOURCE_DATASET_PATH` JSON map); `src` imported relative to `__file__`; output to `TARGET_DATASET_PATH`/`/output` |
| CO-09 | `Dockerfile` generated (Mode A only) | Check file in work copy | `COPY requirements.txt` before `COPY ./src`; Mode B has no Dockerfile |
| CO-10 | `operator_config.json` validated | Field constraints check | No validation errors |

### Phase 2: Image Build & Push 镜像构建推送（Mode A；Mode B 跳过）

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CO-11 | Mode B skips build | Inspect the workflow | No docker login / build / push executed |
| CO-12 | SWR login auto-generated from AK/SK | Execute auto-generated command | `Login Succeeded`; on failure **classify the cause (AK/SK invalid/expired, SWR not enabled / IAM permission missing, region mismatch, network) → walk the fix with the customer → re-run; only if still failing, ask for a full command** — never proceed without verified login |
| CO-13 | Image built + pushed with timestamp tag | `docker images` / `docker push` | Image present; push success; `engine.image_url` written back to `operator_config.json` |
| CO-14 | Build network probed first | Inspect the workflow | External → plain `docker build`; proxy-fronted → `--build-arg HTTP_PROXY/HTTPS_PROXY` + `NO_PROXY` incl. `*.huawei.com` |
| CO-15 | Local junk cleaned after verification **without touching customer artifacts** | `docker images` / `docker ps -a` / precheck logs | Only this run's throwaway/probe/test tags (digest-checked) + recorded containers + proven dangling images/build cache removed; final SWR-tagged image + base image + **all customer images/containers retained**; NO unfiltered `docker container prune -f` / `docker image prune -af` / `docker system prune` in the transcript |

### Phase 3: Asset Registration 资产注册

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CO-16 | Mode A first submission: image + algorithm assets created | `create-asset --type image` then `--type algorithm` | Both return `asset_id` |
| CO-17 | Mode A re-submission: image version + algorithm update | `create-version` (image) + `update-asset` (algorithm) | New image version; `engine.image_url` = new SWR URL; **no new algorithm version** |
| CO-17a | Asset names equal the dialogue-confirmed operator name | `show-asset` on image + algorithm assets | Both `name` == confirmed operator name (no silent rename / auto suffix) |
| CO-18 | Mode B 空间资产-算法 first submission: preset image + algorithm (`image_source=custom`, `engine.asset_id` + `engine.asset_version_id` link the image asset, `code_dir`) | `create-asset` ×2 | Both return `asset_id`; algorithm `engine.asset_id`/`engine.asset_version_id` = image asset id/version id; `code_dir` = OBS path under `default_obs_path` |
| CO-18a | Mode B OBS算法 (mount OBS code directly) skips Phase 3 | Inspect the workflow | **No `create-asset` calls** — no image/algorithm assets; go straight to Phase 4 |
| CO-19 | No `--sub-type` together with `--tags` | Check algorithm creation request | No `400 Invalid parameter: tags` |
| CO-20 | `image_url` consistency (Mode A) | Compare algorithm `engine.image_url` vs image asset `url` | Same SWR URL string |
| CO-21 | Assets verifiable | `cloudrobo asset show-asset --asset-id <id>` | `status=DRAFT` or `available` |

### Phase 4: Proc-Task Runtime Verification 任务运行验收（端到端）

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CO-22 | Dataset source asked first (① 空间资产-数据-新建 / ② 空间资产-数据-复用 / ③ OBS存储) | Inspect the workflow | ① auto: `create-asset --type dataset` + `create-version --url` + `update-version --status RELEASE`; ② reuse: none → remind upload, one → default, multiple → multi-select (max 10); ③ OBS存储: `dataset_configs` entry `{"obs_path":...,"dataset_type":"UDF_OBS_ASSET"}` — no dataset asset created or referenced, no `RELEASE`, and **`obs_path` bucket must equal the workspace-bound bucket (`default_obs_path` from `cloudrobo workspace current`; other OBS buckets rejected & re-asked)** |
| CO-22a | Multiple data sources → ONE task (Mode A & B) | Inspect the workflow + task list | Several OBS paths / datasets (≤10) → **single `create-task`** with N `dataset_configs` entries; exactly ONE task in `list-tasks`; operator log shows "Resolved N datasets"; no per-dataset task split (batch per-dataset split only on explicit user request + confirmed) |
| CO-22b | Mode B task-creation way asked first (空间资产-算法 use created algorithm / OBS算法 mount OBS code directly) | Inspect the workflow | Mandatory choice asked in Phase 0; 空间资产-算法: `algo_type=WORKSPACE_ASSETS` with `algo_id` = Phase 3 algorithm `asset_id` + `algo_path` (= asset `code_dir`) + `job_local_path` (Phase 3 registers assets); OBS算法: `algo_type=OBS_ASSETS` with `algo_path` + `job_local_path`, no `algo_id` **and Phase 3 is skipped**; both keep `algo_name` |
| CO-23 | Mode A proc-task (`WORKSPACE_ASSETS` + `algo_id`) / Mode B 空间资产-算法 (`WORKSPACE_ASSETS` + `algo_id` = Phase 3 asset id + `algo_path` = `code_dir` + `job_local_path`, absolute `algo_entrance`) / Mode B OBS算法 (`OBS_ASSETS` + `algo_path` + `job_local_path`, no `algo_id`, `algo_name` required) | `create-task` | `task_id` returned; unique `output_name` used |
| CO-24 | Task reaches SUCCEEDED + output produced | `show-task` / `get-frames` | `SUCCEEDED`; non-empty `files[]` |
| CO-24a | Output layout clean | `get-frames` on output prefix | Single-dataset output **flat** at the output root (no `{output_name}`-nested dir); no `.cloudrobo-tmp` folder visible |
| CO-25 | User log OK | `get-log --file-name job-std-output.log` | `[DONE] Processed N items, success N, failed 0` (legacy Chinese form also OK); CLI-type operators may use their own success summary |
| CO-26 | Failure handled | Task FAILED | `custom-operator/custom-operator-workflow.md` pattern matched; fix suggested |
| CO-26a | Re-run after rebuild uses the re-submission branch | Inspect the workflow on retry | `create-version` + `update-asset` (never re-`create-asset`); algorithm asset verified pointing at the new image version; fresh `output_name`; re-run `create-task` successful (no HTTP 500) |
| CO-26b | Cancel/re-issue after a task was created deletes the OLD task first | Inspect the workflow + task list | Show `{task_id}` status → confirm with user 「是否删除/停止旧任务？①删除 ②保留 ③查看日志」→ on ① `delete-task` + `show-task` = `DELETED`; only then create the new task; no orphaned running task left (front-end shows no duplicate "running") |
| CO-27 | Cleanup + verification report | Final steps | Server-side local junk cleaned (always, this-run scope only); platform junk cleaned (confirmed + `show-asset`/`show-task` verified per item, never batch, never customer assets); `verification-report.md` offered |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |
