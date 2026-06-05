# Task: Repository Permissions

## Overview

SWR repository permissions provide granular access control for individual image repositories within a namespace. This task covers granting, querying, modifying, and revoking repository-level permissions.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ShowUserRepositoryAuth` | GET | 查询镜像仓库权限       | `--namespace`, `--repository`                   |
| `CreateUserRepositoryAuth` | POST | 创建镜像仓库权限     | `--namespace`, `--repository`, `--[N].auth`, `--[N].user_id`, `--[N].user_name` |
| `UpdateUserRepositoryAuth` | PUT | 修改镜像仓库权限      | `--namespace`, `--repository`, `--[N].auth`, `--[N].user_id`, `--[N].user_name` |
| `DeleteUserRepositoryAuth` | DELETE | 删除镜像仓库权限     | `--namespace`, `--repository`, `--[N].user_id`, `--[N].user_name` |

## Workflows

### W1: Audit Repository Permissions

```bash
# Show who has access to a specific repository
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):
- `id`: Repository numeric ID
- `name`: Repository name
- `self_auth`: Your own permission object
  - `user_id`: Your IAM user ID
  - `user_name`: Your IAM user name
  - `auth`: Your permission level (7=manage, 3=edit, 1=read)
- `others_auths`: Array of other users' permission objects
  - Each has `user_id`, `user_name`, `auth` fields

**⚠️ Important**: Same structure as namespace auth — `self_auth` is separate from `others_auths`.

### W2: Grant Repository Permission

**Pre-grant Checklist**:
1. Verify repository exists: `hcloud SWR ShowRepository --namespace=<name> --repository=<repo> --cli-region=cn-north-4`
2. Obtain the target user's IAM user ID and user name
3. Decide the appropriate auth level (7=manage, 3=edit, 1=read)

```bash
# Grant manage permission on a repository
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Grant edit permission (push/pull)
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4

# Grant read permission (pull only)
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=1 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

**⚠️ Array-Style Parameters**: Same format as namespace permissions — use `--1.auth`, `--1.user_id`, `--1.user_name` (1-based index).

**Post-grant Verification**:

```bash
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

### W3: Modify Repository Permission

```bash
# Downgrade from manage to edit
hcloud SWR UpdateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Upgrade from read to edit
hcloud SWR UpdateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

### W4: Revoke Repository Permission

```bash
hcloud SWR DeleteUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Post-revoke Verification**:

```bash
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

## Namespace vs Repository Permissions

| Aspect           | Namespace Permission              | Repository Permission            |
| ---------------- | --------------------------------- | -------------------------------- |
| Scope            | ALL repositories under namespace  | Single specific repository       |
| Use case         | Broad team/project access         | Granular per-repo access         |
| Cascade effect   | Affects all repos in namespace    | Only affects one repo            |
| Recommended      | Team-wide access needs            | External partner or specific role|

**When to use each**:
- **Namespace permission**: When a user needs consistent access across all repos in the namespace
- **Repository permission**: When a user only needs access to specific repos, or when you want to grant different levels for different repos

## Common Scenarios

### S1: External Partner Access to Specific Repository

Grant an external partner read access to only one repository:

```bash
# Grant read on a specific repo (not the whole namespace)
hcloud SWR CreateUserRepositoryAuth --namespace=team-backend --repository=shared-base-image --1.auth=1 --1.user_id=<partner-id> --1.user_name=<partner-name> --cli-region=cn-north-4
```

### S2: CI/CD Pipeline Push Access

Grant a CI/CD pipeline edit access to push images:

```bash
# Grant edit (push/pull) on specific repository
hcloud SWR CreateUserRepositoryAuth --namespace=team-backend --repository=my-app --1.auth=3 --1.user_id=<pipeline-id> --1.user_name=<pipeline-name> --cli-region=cn-north-4
```

### S3: Mixed Permission Levels

Grant different levels for different repositories within the same namespace:

```bash
# Grant edit on development repo
hcloud SWR CreateUserRepositoryAuth --namespace=team-backend --repository=my-app-dev --1.auth=3 --1.user_id=<dev-id> --1.user_name=<dev-name> --cli-region=cn-north-4

# Grant read on production repo
hcloud SWR CreateUserRepositoryAuth --namespace=team-backend --repository=my-app-prod --1.auth=1 --1.user_id=<dev-id> --1.user_name=<dev-name> --cli-region=cn-north-4
```