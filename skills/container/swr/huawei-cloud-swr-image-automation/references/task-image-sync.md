# Task: Image Sync

## Overview

SWR image sync enables cross-region image replication. You can configure auto-sync to automatically replicate images on every push, or manually sync specific tags. This task covers auto-sync configuration, manual sync, available sync regions, and sync job status.

## Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `ListSyncRegions`            | GET    | 查询可用同步区域         | `--cli-region`                                  |
| `CreateImageSyncRepo`        | POST   | 创建镜像自动同步         | `--namespace`, `--repository`, `--remoteRegionId`, `--remoteNamespace`, `--override`, `--syncAuto` |
| `ListImageAutoSyncReposDetails` | GET | 查询镜像自动同步列表 | `--namespace`, `--repository`                   |
| `DeleteImageSyncRepo`        | DELETE | 删除镜像自动同步         | `--namespace`, `--repository`, `--remoteRegionId`, `--remoteNamespace` |
| `CreateManualImageSyncRepo`  | POST   | 创建手动同步任务         | `--namespace`, `--repository`, `--remoteRegionId`, `--remoteNamespace`, `--imageTag.[N]`, `--override` |
| `ShowSyncJob`                | GET    | 查询同步任务状态         | `--namespace`, `--repository`                   |

## Workflows

### W1: Check Available Sync Regions

Before setting up any sync, verify which regions are available as targets:

```bash
# List all available sync target regions
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Output Fields** (verified against actual API — flat array):
- ``regionID``: Region identifier (use as `--remoteRegionId`)
- `region_name`: Human-readable region name
- Response is a **flat array** of region objects (not wrapped)

### W2: Configure Auto-sync for a Repository

Set up automatic image replication across regions:

**Pre-creation Checklist**:
1. Verify target region is available: `hcloud SWR ListSyncRegions --cli-region=cn-north-4`
2. Ensure target namespace exists in target region:
```bash
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-east-3
```
3. Verify source repository exists:
```bash
hcloud SWR ShowRepository --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

```bash
# Configure auto-sync (automatically sync on every new push)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --override=false --cli-region=cn-north-4

# Configure sync without auto-trigger (manual sync only)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=false --override=false --cli-region=cn-north-4
```

**Parameters**:
- `--syncAuto=true`: Every push triggers automatic sync to target region
- `--syncAuto=false`: Sync config exists but only triggers manually
- `--override=true`: Overwrite existing images in target region
- `--override=false`: Skip images that already exist in target

**Post-creation Verification**:

```bash
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

### W3: View Auto-sync Configurations

```bash
# List all auto-sync configurations for a repository
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Use Cases**:
- Verify which regions a repository is syncing to
- Check whether auto-sync is enabled or manual-only
- Audit cross-region replication setup

### W4: Manually Sync Specific Tags

Manually replicate specific image tags to a target region:

**Pre-sync Checklist**:
1. Verify source tags exist:
```bash
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```
2. Ensure target namespace exists:
```bash
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-east-3
```

```bash
# Sync a single tag
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --override=false --cli-region=cn-north-4

# Sync multiple tags
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --imageTag.2=v2.0 --override=false --cli-region=cn-north-4

# Sync with override (replace existing images)
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=latest --override=true --cli-region=cn-north-4
```

**⚠️ Critical**: `--imageTag` uses indexed array format:
- ✅ `--imageTag.1=v1.0 --imageTag.2=v2.0` (correct)
- ❌ `--imageTag=v1.0` (missing index)
- ❌ `--imageTag=v1.0,v2.0` (comma not supported)

**Note**: Manual sync is a one-time operation. It does not set up ongoing replication.

### W5: Check Sync Job Status

```bash
# Check status of sync jobs for a repository
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Use Cases**:
- Verify whether a sync completed successfully
- Check if a manual sync job is still running
- Troubleshoot failed sync operations

### W6: Delete Auto-sync Configuration

⚠️ **Note**: Deleting sync config stops automatic replication but does NOT delete already-synced images.

```bash
hcloud SWR DeleteImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should no longer show the sync config
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

## Common Scenarios

### S1: Multi-region DR Setup

Set up cross-region replication for disaster recovery:

```bash
# 1. Create target namespace in each DR region
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-east-3
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=ap-southeast-1

# 2. Configure auto-sync to each DR region
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --override=true --cli-region=cn-north-4
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=ap-southeast-1 --remoteNamespace=group-dev --syncAuto=true --override=true --cli-region=cn-north-4

# 3. Verify sync configurations
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

### S2: Selective Production Release Sync

Only sync production-ready tags to target regions:

```bash
# 1. Configure sync WITHOUT auto-trigger
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=false --override=false --cli-region=cn-north-4

# 2. Manually sync only production tags
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v2.1.0-stable --cli-region=cn-north-4

# 3. Verify sync status
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

### S3: Regional Namespace Alignment

Use identical namespace names across regions for easy management:

```bash
# Create matching namespaces in multiple regions
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-north-4
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-east-3
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=ap-southeast-1

# Set up sync with same namespace name
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --cli-region=cn-north-4
```