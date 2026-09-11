# Verification Method

How to verify the output of each `huawei_*` action after execution.

## Query (R3)

| Action | Success criteria |
|--------|------------------|
| `huawei_list_gaussdb_instances` | JSON with `instances` array (may be empty); HTTP 200. Non-empty entries contain `id`, `name`, `status`, `datastore`. |
| `huawei_get_gaussdb_instance` | JSON with `instance` object containing lifecycle fields (`id`, `status`, `type`, `datastore`, `nodes`). |
| `huawei_list_gaussdb_flavors` | JSON with `flavors` array; each contains `spec_code`, `vcpus`, `ram`, `az_status`. |
| `huawei_list_gaussdb_databases` | JSON with `databases` array; each contains `name`, `charset`, `collations`. |

## Analyze (R3)

| Action | Success criteria |
|--------|------------------|
| `huawei_analyze_gaussdb_deployment` | Report states: engine product family, instance count, node topology (primary/readonly/shard counts), engine versions available. For openGauss: deployment form (Ha/distributed), readonly node list, shard disk usage. |
| `huawei_analyze_gaussdb_security` | Report states: security group ID of the instance, whether an EIP is bound, SSL option state, and (when VPC data available) whether the DB port is exposed to 0.0.0.0/0. |

## Manage (R2/R1)

| Action | Success criteria |
|--------|------------------|
| `huawei_create_gaussdb_instance` | Job/order response with `id`/`job_id`; follow up via `ListGaussMySqlInstances` until `status=ACTIVE` (may take 10-30 min). |
| `huawei_create_gaussdb_backup` | `job_id`/`backup_id` returned; verify via `ShowGaussMySqlBackupList`. |
| `huawei_add_gaussdb_readonly_node` | `job_id` returned; verify via `ListInstanceNode` — node count increased. |
| `huawei_add_gaussdb_sharding_node` | `job_id` returned; verify via `ShowShardDiskMessages` — shard count increased. |
| `huawei_update_gaussdb_database_permission` | Success message; verify via `ListGaussMySqlDatabaseUser` and instance's user list. |
| `huawei_delete_gaussdb_instance` | Success message; verify via `ListGaussMySqlInstances` — instance absent (or in recycle bin). |

## General

- All commands should be executed with `--cli-region={region}`. If `--project_id` is required by the help output and the profile lacks it, pass it explicitly.
- JSON output: pipe to `python3 -m json.tool` or `jq` for readability.
- Any HTTP != 2xx → capture the error code, map to the error-code convention in SKILL.md (U/C/N/B/P), and report.

## Reusable Sample Data

Concrete values for business/optional parameters, verified against KooCLI 7.2.12
help output in `cn-north-4`. Use these for verification runs and automated tests
instead of empty placeholders.

| Parameter | Sample value | Notes |
|-----------|--------------|-------|
| `--X-Language` | `en-us` | Header param; **required** for `GaussDB ListInstanceNode` (and its absence makes the command fail with `缺少必填参数:X-Language`) |
| `--availability_zone_mode` | `multi` | `ShowGaussMySqlFlavors`: `single` or `multi` |
| `--database_name` (mysql family) | `gaussdb-mysql` | Engine family used by flavors/engine-version queries |
| `--spec_code` (mysql flavor) | `gaussdb.mysql.large.x86.4` | 4 vCPU/8 GB example; list real values via `ShowGaussMySqlFlavors` |
| `--version_name` (mysql flavor) | `8.0` | MySQL 8.0 is the supported version |
| `--version` (openGauss flavor) | `V2.0-8.0.0` | List real values via `gaussdbforopengauss ListFlavors` |
| `--ha_mode` (openGauss flavor) | `enterprise` | `centralization_standard` (centralized) or `enterprise` (distributed) |
| `--datastore.version` (create, mysql) | `8.0` | Pinned per product family (Critical Warning #3) |
| `--datastore.type` (create, opengauss) | `GaussDB` | openGauss distributed product family |
| `--ha.mode` (create, opengauss) | `Ha` | `Ha` or `Replica` |
| `--charge_info.charge_mode` (create, mysql) | `postPaid` | `postPaid` avoids a long-lived monthly commitment |
| `--priorities.1` (add mysql readonly node) | `1` | Failover priority 1–16 |
| `--expand_cluster.shard.count` (add sharding node) | `1` | DN shard count to add; only valid for openGauss distributed |
| `--users.[N].host` (mysql db permission) | `192.168.1.10` | **Required** host IP for AddDatabasePermission/DeleteDatabasePermission (`--users.1.host=...`) |
| `--users.[N].schema_name` (openGauss db permission) | `app_schema` | **Required** schema name for AllowDbPrivileges (`--users.1.schema_name=...`); avoids template names (postgres/template0/template1) |
| `--is_auto_pay` | `false` | Prevents an unexpected automatic charge during verification |

> Optional parameters are only appended to a command when a concrete value is
> available — never pass bare placeholders (e.g. `--spec_code=`) since KooCLI
> rejects empty values.