# Data Flow Diagram

```mermaid
flowchart TD
    A[User Request] --> B{hcloud CLI KooCLI}
    B --> C[hcloud EIP ListPublicips/v2]
    C --> D[EIP Resource List<br/>id / public_ip_address / status / bandwidth_id]
    B --> E[hcloud EIP ShowPublicip/v2]
    E --> F[EIP Detail<br/>bandwidth_share_type / bandwidth_size]
    B --> G[hcloud CES ListMetrics<br/>namespace=SYS.VPC]
    G --> H[Available EIP Metrics]
    D --> I{Choose dimension}
    F --> I
    H --> I
    I -->|"publicip_id"| J[hcloud CES ShowMetricData<br/>dim.0=publicip_id,{id}]
    I -->|"bandwidth_id (shared bw)"| K[hcloud CES ShowMetricData<br/>dim.0=bandwidth_id,{id}]
    J --> L[Monitoring Datapoints<br/>% / Byte / bit/s]
    K --> L
    L --> M[Formatted Report<br/>usage rate / traffic / peak / avg]
    M --> N[User]
```
