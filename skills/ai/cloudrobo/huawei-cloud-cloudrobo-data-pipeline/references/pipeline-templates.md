# Pipeline Templates & Quick Reference


新建执行时，模板中的产物名称是待解析项或业务基名，不可每次直接复用固定示例名。
按已选工作流运行 `python scripts/custom_pipeline.py suggest-names --pipeline-name teleop --stage convert --stage clean`，
选用实际返回的 `管线名-步骤短名-MMDDHHmmss`，完整长度 ≤64（含时间戳和必要的重名序号）。
默认不加随机串；超长提示缩短管线名/步骤短名。确认前核实选中 catalog 内同名资产，不把时间戳当跨机器唯一保证。
已有 run 的恢复沿用已确认名；用户明确要求某个合法精确名时保持原名。

## Table of Contents

- [YAML Structure](#yaml-structure)
- [Field Definitions](#field-definitions)
- [Use Case Mapping](#use-case-mapping)
- [Template A: Built-in Pipeline — Sim Data (Local Directory)](#template-a-built-in-pipeline--sim-data-local-directory)
- [Template B: Built-in Pipeline — Teleop Data (OBS Path)](#template-b-built-in-pipeline--teleop-data-obs-path)
- [Template C: Custom Pipeline (User-Provided YAML)](#template-c-custom-pipeline-user-provided-yaml)
- [Guided Creation Without YAML](#guided-creation-without-yaml)
- [Template C2: Custom Operator Insertion](#template-c2-custom-operator-insertion)
- [Template D: Partial Pipeline (Start from Mid-Stage)](#template-d-partial-pipeline-start-from-mid-stage)
- [Pipeline State Tracking Template](#pipeline-state-tracking-template)
- [Polling Interval Reference](#polling-interval-reference)
- [Resource Specifications](#resource-specifications)

---

## YAML Structure

```yaml
pipeline:
  name: sim-teleop-cleaning        # Required: pipeline name (task-name prefix)
  workspace_id: <workspace_id>     # Optional: defaults to current CLI workspace
  inputs:                          # Required: initial sources; this built-in example uses one dataset
    - source_type: obs             # local | asset | obs
      obs_path: obs://<bucket>/raw/<episode-dir>/   # Required when source_type=obs
      data_source_type: h5         # Input format label (h5 | ros2 | umi); set operator/operator_id explicitly
      robot_type: a2d              # Optional: map to the operator's `robot` env enum, or ask the user
  output:
    asset_name: "<generated_output_name>" # Generate a short unique name before plan confirmation
  stages:                          # Required: stage list
    - id: convert-lerobotv3        # DAG label only (not a search keyword)
      operator: 数据转换--H5转LeRobotV3   # Exact Chinese operator name (or operator_id: exact asset_id)
      # params:                    # Optional: only `envs` and `inputs`
      #   envs: { <ENV_NAME>: <value> }
      #   inputs: [ { name: <INPUT_NAME>, url_path: obs://<bucket>/<dir>/ } ]
    - id: cleaning
      operator: 数据清洗           # Single cleaning operator with multiple sub-checks
      depends_on: [convert-lerobotv3]
    - id: evaluation
      depends_on: [cleaning]
      fail_fast: false             # Evaluation is advisory
      parallel_group:              # Parallel evaluation after cleaning (optional config mounts go in each member's params.inputs)
        - id: quality-eval
          operator: 数据集质量评测-LeRobot
        - id: diversity-eval
          operator: 数据集多样性评测-LeRobot
```

## Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `pipeline.name` | Yes | Pipeline name; prefix of every task name (`<pipeline_name>-<stage_id>-<MMDDHHmmss>`) |
| `pipeline.workspace_id` | No | Workspace ID; defaults to current CLI workspace (`cloudrobo workspace use --workspace-id <id>`) |
| `pipeline.inputs[]` | Yes | Initial datasets; multiple sources require unique IDs and explicit input_from bindings |
| `pipeline.inputs[].source_type` | Yes | `local` / `asset` / `obs` |
| `pipeline.inputs[].obs_path` | Conditional | Required when `source_type=obs` |
| `pipeline.inputs[].local_path` | Conditional | Required when `source_type=local` |
| `pipeline.inputs[].id` | Conditional | Unique source ID when multiple initial datasets; single unnamed input is input:default |
| `pipeline.inputs[].asset_id` / `version_id` | Conditional | Required when `source_type=asset` (registered dataset asset and version) |
| `pipeline.inputs[].asset_name` / `obs_path` | No (asset) | Verified name and version URL for asset input; may be resolved by CLI before execution |
| `pipeline.inputs[].data_source_type` | No | Input format label `h5` / `ros2` / `umi`; does **not** select the operator — set `operator`/`operator_id` explicitly (see [mapping](#data-source-type--suggested-conversion-operator)) |
| `pipeline.inputs[].robot_type` | No | Robot type; mapped to an enumerated value of the operator's `robot` env (if the operator declares one), otherwise ask the user |
| `pipeline.output.asset_name` | No | Selected final proc task's output_name; built-in template uses cleaning, custom workflows use output.from_stage |
| `pipeline.output.from_stage` | Conditional | Final proc data source; infer a unique data leaf, ask when multiple outputs remain |
| `stages[]` | Yes | Stage list |
| `stages[].id` | Yes | Unique ASCII stage label used by `depends_on` and task naming; DAG label only, not an operator search keyword |
| `stages[].kind` | No | Single task: proc (default) or eval. Guided authoring emits eval explicitly for a standalone evaluation; parallel_group implies eval-group |
| `stages[].operator` | Conditional | Exact Chinese marketplace operator name (e.g. `数据清洗`); mutually exclusive with `parallel_group`. Resolved by `list-publication-assets --name` and confirmed unique |
| `stages[].operator_id` | Conditional | Exact operator asset_id (alternative to `operator`); mutually exclusive with `parallel_group` |
| `stages[].operator_source` | No | `preset` (default) / `workspace` / `obs` → `--algo-type` / `task_config.algo_type` = `PRESET_ASSETS` / `WORKSPACE_ASSETS` / `OBS_ASSETS` (proc stages only; `dataset eval create-task` has no `--algo-type`) |
| `stages[].algo_path` | Conditional | Required when `operator_source=obs` — OBS path of the operator code |
| `stages[].job_local_path` | Conditional | Required when `operator_source=obs` — container mount path for the code |
| `stages[].image` | Conditional | Required when `operator_source=obs` — SWR image address |
| `stages[].algo_entrance` | Conditional | Required when `operator_source=obs` — startup command |
| `stages[].input_from[]` | No | Ordered data references: proc stage IDs or input:<id>; required to disambiguate multiple waiting dependencies/sources; eval accepts one |
| `stages[].depends_on[]` | No | Waiting stage IDs; defaults to previous stage without input_from; explicit data references imply their producer dependencies |
| `stages[].fail_fast` | No | Stage-level bool (not inside `params`); default `true` (a failed stage stops the pipeline). Evaluation stage: `false` (advisory, does not block TrainingReady output) |
| `stages[].parallel_group[]` | Conditional | Parallel member list; mutually exclusive with `operator`/`operator_id`. Each member is an object `{id, operator \| operator_id, params}`; cloud tasks can run concurrently and the next stage waits until all reach a terminal state; reserve/submit/resolve transactions remain sequential |
| `stages[].parallel_group[].id` | Yes (per member) | Member label; used in the member's task name |
| `stages[].parallel_group[].operator` / `operator_id` | Yes (one of) | Exact Chinese operator name or exact asset_id of the member |
| `stages[].parallel_group[].params` | No | Same shape as `stages[].params` |
| `robot_config` | Removed | No longer accepted at stage or member level; mount config directories (e.g. robot description `ROBOT_CONFIG_PATH`) via that evaluation's `params.inputs` |
| `stages[].params` | No | Operator overrides; only the two keys below are allowed |
| `stages[].params.envs` | No | Map of env name → value. Names must exist in the operator's `ext_metadata.environment_variables`; maps to the task_config `envs` string. Priority: `params.envs` > `environment_variables[].default` |
| `stages[].params.inputs[]` | No | Declaration form `{name, url_path}`; `name` must exist in the operator's current `ext_metadata.inputs`. At submit time each entry is expanded into the full `ext_metadata.inputs[]` element (copied as returned, only `url_path` replaced) inside the task_config `inputs` JSON-array string. Optional inputs are omitted by default |

**Execution normalization**: All steps enter one task graph and ready queue. `parallel_group`
is a compatible grouping syntax: members expand to ordinary task nodes, with member
overrides applied and references to the group expanded to waiting for all members.
`pipeline_state.py ready-tasks` exposes the same scheduling path for all nodes: dispatch
every ready node before polling, re-querying after each reserve/create/verify-ID/resolve.
The submission slot is released after the task ID is recorded, while cloud execution
continues. Existing YAML and Web grouping do not require migration. See
[unified scheduling](web-monitor.md#parallel-submission) for the complete command.

**Stage ordering**: Evaluation depends directly/transitively on cleaning output; eval-only
partial pipelines use verified externally cleaned input. A direct dependency is the usual
`depends_on: [cleaning]`; an inserted custom processing step can sit between them.

**Cleaning sub-checks**: the single `数据清洗` operator covers outlier detection, anomaly
detection, State-Action consistency, FK correction, base-frame alignment and blur-frame
detection. These are descriptive only — they are not pipeline.yaml keys. A custom cleaning
config is supplied via the operator's `CURATION_CONFIG_PATH` input when the operator
exposes it.

**Built-in vs Custom**:
- **Built-in**: `templates/sim-teleop-cleaning.yaml`; user triggers verbally, no YAML needed;
  user can override template fields
- **Custom**: User provides YAML or the guided authoring flow generates it from natural-language choices |

**No `type` field**: There is no type selector in pipeline.yaml. A custom-creation request
uses the guided flow; only an explicit built-in-template request selects the built-in template.

**Plan confirmation**: before any mutating operation (`create-asset` / `create-version` /
`import-asset` / `update-version` / `create-task`), show the resolved plan — operators
(name / asset_id / image), envs, inputs, specs, resource pool, output names and paths —
and wait for user confirmation.

---

## Use Case Mapping

### Data Source Type → Suggested Conversion Operator

Guide only — the conversion stage must set `operator`/`operator_id` explicitly.

| `data_source_type` | Source | Conversion Operator (exact name) | `--name` fragment |
|--------------------|--------|----------------------------------|-------------------|
| `h5` | H5 format (e.g., Guodi A2D) | `数据转换--H5转LeRobotV3` | `H5转LeRobotV3` |
| `ros2` | ROS2 bag format | `数据转换--ros转LeRobotV3` | `ros转LeRobotV3` |
| `umi` | UMI format | `数据转换--UMI转LeRobotV3` | `UMI转LeRobotV3` |

### Stage → Operator Discovery

| Stage `id` (label) | Operator (exact name) | Discovery command |
|--------------------|-----------------------|-------------------|
| `convert-lerobotv3` | see table above | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "<fragment>"` |
| `cleaning` | `数据清洗` | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "数据清洗"` |
| `quality-eval` | `数据集质量评测-LeRobot` | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "质量评测"` |
| `diversity-eval` | `数据集多样性评测-LeRobot` | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "多样性评测"` |

- Re-run discovery before every submission and use the current result (image, command,
  `environment_variables`, `inputs`).
- If the required operator is not found in the current region/marketplace, **stop and tell
  the user** — never silently substitute another operator.
- The `robot` env enum is operator-specific (e.g. ros conversion:
  `auto|galaxea_r1|galaxea_a1z|jaka|moz1|azureloong|ur5e`) — map `robot_type` to an
  enumerated value or ask the user.

### Source Type Processing

输入准备先按主文档的“Data Upload Routing 数据上传先用资产中心”加载 `huawei-cloud-cloudrobo-asset`，
使用该 skill 的 CLI 工作流；本地导入的上传由 import-asset 内部完成，不另找 OBS 工具。
以下表格是同一资产流程的命令参考；OBS 数据不重复上传，已有资产不重复创建。

| Source | Processing |
|--------|-----------|
| Registered asset | `cloudrobo asset list-assets --catalog-id <catalog_id> --type dataset --name "<name>"` (or use the given `asset_id`) → `cloudrobo asset list-versions --asset-id <id> --sort-key created_at --sort-dir desc --limit 1` → `cloudrobo asset show-version --asset-id <id> --version-id <vid>` |
| OBS path | `cloudrobo asset create-asset --catalog-id <id> --type dataset --name <n> --ext-metadata '{"annotation_status":true}'` + `create-version --asset-id <id> --url <obs_path>` → `show-version` |
| Local directory | `cloudrobo asset import-asset --catalog-id <id> --type dataset --name <n> --local-path <dir> --ext-metadata '{"annotation_status":true}'` → `show-version` |
| Not specified | **Must ask user** |

In every case, verify the exact version/path with `show-version`. Verified DRAFT can
proceed on supporting platforms/operators; do not prompt for publication by default. Only
an established downstream RELEASE requirement triggers publication confirmation. Summarize
all output version states and give one consolidated reminder at completion.

---

## Template A: Built-in Pipeline — Sim Data (Local Directory)

### Stage 0: Load Built-in Template

```
User input: "用仿真数据处理模板，数据在本地 /data/sim-raw/" (use sim data processing template, data in local /data/sim-raw/)
Parse result:
  pipeline_name:    sim-teleop-cleaning
  source_type:      local
  local_path:       /data/sim-raw/
  data_source_type: ros2      # inferred from "sim" (template supports Simulation: StarSea R1 / ROS2) — confirm with user
  robot_type:       r1        # inferred, confirm; maps to ros conversion env robot=galaxea_r1
  conversion operator: 数据转换--ros转LeRobotV3   # set explicitly, confirm
  output.asset_name: <confirmed TrainingReady dataset name>
```

> `data_source_type`/`robot_type` inferred from the template's supported data types are
> proposals, not decisions — confirm them (and the template's `h5`/`a2d` defaults when they
> apply) with the user in the execution plan before Stage 1.

### Stage 1: Upload & Register

先使用资产中心 `huawei-cloud-cloudrobo-asset` 的本地导入流程；以下 import-asset 已包含上传和资产/版本登记。
确认计划并处理打开监控偏好后再执行，不额外上传一次，也不在导入后再次注册同一数据。

```bash
# Get workspace catalog_id
cloudrobo workspace current

# Import local directory to OBS (capture asset_id / version_id from the output)
cloudrobo asset import-asset --catalog-id <catalog_id> --type dataset --name sim-raw-<MMDDHHmmss> --local-path /data/sim-raw/ --ext-metadata '{"annotation_status":true}'

# Check version status and OBS path
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>

# Only for an established downstream RELEASE requirement and confirmed publication:
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

Extract: `dataset_asset_id`, `dataset_version_id`, dataset OBS path

### Stage 2: Format Conversion (ROS2 → LeRobotV3)

```bash
# Discover the explicitly set conversion operator (数据转换--ros转LeRobotV3)
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "ros转LeRobotV3"

# Submit conversion task (no --wait); envs: robot=galaxea_r1 (confirmed)
cloudrobo dataset proc create-task --name "sim-teleop-cleaning-convert-lerobotv3-<MMDDHHmmss>" --algo-type PRESET_ASSETS --task-config '<json>'

# Wait for terminal state, then read the result
cloudrobo dataset proc wait-task --task-id <task_id> --timeout 300 --interval 15
cloudrobo dataset proc show-task --task-id <task_id>
# Extract: status, target_path, target_asset_id

# Resolve the output version for the next stage
cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc --limit 1
cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
```

- `wait-task` timed out while the status is still non-terminal → re-run `wait-task` and
  report progress; do **not** resubmit.
- `FAILED` / `DELETED` → diagnose with `cloudrobo dataset proc get-log --task-id <id>`, then
  (after user confirmation) create a **new** task.

### Stage 3: Data Cleaning

```bash
# Discover cleaning operator (数据清洗)
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "数据清洗"

# Submit cleaning task (input dataset_configs = conversion target_path / target_asset_id /
# <conversion output_name> / target_version_id; output_name = pipeline.output.asset_name)
cloudrobo dataset proc create-task --name "sim-teleop-cleaning-cleaning-<MMDDHHmmss>" --algo-type PRESET_ASSETS --task-config '<json>'

cloudrobo dataset proc wait-task --task-id <task_id> --timeout 300 --interval 15
cloudrobo dataset proc show-task --task-id <task_id>
# Extract: target_path (TrainingReady), target_asset_id

cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc --limit 1
cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
```

Same timeout / `FAILED` / `DELETED` handling as Stage 2.

### Stage 4: Evaluation (Parallel)

```bash
# Discover eval operators
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "质量评测"
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "多样性评测"

# Submit both eval tasks WITHOUT --wait (input = cleaning output; config mounts = each member's params.inputs)
cloudrobo dataset eval create-task --name "sim-teleop-cleaning-quality-eval-<MMDDHHmmss>" --task-config '<json>'
cloudrobo dataset eval create-task --name "sim-teleop-cleaning-diversity-eval-<MMDDHHmmss>" --task-config '<json>'
# Record both task_ids, then wait for each
cloudrobo dataset eval wait-task --task-id <quality_task_id> --timeout 300 --interval 15
cloudrobo dataset eval wait-task --task-id <diversity_task_id> --timeout 300 --interval 15

# Get reports (--file-name = target_report_path from show-task without the obs://<bucket>/ prefix)
cloudrobo dataset eval show-task --task-id <quality_task_id>
cloudrobo dataset eval get-preview --task-id <quality_task_id> --file-name <target_report_path-without-bucket>
cloudrobo dataset eval show-task --task-id <diversity_task_id>
cloudrobo dataset eval get-preview --task-id <diversity_task_id> --file-name <target_report_path-without-bucket>
```

Evaluation stage has `fail_fast: false` — a failed eval task is reported (diagnose with
`cloudrobo dataset eval get-log --task-id <id>`) but does not block the TrainingReady output.

### Stage 5: Output

```
TrainingReady dataset: <pipeline.output.asset_name>
TrainingReady data path: <cleaning target_path>
TrainingReady asset/version: <cleaning target_asset_id> / <cleaning target_version_id>
Conversion task ID: <id>
Cleaning task ID: <id>
Quality eval task ID: <id>, report: <link>
Diversity eval task ID: <id>, report: <link>
```

---

## Template B: Built-in Pipeline — Teleop Data (OBS Path)

### Stage 0: Load Built-in Template

```
User input: "用遥操数据处理模板，数据在 obs://bucket/teleop/episode-001/" (use teleop data processing template, data at obs://bucket/teleop/episode-001/)
Parse result:
  pipeline_name:    sim-teleop-cleaning
  source_type:      obs
  obs_path:         obs://bucket/teleop/episode-001/
  data_source_type: h5        # template default (Teleop: Guodi A2D H5) — confirm with user
  robot_type:       a2d       # template default — confirm with user
  conversion operator: 数据转换--H5转LeRobotV3   # set explicitly, confirm
  output.asset_name: <confirmed TrainingReady dataset name>
```

### Stage 1: Register OBS Asset

```bash
cloudrobo workspace current

# Capture asset_id / version_id from the outputs
cloudrobo asset create-asset --catalog-id <catalog_id> --name "teleop-ep001-<MMDDHHmmss>" --type dataset --ext-metadata '{"annotation_status":true}'
cloudrobo asset create-version --asset-id <asset_id> --url "obs://bucket/teleop/episode-001/"
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>

# Only for an established downstream RELEASE requirement and confirmed publication:
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

Stages 2–5: Same as Template A, but the conversion stage uses the explicitly set
`数据转换--H5转LeRobotV3` (discover with `--name "H5转LeRobotV3"`); read its `envs`
from the current `ext_metadata.environment_variables` and map `robot_type` only if a
`robot` env is declared.

---

## Template C: Custom Pipeline (User-Provided YAML)

User provides a custom `pipeline.yaml` with modified stages or params:

```yaml
pipeline:
  name: custom-cleaning-pipeline
  inputs:
    - source_type: obs
      obs_path: obs://my-bucket/raw-data/
      data_source_type: umi
      robot_type: a2d
  output:
    asset_name: custom-cleaned-dataset
  stages:
    - id: convert-lerobotv3
      operator: 数据转换--UMI转LeRobotV3
      params:
        inputs:                          # optional mount (omit for default)
          - name: DATA_CONFIG_PATH
            url_path: obs://my-bucket/config/convert-manifest/
    - id: cleaning
      operator: 数据清洗
      depends_on: [convert-lerobotv3]
      params:
        inputs:                          # optional mount: custom cleaning config
          - name: CURATION_CONFIG_PATH   # (e.g. a config that disables blur-frame detection)
            url_path: obs://my-bucket/config/cleaning-config/
    - id: evaluation
      depends_on: [cleaning]
      fail_fast: false
      parallel_group:                    # only quality eval, no diversity
        - id: quality-eval
          operator: 数据集质量评测-LeRobot
          params:
            inputs:                      # optional robot description mount
              - name: ROBOT_CONFIG_PATH
                url_path: obs://my-bucket/config/robot-desc/
```

> **Inputs mounts**: `DATA_CONFIG_PATH` (custom convert manifest), `CURATION_CONFIG_PATH`
> (custom cleaning config), `ROBOT_CONFIG_PATH` (robot description for eval) are known
> operator inputs (reference — always re-read the current `ext_metadata.inputs`). All are
> optional — in pipeline.yaml declare each as `name` + `url_path`; at submission the skill
> expands each into the **complete operator input element** (from `ext_metadata.inputs`)
> with `url_path` set. Omit `inputs` for the default behavior (auto-compatible).

Skill parses this YAML directly — no template loading. Executes stages as declared.

---

## Guided Creation Without YAML

For “帮我创建一条自定义管线” or a requested revision, follow
[Guided Custom Pipeline Authoring](custom-pipeline-authoring.md). Agent collects choices,
maintains a JSON draft and uses the standard-library helper to emit existing-schema YAML:

```bash
python3 scripts/custom_pipeline.py check --input /path/to/choices.json
python3 scripts/custom_pipeline.py export --input /path/to/choices.json --output-dir /path/to/new-pipeline
```

Outputs: pipeline.yaml, pipeline.draft.json, pipeline-preview.md. No platform writes or
monitor run initialization occur. Incomplete drafts can be saved with --allow-incomplete;
schema/dependency errors still block export. Resources, partial-stage handoff and custom
step roles are companion authoring metadata, not additions to params. Keep the companion
JSON when executing the generated YAML so these choices carry into Stage 0.

---

## Template C2: Custom Operator Insertion

This is one optional example, not the structure imposed on all custom workflows.
Workspace algorithm assets can form the entire workflow or be mixed with preset
operators at any compatible position. For instance, the following smaller workflow
converts H5 and then uses a workspace algorithm, without cleaning or evaluation:

```yaml
pipeline:
  name: custom-normalize
  inputs:
    - source_type: obs
      obs_path: obs://example-bucket/raw/
      data_source_type: h5
  output:
    asset_name: normalized-data
    from_stage: normalize
  stages:
    - id: convert
      operator: 数据转换--H5转LeRobotV3
    - id: normalize
      operator: 我的格式标准化  # illustrative user-selected name; verify it in the workspace
      operator_source: workspace
      depends_on: [convert]
```

Resolve the exact workspace asset and its input/output contract before execution;
the example does not establish that this asset exists. Other combinations can use
only preset operators or only workspace algorithms. The full example below shows
an additional custom step between cleaning and evaluation.

Insert a user-provided operator as a stage, either from workspace algorithm assets
(`operator_source: workspace`) or from OBS code (`operator_source: obs`):

```yaml
pipeline:
  name: pipeline-with-custom-operator
  inputs:
    - source_type: obs
      obs_path: obs://my-bucket/raw-data/
      data_source_type: h5
      robot_type: a2d
  output:
    asset_name: custom-op-cleaned-dataset
    from_stage: my-custom-filter
  stages:
    - id: convert-lerobotv3
      operator: 数据转换--H5转LeRobotV3
    - id: cleaning
      operator: 数据清洗
      depends_on: [convert-lerobotv3]
    # Insert a custom operator between cleaning and evaluation
    - id: my-custom-filter
      operator_id: <custom_operator_asset_id>   # exact asset_id
      # operator: <exact operator name>         # or exact name → confirm unique
      operator_source: workspace          # workspace | obs | preset (default)
      depends_on: [cleaning]
      # For operator_source: obs, add:
      # algo_path: obs://my-bucket/code/my-filter/
      # job_local_path: <container mount path>
      # image: <swr image address>
      # algo_entrance: <startup command>
    - id: evaluation
      depends_on: [my-custom-filter]      # evaluation now depends on the custom stage
      fail_fast: false
      parallel_group:
        - id: quality-eval
          operator: 数据集质量评测-LeRobot
        - id: diversity-eval
          operator: 数据集多样性评测-LeRobot
```

**Operator source resolution:**

| `operator_source` | algo_type (`--algo-type`) | Discovery | Required extra fields |
|-------------------|---------------------------|-----------|----------------------|
| `preset` (default) | `PRESET_ASSETS` | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing"\|"Data Evaluation" --name "<name>"` | none |
| `workspace` | `WORKSPACE_ASSETS` | `cloudrobo asset list-assets --catalog-id <id> --type algorithm --tags "Data Processing"\|"Data Evaluation" --name "<name>"` | none (fields from asset ext_metadata) |
| `obs` | `OBS_ASSETS` | user-provided | `algo_path`, `job_local_path`, `image`, `algo_entrance` |

Choose the `--tags` value by operator type: `Data Processing` for processing operators,
`Data Evaluation` for evaluation operators. `--algo-type` must equal `task_config.algo_type`;
`dataset eval create-task` has no `--algo-type` option.

The custom operator consumes its ordered `input_from` sources as `dataset_configs` and produces
`target_path`/`target_asset_id` for the next stage. It may declare `ext_metadata.inputs`
(optionally) resolved with the same `inputs` logic.

---

## Template D: Partial Pipeline (Start from Mid-Stage)

User says: "我数据已转换好，直接清洗和评测" (data already converted, clean and evaluate directly)

```
Parse result:
  start_stage: 3 (cleaning)
  required input: conversion target_path, target_asset_id, target_version_id, asset name (<conversion output_name>)
  If not provided → ask user
```

Execute Stage 3 → 4 → 5 only.

---

## Pipeline State Tracking Template

New runs use `~/.cloudrobo/pipeline-runs/<run_id>/state.json` (schema v2). Initialize
from the confirmed JSON plan with `pipeline_state.py init`. Every write goes through the
shared locked/CAS script; never edit the JSON directly. Preserve configurations under
`tasks/<task_id>.json` and all earlier task IDs in `attempts`. See
[Web Monitor](web-monitor.md) for complete commands and [the plan example](../templates/monitor-plan.example.json).
Legacy `<run_id>.checkpoint.json` files can be imported read-only.
The following is a field excerpt, not a file to write manually; init generates all stage kinds,
fail_fast flags, plan/upload/output bookends and event bookkeeping.

```json
{
  "schema_version": 2,
  "version": 1,
  "status": "RUNNING",
  "orchestrator": {"heartbeat_at": "<ISO-8601>"},
  "pending_action": null,
  "awaiting_decision": null,
  "run_id": "<run_id>",
  "pipeline_name": "sim-teleop-cleaning",
  "current_stage": "cleaning",
  "workspace_id": "<workspace_id>",
  "inputs": {
    "source_type": "obs",
    "obs_path": "obs://<bucket>/raw/<episode-dir>/",
    "data_source_type": "h5",
    "robot_type": "a2d"
  },
  "output": {
    "asset_name": "<pipeline.output.asset_name>"
  },
  "stages": {
    "convert-lerobotv3": {
      "task_id": "<task_id>",
      "status": "SUCCEEDED",
      "output_name": "<conversion output_name>",
      "target_path": "<conversion target_path>",
      "target_asset_id": "<target_asset_id>",
      "target_version_id": "<target_version_id>",
      "attempts": []
    },
    "cleaning": {
      "task_id": "<task_id>",
      "status": "RUNNING",
      "output_name": "<cleaning output_name>",
      "target_path": null,
      "target_asset_id": null,
      "target_version_id": null,
      "attempts": [{ "task_id": "<failed task_id>", "status": "FAILED" }]
    },
    "evaluation": {
      "members": {
        "quality-eval": { "task_id": null, "status": null, "target_report_path": null, "attempts": [] },
        "diversity-eval": { "task_id": null, "status": null, "target_report_path": null, "attempts": [] }
      }
    }
  }
}
```

---

## Polling Interval Reference

| Stage | CLI Command | Interval | Terminal State | Timeout |
|-------|-----------|----------|---------------|---------|
| Conversion | `cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15` | 15s | `SUCCEEDED`/`FAILED`/`DELETED` | 5min per segment; repeat + heartbeat |
| Cleaning | `cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15` | 15s | `SUCCEEDED`/`FAILED`/`DELETED` | 5min per segment; repeat + heartbeat |
| Evaluation (per member) | `cloudrobo dataset eval wait-task --task-id <id> --timeout 300 --interval 15` | 15s | `SUCCEEDED`/`FAILED`/`DELETED` | 5min per segment; repeat + heartbeat |

If `wait-task` returns on timeout while the task is still non-terminal, re-run `wait-task`
(report progress) — do not resubmit. `FAILED`/`DELETED` → diagnose with `get-log`, then
create a new task after user confirmation.

---

## Resource Specifications

**Default (non-RAY) tasks** — 4c8g:

| Task Type | worker_spec | head_spec | worker_num |
|-----------|-------------|-----------|------------|
| Conversion | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` | `{cpu: 0, memory: 0, gpu: 0, npu: 0}` | 1 |
| Cleaning | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` | `{cpu: 0, memory: 0, gpu: 0, npu: 0}` | 1 |
| Evaluation (per task) | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` | `{cpu: 0, memory: 0, gpu: 0, npu: 0}` | 1 |

`head_spec` / `worker_num` are not required by the CLI eval validator but are included in
the eval template (see `references/task-config-catalog.md`).

**Public pool fallback**: 4c8g may stall at POD_PENDING on the public pool; fall back to
2c4g (`{cpu: 2, memory: 4, gpu: 0, npu: 0}`). `DEDICATED_POOL` additionally needs
`resource_id` / `dedicated_pool_name` (see `references/task-config-catalog.md`).

**RAY tasks** (`CCE_RAY` / `RAY`):

| Component | spec | Value |
|-----------|------|-------|
| head | `head_spec` | `{cpu: 2, memory: 4, gpu: 0, npu: 0}` (2c4g) |
| worker | `worker_spec` | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` (4c8g) |
| worker count | `worker_num` | `2` |

> All data processing tasks default to 4c8g. Public pool: fall back to 2c4g. RAY tasks:
> head 2c4g + workers 4c8g × 2. Parallel group total = parallel_count × spec.

For branch A/B → merge C, control-only dependencies and backward-compatible single-source rules, see the
[multi-input authoring example](custom-pipeline-authoring.md#multi-input). Single-dataset branches are recommended,
not a hard proc limit. Multi-input requires an explicitly selected operator that supports it; eval remains single-input.
