# Container Image Migration to Huawei Cloud SWR

Software Repository for Container (SWR) provides enterprise-grade, high-performance container image hosting on Huawei Cloud. To ensure that pods can pull images locally over the internal VPC backbone network with low latency and zero public data-transfer costs, mirror container images from the source registry (Harbor, DockerHub, AWS ECR, Aliyun ACR, Tencent CCR) to SWR before deploying workloads on CCE.

Huawei Cloud provides **`image-migrator`**, an automated bulk container image migration tool designed specifically for moving images from Docker Registry v2-compliant registries to SWR.

---

## 1. Official Huawei Cloud `image-migrator` Tool (Recommended)

`image-migrator` automatically replicates images in parallel with retry mechanisms, validation, and multi-architecture support.

### 1.1 Tool Download and Installation

See `references/cli-installation-guide.md` Section 6 for download links (Linux x86_64, Linux ARM64, Windows x86_64) and installation steps.

---

### 1.2 Configuration Files

`image-migrator` requires two configuration files in the working directory: `auth.json` and `images.json`.

#### `auth.json` — Registry Authentication

Specifies credentials for both the source registry and the destination SWR registry.

```json
{
  "source-registry.example.com/namespace": {
    "username": "source-user",
    "password": "source-password",
    "insecure": false
  },
  "swr.cn-north-4.myhuaweicloud.com": {
    "username": "cn-north-4@<HUAWEI_ACCESS_KEY>",
    "password": "<swr-login-key>",
    "insecure": false
  }
}
```

- **Target SWR Username**: Formatted as `<region>@<AK>` (e.g. `cn-north-4@ABCDEF...`).
- **Target SWR Password**: Obtain programmatically using the official KooCLI command:
  ```bash
  hcloud SWR CreateSecret --cli-region=<region_id>
  ```
  The returned `.auths["swr.<region>.myhuaweicloud.com"].auth` field contains base64-encoded `username:password` credentials.
- **Anonymous Sources**: If the source registry allows public anonymous pulls (e.g. `quay.io/coreos`), credentials can be left as empty `{}`.

#### `images.json` — Image Mapping Rules

A key-value mapping where each key is the source image repository and the value is the target SWR repository:

```json
{
  "docker.io/library/nginx:1.25": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo/nginx:1.25",
  "registry.k8s.io/coredns/coredns:v1.10.1": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo/coredns:v1.10.1",
  "quay.io/coreos/flannel:v0.14.0": "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo/flannel:v0.14.0"
}
```

---

### 1.3 Execution

Run the migration command with desired concurrency and retry options:

```bash
image-migrator \
  --auth=auth.json \
  --images=images.json \
  --workers=8 \
  --retries=3 \
  --log=image-migration.log
```

- `--workers`: Number of parallel image replication workers (default: 5).
- `--retries`: Retry count for failed layer transfers (default: 3).
- `--log`: Path to output log file for detailed audit.

---

## 2. Source Workload Image Discovery

Extract all unique container image references across active namespaces in the source cluster:

```bash
kubectl get pods -A -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}' | sort -u > source-images.txt
```

### Generating `images.json` Automatically from Cluster Pods

```python
import json

target_swr_prefix = "swr.cn-north-4.myhuaweicloud.com/cce-migration-repo"
image_map = {}

with open("source-images.txt", "r") as f:
    for line in f:
        src = line.strip()
        if not src:
            continue
        image_name_tag = src.split("/")[-1]
        image_map[src] = f"{target_swr_prefix}/{image_name_tag}"

with open("images.json", "w") as f:
    json.dump(image_map, f, indent=2)

print(f"Generated images.json with {len(image_map)} images.")
```

---

## 3. Alternative: `skopeo` CLI Automated Synchronization

For automated scripting or direct image copying using KooCLI and `skopeo`:

### Step 1: Retrieve SWR Login Credentials via KooCLI

Use the official KooCLI command to generate temporary SWR Docker authentication credentials:

```bash
hcloud SWR CreateSecret --cli-region=<region>
```

Extract and decode the authentication string directly in shell pipelines:

