# Acceptance Criteria 验收标准

`SKILL_DIR=skills/ai/cloudrobo/huawei-cloud-cloudrobo-data-pipeline` (paths relative to the
repository root). Commands for each check are detailed in
[Verification Method](verification-method.md).

## Functional Criteria 功能标准

### Pipeline Parsing & Planning 管线解析与计划

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | Verbal trigger loads `templates/sim-teleop-cleaning.yaml`; a user-provided `pipeline.yaml` is parsed directly (no `type` field) | Trigger "用遥操/仿真数据处理模板" and provide a custom YAML; check the parsed stages shown to the user | ☐ |
| AC-02 | Stage DAG is built from `depends_on` (implicit previous-stage dependency); cycles are rejected; operator input/output contracts determine valid ordering | Check the displayed stage order; a YAML with a cycle is rejected with a request to fix it | ☐ |
| AC-03 | Missing input source (`local` / `asset` / `obs`) and operator-required robot choices are clarified; datasets need not include YAML and evaluation does not universally require a robot-description mount | Check built-in robot/default config, file config and evaluation without a robot-description mount | ☐ |
| AC-04 | An execution plan is shown and confirmed **before any mutating operation** (`create-asset`, `create-version`, `import-asset`, `update-version`, `dataset proc create-task`, `dataset eval create-task`). The plan lists per stage the resolved operator (name / asset_id / image), `--algo-type`, `envs`, `inputs` (config mounts), resource pool and specs, task names, output names and paths | Check the transcript: no mutating command before the user's explicit confirmation | ☐ |
| AC-05 | A changed value (smaller flavor after `POD_PENDING`, new task after `FAILED`) is re-confirmed before submission | Check the transcript | ☐ |

### Guided Custom Pipeline Creation 引导创建自定义管线

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| CUSTOM-01 | “引导我创建自定义管线” enters authoring without requiring existing YAML or silently choosing the full built-in template | Walk through the scenarios in [authoring guide](custom-pipeline-authoring.md) | ☐ |
| CUSTOM-09 | An unspecified request leaves an empty draft and starts with the user's goal; preset-only, workspace-only and mixed workflows preserve selected steps without forced conversion/cleaning/evaluation | Offline authoring tests + conversational walkthrough | ☐ |
| CUSTOM-10 | Compatible data can be evaluated without cleaning; known raw-to-LeRobot mismatches are rejected; workspace contracts are checked at discovery | Offline format cases + intranet metadata verification | ☐ |
| CUSTOM-11 | Final data comes from output.from_stage (unique terminal proc inferred, ambiguous branches require selection); reports cannot be selected as datasets; output monitor waits for all terminal branches | Offline export and monitor-plan tests | ☐ |
| CUSTOM-02 | Reuses known information; collects data stage/source, chosen steps/evaluation scope, operator source, necessary params and resources incrementally | Interview scenarios; check single-quality/eval-only outputs | ☐ |
| CUSTOM-03 | Exports pipeline.yaml + editable draft JSON + preview; preserves existing files; resources/handoff stay outside YAML params | Offline export and overwrite tests | ☐ |
| CUSTOM-04 | Rejects dependency cycles/unknown IDs, duplicate task names, ambiguous/invalid multi-input bindings, report-as-data, bad ordering, failure policy, source/schema/name errors | Offline authoring tests | ☐ |
| CUSTOM-05 | Cleaned-input evaluation requires matching asset/version/path/name; a robot-description mount is optional for metrics the operator supports without it; creates no fake conversion/cleaning tasks or dataset output | Offline partial-pipeline test with and without a description directory | ☐ |
| CUSTOM-06 | Single-dataset branches are recommended, not required; A/B → merge C produces ordered proc inputs; control gates remain separate, eval remains single-input; all data paths are checked | Multi-source authoring/export, ambiguous/invalid reference rejection, read-only resolve-inputs and retry verification of every dataset | ☐ |
| CUSTOM-08 | Offline missing-field drafts stay marked incomplete; invalid graphs never export; local validity does not claim live operator readiness | Offline CLI check/export tests | ☐ |
| CUSTOM-07 | Creation-only requests perform no cloud writes or confirmed-run init; requested execution reuses Stage 0 plan confirmation and Web transaction protocol | Review entrypoint and export effects; intranet follow-up | ☐ |
| INPUT-01 | Verified initial datasets are persisted by input ID before downstream work; all inputs are required before upload success, existing-asset SKIPPED and legacy single-input results remain compatible; registration panels update even if status stays SUCCEEDED | record-inputs CLI, missing/invalid/CAS guards, multiple-source display and cached-panel browser checks | ☐ |
| PARALLEL-01 | All syntax normalizes to one task graph and ready frontier; CLI/Web share completion gates. ready-tasks says submit while any ready sibling remains, then poll; resolve releases the submission slot after ID verification, while joins still wait for all required inputs | Syntax-adapter and CLI queue transition tests; A pending/running does not delay B; grouped joins/defaults, terminal/decision/uncertainty guards; intranet submission timestamps vs queueing | ☐ |

