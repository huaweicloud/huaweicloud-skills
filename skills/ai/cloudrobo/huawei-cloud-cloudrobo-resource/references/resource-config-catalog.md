# Resource Config Reference 资源配置参考

## Source 来源

All field definitions are derived from **SDK source code** (`client.py`), **server VOs**
(`QuotaVo.java`, `DomainQuotaVo.java`, `ResourceVo.java`, `NodeInfo.java`, `PageInfo.java`),
**entities** (`Spec.java`), and **OpenAPI spec** (`api/resource.yaml`).

## Enum Types 枚举类型

### ResourceType

| Value | Description |
|-------|-------------|
| `CCE` | CCE cluster resource |
| `MODELARTS` | ModelArts workspace resource |

### ResourceSubType

| Value | Description | Applicable ResourceType |
|-------|-------------|------------------------|
| `CPU` | CPU compute | CCE |
| `GPU` | GPU compute | CCE |
| `STANDARD` | Standard pool | MODELARTS |
| `LITE` | Lite pool | MODELARTS |

### ResourceStatus

| Value | Description |
|-------|-------------|
| `AVAILABLE` | Resource is available |
| `UNAVAILABLE` | Resource is unavailable |

### PoolType

| Value | Description |
|-------|-------------|
| `DEDICATED` | Dedicated resource pool |
| `SHARED` | Shared resource pool |

## Core Value Objects 核心值对象

### Spec

| Field | Type | JSON Key | Description |
|-------|------|----------|-------------|
| cpu | Float | `cpu` | CPU cores |
| memory | Float | `memory` | Memory in GB |
| gpu | Float | `gpu` | GPU cards |
| npu | Integer | `npu` | NPU chips |

### QuotaVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| quotaId | `quota_id` | String (UUID) | Quota ID |
| quotaName | `quota_name` | String | Quota name |
| resourceType | `resource_type` | ResourceType | Resource type |
| resourceSubType | `resource_sub_type` | ResourceSubType | Resource sub-type |
| domainId | `domain_id` | String | Domain ID |
| resourceId | `resource_id` | String (UUID) | Resource ID |
| resourceName | `resource_name` | String | Resource name |
| workspaceId | `workspace_id` | String (UUID) | Workspace ID |
| nodes | `nodes` | List\<NodeInfo\> | Node info list (nullable) |
| totalSpec | `total_spec` | Spec | Total spec |
| usedSpec | `used_spec` | Spec | Used spec |
| availableSpec | `available_spec` | Spec | Available spec |
| config | `config` | Object | Config info (nullable) |
| createAt | `create_at` | Long | Create timestamp (ms) |
| updateAt | `update_at` | Long | Update timestamp (ms, nullable) |
| poolType | `pool_type` | PoolType | Pool type |

### DomainQuotaVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| resourceType | `resource_type` | String | Resource type |
| resourceSubType | `resource_sub_type` | String | Resource sub-type |
| totalSpec | `total_spec` | Spec | Domain total spec |
| usedSpec | `used_spec` | Spec | Domain used spec |
| availableSpec | `available_spec` | Spec | Domain available spec |

### ResourceVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| resourceId | `resource_id` | String (UUID) | Resource ID |
| resourceName | `resource_name` | String | Resource name |
| resourceType | `resource_type` | ResourceType | Resource type |
| resourceSubType | `resource_sub_type` | ResourceSubType | Resource sub-type |
| nodes | `nodes` | List\<NodeInfo\> | Node info list (nullable) |
| config | `config` | Object | Config info |
| status | `status` | ResourceStatus | Resource status |
| description | `description` | String | Description (nullable) |
| usages | `usages` | List\<String\> | Usage list |
| poolType | `pool_type` | String | Pool type |
| createAt | `create_at` | long | Create timestamp (ms) |

### NodeInfo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| name | `name` | String | Node name |
| status | `status` | String | Node status |
| resources | `resources` | Number | Total node resources |
| availableResources | `available_resources` | Number | Available node resources |
| labels | `labels` | Map\<String, String\> | Node labels (nullable) |

### PageInfo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| offset | `offset` | int | Pagination offset |
| currentCount | `current_count` | int | Current page count |
| total | `total` | long | Total record count |

## Quota Calculation Rules 配额计算规则

| ResourceType | Counted Fields | Zeroed Fields |
|--------------|---------------|---------------|
| CCE | cpu, memory, gpu | npu = 0 |
| MODELARTS | npu | cpu = 0, memory = 0, gpu = 0 |

## Validation Rules 校验规则

| Field | Pattern/Constraint | Applicable To |
|-------|-------------------|---------------|
| `pool_id` | UUID pattern | Resource pool show |
| `workspace_id` | UUID pattern | Quota list filter |
| `resource_id` | UUID pattern | Quota list filter |
| `limit` | 1-50 | All list operations |
| `offset` | ≥ 0 | All list operations |
