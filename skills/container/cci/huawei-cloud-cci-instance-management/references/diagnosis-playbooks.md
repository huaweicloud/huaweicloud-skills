# CCI Diagnosis Playbooks

Read-only diagnostic playbooks for the 10 high-frequency CCI ticket categories identified in
issue #506 (container-domain ticket analysis). Each playbook follows the same shape:

**Symptoms -> Read-only diagnostic commands -> How to read the output -> Conclusion / next step**

> **Read-only guarantee**: every `hcloud` operation in this file is a query operation
> (`list*` / `read*`). All of them resolve to HTTP `GET` against the CCI endpoint, verified with
> KooCLI 7.2.12 (`hcloud CCI <Operation> --help`). This file contains **no** create, replace,
> patch or delete command. Fixing an environment is a separate, explicitly confirmed action
> documented in the task references.

## Category Index

| # | Category (tickets) | Playbook | Diagnostic type |
|---|---|---|---|
| 1 | Workload - other / creation and Job submission failures (81) | [Category 1](#category-1--workload-creation-and-job-submission-failures) | CLI diagnosis |
| 2 | Workload - abnormal status, Pending / NotReady / crash (33) | [Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop) | CLI diagnosis |
| 3 | Workload - replica count and quota, OutOfpods (21) | [Category 3](#category-3--replica-count-and-quota-outofpods) | CLI diagnosis |
| 4 | Basic concepts, version / namespace / region / flavor (70) | [Category 4](#category-4--basic-concept-questions) | Knowledge + read-only inventory |
| 5 | Network management, connectivity and public access (22) | [Category 5](#category-5--network-connectivity-and-public-access) | CLI diagnosis |
| 6 | Billing rules (23) | [Category 6](#category-6--billing-rule-questions) | Knowledge / console only |
| 7 | Config center, ConfigMap / Secret / environment variables (18) | [Category 7](#category-7--config-center-configmap--secret--environment-variables) | CLI diagnosis |
| 8 | Storage management, volume mount and disk space (17) | [Category 8](#category-8--storage-mount-and-disk-space) | CLI diagnosis |
| 9 | Image registry, image pull failures and image snapshots (19) | [Category 9](#category-9--image-registry-and-image-pull-failures) | CLI diagnosis |
| 10 | Pre-sales consulting (9) | [Category 10](#category-10--pre-sales-consulting) | Knowledge only |

## Conventions Used in Every Playbook

| Item | Rule |
|---|---|
| Region | Every command needs `--cli-region=<region>`; the endpoint becomes `https://cci.<region>.myhuaweicloud.com` (confirmed with `--dryrun`) |
| Output | `--cli-output=json` for machine-readable output; `--cli-output=table` for a human view |
| Filtering | `--cli-query="<JMESPath>"` extracts a single field, e.g. `--cli-query="status.phase"` |
| Namespace scope | Namespaced operations require `--namespace=<ns>`; `listCoreV1Namespace`, `listStorageV1StorageClass`, `readStorageV1StorageClass` and `listImageSnapshots` are **not** namespaced and must not receive `--namespace` |
| Parameter names | CCI/ Kubernetes-style parameters are case-sensitive camelCase paths. VPC parameters use underscores (`--vpc_id`, `--subnet_id`), never hyphens; hcloud does not normalize `-` to `_` |
| Debug output | The debug switch is a **global** option and must be placed **before** the service name: `hcloud --debug CCI <Operation> ...`. A `cli`-prefixed debug parameter is rejected as an invalid parameter |
| Dry run | Append the global `--dryrun` option to any command to print the request that *would* be sent and skip the call. Useful for validating parameter names without touching the API |
| Missing resource | A read on a non-existent resource returns 404 / "not found". Report it plainly; never guess and never issue a mutating command to "make it work" |

## Category 1 — Workload Creation and Job Submission Failures

**Category 1 of #506 (workload / other, 81 tickets).** Deployment, Job or Volcano Job submission
is rejected, or a CCE burst-to-CCI workload never appears in CCI.

### Symptoms

- A workload create call is rejected with `[USE_ERROR]` (wrong parameter) or a 4xx API error.
- A Job or Volcano Job is accepted by the API but no Pod ever starts.
- A CCE workload configured to burst to CCI does not land in the CCI namespace.

### Diagnostic commands

```bash
# A. Did the object actually get created?
hcloud CCI listAppsV1NamespacedDeployment --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listBatchV1NamespacedJob --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listBatchVolcanoShV1alpha1NamespacedJob --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedPod --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# B. The object exists: read its status
hcloud CCI readBatchV1NamespacedJobStatus --name=<job-name> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readBatchVolcanoShV1alpha1NamespacedJob --name=<job-name> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy-name> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# C. The object was rejected: check the CCI-side preconditions read-only
hcloud CCI readCoreV1Namespace --name=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listNetworkingCciIoV1beta1NamespacedNetwork --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedResourceQuota --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| `[USE_ERROR]不正确的参数:<name>` | The parameter does not exist under that name | Re-check the exact parameter with `hcloud CCI <Operation> --help`; see [parameter-format.md](parameter-format.md) |
| Object absent from the list call | The create request never succeeded (client-side rejection) | Read the create error message; verify namespace flavor annotation and that a Network exists |
| Namespace `metadata.annotations` lacks `namespace-kubernetes.io/flavor` (the dotted canonical key) | CCI rejects namespace-scoped creation | Add the flavor annotation before creating workloads. A **hyphenated** `namespace-kubernetes-io/flavor` key in the returned annotations means the flavor was NOT applied — CCI falls back to `general-computing`. See [task-namespace-management.md](task-namespace-management.md) |
| No Network in the namespace | Workloads stay Pending or are rejected | Create the Network first: [task-network-management.md](task-network-management.md) |
| `status.used` equals `status.hard` in ResourceQuota | Namespace quota exhausted | See [Category 3](#category-3--replica-count-and-quota-outofpods) |
| Job exists, `status.active = 0` and no Pods | Scheduling or image problem | Continue with [Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop) |
| Event with `reason=FailedCreate` / `FailedScheduling` | Admission or scheduler rejection; the message carries the reason | Act on the message; quota, Network and image checks are above |
| 403 | IAM permission missing | See [iam-policies.md](iam-policies.md) |

### Conclusion / next step

1. If the object does not exist, the failure is at request-validation time. Correct the request
   and let the **user** resubmit it; this playbook does not create resources.
2. If the object exists without Pods, hand off to the Pod status playbook ([Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop)).
3. If a CCE burst workload is missing, confirm first that the Pod reached CCI at all (`listCoreV1NamespacedPod`);
   bursting configuration itself belongs to the CCE side, so verify it in the CCE console rather than here.

> **Tip (no API call)**: appending the global `--dryrun` option to the command the user intends to
> run makes KooCLI validate the parameters and print the target URL, headers and body without
> sending anything. It is the fastest way to prove a parameter name is wrong before blaming CCI.

---

## Category 2 — Workload Status Abnormal (Pending / NotReady / CrashLoop)

**Category 2 of #506 (workload / abnormal status, 33 tickets).** The Pod exists but never becomes
Ready, restarts repeatedly, or exits abnormally. Use the three-piece set: **PodStatus + Event + Log**.

### Symptoms

- `Pending`, `Unknown`, `Running` but `Ready=False`, `CrashLoopBackOff`, `OOMKilled`, `Evicted`.
- Deployment `readyReplicas` stays below `replicas`; StatefulSet replicas are not ready.

### Diagnostic commands

```bash
# 1. Pod inventory and workload status
hcloud CCI listCoreV1NamespacedPod --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPod --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedStatefulSetStatus --name=<sts> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedDeploymentScale --name=<deploy> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. Events - the reason for scheduling failures, pull errors and restarts
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# Optional server-side narrowing; if the gateway rejects this selector, list all events and filter locally
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --fieldSelector="involvedObject.name=<pod>" \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedEvent --name=<event-name> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 3. Container logs, current and previous instance
hcloud CCI readCoreV1NamespacedPodLog --name=<pod> --namespace=<ns> --container=<container> \
  --tailLines=100 --cli-region=<region>

hcloud CCI readCoreV1NamespacedPodLog --name=<pod> --namespace=<ns> --container=<container> \
  --previous=true --tailLines=100 --cli-region=<region>

# 4. Resource usage of a running Pod
hcloud CCI listMetricsV1beta1NamespacedPodMetrics --namespace=<ns> \
  --cli-region=<region> --cli-output=json
```

### How to read the output

Typical `PodStatus` fields are `status.phase`, `status.podIP`, `status.reason`,
`status.message`, `status.conditions[]` and `status.containerStatuses[]`. Extract a single field
with `--cli-query`, for example `--cli-query="status.phase"` or
`--cli-query="status.containerStatuses[0].state.waiting.reason"`. If a JMESPath returns nothing,
the field is absent from that response - fall back to the full object (`readCoreV1NamespacedPod`).

| Observation | Meaning | Next step |
|---|---|---|
| `phase=Pending`, event `FailedScheduling` / `OutOfpods` | No schedulable capacity or quota exhausted | [Category 3](#category-3--replica-count-and-quota-outofpods) |
| `phase=Pending`, no Network in namespace | CCI has no network to attach the Pod to | Create the Network: [task-network-management.md](task-network-management.md) |
| `phase=Unknown` | The instance lost contact with the control plane | Check events, then the Pod log; re-check status |
| `waiting.reason=CrashLoopBackOff` | The container starts and exits repeatedly | Read `--previous=true` logs, fix the application exit, re-check limits |
| `waiting.reason=ImagePullBackOff` / `ErrImagePull` | Image cannot be pulled | [Category 9](#category-9--image-registry-and-image-pull-failures) |
| `terminated.reason=OOMKilled` | Memory limit too small for the process | Raise the limit - and the equal request - then resubmit |
| Event `reason=Unhealthy`, `Liveness probe failed` | Probe configuration or application startup time | Fix probe timings or the application; check logs |
| Event `reason=Evicted` with `ephemeral-storage` | Local disk pressure | [Category 8](#category-8--storage-mount-and-disk-space) |
| `status.podIP` empty | Pod never obtained a network address | Network/Network status check in [Category 5](#category-5--network-connectivity-and-public-access) |
| `listMetricsV1beta1NamespacedPodMetrics` usage close to the limit | The container is about to be throttled or killed | Raise limits/requests together; CCI requires `limits == requests` |

### Conclusion / next step

Report the root cause as **phase + reason + the matching event message + the log line**, not just
"the Pod is not Ready". Exit-code, OOM and probe findings are application or sizing issues; missing
Network, quota and image failures are platform-side and link to the corresponding categories.
Recreating the Pod is a mutating action and must be confirmed by the user first.

---

## Category 3 — Replica Count and Quota (OutOfpods)

**Category 3 of #506 (workload / replica count, 21 tickets).** Requested replicas do not reach the
`Ready` state or the namespace reports `OutOfpods` / insufficient quota.

### Symptoms

- `OutOfpods`, `exceeded quota`, `insufficient cpu/memory` in events.
- Deployment scale set to N but only M < N pods exist or are ready.
- Requests to raise the namespace ceiling.

### Diagnostic commands

```bash
# 1. Namespace quota: hard limit versus used amount
hcloud CCI listCoreV1NamespacedResourceQuota --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedResourceQuota --name=<quota-name> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. Desired versus actual replica count
hcloud CCI readAppsV1NamespacedDeploymentScale --name=<deploy> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedStatefulSetStatus --name=<sts> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 3. Pods actually running, and the owner chain
hcloud CCI listCoreV1NamespacedPod --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listAppsV1NamespacedReplicaSet --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedReplicaSet --name=<rs> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 4. Why the extra replicas were refused
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| `status.hard` vs `status.used`: `used` equals `hard` for `pods`, `requests.cpu` or `requests.memory` | Namespace quota exhausted | Report which resource is exhausted; request a quota increase in the CCI console (the quota is a namespace attribute, not a CLI-managed object) |
| Event `reason=OutOfpods` | Pod count ceiling reached | Same as above, or reduce replicas |
| Deployment `status.replicas < spec.replicas` with no quota pressure | Pods are blocked elsewhere | Continue with [Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop) |
| `status.readyReplicas < status.replicas` but pods exist and are Running | Readiness probe failing | Check probe and application logs |
| ReplicaSet exists but owns no Pods | Creation of Pods for that ReplicaSet is failing | Read events for `FailedCreate` |
| Requested per-Pod resources exceed the remaining quota headroom | Even one Pod cannot fit | Lower per-Pod `requests`/`limits` (kept equal) or raise the quota |

### Conclusion / next step

Distinguish the three cases explicitly: **ceiling reached** (quota or `OutOfpods`),
**Pods not schedulable** ([Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop)), or **Pods running but not Ready** (probe/application).
This skill only reads the numbers. Quota increases and replica changes are mutations: show the
current values, explain the ceiling, and let the user confirm the change.

---

## Category 4 — Basic Concept Questions

**Category 4 of #506 (basic concepts, 70 tickets).** Knowledge questions about CCI versions,
namespaces, region availability and flavors/specifications. These are answered from the official
documentation and the console; **no CLI command is invented for them.**

### Symptoms / question shapes

- "What is the difference between CCI 1.0 and 2.0?"
- "Which regions support CCI / this flavor?"
- "What does a namespace mean here, and which flavor should I use?"
- "Is Kunpeng (ARM) or a specific specification supported?"

### Read-only inventory commands (environment facts only)

These confirm facts about the user's own environment. They do not answer product questions.

```bash
# Which namespaces exist in this region, and what flavor each one carries
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json

# One namespace in detail: flavor annotation, labels, status phase
hcloud CCI readCoreV1Namespace --name=<ns> --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning |
|---|---|
| `metadata.annotations` contains `namespace.kubernetes.io/flavor` (dotted canonical key) | The namespace is bound to that flavor (`general-computing`, `gpu-accelerated`) |
| `metadata.annotations` contains only the **hyphenated** `namespace-kubernetes-io/flavor` key | The flavor was **not** applied — CCI falls back to `general-computing`. Recreate the namespace with the helper script (see [task-namespace-management.md](task-namespace-management.md)) |
| `status.phase` of the namespace | `Active` means usable; anything else means the namespace is still provisioning or failing |
| Namespace not returned by the list call but `--cli-region` was correct | The namespace does not exist in that region |

### Authoritative sources for the concept answers

| Question | Where the answer comes from |
|---|---|
| CCI 1.0 vs 2.0 feature differences | Official CCI documentation: <https://support.huaweicloud.com/cci/index.html> |
| Region / flavor availability | The CCI console region selector and the official documentation; never answer from memory |
| Namespace semantics, isolation, flavors | Official documentation plus the read-only inventory above |
| Kunpeng / specification support | Official documentation and the console purchase page; do not assert CPU architecture support without a source |

One verified technical distinction that is safe to state: the Kubernetes-compatible resources
(Pod, Deployment, Namespace, ConfigMap, ...) are served from `/api/v1/...` and `/apis/apps/v1/...`,
while CCI-native v2 resources such as ImageSnapshot are served from `/apis/cci/v2/imagesnapshots`.
Both paths were confirmed with `--dryrun` on KooCLI 7.2.12.

### Conclusion / next step

Answer with a citation to the official page, then confirm the concrete environment facts with the
two read-only queries above. If the documentation does not cover the question, say so and route the
user to a service ticket - do not guess.

---

## Category 5 — Network Connectivity and Public Access

**Category 5 of #506 (network management, 22 tickets).** Pods cannot reach the network, the
service is unreachable, public access fails, or the load balancer returns 5xx.

### Symptoms

- Workloads stuck `Pending` because the namespace has no Network.
- Service has no backend / no address; Ingress has no ingress address.
- A Pod cannot obtain a public IP; EIPPool shows no free EIP.
- ELB returns 502/503/504 or 5xx for CCI backends.

### Diagnostic commands

```bash
# 1. Network of the namespace
hcloud CCI listNetworkingCciIoV1beta1NamespacedNetwork --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus --name=<network> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. Service and its endpoints
hcloud CCI listCoreV1NamespacedService --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedService --name=<service> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedServiceStatus --name=<service> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedEndpoints --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 3. Ingress / external entry
hcloud CCI listExtensionsV1beta1NamespacedIngress --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readExtensionsV1beta1NamespacedIngressStatus --name=<ingress> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 4. Public IP allocation for Pods
hcloud CCI listCrdYangtseCniV1NamespacedEIPPool --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCrdYangtseCniV1NamespacedEIPPoolStatus --name=<eippool> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 5. Pod-side address and state (which Pod is actually behind the Service)
hcloud CCI listCoreV1NamespacedPod --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 6. VPC side of the mapping (read-only; note the underscore in --vpc_id / --subnet_id)
hcloud VPC ShowVpc --vpc_id=<vpc-id> --cli-region=<region> --cli-output=json

hcloud VPC ListSubnets --vpc_id=<vpc-id> --cli-region=<region> --cli-output=json

hcloud VPC ShowSubnet --subnet_id=<subnet-id> --cli-region=<region> --cli-output=json

# 7. Optional cross-service read: EIP state of the account (EIP service, read-only)
hcloud EIP ListPublicips --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| `listNetworkingCciIoV1beta1NamespacedNetwork` returns nothing | The namespace has no Network | Create the Network first: [task-network-management.md](task-network-management.md) |
| Network status not `Active` | Network still provisioning or failed | Re-check status; if it stays non-Active, read the namespace events |
| `Endpoints` for the Service has no `subsets` / no addresses | The Service selector matches no ready Pod | Compare `spec.selector` with the Pod labels; then check Pod readiness ([Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop)) |
| Service `status.loadBalancer.ingress` empty | The ELB has not been provisioned or bound yet | Re-check; ELB provisioning status is visible in the ELB console |
| Ingress status without an address | No ELB bound to the Ingress | Check the Ingress annotations/class against the official documentation and the ELB console |
| EIPPool status shows zero available EIPs | No free public IP for Pods | Free an EIP or enlarge the pool (mutation, needs confirmation); see [task-eippool-management.md](task-eippool-management.md) |
| Pod `status.podIP` empty | Pod has no address yet | Workload status playbook ([Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop)) |
| Subnet CIDR is `10.247.0.0/16` | Reserved for CCI internal routing; causes conflicts | Use another CIDR for the VPC/subnet |
| ELB returns 5xx while Pods are Ready and endpoints are populated | The failure is in the ELB layer, outside this skill's scope | Route the user to the ELB console (listener, health check, backend group) and to the ELB documentation |

### Conclusion / next step

Work from the inside out: **Network exists and Active -> Pod has an address -> Service selector
matches ready Pods -> Endpoints populated -> Service/Ingress has an external address**. Stop at the
first broken link and report it. Creating/fixing Network objects, EIP pools or ELB listeners are
mutations and are not part of this playbook.

---

## Category 6 — Billing Rule Questions

**Category 6 of #506 (billing rules, 23 tickets).** These are consulting questions. **No CLI
command is fabricated for billing**, and this skill never states a price - prices change and must
always be quoted from the official pricing page or the billing console.

### Question shapes

| Question | Where to look (authoritative) |
|---|---|
| How is CCI metered / what is the billing unit? | Billing Center **Bills** page for the actual charge lines, plus the CCI price details page. Do not answer from memory |
| Resource package (套餐包) usage, remaining quota, refund | Billing Center -> Resource Packages; refund eligibility follows the documented policy on that page |
| How to switch to yearly/monthly subscription | Billing Center / product console order flow |
| "I deleted the workload but I am still being charged" | See the check list below |

### Read-only checks for "deleted but still charged"

```bash
# CCI-side leftovers that keep generating charges
hcloud CCI listCrdYangtseCniV1NamespacedEIPPool --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedPersistentVolumeClaim --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedService --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedPod --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# The EIP that an EIPPool created is billed by the EIP service
hcloud EIP ListPublicips --cli-region=<region> --cli-output=json
```

| Finding | Why it can still bill |
|---|---|
| EIPPool still exists | Creating an EIPPool auto-creates EIPs, and EIPs are billed separately even when idle |
| PVC still exists | The underlying EVS/SFS capacity is billed while the volume exists |
| A `LoadBalancer` type Service still exists | It implies an ELB instance, billed by the ELB service - confirm in the ELB console / bill |
| Nothing left in CCI but a charge line remains | Billing settles with a delay; also check other services in the same account in the Bills page |

### Conclusion / next step

Explain the mechanism (leftover billable resources and billing settlement delay), then show the
user the exact bill lines in the Billing Center. Quote prices only from the official pricing page or
console. Billing documentation home: <https://support.huaweicloud.com/billing/index.html>.

---

## Category 7 — Config Center (ConfigMap / Secret / Environment Variables)

**Category 7 of #506 (config center, 18 tickets).** A Pod cannot start or behaves incorrectly
because a ConfigMap, Secret, or environment variable reference is wrong.

### Symptoms

- Pod event `CreateContainerConfigError`, `configmap not found`, `secret not found`.
- Container starts with an unexpected configuration.
- `ImagePullBackOff` caused by a missing image pull secret.

### Diagnostic commands

```bash
# 1. What exists in this namespace
hcloud CCI listCoreV1NamespacedConfigMap --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedSecret --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. What the workload actually references
hcloud CCI readCoreV1NamespacedConfigMap --name=<configmap> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedSecret --name=<secret> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPod --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 3. The failure reason recorded by the platform
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| Event `reason=CreateContainerConfigError` | The referenced ConfigMap/Secret or key is missing | Compare the referenced name and key with the `list`/`read` output |
| The ConfigMap exists but in a **different** namespace | A Pod can only use objects from its own namespace | Recreate/reference it in the Pod namespace (a user-side action) |
| `data` keys present but a different key name | Key mismatch (`env.name` / `valueFrom.configMapKeyRef.key`) | Report the exact expected versus actual keys |
| Secret type or `imagePullSecrets` mismatch | Private registry credentials cannot be used | [Category 9](#category-9--image-registry-and-image-pull-failures) |
| `envFrom` used but the ConfigMap has no matching keys | Variables silently missing | Prefer explicit `valueFrom` keys or correct the ConfigMap keys |
| The Pod object does not show the expected `volumes`/`env` entries | The manifest never carried the reference | The manifests need to be corrected before resubmission |

### Security note

`readCoreV1NamespacedSecret` returns encoded values. Check **key names, types and existence only**.
Never copy Secret contents into chat, tickets or logs, and never expose credentials - see
[credential-configuration.md](credential-configuration.md).

### Conclusion / next step

Read-only inspection of ConfigMap/Secret is in scope here for diagnosis. Creating, updating or
deleting those objects is outside this skill's management scope: change them in the CCI console or
in the user's own manifests, then re-run the checks above.

---

## Category 8 — Storage Mount and Disk Space

**Category 8 of #506 (storage management, 17 tickets).** A volume fails to mount; the workload
stays Pending on storage; or the container runs out of local disk.

### Symptoms

- PVC stuck in `Pending`; Pods stuck `ContainerCreating`.
- Events `FailedMount`, `FailedAttachVolume`, `volume not found`.
- Evictions caused by `ephemeral-storage` pressure.

### Diagnostic commands

```bash
# 1. Claims in the namespace and their phase
hcloud CCI listCoreV1NamespacedPersistentVolumeClaim --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPersistentVolumeClaim --name=<pvc> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. Available storage classes (cluster-scoped: no --namespace)
hcloud CCI listStorageV1StorageClass --cli-region=<region> --cli-output=json

hcloud CCI readStorageV1StorageClass --name=<storage-class> --cli-region=<region> --cli-output=json

# 3. Pod side: mounts and container state
hcloud CCI readCoreV1NamespacedPod --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedSecret --name=<obs-secret> --namespace=<ns> \
  --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| PVC `status.phase=Pending` | The claim was not provisioned / bound | Read the events and the PVC status message; check the StorageClass exists and is the intended one |
| Event `FailedMount` / `FailedAttachVolume` | The volume cannot be attached to the instance | Read the exact message; it names the failing storage service or resource |
| StorageClass list empty | No default provisioner available in this region | Confirm the supported storage types and their StorageClass names in the official documentation |
| Event mentions an OBS secret or AK/SK | The OBS mount credentials are missing or invalid | Check that the Secret exists (key names only) and that credentials are current |
| Event `reason=Evicted`, message `ephemeral-storage` | Local disk pressure on the instance | Reduce local writes or raise the ephemeral-storage request, then re-check |
| Pod `status.phase=Running` and the mount is present | The mount path is fine; the problem is inside the container | Read the Pod log |

### Conclusion / next step

Separate the three storage failure shapes: **claim not bound** (StorageClass / provisioning),
**mount failed** (volume or credentials), and **disk full** (ephemeral storage). EVS, SFS and OBS
resource status lives in those services' consoles - route the user there with the exact volume or
bucket name found in the events. This playbook never resizes, creates or deletes storage.

---

## Category 9 — Image Registry and Image Pull Failures

**Category 9 of #506 (image registry, 19 tickets).** `Back-off pulling image`, private registry
authentication errors, and image snapshot questions.

### Symptoms

- Pod `waiting.reason=ImagePullBackOff` / `ErrImagePull`.
- Events with `Failed to pull image`, `401 Unauthorized`, `manifest unknown`, `i/o timeout`.
- Long image pull times; questions about ImageSnapshot.

### Diagnostic commands

```bash
# 1. The pull failure and its exact message
hcloud CCI listCoreV1NamespacedEvent --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readCoreV1NamespacedPod --name=<pod> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 2. What image the workload actually asks for
hcloud CCI listAppsV1NamespacedDeployment --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI listAppsV1NamespacedReplicaSet --namespace=<ns> \
  --cli-region=<region> --cli-output=json

hcloud CCI readAppsV1NamespacedReplicaSet --name=<rs> --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 3. Registry credentials referenced by the Pod
hcloud CCI listCoreV1NamespacedSecret --namespace=<ns> \
  --cli-region=<region> --cli-output=json

# 4. Container log of the previous instance (start-up failures, not pull errors)
hcloud CCI readCoreV1NamespacedPodLog --name=<pod> --namespace=<ns> --container=<container> \
  --previous=true --tailLines=100 --cli-region=<region>

# 5. CCI image snapshots (region-scoped: this operation has no --namespace parameter)
hcloud CCI listImageSnapshots --cli-region=<region> --cli-output=json
```

### How to read the output

| Observation | Meaning | Next step |
|---|---|---|
| Event `Failed to pull image ... 401 Unauthorized` / `403` | Registry credentials missing or expired | Ensure an `imagePullSecrets` entry exists ([Category 7](#category-7--config-center-configmap--secret--environment-variables)) and that the Secret is valid |
| Event `manifest unknown` / `not found` | Wrong repository or tag | Compare the image string in the workload with the actual repository/tag |
| Event `i/o timeout` / `dial tcp ... timeout` | The registry cannot be reached from CCI | Confirm the registry endpoint and network path in the registry console/documentation; private network access may need the documented VPC endpoint configuration |
| Pull takes very long but eventually succeeds | Large image / slow path | Consider an image snapshot to shorten cold start |
| Pod events show no pull error but the container exits | Not a registry problem | Use the previous-instance log and [Category 2](#category-2--workload-status-abnormal-pending--notready--crashloop) |
| `listImageSnapshots` output | Snapshots visible to the account in the region | Confirm the intended snapshot exists and is usable before blaming image sizes |

`listImageSnapshots` is a CCI-native v2 API served from `/apis/cci/v2/imagesnapshots` and accepts
**only** `--cli-region` (both facts confirmed with `--help` and `--dryrun` on KooCLI 7.2.12).

### Conclusion / next step

Classify the failure as **credentials** (401/403), **image reference** (not found / manifest
unknown), or **network path** (timeout). Registry-side objects (organizations, repositories,
permissions, VPC endpoints) belong to the registry console and its documentation - navigate the user
there with the exact image name found in the event. Never echo registry credentials.

---

## Category 10 — Pre-Sales Consulting

**Category 10 of #506 (pre-sales, 9 tickets).** Public beta / GA status, specification and price
comparison, and CCI versus CCE selection. **These are knowledge questions - no CLI command is
fabricated and no price may be promised by this skill.**

### Question shapes and authoritative sources

| Question | Where the answer comes from |
|---|---|
| Is feature X in public beta or GA? | The CCI console (feature visibility and banners) and the official CCI documentation / service announcements |
| Specification list and current prices | The official CCI price details page and the price calculator on the Huawei Cloud website; quote only what the page shows today |
| CCI versus CCE selection | The official product introductions plus the selection questions below |
| Purchase consultation / volume discount | The pre-sales channel (Huawei Cloud consultation / service ticket), not this skill |

### Selection questions to ask the user (qualitative, no numbers)

| Question | Points toward |
|---|---|
| Do you want to manage cluster nodes, node pools and Kubernetes add-ons yourself? | Full cluster control -> CCE |
| Do you want to run containers without managing any node or cluster? | Serverless container instances -> CCI |
| Do you need cluster-level extensions (custom CNI/CSI, operators, custom schedulers)? | CCE |
| Is the workload a straightforward container image plus a Network and storage mount? | CCI |
| Do you need to compare cost for a specific specification? | Direct the user to the price calculator and the CCI price details page; never estimate |

### Conclusion / next step

Answer with a link to the authoritative page, state clearly that prices and beta status change, and
let the user confirm the current numbers on the price page. Escalate to the pre-sales channel for
commercial commitments. Do not use this skill to promise a price, a discount, or a GA date.

---

## Verified Read-Only Operation Reference

Every operation below was verified with `hcloud CCI <Operation> --help --cli-region=cn-north-4`
on KooCLI 7.2.12; the HTTP method is `GET` for all of them. Parameter lists are the exact
operations parameter sets reported by `--help` (global options such as `--cli-region`,
`--cli-output`, `--cli-query`, `--dryrun` are always accepted).

| Operation | Method | Operation-specific parameters |
|---|---|---|
| `listCoreV1Namespace` | GET | - |
| `readCoreV1Namespace` | GET | `--name` |
| `listCoreV1NamespacedPod` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedPod` | GET | `--name --namespace` |
| `readCoreV1NamespacedPodStatus` | GET | `--name --namespace` |
| `readCoreV1NamespacedPodLog` | GET | `--name --namespace --container --previous --tailLines --sinceSeconds --limitBytes --timestamps --follow` |
| `listCoreV1NamespacedEvent` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedEvent` | GET | `--name --namespace` |
| `listCoreV1NamespacedResourceQuota` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedResourceQuota` | GET | `--name --namespace` |
| `listCoreV1NamespacedConfigMap` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedConfigMap` | GET | `--name --namespace` |
| `listCoreV1NamespacedSecret` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedSecret` | GET | `--name --namespace` |
| `listCoreV1NamespacedService` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedService` | GET | `--name --namespace` |
| `readCoreV1NamespacedServiceStatus` | GET | `--name --namespace` |
| `listCoreV1NamespacedEndpoints` | GET | `--namespace`, list selectors |
| `listCoreV1NamespacedPersistentVolumeClaim` | GET | `--namespace`, list selectors |
| `readCoreV1NamespacedPersistentVolumeClaim` | GET | `--name --namespace` |
| `listStorageV1StorageClass` | GET | - |
| `readStorageV1StorageClass` | GET | `--name` |
| `listMetricsV1beta1NamespacedPodMetrics` | GET | `--namespace`, list selectors |
| `listAppsV1NamespacedDeployment` | GET | `--namespace`, list selectors |
| `readAppsV1NamespacedDeploymentStatus` | GET | `--name --namespace` |
| `readAppsV1NamespacedDeploymentScale` | GET | `--name --namespace` |
| `listAppsV1NamespacedStatefulSet` | GET | `--namespace`, list selectors |
| `readAppsV1NamespacedStatefulSetStatus` | GET | `--name --namespace` |
| `listAppsV1NamespacedReplicaSet` | GET | `--namespace`, list selectors |
| `readAppsV1NamespacedReplicaSet` | GET | `--name --namespace` |
| `listBatchV1NamespacedJob` | GET | `--namespace`, list selectors |
| `readBatchV1NamespacedJob` | GET | `--name --namespace` |
| `readBatchV1NamespacedJobStatus` | GET | `--name --namespace` |
| `listBatchVolcanoShV1alpha1NamespacedJob` | GET | `--namespace`, list selectors |
| `readBatchVolcanoShV1alpha1NamespacedJob` | GET | `--name --namespace` |
| `listNetworkingCciIoV1beta1NamespacedNetwork` | GET | `--namespace`, list selectors |
| `readNetworkingCciIoV1beta1NamespacedNetworkStatus` | GET | `--name --namespace` |
| `listExtensionsV1beta1NamespacedIngress` | GET | `--namespace`, list selectors |
| `readExtensionsV1beta1NamespacedIngressStatus` | GET | `--name --namespace` |
| `listCrdYangtseCniV1NamespacedEIPPool` | GET | `--namespace`, list selectors |
| `readCrdYangtseCniV1NamespacedEIPPoolStatus` | GET | `--name --namespace` |
| `listImageSnapshots` | GET | - (no `--namespace`) |

"list selectors" means the read-only list options reported by `--help`: `--fieldSelector`,
`--labelSelector`, `--limit`, `--continue`, `--resourceVersion`, `--resourceVersionMatch`,
`--timeoutSeconds`, `--watch`, `--allowWatchBookmarks`, `--pretty`.

Read-only VPC/EIP helper queries used by the network and billing playbooks (verified with their own
service help, all `GET`):

| Operation | Method | Operation-specific parameters |
|---|---|---|
| `hcloud VPC ShowVpc` | GET | `--vpc_id` |
| `hcloud VPC ListSubnets` | GET | `--vpc_id --limit --marker` |
| `hcloud VPC ShowSubnet` | GET | `--subnet_id` |
| `hcloud EIP ListPublicips` | GET | list filters (optional) |

## Related References

| Document | Use |
|---|---|
| [task-logs-and-status.md](task-logs-and-status.md) | The underlying status and log query commands |
| [troubleshooting.md](troubleshooting.md) | Error-message oriented troubleshooting plus the category index |
| [task-network-management.md](task-network-management.md) | Network lifecycle, required fields and annotations |
| [task-eippool-management.md](task-eippool-management.md) | EIPPool fields and public IP behavior |
| [parameter-format.md](parameter-format.md) | hcloud parameter syntax rules |
| [iam-policies.md](iam-policies.md) | Permissions required by the queries above |
| [credential-configuration.md](credential-configuration.md) | Credential handling rules |
| [cci-operation-catalog.md](cci-operation-catalog.md) | Complete CCI operation catalogue |
