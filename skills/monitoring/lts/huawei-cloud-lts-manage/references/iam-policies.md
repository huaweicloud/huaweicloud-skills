# IAM Policies for LTS Management

## Least-Privilege Policy

The following policy grants the minimum permissions required by this skill:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lts:groups:list",
        "lts:groups:get",
        "lts:groups:create",
        "lts:groups:delete",
        "lts:groups:modify",
        "lts:streams:list",
        "lts:streams:get",
        "lts:streams:create",
        "lts:streams:delete",
        "lts:streams:modify",
        "lts:index:get",
        "lts:index:create",
        "lts:transfer:list",
        "lts:transfer:create",
        "lts:transfer:delete",
        "lts:transfer:modify",
        "lts:alarm:list",
        "lts:alarm:get",
        "lts:alarm:create",
        "lts:alarm:delete",
        "lts:alarm:modify",
        "lts:logs:list",
        "lts:struct:list",
        "lts:struct:get",
        "lts:struct:modify"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Policy (Query + Diagnose only)

If only query and log search are needed (no Create/Update/Delete):

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lts:groups:list",
        "lts:groups:get",
        "lts:streams:list",
        "lts:streams:get",
        "lts:index:get",
        "lts:transfer:list",
        "lts:alarm:list",
        "lts:alarm:get",
        "lts:logs:list",
        "lts:struct:list",
        "lts:struct:get"
      ],
      "Resource": "*"
    }
  ]
}
```
