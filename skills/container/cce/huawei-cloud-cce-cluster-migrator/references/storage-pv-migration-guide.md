# Multi-Type Persistent Volume (PV/PVC) Migration Guide

Persistent volumes in Kubernetes represent stateful application data. When migrating from external or self-hosted Kubernetes clusters to Huawei Cloud CCE, storage types must be mapped to appropriate Huawei Cloud CCE storage drivers and classes.

This guide provides end-to-end migration strategies for the three primary CCE storage types: **EVS (Block)**, **SFS Turbo (High-Performance Shared File)**, and **OBS (Object Storage)**.

> [!IMPORTANT]
> **Standard SFS 1.0 (`csi-nas`) Sunset Notice**:
> Scalable File Service 1.0 (`csi-nas`) is officially sunset and deprecated across Huawei Cloud. **Do NOT recommend or provision `csi-nas` for migrations.** All shared file storage (`ReadWriteMany` / NFS) workloads must migrate to **SFS Turbo (`csi-sfsturbo`)**.

---

## 1. CCE Storage Driver & StorageClass Matrix

Huawei Cloud CCE uses the unified **Everest CSI Plugin** (`everest-csi-provisioner`) to manage cloud storage resources.

|Storage Type|Underlying Service|CCE StorageClass|Access Modes|Volume Mode|Primary Workload Use Cases|
|-|-|-|-|-|-|
|**Block Storage (Single-AZ)**|Elastic Volume Service (EVS)|`csi-disk`|`ReadWriteOnce` (RWO)|Filesystem / Block|Databases (MySQL, PostgreSQL), single-AZ clusters (`Immediate` binding). Single-Pod exclusive (1 EVS : 1 Pod). Replicas=1 with `strategy: Recreate` for Deployment, or StatefulSet|
|**Block Storage (Multi-AZ / Best Practice)**|Elastic Volume Service (EVS)|`csi-disk-topology`|`ReadWriteOnce` (RWO)|Filesystem / Block|Cross-AZ stateful workloads in multi-AZ clusters (`WaitForFirstConsumer` delayed binding). Single-Pod exclusive. StatefulSet recommended|
|**Shared File Storage**|SFS Turbo|`csi-sfsturbo`|`ReadWriteMany` (RWX), `ReadOnlyMany` (ROX)|Filesystem|Web server content, CMS (WordPress), high-concurrency microservices, AI/ML training|
|**Object Storage**|Object Storage Service (OBS)|`csi-obs`|`ReadWriteMany` (RWX), `ReadOnlyMany` (ROX)|Filesystem|Unstructured data, media archives, log storage, static website assets|

---

## 2. SFS Turbo Specification & Minimum Capacity Selection Guide

> [!IMPORTANT]
> **SFS Turbo Pre-Creation Mandate**:
> SFS Turbo file system instances **CANNOT** be dynamically created from scratch via Kubernetes PVC manifests. Regardless of specification (STANDARD, PERFORMANCE, HPC, etc.), the underlying SFS Turbo instance **MUST be pre-created in Huawei Cloud SFS Turbo** (via Console or KooCLI `hcloud SFSTurbo CreateShare`) within the target VPC and subnet before binding to CCE.

When provisioning shared file storage (`ReadWriteMany`) in SFS Turbo, select the specification matching the workload scenario and enforce the **mandatory platform minimum capacity**:

|SFS Turbo Specification|Minimum Provisioned Capacity|Bandwidth & IOPS Baseline|Recommended Workload Scenarios|SFS Turbo Share Creation (`share_type`)|
|-|-|-|-|-|
|**STANDARD**|**500 GiB** (step: 100 GiB)|100 MB/s base, burst to 350 MB/s|General file sharing, web server document roots (Nginx, Apache), CMS (WordPress, Drupal), dev/test environments, CI/CD shared artifact caches|Create share with `STANDARD` type, then bind in CCE|
|**PERFORMANCE**|**500 GiB** (step: 100 GiB)|350 MB/s base, burst to 1200 MB/s; IOPS up to 100,000|High-concurrency microservices, business-critical file sharing, log ingestion, medium database dumps/backups|Create share with `PERFORMANCE` type, then bind in CCE|
|**20MB/s/TiB ~ 40MB/s/TiB (Standard Plus)**|**1.2 TB (1200 GiB)** (step: 1.2 TB)|20 ~ 40 MB/s per TiB; max 1.2 GB/s|Large-scale enterprise file repositories, media streaming, cold/warm data archives|Pre-create share in SFS Turbo, then bind via static PV|
|**125MB/s/TiB ~ 250MB/s/TiB (HPC)**|**1.2 TB (1200 GiB)** (step: 1.2 TB)|125 ~ 250 MB/s per TiB; max 5 GB/s|High-Performance Computing (HPC), AI/ML training checkpoints, financial risk modeling, EDA simulation|Pre-create share in SFS Turbo, then bind via static PV|
|**500MB/s/TiB ~ 1000MB/s/TiB (Ultra HPC / Extreme)**|**1.2 TB (1200 GiB)** (step: 1.2 TB)|500 ~ 1000 MB/s per TiB; max 20 GB/s|Ultra-high-throughput distributed deep learning clusters, autonomous driving model training, massive genomics and seismic processing|Pre-create share in SFS Turbo, then bind via static PV|

