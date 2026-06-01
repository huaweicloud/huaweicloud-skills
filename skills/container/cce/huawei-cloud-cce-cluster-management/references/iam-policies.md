# CCE IAM Permission Configuration

## Overview

IAM permission policy descriptions required for Huawei Cloud CCE cluster management.

## Key Parameters

| Permission | Description |
|------|------|
| `cce:cluster:list` | Query cluster list |
| `cce:cluster:get` | Query cluster details |
| `cce:cluster:create` | Create cluster |
| `cce:cluster:delete` | Delete cluster |
| `cce:cluster:update` | Update cluster (hibernate/wake/bind EIP) |
| `cce:node:list` | Query node list |
| `cce:node:get` | Query node details |
| `cce:node:delete` | Delete node |
| `cce:node:update` | Update node (cordon/uncordon/drain) |
| `cce:nodepool:list` | Query node pool list |
| `cce:nodepool:update` | Update node pool (scale up/down) |
| `cce:addon:list` | Query addon list |
| `cce:addon:get` | Query addon details |

## Minimum Required Policy (JSON)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cce:cluster:list",
        "cce:cluster:get",
        "cce:cluster:create",
        "cce:cluster:delete",
        "cce:cluster:update",
        "cce:node:list",
        "cce:node:get",
        "cce:node:delete",
        "cce:node:update",
        "cce:nodepool:list",
        "cce:nodepool:update",
        "cce:addon:list",
        "cce:addon:get"
      ],
      "Resource": ["CCE:*:*:cluster:*", "CCE:*:*:node:*", "CCE:*:*:nodepool:*"]
    }
  ]
}
```

## System Policies

| System Policy | Applicable Scenario |
|---------|---------|
| `CCE Administrator` | Full cluster management permissions |
| `CCE Viewer` | Read-only permissions, view cluster information |
| `CES ReadOnlyAccess` | Query monitoring metrics |

## Example

```bash
# Recommended combination: CCE Administrator + CES ReadOnlyAccess
# Add the above policies to user groups in the IAM console
```