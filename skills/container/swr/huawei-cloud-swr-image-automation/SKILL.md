---
id: huawei-cloud-swr-image-automation
name: huawei-cloud-swr-image-automation
description: |
  Huawei Cloud SWR (Software Repository for Container) image automation and operations skill using hcloud CLI.
  Use this skill when the user wants to: (1) configure cross-region image sync (auto or manual), (2) manage SWR triggers for auto-deploy to CCE/CCI, (3) query available sync target regions, (4) check sync job status, (5) create/update/delete trigger configurations.
  Trigger: user mentions "SWR automation", "SWR 自动化", "镜像同步", "SWR sync", "跨区域同步", "cross-region sync", "触发器", "SWR trigger", "自动部署", "auto deploy", "镜像复制", "image replication", "SWR 触发器"
tags:
  - swr
  - image-automation
  - image-sync
  - trigger
  - auto-deploy
---

# Huawei Cloud SWR Image Automation

## Overview

This skill provides image automation capabilities for Huawei Cloud SWR (Software Repository for Container) using the `hcloud` CLI, including cross-region image sync and trigger-based auto-deployment.

**Architecture**: hcloud CLI → SWR Service API → SyncRepo/Trigger/SyncJob/SyncRegion resources

**Related Skills**:
- `huawei-cloud-swr-image-management` - Image lifecycle management (namespaces, repos, tags, auth, quotas). **Image push and authentication (`CreateAuthorizationToken`, `docker login`, `docker push`) are required to verify triggers end-to-end.** If not installed, install it first:
  ```bash
  npx skills add huaweicloud/huaweicloud-skills --skill huawei-cloud-swr-image-management -y
  ```
  For the complete image push and authentication flow, refer to the official SWR Quick Start guide: https://support.huaweicloud.com/qs-swr/index.html
- `huawei-cloud-swr-image-governance` - Image governance (permissions, retention, sharing, tags, immutable rules)
- `huawei-cloud-swr-enterprise-instance` - Enterprise instance management

- Configure auto-sync to replicate images across regions on push
- Manually sync specific image tags to target regions
- List available sync target regions
- Check sync job execution status
- Create and manage triggers for auto-deploy to CCE/CCI workloads
- Enable/disable triggers and update trigger configurations

**Typical Use Cases**:

- "Set up auto-sync for my image repository to cn-east-3"
- "Manually sync image tags v1.0 and v2.0 to another region"
- "List available regions for image sync"
- "Check the status of my image sync job"
- "Create a trigger to auto-update my CCE deployment when a new image is pushed"
- "List all triggers for a repository"
- "Disable a trigger temporarily"
- "Delete an old trigger configuration"
- "Configure image replication across multiple regions"

### 参数确认

> **All write operations (Create, Update, Delete) require explicit user confirmation before execution.**

Before executing any write operation, the skill must:

1. Display the exact hcloud command to be executed
2. Show the target resource (namespace, repository, remote region, etc.)
3. Show the change to be applied (sync config, trigger settings, override status)
4. Wait for user confirmation ("yes" / "confirm") before proceeding
5. If user declines, abort the operation and return to step 1

**Write operations requiring confirmation**:

| Operation | Command | Risk Level | Description |
|-----------|---------|------------|-------------|
| Create auto-sync config | `CreateImageSyncRepo` | 🟠 High | Creates cross-region image replication. **If override=true, overwrites existing images in target region — existing images are unrecoverable. Warn user before proceeding** |
| Delete auto-sync config | `DeleteImageSyncRepo` | 🟡 Medium | Removes auto-sync configuration. **New pushes will no longer auto-replicate to target region. Already-synced images are preserved** |
| Manual sync tags | `CreateManualImageSyncRepo` | 🟡 Medium | One-time sync of specific tags. **If override=true, overwrites existing images in target region** |
| Create trigger | `CreateTrigger` | 🟡 Medium | Sets up auto-deploy to CCE/CCI. **New image pushes will automatically update the target workload — verify trigger condition to avoid unintended deployments** |
| Update trigger | `UpdateTrigger` | 🟡 Medium | Modifies trigger configuration. **Enabling/disabling changes auto-deploy behavior immediately** |
| Delete trigger | `DeleteTrigger` | 🟡 Medium | Removes auto-deploy trigger. **Target workload will no longer auto-update on new image pushes** |

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

hcloud CLI supports two credential modes via environment variables, automatically detected at runtime:

