# 资产参数规则详细参考

本文档按接口组织，列出每个接口的字段校验、参数交互和特殊行为规则。调用接口前查阅对应章节即可。

---

## create-asset

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `catalog_id` | 是 | UUID 格式 |
| `name` | 非 image 时必填 | 3-64 字符：中英文、数字、连字符、下划线、点、斜杠 |
| `type` | 是 | 见类型映射表 |
| `sub_type` | simulation 时必填 | 见类型映射表；model/dataset 无合法 sub_type，传了会报错 |
| `description` | 否 | 最长 512 字符 |
| `status` | 否 | `CREATING` `DRAFT` `ALPHA` `BETA` `RELEASE` `STABLE` `DEPRECATED` `ARCHIVE` |
| `tags` | 否 | 最多 100 个，每项 1-32 字符：中英文、数字、点号、连字符、下划线、空格 |
| `url` | 否 | `obs://bucket/path` 或 SWR 镜像格式，最长 1024；image 必须用 SWR 格式、algorithm 不应提供 url（后端校验，客户端不拦截） |
| `ext_metadata` | 否 | 按 type 校验，见下方 ext_metadata 章节 |
| `parent_asset_version_id` | 否 | UUID 格式；提供时必须同时提供 `generation_method` |
| `generation_method` | 否 | 字母开头，1-64 字符：字母、数字、下划线 |

### 参数交互

- **`parent_asset_version_id` 依赖 `generation_method`**：提供前者时必须同时提供后者，否则报错
- **`name` 依赖 `type`**：非 image 类型必填，image 类型可选
- **`sub_type` 依赖 `type`**：type 有值时 sub_type 必须属于该 type 的合法子类型

---

## update-asset

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `name` | 否 | 3-64 字符 |
| `description` | 否 | 最长 512 字符 |
| `status` | 否 | 同 create-asset 枚举 |
| `tags` | 否 | 最多 100 个，每项 1-32 字符：中英文、数字、点号、连字符、下划线、空格 |
| `ext_metadata` | 否 | 由后端根据资产 type 校验（客户端无法获知类型） |
| `author` | 否 | 后端静默忽略，传值不报错但不生效 |
| `catalog_id` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `type` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `sub_type` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `url` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `parent_asset_version_id` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `generation_method` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |

### 参数交互

- **update-asset 仅支持修改**：`name`、`description`、`status`、`tags`、`ext_metadata`
- **不可修改字段**：`catalog_id`、`type`、`sub_type`、`url`、`parent_asset_version_id`、`generation_method` — CLI 与 SDK 均不提供对应参数，字段不可变（客户端不存在"传值报 ValidationError"的路径）
- **后端静默忽略**：`author` 传值不报错但不生效

---

## create-version

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `version` | 否 | 2-128 字符：字母或数字开头，可含字母、数字、点、连字符、下划线 |
| `description` | 否 | 最长 512 字符 |
| `status` | 否 | 同 create-asset 枚举 |
| `url` | 否 | `obs://bucket/path` 或 SWR 镜像格式，最长 1024 |
| `ext_metadata` | 否 | 由后端根据资产 type 校验（客户端不校验，因创建版本时无法获知资产类型） |
| `parent_asset_version_id` | 否 | UUID 格式；提供时必须同时提供 `generation_method` |
| `generation_method` | 否 | 字母开头，1-64 字符 |

### 参数交互

- **`parent_asset_version_id` 依赖 `generation_method`**：同 create-asset

---

## update-version

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `version` | 否 | 2-128 字符 |
| `description` | 否 | 最长 512 字符 |
| `status` | 否 | 同 create-asset 枚举 |
| `ext_metadata` | 否 | 由后端根据资产 type 校验（客户端无法获知资产类型） |
| `url` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `parent_asset_version_id` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |
| `generation_method` | 不可修改 | CLI/SDK 不提供该参数，字段不可变 |

### 参数交互

- **update-version 仅支持修改**：`version`、`description`、`status`、`ext_metadata`
- **不可修改字段**：`url`、`parent_asset_version_id`、`generation_method` — CLI 与 SDK 均不提供对应参数，字段不可变（客户端不存在"传值报 ValidationError"的路径）

## list-assets

### 参数交互

