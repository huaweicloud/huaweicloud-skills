# Data Flow Diagram — huawei-cloud-vpc-network-diagnosis-management

```mermaid
flowchart TD
    subgraph Agent["AI Agent (skill invocation)"]
        A1["Intent: query / diagnose / manage VPC"]
        A2["Classify risk: R3 auto / R2 preview+confirm / R1 verify+confirm"]
        A3["Build hcloud VPC command from verified templates"]
        A4["Parse JSON response"]
    end

    subgraph Skill["Skill package (this skill)"]
        S1["SKILL.md templates + parameter tables"]
        S2["Diagnosis engine (local composition)"]
        S3["CIDR conflict analyzer (ipaddress)"]
        S4["skill-quality-cli telemetry wrapper"]
    end

    subgraph Auth["Authentication"]
        C1["AK/SK env vars<br/>HUAWEICLOUD_SDK_AK/SK"]
        C2["Local hcloud AKSK profile"]
    end

    subgraph Cloud["Huawei Cloud"]
        IAM["IAM token / project_id"]
        VPCAPI["VPC API (VPC/Subnet/RouteTable/Port/SecurityGroup)"]
    end

    A1 --> A2
    A2 -->|R3 Query/Diagnose| A3
    A2 -->|R2/R1 preview + user confirm| A3
    A3 --> S1
    S1 --> C1
    S1 --> C2
    C1 --> IAM
    C2 --> IAM
    IAM --> VPCAPI
    VPCAPI -->|JSON| A4
    A4 -->|diagnose intent| S2
    A4 -->|CIDR conflict intent| S3
    S2 -->|checks: CIDR-in-VPC, overlap, default route, association, gateway| A4
    S3 -->|conflict pairs| A4
    A4 -->|structured report| A1
    A1 -.-> S4
```

## Flow description

1. **Intent & risk classification** — the agent decides whether the request is a read-only
   query/diagnosis (R3, auto execute) or a write operation (R2/R1, always preview + confirm).
2. **Command construction** — commands are built strictly from the verified templates and
   parameter tables in SKILL.md (exact names from `hcloud VPC <Operation> --help`).
3. **Authentication** — either AK/SK environment variables or the local hcloud AKSK profile;
   `--cli-region` is always passed, `--project_id` is auto-filled by KooCLI.
4. **Execution** — KooCLI calls the VPC API; responses are JSON.
5. **Diagnosis composition** — diagnose actions fetch the relevant resource sets and evaluate
   the rules locally (CIDR containment/overlap, default-route presence, port state, SG rules).
6. **Output** — a structured JSON summary + readable report, never echoing credentials.
7. **Telemetry** — every execution is wrapped with `skill-quality-cli run` for quality reporting.

## Resource relationships checked by diagnosis

```mermaid
erDiagram
    VPC ||--o{ SUBNET : contains
    VPC ||--o{ ROUTE_TABLE : owns
    ROUTE_TABLE }o--o{ SUBNET : associated
    SUBNET ||--o{ PORT : hosts
    PORT }o--o{ SECURITY_GROUP : bound
    VPC ||--o{ SECURITY_GROUP : default
```

- A subnet CIDR must be contained in its VPC CIDR.
- Two subnets in the same VPC must not overlap.
- Each subnet routes via exactly one route table.
- A port's connectivity depends on: port status, admin state, device binding, and the inbound
  rules of its security groups.