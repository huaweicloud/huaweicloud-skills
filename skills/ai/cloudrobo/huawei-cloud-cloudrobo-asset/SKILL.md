---
name: huawei-cloud-cloudrobo-asset
description: >
  Manage the full lifecycle of CloudRobo assets — query repositories and catalogs,
  create/list/show/update/delete assets and versions, batch-delete, tag management,
  predefined tag discovery, Action CRUD, permission checks, marketplace search,
  official/community asset listing, asset lineage, and local-to-OBS import/export.
  Triggers include: asset import, asset export, asset version management, tag management,
  Action configuration, permission check, marketplace search, lineage query, repository
  listing, catalog listing, publication asset discovery, 资产管理, 资产导入导出, 版本管理,
  标签管理, Action配置, 权限校验, 广场搜索, 血缘关系, 资产仓库, 目录查询.
tags:
  - huawei-cloud-cloudrobo
  - asset-management
  - version-management
  - import-export
  - marketplace-search
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview 概述

The `cloudrobo-asset` skill manages the full lifecycle of CloudRobo platform assets. It
covers repository and catalog queries, asset CRUD (create/list/show/update/delete/batch-delete),
version CRUD, tag management, Action CRUD, permission checks, marketplace search,
official/community asset listing, asset lineage, and local-to-OBS import/export.

**Applicable scenarios:**

- **Asset lifecycle** — Create, list, show, update, delete, batch-delete assets and versions
- **Import/Export** — Import local folders to OBS as assets; export asset versions to local paths
- **Marketplace discovery** — Search marketplace assets; list official/community publication assets
- **Tag management** — Add/delete tags; query platform predefined tag lists
- **Action management** — Create/list/show/update/delete Actions on asset versions
- **Permission check** — Verify user permissions on asset versions
- **Lineage** — Query parent-child relationships between asset versions

**Architecture:**

```
Agent / LLM
    │
    ├── CLI  →  cloudrobo asset <command>
    ├── SDK  →  AssetClient (Python)
                    │
                    ▼
              cloudrobo-asset-manager (REST API)
              /v1/repositories
              /v1/catalogs
              /v1/assets/*
              /v1/asset-service/search
              /v1/asset-service/publication-assets
              /v1/asset-tags
              │
              ├── OBS (import/export file transfer)
              └── cloudrobo-obs endpoint (configured separately)
```

All operations target the `cloudrobo-asset-manager` backend. Import/export additionally
requires a `cloudrobo-obs` endpoint for OBS file transfer.

## Prerequisites 前置条件

See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
configuration. Import/export operations require the `cloudrobo-obs` endpoint to be configured in
`~/.cloudrobo/config.yaml` or via the `CLOUDROBO_ENDPOINT_cloudrobo-obs` environment variable.

## Workflow 工作流

### Prerequisite: Get catalog_id 前置步骤

Multiple scenarios require a `catalog_id`. Only execute when the user has not provided it:

1. **Get from current workspace (preferred):** `cloudrobo workspace current` → read
   `asset_catalog_id` field (the catalog bound to the current workspace)
2. **Fallback — list repositories and catalogs:** If no workspace is configured or
   `asset_catalog_id` is empty:
   1. `cloudrobo asset list-repositories` → get `repository_id`
   2. `cloudrobo asset list-catalogs --repository-id <repo-id>` → get `catalog_id`

### Scenario 1: Import Local Asset 导入资产

Import local files (models, datasets, etc.) into the CloudRobo asset repository.

**Fast path:** If `local-path/README.md` exists with valid frontmatter (e.g., from a previous
`export-asset`), only `--catalog-id` (for new asset) or `--asset-id` (for new version) is needed
— all other metadata is read from frontmatter. Without frontmatter, `catalog_id`, `name`, `type`
(and `sub_type` for simulation) must be provided via CLI.

1. (Only when creating new asset and catalog_id is missing) Execute "Prerequisite: Get catalog_id"
2. Import:
   ```bash
   # With frontmatter (recommended — after export)
   cloudrobo asset import-asset --catalog-id <id> --local-path <path>
   # Without frontmatter
   cloudrobo asset import-asset --catalog-id <id> --name <name> --type <type> --local-path <path> [--sub-type <sub-type>] [--ext-metadata '{"key":"value"}']
   ```
   - Auto-reads `local-path/README.md` frontmatter for metadata (name, type, sub_type, description,
     status, tags, version, ext_metadata, parent_asset_version_id, generation_method)
   - Frontmatter values override CLI parameters (except catalog_id, CLI only); fields missing from both trigger errors
   - `--ext-metadata` CLI param also supported (frontmatter overrides it)
   - ext_metadata pre-validated by type before API call (model→model_type, dataset→annotation_status,
     algorithm→engine+command, image→arch+device_type, simulation (sub_type=robot)→robot_type+robot_manufacturer)
   - Auto-creates asset + version + uploads to OBS
   - Existing asset new version: add `--asset-id <existing-asset-id>`
   - Reuse existing version for upload retry: add `--asset-id <id> --version-id <vid>` (default: incremental upload — skips existing OBS objects; use `--overwrite` to force re-upload all files)
