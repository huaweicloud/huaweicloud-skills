# Data Flow Diagram

```mermaid
graph TD
    User[User / Agent] -->|Specifies query type & params| CLI[hcloud CLI]
    CLI -->|CC ShowGlobalConnectionBandwidth| API1[GET /v3/{domain_id}/gcb/gcbandwidths/{id}]
    CLI -->|CC ListGlobalConnectionBandwidths| API2[GET /v3/{domain_id}/gcb/gcbandwidths]
    CLI -->|CC ListGlobalConnectionBandwidthConfigs| API3[GET /v3/{domain_id}/gcb/configs]
    CLI -->|CC ListSupportBindingConnectionBandwidths| API4[GET /v3/{domain_id}/gcb/gcbandwidths/support-bindings]

    API1 -->|GCB detail + bound instances| R1[Single GCB Response]
    API2 -->|Paginated GCB list| R2[GCB List Response]
    API3 -->|Tenant config: size ranges, quotas, services| R3[Config Response]
    API4 -->|GCBs eligible for binding| R4[Support Binding Response]

    R1 --> Output[JSON Output to User]
    R2 --> Output
    R3 --> Output
    R4 --> Output

    style CLI fill:#e1f5fe,stroke:#0288d1
    style Output fill:#e8f5e9,stroke:#388e3c
```

## Query Flow Description

| Step | Action | Input | Output |
|------|--------|-------|--------|
| 1 | User specifies query type | domain_id + optional filters | — |
| 2 | hcloud CLI sends GET request | API path + query params | HTTP response |
| 3 | CLI parses JSON response | Raw JSON | Formatted JSON |
| 4 | User reviews results | Formatted JSON | GCB details / list / configs |

## API Endpoint Summary

| Command | Method | Path |
|---------|--------|------|
| ShowGlobalConnectionBandwidth | GET | `/v3/{domain_id}/gcb/gcbandwidths/{id}` |
| ListGlobalConnectionBandwidths | GET | `/v3/{domain_id}/gcb/gcbandwidths` |
| ListGlobalConnectionBandwidthConfigs | GET | `/v3/{domain_id}/gcb/configs` |
| ListSupportBindingConnectionBandwidths | GET | `/v3/{domain_id}/gcb/gcbandwidths/support-bindings` |

All APIs use the endpoint `cc.myhuaweicloud.com`.
