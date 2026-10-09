# IAM Permission Policies Reference

This document defines the official Huawei Cloud Identity and Access Management (IAM) policies required for Kubernetes cluster migration to CCE. All policy identifiers, syntax structures, and action names are verified through Huawei Cloud IAM 5.0 metadata (`hcloud IAM GetAuthorizationSchemaV5` and `hcloud IAM GetPolicyVersionV5`).

---

## 1. Official System Policies

For administrative users or migration automation roles, the following official Huawei Cloud IAM 5.0 system-managed policies can be assigned:

|System Policy Name|Policy URN|Scope|Description|
|-|-|-|-|
|`CCEFullPolicy`|`iam::system:policy:CCEFullPolicy`|Region-level|Full administrative access to CCE clusters, nodes, workloads, and dependent infrastructure (ECS, EVS, VPC, ELB, SFS).|
|`CCEReadOnlyPolicy`|`iam::system:policy:CCEReadOnlyPolicy`|Region-level|Read-only access to query CCE clusters, configurations, add-ons, and node pools.|
|`SWRFullAccessPolicy`|`iam::system:policy:SWRFullAccessPolicy`|Region-level|Full access to create repositories and push container images to Software Repository for Container (SWR).|
|`EVSFullAccessPolicy`|`iam::system:policy:EVSFullAccessPolicy`|Region-level|Full access to manage Elastic Volume Service disks for EVS block PVs.|
|`SFSTurboFullAccessPolicy`|`iam::system:policy:SFSTurboFullAccessPolicy`|Region-level|Full access to create and mount SFS Turbo shared file systems for high-performance PVs.|
|`VPCFullAccessPolicy`|`iam::system:policy:VPCFullAccessPolicy`|Region-level|Full access to VPC subnets, security groups, and routing.|
|`ELBFullAccessPolicy`|`iam::system:policy:ELBFullAccessPolicy`|Region-level|Full access to manage Dedicated Elastic Load Balancers for Kubernetes Ingress.|

### Official System Policy Document: `CCEFullPolicy` (Verified Version 5.0)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Action": [
        "cce:*:*",
        "ecs:*:*",
        "evs:*:*",
        "vpc:*:*",
        "bms:*:get*",
        "bms:*:list*",
        "ims:*:get*",
        "ims:*:list*",
        "elb:*:get",
        "elb:*:list",
        "nat:*:get",
        "nat:*:list",
        "sfs:*:get*",
        "sfs:shares:ShareAction",
        "sfsturbo:*:get*",
        "sfsturbo:shares:ShareAction",
        "tms:resourceTags:list",
        "kps:domainKeypairs:list",
        "kps:domainKeypairs:get",
        "kms:cmk:get",
        "kms:cmk:list",
        "aom:*:get",
        "aom:*:list",
        "aom:autoScalingRule:*",
        "apm:icmgr:*"
      ],
      "Effect": "Allow"
    }
  ]
}
```

---

## 2. Least-Privilege Custom Policy for Migration Agent

When full administrative permissions are not desired, create a custom IAM 5.0 policy granting strictly the actions necessary for cluster assessment, kubeconfig synchronization, add-on verification, container image sync, and multi-storage PV provisioning.

### Least-Privilege Policy: `CCEMigrationOperatorCustomPolicy`

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Sid": "CCEDiscoveryAndAccess",
      "Effect": "Allow",
      "Action": [
        "cce:cluster:list",
        "cce:cluster:getCluster",
        "cce:cluster:getEndpoints",
        "cce:cluster:getConfiguration",
        "cce:cluster:generateClientCredential",
        "cce:node:list",
        "cce:node:getNode",
        "cce:nodepool:list",
        "cce:nodepool:getNodepool",
        "cce:addonInstance:list",
        "cce:addonInstance:get",
        "cce:addonInstance:create",
        "cce:quota:get",
        "cce:job:get"
      ]
    },
    {
      "Sid": "SWRImageSynchronization",
      "Effect": "Allow",
      "Action": [
        "swr:repo:listRepos",
        "swr:repo:createRepo",
        "swr:repo:getRepo",
        "swr:repo:listRepoTags",
        "swr:repo:upload",
        "swr:repo:download",
        "swr:namespace:listNamespaces",
        "swr:namespace:createNamespace"
      ]
    },
    {
      "Sid": "MultiTypeStorageProvisioning",
      "Effect": "Allow",
      "Action": [
        "evs:volumes:get",
        "evs:volumes:list",
        "evs:volumes:create",
        "evs:volumes:use",
        "sfs:*:get*",
        "sfs:shares:ShareAction",
        "sfsturbo:shares:getShare",
        "sfsturbo:shares:getAllShares",
        "sfsturbo:shares:createShare",
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:ListBucket",
        "obs:bucket:GetBucketLocation",
        "obs:object:GetObject",
        "obs:object:PutObject"
      ]
    },
    {
      "Sid": "NetworkAndLoadBalancerAccess",
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:get",
        "vpc:vpcs:list",
        "vpc:subnets:get",
        "vpc:subnets:list",
        "vpc:securityGroups:get",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:get",
        "vpc:securityGroupRules:list",
        "vpc:securityGroupRules:create",
        "nat:natGateways:get",
        "nat:natGateways:list",
        "nat:snatRules:get",
        "nat:snatRules:list",
        "elb:loadbalancers:show",
        "elb:loadbalancers:list",
        "elb:listeners:show",
        "elb:listeners:list",
        "eip:publicIps:list",
        "eip:publicIps:get",
        "eip:bandwidths:list",
        "eip:bandwidths:get"
      ]
    }
  ]
}
```

---

## 3. Storage-Specific IAM Considerations

- **EVS Block Storage**: Required by the CCE `everest-csi-provisioner` to dynamically allocate, attach, and expand block volumes (`csi-disk`).
- **SFS / SFS Turbo File Storage**: Requires VPC interconnectivity and security group rules on port 2049 (NFS) and 111 (portmapper).
- **OBS Object Storage**: Used for both Velero backup storage location and application-level object PVs (`csi-obs`). The migration operator must have permission to create and write to the migration backup bucket.
