# Data Flow Diagram

```mermaid
flowchart TD
    U[User / Agent request] --> C{Intent classify}

    C -->|query / diagnose| Q1[Read-only: build hcloud command]
    C -->|create / start / stop / restart| M2[Manage R2: preview + dry-run + confirm]
    C -->|delete| M1[Manage R1: verify instance + irreversible warning + confirm]

    subgraph Query [R3 Query - auto execute]
        Q1 --> L1[hcloud ECS ListServersDetails]
        Q1 --> L2[hcloud ECS ShowServer]
        Q1 --> L3[hcloud ECS ListFlavors]
        Q1 --> L4[hcloud IMS ListImages]
        Q1 --> L5[hcloud ECS ShowServerLimits]
    end

    subgraph Diag [R3 Diagnose - auto execute]
        D1[Step 1 Quota: ShowServerLimits] -->|ok| D2[Step 2 Flavor: ListFlavors]
        D2 -->|ok| D3[Step 3 Image: IMS ListImages]
        D3 -->|ok| D4[Step 4 Network: VPC ListSubnets / ListSecurityGroups / EIP ListPublicips]
        D4 -->|ok| D5[Step 5 Keypair: KPS ListKeypairs]
        D5 -->|ok| D6[Step 6 Disk: EVS ListVolumes]
        D1 -.fail.-> R1[Root cause: quota]
        D2 -.fail.-> R2[Root cause: flavor]
        D3 -.fail.-> R3c[Root cause: image]
        D4 -.fail.-> R4[Root cause: network]
        D5 -.fail.-> R5[Root cause: keypair]
        D6 -.fail.-> R6[Root cause: disk]
        D6 -->|all ok| J{Job id available?}
        J -->|yes| S[ECS ShowJob - job status / error]
        J -->|no| P[Report param-level API error + retry suggestion]
    end

    subgraph Manage [Manage]
        M2 --> X[Execute create / start / stop / restart]
        M1 --> Y[Execute DeleteServers]
    end

    Query --> Out[JSON summary + readable report]
    Diag --> Out
    Manage --> Out
    Out --> QCLI[skill-quality-cli run wraps every hcloud call - telemetry]
```

Diagnosis flow rule: execute steps **in order** (quota → flavor → image → network → keypair →
disk); stop at the first failing check and report that root cause with evidence and a fix
suggestion. If every check passes but the create request still failed, report the exact API
error body from the request parameters (or the `ShowJob` result when a job id exists) and
suggest a retry.