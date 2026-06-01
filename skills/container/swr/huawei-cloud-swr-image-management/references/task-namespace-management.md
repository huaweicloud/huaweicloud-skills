# Task: Namespace Management

## Overview

SWR namespace (organization) is the top-level grouping for image repositories. All repositories must belong to a namespace. This task covers creating, querying, and deleting namespaces.

## Operations Catalog

| Operation       | Method | Description              | Key Parameters                    |
| --------------- | ------ | ------------------------ | --------------------------------- |
| `ListNamespaces` | GET    | 查询组织列表             | `--filter`                        |
| `ShowNamespace`  | GET    | 获取组织详情             | `--namespace`                     |
| `CreateNamespace` | POST   | 创建组织                 | `--namespace`                     |
| `DeleteNamespaces` | DELETE | 删除组织                 | `--namespace`                     |

## Workflows

### W1: View All Namespaces

```bash
# List all namespaces you have permission to
hcloud SWR ListNamespaces --cli-region=cn-north-4

# List namespaces with visible mode (includes repos you have access to even if namespace access is limited)
hcloud SWR ListNamespaces --filter="mode::visible" --cli-region=cn-north-4

# Search for a specific namespace
hcloud SWR ListNamespaces --filter="namespace::group-dev" --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):
- `id`: Namespace numeric ID
- `name`: Namespace name
- `creator_name`: Creator IAM user name (**NOT** `creator`)
- `auth`: Permission level (7=manage, 3=edit, 1=read)
- `access_user_count`: Number of users with access
- `repo_count`: Number of repositories under this namespace

### W2: Check Namespace Details

```bash
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4
```

**Use Cases**:
- Verify namespace exists before creating repositories
- Check namespace permissions and metadata
- Troubleshoot "namespace not found" errors

### W3: Create a New Namespace

**Pre-creation Checklist**:
1. Verify namespace name follows naming rules (1-64 chars, lowercase start)
2. Check quota availability: `hcloud SWR ListQuotas --cli-region=cn-north-4`
3. Verify namespace doesn't already exist: `hcloud SWR ShowNamespace --namespace=<name> --cli-region=cn-north-4`

```bash
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-north-4
```

**Post-creation Verification**:

```bash
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4
```

### W4: Delete a Namespace

⚠️ **CAUTION**: Deleting a namespace permanently removes ALL repositories and images under it. This is irreversible.

**Pre-deletion Checklist**:
1. List all repositories in the namespace:
```bash
hcloud SWR ListReposDetails --namespace=<name> --cli-region=cn-north-4
```
2. Confirm with user that all repositories and images will be deleted
3. Optionally save critical images by syncing to another region or namespace

```bash
hcloud SWR DeleteNamespaces --namespace=group-dev --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404 or empty result
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4
```

## Common Scenarios

### S1: Organize Images by Team/Project

Create separate namespaces for different teams or projects:

```bash
# Team namespaces
hcloud SWR CreateNamespace --namespace=team-backend --cli-region=cn-north-4
hcloud SWR CreateNamespace --namespace=team-frontend --cli-region=cn-north-4
hcloud SWR CreateNamespace --namespace=team-data --cli-region=cn-north-4

# Project namespaces
hcloud SWR CreateNamespace --namespace=proj-order-service --cli-region=cn-north-4
hcloud SWR CreateNamespace --namespace=proj-user-service --cli-region=cn-north-4
```

### S2: Migrate Namespace

When reorganizing, migrate images by pushing to the new namespace and then deleting the old one:

```bash
# 1. Create new namespace
hcloud SWR CreateNamespace --namespace=team-new-backend --cli-region=cn-north-4

# 2. Push images to new namespace (using docker)
docker tag old-image:latest swr.cn-north-4.myhuaweicloud.com/team-new-backend/old-image:latest
docker push swr.cn-north-4.myhuaweicloud.com/team-new-backend/old-image:latest

# 3. Verify migration
hcloud SWR ListReposDetails --namespace=team-new-backend --cli-region=cn-north-4

# 4. Delete old namespace (after confirming migration is complete)
hcloud SWR DeleteNamespaces --namespace=team-backend --cli-region=cn-north-4
```