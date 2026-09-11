# Data Flow Diagram — huawei-cloud-deployment-task-management

## 1. Query & Analyze Flow (R3 — automatic execution)

```mermaid
flowchart LR
    A[User request] --> B{Intent classification}
    B -->|query| C[huawei_list_clouddeploy_apps / tasks / get task]
    B -->|analyze| D[huawei_analyze_clouddeploy_failure / artifact]
    C --> E[hcloud CodeArtsDeploy: ListAllApp / ListDeployTasks /<br/>ShowDeployTaskDetail]
    D --> F[hcloud CodeArtsDeploy: ListDeployTaskHistoryByDate /<br/>ShowDeployTaskDetail + hcloud obs ls]
    E --> G[Raw JSON results]
    F --> H[Root-cause or artifact evaluation]
    G --> I[Structured result to user]
    H --> I
```

## 2. Application & Task Lifecycle (manage — R2/R1, preview + confirm)

```mermaid
flowchart LR
    A[User requests create/start/delete] --> B{Operation type}
    B -->|create app| C[CheckIsDuplicateAppName pre-check]
    C -->|duplicate| C2[Advise another name - FAIL fast]
    C -->|unique| D{huawei_create_clouddeploy_app}
    B -->|create task| E{App/project exists?}
    E -->|no| E2[Create application first - FAIL fast]
    E -->|yes| F{huawei_create_clouddeploy_task}
    B -->|start| G{Tasks running on same hosts?}
    G -->|yes| G2[Advise serializing - parallel conflict trap]
    G -->|no| H{huawei_start_clouddeploy_task}
    B -->|delete| I{huawei_delete_clouddeploy_task}
    D --> J[Preview exact command]
    F --> J
    H --> J
    I --> J
    J --> K{User confirms?}
    K -->|no| L[Abort - no changes]
    K -->|yes| M[Execute CLI operation]
    M --> N[Verify: ListAllApp / ListDeployTasks / history]
    N --> O[Report result]
```

## 3. Failure Root-Cause Analysis

```mermaid
flowchart LR
    A[ListDeployTaskHistoryByDate] --> B{Latest record failed?}
    B -->|no| C[Report success/status]
    B -->|yes| D{Check execution log}
    D -->|host/agent offline| E[Verify host agent installed & online]
    D -->|timeout| F[Check artifact size, task timeout, host resources]
    D -->|artifact missing| G[huawei_analyze_clouddeploy_artifact: OBS bucket/object]
    D -->|permission denied| H[Check IAM policy + host permissions]
    E --> I[Actionable advice to user]
    F --> I
    G --> I
    H --> I
```

## 4. Artifact Link Verification

```mermaid
flowchart LR
    A[ShowDeployTaskDetail] --> B{Artifact source}
    B -->|OBS| C[Parse bucket + object path]
    C --> D[hcloud obs ls obs://bucket/object]
    D -->|object exists| E[Artifact OK]
    D -->|missing| F[Advise re-upload or fix task path]
    D -->|access denied| G[Check bucket policy + GetObject permission]
    B -->|other source| H[Advise checking the configured source]