3. Verify: `cloudrobo asset show-asset --asset-id <asset-id>`

**Error recovery:** If import fails at OBS upload (asset and version created but files not
uploaded, version stays in `CREATING` status), do NOT create a new version. Two recovery strategies:
- **Reuse version (recommended):** `list-versions --asset-id <id>` to find the failed version,
  re-run `import-asset --asset-id <id> --version-id <vid>` to upload directly (incremental by
  default — only uploads missing files; the version transitions to `DRAFT` once upload succeeds)
- **Delete and retry:** `delete-version --asset-id <id> --version-id <vid>` then re-run
  `import-asset --asset-id <id>`

### Scenario 2: Search Marketplace 搜索广场资产

1. Search: `cloudrobo asset search-assets --keyword <keyword>`
2. Show detail: `cloudrobo asset show-asset --asset-id <asset-id>`

**Browse official/community:** `cloudrobo asset list-publication-assets --type <type>`

**Export after search:** Only when the user requests export. If the marketplace asset permission
does not include `data_read`, export is not allowed. `cloudrobo asset export-asset --asset-id <id>
--local-path <path>` (default latest version; add `--version-id` for specific version). Export
automatically generates `README.md` with YAML frontmatter containing asset metadata, enabling
seamless re-import with minimal CLI parameters.

### Scenario 3: List Workspace Assets 列举空间资产

1. (Only when catalog_id is missing) Execute "Prerequisite: Get catalog_id"
2. List: `cloudrobo asset list-assets --catalog-id <catalog-id>`
   - Filter by `--type`, `--sub-type`, `--status`
   - Or use `--repository-id` instead of `--catalog-id` for repository-level queries

### Scenario 4: List Asset Versions 列举资产版本

1. If asset_id is known, skip to step 3
2. (Only when asset_id is missing) Execute "Prerequisite: Get catalog_id", then
   `list-assets --catalog-id <id>` to locate `asset_id`
3. List versions: `cloudrobo asset list-versions --asset-id <asset-id>`

### Scenario 5: Create Asset with ext_metadata 创建含扩展元数据的资产

model, dataset, simulation, algorithm, image types require ext_metadata at creation. Consult
`references/validation-rules.md` for required fields by type.

1. (Only when catalog_id is missing) Execute "Prerequisite: Get catalog_id"
2. Create: `cloudrobo asset create-asset --catalog-id <id> --name <name> --type model --ext-metadata '{"model_type":"planning"}'`
3. Create version: `cloudrobo asset create-version --asset-id <id> --version 1.0.0 --ext-metadata '{"model_type":"planning"}'`

### Scenario 6: Tag Management 标签管理

1. Add: `cloudrobo asset add-tags --asset-id <id> --tags "tag1,tag2"`
2. Delete: `cloudrobo asset delete-tag --asset-id <id> --tag <tag>`
3. Query predefined: `cloudrobo asset list-tags --language zh` (optional `--type`/`--sub-type` filter)

## CLI Command Format Standard CLI命令格式标准

