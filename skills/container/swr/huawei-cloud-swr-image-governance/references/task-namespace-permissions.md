# Task: Namespace Permissions

## Overview

SWR namespace permissions control who can access and manage images within an organization (namespace). This task covers granting, querying, modifying, and revoking namespace-level permissions.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ShowNamespaceAuth` | GET   | 查询组织权限             | `--namespace`                                   |
| `CreateNamespaceAuth` | POST | 创建组织权限             | `--namespace`, `--[N].auth`, `--[N].user_id`, `--[N].user_name` |
| `UpdateNamespaceAuth` | PUT  | 修改组织权限             | `--namespace`, `--[N].auth`, `--[N].user_id`, `--[N].user_name` |
| `DeleteNamespaceAuth` | DELETE | 删除组织权限             | `--namespace`, `--[N].user_id`, `--[N].user_name` |

## Workflows

### W1: Audit Namespace Permissions

```bash
# Show who has access to a namespace
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):
- `id`: Namespace numeric ID
- `name`: Namespace name
- `creator_name`: Creator IAM user name
- `self_auth`: Your own permission object (separate from others)
  - `user_id`: Your IAM user ID
  - `user_name`: Your IAM user name
  - `auth`: Your permission level (7=manage, 3=edit, 1=read)
- `others_auths`: Array of other users' permission objects
  - Each has `user_id`, `user_name`, `auth` fields

**⚠️ Important**: `self_auth` is separate from `others_auths`. When auditing, check both to get the complete access list.

### W2: Grant Namespace Permission

**Pre-grant Checklist**:
1. Verify namespace exists: `hcloud SWR ShowNamespace --namespace=<name> --cli-region=cn-north-4`
2. Obtain the target user's IAM user ID and user name
3. Decide the appropriate auth level:
   - `7` (manage): Full control — can create/delete repos, manage permissions
   - `3` (edit): Push and pull — can push images and pull images
   - `1` (read): Pull only — can only pull images

```bash
# Grant manage permission (full control)
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Grant edit permission (push/pull)
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4

# Grant read permission (pull only)
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=1 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4

# Grant permissions to multiple users at once
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=<id1> --1.user_name=<name1> --2.auth=3 --2.user_id=<id2> --2.user_name=<name2> --cli-region=cn-north-4
```

**⚠️ Array-Style Parameters**: Use `--1.auth`, `--1.user_id`, `--1.user_name` (1-based index). NOT `--auth`, `--user_id` or `--0.auth`.

**Post-grant Verification**:

```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

### W3: Modify Namespace Permission

Change an existing user's permission level:

```bash
# Downgrade from manage to edit
hcloud SWR UpdateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Upgrade from read to edit
hcloud SWR UpdateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

**Post-update Verification**:

```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

### W4: Revoke Namespace Permission

⚠️ **CAUTION**: Revoking namespace permission removes access to the namespace AND ALL repositories under it.

```bash
hcloud SWR DeleteNamespaceAuth --namespace=pancake --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Pre-revoke Checklist**:
1. Check if the user has repository-level permissions that should be preserved
2. Confirm with the user that they understand the impact
3. Consider whether a downgrade (Update) is more appropriate than full revocation (Delete)

**Post-revoke Verification**:

```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

## Common Scenarios

### S1: Team Access Setup

Grant appropriate permissions to team members:

```bash
# Grant manage to team lead
hcloud SWR CreateNamespaceAuth --namespace=team-backend --1.auth=7 --1.user_id=<lead-id> --1.user_name=<lead-name> --cli-region=cn-north-4

# Grant edit to developers
hcloud SWR CreateNamespaceAuth --namespace=team-backend --1.auth=3 --1.user_id=<dev1-id> --1.user_name=<dev1-name> --2.auth=3 --2.user_id=<dev2-id> --2.user_name=<dev2-name> --cli-region=cn-north-4

# Grant read to QA team
hcloud SWR CreateNamespaceAuth --namespace=team-backend --1.auth=1 --1.user_id=<qa-id> --1.user_name=<qa-name> --cli-region=cn-north-4
```

### S2: Permission Audit

Regularly review who has access:

```bash
# For each namespace, check permissions
hcloud SWR ShowNamespaceAuth --namespace=team-backend --cli-region=cn-north-4

# Downgrade overly broad permissions
hcloud SWR UpdateNamespaceAuth --namespace=team-backend --1.auth=3 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

### S3: Least Privilege Implementation

Apply least privilege by using the minimum auth level needed:

| Role              | Recommended Auth | Access Scope                |
| ----------------- | ---------------- | --------------------------- |
| CI/CD pipeline    | `3` (edit)       | Push and pull images        |
| Developer         | `3` (edit)       | Push and pull images        |
| QA tester         | `1` (read)       | Pull images only            |
| External partner  | `1` (read)       | Pull images only            |
| Namespace admin   | `7` (manage)     | Full control                |