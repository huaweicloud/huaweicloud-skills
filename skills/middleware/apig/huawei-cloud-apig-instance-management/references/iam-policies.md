# IAM Policies for APIG Skill (Least Privilege)

This skill operates on Huawei Cloud APIG dedicated instances. The IAM policies
below grant **only** the APIG permissions needed by the skill's `huawei_*`
actions. Read-only actions (Query R3 / Analyze R3) need only the `apig:instance:list`
/ `apig:group:list` style permissions; mutating actions need the corresponding
write permissions.

## 1. Read-only policy (Query + Analyze, R3)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apig:instance:list",
        "apig:instance:get",
        "apig:group:list",
        "apig:group:get",
        "apig:api:list",
        "apig:api:get",
        "apig:throttle:list",
        "apig:throttle:get"
      ],
      "Resource": "*"
    }
  ]
}
```

On the console this maps to the predefined roles:

- **APIG Administrator** (full) — only when management actions are required.
- **APIG Inspector / API Gateway Inspector** (read-only) — sufficient for Query/Analyze actions.

## 2. Management policy (Manage R2 + delete R1)

When the agent is allowed to create/update/delete APIG resources:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apig:instance:create",
        "apig:instance:delete",
        "apig:instance:update",
        "apig:instance:bindEip",
        "apig:group:create",
        "apig:group:delete",
        "apig:group:update",
        "apig:api:create",
        "apig:api:update",
        "apig:api:delete",
        "apig:api:publish",
        "apig:throttle:create",
        "apig:throttle:update",
        "apig:throttle:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. Supporting permissions

- **VPC / subnet / security group**: when creating an APIG instance, the agent
  needs read access to VPC resources in the target region:
  `vpc:vpcs:list`, `vpc:subnets:list`, `vpc:securityGroups:list`.
- **EIP**: `vpc:publicIps:list` to inspect bound EIPs for the public-access
  analysis (`eip_address` is returned by `ListInstancesV2` itself, so this is
  only needed for cross-checks).
- **Enterprise Project**: if the account uses enterprise projects, include the
  target project in the user's project list; `--enterprise_project_id=0` selects
  the default project.

## 4. Principle

Grant read-only permissions by default. Elevate to the management policy only
for agents that are explicitly allowed to mutate APIG resources, and require
user confirmation before every mutating command (see SKILL.md Critical Warnings
and Workflow).