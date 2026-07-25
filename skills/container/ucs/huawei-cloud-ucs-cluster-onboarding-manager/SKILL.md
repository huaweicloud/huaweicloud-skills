---
name: huawei-cloud-ucs-cluster-onboarding-manager
description: |
  Huawei Cloud UCS cluster onboarding, lifecycle, and fleet management via hcloud CLI. Register/query/remove clusters, manage fleet groups, obtain kubeconfig, check quotas.
  Trigger: "UCS cluster onboarding", "UCS 集群纳管", "UCS fleet", "UCS 舰队", "UCS kubeconfig", "UCS federation", "UCS 联邦", "UCS 配额", "cluster lifecycle", "纳管集群", "集群管理"
tags: [ucs, cluster-onboarding, fleet, kubeconfig, cluster-lifecycle]
---

# Huawei Cloud UCS Cluster Onboarding Manager

## Overview

This skill provides cluster onboarding, lifecycle, and fleet grouping management capabilities for Huawei Cloud UCS (Ubiquitous Cloud Native Service) using the `hcloud` CLI.

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

hcloud CLI supports two credential modes via environment variables, automatically detected at runtime:

**Mode A — Long-term AK/SK** (permanent access):
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Mode B — Temporary AK/SK + SecurityToken** (recommended for temporary or delegated access):
```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

> When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication. When only AK/SK are set, it uses long-term credential authentication.

- **Security Rules**:
  - 🚫 Never expose AK/SK/SecurityToken values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, `HUAWEI_CLOUD_SECURITY_TOKEN`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. K8s Version Compatibility (CRITICAL)

⚠️ **UCS has a maximum supported Kubernetes version limit.** CCE clusters created with default settings may use a version that exceeds UCS support range. Registering an unsupported version will fail with error `UCS.01030012: Register cce cluster error - cce cluster version not support in UCS service` (verified: CCE default creates v1.35, UCS supports up to v1.34 as of 2025-07). **Always query the supported versions dynamically** — do not hardcode version numbers, as UCS updates its support range over time:
   ```bash
   hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
   ```

**Pre-registration Version Check**:

```bash
# List unimported CCE clusters to check their versions
hcloud UCS ListManagedClusters --unimported=true --cli-region=cn-north-4

# Or check specific CCE cluster version via CCE API
hcloud CCE ShowCluster --clusterid=<cce-cluster-id> --cli-region=cn-north-4
```

If the cluster K8s version exceeds UCS support range, either:
- Downgrade the CCE cluster K8s version to within UCS support range, OR
- Wait for UCS to support the newer version

### 4. IAM Permission Requirements

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
# Register a CCE cluster to UCS (⚠️ 接入收费: requires user confirmation)
# **Confirm with user before executing** — UCS cluster onboarding is a paid service, costs will be incurred
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-backend-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

# Register a CCE cluster and assign to fleet group at registration
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-backend-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --spec.clusterGroupID=<group-id> --cli-region=cn-north-4

# Register a self-managed/attached cluster
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-yaml-content> --cli-region=cn-north-4

# Retry cluster activation (if registration stuck)
hcloud UCS RetryClusterActivation --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Remove a cluster from UCS (⚠️ destructive: requires user confirmation)
# **Confirm with user before executing** — deregistration is irreversible
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Cluster Categories (spec.category)**:
- `self`: Huawei Cloud CCE (Cloud Container Engine) managed cluster
  - UCS directly accesses CCE API via internal network — **no proxy-agent needed**
  - Use CCE API `CreateKubernetesClusterCert` to obtain kubeconfig (NOT UCS `CreateClusterKubeconfig`)
  - `ShowClusterAccessInfo` returns `UCS.01030011` — **NOT supported** for this category
  - `RetryClusterActivation` returns `UCS.01000011` — **NOT supported** for this category
  - Note: CCE cluster `spec.category` is `Turbo`, but UCS `ListManagedClusters` returns `category=self`, `type=turbo`
- `onpremise`: Self-managed or third-party Kubernetes cluster
  - Requires deploying proxy-agent to establish tunnel between cluster and UCS
  - Use `ShowClusterAccessInfo` to obtain proxy-agent configuration, then deploy proxy-agent
  - Use `CreateClusterKubeconfig` to obtain kubeconfig after proxy-agent is running

**Kubeconfig Retrieval Decision Tree** (verified via API testing):
```
Need cluster kubeconfig?
├── category=self (CCE cluster)
│   └── CCE CreateKubernetesClusterCert --cluster_id=<cce-cluster-id> --duration=30
│       (CCE API, NOT UCS CreateClusterKubeconfig which returns internal error)
└── category=onpremise (self-managed cluster)
    ├── Step 1: ShowClusterAccessInfo --clusterid=<ucs-cluster-id>
    │   (obtain proxy-agent configuration — only for onpremise, returns UCS.01030011 for CCE)
    ├── Step 2: Deploy proxy-agent in the cluster
    └── Step 3: CreateClusterKubeconfig --clusterid=<ucs-cluster-id>
        (obtain kubeconfig after tunnel established)
