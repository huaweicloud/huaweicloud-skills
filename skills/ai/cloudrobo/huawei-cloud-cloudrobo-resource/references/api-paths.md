# API Paths API路径

## Source 来源

All API paths are derived from **SDK source code** (`cloudrobo_resource.client`)
via `_url()` calls. This is trusted source #1 per the Huawei Cloud Skill Creator specification.
No paths are inferred or guessed.

## Base Path 基础路径

```
Service: cloudrobo-service
Base URL: https://cloudrobo.{region}.myhuaweicloud.com
```

## Endpoint List 端点列表

### Quota Query 配额查询

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| List quotas | GET | `/v1/resources/quotas` | `list_quotas()` |

### Resource Pool Query 资源池查询

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| List pools | GET | `/v1/resources/pools` | `list_pools()` |
| Show pool | GET | `/v1/resources/pools/{pool_id}` | `show_pool()` |

## Query Parameters 查询参数

### List Quotas

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace_id` | string (UUID) | No | Workspace ID filter |
| `resource_id` | string (UUID) | No | Resource ID filter |
| `resource_type` | enum (CCE/MODELARTS) | No | Resource type filter |
| `resource_sub_type` | enum (CPU/GPU/STANDARD/LITE) | No | Resource sub-type filter |
| `pool_type` | enum (DEDICATED/SHARED) | No | Pool type filter |
| `limit` | int (1-50) | No | Max results (default 10) |
| `offset` | int (≥0) | No | Pagination offset (default 0) |
| `order` | enum (ASC/DESC) | No | Sort order (default DESC) |

### List Pools

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource_type` | enum (CCE/MODELARTS) | No | Resource type filter |
| `resource_sub_type` | enum (CPU/GPU/STANDARD/LITE) | No | Resource sub-type filter |
| `pool_type` | enum (DEDICATED/SHARED) | No | Pool type filter |
| `usages` | string[] | No | Usage list filter |
| `limit` | int (1-50) | No | Max results (default 10) |
| `offset` | int (≥0) | No | Pagination offset (default 0) |
| `order` | enum (ASC/DESC) | No | Sort order (default DESC) |

## Path Parameters 路径参数

| Parameter | Type | Pattern | Description |
|-----------|------|---------|-------------|
| `pool_id` | string (UUID) | UUID pattern | Resource pool ID |

## Server-Side Controller 服务端Controller

| Controller | Base Path | Endpoints |
|------------|-----------|-----------|
| `QuotaController` | `/v1/resources` | 3 endpoints (quotas list, pools list, pools show) |

## Verification 验证

```bash
# Extract all _url() calls from client.py
grep "_url(" $(python -c "import cloudrobo_resource.client as m; print(m.__file__)")

# Expected output:
# self._url("/v1/resources/quotas")
# self._url("/v1/resources/pools")
# self._url(f"/v1/resources/pools/{pool_id}")
```
