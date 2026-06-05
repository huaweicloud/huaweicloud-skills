---
id: huawei-cloud-swr-image-management
name: huawei-cloud-swr-image-management
description: |
  Huawei Cloud SWR (Software Repository for Container) image lifecycle management skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage SWR namespaces (organizations) - create/query/delete, (2) manage image repositories - create/query/update/delete, (3) manage image tags/versions - query/create/delete, (4) obtain docker login credentials for SWR, (5) check SWR quotas and usage limits.
  Trigger: user mentions "SWR image management", "SWR 镜像管理", "container image", "镜像仓库", "SWR 组织", "SWR namespace", "镜像版本", "docker login", "SWR 配额", "SWR tag", "容器镜像", "镜像生命周期", "SWR repository", "SWR 登录", "SWR quota"
tags: [swr, image-management, namespace, repository, tag]
version: 1.0.0
---

# Huawei Cloud SWR Image Management

## Overview

This skill provides lifecycle management capabilities for Huawei Cloud SWR (Software Repository for Container) images using the `hcloud` CLI.

**Architecture**: hcloud CLI → SWR Service API → Namespace/Repository/Tag/Auth/Quota resources

**Related Skills**:
- `huawei-cloud-swr-image-governance` - Image governance (permissions, retention, sharing, tags, immutable rules)
- `huawei-cloud-swr-image-automation` - Image automation ops (sync, triggers, domains)
- `huawei-cloud-swr-enterprise-instance` - Enterprise instance management

- Create and manage SWR namespaces (organizations)
- Create and manage image repositories with public/private settings
- Query and manage image tags/versions
- Obtain docker login credentials (temporary and long-term)
- Check SWR resource quotas

**Typical Use Cases**:

- "Create a SWR namespace for my project"
- "List all image repositories in namespace 'group-dev'"
- "Query image tags for repository 'nginx' in namespace 'group-dev'"
- "Get docker login command for SWR"
- "Delete an old image tag to clean up storage"
- "Check my SWR quota usage"
- "Create a private repository for my custom image"
- "Update repository description and visibility"

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
| `swr:namespace:create`           | Create namespace  | Create SWR organizations               |
| `swr:namespace:list`             | List namespaces   | Query all namespaces                   |
| `swr:namespace:get`              | Get namespace     | View individual namespace information  |
| `swr:namespace:delete`           | Delete namespace  | Remove organizations                   |
| `swr:repository:create`          | Create repo       | Create image repositories              |
| `swr:repository:list`            | List repos        | Query image repositories               |
| `swr:repository:get`             | Get repo          | View repository details                |
| `swr:repository:update`          | Update repo       | Modify repository properties           |
| `swr:repository:delete`          | Delete repo       | Remove image repositories              |
| `swr:tag:list`                   | List tags         | Query image tags/versions              |
| `swr:tag:get`                    | Get tag           | View specific tag details              |
| `swr:tag:create`                 | Create tag        | Create image tag                       |
| `swr:tag:delete`                 | Delete tag        | Remove image tag                       |
| `swr:login:get`                  | Get login token   | Obtain docker login credentials        |
| `swr:quota:get`                  | Get quota         | Check resource quotas                  |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Namespace (Organization) Management

See [Task: Namespace Management](references/task-namespace-management.md) for detailed workflows.

```bash
# List all namespaces
hcloud SWR ListNamespaces --cli-region=cn-north-4

# List namespaces with filter
hcloud SWR ListNamespaces --filter="namespace::group-dev|mode::visible" --cli-region=cn-north-4

# Show namespace details
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4

# Create a namespace
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-north-4

# Delete a namespace (CAUTION: removes all repos under it)
hcloud SWR DeleteNamespaces --namespace=group-dev --cli-region=cn-north-4
```

**Namespace Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, dots, underscores, or hyphens
- Max 2 consecutive underscores
- Dots, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-64 characters

### 2. Repository (Image Repository) Management

See [Task: Repository Management](references/task-repository-management.md) for detailed workflows.

```bash
# List all repositories
hcloud SWR ListReposDetails --cli-region=cn-north-4

# List repositories in a namespace
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4

# List repositories with pagination and sorting
hcloud SWR ListReposDetails --namespace=group-dev --limit=20 --offset=0 --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# List repositories by category
hcloud SWR ListReposDetails --category=database --cli-region=cn-north-4

# Show repository details
hcloud SWR ShowRepository --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# Create a repository
hcloud SWR CreateRepo --namespace=group-dev --repository=my-app --is_public=false --category=other --description="Custom app image" --cli-region=cn-north-4

# Update repository (change visibility, description, category)
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --description="Updated description" --cli-region=cn-north-4

# Delete a repository (CAUTION: removes all image tags)
hcloud SWR DeleteRepo --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Repository Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots, slashes, underscores, or hyphens
- Max 2 consecutive underscores
- Dots, slashes, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-128 characters

**Repository Categories**: `app_server`, `linux`, `framework_app`, `database`, `lang`, `other`, `windows`, `arm`

### 3. Image Tag (Version) Management

See [Task: Tag Management](references/task-tag-management.md) for detailed workflows.

```bash
# List all tags in a repository
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# List tags with pagination and sorting
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --offset=0 --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Search for a specific tag
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --filter="tag::v1.0" --cli-region=cn-north-4

