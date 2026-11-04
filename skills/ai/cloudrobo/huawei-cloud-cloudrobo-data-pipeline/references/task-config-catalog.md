# Operator Field Mapping & Task Config Reference

## Operator Field Mapping

Extract fields from `list-publication-assets` query results and map to task_config:

| Operator Field | task_config Field | Description |
|---------------|-------------------|-------------|
| `asset_id` | `algo_id` | Algorithm ID |
| `name` | `algo_name` | Algorithm name |
| `ext_metadata.command` | `algo_entrance` | Startup command |
| `ext_metadata.engine.image_url` | `image` | Image address |
| `ext_metadata.environment_variables` | `envs` (some operators have this) | Environment variables, string field |
| `ext_metadata.inputs` | `inputs` (optional) | Input mounts (config/model paths) declared by the operator, JSON-array string field |

> **catalog_id**: Uses the workspace's catalog_id (from `workspace current`), NOT the
> operator's `catalog_id`.

> **No `params` / hyperparams field**: operator `ext_metadata` keys are `engine`, `inputs`,
> `command`, `outputs`, `resource`, `environment_variables` (not every operator has all of
> them). There is no `ext_metadata.hyperparams` and no top-level task_config `params`
> field. Operator behaviour is tuned only through `envs` and `inputs`.
>
> **Override priority (envs)**: pipeline.yaml stage `params.envs` value > operator
> `environment_variables[].default`.

> **`algo_entrance` for `PRESET_ASSETS`**: copy the operator's `ext_metadata.command`
> unchanged. Do not try to change operator behaviour by editing `algo_entrance` (e.g.
> adding an `export ROBOT_CONFIG=/` prefix); use `envs` / `inputs` instead. Changes to the
> entrance command belong in the operator asset version's `ext_metadata.command`, not in
> task_config.

## Operator Inputs Mount (`ext_metadata.inputs`)

Operators declare optional/required external inputs in
`ext_metadata.inputs`. An input element can contain the following fields (not every
operator returns all of them — e.g. `label` / `required` may be absent):

| Field | Meaning |
|-------|---------|
| `name` | Input identifier, e.g. `DATA_CONFIG_PATH` / `CURATION_CONFIG_PATH` / `ROBOT_CONFIG_PATH` / `DESENS_MODEL_PATH` |
| `label` | Display name |
| `description` | What the input is for |
| `required` | `true` = must be provided; `false` = optional (omit → default behavior) |
| `input_type` | `DATA_CONFIG` (config file dir) / `MODEL` (model/robot description dir) / `DATA` / `MODEL_CONFIG` |
| `url_path` | Built-in default path if any (may be an `obs://` system path or a platform-internal path — copy as returned); user-supplied values must be `obs://` paths |
| `access_method` | `env` — injected as an environment variable into the operator container |

**Known operator inputs (reference — always re-read the current `ext_metadata.inputs`):**

| Operator | Input name | required | input_type | Meaning |
|----------|-----------|----------|------------|---------|
| 数据脱敏 | `DESENS_MODEL_PATH` | true | MODEL | Model weights dir; `url_path` is built-in — no user action |
| 数据清洗 | `CURATION_CONFIG_PATH` | false | DATA_CONFIG | Custom cleaning config dir |
| 数据转换 ros→V3/V21, H5→V3, UMI→V3 | `DATA_CONFIG_PATH` | false | DATA_CONFIG | Custom manifest config dir |
| 评测 质量/多样性 | `ROBOT_CONFIG_PATH` | false | MODEL | Robot description dir (robots.yaml / URDF) |

> This table is a reference only. Operator versions differ by region and over time, and an
> operator may declare no `inputs` at all (`ext_metadata.inputs` absent or `null`; e.g. in
> cn-southwest-2 the ros conversion and LeRobot evaluation operators currently declare no
> inputs) — in that case omit the `inputs` field. Always use the inputs returned by the
> **current** query.

