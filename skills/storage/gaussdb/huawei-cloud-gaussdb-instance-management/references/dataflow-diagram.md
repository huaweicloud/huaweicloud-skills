# Data Flow Diagram

## Query / Analyze (R3 — read-only, auto-execute)

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant S as SKILL.md (huawei-cloud-gaussdb-instance-management)
    participant C as hcloud CLI
    participant G as GaussDB API (mysql/opengauss)

    U->>A: "列出 GaussDB 实例" / "分析部署形态"
    A->>S: match huawei_* action (R3)
    S->>C: hcloud GaussDB ListGaussMySqlInstances --cli-region={region}
    C->>G: GET /v3/{project_id}/instances
    G-->>C: JSON instances
    C-->>S: JSON output
    S-->>A: structured result
    A-->>U: summary table / analysis report
```

## Manage (R2/R1 — preview + confirm)

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant S as SKILL.md (huawei-cloud-gaussdb-instance-management)
    participant C as hcloud CLI
    participant G as GaussDB API

    U->>A: "创建 GaussDB 实例" / "删除实例"
    A->>S: match huawei_* action (R2/R1)
    S-->>A: exact command + effect preview
    A-->>U: show command preview, request confirmation
    Note over U: confirmation required (R1: risk confirmation)
    U-->>A: confirm
    A->>C: hcloud GaussDB CreateGaussMySqlInstance / DeleteGaussMySqlInstance ...
    C->>G: POST/DELETE API call
    G-->>C: job_id / result
    C-->>A: execution result
    A-->>U: success + verification steps
```

## Key facts carried through the flow

- **Product family** (MySQL-compatible vs openGauss) is selected first and routes the service name (`GaussDB` vs `gaussdbforopengauss`).
- **Critical Warnings** are surfaced at the preview step for R2/R1 actions: shard key permanent, ≥3 nodes minimum, engine version pinned.
- **Quality reporting** is documented for every execution via the SKILL.md Quality Reporting section (skill_quality_sdk.py integration, non-blocking).