# IAM Policies

The skill covers both read-only inspection and write operations, so choose the
policy that matches the commands the operator actually needs.

## Read-Only Policy

Use the system-defined **BCS ReadOnlyAccess** policy, or the following custom
policy:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bcs:instance:list",
        "bcs:instance:get",
        "bcs:channel:list",
        "bcs:member:list",
        "bcs:quota:get",
        "bcs:metric:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

This covers `list`, `detail`, `nodes`, `channels`, `members`, `notifications`,
`flavors`, `quotas`, `status`, `op-record`, `alerts` and `metrics`.

## Full Read/Write Policy

Scope the policy to the resources and actions the operator actually needs; the
example below covers every operation of this skill:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bcs:instance:create",
        "bcs:instance:update",
        "bcs:instance:delete",
        "bcs:instance:list",
        "bcs:instance:get",
        "bcs:channel:create",
        "bcs:channel:delete",
        "bcs:channel:list",
        "bcs:channel:update",
        "bcs:cert:create",
        "bcs:cert:download",
        "bcs:cert:freeze",
        "bcs:cert:unfreeze",
        "bcs:member:invite",
        "bcs:member:delete",
        "bcs:notification:handle",
        "bcs:metric:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> IAM action names follow the BCS console policy templates. Validate the exact
> action names in the IAM policy simulator for your account before production
> use.

## Managed Policies

- `BCS ReadOnlyAccess` — read-only access to BCS instances, channels, members,
  operation records, alerts and metrics.
- `BCS FullAccess` — full read/write access; convenient but broad.

## Region Restriction

Scope the policy to the regions where the tenant owns BCS resources:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bcs:instance:list", "bcs:instance:get"],
      "Resource": ["*"],
      "Condition": {
        "StringEquals": {
          "g:Region": ["cn-north-4", "cn-south-1"]
        }
      }
    }
  ]
}
```

## Additional Service Permissions

Some write operations touch dependent services:

| Operation | Additional permissions |
|-----------|------------------------|
| Create instance with a new CCE cluster | CCE cluster/node permissions |
| Create instance with EIP bandwidth | VPC/EIP permissions |
| Delete instance with `--delete-storage/--delete-obs/--delete-resource` | EVS / OBS / CCE delete permissions |
| IEF edge deployment | IEF permissions |

## Credential Handling

- Read AK/SK from environment variables (`HUAWEICLOUD_SDK_AK`,
  `HUAWEICLOUD_SDK_SK`); never hardcode credentials in scripts or documents.
- Temporary credentials are supported through `HW_SECURITY_TOKEN`.
- The quality-reporting SDK masks credentials and never logs them.
- Certificate/SDK artifacts contain private key material — store them only in a
  user-approved local directory and never commit them.
- Do not put instance passwords into documents committed to a repository.