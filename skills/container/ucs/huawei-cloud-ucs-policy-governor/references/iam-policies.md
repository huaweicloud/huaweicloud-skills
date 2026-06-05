# IAM Permission Policies - UCS Policy Governor Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud UCS Policy Governor skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                          | Permission        | Purpose                                |
| ----------------------------------- | ----------------- | -------------------------------------- |
| `ucs:policyInstance:get`            | Get policy        | View policy instance details           |
| `ucs:policyInstance:list`           | List policies     | List all policy instances              |
| `ucs:policyDefinition:list`         | List definitions  | List available policy definitions      |
| `ucs:policyDefinition:get`          | Get definition    | View policy definition details         |
| `ucs:policyJob:list`                | List jobs         | List policy enforcement jobs           |
| `ucs:policyJob:get`                 | Get job           | View policy enforcement job details    |

## Write Operations (Require Additional Authorization)

| API Action                                  | Permission        | Purpose                                |
| ------------------------------------------- | ----------------- | -------------------------------------- |
| `ucs:clusterPolicyInstance:create`           | Create policy     | Create cluster-level policy instances  |
| `ucs:clusterGroupPolicyInstance:create`      | Create policy     | Create fleet group-level policy instances |
| `ucs:policyInstance:update`                  | Update policy     | Modify policy instances                |
| `ucs:policyInstance:delete`                  | Delete policy     | Remove policy instances                |
| `ucs:clusterPolicy:enable`                   | Enable policy     | Enable cluster-level policy enforcement |
| `ucs:clusterPolicy:disable`                  | Disable policy    | Disable cluster-level policy enforcement |
| `ucs:clusterGroupPolicy:enable`              | Enable policy     | Enable fleet group-level policy enforcement |
| `ucs:clusterGroupPolicy:disable`             | Disable policy    | Disable fleet group-level policy enforcement |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ucs:policyInstance:get",
        "ucs:policyInstance:list",
        "ucs:policyDefinition:list",
        "ucs:policyDefinition:get",
        "ucs:policyJob:list",
        "ucs:policyJob:get"
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
        "ucs:policyInstance:get",
        "ucs:policyInstance:list",
        "ucs:clusterPolicyInstance:create",
        "ucs:clusterGroupPolicyInstance:create",
        "ucs:policyInstance:update",
        "ucs:policyInstance:delete",
        "ucs:policyDefinition:list",
        "ucs:policyDefinition:get",
        "ucs:policyJob:list",
        "ucs:policyJob:get",
        "ucs:clusterPolicy:enable",
        "ucs:clusterPolicy:disable",
        "ucs:clusterGroupPolicy:enable",
        "ucs:clusterGroupPolicy:disable"
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