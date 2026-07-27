# API Paths — Verified from SDK Source

> All API paths extracted from `huaweicloudsdkmodelarts` v1 `_http_info` `resource_path` field. No inferred endpoints.

## Instance Management

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| CreateNotebook | POST | /v1/{project_id}/notebooks |
| ListNotebooks | GET | /v1/{project_id}/notebooks |
| ListAllNotebooks | GET | /v1/{project_id}/notebooks/all |
| ShowNotebook | GET | /v1/{project_id}/notebooks/{id} |
| UpdateNotebook | PUT | /v1/{project_id}/notebooks/{id} |
| DeleteNotebook | DELETE | /v1/{project_id}/notebooks/{id} |
| StartNotebook | POST | /v1/{project_id}/notebooks/{id}/start |
| StopNotebook | POST | /v1/{project_id}/notebooks/{id}/stop |

## Lease Management

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| ShowLease | GET | /v1/{project_id}/notebooks/{id}/lease |
| RenewLease | PATCH | /v1/{project_id}/notebooks/{id}/lease |

## Tag Management

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| ShowNotebookTags | GET | /v1/{project_id}/notebooks/tags |
| CreateNotebookTags | POST | /v1/{project_id}/notebooks/{resource_id}/tags/create |
| DeleteNotebookTags | DELETE | /v1/{project_id}/notebooks/{resource_id}/tags/delete |

## Image Management

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| CreateImage | POST | /v1/{project_id}/notebooks/{id}/create-image |
| ListImage | GET | /v1/{project_id}/images |
| RegisterImage | POST | /v1/{project_id}/images |
| ShowImage | GET | /v1/{project_id}/images/{id} |
| DeleteImage | DELETE | /v1/{project_id}/images/{id} |
| SyncImage | POST | /v1/{project_id}/images/{image_id}/sync |
| ListImageGroup | GET | /v1/{project_id}/images/group |
| DeleteImageGroup | DELETE | /v1/{project_id}/images/group/{id} |
| UpdateImageGroup | PUT | /v1/{project_id}/images/group/{id} |

## Flavor and Cluster

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| ListFlavors | GET | /v1/{project_id}/notebooks/flavors |
| ShowSwitchableFlavors | GET | /v1/{project_id}/notebooks/{id}/flavors |
| ListAuthoringClusters | GET | /v1/{project_id}/authoring/clusters |
| ShowCluster | GET | /v1/{project_id}/authoring/clusters/{cluster_id} |

## Feature Query

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| ListFeatures | GET | /v1/{project_id}/authoring/features/{feature} |

## Dynamic Storage

| CLI Operation | HTTP Method | Resource Path |
|---------------|-------------|---------------|
| ListDynamicStorages | GET | /v1/{project_id}/notebooks/{instance_id}/storage |
| AttachDynamicStorage | POST | /v1/{project_id}/notebooks/{instance_id}/storage |
| ShowDynamicStorage | GET | /v1/{project_id}/notebooks/{instance_id}/storage/{storage_id} |
| DetachDynamicStorage | DELETE | /v1/{project_id}/notebooks/{instance_id}/storage/{storage_id} |

## Source

- SDK Package: `huaweicloudsdkmodelarts` v3.1.207
- Source File: `huaweicloudsdkmodelarts/v1/modelarts_client.py`
- Extraction Method: `grep _http_info` → `resource_path` field
