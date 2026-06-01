# Task: Trigger Management

## Overview

SWR triggers enable automatic deployment updates when new images are pushed. A trigger watches a repository for new image pushes matching a condition, and automatically updates a CCE or CCI workload. This task covers creating, querying, updating, and deleting triggers.

## Operations Catalog

| Operation            | Method | Description              | Key Parameters                                  |
| -------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateTrigger`      | POST   | 创建触发器               | `--namespace`, `--repository`, `--name`, `--trigger_type`, `--condition`, `--action`, `--app_type`, `--application`, `--cluster_ns`, `--enable`, `--trigger_mode`, `--cluster_id` |
| `ListTriggersDetails` | GET   | 查询触发器列表           | `--namespace`, `--repository`                   |
| `ShowTrigger`        | GET    | 查询触发器详情           | `--namespace`, `--repository`, `--trigger`      |
| `UpdateTrigger`      | PUT    | 更新触发器               | `--namespace`, `--repository`, `--trigger`, `--enable` |
| `DeleteTrigger`      | DELETE | 删除触发器               | `--namespace`, `--repository`, `--trigger`      |

## Workflows

### W1: Create a Trigger

Set up auto-deploy to a CCE workload when new images are pushed:

**Pre-creation Checklist**:
1. Verify repository exists:
```bash
hcloud SWR ShowRepository --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```
2. Obtain CCE cluster ID from CCE console
3. Verify deployment exists in the CCE cluster
4. Decide trigger type and condition

```bash
# Create trigger for ALL image pushes to CCE deployment
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=deploy-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cluster_name=<cluster-name> --cli-region=cn-north-4

# Create trigger for specific tag pushes (only v2.0)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=release-trigger --trigger_type=tag --condition=v2.0 --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# Create trigger for semver tag pattern
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=semver-trigger --trigger_type=regular --condition="v\d+\.\d+\.\d+" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# Create trigger for StatefulSet
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=sts-trigger --trigger_type=all --condition=".*" --action=update --app_type=statefulsets --application=my-statefulset --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --cli-region=cn-north-4

# Create trigger for CCI (no cluster_id)
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=cci-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-cci-app --cluster_ns=default --enable=true --trigger_mode=cci --cli-region=cn-north-4

# Create trigger targeting a specific container only
hcloud SWR CreateTrigger --namespace=group-dev --repository=my-app --name=container-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --container=my-sidecar --cli-region=cn-north-4
```

**Trigger Parameters**:
- `--trigger_type`: `all` (any push), `tag` (exact tag), `regular` (regex match)
- `--condition`: Must match trigger_type — `.*` for all, tag name for tag, regex for regular
- `--app_type`: `deployments` or `statefulsets`
- `--trigger_mode`: `cce` (CCE cluster, requires `cluster_id`) or `cci` (CCI instance)
- `--container`: Optional — target specific container within multi-container pods

**Post-creation Verification**:

```bash
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

### W2: List All Triggers

```bash
# List triggers for a repository
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Use Cases**:
- Audit all trigger configurations for a repository
- Verify trigger was created correctly
- Check trigger enable/disable status

### W3: View Trigger Details

```bash
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

**Use Cases**:
- Verify trigger configuration (type, condition, target)
- Check trigger status (enabled/disabled)
- Troubleshoot trigger not firing

### W4: Update a Trigger

```bash
# Disable a trigger (pause auto-deploy without deleting)
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=false --cli-region=cn-north-4

# Re-enable a trigger
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=true --cli-region=cn-north-4
```

**Common Update Use Cases**:
- Temporarily disable trigger during maintenance
- Re-enable after maintenance window
- Run `hcloud SWR UpdateTrigger --help` for all updateable parameters

### W5: Delete a Trigger

⚠️ **Best Practice**: Disable trigger before deleting to prevent unintended deployments during the deletion process.

```bash
# 1. Disable trigger first (recommended)
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --enable=false --cli-region=cn-north-4

# 2. Delete trigger
hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=deploy-trigger --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404 or trigger should not appear in list
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

## Common Scenarios

### S1: CI/CD Auto-deploy Pipeline

Set up automatic deployment updates when CI pushes new images:

```bash
# 1. Create trigger for production deployment (semver only)
hcloud SWR CreateTrigger --namespace=prod --repository=my-app --name=prod-deploy --trigger_type=regular --condition="v\d+\.\d+\.\d+" --action=update --app_type=deployments --application=my-app-deployment --cluster_ns=production --enable=true --trigger_mode=cce --cluster_id=<prod-cluster-id> --cli-region=cn-north-4

# 2. Create trigger for staging (all pushes)
hcloud SWR CreateTrigger --namespace=staging --repository=my-app --name=staging-deploy --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-app-deployment --cluster_ns=staging --enable=true --trigger_mode=cce --cluster_id=<staging-cluster-id> --cli-region=cn-north-4
```

### S2: Multi-container Deployment Update

Update only a specific container in a multi-container pod:

```bash
# Update only the sidecar container, not the main app container
hcloud SWR CreateTrigger --namespace=group-dev --repository=log-collector --name=sidecar-trigger --trigger_type=all --condition=".*" --action=update --app_type=deployments --application=my-app-deployment --cluster_ns=default --enable=true --trigger_mode=cce --cluster_id=<cluster-id> --container=log-collector --cli-region=cn-north-4
```

### S3: Trigger Audit and Cleanup

Periodically review and clean up triggers:

```bash
# 1. List all triggers for each repository
hcloud SWR ListTriggersDetails --namespace=group-dev --repository=my-app --cli-region=cn-north-4

# 2. Review each trigger configuration
hcloud SWR ShowTrigger --namespace=group-dev --repository=my-app --trigger=<trigger-name> --cli-region=cn-north-4

# 3. Disable unused triggers
hcloud SWR UpdateTrigger --namespace=group-dev --repository=my-app --trigger=<unused-trigger> --enable=false --cli-region=cn-north-4

# 4. Delete obsolete triggers
hcloud SWR DeleteTrigger --namespace=group-dev --repository=my-app --trigger=<obsolete-trigger> --cli-region=cn-north-4
```