# IAM Policies

## Least-Privilege Policy for Config Helper

This skill is **read-only**. The AK/SK used by this skill only requires the
`Config ReadOnlyAccess` system policy (or an equivalent custom policy below).
Do not grant write permissions.

### Option 1: System Policy (Recommended)

Grant the system policy **`Config ReadOnlyAccess`** to the IAM user used by this skill.
No other permissions are required.

### Option 2: Custom Policy (Fine-Grained)

If a custom fine-grained policy is preferred, allow only the following read actions:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rms:*:list",
        "rms:*:get",
        "rms:*:getStatus",
        "rms:resources:summarize",
        "rms:resources:getHistory",
        "rms:resources:getRelation",
        "rms:policyAssignmentsRemediation:getRemediationConfiguration",
        "rms:policyAssignmentsRemediation:listRemediationExecutionStatuses",
        "rms:policyAssignmentsRemediation:listRemediationExceptions",
        "rms:resources:listTagsForResource",
        "rms:resources:listTags",
        "rms:resources:listResourcesByTag"
      ]
    }
  ]
}
```

> Note: The skill uses these Config OpenAPIs:
> - `ListBuiltInPolicyDefinitions` — 预置合规规则查询
> - `ListSchemas` — 资源 Schema 查询
> - `RunQuery` — 高级查询（SQL）
>
> Verify exact action names via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=config`

### Scope Notes

- The resource queries (Scenario 1/3) return resource data across services (ECS, VPC, IAM,
  OBS, etc.) collected by the Config recorder — the `Config ReadOnlyAccess` permission is
  sufficient; no per-service read permissions are needed on the query principal.
- IAM user AK/SK should be rotated periodically; never hardcode credentials in scripts.
- When using temporary AK/SK, set the `HW_SECURITY_TOKEN` environment variable.

