---
name: huawei-cloud-cci-instance-management
description: >-
  Huawei Cloud CCI (Cloud Container Instance) full lifecycle management using hcloud CLI.
  Covers Namespace, Network, Deployment, StatefulSet, Pod creation/update/delete/status, EIPPool for public IP, logs and metrics.
  Two-step confirmation for all destructive operations (delete namespace cascades all resources under it).
  Use this skill when the user wants to operate CCI serverless containers via command line.
  Triggers: CCI, 云容器实例, serverless container, 容器实例, namespace, deployment, statefulset, pod, EIPPool, CCI负载, 无服务器容器, 创建容器实例, 删除容器实例, 容器状态, 容器日志
tags: [cci, container-instance, serverless, namespace, deployment]
---

# Huawei Cloud CCI Container Instance Lifecycle Management

## Overview

Manage Huawei Cloud CCI (Cloud Container Instance) full lifecycle using hcloud CLI (KooCLI). CCI is a serverless container service — no cluster management needed, just create a Namespace, define a Network, then deploy workloads directly.

**Architecture**: hcloud CLI → CCI OpenAPI → Namespace / Network / Deployment / StatefulSet / Pod / EIPPool / Service / Ingress

## Constraints and Rules

### Security Rules

- **Two-step confirmation**: All destructive operations (delete Namespace/Network/Deployment/StatefulSet/Pod/EIPPool) require explicit user confirmation — preview command, resource details, and risk warning first; execute only after user confirms.
- **Credential security**: Never expose AK/SK values in conversation, commands, or output. Only use `hcloud configure list` to check credential status (presence only). Prefer profile mode or environment variables over explicit AK/SK parameters.

### Resource Constraints

- **Namespace flavor annotation is mandatory**: Every namespace must carry `namespace-kubernetes-io/flavor` annotation (value: `general-computing` or `gpu-accelerated`). Without it, creation fails.
- **limits must equal requests**: CCI enforces `resources.limits == resources.requests`. Mismatch causes "limit and request doesn't equal" error. Set both to the same values (e.g., `500m/1Gi`).
- **Network must precede workloads**: Pod/Deployment/StatefulSet creation fails or stays Pending if no Network exists in the namespace. Always create Network before deploying workloads.
- **VPC CIDR restriction**: VPC subnet CIDR must NOT be `10.247.0.0/16` — CCI reserves this range for Service networking. Using it causes IP conflicts and workload creation failures.
- **Deletion order**: Pod → Deployment/StatefulSet → EIPPool → Network → Namespace. Deleting a Namespace cascades all resources under it.

### hcloud CLI Constraints

- **Network creation must use Python helper script**: hcloud CLI cannot pass annotation keys containing dots (`network.alpha.kubernetes.io/default-security-group`). Neither dot notation nor `--cli-jsonInput` works. Use `scripts/cci_network_helper.py`.
- **Namespace annotation uses hyphen replacement**: Keys like `namespace.kubernetes.io/flavor` can use hyphens (`namespace-kubernetes-io/flavor`) and CCI auto-normalizes. This workaround only works for Namespace, NOT for Network.
- **Always verify parameters with `--help`**: CCI has hundreds of parameters. Run `hcloud CCI <Operation> --help` before constructing any command. The help output is the authoritative source.