### Operator Discovery 算子发现

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-06 | Operators are discovered **in every run, right before each submission** with `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing"` / `"Data Evaluation"` and a Chinese `--name` fragment; no hardcoded asset IDs and no operator info (image / algo_id / command / inputs) reused from a previous run | Check the transcript for a fresh discovery call per stage | ☐ |
| AC-07 | The result is matched against the stage's exact `operator` name (or `operator_id`) and is unique; multiple matches → the user chooses | Run `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --exact-name "<operator>"`; `page_info.total` = 1 | ☐ |
| AC-08 | **Operator not found → stop**: if the required operator is not returned in the current region/marketplace, the pipeline stops and tells the user; no other operator is substituted | Use an operator name that does not exist; check that no task is created | ☐ |
| AC-09 | `algo_id`, `algo_name`, `algo_entrance`, `image` come from the current result (`asset_id`, `name`, `ext_metadata.command`, `ext_metadata.engine.image_url`); `algo_entrance` is copied unchanged | Compare the submitted task_config with the discovery output | ☐ |

### Task Configuration 任务配置

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-10 | `inputs` is a JSON-array **string**; each element is the operator's current `ext_metadata.inputs[]` element copied as returned, with only `url_path` set to the user-selected `obs://` path; no `obs_path` key; optional inputs omitted by default; inputs with a built-in `url_path` need no user action | Inspect the submitted task_config of a task with an input mount | ☐ |
| AC-11 | `envs` is a JSON-array string; only names declared in `ext_metadata.environment_variables`; `params.envs` overrides the operator default; undeclared names are reported as errors | Inspect task_config; try an undeclared env name | ☐ |
| AC-12 | Proc `--algo-type` follows `operator_source` (`preset` → `PRESET_ASSETS`, `workspace` → `WORKSPACE_ASSETS`, `obs` → `OBS_ASSETS`) and equals `task_config.algo_type`; `dataset eval create-task` is called without `--algo-type` | Inspect the commands | ☐ |
| AC-13 | proc / eval task_config contain required fields; eval task_config never contains `robot_config`; supplied config mounts are full operator `inputs` elements with `obs://` `url_path`, absent mounts remain omitted; an outdated client requiring `robot_config` is reported as needing an upgrade | Check submission without `robot_config`, old-client pre-dispatch rejection message; no fabricated path or empty mount array | ☐ |
| NAME-01 | New tasks/data outputs use pipeline-stage-MMDDHHmmss (no default random suffix; complete total ≤64 including collision ordinal; preserve both semantic components); preserve explicit legal names and confirmed-run resume; proc retry suggests a fresh output, eval/bypass keep their actual input names | Local naming/64-character boundary tests plus two new conversations, retry and resume checks | ☐ |
| AC-14 | Task names follow `<pipeline_name>-<stage_id>-<MMDDHHmmss>` (member `id` inside `parallel_group`) and stay within the CLI limit of 3–64 characters | `cloudrobo dataset proc list-tasks --name "<pipeline_name>"`, `cloudrobo dataset eval list-tasks --name "<pipeline_name>"` | ☐ |
| AC-15 | Resource pool and specs are the confirmed values; `POD_PENDING` on the public pool leads to a smaller flavor or dedicated pool and a **new** task after confirmation | Inspect task_config and the transcript | ☐ |

