# Verification Method - SWR Image Automation Skill

## Overview

This document defines the verification steps for the SWR image automation skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 hcloud CLI Installation

| Item                 | Command           | Success Criteria                          |
| -------------------- | ------------------ | ----------------------------------------- |
| hcloud installed     | `hcloud version`   | Returns version number >= 7.2.2           |

### 1.2 hcloud CLI First Run

```bash
# Accept privacy statement (first time only)
printf "y\n" | hcloud version
```

Expected: Version number displayed without error.

## Level 2: Configuration Verification

### 2.1 Credential Configuration

| Item                    | Command                | Success Criteria                        |
| ----------------------- | ---------------------- | --------------------------------------- |
| Credentials configured  | `hcloud configure list` | Shows valid AK/SK configuration (values masked) |

✅ **Correct**: Use `hcloud configure list` to verify
❌ **Incorrect**: Do NOT use `echo $HUAWEI_CLOUD_AK` to check credentials

### 2.2 Connectivity Test

```bash
# Test API connectivity with a read-only operation
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and list of available sync regions.

## Level 3: Functional Verification

### 3.1 Sync Regions (Read-only)

```bash
# List available sync target regions
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

Expected: returns array of objects with `regionID` field with `region_id` and `region_name` fields.

### 3.2 Auto Sync Configuration

```bash
# List existing auto-sync configurations (read-only)
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

Expected: Returns list of sync configurations (may be empty if none configured).

```bash
# Create auto-sync configuration (requires existing repo and target namespace)
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --syncAuto=true --override=false --cli-region=cn-north-4
```

Expected: Auto-sync configuration created.

```bash
# Verify auto-sync creation
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

Expected: Shows the newly created sync configuration.

```bash
# Clean up: delete auto-sync configuration
hcloud SWR DeleteImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

Expected: Auto-sync configuration removed.

### 3.3 Manual Sync (Requires existing tags in repository)

```bash
# Manually sync specific tags (requires existing image tags)
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --override=false --cli-region=cn-north-4
```

Expected: Manual sync job initiated for the specified tags.

### 3.4 Sync Job Status

```bash
# Check sync job status
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

Expected: Returns sync job status information.

### 3.5 Trigger Management

```bash
# List existing triggers (read-only)
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

Expected: Returns list of triggers (may be empty if none configured).

```bash
# Create a trigger (requires CCE cluster)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=test-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=<deployment-name> --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4
```

Expected: Trigger created successfully.

```bash
# Show trigger details
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=test-trigger --cli-region=cn-north-4
```

Expected: Returns trigger details including configuration and status.

```bash
# Update trigger (disable)
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=test-trigger --enable=false --cli-region=cn-north-4
```

Expected: Trigger disabled.

```bash
# Clean up: delete trigger
hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=test-trigger --cli-region=cn-north-4
```

Expected: Trigger deleted.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud SWR ListSyncRegions --cli-region=cn-north-4` | ☐      |
| 4  | List sync regions         | `hcloud SWR ListSyncRegions --cli-region=cn-north-4` | ☐      |
| 5  | List auto-sync configs    | `hcloud SWR ListImageAutoSyncReposDetails --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 6  | Create auto-sync          | `hcloud SWR CreateImageSyncRepo --namespace=<ns> --repository=<repo> --remoteRegionId=<id> --remoteNamespace=<ns> --syncAuto=true --cli-region=cn-north-4` | ☐ |
| 7  | Delete auto-sync          | `hcloud SWR DeleteImageSyncRepo --namespace=<ns> --repository=<repo> --remoteRegionId=<id> --remoteNamespace=<ns> --cli-region=cn-north-4` | ☐ |
| 8  | Manual sync               | `hcloud SWR CreateManualImageSyncRepo --namespace=<ns> --repository=<repo> --remoteRegionId=<id> --remoteNamespace=<ns> --imageTag.1=<tag> --cli-region=cn-north-4` | ☐ |
| 9  | Check sync job status     | `hcloud SWR ShowSyncJob --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 10 | List triggers             | `hcloud SWR ListTriggersDetails --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 11 | Create trigger            | `hcloud SWR CreateTrigger --namespace=<ns> --repository=<repo> --name=<trigger> --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=<app> --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<id> --cli-region=cn-north-4` | ☐ |
| 12 | Show trigger              | `hcloud SWR ShowTrigger --namespace=<ns> --repository=<repo> --trigger=<trigger> --cli-region=cn-north-4` | ☐ |
| 13 | Update trigger            | `hcloud SWR UpdateTrigger --namespace=<ns> --repository=<repo> --trigger=<trigger> --enable=false --cli-region=cn-north-4` | ☐ |
| 14 | Delete trigger            | `hcloud SWR DeleteTrigger --namespace=<ns> --repository=<repo> --trigger=<trigger> --cli-region=cn-north-4` | ☐ |