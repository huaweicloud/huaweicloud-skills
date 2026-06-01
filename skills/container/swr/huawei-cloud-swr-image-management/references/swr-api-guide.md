# SWR API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud SWR (Software Repository for Container) operations using hcloud CLI. All commands follow the standard format: `hcloud SWR <Operation> --param=value --cli-region=<region>`.

## Authentication

### Environment Variables

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
```

### hcloud CLI Configuration

```bash
# Interactive configuration
hcloud configure

# Verify configuration (safe - does not expose values)
hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEI_CLOUD_AK` to check credentials

## Namespace Operations

### 1. List Namespaces

```bash
hcloud SWR ListNamespaces --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID
- `--namespace` (optional): Filter by namespace name
- `--filter` (optional): `namespace::{name}|mode::{mode}`

**Response Example** (verified against actual API):

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

**Key Fields**:
- `id`: Namespace numeric ID
- `name`: Namespace name
- `creator_name`: Creator IAM user name
- `auth`: Permission level (7=manage, 3=edit, 1=read)
- `access_user_count`: Number of users with access
- `repo_count`: Number of repositories under this namespace

### 2. Show Namespace Details

```bash
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--cli-region` (required): Region ID

### 3. Create Namespace

```bash
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (body parameter)
- `--cli-region` (required): Region ID

**Namespace Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, dots (`.`), underscores (`_`), or hyphens (`-`)
- Max 2 consecutive underscores
- Dots, underscores, hyphens cannot be directly connected (e.g., `a._b` or `a.-b` is invalid)
- End with lowercase letter or digit
- Length: 1-64 characters

**Valid Examples**: `group-dev`, `team1`, `my.project`, `dev_ops`
**Invalid Examples**: `Group-dev` (uppercase start), `dev__ops` (3 consecutive underscores), `dev.-ops` (dot-hyphen connected)

### 4. Delete Namespace

```bash
hcloud SWR DeleteNamespaces --namespace=group-dev --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--cli-region` (required): Region ID

⚠️ **Warning**: This operation is irreversible. All repositories and images under the namespace will be permanently deleted.

## Repository Operations

### 1. List Repositories

```bash
# List all repositories (no filter)
hcloud SWR ListReposDetails --cli-region=cn-north-4

# List repositories in a namespace
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4

# List repositories with pagination
hcloud SWR ListReposDetails --namespace=group-dev --limit=20 --offset=0 --cli-region=cn-north-4

# Sort repositories by update time (descending)
hcloud SWR ListReposDetails --namespace=group-dev --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Search by name (fuzzy match)
hcloud SWR ListReposDetails --name=nginx --cli-region=cn-north-4

# Filter by category
hcloud SWR ListReposDetails --category=database --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID
- `--namespace` (optional): Namespace name
- `--name` (optional): Repository name (fuzzy match)
- `--category` (optional): Repository category (`app_server`, `linux`, `framework_app`, `database`, `lang`, `other`, `windows`, `arm`)
- `--limit` (optional): Page size, default 100, max 1000
- `--offset` (optional): Page offset (must pair with `--limit`)
- `--order_column` (optional): Sort column (`name`, `updated_time`, `tag_count` — note: `tag_count` is the param value, response field is `num_images`)
- `--order_type` (optional): Sort direction (`desc`, `asc`)
- `--filter` (optional): Complex filter expression

**Response Example** (verified against actual API - flat JSON array):

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

**Key Fields**:
- `name`: Repository name
- `num_images`: Image/tag count (**NOT** `tag_count`)
- `num_download`: Total download count
- `tags`: Array of tag name strings included directly in listing
- `path`: Full image path for docker pull
- `size`: Total storage size in bytes
- `is_public`: Public/private visibility
- Response is a **flat array** (not wrapped in a `repositories` object)

### 2. Show Repository Details

```bash
hcloud SWR ShowRepository --namespace=group-dev --repository=nginx --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "id": 3374887,
  "ns_id": 3827347,
  "name": "nginx",
  "category": "other",
  "description": "",
  "creator_id": "05949eb5350010e21f85c017722182de",
  "creator_name": "user-name",
  "size": 1946933102,
  "is_public": false,
  "num_images": 17,
  "num_download": 35,
  "url": "",
  "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
  "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
  "created": "2026-03-26T07:42:40.069829Z",
  "updated": "2026-05-06T09:22:11.436606Z",
  "domain_id": "05949eb4190010e40f36c017b62fafa0",
  "priority": 0
}
```

**Key Fields**:
- `ns_id`: Namespace numeric ID
- `creator_id`: Creator IAM user ID (hex string)
- `creator_name`: Creator IAM user name
- `num_images`: Image/tag count (**NOT** `tag_count`)
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at` — different from ListReposDetails!)
- `domain_id`: Domain ID (hex string)
- `priority`: Repository priority (default 0)

### 3. Create Repository

```bash
hcloud SWR CreateRepo --namespace=group-dev --repository=my-app --is_public=false --category=other --description="Custom application image" --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (body parameter)
- `--is_public` (required): Public or private (`true`/`false`)
- `--category` (optional): Repository category
- `--description` (optional): Repository description
- `--cli-region` (required): Region ID

