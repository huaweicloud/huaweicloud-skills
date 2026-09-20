# IAM Permission Policies

## Overview

This document describes the IAM permission list and configuration methods required for the huawei-cloud-devkit-application-check-cli skill.

## Required Permissions

### ECS Related Permissions

| API Action | Permission | Purpose |
|------------|-----------|---------|
| ecs:servers:create | Create cloud servers | Create DevKit ECS instance |
| ecs:servers:get | Query cloud server details | Poll ECS status to ACTIVE, query EIP |
| ecs:servers:list | Query cloud server list | Detect existing `devkit-ecs-*` instances, resolve EIP |
| ecs:cloudServerFlavors:list | Query flavor list | Get available 4U8G ac/C/S/T/X series flavors |
| ecs:cloudImages:list | Query image list via ECS Nova API | Get available OS images (CentOS 7.6 / Ubuntu 20.04) with `HW_ARCH` metadata for x86_64 filtering |

### VPC Related Permissions

| API Action | Permission | Purpose |
|------------|-----------|---------|
| vpc:vpcs:list | Query VPC list | Detect existing `devkit-vpc-*` VPC |
| vpc:vpcs:create | Create VPC | Create `devkit-vpc-{timestamp}` |
| vpc:vpcs:get | Query VPC details | Get VPC info |
| vpc:subnets:list | Query subnet list | Detect existing `devkit-subnet-*` subnet |
| vpc:subnets:create | Create subnet | Create `devkit-subnet-{timestamp}` |
| vpc:subnets:get | Query subnet details | Get subnet info |
| vpc:securityGroups:list | Query security group list | Detect existing `devkit-secgroup-*` security group |
| vpc:securityGroups:create | Create security group | Create `devkit-secgroup-{timestamp}` (auto-adds ICMP rule after creation) |
| vpc:securityGroups:get | Query security group details | Get security group info |
| vpc:securityGroupRules:create | Create security group rule | Auto-add ICMP inbound rule (0.0.0.0/0) |

### EIP Related Permissions

| API Action | Permission | Purpose |
|------------|-----------|---------|
| eip:publicIps:list | Query elastic public IPs | List EIPs |
| eip:publicIps:get | Query elastic public IP details | Get EIP info |

> **Note**: EIP is created and bound during ECS creation via the `--server.publicip` parameter, covered by `ecs:servers:create` permission.

### IMS Related Permissions

> **Note**: Image queries use **ECS Nova API** (`ecs:cloudImages:list`), NOT IMS API. No `ims:images:list` permission is required.

## IAM Policy Configuration

### Method 1: Use Predefined Policies

Add the following predefined policies to the user in the IAM console:
- `ECS FullAccess` - ECS full access permission
- `VPC FullAccess` - VPC full access permission
- `EIP FullAccess` - EIP full access permission

### Method 2: Custom Policy

✅ **Correct Example**:
```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:create",
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudImages:list",
        "vpc:vpcs:list",
        "vpc:vpcs:create",
        "vpc:vpcs:get",
        "vpc:subnets:list",
        "vpc:subnets:create",
        "vpc:subnets:get",
        "vpc:securityGroups:list",
        "vpc:securityGroups:create",
        "vpc:securityGroups:get",
        "vpc:securityGroupRules:create",
        "eip:publicIps:list",
        "eip:publicIps:get"
      ]
    }
  ]
}
```

❌ **Incorrect Example**:
```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*"  // Too permissive - violates least privilege principle
      ]
    }
  ]
}
```

## Prohibited Permissions

The following permissions are **not needed** by this skill and should not be granted:

| API Action | Reason |
|------------|--------|
| ecs:servers:resetPassword | `BatchResetServersPassword` is prohibited; passwords come only from environment variables |
| ecs:servers:delete | This skill does not delete ECS instances |


## Permission Failure Handling

If you encounter insufficient permission errors (403 Unauthorized):

