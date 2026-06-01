# CCI Common Workflows

Complete end-to-end workflow sequences with actual `hcloud` commands. Default region: `cn-north-4`.

## Critical Notes

- **Network creation requires a Python helper script**: The annotation key `network.alpha.kubernetes.io/default-security-group` contains dots that `hcloud` CLI cannot pass as parameter names. Use `cci_network_helper.py` from the `scripts/` directory for Network creation.
- **Namespace creation**: Use hyphens instead of dots in annotation keys, e.g. `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` (CCI auto-normalizes hyphenated keys back to canonical dotted form for Namespace resources).
- **Deployment/Pod/StatefulSet**: CCI requires **limits == requests** for container resources. If limits != requests, creation fails with "limit and request doesn't equal" error. Always set requests to the same values as limits.
- **EIPPool creation**: Requires `--apiVersion=crd.yangtse.cni/v1` and `--kind=EIPPool` (mandatory). Also requires `--spec.eipAttributes.networkType` and all bandwidth fields (`shareType`, `size`, `chargeMode`, `name`).
- **Annotation keys containing dots**: Keys like `yangtse.io/eippool` must use hyphen replacement (`yangtse-io/eippool`) when passed via hcloud CLI.

---

## Workflow 1: Create and Run a Deployment

### Step 1: Create Namespace

```bash
hcloud CCI createCoreV1Namespace \
  --metadata.name=my-ns \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=cn-north-4
```

### Step 2: Create Network (requires VPC/subnet — use Python helper)

The Network spec requires these fields: `attachedVPC`, `subnetID`, `networkType`, and **`networkID`** (the neutron network ID of the VPC subnet). Because annotation keys with dots cannot be passed via hcloud CLI, use the helper script.

**Step 2a: Get VPC subnet details (including neutron_network_id)**

```bash
hcloud VPC ShowSubnet \
  --vpc_id=vpc-def456 \
  --subnet_id=subnet-abc123 \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Extract `neutron_network_id` from the response.

**Step 2b: Create Network via Python helper script**

```bash
python scripts/cci_network_helper.py create \
  --namespace=my-ns \
  --name=my-network \
  --vpc-id=vpc-def456 \
  --subnet-id=subnet-abc123 \
  --network-id=<neutron-network-id> \
  --security-group-id=<sg-id> \
  --region=cn-north-4
```

**Step 2c: Check Network status until Active**

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=my-network \
  --namespace=my-ns \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Repeat until `status.phase` is `Active`.

### Step 3: Create Deployment

```bash
hcloud CCI createAppsV1NamespacedDeployment \
  --namespace=my-ns \
  --metadata.name=my-deploy \
  --metadata.annotations.network-alpha-kubernetes-io/default-network=my-network \
  --spec.replicas=2 \
  --spec.selector.matchLabels.app=my-deploy \
  --spec.template.metadata.labels.app=my-deploy \
  --spec.template.spec.containers.1.name=nginx \
  --spec.template.spec.containers.1.image=nginx:latest \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=500m \
  --spec.template.spec.containers.1.resources.requests.memory=1Gi \
  --spec.template.spec.containers.1.ports.1.containerPort=80 \
  --cli-region=cn-north-4
```

### Step 4: Verify Deployment Status (poll until readyReplicas > 0)

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --namespace=my-ns \
  --name=my-deploy \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Repeat until `status.readyReplicas` equals `spec.replicas`.

### Step 5: View Pod Logs

```bash
hcloud CCI listCoreV1NamespacedPod \
  --namespace=my-ns \
  --cli-region=cn-north-4 \
  --cli-output=json
```

```bash
hcloud CCI readCoreV1NamespacedPodLog \
  --namespace=my-ns \
  --name=<pod-name> \
  --cli-region=cn-north-4
```

---

## Workflow 2: Create a Pod with Public IP (EIPPool)

### Step 1: Create Namespace

```bash
hcloud CCI createCoreV1Namespace \
  --metadata.name=eip-ns \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=cn-north-4
```

### Step 2: Create Network (use Python helper)

**Step 2a: Get VPC subnet details**

```bash
hcloud VPC ShowSubnet \
  --vpc_id=vpc-def456 \
  --subnet_id=subnet-abc123 \
  --cli-region=cn-north-4 \
  --cli-output=json
