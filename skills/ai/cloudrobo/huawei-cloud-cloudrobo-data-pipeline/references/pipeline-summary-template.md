# Pipeline Summary Template 管线执行总结模板

Output skeleton for **Stage 5** of the pipeline. Produce it when the pipeline reaches the
end, or when it stops at a terminal state (a blocking stage `FAILED` / `DELETED`, or the
user terminates). Fill every field from real command output (`show-task`, `list-versions`,
`show-version`, `eval show-task`, `get-preview`). Write `—` for fields that do not apply,
and never invent values.

For a custom workflow, build stage rows from its actual DAG and operator sources,
including preset-only/workspace-only combinations. Read final data from
`pipeline.output.from_stage` and report its verified path/asset/version; for eval-only
workflows preserve the input and list reports. Do not assume a cleaning output or label
all results TrainingReady. The numbered conversion/cleaning/evaluation examples below
describe the optional sim/teleop template, not mandatory custom steps.

**Before writing the summary 生成总结前:**

- Verify artifacts before reporting success. A task can be `FAILED` while its output or
  report partly exists, and it can be `SUCCEEDED` while a downstream operator rejects the
  output. Check with `cloudrobo dataset proc show-task --task-id <id>` and
  `cloudrobo asset show-version --asset-id <target_asset_id> --version-id <version_id>`.
  Optionally list the output files with
  `cloudrobo dataset proc get-frames --task-id <id> --prefix <target_path without obs://<bucket>/>`.
- The TrainingReady data path is the **cleaning stage's `target_path`**. There is no
  separate publish step: cleaning + evaluation complete = TrainingReady data.
- Evaluation is advisory (`fail_fast: false`). A failed or skipped evaluation makes the
  run ⚠️ PARTIAL, not ❌ FAILED.

**Status legend 状态图例:** ✅ SUCCEEDED · ⚠️ PARTIAL (finished with failed or skipped
advisory members) · ❌ FAILED (`FAILED` / `DELETED`, or a blocking stage did not finish)
· ⏭️ SKIPPED (not run / skipped by the user)

**Overall result 总体结果:** ✅ if every stage succeeded. ⚠️ if the cleaning stage succeeded
(TrainingReady data exists) but an evaluation member failed or was skipped. ❌ if
conversion or cleaning did not succeed (no TrainingReady data).

---

## Version Publication 版本发布

At completion, read the exact recorded output asset/version IDs with `show-version` and
list the statuses of intermediate and final data outputs. Give one consolidated reminder
about publishing selected versions, respecting decisions already made. DRAFT is not itself
a run failure/warning, and publication is not a `finish` condition. Publish only after
confirmation; do not put asset-version status in task `status` or invent set-result fields.

## Template 模板

````markdown
# Pipeline Run Summary — <pipeline_name>

**Overall result**: ✅ SUCCEEDED | ⚠️ PARTIAL | ❌ FAILED

## 1. Pipeline Run Overview 运行概览

| Item | Value |
|------|-------|
| Pipeline name | <pipeline.name> |
| Mode | Built-in template (`sim-teleop-cleaning`) / Custom pipeline.yaml / Partial (from Stage <n>) |
| Run ID | <run_id> |
| Workspace ID | <workspace_id> |
| Run window | <start time> → <end time> (total <duration>) |
| Region / source | <verified region> / <CLI config or user confirmation; endpoint check> |

| Stage | Stage id | Operator (name / asset_id) | Task ID | Status | Duration | Output asset / version | target_path / report |
|-------|----------|----------------------------|---------|--------|----------|------------------------|----------------------|
| 1 Upload & register | — | — | — | ✅ | <duration> | <dataset asset_id> / <version_id> | <dataset obs_path> |
| 2 Conversion | convert-lerobotv3 | <operator name> / <asset_id> | <task_id> | ✅ | <duration> | <target_asset_id> / <version_id> | <target_path> |
| 3 Cleaning | cleaning | <operator name> / <asset_id> | <task_id> | ✅ | <duration> | <target_asset_id> / <version_id> | <target_path> |
| 4 Evaluation | quality-eval | <operator name> / <asset_id> | <eval_task_id> | ✅ / ❌ / ⏭️ | <duration> | — | <target_report_path> |
| 4 Evaluation | diversity-eval | <operator name> / <asset_id> | <eval_task_id> | ✅ / ❌ / ⏭️ | <duration> | — | <target_report_path> |

## 2. Data Situation 数据情况

| Item | Value |
|------|-------|
| Input source | <source_type: local / asset / obs> — <obs_path / local_path / asset_id + version_id> |
| Input format | <data_source_type: h5 / ros2 / umi> |
| Robot type | <robot_type> (operator `robot` env value: <value or —>) |
| Registered input dataset | <asset name> / <asset_id> / <version_id> |
| Conversion output | <output_name> / <target_asset_id> / <version_id> / <target_path> |
| Cleaning output | <output_name> / <target_asset_id> / <version_id> / <target_path> |
| **TrainingReady data path** | **<cleaning target_path>** (asset <pipeline.output.asset_name>, version <version_id>, status <version status from show-version>) |

