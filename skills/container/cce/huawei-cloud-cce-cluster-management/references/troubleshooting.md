# Common Troubleshooting Issues

## Overview

Common issues and solutions in CCE cluster management operations.

## Issue Categories

| Error Type | Possible Cause | Solution |
|---------|---------|---------|
| 403 Insufficient Permissions | Missing IAM permissions | Check IAM policy configuration |
| 404 Resource Not Found | Incorrect cluster/node ID | Verify resource ID is correct |
| 400 Parameter Error | Invalid parameter format | Check parameter format and values |
| 409 State Conflict | Operation not allowed in current resource state | Wait for resource state change and retry |

## Common Issues

### 1. Cluster query returns empty list

**Possible Causes:**
- Incorrect region parameter
- Current account has no clusters

**Solutions:**
```bash
# Verify region is correct
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# Check other regions
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-east-3
```

### 2. Node operation returns insufficient permissions

**Possible Causes:**
- IAM lacks `cce:node:update` permission

**Solutions:**
Add CCE-related permissions for the user in the IAM console.

### 3. Cluster sleep/awaken operation failed

**Possible Causes:**
- Cluster state does not support this operation
- Cluster is executing other tasks

**Solutions:**
```bash
# First query cluster status
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# Confirm status is Available before operating
```

### 4. Node pool scaling not taking effect

**Possible Causes:**
- Forgot to add `confirm=true` parameter
- Node pool is currently scaling

**Solutions:**
```bash
# Add confirm parameter
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=5 \
  confirm=true
```

### 5. Password-related errors when creating nodes/node pools

**Error Messages:**
- `CCE_CM.0004 - Request is invalid, Unexpected initial node password format`
- `CCE_NODE_PASSWORD environment variable is not set`
- `CCE_NODE_PASSWORD length must be 8-26 characters`
- `CCE_NODE_PASSWORD must contain at least 3 of: uppercase, lowercase, digits, special chars`

**Causes:**
- `CCE_NODE_PASSWORD` environment variable not set
- Password complexity does not meet requirements (8-26 characters, must contain at least 3 of: uppercase, lowercase, digits, special characters)
- When calling CCE API directly, password not encrypted with SHA-512 salted encryption + base64 encoding

**Solutions:**
```bash
# Set password environment variable (must meet complexity requirements)
export CCE_NODE_PASSWORD="MyPass123!"

# The script automatically performs SHA-512 salted encryption + base64 encoding, no manual processing needed
python3 huawei-cloud.py huawei_create_cce_nodepool ...
```

When calling CCE API directly, you need to encrypt yourself:
```python
import os
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
```

### 6. "Flavor ENI network is not supported" error when creating node pool

**Error Message:** `Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

**Cause:** Node pool in a Turbo (ENI network) cluster uses a node flavor that does not support ENI.

**Flavors that do not support ENI:** `s6` series, `c6` series, etc.
**Flavors that support ENI:** `c7` series (e.g., `c7.large.2`), `s7` series

**Solutions:**
```bash
# Turbo cluster uses c7 series flavor
python3 huawei-cloud.py huawei_create_cce_nodepool \
  flavor=c7.large.2 \
  ...
```

### 7. "Data volume needed" error when creating node pool

**Error Message:** `Data volume needed for non-local-disk flavor or non-system diskType`

**Cause:** Some node flavors (non-local disk types) must configure data volumes.

**Solutions:**
```bash
python3 huawei-cloud.py huawei_create_cce_nodepool \
  ... \
  'data_volumes=[{"size":100,"type":"SSD"}]'
```

### 8. "instanceID is invalid" error when querying addon details

**Error Message:** `CCE.03400001 - Invalid request., instanceID is invalid`

**Cause:** Incorrect value passed to the `id` field of `ShowAddonInstanceRequest`.

**Solutions:**
- The `id` field should use the addon instance UID (obtained from `huawei_list_cce_addons` or the `uid` field in the creation response)
- Do not use the `addon_name` field (deprecated), use the `id` field instead
- Call `client.show_addon_instance()` method, not `client.show_addon()`

### 9. "InstanceSpec got unexpected keyword argument 'template_name'" error when installing addon

**Error Message:** `InstanceSpec.__init__() got an unexpected keyword argument 'template_name'`

**Cause:** The correct field name for CCE SDK `InstanceSpec` class is `addon_template_name`, not `template_name`.

**Solutions:**
```python
spec = InstanceSpec(
    addon_template_name="volcano",  # Correct
    # template_name="volcano",      # Incorrect
    ...
)
```

### 10. "cannot import name 'CreateNodeRequestBody'" error when creating node

**Error Message:** `cannot import name 'CreateNodeRequestBody' from 'huaweicloudsdkcce.v3'`

**Cause:** CCE SDK does not have `CreateNodeRequestBody` class; use `Node` object as the body of `CreateNodeRequest`.

**Solutions:**
```python
from huaweicloudsdkcce.v3 import CreateNodeRequest, Node, NodeMetadata, NodeSpec

body = Node(kind="Node", api_version="v3", metadata=NodeMetadata(name="my-node"), spec=node_spec)
request = CreateNodeRequest(cluster_id="cluster-id")
request.body = body
response = client.create_node(request)
```

### 11. SDK attribute name error when creating node

**Error Message:** `Login.__init__() got an unexpected keyword argument 'userPassword'` or similar

**Cause:** CCE SDK Python package attribute names use snake_case, not camelCase.

**Common error reference:**

| Incorrect (camelCase) | Correct (snake_case) |
|----------------------|----------------------|
| `Login(userPassword=...)` | `Login(user_password=...)` |
| `Login(sshkey=...)` | `Login(ssh_key=...)` |
| `NodeSpec(rootVolume=...)` | `NodeSpec(root_volume=...)` |
| `NodeSpec(dataVolumes=...)` | `NodeSpec(data_volumes=...)` |
| `NodeSpec(nodeNicSpec=...)` | `NodeSpec(node_nic_spec=...)` |
| `NodeNicSpec(subnetId=...)` | `NodeNicSpec(primary_nic={"subnetId": "xxx"})` |

### 12. NodeNicSpec construction error

**Error Message:** `NodeNicSpec.__init__() got an unexpected keyword argument 'subnetId'`

**Cause:** `NodeNicSpec` does not directly accept `subnetId` parameter; pass it through `primary_nic` dict.

**Solutions:**
```python
node_nic_spec = NodeNicSpec(primary_nic={"subnetId": "subnet-id"})  # Correct
# NodeNicSpec(subnetId="subnet-id")  # Incorrect
```