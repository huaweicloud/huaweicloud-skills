# DLI Operation Catalog — hcloud CLI Parameter Reference

> Compiled from `hcloud dli <Operation> --cli-region=cn-north-4 --help` (KooCLI 7.2.12).
> `--cli-region` and `--project_id` are auto-filled by KooCLI and omitted. Array params use indexed form: `--paths.1=...`. All operations belong to service `dli`.

## 01 Queue Management

### ListQueues

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_type` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |
| `--with-charge-info` | No | indexed/array if `.[N]` present |
| `--with-priv` | No | indexed/array if `.[N]` present |

### ShowQueue

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_name` | Yes | indexed/array if `.[N]` present |

### CreateQueue

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--cu_count` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--charging_mode` | No | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--elastic_resource_pool_name` | No | indexed/array if `.[N]` present |
| `--engine` | No | indexed/array if `.[N]` present |
| `--enterprise_project_id` | No | indexed/array if `.[N]` present |
| `--feature` | No | indexed/array if `.[N]` present |
| `--platform` | No | indexed/array if `.[N]` present |
| `--queue_type` | No | indexed/array if `.[N]` present |

### DeleteQueue

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_name` | Yes | indexed/array if `.[N]` present |

### RunQueueAction

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--action` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--cu_count` | No | indexed/array if `.[N]` present |
| `--force` | No | indexed/array if `.[N]` present |

### ListQueuePlans

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_name` | Yes | indexed/array if `.[N]` present |

### CreateQueuePlan

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--plan_name` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--start_hour` | Yes | indexed/array if `.[N]` present |
| `--start_minute` | Yes | indexed/array if `.[N]` present |
| `--target_cu` | Yes | indexed/array if `.[N]` present |
| `--activate` | No | indexed/array if `.[N]` present |
| `--valid_date_begin` | No | indexed/array if `.[N]` present |
| `--valid_date_end` | No | indexed/array if `.[N]` present |

### UpdateQueuePlan

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--plan_id` | Yes | indexed/array if `.[N]` present |
| `--plan_name` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--start_hour` | Yes | indexed/array if `.[N]` present |
| `--start_minute` | Yes | indexed/array if `.[N]` present |
| `--target_cu` | Yes | indexed/array if `.[N]` present |
| `--activate` | No | indexed/array if `.[N]` present |
| `--valid_date_begin` | No | indexed/array if `.[N]` present |
| `--valid_date_end` | No | indexed/array if `.[N]` present |

### DeleteQueuePlan

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--plan_id` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |

