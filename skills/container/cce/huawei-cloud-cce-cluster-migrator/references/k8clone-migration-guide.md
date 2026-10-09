# k8clone Metadata Migration Guide

`k8clone` is Huawei Cloud's official lightweight Kubernetes metadata cloning tool. It exports Kubernetes resource manifests (Deployments, StatefulSets, ConfigMaps, Secrets, Services, Ingress, and PVCs) into a local compressed archive and restores them to a target CCE cluster with automated **StorageClass substitution** and **Image Repository re-pointing**.

---

## 1. Tool Overview and Architecture

|Feature|`velero`|`k8clone`|
|-|-|-|
|**Primary Scope**|Full cluster state + Persistent Volume (PV) data.|Lightweight Kubernetes object metadata cloning.|
|**Cluster Footprint**|Deploys controller pods and `node-agent` daemonsets.|Zero cluster installation; runs purely from client workstation.|
|**PV Data Migration**|Supported via Restic, Kopia, or CSI volume snapshots.|Not supported (PVC definitions are migrated, but underlying volume data requires separate sync).|
|**StorageClass Mapping**|Supported via `RestoreItemAction` ConfigMap plugin.|Supported natively via `restore.json`.|
|**Image Re-pointing**|Requires Velero image patch plugins or kustomize.|Supported natively via `restore.json` (`ImageRepo` block).|
|**HostPath Volumes**|**Not supported** by Velero or cloud CSI drivers.|Migrated as manifest, but HostPath does not map to cloud storage.|

### Tool Download and Installation

See `references/cli-installation-guide.md` Section 7 for download links and installation steps for both Linux x86_64 and ARM64 architectures.

---

## 2. Critical Caution: PersistentVolume Reclaim Policy

> [!CAUTION]
> When a PersistentVolume has `reclaimPolicy: Delete`, restoring a PV object prior to its PVC can trigger Kubernetes to delete the PV and permanently purge the underlying cloud storage volume.
>
> To safeguard application data:
>
> 1. `k8clone` by default excludes PV objects where `reclaimPolicy` is set to `Delete`.
> 2. Ensure StorageClass definitions on CCE use `reclaimPolicy: Retain` during the migration window.
> 3. Migrate PVC manifests and let CCE dynamic provisioning bind new volumes, or sync data independently (see `references/storage-pv-migration-guide.md`).

---

## 3. Backup Procedure

Connect `kubectl` to the source cluster and execute backup:

### Common Backup Options

```bash
# Backup all workloads, configmaps, and secrets excluding system namespaces
k8clone backup \
  --kubeconfig=~/.kube/source-config \
  --exclude-namespaces="kube-system,kube-public,kube-node-lease,velero" \
  --exclude-having-owner-ref=true \
  --local-dir=./k8clone-dump

# Backup a specific namespace
k8clone backup \
  --kubeconfig=~/.kube/source-config \
  --namespace=production \
  --exclude-having-owner-ref=true \
  --local-dir=./k8clone-dump
```

- `--exclude-having-owner-ref=true`: **Crucial parameter**. Excludes managed child pods/replicasets generated dynamically by Deployments/Jobs, preventing duplicate restoration.
- The command generates a `k8clone-dump.zip` archive containing all exported YAML definitions.

---

## 4. Automated Restoration via `restore.json`

`k8clone` automatically mutates manifests during restore according to rules defined in `restore.json`:

- **StorageClass**: Substitutes source StorageClasses in PVCs and StatefulSet `volumeClaimTemplates` to target CCE Everest classes (`csi-disk`, `csi-sfsturbo`, `csi-obs`).
- **ImageRepo**: Re-points container image registries to Huawei Cloud SWR.

### `restore.json` Configuration

Configure StorageClass mapping and ImageRepo re-pointing in `restore.json`. See `templates/k8clone-restore.json`:

```json
{
  "StorageClass": {
    "gp2": "csi-disk",
    "standard": "csi-disk",
    "nfs-client": "csi-sfsturbo",
    "efs-sc": "csi-sfsturbo",
    "minio-sc": "csi-obs"
  },
  "ImageRepo": {
    "docker.io": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo",
    "quay.io": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo",
    "registry.k8s.io": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo"
  }
}
```