- **`repository_id`/`catalog_id` 至少提供一个**：都不传时后端报错；同时传则以 AND 关系叠加
- **`exact_name` 覆盖 `name`**：同时提供时精确匹配生效，模糊匹配被忽略
- **`actions` 仅对 model/algorithm/dataset 生效**：其他 type 时 `actions` 和 `actions_operator` 被静默清空，不报错
- **`action_status` 依赖 `actions`**：`actions` 为空时 `action_status` 单独传入无过滤效果
- **`sub_type` 依赖 `type`**：type 有值时 sub_type 必须属于该 type 的合法子类型
- **`mine` 与 `author` AND 叠加**：同时使用且当前用户不在 author 列表中时结果为空集
- **`permissions` 自动注入 `meta_read`**：无论传了什么，系统始终自动添加 `meta_read`
- **`recommend_score` 覆盖排序**：为 true 时主排序变为 recommend_score DESC，sort_key 仅作次排序

### 默认值

| 参数 | 默认值 |
|------|--------|
| `sort_dir` | `desc` |
| `sort_key` | `created_at` |
| `tags_operator` | `and` |
| `actions_operator` | `OR` |
| `offset` | 0 |
| `limit` | 100 |

---

## list-versions

### 参数交互

- **`exact_version` 覆盖 `version`**：同时提供时精确匹配生效，模糊匹配被忽略
- **`actions` 仅对 model/algorithm/dataset 生效**：同 list-assets
- **`action_status` 依赖 `actions`**：同 list-assets

### 默认值

| 参数 | 默认值 |
|------|--------|
| `sort_dir` | `desc` |
| `sort_key` | `created_at` |
| `actions_operator` | `OR` |
| `offset` | 0 |
| `limit` | 100 |

---

## list-publication-assets

### 参数交互

- **`exact_name` 覆盖 `name`**：同 list-assets
- **`capabilities` 覆盖 `actions`**：capabilities 非空且 type 为 model/null 时，转换后覆盖用户传入的 actions；capabilities 为空或 type 非 model 时 actions 正常生效
- **`capabilities` 仅对 type=model 生效**：type 非 model 时 capabilities 被忽略
- **`capabilities` 映射**：`training`→[PRETRAINING,FFT,LORA]，`inference`→[ONLINE_DEPLOYMENT]，`reinforcement_learning`→[LIBERO_SPATIAL,LIBERO_OBJECT,LIBERO_GOAL,LIBERO_10]
- **`actions` 仅对 model/algorithm/dataset 生效**：同 list-assets
- **`action_status` 依赖 `actions`**：同 list-assets
- **`sub_type` 依赖 `type`**：同 list-assets
- **`permissions` 自动注入 `meta_read`**：同 list-assets
- **`recommend_score` 覆盖排序**：同 list-assets

### 默认值

| 参数 | 默认值 |
|------|--------|
| `recommend_score` | **`true`**（与 list-assets 不同） |
| `sort_dir` | `desc` |
| `sort_key` | `created_at` |
| `tags_operator` | `and` |
| `actions_operator` | `OR` |
| `offset` | 0 |
| `limit` | 100 |

---

## search-assets

### 参数交互

- **`type` 默认限制**：type 支持 dataset/model/simulation，不传 type 时搜索 dataset/model/simulation

### 默认值

| 参数 | 默认值 |
|------|--------|
| `offset` | 0 |
| `limit` | 10 |

---

## list-repositories

### 默认值

| 参数 | 默认值 |
|------|--------|
| `sort_dir` | **`asc`**（与 list-assets 不同） |
| `offset` | 0 |
| `limit` | 100 |

---

## list-catalogs

### 默认值

| 参数 | 默认值 |
|------|--------|
| `sort_dir` | **`asc`**（与 list-assets 不同） |
| `offset` | 0 |
| `limit` | 100 |

---

## create-action

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `action` | 是 | 枚举：PRETRAINING、FFT、LORA、ONLINE_DEPLOYMENT、LIBERO_SPATIAL、LIBERO_OBJECT、LIBERO_GOAL、LIBERO_10 |
| `algorithm.asset_id` | 是 | UUID，必须指向 type=algorithm 的资产 |
| `algorithm.version_id` | 是 | UUID |
| `status` | 否 | `ENABLE`（默认）/ `DISABLE` |
| `inherited` | 否 | 布尔值，默认 true |

### 参数交互

- **Action 仅对 model/algorithm/dataset 生效**：其他 type 的资产创建 action 会被拒绝
- **algorithm.asset_id 必须是 algorithm 类型**：否则报错
- **algorithm 必须同目录或已发布**：算法资产必须与目标资产在同一目录，或算法资产已发布到广场
- **action 不可重复**：同一资产版本下每个 action 类型只能有一个

