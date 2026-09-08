# cloudrobo-dispatch 参数校验规则参考

> 本文件由 cloudrobo-client/scripts/gen_schemas.py 从根
> pilot-manager.yaml 自动生成（存在根时以根为准，各包 robo-operations.yaml
> 是其分发视图）。请勿手动修改；修改请改根 yaml 后重新生成。

## create-task-dispatch

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `constraints` | object | 是 | - | CreateDispatcherTaskRequestBody.constraints |
| `name` | string | 是 | 1-1024 字符 | CreateDispatcherTaskRequestBody.name |
| `task` | string | 是 | 1-1024 字符 | CreateDispatcherTaskRequestBody.task |

### constraints

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `exec_constraints` | object | 否 | - | CreateDispatcherTaskRequestBody.constraints.exec_constraints |
| `model` | object | 是 | - | CreateDispatcherTaskRequestBody.constraints.model |
| `robot_id` | string | 是 | 1-64 字符 | CreateDispatcherTaskRequestBody.constraints.robot_id |

#### constraints.exec_constraints

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `max_iter_num` | integer | 否 | 1-300000 | CreateDispatcherTaskRequestBody.constraints.exec_constraints.max_iter_num |
| `max_run_time` | integer | 否 | 1-300 | CreateDispatcherTaskRequestBody.constraints.exec_constraints.max_run_time |

#### constraints.model

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `exec_model_id` | string | 是 | 1-64 字符 | CreateDispatcherTaskRequestBody.constraints.model.exec_model_id |

