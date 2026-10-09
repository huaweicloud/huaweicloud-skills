# Kubernetes ConfigMap and Secret Migration Guide

Kubernetes **ConfigMaps** (configuration items) and **Secrets** (confidential credentials) decouple application binaries from runtime parameters, environment variables, TLS certificates, database connection strings, and registry credentials.

When migrating to Huawei Cloud CCE, configuration items and secrets require meticulous handling to ensure seamless execution, security, and environment-specific parameter adaptation.

---

## 1. Overview of ConfigMaps and Secrets

|Resource Type|Kubernetes Kind|Common Use Cases|Key Considerations During Migration|
|-|-|-|-|
|**ConfigMaps**|`ConfigMap`|Application config files (`.yaml`, `.properties`, `.json`), environment variables, CoreDNS Corefile, nginx configs.|Endpoint adaptation (updating source database IPs, external service endpoints, and internal DNS suffixes to Huawei Cloud VPC equivalents).|
|**Opaque Secrets**|`Secret` (`Opaque`)|API keys, database passwords, OAuth client secrets, symmetric encryption keys.|Ensure least-privilege RBAC on CCE; verify encryption at rest via CCE master KMS integration.|
|**TLS Secrets**|`Secret` (`kubernetes.io/tls`)|Ingress SSL certificates, internal mTLS service certificates.|Verify certificate expiration dates; ensure matching secret keys (`tls.crt`, `tls.key`).|
|**Docker Registry Secrets**|`Secret` (`kubernetes.io/dockerconfigjson`)|Credentials to pull images from private registries.|Replace or supplement with Huawei Cloud SWR image pull secrets (`swr.<region>.myhuaweicloud.com`).|
|**ServiceAccount Tokens**|`Secret` (`kubernetes.io/service-account-token`)|Legacy auto-generated authentication tokens for ServiceAccounts.|**DO NOT MIGRATE**. Old tokens carry source cluster CA and issuer tokens; let CCE generate new tokens.|

---

## 2. Migration Strategies

### Method A: Velero Automated Workload Restore (Recommended)

Velero automatically captures ConfigMaps and Secrets when backing up namespaces.

#### Critical Rule 1: Exclude ServiceAccount Tokens

Legacy Kubernetes versions (prior to v1.24) automatically generated long-lived token secrets for every ServiceAccount. Migrating these tokens to CCE causes authentication conflicts and permission errors because the cryptographic signature does not match the CCE cluster certificate authority (CA).

#### Critical Rule 2: Never Backup or Restore `paas.elb` Secret

In Huawei Cloud CCE, secrets named `paas.elb` contain internal authentication tokens used by the cloud platform for load balancer and storage orchestration. The contents of `paas.elb` are rotated automatically by CCE. Restoring a stale `paas.elb` secret will overwrite valid tokens, causing ELB network communication failures and CSI storage provisioning errors.

Velero does not natively filter secrets by `type` during backup. Legacy `service-account-token` secrets are excluded automatically during **restore** by applying a `RestoreItemAction` plugin or by pre-labeling them on the source cluster with `velero.io/exclude-from-backup=true`:

```bash
# Option A: Label token secrets for exclusion before backup
kubectl label secret -l kubernetes.io/service-account-token --all-namespaces velero.io/exclude-from-backup=true

# Execute backup (labeled secrets are automatically excluded)
velero backup create k8s-migration-backup \
  --include-namespaces=production,staging \
  --wait
```

When performing selective manifest exports or namespace-to-namespace migrations, explicitly exclude `paas.elb`:

```bash
kubectl get secrets -n <namespace> -o json | \
  jq '.items[] | select(.metadata.name != "paas.elb")' > filtered-secrets.json
```

---

### Method B: Selective Manifest Export, Sanitization, and Apply

For fine-grained control or staging adjustments without Velero:

#### Step 1: Export ConfigMaps and Secrets from Source Cluster

```bash
# Export all ConfigMaps in target namespace
kubectl get configmap -n <source-namespace> -o yaml > configmaps.yaml

# Export all Secrets excluding auto-generated default service account tokens
kubectl get secret -n <source-namespace> \
  --field-selector=type!=kubernetes.io/service-account-token \
  -o yaml > secrets.yaml
```

#### Step 2: Sanitize Metadata

Remove cluster-specific runtime metadata fields (`uid`, `resourceVersion`, `creationTimestamp`, `selfLink`, `ownerReferences`, `status`):

