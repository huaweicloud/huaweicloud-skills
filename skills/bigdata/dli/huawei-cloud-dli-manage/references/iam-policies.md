# IAM Policies for DLI Resource Management

This Skill operates Huawei Cloud DLI through the hcloud CLI. IAM policies below
follow least privilege: read-only for inspection, scoped write for management
operations. DLI permissions use the `dli:*` / `dli:<action>` IAM action names
(project-level).

## Policy 1: DLI Read-Only (Inspection & Troubleshooting)

Suitable for daily patrol, job troubleshooting, metadata queries, and report
generation. No create/update/delete rights.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dli:queue:list",
        "dli:queue:show",
        "dli:database:list",
        "dli:database:show",
        "dli:table:list",
        "dli:table:show",
        "dli:table:preview",
        "dli:table:showPartitions",
        "dli:job:list",
        "dli:job:show",
        "dli:job:showProgress",
        "dli:job:showLog",
        "dli:connection:list",
        "dli:connection:show",
        "dli:resource:list",
        "dli:resource:show",
        "dli:variable:list",
        "dli:template:list",
        "dli:flinkTemplate:list",
        "dli:sparkTemplate:list",
        "dli:auth:list",
        "dli:quota:show",
        "dli:elasticResourcePool:list",
        "dli:elasticResourcePool:show",
        "dli:agency:show",
        "dli:catalog:list",
        "dli:catalog:show"
      ],
      "Resource": "*"
    }
  ]
}
```

> Note: `resource` values of `*` scoped to the project where the policy is
> attached. For production, restrict `Resource` to specific queue/database
> resources where feasible.

## Policy 2: DLI Operations (Full Management)

For agents performing management tasks (submit/cancel jobs, create/update/delete
queues, metadata governance, connection management, resource uploads, template
management). This is the recommended policy for this Skill.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dli:queue:create",
        "dli:queue:delete",
        "dli:queue:update",
        "dli:queue:scale",
        "dli:queuePlan:create",
        "dli:queuePlan:update",
        "dli:queuePlan:delete",
        "dli:queue:grantAgency",
        "dli:database:create",
        "dli:database:delete",
        "dli:database:updateOwner",
        "dli:table:create",
        "dli:table:delete",
        "dli:table:updateOwner",
        "dli:table:grantPrivilege",
        "dli:table:revokePrivilege",
        "dli:job:submit",
        "dli:job:cancel",
        "dli:job:stop",
        "dli:job:exportResult",
        "dli:job:executeFlink",
        "dli:job:batchRun",
        "dli:job:batchStop",
        "dli:job:batchDelete",
        "dli:connection:create",
        "dli:connection:update",
        "dli:connection:delete",
        "dli:connection:associateQueue",
        "dli:connection:disassociateQueue",
        "dli:connection:testConnectivity",
        "dli:resource:upload",
        "dli:resource:delete",
        "dli:resource:updateOwner",
        "dli:variable:create",
        "dli:variable:update",
        "dli:variable:delete",
        "dli:template:create",
        "dli:template:update",
        "dli:template:delete",
        "dli:flinkTemplate:create",
        "dli:flinkTemplate:update",
        "dli:flinkTemplate:delete",
        "dli:sparkTemplate:create",
        "dli:sparkTemplate:update",
        "dli:auth:update",
        "dli:auth:registerQueue",
        "dli:elasticResourcePool:update",
        "dli:elasticResourcePool:scale",
        "dli:elasticResourcePool:associateQueue",
        "dli:elasticResourcePool:disassociateQueue"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy 3: Minimal — Connectivity Troubleshooting Only

Compose from Policy 1 plus:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dli:connection:testConnectivity",
        "dli:queue:show"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- IAM action names follow the DLI permission model (`dli:<category>:<action>`).
  Verify exact action strings against the current Huawei Cloud DLI permission
  documentation for the target region, as service-side permission names may
  evolve.
- Do **not** grant `dli:job:submit` to agents that only perform inspection.
- The agent must never hardcode AK/SK; credentials come from the environment
  (`HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` or `hcloud configure`).