# Dataflow Diagram 数据流图

## Custom Workflow 自定义工作流

```mermaid
flowchart LR
    A[用户目标与输入数据] --> B[查询内置算子 / 空间算法]
    B --> C[用户选择算子和顺序]
    C --> D[核对输入输出兼容性 / 选择最终产物来源]
    D --> E[导出配置和预览]
    E --> F[确认执行计划]
    F --> G[按声明的 DAG 执行 / Web 监控]
    G --> H[核实选定产物和评测报告]
```

无明确需求时从目标开始提问，保留空白草案。以下编号阶段仅展示可主动选择的内置模板，
不能由这些示意图推导出所有自定义工作流都要转换、清洗或评测。

## Built-in Template Overview 内置模板总览

```mermaid
flowchart TD
    subgraph S0[Stage 0: Pipeline Parsing 管线解析]
        A0{Source of definition?}
        A0 -->|Explicit template request| A1[Load templates/sim-teleop-cleaning.yaml]
        A0 -->|User pipeline.yaml| A2[Parse user YAML]
        A1 --> A3[Build stage DAG<br/>depends_on / parallel_group]
        A2 --> A3
        A3 --> A4[Discover operators<br/>list-publication-assets]
        A4 --> A5{All required operators found?}
        A5 -->|No| AX[Stop and tell the user<br/>never substitute]
        A5 -->|Yes| A6[Show execution plan<br/>wait for user confirmation]
    end

    subgraph S1[Stage 1: Upload & Register 上传与注册]
        B0{source_type}
        B0 -->|asset| B1[list-assets / list-versions<br/>show-version]
        B0 -->|obs| B2[create-asset + create-version]
        B0 -->|local| B3[import-asset --local-path]
        B1 --> B4[show-version: verify version/path<br/>DRAFT can proceed when supported]
        B2 --> B4
        B3 --> B4
    end

    subgraph S2[Stage 2: Conversion 格式转换 — convert-lerobotv3]
        C1[dataset proc create-task<br/>--algo-type PRESET_ASSETS] --> C2[dataset proc wait-task]
        C2 --> C3[dataset proc show-task<br/>target_path / target_asset_id]
    end

    subgraph S3[Stage 3: Cleaning 数据清洗 — cleaning]
        D1[dataset proc create-task] --> D2[dataset proc wait-task]
        D2 --> D3[dataset proc show-task<br/>target_path = TrainingReady path]
    end

    subgraph S4[Stage 4: Evaluation 数据评测 — parallel_group, fail_fast false]
        E1[eval create-task<br/>quality-eval] --> E3[eval wait-task × 2]
        E2[eval create-task<br/>diversity-eval] --> E3
        E3 --> E4[eval show-task<br/>target_report_path]
    end

    subgraph S5[Stage 5: Output 输出]
        F1[Pipeline summary<br/>references/pipeline-summary-template.md]
    end

    A6 --> B0
    B4 -->|dataset_configs: obs_path / asset_id / asset_name / version_id| C1
    C3 -->|list-versions + show-version<br/>→ cleaning dataset_configs| D1
    D3 -->|exact version + show-version<br/>→ eval top-level fields + dataset_configs.version_id| E1
    D3 --> E2
    E4 -->|get-preview report links| F1
    D3 -->|TrainingReady data path| F1
```

> **Partial pipeline**: when the user already has converted data, the run starts at
> Stage 3 with a user-supplied `target_path` / `target_asset_id` / `version_id` and asset name.

