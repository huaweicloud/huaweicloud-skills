# Task: Instance Registries and Repositories

## Overview

SWR enterprise instance registries define target repositories for image synchronization (replication). Instance repositories hold container images within namespaces. This task covers registry CRUD operations and repository management.

## Part 1: Instance Registries (Sync Targets)

### Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateInstanceRegistry`     | POST   | 创建镜像同步目标仓库      | `--instance_id`, `--name`, `--type`, `--url`, `--credential.type`, `--credential.access_key`, `--credential.access_secret`, `--insecure` |
| `ListInstanceRegistries`     | GET    | 获取目标仓库列表         | `--instance_id`, `--limit`, `--offset`, `--name`, `--type` |
| `ShowInstanceRegistry`      | GET    | 获取目标仓库详情         | `--instance_id`, `--registry_id`                |
| `UpdateInstanceRegistry`     | PUT    | 修改目标仓库             | `--instance_id`, `--registry_id`, `--name`, `--type`, `--url`, `--credential.*`, `--insecure` |
| `DeleteInstanceRegistry`     | DELETE | 删除同步仓库             | `--instance_id`, `--registry_id`                |

### Workflows

#### W1: Create a Registry

Registries define external target repositories for image replication/sync.

**Pre-creation Checklist**:
1. Verify the target registry URL is accessible
2. Obtain authentication credentials for the target registry
3. Decide registry type: `swr-pro` (Harbor), `swr-pro-internal` (SWR enterprise), `huawei-SWR` (basic SWR)

```bash
# Create registry for another SWR enterprise instance
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=target-instance --type=swr-pro-internal --url=https://<target>.cn-east-3.myhuaweicloud.com --credential.type=basic --credential.access_key=<username> --credential.access_secret=<password> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# Create registry for open-source Harbor
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=harbor-prod --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=false --description="Production Harbor" --cli-region=cn-north-4

# Create registry for basic SWR
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=swr-basic --type=huawei-SWR --url=https://swr.cn-north-4.myhuaweicloud.com --credential.type=basic --credential.access_key=<username> --credential.access_secret=<password> --insecure=false --cli-region=cn-north-4

# Create registry with DNS host mapping (for custom DNS resolution)
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=custom-harbor --type=swr-pro --url=https://harbor.internal.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=false --dns_conf.hosts.harbor.internal.example.com=10.0.1.100 --cli-region=cn-north-4

# Create registry without certificate verification (for self-signed certs)
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=self-signed-harbor --type=swr-pro --url=https://harbor.internal.local --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=true --cli-region=cn-north-4
```

**Registry Types**:
- `swr-pro`: Open-source Harbor registry (third-party)
- `swr-pro-internal`: Another Huawei Cloud SWR enterprise instance
- `huawei-SWR`: Basic Huawei Cloud SWR (shared instance)

**Type-Specific Requirements**:
- `swr-pro-internal`: Requires `--instance_id` (body, target instance), `--project_id` (body, target project), `--region_id`
- `swr-pro` and `huawei-SWR`: No additional required fields

⚠️ **Note**: When using `swr-pro-internal`, `--instance_id` appears both as path parameter (source) and body parameter (target). Both must be provided.

**Post-creation Verification**:

```bash
hcloud SWR ShowInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4
```

#### W2: List Registries

```bash
# List all registries
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by name (fuzzy match)
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --name=harbor --cli-region=cn-north-4

# Filter by type
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --type=swr-pro --cli-region=cn-north-4

# Sort by name
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --order_column=name --order_type=asc --cli-region=cn-north-4
```

#### W3: Update a Registry

```bash
# Update registry credentials
hcloud SWR UpdateInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --name=target-instance --type=swr-pro-internal --url=https://<target>.cn-east-3.myhuaweicloud.com --credential.type=basic --credential.access_key=<new-key> --credential.access_secret=<new-secret> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# Update registry description
hcloud SWR UpdateInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --name=harbor-prod --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=false --description="Updated: Production Harbor v2" --cli-region=cn-north-4
```

⚠️ **Note**: All required parameters from `CreateInstanceRegistry` must be provided when updating, even for partial changes.

#### W4: Delete a Registry

```bash
hcloud SWR DeleteInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4
```

