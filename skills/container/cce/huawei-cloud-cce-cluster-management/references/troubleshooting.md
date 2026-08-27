# Common Troubleshooting Issues

## Overview

Common issues and solutions for CCE cluster management operations executed via **hcloud (KooCLI)** and **kubectl cce**. hcloud failures are categorized by bracketed tags in stderr; kubectl cce failures surface as connection, validation, or RBAC errors.

## hcloud Error Categories

hcloud tags every failure with a bracketed category in stderr. The skill surfaces the full stderr line in the `error` field of tool responses.

| Tag | Meaning | Typical Cause |
|---------|---------|---------|
| `[NETWORK_ERROR]` | Cannot reach Huawei Cloud API | Network outage, DNS, proxy, wrong region endpoint |
| `[CLI_ERROR]` | hcloud CLI internal failure | hcloud not installed / wrong version, bad CLI args, missing `--cli-jsonInput` temp file |
| `[USE_ERROR]` | Parameter / usage error | Invalid param value, missing required flag, malformed JSON body |
| `[OPENAPI_ERROR]` | Huawei Cloud OpenAPI returned 4xx/5xx | Insufficient IAM permissions, resource not found, state conflict, quota exceeded |
| `[APIE_ERROR]` | API gateway / engine error | Throttling, gateway-side failure, transient — retry candidate |

## Quick Triage Table

| Error Type | Possible Cause | Solution |
|---------|---------|---------|
| `[OPENAPI_ERROR]` 403 Insufficient Permissions | Missing IAM permissions | Check IAM policy configuration |
| `[OPENAPI_ERROR]` 404 Resource Not Found | Incorrect cluster/node/nodepool/addon ID | Verify resource ID is correct |
| `[OPENAPI_ERROR]` 400 Parameter Error | Invalid parameter format | Check parameter format and values |
| `[OPENAPI_ERROR]` 409 State Conflict | Operation not allowed in current resource state | Wait for resource state change and retry |
| `[APIE_ERROR]` Throttled | API gateway rate limiting | Wait, then retry with backoff |
| `[NETWORK_ERROR]` | Cannot reach API | Check region, DNS, proxy, network |
| `[CLI_ERROR]` | hcloud misconfigured | Verify `hcloud version` ≥ 7.2; re-run installer |

## Common Issues

### 1. Cluster query returns empty list

**Possible Causes:**
- Incorrect region parameter
- Current account has no clusters

**Solutions:**
```bash
# Verify region is correct (hcloud connectivity test)
hcloud CCE ListClusters --cli-region=cn-north-4

# Check other regions
hcloud CCE ListClusters --cli-region=cn-east-3
```

### 2. Node operation returns insufficient permissions

**Possible Causes:**
- IAM lacks `cce:node:update` permission
- For kubectl cce ops, the AK/SK identity lacks RBAC on the cluster

**Solutions:**
- Add CCE-related permissions for the user in the IAM console.
- For kubectl cce operations, ensure the IAM user is a member of the cluster's `iam:group` (CCE console → Cluster → Permissions).

### 3. Cluster hibernate/awaken operation failed

**Possible Causes:**
- Cluster state does not support this operation
- Cluster is executing other tasks

**Solutions:**
```bash
# First query cluster status
hcloud CCE ListClusters --cli-region=cn-north-4
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
- `CCE_NODE_PASSWORD environment variable is not set` (only when no ssh_key / password / env var is supplied — the skill auto-generates a password in this case)
- `CCE_NODE_PASSWORD length must be 8-26 characters`
- `CCE_NODE_PASSWORD must contain at least 3 of: uppercase, lowercase, digits, special chars`

**Causes:**
- `CCE_NODE_PASSWORD` environment variable set but not meeting complexity (8–26 chars, ≥3 of: uppercase, lowercase, digits, special)
- Password not encrypted with SHA-512 salted + base64 encoding before being sent to the CCE API

**Node login resolution priority (see [SKILL.md](../SKILL.md) "Node Login Password Security"):**
1. `ssh_key` parameter (preferred)
2. `password` parameter
3. `CCE_NODE_PASSWORD` environment variable
4. **Auto-generated random password** (never returned in the response; reset via CCE console / ECS API to access the node)

**Solutions:**
```bash
# Option A: set a compliant password env var
export CCE_NODE_PASSWORD  # from $NODE_PASSWORD (8-26 chars, at least 3 char categories)
python3 huawei-cloud.py huawei_create_cce_nodepool ...

# Option B: pass an ssh_key (preferred when available)
python3 huawei-cloud.py huawei_create_cce_nodepool ... ssh_key=KeyPair-dev

