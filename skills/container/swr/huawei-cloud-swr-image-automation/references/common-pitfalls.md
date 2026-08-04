# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud SWR Image Automation skill.

## Pitfall 1: `--imageTag` Array Format Wrong

**Symptom**: `CreateManualImageSyncRepo` fails with parameter validation error

**Root Cause**: The `--imageTag` parameter uses indexed array format, NOT plain value or comma-separated

**Common Mistakes**:
- ❌ `--imageTag=v1.0` — missing index number
- ❌ `--imageTag=v1.0,v2.0` — comma-separated not supported
- ❌ `--imageTag.0=v1.0` — index starts from 1, not 0
- ❌ `--imageTag.1=v1` `--imageTag1=v2` — inconsistent format

**Solution**: Always use indexed array format starting from 1:

```bash
# ✅ CORRECT - Single tag
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --cli-region=cn-north-4

# ✅ CORRECT - Multiple tags
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --imageTag.2=v2.0 --cli-region=cn-north-4
```

## Pitfall 2: Target Namespace Does Not Exist in Target Region

**Symptom**: `CreateImageSyncRepo` or `CreateManualImageSyncRepo` fails with namespace not found

**Root Cause**: The target namespace must exist in the target region before creating sync configurations

**Solution**: Create the namespace in the target region first:

```bash
# Create namespace in target region (using target region's cli-region)
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-east-3

# Then create sync configuration (using source region's cli-region)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --cli-region=cn-north-4
```

## Pitfall 3: Invalid remoteRegionId

**Symptom**: Sync creation fails with invalid region ID

**Root Cause**: The `--remoteRegionId` value must be a valid region returned by `ListSyncRegions`

**Solution**: Always verify the target region ID before creating sync:

```bash
# List available sync regions
hcloud SWR ListSyncRegions --cli-region=cn-north-4

# Use a valid region_id from the result as remoteRegionId
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

## Pitfall 4: Auto-sync Replicates Unexpectedly

**Symptom**: Every image push triggers sync, causing unexpected images in target region

**Root Cause**: Auto-sync with `syncAuto=true` triggers on every push, including development/beta images

**Solution**:
- Use `syncAuto=false` for repos where you want manual control of what gets synced
- Alternatively, create a separate "release" repository with auto-sync, and only push production-ready images to it
- Delete auto-sync config if no longer needed:

```bash
# Delete unwanted auto-sync
hcloud SWR DeleteImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

## Pitfall 5: override=true Overwrites Production Images

**Symptom**: Production images in target region are accidentally overwritten by older/different versions

**Root Cause**: Setting `override=true` causes existing images in the target region to be replaced

**Solution**:
- Default to `override=false` for safety
- Only use `override=true` when you intentionally want to update images (e.g., patch releases)
- Before using `override=true`, verify what images exist in the target region:

```bash
# Check existing images in target region (use target region's cli-region)
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=my-app --cli-region=cn-east-3
```

## Pitfall 6: CCE Cluster ID Required But Not Provided

**Symptom**: `CreateTrigger` fails for CCE mode when `--cluster_id` is missing

**Root Cause**: CCE trigger mode requires `--cluster_id`; without it, the trigger cannot locate the target cluster

