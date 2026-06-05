# UCS Cluster Onboarding API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud UCS (Universal Cloud Service) cluster onboarding operations using hcloud CLI. All commands follow the standard format: `hcloud UCS <Operation> --param=value --cli-region=<region>`.

## Authentication

### Environment Variables

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
```

### hcloud CLI Configuration

```bash
hcloud configure

hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEI_CLOUD_AK` to check credentials

## RegisterCluster — Kubernetes-Style Parameters

⚠️ **Important**: `RegisterCluster` uses Kubernetes-style (structured) parameters, NOT simple flat parameters. The command follows the pattern of a Kubernetes resource manifest with `--apiVersion`, `--kind`, `--metadata.*`, and `--spec.*` parameters.

### Required Parameters (All Cluster Types)

| Parameter              | Description                          | Example Value           |
| ---------------------- | ------------------------------------ | ----------------------- |
| `--apiVersion`         | API version (always `v1`)            | `v1`                    |
| `--kind`               | Resource kind (always `Cluster`)     | `Cluster`               |
| `--metadata.name`      | Display name for the cluster in UCS  | `prod-backend-cluster`  |
| `--spec.category`      | Cluster category                     | `self` or `onpremise`   |
| `--spec.provider`      | Cluster provider                     | `huaweicloud` or `self_managed` |
| `--spec.type`          | Cluster type                         | `cce` or `Kubernetes`   |
| `--spec.manageType`    | Management type                      | `grouped` or `discrete` |
| `--spec.country`       | Country code                         | `CN`                    |
| `--spec.city`          | City code                            | `110000`                |

### CCE Cluster-Specific Parameters

| Parameter              | Description                          | Required for CCE        |
| ---------------------- | ------------------------------------ | ----------------------- |
| `--metadata.uid`       | CCE cluster ID                       | Yes (for CCE import)    |
| `--spec.projectID`     | Huawei Cloud project ID              | Yes (for CCE import)    |
| `--spec.region`        | Region where CCE cluster resides     | Yes (for CCE import)    |

### Self-Managed Cluster-Specific Parameters

| Parameter              | Description                          | Required for SelfManaged |
| ---------------------- | ------------------------------------ | ----------------------- |
| `--metadata.annotations.kubeconfig` | Kubeconfig YAML content | Yes (for attached clusters) |

### Optional Parameters

| Parameter              | Description                          |
| ---------------------- | ------------------------------------ |
| `--metadata.labels.*`  | Custom labels (key-value pairs)      |
| `--spec.clusterGroupID`| Fleet group ID to assign on creation |
| `--spec.projectID`     | Project ID (CCE import)              |
| `--spec.region`        | Region (CCE import)                  |

## Cluster Registration Operations

### 1. Register a CCE Cluster

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cce-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

**Response Example** (verified):

UCS API returns a simple JSON response with the cluster UID:

```json
{
  "uid": "aabe1df4-5c1c-11f1-a7f6-0255ac10026a"
}
```

**Key Fields**:
- `metadata.uid`: UCS-assigned cluster UUID (different from CCE cluster ID, not flat `id`)
- `status.phase`: Initial phase is `Registering`, transitions to `Available` upon successful registration (not flat `status`)
- `spec.category`: Registered cluster category

### 2. Register a Self-Managed Cluster

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-content> --cli-region=cn-north-4
```

**Self-Managed Cluster Requirements**:
- The kubeconfig must be valid YAML in standard Kubernetes format
- The cluster API server must be reachable from UCS management plane
- Ensure the kubeconfig user has sufficient RBAC permissions
- Recommended: use a dedicated service account with cluster-admin or admin privileges

### 3. Delete (Deregister) a Cluster

```bash
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID (not CCE cluster ID)
- `--cli-region` (required): Region ID

⚠️ **Warning**: Deregistration removes the cluster from UCS management. All policy governance, fleet grouping, and federation access for this cluster will be disabled. This is irreversible — you must re-register to restore UCS management.

### 4. Retry Cluster Activation

```bash
hcloud UCS RetryClusterActivation --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID
- `--cli-region` (required): Region ID

**Use Case**: Retry activation when cluster status is stuck in `Registering` or `Unavailable`.

## Cluster Query Operations

### 1. Show Cluster Details