**Mode A — Long-term AK/SK** (permanent access):
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Mode B — Temporary AK/SK + SecurityToken** (recommended for temporary or delegated access):
```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

> When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication. When only AK/SK are set, it uses long-term credential authentication.

- **Security Rules**:
  - 🚫 Never expose AK/SK/SecurityToken values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, `HUAWEI_CLOUD_SECURITY_TOKEN`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| API Action                             | Permission           | Purpose                                    |
| -------------------------------------- | -------------------- | ------------------------------------------ |
| `swr:sync:create`                      | Create sync repo     | Configure cross-region image sync          |
| `swr:sync:delete`                      | Delete sync repo     | Remove sync configuration                  |
| `swr:sync:list`                        | List sync repos      | Query auto-sync configurations             |
| `swr:syncmanual:create`                | Manual sync          | Trigger manual image sync                  |
| `swr:syncregion:list`                  | List sync regions    | Query available sync target regions        |
| `swr:syncjob:get`                      | Get sync job status  | Check sync execution status                |
| `swr:trigger:create`                   | Create trigger       | Set up auto-deploy trigger                 |
| `swr:trigger:list`                     | List triggers        | Query trigger configurations               |
| `swr:trigger:get`                      | Get trigger          | View specific trigger details              |
| `swr:trigger:update`                   | Update trigger       | Modify trigger configuration               |
| `swr:trigger:delete`                   | Delete trigger       | Remove trigger configuration               |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## 工作流

1. **Confirm parameters** — Review the confirmation table above; confirm the risk level and key parameters with the user before any write operation
2. **Query sync regions** — `ListSyncRegions` to retrieve available cross-region sync targets
3. **Configure sync** — `CreateImageSyncRepo` (auto-sync) or `CreateManualImageSyncRepo` (one-time manual sync)
4. **Manage triggers** — `CreateTrigger` / `UpdateTrigger` / `DeleteTrigger` to configure auto-deploy to CCE/CCI
5. **Query status** — `ListImageAutoSyncReposDetails` / `ShowTrigger` / `ListSyncJobsDetails` to check sync and trigger status
6. **Cleanup** — `DeleteImageSyncRepo` to stop sync, `DeleteTrigger` to remove trigger

## KooCLI Command Format Standard

All commands follow the standard hcloud KooCLI format:

```bash
hcloud SWR <Operation> --param1=value1 --param2=value2 --cli-region=<region>
```

**Key conventions**:
- Service name: `SWR` (uppercase, matches KooCLI Services listing)
- Operation name: PascalCase (e.g., `CreateImageSyncRepo`, `ListSyncRegions`, `CreateTrigger`)
- Region parameter: `--cli-region=<value>` (default: `cn-north-4`, or `HUAWEI_CLOUD_REGION` env var)
- Output format: `--cli-output=json` (for agent processing)
- JMESPath filtering: `--cli-query="<expression>"` (to reduce output)
- Array-style parameters: `--imageTag.1=v1 --imageTag.2=v2` (index starts from 1, not 0)

**Example — read operation**:
```bash
hcloud SWR ListSyncRegions --cli-region=cn-north-4 --cli-output=json
```

**Example — write operation (requires user confirmation)**:
```bash
# Step 1: Display command and parameters for user confirmation
# Step 2: After user confirms, execute:
hcloud SWR CreateImageSyncRepo --namespace=pancake --repository=openclaw-sandbox \
  --remoteRegionId=cn-east-3 --remoteNamespace=pancake --syncAuto=true --override=false \
  --cli-region=cn-north-4
```


## Core Commands

### 1. Auto Sync (Cross-region Image Replication)

See [Task: Image Sync](references/task-image-sync.md) for detailed workflows.

```bash
# List available sync target regions
hcloud SWR ListSyncRegions --cli-region=cn-north-4

# Configure auto-sync for a repository to target region
hcloud SWR CreateImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --override=false --syncAuto=true --cli-region=cn-north-4

