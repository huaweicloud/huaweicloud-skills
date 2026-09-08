# API Paths API路径

## Source 来源

All API paths are derived from **SDK source code** (`cloudrobo_workspace.client`)
via `_url()` calls. This is trusted source #1 per the Huawei Cloud Skill Creator specification.
No paths are inferred or guessed. Line numbers are intentionally omitted — they drift
between SDK versions; locate each method by name instead.

## Base Path 基础路径

```
Service: cloudrobo-service
Base URL: https://cloudrobo.{region}.myhuaweicloud.com
API root: /v1/workspaces
```

## Endpoint List 端点列表

### Workspace CRUD 工作空间CRUD

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| Create workspace | POST | `/v1/workspaces` | `create_workspace()` |
| List workspaces | GET | `/v1/workspaces` | `list_workspaces()` |
| Show workspace | GET | `/v1/workspaces/{workspace_id}` | `show_workspace()` |
| Update workspace | PUT | `/v1/workspaces/{workspace_id}` | `update_workspace()` |
| Delete workspace | DELETE | `/v1/workspaces/{workspace_id}` | `delete_workspace()` |

### Member Management 成员管理

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| Add members | POST | `/v1/workspaces/{workspace_id}/members` | `add_workspace_members()` |
| List members | GET | `/v1/workspaces/{workspace_id}/members` | `list_workspace_members()` |
| Update member | PUT | `/v1/workspaces/{workspace_id}/members` | `update_workspace_member()` |
| Delete members | DELETE | `/v1/workspaces/{workspace_id}/members?user_ids=` | `delete_workspace_members()` |

### Overview 统计概览

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| Get overview | GET | `/v1/workspaces/statistic/overview` | `get_workspace_overview()` |

### Internal API (Service-to-Service) 内部接口

| Operation | Method | Path | Controller |
|-----------|--------|------|------------|
| Internal list workspaces | GET | `/v1/internal/workspaces` | `WorkspaceInternalController` |

**Note:** Internal API is used for service-to-service calls without IAM auth. It reads
`X-Apply-DomainID` and `X-Apply-DomainName` headers. Not exposed via CLI/SDK.

## Query Parameters 查询参数

### List Workspaces

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max results (1-100, default 100) |
| `offset` | int | No | Pagination offset (default 0) |

### Delete Members

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_ids` | string[] | Yes | Comma-separated user IDs (max 20 per API, 100 per CLI) |

## Path Parameters 路径参数

| Parameter | Type | Pattern | Description |
|-----------|------|---------|-------------|
| `workspace_id` | string (UUID) | `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$` | Workspace ID |

## Server-Side Endpoints (common-server) 服务端端点

The server-side controller `WorkspaceController` (`/v1/workspaces`) also exposes legacy
compatibility endpoints:

| Operation | Method | Path | Note |
|-----------|--------|------|------|
| Update workspace (legacy) | PUT | `/v1/workspaces` | Body contains `workspace_id`; marked "兼容前端，待删除" |
| Add members (legacy) | POST | `/v1/workspaces/members` | Body contains `workspace_id` |
| Update member (legacy) | PUT | `/v1/workspaces/members` | Body contains `workspace_id` |

**Note:** These legacy endpoints are being phased out. Always use the path-parameterized
versions (`/{workspace_id}/members`) instead.

## Verification 验证

To verify these API paths against the SDK source:

```bash
# Extract all _url() calls from client.py
grep "_url(" $(python -c "import cloudrobo_workspace.client as m; print(m.__file__)")

# Expected output:
# self._url("/v1/workspaces")
# self._url("/v1/workspaces")
# self._url(f"/v1/workspaces/{workspace_id}")
# self._url(f"/v1/workspaces/{workspace_id}")
# self._url(f"/v1/workspaces/{workspace_id}")
# self._url(f"/v1/workspaces/{workspace_id}/members")
# self._url(f"/v1/workspaces/{workspace_id}/members")
# self._url(f"/v1/workspaces/{workspace_id}/members")
# self._url(f"/v1/workspaces/{workspace_id}/members")
# self._url("/v1/workspaces/statistic/overview")
```
