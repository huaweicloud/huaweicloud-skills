# CLI Command Examples — ModelArts Resource Pool Management

> Detailed command syntax and examples for all 53 ModelArts resource pool CLI APIs.
> Replace `{region}` with actual region (e.g., `cn-north-4`). `project_id` auto-resolved if omitted.

---

## Operation Summary

| # | Operation | Method | Domain | Write | Description |
|---|-----------|--------|--------|-------|-------------|
| 1 | ListPools | GET | Pool Mgmt | No | List resource pools |
| 2 | ShowPool | GET | Pool Mgmt | No | Show pool details |
| 3 | CreatePool | POST | Pool Mgmt | Yes | Create resource pool |
| 4 | PatchPool | PATCH | Pool Mgmt | Yes | Update resource pool |
| 5 | DeletePool | DELETE | Pool Mgmt | Yes | Delete resource pool |
| 6 | ShowPoolMonitor | GET | Pool Mgmt | No | Show pool monitor data |
| 7 | ShowPoolStatistics | GET | Pool Mgmt | No | Show pool statistics |
| 8 | ShowPoolRuntimeMetrics | GET | Pool Mgmt | No | Show pool runtime metrics |
| 9 | ShowPoolNodeConfig | GET | Pool Mgmt | No | Show pool node config |
| 10 | CreateOrderId | POST | Pool Mgmt | Yes | Create order ID |
| 11 | ShowOrder | GET | Pool Mgmt | No | Show order details |
| 12 | ListPoolNodes | GET | Node Mgmt | No | List pool nodes |
| 13 | ShowPoolNode | GET | Node Mgmt | No | Show pool node details |
| 14 | BatchDeletePoolNodes | POST | Node Mgmt | Yes | Batch delete nodes |
| 15 | BatchUpdatePoolNodes | POST | Node Mgmt | Yes | Batch update nodes |
| 16 | BatchLockPoolNodes | POST | Node Mgmt | Yes | Batch lock nodes |
| 17 | BatchUnlockPoolNodes | POST | Node Mgmt | Yes | Batch unlock nodes |
| 18 | BatchRebootPoolNodes | POST | Node Mgmt | Yes | Batch reboot nodes |
| 19 | BatchResetPoolNodes | POST | Node Mgmt | Yes | Batch reset nodes |
| 20 | BatchResizePoolNodes | POST | Node Mgmt | Yes | Batch resize nodes |
| 21 | BatchMigratePoolNodes | POST | Node Mgmt | Yes | Batch migrate nodes |
| 22 | BatchBindPoolNodes | POST | Node Mgmt | Yes | Batch bind nodes |
| 23 | ListNodePools | GET | Node Pool | No | List node pools |
| 24 | ShowNodePool | GET | Node Pool | No | Show node pool details |
| 25 | CreateNodePool | POST | Node Pool | Yes | Create node pool |
| 26 | PatchNodePool | PATCH | Node Pool | Yes | Update node pool |
| 27 | DeleteNodePool | DELETE | Node Pool | Yes | Delete node pool |
| 28 | ListNodePoolNodes | GET | Node Pool | No | List node pool nodes |
| 29 | ListNetworks | GET | Network | No | List networks |
| 30 | ShowNetwork | GET | Network | No | Show network details |
| 31 | CreateNetwork | POST | Network | Yes | Create network |
| 32 | PatchNetwork | PATCH | Network | Yes | Update network |
| 33 | DeleteNetwork | DELETE | Network | Yes | Delete network |
| 34 | ShowNetworkAvailableIp | GET | Network | No | Show available IPs |
| 35 | ListPoolTags | GET | Tags | No | List pool tags |
| 36 | ShowPoolTags | GET | Tags | No | Show pool tags |
| 37 | BatchCreatePoolTags | POST | Tags | Yes | Batch create tags |
| 38 | BatchDeletePoolTags | POST | Tags | Yes | Batch delete tags |
| 39 | ListPluginTemplates | GET | Plugin | No | List plugin templates |
| 40 | ShowPluginTemplate | GET | Plugin | No | Show plugin template |
| 41 | ListPoolPlugins | GET | Plugin | No | List pool plugins |
| 42 | CreatePoolPlugin | POST | Plugin | Yes | Create pool plugin |
| 43 | ListWorkloads | GET | Jobs | No | List workloads |
| 44 | ShowWorkloadStatistics | GET | Jobs | No | Show workload statistics |
| 45 | ListJobs | GET | Jobs | No | List jobs |
| 46 | ListScheduledEvents | GET | Events | No | List scheduled events |
| 47 | AcceptScheduledEvent | POST | Events | Yes | Accept scheduled event |
| 48 | ShowOsConfig | GET | OS Config | No | Show OS config |
| 49 | ShowOsQuota | GET | OS Config | No | Show OS quota |
| 50 | ListResourceFlavors | GET | Resource | No | List resource flavors |
| 51 | ListEvents | GET | Resource | No | List events |
| 52 | ShowNodeConfigTemplate | GET | Resource | No | Show node config template |
| 53 | ShowPoolNodeConfigTemplate | GET | Resource | No | Show pool node config template |