**Compatibility rule (old/new auto-compatible):**
- `required: false` inputs are **optional** — if the user does not provide a path, omit the
  `inputs` field entirely and the operator falls back to the old behavior (built-in
  manifest / `robot` env / dataset `config.yaml`).
- `required: true` inputs with a built-in `url_path` need no user action (the platform
  mounts the built-in path automatically).
- **Never prompt for a `required: false` input by default** — only ask when the user
  explicitly wants custom config, or when the operator would otherwise fail (e.g. eval on
  an unsupported robot type → provide `ROBOT_CONFIG_PATH` if the operator declares it).

**task_config `inputs` structure (when provided):**

> `inputs` is a **string field** — a JSON array (like `dataset_configs` / `envs`). Each
> element is the operator's `ext_metadata.inputs[]` element **copied as returned by the
> current query** (do not add or strip fields), with only `url_path` set to the
> user-selected `obs://` path. Never use `obs_path` as an inputs key.

```text
"inputs": "[{\"name\":\"DATA_CONFIG_PATH\",\"label\":\"自定义转换配置\",\"required\":false,\"url_path\":\"obs://bucket/config/convert-manifest/\",\"input_type\":\"DATA_CONFIG\",\"description\":\"自定义manifest配置文件目录（可选）\",\"access_method\":\"env\"}]"
```

> The platform mounts `url_path` into the operator container and exposes it via the input's
> `access_method` (`env`). Omit the whole `inputs` field when no custom mounts are needed.
>
> **pipeline.yaml declaration form**: a stage declares inputs as
> `params.inputs: [{name: <NAME>, url_path: obs://...}]`. At submit time each declared
> entry is expanded into the full current `ext_metadata.inputs[]` element with `url_path`
> replaced. A declared `name` that the operator does not expose is an error — tell the user.

### Input priority

```text
User-provided inputs[].url_path > operator built-in url_path > dataset directory config (config.yaml/manifest.yaml) > robot env default
```

<a id="manifest-config-names"></a>
### Manifest 配置文件名与候选查找

数据集不通用要求附带 YAML：可使用算子支持的内置 `robot` 环境变量/默认配置、数据集已有配置或外部配置挂载。
先按当前算子声明选择实际配置来源；使用内置配置时无需查找或补造文件。manifest 类别本身也不使外部 YAML
或评测配置挂载必填。**只有确定要从目录读取 YAML 配置时**，才推荐 `manifest.yaml`、其次
`manifest.yml` 并按下述方式查找候选；算子实际支持的名称和读取方式需按当前版本核实。

- 先按当前算子的配置优先级确定实际生效来源：配置挂载目录、内置配置或数据集目录；不要求每处都放一份。
- 用户已明确指定配置文件时先核实该文件；未指定时，Agent 在生效目录的第一层依次查找
  `manifest.yaml` → `manifest.yml` → 其他 `.yaml` / `.yml` 候选，其他候选按文件名排序列出。
  这是 **Agent 查找候选的顺序**，不代表算子已经实现同样的自动回退逻辑。
- 缺少推荐文件名不能单独作为失败依据，例如 `h5_a2d_fps30.yaml` 仍可作为候选。
  核对其内容用途，并用当前算子元数据、版本说明或源码确认实际文件名/显式路径的读取支持后再执行。
  多个候选用途不明确时请用户选择，不因排序靠前就随意采用，也不把普通 YAML 文件都当成 manifest。
- `inputs[].url_path` 仍按算子声明传目录；不擅自改传文件路径或新增算子未声明的选择参数。
  `import-asset` 保留文件名及相对目录，不会替用户查找或改名。
- 读取规则未核实时说明待确认项，不断言“缺少 manifest.yaml 必然失败”或“其他 YAML 会自动被读取”。
  只有确认当前版本固定要求某个文件名时才按该要求处理；需要适配时使用临时上传副本，保留用户原文件。

## Discovery Commands by Stage