⚠️ **Warning**: Deleting a registry removes the sync target configuration. Existing replication policies referencing this registry will fail.

**Post-deletion Verification**:

```bash
# Registry should not appear in list
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --cli-region=cn-north-4
```

## Part 2: Instance Repositories

### Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `ListInstanceRepositories`   | GET    | 获取制品仓库列表         | `--instance_id`, `--namespace_id`, `--limit`, `--offset` |
| `ListAllInstanceRepositories`| GET    | 获取所有实例仓库列表     | `--limit`, `--marker`, `--name`                 |
| `ShowInstanceRepository`     | GET    | 获取制品仓库详情         | `--instance_id`, `--namespace_name`, `--repository_name` |
| `UpdateInstanceRepository`   | PUT    | 修改制品仓库             | `--instance_id`, `--namespace_name`, `--repository_name`, `--description` |
| `DeleteInstanceRepository`   | DELETE | 删除仓库                 | `--instance_id`, `--namespace_name`, `--repository_name` |

### Workflows

#### W5: List Repositories in Instance

```bash
# List all repositories in instance
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --cli-region=cn-north-4

# Filter by namespace ID
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --namespace_id=<ns-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Sort by update time (most recent first)
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```

⚠️ **Note**: `ListInstanceRepositories` uses `--namespace_id` (numeric), not `--namespace_name` (string). Get the namespace ID from `ShowInstanceNamespace`.

#### W6: List All Repositories Across All Instances

```bash
# List all repositories across all instances in the project
hcloud SWR ListAllInstanceRepositories --cli-region=cn-north-4

# Filter by repository name
hcloud SWR ListAllInstanceRepositories --name=my-app --cli-region=cn-north-4

# Pagination using marker
hcloud SWR ListAllInstanceRepositories --limit=20 --cli-region=cn-north-4

# Next page using next_marker from previous response
hcloud SWR ListAllInstanceRepositories --limit=20 --marker=<next_marker> --cli-region=cn-north-4
```

⚠️ **Note**: This operation uses `--marker/--limit` pagination, NOT `--offset/--limit`.

#### W7: View Repository Details

```bash
hcloud SWR ShowInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

**Use Cases**:
- Check repository artifact count
- View repository description
- Verify repository before updating or deleting

#### W8: Update Repository Description

```bash
hcloud SWR UpdateInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --description="Updated: Production-ready app v2" --cli-region=cn-north-4
```

⚠️ **Note**: `UpdateInstanceRepository` only supports updating `--description`. Visibility changes are managed at the namespace level.

#### W9: Delete a Repository

⚠️ **CAUTION**: Deleting a repository permanently removes ALL artifacts (image versions). This is irreversible.

**Pre-deletion Checklist**:
1. List all artifacts to verify what will be deleted:
```bash
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```
2. Confirm with the user that all artifacts will be permanently deleted

```bash
hcloud SWR DeleteInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404
hcloud SWR ShowInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

## Common Scenarios

### S1: Configure Cross-Instance Image Replication

Set up replication between two enterprise instances:

```bash
# 1. Create a registry targeting the destination instance
hcloud SWR CreateInstanceRegistry --instance_id=<source-id> --name=destination --type=swr-pro-internal --url=https://<dest>.cn-east-3.myhuaweicloud.com --credential.type=basic --credential.access_key=<username> --credential.access_secret=<password> --insecure=false --instance_id=<dest-instance-id> --project_id=<dest-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# 2. Verify registry creation
hcloud SWR ShowInstanceRegistry --instance_id=<source-id> --registry_id=<registry-id> --cli-region=cn-north-4

# 3. Create replication policy (using separate replication policy operations)
```

### S2: Repository Inventory Audit

Periodically review repositories across all instances:

```bash
# 1. List all instances
hcloud SWR ListInstance --cli-region=cn-north-4

# 2. For each instance, list repositories
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --cli-region=cn-north-4

# 3. Or list across all instances at once
hcloud SWR ListAllInstanceRepositories --cli-region=cn-north-4

# 4. Check details for specific repositories
hcloud SWR ShowInstanceRepository --instance_id=<instance-id> --namespace_name=<ns> --repository_name=<repo> --cli-region=cn-north-4
```