```bash
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID
- `--cli-region` (required): Region ID

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList pattern]:

UCS API returns Kubernetes-style objects, not flat JSON. Based on the verified `ShowClusterList` response, `ShowCluster` likely returns a single k8s-style Cluster object:

```json
{
  "kind": "Cluster",
  "apiVersion": "v1",
  "metadata": {
    "name": "my-cluster",
    "uid": "b1c1e9b6-65e6-11ee-8d84-0255ac1000d3",
    "creationTimestamp": "2026-03-15T10:30:00Z",
    "annotations": {
      "vpcId": ""
    }
  },
  "spec": {
    "category": "self",
    "provider": "huaweicloud",
    "type": "cce",
    "manageType": "grouped",
    "country": "CN",
    "city": "110000",
    "syncMode": "Push",
    "apiEndpoint": "https://kubernetes.default.svc.cluster.local"
  },
  "status": {
    "phase": "Available",
    "conditions": [
      {
        "type": "Ready",
        "status": "True",
        "lastTransitionTime": "2026-05-20T14:20:00Z",
        "reason": "Available",
        "message": "Cluster is available"
      }
    ]
  }
}
```

### 2. List Managed Clusters

```bash
hcloud UCS ShowClusterList --cli-region=cn-north-4

hcloud UCS ShowClusterList --limit=20 --offset=0 --cli-region=cn-north-4

hcloud UCS ShowClusterList --category=self --managetype=grouped --cli-region=cn-north-4

hcloud UCS ShowClusterList --clustergroupid=<group-id> --cli-region=cn-north-4

hcloud UCS ListManagedClusters --cli-region=cn-north-4

hcloud UCS ListManagedClusters --unimported --cli-region=cn-north-4
```

**ShowClusterList Parameters**:
- `--cli-region` (required): Region ID
- `--limit` (optional): Page size, default 20, max 100
- `--offset` (optional): Page offset
- `--category` (optional): Filter by cluster category (`self`, `onpremise`)
- `--managetype` (optional): Filter by management type (`grouped`, `discrete`)
- `--clustergroupid` (optional): Filter by fleet group ID
- `--clusterids` (optional): Filter by specific cluster IDs
- `--enablestatus` (optional): Filter by enable status
- `--order` (optional): Sort order (`asc`, `desc`)
- `--order_by` (optional): Sort field

⚠️ **Note**: `ShowClusterList` does NOT support `--name` as a filter parameter. Use `--category`, `--managetype`, or `--clustergroupid` for filtering.

**Response Example** (verified):

```json
{
  "items": [
    {
      "kind": "Cluster",
      "apiVersion": "v1",
      "metadata": {
        "name": "test1",
        "uid": "b1c1e9b6-65e6-11ee-8d84-0255ac1000d3",
        "creationTimestamp": "2023-10-08T14:26:39Z",
        "annotations": {
          "vpcId": ""
        }
      },
      "spec": {
        "syncMode": "Push",
        "manageType": "discrete",
        "apiEndpoint": "https://kubernetes.default.svc.cluster.local",
        "provider": "huaweicloud",
        "type": "baremetal",
        "category": "onpremise",
        "country": "CN",
        "city": "110000",
        "IsDownloadedCert": false,
        "operatorNamespace": "05949eb4190010e40f36c017b62fafa0"
      },
      "status": {
        "conditions": [
          {
            "type": "Ready",
            "status": "False",
            "lastTransitionTime": "2023-10-09T22:27:05.907728+08:00",
            "reason": "Failed",
            "message": "currently no agents available"
          }
        ],
        "phase": "Failed"
      }
    }
  ],
  "total": 1
}
```

**Key Fields**:
- `items`: Array of k8s-style Cluster objects (not flat objects)
- `total`: Total count of clusters (not `total_count`)
- `metadata.uid`: Cluster UUID (not flat `id`)
- `metadata.name`: Cluster display name
- `spec.category`: Cluster category (not flat `cluster_type`)
- `spec.provider`: Cluster provider
- `spec.type`: Cluster type
- `spec.manageType`: Management type
- `status.phase`: Cluster phase (`Available`, `Failed`, etc.) (not flat `status`)
- `status.conditions`: Array of status conditions with `type`, `status`, `reason`, `message`

**ListManagedClusters Parameters**:
- `--unimported` (optional): Boolean flag to list only unimported clusters

### 3. Update Cluster

```bash
hcloud UCS UpdateCluster --clusterid=<ucs-cluster-id> --apiVersion=v1 --kind=Cluster --spec.city=Shanghai --spec.country=CN --cli-region=cn-north-4
```

**Parameters** (Kubernetes-style):
- `--clusterid` (required, path): UCS cluster ID
- `--apiVersion` (required): Must be `v1`
- `--kind` (required): Must be `Cluster`
- `--metadata.annotations` (optional): Updated annotations
- `--spec.city` (optional): Updated city
- `--spec.country` (optional): Updated country
- `--spec.workerConfig.replicas` (optional): Updated worker config replicas
- `--spec.workerConfig.strategy.*` (optional): Updated worker config strategy
- `--cli-region` (required): Region ID

### 4. Show Cluster Access Information

```bash
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

