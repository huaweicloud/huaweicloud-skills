# Task Config Reference

## Operator Field Mapping

Extract fields from query operator results and map to task_config:

| Operator Field                       | task_config Field                 | Description                         |
|--------------------------------------|-----------------------------------|-------------------------------------|
| `asset_id`                           | `algo_id`                         | Algorithm ID                        |
| `name`                               | `algo_name`                       | Algorithm name                      |
| `ext_metadata.command`               | `algo_entrance`                   | Startup command                     |
| `ext_metadata.engine.image_url`      | `image`                           | Image address                       |
| `ext_metadata.environment_variables` | `envs` (some operators have this) | Environment variables, string field |
| `ext_metadata.inputs`                | `inputs` (optional; some operators have this) | Operator input mounts, JSON array string of complete input elements (see [Operator Inputs Mount](#operator-inputs-mount-ext_metadatainputs)) |

**Note:** `catalog_id` uses the workspace's catalog_id, not the operator's `catalog_id`.

## Required Fields Template

```json
{
  "name": "Task name",
  "algo_type": "PRESET_ASSETS",
  // Preset algorithm; workspace asset algorithm uses WORKSPACE_ASSETS; OBS algorithm uses OBS_ASSETS
  "algo_name": "<operator name>",
  "algo_entrance": "<operator ext_metadata.command>",
  "image": "<operator ext_metadata.engine.image_url>",
  "algo_id": "<operator asset_id>",
  "catalog_id": "<workspace catalog_id>",
  "resource_pool_type": "PUBLIC_POOL",
  "cluster_type": "CCE",
  "task_framework_type": "K8S",
  "dataset_configs": "[{\"obs_path\":\"obs://bucket/path/\",\"dataset_type\":\"UDF_OBS_ASSET\"}]",
  "output_type": "BUILD_IN_ASSET",
  "output_path": "obs://bucket/output-path",
  "output_name": "Output name",
  "head_spec": {
    "cpu": 0,
    "memory": 0,
    "gpu": 0,
    "npu": 0
  },
  "worker_spec": {
    "cpu": 4,
    "memory": 8,
    "gpu": 0,
    "npu": 0
  },
  "worker_num": 1,
  "evs_spec": 0
}
```

## Optional Fields

| Field                 | Description                                                                                             |
|-----------------------|---------------------------------------------------------------------------------------------------------|
| `algo_path`           | Algorithm path (required when `algo_type=OBS_ASSETS`, OBS storage path for algorithm code/files)        |
| `job_local_path`      | Container mount path (required when `algo_type=OBS_ASSETS`, mount path for algorithm data in container) |
| `resource_id`         | Dedicated resource pool ID (used when `resource_pool_type=DEDICATED_POOL`)                              |
| `dedicated_pool_name` | Dedicated resource pool name (used when `resource_pool_type=DEDICATED_POOL`)                            |
| `envs`                | Environment variables (JSON array string) — see [envs Field Format](#envs-field-format)                 |
| `inputs`              | Operator input mounts (JSON array string, proc and eval) — see [Operator Inputs Mount](#operator-inputs-mount-ext_metadatainputs) |

## algo_type Values

| Algorithm Source          | algo_type Value    | Required Fields                                                                                                 |
|---------------------------|--------------------|-----------------------------------------------------------------------------------------------------------------|
| Preset algorithm          | `PRESET_ASSETS`    | `algo_id`, `algo_name`, `algo_entrance`, `image` (extract from operator ext_metadata)                           |
| Workspace asset algorithm | `WORKSPACE_ASSETS` | `algo_id` (required, asset linkage), `algo_name`, `algo_path` (= asset `code_dir`, mount source — **required**), `job_local_path` (**required**), `algo_entrance` (**absolute** `python3 {job_local_path}/entrypoint.py`), `image` (asset `ext_metadata.engine.image_url`). The asset's `image_source` is `custom` for both Mode A and Mode B 空间资产-算法 (the algorithm asset links the image asset via `engine.asset_id` + `engine.asset_version_id`); verified: missing `algo_path`/`job_local_path` fails at runtime (`//entrypoint.py` no such file) |
| OBS algorithm             | `OBS_ASSETS`       | `algo_path`, `job_local_path`, `algo_entrance`, `image` (provided by user); `algo_id` **omit it** — direct OBS code mount (Mode B OBS算法). If `algo_id` is provided it must be a valid UUID (asset linkage only, runtime still mounts `algo_path`) |

## Operator Inputs Mount (`ext_metadata.inputs`)

Preset algorithms may declare optional/required external inputs in `ext_metadata.inputs`.
An input element can contain the following fields (not every operator returns all of them —
e.g. `label` / `required` may be absent):

| Field | Meaning |
|-------|---------|
| `name` | Input identifier (e.g. `DATA_CONFIG_PATH`, `CURATION_CONFIG_PATH`, `ROBOT_CONFIG_PATH`, `DESENS_MODEL_PATH`) |
| `label` | Display name |
| `description` | Purpose of the input |
| `required` | `true` = must be provided; `false` = optional (omit → default behavior) |
| `input_type` | `DATA_CONFIG` / `MODEL` / `DATA` / `MODEL_CONFIG` |
| `url_path` | Built-in default path, if any (may be an `obs://` system path or a platform-internal path such as `/asset/models/...` — copy as returned); empty = user provides when required. User-supplied values must be `obs://` paths |
| `access_method` | `env` — injected as environment variable into the task container |

**task_config `inputs` field (when provided):**

> **Format**: each element is the **complete** `ext_metadata.inputs[]` element, copied as
> returned by the **current** query (do not add or strip fields), with only `url_path` set
> to the user-selected `obs://` path. Never use `obs_path` as an inputs key.

```json
"inputs": "[{\"name\":\"ROBOT_CONFIG_PATH\",\"label\":\"机器人描述文件\",\"required\":false,\"url_path\":\"obs://bucket/config/robot-desc/\",\"input_type\":\"MODEL\",\"description\":\"机器人描述文件目录（含robots.yaml或URDF）（可选）\",\"access_method\":\"env\"}]"
```

- `inputs` is a **string field** (JSON array string), like `dataset_configs`/`envs`
- Each element is the complete operator input element with `url_path` = user-selected OBS path
- **`required: false` inputs**: do not prompt by default — omit them (and omit the whole
  `inputs` field when nothing needs to be mounted); the algorithm uses its default behavior
  (old/new auto-compatible). Only ask when the user explicitly wants a custom mount
- **`required: true` inputs with a built-in `url_path`**: no user action; the platform uses
  the built-in path, so they do not need to be listed in `inputs`
- **`required: true` inputs with an empty `url_path`**: must be supplied by the user and
  included in `inputs`
- If the operator's current `ext_metadata` has no `inputs` (absent or `null`), omit the
  `inputs` field
- Do not send an empty array `"[]"` — omit the field instead (not enforced by the CLI
  validator)

**Known operator inputs (reference — always re-read the current `ext_metadata.inputs`):**

| Operator | Input name | required | input_type | Meaning |
|----------|-----------|----------|------------|---------|
| 数据脱敏 | `DESENS_MODEL_PATH` | true | MODEL | Model weights dir; `url_path` is built-in — no user action |
| 数据清洗 | `CURATION_CONFIG_PATH` | false | DATA_CONFIG | Custom cleaning config dir |
| 数据转换 ros→V3/V21, H5→V3, UMI→V3 | `DATA_CONFIG_PATH` | false | DATA_CONFIG | Custom manifest config dir |
| 评测 质量/多样性 | `ROBOT_CONFIG_PATH` | false | MODEL | Robot description dir (robots.yaml/URDF) |

> This table is a reference only. Operator versions differ by region and over time, and an
> operator may currently declare no `inputs` at all. Always use the inputs (names, fields,
> `required`, built-in `url_path`) returned by the **current** query.

**Priority:** `inputs[].url_path` > operator built-in `url_path`/default manifest >
dataset directory config (config.yaml/manifest.yaml) > `robot` env default (the `robot`
variable is read from the operator's `ext_metadata.environment_variables`, when declared).

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

## envs Field Format

When operator's `ext_metadata.environment_variables` is not empty, need to construct it as `envs` field in task_config.

`envs` is a **string field** in task_config, value is a string representation of JSON array:

```
"envs": "[{\"key\":\"K\",\"value\":\"V\",\"description\":\"D\"}]"
```

Not a nested object: `"envs": [{"key":"K","value":"V"}]` ❌

Each environment variable should include `key`, `value`, and `description` fields. Read `description` from
`ext_metadata.environment_variables` definitions.

**Dynamic processing rule:** Read variable definitions from `ext_metadata.environment_variables` (including variable
name, description, optional values, etc.), display to user and confirm specific values, then construct as `envs` string.
Do not hardcode environment variables for any operator.

**⚠️ EXCLUDE platform-injected input ports from `envs` (verified, Mode A e2e):** inputs declared with
`access_method=env` (e.g. `SOURCE_DATASET_PATH`) are **injected by the platform at runtime**. If `envs` includes them
with their fallback `default` (e.g. `/tmp/source/dataset`), that literal placeholder **overrides/blocks the platform
injection** — the container reads the placeholder instead of the injected JSON map and the task fails with
`SOURCE_DATASET_PATH is not a valid JSON map` / `INPUT environment variable is not set`. Build `envs` from
`ext_metadata.environment_variables` but **drop `SOURCE_DATASET_PATH` and any other `access_method=env` input ports**;
keep only business variables (e.g. `UMI_PLATFORM`).

## dataset_configs Field (Multiple Dataset Input)

`dataset_configs` is a **string field** in task_config, value is a string representation of JSON array, supports
multiple dataset input. Each item structure:

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

- `dataset_type` values: `BUILD_IN_ASSET` (platform asset) or `UDF_OBS_ASSET` (user OBS path)
- `obs_path` must use dataset asset's `url` field, query via
  `cloudrobo asset list-assets --catalog-id <catalog-id> --type dataset`, or use
  `cloudrobo asset show-asset --asset-id <id>` when asset_id is known. Do not manually concatenate

> **⚠️ `UDF_OBS_ASSET` workspace-bound bucket constraint:** a user-provided `obs_path`
> **MUST use the workspace-bound OBS bucket** — the bucket of `default_obs_path`
> (`cloudrobo workspace current`, e.g. `obs://{default-bucket}/cloudrobo/{workspace_id}/`).
> Other OBS buckets are **not supported** (task creation rejects a foreign-bucket path).
> Validate `obs://<bucket>/...` → bucket must equal the `default_obs_path` bucket;
> mismatch → reject and re-ask, showing `obs://<default-bucket>/` as the expected bucket.

**Field requirements for different dataset_type:**

| Field        | BUILD_IN_ASSET                         | UDF_OBS_ASSET                          |
|--------------|----------------------------------------|----------------------------------------|
| `obs_path`   | Required (get from asset `url` field)  | Required (OBS path provided by user)   |
| `asset_id`   | Required (get from asset query result) | **Omit** (do not include empty fields) |
| `asset_name` | Required (get from asset `name` field) | **Omit** (do not include empty fields) |
| `version_id` | Required (get from asset query result) | **Omit** (do not include empty fields) |

**UDF_OBS_ASSET example:** `{"obs_path":"obs://bucket/path/","dataset_type":"UDF_OBS_ASSET"}` — only include `obs_path`
and `dataset_type`, omit empty `asset_id`/`asset_name`/`version_id`.

Note: Built-in operators use `list-publication-assets` (public assets) to query; custom operators and datasets use
`list-assets` (workspace assets), the interfaces are different.

**Deprecated fields:** `dataset_ids`, `dataset_names`, `dataset_paths`, `dataset_version_ids` have been replaced by
`dataset_configs`, no longer used.

## cluster_type and task_framework_type Matching

| cluster_type | task_framework_type |
|--------------|---------------------|
| CCE          | K8S                 |
| CCE_RAY      | RAY                 |

## eval-tasks Field Differences

Key differences between evaluation tasks (eval-tasks) and processing tasks (proc-tasks):

| Field                | proc-tasks                                               | eval-tasks                                            |
|----------------------|----------------------------------------------------------|-------------------------------------------------------|
| Dataset input        | `dataset_configs` (JSON string array, multiple datasets) | Top-level dataset fields plus a matching single-item `dataset_configs` JSON string (asset input includes exact `version_id`) |
| Config files         | Optional `inputs` mounts                                 | Optional `inputs` mounts (e.g. `ROBOT_CONFIG_PATH`); `robot_config` removed |
| Deletion granularity | Single (CLI `delete-task --task-id`) / Batch (SDK `delete_tasks`, API `?ids=`) | Single (`delete-task --task-id`) |
| Copy                 | Supported (`copy-task --name --output-name`)             | Supported (`copy-task --name`)                        |
| Restart              | Not supported                                            | Not supported                                         |
| Wait for terminal state | `dataset proc wait-task`                              | `dataset eval wait-task`                              |
| Resource monitoring  | Supported (`get-resource-usage`)                         | Not supported                                         |
| Frame listing        | Supported (`get-frames`)                                 | Not supported                                         |
| Report preview       | Supported (`get-preview --file-name [--is-download]`)    | Supported (`get-preview --file-name [--is-download]`) |
| Task events          | Supported (`get-events --job-name`)                      | Supported (`get-events --job-name`)                   |

## eval-tasks Required Fields

Common required fields (non-empty; check legacy client compatibility below):

`name`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `dataset_type`, `dataset_name`,
`dataset_path`, `dataset_configs`, `resource_pool_type`, `worker_spec`. Asset inputs also require
`dataset_configs[0].version_id`, the exact verified version ID.

`dataset_id` is additionally required when `dataset_type=BUILD_IN_ASSET`.

Eval task-config does **not** use proc-only fields (`algo_type`, `catalog_id`, `cluster_type`,
`task_framework_type`, `head_spec`, `worker_num`, `evs_spec`,
`output_type`/`output_path`/`output_name`). Optional fields: `description`, `resource_id`,
`dedicated_pool_name`, `workspace_id`, `envs`, `inputs` (operator mounts; see above).

```json
{
  "name": "Eval task name",
  "algo_id": "<operator asset_id>",
  "algo_name": "<operator name>",
  "algo_entrance": "<operator ext_metadata.command>",
  "image": "<operator ext_metadata.engine.image_url>",
  "dataset_type": "BUILD_IN_ASSET",
  "dataset_id": "<dataset asset ID>",
  "dataset_name": "<dataset name>",
  "dataset_path": "obs://bucket/path/",
  "dataset_configs": "[{\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<dataset asset ID>\",\"asset_name\":\"<dataset name>\",\"obs_path\":\"obs://bucket/path/\",\"version_id\":\"<exact version ID>\"}]",
  "resource_pool_type": "PUBLIC_POOL",
  "worker_spec": {"cpu": 2, "memory": 4}
}
```

**Robot description via OBS mount:** the top-level `robot_config` field has been removed.
The robot description (robots.yaml / URDF) is passed only as an operator mount through
`inputs` (e.g. `ROBOT_CONFIG_PATH`) when currently declared and needed. Without a mount the
operator uses its built-in/default configuration; manifest mode alone does not make a mount
mandatory. Add an actual description only when selected metrics require it, and list
unavailable metrics in the report.

<a id="eval-robot-config-compatibility"></a>
### 评测配置文件挂载（robot_config 已移除）

评测任务不再使用 `robot_config` 字段，CLI/SDK 也不再将其列为必填；配置目录统一通过算子声明的
`inputs` 挂载传入。若 CLI/SDK 创建评测时提示缺少 `robot_config`，说明本地客户端过旧，升级后重试；
不补写该字段、不编造路径、不传空字符串、不用数据集路径代替，也不绕过客户端换通道提交。
独立核对算子支持的内置 robot、配置来源及实际可用指标。

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

## Update Limitations

Update interface (`update-task`) for both proc-tasks and eval-tasks only allows modifying `name` and `description`
fields, other fields cannot be updated.

## Non-Empty Validation Rule

**Except `description`, all parameters cannot be empty values.** The SDK (`DatasetClient.create_task` /
`create_eval_task`) validates before API submission:

- **Missing fields**: Required fields must be present in task_config
- **Empty string**: String fields (e.g., `name`, `algo_name`, `algo_entrance`, `image`, `catalog_id`, `output_path`,
  `output_name`) cannot be `""` or whitespace-only
- **Empty dict**: `head_spec` and `worker_spec` cannot be `{}` — must contain `cpu` and `memory` keys
- **Missing spec keys**: `head_spec`/`worker_spec` must include `cpu` and `memory` (add `gpu`/`npu` as `0` when unused; SDK validates only `cpu`/`memory`)
- **Numeric zero is valid**: `worker_num: 1`, `evs_spec: 0`, `cpu: 0` are valid non-empty values
- **Empty dataset_configs is invalid**: `"[]"` (empty array) is not acceptable, it must be contained at leat one
  dataset.
- **`envs` optional but non-empty if present**: If `envs` field is included, it must be a non-empty JSON string array
- **`inputs` optional**: omit the field when nothing needs to be mounted rather than sending `"[]"` (not enforced
  by the CLI validator)

**algo_type-specific required fields:**

| algo_type          | Additional required fields    | Not required                               |
|--------------------|-------------------------------|--------------------------------------------|
| `PRESET_ASSETS`    | `algo_id`                     | —                                          |
| `WORKSPACE_ASSETS` | `algo_id`, `algo_path`, `job_local_path` | — (both ways need these; 空间资产-算法 additionally carries `algo_id` for asset linkage) |
| `OBS_ASSETS`       | `algo_path`, `job_local_path` | `algo_id` (omit it — direct OBS code mount, Mode B OBS算法; if provided must be a valid UUID, linkage only) |
