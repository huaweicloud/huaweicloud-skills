# Verification Method 验证方法

Run the commands below from the repository root. Stage checks are **read-only** unless
marked otherwise.

```bash
SKILL_DIR=skills/ai/cloudrobo/huawei-cloud-cloudrobo-data-pipeline
```

## Specification Compliance Verification 规范合规验证

### Structure Validation 结构验证

```bash
# Verify skill directory structure
ls -la "$SKILL_DIR"/
ls -la "$SKILL_DIR"/references/
ls -la "$SKILL_DIR"/scripts/
ls -la "$SKILL_DIR"/templates/

# Every references/*.md linked from SKILL.md exists (expected: no output)
grep -o 'references/[a-z0-9-]*\.md' "$SKILL_DIR"/SKILL.md | sort -u | while read -r f; do
  [ -f "$SKILL_DIR/$f" ] || echo "MISSING: $f"
done
```

### Frontmatter Validation Frontmatter验证

```bash
# Check frontmatter exists
grep '^---$' "$SKILL_DIR"/SKILL.md | head -2

# Check name, description triggers, tags
grep '^name: huawei-cloud-cloudrobo-data-pipeline$' "$SKILL_DIR"/SKILL.md
grep 'Triggers include:' "$SKILL_DIR"/SKILL.md
grep '^tags:' "$SKILL_DIR"/SKILL.md

# No metadata block (expected: no output)
grep '^metadata:' "$SKILL_DIR"/SKILL.md
```

### Section Validation 章节验证

```bash
# Required sections (bilingual headers)
grep '^## .*概述' "$SKILL_DIR"/SKILL.md
grep '^## .*前置条件' "$SKILL_DIR"/SKILL.md
grep '^## .*工作流' "$SKILL_DIR"/SKILL.md
grep '^## .*CLI命令格式标准' "$SKILL_DIR"/SKILL.md
grep '^## .*核心命令' "$SKILL_DIR"/SKILL.md
grep '^## .*参数确认' "$SKILL_DIR"/SKILL.md
grep '^## .*参考文档' "$SKILL_DIR"/SKILL.md
grep '^## .*边界情况' "$SKILL_DIR"/SKILL.md
grep '^## .*验证方法' "$SKILL_DIR"/SKILL.md
```

### Content Consistency Checks 内容一致性检查

Each command below is expected to print **no output** (this file is excluded because it
contains the search patterns).

```bash
# No restart command (failure handling = diagnose logs, then create a new task)
grep -rnE --exclude=verification-method.md 'restart-task|restart_task|/restart' "$SKILL_DIR"

# pipeline.yaml keys are snake_case
grep -rnE --exclude=verification-method.md 'parallel-group|fail-fast' "$SKILL_DIR"

# Removed pipeline.yaml params keys are not used in the template
grep -nE '^[[:space:]]*(checks|urdf_path):' "$SKILL_DIR"/templates/*.yaml

# workspace use takes --workspace-id (no positional argument)
grep -rnE --exclude=verification-method.md 'workspace use <' "$SKILL_DIR"

# Agent helpers stay CLI/offline; SDK imports belong to the Web adapter only
rg -n '^[[:space:]]*(from|import) cloudrobo' "$SKILL_DIR/scripts/custom_pipeline.py" "$SKILL_DIR/scripts/pipeline_state.py" "$SKILL_DIR/scripts/platform_utils.py"

# No experimental conclusions
grep -rnE --exclude=verification-method.md '\(verified\)|rejected with 500|Verified operator inputs' "$SKILL_DIR"

# obs:// is the only object-storage scheme
grep -rnE --exclude=verification-method.md '(s3|oss|gs)://' "$SKILL_DIR"
```

Manual review: `grep -rn 'obs_path' "$SKILL_DIR"` — every hit must be a
`pipeline.inputs[]` field, a `dataset_configs` field, or the rule that `obs_path` is never
an `inputs` key. `inputs` elements carry `url_path` only.

