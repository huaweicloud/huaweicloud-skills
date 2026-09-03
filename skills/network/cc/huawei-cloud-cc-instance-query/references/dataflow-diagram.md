# Data Flow Diagram

```mermaid
graph TD
    User[User / Agent] -->|hcloud CC command| CLI[hcloud CLI]
    CLI -->|GET request with AK/SK auth| CC_API[Cloud Connect API]

    subgraph "Cloud Connect Resources"
        CC_API --> CC[Cloud Connections]
        CC_API --> BP[Bandwidth Packages]
        CC_API --> IRBW[Inter-Region Bandwidths]
        CC_API --> NI[Network Instances]
        CC_API --> CR[Cloud Connection Routes]
        CC_API --> AUTH[Authorisations — Granted]
        CC_API --> PERM[Permissions — Received]
    end

    CC -->|JSON response| CLI
    BP -->|JSON response| CLI
    IRBW -->|JSON response| CLI
    NI -->|JSON response| CLI
    CR -->|JSON response| CLI
    AUTH -->|JSON response| CLI
    PERM -->|JSON response| CLI

    CLI -->|Formatted output| User

    subgraph "Query Types"
        Q1[Show: single by ID]
        Q2[List: filtered + paginated]
    end

    User -.->|Show: --id=xxx| Q1
    User -.->|List: --limit, --marker, --status| Q2
```

## Resource Relationships

```mermaid
graph LR
    CC[Cloud Connection] -->|1:N| BP[Bandwidth Package]
    BP -->|1:N| IRBW[Inter-Region Bandwidth]
    CC -->|1:N| NI[Network Instance]
    CC -->|1:N| CR[Cloud Connection Route]
    NI -->|references| CC
    IRBW -->|references| BP
    IRBW -->|references| CC
    CR -->|references| CC
    CR -->|references| NI

    subgraph "Cross-Account Authorisation"
        AUTH[Authorisation] -->|grants| NI_OWNED[Network Instance owned by grantor]
        NI_OWNED -->|loadable into| CC_FOREIGN[Cloud Connection owned by grantee]
        PERM[Permission] -->|received from| NI_FOREIGN[Network Instance owned by foreign account]
        NI_FOREIGN -->|loadable into| CC[Cloud Connection owned by grantee]
    end
```

## Query Flow

1. **Single query** — User provides `--domain_id` + `--id` → API returns one resource detail
2. **List query** — User provides `--domain_id` + optional filters → API returns paginated list
3. **Pagination** — User provides `--marker` from previous response to get next page
4. **Authorisation audit** — `ListAuthorisations` shows what this account granted; `ListPermissions` shows what this account received. Cross-reference `cloud_connection_domain_id` (in authorisations) or `instance_domain_id` (in permissions) to identify the other party.