# Show tag details (image digest, size, create time)
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4

# Create a tag (retag existing image)
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.0 --destination_tag=v1.0-stable --override=false --cli-region=cn-north-4

# Delete a tag (CAUTION: removes the image version permanently)
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```

### 4. Docker Login & Authentication

See [Task: Auth Management](references/task-auth-management.md) for detailed workflows.

```bash
# Get temporary docker login credentials (valid for 12 hours)
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# Get long-term docker login credentials (valid for 1 year)
hcloud SWR CreateSecret --cli-region=cn-north-4
```

**Response Format** (verified against actual API):

The response returns a Docker auth config object:

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-auth-token"
    }
  }
}
```

- `auths`: Docker config auth object, registry host as key
- `auth`: Base64-encoded `username:password` string

**Docker Login Command**:

```bash
# Decode auth field: echo <auth_value> | base64 -d → username:password
docker login -u <decoded_username> -p <decoded_password> swr.cn-north-4.myhuaweicloud.com
```

### 5. Quota Management

See [Task: Quota Management](references/task-quota-management.md) for detailed workflows.

```bash
# Check SWR quotas
hcloud SWR ListQuotas --cli-region=cn-north-4
```

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--namespace`   | Context-dependent | SWR namespace (organization)  | N/A                                  |
| `--repository`  | Context-dependent | Image repository name         | N/A                                  |
| `--tag`         | Context-dependent | Image tag/version name        | N/A                                  |

### Namespace Parameters

| Parameter      | Required | Description            | Constraints                                    |
| -------------- | -------- | ---------------------- | ---------------------------------------------- |
| `--namespace`  | Yes      | Namespace name         | 1-64 chars, lowercase start, specific rules    |
| `--filter`     | No       | Filter by name/mode    | `namespace::{name}|mode::{mode}`               |

### Repository Parameters

| Parameter         | Required | Description              | Constraints                                  |
| ----------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`     | Yes      | Namespace name           | See naming rules                             |
| `--repository`    | Yes      | Repository name          | See naming rules                             |
| `--is_public`     | Yes      | Public/private           | `true` or `false`                            |
| `--category`      | No       | Repository category      | See category list                            |
| `--description`   | No       | Repository description   | Free text                                    |
| `--limit`         | No       | Page size                | Max 1000, default 100                        |
| `--offset`        | No       | Page offset              | Must pair with `--limit`                     |
| `--order_column`  | No       | Sort column              | `name`, `updated_time`, `tag_count` (note: `tag_count` is the param value even though response field is `num_images`) |
| `--order_type`    | No       | Sort direction           | `desc` (descending), `asc` (ascending)       |
| `--name`          | No       | Search by name (fuzzy)   | Partial match                                |

### Tag Parameters