**Solution**:
- For CCE mode: always provide `--cluster_id` (obtain from CCE console)
- For CCI mode: omit `--cluster_id` (CCI doesn't use cluster IDs)

```bash
# ✅ CORRECT - CCE mode with cluster_id
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=cce-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# ✅ CORRECT - CCI mode (no cluster_id)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=cci-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-cci-app --cluster_ns=default --enable=true --trigger_mode=cci --cli-region=cn-north-4
```

## Pitfall 7: Trigger Name Already Exists

**Symptom**: `CreateTrigger` returns 409 Conflict

**Root Cause**: Trigger names must be unique within a repository

**Solution**: Check existing triggers before creating:

```bash
# Check existing triggers
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# Or check a specific trigger name
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

## Pitfall 8: Trigger Condition Format Errors

**Symptom**: Trigger doesn fire as expected or fails creation

**Root Cause**: Wrong `--condition` format for the chosen `--trigger_type`

**Condition Rules**:
- `trigger_type=all`: condition must be `.*`
- `trigger_type=tag`: condition is exact tag name (e.g., `v2.0`)
- `trigger_type=regular`: condition is regex pattern (e.g., `v\d+\.\d+`)

**Common Mistakes**:
- ❌ `trigger_type=all` with `condition=v1.0` — should use `.*`
- ❌ `trigger_type=regular` with `condition=v1.0` — should use regex pattern
- ❌ `trigger_type=tag` with `condition=.*` — should use exact tag name

**Solution**: Match condition format to trigger type:

```bash
# All pushes
hcloud SWR CreateTrigger --trigger_type=all --condition=".*" ...

# Specific tag
hcloud SWR CreateTrigger --trigger_type=tag --condition=v2.0 ...

# Regex pattern (semver)
hcloud SWR CreateTrigger --trigger_type=regular --condition="v\d+\.\d+" ...
```

## Pitfall 9: Sync Job Status Check Missing Parameters

**Symptom**: `ShowSyncJob` returns unexpected results or errors

**Root Cause**: Missing required path parameters

**Solution**: Always provide namespace and repository:

```bash
# ✅ CORRECT
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# ❌ WRONG - missing namespace
hcloud SWR ShowSyncJob --repository=my-app --cli-region=cn-north-4
```

## Pitfall 10: Deleting Sync Configuration Does Not Delete Synced Images

**Symptom**: Images remain in target region after deleting sync configuration

**Root Cause**: `DeleteImageSyncRepo` only removes the sync configuration, not the already-synced images

**Solution**: If you need to remove synced images, delete them separately in the target region:

```bash
# Delete tags in target region (use target region's cli-region)
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=my-app --tag=v1.0 --cli-region=cn-east-3
```

## Pitfall 11: CCI Not Authorized — Misleading "Server internal error"

**Symptom**: `CreateTrigger` with `trigger_mode=cci` returns `SVCSTG.SWR.5004002 "Server internal error: fail to get k8s deployment"`

**Root Cause**: CCI service has not been authorized. The SWR API wraps the CCI authorization error as a generic "Server internal error", which does not mention CCI authorization at all.

**Solution**: Before creating a CCI trigger, verify CCI is authorized:

```bash
# Check CCI authorization
hcloud CCI ListNamespaces --cli-region=cn-north-4
# If you get 403 or "user has no agency to cci":
#   CCI is not authorized. Authorize at:
#   https://console.huaweicloud.com/cci/?region=cn-north-4
#   (Service Authorization -> agree)
```

Do NOT mistake this error for a deployment issue. The real problem is CCI authorization, not a missing deployment.

## Pitfall 12: CreateTrigger "Invalid param" — Multiple Possible Causes

**Symptom**: `CreateTrigger` returns `SVCSTG.SWR.4000014 "Invalid param"` with empty detail

**Root Cause**: The API returns the same generic error for multiple distinct failure scenarios:
- Trigger name already exists (duplicate)
- CCE cluster_id does not exist
- Application/deployment name is wrong
- Namespace is incorrect

**Solution**: Run pre-creation checks to identify the specific cause:

```bash
# 1. Check if trigger name already exists
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# 2. Check if CCE cluster exists (for trigger_mode=cce)
hcloud CCE ShowCluster --cluster_id={cluster_id} --cli-region=cn-north-4

# 3. Verify application/deployment exists in the cluster
#    (via CCE/CCI console or API)
```

If the trigger name already exists, choose a different name. If the cluster doesn't exist, verify the cluster ID.

## Pitfall 13: API Returns Error but CLI Exit Code is 0

**Symptom**: `hcloud SWR` commands return error messages (e.g., `SVCSTG.SWR.4040126 "Not found trigger"`) but the shell exit code is 0, causing automation scripts to incorrectly assume success.

**Root Cause**: hcloud CLI (KooCLI 7.2.2) does not set a non-zero exit code when SWR API returns HTTP error status codes. This is a CLI-level limitation affecting all SWR operations.

**Affected Commands**: `DeleteTrigger`, `DeleteImageSyncRepo`, `ShowTrigger`, `CreateManualImageSyncRepo`, and other SWR operations.

**Solution**: In automation scripts, do NOT rely solely on exit code. Check the output content for `error_code` or `error_msg` fields:

```bash
result=$(hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=nonexistent --cli-region=cn-north-4 2>&1)
if echo "$result" | grep -q "error_code"; then
    echo "Operation failed: $result"
    # Error handling
else
    echo "Operation succeeded"
fi
```

## Pitfall 14: Sync to Non-existent Namespace Silently Succeeds

**Symptom**: `CreateImageSyncRepo` returns success (exit 0, empty response `{}`) even when the target namespace does not exist in the target region. The sync config is created but will never function.

**Root Cause**: The SWR API does not validate whether `remoteNamespace` exists in `remoteRegionId` at config creation time. The invalid config is silently stored.

**Solution**: Always verify the target namespace exists before creating a sync config:

```bash
# Verify target namespace exists in target region
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-east-3
# If 404: create the namespace first, then create the sync config
```

## Pitfall 15: Sync to Invalid Region Returns "Internal error"

**Symptom**: `CreateImageSyncRepo` with an invalid `--remoteRegionId` returns `SVCSTG.SWR.5001101 "Internal error"` with no indication that the region is the problem.

**Root Cause**: The API returns a generic internal error for invalid target regions, without specifying which parameter is wrong.

**Solution**: Always verify the target region before creating a sync config:

```bash
# List valid sync target regions
hcloud SWR ListSyncRegions --cli-region=cn-north-4
# Verify that --remoteRegionId appears in the returned list
```

## Pitfall 16: Manual Sync with Non-existent Tags Silently Succeeds

**Symptom**: `CreateManualImageSyncRepo` returns success even when the specified `--imageTag` values do not exist in the source repository. The sync job is created but will fail silently.

**Root Cause**: The API does not validate tag existence at request time for manual sync operations.

**Solution**: Always verify tags exist before triggering manual sync:

```bash
# List existing tags in the source repository
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=my-app --cli-region=cn-north-4
# Verify all --imageTag values appear in the returned tag list
```

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `SWR.001`           | 400         | Invalid parameter            | Check parameter format and rules      |
| `SWR.002`           | 404         | Resource not found           | Verify resource exists first          |
| `SWR.003`           | 409         | Resource already exists      | Use Show operation to check           |
| `SWR.004`           | 403         | Permission denied            | Check IAM policies                    |
| `SWR.005`           | 403         | Quota exceeded               | Check quotas, clean up or apply       |
| `SWR.006`           | 401         | Authentication failed        | Regenerate login credentials          |
| `SWR.007`           | 429         | Too many requests            | Add delay, reduce request rate        |