# Data Flow Diagrams

## 1. Lifecycle: instance -> group -> API -> publish

```mermaid
flowchart TD
    A[huawei_list_apig_instances<br/>ListInstancesV2] -->|instance_id, status| B{Instance Running?}
    B -- No --> A
    B -- Yes --> C[huawei_create_apig_api_group<br/>CreateApiGroupV2]
    C -->|group_id + sl_domain| D[huawei_create_apig_api<br/>CreateApiV2]
    D -->|api_id| E[huawei_publish_apig_api<br/>BatchPublishOrOfflineApiV2<br/>--apis.1]
    E -->|publish_id| F[Public endpoint via eip_address]
```

## 2. Public access analysis

```mermaid
flowchart TD
    Q1[huawei_get_apig_instance<br/>ListInstancesV2 --instance_id] --> P{eip_address valid IP?}
    P -- Yes --> PUB[Public entry exists.<br/>Use eip_address for public access]
    P -- No --> G[huawei_list_apig_api_groups<br/>ListApiGroupsV2]
    G --> S{sl_domain present?}
    S -- Yes --> WARN[internal-only domain<br/>NOT for public internet<br/>Create PROFESSIONAL + elb for public]
    S -- No --> NONE[No groups yet]
```

## 3. Instance creation (async polling)

```mermaid
sequenceDiagram
    participant A as Agent
    participant C as hcloud CLI
    A->>C: CreateInstanceV2 (spec_id, vpc, subnet, sg, AZ)
    C-->>A: 202 accepted (job started)
    loop every 60s
        A->>C: ListInstancesV2 --instance_id
        C-->>A: status (Creating / CreateSuccess / Running / ...)
    end
    Note over A: stop when status == "Running"<br/>(NOT "SUCCESS" / "CreateSuccess")
    A->>C: AddIngressEipV2 (optional, elb provider)
    A->>C: ListInstancesV2 → eip_address MAY stay null > 8 min;<br/>confirm via AddIngressEipV2 response / retry / cloud EIP list
```

## 4. Publish chain diagnosis

```mermaid
flowchart LR
    L1[ListInstancesV2] -->|instance?| L2[ListApiGroupsV2]
    L2 -->|group?| L3[ListApisV2]
    L3 -->|api?| L4{has publish_id?}
    L4 -- Yes --> OK[Published OK]
    L4 -- No --> FIX[Run huawei_publish_apig_api<br/>BatchPublishOrOfflineApiV2 --action=online]
    L1 -- No --> E1[No APIG instance]
    L2 -- No --> E2[No API group]
    L3 -- No --> E3[No API]
```