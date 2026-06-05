# IAM Permission Policies - SWR Image Management Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud SWR Image Management skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `swr:namespace:list`       | List namespaces   | Query all SWR organizations            |
| `swr:namespace:get`        | Get namespace     | View individual namespace information  |
| `swr:repository:list`      | List repositories | Query image repositories               |
| `swr:repository:get`       | Get repository    | View repository details                |
| `swr:tag:list`             | List tags         | Query image tags/versions              |
| `swr:tag:get`              | Get tag           | View specific tag details              |
| `swr:quota:get`            | Get quota         | Check resource quotas                  |

## Write Operations (Require Additional Authorization)

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `swr:namespace:create`     | Create namespace  | Create SWR organizations               |
| `swr:namespace:delete`     | Delete namespace  | Remove organizations (irreversible)    |
| `swr:repository:create`    | Create repo       | Create image repositories              |
| `swr:repository:update`    | Update repo       | Modify repository properties           |
| `swr:repository:delete`    | Delete repo       | Remove repositories (irreversible)     |
| `swr:tag:create`           | Create tag        | Create/retag image versions            |
| `swr:tag:delete`           | Delete tag        | Remove image versions (irreversible)   |
| `swr:login:get`            | Get login token   | Obtain docker login credentials        |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:namespace:list",
        "swr:namespace:get",
        "swr:repository:list",
        "swr:repository:get",
        "swr:tag:list",
        "swr:tag:get",
        "swr:quota:get"
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
        "swr:namespace:list",
        "swr:namespace:get",
        "swr:namespace:create",
        "swr:namespace:delete",
        "swr:repository:list",
        "swr:repository:get",
        "swr:repository:create",
        "swr:repository:update",
        "swr:repository:delete",
        "swr:tag:list",
        "swr:tag:get",
        "swr:tag:create",
        "swr:tag:delete",
        "swr:login:get",
        "swr:quota:get"
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