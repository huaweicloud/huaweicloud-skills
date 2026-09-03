# Known Issues and Workarounds

> Documented issues encountered during **real API testing** of all 53 resource pool operations.
> Every issue below was discovered through hands-on testing and verified with a workaround.
> **Read this file BEFORE executing any write operation** to avoid repeating known mistakes.

---

## ⚠️ Critical Issues (Will Cause Immediate Failure)

### 1. PATCH Operations Content-Type (PatchPool, PatchNetwork, PatchNodePool)

**Issue**: PATCH operations fail with `ModelArts.50004100 Content type not supported` when using standard CLI parameters or plain `--cli-jsonInput` without the correct Content-Type header.

**Root Cause**: The ModelArts PATCH API requires `Content-Type: application/merge-patch+json`, but hcloud CLI defaults to `application/json` for PATCH requests.

**Workaround**: Use `--cli-jsonInput` with a JSON file that includes the `header` section:

```json
// /tmp/patch_pool.json
{
  "header": {
    "Content-Type": "application/merge-patch+json"
  },
  "body": {
    "metadata": {
      "annotations": {
        "os.modelarts/description": "new-description"
      }
    }
  }
}
```

```bash
hcloud ModelArts PatchPool --cli-region={region} --pool_name={pool_name} --cli-jsonInput=/tmp/patch_pool.json
```

**Affected APIs**: PatchPool, PatchNetwork, PatchNodePool — ALL PATCH operations.

### 2. CreatePool Parameter Names

**Issue**: SKILL.md and some docs use simplified parameter names that differ from the actual hcloud CLI parameters.

**Workaround**: Use the actual CLI parameter names:

| Simplified | Actual CLI Parameter | Notes |
|------------|---------------------|-------|
| `--metadata.name` | `--metadata.labels.os.modelarts/name` | Pool name is under labels |
| `--spec.networkId` | `--spec.network.name` | Value is network's metadata.name |
| (none) | `--apiVersion=v2` | Fixed parameter, always required |
| (none) | `--kind=Pool` | Fixed parameter, always required |

### 3. Pool Type Spelling

**Issue**: Using `Dedicated` (with trailing d) as the pool type value causes an error.

**Workaround**: Use `Dedicate` (no trailing d):
```bash
# Correct
--spec.type=Dedicate

# Wrong (will fail)
--spec.type=Dedicated
```

### 4. CreatePool Network Name Format

**Issue**: The `--spec.network.name` value must be the network's full `metadata.name` (includes project ID suffix), not a user-friendly short name.

**Workaround**: Query `ListNetworks` first and use the exact `metadata.name` value:
```bash
# Correct (full name with project ID suffix)
--spec.network.name=pool-network-16u64g-92a3f81a953d4116b79ed3d2e2b8fc70

# Wrong (short name)
--spec.network.name=pool-network-16u64g
```

### 5. BatchUpdatePoolNodes Action Parameter Bug

**Issue**: The `--action` parameter help text says `[true|false]` but the actual valid values are string constants. Using `true` or `false` will fail.

**Workaround**: Use `--cli-jsonInput` with the correct action value in the JSON body:

| Action | Purpose |
|--------|---------|
| `openHaRedundant` | Enable HA redundancy |
| `closeHaRedundant` | Disable HA redundancy |
| `createTags` | Create node tags |
| `deleteTags` | Delete node tags |

```json
// /tmp/batch_update.json
{
  "body": {
    "nodeNames": ["node-name"],
    "action": "createTags",
    "tags": [{"key": "env", "value": "test"}]
  }
}
```

### 6. ListEvents Resource Parameter Must Be Plural

**Issue**: The `--resource` parameter for `ListEvents` must use the plural form `pools`, not `pool`.

**Workaround**:
```bash
# Correct
hcloud ModelArts ListEvents --cli-region={region} --name={pool_name} --resource=pools

# Wrong (will fail)
hcloud ModelArts ListEvents --cli-region={region} --name={pool_name} --resource=pool
```

### 7. ShowNetworkAvailableIp Network ID Source

**Issue**: The `--network_id` parameter must use the value from `status.subnets[0].networkId`, NOT from `spec.subnets[0].id` or `spec.subnets[0].name`.

**Workaround**: Query `ShowNetwork` first and extract the correct field:
```bash
# Step 1: Get network details
hcloud ModelArts ShowNetwork --cli-region={region} --network_name={network_name}
# Look for: status.subnets[0].networkId

# Step 2: Use that value
hcloud ModelArts ShowNetworkAvailableIp --cli-region={region} \
  --network_name={network_name} \
  --network_id={status.subnets[0].networkId}
```

---

## CLI Parameter Issues

### 8. ListScheduledEvents Parameter Case

**Issue**: `ListScheduledEvents` uses camelCase `--poolName` instead of the standard `--pool_name`.

**Workaround**: Use camelCase for this specific API:
```bash
hcloud ModelArts ListScheduledEvents --cli-region={region} --poolName={pool_name}
```

### 9. Parameter Name vs ID

