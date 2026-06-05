# CCE SDK API Reference

## Overview

Huawei Cloud CCE Python SDK API call reference documentation, including key notes and common issues.

## SDK Installation

```bash
pip install huaweicloudsdkcore huaweicloudsdkcce huaweicloudsdkiam
```

Node password salted encryption requires installing passlib. The script reads the password from the `CCE_NODE_PASSWORD` environment variable and automatically validates complexity:

```bash
pip install passlib
export CCE_NODE_PASSWORD="your-password"
```

## Authentication Configuration

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

credentials = BasicCredentials(ak, sk, project_id)
client = CceClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(CceRegion.value_of("cn-north-4")) \
    .build()
```

## Main APIs

| API | Description | Corresponding Tool |
|-----|-------------|--------------------|
| ListClusters | List clusters | `huawei_list_cce_clusters` |
| CreateCluster | Create cluster | `huawei_create_cce_cluster` |
| DeleteCluster | Delete cluster | `huawei_delete_cce_cluster` |
| UpdateCluster | Update cluster | `huawei_hibernate/awake_cce_cluster` |
| ListNodes | List nodes | `huawei_list_cce_nodes` |
| CreateNode | Create node | `huawei_create_cce_node` |
| DeleteNode | Delete node | `huawei_delete_cce_node` |
| ListNodePools | List node pools | `huawei_list_cce_nodepools` |
| CreateNodePool | Create node pool | `huawei_create_cce_nodepool` |
| UpdateNodePool | Update node pool | `huawei_resize_cce_nodepool` |
| CreateAddonInstance | Install addon | `huawei_install_cce_addon` |
| ShowAddonInstance | Get addon details | `huawei_get_cce_addon_detail` |
| ListAddonTemplates | List addon templates | No corresponding tool, needs direct SDK call |

## Example Code

### List Clusters

```python
from huaweicloudsdkcce.v3 import ListClustersRequest

request = ListClustersRequest()
response = client.list_clusters(request)
for cluster in response.items:
    print(f"Cluster: {cluster.metadata.name}, Status: {cluster.status.phase}")
```

### Create Node Pool (with Password Salting)

> **Important: The password is read from the `CCE_NODE_PASSWORD` environment variable. The `UserPassword.password` field must be passed a SHA-512 salted and base64-encoded value; the raw password cannot be passed directly.**

```python
import os
from huaweicloudsdkcce.v3 import (
    CreateNodePoolRequest, NodePool, NodePoolMetadata, NodePoolSpec,
    NodeSpec, Login, UserPassword, Volume
)
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")

login = Login()
login.user_password = UserPassword(password=salted_b64)

node_spec = NodeSpec(
    flavor="c7.large.2",
    az="cn-north-4a",
    os="EulerOS",
    root_volume=Volume(size=40, volumetype="GPSSD"),
    login=login,
)
# Turbo cluster node pools also need data_volumes configured
node_spec.data_volumes = [Volume(size=100, volumetype="SSD")]

spec = NodePoolSpec(initial_node_count=1, node_template=node_spec)
body = NodePool(kind="NodePool", api_version="v3", metadata=NodePoolMetadata(name="my-pool"), spec=spec)

request = CreateNodePoolRequest(cluster_id="cluster-id", body=body)
response = client.create_node_pool(request)
```

### Create Node (with Password Salting)

> **Important: The SDK does not have a `CreateNodeRequestBody` class. Use the `Node` object as the request body. `NodeSpec.count` sets the node count. SDK attribute names use snake_case.**

```python
import os
from huaweicloudsdkcce.v3 import (
    CreateNodeRequest, Node, NodeMetadata, NodeSpec,
    Volume, Login, UserPassword, NodeNicSpec
)
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")

login = Login(user_password=UserPassword(username="root", password=salted_b64))
# Note: attribute names are snake_case: user_password, ssh_key, root_volume, data_volumes, node_nic_spec

node_spec = NodeSpec(
    flavor="c7.large.2",
    az="cn-north-4a",
    os="EulerOS 2.9",
    root_volume=Volume(size=40, volumetype="SSD"),
    login=login,
    data_volumes=[Volume(size=100, volumetype="SSD")],  # snake_case, not dataVolumes
    node_nic_spec=NodeNicSpec(primary_nic={"subnetId": "subnet-id"}),  # Note: primary_nic is a dict
    count=1,  # node count is set in NodeSpec.count
)