### Stage Execution & Waiting 阶段执行与等待

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-16 | Stage 1: the input dataset version is read with `show-version`; verified DRAFT can proceed when supported; publication uses `update-version --status RELEASE` only after confirmation for an established requirement; the dataset OBS path is the version `url` | `cloudrobo asset show-version --asset-id <id> --version-id <vid>` | ☐ |
| ASSET-01 | Pipeline local-data uploads first load the Asset Center skill and use asset CLI import-asset for upload plus registration; honor confirmed metadata/frontmatter and import recovery; OBS sources only register, existing assets only verify; no generic OBS-tool search or duplicate creation | Review local/OBS/existing-asset and interrupted-import routes, confirmation order and verified IDs/path handoff | ☐ |
| AC-17 | Conversion: reserve-task → create-task without --wait → resolve-action → wait-task --timeout 300 with heartbeat/state reload → show-task; status SUCCEEDED | `cloudrobo dataset proc show-task --task-id <conversion_task_id>` | ☐ |
| AC-18 | Cleaning: same flow; input = conversion output; `output_name` = `pipeline.output.asset_name` | `cloudrobo dataset proc show-task --task-id <cleaning_task_id>` (`target_asset_name`) | ☐ |
| AC-19 | Evaluation: quality and diversity tasks are both created **without `--wait`**, both task IDs are recorded, then `dataset eval wait-task --task-id <id>` runs for each; Stage 5 starts only when both are terminal | Check command order in the transcript; `cloudrobo dataset eval show-task --task-id <id>` for each | ☐ |
| AC-20 | `wait-task` timeout while the task is non-terminal → `wait-task` is re-run and progress is reported; the task is not resubmitted | Check that no duplicate task exists in `list-tasks --name "<pipeline_name>"` | ☐ |
| AC-21 | Terminal states are `SUCCEEDED`, `FAILED`, `DELETED`; `DELETED` is handled like a failure | Check the stage status table | ☐ |

### Artifact Handoff 产物交接

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-22 | After a proc task `SUCCEEDED`, read its output path, asset and exact version from task detail; if version is absent, inspect version candidates and verify task/output ownership with `show-version`, without assuming newest | Compare the verified asset/version/path with the checkpoint; ambiguity blocks handoff | ☐ |
| AC-23 | The next proc stage's `dataset_configs` (`obs_path`, `dataset_type: BUILD_IN_ASSET`, `asset_id`, `asset_name`, `version_id`) or eval stage's matching top-level fields plus single-item `dataset_configs` use each selected input_from source's exact asset/version/path; eval does not omit `version_id` — no hardcoded names or paths | Inspect the next task's task_config | ☐ |
| AC-24 | The version/path is checked with `show-version`; verified DRAFT may proceed, and publication (`update-version --status RELEASE`) requires confirmation only for an established downstream restriction | Check the transcript | ☐ |

### Evaluation & Reports 评测与报告

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-25 | Evaluation is advisory (`fail_fast: false`): a failed eval member does not block the TrainingReady output; the run is recorded as SUCCEEDED_WITH_WARNINGS with the missing/failed evaluation identified | Run with a failing eval member; the summary still reports the TrainingReady path | ☐ |
| AC-26 | For each `SUCCEEDED` eval member, `target_report_path` is read with `eval show-task` and the report link is fetched with `dataset eval get-preview --task-id <id> --file-name <target_report_path without obs://<bucket>/>` | Run the commands | ☐ |
| AC-27 | Each eval member resolves its own optional `params.inputs` config mounts (e.g. `ROBOT_CONFIG_PATH`); no group-level default; absent mounts run the operator's built-in/default config. A pipeline still using `robot_config` fails validation/init with migration guidance; Web retry drops a legacy `robot_config` and keeps refreshed mounts. Invalid `url_path` values are reported. Robot-dependent metrics and operator limitations are explained; mounts only if declared/needed; no `algo_entrance` workaround | Check distinct/absent mounts in preview, YAML, task configs and Web retry, `robot_config` rejection, and old-client errors without dispatch | ☐ |

### Failure Handling & Recovery 故障处理与恢复

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-28 | `FAILED` / `DELETED` tasks are diagnosed with `dataset proc\|eval get-log --task-id <id> --is-system true\|false`, then `--file-name <name> --file-path <path>`; the cause is reported | Run the commands on a failed task | ☐ |
| AC-29 | Retry is always a **new** `create-task` after user confirmation; no restart command is used | Check the transcript and `list-tasks --name "<pipeline_name>"` (new task ID) | ☐ |
| AC-30 | A failed/submitted `fail_fast: true` processing stage blocks downstream and cannot be directly skipped; unsubmitted single-input proc may request Agent-verified bypass with exact original-input handoff; advisory evaluation may skip under its rules | Check the transcript | ☐ |
| AC-31 | `~/.cloudrobo/pipeline-runs/<run_id>/state.json` schema v2 records stage task IDs/status/artifacts and attempts; all writes use pipeline_state.py with lock/CAS; resume reloads Web changes and follows current tasks | Interrupt a run, retry in Web, resume at terminal | ☐ |

