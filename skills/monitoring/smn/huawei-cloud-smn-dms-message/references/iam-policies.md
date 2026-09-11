# IAM Policies for huawei-cloud-smn-dms-message

Least-privilege IAM permissions needed to run the 15 actions of this skill. Prefer role-based
assignments that match the risk tier of the work being done. Never grant `admin` whole-account roles for query-only use.

## Minimal permission set

| IAM Policy / Role | Grants | Used by |
|-------------------|--------|---------|
| `SMN Administrator` | Full SMN management (topics, subscriptions, templates, publishing) | R2/R1 SMN actions |
| `SMN ReadOnlyAccess` | List/get SMN topics, subscriptions, templates | R3 SMN query & diagnose actions |
| `DMS FullAccess` | Full DMS management across Kafka / RabbitMQ / RocketMQ | R2/R1 DMS actions |
| `DMS User` | Read + manage DMS instances | R3 DMS query actions |
| `VPC ReadOnlyAccess` (optional) | Read VPC/subnet/security-group IDs to pass to `CreateDmsInstance` | `huawei_create_dms_instance` |

## Least-privilege custom policy (recommended)

If the platform requires custom JSON policies, the following covers the exact API actions used:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "smn:topic:list",
        "smn:topic:create",
        "smn:topic:delete",
        "smn:topic:publish",
        "smn:subscription:list",
        "smn:subscription:create",
        "smn:subscription:delete",
        "smn:subscription:confirm",
        "smn:template:list",
        "smn:template:create"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dms:instance:list",
        "dms:instance:get",
        "dms:instance:create",
        "dms:instance:delete",
        "dms:topic:list",
        "dms:topic:create"
      ],
      "Resource": "*"
    }
  ]
}
```

> Note: the exact IAM action names (e.g. `smn:topic:list`) vary by cloud version. If the custom
> policy is rejected, fall back to the managed roles (`SMN ReadOnlyAccess` + `DMS User` for query,
> plus `SMN Administrator` / `DMS FullAccess` for management) which are version-stable.

## Security notes

- Credentials must never be hardcoded, printed, or passed in chat (see SKILL.md Authentication).
- Prefer scoping policies to the specific regions/EP where this skill is used.
- Permanent principal recommended: an IAM user or agency token used only for these SMN/DMS operations.