| Stage | Discovery Command | Tags Filter |
|-------|------------------|-------------|
| Stage 2: Conversion | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "H5转LeRobotV3"` (or `ros转LeRobotV3` / `UMI转LeRobotV3`) | `Data Processing` |
| Stage 3: Cleaning | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "数据清洗"` | `Data Processing` |
| Stage 4: Evaluation | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "质量评测"` / `--name "多样性评测"` | `Data Evaluation` |

> Processing operators have `sub_type` `data_processing`; evaluation operators have
> `sub_type` `data_evaluating`. Match the result against the stage's exact `operator`
> name (or `operator_id`). Stage `id`s (`convert-lerobotv3`, `cleaning`, `quality-eval`,
> `diversity-eval`) are DAG labels only — they are not search terms.

### data_source_type → Expected Conversion Operator (guidance only)

`data_source_type` is a format label. It does **not** select the operator automatically —
set the stage `operator` (or `operator_id`) explicitly. The table below is guidance for
choosing it:

| `data_source_type` | Expected operator (`operator`) | `--name` fragment |
|--------------------|-------------------------------|-------------------|
| `h5` | 数据转换--H5转LeRobotV3 | `H5转LeRobotV3` |
| `ros2` | 数据转换--ros转LeRobotV3 | `ros转LeRobotV3` |
| `umi` | 数据转换--UMI转LeRobotV3 | `UMI转LeRobotV3` |

> **Operator not found → stop**: if the required operator is not returned in the current
> region/marketplace, stop and tell the user. Never silently substitute another operator.
>
> **`robot` env values are operator-specific**: e.g. 数据转换--ros转LeRobotV3 accepts
> `auto | galaxea_r1 | galaxea_a1z | jaka | moz1 | azureloong | ur5e` (read the enum from
> the current `environment_variables[].description`). Map the pipeline `robot_type` to an
> enumerated value, or ask the user if there is no match.

> **Dynamic discovery only — query fresh every time**: Never hardcode operator asset IDs
> and **never reuse operator info (image/algo_id/command/inputs) from a previous run**.
> Platform updates operator assets (new image versions, fixed commands); a stale image can
> silently fail. Re-run `list-publication-assets` before every task submission and extract
> fields from the **current** result. If multiple matches, ask user to select; if no match,
> stop and list similar operators for the user.

## proc-task task_config Template (Conversion / Cleaning)

The example below uses `PRESET_ASSETS` with platform-managed `BUILD_IN_ASSET` output.
Required and conditional fields are listed under [Required Fields](#required-fields-cli-validator).
`envs` / `inputs` are optional and added only when needed.

```json
{
  "name": "<pipeline_name>-convert-lerobotv3-<MMDDHHmmss>",
  "algo_type": "PRESET_ASSETS",
  "algo_name": "<operator name>",
  "algo_entrance": "<operator ext_metadata.command>",
  "image": "<operator ext_metadata.engine.image_url>",
  "algo_id": "<operator asset_id>",
  "catalog_id": "<workspace catalog_id>",
  "resource_pool_type": "PUBLIC_POOL",
  "cluster_type": "CCE",
  "task_framework_type": "K8S",
  "dataset_configs": "[{\"obs_path\":\"obs://bucket/path/\",\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<id>\",\"asset_name\":\"<name>\",\"version_id\":\"<vid>\"}]",
  "output_type": "BUILD_IN_ASSET",
  "output_name": "<output asset name>",
  "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
  "worker_spec": {"cpu": 4, "memory": 8, "gpu": 0, "npu": 0},
  "worker_num": 1,
  "evs_spec": 0
}
```

> Default task and new output names follow `<pipeline_name>-<stage_id>-<MMDDHHmmss>`;
> parallel evaluation tasks use the member ID. Suggest names with
> `custom_pipeline.py suggest-names --pipeline-name teleop --stage convert --stage clean`.
> No random suffix; same-second collisions use short ordinals. Verify same-name assets
> in the selected catalog before confirmation. The complete name including timestamp/ordinal
> must fit 64 characters; shorten pipeline/stage names explicitly, never silently truncate.
> Preserve explicit legal names and confirmed names on checks/resume. A proc output_name
> comes from authoring.output_names, or pipeline.output.asset_name for the final selected
> output stage; after a retry, use the new submitted config and verified artifact name.

### Output Location by Output Type

| output_type | output_path | Actual output source |
|---|---|---|
| `BUILD_IN_ASSET` | Omit from newly generated task_config; do not invent an OBS path | `show-task.target_path`, verified against the exact output version |
| `UDF_OBS_ASSET` | Required; use the user's confirmed OBS destination | The confirmed destination and actual task result |

For a user-selected OBS output, change the example's output fields to:

```json
{
  "output_type": "UDF_OBS_ASSET",
  "output_path": "<user-confirmed obs:// output directory>",
  "output_name": "<confirmed output name>"
}
```

This is a field replacement fragment, not a complete task_config. Existing task records
retain the configuration actually submitted for traceability.

### Artifact Passing Between Stages

**Stage 2 → Stage 3** (conversion → cleaning):

1. After the conversion task is `SUCCEEDED`, `cloudrobo dataset proc show-task --task-id <id>`
   provides `target_path` and `target_asset_id`.
2. Get the newest version of the output asset:

   ```bash
   cloudrobo asset list-versions --asset-id <conversion target_asset_id> --sort-key created_at --sort-dir desc --limit 1
   cloudrobo asset show-version --asset-id <conversion target_asset_id> --version-id <version_id>
   ```

3. Verify the exact version status/path with `show-version`. Supported `DRAFT` inputs
   proceed without publication. Only when the platform/operator explicitly requires RELEASE,
   or a failure is verified as a release-state restriction, ask before publishing with
   `cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE`.
   Do not treat every non-RELEASE state or every task failure as a publication requirement.
4. Construct the cleaning task's `dataset_configs` entry:

```json
{
  "obs_path": "<conversion target_path>",
  "dataset_type": "BUILD_IN_ASSET",
  "asset_id": "<conversion target_asset_id>",
  "asset_name": "<conversion output_name>",
  "version_id": "<version_id from list-versions>"
}
```

**Stage 3 → Stage 4** (cleaning → evaluation):

Verify the cleaning output version with `list-versions` / `show-version`, then set the eval
task's top-level `dataset_type: BUILD_IN_ASSET`, `dataset_id` = cleaning `target_asset_id`,
`dataset_name` = `<cleaning output_name>`, and `dataset_path` = cleaning `target_path`.
Also send one `dataset_configs` entry with the same asset/name/path/type and the exact
cleaning `target_version_id` as its `version_id`; verification in local state alone is insufficient.

### Custom Operator Sources (自定义算子来源)

A stage operator can come from three sources, selected by the stage `operator_source` and
mapped to `algo_type`. For proc tasks, `create-task --algo-type <value>` overrides
`task_config.algo_type`, so keep both identical. `dataset eval create-task` has no
`--algo-type` option.

| `operator_source` | algo_type | Operator source | Discovery | Required fields |
|-------------------|-----------|----------------|-----------|-----------------|
| `preset` (default) | `PRESET_ASSETS` | Platform built-in | `list-publication-assets --type algorithm` | `algo_id`/`algo_name`/`algo_entrance`/`image` from asset ext_metadata |
| `workspace` | `WORKSPACE_ASSETS` | Workspace algorithm asset (custom operator) | `list-assets --catalog-id <id> --type algorithm --tags "Data Processing"` | same as preset (from workspace asset ext_metadata) |
| `obs` | `OBS_ASSETS` | OBS code/image, no asset registration | user-provided | `algo_path`, `job_local_path`, `algo_entrance`, `image`; `algo_id` not required (valid UUID if provided) |

**WORKSPACE_ASSETS example** (custom operator registered as a workspace asset; other
fields as in the proc template):

```jsonc
{
  "algo_type": "WORKSPACE_ASSETS",
  "algo_id": "<workspace algo asset_id>",
  "algo_name": "my-custom-operator",
  "algo_entrance": "python main.py",
  "image": "swr.cn-north-7.myhuaweicloud.com/cloudrobo/my-operator:1.0",
  "catalog_id": "<workspace catalog_id>"
  // ... remaining required fields as in the proc template
}
```

**OBS_ASSETS example** (algorithm code on OBS, requires mount; other fields as in the proc
template):

```jsonc
{
  "algo_type": "OBS_ASSETS",
  "algo_path": "obs://bucket/config/operator-config/",
  "job_local_path": "/home/user/config/",
  "algo_entrance": "<command>",
  "image": "<image_url>",
  "algo_id": "<valid-uuid-if-provided>"
  // ... remaining required fields as in the proc template
}
```

> `algo_path` = OBS algorithm code/config path; `job_local_path` = container mount path.
> When `algo_type=OBS_ASSETS`, both `algo_path` and `job_local_path` are required.
> Custom operators (workspace/OBS) may also declare `ext_metadata.inputs`; resolve
> them with the same `inputs` field logic.

## eval-task task_config Template (Evaluation)

Evaluation tasks use top-level dataset fields **and** one `dataset_configs` entry with the
exact input version. The two representations must describe the same dataset.
`envs` and operator `inputs` are optional; the basic example omits them:

```jsonc
{
  "name": "<pipeline_name>-quality-eval-<MMDDHHmmss>",
  "algo_name": "<eval operator name>",
  "algo_entrance": "<operator ext_metadata.command>",
  "image": "<operator ext_metadata.engine.image_url>",
  "algo_id": "<operator asset_id>",
  "dataset_type": "BUILD_IN_ASSET",
  "dataset_id": "<cleaning target_asset_id>",
  "dataset_name": "<cleaning output_name>",
  "dataset_path": "<cleaning target_path>",
  "dataset_configs": "[{\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<cleaning target_asset_id>\",\"asset_name\":\"<cleaning output_name>\",\"obs_path\":\"<cleaning target_path>\",\"version_id\":\"<cleaning target_version_id>\"}]",
  "resource_pool_type": "PUBLIC_POOL",
  "worker_spec": {"cpu": 4, "memory": 8, "gpu": 0, "npu": 0}
}
```

> **`robot_config` 已移除**：评测 task_config 不再包含该字段，不要发送。机器人描述（robots.yaml /
> URDF）等配置目录只通过下方 `inputs` 挂载传入。
>
> **`inputs` (optional)**: copy the operator's current `ext_metadata.inputs[]` element and
> set `url_path` to the user-selected OBS path. For evaluation, `ROBOT_CONFIG_PATH` (when the
> operator declares it) mounts a directory containing `robots.yaml`/URDF — provide it when
> the selected metrics need it or the task fails with `ROBOT_CONFIG environment variable is
> not set`. Omit `inputs` entirely for the operator's built-in/default configuration.
> Resolve each evaluation member's mounts independently (pipeline `params.inputs`); never
> reuse another member's directory by default.

### eval-task Field Differences from proc-task

| Field | proc-tasks | eval-tasks |
|-------|-----------|------------|
| Dataset input | `dataset_configs` (JSON string array, multiple) | Matching top-level `dataset_type`/`dataset_id`/`dataset_name`/`dataset_path` plus single-item `dataset_configs`; assets require `version_id` |
| Config files | Optional `inputs` mounts | Optional `inputs` mounts (e.g. robot description `ROBOT_CONFIG_PATH`); `robot_config` removed |
| Deletion granularity | Single (`delete-task --task-id`) | Single (`delete-task --task-id`) |
| Resource usage in local Web | Not exposed; inspect CloudRobo Console | Not exposed; inspect CloudRobo Console |
| Report preview | Not supported | Supported (`get-preview --file-name [--is-download]`) |

> `dataset_id` is required when `dataset_type` is `BUILD_IN_ASSET`.

<a id="dataset-version-handoff"></a>
### 数据集版本交接与平台克隆

按已确认的后端契约，创建 proc/eval 任务时，资产输入都传 `dataset_configs[].version_id`。
`dataset_configs` 沿用 JSON 数组字符串；proc 可多项，eval 恰好一项，并保留原有顶层
`dataset_type/dataset_id/dataset_name/dataset_path`，两处类型、资产 ID、名称和路径必须一致。
版本使用真实版本 ID，不是版本显示名称；不增加猜测的顶层 `dataset_version_id` 字段。
直接 OBS 输入使用 `UDF_OBS_ASSET`，只传路径和类型，不补造资产或版本。管线按原规则先登记后使用资产输入。

- 优先使用本次上传/上游任务已核实的确切版本。任务没返回版本时，查询版本列表并用 show-version
  核对本次输出路径；不能不加核实就取最新版本，克隆/重试也不能切到后来新增的版本。
- 首次创建后，用 show-task 回读数据集配置，核对资产、版本和路径是否被平台完整保存；CLI/SDK 能透传
  不等于后端已支持/落库。后端版本契约尚未上线或回读缺失时明确报告，不以“创建成功”宣称克隆已可用。
- 历史任务缺版本不会因升级 skill 自动修复。确认原输入版本后，可按平台支持的 copy-task 覆盖配置或
  重新创建；不得猜最新版本、删除原任务或只改本地记录假装修复了平台任务。
- 内网验证：分别创建处理和评测任务，回读并使用 Console 克隆；核对克隆仍使用相同资产与确切版本。
  再增加该资产的新版本重复克隆，确认未切换；多输入处理逐项检查。直接 OBS 输入不要求资产版本。

CLI/SDK 当前 JSON 传输路径无需新增命令行参数；旧客户端可能不检查嵌套 version_id，不能用其校验通过
代替上述检查。skill 的本地 reserve-task 和 Web 提交会检查版本；Web 平台访问继续使用 SDK，Agent 继续用 CLI。

## Required Fields (CLI validator)

The CLI validates task_config before submission; a missing or empty required field fails
with a validation error.

| Task | Required fields | Conditional |
|------|-----------------|-------------|
| proc | `name`, `algo_type`, `algo_name`, `algo_entrance`, `image`, `catalog_id`, `resource_pool_type`, `cluster_type`, `task_framework_type`, `dataset_configs`, `output_type`, `output_name`, `head_spec`, `worker_spec`, `worker_num`, `evs_spec` | `algo_id` unless `algo_type=OBS_ASSETS`; `algo_path` + `job_local_path` when `OBS_ASSETS`; `output_path` when `output_type=UDF_OBS_ASSET` |
| eval | `name`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `dataset_type`, `dataset_name`, `dataset_path`, `dataset_configs`, `resource_pool_type`, `worker_spec` | `dataset_id` and nested `version_id` when `dataset_type=BUILD_IN_ASSET`; `inputs` only when a config mount is selected (no `robot_config`) |

<a id="eval-robot-config-compatibility"></a>
### 评测配置文件挂载（robot_config 已移除）

评测任务不再使用 `robot_config` 字段，CLI/SDK 也不再将其列为必填。机器人描述等配置目录统一通过
算子声明的 `ext_metadata.inputs` 挂载（如 `ROBOT_CONFIG_PATH`），`url_path` 填用户提供的 OBS 目录；
未选择挂载时省略 `inputs`，按算子内置/默认配置执行，报告应列明依赖机器人描述而未执行的指标。

若 CLI/SDK 创建评测时提示缺少 `robot_config`，说明本地客户端过旧：升级 CloudRobo SDK/CLI 后重试。
不能为通过旧校验而补写该字段、编造路径、传空字符串、用数据集目录冒充机器人描述，或绕过 SDK 改用其他提交通道。
Web 保持 SDK、Agent 保持 CLI。

> Eval tasks do not use proc-only fields: `algo_type`, `catalog_id`, `cluster_type`,
> `task_framework_type`, `head_spec`, `worker_num`, `evs_spec`, or
> `output_type` / `output_path` / `output_name`. Optional `envs` and operator `inputs` are
> included only when needed.

## envs Field Format

When operator's `ext_metadata.environment_variables` is not empty, construct `envs` field:

`envs` is a **string field** in task_config, value is a string representation of JSON array:

```text
"envs": "[{\"key\":\"K\",\"value\":\"V\",\"description\":\"D\"}]"
```

Not a nested object: `"envs": [{"key":"K","value":"V"}]` (invalid)

Each element's `key` is an `environment_variables[].name`, `value` defaults to its
`default` (overridden by the stage `params.envs`), and `description` is copied from the
definition. Keys in `params.envs` must exist in the operator's `environment_variables`.

## dataset_configs Format

`dataset_configs` is a **string field** — JSON array string. For a multi-input proc,
create one entry per `input_from` reference, preserving its order; waiting-only
`depends_on` entries do not become data inputs. Verify each exact asset version/path and
the operator's supported input count, formats and ordering. A multi-input merge still
produces one dataset; eval keeps its single top-level dataset fields plus a matching
single-item versioned `dataset_configs`. See the
[multi-input example](custom-pipeline-authoring.md#multi-input).

```json
[
  {
    "obs_path": "obs://bucket/path/to/data",
    "dataset_type": "BUILD_IN_ASSET",
    "asset_id": "<dataset asset ID>",
    "asset_name": "<dataset asset name>",
    "version_id": "<version ID>"
  }
]
```

| Field | BUILD_IN_ASSET | UDF_OBS_ASSET |
|-------|---------------|---------------|
| `obs_path` | Required (from asset `url` field) | Required (user-provided OBS path) |
| `asset_id` | Required | **Omit** |
| `asset_name` | Required | **Omit** |
| `version_id` | Required | **Omit** |

## Resource Specs

Resource guidance follows the dataset skill (`huawei-cloud-cloudrobo-dataset`):

- **Pool**: `resource_pool_type` is `PUBLIC_POOL` (default) or `DEDICATED_POOL`. For
  `DEDICATED_POOL`, also set `resource_id` and `dedicated_pool_name` from
  `cloudrobo resource list-pools`.
- **Spec**: choose `worker_spec` from the pool's available flavors; the templates use
  4c8g (`{cpu: 4, memory: 8, gpu: 0, npu: 0}`) as the default value.
- **CCE/K8S (single container)**: `head_spec` is `{cpu: 0, memory: 0, gpu: 0, npu: 0}`,
  `worker_num` is `1`.
- **EVS**: `evs_spec: 0` by default; only public pool tasks can set a non-zero EVS size.

**Public pool note**: on the public pool, a 4c8g pod can stay in `POD_PENDING` under
resource contention. If that happens, choose a smaller flavor such as 2c4g
(`worker_spec: {cpu: 2, memory: 4, gpu: 0, npu: 0}`) or use a dedicated pool, then create
a new task after user confirmation.

**RAY tasks** (`cluster_type: CCE_RAY`, `task_framework_type: RAY`): select both
`head_spec` and `worker_spec` from the pool flavors and ask for `worker_num`. Example:

| Component | spec | Example value |
|-----------|------|---------------|
| head | `head_spec` | `{cpu: 2, memory: 4, gpu: 0, npu: 0}` (2c4g) |
| worker | `worker_spec` | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` (4c8g) |
| worker count | `worker_num` | `2` |

> **Parallel group total**: For evaluation stage with 2 parallel eval tasks,
> total resource = 2 × the selected eval `worker_spec`.
>
> **head_spec must be non-zero for RAY**: the RAY head is a real workload component
> (unlike CCE/K8S where head_spec `{cpu: 0, memory: 0, gpu: 0, npu: 0}` is valid).

## Non-Empty Validation

Except `description`, all parameters cannot be empty values. The CLI validates before API
submission:
- Required fields (see [Required Fields](#required-fields-cli-validator)) must be present
- String fields cannot be `""` or whitespace-only
- `head_spec`/`worker_spec` cannot be `{}` and must include `cpu` and `memory` keys (value
  `0` is valid); the templates also include `gpu` and `npu`
- `dataset_configs` must contain at least 1 dataset entry; empty array `"[]"` is invalid
- `envs` optional but non-empty if present
