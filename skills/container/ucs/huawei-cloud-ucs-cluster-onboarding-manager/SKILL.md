---
id: huawei-cloud-ucs-cluster-onboarding-manager
name: huawei-cloud-ucs-cluster-onboarding-manager
description: |
  Huawei Cloud UCS (Universal Cloud Service) cluster onboarding, lifecycle, and fleet grouping management skill using hcloud CLI.
  Use this skill when the user wants to: (1) register self-managed or CCE clusters to UCS - register/query/remove, (2) manage cluster lifecycle - update/query/list clusters, (3) manage fleet groups - create/delete/query cluster groups, (4) obtain cluster access information and kubeconfig, (5) download federation kubeconfig for multi-cluster access, (6) check UCS resource quotas.
  Trigger: user mentions "UCS cluster onboarding", "UCS 集群纳管", "UCS cluster registration", "UCS 注册集群", "UCS fleet", "UCS 舰队", "UCS 集群组", "cluster group", "fleet grouping", "UCS kubeconfig", "UCS 集群接入", "UCS federation", "UCS 联邦", "UCS 配额", "cluster lifecycle", "集群生命周期", "managed clusters", "纳管集群", "集群管理"
tags: [ucs, cluster-onboarding, fleet, kubeconfig, cluster-lifecycle]
---

# Huawei Cloud UCS Cluster Onboarding Manager

## Overview

This skill provides cluster onboarding, lifecycle, and fleet grouping management capabilities for Huawei Cloud UCS (Universal Cloud Service) using the `hcloud` CLI.

**Architecture**: hcloud CLI → UCS Service API → Cluster/ClusterGroup/AccessConfig/KubeConfig resources

**Related Skills**:
- `huawei-cloud-ucs-policy-governor` - UCS policy governance, compliance, and audit management

**Capabilities**:
- Register self-managed or CCE clusters to UCS for unified management
- Remove clusters from UCS management (deregistration)
- Query cluster details, list managed clusters
- Update cluster properties and metadata
- Create, delete, update, and query fleet groups for cluster organization
- Add/remove clusters from fleet groups (join/leave)
- Retry cluster activation
- Obtain cluster access information and kubeconfig credentials
- Download federation kubeconfig for multi-cluster access
- Check UCS resource quotas

**Typical Use Cases**:

- "Register my CCE cluster to UCS"
- "List all clusters managed by UCS"
- "Remove a cluster from UCS management"
- "Create a fleet group for production clusters"
- "Get kubeconfig for my UCS-managed cluster"
- "Download federation kubeconfig for multi-cluster access"
- "Check my UCS quota usage"
- "Update cluster metadata"
- "Query cluster access information"
- "Add a cluster to a fleet group"
- "Remove a cluster from a fleet group"
- "Retry cluster activation"

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

- Valid Huawei Cloud credentials (AK/SK mode)
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**Configuration Method** (Environment Variables Only):

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| API Action                       | Permission        | Purpose                                |
| -------------------------------- | ----------------- | -------------------------------------- |
| `ucs:cluster:create`             | Register cluster  | Register cluster to UCS                |
| `ucs:cluster:delete`             | Delete cluster    | Remove cluster from UCS                |
| `ucs:cluster:get`                | Get cluster       | View cluster details                   |
| `ucs:cluster:list`               | List clusters     | List all managed clusters              |
| `ucs:cluster:update`             | Update cluster    | Modify cluster properties              |
| `ucs:clusterGroup:create`        | Create group      | Create fleet group                     |
| `ucs:clusterGroup:delete`        | Delete group      | Remove fleet group                     |
| `ucs:clusterGroup:get`           | Get group         | View fleet group details               |
| `ucs:clusterGroup:update`        | Update group      | Update fleet group description         |
| `ucs:clusterAccess:get`          | Get access info   | Obtain cluster access information      |
| `ucs:quota:get`                  | Get quota         | Check UCS resource quotas              |
| `ucs:kubeconfig:create`          | Create kubeconfig | Obtain cluster kubeconfig              |
| `ucs:federationKubeconfig:get`   | Get federation    | Download federation kubeconfig         |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Cluster Registration & Deregistration

See [Task: Cluster Registration](references/task-cluster-registration.md) for detailed workflows.

RegisterCluster uses Kubernetes API-style parameters (apiVersion, kind, metadata.*, spec.*).