---

## update-action

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `algorithm.asset_id` | 是 | 同 create-action |
| `algorithm.version_id` | 是 | 同 create-action |
| `status` | 否 | 不传则保持原值 |
| `inherited` | 否 | 不传则保持原值 |

### 参数交互

- **`algorithm` 始终必填**：即使只想修改 status/inherited，也必须传入 algorithm
- **algorithm 校验同 create-action**：类型、目录、发布要求一致

---

## import-asset

### Frontmatter 驱动的参数解析

`import-asset` 支持从 `local-path/README.md` YAML frontmatter 自动读取元信息。

**Frontmatter 字段**：`name`, `type`, `sub_type`, `description`, `status`, `tags`, `version`,
`ext_metadata`, `parent_asset_version_id`, `generation_method`

**解析优先级**：frontmatter > CLI 参数 > 报错（必填字段；catalog_id 除外，catalog_id 仅支持 CLI）

| 字段 | 创建新资产时 | 创建新版本时（`--asset-id`） |
|------|-------------|---------------------------|
| `catalog_id` | **CLI 必填** | N/A |
| `asset_id` | N/A | **CLI 必填** |
| `name` | frontmatter > CLI > **报错** | 不需要 |
| `type` | frontmatter > CLI > **报错** | 不需要 |
| `sub_type` | frontmatter > CLI > **报错**(simulation) | 不需要 |
| `ext_metadata` | frontmatter > CLI > **报错**(有必填字段时) | frontmatter > CLI（可选） |
| `version` | frontmatter（可选） | frontmatter（可选） |
| `description` | frontmatter（可选） | frontmatter（可选） |
| `status` | frontmatter（可选） | frontmatter（可选） |
| `tags` | frontmatter（可选） | 不需要 |
| `parent_asset_version_id` | frontmatter（可选） | frontmatter（可选） |
| `generation_method` | frontmatter（可选） | frontmatter（可选） |

### 校验规则

`import-asset` 有两种模式，校验规则分别继承已有接口：

1. **非 `asset_id` 模式**（创建新资产 + 首版本）：字段校验同 `create-asset`（type/sub_type/name/catalog_id/ext_metadata 等），版本字段同 `create-version`
2. **`asset_id` 模式**（为已有资产创建新版本）：版本字段校验同 `create-version`；若提供 ext_metadata，按已有资产的 type/sub_type 校验其合法性

### 增量上传与状态流转

**三种模式：**

| 模式 | 参数 | 行为 |
|------|------|------|
| Mode 1 | 无 `--asset-id` | 创建新资产+版本 → 上传 OBS → 若 status=CREATING 则更新为 DRAFT |
| Mode 2 | 仅 `--asset-id` | 创建新版本 → 上传 OBS → 若 status=CREATING 则更新为 DRAFT |
| Mode 3 | `--asset-id` + `--version-id` | 复用已有版本 → 增量上传 OBS → 若 status=CREATING 则更新为 DRAFT |

**增量上传（Mode 3 默认）：**
- `overwrite=False`（默认）：对每个本地文件先 `head_object` 检查 OBS 是否已存在，存在则跳过
- `--overwrite`：强制覆盖所有已存在的 OBS 对象
- 适用于给已存在版本追加新文件、或重试部分失败的上传

**CREATING→DRAFT 状态流转：**
- 用户未指定 `--status` 时，后端创建版本默认状态为 `CREATING`（表示正在上传）
- OBS 上传成功后，SDK 自动 `show_asset_version` 检查当前状态：只有 `status == "CREATING"` 时才调 `update_asset_version` 更新为 `DRAFT`
- 用户显式指定了其他状态（如 `RELEASE`）时，上传完成后**不**自动修改状态
- `update_asset_version` 失败只记 warning 不阻断导入（上传已成功，状态更新是辅助操作）

### ext_metadata 前置校验

创建新资产时，`import-asset` 在调用 API 前进行客户端校验：

| type | sub_type | ext_metadata 必填字段 |
|------|----------|----------------------|
| `model` | — | `model_type` |
| `dataset` | — | `annotation_status` |
| `algorithm` | — | `engine`（含 `image_url`/`image_source`）, `command` |
| `image` | — | `arch`, `device_type` |
| `simulation` | `robot` | `robot_type`, `robot_manufacturer` |
| `simulation` | 其他 | 无必填 |

