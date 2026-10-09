# Data Flow Diagram

```mermaid
flowchart LR
    U[User query<br/>客户列表/余额/账单/订单...] --> A[Agent]
    A -->|trigger match + scope/time/money check| B[catalog.yml<br/>10 entry_points]
    B -->|entry_point -> primary_facts| C[semantic models<br/>22 facts / 6 model files]
    C -->|source_operations| D[related-commands.md<br/>SDK templates]
    D --> E[BssClient global helper<br/>GlobalCredentials + bss.myhuaweicloud.com]
    E --> F[(huaweicloudsdkbss 3.1.211<br/>real REST paths from _http_info)]
    F -->|List* / Show* only| G[(BSS Partner API<br/>bpconsole v156 代售)]
    G --> H{Error?}
    H -->|domain_id no access / CBC.0151| I[Stop + tell user<br/>no partner permission]
    H -->|NETWORK_ERROR| J[Suggest HTTPS_PROXY]
    H -->|limit > 100| K[Retry limit<=100]
    H -->|OK| L[Evidence rows]
    L --> M[Desensitize IDs<br/>No-Leak]
    M --> N[Briefing-style answer<br/>fact x grain x money_basis]
    N --> O[quality_report<br/>skill_quality_sdk.py]
```

## Flow Description

1. **Routing** — SKILL.md gates the provider (Huawei Cloud partner account), then
   `catalog.yml` matches the user's scope/time/money requirement to an entry point.
2. **Fact resolution** — the entry point's `primary_facts` select the model file;
   each fact declares `source_operations`, `grain`, `evidence_boundary`, and
   measure `additivity`.
3. **Execution** — `related-commands.md` provides the copyable SDK template; the
   shared client uses `GlobalCredentials` + fixed endpoint
   `https://bss.myhuaweicloud.com` (region `cn-north-1`).
4. **Guards** — read-only whitelist enforced before execution; error table
   intercepts permission/network/limit failures.
5. **Delivery** — evidence rows are desensitized and summarized; the run reports
   quality telemetry via `scripts/skill_quality_sdk.py` (fail-silent).