```bash
# Register a CCE cluster to UCS
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-backend-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

# Register a CCE cluster and assign to fleet group at registration
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-backend-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --spec.clusterGroupID=<group-id> --cli-region=cn-north-4

# Register a self-managed/attached cluster
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-yaml-content> --cli-region=cn-north-4

# Retry cluster activation (if registration stuck)
hcloud UCS RetryClusterActivation --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Remove a cluster from UCS
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Cluster Categories (spec.category)**:
- `self`: Huawei Cloud CCE (Cloud Container Engine) managed cluster
- `onpremise`: Self-managed or third-party Kubernetes cluster

**Cluster Providers (spec.provider)**:
- `huaweicloud`: Huawei Cloud managed CCE cluster
- `self_managed`: Self-managed Kubernetes cluster

**Manage Types (spec.manageType)**:
- `grouped`: Cluster managed within a fleet group
- `discrete`: Cluster managed independently

### 2. Cluster Query & Lifecycle

```bash
# Show cluster details
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# List managed clusters (with pagination)
hcloud UCS ShowClusterList --limit=20 --offset=0 --cli-region=cn-north-4

# List managed clusters with filters
hcloud UCS ShowClusterList --category=CCE --enablestatus=Available --clustergroupid=<group-id> --cli-region=cn-north-4

# List all managed clusters (with optional unimported flag)
hcloud UCS ListManagedClusters --cli-region=cn-north-4
hcloud UCS ListManagedClusters --unimported --cli-region=cn-north-4

# Update cluster properties (K8s API-style params)
hcloud UCS UpdateCluster --clusterid=<ucs-cluster-id> --apiVersion=v1 --kind=Cluster --spec.city=Shanghai --spec.country=CN --cli-region=cn-north-4

# Show cluster access information
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Show cluster access information with optional filters
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --region=cn-north-4 --vpcendpoint=<vpc-id> --cli-region=cn-north-4
```

**ShowClusterList Valid Filter Parameters**:
- `--category`: Filter by cluster category (self, onpremise)
- `--clustergroupid`: Filter by fleet group ID
- `--clusterids`: Filter by specific cluster IDs
- `--enablestatus`: Filter by cluster status (Available, Unavailable)
- `--managetype`: Filter by manage type (grouped, discrete)
- `--limit`: Pagination limit
- `--offset`: Pagination offset
- `--order`: Sort order (asc, desc)
- `--order_by`: Sort field

### 3. Fleet Group Management

See [Task: Fleet Management](references/task-fleet-management.md) for detailed workflows.

```bash
# Create a fleet group
hcloud UCS RegisterClusterGroup --metadata.name=production-fleet --spec.description="All production clusters" --spec.clusterIds.1=<cluster-id-1> --cli-region=cn-north-4

# List all fleet groups
hcloud UCS ListClusterGroup --limit=20 --offset=0 --cli-region=cn-north-4

# Show fleet group details
hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4

# Update fleet group description
hcloud UCS UpdateClusterGroup --clustergroupid=<group-id> --description="Updated fleet description" --cli-region=cn-north-4

# Add clusters to fleet group
hcloud UCS UpdateClusterGroupAssociatedClusters --clustergroupid=<group-id> --clusterIds.1=<cluster-id-1> --clusterIds.2=<cluster-id-2> --cli-region=cn-north-4

# Add a single cluster to fleet group (join)
hcloud UCS JoinGroup --clusterid=<ucs-cluster-id> --clusterGroupID=<group-id> --cli-region=cn-north-4

# Remove a cluster from fleet group (leave)
hcloud UCS LeaveGroup --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Delete a fleet group
hcloud UCS DeleteClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

### 4. Kubeconfig & Access Management

See [Task: Access Management](references/task-access-management.md) for detailed workflows.

```bash
# Get kubeconfig for a specific cluster
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Create cluster configuration
hcloud UCS CreateClusterConf --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Download federation kubeconfig (for multi-cluster access)
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=3600 --cli-region=cn-north-4
```

**DownloadFederationKubeconfig Required Parameters**:
- `--clustergroupid`: Fleet group ID (required path parameter)
- `--duration`: Token validity duration in seconds (required integer body parameter)

### 5. Quota Management

