# Pod Management

Pod lifecycle operations — bare pods (single container instance, no replica management).

---

## 1. Create Pod (Bare Pod)

```bash
hcloud CCI createCoreV1NamespacedPod \
  --namespace=<ns-name> \
  --metadata.name=<pod-name> \
  --spec.containers.1.name=<container-name> \
  --spec.containers.1.image=<image> \
  --spec.containers.1.resources.limits.cpu=500m \
  --spec.containers.1.resources.limits.memory=1Gi \
  --spec.containers.1.resources.requests.cpu=500m \
  --spec.containers.1.resources.requests.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json
```

**Prerequisites:**
- Namespace must exist before creating a Pod
- Network resource must exist in the namespace

**CCI-specific requirements:**
- `resources.limits` and `resources.requests` are MANDATORY — CCI rejects pods without resource specifications
- `resources.requests` **MUST equal** `resources.limits` (same CPU value and same memory value) — CCI rejects mismatches with `limit and request doesn't equal`
- Array items are 1-based: `--spec.containers.1.name` (not `0`)

**NOT recommended for production** — bare pods are not self-healing. Use Deployment or StatefulSet for replica management and restart policies.

---

## 2. List Pods

```bash
# List pods in a specific namespace
hcloud CCI listCoreV1NamespacedPod --namespace=<ns-name> --cli-region=<region> --cli-output=json

# List pods across all namespaces
hcloud CCI listCoreV1PodForAllNamespaces --cli-region=<region> --cli-output=json
```

**JMESPath filter example:**

```bash
hcloud CCI listCoreV1NamespacedPod \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="items[].{Name:metadata.name,Phase:status.phase,IP:status.podIP}"
```

---

## 3. Read Pod / Pod Status

```bash
# Read full Pod definition
hcloud CCI readCoreV1NamespacedPod --name=<pod-name> --namespace=<ns-name> --cli-region=<region>

# Read Pod status only
hcloud CCI readCoreV1NamespacedPodStatus --name=<pod-name> --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

**Resource existence check:** if the read reports that the Pod was not found (HTTP 404 / `not found`), tell the user **"resource does not exist"** — do not retry with guessed names and do not treat the empty result as a healthy Pod.

---

## 4. Delete Pod — TWO-STEP CONFIRMATION

### Step 1: Verify the Pod exists (mandatory pre-check)

```bash
hcloud CCI readCoreV1NamespacedPod --name=<pod-name> --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

If the read reports the Pod was not found, reply **"resource does not exist"** and **stop** — do **not** run the delete command.

### Step 2: Warn the user, then delete only after explicit confirmation

> **WARNING**: Deleting a Pod is irreversible. If the Pod is managed by a Deployment/StatefulSet, the controller recreates it, so deleting a replica Pod does not reduce the replica count — scale the controller (see [task-deployment-management.md](task-deployment-management.md)) instead.

```bash
hcloud CCI deleteCoreV1NamespacedPod --name=<pod-name> --namespace=<ns-name> --cli-region=<region>
```

---

## 5. Pod Phases

| Phase | Meaning |
|---|---|
| `Pending` | Pod accepted but containers not yet running (waiting for scheduling, image pull, etc.) |
| `Running` | Pod bound to a node and at least one container is running |
| `Succeeded` | All containers terminated successfully (won't restart) |
| `Failed` | At least one container terminated with non-zero exit code |
| `Unknown` | Pod state could not be determined (typically node communication failure) |

---

## 6. Pod with EIP Annotation (Public IP)

To assign a public IP to a Pod via EIPPool:

```bash
hcloud CCI createCoreV1NamespacedPod \
  --namespace=<ns-name> \
  --metadata.name=<pod-name> \
  --metadata.annotations.yangtse-io/eippool=<eippool-name> \
  --spec.containers.1.name=<container-name> \
  --spec.containers.1.image=<image> \
  --spec.containers.1.resources.limits.cpu=500m \
  --spec.containers.1.resources.limits.memory=1Gi \
  --spec.containers.1.resources.requests.cpu=500m \
  --spec.containers.1.resources.requests.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json
```

The Pod annotation `yangtse.io/eippool=<eippool-name>` tells CCI to allocate an EIP from the specified EIPPool to this Pod.

**Note on the annotation key:** `yangtse.io/eippool` contains a dot, so it **cannot** be passed through hcloud dot notation: writing the key in dotted form inside `--metadata.annotations.<key>=<value>` is rejected with `[USE_ERROR]不正确的参数`. Only the hyphenated key `yangtse-io/eippool` is accepted by hcloud, and it places that literal key in the request body. See [parameter-format.md](parameter-format.md) section 5 for the dot-parsing limitation and [task-eippool-management.md](task-eippool-management.md) for the Pod EIPPool caveats.