```

**Step 2b: Create Network via Python helper script**

```bash
python scripts/cci_network_helper.py create \
  --namespace=eip-ns \
  --name=eip-network \
  --vpc-id=vpc-def456 \
  --subnet-id=subnet-abc123 \
  --network-id=<neutron-network-id> \
  --security-group-id=<sg-id> \
  --region=cn-north-4
```

**Step 2c: Check Network status until Active**

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=eip-network \
  --namespace=eip-ns \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Repeat until `status.phase` is `Active`.

### Step 3: Create EIPPool

```bash
hcloud CCI createCrdYangtseCniV1NamespacedEIPPool \
  --namespace=eip-ns \
  --apiVersion=crd.yangtse.cni/v1 \
  --kind=EIPPool \
  --metadata.name=my-eippool \
  --spec.amount=1 \
  --spec.eipAttributes.networkType=5_bgp \
  --spec.eipAttributes.ipVersion=4 \
  --spec.eipAttributes.bandwidth.shareType=PER \
  --spec.eipAttributes.bandwidth.size=5 \
  --spec.eipAttributes.bandwidth.chargeMode=bandwidth \
  --spec.eipAttributes.bandwidth.name=eip-bw \
  --cli-region=cn-north-4
```

### Step 4: Create Pod with EIPPool Annotation

```bash
hcloud CCI createCoreV1NamespacedPod \
  --namespace=eip-ns \
  --metadata.name=eip-pod \
  --metadata.annotations.network-alpha-kubernetes-io/default-network=eip-network \
  --metadata.annotations.yangtse-io/eippool=my-eippool \
  --spec.containers.1.name=nginx \
  --spec.containers.1.image=nginx:latest \
  --spec.containers.1.resources.limits.cpu=500m \
  --spec.containers.1.resources.limits.memory=1Gi \
  --spec.containers.1.ports.1.containerPort=80 \
  --cli-region=cn-north-4
```

### Step 5: Verify Pod Status and EIP Allocation

```bash
hcloud CCI readCoreV1NamespacedPodStatus \
  --namespace=eip-ns \
  --name=eip-pod \
  --cli-region=cn-north-4 \
  --cli-output=json
```

```bash
hcloud CCI readCrdYangtseCniV1NamespacedEIPPoolStatus \
  --namespace=eip-ns \
  --name=my-eippool \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Check `status.eips` for the allocated public IP address.

---

## Workflow 3: Scale a Deployment

### Step 1: Read Current Deployment Scale

```bash
hcloud CCI readAppsV1NamespacedDeploymentScale \
  --namespace=my-ns \
  --name=my-deploy \
  --cli-region=cn-north-4 \
  --cli-output=json
```

### Step 2: Patch Scale to New Replica Count

```bash
hcloud CCI patchAppsV1NamespacedDeploymentScale \
  --namespace=my-ns \
  --name=my-deploy \
  --spec.replicas=5 \
  --cli-region=cn-north-4
```

### Step 3: Verify New Replicas Are Ready

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --namespace=my-ns \
  --name=my-deploy \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Repeat until `status.readyReplicas >= 5`.

---

## Workflow 4: Update Deployment Image (Rolling Update)

### Step 1: Read Current Deployment

```bash
hcloud CCI readAppsV1NamespacedDeployment \
  --namespace=my-ns \
  --name=my-deploy \
  --cli-region=cn-north-4 \
  --cli-output=json
```

### Step 2: Patch Container Image

```bash
hcloud CCI patchAppsV1NamespacedDeployment \
  --namespace=my-ns \
  --name=my-deploy \
  --spec.template.spec.containers.1.image=nginx:1.25 \
  --cli-region=cn-north-4
```

### Step 3: Monitor Rolling Update Status

```bash
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --namespace=my-ns \
  --name=my-deploy \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Monitor until:
- `status.updatedReplicas == spec.replicas`
- `status.readyReplicas == spec.replicas`
- `status.oldReplicas == 0` (if present)

---

## Workflow 5: Full Cleanup (Delete All Resources)

### Step 1: Delete All Deployments/StatefulSets/Pods

```bash
hcloud CCI deleteAppsV1CollectionNamespacedDeployment \
  --namespace=my-ns \
  --cli-region=cn-north-4

hcloud CCI deleteAppsV1CollectionNamespacedStatefulSet \
  --namespace=my-ns \
  --cli-region=cn-north-4