### Output 输出

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-32 | A pipeline-artifact summary is produced per [Pipeline Summary Template](pipeline-summary-template.md): run overview with per-stage status, data/versions, confirmed resource configuration (live usage available in Console), issues & recommendations, evaluation reports, all task IDs and the instantiated pipeline.yaml | Check the final output | ☐ |
| AC-33 | Final data comes from output.from_stage, or the input is preserved for eval-only workflows; no generic TrainingReady claim; success is claimed only for verified artifacts | Compare selected source with `show-task` / `show-version` and Web summary | ☐ |

## Non-Functional Criteria 非功能标准

### Security & Constraints 安全与约束

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-34 | No real AK/SK in the skill — placeholders only | `grep -rnE --exclude=acceptance-criteria.md 'HUAWEI_CLOUD_(AK\|SK)="[^<]\|config set ak [^<]' "$SKILL_DIR"` returns no output | ☐ |
| AC-35 | Credentials come from `cloudrobo config set` or `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK`; they never appear in `pipeline.yaml`, task_config, checkpoint, summary or chat | Check docs and run artifacts | ☐ |
| AC-36 | Agent orchestration stays CLI; Web platform reads and confirmed retries use SDK without CLI subprocesses | Content consistency checks in [Verification Method](verification-method.md) | ☐ |
| AC-37 | Only `obs://` object-storage paths are used | Content consistency checks in [Verification Method](verification-method.md) | ☐ |
| AC-38 | All commands and flags exist in the CLI help (`cloudrobo <group> <command> --help`) | Compare each documented command with its `--help` output | ☐ |

### Documentation 文档

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-39 | Frontmatter has `name`, `description` (with `Triggers include:`) and `tags`; no `metadata:` block | Frontmatter checks in [Verification Method](verification-method.md) | ☐ |
| AC-40 | Bilingual section headers are present | Section checks in [Verification Method](verification-method.md) | ☐ |
| AC-41 | Every reference document listed in SKILL.md exists | Structure checks in [Verification Method](verification-method.md) | ☐ |
| AC-42 | `scripts/test-cli-commands.sh` runs read-only commands only; `templates/test-vars.json` is valid JSON and marks every mutating case `requires_confirmation: true` | `bash "$SKILL_DIR"/scripts/test-cli-commands.sh -s "$SKILL_DIR" -e cli`; `python3 -m json.tool "$SKILL_DIR"/templates/test-vars.json > /dev/null` | ☐ |
| AC-43 | Directory size ≤ 40 MB | `du -sh "$SKILL_DIR"/` | ☐ |
| AC-44 | Skill source files ≤ 40, including native frontend modules (exclude generated test/runtime outputs, caches and distribution LICENSE) | Count non-cache source files in the skill folder | ☐ |

## Quality Gates 质量门禁

