# IAM Policies - MGC Cross-Region Migration

This document lists the Huawei Cloud IAM permissions required by `scripts/mgc_sms_existing_target_batch.py`, `scripts/mgc_migrate.py`, and `scripts/repair_boot_via_helper.py`, derived from the REST APIs they actually call (`IAM`, `SMS`, `ECS`, `VPC`, `EVS`).

## Required Services

| Service | Why it is called |
|---|---|
| IAM | Resolve project ID for source/destination regions (`GET /v3/projects`) |
| SMS | Accept privacy agreement, create migration project, list sources, create/start/poll/delete migration tasks |
| ECS | Create/query the target server, query flavors/availability zones, reset password, reboot/stop/start for repair |
| VPC | Create/query VPC, subnet, security group, security group rules, and publicip/EIP |
| EVS | Query/attach/detach volumes when repairing a target's boot disk via a helper ECS |

## Recommended System-Defined Policies

Huawei Cloud SMS does not currently publish fine-grained IAM actions in the same way as ECS/VPC/EVS; use the system-defined policy at the project level and scope it with a dedicated IAM user or enterprise project rather than the primary account:

| Policy | Scope | Purpose |
|---|---|---|
| `SMS FullAccess` | Project | Create/manage migration projects and tasks |
| `ECS FullAccess` (or narrower custom policy below) | Project | Create/repair target server, reset password, query status |
| `VPC FullAccess` (or narrower custom policy below) | Project | Create/query VPC, subnet, security group, EIP |
| `EVS FullAccess` (or narrower custom policy below) | Project | Query/attach/detach volumes during boot repair |

## Custom Least-Privilege Policy (ECS/VPC/EVS actions)

The following fine-grained actions cover the ECS/VPC/EVS endpoints these scripts call. Attach this alongside the SMS system-defined policy (SMS actions are not broken out below since they are not independently documented for custom policies at this time — validate in the IAM console before relying on a narrower SMS policy).

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
        "ecs:servers:reboot",
        "ecs:servers:stop",
        "ecs:servers:start",
        "ecs:servers:delete",
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
        "evs:volumes:get",
        "evs:volumes:list",
        "evs:volumes:attach",
        "evs:volumes:detach"
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
