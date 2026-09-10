# cloudrobo-robot 参数校验规则参考

> 本文件由 cloudrobo-client/scripts/gen_schemas.py 从根
> pilot-manager.yaml 自动生成（存在根时以根为准，各包 robo-operations.yaml
> 是其分发视图）。请勿手动修改；修改请改根 yaml 后重新生成。

## create-robot

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `description` | string | 否 | 0-512 字符；pattern | CreateRobotRequestBody.description |
| `manufacturer` | string | 是 | 1-64 字符 | CreateRobotRequestBody.manufacturer |
| `name` | string | 是 | 3-64 字符；pattern | CreateRobotRequestBody.name |
| `robot_model` | string | 是 | 1-64 字符 | CreateRobotRequestBody.robot_model |
| `type` | string | 是 | `ARM` `HUMANOID` `OPERATION` `OTHER` `QUADRUPED` `WHEELED`；1-32 字符 | CreateRobotRequestBody.type |
| `workspace_id` | string | 是 | 1-64 字符 | CreateRobotRequestBody.workspace_id |


## update-robot

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `description` | string | 否 | 0-512 字符；pattern | UpdateRobotRequestBody.description |
| `name` | string | 否 | 3-64 字符；pattern | UpdateRobotRequestBody.name |
| `workspace_id` | string | 是 | 1-64 字符 | UpdateRobotRequestBody.workspace_id |


## export-certificate-robot

### 字段校验

| 字段 | 类型 | 必填 | 枚举/约束 | Source(yaml) |
|------|------|------|-----------|--------------|
| `password` | string | 否 | 0-32 字符 | ExportRobotCertificateRequestBody.password |