# Option C: omit both — the skill auto-generates a strong password.
# The success message will instruct you to reset the node password to access it.
```

The skill automatically applies SHA-512 salted + base64 encoding; no manual processing is needed.

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

### 8. hcloud CreateCluster / CreateNodePool defect (SDK fallback)

**Error Message (when forced through hcloud):** metadata/spec parsing failure, or the API rejects the request with a missing-field error even though the body is populated.

**Cause:** `hcloud CCE CreateCluster` and `hcloud CCE CreateNodePool` have a known **metadata parsing defect** — nested `metadata`/`spec` fields are not parsed correctly by hcloud.

**Mitigation (already in place):** the skill's `huawei_create_cce_cluster` and `huawei_create_cce_nodepool` tools bypass hcloud and call the Python SDK directly (`huaweicloudsdkcce.v3`). No user action is needed. If you see this error, confirm you are calling the skill's tool and not invoking `hcloud CCE CreateCluster` manually. See [cce-api-guide.md](cce-api-guide.md#hcloud-defect-createcluster--createnodepool-sdk-fallback).

### 9. kubectl cce: "The connection to the server was refused" / connection errors

**Error Message:** `Unable to connect to the server: dial tcp ...: connect: connection refused` or `error: ... connection refused`.

**Possible Causes:**
- kubectl-cce plugin not installed or not in PATH
- Cluster API gateway endpoint not reachable (region mismatch)
- Credentials invalid (AK/SK/token)

**Solutions:**
```bash
# 1. Verify kubectl-cce plugin is installed
kubectl cce --help

# 2. Test connectivity manually
HW_ACCESS_KEY=<AK> HW_SECRET_KEY=<SK> HW_SECURITY_TOKEN=<token> \
  kubectl cce --cluster-id <id> --region <region> --project-id <pid> get nodes

# 3. Confirm region matches the cluster's region
# 4. Confirm HW_ACCESS_KEY / HW_SECRET_KEY (and HW_SECURITY_TOKEN for temp creds) are set
```

### 9a. kubectl cce: "failed to request discovery client" / OpenAPI validation error

**Error Message:** `failed to request discovery client to find mappings` or `the server could not find the requested resource`.

**Cause:** The CCE API Gateway `/api/` endpoint may return 404 on OpenAPI schema validation with certain kubectl versions.

**Solution:** Ensure the kubectl-cce plugin is up to date. The `kubectl_cce()` helper handles connection setup automatically.

### 10. kubectl drain blocked by PodDisruptionBudget

**Error Message:** `error: unable to drain node "xxx" due to error:PodDisruptionBudget ...`, or `cannot delete pods ... because PDB ... would be violated`.

**Cause:** `huawei_cce_node_drain` uses `kubectl cce drain` with `--ignore-daemonsets --delete-emptydir-data`, which **respects PodDisruptionBudget**. Pods governed by a PDB that forbids disruption will block the drain.

**Solutions:**
- Wait for the protected workload to drain naturally, or scale it down / delete the PDB intentionally.
- Do **not** add `--force` bypass logic — the skill intentionally preserves PDB safety. If the user explicitly requests a forced drain, run `kubectl cce ... drain <node> --force --ignore-daemonsets --delete-emptydir-data` manually with appropriate review.

### 11. API gateway rate limiting (`[APIE_ERROR]`)

**Error Message:** `[APIE_ERROR]` throttling / 429 / "Request too frequent".

**Cause:** API gateway throttled the hcloud call.

**Solutions:**
- Wait a few seconds and retry.
- For batch node-pool operations, space calls by a few seconds.

### 12. hcloud not installed / wrong version (`[CLI_ERROR]`)

**Error Message:** `'hcloud' is not recognized` / `[CLI_ERROR]` / `unknown command`.

**Solutions:**
```bash
# Verify install and version (must be 7.2+)
hcloud version

# Install / upgrade
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh
```

### 13. Node drain timeout (`drain ... timeout`)

**Error Message:** `error: timed out waiting for the condition` / drain command exits with timeout after 120s.

**Cause:** `huawei_cce_node_drain` uses `--timeout=120s`. On nodes with many pods or large workloads, eviction can take longer than 120 seconds. This is a CCE platform behavior, not a skill bug.

**Solutions:**
- The cordon portion of drain still succeeds even if eviction times out — the node is marked unschedulable.
- Retry the drain after workloads have been scaled down or migrated.
- For maintenance windows, cordon the node first (`huawei_cce_node_cordon`), then manually drain with a longer timeout via `kubectl cce ... drain <node> --timeout=300s`.

### 14. Addon uninstall fails when addon is upgrading

**Error Message:** `CCE.0500` or similar error when calling `huawei_uninstall_cce_addon`.

**Cause:** The addon is in `upgrading` state (check via `huawei_list_cce_addons` → `status.status`). CCE does not allow deleting an addon that is currently being upgraded.

**Solutions:**
- Wait for the upgrade to complete (addon status returns to `running` or `abnormal`).
- Then retry `huawei_uninstall_cce_addon` with the addon **UID** (not name).

### 15. ShowAddonInstance returns "not found" when using addon name

**Error Message:** `Addon not found` or similar 404 error.

**Cause:** `huawei_get_cce_addon_detail` (`ShowAddonInstance`), `huawei_uninstall_cce_addon` (`DeleteAddonInstance`), and `huawei_update_cce_addon` (`UpdateAddonInstance`) all require the addon **UID**, not the addon name. Using a name returns error CCE.03400001.

**Solutions:**
- Call `huawei_list_cce_addons` first to get the addon list.
- Use the `metadata.uid` field (not `metadata.name`) as the `addon_id` parameter.

### 16. DeleteNode returns error when using node name instead of UID

**Error Message:** `Node not found` or similar 404/400 error (e.g., CCE.03400001).

**Cause:** `huawei_delete_cce_node` (`DeleteNode`) requires the node **UID**, not the node name.

**Solutions:**
- Call `huawei_list_cce_nodes` first to get the node list.
- Use the `metadata.uid` field (not `metadata.name`) as the `node_id` parameter.