### File Size Constraint 文件大小约束

```bash
# Total skill directory size must not exceed 40 MB
du -sh "$SKILL_DIR"/
```

### File Count Constraint 文件数量约束

```bash
# Skill source files must not exceed 40, including native frontend modules
# (exclude generated caches and distribution LICENSE).
find "$SKILL_DIR"/ -type f ! -path '*/__pycache__/*' \
  ! -name '*.pyc' ! -name '*.pyo' ! -name '.DS_Store' ! -name LICENSE | wc -l
```

The modular frontend and cross-platform runtime bring the package to 40 source files. The source-file budget includes
each separately reviewable JavaScript module; production JavaScript also has a 400-line
per-file limit, checked by ESLint below.

## Functional Testing 功能测试

### CLI Smoke Tests CLI冒烟测试

```bash
bash "$SKILL_DIR"/scripts/test-cli-commands.sh -s "$SKILL_DIR" -e cli
```

The script runs read-only commands only (version, workspace, operator discovery, task
listing, and optional checks on existing task IDs — see the script header for its
environment variables). Test cases are listed in `templates/test-vars.json`; cases with
`requires_confirmation: true` are mutating and are run manually only after the user
confirms. These Agent CLI smoke checks do not use the SDK; Web SDK contracts are tested separately.

### API Testing API测试

