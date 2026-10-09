# Data Flow and Architecture Diagrams

This document visualizes the migration workflow, storage replication paths, and traffic cutover mechanics for the `huawei-cloud-cce-cluster-migrator` skill.

---

## 1. End-to-End Migration Flow

```mermaid
flowchart TD
    subgraph SRC["Source Kubernetes Cluster"]
        A1["Source Workloads\n(Deployments, StatefulSets)"]
        A2["Source PV Storage\n(EVS/Disk, NFS, S3)"]
        A3["Velero Node-Agent & Backup Client"]
    end

    subgraph CLOUD["Huawei Cloud Infrastructure"]
        B1["OBS Bucket\n(Velero Backup Repository)"]
        B2["SWR Container Registry\n(Mirrored Images)"]
        B3["Dedicated ELB\n(Load Balancing & SSL)"]
    end

    subgraph TGT["Target Huawei Cloud CCE"]
        C1["Velero Restore Operator"]
        C2["Everest CSI Provisioner\n(csi-disk / nas / turbo / obs)"]
        C3["Target Workloads Running on CCE"]
        C4["Bound Persistent Volumes\n(EVS / SFS / Turbo / OBS)"]
    end

    A1 -->|1. Extract Images| B2
    A1 & A2 -->|2. Velero Backup| A3
    A3 -->|3. Manifests & Volume Data| B1
    B1 -->|4. Pull Backup| C1
    B2 -->|5. Fast Image Pull| C3
    C1 -->|6. StorageClass Mapping| C2
    C2 -->|7. Dynamic Storage Binding| C4
    C1 -->|8. Reconcile Workloads| C3
    B3 -->|9. Route Production Ingress| C3
```

---

## 2. Multi-Type PV Storage Migration Matrix

```mermaid
flowchart LR
    subgraph IN["Source Volumes"]
        P1["Block Volume\n(gp2/gp3/RBD)"]
        P2["Shared File Volume\n(NFS / EFS)"]
        P3["High-Perf Shared Volume\n(HPC / Lustre / EFS)"]
        P4["Object Storage Mount\n(MinIO / S3)"]
    end

    subgraph SYNC["Sync & Backup Mechanism"]
        M1["Velero Kopia / CSI Snapshot"]
        M2["In-Pod Rsync / DataSync"]
        M3["Parallel Rsync / Direct NFS"]
        M4["obsutil / OMS Direct Sync"]
    end

    subgraph OUT["Target CCE Everest Storage"]
        T1["EVS Block Disk\n(csi-disk / bs)"]
        T2["SFS Turbo Standard\n(csi-sfsturbo / min 500Gi)"]
        T3["SFS Turbo HPC/Perf\n(csi-sfsturbo / min 1.2TB)"]
        T4["OBS Bucket Mount\n(csi-obs / obs)"]
    end

    P1 --> M1 --> T1
    P2 --> M2 --> T2
    P3 --> M3 --> T3
    P4 --> M4 --> T4
```

---

## 3. Ingress Traffic Cutover Sequence

```mermaid
sequenceDiagram
    autonumber
    participant User as User Traffic
    participant Admin as Migration Administrator
    participant DNS as Public DNS Service
    participant OldLB as Source Ingress / LB
    participant NewELB as Huawei Cloud Dedicated ELB
    participant CCE as Target CCE Cluster Workloads

    Note over User,OldLB: Normal Source Traffic
    User->>OldLB: HTTP/HTTPS Requests
    OldLB->>User: Source Service Responses

    Note over Admin,CCE: Pre-Cutover Verification
    Admin->>NewELB: Smoke Test via curl --resolve
    NewELB->>CCE: Forward to CCE Service
    CCE-->>Admin: 200 OK and Verified Payload

    Note over Admin,DNS: Switchover Execution
    Admin->>DNS: Update DNS A or CNAME Record to Target ELB IP
    DNS-->>User: Resolved New ELB IP (TTL Expiry)

    Note over User,CCE: Post-Cutover Live Traffic
    User->>NewELB: Production Requests
    NewELB->>CCE: Route to CCE Pods
    CCE-->>User: CCE Production Responses
```
