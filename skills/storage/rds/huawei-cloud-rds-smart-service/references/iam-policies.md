# IAM Policies for RDS Smart Service

## Least-Privilege Policy

The following custom IAM policy grants the minimum permissions required for the RDS Smart Service skill to operate across all six capability domains.

### Read-Only Policy (Query & Diagnosis)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:*:list*",
        "rds:*:get*",
        "rds:*:show*",
        "rds:*:query*",
        "rds:*:download*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### Full Management Policy (Query + O&M + Backup/Recovery)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:*:list*",
        "rds:*:get*",
        "rds:*:show*",
        "rds:*:query*",
        "rds:*:download*",
        "rds:*:create*",
        "rds:*:update*",
        "rds:*:set*",
        "rds:*:switch*",
        "rds:*:change*",
        "rds:*:start*",
        "rds:*:stop*",
        "rds:*:restart*",
        "rds:*:resize*",
        "rds:*:enlarge*",
        "rds:*:reduce*",
        "rds:*:failover*",
        "rds:*:restore*",
        "rds:*:apply*",
        "rds:*:delete*",
        "rds:*:kill*",
        "rds:*:validate*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## System Policies

Huawei Cloud provides predefined RDS system policies:

| Policy Name | Description | Scope |
|-------------|-------------|-------|
| `RDS ReadOnlyAccess` | Read-only access to RDS | Query, list, show operations only |
| `RDS CommonAccess` | Common RDS operations | Query + basic management |
| `RDS FullAccess` | Full access to RDS | All RDS operations |
| `RDS Administrator` | RDS administrator | All RDS operations + parameter management |

## Recommended Approach

1. **For read-only/diagnosis scenarios**: Assign `RDS ReadOnlyAccess` system policy
2. **For daily O&M**: Create custom policy with query + restart + resize + backup permissions
3. **For full DBA access**: Assign `RDS FullAccess` system policy
4. **For production environments**: Use least-privilege custom policy, grant write permissions per-instance via resource conditions

## Resource-Level Authorization

For finer-grained control, restrict access to specific instances:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["rds:*:*"],
      "Resource": [
        "rds:*:*:instance:{instance_id_1}",
        "rds:*:*:instance:{instance_id_2}"
      ]
    }
  ]
}
```

## Notes

- The `rds:*:download*` permission is needed for slow log and error log file downloads
- The `rds:*:kill*` permission is needed for intelligent session kill (fault diagnosis)
- The `rds:*:restore*` permission is needed for backup restore operations
- Parameter group operations require `rds:*:create*`, `rds:*:update*`, and `rds:*:apply*` permissions