```bash
# Show UCS resource quotas (domainid is required - account ID)
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

## Parameter Reference

### Common Parameters

| Parameter        | Required/Optional | Description                   | Default                              |
| ---------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`   | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--clusterid`    | Context-dependent | UCS cluster ID                | N/A                                  |
| `--clustergroupid` | Context-dependent | Fleet group ID              | N/A                                  |

### Cluster Registration Parameters (K8s API Style)

| Parameter                        | Required | Description                        | Constraints                                  |
| -------------------------------- | -------- | ---------------------------------- | -------------------------------------------- |
| `--apiVersion`                   | Yes      | API version (always `v1`)          | Must be `v1`                                 |
| `--kind`                         | Yes      | Resource kind (always `Cluster`)   | Must be `Cluster`                            |
| `--metadata.name`                | Yes      | Cluster display name               | 1-128 chars                                  |
| `--spec.category`                | Yes      | Cluster category                   | `self` or `onpremise`                        |
| `--spec.provider`                | Yes      | Cluster provider                   | `huaweicloud` or `self_managed`              |
| `--spec.type`                    | Yes      | Cluster type                       | `cce`, `baremetal`, `Kubernetes`, etc.       |
| `--spec.manageType`              | Yes      | Management type                    | `grouped` or `discrete`                      |
| `--spec.country`                 | Yes      | Country code                       | Country code (e.g., `CN`)                    |
| `--spec.city`                    | Yes      | City code                          | City code (e.g., `110000` for Beijing)       |
| `--metadata.uid`                 | CCE only | CCE cluster ID                     | Must reference existing CCE cluster          |
| `--spec.projectID`               | CCE only | Project ID                         | Valid Huawei Cloud project ID                |
| `--spec.region`                  | CCE only | CCE cluster region                 | Must match CCE cluster region                |
| `--metadata.annotations.kubeconfig` | Self-managed only | Kubeconfig content | Valid Kubernetes kubeconfig YAML           |
| `--spec.clusterGroupID`          | No       | Assign to fleet at registration    | Valid fleet group ID                         |
| `--metadata.labels.*`            | No       | Custom labels                      | Key-value pairs                              |

### UpdateCluster Parameters (K8s API Style)

| Parameter                        | Required | Description                        | Constraints                                  |
| -------------------------------- | -------- | ---------------------------------- | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID (path param)        | Must be registered cluster                   |
| `--apiVersion`                   | Yes      | API version (always `v1`)          | Must be `v1`                                 |
| `--kind`                         | Yes      | Resource kind (always `Cluster`)   | Must be `Cluster`                            |
| `--spec.city`                    | No       | Update city                        | City name                                    |
| `--spec.country`                 | No       | Update country                     | Country code                                 |
| `--metadata.annotations`         | No       | Update annotations                 | Key-value pairs                              |
| `--spec.workerConfig.replicas`   | No       | Update worker replicas             | Integer                                      |
| `--spec.workerConfig.strategy.*` | No       | Update worker strategy             | K8s deployment strategy fields               |

### Fleet Group Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--metadata.name`                | Yes (create) | Group display name   | 1-128 chars                                  |
| `--spec.description`             | No (create)  | Group description    | Free text                                    |
| `--spec.clusterIds.N`            | No (create)  | Initial cluster IDs  | Indexed (1, 2, 3...)                         |
| `--clustergroupid`               | Yes (get/delete/update) | Group ID    | UUID format                                   |
| `--description`                  | Yes (UpdateClusterGroup) | New description | Free text                  |
| `--clusterIds.N`                 | Yes (UpdateClusterGroupAssociatedClusters) | Cluster IDs to add | Indexed |

### Join/Leave Group Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID (path)    | Must be registered cluster                   |
| `--clusterGroupID`               | Yes (JoinGroup) | Fleet group ID (body) | Valid fleet group ID                       |

### Kubeconfig Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID           | Must be registered cluster                   |
| `--clustergroupid`               | Yes (DownloadFederationKubeconfig) | Fleet group ID | Valid fleet group ID            |
| `--duration`                     | Yes (DownloadFederationKubeconfig) | Token duration in seconds | Integer                   |

### Quota Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--domainid`                     | Yes      | Account ID               | Huawei Cloud account/domain ID               |

### ShowClusterList Filter Parameters

| Parameter        | Required/Optional | Description                   |
| ---------------- | ----------------- | ----------------------------- |
| `--category`     | Optional          | Filter by cluster category    |
| `--clustergroupid` | Optional        | Filter by fleet group ID      |
| `--clusterids`   | Optional          | Filter by specific cluster IDs |
| `--enablestatus` | Optional          | Filter by cluster status      |
| `--managetype`   | Optional          | Filter by manage type         |
| `--limit`        | Optional          | Pagination limit              |
| `--offset`       | Optional          | Pagination offset             |
| `--order`        | Optional          | Sort order (asc/desc)         |
| `--order_by`     | Optional          | Sort field                    |