### SFS Turbo Provisioning Patterns: Dedicated vs Dynamic Subpath

Huawei Cloud SFS Turbo bills based on provisioned capacity, not actual usage. To optimize cost and avoid capacity waste:

|Dimension|Pattern A: Dedicated Instance Static Binding|Pattern B: Dynamic Subpath Provisioning (Recommended for Small/Shared RWX)|
|-|-|-|
|**Mechanism**|Binds an existing pre-created dedicated SFS Turbo instance directly via static PV (`PersistentVolume` + `PersistentVolumeClaim`)|Multiple PVCs share one pre-created SFS Turbo instance, with isolated subdirectories dynamically provisioned by CCE Everest|
|**Minimum Capacity**|**500 GiB** (Standard/Performance) or **1.2 TB** (HPC) per instance|**1 GiB** per PVC (subpath quota limit); underlying shared instance is $\ge 500$ GiB|
|**Subpath Quota**|Entire instance capacity|Enforced directory quota (`everest.io/csi.enable-sfsturbo-dir-quota: "true"`, Everest $\ge 2.4.73$)|
|**Quota Rules**|Instance scale-up via SFS Turbo API/console|Minimum 1 GiB, expansion step 1 GiB, non-shrinkable; Inode limit = quota (KB) / 16 (max 1 billion)|
|**Reclaim Policy**|`Retain` (preserves underlying SFS Turbo instance on PV/PVC deletion)|`retain-volume-only` (retains directory upon PVC deletion) or `delete` (deletes directory without cascading to parent dirs)|
|**Ideal For**|High-throughput monolithic workloads, dedicated AI model datasets, large repositories|Microservices, web server document roots, dev/test environments, workloads needing small capacities (< 500 GiB)|
|**Template**|`templates/pvc-sfsturbo-template.yaml` (Static PV + PVC)|`templates/pvc-sfsturbo-subpath-template.yaml`|

---

## 3. StorageClass Re-Mapping Matrix

When migrating workloads using Velero or Kubernetes manifests, source storage classes must be translated into target CCE StorageClasses:

|Source Cloud / Cluster StorageClass|Recommended CCE Target|CCE StorageClass Name|Notes|
|-|-|-|-|
|AWS `gp2`, `gp3`, `io1`, `io2`|Huawei Cloud EVS|`csi-disk-topology` (or `csi-disk`)|Use `csi-disk-topology` for multi-AZ clusters (delayed binding); annotate `everest.io/disk-volume-type: SSD` or `GPSSD`|
|Azure `default`, `managed-csi`, `managed-premium`|Huawei Cloud EVS|`csi-disk-topology` (or `csi-disk`)|Match performance tier; use `csi-disk-topology` for multi-AZ|
|Self-hosted Ceph `rbd`, OpenEBS, Longhorn|Huawei Cloud EVS|`csi-disk-topology` (or `csi-disk`)|Block storage replacement; use `csi-disk-topology` for multi-AZ|
|AWS `efs-sc`, Azure `azurefile-csi`, NFS, CephFS|Huawei Cloud SFS Turbo|`csi-sfsturbo`|Native `ReadWriteMany` replacement. Use subpath provisioning for < 500 GiB; dedicated instance for $\ge$ 500 GiB / 1.2 TB|
|MinIO / S3 bucket PVCs|Huawei Cloud OBS|`csi-obs`|Direct S3-compatible object bucket mount|

### Critical Architectural Guardrails: Storage Capacity & Mode Constraints

1. **Rule 1 (ReadWriteMany Workloads Mandate SFS Turbo)**:
   - If the source PVC declares `accessModes: [ReadWriteMany]`, it **MUST** be mapped to `csi-sfsturbo`.
   - EVS block storage does not support multi-node shared attachment.
   - `csi-nas` (SFS 1.0) is sunset and forbidden.

