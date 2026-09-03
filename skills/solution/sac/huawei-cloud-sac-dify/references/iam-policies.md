# IAM Policies — huawei-cloud-sac-dify

IAM configuration required to deploy the Dify platform with Terraform.

## Basic Operations (Read-only)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:cloudServers:list | List ECS instances | Verify deployment resources |
| ecs:cloudServers:showServer | View ECS instance details | Check ECS status and details |
| ecs:cloudServers:showServerBlockDevice | View ECS block device details | Verify system disk attachment and volume mapping |
| vpc:bandwidths:get | View bandwidth details | Verify public bandwidth created for the EIP |
| vpc:vpcs:get | View VPC details | Verify VPC |
| vpc:subnets:get | View subnet details | Verify subnet |
| vpc:securityGroups:get | View security group details | Verify security group |
| vpc:securityGroupRules:get | View security group rule details | Verify security group rules |
| vpc:publicIps:get | View EIP details | Verify EIP |
| ims:images:get | View image metadata | Query image metadata |
| ims:images:list | List images | Query image list |
| evs:backups:get | View EVS backup details | Inspect backup metadata referenced by attached volumes |
| evs:snapshots:get | View EVS snapshot details | Inspect snapshot metadata referenced by attached volumes |
| evs:volumes:get | View EVS volume details | Verify system volume state and attachment |

## Deployment Operations (Apply/Destroy)

| API Action | Permission | Purpose |
| ------------ | ----------- | --------- |
| ecs:cloudServers:create | Create ECS instance | Provision ECS instance for Dify |
| ecs:cloudServers:delete | Delete ECS instance | Cleanup |
| vpc:bandwidths:create | Create bandwidth | Allocate EIP bandwidth for public access |
| vpc:bandwidths:delete | Delete bandwidth | Cleanup EIP bandwidth resources |
| vpc:vpcs:create | Create VPC | Network infrastructure |
| vpc:vpcs:delete | Delete VPC | Cleanup |
| vpc:subnets:create | Create subnet | Network infrastructure |
| vpc:subnets:delete | Delete subnet | Cleanup |
| vpc:securityGroups:create | Create security group | Security rules |
| vpc:securityGroups:delete | Delete security group | Cleanup |
| vpc:securityGroups:update | Update security group | Adjust security group attributes during reconciliation |
| vpc:securityGroupRules:create | Create security group rule | Add ICMP/HTTP/HTTPS rules |
| vpc:securityGroupRules:delete | Delete security group rule | Cleanup |
| vpc:publicIps:create | Create EIP | Public access |
| vpc:publicIps:delete | Delete EIP | Cleanup |
| vpc:publicIps:update | Update EIP | Update EIP or bandwidth association during reconciliation |
| evs:volumes:create | Create EVS volume | Provision system or attached volumes required by the ECS instance |
| evs:volumes:delete | Delete EVS volume | Cleanup attached storage resources |
| evs:volumes:attach | Attach EVS volume | Attach created volume to the ECS instance |
| evs:volumes:detach | Detach EVS volume | Detach volume during cleanup or replacement |

## Example Custom Policy JSON (Deployment)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:cloudServers:create",
                "ecs:cloudServers:delete",
                "ecs:cloudServers:list",
                "ecs:cloudServers:showServer",
                "ecs:cloudServers:showServerBlockDevice"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "vpc:bandwidths:create",
                "vpc:bandwidths:delete",
                "vpc:bandwidths:get",
                "vpc:publicIps:create",
                "vpc:publicIps:delete",
                "vpc:publicIps:get",
                "vpc:publicIps:update",
                "vpc:securityGroupRules:create",
                "vpc:securityGroupRules:delete",
                "vpc:securityGroupRules:get",
                "vpc:securityGroups:create",
                "vpc:securityGroups:delete",
                "vpc:securityGroups:get",
                "vpc:securityGroups:update",
                "vpc:subnets:create",
                "vpc:subnets:delete",
                "vpc:subnets:get",
                "vpc:vpcs:create",
                "vpc:vpcs:delete",
                "vpc:vpcs:get"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ims:images:get",
                "ims:images:list"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "evs:backups:get",
                "evs:snapshots:get",
                "evs:volumes:attach",
                "evs:volumes:create",
                "evs:volumes:delete",
                "evs:volumes:detach",
                "evs:volumes:get"
            ]
        }
    ]
}
```

## Account Requirements

- If using the initial account, extra IAM setup is usually not required.
- If using an IAM user, ensure required permissions are granted before `terraform apply`.

## Permission Failure Handling

If Terraform fails with `Unauthorized` or `Forbidden`:

1. Identify missing permissions from the error output.
2. Compare against required permissions in this document.
3. Update IAM policy / user group permissions.
4. Confirm with user before retrying `plan` or `apply`.