With optional parameters:

```bash
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --region=cn-north-4 --vpcendpoint=true --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID
- `--region` (optional): Region
- `--vpcendpoint` (optional): VPC endpoint flag
- `--cli-region` (required): Region ID

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList pattern]:

The exact response format for `ShowClusterAccessInfo` has not been verified. Based on the verified k8s-style pattern from `ShowClusterList`, access info may be returned as a structured object rather than a flat JSON object. The likely fields include:

- API server endpoint address (public and/or private)
- Access type (`Public`, `Private`, `Both`)
- Intranet endpoint (for CCE clusters)

**Key Fields** (expected, format to be verified):
- API server endpoint: Cluster API server address (field name TBD)
- Access type: Network access type (`Public`, `Private`, `Both`)
- Intranet endpoint: Internal network endpoint

## Fleet Group Operations

### 1. Register Fleet Group

```bash
hcloud UCS RegisterClusterGroup --metadata.name=production-group --spec.description="All production clusters" --cli-region=cn-north-4
```

With initial cluster association:

```bash
hcloud UCS RegisterClusterGroup --metadata.name=production-group --spec.description="All production clusters" --spec.clusterIds.1=<cluster-id-1> --cli-region=cn-north-4
```

**Parameters**:
- `--metadata.name` (required): Fleet group display name (1-128 chars)
- `--spec.description` (optional): Group description
- `--spec.clusterIds.1` (optional): Initial cluster ID to associate
- `--cli-region` (required): Region ID

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList pattern]:

UCS API returns Kubernetes-style objects, not flat JSON. Based on the verified k8s-style pattern from `ShowClusterList`, `RegisterClusterGroup` likely returns a k8s-style ClusterGroup object with `kind`, `apiVersion`, `metadata`, `spec`, and `status` fields rather than flat fields like `id`, `name`, `cluster_count`.
```

### 2. List Fleet Groups

```bash
hcloud UCS ListClusterGroup --limit=20 --offset=0 --cli-region=cn-north-4
```

**Parameters**:
- `--limit` (optional): Page size
- `--offset` (optional): Page offset
- `--order` (optional): Sort order
- `--order_by` (optional): Sort field
- `--cli-region` (required): Region ID

### 3. Show Fleet Group Details

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required): Fleet group ID
- `--cli-region` (required): Region ID

### 4. Update Fleet Group Description

```bash
hcloud UCS UpdateClusterGroup --clustergroupid=<group-id> --description="Updated description" --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required): Fleet group ID
- `--description` (optional): New description
- `--cli-region` (required): Region ID

### 5. Add Clusters to Fleet Group

```bash
hcloud UCS UpdateClusterGroupAssociatedClusters --clustergroupid=<group-id> --clusterIds.1=<cluster-id-1> --clusterIds.2=<cluster-id-2> --cli-region=cn-north-4
```

Or add a single cluster:

```bash
hcloud UCS JoinGroup --clusterid=<cluster-id> --clusterGroupID=<group-id> --cli-region=cn-north-4
```

### 6. Remove Cluster from Fleet Group

```bash
hcloud UCS LeaveGroup --clusterid=<cluster-id> --cli-region=cn-north-4
```

### 7. Delete Fleet Group

```bash
hcloud UCS DeleteClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required): Fleet group ID
- `--cli-region` (required): Region ID

⚠️ **Warning**: Deleting a fleet group removes the organizational grouping but does not deregister the clusters within it. Clusters remain individually managed by UCS.

## Kubeconfig Operations

### 1. Create Cluster Kubeconfig

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID
- `--cli-region` (required): Region ID

**Response**: Returns a Kubernetes kubeconfig YAML content that can be saved to a file for `kubectl` access.

### 2. Create Cluster Configuration

