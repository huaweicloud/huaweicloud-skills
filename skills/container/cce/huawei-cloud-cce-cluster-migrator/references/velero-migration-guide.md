# Velero Workload and State Migration Guide

Velero is the standard tool for Kubernetes workload, configuration, and state migration. In a migration to Huawei Cloud CCE, Velero stores backup manifests and volume snapshots in a centralized Huawei Cloud Object Storage Service (OBS) bucket using the standard S3-compatible protocol.

---

## 1. Prerequisites and Architecture

```
[ Source Cluster (Self-Hosted / AWS / Azure) ]
          │  (1) velero backup create
          ▼
   [ Huawei Cloud OBS Bucket (Backup Repository) ]
          │  (2) velero restore create
          ▼
[ Target Cluster (Huawei Cloud CCE) ]
```

### Credentials File (`credentials-velero`)

Prepare a credentials file for the S3-compatible plugin using Huawei Cloud AK/SK:

```ini
[default]
aws_access_key_id=<HUAWEI_ACCESS_KEY>
aws_secret_access_key=<HUAWEI_SECRET_KEY>
```

> [!CAUTION]
> Do not commit this credentials file to git. Use strict file permissions (`chmod 600 credentials-velero`).

---

## 2. Velero Server Installation & Critical Engine Caveats