**Issue**: Several operations use resource names where IDs might be expected.

**Workaround**: Always use resource names, not IDs:

| Expected | Actual | Used By |
|----------|--------|---------|
| `--pool_id` | `--pool_name` | All pool-specific operations |
| `--node_pool_id` | `--nodepool_name` | Node pool operations |
| `--network_id` (ShowNetwork) | `--network_name` | Network operations |
| `--resource_id` (ListEvents) | `--name` + `--resource` | ListEvents operation |

### 10. Indexed Parameters for Batch Operations

**Issue**: Batch node operations require indexed parameter syntax.

**Workaround**: Use dot notation with indices:
```bash
hcloud ModelArts BatchDeletePoolNodes --cli-region={region} \
  --pool_name={pool_name} \
  --node_name.1={node1} --node_name.2={node2}
```

> **Note**: Some batch operations use `--nodeNames.[N]` (capital N, with dot) instead of `--node_name.[N]`. Check the CLI help for each specific operation.

---

## API Behavior Issues

### 11. CreatePool Missing Network

**Issue**: Creating a `Dedicate` type pool without specifying `--spec.network.name` fails with `spec.network is required`.

**Workaround**: Query `ListNetworks` first and select a network. If no networks exist, create one with `CreateNetwork` before creating the pool.

### 12. Flavor Sold Out

**Issue**: Selected resource flavor may be sold out in all availability zones.

**Workaround**: Query `ListResourceFlavors` and filter out flavors with soldout status before presenting options to the user.

### 13. Package-Period Missing Parameters

**Issue**: Setting `billing.mode=1` (package-period) without `period.num` and `period.type` causes an error.

**Workaround**: When billing mode is 1, always include:
```bash
--metadata.annotations.os.modelarts/period.num=1 \
--metadata.annotations.os.modelarts/period.type=month \
--metadata.annotations.os.modelarts/auto.pay=true \
--metadata.annotations.os.modelarts/auto.renew=0
```

### 14. Network Deletion Blocked

**Issue**: Deleting a network that is in use by a resource pool fails with `ModelArts.50025002`.

**Workaround**: Delete the resource pool first, then delete the network. Use `ListPools` to check which pools use the network.

### 15. Batch Node Operation Latency

**Issue**: Batch node operations (reboot, reset, resize, migrate) may take several minutes to complete.

**Workaround**: Poll node status with `ShowPoolNode` until the operation completes. Do not assume immediate completion.

### 16. Scheduled Event Time Window

**Issue**: Some scheduled events require manual acceptance within a specific time window.

**Workaround**: Use `ListScheduledEvents` to monitor pending events. Accept events promptly with `AcceptScheduledEvent` before the window expires.

### 17. Tag Limit

**Issue**: Each resource pool supports a maximum of 20 tags.

**Workaround**: Check existing tags with `ShowPoolTags` before creating new ones. Delete unused tags if the limit is reached.

---

## CreateNodePool Constraints

### 18. CreateNodePool Count and MaxCount Rules

**Issue**: CreateNodePool has strict constraints on `count` and `maxCount` values.

**Rules** (all must be satisfied):
- `count` must be ≥ 1 (count=0 is rejected with "count must greater than 1")
- `maxCount` must be ≤ `count` (maxCount > count is rejected with "pool does not support maxCount more than count now")
- When `count=0`, billing annotations must be omitted (rejected with "billing annotation must be empty while there is no resources addition")

**Workaround**: Always set `count=1` (minimum) and `maxCount=count` for testing:
```bash
hcloud ModelArts CreateNodePool --cli-region={region} \
  --pool_name={pool_name} \
  --metadata.name={nodepool_name} \
  --spec.resources.flavor={flavor} \
  --spec.resources.count=1 \
  --spec.resources.maxCount=1 \
  --spec.resources.nodePool={nodepool_name} \
  --spec.resources.os.name="Huawei Cloud EulerOS 2.0" \
  --metadata.annotations.os.modelarts/billing.mode=0
```

---

## Batch Node Operation Limitations

### 19. BatchResetPoolNodes Strategy Not Supported

**Issue**: The `rollingConfig.strategy` parameter rejects ALL known values with "Strategy X is not support". Tested: Rolling, AllAtOnce, Parallel, InPlace, Rebuild, Reset, Recreate, Batch, Surge, and more.

**Status**: API endpoint is reachable and returns proper error responses, but no valid strategy value exists in the current environment. This may be a feature not yet enabled for regular VM pools.

**Workaround**: None currently. Document for future reference. If node reset is needed, consider deleting and recreating the node via BatchDeletePoolNodes + CreateNodePool.

### 20. BatchResizePoolNodes Only Supports Hyperinstance

**Issue**: BatchResizePoolNodes returns "only support hyperinstance scale currently" for regular VM nodes.

**Status**: API endpoint is reachable but only supports hyperinstance (bare metal) node scaling, not regular VM nodes.

**Workaround**: For VM nodes, delete and recreate with the new flavor via BatchDeletePoolNodes + CreateNodePool.

