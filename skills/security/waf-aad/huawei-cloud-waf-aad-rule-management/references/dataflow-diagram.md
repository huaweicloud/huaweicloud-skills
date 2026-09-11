# Data Flow Diagram — huawei-cloud-waf-aad-rule-management

```mermaid
flowchart TD
    U[User request: WAF/AAD query, diagnose, manage] --> A{Action class?}

    A -->|R3 Query / Diagnose - read-only, auto| Q[Run hcloud CLI read commands]
    A -->|R2 Manage - create rule| P2[Build intent: policy_id + rule params]
    A -->|R1 Manage - delete rule| P1[Resolve rule_id from list output]
    A -->|Manage AAD instance| CONSOLE[Console-only: purchase / unsubscribe - no CLI]

    P2 --> CFM2[Preview exact CLI command + params]
    CFM2 -->|User confirms| EXEC2[Execute BatchCreate*Rule]
    P1 --> CFM1[Preview exact CLI command]
    CFM1 -->|User EXPLICITLY confirms| EXEC1[Execute Delete*Rule]

    Q --> WAF[WAF: ListInstance / ListCompositeHosts / ShowCompositeHost / ListPolicy / ListCustomRules / ListWhiteblackipRule / ListCcRules / ListGeoipRule]
    Q --> AAD[AAD: ListInstance / ListPackage / ListProtectedIp / ListUnboundProtectedIp]

    WAF --> DIAG1{Analyze?}
    DIAG1 -->|CNAME status| D1[Compare host.cname vs actual DNS record]
    DIAG1 -->|Rule order| D2[Sort by priority; flag block-above-log overlaps]
    AAD --> DIAG2{Protection coverage}
    DIAG2 --> D3[Package type vs ListProtectedIp/ListUnboundProtectedIp]

    D1 --> OUT[Structured JSON + readable summary + warnings]
    D2 --> OUT
    D3 --> OUT
    EXEC1 --> VERIFY[List again to confirm change]
    EXEC2 --> VERIFY
    VERIFY --> OUT

    OUT --> RPT[Quality reporting - skill_quality_sdk.py, non-blocking]
```

## Description

1. **R3 path (auto)**: read-only `hcloud WAF` / `hcloud AAD` commands run without confirmation.
   Diagnostics combine list/show outputs with external facts (DNS CNAME records, package type
   semantics) to produce warnings.
2. **R2 path (create)**: the rule intent is compiled into the exact `BatchCreate*` command,
   previewed to the user, and executed only after confirmation. New rules default to action=2
   (log / report-only) unless the user explicitly requests blocking.
3. **R1 path (delete)**: the `rule_id` is resolved first, the exact `Delete*Rule` command is
   previewed, and execution requires an explicit "yes, delete".
4. **AAD instance management**: no CLI exists (verified). Routing goes to console guidance only.
5. Every executed action is verified by re-listing resources; results are reported via the
   quality SDK (fail-silent).
