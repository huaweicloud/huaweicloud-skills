# Workspace Config Reference 工作空间配置参考

## Source 来源

All field definitions are derived from **SDK source code** (`client.py`), **server DTOs**
(`CreateWorkspaceDto.java`, `UpdateWorkspaceDto.java`, `MemberDto.java`), **entity**
(`Workspace.java`), and **OpenAPI spec** (`api/workspace.yaml`).

## Workspace Entity 工作空间实体

| Field | Type | JSON Key | Description |
|-------|------|----------|-------------|
| `workspaceId` | String (UUID) | `workspace_id` | Auto-generated UUID; readonly |
| `name` | String | `name` | 3-64 chars; pattern: `^[\u4e00-\u9fa5a-zA-Z0-9-_./]{3,64}$`; unique per domain (case-insensitive) |
| `description` | String | `description` | 0-512 chars; optional |
| `assetCatalogId` | String (UUID) | `asset_catalog_id` | Auto-created on workspace creation; readonly |
| `defaultObsPath` | String | `default_obs_path` | Must match `^obs://[a-z0-9\-]{3,63}/[^\s]+$`; max 512 chars |
| `domainId` | String | `domain_id` | 32-char hex; auto-set from user context; readonly |
| `ownerId` | String | `owner_id` | Auto-set to creator; updatable via `update --owner-id` |
| `createAt` | Long | `create_at` | Unix timestamp (ms); readonly |
| `updateAt` | Long | `update_at` | Unix timestamp (ms); readonly |
| `tags` | List\<String\> | `tags` | Max 10 tags; each 1-16 chars; pattern: `^[0-9a-zA-Z\u4e00-\u9fa5_.@-]{1,16}$` |
| `deleted` | Integer | — | Soft delete flag (0=active, 1=deleted); internal only |

## Create Workspace Fields 创建工作空间字段

| Field | Required | Type | Validation | Description |
|-------|----------|------|------------|-------------|
| `name` | Yes | String | 3-64 chars, `^[\u4e00-\u9fa5a-zA-Z0-9-_./]{3,64}$` | Workspace name; unique per domain |
| `default_obs_path` | Yes | String | `^obs://[a-z0-9\-]{3,63}/[^\s]+$`, max 512 | Default OBS storage path |
| `description` | No | String | 0-512 chars | Workspace description |
| `tags` | No | List\<String\> | Max 10, each 1-16 chars | Tag list (full replacement on update) |
| `member_list` | No | List\<MemberDto\> | Max 100 | Members to add on creation |

## Update Workspace Fields 更新工作空间字段

| Field | Required | Type | Validation | Description |
|-------|----------|------|------------|-------------|
| `workspace_id` | Yes (in path) | String (UUID) | UUID pattern | Target workspace ID |
| `name` | No | String | 3-64 chars | New workspace name |
| `description` | No | String | 0-512 chars | New description |
| `tags` | No | List\<String\> | Max 10, each 1-16 chars | Full tag replacement |
| `owner_id` | No | String | `^[0-9a-z]{32}$` | New owner user ID (transfer ownership) |
| `default_obs_path` | No | String | obs:// pattern | New default OBS path (default workspace: first-time only) |

## Member Fields 成员字段

### MemberDto

| Field | Required | Type | Validation | Description |
|-------|----------|------|------------|-------------|
| `user_id` | Yes | String | `^[0-9a-z]{32}$` (IAM project ID) | IAM sub-user ID |
| `role_ids` | Yes | List\<String\> | UUID pattern, max 10 | Role ID list |

### CreateMemberDto

| Field | Required | Type | Validation | Description |
|-------|----------|------|------------|-------------|
| `workspace_id` | No (in path) | String (UUID) | UUID pattern | Target workspace ID |
| `member_list` | Yes | List\<MemberDto\> | Max 100, non-empty | Members to add |

### UpdateMemberDto

| Field | Required | Type | Validation | Description |
|-------|----------|------|------------|-------------|
| `user_id` | Yes | String | `^[0-9a-z]{32}$` | Target member user ID |
| `role_ids` | Yes | List\<String\> | UUID pattern, max 10 | New role ID list |

