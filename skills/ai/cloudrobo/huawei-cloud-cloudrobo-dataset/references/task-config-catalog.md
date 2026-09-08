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

## algo_type Values

| Algorithm Source          | algo_type Value    | Required Fields                                                                                                 |
|---------------------------|--------------------|-----------------------------------------------------------------------------------------------------------------|
| Preset algorithm          | `PRESET_ASSETS`    | `algo_id`, `algo_name`, `algo_entrance`, `image` (extract from operator ext_metadata)                           |
| Workspace asset algorithm | `WORKSPACE_ASSETS` | `algo_id`, `algo_name`, `algo_entrance`, `image` (extract from workspace operator ext_metadata)                 |
| OBS algorithm             | `OBS_ASSETS`       | `algo_path`, `job_local_path`, `algo_entrance`, `image` (provided by user); `algo_id` must be valid UUID format |

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

## dataset_configs Field (Multiple Dataset Input)

`dataset_configs` is a **string field** in task_config, value is a string representation of JSON array, supports
multiple dataset input. Each item structure:

```json
[
  {
    "obs_path": "obs://bucket/path/to/data",
    "dataset_type": "UDF_OBS_ASSET",
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
| Dataset input        | `dataset_configs` (JSON string array, multiple datasets) | `dataset_configs` (same as proc, single dataset)      |
| robot_config         | Not needed                                               | **Must provide**                                      |
| Deletion granularity | Single (`delete-task --task-id`)                         | Single (`delete-task --task-id`)                      |
| restart              | Supported                                                | Not supported                                         |
| Resource monitoring  | Supported (`get-resource-usage`)                         | Not supported                                         |
| Report preview       | Not supported                                            | Supported (`get-preview --file-name [--is-download]`) |

## Update Limitations

Update interface (`update-task`) for both proc-tasks and eval-tasks only allows modifying `name` and `description`
fields, other fields cannot be updated.

## Non-Empty Validation Rule

**Except `description`, all parameters cannot be empty values.** The SDK (`DatasetClient.create_task` /
`create_eval_task`) validates before API submission:

- **Missing fields**: Required fields must be present in task_config
- **Empty string**: String fields (e.g., `name`, `algo_name`, `algo_entrance`, `image`, `catalog_id`, `output_path`,
  `output_name`) cannot be `""` or whitespace-only
- **Empty dict**: `head_spec` and `worker_spec` cannot be `{}` — must contain `cpu`, `memory`, `gpu`, `npu` keys
- **Missing spec keys**: `head_spec`/`worker_spec` must include all four keys: `cpu`, `memory`, `gpu`, `npu` (value can
  be `0`)
- **Numeric zero is valid**: `worker_num: 1`, `evs_spec: 0`, `cpu: 0` are valid non-empty values
- **Empty dataset_configs is invalid**: `"[]"` (empty array) is not acceptable, it must be contained at leat one
  dataset.
- **`envs` optional but non-empty if present**: If `envs` field is included, it must be a non-empty JSON string array

**algo_type-specific required fields:**

| algo_type          | Additional required fields    | Not required                               |
|--------------------|-------------------------------|--------------------------------------------|
| `PRESET_ASSETS`    | `algo_id`                     | —                                          |
| `WORKSPACE_ASSETS` | `algo_id`                     | —                                          |
| `OBS_ASSETS`       | `algo_path`, `job_local_path` | `algo_id` (must be valid UUID if provided) |
