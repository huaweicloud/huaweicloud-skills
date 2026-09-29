# Data Flow Diagram — huawei-cloud-codearts-pipeline-diagnose

## 1. Query Flow (R3 — automatic execution)

```mermaid
flowchart LR
    A[User request] --> B{Intent classification}
    B -->|list pipelines| C[huawei_list_pipelines]
    B -->|list build tasks| D[huawei_list_build_tasks]
    B -->|get pipeline| E[huawei_get_pipeline]
    B -->|get build task| F[huawei_get_build_task]
    B -->|get build log| G[huawei_get_build_log]
    C --> C1[hcloud CodeArtsPipeline ListPipelines]
    D --> D1[hcloud CodeArtsBuild ListProjectJobs]
    E --> E1[hcloud CodeArtsPipeline ShowPipelineDetail / ShowPipelineRunDetail]
    F --> F1[hcloud CodeArtsBuild ShowBuildDetails / ShowBuildRecord]
    G --> G1[hcloud CodeArtsBuild DownloadBuildLog / DownloadBuildRealTimeLog]
    C1 & D1 & E1 & F1 & G1 --> H[Raw JSON results]
    H --> I[Structured result to user]
```

## 2. Analyze Flow (R3 — automatic execution)

```mermaid
flowchart LR
    A[User: pipeline/build failed] --> B{Which domain?}
    B -->|build| C[huawei_diagnose_build_failure]
    B -->|pipeline| D[huawei_diagnose_pipeline_failure]
    B -->|extract errors| E[huawei_extract_build_log_errors]
    C --> C1[ListBuildInfoRecordByJobId / ShowBuildRecord]
    C1 --> C2[DownloadBuildLog]
    C2 --> C3[Classify: network / parameter / load / code / dependency / permission]
    D --> D1[ShowPipelineRunDetail / ListPipelineRuns]
    D1 --> D2{Orchestration or execution error?}
    D2 -->|stages not executed / manual gate| D3[Check definition + trigger conditions]
    D2 -->|job failed| D4[ShowPipelineLog → classify like build failure]
    E --> E1[DownloadBuildLog / DownloadBuildRealTimeLog]
    E1 --> E2[Match error-pattern catalog]
    C3 & D3 & D4 & E2 --> F[Root-cause + actionable advice]
    F --> G[Structured result to user]
```

## 3. Manage Flow (R2/R1 — preview + confirm)

```mermaid
flowchart LR
    A[User requests create/start/delete] --> B{Operation type}
    B -->|create pipeline| C{huawei_create_pipeline}
    B -->|create build task| D{huawei_create_build_task}
    B -->|start pipeline| E{Check latest run state}
    B -->|start build task| F{Check conflicting run}
    B -->|delete pipeline| G{huawei_delete_pipeline}
    B -->|delete build task| H{huawei_delete_build_task}
    C --> J[Preview exact command + effect]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
    J --> K{User confirms?}
    K -->|no| L[Abort - no changes]
    K -->|yes| M[Execute CLI operation]
    M --> N[Verify: ListPipelines / ListProjectJobs / run detail]
    N --> O[Report result]
```

## 4. Failure Root-Cause Analysis (build)

```mermaid
flowchart LR
    A[ListBuildInfoRecordByJobId / ShowBuildRecord] --> B{Record failed?}
    B -->|no| C[Report success/status]
    B -->|yes| D[DownloadBuildLog]
    D --> E{Error pattern match}
    E -->|network| N1[Check connectivity/DNS/timeout]
    E -->|parameter| N2[Check build params/scm refs/config]
    E -->|load| N3[Check flavor/limits/timeout]
    E -->|code/dependency/permission| N4[Fix code / repo creds / IAM]
    N1 & N2 & N3 & N4 --> F[Actionable advice to user]
```