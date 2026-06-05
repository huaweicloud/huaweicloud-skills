# StatefulSet Management

StatefulSet lifecycle operations for stateful workloads (databases, message queues, etc.).

---

## 1. Create StatefulSet

```bash
hcloud CCI createAppsV1NamespacedStatefulSet \
  --namespace=<ns-name> \
  --metadata.name=<sts-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<sts-name> \
  --spec.template.metadata.labels.app=<sts-name> \
  --spec.template.spec.containers.1.name=<container-name> \
  --spec.template.spec.containers.1.image=<image> \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.serviceName=<sts-name> \
  --cli-region=<region> \
  --cli-output=json
```

**Required fields:**
- `spec.serviceName` — headless Service name for network identity (REQUIRED for StatefulSet)
- `spec.selector.matchLabels` — must match `spec.template.metadata.labels`
- Resources (`limits`) are MANDATORY on CCI

**PVC volumeClaimTemplates example (persistent storage):**

```bash
hcloud CCI createAppsV1NamespacedStatefulSet \
  --namespace=<ns-name> \
  --metadata.name=<sts-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<sts-name> \
  --spec.template.metadata.labels.app=<sts-name> \
  --spec.template.spec.containers.1.name=<container-name> \
  --spec.template.spec.containers.1.image=<image> \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.volumeMounts.1.name=data \
  --spec.template.spec.containers.1.volumeMounts.1.mountPath=/data \
  --spec.volumeClaimTemplates.1.metadata.name=data \
  --spec.volumeClaimTemplates.1.spec.accessModes.1=ReadWriteOnce \
  --spec.volumeClaimTemplates.1.spec.resources.requests.storage=10Gi \
  --spec.volumeClaimTemplates.1.spec.storageClassName=<sc-name> \
  --spec.serviceName=<sts-name> \
  --cli-region=<region> \
  --cli-output=json
```

---

## 2. List / Read / Status

```bash
# List all StatefulSets in namespace
hcloud CCI listAppsV1NamespacedStatefulSet --namespace=<ns-name> --cli-region=<region> --cli-output=json

# Read a specific StatefulSet
hcloud CCI readAppsV1NamespacedStatefulSet --name=<sts-name> --namespace=<ns-name> --cli-region=<region>

# Read StatefulSet status only
hcloud CCI readAppsV1NamespacedStatefulSetStatus --name=<sts-name> --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

---

## 3. Update StatefulSet (Patch)

```bash
hcloud CCI patchAppsV1NamespacedStatefulSet \
  --name=<sts-name> --namespace=<ns-name> \
  --spec.template.spec.containers.1.image=<new-image> \
  --cli-region=<region>
```

Common patch operations:
- Image update: `--spec.template.spec.containers.1.image=<new-image>`
- Replica scaling: `--spec.replicas=<new-count>`

---

## 4. Delete StatefulSet — TWO-STEP CONFIRMATION

```bash
hcloud CCI deleteAppsV1NamespacedStatefulSet --name=<sts-name> --namespace=<ns-name> --cli-region=<region>
```

**WARNING:** PVCs created by volumeClaimTemplates are NOT automatically deleted when the StatefulSet is deleted. Manual cleanup is required:

```bash
hcloud CCI deleteCoreV1NamespacedPersistentVolumeClaim --name=<pvc-name> --namespace=<ns-name> --cli-region=<region>
```

Always confirm with the user before deleting a StatefulSet. List PVCs first to show what will remain.

---

## 5. StatefulSet vs Deployment — When to Use Each

| Criteria | StatefulSet | Deployment |
|---|---|---|
| Workload type | Databases, message queues, distributed storage | Web servers, APIs, microservices |
| Pod identity | Stable hostname (`<sts-name>-0`, `-1`, ...) | Random generated names |
| Pod ordering | Ordered create/delete (0→1→2) | Parallel, no ordering |
| Storage | volumeClaimTemplates per pod | Shared or no persistent storage |
| Network | Stable DNS per pod via headless Service | Single Service endpoint |
| Updates | RollingUpdate with partition support or OnDelete | RollingUpdate by default |

Use **StatefulSet** when you need: stable network identity, ordered deployment, or per-pod persistent storage.
Use **Deployment** for all other stateless workloads.

---

## 6. PVC Handling Notes

- **volumeClaimTemplates** auto-creates one PVC per replica: `<pvc-name>-<sts-name>-<ordinal>`
- PVC naming: `<volumeClaimTemplateName>-<sts-name>-0`, `-1`, etc.
- **StorageClass**: specify `--spec.volumeClaimTemplates.1.spec.storageClassName=<sc-name>`; CCI provides default if omitted
- **PVC lifecycle is independent** — deleting the StatefulSet does NOT delete PVCs
- To clean up: manually delete each PVC after the StatefulSet is removed
- **Reclaim policy**: follows StorageClass settings (Retain or Delete)