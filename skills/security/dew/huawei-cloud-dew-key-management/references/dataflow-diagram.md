# Data Flow Diagram — huawei-cloud-dew-key-management

## 1. Query flow (R3 — read-only, auto execute)

```mermaid
flowchart LR
    A[User request: list/describe secrets or keys] --> B[Agent loads huawei-cloud-dew-key-management skill]
    B --> C{"Action class?"}
    C -->|Query R3| D[hcloud CSMS/KMS read-only command]
    C -->|Diagnose R3| E[Composite read-only analysis]
    C -->|Manage R2/R1| F[Preview + user confirmation]
    D --> G[(Huawei Cloud DEW API)]
    E --> G
    G -->|metadata JSON| H[Agent summarizes - NO secret values]
    F -->|confirmed| I[hcloud management command]
    I --> G
```

## 2. Security boundary — secret values never enter agent context

```mermaid
flowchart LR
    subgraph Agent side
        A[Agent context]
        B[BLOCKED: DownloadSecretBlob / ShowSecretVersion value / DecryptData]
    end
    subgraph Runtime side
        C[Application runtime]
        D[{{resolve:csms:secret-id:SecretString:key}}]
        E[(CSMS secret store)]
    end
    A -.->|never| E
    C -->|resolve at deploy| D --> E
    E -->|value injected at runtime only| C
```

## 3. Rotation analysis flow (huawei_analyze_dew_rotation)

```mermaid
flowchart TD
    A[ListSecrets] --> B[For each secret: ShowSecret]
    B --> C{auto_rotation?}
    C -->|enabled| D[Check rotation_period + rotation_func_urn]
    C -->|disabled| E[Flag: rotation not enabled]
    D --> F[Optional: KMS ShowKeyRotationStatus for the secret's KMS key]
    F --> G[Rotation status report]
```

## 4. Key usage audit flow (huawei_analyze_dew_key_usage)

```mermaid
flowchart TD
    A[CTS ListTraces --service_type=KMS] --> B[Filter encrypt/decrypt/delete events]
    B --> C[Group by key_id, user, source_ip]
    C --> D{Anomalies?}
    D -->|failed decrypts / ops on deleted keys| E[Flag risks]
    D -->|normal usage| F[Usage summary]
    E --> G[Audit report]
    F --> G
```