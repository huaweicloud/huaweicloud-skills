# API Paths API路径

## Source 来源

All API paths are derived from **SDK source code** (`cloudrobo_asset.client`)
via `_url()` calls. This is trusted source #1 per the Huawei Cloud Skill Creator specification.
No paths are inferred or guessed.

## Base Path 基础路径

```
Service: cloudrobo-asset-manager
Base URL: https://cloudrobo-gallery.{region}.myhuaweicloud.com
```

## Endpoint List 端点列表

### Repositories 仓库

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| List repositories | GET | `/v1/repositories` | `list_repositories()` | client.py:23 |
| List catalogs | GET | `/v1/catalogs?repository_id=` | `list_catalogs()` | client.py:26 |
| Show catalog | GET | `/v1/catalogs/{catalog_id}` | `show_catalog()` | client.py:30 |

### Assets 资产

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| Create asset | POST | `/v1/assets` | `create_asset()` | client.py:34 |
| List assets | GET | `/v1/assets` | `list_assets()` | client.py:39 |
| Show asset | GET | `/v1/assets/{asset_id}` | `show_asset()` | client.py:49 |
| Update asset | PUT | `/v1/assets/{asset_id}` | `update_asset()` | client.py:43 |
| Delete asset | DELETE | `/v1/assets/{asset_id}` | `delete_asset()` | client.py:46 |
| Batch delete assets | POST | `/v1/assets/batch-delete` | `batch_delete_assets()` | client.py:52 |

### Versions 版本

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| Create version | POST | `/v1/assets/{asset_id}/versions` | `create_asset_version()` | client.py:56 |
| List versions | GET | `/v1/assets/{asset_id}/versions` | `list_asset_versions()` | client.py:59 |
| Show version | GET | `/v1/assets/{asset_id}/versions/{version_id}` | `show_asset_version()` | client.py:62 |
| Update version | PUT | `/v1/assets/{asset_id}/versions/{version_id}` | `update_asset_version()` | client.py:66 |
| Delete version | DELETE | `/v1/assets/{asset_id}/versions/{version_id}` | `delete_asset_version()` | client.py:69 |
| Batch delete versions | POST | `/v1/assets/{asset_id}/versions/batch-delete` | `batch_delete_asset_versions()` | client.py:72 |

### Tags 标签

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| Add tags | POST | `/v1/assets/{asset_id}/tags` | `add_tags()` | client.py:75 |
| Delete tag | DELETE | `/v1/assets/{asset_id}/tags/{tag}` | `delete_tag()` | client.py:79 |
| List predefined tags | GET | `/v1/asset-tags` | `list_all_tags()` | client.py:110 |

