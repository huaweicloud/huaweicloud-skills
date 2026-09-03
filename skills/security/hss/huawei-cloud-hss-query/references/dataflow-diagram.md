# Data Flow Diagram

```mermaid
graph TB
    User[User / Agent] -->|Trigger: inspection / incident| Skill[HSS Skill]

    Skill -->|Query| QueryLayer{Query Layer}

    QueryLayer -->|List assets| Cmd1[ListHostStatus]
    QueryLayer -->|List vulnerabilities| Cmd2[ListVulnerabilities]
    QueryLayer -->|Show vul details| Cmd3[ShowLinuxVulDetail / ShowWindowsVulDetail]
    QueryLayer -->|Show baseline| Cmd4[ShowBaselineOverview / ShowBaselineStatistic]
    QueryLayer -->|List events| Cmd5[ListEventHandleHistory]
    QueryLayer -->|Login audit| Cmd6[ListLoginCommonIp / ListLoginCommonLocation]
    QueryLayer -->|Risk score| Cmd7[ShowRiskScore]

    Cmd1 -->|JSON| HSS[HSS API]
    Cmd2 -->|JSON| HSS
    Cmd3 -->|JSON| HSS
    Cmd4 -->|JSON| HSS
    Cmd5 -->|JSON| HSS
    Cmd6 -->|JSON| HSS
    Cmd7 -->|JSON| HSS

    Skill -->|Diagnose| DiagLayer{Diagnose Layer}
    DiagLayer -->|Risk score| Cmd7
    DiagLayer -->|Host risk| Cmd8[ListHostsRisk]
    DiagLayer -->|Vul stats| Cmd9[ShowVulStatics]
    Cmd8 -->|JSON| HSS
    Cmd9 -->|JSON| HSS

    Skill -->|Handle| HandleLayer{Handle Layer}
    HandleLayer -->|⚠️ Confirm required| Cmd10[ChangeEvent]
    HandleLayer -->|⚠️ Confirm required| Cmd11[ChangeVulStatus]
    Cmd10 -->|POST| HSS
    Cmd11 -->|PUT| HSS

    HSS -->|Response| Output[Structured Risk Report]
    Output -->|JSON + Summary| User
```

## Flow Description

1. **Query Layer** — Read-only operations: list hosts, vulnerabilities, baselines, events, login logs, risk scores
2. **Diagnose Layer** — Risk analysis: aggregate risk scores, host risk status, vulnerability statistics
3. **Handle Layer** — Mutating operations: update alert handling status (requires explicit user confirmation)
4. **Output** — All results aggregated into a structured JSON risk report with readable summary