```bash
cloudrobo asset <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Command group | `cloudrobo asset` | `cloudrobo asset list-assets` |
| Subcommand | kebab-case | `list-repositories`, `create-asset`, `import-asset` |
| JSON parameter | `--ext-metadata '{"key":"value"}'` | `--ext-metadata '{"model_type":"planning"}'` |
| Comma list | `--tags tag1,tag2` | `--tags robot,arm` |
| Dry-run | `--dry-run` (where supported) | Preview without executing |
| Output format | JSON to stdout | `out(result)` |
| UUID identifiers | `--asset-id`, `--version-id`, `--catalog-id` | UUID format required |

## Core Commands 核心命令

### Repository & Catalog 仓库与目录

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| list-repositories | `[--name] [--sort-dir] [--offset] [--limit]` | `client.list_repositories(**params)` | `GET /v1/repositories` |
| list-catalogs | `--repository-id <id> [--name] [--sort-dir] [--offset] [--limit]` | `client.list_catalogs(repository_id, **params)` | `GET /v1/catalogs` |
| show-catalog | `--catalog-id <id>` | `client.show_catalog(catalog_id)` | `GET /v1/catalogs/{catalog_id}` |

### Asset Management 资产管理

#### Create asset
```bash
cloudrobo asset create-asset --catalog-id <catalog-id> --type <type> [--name <name>] [--sub-type <sub-type>] [--description <desc>] [--status <status>] [--tags "tag1,tag2"] [--url <obs-or-swr-path>] [--ext-metadata '{"key":"value"}'] [--parent-asset-version-id <uuid>] [--generation-method <method>] [--dry-run]
```
- **SDK:** `client.create_asset(req: dict)`
- **API:** `POST /v1/assets`

#### List assets
```bash
cloudrobo asset list-assets [--repository-id <id>] [--catalog-id <id>] [--type <type>] [--sub-type <sub-type>] [--status <status>] [--name <name>] [--tags "tag1,tag2"] [--mine] [--offset <n>] [--limit <n>]
# Either --repository-id OR --catalog-id filters the list. Full parameter list: see references/api-paths.md → List Assets
```
- **SDK:** `client.list_assets(**params)`
- **API:** `GET /v1/assets`

**Note:** `repository-id` and `catalog-id` — at least one must be provided; both provided =
AND filter.

#### Update asset
```bash
cloudrobo asset update-asset --asset-id <asset-id> [--name <name>] [--description <desc>] [--status <status>] [--tags "tag1,tag2"] [--ext-metadata '{"key":"value"}'] [--dry-run]
```
- **SDK:** `client.update_asset(asset_id, req: dict)`
- **API:** `PUT /v1/assets/{asset_id}`

**Note:** `update-asset` only supports modifying `name`/`description`/`status`/`tags`/
`ext-metadata` — the CLI exposes no parameters for `catalog_id`, `type`, `sub_type`,
`url`, `parent_asset_version_id`, or `generation_method`, so these fields are immutable.

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| show-asset | `--asset-id <id>` | `client.show_asset(asset_id)` | `GET /v1/assets/{asset_id}` |
| delete-asset | `--asset-id <id> [--dry-run]` | `client.delete_asset(asset_id)` | `DELETE /v1/assets/{asset_id}` |
| batch-delete-assets | `--asset-ids "id1,id2" [--dry-run]` | `client.batch_delete_assets({"asset_ids": [...]})` | `POST /v1/assets/batch-delete` |

### Version Management 版本管理

#### Create version
```bash
cloudrobo asset create-version --asset-id <asset-id> [--version <version>] [--description <desc>] [--status <status>] [--url <obs-or-swr-path>] [--ext-metadata '{"key":"value"}'] [--parent-asset-version-id <uuid>] [--generation-method <method>] [--dry-run]
```
- **SDK:** `client.create_asset_version(asset_id, req: dict)`
- **API:** `POST /v1/assets/{asset_id}/versions`

#### List versions
```bash
cloudrobo asset list-versions --asset-id <asset-id> [--version <version>] [--exact-version <version>] [--sort-key <field>] [--sort-dir <asc|desc>] [--offset <n>] [--limit <n>] [--actions "FFT,LORA"] [--actions-operator <and|or>] [--ext-metadata <key=value>] [--action-status "ENABLE,DISABLE"]
```
- **SDK:** `client.list_asset_versions(asset_id, **params)`
- **API:** `GET /v1/assets/{asset_id}/versions`

#### Update version
```bash
cloudrobo asset update-version --asset-id <asset-id> --version-id <version-id> [--version <version>] [--description <desc>] [--status <status>] [--ext-metadata '{"key":"value"}'] [--dry-run]
```
- **SDK:** `client.update_asset_version(asset_id, version_id, req: dict)`
- **API:** `PUT /v1/assets/{asset_id}/versions/{version_id}`

**Note:** `update-version` only supports modifying `version`/`description`/`status`/
`ext-metadata` — the CLI exposes no parameters for `url`, `parent_asset_version_id`, or
`generation_method`, so these fields are immutable.

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| show-version | `--asset-id <id> --version-id <vid>` | `client.show_asset_version(asset_id, version_id)` | `GET /v1/assets/{asset_id}/versions/{version_id}` |
| delete-version | `--asset-id <id> --version-id <vid> [--dry-run]` | `client.delete_asset_version(asset_id, version_id)` | `DELETE /v1/assets/{asset_id}/versions/{version_id}` |
| batch-delete-versions | `--asset-id <id> --version-ids "v1,v2" [--dry-run]` | `client.batch_delete_asset_versions(asset_id, {"version_ids": [...]})` | `POST /v1/assets/{asset_id}/versions/batch-delete` |

### Tag Management 标签管理

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| add-tags | `--asset-id <id> --tags "t1,t2" [--dry-run]` | `client.add_tags(asset_id, tags)` | `POST /v1/assets/{asset_id}/tags` |
| delete-tag | `--asset-id <id> --tag <tag> [--dry-run]` | `client.delete_tag(asset_id, tag)` | `DELETE /v1/assets/{asset_id}/tags/{tag}` |
| list-tags | `--language <zh\|en> [--type] [--sub-type]` | `client.list_all_tags(language, type, sub_type)` | `GET /v1/asset-tags` |

### Action Management Action管理

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| list-actions | `--asset-id <id> --version-id <vid>` | `client.list_asset_actions(asset_id, version_id)` | `GET /v1/assets/{asset_id}/versions/{version_id}/actions` |
| show-action | `--asset-id <id> --version-id <vid> --action <name>` | `client.show_asset_action(asset_id, version_id, action)` | `GET .../actions/{action}` |
| delete-action | `--asset-id <id> --version-id <vid> --action <name> [--dry-run]` | `client.delete_asset_action(asset_id, version_id, action)` | `DELETE .../actions/{action}` |

**Create/Update action** (detailed):
```bash
cloudrobo asset create-action --asset-id <id> --version-id <vid> --action-info '{"action":"FFT","algorithm":{"asset_id":"...","version_id":"..."},"status":"ENABLE"}' [--dry-run]
# SDK: client.create_asset_action(asset_id, version_id, req)
# API: POST /v1/assets/{asset_id}/versions/{version_id}/actions