> [!CAUTION]
> **Mandatory Uploader Selection: Enforce `--uploader-type=restic` (Do NOT use Kopia on Huawei Cloud OBS)**:
>
> 1. **Protocol Incompatibility (Virtual-Hosted vs Path-Style)**: Huawei Cloud OBS officially enforces **Virtual-Hosted-Style** (`https://<bucket>.obs.<region>.myhuaweicloud.com/`) and prohibits legacy Path-Style access (`https://obs.<region>.myhuaweicloud.com/<bucket>`).
> 2. **Kopia Upstream Defect (Velero Issue #9780)**: Velero's Kopia uploader ignores BSL virtual-hosted configuration and hardcodes/defaults to Path-Style addressing. When Kopia sends Path-Style requests to OBS, OBS rejects or fails to locate the bucket (returning `NoSuchBucket` on writes).
> 3. **Silent Fake Completion Hazard**: Kopia creates a local snapshot ID, but its in-memory blob flush to OBS fails. Velero 1.14 fails to escalate this backend flush error, reporting `phase: Completed (0 errors)` even though the OBS `repositories/` prefix is **completely empty (0 bytes)**.
> 4. **Mandatory Standard**: Always explicitly install Velero with **`--uploader-type=restic`** on both source and target clusters. Restic's S3 client reliably uploads chunks to `obs://<bucket>/<prefix>/restic/`.

### Step A: Install on Source Kubernetes Cluster

Deploy Velero into the source cluster connected to the shared Huawei Cloud OBS bucket:

```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket <your-migration-obs-bucket> \
  --prefix <migration-prefix> \
  --secret-file ./credentials-velero \
  --use-node-agent \
  --uploader-type=restic \
  --backup-location-config region=<region>,s3ForcePathStyle="false",s3Url=https://obs.<region>.myhuaweicloud.com
```

Verify deployment:

```bash
kubectl -n velero get pods
velero backup-location get
```

### Step B: Install on Target Huawei Cloud CCE Cluster (Private Nodes & SWR)

Deploy Velero on CCE pointing to the exact same OBS bucket and prefix.

> [!TIP]
> **Complete SWR Image Flags & `imagePullSecrets` for Private CCE Nodes**:
> CCE nodes in private subnets cannot pull from `docker.io` without a NAT Gateway. You **must specify SWR image paths for all Velero components** (see `references/swr-image-sync-guide.md` Section 3 for the pre-mirroring script):
>
> 1. `--image`: The Velero server and node-agent daemonset image
> 2. `--plugins`: The AWS/OBS S3 plugin init container image
> 3. `--restore-helper-image`: The restore helper init container image injected into restored pods

```bash
# Switch to target CCE context
kubectl config use-context cce-context

velero install \
  --provider aws \
  --image swr.<region>.myhuaweicloud.com/<swr-org>/velero:v1.14.0 \
  --plugins swr.<region>.myhuaweicloud.com/<swr-org>/velero-plugin-for-aws:v1.9.0 \
  --restore-helper-image swr.<region>.myhuaweicloud.com/<swr-org>/velero-restore-helper:v1.14.0 \
  --bucket <your-migration-obs-bucket> \
  --prefix <migration-prefix> \
  --secret-file ./credentials-velero \
  --use-node-agent \
  --uploader-type=restic \
  --backup-location-config region=<region>,s3ForcePathStyle="false",s3Url=https://obs.<region>.myhuaweicloud.com
```

#### Private SWR Authentication Patch for Velero Components

When running on private nodes without public internet egress, the Velero deployment and `node-agent` daemonset require `imagePullSecrets` to pull from private SWR:

```bash
# 1. Create SWR pull secret in velero namespace
SWR_USER=$(cat /tmp/swr_user)
SWR_PWD=$(cat /tmp/swr_pwd)
kubectl -n velero create secret docker-registry default-secret \
  --docker-server=swr.<region>.myhuaweicloud.com \
  --docker-username="${SWR_USER}" \
  --docker-password="${SWR_PWD}" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Patch Velero Deployment and node-agent DaemonSet with imagePullSecrets
kubectl -n velero patch deployment velero --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/imagePullSecrets","value":[{"name":"default-secret"}]}]'

kubectl -n velero patch daemonset node-agent --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/imagePullSecrets","value":[{"name":"default-secret"}]}]'

# 3. Verify BSL reaches Available state
kubectl -n velero get backupstoragelocation
```

---

## 3. StorageClass Re-mapping & EVS 10 GiB Capacity Sizing

> [!WARNING]
> **Huawei Cloud EVS 10 GiB Minimum Constraint**:
> Huawei Cloud EVS enforces a strict minimum volume capacity of **10 GiB**. Velero's StorageClass mapping plugin (`templates/velero-sc-mapping.yaml`) substitutes the class name (`storageClassName`), but **cannot mutate volume size requests**.
> If source PVCs request less than 10 GiB (e.g. 1Gi, 5Gi, 8Gi), CCE's Everest CSI driver will reject the provision request, leaving restored PVCs permanently in `Pending`.

### Remediation: Pre-Provision Target PVCs on CCE

To ensure seamless restore of volumes with source sizes $< 10$ GiB:

1. Pre-create target PVCs in the target namespace on CCE with minimum `10Gi` (or greater) using `csi-disk-topology`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: <target-pvc-name>
  namespace: <target-namespace>
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: csi-disk-topology
  resources:
    requests:
      storage: 10Gi
```

2. When creating the Velero Restore object in Section 5, set **`restorePVs: false`** so that Velero binds application workloads to pre-existing, correctly sized PVCs rather than attempting to recreate undersized claims.

---

## 4. Transactional Consistency & Quiescent PVC Backup

> [!CAUTION]
> **Live Filesystem Backup Consistency Risk**:
> Backing up active transactional databases (PostgreSQL, MySQL, Redis, Weaviate) while workloads are processing live writes causes **"torn pages"** and out-of-sync WAL segments, resulting in crash recovery failures or initial `/install` wizard screens post-restore.

### Method 1: Velero Backup Hooks (`pre.hook` / `post.hook`) — Zero-Downtime Hot Backup

Annotate database StatefulSets or Pods so Velero executes flush/checkpoint commands before taking the volume snapshot:

#### PostgreSQL:

```yaml
metadata:
  annotations:
    pre.hook.backup.velero.io/container: postgresql
    pre.hook.backup.velero.io/command: '["/bin/sh", "-c", "psql -U postgres -c \"SELECT pg_backup_start(''velero'', true);\""]'
    post.hook.backup.velero.io/container: postgresql
    post.hook.backup.velero.io/command: '["/bin/sh", "-c", "psql -U postgres -c \"SELECT pg_backup_stop();\""]'
```

#### Redis:

```yaml
metadata:
  annotations:
    pre.hook.backup.velero.io/container: redis
    pre.hook.backup.velero.io/command: '["/bin/sh", "-c", "redis-cli bgsave && while [ $(redis-cli lastsave) -eq $LAST ]; do sleep 1; done"]'
```

### Method 2: Maintenance Window Scale-Down + Placeholder Pod Pattern (100% Consistent)

> [!IMPORTANT]
> **Velero File System Backup (FSB) Requires Running Pods**:
> Velero `node-agent` (Restic) discovers and reads volume data through the host pod volume directories. If workloads are scaled to 0, no pods mount the PVCs, and Velero **will silently skip all volume data backups**.
>
> **Standard Quiescent Execution Pattern**:
>
> 1. Scale down application deployments to flush memory and suspend writes:
>    ```bash
>    kubectl scale deployment --all --replicas=0 -n <namespace>
>    kubectl scale statefulset --all --replicas=0 -n <namespace>
>    ```
> 2. Create a temporary lightweight **Placeholder Deployment** mounting all target PVCs with a sleeping container:
>    ```yaml
>    apiVersion: apps/v1
>    kind: Deployment
>    metadata:
>      name: placeholder
>      namespace: <namespace>
>    spec:
>      replicas: 1
>      selector:
>        matchLabels: { app: placeholder }
>      template:
>        metadata:
>          labels: { app: placeholder }
>        spec:
>          containers:
>            - name: holder
>              image: busybox:1.36
>              command: ["/bin/sh", "-c", "sleep 7200"]
>              volumeMounts:
>                - { name: vol-1, mountPath: /data/vol-1 }
>                - { name: vol-2, mountPath: /data/vol-2 }
>          volumes:
>            - name: vol-1
>              persistentVolumeClaim: { claimName: <pvc-1> }
>            - name: vol-2
>              persistentVolumeClaim: { claimName: <pvc-2> }
>    ```
> 3. Execute the Velero backup. Because the placeholder pod is running and mounting the claims, Restic captures 100% consistent disk data.
> 4. Delete the placeholder pod prior to cutover.

---

## 5. Migration Execution

### Step 1: Execute Backup on Source Cluster

Ensure `defaultVolumesToFsBackup: true` is enabled to capture volume content:

```bash
velero backup create k8s-migration-backup \
  --include-namespaces=<namespace> \
  --exclude-namespaces=kube-system,kube-public,kube-node-lease,velero \
  --default-volumes-to-fs-backup=true \
  --wait
```

### Step 2: Validate Backup & OBS Data Integrity

Verify backup manifest completion and check that real restic chunk data exists in the OBS bucket:

```bash
# 1. Inspect Velero status
velero backup describe k8s-migration-backup --details
kubectl -n velero get podvolumebackups -l velero.io/backup-name=k8s-migration-backup

# 2. Verify physical data in OBS bucket
hcloud obs ls obs://<bucket>/<prefix>/restic/ -e https://obs.<region>.myhuaweicloud.com
# Ensure data/, index/, and keys/ directories contain non-zero byte objects
```

### Step 3: Execute Restore on CCE

If PVCs were pre-created on CCE to fulfill the EVS 10 GiB minimum rule:

```bash
kubectl config use-context cce-context

kubectl -n velero create -f - <<EOF
apiVersion: velero.io/v1
kind: Restore
metadata:
  name: cce-migration-restore
  namespace: velero
spec:
  backupName: k8s-migration-backup
  includedNamespaces: ["<namespace>"]
  restorePVs: false
EOF
```

Monitor restore progress:

```bash
velero restore describe cce-migration-restore --details
kubectl -n velero get podvolumerestores -l velero.io/restore-name=cce-migration-restore
```

### Step 4: Post-Restore Workload Remediation (Critical)

Velero restores objects with raw source definitions (e.g. `docker.io` images, zero replicas from scale-down, no SWR secrets). Apply remediation across all restored workloads:

1. **Both `containers` AND `initContainers` SWR Image Rewriting**: Update all container image references to the target private SWR organization. Omitting `initContainers` will leave pods stuck in `PodInitializing`.
2. **SWR `imagePullSecrets` Injection**: Add `imagePullSecrets: [{"name": "default-secret"}]` to pod templates.
3. **EVS ReadWriteOnce (RWO) Node Pinning**: CCE EVS volumes are RWO block devices attached to a single node. In multi-node CCE clusters, `csi-disk-topology` guarantees AZ placement but does not prevent pods from rescheduling across worker nodes, triggering `Multi-Attach error`. Pin stateful workloads with EVS volumes to their host node:
   ```bash
   kubectl -n <namespace> patch deployment <deploy-with-evs> --type=json \
     -p='[{"op":"add","path":"/spec/template/spec/nodeSelector","value":{"kubernetes.io/hostname":"<node-name>"}}]'
   ```
4. **Replica Scale-Up**: Restore workloads to target operational replica counts:
   ```bash
   kubectl -n <namespace> scale deployment --all --replicas=1
   kubectl -n <namespace> scale statefulset --all --replicas=1
   ```

### Step 5: Post-Restore Database Consistency Verification

Before routing live traffic, verify database table counts against the source baseline:

```bash
# Verify PostgreSQL row count
kubectl exec -i <postgres-pod> -n <namespace> -- \
  psql -U <db-user> -d <db-name> -c "SELECT count(*) FROM accounts;"

# Verify Redis key count
kubectl exec -i <redis-pod> -n <namespace> -- redis-cli dbsize
```