**Statistics**: 53 total operations — 26 read (GET), 27 write (POST/PATCH/DELETE), 10 functional domains.

---

## 1. Resource Pool Management (11 APIs)

### 1.1 ListPools — 查询资源池列表

```bash
hcloud ModelArts ListPools --cli-region={region} [--limit=10] [--offset=0] [--pool_name={name}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--limit` | No | Max results per page (default 10) |
| `--offset` | No | Pagination offset (default 0) |
| `--pool_name` | No | Filter by pool name (fuzzy match) |

### 1.2 ShowPool — 查询资源池详情

```bash
hcloud ModelArts ShowPool --cli-region={region} --pool_name={pool_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |

### 1.3 CreatePool — 创建资源池

> ⚠️ **Write operation** — requires user confirmation.
> 💰 **Pricing inquiry required** — query BSS on-demand price for the target flavor before creation.

#### Required Information to Collect

| # | Information | CLI Parameter | Options |
|---|-------------|---------------|---------|
| 1 | Region | `--cli-region` | e.g., `cn-north-4` |
| 2 | Pool name | `--metadata.labels.os.modelarts/name` | User-defined name |
| 3 | Pool type | `--spec.type` | `Dedicate`(物理/专属), `Logical`(逻辑) |
| 4 | Job scope | `--spec.scope.1` | `Train`, `Infer`, `Notebook` (at least one) |
| 5 | Billing mode | `--metadata.annotations.os.modelarts/billing.mode` | `0`(按需), `1`(包周期) |
| 6 | Node flavor | `--spec.resources.1.flavor` | Query `ListResourceFlavors` first |
| 7 | Node count | `--spec.resources.1.count` | Positive integer |
| 8 | Network (Dedicate only) | `--spec.network.name` | Query `ListNetworks` first |

#### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--spec.resources.1.maxCount` | Elastic scaling upper limit (≥ count) | Same as count |
| `--spec.resources.1.os.name` | Node OS image name | `Huawei Cloud EulerOS 2.0` |
| `--metadata.labels.os.modelarts/node.prefix` | Custom node name prefix | Auto-generated |
| `--metadata.annotations.os.modelarts/description` | Pool description | None |
| `--spec.resources.1.extendParams.dockerBaseSize` | Container engine space (GB) | `50` |
| `--spec.driver.gpuVersion` | GPU driver version | Auto-selected |
| `--spec.driver.npuVersion` | NPU driver version | Auto-selected |

#### Fixed Parameters (no user input needed)

| CLI Parameter | Value | Description |
|---------------|-------|-------------|
| `--apiVersion` | `v2` | API version, always v2 |
| `--kind` | `Pool` | Resource type, always Pool |

#### Package-Period Parameters (billing.mode=1)

| Parameter | Description |
|-----------|-------------|
| `--metadata.annotations.os.modelarts/period.num` | Subscription period number |
| `--metadata.annotations.os.modelarts/period.type` | `month` or `year` |
| `--metadata.annotations.os.modelarts/auto.pay` | `true` or `false` |
| `--metadata.annotations.os.modelarts/auto.renew` | `1` or `0` |

