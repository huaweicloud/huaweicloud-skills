# IAM 权限策略

## 最小权限集

RDS 主备倒换演练所需的最小权限（授权项名称经华为云官方 [身份策略授权参考](https://support.huaweicloud.com/api-rds/rds_10_0008.html) 逐一核实）：

> **别名 ≠ 依赖项**：华为云 IAM 授权项表有六列（授权项 | 访问级别 | 资源类型 | 条件键 | 别名 | 依赖的授权项）。
> 「别名」是同一权限的替代写法——策略中写主名或别名任意一个即可生效，**无需同时授予**。
> 「依赖的授权项」才是必须额外单独授予的前置权限。经核实，以下所有 API 的依赖项均为 `-`（无依赖）。

### 必需权限

| 权限动作 | 说明 | 资源类型 | 别名 | Resource 范围 |
|---------|------|---------|------|---------|
| `rds:instance:listAll` | 查询实例列表 + 存储空间（ListInstances / ShowStorageUsedSpace） | `-` | `rds:instance:list` | `*`（不支持资源级授权） |
| `rds:instance:getReplicaStatus` | 查询主备复制状态（ShowReplicationStatus） | `instance` | `rds:instance:list` | 目标实例 URN |
| `rds:instance:getParameter` | 查询实例参数配置（ShowInstanceConfiguration） | `instance` | `rds:param:list` | 目标实例 URN |
| `rds:backup:list` | 查询备份列表（ListBackups，风险评估·备份新鲜度检查） | `-` | `-` | `*`（不支持资源级授权） |
| `rds:instance:switchover` | 执行 RDS 主备倒换（StartFailover） | `instance` | `-` | 演练目标实例 URN |

### 可选权限（增强诊断）

| 权限动作 | 说明 | 资源类型 | 别名 | Resource 范围 |
|---------|------|---------|------|---------|
| `rds:log:getErrorLogs` | 查询 RDS 错误日志（ListErrorLogs） | `instance` | `rds:log:list` | 目标实例 URN |
| `rds:log:getSlowLogs` | 查询 RDS 慢 SQL 日志（ListSlowLogs） | `instance` | `rds:log:list` | 目标实例 URN |
| `ces:alarms:list` | 查询 CES 告警规则 | `-` | `-` | `*`（CES 资源，非 RDS 实例） |
| `ces:metricData:get` | 查询 CES 监控指标数据 | `-` | `-` | `*`（CES 资源，非 RDS 实例） |

> ⚠️ **授权项名称已核实**（来源：华为云 [身份策略授权参考 rds_10_0008](https://support.huaweicloud.com/api-rds/rds_10_0008.html) + [策略授权参考 rds_10_0007](https://support.huaweicloud.com/api-rds/rds_10_0007.html)，以及各 API 文档页的授权信息表）：
> - `rds:instance:switchover`：[StartFailover](https://support.huaweicloud.com/api-rds/rds_05_0013.html)，资源类型 `instance`，支持资源级授权
> - `rds:instance:getReplicaStatus`：[ShowReplicationStatus](https://support.huaweicloud.com/api-rds/rds_05_0033.html)，资源类型 `instance`，别名 `rds:instance:list`，无依赖
> - `rds:instance:getParameter`：[ShowInstanceConfiguration](https://support.huaweicloud.com/api-rds/rds_09_0306.html)，资源类型 `instance`，别名 `rds:param:list`，无依赖
> - `rds:instance:listAll`：[ListInstances](https://support.huaweicloud.com/api-rds/rds_01_0004.html) / [ShowStorageUsedSpace](https://support.huaweicloud.com/api-rds/rds_04_0010.html)，资源类型 `-`，别名 `rds:instance:list`，无依赖
> - `rds:backup:list`：[ListBackups](https://support.huaweicloud.com/api-rds/rds_09_0005.html)，资源类型 `-`，无别名，无依赖
> - `rds:log:getErrorLogs` / `rds:log:getSlowLogs`：资源类型 `instance`，别名 `rds:log:list`，无依赖
> - `ces:metricData:get`：ShowMetricData，资源类型 `-`
>
> 请勿使用以下名称——它们在官方文档中不存在或非授权项：
> - ❌ `rds:instance:failover`（官方授权项为 `rds:instance:switchover`）
> - ❌ `rds:instance:get`（官方无此授权项；复制状态用 `getReplicaStatus`，参数用 `getParameter`，存储用 `listAll`）
> - ❌ `rds:log:listErrorLogs` / `rds:log:listSlowLogs`（官方授权项为 `getErrorLogs` / `getSlowLogs`）
> - ❌ `ces:alarm:list`（官方授权项为 `ces:alarms:list`，注意复数）
> - ❌ 将别名当作依赖项额外授予（别名是同一权限的替代写法，策略中写主名即可）

## 策略模板

可直接在 IAM 控制台创建以下自定义策略。策略将**支持资源级授权的操作**（`switchover` / `getReplicaStatus` / `getParameter` / 日志查询）限定到演练目标实例 URN；其余操作（实例列表、备份列表、CES 查询）的资源类型为 `-`，无法收窄到单实例，保持 `*`：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:instance:switchover",
        "rds:instance:getReplicaStatus",
        "rds:instance:getParameter",
        "rds:log:getErrorLogs",
        "rds:log:getSlowLogs"
      ],
      "Resource": [
        "rds:<region>:<domainId>:instance:<instanceId>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:instance:listAll",
        "rds:backup:list",
        "ces:alarms:list",
        "ces:metricData:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

### Resource URN 格式说明

RDS 实例的 Resource 格式为（参见 [IAM 策略语法](https://support.huaweicloud.com/usermanual-iam/iam_01_0019.html)）：

```
rds:<region>:<domainId>:instance:<instanceId>
```

| 占位符 | 含义 | 获取方式 |
|--------|------|---------|
| `<region>` | 华为云区域 ID（如 `cn-north-4`） | 与 config.json 的 region 一致 |
| `<domainId>` | 账号 ID（租户 ID） | 控制台 → 账号中心 → 基本信息，或调用 `hcloud IAM GetUser` |
| `<instanceId>` | 目标 RDS 实例 ID | 与 config.json 的 instance_id 一致 |

**示例**：区域 `cn-north-4`，账号 ID `0483b6b16e954cb88930a360d2c4e663`，实例 `dsfae23fsfdsae3435in01`：

```
rds:cn-north-4:0483b6b16e954cb88930a360d2c4e663:instance:dsfae23fsfdsae3435in01
```

> ⚠️ **Resource 不要留空**。缺省 Resource 等效于 `*`，倒换权限会作用于账号/项目下所有 RDS 实例——任何被分配该策略的用户组成员都可对非演练目标实例执行主备倒换，造成大面积可用性风险。
>
> ⚠️ **不要使用 `rds:*:list`、`rds:*:get` 等通配符 Action**，它们会扩大到所有 RDS 资源的全部读写权限，违反最小权限原则。仅保留上方列出的具体 action。

## 创建策略步骤

1. 登录华为云控制台，进入 **统一身份认证服务（IAM）**
2. 选择 **权限管理 → 权限策略 → 创建自定义策略**
3. 填写策略名称 `RDSFailoverExperimentPolicy`
4. 选择 JSON 视图，粘贴上方策略模板（**将 Resource 中的占位符替换为实际值**）
5. 点击确定创建策略
6. 在 **用户组管理** 中将策略分配给目标用户组

## 验证权限

```bash
# 验证 RDS 列表权限
hcloud RDS ListInstances --cli-region=cn-north-1

# 验证 CES 告警查询权限
hcloud CES ListAlarmRules --cli-region=cn-north-1
```

## 安全检查项

prepare 阶段运行以下 IAM 相关检查：

| 检查项 | 类型 | 说明 |
|--------|------|------|
| RDS 实例列表查询权限 | 必需 | 验证 `rds:instance:listAll`（通过实际只读 API 调用） |
| RDS 主备倒换执行权限 | 必需 | 验证 `rds:instance:switchover` |
| hcloud 认证就绪 | 必需 | 通过实际只读 API 调用验证 hcloud profile 认证是否可用（非环境变量检查） |
| RDS 相关策略已分配 | 建议 | 检查 IAM 策略列表中是否含 RDS 策略 |
