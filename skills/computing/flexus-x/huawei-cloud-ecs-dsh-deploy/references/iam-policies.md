# IAM Permission Policies

## Overview

This document describes the IAM permissions required for this skill and how to configure them.

## Required Permissions

### ECS Related Permissions

| API Action | Permission | Purpose |
|------------|------------|---------|
| ecs:servers:create | Create Cloud Server | Create ECS instance |
| ecs:servers:get | Query Cloud Server Details | Check server status |
| ecs:servers:list | Query Cloud Server List | List all servers |
| ecs:serverVolumes:attach | Attach Cloud Disk | Attach system disk |
| ecs:cloudServerFlavors:list | Query Flavor List | Get available flavors |
| ecs:cloudImages:list | Query Image List | Get available images |

### VPC Related Permissions

| API Action | Permission | Purpose |
|------------|------------|---------|
| vpc:vpcs:create | Create VPC | Create virtual private cloud |
| vpc:vpcs:get | Query VPC Details | Get VPC information |
| vpc:subnets:create | Create Subnet | Create subnet |
| vpc:subnets:get | Query Subnet Details | Get subnet information |
| vpc:securityGroups:create | Create Security Group | Create sg-dsh (empty, no inbound rules) |

### EIP Related Permissions

| API Action | Permission | Purpose |
|------------|------------|---------|
| eip:publicIps:create | Create Elastic Public IP | Bind EIP |
| eip:publicIps:get | Query Elastic Public IP | Get EIP information |
| eip:publicIps:bind | Bind Elastic Public IP | Bind to ECS |

### COC Related Permissions

| API Action | Permission | Purpose |
|------------|------------|---------|
| coc:scripts:create | Create Script | Create deployment script |
| coc:scripts:execute | Execute Script | Execute script on instance |
| coc:scripts:get | Query Script Details | Query script status |
| coc:scriptJobs:get | Query Script Execution Record | Query execution status |
| coc:resources:list | Query Resource List | Query UniAgent status |

### IAM Related Permissions (Project ID auto-fetch)

| API Action | Permission | Purpose |
|------------|------------|---------|
| iam:projects:list | List Projects | Auto-fetch Project ID by region |

**Note:** This skill does **not** require OBS permissions — dsh does not use Huawei Cloud OBS for storage.

## IAM Policy Configuration

### Method 1: Use Preset Policies

Add the following preset policies to users in the IAM console:
- `ECS FullAccess` - ECS full access permissions
- `VPC FullAccess` - VPC and EIP full access permissions
- `COC FullAccess` - COC full access permissions

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
        "ecs:serverVolumes:attach",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudImages:list",
        "vpc:vpcs:create",
        "vpc:vpcs:get",
        "vpc:subnets:create",
        "vpc:subnets:get",
        "vpc:securityGroups:create",
        "eip:publicIps:create",
        "eip:publicIps:get",
        "eip:publicIps:bind",
        "coc:scripts:create",
        "coc:scripts:execute",
        "coc:scripts:get",
        "coc:scriptJobs:get",
        "coc:resources:list",
        "iam:projects:list"
      ]
    }
  ]
}
```

❌ **Error Example**:
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

## Permission Failure Handling

If you encounter insufficient permissions error (403 Unauthorized):

1. **Check IAM Policy**
   - Confirm the policy is correctly attached to the user/role
   - Check if the Action in the policy includes the required permissions

2. **Verify AK/SK**
   - Confirm AK/SK has not expired
   - Confirm AK/SK belongs to a user with permissions

3. **Confirm Region Configuration**
   - Check if the Region parameter is correct
   - Some permissions may require region-level configuration

4. **Check Error Details**

✅ **Correct Example**:
```bash
hcloud ECS ListServers --cli-region=cn-north-4
# Error: {"error_code": "APIGW.0101", "error_msg": "API not exist or not published"}
```

## Principle of Least Privilege

It is recommended to configure according to the principle of least privilege:
- Only grant required API Actions
- Limit resource scope (such as specific project/region)
- Regularly review and clean up unnecessary permissions