```bash
hcloud UCS CreateClusterConf --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required): UCS cluster ID
- `--cli-region` (required): Region ID

### 3. Download Federation Kubeconfig

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required): Fleet group ID
- `--duration` (required): Kubeconfig validity duration in seconds
- `--cli-region` (required): Region ID

**Response**: Returns a federation kubeconfig YAML that provides unified access to all clusters in the fleet group.

**Use Cases**:
- Multi-cluster workload distribution
- Cross-cluster resource queries
- Federation-level kubectl operations

## Quota Operations

### 1. Show UCS Quotas

```bash
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

**Parameters**:
- `--domainid` (required): Account ID (domain ID)
- `--cli-region` (required): Region ID

**Response Example** (verified):

```json
{
  "quotas": {
    "resources": [
      {
        "type": "cluster",
        "quota": 50,
        "used": 1,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "clustergroup",
        "quota": 50,
        "used": 0,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "rule",
        "quota": 50,
        "used": 0,
        "unit": "",
        "min": 20,
        "max": 100
      },
      {
        "type": "federation",
        "quota": 1,
        "used": 0,
        "unit": "",
        "min": 1,
        "max": 50
      }
    ]
  }
}
```

**Key Fields**:
- `type`: Resource type (`cluster`, `clustergroup`, `rule`, `federation`) — note lowercase `clustergroup`, not `clusterGroup`
- `quota`: Maximum allowed count (not `quota_limit`)
- `used`: Current usage count
- `unit`: Unit of measurement
- `min`: Minimum quota value
- `max`: Maximum quota value

## Common Region IDs

| Region Name                    | Region ID        |
| ------------------------------ | ---------------- |
| North China - Beijing 4        | `cn-north-4`     |
| North China - Beijing 1        | `cn-north-1`     |
| East China - Shanghai 1        | `cn-east-3`      |
| East China - Shanghai 2        | `cn-east-2`      |
| South China - Guangzhou        | `cn-south-1`     |
| South China - Shenzhen         | `cn-south-4`     |
| Southwest China - Guiyang 1    | `cn-southwest-2` |
| Asia Pacific - Bangkok         | `ap-southeast-2` |
| Asia Pacific - Singapore       | `ap-southeast-1` |
| Asia Pacific - Hong Kong       | `ap-southeast-3` |
| Europe - Paris                 | `eu-west-0`      |

## Common Errors

| Error                   | Cause                       | Solution                                        |
| ----------------------- | --------------------------- | ------------------------------------------------ |
| `InvalidAccessKeyId`    | Invalid AK/SK               | Check credential configuration via `hcloud configure list` |
| `ClusterNotFound`       | Cluster does not exist      | Verify cluster ID with `ShowCluster --clusterid=<id>` |
| `ClusterAlreadyRegistered` | Cluster already in UCS  | Use `ShowClusterList` to check existing registration |
| `QuotaExceeded`         | Resource quota limit        | Check quotas with `ShowQuota --domainid=<account-id>` |
| `InvalidKubeconfig`     | Invalid kubeconfig format   | Verify kubeconfig is valid YAML with correct structure |
| `GroupNotFound`         | Fleet group does not exist  | Verify group ID with `ShowClusterGroup --clustergroupid=<id>` |
| `GroupAlreadyExists`    | Fleet group name conflict   | Check with `ListClusterGroup` first             |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                 |
| `MissingDomainId`       | ShowQuota missing domainid  | Provide `--domainid=<account-id>` parameter     |
| `MissingRequiredParams` | Missing required k8s-style params | Provide all required `--apiVersion`, `--kind`, `--metadata.name`, `--spec.*` parameters; note `spec.category` uses `self`/`onpremise` (not `CCE`/`AttachedCluster`) |
| `InvalidCategory`       | Invalid spec.category value         | Use `self` for CCE clusters, `onpremise` for self-managed clusters (not `CCE`/`AttachedCluster`) |
| `InvalidProvider`       | Invalid spec.provider value         | Use `huaweicloud` for CCE clusters (not `huawei_cloud`) |
| `InvalidType`           | Invalid spec.type value             | Use lowercase `cce` for CCE clusters (not uppercase `CCE`) |
| `InvalidCity`           | Invalid spec.city value             | Use city codes like `110000` (not city names like `Beijing`) |

## Related Documentation

- [Huawei Cloud UCS Documentation](https://support.huaweicloud.com/ucs/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)