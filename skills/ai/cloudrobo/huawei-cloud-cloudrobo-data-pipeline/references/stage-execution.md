# Stage Execution Detail (Stages 2–4)

Load this file **when you are about to submit a task** — not while planning. It holds the
per-stage command mechanics and `task_config` construction rules that `SKILL.md` summarizes.

> **Context budget**: read only the stage you are executing (Stage 2 / 3 / 4), not all three.
> If you already know the field mapping from
> [Task Config Reference](task-config-catalog.md), you may skip the corresponding section.

Operator discovery, the "operator not found → stop" rule, and the "query fresh every time"
rule live in `SKILL.md` §Stage 2 and still apply. Every operator field
(`algo_id` / `algo_name` / `algo_entrance` / `image` / `envs` / `inputs`) comes from the
**current** `list-publication-assets` result, never from this file or a previous run.

---

## Operator field mapping (all stages)

| Operator Asset Field | task_config Field |
|---------------------|-------------------|
| `asset_id` | `algo_id` |
| `name` | `algo_name` |
| `ext_metadata.command` | `algo_entrance` |
| `ext_metadata.engine.image_url` | `image` |
| `ext_metadata.environment_variables` | `envs` (if present) |
| `ext_metadata.inputs` | `inputs` (optional mounts) |

There is no `ext_metadata.hyperparams` and no task_config `params` field — operator
behaviour is tuned only through `envs` and `inputs`.

---

## Resolve operator input mounts (all proc stages)

Read `ext_metadata.inputs` from the discovered operator (it may be absent or `null` — then
omit `inputs`) and decide which to mount:

- `required: true` must be provided (a built-in `url_path` needs no action).
- `required: false` is optional — **do not prompt by default**; ask only for custom config
  or when the operator would otherwise fail.