body = Node(
    kind="Node",
    api_version="v3",
    metadata=NodeMetadata(name="node-clusterid8"),
    spec=node_spec,
)

request = CreateNodeRequest(cluster_id="cluster-id")
request.body = body
response = client.create_node(request)
```

### Install Addon

> **Important: `InstanceSpec` uses the `addon_template_name` field, not `template_name`.**

```python
from huaweicloudsdkcce.v3 import (
    CreateAddonInstanceRequest, AddonInstance, AddonMetadata, InstanceSpec
)

spec = InstanceSpec(
    cluster_id="cluster-id",
    version="1.21.7",
    addon_template_name="volcano",  # Note: field name is addon_template_name, not template_name
    values={"basic": {"category": "small", "flavor": 1},
            "custom": {"default_scheduler": True}}
)

body = AddonInstance(
    kind="Addon", api_version="v3",
    metadata=AddonMetadata(annotations={"addon.install/type": "install"}),
    spec=spec
)

request = CreateAddonInstanceRequest(body=body)
response = client.create_addon_instance(request)
```

### Get Addon Details

> **Important: `ShowAddonInstanceRequest` uses the `id` field, not `addon_name`. And use the `show_addon_instance` method, not `show_addon`.**

```python
from huaweicloudsdkcce.v3 import ShowAddonInstanceRequest

request = ShowAddonInstanceRequest()
request.cluster_id = "cluster-id"
request.id = "addon-instance-id"  # Note: field name is id, not addon_name

response = client.show_addon_instance(request)  # Note: method name is show_addon_instance, not show_addon
print(f"Addon: {response.metadata.name}, Status: {response.status}")
```

### List Addon Template Versions

Before installing an addon, query available versions:

```python
from huaweicloudsdkcce.v3 import ListAddonTemplatesRequest

request = ListAddonTemplatesRequest()
request.cluster_id = "cluster-id"
request.addon_template_name = "volcano"

response = client.list_addon_templates(request)
for item in response.items:
    for v in item.spec.versions:
        print(f"  Version: {v.version}, Stable: {v.stable}")
```

### Update Node Scheduling Status

```python
from huaweicloudsdkcce.v3 import UpdateNodeRequest, NodeMetadata, NodeSpec

request = UpdateNodeRequest(
    cluster_id="cluster-id",
    node_id="node-id",
    body=NodeUpdateRequest(
        metadata=NodeMetadata(unschedulable=True)
    )
)
client.update_node(request)
```

## SDK Key Notes

| Issue | Description |
|-------|-------------|
| `InstanceSpec.template_name` | ❌ Wrong field name, should use `addon_template_name` |
| `ShowAddonInstanceRequest.addon_name` | ❌ Wrong field name, should use `id` (value is addon instance UID) |
| `client.show_addon()` | ❌ Wrong method name, should use `client.show_addon_instance()` |
| `UserPassword.password` raw password | ❌ Cannot pass raw password directly; must use SHA-512 salted + base64 encoding. The script reads from `CCE_NODE_PASSWORD` environment variable and handles it automatically |
| `CreateNodeRequestBody` | ❌ This class does not exist; use `Node` object as the body of `CreateNodeRequest` |
| SDK attribute names camelCase | ❌ Some old examples use camelCase; the SDK actually uses snake_case: `user_password`, `ssh_key`, `root_volume`, `data_volumes`, `node_nic_spec` |
| `NodeNicSpec(subnetId=...)` | ❌ Wrong construction; should use `NodeNicSpec(primary_nic={"subnetId": "xxx"})` |
| `CreateNodeRequestBody.count` | ❌ Does not exist; node count is set via `NodeSpec.count` |
| Turbo cluster node flavor | Must use ENI-compatible specs (e.g., `c7` series); `s6`, `c6`, etc. do not support ENI |
| Non-local-disk node data_volumes | Some specs require data volumes to be configured; otherwise creation fails |

## Official Documentation

- [CCE API Reference](https://support.huaweicloud.com/api-cce/cce_02_0082.html)
- [CCE Python SDK](https://support.huaweicloud.com/sdk-python/cce_02_0101.html)
- [Password Salting Encryption Method](https://support.huaweicloud.com/api-cce/add-salt.html)