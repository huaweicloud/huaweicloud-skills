# IAM Policies — huawei-cloud-sac-new-api

IAM configuration required to deploy the NewAPI LLM Gateway.

## Basic operations (read-only)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:servers:get | View ECS instance details | Check instance status |
| ecs:servers:list | List ECS instances | Verify deployment |
| vpc:vpcs:get | View VPC details | Verify network |
| vpc:subnets:get | View subnet details | Verify network |
| vpc:securityGroups:get | View security group | Verify security rules |
| eip:globalEips:get | View EIP details | Verify public access |
| evs:volumes:get | View EVS volume | Verify storage |

## Deployment operations (Apply/Destroy)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:servers:create | Create ECS instance | Provision instance |
| ecs:servers:delete | Delete ECS instance | Cleanup |
| vpc:vpcs:create | Create VPC | Network infrastructure |
| vpc:vpcs:delete | Delete VPC | Cleanup |
| vpc:subnets:create | Create subnet | Network infrastructure |
| vpc:subnets:delete | Delete subnet | Cleanup |
| vpc:securityGroups:create | Create security group | Security rules |
| vpc:securityGroups:delete | Delete security group | Cleanup |
| vpc:securityGroupRules:create | Create security group rules | Security rules |
| eip:globalEips:create | Create EIP | Public access |
| eip:globalEips:delete | Delete EIP | Cleanup |
| evs:volumes:create | Create EVS volume | Storage disks |
| evs:volumes:delete | Delete EVS volume | Cleanup |

## Example Custom Policy JSON (Deployment)

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
        "ecs:servers:delete"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:get",
        "vpc:vpcs:create",
        "vpc:vpcs:delete",
        "vpc:subnets:get",
        "vpc:subnets:create",
        "vpc:subnets:delete",
        "vpc:securityGroups:get",
        "vpc:securityGroups:create",
        "vpc:securityGroups:delete",
        "vpc:securityGroupRules:create"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "eip:globalEips:get",
        "eip:globalEips:create",
        "eip:globalEips:delete"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "evs:volumes:get",
        "evs:volumes:create",
        "evs:volumes:delete"
      ]
    }
  ]
}
```

## Account Requirements

- If using the **initial registered account** (the account created when
  first registering with Huawei Cloud), no additional IAM preparation
  is needed.
- If using an **IAM user**, confirm the user has the required permissions
  before running `terraform apply`.

## Permission Failure Handling

If Terraform fails with `Unauthorized` or `Forbidden`:

1. Identify missing permissions from the error output.
2. Compare against required permissions in this document.
3. Update IAM policy / user group permissions.
4. Confirm with user before retrying `plan` or `apply`.