> Detailed breakdowns of these rules are in [Security Constraints](#security-constraints), [hcloud CLI Limitations](#hcloud-cli-limitations), and [Precautions](#precautions).

## Standard Workflow

```
1. Create Namespace (with flavor annotation)
2. Create Network (requires Python helper script for annotation — see hcloud CLI Limitations)
3. Create Deployment / StatefulSet / Pod (run workloads)
4. Query status, view logs
5. (Optional) Create EIPPool for Pod public IP access
6. Cleanup: delete workload → delete Network → delete Namespace
```

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

hcloud CLI supports two credential modes. See [references/credential-configuration.md](references/credential-configuration.md) for full details.

**Quick setup** (choose one):

```bash
# Mode A — Long-term AK/SK
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4

# Mode B — Temporary AK/SK + SecurityToken
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

- **Security rules**: Never expose AK/SK/SecurityToken values. Use `hcloud configure list` to check presence only.

> ⚠️ **Known limitation — Python helper script credentials are independent of hcloud CLI**: The Python helper script (`scripts/cci_network_helper.py`) uses `HW_ACCESS_KEY` / `HW_SECRET_KEY` (and optionally `HW_SECURITY_TOKEN`) environment variables for authentication, which are **separate from** hcloud CLI's credential source (profile or `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK`). If the credentials in `HW_ACCESS_KEY`/`HW_SECRET_KEY` lack the necessary IAM permissions for CCI Network creation, the script will fail with a 403 error. Ensure these variables contain credentials with sufficient CCI permissions (e.g., `CCI FullAccess`). The hcloud CLI continues using its own credential source independently — running the helper script does not affect subsequent hcloud CLI commands.

### 3. Validation Check

```bash
hcloud version
hcloud configure list
```

## Security Constraints

### Dangerous Operation Confirmation Mechanism

> **This skill strictly enforces a two-step confirmation mechanism for all destructive operations.**

All destructive operations require explicit user confirmation before execution. The process:

**Step 1: Preview** — Show the command, resource details, and risk warning

**Step 2: Confirm & Execute** — Only after user explicitly confirms

#### Operations Requiring Confirmation

| Operation | Risk Level | Description |
|-----------|------------|-------------|
| Delete Namespace | 🔴 Critical | Cascades — deletes ALL resources under this namespace (Network, Pods, Deployments, etc.) |
| Delete Network | 🟠 High | Disconnects namespace from VPC; running pods lose network |
| Delete Deployment | 🟠 High | Terminates all replicas of the workload |
| Delete StatefulSet | 🟠 High | Terminates all replicas; PVC data may be lost |
| Delete Pod | 🟠 High | Terminates the container instance |
| Delete EIPPool | 🟡 Medium | Releases public IPs allocated to pods |

### Credential Security

- **Never expose AK/SK/SecurityToken values** in conversation, commands, or output
- **Never ask user to input AK/SK/SecurityToken directly** in conversation
- **Only use** `hcloud configure list` to check credential status (presence only, not values)
- **Prefer** profile mode or environment variables over explicit AK/SK parameters

## Command Format Standard

CCI follows the standard hcloud format with Kubernetes-style nested parameters:

```bash
hcloud CCI <Operation> --param=value --cli-region=<region> --cli-output=json
```

### CCI-Specific Parameter Rules

CCI parameters follow Kubernetes API conventions — deeply nested objects with dot notation:

1. **Annotations use `{*}` format**: `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing`
2. **Labels use `{*}` format**: `--metadata.labels.app=my-app`
3. **Containers array (1-based)**: `--spec.template.spec.containers.1.name=main --spec.template.spec.containers.1.image=nginx`
4. **Resources use `{*}` format**: `--spec.template.spec.containers.1.resources.limits.cpu=500m`
5. **Selector matchLabels use `{*}` format**: `--spec.selector.matchLabels.app=my-app`
6. **Namespaced operations require `--namespace`**: all workload operations must specify namespace

> **⚠️ Critical**: Before constructing any CCI command, always run `hcloud CCI <Operation> --help` to verify exact parameter names. CCI has hundreds of parameters; the help output is the authoritative source.

### Parameter Format Details

See [references/parameter-format.md](references/parameter-format.md) for complete CCI parameter format rules and examples.

## Scenario Routing

| User Intent | Reference Document |
|---|---|
| Create/query/delete Namespace | [references/task-namespace-management.md](references/task-namespace-management.md) |
| Create/query/delete Network | [references/task-network-management.md](references/task-network-management.md) |
| Create/query/update/delete/scale Deployment | [references/task-deployment-management.md](references/task-deployment-management.md) |
| Create/query/update/delete StatefulSet | [references/task-statefulset-management.md](references/task-statefulset-management.md) |
| Create/query/delete Pod | [references/task-pod-management.md](references/task-pod-management.md) |
| Create/query/delete EIPPool | [references/task-eippool-management.md](references/task-eippool-management.md) |
| Query status, view logs, events | [references/task-logs-and-status.md](references/task-logs-and-status.md) |
| Full workflow (create→run→cleanup) | [references/common-workflows.md](references/common-workflows.md) |
| All CCI operations quick reference | [references/cci-operation-catalog.md](references/cci-operation-catalog.md) |
| Troubleshooting | [references/troubleshooting.md](references/troubleshooting.md) |
| IAM permissions | [references/iam-policies.md](references/iam-policies.md) |
| Verification steps | [references/verification-method.md](references/verification-method.md) |
| Correct/error pattern comparison | [references/acceptance-criteria.md](references/acceptance-criteria.md) |

## Core Commands

### Namespace

```bash
# Create namespace (general-computing flavor)
hcloud CCI createCoreV1Namespace \
  --metadata.name=<ns-name> \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=<region \
  --cli-output=json

# List namespaces
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json

# Read namespace details
hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json

# Delete namespace (TWO-STEP CONFIRMATION REQUIRED)
hcloud CCI deleteCoreV1Namespace --name=<ns-name> --cli-region=<region>
```

### Network

> **⚠️ hcloud CLI limitation**: Network creation requires a Python helper script because hcloud CLI cannot pass the annotation key `network.alpha.kubernetes.io/default-security-group` (contains dots that hcloud treats as nested levels). The `--cli-jsonInput` approach also doesn't work due to an hcloud bug where annotations show in `--dryrun` but aren't transmitted in actual requests. See [hcloud CLI Limitations](#hcloud-cli-limitations) below.
>
> **⚠️ Credential requirement**: The Python helper script uses `HW_ACCESS_KEY`/`HW_SECRET_KEY` (and optionally `HW_SECURITY_TOKEN`) environment variables for authentication. This is **independent** from hcloud CLI's credential source (which reads from `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` or its profile). If the credentials in `HW_ACCESS_KEY`/`HW_SECRET_KEY` lack CCI Network creation permissions, the script will fail with 403. Ensure they have sufficient IAM permissions (e.g., `CCI FullAccess`). After the script runs, hcloud CLI commands continue using their own credential source unaffected.

```bash
# Step 1: Get VPC subnet details (including neutron_network_id)
hcloud VPC ShowSubnet --vpc_id=<vpc-id> --subnet_id=<subnet-id> --cli-region=<region> --cli-output=json

# Step 2: Create network via Python helper script
python scripts/cci_network_helper.py create \
  --namespace=<ns-name> \
  --name=<network-name> \
  --vpc-id=<vpc-id> \
  --subnet-id=<subnet-id> \
  --network-id=<neutron-network-id> \
  --security-group-id=<sg-id> \
  --region=<region>

# Step 3: Check network status until Active
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=<network-name> \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json

# List networks
hcloud CCI listNetworkingCciIoV1beta1NamespacedNetwork \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json
```

**Required Network spec fields**: Network creation requires `attachedVPC`, `subnetID`, `networkType`, AND `networkID` (neutron network ID). The `networkID` field is REQUIRED — it is the neutron network ID obtained from `hcloud VPC ShowSubnet`.

**Required Network annotation**: `network.alpha.kubernetes.io/default-security-group` (the correct annotation key for CCI Network security group, NOT `security-group-id`). This annotation must be set to the security group ID.

### Deployment

```bash
# Create deployment
hcloud CCI createAppsV1NamespacedDeployment \
  --namespace=<ns-name> \
  --metadata.name=<deploy-name> \
  --spec.replicas=1 \
  --spec.selector.matchLabels.app=<deploy-name> \
  --spec.template.metadata.labels.app=<deploy-name> \
  --spec.template.spec.containers.1.name=<container-name> \
  --spec.template.spec.containers.1.image=<image> \
  --spec.template.spec.containers.1.resources.limits.cpu=500m \
  --spec.template.spec.containers.1.resources.limits.memory=1Gi \
  --spec.template.spec.containers.1.resources.requests.cpu=500m \
  --spec.template.spec.containers.1.resources.requests.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json

# Scale deployment
hcloud CCI patchAppsV1NamespacedDeploymentScale \
  --name=<deploy-name> \
  --namespace=<ns-name> \
  --spec.replicas=<new-replicas> \
  --cli-region=<region>

# Read deployment status
hcloud CCI readAppsV1NamespacedDeploymentStatus \
  --name=<deploy-name> \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json
```

### StatefulSet

```bash
# Create statefulset
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
  --cli-region=<region> \
  --cli-output=json

# Read statefulset status
hcloud CCI readAppsV1NamespacedStatefulSetStatus \
  --name=<sts-name> \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json
```

### Pod

```bash
# Create pod (single container instance)
hcloud CCI createCoreV1NamespacedPod \
  --namespace=<ns-name> \
  --metadata.name=<pod-name> \
  --spec.containers.1.name=<container-name> \
  --spec.containers.1.image=<image> \
  --spec.containers.1.resources.limits.cpu=500m \
  --spec.containers.1.resources.limits.memory=1Gi \
  --cli-region=<region> \
  --cli-output=json

# Read pod status
hcloud CCI readCoreV1NamespacedPodStatus \
  --name=<pod-name> \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json

# Read pod logs
hcloud CCI readCoreV1NamespacedPodLog \
  --name=<pod-name> \
  --namespace=<ns-name> \
  --container=<container-name> \
  --cli-region=<region>
```

### EIPPool

```bash
# Create EIPPool (for pod public IP access — auto-create EIPs)
hcloud CCI createCrdYangtseCniV1NamespacedEIPPool \
  --namespace=<ns-name> \
  --apiVersion=crd.yangtse.cni/v1 \
  --kind=EIPPool \
  --metadata.name=<eippool-name> \
  --spec.amount=1 \
  --spec.eipAttributes.networkType=5_bgp \
  --spec.eipAttributes.ipVersion=4 \
  --spec.eipAttributes.bandwidth.shareType=PER \
  --spec.eipAttributes.bandwidth.size=5 \
  --spec.eipAttributes.bandwidth.chargeMode=bandwidth \
  --spec.eipAttributes.bandwidth.name=<bw-name> \
  --cli-region=<region> \
  --cli-output=json

# Read EIPPool status
hcloud CCI readCrdYangtseCniV1NamespacedEIPPoolStatus \
  --name=<eippool-name> \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json
```

**EIPPool required fields**: `--apiVersion=crd.yangtse.cni/v1` and `--kind=EIPPool` are mandatory. `spec.eipAttributes.networkType` is required (values: `5_bgp` for dynamic BGP, `5_gray` for dedicated load balancing). `spec.eipAttributes.bandwidth.chargeMode` and `name` are required when auto-creating EIPs.

**Pod EIP binding**: To assign an EIPPool to a Pod, add annotation `yangtse.io/eippool=<eippool-name>` (use hyphen workaround: `--metadata.annotations.yangtse-io/eippool=<eippool-name>`).

## VPC/Subnet Prerequisites

CCI workloads run inside a Network that maps to an existing VPC subnet. Before creating a Network, query available VPCs and subnets, and obtain the neutron network ID (required for Network creation):

```bash
# List VPCs
hcloud VPC ListVpcs --cli-region=<region> --cli-output=json

# List subnets
hcloud VPC ListSubnets --cli-region=<region> --cli-output=json

# Get subnet details (including neutron_network_id — REQUIRED for Network creation)
hcloud VPC ShowSubnet --vpc_id=<vpc-id> --subnet_id=<subnet-id> --cli-region=<region> --cli-output=json
```

> **⚠️ VPC subnet CIDR restriction**: The VPC and subnet CIDR must NOT be `10.247.0.0/16` — this range is reserved by CCI for Service networking. Using it causes IP conflicts and workload creation failures.

> **⚠️ neutron_network_id is required**: The `neutron_network_id` from `VPC ShowSubnet` output is the value for the `networkID` field in Network spec. This field is REQUIRED for Network creation.

## Namespace Flavor Types

| Flavor Value | Description | Use Case |
|---|---|---|
| `general-computing` | General computing type | Standard workloads, web services, microservices |
| `gpu-accelerated` | GPU accelerated type | AI, ML, high-performance computing |

## Resource Quota and Limits

CCI enforces resource quotas per namespace. Common defaults:

| Resource | Default Limit |
|---|---|
| Pods | varies by region |
| CPU per Pod | 0.25 - 8 cores |
| Memory per Pod | 0.5Gi - 32Gi |
| PVCs | varies |

Query current quotas:

```bash
hcloud CCI listCoreV1NamespacedResourceQuota --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

## Output Format

### JSON (recommended)
```bash
hcloud CCI <Operation> --cli-region=<region> --cli-output=json
```

### Table (for manual viewing)
```bash
hcloud CCI <Operation> --cli-region=<region> --cli-output=table
```

### JMESPath Filtering
```bash
# Filter deployment status
hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy> --namespace=<ns> --cli-region=<region> --cli-output=json --cli-query="{replicas:status.replicas,ready:status.readyReplicas,available:status.availableReplicas}"

# Filter pod phase
hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> --cli-region=<region> --cli-output=json --cli-query="status.phase"
```
  --cli-region=<region> --cli-output=json \
  --cli-query="status.phase"
```

## Debugging

Add `--cli-debug=true` to any command for detailed request/response information:

```bash
hcloud CCI <Operation> --cli-debug=true --cli-region=<region>
```

## Parameter Confirmation

Before executing any CCI operation, confirm these parameters:

| Parameter | Required | Description | Source |
|---|---|---|---|
| `--namespace` | Yes | CCI namespace name | Existing or newly created |
| `--cli-region` | Yes | Huawei Cloud region ID | `HUAWEI_CLOUD_REGION` or config |
| `--metadata.name` | Yes | Resource name | User specified |
| Flavor annotation | Yes (Namespace) | `general-computing` or `gpu-accelerated` | User choice |
| VPC/Subnet ID | Yes (Network) | From `VPC ListVpcs` / `VPC ShowSubnet` | Query existing resources |
| neutron_network_id | Yes (Network) | From `VPC ShowSubnet` response | Query result |

> Run `hcloud CCI <Operation> --help` before any CCI command to verify parameter names, then cross-reference the table above.

## Precautions

See [references/troubleshooting.md](references/troubleshooting.md) for detailed troubleshooting.

**Quick reference**:

| Issue | Cause | Quick Fix |
|---|---|---|
| Namespace creation fails | Missing flavor annotation | Add `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` |
| Network creation fails (400/403) | Missing VPC/subnet/annotation/networkID, or credential scope insufficient | Verify subnet/neutron IDs, security group; use Python helper; use **long-term AK/SK** (Mode A) |
| Pod stays Pending | No Network in namespace | Create Network first |
| 403 permission error | Insufficient IAM | Check [references/iam-policies.md](references/iam-policies.md) |
| Deep nested param errors | Wrong dot notation | Use `--help` to verify exact parameter path |
| Annotation with dots not passed | hcloud CLI limitation | Use Python helper script for Network creation |
| EIPPool creation fails (400/422) | Missing apiVersion/kind/networkType | Add all required fields (see EIPPool section) |
| limit/request mismatch | CCI requires limits == requests | Set requests same as limits (e.g., both `500m/1Gi`) |

## Verification Method

See [references/verification-method.md](references/verification-method.md) for complete verification steps.

**Quick checklist**:

| Step | Command | Expected Result |
|---|---|---|
| Namespace | `hcloud CCI readCoreV1Namespace --name=<ns> --cli-region=<region>` | status.phase=Active |
| Network | `hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus --name=<net> --namespace=<ns>` | status.phase=Active |
| Deployment | `hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy> --namespace=<ns>` | readyReplicas >= 1 |
| Pod | `hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns>` | status.phase=Running |

## Best Practices

1. **Namespace isolation**: Use different namespaces for different teams/projects to avoid resource conflicts
2. **EIPPool on-demand**: Only create EIPPool when Pod public IP access is needed

## hcloud CLI Limitations

> **⚠️ Critical**: hcloud CLI has known limitations that affect CCI operations. Understanding these is essential for successful Network creation.

| Limitation | Impact | Workaround |
|---|---|---|
| **Cannot pass annotation keys containing dots (.) via CLI parameters** | hcloud treats dots in parameter names as nested object levels, so `--metadata.annotations.network.alpha.kubernetes.io/default-security-group` creates a deeply nested structure instead of a single annotation key | Use Python helper script (`scripts/cci_network_helper.py`) for Network creation |
| **`--cli-jsonInput` doesn't properly transmit annotations** | hcloud bug: annotations appear in `--dryrun` output but are not transmitted in actual API requests | Use Python helper script instead |
| **`--cli-jsonInput` requires ASCII encoding** | UTF-8 BOM causes JSON parsing failure | Ensure JSON input files are saved as plain ASCII (no BOM) |
| **Namespace annotation works with hyphen replacement** | Keys like `namespace.kubernetes.io/flavor` can use hyphens (`namespace-kubernetes-io/flavor`) and CCI auto-normalizes them back | This workaround only works for Namespace, NOT for Network |

**Why Network needs a Python helper**: The Network annotation key `network.alpha.kubernetes.io/default-security-group` cannot be passed via hcloud CLI (neither dot notation nor `--cli-jsonInput`). Unlike Namespace annotations, CCI does NOT normalize hyphen-replaced keys for Network resources. The Python helper script (`scripts/cci_network_helper.py`) constructs the correct API request body directly.

## References

| Document | Description |
|---|---|
| [task-namespace-management.md](references/task-namespace-management.md) | Namespace lifecycle operations |
| [task-network-management.md](references/task-network-management.md) | Network lifecycle operations |
| [task-deployment-management.md](references/task-deployment-management.md) | Deployment lifecycle operations |
| [task-statefulset-management.md](references/task-statefulset-management.md) | StatefulSet lifecycle operations |
| [task-pod-management.md](references/task-pod-management.md) | Pod lifecycle operations |
| [task-eippool-management.md](references/task-eippool-management.md) | EIPPool operations |
| [task-logs-and-status.md](references/task-logs-and-status.md) | Status queries and log viewing |
| [cci-operation-catalog.md](references/cci-operation-catalog.md) | Full CCI operation quick reference |
| [parameter-format.md](references/parameter-format.md) | CCI parameter format rules and examples |
| [common-workflows.md](references/common-workflows.md) | Complete workflow sequences |
| [credential-configuration.md](references/credential-configuration.md) | Credential setup (long-term AK/SK & temporary AK/SK+SecurityToken) |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [troubleshooting.md](references/troubleshooting.md) | Error troubleshooting |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/error pattern comparison |
| [scripts/cci_network_helper.py](scripts/cci_network_helper.py) | Python helper script for Network creation (bypasses hcloud CLI annotation limitations) |