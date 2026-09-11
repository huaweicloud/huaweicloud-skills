# IAM Policies — GaussDB (Least Privilege)

This document lists least-privilege IAM policies for the `huawei-cloud-gaussdb-instance-management` Skill actions. Apply the narrowest policy that covers the tier you are using.

## Read-only (Query + Analyze — R3)

Required actions for listing/querying instances, flavors, databases, deployment form, security info:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gaussdb:listInstance",
        "gaussdb:getInstance",
        "gaussdb:listFlavors",
        "gaussdb:listDatabase",
        "gaussdb:listNode",
        "gaussdb:getEngineVersion",
        "gaussdb:showDeploymentForm",
        "gaussdb:listReadonlyNodes",
        "gaussdb:showShardDiskMessages",
        "gaussdb:showEip"
      ],
      "Resource": [
        "gaussdb:*:*:instance:*",
        "gaussdb:*:*:flavor:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:get",
        "vpc:securityGroupRules:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Manage (R2 — create instance / backup / add nodes)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gaussdb:createInstance",
        "gaussdb:createBackup",
        "gaussdb:addReadonlyNode",
        "gaussdb:addShardingNode",
        "gaussdb:expandCluster"
      ],
      "Resource": ["gaussdb:*:*:instance:*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:get",
        "vpc:subnets:get",
        "vpc:securityGroups:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Manage (R1 — database permission change / delete instance)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gaussdb:updateDatabasePermission",
        "gaussdb:deleteInstance"
      ],
      "Resource": ["gaussdb:*:*:instance:*"]
    }
  ]
}
```

> **Note:** Cloud service action names above follow Huawei Cloud IAM's `service:action`
> granularity. If a specific action key is not accepted by your IAM console, grant the
> coarse-grained `GaussDB FullAccess` (read+manage) or `GaussDB ReadOnlyAccess`
> (read-only) **and** `VPC ReadOnlyAccess`, then tighten later. Never embed AK/SK in
> policies or scripts.