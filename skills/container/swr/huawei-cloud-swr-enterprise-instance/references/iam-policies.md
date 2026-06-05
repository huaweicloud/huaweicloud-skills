# IAM Permission Policies - SWR Enterprise Instance Skill

## Overview

This document declares the IAM permissions required by the Huawei Cloud SWR Enterprise Instance skill. All permissions follow the principle of least privilege.

## Read-Only Operations

| API Action                          | Permission                   | Purpose                                        |
| ----------------------------------- | ---------------------------- | ---------------------------------------------- |
| `swr:instance:list`                 | List instances               | Query all enterprise instances                  |
| `swr:instance:get`                  | Get instance                 | View instance details                           |
| `swr:instanceNamespace:list`        | List instance namespaces     | Query instance namespaces                       |
| `swr:instanceNamespace:get`         | Get instance namespace       | View namespace details                          |
| `swr:instanceRegistry:list`         | List instance registries     | Query sync target registries                    |
| `swr:instanceRegistry:get`          | Get instance registry        | View registry details                           |
| `swr:instanceRepository:list`       | List instance repos          | Query repositories                              |
| `swr:instanceRepository:get`        | Get instance repo            | View repository details                         |
| `swr:instanceArtifact:list`         | List instance artifacts      | Query image versions/artifacts                  |
| `swr:instanceArtifact:get`          | Get instance artifact        | View artifact details                           |
| `swr:instanceCredential:list`       | List instance credentials    | Query long-term credentials                     |
| `swr:instanceEndpoint:list`         | List instance endpoints      | Query network access endpoints                  |
| `swr:instanceEndpoint:get`          | Get instance endpoint        | View endpoint details                           |
| `swr:instanceDomain:list`           | List domain names            | Query all domains                               |
| `swr:instanceDomain:get`            | Get domain overview          | View domain details                             |
| `swr:instanceJob:list`              | List instance jobs           | Query async job status                          |
| `swr:instanceJob:get`               | Get instance job             | View job details                                |
| `swr:instanceStatistic:get`         | Get instance statistics      | View instance resource statistics               |

## Write Operations (Require Additional Authorization)

| API Action                          | Permission                   | Purpose                                        |
| ----------------------------------- | ---------------------------- | ---------------------------------------------- |
| `swr:instance:create`               | Create instance              | Create enterprise registry instances            |
| `swr:instance:delete`               | Delete instance              | Remove enterprise instances (irreversible)      |
| `swr:instance:update`               | Update instance              | Modify instance configuration                   |
| `swr:instanceNamespace:create`      | Create instance namespace    | Create namespaces in instance                   |
| `swr:instanceNamespace:update`      | Update instance namespace    | Modify namespace settings                       |
| `swr:instanceNamespace:delete`      | Delete instance namespace    | Remove namespaces                               |
| `swr:instanceRegistry:create`       | Create instance registry     | Configure sync target registries                |
| `swr:instanceRegistry:update`       | Update instance registry     | Modify registry settings                        |
| `swr:instanceRegistry:delete`       | Delete instance registry     | Remove sync target registries                   |
| `swr:instanceRepository:delete`     | Delete instance repo         | Remove repositories                             |
| `swr:instanceRepository:update`     | Update instance repo         | Modify repository settings                      |
| `swr:instanceArtifact:delete`       | Delete instance artifact     | Remove image versions                           |
| `swr:instanceArtifact:scan`         | Scan instance artifact       | Trigger vulnerability scanning                  |
| `swr:instanceCredential:create`     | Create instance credential   | Obtain access credentials                       |
| `swr:instanceCredential:update`     | Update instance credential   | Enable/disable long-term credentials            |
| `swr:instanceCredential:delete`     | Delete instance credential   | Remove long-term credentials                    |
| `swr:instanceEndpoint:create`       | Create instance endpoint     | Configure VPC internal endpoints                |
| `swr:instanceEndpoint:delete`       | Delete instance endpoint     | Remove internal endpoints                       |
| `swr:instanceEndpoint:update`       | Update instance endpoint     | Configure public access whitelist               |
| `swr:instanceDomain:add`            | Add domain name              | Add custom domain                               |
| `swr:instanceDomain:delete`         | Delete domain name           | Remove custom domain                            |
| `swr:instanceDomain:update`         | Update domain name           | Update domain certificate                       |
| `swr:instanceJob:delete`            | Delete instance job          | Remove job records                              |

## Minimum Read-Only Policy (JSON)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "swr:instance:list",
        "swr:instance:get",
        "swr:instanceNamespace:list",
        "swr:instanceNamespace:get",
        "swr:instanceRegistry:list",
        "swr:instanceRegistry:get",
        "swr:instanceRepository:list",
        "swr:instanceRepository:get",
        "swr:instanceArtifact:list",
        "swr:instanceArtifact:get",
        "swr:instanceCredential:list",
        "swr:instanceEndpoint:list",
        "swr:instanceEndpoint:get",
        "swr:instanceDomain:list",
        "swr:instanceDomain:get",
        "swr:instanceJob:list",
        "swr:instanceJob:get",
        "swr:instanceStatistic:get"
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
        "swr:instance:list",
        "swr:instance:get",
        "swr:instance:create",
        "swr:instance:delete",
        "swr:instance:update",
        "swr:instanceNamespace:list",
        "swr:instanceNamespace:get",
        "swr:instanceNamespace:create",
        "swr:instanceNamespace:update",
        "swr:instanceNamespace:delete",
        "swr:instanceRegistry:list",
        "swr:instanceRegistry:get",
        "swr:instanceRegistry:create",
        "swr:instanceRegistry:update",
        "swr:instanceRegistry:delete",
        "swr:instanceRepository:list",
        "swr:instanceRepository:get",
        "swr:instanceRepository:update",
        "swr:instanceRepository:delete",
        "swr:instanceArtifact:list",
        "swr:instanceArtifact:get",
        "swr:instanceArtifact:delete",
        "swr:instanceArtifact:scan",
        "swr:instanceCredential:create",
        "swr:instanceCredential:list",
        "swr:instanceCredential:update",
        "swr:instanceCredential:delete",
        "swr:instanceEndpoint:create",
        "swr:instanceEndpoint:list",
        "swr:instanceEndpoint:get",
        "swr:instanceEndpoint:delete",
        "swr:instanceEndpoint:update",
        "swr:instanceDomain:add",
        "swr:instanceDomain:list",
        "swr:instanceDomain:get",
        "swr:instanceDomain:delete",
        "swr:instanceDomain:update",
        "swr:instanceJob:list",
        "swr:instanceJob:get",
        "swr:instanceJob:delete",
        "swr:instanceStatistic:get"
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