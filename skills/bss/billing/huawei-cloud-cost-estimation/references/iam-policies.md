# IAM 最小权限 (Least-Privilege IAM Policies)

IAM Action 随账号类型、站点和服务版本变化，落地前以 API Explorer 与运行时
具体命令的 `--help` 输出为准（形如 `hcloud BSS ListServiceTypes --help`）。权限不足时报告用户补授权：
不得用写权限补救查询失败，不得自行提权重试。

## 询价（只读）

| 层级 | 操作 | 用途 |
| --- | --- | --- |
| BSS 询价 | `ListRateOnPeriodDetail`, `ListOnDemandResourceRatings` | 取得包周期或按需报价 |
| BSS 字典 | `ListServiceTypes`, `ListResourceTypes`, `ListServiceResources`, `ListResourceSpecs`, `ListMeasureUnits`, `ListConversions` | 解析服务、资源、规格和度量 |
| 产品辅助 | `ECS/NovaListAvailabilityZones` | 用户指定 AZ 时（可选） |
| 身份范围 | `IAM/KeystoneListAuthProjects`, `IAM/KeystoneListProjects`, `IAM/KeystoneListAuthDomains` | 解析可访问项目与账户 |

询价常用策略为 `bss:order:view` 加对应 BSS/IAM 只读 Action。

## 拒绝的写权限

本 Skill 为纯只读，不申请任何写权限。若账号策略仅在写权限下才能通过，停止并报错，
不给用户提供写路径变通。不要在列表中引入 Create/Delete/Update 操作。

## 伙伴代客户询价

使用客户授权所得 Token 调 `KeystoneListAuthProjects` 解析目标 region 的客户
`project_id`，再询价。授权失败时停止，不扩大范围。

## 权限与限流失败处理

| 现象 | 处理 |
| --- | --- |
| `403 Forbidden` / `CBC.0151` | 记录操作与账号范围，建议补对应 Action（询价只补只读） |
| `429` | 等 2 秒重试一次；仍失败则停止 |

参数类错误（`CBC.0100` / `CBC.99006006` / `CBC.99006055` 等）见
`commands.md` 陷阱区。历史账单、余额和对账不属于本技能；
使用费用中心或独立只读账单技能。