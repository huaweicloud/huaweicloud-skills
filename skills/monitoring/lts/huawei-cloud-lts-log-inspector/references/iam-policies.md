# IAM Policies for LTS Log Inspector

## Least-Privilege Policy

This Skill requires LTS read permissions for query/inspection operations and
LTS transfer write permissions for OBS transfer create/delete operations.

### Policy: LTS Log Inspector (Read + Transfer)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lts:groups:list",
        "lts:streams:list",
        "lts:logs:list",
        "lts:histogram:list",
        "lts:statistics:list",
        "lts:context:list",
        "lts:hostGroups:list",
        "lts:hosts:list",
        "lts:accessConfig:list",
        "lts:transfers:list"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lts:transfers:create",
        "lts:transfers:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

### Policy: LTS Read-Only (Inspection Only)

For environments where only query/inspection is needed (no OBS transfer):

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lts:groups:list",
        "lts:streams:list",
        "lts:logs:list",
        "lts:histogram:list",
        "lts:statistics:list",
        "lts:context:list",
        "lts:hostGroups:list",
        "lts:hosts:list",
        "lts:accessConfig:list",
        "lts:transfers:list"
      ],
      "Resource": "*"
    }
  ]
}
```

### OBS Permissions (for transfer target bucket)

If the OBS transfer writes to an OBS bucket, the caller also needs OBS write
permissions on the target bucket:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:PutObject",
        "obs:bucket:GetObject"
      ],
      "Resource": [
        "obs:*:*:bucket:{obs_bucket_name}",
        "obs:*:*:bucket:{obs_bucket_name}/*"
      ]
    }
  ]
}
```
