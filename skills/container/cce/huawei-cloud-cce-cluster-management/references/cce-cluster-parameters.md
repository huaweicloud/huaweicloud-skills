# Cluster Creation Parameter Reference

## Overview

Detailed parameters required for creating CCE clusters, node pools, and nodes, including key constraints such as Turbo clusters, password salting/encryption, and ENI flavor compatibility.

## Required Cluster Parameters

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| `region` | Huawei Cloud region | `cn-north-4` |
| `cluster_name` | Cluster name | `my-cluster` |
| `cluster_version` | Kubernetes version | `v1.28` |
| `flavor_id` | Cluster specification | `cce.s1.small` |
| `vpc_id` | VPC ID | `vpc-xxx` |
| `subnet_id` | Subnet ID | `subnet-xxx` |

## Optional Cluster Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `cluster_type` | Cluster type | `VirtualMachine` |
| `container_network_type` | Container network type | `overlay_l2` |
| `container_network_cidr` | Container network CIDR | Auto-assigned |
| `eni_subnet_id` | ENI subnet ID (Turbo cluster) | Empty |
| `description` | Cluster description | Empty |

### Turbo Cluster

When creating a CCE Turbo (ENI network) cluster, set:

- `cluster_type=VirtualMachine` (the Turbo cluster's category is automatically determined by the API based on container_network_type)
- `container_network_type=eni`
- `flavor_id` can use any specification such as `cce.s1.small`

The `spec.category` returned by the API will automatically become `Turbo`.

## Cluster Specifications

| Specification | Description | Applicable Scenario |
|---------------|-------------|---------------------|
| `cce.s1.small` | Small scale, 50 nodes | Development & testing |
| `cce.s1.medium` | Medium scale, 200 nodes | Production environment |
| `cce.s1.large` | Large scale, 1000 nodes | Large-scale applications |
| `cce.s2.small` | HA small scale | HA testing |
| `cce.s2.medium` | HA medium scale | HA production |

## Node Pool Creation Parameters

### Required Parameters

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| `region` | Huawei Cloud region | `cn-north-4` |
| `cluster_id` | Cluster ID | `xxx` |
| `nodepool_name` | Node pool name | `dev-worker-pool` |
| `flavor` | Node specification | `c7.large.2` |
| `availability_zone` | Availability zone | `cn-north-4a` |
| `root_volume_size` | System disk size (GB) | `40` |
| `root_volume_type` | System disk type | `GPSSD` |
| `initial_node_count` | Initial node count | `1` |

### Login Authentication (one is required)

| Parameter | Description | Notes |
|-----------|-------------|-------|
| `ssh_key` | SSH key pair name | Mutually exclusive with password |
| Password | Read from `CCE_NODE_PASSWORD` environment variable | 8-26 characters, must include at least three of: uppercase, lowercase, digits, special characters |

> **Important: The password is passed via the `CCE_NODE_PASSWORD` environment variable. The script automatically performs SHA-512 salted encryption + base64 encoding. No manual processing is needed.**

### CCE_NODE_PASSWORD Environment Variable

When creating nodes/node pools without providing `ssh_key`, the script reads the password from the environment variable `CCE_NODE_PASSWORD`:

```bash
export CCE_NODE_PASSWORD="your_password"
```

Password complexity requirements:
- Length: 8-26 characters
- Must include at least three of: uppercase letters, lowercase letters, digits, special characters
- Special characters: `!@$%^-_=+[]{}:,./?`

The script automatically validates password complexity and returns an error message if requirements are not met.

### Password Salting and Encryption

> **Important: The CCE API requires the password field to be SHA-512 salted encrypted and then base64 encoded. Raw passwords cannot be passed directly.**

Encryption steps (Python):

```python
from passlib.hash import sha512_crypt
import base64

hashed = sha512_crypt.using(rounds=5000).hash("raw_password")
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
# salted_b64 is the value for the UserPassword.password field
```

Dependency required: `pip install passlib`

### Optional Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `os_type` | Operating system | `EulerOS` |
| `data_volumes` | Data volume configuration JSON | Required for some specifications |
| `subnet_id` | Subnet ID | Uses cluster subnet |
| `autoscaling_enabled` | Enable autoscaling | `false` |
| `min_node_count` | Minimum node count for autoscaling | 0 |
| `max_node_count` | Maximum node count for autoscaling | 0 |

### Data Volumes (data_volumes)

Some node specifications (e.g., non-local disk types) **must have data volumes configured**, otherwise creation will fail. Format is a JSON array:

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor Compatibility

> **Important: Node pools in Turbo (ENI network) clusters must use ENI-compatible flavors.**

Flavors that do not support ENI (such as `s6.large.2`, `c6.large.2`) will produce an error:
`Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

Recommended for Turbo clusters: `c7` series (e.g., `c7.large.2`), `s7` series.

## Node Creation Parameters

Parameters for direct node creation (non-node pool) are essentially the same as node pool, with the additional:

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `node_count` | Number of nodes to create | `1` |

The password also requires SHA-512 salted encryption + base64 encoding.

## Kubernetes Versions

Common versions: `v1.27`, `v1.28`, `v1.29`, `v1.30`, `v1.31`

## Password Salting and Encryption

When creating nodes/node pools, the `password` field must be SHA-512 salted encrypted and then base64 encoded. Raw passwords cannot be passed directly.

### Salting Method

 Reference: [CCE Password Salting and Encryption](https://support.huaweicloud.com/api-cce/add-salt.html)

 

 ### Python Example

 ```python
from passlib.hash import sha512_crypt
import base64

 hashed = sha512_crypt.using(rounds=5000).hash("raw_password")
 salted_password = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
 ```



### Password Complexity Requirements

 - Length: 8-26 characters
 - Must include at least three of: uppercase letters, lowercase letters, digits, special characters
 - Special characters: `!@$%^-_=+[]{}:,./?`

## Example

### Create a Standard Cluster

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=my-cluster \
  cluster_version=v1.28 \
  flavor_id=cce.s1.small \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

### Create a Turbo Cluster

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=dev-turbo-cluster \
  cluster_version=v1.28 \
  cluster_type=VirtualMachine \
  container_network_type=eni \
  flavor_id=cce.s1.small \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

### Create a Node Pool

```bash
export CCE_NODE_PASSWORD="your_password"

python3 huawei-cloud.py huawei_create_cce_nodepool \
    region=cn-north-4 \
    cluster_id=xxx \
    nodepool_name=dev-worker-pool \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    initial_node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]'
```

## Notes

- Cluster name: 1-63 characters, letters, digits, and hyphens
- VPC and subnet must exist in the specified region
- Cluster creation may take 5-15 minutes
- Cluster specification cannot be changed after creation
- Turbo cluster nodes must use ENI-compatible flavors
- Non-local disk specifications must have data volumes configured
- The password field must be SHA-512 salted + base64 encoded; the script handles this automatically