## Stage Submit / Poll / Handoff Sequence 提交-轮询-交接时序

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant CLI as cloudrobo CLI
    participant AM as cloudrobo-asset-manager
    participant API as cloudrobo-service
    participant OBS as Object Storage

    Agent->>CLI: asset list-publication-assets --type algorithm --tags "Data Processing" --name <fragment>
    CLI->>AM: GET /v1/asset-service/publication-assets
    AM-->>CLI: operator asset_id / name / ext_metadata (engine, command, inputs, environment_variables)
    CLI-->>Agent: current operator info (never reused from a previous run)

    Agent->>User: Execution plan (operators, envs, inputs, specs, pool, output names)
    User-->>Agent: Confirm

    Agent->>CLI: dataset proc create-task --name <pipeline>-convert-lerobotv3-<ts> --algo-type PRESET_ASSETS --task-config '<json>'
    CLI->>CLI: validate required fields (task config validation error if missing/empty)
    CLI->>API: POST /v1/data-eng/proc-tasks
    API-->>CLI: task_id
    CLI-->>Agent: task_id (recorded in checkpoint)

    Agent->>CLI: dataset proc wait-task --task-id <id> --timeout 300
    loop Poll until SUCCEEDED / FAILED / DELETED or timeout
        CLI->>API: GET /v1/data-eng/proc-tasks/{task_id}
        API-->>CLI: status
    end
    API->>OBS: write converted LeRobotV3 data
    CLI-->>Agent: final status (re-run wait-task if still non-terminal)

    Agent->>CLI: dataset proc show-task --task-id <id>
    CLI->>API: GET /v1/data-eng/proc-tasks/{task_id}
    API-->>Agent: target_path + target_asset_id

    Agent->>CLI: asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc --limit 1
    CLI->>AM: GET /v1/assets/{asset_id}/versions
    AM-->>Agent: version_id
    Agent->>CLI: asset show-version --asset-id <target_asset_id> --version-id <version_id>
    CLI->>AM: GET /v1/assets/{asset_id}/versions/{version_id}
    AM-->>Agent: version status + url

    opt Established downstream RELEASE requirement and user-confirmed publication
        Agent->>CLI: asset update-version --status RELEASE
        CLI->>AM: PUT /v1/assets/{asset_id}/versions/{version_id}
    end

    Note over Agent,API: Cleaning repeats create-task → wait-task → show-task → list-versions / show-version<br/>with dataset_configs built from the conversion output

    par quality-eval
        Agent->>CLI: dataset eval create-task --name <pipeline>-quality-eval-<ts> --task-config '<json>'
        CLI->>API: POST /v1/data-eng/eval-tasks
        API-->>Agent: quality eval task_id
    and diversity-eval
        Agent->>CLI: dataset eval create-task --name <pipeline>-diversity-eval-<ts> --task-config '<json>'
        CLI->>API: POST /v1/data-eng/eval-tasks
        API-->>Agent: diversity eval task_id
    end
    API->>OBS: read cleaned data (dataset_path = cleaning target_path)

    loop For each eval task_id
        Agent->>CLI: dataset eval wait-task --task-id <id> --timeout <seconds>
        CLI->>API: GET /v1/data-eng/eval-tasks/{task_id}
        API-->>Agent: terminal status
    end

    Agent->>CLI: dataset eval show-task --task-id <id>
    CLI->>API: GET /v1/data-eng/eval-tasks/{task_id}
    API-->>Agent: target_report_path
    Agent->>CLI: dataset eval get-preview --task-id <id> --file-name <report path without obs://bucket/>
    CLI->>API: GET /v1/data-eng/eval-tasks/{task_id}/preview
    API-->>Agent: temporary OBS URL (save promptly)

    Agent->>User: Stage 5 pipeline summary (TrainingReady path = cleaning target_path)
```

## Failure Handling Flow 故障处理流程

```mermaid
flowchart TD
    A[wait-task returns] --> B{Status}
    B -->|SUCCEEDED| C[show-task → hand off artifacts]
    B -->|CREATING / PENDING / RUNNING<br/>timeout reached| D[Report status + elapsed time<br/>re-run wait-task on same task_id]
    D --> A
    B -->|FAILED| E[get-log --is-system true / false<br/>→ get-log --file-name --file-path<br/>or download-log]
    B -->|DELETED| F[No output — confirm with user]
    E --> G[Identify cause<br/>references/fault-recovery.md]
    F --> H
    G --> H{fail_fast?}
    H -->|true: conversion / cleaning| I{User decision}
    H -->|false: evaluation| J{User decision}
    I -->|retry| K[Re-run discovery → rebuild task_config<br/>→ confirm → NEW create-task]
    I -->|terminate| L[Stage 5 summary ❌]
    J -->|retry failed member| K
    J -->|skip| M[Stage 5 summary ⚠️]
    K --> A