API-level verification is manual — replay the API paths listed in
[Dataflow Diagram](dataflow-diagram.md) in
[API Explorer](https://console.huaweicloud.com/apiexplorer/) against a live environment.

## Pipeline Stage Verification 分阶段验证

### Pre-flight 预检

```bash
cloudrobo --version
# Expected: prints the CLI version

cloudrobo config get region
# Inspect the configured value and its source; cross-check intended region/endpoint.
# Missing/conflicting configuration requires user confirmation; never infer from image URL.

cloudrobo workspace current
# Expected: JSON with workspace_id and asset_catalog_id (not "未配置工作空间")
```

> `create-task --dry-run` only echoes the arguments; it does not validate task_config.
> It is not a substitute for the plan confirmation or the CLI required-field validation.

### Stage 0: Pipeline Parsing 管线解析

No CLI call. Check the parsed pipeline and the execution plan:

| Check | Expected |
|-------|----------|
| Keys | snake_case (`parallel_group`, `fail_fast`, `depends_on`, `operator_source`) |
| Operators | Every stage / `parallel_group` member has `operator` (exact Chinese name) or `operator_id` |
| DAG | All `depends_on` targets exist; no cycles; evaluation declares `depends_on: [cleaning]` |
| `params` | Only `envs` and `inputs`; `inputs` declared as `{name, url_path}` |
| Evaluation | No `robot_config` in task_config; optional config mounts (e.g. `ROBOT_CONFIG_PATH`) are full operator `inputs` elements with `obs://` `url_path`, omitted when not selected; `fail_fast: false` |
| Plan | Shown to and confirmed by the user before the first mutating command |

### Operator Discovery (Steps 2.1 / 3.1 / 4.1) 算子发现

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --exact-name "<stage operator>"
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --exact-name "<eval member operator>"
# Expected: page_info.total = 1; data[0].name equals the stage operator; sub_type is
# data_processing / data_evaluating; ext_metadata.engine.image_url and ext_metadata.command
# are non-empty
```

- `page_info.total = 0` → the run must have stopped and told the user (no substitute
  operator was used)
- The submitted `algo_id` / `image` / `algo_entrance` / `inputs` equal the values of the
  query made right before submission (not values from an earlier run)

### Stage 1: Input Registration 数据注册

```bash
cloudrobo asset list-versions --asset-id <dataset_asset_id> --sort-key created_at --sort-dir desc --limit 1
# Expected: returns the version recorded as dataset_version_id

cloudrobo asset show-version --asset-id <dataset_asset_id> --version-id <dataset_version_id>
# Expected: url is an obs:// path (passed to Stage 2 dataset_configs); status was checked —
# RELEASE when the next stage requires a released version
```

### Stage 2 / 3: Conversion and Cleaning 格式转换与数据清洗

```bash
cloudrobo dataset proc list-tasks --name "<pipeline_name>"
# Expected: task names follow <pipeline_name>-<stage_id>-<YYYYMMDDHHmmss>

cloudrobo dataset proc show-task --task-id <proc_task_id>
# Expected: status SUCCEEDED; target_path (obs://...) and target_asset_id are non-empty;
# for the cleaning task, target_asset_name = pipeline.output.asset_name

cloudrobo dataset proc wait-task --task-id <proc_task_id> --timeout 60 --interval 10
# Expected for a finished task: "START → SUCCEEDED" and "最终状态: SUCCEEDED"
```

> `wait-task` prints text (not JSON) and prompts interactively when the task is `FAILED`
> (`任务失败，是否查看日志？`; with no stdin it prints `Aborted!` and exits 1). In
> non-interactive runs pipe `printf 'n\n' |` into it. For verification of failed tasks,
> use `show-task` and `get-log` instead. A `最终状态` that is not `SUCCEEDED` /
> `FAILED` / `DELETED` means the wait timed out — re-run `wait-task`; the task must not
> have been resubmitted.

**Artifact handoff 产物交接**

```bash
cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc
# Inspect further pages if needed; identify the exact task output, not just newest.

cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
# Expected: version status was checked before the next stage (published with
# update-version --status RELEASE only after user confirmation, if required)
```

The next proc stage's `dataset_configs` use this stage's `target_path`, `target_asset_id`,
`target_version_id` and output name. Eval stages set top-level `dataset_type` /
`dataset_id` / `dataset_name` / `dataset_path` plus single-item `dataset_configs` with the same exact version — no hardcoded
names or paths.

**Failure diagnosis 失败诊断**

```bash
cloudrobo dataset proc get-log --task-id <proc_task_id> --is-system true    # Expected: system log file list
cloudrobo dataset proc get-log --task-id <proc_task_id> --is-system false   # Expected: job log file list
cloudrobo dataset proc get-log --task-id <proc_task_id> --file-name <name> --file-path <path>
# Expected: log content (latest 64 KB; add --all for the full log)
```

After a `FAILED` / `DELETED` task, the retry is a **new** `create-task` with a new task
ID, created only after user confirmation; the failed task is left as is.

### Stage 4: Evaluation 数据评测

```bash
cloudrobo dataset eval list-tasks --name "<pipeline_name>"
# Expected: one quality-eval and one diversity-eval task for the run

cloudrobo dataset eval show-task --task-id <quality_eval_task_id>
cloudrobo dataset eval show-task --task-id <diversity_eval_task_id>
# Expected: both in a terminal state (SUCCEEDED / FAILED / DELETED);
# target_report_path is non-empty for SUCCEEDED tasks

cloudrobo dataset eval get-preview --task-id <eval_task_id> --file-name <target_report_path without obs://<bucket>/>
# Expected: temporary OBS preview link (add --is-download for a download link)

cloudrobo dataset eval get-log --task-id <eval_task_id> --is-system true     # failed member only
```

- Both eval tasks were created (without `--wait`) before either `eval wait-task` was run
- A failed eval member did not block Stage 5 (`fail_fast: false`)

### Stage 5: Output 输出

| Check | Expected |
|-------|----------|
| TrainingReady path | Equals the cleaning task's `target_path` |
| Summary | Follows [Pipeline Summary Template](pipeline-summary-template.md): per-stage status, artifacts, resources, issues, all task IDs, instantiated pipeline.yaml |
| Failed stages | Reported with error message and log-based cause; success claimed only for verified artifacts |
| Checkpoint | `~/.cloudrobo/pipeline-runs/<run_id>/state.json` schema v2, written through pipeline_state.py with task CAS and historical attempts |

## End-to-End Verification Checklist 端到端验证清单

| Check | Verification Method |
|-------|---------------------|
| Plan confirmation | No mutating command ran before the user confirmed the plan (operators, envs, inputs, specs, pool, output names/paths) |
| Fresh operator discovery | `list-publication-assets` ran in this run before each submission |
| Operator not found | Run stopped and the user was told; no substitute operator |
| `inputs` format | JSON-array string; each element copied from the current `ext_metadata.inputs[]` with only `url_path` set; optional inputs omitted by default |
| `--algo-type` | Matches stage `operator_source` and `task_config.algo_type` (proc only) |
| Required fields | proc / eval task_config pass the CLI required-field validation |
| Task naming | `<pipeline_name>-<stage_id>-<YYYYMMDDHHmmss>` |
| Proc wait | `create-task` without `--wait` → `proc wait-task` → `show-task` |
| Eval parallel | Both eval tasks created without `--wait`, then `eval wait-task` per task |
| Handoff | Exact asset/version/path verified via task detail and `show-version` → proc `dataset_configs` or eval matching top-level fields plus single-item `dataset_configs` |
| Eval advisory | Eval failure did not block TrainingReady output |
| No restart | Failures handled by `get-log` diagnosis + new task after confirmation |
| Agent / Web boundary | Agent uses CLI; Web uses SDK, without CLI subprocesses |
| Object storage | Only `obs://` paths |
| Summary | TrainingReady path, task IDs and issues reported |

## CLI Command Reference CLI命令参考

| Stage | CLI Command | Purpose | Type |
|-------|-------------|---------|------|
| Pre-flight | `cloudrobo workspace current` | Current workspace + `asset_catalog_id` | Read (local) |
| Pre-flight | `cloudrobo workspace use --workspace-id <id>` | Set default workspace | Local config |
| Pre-flight | `cloudrobo resource list-pools` | Dedicated pool `resource_id` / name | Read |
| Stage 1 | `cloudrobo asset list-assets` / `show-asset` | Find registered dataset | Read |
| Stage 1 | `cloudrobo asset create-asset` + `create-version` | Register OBS dataset | Mutating |
| Stage 1 | `cloudrobo asset import-asset` | Import local directory | Mutating |
| Stage 1 / handoff | `cloudrobo asset list-versions` / `show-version` | Version id, `url`, status | Read |
| Stage 1 / handoff | `cloudrobo asset update-version --status RELEASE` | Publish version | Mutating |
| Discovery | `cloudrobo asset list-publication-assets` | Resolve operators | Read |
| Stage 2 / 3 | `cloudrobo dataset proc create-task` | Submit conversion / cleaning | Mutating |
| Stage 2 / 3 | `cloudrobo dataset proc wait-task` / `show-task` / `list-tasks` | Wait, read output | Read |
| Stage 2 / 3 | `cloudrobo dataset proc get-log` / `download-log` | Diagnose | Read |
| Stage 4 | `cloudrobo dataset eval create-task` | Submit quality / diversity eval | Mutating |
| Stage 4 | `cloudrobo dataset eval wait-task` / `show-task` / `list-tasks` | Wait, read report path | Read |
| Stage 4 | `cloudrobo dataset eval get-preview` | Report preview / download link | Read |
| Stage 4 | `cloudrobo dataset eval get-log` / `download-log` | Diagnose | Read |

## Verification Flow 验证流程

```
Each test case → Run the CLI command
  ├── ✅ Success → Record PASS
  └── ❌ Failure → Compare the command with `cloudrobo <group> <command> --help`
       ├── ✅ Syntax issue → Fix and retry
       └── ❌ Non-syntax issue → Check credentials / workspace / region
            ├── ✅ Fixed → Retry and record PASS
            └── ❌ Still failing → Record FAIL ⛔ requires manual verification
```

## Local Website Smoke Tests 本地网站基础验证

From the skill directory, run the offline suite (standard library only):

```bash
python3 -m unittest discover -s scripts/pipeline-monitor/tests -p 'test_*.py' -v
node scripts/pipeline-monitor/tests/test_browser.mjs --out /tmp/cloudrobo-monitor-qa
```

The optional browser suite requires Node 22+ and an installed Chrome/Chromium; it starts
an isolated demo service, uses no cloud credentials and installs no packages. It verifies
run list/search, DAG/drawer/history/config, logs/search, Console resource-detail guidance, confirmed
retry/skip/terminate, report/summary and 2560/1920/1512/1280/768/390 layouts. Screenshots and report.json
are generated under the specified output directory.

The Python suite covers output parsing, plan validation, run/task/log membership, masking,
operator freshness, conflicting retries, direct advisory skip and verified original-input processing bypass, terminal/legacy restrictions,
uncertain submissions, query failures and authenticated HTTP/Host/CSRF behavior. Terminal
submissions must reserve-task before create-task and resolve-action after the result, so
Agent and Web use the same transaction lock. See [Web Monitor](web-monitor.md).

Intranet validation must still check actual show-task timestamps/errors,
get-log/frames/preview response shapes, available operators and one explicitly
confirmed new-task submission followed by Agent artifact handoff. Keep these marked
unverified until they run against the company environment; demo success does not prove
cloud API or algorithm availability. Results: [Web Test Report](web-monitor-test-report.md).

## Guided Authoring Verification 引导创建验证

Use the same offline unittest discovery command above: 22 CustomPipelineTests cover
single-evaluation export, custom workspace/OBS steps, cleaned-input handoff, cycles/unknown
dependencies, ordered multi-input merges/control gates and rejected report handoff, task naming, params/credentials/failure
policies, preserving original files, incomplete/invalid CLI exports and preview usability
(per-member config mounts, removed `robot_config` rejection, recorded resources and unselected intermediate output names). The full
suite contains 83 tests (43 monitor + 22 authoring + 10 runtime compatibility + 4 SDK isolation + 4 installed-SDK contracts), including input-dependent
upload omission, finish without a false warning, consistent status/service return contracts
and JSON object checks for checkpoints and task records. The separate browser suite contains
35 checks, including evaluation retry with immutable top-level dataset fields, processing skip request/cancel/apply and required-conversion rejection, ordered multi-input display, a failed preview read without automatic retry and successful manual recovery, tree hierarchy/lazy loading, retained tab content/request counts, explicit directory refresh, Windows CLI-copy quoting, file-opening startup guidance, manual check/preparation/artifact nodes without task requests, actual
local downloads, error visibility and six viewports (390 through 2560 px).

Generic-workflow coverage includes empty drafts without template defaults, preset-only
and workspace-only chains, mixed-source export, processed OBS/local inputs, evaluation
without mandatory cleaning, raw-to-LeRobot format errors, explicit/ambiguous final data
selection and monitoring all terminal branches. Multi-input cases cover separate initial IDs,
shared input fan-out, A/B → C ordering/export, control-only eval gates, invalid/ambiguous
sources, per-input processed metadata and data-path format validation. resolve-inputs
is checked for read-only behavior, both-producer readiness, exact input metadata and
legacy single-upload handoff; Web retry rechecks every original input without reordering. These structural tests do not establish
that the example workspace operators exist; actual asset subtypes and data contracts must
be checked with the intranet CLI before execution.

SDK isolation coverage rejects Web subprocess creation, checks lazy dependency loading,
clear missing-SDK errors, four-operation concurrency, session ownership/cleanup and unsupported methods.
Run the same suite with a Python environment containing CloudRobo SDK to exercise the four additional
contracts against actual installed SDK classes/signing, intercepting HTTP requests only: proc/eval
URLs, parameter names, tail/full logs, previews, Unicode/nested JSON, explicit workspace, timeouts,
no automatic retries, validation and uncertain creation results. Without SDK, these four are skipped
(79 pass / 4 skipped). Neither path accesses cloud services or creates real tasks.
Windows background process flags still use API substitutes on macOS; native desktop verification remains required.

Read the scenarios in [Guided Custom Pipeline Authoring](custom-pipeline-authoring.md)
for conversational review. Independent simulated-user trials exercised first creation,
revision without overwriting earlier files, and evaluation of an existing cleaned asset;
an independent regression pass checked the automatically generated preview after fixes.
Check that a user can start without YAML, supplied information is reused, changing the
evaluation selection preserves other choices, and creation-only requests stop after the
three local artifacts. See the [two-round report](web-monitor-test-report.md) for evidence
and limits. No live discovery or execution was tested by these local cases. Generated YAML
was also round-tripped with a standard YAML parser,
including newline/colon/boolean-looking strings, and accepted by monitor plan normalization.

Skill-creator's system quick validator does not recognize this repository's existing
top-level tags field; its raw result flags that schema difference. Keep the repository
frontmatter convention (name/description/tags), validate those fields separately, and use
the system checker on a temporary copy without tags to check the remaining name,
description and body rules. Do not claim an unmodified system-validator pass.

## Code Review Rules 代码检视规则

The [ESLint configuration](../scripts/pipeline-monitor/tests/eslint.config.mjs) applies to
the frontend, browser test and configuration itself. It rejects nested conditional expressions
(including those inside template interpolation), requires braces for control bodies and one
variable declaration per statement, checks keyword/operator spacing, and limits each
if/for/while/do/conditional test to three boolean conditions. Production frontend modules
also reject undefined/unused bindings and files longer than 400 physical lines, including
comments and blank lines. More involved decisions belong in named checks and rendering
helpers. The module responsibilities are listed in [Web Monitor](web-monitor.md#8-前端模块-frontend-modules).

From the skill root, a development environment with ESLint 9+ and Pylint can run:

```bash
eslint --config scripts/pipeline-monitor/tests/eslint.config.mjs \
  scripts/pipeline-monitor/static/*.js scripts/pipeline-monitor/tests/*.mjs
python3 -m pylint --disable=all --enable=inconsistent-return-statements --score=n \
  scripts/platform_utils.py scripts/custom_pipeline.py scripts/pipeline_state.py \
  scripts/pipeline-monitor/sdk_adapter.py scripts/pipeline-monitor/monitor.py \
  scripts/pipeline-monitor/server.py scripts/pipeline-monitor/tests/test_monitor.py
```

These are development checks; the frontend and ordinary offline tests need no npm/pip
runtime dependencies. Real Web platform access requires the documented Python SDK packages. HTTP handlers consistently return None; persisted object readers and
service/node lookups return dictionaries; timestamp parsing returns a float. The validators
and task lookup keep their fixed three/four-element tuples. JSON adapters declare one
JSONValue contract and use one return value, preserving supported JSON objects, arrays and
text logs instead of changing the wire format for a style rule.

Windows follow-up coverage retains hidden STARTUPINFO and background process-group flags.
The previous Web CLI launcher workaround is superseded by direct SDK calls. Old-service health versions
are tested through real local HTTP: diagnose reports restart_required and installed SDK metadata,
and startup refuses silent reuse without altering runs or making cloud calls.
These tests still do not establish native Windows desktop behavior.

Processing-bypass coverage checks request/cancel, no early downstream readiness, CLI application with
exact original version, summary warnings, required-format/multi-input rejection, current-version/source/note
guards, existing decisions/submitted descendants, chained branch handoff, legacy/terminal restrictions
and original upload compatibility. Agent checks of real workspace/OBS contracts still require intranet CLI access.
