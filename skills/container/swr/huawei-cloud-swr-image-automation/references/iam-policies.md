# IAM Permission Policies - SWR Image Automation Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud SWR Image Automation skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                 | Permission           | Purpose                                    |
| -------------------------- | -------------------- | ------------------------------------------ |
| `swr:syncregion:list`      | List sync regions    | Query available sync target regions         |
| `swr:sync:list`            | List sync repos      | Query auto-sync configurations             |
| `swr:syncjob:get`          | Get sync job status  | Check sync execution status                |
| `swr:trigger:list`         | List triggers        | Query trigger configurations               |
| `swr:trigger:get`          | Get trigger          | View specific trigger details              |

## Write Operations (Require Additional Authorization)

| API Action                 | Permission           | Purpose                                    |
| -------------------------- | -------------------- | ------------------------------------------ |
| `swr:sync:create`          | Create sync repo     | Configure cross-region image sync          |
| `swr:sync:delete`          | Delete sync repo     | Remove sync configuration                  |
| `swr:syncmanual:create`    | Manual sync          | Trigger manual image sync                  |
| `swr:trigger:create`       | Create trigger       | Set up auto-deploy trigger                 |
| `swr:trigger:update`       | Update trigger       | Modify trigger configuration               |
| `swr:trigger:delete`       | Delete trigger       | Remove trigger configuration               |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:syncregion:list",
        "swr:sync:list",
        "swr:syncjob:get",
        "swr:trigger:list",
        "swr:trigger:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Full Automation Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:syncregion:list",
        "swr:sync:list",
        "swr:sync:create",
        "swr:sync:delete",
        "swr:syncmanual:create",
        "swr:syncjob:get",
        "swr:trigger:list",
        "swr:trigger:get",
        "swr:trigger:create",
        "swr:trigger:update",
        "swr:trigger:delete"
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