```

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

# Update cluster properties (K8s API-style params) (⚠️ modification: requires user confirmation)
# **Confirm with user before executing**
hcloud UCS UpdateCluster --clusterid=<ucs-cluster-id> --apiVersion=v1 --kind=Cluster --spec.city=Shanghai --spec.country=CN --cli-region=cn-north-4

# Show cluster access information (only for category=onpremise clusters)
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Show cluster access information with optional filters (only for category=onpremise clusters)
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --region=cn-north-4 --vpcendpoint=<vpc-id> --cli-region=cn-north-4
```

> ⚠️ **ShowClusterAccessInfo only applies to `category=onpremise` clusters.** For `category=self` (CCE) clusters, it returns `UCS.01030011: Cluster category not supported` (verified). For CCE cluster kubeconfig, use CCE API `CreateKubernetesClusterCert` instead of UCS `CreateClusterKubeconfig`.

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

# Update fleet group description (⚠️ modification: requires user confirmation)
# **Confirm with user before executing**
hcloud UCS UpdateClusterGroup --clustergroupid=<group-id> --description="Updated fleet description" --cli-region=cn-north-4

# Add clusters to fleet group (⚠️ modification: requires user confirmation)
# **Confirm with user before executing**
hcloud UCS UpdateClusterGroupAssociatedClusters --clustergroupid=<group-id> --clusterIds.1=<cluster-id-1> --clusterIds.2=<cluster-id-2> --cli-region=cn-north-4

# Add a single cluster to fleet group (join)
hcloud UCS JoinGroup --clusterid=<ucs-cluster-id> --clusterGroupID=<group-id> --cli-region=cn-north-4

# Remove a cluster from fleet group (leave)
hcloud UCS LeaveGroup --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Delete a fleet group (⚠️ destructive: requires user confirmation)
# **Confirm with user before executing** — deletion removes the group but clusters remain registered
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

## 参数确认

> ⚠️ **费用提醒**: UCS 集群接入为**收费服务**，注册集群到 UCS 会产生费用。在执行 `RegisterCluster` 等接入操作前，**必须向用户确认是否同意产生费用**，获得明确同意后方可执行。

### 通用参数

| Parameter        | Required/Optional | Description                   | Default                              |
| ---------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`   | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--clusterid`    | Context-dependent | UCS cluster ID                | N/A                                  |
| `--clustergroupid` | Context-dependent | Fleet group ID              | N/A                                  |

### 集群注册参数 (K8s API Style)

| Parameter                        | Required | Description                        | Constraints                                  |
| -------------------------------- | -------- | ---------------------------------- | -------------------------------------------- |
| `--spec.category`                | Yes      | Cluster category                   | `self` (CCE) or `onpremise` (self-managed)   |
| `--spec.provider`                | Yes      | Cluster provider                   | `huaweicloud` or `self_managed`              |
| `--spec.type`                    | Yes      | Cluster type                       | `cce`, `baremetal`, `Kubernetes`, etc.       |
| `--spec.manageType`              | Yes      | Management type                    | `grouped` or `discrete`                      |
| `--metadata.uid`                 | CCE only | CCE cluster ID                     | Must reference existing CCE cluster          |
| `--spec.projectID`               | CCE only | Project ID                         | Obtain via `ListManagedClusters` response    |
| `--spec.clusterGroupID`          | No       | Assign to fleet at registration    | Valid fleet group ID                         |