#### Example: On-demand Dedicate pool

```bash
hcloud ModelArts CreatePool --cli-region=cn-north-4 \
  --apiVersion=v2 \
  --kind=Pool \
  --metadata.labels.os.modelarts/name=my-training-pool \
  --metadata.annotations.os.modelarts/billing.mode=0 \
  --spec.type=Dedicate \
  --spec.scope.1=Train \
  --spec.network.name={network_name} \
  --spec.resources.1.flavor=modelarts.vm.cpu.16u64g.d \
  --spec.resources.1.count=1 \
  --spec.resources.1.maxCount=1
```

#### Example: On-demand Logical pool (no network needed)

```bash
hcloud ModelArts CreatePool --cli-region=cn-north-4 \
  --apiVersion=v2 \
  --kind=Pool \
  --metadata.labels.os.modelarts/name=my-logical-pool \
  --metadata.annotations.os.modelarts/billing.mode=0 \
  --spec.type=Logical \
  --spec.scope.1=Train \
  --spec.resources.1.flavor=modelarts.vm.cpu.16u64g.d \
  --spec.resources.1.count=1 \
  --spec.resources.1.maxCount=1
```

#### Example: Package-period Dedicate pool

```bash
hcloud ModelArts CreatePool --cli-region=cn-north-4 \
  --apiVersion=v2 \
  --kind=Pool \
  --metadata.labels.os.modelarts/name=my-period-pool \
  --metadata.annotations.os.modelarts/billing.mode=1 \
  --metadata.annotations.os.modelarts/period.num=1 \
  --metadata.annotations.os.modelarts/period.type=month \
  --metadata.annotations.os.modelarts/auto.pay=true \
  --metadata.annotations.os.modelarts/auto.renew=0 \
  --spec.type=Dedicate \
  --spec.scope.1=Train \
  --spec.network.name={network_name} \
  --spec.resources.1.flavor=modelarts.vm.cpu.16u64g.d \
  --spec.resources.1.count=2 \
  --spec.resources.1.maxCount=5
```

#### Example: Multi-scope + GPU flavor

```bash
hcloud ModelArts CreatePool --cli-region=cn-north-4 \
  --apiVersion=v2 \
  --kind=Pool \
  --metadata.labels.os.modelarts/name=my-gpu-pool \
  --metadata.annotations.os.modelarts/billing.mode=0 \
  --spec.type=Dedicate \
  --spec.scope.1=Train \
  --spec.scope.2=Infer \
  --spec.network.name={network_name} \
  --spec.resources.1.flavor=modelarts.vm.gpu.2v100nv16g.16u128g.d \
  --spec.resources.1.count=1 \
  --spec.resources.1.maxCount=3
```

#### Parameter Name Mapping

> ⚠️ Simplified names in SKILL.md vs actual hcloud CLI parameter names:

| Simplified | Actual CLI Parameter | Notes |
|------------|---------------------|-------|
| `--metadata.name` | `--metadata.labels.os.modelarts/name` | Pool name is under labels |
| `--spec.type` | `--spec.type` | Value is `Dedicate` (no trailing d) |
| `--spec.networkId` | `--spec.network.name` | Value is network's metadata.name |
| (none) | `--apiVersion=v2` | Fixed parameter |
| (none) | `--kind=Pool` | Fixed parameter |

#### Agent Interaction Checklist

Before executing CreatePool, confirm ALL of the following:

- [ ] **Region** — confirmed, ModelArts available in region
- [ ] **Pool name** — confirmed, no name conflict
- [ ] **Pool type** — `Dedicate` or `Logical`
- [ ] **Job scope** — at least one of Train/Infer/Notebook
- [ ] **Billing mode** — on-demand(0) or package-period(1)
- [ ] **Node flavor** — `ListResourceFlavors` queried, user selected
- [ ] **Node count** — confirmed
- [ ] **Network** (Dedicate required) — `ListNetworks` queried, user selected; create if none
- [ ] **Pricing** — BSS on-demand price queried and shown
- [ ] **User confirmation** — user explicitly confirmed