When guidance IS needed (no default, inferred value differs, required input with empty
url_path, or the user asks to customize), follow the
[envs/inputs guidance rules](user-facing-interaction.md#46-when-to-guide-envs--inputs-configuration)
— translate options to user language, pre-select a recommended value, ask in the same
confirmation round, never expose raw JSON keys.

> **`inputs` format**: `inputs` is a JSON-array **string** field (like `dataset_configs` /
> `envs`). Each element is the operator's `ext_metadata.inputs[]` element **copied as
> returned by the current query** (do not add or strip fields), with only `url_path` set to
> the user-selected `obs://` path. Never use `obs_path` as an inputs key. Input names
> (`DATA_CONFIG_PATH`, `CURATION_CONFIG_PATH`, `ROBOT_CONFIG_PATH`, etc.) are **dynamic** —
> read them from `ext_metadata.inputs` at discovery time, never hardcode.

```text
"inputs": "[{\"name\":\"<input-name-from-ext_metadata>\",\"label\":\"<as returned>\",\"required\":false,\"url_path\":\"obs://bucket/config/\",\"input_type\":\"<as returned>\",\"description\":\"<as returned>\",\"access_method\":\"env\"}]"
```

Known operator inputs (reference only — always re-read the current `ext_metadata.inputs`):
conversion/cleaning may have optional config mounts; evaluation may have an optional robot
description mount; desensitization has a required built-in model mount.

Input datasets do not universally require YAML files. Use the selected operator's built-in
`robot` environment/default configuration, existing dataset config, or optional external
config mount as appropriate. Only when a YAML config file is actually needed, apply the
[manifest candidate rules](task-config-catalog.md#manifest-config-names); manifest mode
alone does not require an external file or an evaluation config mount.

---

## Shared submission mechanics (proc stages)

```bash
cloudrobo dataset proc create-task --name "<pipeline_name>-<stage_id>-<MMDDHHmmss>" --algo-type <PRESET_ASSETS|WORKSPACE_ASSETS|OBS_ASSETS> --task-config '<json>'
```

`--algo-type` comes from the stage `operator_source` (`preset` → `PRESET_ASSETS`,
`workspace` → `WORKSPACE_ASSETS`, `obs` → `OBS_ASSETS`) and overrides
`task_config.algo_type`, so keep both identical. Submit **without** `--wait`, record the
`task_id`, then wait.

**Resource spec**: `resource_pool_type` is `PUBLIC_POOL` (default) or `DEDICATED_POOL` —
ask the user in Stage 0; for `DEDICATED_POOL` also set `resource_id` and
`dedicated_pool_name`. Templates use **4c8g** (`worker_spec: {cpu: 4, memory: 8, gpu: 0,
npu: 0}`) as the default `worker_spec`; for CCE/K8S `head_spec` is `{cpu: 0, memory: 0,
gpu: 0, npu: 0}` and `worker_num` is `1`.

**Public pool note**: a 4c8g pod can stay in `POD_PENDING` under resource contention. If
that happens, choose a smaller flavor such as 2c4g (`{cpu: 2, memory: 4, gpu: 0, npu: 0}`)
or use a dedicated pool, then create a new task after user confirmation.

**RAY tasks (cluster_type=CCE_RAY / task_framework_type=RAY)**: `head_spec` must be
non-zero; example head **2c4g** (`{cpu: 2, memory: 4, gpu: 0, npu: 0}`), workers **4c8g × 2**
(`worker_spec: {cpu: 4, memory: 8, gpu: 0, npu: 0}`, `worker_num: 2`).

See [Task Config Reference](task-config-catalog.md) for the full task_config template and a
complete JSON example.

> **Required proc task_config fields** (CLI validation rejects missing/empty values):
> - `catalog_id` — workspace's catalog_id (from `cloudrobo workspace current`, **not** the operator's)
> - `cluster_type` — `CCE` (standard); `CCE_RAY` for RAY tasks
> - `task_framework_type` — `K8S` (standard); `RAY` for RAY tasks
> - `output_type` — `BUILD_IN_ASSET` (default) or `UDF_OBS_ASSET` (user OBS output)
> - `evs_spec` — `0` (default; only public-pool tasks may set non-zero)
>
> **Note**: `envs`, `dataset_configs` and `inputs` are JSON array **strings** (double-quoted),
> not native JSON objects.

`OBS_ASSETS` operators use `algo_path` + `job_local_path` instead of a registered asset —
see [Custom Operator Stages](../SKILL.md#custom-operator-stages).

---

## Waiting and extracting output (all proc stages)

```bash
cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15
cloudrobo dataset proc show-task --task-id <id>   # status / target_path / target_asset_id
cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc
cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
```

Use the task's returned version when available. Otherwise inspect version candidates
(including further pages as needed) and verify which belongs to this task and output path.
Do not select the newest version by position; ask if the exact version remains ambiguous.

> **`wait-task` output and FAILED prompt**: `wait-task` prints text status lines
> (`START → <status>`, `最终状态: <status>`), not JSON. On `FAILED` it asks interactively
> whether to show logs (`任务失败，是否查看日志？`); with no stdin it prints `Aborted!` and
> exits 1 after `最终状态: FAILED` — that is the task result, not a CLI error. In
> non-interactive runs pipe an answer: `printf 'n\n' | cloudrobo dataset proc|eval wait-task
> ...`. Always read the result with `show-task`, then diagnose with `get-log`.

- `SUCCEEDED` → extract `target_path`, `target_asset_id` and the exact `target_version_id`
  matching this task output; verify the version/path with `show-version`; a verified `DRAFT`
  may proceed without publication. Only an established downstream RELEASE requirement needs
  publication confirmation.
- `wait-task` timed out while the status is still non-terminal → re-run `wait-task` and
  report progress; do **not** resubmit.
- `FAILED` / `DELETED` → diagnose with `cloudrobo dataset proc get-log --task-id <id>
  --is-system true|false`, then `--file-name <name> --file-path <path>`; after user
  confirmation create a **new** task. See [Fault Recovery](fault-recovery.md).

---

## Stage 2: Conversion task_config

- **Input**: registered asset from Stage 1 — `dataset_configs` with `obs_path` = version
  `url` from `show-version`, `dataset_type: BUILD_IN_ASSET`, `asset_id`, `asset_name`,
  `version_id`.
- **envs**: from the conversion operator's `environment_variables` (e.g. `robot`).
- **inputs**: optional `DATA_CONFIG_PATH` (custom conversion manifest) per the mounts rule.
- **Output**: `output_name` = the conversion output name confirmed in the plan.

---

## Stage 3: Cleaning task_config

Input is the Stage 2 output: `dataset_configs` built from `target_path` /
`target_asset_id` / `target_version_id` / `<conversion output_name>`.

- **envs**: read `environment_variables` from the operator `ext_metadata` — names, valid
  values and defaults are all dynamic (do not hardcode), e.g. `mode` (cleaning strategy)
  and `robot` (robot type) when declared. Map `robot_type` to an enumerated `robot` value
  (see [Robot type mapping](../SKILL.md#robot-type-mapping)).
- **inputs**: optional `CURATION_CONFIG_PATH` (custom cleaning config) from stage
  `params.inputs`, expanded per the mounts rule above.
- **Output**: `output_name` = `pipeline.output.asset_name` (训练就绪数据集名).
- **Resource**: as in the shared submission mechanics.

Cleaning-specific task_config differences from conversion:
`algo_id`/`algo_name`/`algo_entrance`/`image` come from the discovered `数据清洗` operator;
`envs` might look like `[{"key":"mode","value":"mark"},{"key":"robot","value":"galaxea_r1"}]`.

---

## Stage 4: Evaluation task_config

Evaluation tasks use `dataset eval create-task` (not `proc create-task`, no `--algo-type`).
Common eval fields: `name`, `algo_id`, `algo_name`, `algo_entrance`, `image`,
`dataset_type`, `dataset_name`, `dataset_path`, `resource_pool_type`, `worker_spec`,
`dataset_configs` (+ `dataset_id` when `dataset_type=BUILD_IN_ASSET`). See
[Task Config Reference](task-config-catalog.md) for the eval template.

**Input**: top-level `dataset_type: BUILD_IN_ASSET`, `dataset_id` = cleaning
`target_asset_id`, `dataset_name` = `<cleaning output_name>`, `dataset_path` = cleaning
`target_path`. Include a single-item `dataset_configs` JSON-array string with that same
asset/name/path and exact `version_id` = cleaning `target_version_id`. Both eval tasks
share the same cleaned input/version. Use the
[version handoff rules](task-config-catalog.md#dataset-version-handoff).

**Config mounts (`inputs`) & `robot_config`**: `robot_config` is removed; config
directories (e.g. robot description) are passed only via the operator's declared
`ext_metadata.inputs` with `url_path` set to the user's `obs://` directory. When no mount
is selected, omit `inputs` and run with the operator's built-in/default configuration. If
the CLI/SDK rejects an eval task because `robot_config` is missing, the client is outdated —
upgrade it, do not add the field. Show each member's mounts or "no mount (uses the
operator's built-in/default configuration)" in the execution plan, rendered in the user's
language. Do not invent a path or use the dataset path as a substitute.

**envs**: if the eval operator declares `environment_variables`, read valid values/defaults
at discovery time and map `robot_type` to an enumerated value; if none declared, omit `envs`.

**Robot description mount failure**: if the task fails with
`ValueError: ROBOT_CONFIG environment variable is not set`, check whether the chosen
metrics require robot geometry. If the operator declares a matching input (e.g.
`ROBOT_CONFIG_PATH`), offer the actual robots.yaml/URDF OBS directory as that member's
mount and confirm the scope change before a new task. Otherwise report the operator
limitation (evaluation is informational only). Do not work around via `algo_entrance` —
copy `ext_metadata.command` unchanged; use `envs`/`inputs` instead.

**Submission**: submit both eval tasks **without** `--wait`, record both `task_id`s, then
wait for each. Stage 5 only proceeds when all members reach a terminal state. Complete
reserve/create/verify-ID/resolve for the first member, then submit the second immediately;
never run wait-task or wait for the first report between these transactions.

```bash
cloudrobo dataset eval create-task --name "<pipeline_name>-quality-eval-<MMDDHHmmss>" --task-config '<json>'
cloudrobo dataset eval create-task --name "<pipeline_name>-diversity-eval-<MMDDHHmmss>" --task-config '<json>'
```

**Resource**: as in the shared submission mechanics, per eval task. Parallel group total =
2 × the selected eval `worker_spec`.

### Waiting for both eval tasks

```bash
cloudrobo dataset eval wait-task --task-id <quality_task_id> --timeout 300 --interval 15
cloudrobo dataset eval wait-task --task-id <diversity_task_id> --timeout 300 --interval 15
```

`wait-task` prints status lines (not JSON) and prompts on `FAILED` — in non-interactive runs
pipe `printf 'n\n' |` into it, then read each result with
`cloudrobo dataset eval show-task --task-id <id>`.

- All `SUCCEEDED` → fetch reports.
- Timed out while non-terminal → re-run `wait-task`, report progress; do not resubmit.
- Any `FAILED` / `DELETED` → diagnose with `cloudrobo dataset eval get-log --task-id <id>
  --is-system true|false`; evaluation is informational only and does not block the final
  training-ready dataset. A new eval task is created only after user confirmation.

### Fetching evaluation reports

Run for **each** eval member (quality and diversity):

```bash
cloudrobo dataset eval show-task --task-id <eval_task_id>   # extract target_report_path
cloudrobo dataset eval get-preview --task-id <eval_task_id> --file-name <target_report_path-without-obs://bucket/-prefix>
```

`--file-name` is `target_report_path` with the `obs://<bucket>/` prefix removed (e.g.
`obs://bucket-0/cloudrobo/test.pdf` → `cloudrobo/test.pdf`). Add `--is-download` for a
download link instead of a preview link.

For a platform `get-preview` error 500/502/503/504, wait briefly and repeat the same read
once. If it fails again, retain the task ID, report path and error for diagnosis. A preview
read failure does not change the evaluation task result or justify resubmitting the task.