### Local Web Monitor 本地网站

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| WEB-01 | Local assets and standard-library HTTP server, SDK for real platform operations, only 127.0.0.1; token→HttpOnly/SameSite cookie, Host/CSRF and run/task/log membership validation | Offline Python HTTP tests | ☐ |
| WEB-02 | Viewport-sized workbench contains DAG/list/summary/details; timeline defaults collapsed, fixed-height panel renders ≤20 events with filters/paging, new events preserve historical page and scroll, no document vertical overflow across desktop/short/mobile viewports | Large-event browser regression, paging/new-event/scroll preservation, six viewport widths plus native Windows/real task checks | ☐ |
| WEB-03 | Config tables/raw JSON/diff, job/system log selection/tail/search/errors/full/download | Demo + real intranet task | ☐ |
| WEB-04 | Proc frames/preview and fresh eval report links per click; resource details use CloudRobo Console; no local resource tab, endpoint or CLI resource query | Demo + HTTP/CLI exclusion and actual response-field verification | ☐ |
| WEB-05 | Retry refreshes preset operator and verifies upstream version/path (DRAFT or RELEASE); only confirmed config creates a new task; old attempts retained | Offline adapter/action tests + confirmed intranet retry | ☐ |
| WEB-06 | Web and terminal reserve before create under one lock/CAS; concurrent callers create at most one task; uncertainty retains pending_action for reconciliation | Offline concurrency/recovery tests; terminal reserve-task/resolve-action | ☐ |
| WEB-07 | Advisory steps may skip; unsubmitted single-input proc bypass requires an Agent-verified compatibility decision; historical attempts/legacy v1 are read-only; termination requires run ID and leaves cloud tasks untouched | Offline state/action and browser tests | ☐ |
| WEB-08 | Stale/failed queries disable mutations; missing configs/operators block retries; errors remain visible | Offline negative-path tests + intranet unavailable interfaces | ☐ |
| WEB-09 | Agent state reload + heartbeat after each 300-second wait; Web never advances DAG or calls wait-task/restart-task | Inspect SDK adapter/public Web routes, Agent CLI workflow and shared state; verify no Web CLI subprocesses | ☐ |
| WEB-10 | No claim of cloud integration success from demo; remaining internal checks recorded | [Web test report](web-monitor-test-report.md) | ☐ |
| WEB-11 | Frontend uses modules by responsibility; each production JS file ≤ 400 physical lines; module requests keep authentication, JavaScript MIME type and parallel loading support | ESLint + HTTP and browser tests | ☐ |
| WEB-12 | “打开监控网站” directly opens an established real run or the persisted run list; empty lists work without CLI/credentials; only explicit demo requests use --demo; opening does not init sample runs | Opening-guide review + isolated default-mode HTTP/start/reuse/stop smoke check | ☐ |
| WEB-13 | Immediately after execution-plan confirmation and local init, offer once before upload/asset registration/publication/task submission; if accepted or previously authorized, open that run before input preparation; local init is not cloud submission, unanswered preference does not block orchestration, and retry/recovery does not repeat it | Walk through OBS/local/existing-asset and eval-only inputs; check offer/open ordering, terminal-only/prior-request/creation-only paths and pre-task page | ☐ |

| WEB-14 | Confirmed local deletion only for terminal v2 runs without pending submissions; CAS/shared lock/path protection, full local file and cache removal, stale-link fallback and explicit cleanup-failure reporting; no cloud task/asset deletion or stop | Terminal-state, cancel, active/legacy/pending/version/lock guards, concurrency, filesystem fault, symlink, HTTP and browser tests | ☐ |

Commands and manual intranet steps: [Web Monitor](web-monitor.md).

The following numbered gates apply to the built-in template; custom workflows gate each
declared edge by its actual operator contract and select their own output source.

| Gate | Must Pass Before |
|------|------------------|
| Stage 0 complete (DAG valid, operators resolved, plan confirmed) | Any mutating operation |
| Stage 1 complete (input dataset registered, version checked) | Submitting conversion |
| Conversion `SUCCEEDED` + handoff version resolved (or verified compatible unsubmitted bypass) | Submitting cleaning |
| Cleaning `SUCCEEDED` + handoff version resolved (or verified compatible unsubmitted bypass) | Submitting evaluation |
| Both eval members terminal (any status) | Stage 5 summary |
| Summary produced | Pipeline declared done |

## Partial Pipeline Gates 部分管线门禁

| Start Stage | Required Inputs | Output |
|-------------|-----------------|--------|
| Stage 3 (cleaning) | Conversion `target_path`, `target_asset_id`, `target_version_id`, asset name | TrainingReady data + eval reports |
| Stage 4 (evaluation) | Cleaning `target_path`, `target_asset_id`, `target_version_id`, asset name; optional eval config mounts (`inputs`) | Eval reports with actual metric coverage |
| Full pipeline | Input source (`local` / `asset` / `obs`), stage operators; optional robot description for selected metrics | TrainingReady data + eval reports |

## Sign-off 签收

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Skill Author | | | |
| Reviewer | | | |
| Approver | | | |

### Follow-up Gates 后续能力门禁

| # | Criterion | Verification | Status |
|---|---|---|---|
| WEB-EX-01 | Web platform queries/retries use SDK without CLI subprocesses; the background server uses Windows no-window/hidden STARTUPINFO flags | SDK contracts/no-subprocess checks plus native Windows service, query and browser retests | ☐ |
| WEB-EX-02 | Unsubmitted single-input proc offers request/cancel skip; only Agent-verified compatible original input is forwarded, never arbitrary success | Skip lifecycle, format/data/CAS/legacy/started-task guards, exact handoff and warning completion tests | ☐ |
| WEB-EX-03 | Updated source detects stale background service; diagnose reveals source/service revision and SDK package metadata without secrets or cloud calls | Local HTTP old-version service and restart-required test | ☐ |