### UpdateQueueCidr

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--cidr_in_vpc` | No | indexed/array if `.[N]` present |

## 02 Batch Job Management

### CreateSqlJob

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--sql` | Yes | indexed/array if `.[N]` present |
| `--conf.[N]` | No | indexed/array if `.[N]` present |
| `--current_catalog` | No | indexed/array if `.[N]` present |
| `--currentdb` | No | indexed/array if `.[N]` present |
| `--driver_memory` | No | indexed/array if `.[N]` present |
| `--driver_cores` | No | indexed/array if `.[N]` present |
| `--executor_memory` | No | indexed/array if `.[N]` present |
| `--executor_cores` | No | indexed/array if `.[N]` present |
| `--num_executors` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--sql_type` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ListSqlJobs

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--current-page` | No | indexed/array if `.[N]` present |
| `--db_name` | No | indexed/array if `.[N]` present |
| `--end` | No | indexed/array if `.[N]` present |
| `--engine-type` | No | indexed/array if `.[N]` present |
| `--job-id` | No | indexed/array if `.[N]` present |
| `--job-status` | No | indexed/array if `.[N]` present |
| `--job-type` | No | indexed/array if `.[N]` present |
| `--order` | No | indexed/array if `.[N]` present |
| `--owner` | No | indexed/array if `.[N]` present |
| `--page-size` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--sql_pattern` | No | indexed/array if `.[N]` present |
| `--start` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ShowSqlJobStatus

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### ShowSqlJobDetail

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### ShowSqlJobProgress

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### CancelSqlJob

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### ExportSqlJobResult

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--data_path` | Yes | indexed/array if `.[N]` present |
| `--data_type` | Yes | indexed/array if `.[N]` present |
| `--job_id` | Yes | indexed/array if `.[N]` present |
| `--compress` | No | indexed/array if `.[N]` present |
| `--encoding_type` | No | indexed/array if `.[N]` present |
| `--escape_char` | No | indexed/array if `.[N]` present |
| `--export_mode` | No | indexed/array if `.[N]` present |
| `--limit_num` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--quote_char` | No | indexed/array if `.[N]` present |
| `--with_column_header` | No | indexed/array if `.[N]` present |

### PreviewSqlJobResult

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |
| `--queue-name` | No | indexed/array if `.[N]` present |

### CreateSparkJob

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--className` | Yes | indexed/array if `.[N]` present |
| `--file` | Yes | indexed/array if `.[N]` present |
| `--args.[N]` | No | indexed/array if `.[N]` present |
| `--auto_recovery` | No | indexed/array if `.[N]` present |
| `--catalog_name` | No | indexed/array if `.[N]` present |
| `--cluster_name` | No | indexed/array if `.[N]` present |
| `--conf.[N]` | No | indexed/array if `.[N]` present |
| `--driver_cores` | No | indexed/array if `.[N]` present |
| `--driver_memory` | No | indexed/array if `.[N]` present |
| `--executor_cores` | No | indexed/array if `.[N]` present |
| `--executor_memory` | No | indexed/array if `.[N]` present |
| `--flink_version` | No | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |
| `--jars.[N]` | No | indexed/array if `.[N]` present |
| `--max_retry_times` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--obs_bucket` | No | indexed/array if `.[N]` present |
| `--pyFiles.[N]` | No | indexed/array if `.[N]` present |
| `--queue` | No | indexed/array if `.[N]` present |
| `--resources.[N]` | No | indexed/array if `.[N]` present |
| `--spark_version` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |
| `--USER-ID` | No | indexed/array if `.[N]` present |

### ListSparkJobs

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--cluster_name` | No | indexed/array if `.[N]` present |
| `--end` | No | indexed/array if `.[N]` present |
| `--from` | No | indexed/array if `.[N]` present |
| `--job-id` | No | indexed/array if `.[N]` present |
| `--job_name` | No | indexed/array if `.[N]` present |
| `--order` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--size` | No | indexed/array if `.[N]` present |
| `--state` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ShowSparkJob

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--batch_id` | Yes | indexed/array if `.[N]` present |

### ShowSparkJobStatus

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--batch_id` | Yes | indexed/array if `.[N]` present |

### ShowSparkJobLog

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--batch_id` | Yes | indexed/array if `.[N]` present |
| `--from` | No | indexed/array if `.[N]` present |
| `--index` | No | indexed/array if `.[N]` present |
| `--size` | No | indexed/array if `.[N]` present |
| `--type` | No | indexed/array if `.[N]` present |

