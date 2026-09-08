---
name: huawei-cloud-cloudrobo-workspace
description: >
  Manage CloudRobo workspaces — create, list, show, update, delete workspaces; manage
  workspace members (add, list, update role, delete); view workspace overview statistics
  (capacity, used, available, member count); switch active workspace context for use by
  other cloudrobo skills (dataset, train, eval, infer, etc.). Workspace is the foundational
  resource container — all other CloudRobo operations require a valid workspace_id.
  Triggers include: workspace management, workspace member management, workspace switching,
  workspace overview, workspace configuration, default workspace, asset catalog creation,
  workspace quota, 工作空间管理, 工作空间成员, 工作空间切换, 工作空间概览, 工作空间配置, 默认工作空间.
tags:
  - huawei-cloud-cloudrobo
  - workspace
  - workspace-management
  - member-management
  - workspace-overview
  - workspace-context
  - asset-catalog
  - workspace-quota
  - default-workspace
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview 概述

The `cloudrobo-workspace` skill manages the full lifecycle of CloudRobo workspaces. A
workspace is the foundational resource container — all other CloudRobo operations (dataset
processing, model training, evaluation, inference, etc.) require a valid `workspace_id`.
This skill covers workspace CRUD, member management (add/list/update-role/delete), workspace
overview statistics, and workspace context switching (`use`/`current`).

**Applicable scenarios:**

- **Workspace management** — Create, list, show, update, or delete workspaces
- **Member management** — Add members, list members, update member roles, delete members
- **Context switching** — Switch active workspace via `use`, verify current via `current`;
  all other skills (dataset, train, eval, infer) read the active workspace from
  `~/.cloudrobo/workspace.json`
- **Overview & quota** — View workspace capacity, used count, available count, member count
- **Onboarding** — First-time setup: create workspace → switch to it → start using other skills

**Architecture:**

```
Agent / LLM
    │
    ├── CLI  →  cloudrobo workspace <command>
    ├── SDK  →  WorkspaceClient (Python)
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/workspaces/*
              /v1/workspaces/{workspace_id}/members/*
              /v1/workspaces/statistic/overview
```

All operations target the `cloudrobo-service` backend. Workspace is a domain-level (account-level)
resource — no `--workspace-id` override needed for workspace operations themselves. The active
workspace context is stored in `~/.cloudrobo/workspace.json` and consumed by all other skills.

## Prerequisites 前置条件

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
initial configuration. Workspace is the first skill to use during onboarding — create a
workspace and run `cloudrobo workspace use` before using any other cloudrobo skill.

## Workflow 工作流

### Onboarding Workflow (First-Time Setup) 首次设置

1. **Verify credentials** — Ensure `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` are set
2. **List existing workspaces** — `cloudrobo workspace list` (a default workspace may already exist)
3. **Create a workspace** (if needed) — `cloudrobo workspace create --name <name> --default-obs-path <obs://...>`
4. **Switch to workspace** — `cloudrobo workspace use --workspace-id <id>` (validates and saves context)
5. **Verify** — `cloudrobo workspace current` (shows active workspace config)
6. **Proceed** — Other skills (dataset, train, eval, infer) now use the active workspace

### Standard Workflow (Workspace CRUD) 工作空间管理

1. **Create** — `cloudrobo workspace create --name <name> --default-obs-path <obs://...> [--description ...] [--tags ...] [--member-list ...]`
2. **List** — `cloudrobo workspace list [--limit N] [--offset N]` (returns workspaces + page_info + last_count)
3. **Show** — `cloudrobo workspace show --workspace-id <id>` (returns full detail including asset_catalog_id)
4. **Update** — `cloudrobo workspace update --workspace-id <id> [--name ...] [--description ...] [--tags ...] [--owner-id ...]`
5. **Delete** — `cloudrobo workspace delete --workspace-id <id>` (irreversible; triggers async cleanup)

### Member Management Workflow 成员管理

1. **List members** — `cloudrobo workspace list-members --workspace-id <id>`
2. **Add members** — `cloudrobo workspace add-members --workspace-id <id> --member-list '<json>'`
3. **Update member role** — `cloudrobo workspace update-member --workspace-id <id> --user-id <uid> --role-ids <r1,r2>`
4. **Delete members** — `cloudrobo workspace delete-members --workspace-id <id> --user-ids <u1,u2>`

