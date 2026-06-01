# IAM Permission Policies - SWR Image Governance Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud SWR Image Governance skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `swr:namespace:auth:get`   | Get NS auth       | Query namespace permissions            |
| `swr:repository:auth:get`  | Get repo auth     | Query repository permissions           |
| `swr:retention:list`       | List retention    | List retention rules                   |
| `swr:retention:get`        | Get retention     | View retention rule details            |
| `swr:domain:list`          | List domains      | List shared download domains           |
| `swr:domain:get`           | Get domain        | View domain details                    |
| `swr:share:list`           | List shared repos | List shared repositories               |
| `swr:share:get`            | Get shared repo   | View shared repository details         |
| `swr:share:feature:get`    | Get share feature | Check sharing feature gates            |
| `swr:global:feature:get`   | Get global feature| Check global feature gates             |
| `swr:agency:check`         | Check agency      | Check agency delegation status         |
| `swr:accessory:list`       | List accessories  | List repository accessories            |
| `swr:reference:list`       | List references   | List repository references             |

## Write Operations (Require Additional Authorization)

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `swr:namespace:auth:create`| Create NS auth   | Grant namespace permissions            |
| `swr:namespace:auth:update`| Update NS auth   | Modify namespace permissions           |
| `swr:namespace:auth:delete`| Delete NS auth   | Revoke namespace permissions           |
| `swr:repository:auth:create`| Create repo auth | Grant repository permissions           |
| `swr:repository:auth:update`| Update repo auth | Modify repository permissions          |
| `swr:repository:auth:delete`| Delete repo auth | Revoke repository permissions          |
| `swr:retention:create`     | Create retention  | Create retention rules                 |
| `swr:retention:update`     | Update retention  | Modify retention rules                 |
| `swr:retention:delete`     | Delete retention  | Remove retention rules                 |
| `swr:domain:create`        | Create domain     | Create shared download domains         |
| `swr:domain:update`        | Update domain     | Modify domain settings                 |
| `swr:domain:delete`        | Delete domain     | Remove shared download domains         |
| `swr:agency:create`        | Create agency     | Create agency delegation               |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:namespace:auth:get",
        "swr:repository:auth:get",
        "swr:retention:list",
        "swr:retention:get",
        "swr:domain:list",
        "swr:domain:get",
        "swr:share:list",
        "swr:share:get",
        "swr:share:feature:get",
        "swr:global:feature:get",
        "swr:agency:check",
        "swr:accessory:list",
        "swr:reference:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Full Governance Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:namespace:auth:get",
        "swr:namespace:auth:create",
        "swr:namespace:auth:update",
        "swr:namespace:auth:delete",
        "swr:repository:auth:get",
        "swr:repository:auth:create",
        "swr:repository:auth:update",
        "swr:repository:auth:delete",
        "swr:retention:list",
        "swr:retention:get",
        "swr:retention:create",
        "swr:retention:update",
        "swr:retention:delete",
        "swr:domain:list",
        "swr:domain:get",
        "swr:domain:create",
        "swr:domain:update",
        "swr:domain:delete",
        "swr:share:list",
        "swr:share:get",
        "swr:share:feature:get",
        "swr:global:feature:get",
        "swr:agency:check",
        "swr:agency:create",
        "swr:accessory:list",
        "swr:reference:list"
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