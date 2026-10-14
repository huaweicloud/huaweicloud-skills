# IAM Policies

## Least-Privilege IAM Policy

The following IAM policy provides the minimum permissions required for all CCE log query, analysis, and LogConfig management operations:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cce:cluster:get",
        "cce:cluster:list",
        "cce:logConfig:get",
        "cce:logConfig:list",
        "cce:logConfig:create",
        "cce:logConfig:delete"
      ],
      "Resource": [
        "cce:*:*:cluster:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lts:accessConfig:list",
        "lts:accessConfig:create",
        "lts:accessConfig:delete",
        "lts:logGroup:list",
        "lts:logStream:list",
        "lts:logs:list"
      ],
      "Resource": [
        "lts:*:*:*:*"
      ]
    }
  ]
}
```

## Scope Notes

| Permission | Required For | Risk Level |
|-----------|-------------|------------|
| `cce:cluster:get` | Verifying cluster ID through `ShowCluster` | R3 (Read-only) |
| `cce:cluster:list` | Resolving cluster name to UUID through `ListClusters` | R3 (Read-only) |
| `cce:logConfig:get` | Reading LogConfig custom resources | R3 (Read-only) |
| `cce:logConfig:list` | Listing LogConfig collection rules | R3 (Read-only) |
| `cce:logConfig:create` | Creating new LogConfig rules | R2 (Requires confirmation) |
| `cce:logConfig:delete` | Removing LogConfig rules | R1 (Requires confirmation) |
| `lts:accessConfig:list` | Listing LTS Access Config rules | R3 (Read-only) |
| `lts:accessConfig:create` | Creating LTS Access Config rules | R2 (Requires confirmation) |
| `lts:accessConfig:delete` | Removing LTS Access Config rules | R1 (Requires confirmation) |
| `lts:logGroup:list` | Discovering LTS log groups for destination selection | R3 (Read-only) |
| `lts:logStream:list` | Discovering LTS log streams for destination selection | R3 (Read-only) |
| `lts:logs:list` | Querying log content from LTS | R3 (Read-only) |

## Credential Requirements

The SKILL uses `hcloud` CLI credentials or explicit AK/SK. IAM permissions must be assigned to the corresponding user or agency. For CCE LogConfig operations, the CCE cluster must have the Cloud Native Logging add-on installed in addition to these IAM permissions.