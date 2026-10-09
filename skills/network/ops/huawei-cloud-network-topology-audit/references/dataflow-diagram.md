# Data Flow Diagram

```mermaid
flowchart TB
    User[User describes access path] --> S1[Step 1: Connectivity Precheck]
    S1 -->|pass| S2[Step 2: Path Parsing & find-skills Lookup]
    S1 -->|fail| Err[Prompt: configure credentials]

    S2 --> S3[Step 3: Real Topology Discovery]

    subgraph S3_Detail[Step 3 Detail]
        direction TB
        P1[Path A: network-query<br/>computing-query<br/>rds-smart-service<br/>cce-cluster-mgmt]
        P2[Path B: scripts/query-dcs-instances.py]
        P1 --> Merge[Merge topology dataset]
        P2 --> Merge
        Merge --> Expand[Expand to full VPC surface]
    end

    S3 --> S4[Step 4: Diff Analysis]
    S4 --> S5[Step 5: User Confirmation]
    S5 -->|confirmed| S6[Step 6: Risk Audit]

    subgraph S6_Detail[Step 6 Detail]
        direction TB
        Rules[Load rules/network-audit-rules.yaml] --> Validate[python3 scripts/validate-rules.py]
        Validate --> Eval[Evaluate rules vs topology dataset]
        Eval --> Findings[Collect risk findings]
        Findings --> Sort[Sort by severity]
    end

    S6 --> S7[Step 7: Report Rendering]
    S7 --> Report[Markdown Audit Report]

    subgraph Report_Content[Report Contents]
        ReportTopo[Topology Summary]
        ReportSG[Security Group Inventory]
        ReportRisk[Risk List by Severity]
        ReportDiagram[Mermaid Topology Diagram]
    end
```

## Data Sources

| Source | Type | Tool/Method |
|--------|------|-------------|
| VPC/Subnet/SG/ELB/EIP/NAT | Path A query skill | huawei-cloud-network-query |
| ECS/NIC | Path A query skill | huawei-cloud-computing-query |
| RDS | Path A query skill | huawei-cloud-rds-smart-service |
| CCE | Path A query skill | huawei-cloud-cce-cluster-management |
| DCS | Path B SDK script | scripts/query-dcs-instances.py |
| Rules | Static file | rules/network-audit-rules.yaml |

## Output Flow

```
Topology Dataset (.json internal)
    │
    ├── Diff Engine → Diff List
    ├── Audit Engine → Risk List (sorted by severity)
    └── Report Engine → Markdown Report
                        ├── Topology Summary
                        ├── Security Group Inventory
                        ├── Risk List
                        └── Mermaid Diagram
```