**Repository Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots (`.`), slashes (`/`), underscores (`_`), or hyphens (`-`)
- Max 2 consecutive underscores
- Dots, slashes, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-128 characters

### 4. Update Repository

```bash
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --description="Updated description" --category=app_server --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--is_public` (required): Public or private (`true`/`false`)
- `--category` (optional): New category
- `--description` (optional): New description
- `--cli-region` (required): Region ID

### 5. Delete Repository

```bash
hcloud SWR DeleteRepo --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--cli-region` (required): Region ID

⚠️ **Warning**: This operation is irreversible. All image tags in the repository will be permanently deleted.

### 6. List Repositories by Namespace

```bash
hcloud SWR ListNamespaceRepositories --namespace=group-dev --cli-region=cn-north-4
```

This is an alternative to `ListReposDetails` when you want to list repos specifically within one namespace.

## Tag Operations

### 1. List Tags

```bash
# List all tags in a repository
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# List tags with pagination
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --offset=0 --cli-region=cn-north-4

# Sort tags by update time
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Search for specific tag
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --filter="tag::v1.0" --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--cli-region` (required): Region ID
- `--limit` (optional): Page size, default 100, max 1000
- `--offset` (optional): Page offset
- `--order_column` (optional): Sort column (`updated_at`)
- `--order_type` (optional): Sort direction (`desc`, `asc`)
- `--tag` (optional): Search by tag name
- `--filter` (optional): Complex filter expression

**Response Example** (verified against actual API - flat JSON array):

```json
[
  {
    "id": 32962315,
    "repo_id": 3374895,
    "Tag": "v1.0",
    "image_id": "f47c82866a200fa5...",
    "digest": "sha256:c8cede14b1214e45...",
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

**Key Fields**:
- `Tag`: Tag/version name (**capital T**, not lowercase `name`)
- `image_id`: Image content identifier (hex string)
- `digest`: Image content hash (SHA256)
- `size`: Image size in bytes
- `path`: Full image path for docker pull
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at`)
- Response is a **flat array** (not wrapped in a `tags` object)
- `manifest` field contains full OCI/Docker manifest JSON (very long, omitted above)

### 2. Show Tag Details

```bash
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--tag` (required): Image tag/version name
- `--cli-region` (required): Region ID

### 3. Create Tag (Retag)

```bash
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.0 --destination_tag=v1.0-stable --override=false --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--source_tag` (required): Source tag name
- `--destination_tag` (required): Target tag name
- `--override` (optional): Overwrite existing tag (`true`/`false`)
- `--cli-region` (required): Region ID

**Use Case**: Retagging allows you to create aliases for existing image versions without re-pushing the image. For example, tagging `v1.0` as `stable` to indicate it's the current stable release.

### 4. Delete Tag

```bash
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--tag` (required): Image tag/version name
- `--cli-region` (required): Region ID

⚠️ **Warning**: This operation is irreversible. The image version will be permanently deleted.

## Authentication Operations

### 1. Get Temporary Login Token (12-hour validity)

```bash
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID
- `--projectname` (optional): Project name, defaults to region name (e.g., `cn-north-1`)

**Response Example** (verified against actual API - Docker auth config format):

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-auth-token"
    }
  }
}
```

**Key Fields**:
- `auths`: Docker config auth object
- `auth`: Base64-encoded string in format `username:password`
- Registry host is the key under `auths` (e.g., `swr.cn-north-4.myhuaweicloud.com`)

**Usage**:

```bash
# Decode the base64 auth field to get username and password:
# echo <auth_value> | base64 -d  →  username:password
# Then use decoded credentials:
docker login -u <decoded_username> -p <decoded_password> swr.cn-north-4.myhuaweicloud.com
```

### 2. Get Long-term Login Secret (1-year validity)

```bash
hcloud SWR CreateSecret --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID
- `--projectname` (optional): Project name

**Usage**: Recommended for CI/CD pipelines and automation where long-term credentials are needed.

## Quota Operations

### 1. Check Quotas

```bash
hcloud SWR ListQuotas --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID
- `--project_id` (path parameter, auto-filled from credentials)

**Response Example** (verified against actual API - array of quota objects):

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

**Key Fields**:
- `quota_key`: Resource type identifier (`namespace`, `repo`, `tag`, etc.)
- `quota_limit`: Maximum allowed for this resource type
- `used`: Current usage count
- `unit`: Unit of measurement (typically empty string for count-based quotas)
- Response is an **array of quota objects** (not flat key-value pairs)

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
| `NamespaceNotFound`     | Namespace does not exist    | Verify namespace name with `ShowNamespace`       |
| `RepoAlreadyExists`    | Repository name conflict    | Check with `ShowRepository` first                |
| `TagNotFound`           | Tag does not exist          | Verify tag with `ListRepositoryTags`             |
| `QuotaExceeded`         | Resource quota limit        | Check quotas with `ListQuotas`                   |
| `NamespaceNameInvalid`  | Naming rule violation       | Follow naming rules (1-64 chars, lowercase start) |
| `RepoNameInvalid`       | Naming rule violation       | Follow naming rules (1-128 chars, lowercase/digit start) |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                  |

## Related Documentation

- [Huawei Cloud SWR Documentation](https://support.huaweicloud.com/swr/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)