### CancelSparkJob

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--batch_id` | Yes | indexed/array if `.[N]` present |

## 03 Flink Job Management

### CreateFlinkSqlJob

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--name` | Yes | indexed/array if `.[N]` present |
| `--checkpoint_enabled` | No | indexed/array if `.[N]` present |
| `--checkpoint_interval` | No | indexed/array if `.[N]` present |
| `--checkpoint_mode` | No | indexed/array if `.[N]` present |
| `--cu_number` | No | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--dirty_data_strategy` | No | indexed/array if `.[N]` present |
| `--execution_agency_urn` | No | indexed/array if `.[N]` present |
| `--flink_log_config` | No | indexed/array if `.[N]` present |
| `--job_type` | No | indexed/array if `.[N]` present |
| `--main_class` | No | indexed/array if `.[N]` present |
| `--obs_bucket` | No | indexed/array if `.[N]` present |
| `--parallel_number` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--restart_waiting_time` | No | indexed/array if `.[N]` present |
| `--resume_checkpoint` | No | indexed/array if `.[N]` present |
| `--resume_max_num` | No | indexed/array if `.[N]` present |
| `--runtime_config` | No | indexed/array if `.[N]` present |
| `--savepoint_path` | No | indexed/array if `.[N]` present |
| `--smn_topic` | No | indexed/array if `.[N]` present |
| `--sql` | No | indexed/array if `.[N]` present |
| `--sql_catalog` | No | indexed/array if `.[N]` present |
| `--sql_dialect` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### CreateFlinkJarJob

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--name` | Yes | indexed/array if `.[N]` present |
| `--checkpoint_enabled` | No | indexed/array if `.[N]` present |
| `--checkpoint_interval` | No | indexed/array if `.[N]` present |
| `--checkpoint_mode` | No | indexed/array if `.[N]` present |
| `--checkpoint_path` | No | indexed/array if `.[N]` present |
| `--cu_number` | No | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--entrypoint` | No | indexed/array if `.[N]` present |
| `--entrypoint_args` | No | indexed/array if `.[N]` present |
| `--execution_agency_urn` | No | indexed/array if `.[N]` present |
| `--flink_log_config` | No | indexed/array if `.[N]` present |
| `--flink_version` | No | indexed/array if `.[N]` present |
| `--jar_url` | No | indexed/array if `.[N]` present |
| `--job_type` | No | indexed/array if `.[N]` present |
| `--main_class` | No | indexed/array if `.[N]` present |
| `--obs_bucket` | No | indexed/array if `.[N]` present |
| `--parallel_number` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--restart_waiting_time` | No | indexed/array if `.[N]` present |
| `--resume_checkpoint` | No | indexed/array if `.[N]` present |
| `--resume_max_num` | No | indexed/array if `.[N]` present |
| `--runtime_config` | No | indexed/array if `.[N]` present |
| `--savepoint_path` | No | indexed/array if `.[N]` present |
| `--smn_topic` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ListFlinkJobs

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_type` | No | indexed/array if `.[N]` present |
| `--limit` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--order` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--root_job_id` | No | indexed/array if `.[N]` present |
| `--show_detail` | No | indexed/array if `.[N]` present |
| `--status` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ShowFlinkJob

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### UpdateFlinkSqlJob

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |
| `--checkpoint_enabled` | No | indexed/array if `.[N]` present |
| `--checkpoint_interval` | No | indexed/array if `.[N]` present |
| `--checkpoint_mode` | No | indexed/array if `.[N]` present |
| `--cu_number` | No | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--dirty_data_strategy` | No | indexed/array if `.[N]` present |
| `--execution_agency_urn` | No | indexed/array if `.[N]` present |
| `--flink_log_config` | No | indexed/array if `.[N]` present |
| `--job_type` | No | indexed/array if `.[N]` present |
| `--main_class` | No | indexed/array if `.[N]` present |
| `--obs_bucket` | No | indexed/array if `.[N]` present |
| `--parallel_number` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--restart_waiting_time` | No | indexed/array if `.[N]` present |
| `--resume_checkpoint` | No | indexed/array if `.[N]` present |
| `--resume_max_num` | No | indexed/array if `.[N]` present |
| `--runtime_config` | No | indexed/array if `.[N]` present |
| `--savepoint_path` | No | indexed/array if `.[N]` present |
| `--smn_topic` | No | indexed/array if `.[N]` present |
| `--sql` | No | indexed/array if `.[N]` present |
| `--sql_catalog` | No | indexed/array if `.[N]` present |
| `--sql_dialect` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### UpdateFlinkJarJob

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |
| `--checkpoint_enabled` | No | indexed/array if `.[N]` present |
| `--checkpoint_interval` | No | indexed/array if `.[N]` present |
| `--checkpoint_mode` | No | indexed/array if `.[N]` present |
| `--checkpoint_path` | No | indexed/array if `.[N]` present |
| `--cu_number` | No | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--entrypoint` | No | indexed/array if `.[N]` present |
| `--entrypoint_args` | No | indexed/array if `.[N]` present |
| `--execution_agency_urn` | No | indexed/array if `.[N]` present |
| `--flink_log_config` | No | indexed/array if `.[N]` present |
| `--flink_version` | No | indexed/array if `.[N]` present |
| `--jar_url` | No | indexed/array if `.[N]` present |
| `--job_type` | No | indexed/array if `.[N]` present |
| `--main_class` | No | indexed/array if `.[N]` present |
| `--obs_bucket` | No | indexed/array if `.[N]` present |
| `--parallel_number` | No | indexed/array if `.[N]` present |
| `--queue_name` | No | indexed/array if `.[N]` present |
| `--restart_waiting_time` | No | indexed/array if `.[N]` present |
| `--resume_checkpoint` | No | indexed/array if `.[N]` present |
| `--resume_max_num` | No | indexed/array if `.[N]` present |
| `--runtime_config` | No | indexed/array if `.[N]` present |
| `--savepoint_path` | No | indexed/array if `.[N]` present |
| `--smn_topic` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### BatchRunFlinkJobs

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_ids.[N]` | Yes | indexed/array if `.[N]` present |
| `--resume_savepoint` | No | indexed/array if `.[N]` present |