### Actions

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| List actions | GET | `/v1/assets/{asset_id}/versions/{version_id}/actions` | `list_asset_actions()` | client.py:88 |
| Create action | POST | `/v1/assets/{asset_id}/versions/{version_id}/actions` | `create_asset_action()` | client.py:91 |
| Show action | GET | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` | `show_asset_action()` | client.py:95 |
| Update action | PUT | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` | `update_asset_action()` | client.py:98 |
| Delete action | DELETE | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` | `delete_asset_action()` | client.py:101 |

### Permission & Lineage 权限与血缘

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| Check permission | POST | `/v1/assets/{asset_id}/versions/{version_id}/check-permission` | `check_asset_permission()` | client.py:85 |
| Show lineage | GET | `/v1/assets/{asset_id}/versions/{version_id}/tree?type=` | `show_asset_tree()` | client.py:82 |

### Marketplace 广场

| Operation | Method | Path | SDK Method | Source Line |
|-----------|--------|------|------------|-------------|
| Search assets | POST | `/v1/asset-service/search` | `search_assets()` | client.py:104 |
| List publication assets | GET | `/v1/asset-service/publication-assets` | `list_publication_assets()` | client.py:107 |

## Composite Operations 复合操作

### Import Asset 导入资产

`import_asset()` is a composite operation combining multiple API calls:

| Step | Method | Path | SDK Method |
|------|--------|------|------------|
| 1a. Create asset (no asset_id) | POST | `/v1/assets` | `create_asset()` |
| 1b. Create version (with asset_id) | POST | `/v1/assets/{asset_id}/versions` | `create_asset_version()` |
| 1c. Verify asset+version (asset_id + version_id) | GET | `/v1/assets/{asset_id}` + `/v1/assets/{asset_id}/versions/{version_id}` | `show_asset()` + `show_asset_version()` |
| 2. Get version detail | GET | `/v1/assets/{asset_id}/versions/{version_id}` | `show_asset_version()` |
| 3. Upload to OBS | — | OBS SDK | `OBSClient.upload_folder(overwrite=...)` |
| 4. Conditional status update | GET + PUT | `/v1/assets/{asset_id}/versions/{version_id}` | `show_asset_version()` → if status=CREATING → `update_asset_version({status: DRAFT})` |

### Export Asset 导出资产

`export_asset()` is a composite operation:

| Step | Method | Path | SDK Method |
|------|--------|------|------------|
| 1. List versions | GET | `/v1/assets/{asset_id}/versions` | `list_asset_versions()` |
| 2. Resolve version | — | — | `_resolve_version()` |
| 3. Get version detail | GET | `/v1/assets/{asset_id}/versions/{version_id}` | `show_asset_version()` |
| 4. Download from OBS | — | OBS SDK | `OBSClient.download_folder()` |

## Query Parameters 查询参数

### List Assets

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repository_id` | string | Yes (or catalog_id) | Repository ID |
| `catalog_id` | string | Yes (or repository_id) | Catalog ID |
| `type` | string | No | Asset type filter |
| `sub_type` | string | No | Sub-type filter |
| `status` | string | No | Status list (comma-separated) |
| `name` | string | No | Fuzzy name match |
| `exact_name` | string | No | Exact name match (overrides `name`) |
| `tags` | string | No | Tag list (comma-separated) |
| `tags_operator` | string | No | Multi-tag logic (and/or) |
| `offset` | int | No | Pagination offset (default 0) |
| `limit` | int | No | Page size (default 100) |

### List Publication Assets

Same parameters as List Assets, plus:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `capabilities` | string | No | Capability filter (training/inference/reinforcement_learning) — model type only |

### Search Assets

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | Yes | Search keyword |
| `type` | string | No | Type filter (simulation/model/dataset) |
| `limit` | int | No | Result limit (default 10) |
| `offset` | int | No | Result offset (default 0) |

## Verification 验证

To verify these API paths against the SDK source:

```bash
# Extract all _url() calls from client.py
grep "_url(" $(python -c "import cloudrobo_asset.client as m; print(m.__file__)")

# Expected output:
# self._url("/v1/repositories")
# self._url("/v1/catalogs")
# self._url(f"/v1/catalogs/{catalog_id}")
# self._url("/v1/assets")
# self._url(f"/v1/assets/{asset_id}")
# self._url("/v1/assets/batch-delete")
# self._url(f"/v1/assets/{asset_id}/versions")
# self._url(f"/v1/assets/{asset_id}/versions/{version_id}")
# self._url(f"/v1/assets/{asset_id}/versions/batch-delete")
# self._url(f"/v1/assets/{asset_id}/tags")
# self._url(f"/v1/assets/{asset_id}/tags/{tag}")
# self._url(f"/v1/assets/{asset_id}/versions/{version_id}/tree")
# self._url(f"/v1/assets/{asset_id}/versions/{version_id}/check-permission")
# self._url(f"/v1/assets/{asset_id}/versions/{version_id}/actions")
# self._url(f"/v1/assets/{asset_id}/versions/{version_id}/actions/{action}")
# self._url("/v1/asset-service/search")
# self._url("/v1/asset-service/publication-assets")
# self._url("/v1/asset-tags")
```
