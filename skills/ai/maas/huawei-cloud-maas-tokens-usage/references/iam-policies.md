# IAM Permission Policy

## Required Permissions

| Operation | Permission | Description |
|-----------|-----------|-------------|
| Query MaaS monitoring statistics | `modelarts:monitoring:get` | Call ShowStatistics API |
| Query service information | `modelarts:service:get` | Get service list etc. |
| Get project ID | `iam:projects:get` | Auto-get project_id |

## Minimum Permission Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "modelarts:monitoring:get",
                "modelarts:service:get",
                "iam:projects:get"
            ]
        }
    ]
}
```

## Predefined Permission Policies

- **ModelArts CommonOperations** — ModelArts common operations (includes `modelarts:service:get`, `modelarts:monitoring:get`)
- **IAM ReadOnlyAccess** — IAM read-only access (includes `iam:projects:get`)
