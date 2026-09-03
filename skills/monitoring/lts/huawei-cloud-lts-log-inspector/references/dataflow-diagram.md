# Data Flow Diagram

## Mermaid Data Flow

```mermaid
graph TD
    User[User Trigger] --> WF{Workflow Type}

    WF -->|Traffic Anomaly| S1[Scenario 1: Traffic Troubleshooting]
    WF -->|Fault Deep-Dive| S2[Scenario 2: Context Query]
    WF -->|Collection Patrol| S3[Scenario 3: Collection Inspection]
    WF -->|Batch Export| S4[Scenario 4: OBS Transfer]
    WF -->|Full Patrol| S5[Scenario 5: Full Report]

    %% Scenario 1
    S1 --> TOPN[ListTopnTrafficStatistics]
    S1 --> TL[ListTimeLineTrafficStatistics]
    S1 --> HG[ListLogHistogram]
    TOPN --> R1[Traffic Anomaly Report]
    TL --> R1
    HG --> R1

    %% Scenario 2
    S2 --> LL[ListLogs]
    LL --> LN[Extract line_num]
    LN --> CTX[ListLogContext]
    CTX --> R2[Context Log Fragments]

    %% Scenario 3
    S3 --> HGL[ListHostGroup]
    S3 --> HOFF[ListHost status=offline]
    S3 --> HERR[ListHost status=error]
    S3 --> AC[ListAccessConfig]
    HGL --> R3[Collection Anomaly Checklist]
    HOFF --> R3
    HERR --> R3
    AC --> R3

    %% Scenario 4
    S4 --> WARN[Cost Risk Warning]
    WARN --> CONF{User Confirms?}
    CONF -->|Yes| CT[CreateTransfer]
    CONF -->|No| ABORT[Abort]
    CT --> LT[ListTransfers]
    LT --> R4[Transfer Status]
    R4 --> DT[Optional: DeleteTransfer]

    %% Scenario 5
    S5 --> TOPN
    S5 --> TL
    S5 --> HGL
    S5 --> HOFF
    S5 --> HERR
    S5 --> AC
    S5 --> R5[Full Patrol Report]

    %% Styling
    classDef query fill:#d4edda,stroke:#28a745
    classDef mutate fill:#fff3cd,stroke:#ffc107
    classDef report fill:#d1ecf1,stroke:#17a2b8
    classDef warn fill:#f8d7da,stroke:#dc3545

    class TOPN,TL,HG,LL,CTX,HGL,HOFF,HERR,AC,LT query
    class CT,DT mutate
    class R1,R2,R3,R4,R5 report
    class WARN,ABORT warn
```

## Data Flow Description

| Flow | Input | Processing | Output |
|------|-------|-----------|--------|
| Traffic Stats | Time range, resource type | TOP-N + Timeline + Histogram queries | Structured traffic briefing |
| Context Query | Log group, stream, line_num | ListLogs -> ListLogContext | Concise log fragments |
| Collection Patrol | Host group filter | ListHostGroup + ListHost + ListAccessConfig | Anomaly checklist |
| OBS Transfer | Log group, stream, OBS bucket | CreateTransfer -> ListTransfers | Transfer task status |
| Full Patrol | Time range | All queries aggregated | Complete patrol report |
