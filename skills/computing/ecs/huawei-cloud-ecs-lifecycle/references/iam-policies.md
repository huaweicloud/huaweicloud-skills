# IAM Policies for Huawei Cloud ECS Lifecycle Management

Least-privilege IAM permissions required by this Skill. Authenticate with an IAM user (or agency)
that has exactly these permissions — no more.

## Built-in Roles (simplest)

| Operation Group | Built-in Role |
| ----------------- | --------------- |
| List / Show ECS instances | `ECS ReadOnlyAccess` |
| Create / Rename / Start / Stop / Reboot / Delete ECS | `ECS FullAccess` |
| Create instances (network resources referenced) | `VPC ReadOnlyAccess` (to resolve VPC/subnet/SG) |

> If the account uses fine-grained policies, use the JSON below instead of built-in roles.

## Fine-grained Policy (least privilege)

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:servers:get"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:cloudServers:create",
        "ecs:cloudServers:delete",
        "ecs:cloudServers:reboot",
        "ecs:cloudServers:start",
        "ecs:cloudServers:stop",
        "ecs:cloudServers:update",
        "ecs:cloudServers:updateName"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** action names may vary slightly by region/version — verify against the IAM permission
> catalogue for the target project (`统一身份认证服务 → 权限`, filter by `ECS`).

## Credentials

- Credentials are read from the environment: any of
  `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY`, `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`, or the
  `hcloud` CLI profile (`hcloud configure set`).
- **Never hardcode AK/SK** in scripts or documentation.