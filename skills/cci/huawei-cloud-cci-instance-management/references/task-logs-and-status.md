# Logs and Status Queries

Status reading and log viewing across all CCI resources.

---

## 1. Pod Status

```bash
hcloud CCI readCoreV1NamespacedPodStatus \
  --name=<pod-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

**Phase values:** `Pending`, `Running`, `Succeeded`, `Failed`, `Unknown`

**JMESPath quick query:**

```bash
--cli-query="status.phase"
```

---

## 2. Pod Logs

```bash
hcloud CCI readCoreV1NamespacedPodLog \
  --name=<pod-name> --namespace=<ns-name> \
  --container=<container-name> \
  --cli-region=<region>
```

**Optional parameters:**
- `--sinceSeconds=3600` — show logs from last hour (3600 seconds)
- `--limitBytes=10000` — limit output to 10000 bytes
- `--previous=true` — show logs from previous (crashed) container instance
- `--tailLines=100` — show last 100 lines

**Multi-container pods:** `--container=<container-name>` is REQUIRED when the Pod has more than one container.

---

## 3. Deployment Status

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --name=<deploy-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

**Key status fields:**
- `replicas` — desired replica count
- `readyReplicas` — pods passing readiness checks
- `availableReplicas` — pods available for service
- `updatedReplicas` — pods on the current template version

---

## 4. StatefulSet Status

```bash
hcloud CCI readAppsV1NamespacedStatefulSetStatus \
  --name=<sts-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

**Key status fields:** same as Deployment plus `currentReplicas` and `currentRevision`.

---

## 5. Network Status

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=<network-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

---

## 6. EIPPool Status

```bash
hcloud CCI readCrdYangtseCniV1NamespacedEIPPoolStatus \
  --name=<eippool-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

Shows allocated EIP count, available EIP count, and specific IP assignments.

---

## 7. Events (Diagnose Issues)

```bash
# List all events in namespace
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns-name> --cli-region=<region> --cli-output=json

# Read a specific event
hcloud CCI readCoreV1NamespacedEvent --name=<event-name> --namespace=<ns-name> --cli-region=<region>
```

Events record pod scheduling failures, image pull errors, crash loops, etc.

---

## 8. ResourceQuota

```bash
hcloud CCI listCoreV1NamespacedResourceQuota --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

Shows CPU, memory, and pod count limits for the namespace.

---

## 9. Pod Metrics

```bash
hcloud CCI listMetricsV1beta1NamespacedPodMetrics --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

Returns current CPU and memory usage per Pod.

---

## 10. Service Status

```bash
hcloud CCI readCoreV1NamespacedServiceStatus \
  --name=<svc-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

---

## 11. Wait for Pod Running Pattern

Poll Pod status until `phase=Running`:

```bash
# Check status repeatedly until Running
$phase = ""
while ($phase -ne "Running") {
  $result = hcloud CCI readCoreV1NamespacedPodStatus `
    --name=<pod-name> --namespace=<ns-name> `
    --cli-region=<region> --cli-output=json `
    --cli-query="status.phase"
  $phase = $result.Trim()
  if ($phase -ne "Running") {
    Start-Sleep -Seconds 5
  }
}
Write-Output "Pod is Running"
```

**Alternative phases to wait for:**
- `Succeeded` — for batch/job pods
- `Failed` — indicates error; stop waiting and inspect events

**Timeout pattern:** add a max iteration count to prevent infinite loops (e.g., 60 iterations × 5s = 5 minutes max).