# List auto-sync configurations for a repository
hcloud SWR ListImageAutoSyncReposDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# Delete auto-sync configuration
hcloud SWR DeleteImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --cli-region=cn-north-4
```

**Auto Sync Behavior**: When `syncAuto=true`, every new image push to the source repository automatically triggers a sync to the target region. When `syncAuto=false`, sync only occurs on manual trigger.

### 2. Manual Sync

```bash
# Manually sync specific image tags to target region
hcloud SWR CreateManualImageSyncRepo --namespace=group-dev --repository=my-app --remoteRegionId=cn-east-3 --remoteNamespace=group-dev --imageTag.1=v1.0 --imageTag.2=v2.0 --override=false --cli-region=cn-north-4
```

**⚠️ Important**: `--imageTag` uses indexed array format, NOT plain value format:
- ✅ CORRECT: `--imageTag.1=v1.0 --imageTag.2=v2.0`
- ❌ WRONG: `--imageTag=v1.0` (missing index)
- ❌ WRONG: `--imageTag=v1.0,v2.0` (comma-separated not supported)

### 3. Sync Regions

```bash
# List all regions available as sync targets
hcloud SWR ListSyncRegions --cli-region=cn-north-4
```

**Response Format** (verified against actual API):

```json
[
  {
    "regionID": "cn-north-4"
  }
```

Returns all regions where you can sync images. Use the `regionID` field value as the `--remoteRegionId` parameter.

### 4. Sync Job Status

```bash
# Check sync job status (--filter is REQUIRED with limit and offset)
hcloud SWR ShowSyncJob --namespace=group-dev --repository=my-app --filter="limit::10|offset::0" --cli-region=cn-north-4
```

**⚠️ Important**: `--filter` is required and must include both `limit::N` and `offset::N` (e.g., `"limit::10|offset::0"`). Without it, the command returns a missing parameter error.

**Response format** (verified against actual API): Returns a flat JSON array. Returns `[]` when no sync jobs exist.

### 5. Trigger Management (Auto-deploy to CCE/CCI)

See [Task: Trigger Management](references/task-trigger-management.md) for detailed workflows.

```bash
# Create a trigger for auto-deploy to CCE
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=deploy-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cluster_name=<cluster-name> --cli-region=cn-north-4

# List all triggers for a repository
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# Show trigger details
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4

# Update a trigger (enable/disable or modify configuration)
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=false --cli-region=cn-north-4

# Delete a trigger
hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

**Trigger Types**:
- `all`: Trigger on any image push (`condition=".*"`)
- `tag`: Trigger on specific tag push (`condition=tag-name`)
- `regular`: Trigger on tag matching regex (`condition=regex-pattern`)

**Trigger Modes**:
- `cce`: Deploy to CCE (Cloud Container Engine) cluster — requires `--cluster_id`
- `cci`: Deploy to CCI (Cloud Container Instance) — no cluster ID needed

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--namespace`   | Context-dependent | SWR namespace (organization)  | N/A                                  |
| `--repository`  | Context-dependent | Image repository name         | N/A                                  |

### Auto Sync Parameters

| Parameter          | Required | Description              | Constraints                                  |
| ------------------ | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`      | Yes      | Source namespace          | Existing namespace name                      |
| `--repository`     | Yes      | Source repository         | Existing repository name                     |
| `--remoteRegionId` | Yes      | Target region ID          | Must be from `ListSyncRegions` result        |
| `--remoteNamespace`| Yes      | Target namespace          | Namespace name in target region              |
| `--override`       | No       | Overwrite existing images | `true` or `false` (default `false`)          |
| `--syncAuto`       | No       | Auto sync on push         | `true` or `false` (default `false`)          |

### Manual Sync Parameters

| Parameter          | Required | Description              | Constraints                                  |
| ------------------ | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`      | Yes      | Source namespace          | Existing namespace name                      |
| `--repository`     | Yes      | Source repository         | Existing repository name                     |
| `--remoteRegionId` | Yes      | Target region ID          | Must be from `ListSyncRegions` result        |
| `--remoteNamespace`| Yes      | Target namespace          | Namespace name in target region              |
| `--imageTag.[N]`   | Yes      | Tag list (indexed array)  | `--imageTag.1=v1.0 --imageTag.2=v2.0`       |
| `--override`       | No       | Overwrite existing images | `true` or `false` (default `false`)          |

### Trigger Parameters

| Parameter          | Required | Description              | Constraints                                  |
| ------------------ | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`      | Yes      | SWR namespace             | Existing namespace name                      |
| `--repository`     | Yes      | Image repository          | Existing repository name                     |
| `--name`           | Yes      | Trigger name              | Unique within repository                     |
| `--trigger_type`   | Yes      | Trigger type              | `all`, `tag`, `regular`                      |
| `--condition`      | Yes      | Match condition           | `.*` for all, tag name for tag, regex for regular |
| `--action`         | Yes      | Trigger action            | `update`                                     |
| `--app_type`       | Yes      | Application type          | `deployments` or `statefulsets`              |
| `--application`    | Yes      | CCE/CCI application name  | Existing deployment name                     |
| `--cluster_ns`     | Yes      | Application namespace     | Kubernetes namespace (e.g., `default`)       |
| `--enable`         | Yes      | Enable trigger            | `true` or `false`                            |
| `--trigger_mode`   | No       | Deploy target             | `cce` (default) or `cci`                     |
| `--cluster_id`     | CCE only | CCE cluster ID            | Required for cce mode, empty for cci         |
| `--cluster_name`   | No       | CCE cluster name          | Optional cluster name                        |
| `--container`      | No       | Target container          | Specific container name (default: all)       |

## Output Format

### ListSyncRegions (verified)

Response is a flat JSON array of region objects:

```json
[
  {
    "regionID": "cn-north-4",
    "region_name": "north-1"
  }
]
```

**Note**: Returns all available sync target regions. Use `region_id` as `--remoteRegionId`.

### ListImageAutoSyncReposDetails

Response format to be verified — returns list of sync repo configurations when they exist. Returns empty when no auto sync configured.

### ListTriggersDetails

Response format to be verified — returns list of trigger objects when they exist. Returns empty when no triggers configured.

### ShowTrigger

Response format to be verified. Use `--namespace`, `--repository`, `--trigger` (trigger name) as parameters.

### ShowSyncJob (verified)

Response is a flat JSON array. Returns `[]` when no sync jobs exist:

```json
[]
```

**Note**: Requires `--filter="limit::N|offset::N"` parameter. See [Sync Job Status](#4-sync-job-status) for usage.

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

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

## Best Practices

1. **Auto-sync for production repos**: Set `syncAuto=true` for production repositories to ensure images are automatically replicated to target regions
2. **Manual sync for selective replication**: Use `CreateManualImageSyncRepo` when you only need to sync specific tags (e.g., production releases)
3. **Override caution**: Only set `override=true` when you intentionally want to overwrite existing images in the target region
4. **Trigger naming**: Use descriptive trigger names (e.g., `prod-deploy-trigger`, `staging-update-trigger`)
5. **Trigger condition design**: Use `trigger_type=regular` with regex for flexible matching (e.g., `v\d+\.\d+\.\d+` for semver tags)
6. **Disable before delete**: Disable a trigger (`enable=false`) before deleting to avoid unintended deployments during cleanup
7. **Verify target namespace**: Ensure the target namespace exists in the target region before creating sync configurations
8. **Regional namespace alignment**: Use identical namespace names across regions for easier cross-region management
9. **Check sync regions first**: Always run `ListSyncRegions` before creating sync configurations to verify the target region is available

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR Automation API Guide](references/swr-automation-api-guide.md) | hcloud SWR automation API reference |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Image Sync](references/task-image-sync.md)      | Auto/manual sync workflows               |
| [Task: Trigger Management](references/task-trigger-management.md) | Trigger workflows             |
| [CLI Installation Guide](references/cli-installation-guide.md) | KooCLI setup and credential config |
| [Acceptance Criteria](references/acceptance-criteria.md) | Correct/error pattern comparison |