### BatchStopFlinkJobs

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_ids.[N]` | Yes | indexed/array if `.[N]` present |
| `--trigger_savepoint` | No | indexed/array if `.[N]` present |

### BatchDeleteFlinkJobs

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_ids.[N]` | Yes | indexed/array if `.[N]` present |

### DeleteFlinkJob

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_id` | Yes | indexed/array if `.[N]` present |

### ShowFlinkMetric

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_ids.[N]` | Yes | One or more Flink job IDs, indexed/array if `.[N]` present, e.g. `--job_ids.1=101 --job_ids.2=102` |

## 04 Database Management

### ListDatabases

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--keyword` | No | indexed/array if `.[N]` present |
| `--limit` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |
| `--with-priv` | No | indexed/array if `.[N]` present |

### CreateDatabase

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--enterprise_project_id` | No | indexed/array if `.[N]` present |

### DeleteDatabase

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--async` | No | indexed/array if `.[N]` present |
| `--cascade` | No | indexed/array if `.[N]` present |

### UpdateDatabaseOwner

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--new_owner` | Yes | indexed/array if `.[N]` present |

### ListDatabaseUsers

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |

## 05 Table Management

### ListTables

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--current-page` | No | indexed/array if `.[N]` present |
| `--keyword` | No | indexed/array if `.[N]` present |
| `--page-size` | No | indexed/array if `.[N]` present |
| `--table-type` | No | indexed/array if `.[N]` present |
| `--with-detail` | No | indexed/array if `.[N]` present |
| `--with-priv` | No | indexed/array if `.[N]` present |

### ShowTable

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |

### CreateTable

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--columns.[N].column_name` | Yes | indexed/array if `.[N]` present |
| `--columns.[N].type` | Yes | indexed/array if `.[N]` present |
| `--data_location` | Yes | indexed/array if `.[N]` present |
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |
| `--columns.[N].description` | No | indexed/array if `.[N]` present |
| `--columns.[N].is_partition_column` | No | indexed/array if `.[N]` present |
| `--data_path` | No | indexed/array if `.[N]` present |
| `--data_type` | No | indexed/array if `.[N]` present |
| `--date_format` | No | indexed/array if `.[N]` present |
| `--delimiter` | No | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--escape_char` | No | indexed/array if `.[N]` present |
| `--quote_char` | No | indexed/array if `.[N]` present |

### DeleteTable

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |
| `--async` | No | indexed/array if `.[N]` present |

### UpdateTableOwner

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--new_owner` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |

### ListPartitions

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |
| `--limit` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |

### PreviewTable

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |
| `--mode` | No | indexed/array if `.[N]` present |

### ListTableUsers

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |

### ListTablePrivileges

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--database_name` | Yes | indexed/array if `.[N]` present |
| `--table_name` | Yes | indexed/array if `.[N]` present |
| `--user_name` | Yes | indexed/array if `.[N]` present |

## 06 Connection Management

### ListEnhancedConnections

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--limit` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--status` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ShowEnhancedConnection

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### CreateEnhancedConnection

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--dest_network_id` | Yes | indexed/array if `.[N]` present |
| `--dest_vpc_id` | Yes | indexed/array if `.[N]` present |
| `--name` | Yes | indexed/array if `.[N]` present |
| `--routetable_id` | No | indexed/array if `.[N]` present |

### UpdateEnhancedConnection

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |
| `--hosts.[N].ip` | No | indexed/array if `.[N]` present |
| `--hosts.[N].name` | No | indexed/array if `.[N]` present |

### DeleteEnhancedConnection

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### AssociateQueueToEnhancedConnection

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### DisassociateQueueFromEnhancedConnection

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### CreateConnectivityTask

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--address` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |

### ShowConnectivityTask

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--task_id` | Yes | indexed/array if `.[N]` present |

### ListDatasourceConnections

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--tags` | No | indexed/array if `.[N]` present |

### ShowDatasourceConnection

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### CreateDatasourceConnection

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--name` | Yes | indexed/array if `.[N]` present |
| `--network_id` | Yes | indexed/array if `.[N]` present |
| `--security_group_id` | Yes | indexed/array if `.[N]` present |
| `--service` | Yes | indexed/array if `.[N]` present |
| `--url` | No | indexed/array if `.[N]` present |

### DeleteDatasourceConnection

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

## 07 Resource Package Management

### ListJobResources

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--kind` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### ShowJobResource

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--resource_name` | Yes | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |

### UploadJarJobResources

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--group` | Yes | indexed/array if `.[N]` present |
| `--paths.[N]` | Yes | indexed/array if `.[N]` present |

### UploadPythonFileJobResources

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--group` | Yes | indexed/array if `.[N]` present |
| `--paths.[N]` | Yes | indexed/array if `.[N]` present |

### UploadFileJobResources

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--group` | Yes | indexed/array if `.[N]` present |
| `--paths.[N]` | Yes | indexed/array if `.[N]` present |

### UploadJobResources

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--group` | Yes | indexed/array if `.[N]` present |
| `--kind` | Yes | indexed/array if `.[N]` present |
| `--paths.[N]` | Yes | indexed/array if `.[N]` present |
| `--is_async` | No | indexed/array if `.[N]` present |

### DeleteJobResource

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--resource_name` | Yes | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |

### UpdateJobResourceOwner

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--group_name` | Yes | indexed/array if `.[N]` present |
| `--new_owner` | Yes | indexed/array if `.[N]` present |
| `--resource_name` | No | indexed/array if `.[N]` present |

## 08 Global Variable Management

### ListGlobalVariables

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--limit` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |

### CreateGlobalVariable

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--var_name` | Yes | indexed/array if `.[N]` present |
| `--var_value` | Yes | indexed/array if `.[N]` present |
| `--is_sensitive` | No | indexed/array if `.[N]` present |

### UpdateGlobalVariable

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--var_name` | Yes | indexed/array if `.[N]` present |
| `--var_value` | Yes | indexed/array if `.[N]` present |

### DeleteGlobalVariable

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--var_name` | Yes | indexed/array if `.[N]` present |

## 09 Job Template Management

### ListSqlJobTemplates

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--keyword` | No | indexed/array if `.[N]` present |

### CreateSqlJobTemplate

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--sql` | Yes | indexed/array if `.[N]` present |
| `--sql_name` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |

### UpdateSqlJobTemplate

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--sql_id` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |
| `--sql` | No | indexed/array if `.[N]` present |
| `--sql_name` | No | indexed/array if `.[N]` present |

### BatchDeleteSqlJobTemplates

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--sql_ids.[N]` | Yes | indexed/array if `.[N]` present |

