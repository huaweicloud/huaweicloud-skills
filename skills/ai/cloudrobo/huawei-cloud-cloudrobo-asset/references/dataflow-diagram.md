# Dataflow Diagram 数据流图

## Architecture Overview 架构概览

```mermaid
graph TB
    subgraph "Client Layer 客户端层"
        CLI[cloudrobo asset CLI]
        SDK[AssetClient SDK]
    end

    subgraph "Core Layer 核心层"
        Config[Config<br/>~/.cloudrobo/config.yaml]
        HTTP[HttpClient<br/>APIG HMAC-SHA256]
        Auth[AuthManager]
        Base[BaseClient<br/>SERVICE=cloudrobo-asset-manager]
        OBS[OBSClient<br/>obs upload/download]
    end

    subgraph "Backend Layer 后端层"
        AM[cloudrobo-asset-manager<br/>/v1/assets/*]
        AS[asset-service<br/>/v1/asset-service/*]
        AT[asset-tags<br/>/v1/asset-tags]
    end

    subgraph "External 外部"
        ENV[Environment Variables<br/>HUAWEI_CLOUD_AK/SK]
        LocalFS[Local Filesystem<br/>import source / export target]
    end

    ENV --> Config
    Config --> HTTP
    Auth --> HTTP
    HTTP --> Base

    CLI --> Base
    SDK --> Base
    Base --> OBS

    Base -->|REST API| AM
    Base -->|REST API| AS
    Base -->|REST API| AT

    AM -->|OBS URL| OBS
    OBS -->|upload/download| LocalFS
    OBS -->|response| Base
    Base -->|JSON output| CLI
    Base -->|Dict return| SDK
```

## Asset Lifecycle Flow 资产生命周期流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-asset-manager
    participant OBS as Object Storage

    Agent->>CLI: list-repositories
    CLI->>SDK: list_repositories()
    SDK->>API: GET /v1/repositories
    API-->>SDK: repository list
    SDK-->>CLI: JSON
    CLI-->>Agent: repositories

    Agent->>CLI: list-catalogs --repository-id <id>
    CLI->>SDK: list_catalogs(repository_id)
    SDK->>API: GET /v1/catalogs?repository_id=<id>
    API-->>SDK: catalog list
    SDK-->>CLI: JSON
    CLI-->>Agent: catalogs (get catalog_id)

    Agent->>CLI: create-asset --catalog-id --type --name
    CLI->>SDK: create_asset(req)
    SDK->>API: POST /v1/assets
    API-->>SDK: asset_id, latest_version_id
    SDK-->>CLI: asset created
    CLI-->>Agent: asset_id

    Agent->>CLI: show-asset --asset-id
    CLI->>SDK: show_asset(asset_id)
    SDK->>API: GET /v1/assets/{asset_id}
    API-->>SDK: asset detail
    SDK-->>CLI: JSON
    CLI-->>Agent: asset detail

    Agent->>CLI: delete-asset --asset-id
    CLI->>SDK: delete_asset(asset_id)
    SDK->>API: DELETE /v1/assets/{asset_id}
    API-->>SDK: deleted
    SDK-->>CLI: success
    CLI-->>Agent: cleanup done
```

## Import/Export Flow 导入导出流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-asset-manager
    participant OBS as Object Storage
    participant FS as Local Filesystem

    Note over Agent,FS: Import Asset Flow (3 modes)

    Agent->>CLI: import-asset --local-path <path> [--catalog-id ...] [--asset-id ...] [--version-id ...]
    CLI->>FS: Read README.md frontmatter
    FS-->>CLI: frontmatter dict (or empty if missing)
    CLI->>CLI: Resolve parameters (frontmatter > CLI > error)
    CLI->>CLI: Validate ext_metadata (if creating new asset)
    CLI->>SDK: import_asset(catalog_id/asset_id/version_id, local_path, ...)

    alt Mode 1: Create new asset (no asset_id)
        SDK->>API: POST /v1/assets
        API-->>SDK: asset_id, latest_version_id
    else Mode 2: Create new version (asset_id only)
        SDK->>API: GET /v1/assets/{asset_id} (verify asset exists)
        API-->>SDK: asset detail
        SDK->>SDK: validate ext_metadata (if provided, by asset type)
        SDK->>API: POST /v1/assets/{asset_id}/versions
        API-->>SDK: version_id
    else Mode 3: Reuse existing version (asset_id + version_id)
        SDK->>API: GET /v1/assets/{asset_id} (verify asset exists)
        API-->>SDK: asset detail
        SDK->>API: GET /v1/assets/{asset_id}/versions/{version_id} (verify version exists)
        API-->>SDK: version_data
    end

    SDK->>API: GET /v1/assets/{asset_id}/versions/{version_id}
    API-->>SDK: version data (contains obs_url)
    SDK->>OBS: upload_folder(local_path, obs_prefix, overwrite=...)
    OBS-->>SDK: upload success
    SDK->>API: GET /v1/assets/{asset_id}/versions/{version_id} (check status)
    API-->>SDK: version data (status)
    alt status == CREATING
        SDK->>API: PUT /v1/assets/{asset_id}/versions/{version_id} ({status: DRAFT})
        API-->>SDK: updated version
    end
    SDK-->>CLI: version data
    CLI-->>Agent: import result

    Note over Agent,FS: Export Asset Flow

    Agent->>CLI: export-asset --asset-id --local-path [--version-id]
    CLI->>SDK: export_asset(asset_id, local_path, version_id)
    SDK->>API: GET /v1/assets/{asset_id}/versions
    API-->>SDK: versions list
    SDK->>SDK: _resolve_version(versions, version_id)
    SDK->>SDK: _extract_obs_url_from_version(version_data)
    SDK->>SDK: validate local_path not a file (os.path.isfile)
    SDK->>API: GET /v1/assets/{asset_id}
    API-->>SDK: asset detail
    SDK->>API: GET /v1/assets/{asset_id}/versions/{resolved_version_id}
    API-->>SDK: version detail
    SDK->>SDK: os.makedirs(local_path/asset_id, exist_ok=True)
    SDK->>OBS: download_folder(obs_prefix, export_path)
    OBS-->>SDK: download success
    SDK->>FS: Write README.md with frontmatter
    FS-->>SDK: readme_path
    SDK-->>CLI: export result (with readme_path, metadata)
    CLI-->>Agent: export result
```

