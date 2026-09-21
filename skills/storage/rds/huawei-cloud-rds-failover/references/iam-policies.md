# IAM 权限策略

## 最小权限集

RDS 主备倒换演练所需的最小权限：

| 权限动作 | 说明 | 必需 |
|---------|------|------|
| `rds:instance:list` | 查询 RDS 实例列表 | ✅ 必需 |
| `rds:instance:failover` | 执行 RDS 主备倒换 | ✅ 必需 |
| `rds:log:listErrorLogs` | 查询 RDS 错误日志 | 可选 |
| `rds:log:listSlowLogs` | 查询 RDS 慢 SQL 日志 | 可选 |
| `ces:alarm:list` | 查询 CES 告警规则 | 可选 |
| `ces:metricData:get` | 查询 CES 监控指标数据 | 可选 |

## 策略模板

可直接在 IAM 控制台创建以下自定义策略。策略仅包含演练所需的具体 action，不使用通配符，遵循最小权限原则：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:instance:list",
        "rds:instance:failover",
        "rds:log:listErrorLogs",
        "rds:log:listSlowLogs",
        "ces:alarm:list",
        "ces:metricData:get"
      ]
    }
  ]
}
```

> ⚠️ **不要使用 `rds:*:list` 或 `rds:*:get` 等通配符**，它们会扩大到所有 RDS 资源的读取权限，违反最小权限原则。仅保留上方列出的具体 action。

## 创建策略步骤

1. 登录华为云控制台，进入 **统一身份认证服务（IAM）**
2. 选择 **权限管理 → 权限策略 → 创建自定义策略**
3. 填写策略名称 `RDSFailoverExperimentPolicy`
4. 选择 JSON 视图，粘贴上方策略模板
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
| RDS 实例列表查询权限 | 必需 | 验证 `rds:instance:list` |
| RDS 主备倒换执行权限 | 必需 | 验证 `rds:instance:failover` |
| AK/SK 环境变量已配置 | 建议 | 环境变量或 hcloud profile 均可 |
| RDS 相关策略已分配 | 建议 | 检查 IAM 策略列表中是否含 RDS 策略 |
