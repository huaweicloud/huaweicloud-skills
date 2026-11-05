# Data Flow Diagram

```mermaid
flowchart TD
    A[User query] -->|Trigger| B[list_coupons.py]
    B --> C{Project dimension?}
    C -- No --> D[Fetch voucher list<br/>hcloud BSS ListSubCustomerCoupons<br/>GET /v2/promotions/benefits/coupons]
    C -- Yes: --project-id / --usage-analysis --> F[Fetch voucher list]
    F --> G[Collect coupon order_id / lock_order_id]
    G --> H[Fetch orders<br/>hcloud BSS ListCustomerOrders<br/>GET /v2/orders/customer-orders]
    H --> I[Attribute each coupon to<br/>order.enterprise_projects ids]
    I --> J[Filter coupons locally<br/>by --project-id]
    D --> K[Apply --status / --name / --coupon-type filters]
    K --> L{Output mode}
    I --> K2[Attach project_id / project_name]
    K2 --> L
    L -- table --> M[Full-field table]
    L -- --json --> N[JSON array]
    L -- --names-only --> O[Plan-name list]
    L -- --usage-analysis --> P[Per-project<br/>usage-rate summary]
    D -. SDK fallback .-> Q[huaweicloudsdkbss<br/>GlobalCredentials]
    Q --> K
```

## Execution paths

1. **Plain list** — one GET to the coupon API, paged by offset/limit
   (page size capped at 100, max 100 pages).
2. **Project-filtered list / usage analysis** — coupon GET first, then a
   read-only order GET per referenced order_id to resolve
   `enterprise_projects`; coupons are attributed and filtered client-side.
3. **Write intent** — any mutating vocabulary is rejected by the guard before
   any command is executed.