2. **Rule 2 (SFS Turbo Pre-Creation Mandate & Subpath Multi-Tenancy)**:
   - **Must Be Pre-Created First**: SFS Turbo instances **CANNOT be dynamically created from scratch via Kubernetes PVCs**. The underlying SFS Turbo file system instance **MUST be created first in Huawei Cloud SFS Turbo** (via Console or `hcloud SFSTurbo CreateShare`) within the target VPC and subnet before binding to CCE.
   - **Invalid Annotation**: The annotation `everest.io/share-expand-type` is **deprecated and invalid**; specifications are determined during SFS Turbo instance creation, not inside Kubernetes manifests.
   - **Platform Minimum Capacities**:
     - **500 GiB** minimum for STANDARD and PERFORMANCE tiers.
     - **1.2 TB (1200 GiB)** minimum for 20MB/s/TiB ~ 1000MB/s/TiB HPC tiers.
   - **For Small RWX Volumes (< 500 GiB)**: Do NOT provision separate dedicated instances for each small workload (e.g. 5Gi, 10Gi, 50Gi), which wastes storage budget. Instead, pre-create one shared SFS Turbo instance and use **Dynamic SFS Turbo Subpath Provisioning** (`templates/pvc-sfsturbo-subpath-template.yaml`) to share it across multiple PVCs with individual 1 GiB+ directory quotas referencing `everest.io/sfsturbo-share-id: <sfsturbo_id>`.
   - **For Dedicated Instances ($\ge$ 500 GiB / 1.2 TB)**: Pre-create the instance in SFS Turbo, then bind it using **Static PV/PVC Binding** (`templates/pvc-sfsturbo-template.yaml`) with `driver: sfsturbo.csi.everest.io`, `volumeHandle: <sfsturbo_id>`, and `everest.io/share-export-location: <export_location>`.

3. **Rule 3 (EVS Minimum Disk Size - 10 GiB Constraint)**:
   - Huawei Cloud Elastic Volume Service (EVS) enforces a hard platform minimum volume size of **10 GiB** across all disk categories (SSD, GPSSD, ESSD, SAS).
   - If a manifest with `storage: < 10Gi` is applied using `csi-disk` or `csi-disk-topology`, the Everest CSI provisioner will fail with `size must be greater than or equal to 10Gi`.
   - All block volume requests under `10Gi` **must be adjusted to at least `10Gi`**.

4. **Rule 4 (Single-Node Fallback without Shared Storage)**:
   - If SFS Turbo is not used and the workload runs on a single node (or can tolerate single-pod/single-node scheduling), you **MUST** adjust the manifest `accessModes` to `[ReadWriteOnce]` before mapping to `csi-disk` or `csi-disk-topology`.