1. **Check IAM Policy**
   - Confirm policy is correctly attached to user/role
   - Check that policy Actions include required permissions

2. **Verify AK/SK**
   - Confirm AK/SK has not expired
   - Confirm AK/SK belongs to a user with permissions
   - AK/SK passed via environment variables `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`

3. **Confirm Region Configuration**
   - Check Region parameter is correct (cn-north-4 / cn-east-3 / cn-south-1 / cn-southwest-2)
   - Some permissions may require region-level configuration

4. **View Error Details**

✅ **Correct Example**:
```bash
# Check error details
hcloud ECS ListCloudServers --cli-region=cn-north-4
# Error: {"error_code": "APIGW.0101", "error_msg": "API not exist or not published"}
```

## Least Privilege Principle

Recommended configuration following least privilege principle:
- Grant only required API Actions
- Limit resource scope (e.g., specific project/region)
- Regularly review and clean up unnecessary permissions
- Prohibit using wildcard `*` to replace specific Actions

---

## Permission Boundaries

### Scope Constraint

This skill only creates and manages resources named or tagged with the `devkit-` prefix. **Prohibited** from modifying or deleting existing resources not created by this workflow.

| Resource Type | Naming Convention | Allowed Actions |
|--------------|-------------------|-----------------|
| ECS | `devkit-ecs-*` | create, get, list |
| VPC | `devkit-vpc-*` | create, get, list |
| Subnet | `devkit-subnet-*` | create, get, list |
| Security Group | `devkit-secgroup-*` | create, get, list, create rules |
| EIP | (auto-created with ECS) | get, list |

### Must Stop If

The AI **must stop** the workflow and report to the user when any of the following conditions are encountered:

| Condition | Action |
|-----------|--------|
| Credentials missing or invalid (`DEVKIT_ECS_USER` / `DEVKIT_ECS_PASSWORD` not set) | STOP — prompt user to set environment variables |
| User rejects any confirmation step | STOP — do not execute any subsequent operations |
| ECS creation fails | STOP — report error details |
| SSH connection fails (Layer 1) | STOP — follow authentication failure handling procedure |
| DevKit installation fails | STOP — report error, retain ECS for troubleshooting |
| nodes.conf SSH verification fails | STOP — prompt user to fix nodes.conf |
| IAM permissions insufficient (403) | STOP — prompt user to check IAM policy |
| hcloud connectivity test fails | STOP — prompt user to check network and AK/SK |

### Prohibited Actions

The following actions are **strictly prohibited** in this skill, regardless of user requests:

| Prohibited Action | Reason |
|-------------------|--------|
| Delete any existing ECS instance | May damage user environment |
| Delete any existing VPC / subnet / security group | May damage user network |
| Modify IAM policies or user permissions | Security risk |
| Access resources outside DevKit workflow | Out of skill scope |
| Run commands not documented in this document | Security risk |
| `hcloud ECS BatchResetServersPassword` | Prohibited from modifying ECS password |
| `hcloud ECS DeleteServers` | Prohibited from deleting ECS |
| `hcloud VPC DeleteVpc` | Prohibited from deleting VPC |
| `hcloud EIP DeletePublicip` (EIP not created by this workflow) | Prohibited from deleting non-workflow resources |
| Using `ecs:*` / `vpc:*` wildcard permissions | Violates least privilege principle |
| Cross-region operations | Only operate within user-selected region |

### Resource Cleanup

This skill **does not auto-delete** any created resources. For cleanup:

| Resource | Cleanup Method | When |
|----------|---------------|------|
| DevKit ECS | User manually deletes in ECS console | When DevKit no longer needed |
| VPC / subnet / security group | User manually deletes in VPC console | When network no longer needed |
| Environment variables | User manually clears | `SetEnvironmentVariable(name, $null, "User")` |
| `/tmp/devkit_nodes_verified_hosts` | `find /tmp -name devkit_nodes_verified_hosts -delete` | When reset of verification state is needed |

---