## Role System 角色系统

| Role Name | Sort | Description | Constraint |
|-----------|------|-------------|------------|
| `super_administrator` | 0 | Super administrator | Root user only; auto-assigned |
| `administrator` | 1 | Administrator | Can manage workspace resources |
| `member` | 2 | Regular member | Basic workspace access |

**Notes:**
- Role IDs are dynamic UUIDs, fetched from server at runtime — do not hardcode
- Root user is always `super_administrator` across all workspaces
- Workspace creator (non-root) is automatically assigned `administrator` role
- Member list is sorted by: owner first, then by role sort value (ascending)

## List Response 列表响应

### WorkspaceListVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `workspaces` | `workspaces` | List\<WorkspaceList\> | Workspace list with owner, role_ids, repository_id |
| `pageInfo` | `page_info` | PageInfo | Pagination info (total, current_count, offset) |
| `lastCount` | `last_count` | Integer | Remaining workspace quota |

### WorkspaceList (extends Workspace)

| Additional Field | JSON Key | Type | Description |
|------------------|----------|------|-------------|
| `owner` | `owner` | String | Owner username (resolved from IAM) |
| `roleIds` | `role_ids` | List\<String\> | Current user's role IDs in this workspace |
| `repositoryId` | `repository_id` | String | Asset repository ID |

## Overview Response 概览响应

### WorkspaceOverviewVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `workspaceCapacity` | `workspace_capacity` | int | Max workspaces for this domain |
| `workspaceUsed` | `workspace_used` | int | Current workspace count |
| `workspaceAvailable` | `workspace_available` | int | Remaining workspace quota |
| `memberCapacity` | `member_capacity` | int | Max members (requires BASIC resource SKU) |
| `memberCount` | `member_count` | int | Current member count (including root user) |

## Member Response 成员响应

### MemberListVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `members` | `members` | List\<MemberVo\> | Member list |
| `remainCount` | `remain_count` | Integer | Remaining member quota |

### MemberVo

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `workspaceId` | `workspace_id` | String | Workspace ID |
| `userId` | `user_id` | String | User ID |
| `username` | `username` | String | Username (resolved from IAM) |
| `roles` | `roles` | List\<RoleVo\> | Role list (role_id + role_name + sort) |
| `isOwner` | `is_owner` | Boolean | Whether this member is the workspace owner |

## Workspace Context File 工作空间上下文文件

`~/.cloudrobo/workspace.json` (created by `workspace use`):

```json
{
  "workspace_id": "c1d2e3f4-a5b6-7890-cdef-901234567890",
  "name": "production",
  "asset_catalog_id": "b8ba761c-ed82-4c80-80fa-2d48fce98af9",
  "default_obs_path": "obs://bucket/prod"
}
```

File permissions: `0o600` (owner read/write only).

## Default Workspace 默认工作空间

| Property | Value |
|----------|-------|
| Name | `default` (case-insensitive) |
| Auto-creation | Created on first `list` if not exists |
| Asset catalog | Created without OBS path (null); set on first `default_obs_path` update |
| Owner | Root user of the domain |
| Member operations | Not supported (add/update/delete all rejected) |
| Delete | Not allowed |
| Update | Only `default_obs_path` (first-time only); other fields rejected |

## Server-Side Create Flow 服务端创建流程

1. `checkResourceSku` — Validate member resource SKUs
2. `checkWorkspaceCondition` — Check name uniqueness + workspace count quota
3. Create `Workspace` entity (UUID, timestamps, domain/user from context)
4. `bindBucketPolicy` — Bind OBS bucket policy for the domain
5. `createAssetCatalog` — Create asset repository + catalog via AssetCenterClient
6. `workspaceMapper.insertWorkspace` — Insert to DB
7. `addAdministrator` — Add creator as administrator (if non-root user)
8. `createWorkspaceQuota` — Create default quota (CCE CPU/GPU, ModelArts Standard/Lite)
9. Add members (if `member_list` provided, excluding creator)