若 ext_metadata 缺失必填字段，CLI 报 `UsageError`；若 ext_metadata 有值但字段不合法，报 `UsageError`（含具体字段错误信息）。

**Examples**:
```bash
# model 类型 — 必填: model_type
cloudrobo asset create-asset --catalog-id <id> --name my-model --type model --ext-metadata '{"model_type":"planning"}'

# dataset 类型 — 必填: annotation_status
cloudrobo asset create-asset --catalog-id <id> --name my-dataset --type dataset --ext-metadata '{"annotation_status":true}'

# simulation/robot 类型 — 必填: robot_type, robot_manufacturer
cloudrobo asset create-asset --catalog-id <id> --name my-robot --type simulation --sub-type robot --ext-metadata '{"robot_type":"humanoid","robot_manufacturer":"Galaxea R1"}'

# image 类型 — 必填: arch, device_type
cloudrobo asset create-asset --catalog-id <id> --name my-image --type image --ext-metadata '{"arch":"x86_64","device_type":["GPU","CPU"]}'

# algorithm 类型 — 必填: engine.image_url, engine.image_source, command
cloudrobo asset create-asset --catalog-id <id> --name my-algo --type algorithm --ext-metadata '{"engine":{"image_url":"swr.cn-southwest-2.myhuaweicloud.com/namespace/repo:tag","image_source":"custom"},"command":"python train.py"}'
```

### 标签校验

`import-asset` 在创建资产时对 tags 进行额外校验：
1. **格式校验**：每项 1-32 字符，匹配 `中英文/数字/点号/连字符/下划线/空格` 正则
2. **合法性校验**：调用 `GET /v1/asset-tags` 接口获取服务端预定义标签列表，过滤不在列表中的标签；同时按资产 type/sub_type 校验标签是否属于该分类

`create-asset` 和 `add-tags` 对 tags 做格式校验 + 合法性校验（调用 `GET /v1/asset-tags` 获取预定义标签列表，过滤不在列表中的标签）。

---

## add-tags

### 校验规则

- **格式校验**：同 create-asset 的 tags 字段（每项 1-32 字符，匹配 `中英文/数字/点号/连字符/下划线/空格` 正则），由客户端 SDK 校验（TAG_PATTERN 正则）
- **合法性校验**：调用 `GET /v1/asset-tags` 获取预定义标签列表，过滤不在列表中的标签（与 import-asset 相同）

---

## delete-tag

### 校验规则

- 无客户端校验，直接调用后端 API 删除

---

## list-tags

### 参数交互

- **`language` 必填**：必须为 `zh` 或 `en`
- **`type`/`sub_type` 过滤**：可选，按资产类型过滤预定义标签

---

## check-permission

### 字段校验

| 字段 | 必填 | 规则 |
|------|------|------|
| `permissions` | 是 | 数组，合法值：`meta_read` `meta_write` `data_read` `data_write` `data_usable` |

---

## export-asset

### 参数交互

- **`version_id` 可选**：不传时导出最新版本
- **资产至少有一个版本**：否则抛出 RuntimeError

---

## ext_metadata 按 type 校验规则

以下规则适用于 `create-asset` 的 ext_metadata 字段（客户端校验）。`create-version`、`update-asset`、`update-version` 的 ext_metadata 由后端根据资产 type 校验（客户端无法获知资产类型）。

### model

| 字段 | 必填 | 规则 |
|------|------|------|
| `model_type` | **是** | 枚举：`planning` `perception` `vla` `vln` |
| `skills` | 否（仅 `vla`/`vln` 支持） | 数组，≤50 项；每项需 `name`（1-64 字符：中英文、数字、连字符、下划线、空格，前后不允许空格）+ `prompt`（1-1024 字符）；prompt 不可重复 |
| `strict` | 否（仅 `vla`/`vln` 支持） | 布尔值 |

### dataset

| 字段 | 必填 | 规则 |
|------|------|------|
| `annotation_status` | **是** | 布尔值 |

### algorithm