## Output Format

See [Output Format](references/output-format.md) for detailed response format examples (ShowCluster, ShowClusterList, ShowQuota).

**Key Fields Summary**:
- ShowCluster: `metadata.uid` (UUID), `spec.category` (onpremise/self), `status.phase` (Failed/Available)
- ShowClusterList: `items[]` (k8s-style array), `total` (count)
- ShowQuota: `quotas.resources[]` with `type`/`quota`/`used`/`min`/`max`

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. **Cluster Naming**: Use descriptive names that reflect cluster purpose and environment (e.g., `prod-app-backend`, `staging-data-pipeline`) via `--metadata.name`
2. **Fleet Grouping**: Organize clusters by environment (production/staging/development) or business domain for unified governance
3. **Kubeconfig Security**: Store kubeconfig files securely; never expose them in public repositories or CI logs
4. **Deregistration Caution**: Removing a cluster from UCS disables all policy governance and federation access for that cluster
5. **Self-Managed Registration**: Ensure the self-managed cluster kubeconfig is valid and the cluster API server is reachable; pass it via `--metadata.annotations.kubeconfig`
6. **Quota Monitoring**: Check quotas before registering new clusters to avoid hitting limits
7. **Federation Kubeconfig Duration**: Choose appropriate `--duration` for federation kubeconfig tokens based on usage patterns

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [UCS Cluster Onboarding API Guide](references/ucs-cluster-onboarding-api-guide.md) | hcloud UCS API reference |
| [Output Format](references/output-format.md) | Response format examples (verified) |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Cluster Registration](references/task-cluster-registration.md) | Registration and deregistration workflows |
| [Task: Fleet Management](references/task-fleet-management.md) | Fleet group workflows |
| [Task: Access Management](references/task-access-management.md) | Kubeconfig and access control workflows |

## Notes

- **Cluster deregistration is irreversible** — the cluster loses all UCS management capabilities
- **Self-managed cluster kubeconfig must be valid** — invalid kubeconfig will cause registration failure; pass via `--metadata.annotations.kubeconfig`
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud UCS <Operation>` format
- **Federation kubeconfig requires fleet group ID and duration** — both `--clustergroupid` and `--duration` are required
- **RegisterCluster uses K8s API-style parameters** — not flat params like --name/--cluster_type; note: `spec.category` uses `self`/`onpremise` (not `CCE`/`AttachedCluster`), `spec.provider` uses `huaweicloud` (not `huawei_cloud`), `spec.type` uses lowercase `cce` (not `CCE`), `spec.city` uses city codes like `110000` (not city names like `Beijing`)
- **ShowQuota requires domainid** — the account/domain ID is a required path parameter

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                     | Symptom                         | Quick Fix                                    |
| --------------------------- | ------------------------------- | -------------------------------------------- |
| Invalid kubeconfig          | Registration fails              | Verify kubeconfig validity and API server reachability |
| Cluster already registered  | 409 Conflict                    | Use `ShowCluster` to check existing registration |
| CCE cluster not found       | 404 Not Found                   | Verify CCE cluster ID via `--metadata.uid` in same region |
| Quota exceeded              | 403 Quota limit                 | Check quotas with `ShowQuota --domainid=<account-id>` |
| Fleet group already exists  | 409 Conflict                    | Use `ShowClusterGroup` to check first        |
| Deregistration impact       | Policies stop working           | Consider disabling policies before deregistration |
| Federation kubeconfig expired | Multi-cluster access fails    | Re-download with `DownloadFederationKubeconfig --clustergroupid=<id> --duration=N` |
| Wrong parameter names       | Command fails or unrecognized   | Use `--clusterid` (not --cluster_id), `--clustergroupid` (not --group_id) |
| Using --name on ShowClusterList | Parameter not recognized    | Use `--category`, `--clustergroupid`, `--enablestatus` filters instead |
| Missing domainid on ShowQuota | Missing required parameter    | Provide `--domainid=<account-id>` |
| Missing duration on DownloadFederationKubeconfig | Missing required parameter | Provide `--duration=<seconds>` |