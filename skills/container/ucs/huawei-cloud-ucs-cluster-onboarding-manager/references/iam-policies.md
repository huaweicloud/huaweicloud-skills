# IAM Permission Policies - UCS Cluster Onboarding Manager Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud UCS Cluster Onboarding Manager skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `ucs:cluster:get`          | Get cluster       | View cluster details                   |
| `ucs:cluster:list`         | List clusters     | List all managed clusters              |
| `ucs:clusterGroup:get`     | Get group         | View fleet group details               |
| `ucs:clusterGroup:list`    | List groups       | List fleet groups                      |
| `ucs:clusterAccess:get`    | Get access info   | Obtain cluster access information      |
| `ucs:quota:get`            | Get quota         | Check UCS resource quotas              |

## Write Operations (Require Additional Authorization)

| API Action                 | Permission        | Purpose                                |
| -------------------------- | ----------------- | -------------------------------------- |
| `ucs:cluster:create`       | Register cluster  | Register cluster to UCS                |
| `ucs:cluster:delete`       | Delete cluster    | Remove cluster from UCS                |
| `ucs:cluster:update`       | Update cluster    | Modify cluster properties              |
| `ucs:cluster:joinGroup`    | Join group        | Add cluster to fleet group             |
| `ucs:cluster:leaveGroup`   | Leave group       | Remove cluster from fleet group        |
| `ucs:cluster:retryActivation` | Retry activation | Retry cluster activation             |
| `ucs:clusterGroup:create`  | Create group      | Create fleet group                     |
| `ucs:clusterGroup:delete`  | Delete group      | Remove fleet group                     |
| `ucs:clusterGroup:update`  | Update group      | Update fleet group description/add clusters |
| `ucs:kubeconfig:create`    | Create kubeconfig | Obtain cluster kubeconfig              |
| `ucs:federationKubeconfig:get` | Get federation | Download federation kubeconfig         |
| `ucs:clusterConf:create`   | Create conf       | Create cluster configuration           |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ucs:cluster:get",
        "ucs:cluster:list",
        "ucs:clusterGroup:get",
        "ucs:clusterGroup:list",
        "ucs:clusterAccess:get",
        "ucs:quota:get"
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
        "ucs:cluster:get",
        "ucs:cluster:list",
        "ucs:cluster:create",
        "ucs:cluster:delete",
        "ucs:cluster:update",
        "ucs:cluster:joinGroup",
        "ucs:cluster:leaveGroup",
        "ucs:cluster:retryActivation",
        "ucs:clusterGroup:get",
        "ucs:clusterGroup:list",
        "ucs:clusterGroup:create",
        "ucs:clusterGroup:delete",
        "ucs:clusterGroup:update",
        "ucs:clusterAccess:get",
        "ucs:quota:get",
        "ucs:kubeconfig:create",
        "ucs:federationKubeconfig:get",
        "ucs:clusterConf:create"
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