| 字段 | 必填 | 规则 |
|------|------|------|
| `engine.image_url` | **是** | SWR 格式：`swr.{endpoint}/{namespace}/{repo}:{tag}` |
| `engine.image_source` | **是** | 枚举：`preset`（广场预置镜像，此时 `code_dir` 必填）`custom`（空间自定义镜像） |
| `command` | **是** | 字符串，最长 4096 |
| `code_dir` | 条件必填 | `boot_file` 存在时或 `image_source=preset` 时必填 |
| `boot_file` | 否 | 必须以 `obs://` 开头，以 `.py` 结尾，且位于 `code_dir` 目录下 |
| `inputs` | 否 | 数组，≤10 项；每项需 `name`（1-64 字符：英文、数字、连字符、下划线）+ `access_method`（`env`或`parameter`），可选 `description`（0-512 字符）；name 不可重复 |
| `outputs` | 否 | 数组，≤5 项；格式同 inputs |
| `hyperparams` | 否 | 数组，≤90 项；每项需 `name`（字母/下划线开头，可含字母、数字、下划线、点、连字符，1-64字符）+ `default`（字符串，需按 `constraint.type` 校验格式：`Integer`→整数，`Float`→浮点数，`Boolean`→`true`/`false`，其他类型→匹配字符集（中英文、数字、下划线、斜杠、反斜杠、点、逗号、冒号、at、尖括号、花括号、美元符号、连字符，1-512字符）或合法 JSON 对象/数组）+ `constraint`（对象，需含 type/editable/required/sensitive 四个字段）；`description` 禁止 `\` `@` `#` `$` `%` `^` `&` `*` `<` `>` 字符（0-256字符）；name 不可重复 |
| `environment_variables` | 否 | 数组，≤90 项；每项需 `name`（字母/下划线开头，可含字母、数字、下划线、连字符，1-64字符）+ `default`（1-512字符：中英文、数字、下划线、斜杠、反斜杠、点、逗号、冒号、at、尖括号、花括号、美元符号、连字符），可选 `description`（最长 512 字符）；name 不可重复 |
| `resource` | 否 | 数组；每项需 `key`（`flavor_type`/`device_distributed_mode`/`host_distributed_mode`）+ `operator`（`in`）+ `values`（数组，flavor_type 对应 `CPU`/`GPU`/`NPU`，distributed_mode 对应 `multiple`/`singular`） |
| `yaml_config` | 否 | 字符串（YAML 格式由后端校验） |

### image

| 字段 | 必填 | 规则 |
|------|------|------|
| `arch` | **是** | 枚举：`x86_64` `arm` |
| `device_type` | **是** | 字符串数组，枚举：`CPU` `GPU` `ASCEND` |

### simulation/robot

| 字段 | 必填 | 规则 |
|------|------|------|
| `robot_type` | **是** | 枚举：`humanoid` `mobile_manipulator` `robot_arm` `quadruped_robot` `wheeled_robot` `other` |
| `robot_manufacturer` | **是** | 1-64 字符：中英文数字连字符点下划线空格（支持用户自定义）。已知取值：`Galaxea R1` `AGIBOT G1` `AzureLoong` `Universal Robots UR5e` `AgileX Cobot Magic` `Spirit AI Moz1` `SO-ARM101` `Yijiahe CR100` `Siasun GCR3-618` `Flexiv RIZON 4S` `JAKA mini2` `Franka Emika Panda` |

### simulation/environment、simulation/object、simulation/scene

无 ext_metadata 校验规则。

---

## 校验执行位置

| 校验项 | 执行位置 |
|--------|----------|
| 字段格式（name/version/url/tags 正则）、枚举（model_type/robot_type/arch/device_type/flavor_type/image_source）、条件必填 | 客户端 SDK（`ValidationError`） |
| update-asset 不可修改字段（`catalog_id`/`type`/`sub_type`/`url`/`parent_asset_version_id`/`generation_method`） | 不存在校验路径 — CLI/SDK 均不提供对应参数，字段不可变 |
| update-version 不可修改字段（`url`/`parent_asset_version_id`/`generation_method`） | 不存在校验路径 — CLI/SDK 均不提供对应参数，字段不可变 |
| `create_asset` 的 ext_metadata | 客户端 SDK（`ValidationError`） |
| `import-asset` 创建新资产时的 ext_metadata（前置校验） | 客户端 CLI（`UsageError`） |
| `import-asset` 创建新版本时的 ext_metadata（合法性校验） | 客户端 SDK（`ValidationError`） |
| `update_asset`/`create_version`/`update_version` 的 ext_metadata | 后端（客户端无法获知资产类型） |
| `robot_manufacturer` 枚举 | 后端（客户端仅校验格式） |
| 参数交互规则（覆盖、静默忽略、默认值） | 后端 |