```bash
REGION="cn-north-4"
SWR_AUTH=$(hcloud SWR CreateSecret --cli-region=${REGION} | jq -r ".auths[\"swr.${REGION}.myhuaweicloud.com\"].auth" | base64 -d)
```

### Step 2: Replicate Images via `skopeo` with Robust Pipeline Error Handling

Execute server-to-server image copying without requiring a local Docker daemon.

> [!CAUTION] > **Avoid Shell Pipeline Exit Code Masking**:
> When piping commands (e.g. `skopeo copy ... | tail -1`), the shell `$?` variable captures the exit code of `tail -1` (`0`), masking any skopeo failure (e.g., Docker Hub rate limits or auth errors).
> **Always enable `set -o pipefail`** or inspect `${PIPESTATUS[0]}` to detect push failures.

```bash
#!/usr/bin/env bash
set -euo pipefail

SOURCE_IMAGE="docker.io/library/nginx:1.25"
TARGET_SWR="swr.${REGION}.myhuaweicloud.com/cce-migration-repo/nginx:1.25"

echo "Copying ${SOURCE_IMAGE} -> ${TARGET_SWR}..."
skopeo copy \
  --dest-creds="${SWR_AUTH}" \
  --insecure-policy \
  docker://${SOURCE_IMAGE} \
  docker://${TARGET_SWR}

# Explicit Post-Push Tag Verification
echo "Verifying tag in SWR..."
skopeo list-tags --creds="${SWR_AUTH}" docker://swr.${REGION}.myhuaweicloud.com/cce-migration-repo/nginx | grep -q "1.25"
echo "Image verification succeeded."
```

### Step 3: Mirror the Complete Velero Image Suite

CCE worker nodes in private subnets cannot pull from `docker.io` without a NAT Gateway. You **must mirror all container images required by Velero** to SWR before deploying Velero or executing restore operations:

|Velero Component|Upstream Docker Image|Target SWR Repository|Purpose|
|-|-|-|-|
|**Velero Server & Node-Agent**|`docker.io/velero/velero:v1.13.0`|`swr.<region>.myhuaweicloud.com/<org>/velero:v1.13.0`|Main Velero controller deployment and node-agent DaemonSet|
|**AWS/OBS Plugin**|`docker.io/velero/velero-plugin-for-aws:v1.9.0`|`swr.<region>.myhuaweicloud.com/<org>/velero-plugin-for-aws:v1.9.0`|Plugin init container for Huawei Cloud OBS S3-compatible backend|
|**Restore Helper**|`docker.io/velero/restore-helper:v1.13.0`|`swr.<region>.myhuaweicloud.com/<org>/restore-helper:v1.13.0`|Init container dynamically injected into restored pods for volume data restore|
|**CSI Plugin (Optional)**|`docker.io/velero/velero-plugin-for-csi:v0.7.0`|`swr.<region>.myhuaweicloud.com/<org>/velero-plugin-for-csi:v0.7.0`|CSI snapshot plugin (if using CSI volume snapshots)|

#### Bulk Replication Script for Velero Suite:

```bash
#!/usr/bin/env bash
set -euo pipefail

REGION="cn-north-4"
SWR_ORG="cce-migration-repo"
SWR_PREFIX="swr.${REGION}.myhuaweicloud.com/${SWR_ORG}"
SWR_AUTH=$(hcloud SWR CreateSecret --cli-region=${REGION} | jq -r ".auths[\"swr.${REGION}.myhuaweicloud.com\"].auth" | base64 -d)

VELERO_IMAGES=(
  "docker.io/velero/velero:v1.13.0"
  "docker.io/velero/velero-plugin-for-aws:v1.9.0"
  "docker.io/velero/restore-helper:v1.13.0"
  "docker.io/velero/velero-plugin-for-csi:v0.7.0"
)

for SRC in "${VELERO_IMAGES[@]}"; do
  IMAGE_NAME_TAG="${SRC##*/}"
  DST="${SWR_PREFIX}/${IMAGE_NAME_TAG}"
  echo "Mirroring ${SRC} -> ${DST}..."
  skopeo copy \
    --dest-creds="${SWR_AUTH}" \
    --insecure-policy \
    "docker://${SRC}" \
    "docker://${DST}"
done

echo "Verifying mirrored Velero tags..."
for SRC in "${VELERO_IMAGES[@]}"; do
  IMAGE_NAME=$(echo "${SRC##*/}" | cut -d: -f1)
  TAG=$(echo "${SRC##*/}" | cut -d: -f2)
  skopeo list-tags --creds="${SWR_AUTH}" "docker://${SWR_PREFIX}/${IMAGE_NAME}" | grep -q "${TAG}"
  echo "Verified: ${IMAGE_NAME}:${TAG}"
done
```