### Version Status and Publication 版本状态与发布

| Output | Asset ID | Exact version ID | Verified status (`show-version`) | Publication choice |
|---|---|---|---|---|
| <intermediate or final stage output> | <id> | <vid> | <DRAFT / RELEASE / actual state / unverified> | <keep current / confirmed publish / undecided> |

> Consolidated reminder: <list versions not yet published and ask once whether any should
> be published, unless already decided>. Keeping DRAFT does not block pipeline completion.

## 3. Evaluation Reports 评测报告

| Member | Status | target_report_path | Report link (get-preview) |
|--------|--------|--------------------|---------------------------|
| quality-eval | <status> | <target_report_path> | <preview / download URL> |
| diversity-eval | <status> | <target_report_path> | <preview / download URL> |

> Links come from `cloudrobo dataset eval get-preview --task-id <eval_task_id> --file-name <target_report_path without obs://<bucket>/> [--is-download]`.
> They are temporary OBS URLs, so save or download the reports promptly. Quote results
> only from the reports themselves.

## 4. Resource Usage 资源使用

| Stage id | resource_pool_type (pool name) | cluster_type / task_framework_type | head_spec | worker_spec | worker_num |
|----------|--------------------------------|------------------------------------|-----------|-------------|------------|
| convert-lerobotv3 | <PUBLIC_POOL / DEDICATED_POOL (<dedicated_pool_name>)> | <CCE / K8S> | <spec> | <spec> | <n> |
| cleaning | <...> | <...> | <spec> | <spec> | <n> |
| quality-eval | <...> | <...> | <spec> | <spec> | <n> |
| diversity-eval | <...> | <...> | <spec> | <spec> | <n> |

## 5. Issues & Recommendations 问题与建议

| Stage id | Task ID | Status | Error message (show-task / logs) | Root cause | Next step |
|----------|---------|--------|----------------------------------|------------|-----------|
| <stage id> | <task_id> | <FAILED / DELETED> | <error text> | <cause, see references/fault-recovery.md> | <retry (new task) / skip / terminate / user action> |

**Warnings 警告:**

- <e.g. smaller flavor used after POD_PENDING on the public pool>
- <e.g. evaluation skipped as advisory; reason>
- <e.g. an output version state could not be verified; record actual states above, not a warning merely for DRAFT>
- <e.g. a wait-task timed out and was re-run (elapsed time)>

## 6. Reproducibility 可复现信息

- **Task IDs** (all attempts, including failed ones):
  - convert-lerobotv3: <task_id> (<status>) [, <earlier failed task_id> (FAILED)]
  - cleaning: <task_id> (<status>)
  - quality-eval: <eval_task_id> (<status>)
  - diversity-eval: <eval_task_id> (<status>)
- **Checkpoint**: ~/.cloudrobo/pipeline-runs/<run_id>/state.json (schema v2)
- **Instantiated pipeline.yaml**:

```yaml
<the fully resolved pipeline.yaml used for this run>
```
````

---

## Field Sources 字段来源

| Summary field | Source command / field |
|---------------|------------------------|
| Stage task status, start / finish time | `cloudrobo dataset proc show-task` / `cloudrobo dataset eval show-task` |
| `target_path`, `target_asset_id` | `cloudrobo dataset proc show-task --task-id <id>` |
| Output `version_id` | `cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc --limit 1` |
| Output version status / OBS path | `cloudrobo asset show-version --asset-id <target_asset_id> --version-id <version_id>` |
| `target_report_path` | `cloudrobo dataset eval show-task --task-id <eval_task_id>` |
| Report link | `cloudrobo dataset eval get-preview --task-id <eval_task_id> --file-name <path without obs://<bucket>/> [--is-download]` |
| Error message / root cause | `show-task` detail plus `get-log` (see `references/fault-recovery.md`) |
| Operator name / asset_id / image | `cloudrobo asset list-publication-assets` result used at submission |
| Specs / pool | Submitted task_config |


## Web Summary Mapping 网页摘要映射

The Web monitor uses `SUCCEEDED_WITH_WARNINGS` for the advisory-failure `PARTIAL` result
above. It exports a concise Markdown summary with verified state output, all attempt IDs,
report OBS paths and the instantiated JSON plan. Agent-produced Stage 5 summaries retain
the detailed template above. See [Web Monitor](web-monitor.md) for the `finish` protocol;
Web cached statuses alone do not establish verified TrainingReady artifacts.

已校验保留原输入跳过的处理步骤单独列明：步骤、bypass_from、原始资产/版本/路径、兼容性核实说明。
这是未执行处理的告警，不等同于处理成功或生成新版本；跳过清洗不能声称完成清洗或自动达到 TrainingReady。
