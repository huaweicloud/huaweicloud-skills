# cloudrobo-infer 参数校验规则参考

> 本文件由 cloudrobo-client/scripts/gen_schemas.py 从根
> pilot-manager.yaml 自动生成（存在根时以根为准，各包 robo-operations.yaml
> 是其分发视图）。请勿手动修改；修改请改根 yaml 后重新生成。

## create-infer

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `cmd` | string | 否 | 0-1024 字符 | CreateInferenceServiceRequestBody.cmd |
| `deploy_timeout_minutes` | integer | 否 | 1-300 | CreateInferenceServiceRequestBody.deploy_timeout_minutes |
| `description` | string | 否 | 0-512 字符；pattern | CreateInferenceServiceRequestBody.description |
| `envs` | object | 否 | 最多 100 键 | CreateInferenceServiceRequestBody.envs |
| `files` | array | 否 | 最多 10 项 | CreateInferenceServiceRequestBody.files |
| `flavor` | string | 是 | 1-64 字符 | CreateInferenceServiceRequestBody.flavor |
| `image_swr_url` | string | 否 | 0-1024 字符；pattern | CreateInferenceServiceRequestBody.image_swr_url |
| `internet_access_enable` | boolean | 否 | - | CreateInferenceServiceRequestBody.internet_access_enable |
| `liveness_health` | object | 否 | - | CreateInferenceServiceRequestBody.liveness_health |
| `model` | object | 是 | - | CreateInferenceServiceRequestBody.model |
| `model_ext_metadata` | string | 否 | 0-20480 字符；JSON/YAML 字符串 | CreateInferenceServiceRequestBody.model_ext_metadata |
| `name` | string | 是 | 3-64 字符；pattern | CreateInferenceServiceRequestBody.name |
| `pool_id` | string | 是 | 0-64 字符 | CreateInferenceServiceRequestBody.pool_id |
| `pool_type` | string | 是 | `DEDICATED` `SHARED`；0-16 字符 | CreateInferenceServiceRequestBody.pool_type |
| `readiness_health` | object | 否 | - | CreateInferenceServiceRequestBody.readiness_health |
| `service_invoke` | object | 否 | - | CreateInferenceServiceRequestBody.service_invoke |
| `skill_config` | object | 否 | - | CreateInferenceServiceRequestBody.skill_config |
| `startup_health` | object | 否 | - | CreateInferenceServiceRequestBody.startup_health |
| `stop_schedule` | object | 否 | - | CreateInferenceServiceRequestBody.stop_schedule |
| `workspace_id` | string | 是 | 1-64 字符 | CreateInferenceServiceRequestBody.workspace_id |

### files[]

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `address` | string | 否 | 1-512 字符；pattern | CreateInferenceServiceRequestBody.item.address |
| `host_cache` | boolean | 否 | - | CreateInferenceServiceRequestBody.item.host_cache |
| `mount_path` | string | 否 | 1-512 字符；pattern | CreateInferenceServiceRequestBody.item.mount_path |
| `os_warm_up` | boolean | 否 | - | CreateInferenceServiceRequestBody.item.os_warm_up |
| `source` | string | 否 | `OBS`；1-16 字符 | CreateInferenceServiceRequestBody.item.source |

### liveness_health

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `check_method` | string | 否 | `EXEC` `HTTP`；1-10 字符 | CreateInferenceServiceRequestBody.liveness_health.check_method |
| `cmd` | string | 否 | 0-1024 字符；pattern | CreateInferenceServiceRequestBody.liveness_health.cmd |
| `failure_threshold` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.liveness_health.failure_threshold |
| `initial_delay_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.liveness_health.initial_delay_seconds |
| `period_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.liveness_health.period_seconds |
| `protocol` | string | 否 | `HTTP` `HTTPS` | CreateInferenceServiceRequestBody.liveness_health.protocol |
| `timeout_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.liveness_health.timeout_seconds |
| `url` | string | 否 | 1-1024 字符；pattern | CreateInferenceServiceRequestBody.liveness_health.url |

### model

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `model_id` | string | 是 | 1-64 字符 | CreateInferenceServiceRequestBody.model.model_id |
| `model_version_id` | string | 是 | 1-64 字符 | CreateInferenceServiceRequestBody.model.model_version_id |
| `mount_path` | string | 否 | 1-512 字符；pattern | CreateInferenceServiceRequestBody.model.mount_path |

### readiness_health

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `check_method` | string | 否 | `EXEC` `HTTP`；1-10 字符 | CreateInferenceServiceRequestBody.readiness_health.check_method |
| `cmd` | string | 否 | 0-1024 字符；pattern | CreateInferenceServiceRequestBody.readiness_health.cmd |
| `failure_threshold` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.readiness_health.failure_threshold |
| `initial_delay_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.readiness_health.initial_delay_seconds |
| `period_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.readiness_health.period_seconds |
| `protocol` | string | 否 | `HTTP` `HTTPS` | CreateInferenceServiceRequestBody.readiness_health.protocol |
| `timeout_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.readiness_health.timeout_seconds |
| `url` | string | 否 | 1-1024 字符；pattern | CreateInferenceServiceRequestBody.readiness_health.url |