### Execute Restore on CCE

```bash
k8clone restore \
  --kubeconfig=~/.kube/cce-config \
  --local-dir=./k8clone-dump.zip \
  --restore-conf=./restore.json
```

---

## 5. Critical Manifest Sanitization Rules

Before applying or during manifest processing, ensure strict metadata hygiene for seamless dynamic provisioning on CCE:

### 5.1 PVC Metadata Sanitization Specification (Preventing `Lost` State)

When source PVCs are backed up or exported, they contain runtime binding metadata from the source cluster:

- `spec.volumeName`: Refers to source cluster PV objects that do not exist in CCE.
- `annotations`:
  - `pv.kubernetes.io/*` (e.g. `pv.kubernetes.io/bind-completed`, `pv.kubernetes.io/bound-by-controller`)
  - `volume.beta.kubernetes.io/*` (e.g. `volume.beta.kubernetes.io/storage-provisioner`)

> [!CAUTION]
> **Mandatory Sanitization Rules**:
>
> 1. **Must delete `spec.volumeName`**
> 2. **Must delete all `pv.kubernetes.io/*` and `volume.beta.kubernetes.io/*` annotations**
>
> **Consequence if Omitted**:
> The target CCE dynamic storage controller (Everest CSI / `everest-csi-provisioner`) will treat the claim as already bound to an existing PV. Consequently, Everest CSI **will not allocate underlying EVS or SFS storage resources**, leaving the PVC stuck in the **`Lost`** state indefinitely.

**Sanitization Snippet**:

```python
def clean_pvc_metadata(pvc_doc):
    # 1. Must delete spec.volumeName
    spec = pvc_doc.get("spec", {})
    spec.pop("volumeName", None)

    # 2. Must delete all pv.kubernetes.io/* and volume.beta.kubernetes.io/* annotations
    annotations = pvc_doc.get("metadata", {}).get("annotations", {})
    for k in list(annotations.keys()):
        if k.startswith("pv.kubernetes.io/") or k.startswith("volume.beta.kubernetes.io/"):
            annotations.pop(k)
```

### 5.2 StatefulSet `volumeClaimTemplates` Immutability

Kubernetes prohibits modifying `volumeClaimTemplates` on existing StatefulSets.
If a StatefulSet was created with incorrect storage classes or requires volume adjustments:

1. Delete the StatefulSet while preserving underlying pods:
   ```bash
   kubectl delete sts <statefulset-name> -n <namespace> --cascade=orphan
   ```
2. Re-apply the updated StatefulSet manifest with correct `storageClassName: csi-disk` (or `csi-sfsturbo`).

### 5.3 Pre-Restore EVS 10 GiB Capacity Normalization

Huawei Cloud EVS enforces a minimum volume size of **10 GiB**. If source manifests define smaller PVCs (e.g. 1Gi, 5Gi, 8Gi), normalize them in the uncompressed `k8clone-dump` directory before restoring:

```bash
# Normalize all requested storage smaller than 10Gi to 10Gi in exported PVC manifests
find ./k8clone-dump -name "*.yaml" -exec sed -i -E 's/storage: [1-9]Gi/storage: 10Gi/g' {} +
```

### 5.4 Stateful Data Ingestion Sequencing & Direct DB Streaming

For stateful applications (PostgreSQL, MySQL, Redis, Weaviate), pairing `k8clone` with direct database logical streaming guarantees 100% transactional consistency, zero cluster footprint, and zero S3 protocol friction:

1. **Deploy Workloads with Replicas = 0**: Restore metadata via `k8clone restore` with application deployments scaled to `0`.
2. **Wait for Target Databases to Reach Running**:
   ```bash
   kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=postgresql -n <namespace> --timeout=180s
   ```