---

## 4. Target CCE Image Pull Configuration & In-Cluster Verification

When pulling private images from Huawei Cloud SWR, Kubernetes workloads must be configured with `imagePullSecrets`. In Huawei Cloud CCE, each namespace is pre-populated with a native secret named `default-secret` containing valid regional SWR credentials (automatically generated and rotated by CCE).

### Method 1: Workload Manifest Specification (Recommended)

Declare `imagePullSecrets` directly in the workload manifest (`spec.template.spec`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: <target-namespace>
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      imagePullSecrets:
        - name: default-secret
      containers:
        - name: sample-app
          image: swr.cn-north-4.myhuaweicloud.com/<org>/sample-app:v1.0.0
```

To batch-patch existing or migrated workloads that lack `imagePullSecrets`:

```bash
# Patch a single deployment
kubectl patch deployment <deployment-name> -n <target-namespace> \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"default-secret"}]}}}}' \
  --kubeconfig=~/.kube/cce-config

# Batch patch all deployments in the target namespace
kubectl get deployments -n <target-namespace> --kubeconfig=~/.kube/cce-config -o jsonpath='{.items[*].metadata.name}' | \
  xargs -n1 -I{} kubectl patch deployment {} -n <target-namespace> \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"default-secret"}]}}}}' \
  --kubeconfig=~/.kube/cce-config
```

### Method 2: ServiceAccount Binding

Associate `default-secret` with the namespace's ServiceAccount (`default` or custom SA):

```bash
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets": [{"name": "default-secret"}]}' \
  --namespace=<target-namespace> \
  --kubeconfig=~/.kube/cce-config
```

> [!NOTE]
> Workloads specifying a custom `serviceAccountName` (e.g. `serviceAccountName: backend-sa`) will only inherit pull secrets if that specific ServiceAccount is patched or `imagePullSecrets` is explicitly declared in the pod spec.

### Method 3: Dedicated Secret via KooCLI (Cross-Region / Cross-Account)

If pulling from an SWR repository in another region or another tenant account, retrieve an SWR temporary login token via KooCLI and generate a registry secret:

```bash
# Retrieve SWR authentication token and decode credentials
SWR_AUTH=$(hcloud SWR CreateSecret --cli-region=<region_id> | jq -r '.auths["swr.cn-north-4.myhuaweicloud.com"].auth' | base64 -d)

# Deploy docker-registry secret into target namespace
kubectl create secret docker-registry swr-secret \
  --docker-server=swr.cn-north-4.myhuaweicloud.com \
  --docker-username="${SWR_AUTH%%:*}" \
  --docker-password="${SWR_AUTH#*:}" \
  --namespace=<target-namespace> \
  --kubeconfig=~/.kube/cce-config
```

Workloads referencing cross-tenant SWR images must specify `- name: swr-secret` under `imagePullSecrets`.

### Verification Steps

1. Verify image availability in SWR:
   ```bash
   hcloud SWR ListReposDetails --cli-region=<region> --namespace=cce-migration-repo
   ```
2. Test pull capability by deploying a transient pod (specifying `default-secret` in `imagePullSecrets`):
   ```bash
   kubectl run test-swr-pull \
     --image=swr.cn-north-4.myhuaweicloud.com/cce-migration-repo/nginx:1.25 \
     --overrides='{"spec":{"imagePullSecrets":[{"name":"default-secret"}]}}' \
     --restart=Never \
     --kubeconfig=~/.kube/cce-config
   kubectl get pod test-swr-pull --kubeconfig=~/.kube/cce-config
   kubectl delete pod test-swr-pull --kubeconfig=~/.kube/cce-config
   ```