### Overview Workflow 概览统计

1. **Get overview** — `cloudrobo workspace overview` (returns workspace_capacity, workspace_used, workspace_available, member_capacity, member_count)

### Context Switching Workflow 工作空间切换

1. **Switch** — `cloudrobo workspace use --workspace-id <id>` (validates workspace, saves to `~/.cloudrobo/workspace.json`)
2. **Verify** — `cloudrobo workspace current` (displays saved workspace config)

## CLI Command Format Standard CLI命令格式标准

```bash
cloudrobo workspace <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Command group | `workspace` | `cloudrobo workspace` |
| Subcommand | kebab-case | `create`, `list`, `show`, `add-members` |
| Workspace ID | `--workspace-id <id>` | `--workspace-id c1d2e3f4-a5b6-7890-cdef-901234567890` |
| Output format | JSON to stdout | `out(result)` |
| Dry-run | `--dry-run` (create/update/delete) | Preview without executing |
| OBS policy bind | `--bind-obs-policy` (update only) | Bind OBS bucket policy only; no other field updated |
| Comma list | `--user-ids id1,id2,id3` | `--user-ids aaa,bbb` |
| JSON string | `--member-list '<json>'` | `--member-list '[{"user_id":"u1","role_ids":["r1"]}]'` |
| Tags | `--tags tag1,tag2` (comma-separated) | `--tags dev,internal` |

## Core Commands 核心命令

### Workspace Management 工作空间管理

#### Create a workspace

```bash
cloudrobo workspace create --name <workspace-name> --default-obs-path <obs://bucket/path> [--description <description>] [--tags <tag1,tag2>] [--member-list '<json>'] [--dry-run]
```

- **SDK:** `client.create_workspace(req: dict)`
- **API:** `POST /v1/workspaces`

Required fields: `name` (3-64 chars, pattern: `^[\u4e00-\u9fa5a-zA-Z0-9-_./]{3,64}$`),
`default_obs_path` (obs:// protocol, max 512 chars). Optional: `description` (max 512),
`tags` (max 10, each 1-16 chars), `member_list` (max 100 members). See
`references/workspace-config-catalog.md` for full field mapping and validation rules.

Server-side actions on create: check name uniqueness → check workspace quota → create
Workspace entity → bind OBS bucket policy → create asset catalog → insert DB → add
administrator (if non-root user) → create default quota → add members (if provided).

#### List workspaces

```bash
cloudrobo workspace list [--limit <n>] [--offset <n>]
```

- **SDK:** `client.list_workspaces(limit=..., offset=...)`
- **API:** `GET /v1/workspaces?limit=<n>&offset=<n>`

Returns: `workspaces` (list), `page_info` (total, current_count, offset), `last_count`
(remaining workspace quota). A default workspace named "default" is auto-created on first
list if it does not exist.

#### Show workspace detail

```bash
cloudrobo workspace show --workspace-id <workspace-id>
```

- **SDK:** `client.show_workspace(workspace_id: str)`
- **API:** `GET /v1/workspaces/{workspace_id}`

Returns: full workspace detail including `workspace_id`, `name`, `description`,
`asset_catalog_id`, `default_obs_path`, `domain_id`, `owner_id`, `owner` (name),
`create_at`, `update_at`, `tags`, `role_ids`, `repository_id`.

#### Update a workspace

```bash
cloudrobo workspace update --workspace-id <workspace-id> [--name <new-name>] [--description <new-description>] [--tags <tag1,tag2>] [--owner-id <user-id>] [--default-obs-path <obs://...>] [--bind-obs-policy] [--dry-run]
```

- **SDK:** `client.update_workspace(workspace_id: str, req: dict)`
- **API:** `PUT /v1/workspaces/{workspace_id}`

Updatable fields: `name`, `description`, `tags` (full replacement), `owner_id` (transfer
ownership), `default_obs_path`, `bind_obs_policy` (boolean flag — binds the OBS bucket
policy only, does not update any other workspace field). The default workspace can only set
`default_obs_path` once (first time); other updates to the default workspace are rejected.

#### Delete a workspace

```bash
cloudrobo workspace delete --workspace-id <workspace-id> [--dry-run]
```

- **SDK:** `client.delete_workspace(workspace_id: str)`
- **API:** `DELETE /v1/workspaces/{workspace_id}`

Deletion is irreversible. Only root user or workspace owner can delete. The default
workspace cannot be deleted. Server creates async cleanup tasks on deletion.

### Member Management 成员管理

#### List workspace members

```bash
cloudrobo workspace list-members --workspace-id <workspace-id>
```

- **SDK:** `client.list_workspace_members(workspace_id: str)`
- **API:** `GET /v1/workspaces/{workspace_id}/members`

Returns: `members` (list with `workspace_id`, `user_id`, `username`, `roles` (role_id +
role_name), `is_owner`), `remain_count` (remaining member quota). The root user is always
listed as super_administrator.

#### Add workspace members

```bash
cloudrobo workspace add-members --workspace-id <workspace-id> --member-list '<json>'
```

- **SDK:** `client.add_workspace_members(workspace_id: str, req: dict)`
- **API:** `POST /v1/workspaces/{workspace_id}/members`

Required: `member_list` JSON array, each entry has `user_id` (32-char hex, IAM project ID
format) and `role_ids` (UUID list, max 10). Root users cannot be added as members. Duplicate
members are rejected. The default workspace does not support member operations.

#### Update a member's roles

```bash
cloudrobo workspace update-member --workspace-id <workspace-id> --user-id <user-id> --role-ids <role-id-1,role-id-2>
```

- **SDK:** `client.update_workspace_member(workspace_id: str, req: dict)`
- **API:** `PUT /v1/workspaces/{workspace_id}/members`

Required: `user_id` and `role_ids`. The workspace owner's role cannot be updated. The
default workspace does not support member operations.

#### Delete workspace members

```bash
cloudrobo workspace delete-members --workspace-id <workspace-id> --user-ids <user-id-1,user-id-2>
```

- **SDK:** `client.delete_workspace_members(workspace_id: str, user_ids: list)`
- **API:** `DELETE /v1/workspaces/{workspace_id}/members?user_ids=<ids>`

The workspace owner cannot be deleted. The default workspace does not support member
operations. Max 20 user IDs per request (API constraint) / 100 per request (CLI constraint).

### Overview & Statistics 概览统计

#### Get workspace overview

```bash
cloudrobo workspace overview
```

- **SDK:** `client.get_workspace_overview()`
- **API:** `GET /v1/workspaces/statistic/overview`

Returns: `workspace_capacity` (max workspaces), `workspace_used` (current count),
`workspace_available` (remaining), `member_capacity` (max members, requires BASIC resource
SKU), `member_count` (current member count including root user).

### Workspace Context 工作空间上下文

#### Switch active workspace

```bash
cloudrobo workspace use --workspace-id <workspace-id>
```

Validates the workspace exists and is accessible, then saves to
`~/.cloudrobo/workspace.json`: `workspace_id`, `name`, `asset_catalog_id`,
`default_obs_path`. All other skills read this file to determine the active workspace.

#### Show current workspace

```bash
cloudrobo workspace current
```

Displays the saved workspace config from `~/.cloudrobo/workspace.json`. If no workspace is
configured, outputs "未配置工作空间".

## Reference Documents 参考文档

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [API Paths](references/api-paths.md) — REST API paths discovered via SDK source
- [Workspace Config Reference](references/workspace-config-catalog.md) — Field mapping, validation rules, role system, member format
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Verification Method](references/verification-method.md) — Verification method details
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria

## Edge Cases 边界情况

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Operations fail with validation error; use `cloudrobo workspace list` to find valid IDs |
| Default workspace | Auto-created on first `list`; cannot be deleted; only supports first-time `default_obs_path` update; does not support member add/update/delete operations |
| Workspace name conflict | Server rejects with `WORKSPACE_NAME_EXIST` error; names are case-insensitive unique per domain |
| Workspace quota exceeded | Server rejects with `WORKSPACE_EXCEED_NUM_LIMIT`; check `overview` for capacity; `last_count` in list response shows remaining |
| Root user as member | Server rejects with `ADD_ADMINISTRATOR_LIMIT_ERROR`; root user is always super_administrator |
| Update/delete workspace owner | Server rejects with `REQUEST_FORBIDDEN_ERROR`; owner's role cannot be changed, owner cannot be removed as member |
| Transfer ownership | `update --owner-id <new-owner>` — new owner must be an existing IAM user; if not root, must be or become a workspace member with administrator role |
| `default_obs_path` format | Must match `^obs://[a-z0-9\-]{3,63}/[^\s]+$`; `s3://` is prohibited |
| `workspace_id` format | Must be UUID: `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$` |
| `user_id` format | Must be 32-char lowercase hex (IAM project ID): `^[0-9a-z]{32}$` |
| `role_ids` format | Must be UUID format; validated against role cache; max 10 per member |
| Member already exists | Server rejects with `WORKSPACE_MEMBER_HAS_EXIST` |
| Member not found | Server rejects with `WORKSPACE_MEMBER_NOT_EXIST` |
| AK/SK not set | Operations fail at HTTP signing step; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| `workspace use` on invalid ID | CLI catches error, outputs "切换失败: ..." and exits with code 1 |
| `workspace current` with no config | Outputs "未配置工作空间" (no workspace configured) |
| Tags full replacement | `update --tags` replaces all tags; to remove all tags, pass empty string |
| Delete triggers cleanup | Server creates async cleanup tasks (`CleanupService`); workspace resources (OBS, catalog, quota) are cleaned asynchronously |
| `asset_catalog_id` | Auto-created on workspace creation (or first `default_obs_path` set for default workspace); stored in workspace entity; used by asset/dataset skills |
| Role system | 3 roles: `super_administrator` (sort=0, root user only), `administrator` (sort=1), `member` (sort=2); role_ids are dynamic UUIDs fetched from server |
| Member sorting | Members sorted by: owner first, then by role sort value (super_administrator > administrator > member) |
| Internal API | `/v1/internal/workspaces` exists for service-to-service calls (no IAM auth); not used by CLI/SDK |
| Object storage paths | Must use `obs://` protocol; `s3://` is prohibited |
| API paths | Sourced from SDK source code (`_url()` calls in `client.py`), not inferred |
| Mutating operations | create/update/delete/add-members/update-member/delete-members should be confirmed by the user |
| Cross-skill invocation | This skill does not call other skills by name; provides foundational workspace context for all other skills |
| `workspace.json` permissions | File created with `0o600` permissions (owner read/write only) |
| Member list in create | When creating workspace with `member_list`, the creator is automatically excluded (no duplicate) |

## Verification Method 验证方法

### Specification Compliance Verification 规范合规验证

```bash
bash scripts/test-cli-commands.sh -s . -e cli
```

### Functional Testing 功能测试

```bash
# CLI / SDK
bash scripts/test-cli-commands.sh -s . -e {cli|sdk}
```

API-level verification is manual — replay the paths in `references/api-paths.md` in
[API Explorer](https://console.huaweicloud.com/apiexplorer/).

### Test Cases 测试用例

See `templates/test-vars.json` for the full test case list covering workspace CRUD, member
management, overview, and context switching scenarios.

### Verification Checklist 验证清单

- After creating a workspace, verify via `show --workspace-id <id>` that `asset_catalog_id` is populated
- After `use --workspace-id <id>`, verify `current` outputs the correct workspace config
- After adding members, verify via `list-members` that new members appear with correct roles
- After deleting a workspace, verify it no longer appears in `list`
- Verify `overview` returns consistent `workspace_used` count with `list` results

## Best Practices 最佳实践

- Always run `workspace list` first to check existing workspaces before creating a new one
- Use `--dry-run` with `create`/`update`/`delete` to preview operations before executing
- After creating a workspace, immediately run `workspace use --workspace-id <id>` to switch context
- Before deleting a workspace, confirm the workspace ID to avoid irreversible deletion
- When adding members, use `list-members` first to check existing members and avoid duplicates
- The default workspace ("default") has special restrictions — prefer creating a named workspace for production use
- Check `workspace overview` periodically to monitor workspace and member quota usage
- `workspace current` is a quick way to verify the active workspace before running other cloudrobo commands
- Transfer ownership with caution — the new owner gains full control of the workspace
- Tags are fully replaced on update, not merged — include all desired tags in the update command
