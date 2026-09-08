# Dataflow Diagram 数据流图

## Architecture Overview 架构概览

```mermaid
graph TB
    subgraph "Client Layer 客户端层"
        CLI[cloudrobo workspace CLI]
        SDK[WorkspaceClient SDK]
    end

    subgraph "Core Layer 核心层"
        Config[Config<br/>~/.cloudrobo/config.yaml]
        HTTP[HttpClient<br/>APIG HMAC-SHA256]
        Auth[AuthManager]
        Base[BaseClient<br/>SERVICE=cloudrobo-service]
    end

    subgraph "Backend Layer 后端层"
        CS[cloudrobo-service<br/>common-server<br/>/v1/workspaces]
        AC[AssetCenter<br/>repository + catalog]
        OBS[OBS<br/>bucket policy]
    end

    subgraph "External 外部"
        ENV[Environment Variables<br/>HUAWEI_CLOUD_AK/SK]
        WS[~/.cloudrobo/workspace.json<br/>active workspace context]
    end

    ENV --> Config
    Config --> HTTP
    Auth --> HTTP
    HTTP --> Base

    CLI --> Base
    SDK --> Base

    Base -->|REST API| CS
    CS -->|create catalog| AC
    CS -->|bind policy| OBS
    Base -->|JSON output| CLI
    Base -->|Dict return| SDK

    CLI -->|workspace use| WS
    WS -->|read context| CLI
```

## Onboarding Flow 首次设置流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-service
    participant AC as AssetCenter
    participant OBS as Object Storage
    participant WS as workspace.json

    Agent->>CLI: workspace list
    CLI->>SDK: list_workspaces()
    SDK->>API: GET /v1/workspaces
    API-->>SDK: workspaces + page_info + last_count
    SDK-->>CLI: workspace list
    CLI-->>Agent: existing workspaces (default may exist)

    Agent->>CLI: workspace create --name prod --default-obs-path obs://bucket/prod
    CLI->>SDK: create_workspace(req)
    SDK->>API: POST /v1/workspaces
    API->>API: check name uniqueness + quota
    API->>OBS: bind bucket policy
    API->>AC: create repository + catalog
    AC-->>API: catalog_id
    API->>API: insert DB + add admin + create quota
    API-->>SDK: workspace with workspace_id + asset_catalog_id
    SDK-->>CLI: workspace created
    CLI-->>Agent: workspace_id

    Agent->>CLI: workspace use --workspace-id <id>
    CLI->>SDK: show_workspace(id)
    SDK->>API: GET /v1/workspaces/{id}
    API-->>SDK: workspace detail
    SDK-->>CLI: workspace detail
    CLI->>WS: save {workspace_id, name, asset_catalog_id, default_obs_path}
    CLI-->>Agent: switched to workspace
```

## Workspace CRUD Flow 工作空间CRUD流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-service

    Agent->>CLI: workspace create
    CLI->>SDK: create_workspace(req)
    SDK->>API: POST /v1/workspaces
    API-->>SDK: workspace entity
    SDK-->>Agent: workspace_id

    Agent->>CLI: workspace list --limit 10
    CLI->>SDK: list_workspaces(limit=10)
    SDK->>API: GET /v1/workspaces?limit=10
    API-->>SDK: workspaces + page_info + last_count
    SDK-->>Agent: workspace list

    Agent->>CLI: workspace show --workspace-id <id>
    CLI->>SDK: show_workspace(id)
    SDK->>API: GET /v1/workspaces/{id}
    API-->>SDK: workspace detail
    SDK-->>Agent: full detail

    Agent->>CLI: workspace update --workspace-id <id> --name new
    CLI->>SDK: update_workspace(id, req)
    SDK->>API: PUT /v1/workspaces/{id}
    API-->>SDK: updated workspace
    SDK-->>Agent: updated

    Agent->>CLI: workspace delete --workspace-id <id>
    CLI->>SDK: delete_workspace(id)
    SDK->>API: DELETE /v1/workspaces/{id}
    API->>API: create cleanup tasks (async)
    API-->>SDK: 204 No Content
    SDK-->>Agent: deleted
```

## Member Management Flow 成员管理流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-service
    participant IAM as IAM User Cache

    Agent->>CLI: workspace list-members --workspace-id <id>
    CLI->>SDK: list_workspace_members(id)
    SDK->>API: GET /v1/workspaces/{id}/members
    API->>IAM: resolve user names
    API-->>SDK: members + remain_count
    SDK-->>Agent: member list

    Agent->>CLI: workspace add-members --workspace-id <id> --member-list <json>
    CLI->>SDK: add_workspace_members(id, req)
    SDK->>API: POST /v1/workspaces/{id}/members
    API->>IAM: validate users exist
    API->>API: check duplicates + root user
    API-->>SDK: members added
    SDK-->>Agent: added members

    Agent->>CLI: workspace update-member --workspace-id <id> --user-id <uid> --role-ids <r1>
    CLI->>SDK: update_workspace_member(id, req)
    SDK->>API: PUT /v1/workspaces/{id}/members
    API->>API: validate not owner + check roles
    API-->>SDK: updated member
    SDK-->>Agent: updated

    Agent->>CLI: workspace delete-members --workspace-id <id> --user-ids <u1,u2>
    CLI->>SDK: delete_workspace_members(id, [u1, u2])
    SDK->>API: DELETE /v1/workspaces/{id}/members?user_ids=u1,u2
    API->>API: validate not owner + not default workspace
    API-->>SDK: 204 No Content
    SDK-->>Agent: deleted
```

## Workspace Context Switching Flow 工作空间切换流程

```mermaid
flowchart TD
    A[Agent: workspace use --workspace-id id] --> B[CLI calls show_workspace]
    B --> C{Workspace exists?}
    C -->|No| D[Output: 切换失败 + error]
    C -->|Yes| E[Extract: name, asset_catalog_id, default_obs_path]
    E --> F[Save to ~/.cloudrobo/workspace.json]
    F --> G[chmod 0o600]
    G --> H[Output: 已切换到工作空间]
    H --> I[Other skills read workspace.json]

    J[Agent: workspace current] --> K[Read ~/.cloudrobo/workspace.json]
    K --> L{File exists?}
    L -->|No| M[Output: 未配置工作空间]
    L -->|Yes| N[Output: JSON config]
```

## API Path Summary API路径汇总

### Workspace

| Operation | Method | Path |
|-----------|--------|------|
| Create workspace | POST | `/v1/workspaces` |
| List workspaces | GET | `/v1/workspaces` |
| Show workspace | GET | `/v1/workspaces/{workspace_id}` |
| Update workspace | PUT | `/v1/workspaces/{workspace_id}` |
| Delete workspace | DELETE | `/v1/workspaces/{workspace_id}` |

### Members

| Operation | Method | Path |
|-----------|--------|------|
| Add members | POST | `/v1/workspaces/{workspace_id}/members` |
| List members | GET | `/v1/workspaces/{workspace_id}/members` |
| Update member | PUT | `/v1/workspaces/{workspace_id}/members` |
| Delete members | DELETE | `/v1/workspaces/{workspace_id}/members?user_ids=` |

### Overview

| Operation | Method | Path |
|-----------|--------|------|
| Get overview | GET | `/v1/workspaces/statistic/overview` |