| Parameter         | Required | Description              | Constraints                                  |
| ----------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`     | Yes      | Namespace name           | See naming rules                             |
| `--repository`    | Yes      | Repository name          | See naming rules                             |
| `--tag`           | Yes      | Tag/version name         | Free text                                    |
| `--source_tag`    | Yes      | Source tag (for create)  | Existing tag name                            |
| `--destination_tag` | Yes    | Target tag (for create)  | New tag name                                 |
| `--override`      | No       | Overwrite existing tag   | `true` or `false`                            |

## Output Format

### Namespace List

```json
{
  "namespaces": [
    {
      "id": 3827347,
      "name": "group-dev",
      "creator_name": "user-name",
      "auth": 7,
      "access_user_count": 1,
      "repo_count": 2
    }
  ]
}
```

### Repository List

Response is a flat JSON array (not wrapped in an object):

```json
[
  {
    "name": "nginx",
    "category": "app_server",
    "description": "Nginx web server",
    "size": 268435456,
    "is_public": true,
    "num_images": 5,
    "num_download": 120,
    "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
    "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
    "namespace": "group-dev",
    "domain_name": "user-name",
    "tags": ["v1.0", "v1.1", "latest"],
    "created_at": "2026-04-15T10:30:00Z",
    "updated_at": "2026-05-20T14:20:00Z",
    "logo": "",
    "url": "",
    "status": false,
    "total_range": 2
  }
]
```

**Note**: `num_images` is the tag count (not `tag_count`). `tags` is an array of tag name strings included directly in the repository listing.

### Tag List

Response is a flat JSON array (not wrapped in an object):

```json
[
  {
    "id": 32962315,
    "repo_id": 3374895,
    "Tag": "v1.0",
    "image_id": "f47c82866a20...",
    "digest": "sha256:c8cede14b121...",
    "schema": 2,
    "size": 134217728,
    "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
    "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
    "is_trusted": false,
    "created": "2026-04-15T10:30:00Z",
    "updated": "2026-05-20T14:20:00Z",
    "domain_id": "xxx",
    "scanned": false,
    "tag_type": 0
  }
]
```

**Note**: Tag name field is `Tag` (capital T), timestamps use `created`/`updated` (not `created_at`/`updated_at`).

### Show Repository Details

```json
{
  "id": 3374887,
  "ns_id": 3827347,
  "name": "nginx",
  "category": "other",
  "creator_id": "05949eb5...",
  "creator_name": "user-name",
  "num_images": 17,
  "num_download": 35,
  "is_public": false,
  "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
  "created": "2026-03-26T07:42:40Z",
  "updated": "2026-05-06T09:22:11Z",
  "domain_id": "05949eb4...",
  "priority": 0
}
```

**Note**: ShowRepository uses `created`/`updated` and `num_images` — **different** from ListReposDetails which uses `created_at`/`updated_at`.

### Auth Token Response

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-username:password"
    }
  }
}
```

**Note**: The `auth` field is base64-encoded. Decode it to get docker login credentials. This is a Docker config format, NOT a header+body response.

### Quota List

```json
{
  "quotas": [
    {
      "quota_key": "namespace",
      "quota_limit": 5,
      "used": 1,
      "unit": ""
    }
  ]
}
```

**Note**: Quotas are returned as an **array of objects** with `quota_key`/`quota_limit`/`used`/`unit` fields, not flat key-value pairs like `namespace_limit`/`namespace_used`.

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

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

## Best Practices

1. **Namespace Organization**: Use descriptive namespace names following team/project naming (e.g., `team-backend`, `proj-ai`)
2. **Repository Visibility**: Set `is_public=false` for internal images; only set `is_public=true` for images intended for public sharing
3. **Tag Naming Convention**: Use semantic versioning (e.g., `v1.0`, `v1.0-stable`, `latest`) and avoid ambiguous tags
4. **Regular Cleanup**: Periodically delete outdated tags to manage storage quotas
5. **Retag Instead of Re-push**: Use `CreateRepoTag` to create version aliases rather than pushing the same image multiple times
6. **Long-term Login for CI/CD**: Use `CreateSecret` for automation pipelines; use `CreateAuthorizationToken` for temporary access
7. **Delete with Caution**: Deleting a namespace removes ALL repositories under it; deleting a repository removes ALL tags

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR API Guide](references/swr-api-guide.md)           | hcloud SWR API reference                 |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Namespace Management](references/task-namespace-management.md) | Namespace workflows   |
| [Task: Repository Management](references/task-repository-management.md) | Repository workflows  |
| [Task: Tag Management](references/task-tag-management.md) | Tag workflows                        |
| [Task: Auth Management](references/task-auth-management.md) | Login credential workflows          |
| [Task: Quota Management](references/task-quota-management.md) | Quota check workflows             |

## Notes

- **Namespace deletion is irreversible** — removes all repositories and images under it
- **Repository deletion is irreversible** — removes all image tags permanently
- **Tag deletion is irreversible** — the image version cannot be recovered
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **Pagination required for large datasets** — use `--limit` and `--offset` for repositories and tags listing

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                     | Symptom                         | Quick Fix                                    |
| --------------------------- | ------------------------------- | -------------------------------------------- |
| Invalid namespace name      | 400 Bad Request                 | Follow naming rules: lowercase, 1-64 chars   |
| Namespace not found         | 404 Not Found                   | Verify namespace exists with `ShowNamespace`  |
| Repo already exists         | 409 Conflict                    | Use `ShowRepository` to check first           |
| Tag digest mismatch         | Retag fails                     | Verify `source_tag` exists with `ShowRepoTag` |
| Quota exceeded              | 403 Quota limit                 | Check quotas with `ListQuotas`                |
| Auth token expired          | Docker login fails              | Regenerate with `CreateAuthorizationToken`    |
| `Tag` field name            | Tag query returns unexpected structure | Use `Tag` (capital T) not `name`              |
| `num_images` not `tag_count`| Repo listing field mismatch    | Response uses `num_images`; `--order_column` uses `tag_count` |