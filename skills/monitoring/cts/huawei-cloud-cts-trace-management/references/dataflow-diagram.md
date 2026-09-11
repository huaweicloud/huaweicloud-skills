# Data Flow Diagram — huawei-cloud-cts-trace-management

## 1. Query & Analyze Flow (R3 — automatic execution)

```mermaid
flowchart LR
    A[User request] --> B{Intent classification}
    B -->|query| C[huawei_list_cts_* actions]
    B -->|analyze| D[huawei_analyze_cts_* actions]
    C --> E[hcloud CLI: ListTrackers / ListTraces /<br/>ListOperations / ListNotifications / ListTraceResources]
    D --> F[hcloud CLI: ListTraces / ListTrackers]
    E --> G[Raw JSON results]
    F --> H[Local aggregation / retention evaluation]
    G --> I[Structured result to user]
    H --> I
```

## 2. Tracker Lifecycle (manage — R2/R1, preview + confirm)

```mermaid
flowchart LR
    A[User requests create/delete tracker] --> B{Tracker exists?}
    B -->|check| C[ListTrackers]
    C -->|no tracker| D{huawei_create_cts_tracker}
    D --> E{OBS bucket ready?}
    E -->|no| F[Create/confirm OBS bucket first - FAIL fast]
    E -->|yes| G[Preview exact command]
    G --> H{User confirms?}
    H -->|no| I[Abort - no changes]
    H -->|yes| J[CreateTracker with obs_info / is_lts_enabled /<br/>is_organization_tracker flags]
    B -->|data tracker to delete| K[Preview DeleteTracker command]
    K --> L{User confirms?}
    L -->|no| I
    L -->|yes| M[DeleteTracker - data tracker only]
    J --> N[Verify: ListTrackers]
    M --> N
    N --> O[Report result]
```

## 3. Retention & Compliance Analysis

```mermaid
flowchart LR
    A[ListTrackers] --> B{is_lts_enabled?}
    B -->|true| C[LTS long retention - compliant]
    B -->|false| D{obs_info.bucket_name set?}
    D -->|true| E[OBS delivery - check bucket_lifecycle]
    D -->|false| F[7-day default retention - TRAp: advise LTS/OBS]
    C --> G[Retention report]
    E --> G
    F --> G
```

> **Organization tracker:** if org-level cross-account auditing is requested, the tracker must be
> created with `--is_organization_tracker=true`; a normal tracker only covers the current account.