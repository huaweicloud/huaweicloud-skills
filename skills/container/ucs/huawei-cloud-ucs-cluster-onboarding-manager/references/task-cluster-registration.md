# Task: Cluster Registration & Deregistration

## Overview

UCS cluster registration (onboarding) enables unified management of Kubernetes clusters — both Huawei Cloud CCE clusters and self-managed Kubernetes clusters — through the UCS platform. This task covers registering and deregistering clusters.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                    |
| ------------------ | ------ | ------------------------ | --------------------------------- |
| `RegisterCluster`  | POST   | Register cluster to UCS   | `--apiVersion`, `--kind`, `--metadata.name`, `--spec.category`, `--spec.provider`, `--spec.type`, `--spec.manageType`, `--spec.country`, `--spec.city` |
| `DeleteCluster`    | DELETE | Remove cluster from UCS   | `--clusterid`                     |
| `ShowCluster`      | GET    | Get cluster details       | `--clusterid`                     |
| `ShowClusterList`  | GET    | List registered clusters  | `--limit`, `--offset`, `--category`, `--managetype`, `--clustergroupid`, `--clusterids` |
| `ListManagedClusters` | GET | List CCE clusters for current tenant (not UCS-registered) | `--unimported` (optional, filter clusters not imported to UCS) |
| `RetryClusterActivation` | POST | Retry cluster activation  | `--clusterid`                     |
| `UpdateCluster`    | PUT    | Update cluster properties  | `--clusterid`, `--apiVersion`, `--kind`, `--metadata.annotations`, `--spec.city`, `--spec.country` |

## Workflows

### W1: Register a CCE Cluster to UCS

**Pre-registration Checklist**:
1. Verify CCE cluster exists and is in `Available` status in the same region
2. ⚠️ **Verify K8s version compatibility**: Query UCS supported versions and check cluster version is in the list. CCE default version may exceed UCS support range.
   ```bash
   # Step 1: Get UCS supported versions
   hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
   # Step 2: Get cluster version (unimported CCE clusters)
   hcloud UCS ListManagedClusters --unimported=true --cli-region=cn-north-4
   ```
   If the cluster version is not in the `ListRegisteredClusterVersions` response, downgrade the cluster before proceeding.
3. Check UCS quota availability: `hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4`
4. Verify the cluster is not already registered: `hcloud UCS ShowClusterList --category=self --managetype=grouped --cli-region=cn-north-4`
5. **Obtain the correct project ID**: The `--spec.projectID` value must match the CCE cluster's project. Retrieve it from `ListManagedClusters` response (this API returns CCE clusters, not UCS-registered clusters, so it can be called before registration):
   ```bash
   hcloud UCS ListManagedClusters --unimported=true --cli-region=cn-north-4
   ```
   The response includes `spec.projectID` for each unimported CCE cluster — use this exact value in `RegisterCluster`.

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-backend-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

**Post-registration Verification**:

```bash
hcloud UCS ShowClusterList --category=self --managetype=grouped --cli-region=cn-north-4

hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Cluster status transitions from `Registering` to `Available`.

### W2: Register a Self-Managed Kubernetes Cluster

**Pre-registration Checklist**:
1. Verify kubeconfig is valid: `kubectl --kubeconfig=<path> cluster-info`
2. Ensure API server is reachable from UCS management plane
3. Check UCS quota availability
4. Verify kubeconfig user has sufficient RBAC permissions

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-content> --cli-region=cn-north-4
```

**Self-Managed Cluster Requirements**:
- Kubeconfig must contain valid API server URL (HTTPS, publicly reachable)
- Certificate-authority-data must be base64-encoded
- User credentials (token or client certificates) must be valid and not expired
- The cluster must be running Kubernetes version 1.19 or later

**Post-registration Verification**:

```bash
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Cluster status transitions to `Available` after UCS validates connectivity.

### W3: Verify Cluster Registration Status

```bash
hcloud UCS ShowClusterList --cli-region=cn-north-4

hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Cluster Status Values**:
- `Registering`: Cluster is being registered (initial state)
- `Available`: Cluster is registered and operational
- `Unavailable`: Cluster API server is unreachable
- `Deleting`: Cluster is being deregistered

### W4: Retry Cluster Activation

If a cluster remains in `Registering` or `Unavailable` status after registration, retry activation:

```bash
hcloud UCS RetryClusterActivation --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Cluster status transitions from stalled state toward `Available`.

**Category Limitation** (verified): `RetryClusterActivation` only works for `category=onpremise` clusters. For `category=self` (CCE) clusters, it returns `UCS.01000011: Cluster category not supported`. Do not use this API for CCE clusters.

### W5: Deregister (Remove) a Cluster from UCS

⚠️ **CAUTION**: Deregistration is irreversible. The cluster will lose all UCS management capabilities, including policy governance, fleet grouping, and federation access. You must re-register to restore management.

**Pre-deregistration Checklist**:
1. Verify no active policy instances depend on this cluster (use `huawei-cloud-ucs-policy-governor` skill)
2. Remove the cluster from any fleet groups
3. Confirm with the user that deregistration is intended

```bash
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Post-deregistration Verification**:

```bash
hcloud UCS ShowClusterList --cli-region=cn-north-4
```

Expected: Cluster no longer appears in the list.

### W6: Bulk Registration of Multiple CCE Clusters

Register multiple CCE clusters in sequence:

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-cluster-1 --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id-1> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-cluster-2 --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id-2> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=staging-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id-3> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

hcloud UCS ShowClusterList --cli-region=cn-north-4
```

**Note**: For bulk operations, check quota before starting to ensure sufficient capacity.

## Common Scenarios

### S1: Migrate Cluster from One UCS Instance to Another

When reorganizing UCS management, deregister from one instance and register to another:

```bash
hcloud UCS DeleteCluster --clusterid=<current-ucs-id> --cli-region=cn-north-4

hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

hcloud UCS ShowCluster --clusterid=<new-ucs-id> --cli-region=cn-north-4
```

### S2: Re-register a Previously Deregistered Cluster

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=re-registered-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

**Note**: The UCS cluster ID will be different from the previous registration. Previous policy configurations will need to be re-applied.

### S3: Troubleshoot Unavailable Self-Managed Cluster

```bash
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
# Note: Only for category=onpremise clusters. Returns UCS.01030011 for CCE clusters.

hcloud UCS RetryClusterActivation --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cluster --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<updated-kubeconfig> --cli-region=cn-north-4
```