# EIPPool Management

EIPPool is a CCI-specific CRD (`crd.yangtse.cni/v1`) for allocating public IPs (EIPs) to Pods automatically.

---

## 1. Create EIPPool

**Option A — Auto-create EIPs (amount-based):**

```bash
hcloud CCI createCrdYangtseCniV1NamespacedEIPPool \
  --namespace=<ns-name> \
  --apiVersion=crd.yangtse.cni/v1 \
  --kind=EIPPool \
  --metadata.name=<eippool-name> \
  --spec.amount=<number-of-eips> \
  --spec.eipAttributes.networkType=5_bgp \
  --spec.eipAttributes.ipVersion=4 \
  --spec.eipAttributes.bandwidth.shareType=PER \
  --spec.eipAttributes.bandwidth.size=5 \
  --spec.eipAttributes.bandwidth.chargeMode=bandwidth \
  --spec.eipAttributes.bandwidth.name=<bandwidth-name> \
  --cli-region=<region> \
  --cli-output=json
```

**Option B — Use pre-created EIP IDs:**

```bash
hcloud CCI createCrdYangtseCniV1NamespacedEIPPool \
  --namespace=<ns-name> \
  --apiVersion=crd.yangtse.cni/v1 \
  --kind=EIPPool \
  --metadata.name=<eippool-name> \
  --spec.eips.1=<eip-id-1> \
  --spec.eips.2=<eip-id-2> \
  --cli-region=<region> \
  --cli-output=json
```

**Required fields for Option A (auto-create):**

| Field | Value | Description |
|-------|-------|-------------|
| `--apiVersion` | `crd.yangtse.cni/v1` | API version (required) |
| `--kind` | `EIPPool` | Resource kind (required) |
| `--spec.amount` | integer | Number of EIPs to create |
| `--spec.eipAttributes.networkType` | `5_bgp` or `5_gray` | EIP network type (required) |
| `--spec.eipAttributes.bandwidth.shareType` | `PER` or `WHOLE` | Bandwidth share type |
| `--spec.eipAttributes.bandwidth.size` | integer | Bandwidth size in Mbit/s |
| `--spec.eipAttributes.bandwidth.chargeMode` | `bandwidth` or `traffic` | Bandwidth billing mode |
| `--spec.eipAttributes.bandwidth.name` | string | Bandwidth name (required for PER share type) |

**Constraints:**
- `--apiVersion=crd.yangtse.cni/v1` and `--kind=EIPPool` are required (missing these causes 400 error)
- `spec.eipAttributes.networkType` is required (missing causes 422 validation error)
- `spec.eipAttributes.bandwidth.chargeMode` and `name` are required when auto-creating EIPs (missing causes 403 validation error)
- EIPPool must be in the same namespace as the Pod that uses it
- Array items are 1-based: `--spec.eips.1=<eip-id>` (not `0`)
- `5_bgp` = Dynamic BGP EIP; `5_gray` = Dedicated load balancing (internal use)

---

## 2. List / Read / Status

```bash
# List EIPPools in namespace
hcloud CCI listCrdYangtseCniV1NamespacedEIPPool --namespace=<ns-name> --cli-region=<region> --cli-output=json

# Read a specific EIPPool
hcloud CCI readCrdYangtseCniV1NamespacedEIPPool --name=<eippool-name> --namespace=<ns-name> --cli-region=<region>

# Read EIPPool status (allocated IPs, available count)
hcloud CCI readCrdYangtseCniV1NamespacedEIPPoolStatus --name=<eippool-name> --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

Status response includes:
- `status.eips` — array of allocated EIP objects (each with `ipv4`, `id`, `status`, `bandwidthSize`)
- `status.usage` — usage string (e.g., `0/1` means 0 of 1 EIPs bound to Pods)

---

## 3. Delete EIPPool — TWO-STEP CONFIRMATION

```bash
hcloud CCI deleteCrdYangtseCniV1NamespacedEIPPool --name=<eippool-name> --namespace=<ns-name> --cli-region=<region>
```

**WARNING:** Pods currently using this EIPPool will lose their public IP access immediately. Always confirm with the user and check for active Pods referencing this EIPPool before deletion.

After deletion, the EIPPool enters Terminating state with finalizer `yangtse.io/eip-pool`. The EIPs created by the pool are released automatically.

---

## 4. Pod Usage — Assign EIP via Annotation

To associate a Pod with an EIPPool, add the annotation at Pod creation:

**Note:** The annotation key `yangtse.io/eippool` contains dots and a slash. This may encounter the same hcloud CLI dot-parsing limitation as other annotation keys. If hcloud CLI cannot pass this annotation, consider:
- Using the hyphen replacement: `--metadata.annotations.yangtse-io/eippool=<eippool-name>` (may or may not work for Pod annotations — needs testing)
- Using `--cli-jsonInput` (but note this has known issues transmitting annotations for CCI resources)

```bash
hcloud CCI createCoreV1NamespacedPod \
  --namespace=<ns-name> \
  --metadata.name=<pod-name> \
  --metadata.annotations.yangtse-io/eippool=<eippool-name> \
  --spec.containers.1.name=<container-name> \
  --spec.containers.1.image=<image> \
  --spec.containers.1.resources.limits.cpu=500m \
  --spec.containers.1.resources.limits.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json
```

For Deployment or StatefulSet, add the annotation in the Pod template:

```bash
# Deployment with EIP (hyphen workaround for annotation key)
--spec.template.metadata.annotations.yangtse-io/eippool=<eippool-name>

# StatefulSet with EIP (hyphen workaround for annotation key)
--spec.template.metadata.annotations.yangtse-io/eippool=<eippool-name>
```

---

## 5. EIPPool vs Manual EIP

| Criteria | EIPPool (CCI-native) | Manual EIP binding |
|---|---|---|
| Allocation | Automatic — Pod gets EIP on creation | Manual — create EIP then bind to resource |
| Scope | Namespace-level, pod-specific | VPC-level, resource-specific |
| Lifecycle | EIP follows Pod lifecycle (released when Pod deleted) | EIP is independent, persists until manually deleted |
| Use case | Container workloads needing public IP | VMs, load balancers, NAT gateways |
| Management | CCI CRD, managed via k8s-style API | ECS/VPC API, managed via Huawei Cloud console/CLI |
| Dynamic scaling | Yes — pool auto-assigns as pods scale | No — each EIP must be manually bound |

Use **EIPPool** for CCI workloads that need direct public IP on Pods.
Use **manual EIP** for non-container resources or when you need persistent IPs independent of Pod lifecycle.