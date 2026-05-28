# IAM Permission Policies - EIP Management Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud EIP Batch Management & Cost Optimization skill. All permissions follow the principle of least privilege.

## Basic Operations (Read-Only)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `vpc:publicIps:list` | List EIPs | Query all EIPs and their binding status |
| `vpc:publicIps:get` | Get EIP details | View individual EIP information |
| `vpc:publicIpTags:list` | List tags | Query tags on EIPs |

## Write Operations (Require Additional Authorization)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `vpc:publicIps:create` | Create EIP | Create new Elastic Public IPs |
| `vpc:publicIps:delete` | Delete EIP | Release idle EIPs (irreversible) |
| `vpc:publicIps:update` | Update EIP | Adjust bandwidth size |
| `vpc:publicIps:associate` | Associate EIP | Bind EIP to a resource (ECS, ELB, NAT) |
| `vpc:publicIps:disassociate` | Disassociate EIP | Unbind EIP from a resource |
| `vpc:publicIpTags:create` | Create tags | Add tags to EIPs |
| `vpc:publicIpTags:delete` | Delete tags | Remove tags from EIPs |

## Monitoring Operations (Optional)

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `ces:metrics:get` | Get metrics | Query EIP bandwidth usage metrics |
| `ces:alarms:list` | List alarms | View existing alarm rules |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:publicIps:list",
        "vpc:publicIps:get",
        "vpc:publicIpTags:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Full Management Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:publicIps:list",
        "vpc:publicIps:get",
        "vpc:publicIps:create",
        "vpc:publicIps:delete",
        "vpc:publicIps:update",
        "vpc:publicIps:associate",
        "vpc:publicIps:disassociate",
        "vpc:publicIpTags:list",
        "vpc:publicIpTags:create",
        "vpc:publicIpTags:delete"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Assignment Steps

1. Log in to Huawei Cloud IAM console: https://console.huaweicloud.com/iam/
2. Navigate to **Policies** → **Create Custom Policy**
3. Choose **JSON** mode and paste the policy JSON above
4. Navigate to **Users** / **User Groups** → **Authorize**
5. Select the custom policy and confirm

## Permission Failure Handling

When a command fails with a permission error:

1. Read this document (`references/iam-policies.md`)
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console
4. Pause execution and wait for user confirmation that permissions have been granted
5. Retry the failed command
