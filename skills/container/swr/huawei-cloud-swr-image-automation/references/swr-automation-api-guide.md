# SWR Automation API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud SWR automation operations using hcloud CLI. All commands follow the standard format: `hcloud SWR <Operation> --param=value --cli-region=<region>`.

## Authentication

### Environment Variables

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
```

### hcloud CLI Configuration

```bash
# Interactive configuration
hcloud configure

# Verify configuration (safe - does not expose values)
hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEI_CLOUD_AK` to check credentials

## Sync Region Operations

### 1. List Available Sync Regions

```bash
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Source region ID

**Response Example** (verified against actual API — flat array):

```json
[
  {
    "regionID": "cn-north-4"
  }
]
```

**Key Fields**:
- `regionID` (not `region_id`): Region identifier (use as `--remoteRegionId` in sync operations)
- `region_name`: Human-readable region name
- Response is a **flat array** (not wrapped in an object)

**Note**: Returns all regions where cross-region sync is available. The source region is determined by `--cli-region`.

## Auto Sync Operations

### 1. Create Auto Sync Configuration

```bash
# Configure auto-sync (automatically sync on new push)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --override=false --cli-region=cn-north-4

# Configure manual-only sync (no auto-trigger)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=false --override=false --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): Source organization/namespace
- `--repository` (required, path): Source repository
- `--remoteRegionId` (required, body): Target region ID (must be from `ListSyncRegions`)
- `--remoteNamespace` (required, body): Target organization/namespace in target region
- `--override` (optional, body): Overwrite existing images in target (`true`/`false`, default `false`)
- `--syncAuto` (optional, body): Auto sync on new push (`true`/`false`, default `false`)
- `--cli-region` (required): Source region ID

**Auto Sync Behavior**:
- `syncAuto=true`: Every new image push to source repo automatically triggers sync to target
- `syncAuto=false`: Sync configuration exists but requires manual trigger via `CreateManualImageSyncRepo`

### 2. List Auto Sync Configurations

```bash
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): Source namespace
- `--repository` (required, path): Source repository
- `--cli-region` (required): Source region ID

**Response**: Returns list of sync repo configurations when they exist. Returns empty when no auto sync configured. Response format to be verified.

### 3. Delete Auto Sync Configuration

```bash
hcloud SWR DeleteImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): Source namespace
- `--repository` (required, path): Source repository
- `--remoteRegionId` (required): Target region ID
- `--remoteNamespace` (required): Target namespace
- `--cli-region` (required): Source region ID

⚠️ **Warning**: Deleting auto-sync configuration stops automatic replication. Existing synced images in the target region are NOT deleted.

## Manual Sync Operations

### 1. Create Manual Image Sync

```bash
# Sync specific tags to target region
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --imageTag.2=v2.0 --override=false --cli-region=cn-north-4

# Sync a single tag
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --cli-region=cn-north-4

# Sync with override (overwrite existing images)
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=latest --override=true --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): Source namespace
- `--repository` (required, path): Source repository
- `--remoteRegionId` (required, body): Target region ID
- `--remoteNamespace` (required, body): Target namespace in target region
- `--imageTag.[N]` (required, body): Tag list in indexed array format (`--imageTag.1=v1.0 --imageTag.2=v2.0`)
- `--override` (optional, body): Overwrite existing images (`true`/`false`, default `false`)
- `--cli-region` (required): Source region ID

**⚠️ Critical: `--imageTag` Array Format**:
- ✅ CORRECT: `--imageTag.1=v1.0 --imageTag.2=v2.0` (indexed, starts from 1)
- ❌ WRONG: `--imageTag=v1.0` (missing index number)
- ❌ WRONG: `--imageTag=v1.0,v2.0` (comma-separated not supported)
- ❌ WRONG: `--imageTag.0=v1.0` (index starts from 1, not 0)

**Manual Sync Behavior**: This is a one-time operation. It syncs the specified tags immediately and does not set up any ongoing replication.

## Sync Job Status Operations

### 1. Show Sync Job Status

```bash
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): Source namespace
- `--repository` (required, path): Source repository
- Other filtering parameters available (run `hcloud SWR ShowSyncJob --help` for details)
- `--cli-region` (required): Region ID

**Response**: Response format to be verified. Use `--help` for complete parameter list.

## Trigger Operations

### 1. Create Trigger

```bash
# Create trigger for auto-deploy to CCE (all pushes)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=deploy-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cluster_name=<cluster-name> --cli-region=cn-north-4