### ListFlinkSqlJobTemplates

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--limit` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--order` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### CreateFlinkSqlJobTemplate

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--name` | Yes | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--job_type` | No | indexed/array if `.[N]` present |
| `--sql_body` | No | indexed/array if `.[N]` present |

### UpdateFlinkSqlJobTemplate

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--template_id` | Yes | indexed/array if `.[N]` present |
| `--desc` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--sql_body` | No | indexed/array if `.[N]` present |

### DeleteFlinkSqlJobTemplate

**Method:** `DELETE`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--template_id` | Yes | indexed/array if `.[N]` present |

### ListSparkJobTemplates

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--current-page` | No | indexed/array if `.[N]` present |
| `--keyword` | No | indexed/array if `.[N]` present |
| `--page-size` | No | indexed/array if `.[N]` present |
| `--type` | No | indexed/array if `.[N]` present |

### CreateSparkJobTemplate

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--body` | Yes | indexed/array if `.[N]` present |
| `--name` | Yes | indexed/array if `.[N]` present |
| `--type` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |
| `--language` | No | indexed/array if `.[N]` present |

### UpdateSparkJobTemplate

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--body` | Yes | indexed/array if `.[N]` present |
| `--name` | Yes | indexed/array if `.[N]` present |
| `--template_id` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--group` | No | indexed/array if `.[N]` present |

## 10 Privilege And Inspection

### ListAuthorizationPrivileges

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--object` | Yes | indexed/array if `.[N]` present |

### RunAuthorizationAction

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--action` | Yes | indexed/array if `.[N]` present |
| `--projectId` | No | indexed/array if `.[N]` present |
| `--user_name` | No | indexed/array if `.[N]` present |

### RunDataAuthorizationAction

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--action` | Yes | indexed/array if `.[N]` present |
| `--user_name` | Yes | indexed/array if `.[N]` present |

### RegisterAuthorizedQueue

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--action` | Yes | indexed/array if `.[N]` present |
| `--queue_name` | Yes | indexed/array if `.[N]` present |
| `--user_name` | Yes | indexed/array if `.[N]` present |

### ShowEnhancedConnectionPrivilege

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--connection_id` | Yes | indexed/array if `.[N]` present |

### ListElasticResourcePools

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--limit` | No | indexed/array if `.[N]` present |
| `--name` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--status` | No | indexed/array if `.[N]` present |
| `--tags` | No | indexed/array if `.[N]` present |

### UpdateElasticResourcePool

**Method:** `PUT`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--elastic_resource_pool_name` | Yes | indexed/array if `.[N]` present |
| `--description` | No | indexed/array if `.[N]` present |
| `--max_cu` | No | indexed/array if `.[N]` present |
| `--min_cu` | No | indexed/array if `.[N]` present |

### ListElasticResourcePoolScaleRecords

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--elastic_resource_pool_name` | Yes | indexed/array if `.[N]` present |
| `--end_time` | No | indexed/array if `.[N]` present |
| `--limit` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |
| `--start_time` | No | indexed/array if `.[N]` present |
| `--status` | No | indexed/array if `.[N]` present |

### ShowQuota

**Method:** `GET`

No additional parameters (region/project auto only).

### ShowDliAgency

**Method:** `GET`

No additional parameters (region/project auto only).

### ShowFlinkMetric

**Method:** `POST`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--job_ids.[N]` | Yes | One or more Flink job IDs, indexed/array if `.[N]` present, e.g. `--job_ids.1=101 --job_ids.2=102` |

### ListCatalogs

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--limit` | No | indexed/array if `.[N]` present |
| `--offset` | No | indexed/array if `.[N]` present |

### ShowCatalog

**Method:** `GET`

| Parameter | Required | Format note |
|-----------|----------|-------------|
| `--catalog_name` | Yes | indexed/array if `.[N]` present |