cloudrobo asset update-action --asset-id <id> --version-id <vid> --action <name> --action-info '{"status":"DISABLE"}' [--dry-run]
# SDK: client.update_asset_action(asset_id, version_id, action, req)
# API: PUT /v1/assets/{asset_id}/versions/{version_id}/actions/{action}
```

### Permission & Lineage 权限与血缘

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| check-permission | `--asset-id <id> --version-id <vid> --permissions "meta_read,data_read"` | `client.check_asset_permission(asset_id, version_id, req)` | `POST .../check-permission` |
| show-lineage | `--asset-id <id> --version-id <vid> --type <children\|parent>` | `client.show_asset_tree(asset_id, version_id, type)` | `GET .../tree?type=<children\|parent>` |

Valid permissions: `meta_read`, `meta_write`, `data_read`, `data_write`, `data_usable`
Lineage: `children` = parent-to-child; `parent` = child-to-parent.

### Marketplace 广场

| Command | Key Params | SDK Method | API |
|---------|-----------|------------|-----|
| search-assets | `--keyword <kw> [--type] [--limit] [--offset]` | `client.search_assets(req)` | `POST /v1/asset-service/search` |
| list-publication-assets | `[--type] [--sub-type] [--name] [--tags] [--status] [--capabilities] [--offset] [--limit]` | `client.list_publication_assets(**params)` | `GET /v1/asset-service/publication-assets` |

Full parameter list: see references/api-paths.md → List Publication Assets

### Import & Export 导入导出

#### Import asset
```bash
cloudrobo asset import-asset --local-path <local-folder> [--catalog-id <id>] [--name <name>] [--type <type>] [--sub-type <sub-type>] [--ext-metadata '{"key":"value"}'] [--asset-id <id>] [--version-id <vid>] [--overwrite] [--dry-run]
```

**Frontmatter support:**
- Auto-reads `local-path/README.md` YAML frontmatter
- Fields: `name`, `type`, `sub_type`, `description`, `status`, `tags`, `version`, `ext_metadata`,
  `parent_asset_version_id`, `generation_method`
- Priority: frontmatter overrides CLI parameters (except catalog_id, CLI only); fields missing from both trigger errors
- Required fields for new asset: `catalog_id` (CLI only), `name` (frontmatter or CLI), `type` (frontmatter or CLI)
- ext_metadata pre-validation: model/dataset/algorithm/image/simulation types validated before API call (robot is a sub_type of simulation)

**Modes:**
- No `--asset-id`: Create new asset + version + upload to OBS; after upload, if version status is `CREATING`, auto-update to `DRAFT`
- `--asset-id` only: Create new version for existing asset + upload to OBS; after upload, if version status is `CREATING`, auto-update to `DRAFT`
- `--asset-id` + `--version-id`: Reuse existing version, incremental upload to OBS only (skips existing OBS objects by default; use `--overwrite` to force re-upload all files); after upload, if version status is `CREATING`, auto-update to `DRAFT`

**Status flow:** When no `--status` is specified, the backend creates the version with status `CREATING`. After a successful OBS upload, if the version status is still `CREATING`, the SDK automatically calls `update-version` to set it to `DRAFT`. If the user explicitly specifies a status (e.g., `RELEASE` via frontmatter), the upload succeeds but the status is not auto-modified.

#### Export asset
```bash
cloudrobo asset export-asset --asset-id <id> --local-path <local-folder> [--version-id <version-id>] [--dry-run]
```

**README.md generation:**
- Creates `<local-path>/<asset-id>/README.md` with YAML frontmatter
- Frontmatter fields: `name`, `type`, `sub_type`, `description`, `status`, `tags`, `version`,
  `ext_metadata`, `parent_asset_version_id`, `generation_method`
- If README.md already exists, preserves body content and replaces frontmatter only
- Enables seamless re-import with minimal CLI parameters

## Parameter Confirmation 参数确认

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--catalog-id` | Conditional (new asset import, most commands) | Catalog UUID | `b2c3d4e5-f6a7-...` |
| `--asset-id` | Yes (asset/version ops) | Asset UUID | `a1b2c3d4-...` |
| `--version-id` | Yes (version ops) | Version UUID | `d4e5f6a7-b8c9-...` |
| `--type` | Conditional (import without frontmatter) | Asset type | `model`, `dataset`, `algorithm`, `image`, `simulation` |
| `--name` | Conditional (import without frontmatter) | Asset name | `my-model` |
| `--sub-type` | Conditional (algorithm/image/simulation) | Asset sub_type | algorithm: `inference`,`data_processing`,`training`,`data_evaluating`,`rl`; image: `inference`,`data_processing`,`training`,`notebook`,`rl`; simulation: `robot`,`environment`,`object`,`scene` |
| `--local-path` | Yes (import/export) | Local folder path | `./my-model` |
| `--ext-metadata` | Conditional (model/dataset/algorithm/image/simulation) | Extended metadata JSON | `{"model_type":"planning"}` |
| `--language` | Yes (list-tags) | Tag language | `zh`, `en` |
| `--permissions` | Yes (check-permission) | Permission list | `meta_read,data_read` |
| `--dry-run` | No | Preview without executing | flag |
| `--description` | No | Asset/version description | `My model description` |
| `--status` | No | Asset/version status | `CREATING`, `DRAFT`, `RELEASE`, etc. |
| `--tags` | No | Tag list (comma-separated, full replacement on update) | `production,stable` |
| `--url` | No | OBS or SWR path (create-asset/create-version only) | `obs://bucket/path` |
| `--generation-method` | No | Asset generation method (create-asset/create-version only) | `manual` |
| `--parent-asset-version-id` | No | Parent version UUID (create-asset/create-version only) | `d4e5f6a7-...` |

