# IAM Permission Policies for CCI Operations

## Minimum Required Permissions

| Permission | Description |
|---|---|
| `cci:namespace:create` | Create namespace |
| `cci:namespace:get` | Read namespace |
| `cci:namespace:list` | List namespaces |
| `cci:namespace:delete` | Delete namespace |
| `cci:network:create` | Create Network |
| `cci:network:get` | Read Network |
| `cci:network:list` | List Networks |
| `cci:network:delete` | Delete Network |
| `cci:pod:create` | Create Pod |
| `cci:pod:get` | Read Pod |
| `cci:pod:list` | List Pods |
| `cci:pod:delete` | Delete Pod |
| `cci:deployment:create` | Create Deployment |
| `cci:deployment:get` | Read Deployment |
| `cci:deployment:list` | List Deployments |
| `cci:deployment:update` | Update/scale Deployment |
| `cci:deployment:delete` | Delete Deployment |
| `cci:statefulset:create` | Create StatefulSet |
| `cci:statefulset:get` | Read StatefulSet |
| `cci:statefulset:list` | List StatefulSets |
| `cci:statefulset:update` | Update StatefulSet |
| `cci:statefulset:delete` | Delete StatefulSet |
| `vpc:vpcs:list` | List VPCs (for Network creation) |
| `vpc:subnets:get` | Read subnet details (for Network creation) |

## Minimum Required Policy JSON

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cci:namespace:create",
        "cci:namespace:get",
        "cci:namespace:list",
        "cci:namespace:delete",
        "cci:network:create",
        "cci:network:get",
        "cci:network:list",
        "cci:network:delete",
        "cci:pod:create",
        "cci:pod:get",
        "cci:pod:list",
        "cci:pod:delete",
        "cci:deployment:create",
        "cci:deployment:get",
        "cci:deployment:list",
        "cci:deployment:update",
        "cci:deployment:delete",
        "cci:statefulset:create",
        "cci:statefulset:get",
        "cci:statefulset:list",
        "cci:statefulset:update",
        "cci:statefulset:delete",
        "vpc:vpcs:list",
        "vpc:subnets:get"
      ],
      "Resource": [
        "CCI:*:*:namespace:*",
        "CCI:*:*:network:*",
        "CCI:*:*:pod:*",
        "CCI:*:*:deployment:*",
        "CCI:*:*:statefulset:*"
      ]
    }
  ]
}
```

## System Policies

| System Policy | Applicable Scenario |
|---|---|
| `CCI Administrator` | Full CCI management permissions |
| `CCI Viewer` | Read-only, view all CCI resources |
| `VPC Viewer` | Read-only VPC access (for Network creation) |

## EIPPool Additional Permissions

If using EIPPool, add these permissions to the policy:

| Permission | Description |
|---|---|
| `cci:eippool:create` | Create EIPPool |
| `cci:eippool:get` | Read EIPPool |
| `cci:eippool:list` | List EIPPools |
| `cci:eippool:delete` | Delete EIPPool |
| `vpc:publicIps:list` | List available EIPs |

## Permission Failure Handling Process

When any command fails due to permission errors:

1. Read this iam-policies.md file
2. Show required permission list and policy JSON to user
3. Guide user to create custom policy in IAM console
4. Pause execution and wait for user confirmation