#### Common CreatePool Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `metadata.name` parameter incorrect | Used simplified parameter name | Use `--metadata.labels.os.modelarts/name` |
| `spec.network is required` | Dedicate pool missing network | Query and select network first |
| Flavor sold out | Selected flavor unavailable in all AZs | Filter soldout flavors from `ListResourceFlavors` |
| `Dedicated` value incorrect | Spelling error | Correct value is `Dedicate` (no trailing d) |
| Package-period missing period params | billing.mode=1 without period params | Must include period.num and period.type |

### 1.4 PatchPool — 更新资源池

> **⚠️ CRITICAL**: PATCH operations require `--cli-jsonInput` with `Content-Type: application/merge-patch+json` header.
> See [known-issues.md](known-issues.md#1-patch-operations-content-type-patchpool-patchnetwork-patchnodepool) for details.

```bash
# ⚠️ Write operation — requires user confirmation
# Step 1: Create JSON input file with merge-patch+json Content-Type
cat > /tmp/patch_pool.json << 'EOF'
{
  "header": {
    "Content-Type": "application/merge-patch+json"
  },
  "body": {
    "metadata": {
      "annotations": {
        "os.modelarts/description": "updated-pool-description"
      }
    }
  }
}
EOF

# Step 2: Execute PATCH with --cli-jsonInput
hcloud ModelArts PatchPool --cli-region={region} --pool_name={pool_name} --cli-jsonInput=/tmp/patch_pool.json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--cli-jsonInput` | Yes | JSON file with header.Content-Type=application/merge-patch+json |
| `body.metadata.annotations` | No | Annotations to merge-patch (e.g., description) |

### 1.5 DeletePool — 删除资源池

```bash
# ⚠️ Write operation — requires user confirmation (irreversible)
hcloud ModelArts DeletePool --cli-region={region} --pool_name={pool_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |

### 1.6 ShowPoolMonitor — 查询资源池监控

```bash
hcloud ModelArts ShowPoolMonitor --cli-region={region} --pool_name={pool_name}
```

### 1.7 ShowPoolStatistics — 查询资源池统计

```bash
hcloud ModelArts ShowPoolStatistics --cli-region={region}
```

### 1.8 ShowPoolRuntimeMetrics — 查询资源池运行时指标

```bash
hcloud ModelArts ShowPoolRuntimeMetrics --cli-region={region}
```

### 1.9 ShowPoolNodeConfig — 查询资源池节点配置

```bash
hcloud ModelArts ShowPoolNodeConfig --cli-region={region} --pool_name={pool_name}
```

### 1.10 CreateOrderId — 创建订单ID

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateOrderId --cli-region={region} --name={pool_name} [--period_num=1] [--period_type=month]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | Pool name |
| `--period_num` | No | Subscription period number |
| `--period_type` | No | Period type: `month` or `year` |

### 1.11 ShowOrder — 查询订单详情

```bash
hcloud ModelArts ShowOrder --cli-region={region} --order_name={order_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--order_name` | Yes | Order name |

---

## 2. Pool Node Management (11 APIs)

### 2.1 ListPoolNodes — 查询资源池节点列表

```bash
hcloud ModelArts ListPoolNodes --cli-region={region} --pool_name={pool_name} [--limit=10] [--offset=0]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--limit` | No | Max results per page |
| `--offset` | No | Pagination offset |

### 2.2 ShowPoolNode — 查询资源池节点详情

```bash
hcloud ModelArts ShowPoolNode --cli-region={region} --pool_name={pool_name} --node_name={node_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--node_name` | Yes | Node name |

### 2.3 BatchDeletePoolNodes — 批量删除节点

```bash
# ⚠️ Write operation — requires user confirmation (irreversible)
hcloud ModelArts BatchDeletePoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

### 2.4 BatchUpdatePoolNodes — 批量更新节点

> **⚠️ CRITICAL**: The `--action` parameter help says `[true|false]` but actual values are string constants.
> Must use `--cli-jsonInput` for correct behavior.
> See [known-issues.md](known-issues.md#5-batchupdatepoolnodes-action-parameter-bug) for details.

```bash
# ⚠️ Write operation — requires user confirmation
# Step 1: Create JSON input file
cat > /tmp/batch_update_nodes.json << 'EOF'
{
  "body": {
    "nodeNames": ["node-name-1"],
    "action": "createTags",
    "tags": [{"key": "env", "value": "test"}]
  }
}
EOF

# Step 2: Execute with --cli-jsonInput
hcloud ModelArts BatchUpdatePoolNodes --cli-region={region} --pool_name={pool_name} --cli-jsonInput=/tmp/batch_update_nodes.json
```

| Action Value | Purpose |
|-------------|---------|
| `openHaRedundant` | Enable HA redundancy |
| `closeHaRedundant` | Disable HA redundancy |
| `createTags` | Create node tags |
| `deleteTags` | Delete node tags |

### 2.5 BatchLockPoolNodes — 批量锁定节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchLockPoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

### 2.6 BatchUnlockPoolNodes — 批量解锁节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchUnlockPoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

### 2.7 BatchRebootPoolNodes — 批量重启节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchRebootPoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

### 2.8 BatchResetPoolNodes — 批量重置节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchResetPoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1} --image_id={image_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--node_name.1` | Yes | Node name (indexed) |
| `--image_id` | Yes | Image ID for OS reinstallation |

### 2.9 BatchResizePoolNodes — 批量变更节点规格

```bash
# ⚠️ Write operation — requires user confirmation
# 💰 Pricing inquiry recommended — resizing changes flavor and may change costs
hcloud ModelArts BatchResizePoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1} --flavor_id={flavor_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--node_name.1` | Yes | Node name (indexed) |
| `--flavor_id` | Yes | Target flavor ID |

### 2.10 BatchMigratePoolNodes — 批量迁移节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchMigratePoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

### 2.11 BatchBindPoolNodes — 批量绑定节点

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchBindPoolNodes --cli-region={region} --pool_name={pool_name} --node_name.1={node1}
```

#### Batch Node Operations — Common Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--node_name.1` | Yes | First node name (indexed) |
| `--node_name.2` | No | Second node name (indexed) |
| `--node_name.N` | No | Nth node name (indexed) |

---

## 3. Node Pool Management (6 APIs)

### 3.1 ListNodePools — 查询节点池列表

```bash
hcloud ModelArts ListNodePools --cli-region={region} --pool_name={pool_name}
```

### 3.2 ShowNodePool — 查询节点池详情

```bash
hcloud ModelArts ShowNodePool --cli-region={region} --pool_name={pool_name} --nodepool_name={nodepool_name}
```

### 3.3 CreateNodePool — 创建节点池

> **⚠️ Constraints**: `count` must be ≥ 1; `maxCount` must be ≤ `count`; billing annotation required when count > 0.
> See [known-issues.md](known-issues.md#18-createnodepool-count-and-maxcount-rules) for details.

```bash
# ⚠️ Write operation — requires user confirmation
# 💰 Pricing inquiry required — query BSS on-demand price for target flavor
hcloud ModelArts CreateNodePool --cli-region={region} \
  --pool_name={pool_name} \
  --nodepool_name={nodepool_name} \
  --metadata.name={nodepool_name} \
  --spec.resources.flavor={flavor} \
  --spec.resources.count=1 \
  --spec.resources.maxCount=1 \
  --spec.resources.nodePool={nodepool_name} \
  --spec.resources.os.name="Huawei Cloud EulerOS 2.0" \
  --metadata.annotations.os.modelarts/billing.mode=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--nodepool_name` | Yes | Node pool name |
| `--metadata.name` | Yes | Node pool name |
| `--spec.resources.flavor` | Yes | Resource flavor (from ListResourceFlavors) |
| `--spec.resources.count` | Yes | Node count (must be ≥ 1) |
| `--spec.resources.maxCount` | Yes | Max node count (must be ≤ count) |
| `--spec.resources.os.name` | Yes | OS name |
| `--metadata.annotations.os.modelarts/billing.mode` | Yes | 0=on-demand, 1=package-period |

### 3.4 PatchNodePool — 更新节点池

> **⚠️ CRITICAL**: PATCH operations require `--cli-jsonInput` with `Content-Type: application/merge-patch+json` header.
> See [known-issues.md](known-issues.md#1-patch-operations-content-type-patchpool-patchnetwork-patchnodepool) for details.

```bash
# ⚠️ Write operation — requires user confirmation
# Step 1: Create JSON input file with merge-patch+json Content-Type
cat > /tmp/patch_nodepool.json << 'EOF'
{
  "header": {
    "Content-Type": "application/merge-patch+json"
  },
  "body": {
    "spec": {
      "resources": {
        "flavor": "modelarts.bm.4u8g.d910",
        "count": 2,
        "maxCount": 2
      }
    }
  }
}
EOF

# Step 2: Execute PATCH with --cli-jsonInput
hcloud ModelArts PatchNodePool --cli-region={region} --pool_name={pool_name} --nodepool_name={nodepool_name} --cli-jsonInput=/tmp/patch_nodepool.json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--nodepool_name` | Yes | Node pool name |
| `--cli-jsonInput` | Yes | JSON file with header.Content-Type=application/merge-patch+json |

### 3.5 DeleteNodePool — 删除节点池

```bash
# ⚠️ Write operation — requires user confirmation (irreversible)
hcloud ModelArts DeleteNodePool --cli-region={region} --pool_name={pool_name} --nodepool_name={nodepool_name}
```

### 3.6 ListNodePoolNodes — 查询节点池节点列表

```bash
hcloud ModelArts ListNodePoolNodes --cli-region={region} --pool_name={pool_name} --nodepool_name={nodepool_name}
```

#### Node Pool Operations — Common Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--nodepool_name` | Yes | Node pool name (note: no underscore) |

---

## 4. Network Resources (6 APIs)

### 4.1 ListNetworks — 查询网络列表

```bash
hcloud ModelArts ListNetworks --cli-region={region}
```

### 4.2 ShowNetwork — 查询网络详情

```bash
hcloud ModelArts ShowNetwork --cli-region={region} --network_name={network_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--network_name` | Yes | Network name |

### 4.3 CreateNetwork — 创建网络

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateNetwork --cli-region={region} \
  --metadata.name={network_name} \
  --spec.vpcId={vpc_id} \
  --spec.subnetId={subnet_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--metadata.name` | Yes | Network name |
| `--spec.vpcId` | Yes | VPC ID |
| `--spec.subnetId` | Yes | Subnet ID |

### 4.4 PatchNetwork — 更新网络

> **⚠️ CRITICAL**: PATCH operations require `--cli-jsonInput` with `Content-Type: application/merge-patch+json` header.
> See [known-issues.md](known-issues.md#1-patch-operations-content-type-patchpool-patchnetwork-patchnodepool) for details.

```bash
# ⚠️ Write operation — requires user confirmation
# Step 1: Create JSON input file with merge-patch+json Content-Type
cat > /tmp/patch_network.json << 'EOF'
{
  "header": {
    "Content-Type": "application/merge-patch+json"
  },
  "body": {
    "metadata": {
      "annotations": {
        "os.modelarts/description": "updated-network-description"
      }
    }
  }
}
EOF

# Step 2: Execute PATCH with --cli-jsonInput
hcloud ModelArts PatchNetwork --cli-region={region} --network_name={network_name} --cli-jsonInput=/tmp/patch_network.json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--network_name` | Yes | Network name |
| `--cli-jsonInput` | Yes | JSON file with header.Content-Type=application/merge-patch+json |

### 4.5 DeleteNetwork — 删除网络

```bash
# ⚠️ Write operation — requires user confirmation (irreversible)
hcloud ModelArts DeleteNetwork --cli-region={region} --network_name={network_name}
```

### 4.6 ShowNetworkAvailableIp — 查询网络可用IP数

> **⚠️ Note**: `--network_id` must use the value from `status.subnets[0].networkId` (obtained via ShowNetwork), NOT `spec.subnets[0].id` or `spec.subnets[0].name`.
> See [known-issues.md](known-issues.md#7-shownetworkavailableip-network-id-source) for details.

```bash
# Step 1: Get network details to find the correct network_id
hcloud ModelArts ShowNetwork --cli-region={region} --network_name={network_name}
# Extract: status.subnets[0].networkId

# Step 2: Query available IPs using the correct network_id
hcloud ModelArts ShowNetworkAvailableIp --cli-region={region} --network_name={network_name} --network_id={status.subnets[0].networkId}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--network_name` | Yes | Network name |
| `--network_id` | Yes | Subnet network ID from `ShowNetwork` response: `status.subnets[0].networkId` |

---

## 5. Tag Management (4 APIs)

### 5.1 ListPoolTags — 查询资源池标签列表

```bash
hcloud ModelArts ListPoolTags --cli-region={region}
```

### 5.2 ShowPoolTags — 查询资源池标签

```bash
hcloud ModelArts ShowPoolTags --cli-region={region} --pool_name={pool_name}
```

### 5.3 BatchCreatePoolTags — 批量创建标签

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchCreatePoolTags --cli-region={region} \
  --pool_name={pool_name} \
  --tags.1.key={key1} --tags.1.value={value1}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--tags.1.key` | Yes | Tag key (indexed) |
| `--tags.1.value` | Yes | Tag value (indexed) |

### 5.4 BatchDeletePoolTags — 批量删除标签

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts BatchDeletePoolTags --cli-region={region} \
  --pool_name={pool_name} \
  --tags.1.key={key1} --tags.1.value={value1}
```

---

## 6. Plugin Management (4 APIs)

### 6.1 ListPluginTemplates — 查询插件模板列表

```bash
hcloud ModelArts ListPluginTemplates --cli-region={region}
```

### 6.2 ShowPluginTemplate — 查询插件模板详情

```bash
hcloud ModelArts ShowPluginTemplate --cli-region={region} --plugintemplate_name={plugintemplate_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plugintemplate_name` | Yes | Plugin template name |

### 6.3 ListPoolPlugins — 查询资源池插件列表

```bash
hcloud ModelArts ListPoolPlugins --cli-region={region} --pool_name={pool_name}
```

### 6.4 CreatePoolPlugin — 创建资源池插件

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreatePoolPlugin --cli-region={region} \
  --pool_name={pool_name} \
  --plugintemplate_name={plugintemplate_name} \
  --metadata.name={plugin_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--pool_name` | Yes | Resource pool name |
| `--plugintemplate_name` | Yes | Plugin template name |
| `--metadata.name` | Yes | Plugin name |

---

## 7. Jobs & Workloads (3 APIs)

### 7.1 ListWorkloads — 查询工作负载列表

```bash
hcloud ModelArts ListWorkloads --cli-region={region} --pool_name={pool_name}
```

### 7.2 ShowWorkloadStatistics — 查询工作负载统计

```bash
hcloud ModelArts ShowWorkloadStatistics --cli-region={region} --pool_name={pool_name}
```

### 7.3 ListJobs — 查询作业列表

```bash
hcloud ModelArts ListJobs --cli-region={region} [--resource=pools] [--limit=10] [--offset=0]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--resource` | No | Resource type filter (e.g., `pools`) |
| `--limit` | No | Max results per page |
| `--offset` | No | Pagination offset |

---

## 8. Scheduled Events (2 APIs)

### 8.1 ListScheduledEvents — 查询定时事件列表

```bash
hcloud ModelArts ListScheduledEvents --cli-region={region} --poolName={pool_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--poolName` | Yes | Resource pool name (note: camelCase) |

### 8.2 AcceptScheduledEvent — 接受定时事件

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts AcceptScheduledEvent --cli-region={region} --event_id={event_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--event_id` | Yes | Event ID |

---

## 9. OS Configuration (2 APIs)

### 9.1 ShowOsConfig — 查询OS用户配置

```bash
hcloud ModelArts ShowOsConfig --cli-region={region}
```

### 9.2 ShowOsQuota — 查询OS配额

```bash
hcloud ModelArts ShowOsQuota --cli-region={region}
```

---

## 10. Resource Flavors & Events (4 APIs)

### 10.1 ListResourceFlavors — 查询资源规格列表

```bash
hcloud ModelArts ListResourceFlavors --cli-region={region}
```

> Each flavor contains `flavorId`, `billingCode`, `billingModes` (`[0]`=on-demand, `[1]`=period).

### 10.2 ListEvents — 查询事件列表

> **⚠️ Note**: The `--resource` parameter must use the **plural** form `pools`, not `pool`.
> See [known-issues.md](known-issues.md#6-listevents-resource-parameter-must-be-plural) for details.

```bash
# Correct — use plural form
hcloud ModelArts ListEvents --cli-region={region} --name={pool_name} --resource=pools

# Wrong — singular form will fail
# hcloud ModelArts ListEvents --cli-region={region} --name={pool_name} --resource=pool
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | Resource pool name |
| `--resource` | Yes | Resource type — must be `pools` (plural) |

### 10.3 ShowNodeConfigTemplate — 查询节点配置模板

```bash
hcloud ModelArts ShowNodeConfigTemplate --cli-region={region} --nodeconfigtemplate_name={template_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--nodeconfigtemplate_name` | Yes | Template name |

### 10.4 ShowPoolNodeConfigTemplate — 查询资源池节点配置模板

```bash
hcloud ModelArts ShowPoolNodeConfigTemplate --cli-region={region} --pool_name={pool_name}
```

---

## Parameter Reference

### Global Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--cli-region` | string | Yes | Region ID (e.g., `cn-north-4`, `cn-east-2`) |
| `--project_id` | string | No | Project ID. Auto-resolved from credentials if omitted. |

### Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--pool_name` | string | Conditional | Resource pool name (required for pool-specific operations) |
| `--nodepool_name` | string | Conditional | Node pool name (required for node pool operations) |
| `--network_name` | string | Conditional | Network name (required for network operations) |
| `--node_name` | string | Conditional | Node name (required for node-specific operations) |
| `--limit` | int | No | Maximum number of results (default: 10) |
| `--offset` | int | No | Pagination offset (default: 0) |

### Indexed Parameters

For batch operations and array-type parameters, use indexed syntax:

```bash
# Batch operations with multiple nodes
--node_name.1={node1} --node_name.2={node2} --node_name.3={node3}

# Tags array
--tags.1.key=env --tags.1.value=production
--tags.2.key=team --tags.2.value=ai-platform
```

### Parameter Naming Notes

> ⚠️ **Critical**: Several parameters use non-obvious names. Always use the names listed above.

| Expected | Actual | Reason |
|----------|--------|--------|
| `pool_id` | `pool_name` | API uses resource name, not ID |
| `node_pool_id` | `nodepool_name` | API uses resource name, no underscore |
| `pool_name` (ListScheduledEvents) | `poolName` | camelCase in this specific API |
| `resource_id` (ListEvents) | `name` + `resource` | Split into two parameters |

---

## Read/Write Operation Classification

### Read Operations (No Confirmation Required)

```
ListPools, ShowPool, ShowPoolMonitor, ShowPoolStatistics, ShowPoolRuntimeMetrics,
ShowPoolNodeConfig, ShowOrder, ListPoolNodes, ShowPoolNode, ListNodePools,
ShowNodePool, ListNodePoolNodes, ListNetworks, ShowNetwork, ShowNetworkAvailableIp,
ListPoolTags, ShowPoolTags, ListPluginTemplates, ShowPluginTemplate, ListPoolPlugins,
ListWorkloads, ShowWorkloadStatistics, ListJobs, ListScheduledEvents, ShowOsConfig,
ShowOsQuota, ListResourceFlavors, ListEvents, ShowNodeConfigTemplate, ShowPoolNodeConfigTemplate
```

### Write Operations (Confirmation Required)

```
CreatePool, PatchPool, DeletePool, CreateOrderId,
BatchDeletePoolNodes, BatchUpdatePoolNodes, BatchLockPoolNodes, BatchUnlockPoolNodes,
BatchRebootPoolNodes, BatchResetPoolNodes, BatchResizePoolNodes, BatchMigratePoolNodes, BatchBindPoolNodes,
CreateNodePool, PatchNodePool, DeleteNodePool,
CreateNetwork, PatchNetwork, DeleteNetwork,
BatchCreatePoolTags, BatchDeletePoolTags,
CreatePoolPlugin,
AcceptScheduledEvent
```