```bash
# Clean metadata using yq or python
python3 -c "
import yaml, sys

def clean_manifest(file_path):
    with open(file_path, 'r') as f:
        docs = yaml.safe_load_all(f)
        cleaned_docs = []
        for doc in docs:
            if not doc: continue
            items = doc.get('items', [doc]) if doc.get('kind') == 'List' else [doc]
            for item in items:
                meta = item.get('metadata', {})
                for field in ['uid', 'resourceVersion', 'creationTimestamp', 'selfLink', 'ownerReferences', 'generation']:
                    meta.pop(field, None)
                cleaned_docs.append(item)
    with open(file_path, 'w') as f:
        yaml.safe_dump_all(cleaned_docs, f)

clean_manifest('configmaps.yaml')
clean_manifest('secrets.yaml')
print('Sanitization completed.')
"
```

#### Step 3: Apply Sanitized Resources to CCE

```bash
kubectl apply -f configmaps.yaml --kubeconfig=~/.kube/cce-config
kubectl apply -f secrets.yaml --kubeconfig=~/.kube/cce-config
```

---

## 3. Configuration Parameter Adaptation (Re-Pointing Playbook)

During migration, configuration files stored within ConfigMaps frequently contain references to infrastructure that changes upon migrating to Huawei Cloud:

```
Source Cloud / On-Premise Endpoint           Target Huawei Cloud Equivalent
───────────────────────────────────           ──────────────────────────────
AWS RDS / On-prem MySQL Hostname       ───>   Huawei Cloud GaussDB / RDS Private IP
AWS S3 Endpoint (s3.amazonaws.com)     ───>   Huawei Cloud OBS Endpoint (obs.cn-north-4.myhuaweicloud.com)
Source Internal Registry               ───>   swr.cn-north-4.myhuaweicloud.com
On-prem NFS IP (192.168.x.x)           ───>   Huawei Cloud SFS / SFS Turbo Mount IP (10.0.x.x)
Source Cluster DNS (*.local)           ───>   Target CCE CoreDNS (*.cluster.local)
```

### Parameter Adaptation Procedure:

1. Inspect ConfigMaps for hardcoded IP addresses or external cloud endpoints:
   ```bash
   kubectl get configmaps -n <namespace> -o yaml | grep -E "endpoint|host|url|addr|ip"
   ```
2. Update configuration entries using `kubectl edit configmap <name>` or patch manifests before pod deployment.
3. If ConfigMaps are configured with `immutable: true`, delete and recreate them with the updated values.
4. **Frontend Server-Side Rendering (SSR) Variables**: For frameworks like Next.js or Nuxt, audit Deployment environment variables (e.g. `CONSOLE_API_URL`, `APP_API_URL`, `BACKEND_URL`). Next.js invokes these endpoints server-side inside the container during page loads; ensure they point to the target CCE cluster address, ELB domain, or internal cluster Service (`INTERNAL_API_URL=http://<service-name>:<port>`).

---

## 4. Docker Registry Secrets Handling

During migration, third-party Docker registry credentials (e.g. `Secret` with `type: kubernetes.io/dockerconfigjson` for Docker Hub, Alibaba Cloud ACR, or AWS ECR) should **not** be migrated to CCE if container images are mirrored to Huawei Cloud SWR.

CCE handles SWR registry authentication via native platform credentials:

- **CCE Built-in Secret**: CCE automatically generates and rotates `default-secret` in each namespace for pulling from the tenant's regional SWR repositories.
- **Workload Configuration**: Workload manifests (`spec.template.spec.imagePullSecrets`) or ServiceAccounts in CCE must reference `default-secret` to pull private SWR images without authentication failure.
- **Cross-Region / Cross-Account**: Pulling from SWR repositories in other accounts or regions requires dedicated token generation via KooCLI.

> [!TIP]
> For complete instructions on declaring `imagePullSecrets` in workload manifests, batch-patching existing deployments, and deploying cross-tenant registry secrets, see `references/swr-image-sync-guide.md` Section 4.

---

## 5. Security & Verification Guardrails

1. **Zero Secret Leakage**:
   - Never print Secret contents (`.data`) in cleartext in console transcripts or CI/CD logs.
   - Store temporary YAML secret files with restricted permissions (`chmod 600 secrets.yaml`) and purge them after application.
2. **Encryption at Rest**:
   - Verify that target CCE cluster has KMS secret encryption enabled if required for compliance:
     ```bash
     hcloud CCE ShowCluster --cluster_id=<cluster_id> --cli-region=<region_id>
     ```
3. **Verification Checklist**:
   - Compare ConfigMap keys and data counts between source and target:
     ```bash
     # Source cluster
     kubectl get cm -n <namespace> --no-headers | wc -l
     # Target CCE cluster
     kubectl get cm -n <namespace> --kubeconfig=~/.kube/cce-config --no-headers | wc -l
     ```
   - Verify Secret counts (excluding token secrets):
     ```bash
     kubectl get secret -n <namespace> --field-selector=type!=kubernetes.io/service-account-token --no-headers | wc -l
     ```
   - Test pod mounting: Deploy a test pod mounting the restored ConfigMap and Secret to ensure proper file permissions and content formatting.
