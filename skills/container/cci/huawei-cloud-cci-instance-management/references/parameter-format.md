# CCI Parameter Format Rules

CCI uses deeply nested Kubernetes-style objects via the hcloud CLI. Understanding the parameter format is critical.

## 1. Dot Notation for Nested Objects

Nested fields are accessed via dot-separated paths:

```bash
--metadata.name=my-ns
--metadata.annotations.namespace-kubernetes-io/flavor=general-computing
--metadata.labels.app=my-deploy
--spec.template.spec.containers.1.image=nginx:latest
--spec.networkId=subnet-xxx
--spec.routerId=vpc-xxx
```

## 2. `{*}` Format for Maps (Annotations, Labels, Resources)

Maps are expressed as individual key=value entries using dot notation, NOT as JSON objects:

```bash
# Annotations
--metadata.annotations.namespace-kubernetes-io/flavor=general-computing
--metadata.annotations.key1=value1

# Labels
--metadata.labels.app=my-app
--metadata.labels.environment=production

# Resource limits/requests
--spec.template.spec.containers.1.resources.limits.cpu=500m
--spec.template.spec.containers.1.resources.limits.memory=1Gi
--spec.template.spec.containers.1.resources.requests.cpu=250m
--spec.template.spec.containers.1.resources.requests.memory=512Mi

# Selector matchLabels
--spec.selector.matchLabels.app=my-deploy
```

## 3. 1-Based Array Indexing

Arrays use **1-based** indexing (NOT 0-based):

```bash
# First container is .1, second is .2
--spec.template.spec.containers.1.name=main
--spec.template.spec.containers.2.name=sidecar
--spec.template.spec.containers.1.ports.1.containerPort=80
--spec.template.spec.containers.1.ports.2.containerPort=443
--spec.template.spec.volumes.1.name=data-vol
--spec.template.spec.volumes.2.name=config-vol
```

## 4. Resource Quantity Format

| Type | Format | Examples |
|---|---|---|
| CPU | millicores or cores | `500m` (0.5 core), `1` (1 core), `2` (2 cores) |
| Memory | Mi or Gi suffix | `512Mi`, `1Gi`, `2Gi` |

CPU values: `100m` = 0.1 core, `500m` = 0.5 core, `1` = 1 core, `4` = 4 cores.
Memory values: `256Mi`, `512Mi`, `1Gi`, `2Gi`, `4Gi`.

## 5. CCI Annotation Key Limitations

### 5.1 The Dot Parsing Problem

Annotation keys in Kubernetes often contain dots (e.g., `namespace.kubernetes.io/flavor`, `network.alpha.kubernetes.io/default-security-group`). When passed via hcloud CLI dot notation, hcloud treats dots in the **key name** as nested object delimiters, the same as dots in the **field path**.

This means:

```bash
# INTENDED: annotation key = "network.alpha.kubernetes.io/default-security-group"
# ACTUAL: hcloud parses as nested object path:
#   metadata.annotations.network.alpha.kubernetes.io.default-security-group
#   → {network: {alpha: {kubernetes: {io: {default-security-group: value}}}}}
# This is NOT a valid annotation key-value pair.
--metadata.annotations.network.alpha.kubernetes.io/default-security-group=sg-xxx
```

There is **no escaping mechanism** (quotes, backslashes, etc.) that prevents hcloud from parsing dots as nested delimiters.

### 5.2 Namespace Annotation Workaround (Hyphen Replacement)

For Namespace, the annotation key `namespace.kubernetes.io/flavor` can be passed via hcloud CLI by **replacing dots with hyphens** in the key portion:

```bash
# hcloud CLI parameter (dots replaced with hyphens in the key):
--metadata.annotations.namespace-kubernetes-io/flavor=general-computing

# CCI service auto-adds the canonical dotted version:
# namespace.kubernetes.io/flavor=general-computing
```

This workaround works because the key only contains dots (no additional slashes beyond the single `/` separating domain from name), and CCI recognizes the hyphenated form.

### 5.3 Network Annotation Cannot Use hcloud CLI