### service_invoke

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `auth_type` | string | 是 | `API_KEY` `NONE`；1-16 字符 | CreateInferenceServiceRequestBody.service_invoke.auth_type |
| `port` | integer | 是 | 1024-65535 | CreateInferenceServiceRequestBody.service_invoke.port |
| `protocol` | string | 是 | `HTTP` `HTTPS` `WS` `WSS`；1-8 字符 | CreateInferenceServiceRequestBody.service_invoke.protocol |

### skill_config

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `skills` | array | 否 | 最多 50 项 | CreateInferenceServiceRequestBody.skill_config.skills |
| `strict` | boolean | 否 | - | CreateInferenceServiceRequestBody.skill_config.strict |

#### skill_config.skills[]

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `name` | string | 是 | 1-64 字符；pattern | CreateInferenceServiceRequestBody.skill_config.item.name |
| `prompt` | string | 是 | 1-1024 字符 | CreateInferenceServiceRequestBody.skill_config.item.prompt |

### startup_health

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `check_method` | string | 否 | `EXEC` `HTTP`；1-10 字符 | CreateInferenceServiceRequestBody.startup_health.check_method |
| `cmd` | string | 否 | 0-1024 字符；pattern | CreateInferenceServiceRequestBody.startup_health.cmd |
| `failure_threshold` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.startup_health.failure_threshold |
| `initial_delay_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.startup_health.initial_delay_seconds |
| `period_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.startup_health.period_seconds |
| `protocol` | string | 否 | `HTTP` `HTTPS` | CreateInferenceServiceRequestBody.startup_health.protocol |
| `timeout_seconds` | integer | 否 | 1-2147483647 | CreateInferenceServiceRequestBody.startup_health.timeout_seconds |
| `url` | string | 否 | 1-1024 字符；pattern | CreateInferenceServiceRequestBody.startup_health.url |

### stop_schedule

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `duration` | integer | 是 | 1-10080 | CreateInferenceServiceRequestBody.stop_schedule.duration |
| `time_unit` | string | 是 | `DAYS` `HOURS` `MINUTES`；1-16 字符 | CreateInferenceServiceRequestBody.stop_schedule.time_unit |


## update-infer

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `description` | string | 否 | 0-512 字符；pattern | UpdateInferenceServiceRequestBody.description |
| `model_ext_metadata` | string | 否 | 0-20480 字符；JSON/YAML 字符串 | UpdateInferenceServiceRequestBody.model_ext_metadata |


## list-logs-infer

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `end_time` | integer | 是 | 0-32503680000000 | ListInferenceServiceLogsRequestBody.end_time |
| `highlight` | boolean | 否 | - | ListInferenceServiceLogsRequestBody.highlight |
| `is_count` | boolean | 否 | - | ListInferenceServiceLogsRequestBody.is_count |
| `is_desc` | boolean | 否 | - | ListInferenceServiceLogsRequestBody.is_desc |
| `keywords` | string | 否 | 0-256 字符 | ListInferenceServiceLogsRequestBody.keywords |
| `limit` | integer | 否 | 1-5000 | ListInferenceServiceLogsRequestBody.limit |
| `line_num` | string | 否 | 0-128 字符 | ListInferenceServiceLogsRequestBody.line_num |
| `start_time` | integer | 是 | 0-32503680000000 | ListInferenceServiceLogsRequestBody.start_time |

