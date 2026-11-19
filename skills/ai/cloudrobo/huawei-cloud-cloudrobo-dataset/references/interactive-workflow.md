# Interactive Workflow

## Interaction Rules

- At most **one user-facing question round** per turn; multiple read-only queries may run in parallel to prepare it
- Display query results **before** asking the next question
- Forbid initiating multiple AskUserQuestion calls in parallel
- Forbid executing Bash queries and AskUserQuestion in the same turn
- **推荐优先，不要逐项盘问**：每个决策都有推荐默认值。说明默认值并继续；只在答案会实质改变结果时才问（见 [交互规范](../../huawei-cloud-cloudrobo-data-pipeline/references/user-facing-interaction.md)）。
- **一轮问完**：把所有互不相关的未知项合并到一轮。能推导或用默认值的，不要走固定问卷。
- **能推就推**：任务名由数据集+操作+时间戳推导；描述由请求推导；算法类型由所选算法推导；资源用默认值。

## Proc-Task Creation (recommended flow)

用户要求创建数据处理任务但参数不全时，**不要走 10 步问卷**。改为：

1. **推导**一切可推导项（任务名、描述、算法、资源、数据源）。
2. **一次问**真正开放的选项，每项带推荐默认值。
3. **展示简短确认摘要**（≤8 行，不含 ID/JSON），确认后提交。

用户已给全参数时，直接进入摘要并提交。

下面的逐步骤说明仍作为字段级规则的权威参考；其中"询问"类步骤仅在**该值无法推导**时使用。

### Legacy step reference (apply selectively)

以下逐步描述各字段。**值可推导或有安全默认值时不要问** —— 用方括号里的推荐值。

### Step 1: Task name [derive: `<dataset-or-op>-<operation>-<MMDDHHmmss>`]
- 仅当用户要求自定名称时才问。否则生成并在摘要中说明。

### Step 2: Task description [derive from the user's request]
- 仅当请求中没有可用描述时才问。否则写一行并在摘要中说明。

### Step 3: Select algorithm type [default: PRESET_ASSETS]
Options, in recommended order:
- **Preset Algorithm** (`PRESET_ASSETS`) — Platform built-in public algorithms, **default**
- **Workspace Asset Algorithm** (`WORKSPACE_ASSETS`) — Workspace custom algorithms
- **OBS Algorithm** (`OBS_ASSETS`) — User-provided algorithms, injected into containers via OBS path

仅当没有 preset 覆盖该任务、且用户已有或想新建自定义算子时才问。入驻路径见
`custom-operator/custom-operator-workflow.md`。

### Step 4: Algorithm configuration (branches by algorithm type)

**4a. Preset Algorithm (PRESET_ASSETS)**
- Query and display algorithm list: `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing"`
- Display algorithm list (name, description, update time)
- After user selection, extract field mappings from `ext_metadata`:
  - `asset_id` → `algo_id`
  - `name` → `algo_name`
  - `ext_metadata.command` → `algo_entrance`
  - `ext_metadata.engine.image_url` → `image`
- No additional container injection path needed (preset algorithms are built-in)

**4b. Workspace Asset Algorithm (WORKSPACE_ASSETS)**
- Get workspace `catalog_id` (obtain `asset_catalog_id` from `cloudrobo workspace current`)
- Query and display algorithm list: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type algorithm --tags "Data Processing"`
- Display algorithm list (name, description, update time). Since there may be many algorithms, display only the first few
- **Provide search functionality**: Offer "Search algorithm name" option in AskUserQuestion
  - If user chooses search, ask for search keyword
  - Use `--name` parameter to filter: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type algorithm --tags "Data Processing" --name <keyword>`
- After user selection, extract field mappings from `ext_metadata`:
  - `asset_id` → `algo_id`
  - `name` → `algo_name`
  - `ext_metadata.command` → `algo_entrance`
  - `ext_metadata.engine.image_url` → `image`