The Network resource requires the annotation key `network.alpha.kubernetes.io/default-security-group` (confirmed by official CCI API docs: https://support.huaweicloud.com/api-cci/createNetworkingCciIoV1beta1NamespacedNetwork.html).

This key contains **dots AND a slash**, making it impossible to pass via hcloud CLI:

- Dots are parsed as nested delimiters (no workaround)
- The hyphen replacement trick does not work for Network annotations
- **Use the Python helper script** to create Network resources with this annotation

### 5.4 `--cli-jsonInput` Does Not Solve This

The `--cli-jsonInput` feature allows passing the entire request body as a JSON file. However, it has a critical limitation for CCI:

- Even though `--dryrun` shows annotations correctly in the JSON input, the **actual API request does not include annotations in the request body** when using `--cli-jsonInput`. This is a hcloud bug/limitation.
- `--cli-jsonInput` file encoding must be **ASCII** (UTF-8 with BOM causes parsing failure).

**Do not rely on `--cli-jsonInput` for setting annotations on CCI resources.**

### 5.5 When to Use hcloud CLI vs Python Helper Script

| Resource | Annotation Key | hcloud CLI | Python Script |
|---|---|---|---|
| Namespace | `namespace.kubernetes.io/flavor` | Use hyphen workaround | Optional |
| Network | `network.alpha.kubernetes.io/default-security-group` | **Cannot use** | **Required** |
| Pod / Deployment | Simple keys (no dots) | Works normally | Optional |
| Pod / Deployment | Keys with dots | Cannot pass directly | Required |

### 5.6 Network Required Spec Fields

Network resources require ALL of the following spec fields:

```yaml
spec:
  attachedVPC: <vpc-id>          # VPC ID
  subnetID: <subnet-id>          # Subnet ID
  networkType: <type>            # Network type (e.g., "underlay-neutron")
  networkID: <neutron-network-id> # Neutron network ID of the VPC subnet (REQUIRED)
```

The `networkID` field is **REQUIRED** — it is the neutron network ID associated with the VPC subnet, not the same as `subnetID`.

## 6. Common Format Errors

| Wrong | Correct | Issue |
|---|---|---|
| `--metadata.annotations={"namespace.kubernetes.io/flavor":"general-computing"}` | `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` | Map uses `{*}` dot format, not JSON; use hyphens for Namespace annotation key |
| `--metadata.annotations.network.alpha.kubernetes.io/default-security-group=sg-xxx` | Use Python helper script for Network | Dots in annotation key are parsed as nested delimiters; no hcloud CLI workaround exists |
| `--spec.containers.0.name=main` | `--spec.template.spec.containers.1.name=main` | Array index starts from 1, not 0; also need full path through template.spec |
| `--spec.selector.matchLabels={"app":"my-app"}` | `--spec.selector.matchLabels.app=my-app` | Map uses `{*}` format |
| `--spec.resources.limits={"cpu":"500m"}` | `--spec.template.spec.containers.1.resources.limits.cpu=500m` | Full nested path + `{*}` format |
| `--region=cn-north-4` | `--cli-region=cn-north-4` | Region uses cli prefix |
| `--name my-pod` | `--name=my-pod` | Equals sign required |

## 7. Parameter Path Depth Reference

### Namespace (Shallow)

```
metadata.name
metadata.annotations.*
metadata.labels.*
```

Example:
```bash
hcloud CCI createCoreV1Namespace \
  --metadata.name=my-ns \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=cn-north-4
```

### Network (Shallow but Requires Python Script)

```
metadata.name
metadata.annotations.network.alpha.kubernetes.io/default-security-group
spec.attachedVPC
spec.subnetID
spec.networkType
spec.networkID
```

Example (Python helper script — hcloud CLI cannot set this annotation):
```python
# Use the Python helper script for Network creation
# hcloud CLI cannot pass the required annotation key
```

### Pod (Deep)

```
metadata.name
metadata.annotations.*
metadata.labels.*
spec.containers.1.name
spec.containers.1.image
spec.containers.1.resources.limits.*
spec.containers.1.resources.requests.*
spec.containers.1.ports.1.containerPort
spec.volumes.1.*
```

### Deployment (Very Deep)

```
metadata.name
metadata.annotations.*
metadata.labels.*
spec.replicas
spec.selector.matchLabels.*
spec.template.metadata.labels.*
spec.template.spec.containers.1.name
spec.template.spec.containers.1.image
spec.template.spec.containers.1.resources.limits.*
spec.template.spec.containers.1.resources.requests.*
spec.template.spec.containers.1.ports.1.containerPort
spec.template.spec.volumes.1.*
```

Nesting hierarchy (Deployment):
```
spec                          # Deployment spec
  replicas                    # Number of replicas
  selector                    # Pod selector
    matchLabels.*             # Label match rules
  template                    # Pod template
    metadata                  # Pod metadata
      labels.*                # Pod labels
    spec                      # Pod spec
      containers.1            # First container (1-based)
        name
        image
        ports.1               # First port (1-based)
          containerPort
        resources
          limits.*            # Resource limits map
          requests.*          # Resource requests map
        env.1                 # First env var (1-based)
          name
          value
      volumes.1               # First volume (1-based)
        name
        configMap             # Volume source
          name
```

## 8. DryRun for Validation

Validate parameters without creating resources:

```bash
hcloud CCI createCoreV1Namespace \
  --dryRun=All \
  --metadata.name=test-ns \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=cn-north-4
```

```bash
hcloud CCI createAppsV1NamespacedDeployment \
  --dryRun=All \
  --namespace=test-ns \
  --metadata.name=my-deploy \
  --spec.replicas=2 \
  --spec.selector.matchLabels.app=my-deploy \
  --spec.template.metadata.labels.app=my-deploy \
  --spec.template.spec.containers.1.name=main \
  --spec.template.spec.containers.1.image=nginx:latest \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --cli-region=cn-north-4
```