# Create trigger for specific tag pattern (semver)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=prod-trigger --trigger_type=regular --condition="v\d+\.\d+\.\d+" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# Create trigger for specific tag name
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=release-trigger --trigger_type=tag --condition=v2.0 --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# Create trigger for CCI (no cluster_id needed)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=cci-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-cci-app --cluster_ns=default --enable=true --trigger_mode=cci --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): SWR namespace
- `--repository` (required, path): Image repository
- `--name` (required, body): Trigger name (unique within repository)
- `--trigger_type` (required, body): Trigger type (`all`, `tag`, `regular`)
- `--condition` (required, body): Match condition (`.*` for all, tag name, regex pattern)
- `--action` (required, body): Action type (`update`)
- `--app_type` (required, body): Application type (`deployments` or `statefulsets`)
- `--application` (required, body): CCE/CCI application (deployment) name
- `--cluster_ns` (required, body): Application namespace (Kubernetes namespace)
- `--enable` (required, body): Enable state (`true` or `false`)
- `--trigger_mode` (optional, body): Deploy target (`cce` or `cci`, default `cce`)
- `--cluster_id` (optional): CCE cluster ID (required for `cce` mode, empty for `cci`)
- `--cluster_name` (optional): CCE cluster name
- `--container` (optional): Specific container to update (default: all containers)
- `--cli-region` (required): Region ID

**Trigger Type Details**:
- `all`: Matches any image push. Condition must be `.*`
- `tag`: Matches exact tag name. Condition is the specific tag (e.g., `v2.0`)
- `regular`: Matches regex pattern. Condition is a regex (e.g., `v\d+\.\d+`)

**Trigger Mode Details**:
- `cce`: Updates a workload in a CCE (Cloud Container Engine) cluster. Requires `cluster_id`
- `cci`: Updates a workload in CCI (Cloud Container Instance). No cluster ID needed

### 2. List Triggers

```bash
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): SWR namespace
- `--repository` (required, path): Image repository
- `--cli-region` (required): Region ID

**Response**: Returns list of trigger objects when they exist. Returns empty when no triggers configured. Response format to be verified.

### 3. Show Trigger Details

```bash
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): SWR namespace
- `--repository` (required, path): Image repository
- `--trigger` (required, path): Trigger name
- `--cli-region` (required): Region ID

**Response**: Response format to be verified.

### 4. Update Trigger

```bash
# Disable a trigger
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=false --cli-region=cn-north-4

# Enable a trigger
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=true --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): SWR namespace
- `--repository` (required, path): Image repository
- `--trigger` (required, path): Trigger name
- `--enable` (optional, body): Enable state (`true`/`false`)
- `--cli-region` (required): Region ID

**Note**: Run `hcloud SWR UpdateTrigger --help` for complete updateable parameters.

### 5. Delete Trigger

```bash
hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required, path): SWR namespace
- `--repository` (required, path): Image repository
- `--trigger` (required, path): Trigger name
- `--cli-region` (required): Region ID

⚠️ **Warning**: Deleting a trigger permanently removes the auto-deploy configuration.

## Common Region IDs

| Region Name                    | Region ID        |
| ------------------------------ | ---------------- |
| North China - Beijing 4        | `cn-north-4`     |
| North China - Beijing 1        | `cn-north-1`     |
| East China - Shanghai 1        | `cn-east-3`      |
| East China - Shanghai 2        | `cn-east-2`      |
| South China - Guangzhou        | `cn-south-1`     |
| South China - Shenzhen         | `cn-south-4`     |
| Southwest China - Guiyang 1    | `cn-southwest-2` |
| Asia Pacific - Bangkok         | `ap-southeast-2` |
| Asia Pacific - Singapore       | `ap-southeast-1` |
| Asia Pacific - Hong Kong       | `ap-southeast-3` |
| Europe - Paris                 | `eu-west-0`      |

## Common Errors

| Error                   | Cause                       | Solution                                        |
| ----------------------- | --------------------------- | ------------------------------------------------ |
| `InvalidAccessKeyId`    | Invalid AK/SK               | Check credential configuration via `hcloud configure list` |
| `NamespaceNotFound`     | Namespace does not exist    | Verify namespace name in source and target regions |
| `RepoNotFound`          | Repository does not exist   | Verify repository exists with `ShowRepository`   |
| `InvalidRemoteRegion`   | Invalid target region       | Check available regions with `ListSyncRegions`   |
| `TriggerAlreadyExists`  | Trigger name conflict       | Check with `ShowTrigger` first                   |
| `ClusterNotFound`       | CCE cluster not found       | Verify cluster_id with CCE console               |
| `QuotaExceeded`         | Resource quota limit        | Check quotas, clean up or apply                  |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                  |

## Related Documentation

- [Huawei Cloud SWR Documentation](https://support.huaweicloud.com/swr/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)