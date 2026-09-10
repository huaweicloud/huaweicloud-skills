# Dataflow Diagram

## High-Level Architecture

```mermaid
flowchart TD
    User[User Request] --> Trigger[Skill Trigger Matching]
    Trigger --> Route[Capability Domain Routing]
    Route --> CLI[cloudrobo robot CLI]
    CLI --> RobotPkg[cloudrobo-robot SDK]
    RobotPkg --> RobotAPI[cloudrobo-service API /v1/robots]
    RobotAPI --> OBS[(OBS Storage: certificates, SDK packages)]
    RobotCRUD[robot CRUD]
    CertAPI[certificate/export]
    SDKAPI[GET /v1/robots/sdk]
```

## Robot Registration Dataflow

```mermaid
flowchart LR
    subgraph Prepare
        P1[Select workspace<br/>workspace list/use] --> P2[Choose type<br/>HUMANOID/QUADRUPED/...]
        P2 --> P3[Collect manufacturer + robot_model]
    end
    subgraph Execute
        E1[Create robot<br/>POST /v1/robots<br/>RobotDto] --> E2[robot_id returned]
        E2 --> E3[Verification<br/>robot show]
    end
    subgraph Consume
        X1[Later referenced by<br/>dispatch as robot_id]
    end
    P3 --> E1
    E3 --> X1
```

## Certificate Export Dataflow

```mermaid
flowchart TD
    Start[User requests access config / certificate<br/>下载/导出配置文件] --> Cmd[robot export-certificate<br/>--robot-id [--password] --output <directory>]
    Cmd --> ShowRobot[show_robot<br/>get robot name]
    ShowRobot --> Validate[validate_safe_id<br/>robot_id path check]
    Validate --> API[POST /v1/robots/{robot_id}/certificate/export<br/>body: {password, optional}]
    API --> Binary[Access-config zip binary returned]
    Binary --> Write[CLI auto-generates filename<br/>cert_config_{name}_{timestamp}.zip<br/>writes to --output directory in wb mode]
    Write --> Done[Access-config zip on disk - store securely]
```

## SDK Upgrade Dataflow

```mermaid
flowchart TD
    Start[User needs robot SDK] --> Cmd[robot show-sdk]
    Cmd --> API[GET /v1/robots/sdk]
    API --> Info[file_name / version / signed_url]
    Info --> Download[Download via signed_url]
    Download --> Upgrade[Upgrade robot client SDK]
```

## Cross-Module Dataflow (dispatch + asset + workspace)

```mermaid
flowchart LR
    subgraph robot
        R1[Register robot<br/>robot create] --> R2[robot_id]
    end
    subgraph workspace
        W1[Select workspace<br/>workspace use] --> W2[workspace_id]
    end
    subgraph dispatch
        D1[create-task<br/>robot_id + exec_model_id] --> D2[task_id]
        D2 --> D3[show-task / show-task-result]
    end
    subgraph asset
        A1[model asset<br/>asset list-assets] --> A2[model_id]
    end
    W2 --> R1
    R2 --> D1
    A2 --> D1
```

> Robot registration produces the `robot_id` consumed by the dispatch module to target a physical
> robot. The workspace_id comes from the workspace skill; model IDs come from the asset skill.
