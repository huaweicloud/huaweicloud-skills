# Network Lifecycle Management

A Network maps a VPC subnet into a CCI namespace. A Network **must exist before any workload** (Deployment, Pod) can be created in the namespace.

## VPC/Subnet Query Prerequisite

Before creating a Network, you must identify the VPC, subnet, and neutron network ID.

### List VPCs

```bash
hcloud VPC ListVpcs --cli-region=<region> --cli-output=json
```

### List Subnets for a VPC

```bash
hcloud VPC ListSubnets --vpc_id=<vpc-id> --cli-region=<region> --cli-output=json
```

Record the following from the output:
- `vpc_id` → used as `--spec.attachedVPC` (or `--attached-vpc` in the helper script)
- `subnet_id` → used as `--spec.subnetID` (or `--subnet-id` in the helper script)
- The subnet's neutron network ID → used as `--spec.networkID` (or `--network-id` in the helper script)

> **IMPORTANT**: The subnet CIDR MUST NOT be `10.247.0.0/16` — this range is reserved for the CCI Service network and will cause conflicts.

## Create Network

### Required Spec Fields

The Network spec requires **three mandatory fields**:

| Spec Field | hcloud CLI Parameter | Helper Script Parameter | Source |
|-----------|---------------------|------------------------|--------|
| `networkID` | `--spec.networkID` | `--network-id` | Neutron network ID from subnet query |
| `attachedVPC` | `--spec.attachedVPC` | `--attached-vpc` | VPC ID from `hcloud VPC ListVpcs` |
| `subnetID` | `--spec.subnetID` | `--subnet-id` | Subnet ID from `hcloud VPC ListSubnets` |

> Omitting `networkID` causes the error: `spec[networkID]: Required value`

### Security Group Annotation

CCI Network creation requires the annotation `network.alpha.kubernetes.io/default-security-group` to specify the default security group:

```
metadata.annotations:
  network.alpha.kubernetes.io/default-security-group: <security-group-id>
```

- CCI auto-normalizes this annotation key (the canonical dotted version is preserved alongside any hyphenated variants when applicable)

### hcloud CLI Limitation

**hcloud CLI cannot pass annotation keys containing dots (`.`) as CLI parameters** — hcloud treats dots as nested object delimiters rather than literal annotation key names. The `--cli-jsonInput` approach also fails because hcloud does not properly transmit annotations from JSON input files as part of the request body.

Additionally, `--cli-jsonInput` files must use **ASCII encoding** (not UTF-8 with BOM). UTF-8 with BOM causes the error: `Failed to parse cli-jsonInput parameter file`.

### Primary Method: Python Helper Script

Use the `cci_network_helper.py` script from the skill's `scripts/` directory. It calls the CCI API directly using `huaweicloudsdkcore.signer.signer.Signer` and `requests`, bypassing hcloud's annotation limitation:

```bash
python scripts/cci_network_helper.py create \
  --namespace=<ns-name> \
  --name=<network-name> \
  --network-id=<neutron-network-id> \
  --attached-vpc=<vpc-id> \
  --subnet-id=<subnet-id> \
  --security-group=<security-group-id> \
  --region=<region>
```

- `--namespace` = CCI namespace (must already exist)
- `--name` = Network resource name
- `--network-id` = neutron network ID (required)
- `--attached-vpc` = VPC ID
- `--subnet-id` = subnet ID
- `--security-group` = default security group ID (set via the `network.alpha.kubernetes.io/default-security-group` annotation)
- `--region` = Huawei Cloud region

### Fallback: hcloud CLI (Without Security Group Annotation)

If the security group annotation is not needed, hcloud CLI can create a Network without it:

```bash
hcloud CCI createNetworkingCciIoV1beta1NamespacedNetwork \
  --namespace=<ns-name> \
  --metadata.name=<network-name> \
  --spec.networkID=<neutron-network-id> \
  --spec.attachedVPC=<vpc-id> \
  --spec.subnetID=<subnet-id> \
  --cli-region=<region> \
  --cli-output=json
```

> **Note**: This omits the `network.alpha.kubernetes.io/default-security-group` annotation. Use the Python helper script for complete Network creation with the security group annotation.

### Network Creation Status Lifecycle

Network creation returns `status.state=Initializing`. The Network transitions to `Active` once ready.

| State | Meaning | Action |
|-------|---------|--------|
| `Initializing` | Network is being created | Wait — do not create workloads yet |
| `Active` | Network is ready | You can now create workloads in the namespace |

**You must verify the Network reaches `Active` before creating workloads.** See "Read Network Status" below.

- One Network per namespace is the typical and recommended pattern
- The namespace must already exist before creating a Network in it

## List Networks

```bash
hcloud CCI listNetworkingCciIoV1beta1NamespacedNetwork \
  --namespace=<ns-name> \
  --cli-region=<region> \
  --cli-output=json
```

## Read Network

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetwork \
  --name=<network-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

## Read Network Status

Check whether the Network has become Active (required before creating workloads):

```bash
hcloud CCI readNetworkingCciIoV1beta1NamespacedNetworkStatus \
  --name=<network-name> --namespace=<ns-name> \
  --cli-region=<region> --cli-output=json
```

- Network must reach `Active` state before workloads can be created in the namespace
- If status is `Initializing`, wait and re-check

## Delete Network

**TWO-STEP CONFIRMATION REQUIRED.**

### Step 1: Warn the user

> **WARNING**: Deleting the Network will cause all pods in this namespace to lose network connectivity. This is irreversible.

### Step 2: Execute (only after explicit user confirmation)

```bash
hcloud CCI deleteNetworkingCciIoV1beta1NamespacedNetwork \
  --name=<network-name> --namespace=<ns-name> \
  --cli-region=<region>
```

## Annotation Key Reference

| Annotation Key | Value | Purpose | hcloud CLI Support |
|---------------|-------|---------|-------------------|
| `network.alpha.kubernetes.io/default-security-group` | Security group ID (e.g., `sg-xxxx`) | Default security group for Network | **Cannot pass via hcloud CLI** — dots treated as nested delimiters; use Python helper script |
| `namespace.kubernetes.io/flavor` | `general-computing` or `gpu-accelerated` | Namespace flavor type | Works via `--metadata.annotations.namespace-kubernetes-io/flavor` (hyphen workaround) |