**Mutating operations** (create/update/delete/import/export/batch-delete) should be confirmed
by the user before execution. `--dry-run` can be used to preview the operation safely.

## Reference Documents 参考文档

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [API Paths](references/api-paths.md) — REST API paths discovered via SDK source
- [Validation Rules](references/validation-rules.md) — Field validation, ext_metadata rules, parameter interactions
- [Edge Cases](references/edge-cases.md) — Edge cases and error handling

## Edge Cases 边界情况

Key edge cases include: missing catalog_id, import OBS upload failure recovery, export
permission checks, immutable field validation, built-in vs workspace asset distinction,
and `capabilities` filter mapping. See [Edge Cases](references/edge-cases.md) for the
full table.

## Verification Method 验证方法

```bash
# Specification compliance + functional testing
bash scripts/test-cli-commands.sh . --executor {cli|sdk|api}
```

Test cases: see `templates/test-vars.json` for the full list covering all asset operations.

### Verification Checklist 验证清单
- After create/update/import: verify via `show-asset`/`show-version`/`list-actions` that changes took effect
- After list/search/check-permission: verify results match filter criteria and `verdict` contains `allow`/`deny`
- Before delete: confirm with user — deletion is irreversible
- After export: check local directory file structure matches OBS source

## Best Practices 最佳实践

- Use `--dry-run` with create/update/delete/import/export to validate parameters before execution
- Before creating assets with ext_metadata, consult `references/validation-rules.md` for required fields by type
- Use `import-asset` (not `create-asset`) for most scenarios — it handles the full flow (asset + version + OBS upload)
- For failed imports, reuse the existing version with `--asset-id --version-id` to avoid accumulating empty versions
- Query predefined tags via `list-tags` before adding tags to ensure they are valid
- Use `export-asset` followed by `import-asset` for seamless asset migration — export generates
  README.md with frontmatter, import auto-reads it to fill metadata
- For import without frontmatter, provide `--ext-metadata` for model/dataset/simulation types to
  pass pre-validation