3. **Stream Database Data Directly via Kubectl Pipe**:
   ```bash
   # PostgreSQL streaming dump & load
   kubectl --kubeconfig=~/.kube/source-config -n <namespace> exec -i <source-pg-pod> -- \
     pg_dump -U <db-user> -d <db-name> --no-owner --clean | \
   kubectl --kubeconfig=~/.kube/cce-config -n <namespace> exec -i <cce-pg-pod> -- \
     psql -U <db-user> -d <db-name>

   # Redis replication / data reload
   kubectl --kubeconfig=~/.kube/source-config -n <namespace> exec -i <source-redis-pod> -- \
     redis-cli --raw dump <key> | ...
   ```
4. **Scale Application Deployments to Target Replicas**:
   ```bash
   kubectl --kubeconfig=~/.kube/cce-config -n <namespace> scale deployment --all --replicas=1
   ```

### 5.5 Headless Service `clusterIP: None` Protection Specification

When exporting Services, `k8clone` automatically strips `spec.clusterIP` to allow the target cluster to dynamically allocate a new ClusterIP from its own service CIDR. However, `k8clone`'s stripping logic unconditionally removes `spec.clusterIP` even when its value is `"None"` (Headless Service).

> [!CAUTION]
> **Impact of Stripped `clusterIP: None`**:
>
> 1. **Accidental ClusterIP Allocation**: If a Headless Service manifest is restored without `clusterIP: None`, the Kubernetes API server treats it as a regular service and allocates a standard ClusterIP (e.g. `10.247.x.x`).
> 2. **StatefulSet DNS Failure**: CoreDNS stops returning individual Pod IPs for headless DNS queries, breaking internal peer discovery and quorum clustering for StatefulSets (e.g. PostgreSQL HA, Kafka, ZooKeeper, Redis, Elasticsearch).
> 3. **API Validation Error**: If `spec.clusterIPs: ["None"]` is present or mismatched while `clusterIP` is stripped, `kubectl apply` fails with `spec.clusterIPs: Invalid value: []... may not be empty when clusterIP is "None"`.

**Pre-Restore Manifest Normalization**:
Before executing `k8clone restore`, inspect and normalize all Service manifests in the uncompressed `k8clone-dump` directory. Re-inject `clusterIP: "None"` and `clusterIPs: ["None"]` into all Services that were originally headless:

```bash
# 1. Identify headless services from source cluster
kubectl get svc -A --kubeconfig=~/.kube/source-config \
  -o jsonpath='{range .items[?(@.spec.clusterIP=="None")]}{.metadata.namespace}{"/"}{.metadata.name}{"\n"}{end}' > /tmp/headless-svcs.txt

# 2. Re-inject clusterIP: "None" in k8clone-dump manifests before restore
python3 -c '
import os, glob, yaml

with open("/tmp/headless-svcs.txt") as f:
    headless = set(line.strip() for line in f if line.strip())

for fpath in glob.glob("./k8clone-dump/**/*.yaml", recursive=True):
    with open(fpath, "r") as f:
        try:
            docs = list(yaml.safe_load_all(f))
        except Exception:
            continue
    modified = False
    for doc in docs:
        if doc and doc.get("kind") == "Service":
            ns = doc.get("metadata", {}).get("namespace", "default")
            name = doc.get("metadata", {}).get("name", "")
            if f"{ns}/{name}" in headless:
                doc.setdefault("spec", {})["clusterIP"] = "None"
                doc["spec"]["clusterIPs"] = ["None"]
                modified = True
    if modified:
        with open(fpath, "w") as f:
            yaml.safe_dump_all(docs, f)
'
```

**Post-Restore Recovery**:
If a Headless Service was already restored with an unwanted ClusterIP on CCE, `spec.clusterIP` cannot be mutated from an allocated IP to `None` in-place (the field is immutable). The Service must be deleted and re-created:

```bash
kubectl delete svc <headless-service-name> -n <namespace> --kubeconfig=~/.kube/cce-config
kubectl apply -f <headless-service-manifest.yaml> --kubeconfig=~/.kube/cce-config
```

---

## 6. Post-Restore Validation

Verify restored objects and adapted configurations on CCE:

```bash
# Check PVC storage classes
kubectl get pvc -A --kubeconfig=~/.kube/cce-config

# Check image URLs in deployed pods
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{": "}{range .spec.containers[*]}{.image}{" "}{end}{"\n"}{end}' --kubeconfig=~/.kube/cce-config
```
