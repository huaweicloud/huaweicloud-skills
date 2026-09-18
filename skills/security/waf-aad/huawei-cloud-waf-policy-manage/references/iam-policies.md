# IAM Policies - WAF Policy Management

## Required Permissions

### 策略管理权限

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:policy:create",
        "waf:policy:delete",
        "waf:policy:update",
        "waf:policy:query"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### 规则管理权限

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:rule:create",
        "waf:rule:delete",
        "waf:rule:update",
        "waf:rule:query"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### 完整权限（策略 + 规则）

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:policy:*",
        "waf:rule:*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 权限说明

| 权限 | 说明 | 适用场景 |
|------|------|----------|
| waf:policy:create | 创建防护策略 | 新建策略 |
| waf:policy:delete | 删除防护策略 | 删除策略 |
| waf:policy:update | 更新防护策略 | 修改策略配置 |
| waf:policy:query | 查询防护策略 | 列表/详情查询 |
| waf:rule:create | 创建防护规则 | 创建各类规则 |
| waf:rule:delete | 删除防护规则 | 删除规则 |
| waf:rule:update | 更新防护规则 | 修改规则 |
| waf:rule:query | 查询防护规则 | 规则查询 |

## 最小权限原则

- 仅授予本 Skill 所需的具体权限
- 读操作（query）与写操作（create/update/delete）分开列明
- 生产环境建议使用自定义策略，限制到具体资源

## 配置方法

1. 登录华为云控制台
2. 进入"身份与访问管理" → "用户"
3. 选择目标用户，点击"授权"
4. 选择"自定义策略"，导入上述 JSON
5. 确认授权

## 注意事项

- 删除防护策略前需先解除域名绑定
- 写操作（Create/Update/Delete）建议在测试环境验证后再用于生产
- 建议使用 IAM 用户而非主账号进行操作