## Search & Publication Flow 广场搜索流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-asset-manager

    Agent->>CLI: search-assets --keyword <keyword>
    CLI->>SDK: search_assets(req)
    SDK->>API: POST /v1/asset-service/search
    API-->>SDK: search results
    SDK-->>CLI: JSON
    CLI-->>Agent: asset list

    Agent->>CLI: list-publication-assets --type <type>
    CLI->>SDK: list_publication_assets(**params)
    SDK->>API: GET /v1/asset-service/publication-assets
    API-->>SDK: publication assets
    SDK-->>CLI: JSON
    CLI-->>Agent: official/community assets

    Agent->>CLI: show-asset --asset-id <id>
    CLI->>SDK: show_asset(asset_id)
    SDK->>API: GET /v1/assets/{asset_id}
    API-->>SDK: asset detail
    SDK-->>CLI: JSON
    CLI-->>Agent: asset detail
```

## API Path Summary API路径汇总

### Repositories & Catalogs

| Operation | Method | Path |
|-----------|--------|------|
| List repositories | GET | `/v1/repositories` |
| List catalogs | GET | `/v1/catalogs` |
| Show catalog | GET | `/v1/catalogs/{catalog_id}` |

### Assets

| Operation | Method | Path |
|-----------|--------|------|
| Create asset | POST | `/v1/assets` |
| List assets | GET | `/v1/assets` |
| Show asset | GET | `/v1/assets/{asset_id}` |
| Update asset | PUT | `/v1/assets/{asset_id}` |
| Delete asset | DELETE | `/v1/assets/{asset_id}` |
| Batch delete assets | POST | `/v1/assets/batch-delete` |

### Versions

| Operation | Method | Path |
|-----------|--------|------|
| Create version | POST | `/v1/assets/{asset_id}/versions` |
| List versions | GET | `/v1/assets/{asset_id}/versions` |
| Show version | GET | `/v1/assets/{asset_id}/versions/{version_id}` |
| Update version | PUT | `/v1/assets/{asset_id}/versions/{version_id}` |
| Delete version | DELETE | `/v1/assets/{asset_id}/versions/{version_id}` |
| Batch delete versions | POST | `/v1/assets/{asset_id}/versions/batch-delete` |

### Tags

| Operation | Method | Path |
|-----------|--------|------|
| Add tags | POST | `/v1/assets/{asset_id}/tags` |
| Delete tag | DELETE | `/v1/assets/{asset_id}/tags/{tag}` |
| List predefined tags | GET | `/v1/asset-tags` |

### Actions

| Operation | Method | Path |
|-----------|--------|------|
| List actions | GET | `/v1/assets/{asset_id}/versions/{version_id}/actions` |
| Create action | POST | `/v1/assets/{asset_id}/versions/{version_id}/actions` |
| Show action | GET | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` |
| Update action | PUT | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` |
| Delete action | DELETE | `/v1/assets/{asset_id}/versions/{version_id}/actions/{action}` |

### Permission & Lineage

| Operation | Method | Path |
|-----------|--------|------|
| Check permission | POST | `/v1/assets/{asset_id}/versions/{version_id}/check-permission` |
| Show lineage | GET | `/v1/assets/{asset_id}/versions/{version_id}/tree?type=` |

### Marketplace

| Operation | Method | Path |
|-----------|--------|------|
| Search assets | POST | `/v1/asset-service/search` |
| List publication assets | GET | `/v1/asset-service/publication-assets` |
