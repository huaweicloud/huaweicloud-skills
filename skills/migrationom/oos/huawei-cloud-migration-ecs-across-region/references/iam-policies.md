# IAM Policies - MGC Cross-Region Migration

This document lists the Huawei Cloud IAM permissions required by `scripts/mgc_migrate.py`, derived from the REST APIs it actually calls (`IAM`, `SMS`, `ECS`, `VPC`).

## Required Services

| Service | Why it is called |
|---|---|
| IAM | Resolve project ID for the target region (`GET /v3/projects`) |
| SMS | Accept privacy agreement, create migration project, list sources, create/start/poll/delete migration tasks |
| ECS | Create the target server, query flavors/availability zones, query/reset server details, reset password |
| VPC | Create/query target VPC, subnet, security group, security group rules, and publicip/EIP |

## Recommended System-Defined Policies

Huawei Cloud SMS does not currently publish fine-grained IAM actions in the same way as ECS/VPC; use the system-defined policy at the project level and scope it with a dedicated IAM user or enterprise project rather than the primary account:

| Policy | Scope | Purpose |
|---|---|---|
| `SMS FullAccess` | Project | Create/manage migration projects and tasks |
| `ECS FullAccess` (or narrower custom policy below) | Project | Create target server, reset password, query status |
| `VPC FullAccess` (or narrower custom policy below) | Project | Create/query VPC, subnet, security group, EIP |

## Custom Least-Privilege Policy (ECS/VPC actions)

The following fine-grained actions cover the ECS/VPC endpoints this skill calls. Attach this alongside the SMS system-defined policy (SMS actions are not broken out below since they are not independently documented for custom policies at this time — validate in the IAM console before relying on a narrower SMS policy).

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:servers:create",
        "ecs:servers:resetPassword",
        "ecs:cloudServerFlavors:get",
        "ecs:cloudServerFlavors:list",
        "ecs:availabilityZones:list",
        "ecs:serverJobs:get"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:get",
        "vpc:vpcs:create",
        "vpc:vpcs:list",
        "vpc:subnets:get",
        "vpc:subnets:create",
        "vpc:subnets:list",
        "vpc:securityGroups:get",
        "vpc:securityGroups:create",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:create",
        "vpc:publicIps:get",
        "vpc:publicIps:create"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:projects:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Failure Handling (MUST)

When any command fails with a permission/`403` error:

1. Read this file and identify the missing permission from the error's `error_code`/`error_msg`.
2. Show the user the exact missing permission and the relevant policy JSON above.
3. Instruct the user to create/attach a custom policy (or the system-defined policy) in the IAM console for the account/IAM user in use.
4. Pause execution and wait for the user to confirm the permission has been granted before retrying.
