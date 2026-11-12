# IAM Permissions

This skill is strictly read-only. Grant only the following SCM read actions.

| Operation | IAM action |
|-----------|------------|
| List certificates (`list`) | `scm:cert:list` |
| Show certificate detail (`show`) | `scm:cert:get` |

## Least-Privilege Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "scm:cert:list",
        "scm:cert:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

Notes:

- The policy deliberately excludes apply, purchase, subscribe, revoke, deploy,
  push, import, export, delete and tag-write actions.
- If the account uses enterprise projects, the caller also needs visibility of
  the target enterprise project. Use `--enterprise-project-id` to scope the
  query; omitting it queries all enterprise projects the caller can access.
- Shared certificates require `--include-shared` (API `owned_by_self=false`).

## Typical 403 Message

When the account lacks `scm:cert:list`, SCM returns HTTP 403 with an error such
as `SCM.4002 Permission denied`. The skill surfaces a hint naming the required
read actions and never prints credentials.