5. **Rule 5 (EVS Volume Type & Multi-AZ Mandates `csi-disk-topology`)**:
   - EVS disks are single-AZ block devices and cannot be attached cross-AZ.
   - In multi-AZ CCE clusters, **always use `csi-disk-topology`** (CCE's built-in delay-bound StorageClass with `volumeBindingMode: WaitForFirstConsumer`). This delays EVS volume creation until the pod is scheduled to a specific node, ensuring the volume is provisioned in the same AZ as the node.
   - In single-AZ clusters, `csi-disk` (`Immediate` binding) or `csi-disk-topology` can be used.
   - Annotate EVS PVCs with `everest.io/disk-volume-type: SSD|GPSSD|ESSD|SAS`.

6. **Rule 6 (EVS RWO Single-Node Affinity Pinning in Multi-Node Clusters)**:
   - Because EVS disks are ReadWriteOnce (RWO) block devices, an attached volume cannot be remounted across different worker nodes simultaneously.
   - While `csi-disk-topology` guarantees AZ placement, pod rescheduling across worker nodes in multi-node clusters can cause `Multi-Attach error`.
   - Workloads mounting existing EVS volumes should declare `nodeSelector: kubernetes.io/hostname: <node>` to guarantee pod and disk co-location.

7. **Rule 7 (EVS Single-Pod Exclusivity & Deployment Concurrency Constraints)**:
   - **Single-Pod Exclusivity**: 1 EVS volume can ONLY attach to 1 Pod at any time. Multi-Pod concurrent mounting triggers `Multi-Attach error for volume` or ext4/xfs filesystem corruption due to lack of distributed file locks. Multiple containers within the same Pod CAN safely share the EVS volume via `volumeMounts`.
   - **StatefulSets for Multi-Replica Stateful Workloads**: Multi-replica workloads requiring independent persistent disks **MUST** use `StatefulSet` with `volumeClaimTemplates` (dynamically provisions 1:1 dedicated EVS disks per Pod).
   - **Deployments with EVS Constraint**: Deployments backed by EVS **MUST** set `replicas: 1` and specify `strategy.type: Recreate`. The default `RollingUpdate` strategy triggers a rolling update deadlock (`maxSurge` causes the new Pod to attempt mounting the EVS volume while the old Pod still holds it).
   - **Shared File Access Mandates SFS Turbo**: Workloads requiring multi-Pod concurrent read/write access to the same directory **MUST** migrate to SFS Turbo (`csi-sfsturbo`) with `ReadWriteMany`.

---

## 4. Velero StorageClass Mapping Configuration

Deploy the StorageClass re-mapping ConfigMap on CCE so source StorageClasses are automatically translated to CCE Everest classes (`csi-disk`, `csi-sfsturbo`, `csi-obs`) during Velero restore. See `templates/velero-sc-mapping.yaml`:

```bash
kubectl apply -f templates/velero-sc-mapping.yaml -n velero
```

---

## 5. Data Replication Workflows per Storage Type

### Path A: Block Storage Migration (EVS / `csi-disk`)

For block volumes bound to databases and stateful sets:

1. **Option 1 (Velero File-Level Backup via Kopia / Node-Agent)**:
   - Annotate source pods: `kubectl -n <ns> annotate pod <pod> backup.velero.io/backup-volumes=<vol>`.
   - Execute backup: `velero backup create stateful-backup --include-namespaces=<ns>`.
   - On target CCE, Velero dynamically provisions new EVS disks via `csi-disk` (minimum 10 GiB) and restores volume data. (See `templates/pvc-evs-template.yaml`).
2. **Option 2 (Database-Level Logical Replication)**:
   - For transactional databases (MySQL, PostgreSQL), prefer logical replication (`mysqldump`, `pg_dump`, Huawei Cloud DRS) rather than raw block sync to ensure transactional consistency.

---

### Path B: Shared File System Migration (SFS Turbo / `csi-sfsturbo`)

For shared directories (`ReadWriteMany`) accessed by multiple pods:

1. **Pre-provision Target SFS Turbo Share**:
   - Create SFS Turbo instance in the target CCE VPC with appropriate specification (STANDARD, PERFORMANCE, or HPC) and capacity ($\ge$ 500 GiB or $\ge$ 1.2 TB).
   - Ensure target security groups allow NFS traffic on port 2049.
2. **Data Synchronization via In-Pod Rsync or DataSync**:
   - Run a migration synchronization pod mounted to both source share and target SFS Turbo share:
     ```bash
     rsync -avzP --numeric-ids --delete /source-mount/ /target-sfsturbo-mount/
     ```
   - Perform initial full sync while workloads are active.
   - Schedule maintenance window, scale down source workloads (`kubectl scale deployment <name> --replicas=0`), and run final delta sync.
3. **Workload Storage Binding Options**:
   - **Option 1: Dynamic Subpath Provisioning (Recommended for Small / Shared RWX)**:
     Multiple workloads share one pre-created SFS Turbo instance with isolated directories and enforced quotas ($\ge 1$ GiB). Apply `templates/pvc-sfsturbo-subpath-template.yaml` with `everest.io/sfsturbo-share-id: <sfsturbo_id>`.
   - **Option 2: Dedicated Instance Static PV/PVC Binding**:
     For workloads requiring dedicated instance bandwidth and capacity ($\ge 500$ GiB / 1.2 TB). Apply `templates/pvc-sfsturbo-template.yaml` (creates PV + PVC binding pair referencing the pre-created share).

---

### Path C: Object Storage Migration (OBS / `csi-obs`)

For workloads storing unstructured files or mounting object buckets:

1. **Bucket Creation**: Create target OBS bucket in the CCE cluster's region (`cn-north-4`).
2. **Object Data Replication**: Use `obsutil` for incremental bucket sync:
   ```bash
   obsutil sync /source-local-path/ obs://<target-bucket-name>/
   # Or bucket-to-bucket copy:
   obsutil sync obs://<source-bucket>/ obs://<target-bucket>/ -dryRun=false
   ```
3. **Mount in CCE via `csi-obs`**: Workloads consume the bucket transparently via POSIX semantics using the Everest OBS CSI driver.

---

## 6. Verification and Integrity Check

After restoring or syncing volumes:

1. Verify PVC status:
   ```bash
   kubectl get pvc -A
   # All PVCs must transition to Bound status
   ```
2. Verify mount status inside pods:
   ```bash
   kubectl exec -it <pod-name> -n <namespace> -- df -h
   ```
3. Check filesystem read/write test:
   ```bash
   kubectl exec -it <pod-name> -n <namespace> -- touch /data/migration-test.txt
   kubectl exec -it <pod-name> -n <namespace> -- rm /data/migration-test.txt
   ```
