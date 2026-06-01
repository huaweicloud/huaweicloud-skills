# Task: Tag Management

## Overview

Image tags (versions) represent specific image builds within a repository. This task covers querying, creating (retagging), and deleting image tags.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ListRepositoryTags` | GET | 查询镜像tag列表          | `--namespace`, `--repository`, `--limit`, `--offset` |
| `ShowRepoTag`      | GET    | 查询指定tag的镜像        | `--namespace`, `--repository`, `--tag`          |
| `CreateRepoTag`    | POST   | 创建镜像tag              | `--namespace`, `--repository`, `--source_tag`, `--destination_tag`, `--override` |
| `DeleteRepoTag`    | DELETE | 删除镜像tag              | `--namespace`, `--repository`, `--tag`          |

## Workflows

### W1: List All Tags in a Repository

```bash
# List all tags
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# List tags with pagination (for repositories with many tags)
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --offset=0 --cli-region=cn-north-4

# Sort tags by most recently updated
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Search for a specific tag name
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):
- `Tag`: Tag/version name (**capital T**, not `name`) (e.g., `v1.0`, `latest`)
- `image_id`: Image content identifier (hex string)
- `digest`: Image content hash (SHA256)
- `size`: Image size in bytes
- `created`: Creation timestamp (**NOT** `created_at`)
- `updated`: Last update timestamp (**NOT** `updated_at`)
- `path`: Full image path (e.g., `swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0`)
- `manifest`: Full OCI/Docker manifest JSON (very long string)
- `deleted`: Null for active tags
- `domain_id`: Domain ID (hex string)
- `scanned`: Security scan status (boolean)
- `tag_type`: Tag type (0=normal)

### W2: View Tag Details

```bash
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4
```

**Use Cases**:
- Verify image digest before deployment
- Check image size for storage management
- Confirm tag exists before retagging or deleting

### W3: Create a Tag (Retag)

Retagging creates a new tag pointing to the same image as an existing tag. This is useful for:
- Creating version aliases (e.g., `v1.0` → `stable`)
- Marking production-ready versions
- Organizing tags by release stage

```bash
# Create a new tag from an existing tag
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.0 --destination_tag=stable --override=false --cli-region=cn-north-4

# Create a tag with override (replaces existing tag if it exists)
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.1 --destination_tag=latest --override=true --cli-region=cn-north-4
```

**Pre-retag Checklist**:
1. Verify source tag exists:
```bash
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4
```
2. Decide whether to override if destination tag already exists

**Parameters**:
- `--source_tag` (required): Existing tag name to copy from
- `--destination_tag` (required): New tag name to create
- `--override` (optional): Whether to overwrite if destination tag exists (`true`/`false`, default `false`)

### W4: Delete a Tag

⚠️ **CAUTION**: Deleting a tag permanently removes the image version. This is irreversible.

**Pre-deletion Checklist**:
1. Verify the tag details to confirm it's the correct version:
```bash
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```
2. Confirm with user that the image version will be permanently deleted
3. Check if other tags reference the same image digest (they won't be affected)

```bash
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404 or tag should not appear in list
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```

## Common Scenarios

### S1: Tag Versioning Strategy

Apply semantic versioning with retagging:

```bash
# After pushing image with specific version tag
# Create aliases for release stages
hcloud SWR CreateRepoTag --namespace=group-dev --repository=my-app --source_tag=v2.1.0 --destination_tag=stable --override=true --cli-region=cn-north-4
hcloud SWR CreateRepoTag --namespace=group-dev --repository=my-app --source_tag=v2.1.0 --destination_tag=v2 --override=true --cli-region=cn-north-4
hcloud SWR CreateRepoTag --namespace=group-dev --repository=my-app --source_tag=v2.1.0 --destination_tag=latest --override=true --cli-region=cn-north-4
```

**Recommended Tag Strategy**:
- `v{major}.{minor}.{patch}` — specific version (e.g., `v2.1.0`)
- `v{major}.{minor}` — latest minor version (e.g., `v2.1`)
- `v{major}` — latest major version (e.g., `v2`)
- `stable` — current production-ready version
- `latest` — most recently pushed version

### S2: Clean Up Old Tags

Periodically remove outdated tags to manage storage:

```bash
# 1. List all tags sorted by update time
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=my-app --order_column=updated_at --order_type=asc --cli-region=cn-north-4

# 2. For each old tag, verify and delete
hcloud SWR ShowRepoTag --namespace=group-dev --repository=my-app --tag=v1.0-beta --cli-region=cn-north-4
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=my-app --tag=v1.0-beta --cli-region=cn-north-4
```

### S3: Check Image Inventory

Audit all images across namespaces:

```bash
# For each namespace and repository, list tags
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4
# Then for each repository:
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```