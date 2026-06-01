# Task: Fleet Management

## Overview

UCS fleet groups (集群组/舰队) provide organizational grouping for managed clusters, enabling unified policy governance and management across multiple clusters. This task covers creating, querying, and managing fleet groups.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                    |
| ------------------ | ------ | ------------------------ | --------------------------------- |
| `RegisterClusterGroup` | POST  | 创建集群组             | `--metadata.name`, `--spec.description`, `--spec.clusterIds.1` |
| `ListClusterGroup` | GET    | 列出集群组列表           | `--limit`, `--offset`, `--order`, `--order_by` |
| `ShowClusterGroup` | GET    | 获取集群组详情           | `--clustergroupid`                |
| `UpdateClusterGroup` | PUT  | 更新集群组描述           | `--clustergroupid`, `--description` |
| `UpdateClusterGroupAssociatedClusters` | PUT | 添加集群到舰队 | `--clustergroupid`, `--clusterIds.[N]` |
| `DeleteClusterGroup` | DELETE | 删除集群组             | `--clustergroupid`                |
| `JoinGroup`        | POST   | 添加集群到舰队           | `--clusterid` (path), `--clusterGroupID` (body) |
| `LeaveGroup`       | POST   | 从舰队移除集群           | `--clusterid`                     |

## Workflows

### W1: Create a Fleet Group

**Pre-creation Checklist**:
1. Check UCS quota for fleet groups: `hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4`
2. Plan group naming and description

```bash
hcloud UCS RegisterClusterGroup --metadata.name=production-fleet --spec.description="All production clusters for unified governance" --cli-region=cn-north-4

hcloud UCS RegisterClusterGroup --metadata.name=staging-env --spec.description="Staging environment clusters" --cli-region=cn-north-4

hcloud UCS RegisterClusterGroup --metadata.name=payment-services --spec.description="Payment processing service clusters" --cli-region=cn-north-4
```

**Post-creation Verification**:

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id-from-response> --cli-region=cn-north-4
```

Expected: Returns group details with `cluster_count: 0` (no clusters assigned yet).

### W2: View Fleet Group Details

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

**Response Fields**:
- `id`: Fleet group UUID
- `name`: Group display name
- `description`: Group description
- `cluster_count`: Number of clusters in this group
- `created_at`/`updated_at`: Timestamps

### W3: List Fleet Groups

```bash
hcloud UCS ListClusterGroup --limit=20 --offset=0 --cli-region=cn-north-4
```

**Parameters**:
- `--limit` (optional): Page size, default 20, max 100
- `--offset` (optional): Page offset
- `--order` (optional): Sort order (`asc`, `desc`)
- `--order_by` (optional): Sort field

### W4: Add Clusters to Fleet Group

```bash
hcloud UCS JoinGroup --clusterid=<ucs-cluster-id> --clusterGroupID=<group-id> --cli-region=cn-north-4
```

Or add multiple clusters at once:

```bash
hcloud UCS UpdateClusterGroupAssociatedClusters --clustergroupid=<group-id> --clusterIds.1=<cluster-id-1> --clusterIds.2=<cluster-id-2> --cli-region=cn-north-4
```

**Note**: Clusters must be registered and in `Available` status before joining a fleet group. For grouped management, clusters should be registered with `--spec.manageType=grouped`.

### W5: Remove a Cluster from Fleet Group

```bash
hcloud UCS LeaveGroup --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Post-removal Verification**:

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

Expected: `cluster_count` decreases by 1.

### W6: Update Fleet Group Description

```bash
hcloud UCS UpdateClusterGroup --clustergroupid=<group-id> --description="Updated description for the fleet group" --cli-region=cn-north-4
```

### W7: Delete a Fleet Group

⚠️ **CAUTION**: Deleting a fleet group removes the organizational grouping. Clusters that were part of the group remain individually managed by UCS but lose the group-level policy governance association.

**Pre-deletion Checklist**:
1. Verify no policy instances are bound to this group (use `ucs-policy-governor` skill)
2. Confirm with the user that deletion is intended

```bash
hcloud UCS DeleteClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

Expected: Group not found error (404).

### W8: Organize Clusters into Fleet Groups

Fleet groups are used for organizational grouping. Policy instances in the `ucs-policy-governor` skill can be bound to fleet groups for unified governance across all member clusters.

**Best Practices for Fleet Group Design**:

| Grouping Strategy | Example Name        | Use Case                                  |
| ----------------- | ------------------- | ----------------------------------------- |
| By environment    | `production-fleet`  | Apply stricter security policies to production |
| By environment    | `staging-env`       | Relaxed policies for testing environments |
| By business domain| `payment-services`  | Domain-specific compliance requirements   |
| By region         | `cn-north-4-fleet`  | Region-specific regulatory compliance     |
| By platform type  | `cce-clusters`      | Platform-specific configurations          |
| By platform type  | `self-managed-fleet`| Consistent governance for self-managed    |

## Common Scenarios

### S1: Create Environment-Based Fleet Groups

```bash
hcloud UCS RegisterClusterGroup --metadata.name=production-fleet --spec.description="Production environment - strict compliance" --cli-region=cn-north-4
hcloud UCS RegisterClusterGroup --metadata.name=staging-fleet --spec.description="Staging environment - moderate compliance" --cli-region=cn-north-4
hcloud UCS RegisterClusterGroup --metadata.name=development-fleet --spec.description="Development environment - relaxed compliance" --cli-region=cn-north-4
```

### S2: Create Business-Domain Fleet Groups

```bash
hcloud UCS RegisterClusterGroup --metadata.name=core-banking --spec.description="Core banking service clusters" --cli-region=cn-north-4
hcloud UCS RegisterClusterGroup --metadata.name=user-services --spec.description="User authentication and profile services" --cli-region=cn-north-4
hcloud UCS RegisterClusterGroup --metadata.name=data-platform --spec.description="Data analytics and ML clusters" --cli-region=cn-north-4
```

### S3: Reorganize Fleet Groups

When organizational structure changes, restructure fleet groups:

```bash
hcloud UCS RegisterClusterGroup --metadata.name=new-prod-fleet --spec.description="Reorganized production fleet" --cli-region=cn-north-4

hcloud UCS DeleteClusterGroup --clustergroupid=<old-group-id> --cli-region=cn-north-4
```

### S4: Audit Fleet Groups

Review all fleet groups and their associated clusters:

```bash
hcloud UCS ListClusterGroup --cli-region=cn-north-4

hcloud UCS ShowClusterList --cli-region=cn-north-4

hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4
```

## Fleet Group & Policy Governance Integration

Fleet groups serve as the organizational foundation for UCS policy governance. When creating policy instances (see `ucs-policy-governor` skill), you can bind them to fleet groups for consistent enforcement across all member clusters.

**Typical Workflow**:
1. Create fleet groups for organizational grouping
2. Register clusters and assign them to fleet groups
3. Create policy instances bound to fleet groups (via `ucs-policy-governor`)
4. Monitor compliance across all member clusters