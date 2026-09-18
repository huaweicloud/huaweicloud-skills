# Data Flow Diagram

## WAF Policy Management Workflow

```mermaid
graph TB
    A[User Request] --> B{Operation Type}
    
    B -->|CRUD| C[Policy Management]
    B -->|Rule Creation| D[Rule Management]
    B -->|JSON Import| E[JSON Integration]
    
    C --> C1[CreatePolicy]
    C --> C2[ListPolicy]
    C --> C3[ShowPolicy]
    C --> C4[UpdatePolicy]
    C --> C5[DeletePolicy]
    
    D --> D1[CreateCustomRule<br/>精准防护]
    D --> D2[CreateCcRule<br/>CC防护]
    D --> D3[CreateWhiteblackipRule<br/>黑白名单]
    D --> D4[CreateGeoipRule<br/>地理位置]
    D --> D5[CreateIgnoreRule<br/>全局白名单]
    D --> D6[CreateAnticrawlerRule<br/>反爬虫]
    D --> D7[CreatePrivacyRule<br/>隐私屏蔽]
    D --> D8[CreateAntiTamperRule<br/>防篡改]
    D --> D9[CreateAntileakageRule<br/>防泄露]
    
    E --> E1[Read JSON File]
    E1 --> E2[Parse Structure]
    E2 --> E3[Map to CLI Params]
    E3 --> E4{Create or Update?}
    E4 -->|Create| C1
    E4 -->|Update| C4
    E3 --> E5[Batch Create Rules]
    E5 --> D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9
    
    C1 & C2 & C3 & C4 & C5 --> F[hcloud CLI]
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9 --> F
    F --> G[Huawei Cloud WAF API]
    G --> H[Response]
    H --> I[User Output]
```

## JSON Import Flow

```mermaid
graph LR
    A[huawei-cloud-waf-policy-query<br/>Export JSON] --> B[Read File]
    B --> C{JSON Structure}
    C --> D[metadata]
    C --> E[basic_info]
    C --> F[module_status]
    C --> G[rule_details]
    
    D --> H[region, policy_id]
    E --> I[level, action, hosts]
    F --> J[module switches]
    G --> K[rule configurations]
    
    H & I --> L[CreatePolicy / UpdatePolicy]
    J --> M[Enable Modules]
    K --> N[Batch Create Rules]
    
    L & M & N --> O[Complete Policy Setup]
```

## Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Process step |
| `{ }` | Decision point |
| `-->` | Data flow |