### 写操作参数（需用户确认）

| Command          | Parameters | Confirmation Required | Reason |
| ---------------- | ---------- | --------------------- | ------ |
| `RegisterCluster` | See above | ✅ Yes | **接入收费**，产生费用 |
| `DeleteCluster`   | `--clusterid` | ✅ Yes | 退出纳管，不可逆 |
| `UpdateCluster`   | `--clusterid` + K8s params | ✅ Yes | 修改集群属性 |
| `RegisterClusterGroup` | Group name + description | ✅ Yes | 创建舰队组 |
| `DeleteClusterGroup` | `--clustergroupid` | ✅ Yes | 删除舰队组 |
| `UpdateClusterGroup` | `--clustergroupid` + params | ✅ Yes | 修改舰队组属性 |
| `JoinGroup`      | `--clusterid` + `--clustergroupid` | ✅ Yes | 修改集群归属 |
| `LeaveGroup`     | `--clusterid` + `--clustergroupid` | ✅ Yes | 修改集群归属 |

> 完整参数表见 [Parameter Reference](references/parameter-reference.md)

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

## Workflow

The skill workflow is as follows:

1. **Environment Check** — Verify hcloud CLI is installed and AK/SK credentials are configured (see [CLI Installation Guide](references/cli-installation-guide.md))
2. **Version Compatibility Check** — Call `ListRegisteredClusterVersions` to get the list of K8s versions supported by UCS, and confirm the target cluster version is in the list
3. **Cluster Registration** — Choose registration method based on cluster type:
   - CCE cluster: `--spec.category=self --spec.provider=huaweicloud --spec.type=turbo`
   - Self-managed cluster: `--spec.category=onpremise --spec.provider=self_managed` (requires kubeconfig)
4. **Registration Verification** — Call `ShowCluster` or `ShowClusterList` to confirm cluster status is `Available`
5. **Cluster Management** (optional):
   - Fleet grouping: `RegisterClusterGroup` / `JoinGroup` / `LeaveGroup`
   - Access management: CCE clusters use `CreateKubernetesClusterCert`, third-party clusters use `ShowClusterAccessInfo` + proxy-agent
   - Property update: `UpdateCluster` (requires user confirmation)
6. **Deregister Cluster** (optional) — `DeleteCluster` (⚠️ irreversible operation, requires user confirmation)

## KooCLI Command Format Standard

All operations use `hcloud UCS <Operation> --<param>=<value> --cli-region=<region>` format. See [KooCLI Command Format](references/kocli-command-format.md) for detailed examples and parameter naming rules.

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
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud CLI installation and configuration |
| [Parameter Reference](references/parameter-reference.md) | Complete parameter tables for all operations |
| [KooCLI Command Format](references/kocli-command-format.md) | Command format standard and examples |
| [Acceptance Criteria](references/acceptance-criteria.md) | Skill acceptance criteria and test checklist |

## Notes

- **K8s version compatibility** — UCS has a maximum supported K8s version that updates over time. CCE default cluster version may exceed this limit. Query supported versions with `hcloud UCS ListRegisteredClusterVersions` and verify cluster version is in the list before registration.
- **Cluster deregistration is irreversible** — the cluster loses all UCS management capabilities
- **Self-managed cluster kubeconfig must be valid** — invalid kubeconfig will cause registration failure; pass via `--metadata.annotations.kubeconfig`
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud UCS <Operation>` format
- **Federation kubeconfig requires fleet group ID and duration** — both `--clustergroupid` and `--duration` are required
- **RegisterCluster uses K8s API-style parameters** — not flat params like --name/--cluster_type; note: `spec.category` uses `self`/`onpremise` (not `CCE`/`AttachedCluster`), `spec.provider` uses `huaweicloud` (not `huawei_cloud`), `spec.type` uses lowercase `cce` (not `CCE`), `spec.city` uses city codes like `110000` (not city names like `Beijing`)
- **ShowQuota requires domainid** — the account/domain ID is a required path parameter

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.
