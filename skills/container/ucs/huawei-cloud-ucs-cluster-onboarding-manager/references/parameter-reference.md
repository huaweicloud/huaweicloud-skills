# Parameter Reference

## Common Parameters

| Parameter        | Required/Optional | Description                   | Default                              |
| ---------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`   | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--clusterid`    | Context-dependent | UCS cluster ID                | N/A                                  |
| `--clustergroupid` | Context-dependent | Fleet group ID              | N/A                                  |

## Cluster Registration Parameters (K8s API Style)

| Parameter                        | Required | Description                        | Constraints                                  |
| -------------------------------- | -------- | ---------------------------------- | -------------------------------------------- |
| `--apiVersion`                   | Yes      | API version (always `v1`)          | Must be `v1`                                 |
| `--kind`                         | Yes      | Resource kind (always `Cluster`)   | Must be `Cluster`                            |
| `--metadata.name`                | Yes      | Cluster display name               | 1-128 chars                                  |
| `--spec.category`                | Yes      | Cluster category                   | `self` or `onpremise`                        |
| `--spec.provider`                | Yes      | Cluster provider                   | `huaweicloud` or `self_managed`              |
| `--spec.type`                    | Yes      | Cluster type                       | `cce`, `baremetal`, `Kubernetes`, etc.       |
| `--spec.manageType`              | Yes      | Management type                    | `grouped` or `discrete`                      |
| `--spec.country`                 | Yes      | Country code                       | Country code (e.g., `CN`)                    |
| `--spec.city`                    | Yes      | City code                          | City code (e.g., `110000` for Beijing)       |
| `--metadata.uid`                 | CCE only | CCE cluster ID                     | Must reference existing CCE cluster          |
| `--spec.projectID`               | CCE only | Project ID                         | Valid Huawei Cloud project ID (obtain via `ListManagedClusters` response `spec.projectID` field) |
| `--spec.region`                  | CCE only | CCE cluster region                 | Must match CCE cluster region                |
| `--metadata.annotations.kubeconfig` | Self-managed only | Kubeconfig content | Valid Kubernetes kubeconfig YAML           |
| `--spec.clusterGroupID`          | No       | Assign to fleet at registration    | Valid fleet group ID                         |
| `--metadata.labels.*`            | No       | Custom labels                      | Key-value pairs                              |

## UpdateCluster Parameters (K8s API Style)

| Parameter                        | Required | Description                        | Constraints                                  |
| -------------------------------- | -------- | ---------------------------------- | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID (path param)        | Must be registered cluster                   |
| `--apiVersion`                   | Yes      | API version (always `v1`)          | Must be `v1`                                 |
| `--kind`                         | Yes      | Resource kind (always `Cluster`)   | Must be `Cluster`                            |
| `--spec.city`                    | No       | Update city                        | City name                                    |
| `--spec.country`                 | No       | Update country                     | Country code                                 |
| `--metadata.annotations`         | No       | Update annotations                 | Key-value pairs                              |
| `--spec.workerConfig.replicas`   | No       | Update worker replicas             | Integer                                      |
| `--spec.workerConfig.strategy.*` | No       | Update worker strategy             | K8s deployment strategy fields               |

## Fleet Group Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--metadata.name`                | Yes (create) | Group display name   | 1-128 chars                                  |
| `--spec.description`             | No (create)  | Group description    | Free text                                    |
| `--spec.clusterIds.N`            | No (create)  | Initial cluster IDs  | Indexed (1, 2, 3...)                         |
| `--clustergroupid`               | Yes (get/delete/update) | Group ID    | UUID format                                   |
| `--description`                  | Yes (UpdateClusterGroup) | New description | Free text                  |
| `--clusterIds.N`                 | Yes (UpdateClusterGroupAssociatedClusters) | Cluster IDs to add | Indexed |

## Join/Leave Group Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID (path)    | Must be registered cluster                   |
| `--clusterGroupID`               | Yes (JoinGroup) | Fleet group ID (body) | Valid fleet group ID                       |

## Kubeconfig Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--clusterid`                    | Yes      | UCS cluster ID           | Must be registered cluster                   |
| `--clustergroupid`               | Yes (DownloadFederationKubeconfig) | Fleet group ID | Valid fleet group ID            |
| `--duration`                     | Yes (DownloadFederationKubeconfig) | Token duration in seconds | Integer                   |

## Quota Parameters

| Parameter                        | Required | Description              | Constraints                                  |
| -------------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--domainid`                     | Yes      | Account ID               | Huawei Cloud account/domain ID               |

## ShowClusterList Filter Parameters

| Parameter        | Required/Optional | Description                   |
| ---------------- | ----------------- | ----------------------------- |
| `--category`     | Optional          | Filter by cluster category    |
| `--clustergroupid` | Optional        | Filter by fleet group ID      |
| `--clusterids`   | Optional          | Filter by specific cluster IDs |
| `--enablestatus` | Optional          | Filter by cluster status      |
| `--managetype`   | Optional          | Filter by manage type         |
| `--limit`        | Optional          | Pagination limit              |
| `--offset`       | Optional          | Pagination offset             |
| `--order`        | Optional          | Sort order (asc/desc)         |
| `--order_by`     | Optional          | Sort field                    |
