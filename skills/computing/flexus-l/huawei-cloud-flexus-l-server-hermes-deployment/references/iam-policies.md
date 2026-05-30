# IAM 权限策略参考

本文档描述了使用 Hermes 一键部署技能所需的华为云 IAM 权限策略。

## 权限要求

### 1. Flexus L 实例相关权限

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "hcss:instance:create",
                "hcss:instance:list",
                "hcss:instance:get",
                "hcss:instance:delete"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

### 2. COC (Cloud Operations Center) 相关权限

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "coc:script:create",
                "coc:script:execute",
                "coc:script:query",
                "coc:script:delete"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

### 3. IAM 相关权限（Project ID 获取）

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "iam:project:list",
                "iam:project:get"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

## 推荐策略组合

将上述权限组合为一个完整的自定义策略：

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Action": [
                "hcss:instance:create",
                "hcss:instance:list",
                "hcss:instance:get",
                "hcss:instance:delete",
                "coc:script:create",
                "coc:script:execute",
                "coc:script:query",
                "coc:script:delete",
                "iam:project:list",
                "iam:project:get"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

## 权限配置步骤

1. 登录华为云控制台
2. 进入 "IAM" -> "用户" -> 选择目标用户
3. 点击 "权限" -> "授予权限"
4. 选择 "自定义策略" -> "新建自定义策略"
5. 粘贴上述策略内容并保存
6. 将策略授予目标用户

## 注意事项

- 建议遵循最小权限原则，仅授予必要的权限
- 定期审查和更新权限策略
- 使用 AK/SK 时确保密钥安全存储，避免硬编码