```

## CLI Commands and API Paths CLI命令与API路径汇总

### Discovery & Registration 发现与注册 (cloudrobo-asset-manager)

| Stage | CLI command | Method | API path |
|-------|-------------|--------|----------|
| 0, 2–4 | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" \| "Data Evaluation" --name <fragment>` | GET | `/v1/asset-service/publication-assets` |
| 0, 1 | `cloudrobo workspace current` | — | Local config `~/.cloudrobo/workspace.json` (`asset_catalog_id`) |
| 1 (asset) | `cloudrobo asset show-asset --asset-id <id>` | GET | `/v1/assets/{asset_id}` |
| 1 (obs) | `cloudrobo asset create-asset --catalog-id <id> --name <name> --type dataset --ext-metadata <json>` | POST | `/v1/assets` |
| 1 (obs) | `cloudrobo asset create-version --asset-id <id> --url <obs_path>` | POST | `/v1/assets/{asset_id}/versions` |
| 1 (local) | `cloudrobo asset import-asset --catalog-id <id> --type dataset --local-path <dir> --name <name> --ext-metadata '{"annotation_status":true}'` | POST + OBS upload | `/v1/assets`, `/v1/assets/{asset_id}/versions` (composite) |
| 1–4 | `cloudrobo asset list-versions --asset-id <id> --sort-key created_at --sort-dir desc --limit 1` | GET | `/v1/assets/{asset_id}/versions` |
| 1–4 | `cloudrobo asset show-version --asset-id <id> --version-id <vid>` | GET | `/v1/assets/{asset_id}/versions/{version_id}` |
| 1–4 | `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` | PUT | `/v1/assets/{asset_id}/versions/{version_id}` |

### proc-tasks (conversion / cleaning) — cloudrobo-service

| CLI command | Method | API path |
|-------------|--------|----------|
| `cloudrobo dataset proc create-task --name --algo-type --task-config [--workspace-id]` | POST | `/v1/data-eng/proc-tasks` |
| `cloudrobo dataset proc list-tasks [--name <pipeline_name>]` | GET | `/v1/data-eng/proc-tasks` |
| `cloudrobo dataset proc show-task --task-id` | GET | `/v1/data-eng/proc-tasks/{task_id}` |
| `cloudrobo dataset proc wait-task --task-id [--timeout] [--interval]` | GET (polling) | `/v1/data-eng/proc-tasks/{task_id}` |
| `cloudrobo dataset proc get-log --task-id --is-system true\|false` | GET | `/v1/data-eng/proc-tasks/{task_id}/logs` |
| `cloudrobo dataset proc get-log --task-id --file-name --file-path [--all]` | GET | `/v1/data-eng/proc-tasks/{task_id}/logs/{file_name}` |
| `cloudrobo dataset proc download-log --task-id --file-name --file-path` | GET | `/v1/data-eng/proc-tasks/{task_id}/logs/{file_name}/download` |
| `cloudrobo dataset proc get-frames --task-id --prefix` | GET | `/v1/data-eng/proc-tasks/{task_id}/frames?prefix=` |
| `cloudrobo dataset proc get-preview --task-id --file-name` | GET | `/v1/data-eng/proc-tasks/{task_id}/preview` |

### eval-tasks (quality / diversity) — cloudrobo-service

| CLI command | Method | API path |
|-------------|--------|----------|
| `cloudrobo dataset eval create-task --name --task-config [--workspace-id]` (no `--algo-type`) | POST | `/v1/data-eng/eval-tasks` |
| `cloudrobo dataset eval list-tasks [--name <pipeline_name>]` | GET | `/v1/data-eng/eval-tasks` |
| `cloudrobo dataset eval show-task --task-id` | GET | `/v1/data-eng/eval-tasks/{task_id}` |
| `cloudrobo dataset eval wait-task --task-id [--timeout] [--interval]` | GET (polling) | `/v1/data-eng/eval-tasks/{task_id}` |
| `cloudrobo dataset eval get-log --task-id --is-system true\|false` | GET | `/v1/data-eng/eval-tasks/{task_id}/logs` |
| `cloudrobo dataset eval get-log --task-id --file-name --file-path [--all]` | GET | `/v1/data-eng/eval-tasks/{task_id}/logs/{file_name}` |
| `cloudrobo dataset eval download-log --task-id --file-name --file-path` | GET | `/v1/data-eng/eval-tasks/{task_id}/logs/{file_name}/download` |
| `cloudrobo dataset eval get-preview --task-id --file-name [--is-download]` | GET | `/v1/data-eng/eval-tasks/{task_id}/preview` |

> Terminal states for both task types: `SUCCEEDED`, `FAILED`, `DELETED`. `wait-task`
> defaults to `--timeout 300` / `--interval 10`. When the timeout elapses it returns the
> last status without failing, so re-run it on the same `task_id` instead of resubmitting.