- **Additional step**: Ask for container injection path (`data_mount_path`), i.e., the mount path for algorithm data in the container
- **Onboarding new custom operators**: If the user needs to onboard new custom data processing code
  (not yet registered as a workspace asset), follow the [Custom Operator Onboarding](../SKILL.md#custom-operator-onboarding)
  pipeline in SKILL.md (five-phase: deploy-mode choice → code adaptation → Docker image
  build & SWR push / OBS code delivery → asset creation (image + algorithm) → runtime
  verification). After onboarding completes, the new algorithm will appear in the
  `list-assets` results above.

**4c. OBS Algorithm (OBS_ASSETS)**
- User-provided algorithm, no need to select from algorithm list.
- ✅ **Collect these 4 fields from user:**
  - **OBS Path** (`algo_path`) — OBS storage path for algorithm code/files
  - **Container Injection Path** (`job_local_path`) — Mount path for algorithm data in the container
  - **Runtime Image** (`image`) — Container image address (user input or selection)
  - **Startup Command** (`algo_entrance`) — Algorithm startup command (user input)
- ❌ **Do NOT ask for `algo_id`** — not needed for OBS algorithms (exception: onboarded
  代码放 OBS、运行时挂载 operators in 空间资产-算法 — see **4d**, which uses `WORKSPACE_ASSETS` + `algo_id` =
  the Phase 3 algorithm asset id, not `OBS_ASSETS`)
- ❌ **Do NOT ask for `algo_name`** — not needed for OBS algorithms (exception: onboarded
  代码放 OBS、运行时挂载 operators — see **4d**, where `algo_name` IS required)
- **`algo_type` in task-config must be set to `OBS_ASSETS`**

**4d. Custom Operator Tasks (onboarded operators)**

When the selected algorithm is an **onboarded custom operator** (SKILL.md §Custom
Operator Onboarding; full five-phase pipeline in
`custom-operator/custom-operator-workflow.md`), task creation follows the same 10-step flow with
these operator-specific differences (authoritative detail:
`custom-operator/onboarding-phase-4.md`):

- **Precondition (Phase 0-3)**: the operator must already be onboarded (deploy mode
  chosen, assets registered). If not registered yet, run the onboarding pipeline
  first (SKILL.md §Custom Operator Onboarding) — the new algorithm then appears in
  the Step-4 algorithm list.
- **Step 4 branch** (differs per deploy mode):
  - **把代码打进镜像 (image-inbuilt, `image_source=custom`)** — same as **4b WORKSPACE_ASSETS**:
    `algo_id` = algorithm `asset_id`, `algo_name` = `name`,
    `algo_entrance` = `ext_metadata.command`, `image` = `ext_metadata.engine.image_url`.
    No extra fields.
  - **代码放 OBS、运行时挂载 (OBS-mounted, `image_source=custom` when 空间资产-算法 links the image asset)** —
    **默认使用空间资产-算法**；仅当用户明确要求不注册资产、直接挂载代码时才用 OBS算法。
    - **默认 — 空间资产-算法 (`WORKSPACE_ASSETS`)** — `algo_id` = Phase 3 algorithm `asset_id` (asset
      linkage), `algo_name` (**required**), `algo_path` = asset `code_dir` (**required**),
      `job_local_path` (**required**), **absolute** `algo_entrance` =
      `python3 {job_local_path}/entrypoint.py`, `image` = asset
      `ext_metadata.engine.image_url`. Verified e2e — omitting `algo_path`/`job_local_path`
      fails with `//entrypoint.py`. Phase 3 asset registration runs.
    - **OBS算法 (`OBS_ASSETS`)** — `algo_name` (**required**) + `algo_path` (customer
      OBS path) + `job_local_path` (injection path); **do NOT pass `algo_id`**; Phase 3
      asset registration is **skipped**; `algo_entrance` MUST be **absolute**
      `python3 {job_local_path}/entrypoint.py` (relative `python entrypoint.py` fails
      with `stdbuf: ... Permission denied`).
- **Step 8 (input datasets) — 按推荐来源，仅在含糊时问**：
  ① 若恰好有一个匹配的已有数据集 → **直接复用（默认）**；多个 → 多选（≤10）；
  ② 否则从用户给的数据路径**自动新建**数据集（`create-asset type=dataset` +
  `create-version` + `update-version --status RELEASE`，版本必须 RELEASE）；
  ③ 仅当用户主动提供 `obs://` 路径时才用 OBS存储直挂。只有多个数据集都可能且选错代价高时才问。
- **Step 5 (envs)**: MUST **exclude platform-injected `SOURCE_DATASET_PATH`** — copying
  its fallback `default` into `envs` blocks the runtime injection and the task fails
  with `SOURCE_DATASET_PATH is not a valid JSON map`; keep only business env vars.
- **Step 10 (submit)**: create WITHOUT `--wait`, poll `show-task` with a progress
  heartbeat (`../scripts/poll-task.sh`); on FAILED run the failure analysis engine
  (`custom-operator/failure-analysis-guide.md`).

### Step 5: Configure environment variables
- Read algorithm's `ext_metadata.environment_variables`
- If environment variable definitions exist, display each variable's name, description, and default value. Let user confirm or modify
- If no environment variable definitions, ask user if they want to add custom environment variables
  - If user chooses not to add, skip this step
  - If user chooses to add, let user input custom key-value pairs
- Construct `envs` field (**Note:** must be JSON string format `"[{\"key\":\"K\",\"value\":\"V\"}]"`, not nested objects)

### Step 5b: Operator inputs (`ext_metadata.inputs`)
- Read `ext_metadata.inputs` from the **freshly queried** operator (do not reuse a previous query result)
- If the operator declares no `inputs` (absent or `null`), skip this step and omit the `inputs` field
- `required: true` inputs with a built-in `url_path`: no action needed, do not list them in `inputs`
- `required: true` inputs with an empty `url_path`: ask the user for an `obs://` directory path and include them in `inputs`
- `required: false` inputs: do not prompt unless the user asks for a custom mount (e.g. custom cleaning/manifest config) or the operator would otherwise fail
- Construct `inputs` as a JSON array **string**: each element is the complete `ext_metadata.inputs[]` element copied as returned, with only `url_path` set to the user-selected `obs://` path (never use an `obs_path` key). See `task-config-catalog.md` → "Operator Inputs Mount"
- A dataset need not include YAML: use supported built-in robot/default config, existing dataset config or a selected external mount. Only when file configuration is needed, follow the [manifest candidate rules](task-config-catalog.md#manifest-config-names); manifest mode alone does not require a file or evaluation robot description.

### Step 6: Job type, resource pool, and instance specification

> **默认不要逐项询问 6a–6e。** 套用推荐值并用一行说明
> （`资源：公共池，4c8g，单容器`）。仅当用户主动要求不同资源、或确实需要分布式/独享池时才问。

**6a — Job type** [default: Standard Container (CCE + K8S)]:
- Standard Container (CCE + K8S) — Single container job, **default**
- Ray Distributed (CCE_RAY + RAY) — Distributed job；仅当任务确实多机时才问

**6b — Resource pool type** [default: Public Resource Pool (PUBLIC_POOL)]:
- Public Resource Pool (PUBLIC_POOL) — **default**
- Dedicated Resource Pool (DEDICATED_POOL) — 仅当用户要求或公共池配额不足时

**6c — Query resource pools** (branches by type):
- **PUBLIC_POOL**:
  - Query shared resource pool: `cloudrobo resource list-pools --pool-type SHARED --resource-type CCE --resource-sub-type CPU --usages DATA_PROCESSING --limit 50`
  - **Note:** In CLI, public resource pool `--pool-type` value is `SHARED`, not `PUBLIC`
  - Shared resource pool typically has only one entry, no user selection needed
- **DEDICATED_POOL**:
  - Query dedicated resource pools: `cloudrobo resource list-pools --pool-type DEDICATED --resource-type CCE --resource-sub-type CPU --usages DATA_PROCESSING --limit 50`
  - **Display resource pools**: Show only `resource_name` (e.g., `pool-cpu-enduser-dataplane`), not `resource_id`
  - After user selection, extract `resource_id` and `resource_name` (→ `dedicated_pool_name`) from the selected item

**6d — Select instance specification** (must be performed regardless of resource pool type):
- Get available specification list from query result's `config.flavor.CPU`
- Display specification list for user selection

**6e — Select resource specification by job type** (⚠️ Critical: distinguish to avoid incorrect queries):

- **Single container job (CCE/K8S)**:
  - ✅ **Only need to select Worker resource specification** (`worker_spec`)
  - Display specification list (e.g., `2 vCPUs | 4 GiB`, `4 vCPUs | 8 GiB`, etc.) for user selection
  - Parse user's selected specification into `{"cpu": N, "memory": M, "gpu": 0, "npu": 0}` format
  - ❌ **Do not ask for worker_num**: Fixed at `1`, no need to ask
  - ❌ **Do not ask for head_spec**: Fixed at `{"cpu":0,"memory":0,"gpu":0,"npu":0}`, no need to ask

- **Distributed job (CCE_RAY/RAY)**:
  - Need to select Head resource specification (`head_spec`) and Worker resource specification (`worker_spec`)
  - Select Head resource specification first, then Worker resource specification
  - Parse user's selected specifications into `{"cpu": N, "memory": M, "gpu": 0, "npu": 0}` format
  - ✅ **Need to ask for worker_num** (default `1`)

### Step 7: Dynamic storage (public resource pool only)
- **Only when resource pool type is Public Resource Pool (PUBLIC_POOL)**, ask if dynamic storage (EVS) is needed
- **Dedicated Resource Pool (DEDICATED_POOL) does not need dynamic storage selection**, skip this step, `evs_spec: 0`
- Default is not needed (`evs_spec: 0`)
- If needed, ask for storage capacity (GB), set `evs_spec` to a non-zero value
- **Minimum capacity limit**: EVS capacity must be at least 10 GB. Inputs below 10 GB should be rejected with a prompt

### Step 8: Select input datasets (supports multiple datasets)

**⚠️ Special reminder (this step is most error-prone)**:
- After querying the dataset list, must first display the list in text, then in the **next turn** initiate **one** AskUserQuestion for selection.
- After user selects one dataset, in the **next turn** initiate **one** AskUserQuestion asking "Continue adding datasets?"
- Absolutely forbid asking both "which dataset to select" and "continue adding" in the same turn.
- Absolutely forbid executing Bash queries and initiating AskUserQuestion in the same turn.

**Multi-dataset loop flow**:
```
Loop start:
  1. Ask for data source type (Preset/Workspace/OBS)
  2. Query and display dataset list based on type
  3. User selects dataset, record configuration information
  4. Ask "Continue adding datasets?"
     - If user chooses "Continue adding" → Return to step 1
     - If user chooses "Don't add" → End loop, proceed to Step 9
```
- Must add at least 1 dataset, can add multiple
- Each dataset is configured independently, finally combined into `dataset_configs` array

For each dataset, ask for data source type:
- **Preset Dataset** (`PUBLIC_DATASET_ASSET`) — Platform public datasets
- **Workspace Asset Dataset** (`DATASET`) — Workspace custom datasets
- **OBS Storage** (`UDF_OBS_ASSET`) — User-specified OBS path

**8a. Preset Dataset (PUBLIC_DATASET_ASSET)**
- Query public dataset list: `cloudrobo asset list-publication-assets --type dataset --permissions data_read=allow,data_usable=allow`
- Display dataset list (name, description, update time)
- After user selection, extract `asset_id`, `name` → `asset_name`, `latest_version_id` → `version_id`
- **Get real dataset_path**: Use `cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>` to query, extract real `obs_path` from the result (the `url` field is not the real path)
- Set `dataset_type: "BUILD_IN_ASSET"`

**8b. Workspace Asset Dataset (DATASET)**
- Get workspace `catalog_id` (obtain `asset_catalog_id` from `cloudrobo workspace current`)
- Query workspace datasets: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type dataset --status DRAFT,ALPHA,BETA,RELEASE,STABLE,DEPRECATED,ARCHIVE`
- Display dataset list (name, description, update time). Since there may be many datasets (e.g., 494), display only the first few
- **Provide search functionality**: Offer "Search dataset name" option in AskUserQuestion. User can choose to select directly or search by name
  - If user chooses search, ask for search keyword
  - Use `--name` parameter to filter query
  - Display filtered results (usually fewer), let user select
- After user selection, extract `asset_id`, `name` → `asset_name`, `latest_version_id` → `version_id`
- **Get real dataset_path**: Use `cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>` to query version details
  - Extract `dataset_path` from the result (this is the real dataset path, not the `url` field in the list)
- Set `dataset_type: "BUILD_IN_ASSET"`

**8c. OBS Storage (UDF_OBS_ASSET)**
- Ask user to input OBS path (must start with `obs://`, end with `/`)
- ⚠️ **Workspace-bound bucket constraint**: the OBS path's **bucket MUST match the
  workspace-bound OBS bucket** — the bucket of `default_obs_path` (e.g.
  `obs://{default-bucket}/cloudrobo/{workspace_id}/`) from `cloudrobo workspace current`.
  Other OBS buckets are **not supported**. Always **display the workspace
  `default_obs_path` as the reference** when asking, so the user sees the expected bucket.
- Validate path format **and bucket**: parse `obs://<bucket>/...` and compare `<bucket>`
  with the `default_obs_path` bucket. **Mismatch → reject the path, show the expected
  bucket (`obs://<default-bucket>/`), and re-ask until the bucket matches** — never submit
  a task with a foreign-bucket `obs_path`.
- **Omit** `asset_id`, `asset_name`, `version_id` — do not include empty fields
- Set `dataset_type: "UDF_OBS_ASSET"`

**Construct dataset_configs**:
- For **BUILD_IN_ASSET**: `{"obs_path": "...", "dataset_type": "BUILD_IN_ASSET", "asset_id": "...", "asset_name": "...", "version_id": "..."}`
- For **UDF_OBS_ASSET**: `{"obs_path": "...", "dataset_type": "UDF_OBS_ASSET"}` — only `obs_path` and `dataset_type`, no empty fields
- Combine all dataset objects into a JSON array string, assign to `dataset_configs` field

### Step 9: Configure output

**9a — Output type**: Ask for output type (`output_type`):
- **Workspace Asset Data** (`BUILD_IN_ASSET`) — Output as workspace asset
- **Object Storage Service OBS** (`UDF_OBS_ASSET`) — Output to OBS path

**9b — Output path** (branches by output type):
- **BUILD_IN_ASSET**: Automatically use workspace default path. Obtain `default_obs_path` from `cloudrobo workspace current`, concatenate `cloudrobo/<workspace_id>/` prefix. No need to ask user.
- **UDF_OBS_ASSET**: Ask user to input OBS path (`output_path`). Must start with `obs://` and end with `/`.
  - ⚠️ **Workspace-bound bucket constraint (same as input datasets)**: the `output_path`
    bucket **MUST match the workspace-bound OBS bucket** (`default_obs_path` from
    `cloudrobo workspace current`); other OBS buckets are not supported. Validate the
    bucket: mismatch → reject, show `obs://<default-bucket>/`, re-ask until it matches.

**9c — Output dataset name** (REQUIRED for BOTH output types):
- Ask user to input output dataset name (`output_name`). Default uses task name.
- This step applies to both BUILD_IN_ASSET and UDF_OBS_ASSET output types.

### Step 10: Confirm and submit
- Assemble complete task-config JSON
- **Validate non-empty fields**: Ensure all required fields (except `description`) are present and non-empty. Specifically check:
  - `head_spec`/`worker_spec` include `cpu` and `memory` keys (add `gpu`/`npu` as `0` when unused)
  - String fields (e.g., `algo_name`, `algo_entrance`, `image`, `catalog_id`, `output_path`, `output_name`) are not empty
  - `dataset_configs` is a valid JSON string array with at least 1 dataset entry (empty array `"[]"` is invalid)
  - `envs` (if present) is a non-empty JSON string array with `key`/`value`/`description` fields
  - `inputs` (if present) is a JSON string array of complete operator input elements with `url_path` set; omit the field instead of sending `"[]"` (not enforced by the CLI validator)
- Display a **short confirmation summary** (no internal identifiers, no enum values).
  Render it in the user's language; the template below is the English reference:

  ```
  准备执行：
    任务     <name>
    处理      <algorithm display name>
    输入     <dataset name>（<n> 个文件/轨迹）
    资源     公共池，4c8g，单容器（默认）
    输出     <output name>

  提交？
  ```

  Omit lines that do not apply. Do **not** print `CCE/K8S`, `PUBLIC_POOL`, `worker_spec`,
  `evs_spec`, `dataset_configs`, asset IDs, or OBS paths unless the user asks for details
  (`需要技术细节吗？`).
- **Submit immediately after displaying summary**: Use AskUserQuestion to ask "Confirm submission" (options: Confirm submission / Need modification). After user confirms, execute `cloudrobo dataset proc create-task --name <name> --algo-type PRESET_ASSETS --task-config '<json>'`
- Do not ask in multiple steps. Display summary + ask confirmation + submit should be completed in the same turn
- Do NOT use `--wait`; return control to user after creation

---

## Eval-Task Creation (7 steps)

When the user requests creating a data evaluation task without providing complete parameters, follow these steps sequentially.

### Step 1: Task name
- Prompt the user to input a task name. Do not provide any options.
- Wait for user input before proceeding.
- Do not combine with description or other fields in the same interaction turn.

### Step 2: Task description
- Prompt the user to input a task description. Do not provide any options.
- Wait for user input before proceeding.
- Do not combine with task name or other fields in the same interaction turn.

### Step 3: Resource pool and instance specification

**3a — Resource pool type**: Ask for resource pool type:
- Public Resource Pool (PUBLIC_POOL) — Default
- Dedicated Resource Pool (DEDICATED_POOL) — Requires additional resource pool query

**3b — Query resource pools** (branches by type):
- **PUBLIC_POOL**:
  - Query shared resource pool: `cloudrobo resource list-pools --pool-type SHARED --resource-type CCE --resource-sub-type CPU --usages DATA_PROCESSING --limit 50`
  - **Note:** In CLI, public resource pool `--pool-type` value is `SHARED`, not `PUBLIC`
  - Shared resource pool typically has only one entry, no user selection needed
- **DEDICATED_POOL**:
  - Query dedicated resource pools: `cloudrobo resource list-pools --pool-type DEDICATED --resource-type CCE --resource-sub-type CPU --usages DATA_PROCESSING --limit 50`
  - **Display resource pools**: Show only `resource_name` (e.g., `pool-cpu-enduser-dataplane`), not `resource_id`
  - After user selection, extract `resource_id` and `resource_name` (→ `dedicated_pool_name`) from the selected item

**3c — Select instance specification** (must be performed regardless of resource pool type):
- Get available specification list from query result's `config.flavor.CPU` or `config.flavor.GPU` array
- Display specification list for user selection
- Record specification value after user selection

### Step 4: Select evaluation algorithm
- Query available evaluation algorithms: `cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation"`
- Display algorithm list (name, description, update time)
- Extract algorithm information after user selection (same field mapping as proc-task):
  - `asset_id` → `algo_id`
  - `name` → `algo_name`
  - `ext_metadata.command` → `algo_entrance`
  - `ext_metadata.engine.image_url` → `image`

### Step 4b: Operator inputs (`ext_metadata.inputs`)
- Same rules as proc Step 5b: read `ext_metadata.inputs` from the freshly queried evaluation operator; skip if none are declared
- Required inputs with a built-in `url_path` need no action; required inputs with an empty `url_path` must be supplied by the user
- Do not prompt for optional inputs (e.g. `ROBOT_CONFIG_PATH`) unless the user asks or the operator would otherwise fail
- Construct `inputs` as a JSON array string of complete input elements with `url_path` set

### Step 5: Select dataset (single)
First ask for dataset source type:
- **Workspace Asset Data** (`BUILD_IN_ASSET`) — Select from workspace datasets
- **Object Storage Service OBS** (`UDF_OBS_ASSET`) — User-specified OBS path

**5a. Workspace Asset Data (BUILD_IN_ASSET)**
- Get workspace `catalog_id` (obtain `asset_catalog_id` from `cloudrobo workspace current`)
- Query workspace datasets: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type dataset --status DRAFT,ALPHA,BETA,RELEASE,STABLE,DEPRECATED,ARCHIVE`
- Display dataset list (name, description, update time). Since there may be many datasets, display only the first few
- **Provide search functionality**: Offer "Search dataset name" option in AskUserQuestion
  - If user chooses search, ask for search keyword
  - Use `--name` parameter to filter query
- After user selection, extract `asset_id`, `name` → `asset_name`, `latest_version_id` → `version_id`
- **Get real dataset_path**: Use `cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>` to query version details
  - Extract `dataset_path` from the result (this is the real dataset path, not the `url` field in the list)
- Set `dataset_type: "BUILD_IN_ASSET"`

**5b. Object Storage Service OBS (UDF_OBS_ASSET)**
- Ask user to input OBS path (must start with `obs://`, end with `/`)
- ⚠️ **Workspace-bound bucket constraint**: the path's **bucket MUST match the
  workspace-bound OBS bucket** (the bucket of `default_obs_path` from
  `cloudrobo workspace current`); other OBS buckets are **not supported**. Display the
  workspace `default_obs_path` as the reference when asking.
- Validate path format **and bucket**: mismatch → reject, show the expected bucket
  (`obs://<default-bucket>/`), and **re-ask until the bucket matches**
- Ask user to input dataset name (`dataset_name`)
- Set `dataset_type: "UDF_OBS_ASSET"`
- `dataset_id` is not required for UDF_OBS_ASSET

**Eval uses top-level dataset fields and a single-item `dataset_configs` JSON-array string.**
For asset input, copy the verified `asset_id`, `asset_name`, `version_id`, `obs_path` and
`dataset_type` into the entry; keep top-level ID/name/path/type consistent. For direct OBS
input, the entry needs only type and path, without invented asset/version IDs.
See [version handoff](task-config-catalog.md#dataset-version-handoff).

### Step 6: Optional robot description and metric scope
- Do not ask for a robot description by default. If the user selects one or requested metrics need it, collect its actual OBS directory path and mount it through the operator's declared input (e.g. `ROBOT_CONFIG_PATH`, Step 4b).
- Otherwise omit the mount and run with the operator's built-in/default configuration; explain any robot-dependent metrics that will not be covered. Manifest mode does not make this path mandatory.
- `robot_config` has been removed from eval tasks; never send it. If an outdated CLI/SDK still requires it, upgrade the client ([config mount guidance](task-config-catalog.md#eval-robot-config-compatibility)); never fabricate a path or use an unrelated dataset directory.

### Step 7: Confirm and submit
- **Validate non-empty fields**: Ensure common required fields are present and non-empty: `name`, `algo_id`, `algo_name`, `algo_entrance`, `image`, `dataset_type`, `dataset_name`, `dataset_path`, `dataset_configs`, `resource_pool_type`, `worker_spec` (plus `dataset_id` when `dataset_type=BUILD_IN_ASSET`). Check each asset entry has an exact `version_id` and matches the top-level identity. Do not include the removed `robot_config`. `worker_spec` must include `cpu`/`memory` keys. `inputs` (if present) follows the same rules as proc Step 10.
- Display the same **short confirmation summary** as proc Step 10 (no IDs, no enum values).
  After user confirmation, execute `cloudrobo dataset eval create-task --name <name> --task-config '<json>'`
- Do NOT use `--wait`; return control to user after creation
