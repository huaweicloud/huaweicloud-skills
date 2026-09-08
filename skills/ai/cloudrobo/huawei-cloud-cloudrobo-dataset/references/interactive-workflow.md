# Interactive Workflow

## Interaction Rules

- At most **one tool call** per turn
- Display query results **before** asking the next question
- Forbid initiating multiple AskUserQuestion calls in parallel
- Forbid executing Bash queries and AskUserQuestion in the same turn

## Proc-Task Creation (10 steps)

When the user requests creating a data processing task without providing complete parameters, follow these steps sequentially. If the user provides all parameters upfront, skip the workflow and proceed directly to assemble the configuration and confirm submission.

### Step 1: Task name
- Prompt the user to input a task name. Do not provide any options.
- Wait for user input before proceeding.
- Do not combine with description or other fields in the same interaction turn.

### Step 2: Task description
- Prompt the user to input a task description. Do not provide any options.
- Wait for user input before proceeding.
- Do not combine with task name or other fields in the same interaction turn.

### Step 3: Select algorithm type
Ask for algorithm type (`algo_type` field), presenting these 3 options:
- **Preset Algorithm** (`PRESET_ASSETS`) — Platform built-in public algorithms, default option
- **Workspace Asset Algorithm** (`WORKSPACE_ASSETS`) — Workspace custom algorithms
- **OBS Algorithm** (`OBS_ASSETS`) — User-provided algorithms, injected into containers via OBS path

After user selection, proceed to Step 4 (subsequent steps differ by algorithm type).

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
- Query and display algorithm list: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type algorithm`
- **Note:** Do not add `--tags "Data Processing"` filter; workspace algorithms may not have the tags field set
- Display algorithm list (name, description, update time). Since there may be many algorithms, display only the first few
- **Provide search functionality**: Offer "Search algorithm name" option in AskUserQuestion
  - If user chooses search, ask for search keyword
  - Use `--name` parameter to filter: `cloudrobo asset list-assets --catalog-id <workspace-catalog-id> --type algorithm --name <keyword>`
- After user selection, extract field mappings from `ext_metadata`:
  - `asset_id` → `algo_id`
  - `name` → `algo_name`
  - `ext_metadata.command` → `algo_entrance`
  - `ext_metadata.engine.image_url` → `image`
- **Additional step**: Ask for container injection path (`data_mount_path`), i.e., the mount path for algorithm data in the container

**4c. OBS Algorithm (OBS_ASSETS)**
- User-provided algorithm, no need to select from algorithm list.
- ✅ **Collect these 4 fields from user:**
  - **OBS Path** (`algo_path`) — OBS storage path for algorithm code/files
  - **Container Injection Path** (`job_local_path`) — Mount path for algorithm data in the container
  - **Runtime Image** (`image`) — Container image address (user input or selection)
  - **Startup Command** (`algo_entrance`) — Algorithm startup command (user input)
- ❌ **Do NOT ask for `algo_id`** — not needed for OBS algorithms
- ❌ **Do NOT ask for `algo_name`** — not needed for OBS algorithms
- **`algo_type` in task-config must be set to `OBS_ASSETS`**

### Step 5: Configure environment variables
- Read algorithm's `ext_metadata.environment_variables`
- If environment variable definitions exist, display each variable's name, description, and default value. Let user confirm or modify
- If no environment variable definitions, ask user if they want to add custom environment variables
  - If user chooses not to add, skip this step
  - If user chooses to add, let user input custom key-value pairs
- Construct `envs` field (**Note:** must be JSON string format `"[{\"key\":\"K\",\"value\":\"V\"}]"`, not nested objects)

### Step 6: Job type, resource pool, and instance specification

**6a — Job type**: Ask for job type (`cluster_type` + `task_framework_type` must be paired):
- Standard Container (CCE + K8S) — Single container job, default
- Ray Distributed (CCE_RAY + RAY) — Distributed job

**6b — Resource pool type**: Ask for resource pool type:
- Public Resource Pool (PUBLIC_POOL) — Default
- Dedicated Resource Pool (DEDICATED_POOL) — Requires additional resource pool query

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
- Validate path format
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

**9c — Output dataset name** (REQUIRED for BOTH output types):
- Ask user to input output dataset name (`output_name`). Default uses task name.
- This step applies to both BUILD_IN_ASSET and UDF_OBS_ASSET output types.

### Step 10: Confirm and submit
- Assemble complete task-config JSON
- **Validate non-empty fields**: Ensure all required fields (except `description`) are present and non-empty. Specifically check:
  - `head_spec` includes `cpu`, `memory`, `gpu`, `npu` keys (value `0` is valid)
  - `worker_spec` includes `cpu`, `memory`, `gpu`, `npu` keys
  - String fields (e.g., `algo_name`, `algo_entrance`, `image`, `catalog_id`, `output_path`, `output_name`) are not empty
  - `dataset_configs` is a valid JSON string array with at least 1 dataset entry (empty array `"[]"` is invalid)
  - `envs` (if present) is a non-empty JSON string array with `key`/`value`/`description` fields
- Display configuration summary for user confirmation:
  ```
  ==================== Task Configuration to Submit ====================
  Task Name: xxx
  Description: xxx
  Algorithm: xxx
  Environment Variables: xxx (or "None")
  Job Type: CCE/K8S
  Resource Pool: PUBLIC_POOL
  Worker Spec: 2CPU/4GB x 1
  Dynamic Storage: 0 GB
  Input Datasets: xxx
  Output Type: xxx
  Output Name/Path: xxx
  ========================================================================
  ```
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
- Ask user to input dataset name (`dataset_name`)
- Set `dataset_type: "UDF_OBS_ASSET"`
- For `dataset_configs` entry: only include `obs_path` and `dataset_type` (omit empty `asset_id`/`version_id`)

**Both top-level fields** (`dataset_type`, `dataset_id`, `dataset_name`, `dataset_path`) **and `dataset_configs` array must be populated.**

### Step 6: Configure robot description file
- Ask for `robot_config` path (OBS path)
- `robot_config` is required for eval-tasks, cannot skip

### Step 7: Confirm and submit
- **Validate non-empty fields**: Ensure all required fields (except `description`) are present and non-empty. `head_spec`/`worker_spec` must include `cpu`/`memory`/`gpu`/`npu` keys. `robot_config` must not be empty.
- Display configuration summary. After user confirmation, execute `cloudrobo dataset eval create-task --name <name> --task-config '<json>'`
- Do NOT use `--wait`; return control to user after creation