hcloud CCI deleteCoreV1CollectionNamespacedPod \
  --namespace=my-ns \
  --cli-region=cn-north-4
```

### Step 2: Delete All EIPPools

```bash
hcloud CCI listCrdYangtseCniV1NamespacedEIPPool \
  --namespace=my-ns \
  --cli-region=cn-north-4 \
  --cli-output=json

hcloud CCI deleteCrdYangtseCniV1NamespacedEIPPool \
  --namespace=my-ns \
  --name=<eippool-name> \
  --cli-region=cn-north-4
```

### Step 3: Delete Network

Network deletion works via hcloud CLI with two-step confirmation:

```bash
hcloud CCI deleteNetworkingCciIoV1beta1NamespacedNetwork \
  --name=my-network \
  --namespace=my-ns \
  --cli-region=cn-north-4
```

### Step 4: Delete Namespace

```bash
hcloud CCI deleteCoreV1Namespace \
  --name=my-ns \
  --cli-region=cn-north-4
```

**Important**: Deleting a namespace cascades deletion of ALL resources within it (Deployments, Pods, Networks, EIPPools, etc.). The simplest cleanup approach is to delete the namespace directly:

```bash
hcloud CCI deleteCoreV1Namespace \
  --name=my-ns \
  --cli-region=cn-north-4
```

This is equivalent to Steps 1-4 combined, but the namespace and all its contents must be fully deleted before the namespace name can be reused.

---

## Workflow 6: Create StatefulSet with PVC

### Step 1: Create Namespace + Network

```bash
hcloud CCI createCoreV1Namespace \
  --metadata.name=ss-ns \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=cn-north-4
```

**Create Network via Python helper script**:

```bash
hcloud VPC ShowSubnet \
  --vpc_id=vpc-def456 \
  --subnet_id=subnet-abc123 \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Extract `neutron_network_id` from the response.

```bash
python scripts/cci_network_helper.py create \
  --namespace=ss-ns \
  --name=ss-network \
  --vpc-id=vpc-def456 \
  --subnet-id=subnet-abc123 \
  --network-id=<neutron-network-id> \
  --security-group-id=<sg-id> \
  --region=cn-north-4
```

Check Network status until Active:

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=ss-network \
  --namespace=ss-ns \
  --cli-region=cn-north-4 \
  --cli-output=json
```

### Step 2: Create StatefulSet with volumeClaimTemplates

```bash
hcloud CCI createAppsV1NamespacedStatefulSet \
  --namespace=ss-ns \
  --metadata.name=my-statefulset \
  --metadata.annotations.network-alpha-kubernetes-io/default-network=ss-network \
  --spec.replicas=3 \
  --spec.selector.matchLabels.app=my-statefulset \
  --spec.serviceName=my-statefulset \
  --spec.template.metadata.labels.app=my-statefulset \
  --spec.template.spec.containers.1.name=mysql \
  --spec.template.spec.containers.1.image=mysql:5.7 \
  --spec.template.spec.containers.1.resources.limits.cpu=1 \
  --spec.template.spec.containers.1.resources.limits.memory=2Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=1 \
  --spec.template.spec.containers.1.resources.requests.memory=2Gi \
  --spec.template.spec.containers.1.ports.1.containerPort=3306 \
  --spec.template.spec.containers.1.volumeMounts.1.name=data \
  --spec.template.spec.containers.1.volumeMounts.1.mountPath=/var/lib/mysql \
  --spec.volumeClaimTemplates.1.metadata.name=data \
  --spec.volumeClaimTemplates.1.spec.accessModes.1=ReadWriteOnce \
  --spec.volumeClaimTemplates.1.spec.resources.requests.storage=10Gi \
  --cli-region=cn-north-4
```

### Step 3: Verify PVC Creation

```bash
hcloud CCI listCoreV1NamespacedPersistentVolumeClaim \
  --namespace=ss-ns \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Each replica creates a PVC named `data-my-statefulset-0`, `data-my-statefulset-1`, `data-my-statefulset-2`.

### Step 4: Read Pod Status

```bash
hcloud CCI readAppsV1NamespacedStatefulSetStatus \
  --namespace=ss-ns \
  --name=my-statefulset \
  --cli-region=cn-north-4 \
  --cli-output=json
```

Repeat until `status.readyReplicas >= 3`.