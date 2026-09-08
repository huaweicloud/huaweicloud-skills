# Dataflow Diagram 数据流图

## Architecture Overview 架构概览

```mermaid
graph TB
    subgraph "Client Layer 客户端层"
        CLI[cloudrobo resource CLI]
        SDK[ResourceClient SDK]
    end

    subgraph "Core Layer 核心层"
        Config[Config<br/>~/.cloudrobo/config.yaml]
        HTTP[HttpClient<br/>APIG HMAC-SHA256]
        Base[BaseClient<br/>SERVICE=cloudrobo-service]
    end

    subgraph "Backend Layer 后端层"
        CS[cloudrobo-service<br/>common-server]
        QC[QuotaController<br/>/v1/resources]
    end

    subgraph "External 外部"
        ENV[Environment Variables<br/>HUAWEI_CLOUD_AK/SK]
        WS[~/.cloudrobo/workspace.json<br/>active workspace context]
    end

    ENV --> Config
    Config --> HTTP
    HTTP --> Base

    CLI --> Base
    SDK --> Base

    Base -->|REST API| QC
    QC -->|query| CS

    WS -->|workspace_id| CLI
    Base -->|JSON output| CLI
    Base -->|Dict return| SDK
```

## Quota Query Flow 配额查询流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-service
    participant DB as Database

    Agent->>CLI: resource list-quotas
    CLI->>SDK: list_quotas(**params)
    SDK->>API: GET /v1/resources/quotas
    API->>DB: query quotas by domain_id
    API->>API: aggregate Domain-level quotas
    API-->>SDK: domain_quotas + quotas + page_info
    SDK-->>CLI: quota list
    CLI-->>Agent: JSON output

    Agent->>CLI: resource list-quotas --resource-type CCE
    CLI->>SDK: list_quotas(resource_type='CCE')
    SDK->>API: GET /v1/resources/quotas?resource_type=CCE
    API-->>SDK: CCE quotas (npu=0)
    SDK-->>Agent: CCE quota list
```

## Resource Pool Query Flow 资源池查询流程

```mermaid
sequenceDiagram
    participant Agent
    participant CLI
    participant SDK
    participant API as cloudrobo-service

    Agent->>CLI: resource list-pools
    CLI->>SDK: list_pools(**params)
    SDK->>API: GET /v1/resources/pools
    API-->>SDK: resources + page_info
    SDK-->>Agent: pool list

    Agent->>CLI: resource list-pools --resource-type MODELARTS --resource-sub-type STANDARD
    CLI->>SDK: list_pools(resource_type='MODELARTS', resource_sub_type='STANDARD')
    SDK->>API: GET /v1/resources/pools?resource_type=MODELARTS&resource_sub_type=STANDARD
    API-->>SDK: filtered resources
    SDK-->>Agent: filtered pool list

    Agent->>CLI: resource show-pool --pool-id <resource_id from list-pools>
    CLI->>SDK: show_pool(resource_id)
    SDK->>API: GET /v1/resources/pools/{resource_id}
    API-->>SDK: ResourceVo with nodes
    SDK-->>Agent: pool detail
```

## API Path Summary API路径汇总

| Operation | Method | Path |
|-----------|--------|------|
| List quotas | GET | `/v1/resources/quotas` |
| List pools | GET | `/v1/resources/pools` |
| Show pool | GET | `/v1/resources/pools/{pool_id}` |
