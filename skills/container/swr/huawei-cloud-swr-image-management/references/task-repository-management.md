# Task: Repository Management

## Overview

SWR image repositories hold container images within a namespace. This task covers creating, querying, updating, and deleting repositories.

## Operations Catalog

| Operation           | Method | Description              | Key Parameters                                  |
| ------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `ListReposDetails`  | GET    | 查询镜像仓库列表         | `--namespace`, `--name`, `--category`, `--limit`, `--offset` |
| `ShowRepository`    | GET    | 查询镜像仓库概要信息     | `--namespace`, `--repository`                   |
| `CreateRepo`        | POST   | 创建镜像仓库             | `--namespace`, `--repository`, `--is_public`, `--category`, `--description` |
| `UpdateRepo`        | PATCH  | 更新镜像仓库信息         | `--namespace`, `--repository`, `--is_public`, `--category`, `--description` |
| `DeleteRepo`        | DELETE | 删除镜像仓库             | `--namespace`, `--repository`                   |
| `ListNamespaceRepositories` | GET | 查询组织下镜像仓库列表 | `--namespace`                                   |

## Workflows

### W1: List Repositories

```bash
# List all repositories across all namespaces
hcloud SWR ListReposDetails --cli-region=cn-north-4

# List repositories in a specific namespace
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4

# List repositories with pagination
hcloud SWR ListReposDetails --namespace=group-dev --limit=20 --offset=0 --cli-region=cn-north-4

# Sort by most recently updated
hcloud SWR ListReposDetails --namespace=group-dev --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Sort by tag count (order_column uses "tag_count" even though response field is "num_images")
hcloud SWR ListReposDetails --namespace=group-dev --order_column=tag_count --order_type=desc --cli-region=cn-north-4

# Search by name (fuzzy match)
hcloud SWR ListReposDetails --name=nginx --cli-region=cn-north-4

# Filter by category
hcloud SWR ListReposDetails --category=database --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):
- `namespace`: Parent namespace
- `name`: Repository name
- `category`: Repository category
- `description`: Repository description
- `is_public`: Whether publicly visible
- `num_images`: Number of image tags (**NOT** `tag_count`)
- `num_download`: Total download count
- `size`: Total storage size in bytes
- `tags`: Array of tag name strings included directly in listing
- `path`: Full image path for docker pull
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### W2: View Repository Details

```bash
hcloud SWR ShowRepository --namespace=group-dev --repository=nginx --cli-region=cn-north-4
```

**Output Fields** (verified — different from ListReposDetails):
- `ns_id`: Namespace numeric ID
- `creator_id`: Creator IAM user ID (hex string)
- `creator_name`: Creator IAM user name
- `num_images`: Tag count (**NOT** `tag_count`)
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at`)
- `domain_id`: Domain ID (hex string)
- `priority`: Repository priority (default 0)

**Use Cases**:
- Check repository visibility (public/private)
- View tag count and storage size
- Verify repository before updating or deleting

### W3: Create a Repository

**Pre-creation Checklist**:
1. Verify namespace exists: `hcloud SWR ShowNamespace --namespace=<name> --cli-region=cn-north-4`
2. Check repository name follows naming rules (1-128 chars)
3. Decide visibility: `is_public=true` for public sharing, `is_public=false` for internal use
4. Choose appropriate category

```bash
# Create a private repository
hcloud SWR CreateRepo --namespace=group-dev --repository=my-app --is_public=false --category=other --description="Custom application image" --cli-region=cn-north-4

# Create a public repository
hcloud SWR CreateRepo --namespace=group-dev --repository=nginx --is_public=true --category=app_server --description="Nginx web server" --cli-region=cn-north-4
```

**Category Options**: `app_server`, `linux`, `framework_app`, `database`, `lang`, `other`, `windows`, `arm`

**Post-creation Verification**:

```bash
hcloud SWR ShowRepository --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

### W4: Update Repository Properties

```bash
# Change visibility from private to public
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --cli-region=cn-north-4

# Update description
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --description="Updated: production-ready app" --cli-region=cn-north-4

# Change category
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --category=framework_app --cli-region=cn-north-4
```

**Note**: `--is_public` is required for `UpdateRepo` even if you only want to change description or category.

### W5: Delete a Repository

⚠️ **CAUTION**: Deleting a repository permanently removes ALL image tags. This is irreversible.

**Pre-deletion Checklist**:
1. List all tags to verify what will be deleted:
```bash
hcloud SWR ListRepositoryTags --namespace=<name> --repository=<repo> --cli-region=cn-north-4
```
2. Confirm with user that all tags will be permanently deleted

```bash
hcloud SWR DeleteRepo --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404
hcloud SWR ShowRepository --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

## Common Scenarios

### S1: Standard Project Repository Setup

Set up repositories for a typical development team:

```bash
# Create namespace for the project
hcloud SWR CreateNamespace --namespace=proj-microservice --cli-region=cn-north-4

# Create repositories for each service
hcloud SWR CreateRepo --namespace=proj-microservice --repository=order-service --is_public=false --category=framework_app --description="Order management service" --cli-region=cn-north-4
hcloud SWR CreateRepo --namespace=proj-microservice --repository=user-service --is_public=false --category=framework_app --description="User management service" --cli-region=cn-north-4
hcloud SWR CreateRepo --namespace=proj-microservice --repository=gateway --is_public=false --category=app_server --description="API gateway" --cli-region=cn-north-4
```

### S2: Audit Repository Inventory

Periodically review repositories across all namespaces:

```bash
# List all repositories sorted by tag count (order_column uses "tag_count", response field is "num_images")
hcloud SWR ListReposDetails --order_column=tag_count --order_type=desc --cli-region=cn-north-4

# List repositories in a specific namespace
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4

# For each repository, check tag details
hcloud SWR ShowRepository --namespace=group-dev --repository=nginx --cli-region=cn-north-4
```

### S3: Change Repository Visibility

Switch a repository between public and private:

```bash
# Make repository public (for sharing with external teams)
hcloud SWR UpdateRepo --namespace=group-dev --repository=base-image --is_public=true --cli-region=cn-north-4

# Make repository private (for internal use only)
hcloud SWR UpdateRepo --namespace=group-dev --repository=internal-tool --is_public=false --cli-region=cn-north-4
```