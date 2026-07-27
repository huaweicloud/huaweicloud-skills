# SWR Parameter Reference

This document provides detailed parameter tables and region ID reference for SWR API commands.

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--namespace`   | Context-dependent | SWR namespace (organization)  | N/A                                  |
| `--repository`  | Context-dependent | Image repository name         | N/A                                  |
| `--tag`         | Context-dependent | Image tag/version name        | N/A                                  |

### Namespace Parameters

| Parameter      | Required | Description            | Constraints                                    |
| -------------- | -------- | ---------------------- | ---------------------------------------------- |
| `--namespace`  | Yes      | Namespace name         | 1-64 chars, lowercase start, specific rules    |
| `--filter`     | No       | Filter by name/mode    | `namespace::{name}|mode::{mode}`               |

### Repository Parameters

| Parameter         | Required | Description              | Constraints                                  |
| ----------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`     | Yes      | Namespace name           | See naming rules                             |
| `--repository`    | Yes      | Repository name          | See naming rules                             |
| `--is_public`     | Yes      | Public/private           | `true` or `false`                            |
| `--category`      | No       | Repository category      | See category list                            |
| `--description`   | No       | Repository description   | Free text                                    |
| `--limit`         | No       | Page size                | Max 1000, default 100                        |
| `--offset`        | No       | Page offset              | Must pair with `--limit`                     |
| `--order_column`  | No       | Sort column              | **Varies by command**: `ListReposDetails` accepts `name`, `updated_time`, `tag_count`; `ListRepositoryTags` accepts `updated_at` only. Note: `updated_time` is the sort param, not the response field `updated_at` |
| `--order_type`    | No       | Sort direction           | `desc` (descending), `asc` (ascending)       |
| `--name`          | No       | Search by name (fuzzy)   | Partial match                                |

### Tag Parameters

| Parameter         | Required | Description              | Constraints                                  |
| ----------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`     | Yes      | Namespace name           | See naming rules                             |
| `--repository`    | Yes      | Repository name          | See naming rules                             |
| `--tag`           | Yes      | Tag/version name         | Free text                                    |
| `--source_tag`    | Yes      | Source tag (for create)  | Existing tag name                            |
| `--destination_tag` | Yes    | Target tag (for create)  | New tag name                                 |
| `--override`      | No       | Overwrite existing tag   | `true` or `false`                            |
| `--limit`         | No       | Page size                | Max 1000, default 100                        |
| `--offset`        | No       | Page offset              | Must pair with `--limit`                     |
| `--order_column`  | No       | Sort column              | `updated_at` only (see note below)           |
| `--order_type`    | No       | Sort direction           | `desc` or `asc`                              |

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

