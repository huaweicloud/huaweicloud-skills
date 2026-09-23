# Data Flow Diagram

```mermaid
graph TD
    A[User Request] --> B{Clarify Scope}
    B --> C[Confirm Parameters]
    C --> D[hcloud WAF ListEvent]
    
    D --> E{Has More Pages?}
    E -->|Yes| D
    E -->|No| F[Collect All Events]
    
    F --> G[Multi-Dimensional Analysis]
    
    G --> H[Attack Type Distribution]
    G --> I[Source IP Frequency]
    G --> J[Target Asset Analysis]
    G --> K[Geographic Distribution]
    G --> L[Time Trend Analysis]
    G --> M[Action Distribution]
    
    H --> N[Correlate Patterns]
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O{Pattern Match?}
    
    O -->|High-freq single IP| P[Recommend: IP Blacklist / CC Rule]
    O -->|Specific URL targeted| Q[Recommend: Precise Access Control]
    O -->|Country-based attacks| R[Recommend: Geo Access Control]
    O -->|BOT/Scanner patterns| S[Recommend: BOT Management]
    O -->|SQL injection pattern| T[Recommend: Enable SQLi Protection]
    O -->|XSS pattern| U[Recommend: Enable XSS Protection]
    O -->|Admin path attacks| V[Recommend: Path Restriction Rule]
    
    P --> W[Generate Report + Recommendations]
    Q --> W
    R --> W
    S --> W
    T --> W
    U --> W
    V --> W
    
    W --> X[Present to User]
    X --> Y{User Wants Details?}
    Y -->|Yes| Z[hcloud WAF ShowEvent]
    Z --> AA[Show Event Detail]
    Y -->|No| AB[Done]
    
    style A fill:#e1f5fe
    style W fill:#c8e6c9
    style X fill:#fff9c4
    style D fill:#ffccbc
```

## Data Sources

| Stage | Data Source | Fields Used |
|-------|-------------|-------------|
| Query | `ListEvent` API | sip, host, url, attack, action, attack_time, ip_country, ip_region, rule_id, payload |
| Detail | `ShowEvent` API | Full request headers, payload content, matched rule, response action |

## Aggregation Dimensions

```
Events[] → GroupBy(attack)     → Count per type
Events[] → GroupBy(sip)       → Top-N IPs
Events[] → GroupBy(host)      → Most targeted domains
Events[] → GroupBy(url)       → Most targeted paths
Events[] → GroupBy(ip_country) → Geographic distribution
Events[] → GroupBy(action)    → Block/pass/captcha ratio
Events[] → BucketBy(time)     → Hourly/daily trend
```