### 21. BatchMigratePoolNodes Cluster Name Constraint

**Issue**: `fromClusterName` cannot equal `toClusterName`. Migration requires two different pools/clusters.

**Workaround**: Ensure target pool exists and uses a different cluster name. Query `ShowPool` to find the cluster name in `status.clusters[0].name`.

### 22. BatchBindPoolNodes Already Bound

**Issue**: Returns "the quota of node X does not change" when the node is already bound to the pool.

**Status**: This is expected behavior for nodes already in the pool. The API is working correctly.

**Workaround**: No action needed — the node is already bound. Only use BatchBindPoolNodes for external nodes not yet in the pool.

---

## Data Field Locations

### 23. Node Tags Storage Location

**Issue**: Node tags are stored in `metadata.annotations["os.modelarts/tms.tags"]` as a JSON string, NOT in `metadata.labels`.

**Workaround**: When reading node tags, parse the JSON string from annotations:
```python
import json
tags_str = node["metadata"]["annotations"]["os.modelarts/tms.tags"]
tags = json.loads(tags_str)  # [{"key": "env", "value": "test"}]
```

### 24. Node Lock Status Location

**Issue**: Node lock status is stored in `metadata.annotations["os.modelarts.node/lock.action"]`, NOT in `status.phase` or `metadata.labels`.

**Workaround**: Check the annotation to determine lock status:
```python
lock_action = node["metadata"]["annotations"].get("os.modelarts.node/lock.action", "")
is_locked = bool(lock_action)  # Non-empty means locked
```

---

## Common Errors

| Error Code | Error Message | Cause | Solution |
|------------|--------------|-------|----------|
| `ModelArts.50004100` | Content type not supported | PATCH without `application/merge-patch+json` | Use `--cli-jsonInput` with header (see Issue #1) |
| `ModelArts.50004000` | Invalid request | Wrong parameter name or format | Check [cli-command-examples.md](cli-command-examples.md) |
| `ModelArts.50015001` | Resource pool not found | Pool name doesn't exist | Verify with `ListPools` first |
| `ModelArts.50025002` | Network in use by pool | Deleting network used by a pool | Delete pool first, then network |
| `Record not found` | Pool/node/network name doesn't exist | Name doesn't exist | Verify the name with List operations first |
| `Unauthorized` | AK/SK not configured or expired | Missing credentials | Run `hcloud configure` to re-authenticate |
| `Quota exceeded` | Resource quota limit reached | Quota limit | Use `ShowOsQuota` to check quota |
| `Region not supported` | ModelArts not enabled in region | Wrong region | Switch to a supported region (e.g., cn-north-4) |

---

## Error Handling Workflow

1. **Parse error message** from CLI output — extract `error_code` and `error_msg`
2. **Look up error code** in the Common Errors table above
3. **Check known issues** — scan this file for the specific API that failed
4. **Apply workaround** — follow the documented workaround step by step
5. **If unknown error**: show the raw error and suggest checking [Huawei Cloud documentation](https://support.huaweicloud.com/modelarts/)

---

## Pre-Flight Checklist (Before Write Operations)

> **MANDATORY**: Before executing ANY write operation, verify the following:

- [ ] **Read this file** — Scan relevant sections for the target API
- [ ] **PATCH operations** — Prepare `--cli-jsonInput` file with `Content-Type: application/merge-patch+json` header
- [ ] **CreatePool** — Verify network name format (full name with project ID suffix)
- [ ] **CreateNodePool** — Verify count ≥ 1 and maxCount ≤ count
- [ ] **BatchUpdatePoolNodes** — Use `--cli-jsonInput` with correct action string (not true/false)
- [ ] **DeleteNetwork** — Verify no pools are using the network
- [ ] **BatchResetPoolNodes** — Known limitation: strategy not supported for VM pools
- [ ] **BatchResizePoolNodes** — Known limitation: only supports hyperinstance nodes
- [ ] **BatchMigratePoolNodes** — Verify source ≠ target cluster and target pool exists

---

## Limitations

1. **Region availability**: ModelArts resource pools are available only in specific regions. Check Huawei Cloud console for current availability.
2. **Resource quota**: Each project has quotas for resource pools, nodes, and networks. Use `ShowOsQuota` to check current quota usage.
3. **Node operations**: Batch node operations may take several minutes. Poll status with `ShowPoolNode`.
4. **Network dependencies**: Deleting a network in use by a pool will fail. Delete the pool first.
5. **Tag limits**: Maximum 20 tags per resource pool.
6. **Scheduled events**: Some events require manual acceptance within a time window.
7. **PATCH Content-Type**: All PATCH operations require `application/merge-patch+json` via `--cli-jsonInput`.
8. **BatchResetPoolNodes**: `rollingConfig.strategy` has no valid value for VM pools (feature may not be enabled).
9. **BatchResizePoolNodes**: Only supports hyperinstance scaling, not regular VM nodes.
10. **CreateNodePool**: count must be ≥ 1; maxCount must be ≤ count; billing annotation required when count > 0.