## Notes

- **Auto-sync is persistent** — once configured, it automatically triggers on every new push until deleted
- **Manual sync is one-time** — each `CreateManualImageSyncRepo` invocation syncs specified tags once
- **`--imageTag.[N]` uses indexed array format** — NOT plain value or comma-separated
- **Sync target namespace must exist** — create the namespace in the target region before syncing
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **Trigger requires CCE/CCI cluster** — triggers only work with existing CCE clusters or CCI instances
- **Response formats pending verification** — ListImageAutoSyncReposDetails, ListTriggersDetails, ShowTrigger response formats need live verification

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                        | Symptom                         | Quick Fix                                    |
| ------------------------------ | ------------------------------- | -------------------------------------------- |
| `--imageTag` wrong format      | Manual sync fails               | Use indexed: `--imageTag.1=v1.0`             |
| Target namespace missing       | Sync creation fails             | Create namespace in target region first      |
| Invalid remoteRegionId         | Sync creation fails             | Check with `ListSyncRegions`                 |
| CCE cluster not found          | Trigger creation fails          | Verify cluster_id with CCE console           |
| Trigger already exists         | 409 Conflict                    | Use `ShowTrigger` to check first             |
| Auto-sync unwanted             | Images sync unexpectedly        | Set `syncAuto=false` or delete sync config   |