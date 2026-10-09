---
name: huawei-cloud-dli-manage
description: >
  Manages Huawei Cloud DLI (Data Lake Insight) full lifecycle operations:
  compute queue management (create/scale/plan/delete), batch jobs (SQL/Spark
  submit, cancel, status, logs, result export), Flink stream jobs (submit,
  start/stop, batch delete, metrics), database and table metadata governance
  (create/delete/owner/privileges/partitions/preview), enhanced cross-source
  connections (create/update/delete, queue binding, connectivity checks),
  resource packages (JAR/Py/File upload), global variables, SQL/Flink/Spark job
  templates, permission authorization, and CU usage patrol. Produces structured
  inspection reports and change snapshots, detects over-high CU usage and
  cross-source connectivity failures. High-risk operations require double
  confirmation; cloud-side operations only, no autonomous business SQL overwrite.
triggers:
  - "DLI队列管理"
  - "DLI作业排查"
  - "Flink作业运维"
  - "库表元数据治理"
  - "跨源连接配置"
  - "资源包上传"
  - "全局变量管理"
  - "作业模板管理"
  - "CU用量巡检"
  - "闲置资源清理"
  - "DLI日常巡检"
  - "DLI troubleshooting"
  - "DLI inspection"
  - "DLI queue scale"
  - "DLI job submit"
  - "query DLI databases/tables"
tags: [huawei-cloud, dli, bigdata, data-lake-insight, ops]
---

# Huawei Cloud DLI Resource Management Skill

## Overview

This Skill provides a full-lifecycle operations toolkit for Huawei Cloud DLI
(Data Lake Insight) using the `dli` service of the hcloud CLI, covering ten capability groups:

1. **Queue management** — `ListQueues`, `ShowQueue`, `CreateQueue`, `DeleteQueue`, `RunQueueAction` (scale), queue plans, CIDR
2. **Batch jobs (SQL/Spark)** — `CreateSqlJob`, `ListSqlJobs`, `ShowSqlJobStatus/Detail/Progress`, `CancelSqlJob`, `ExportSqlJobResult`, `PreviewSqlJobResult`, Spark equivalents + `ShowSparkJobLog`
3. **Flink stream jobs** — `CreateFlinkSqlJob`, `CreateFlinkJarJob`, `ListFlinkJobs`, `ShowFlinkJob`, `UpdateFlink*`, `BatchRunFlinkJobs`, `BatchStopFlinkJobs`, `BatchDeleteFlinkJobs`, `ShowFlinkMetric`
4. **Database management** — `ListDatabases`, `CreateDatabase`, `DeleteDatabase`, `UpdateDatabaseOwner`, `ListDatabaseUsers`
5. **Table management** — `ListTables`, `ShowTable`, `CreateTable`, `DeleteTable`, `UpdateTableOwner`, `ListPartitions`, `PreviewTable`, table users/privileges
6. **Enhanced connections** — `ListEnhancedConnections`, `Create/Update/DeleteEnhancedConnection`, queue binding, `CreateConnectivityTask`/`ShowConnectivityTask`
7. **Resource packages** — `ListJobResources`, `ShowJobResource`, `UploadJar/PythonFile/FileJobResources`, `DeleteJobResource`, `UpdateJobResourceOwner`
8. **Global variables** — `ListGlobalVariables`, `CreateGlobalVariable`, `UpdateGlobalVariable`, `DeleteGlobalVariable`; **Job templates** — SQL/Flink SQL/Spark templates: list, create, update, delete
9. **Privileges & patrol** — authorization actions, queue/database/table users, elastic resource pools (CU), quota, agency, catalogs

### Important Constraints

| Constraint | Policy |
|------------|--------|
| High-risk operations | **Double confirmation required** before: deleting databases (especially `--cascade`), deleting tables, deleting queues, deleting/cancelling running stream jobs, batch-stop/batch-delete Flink jobs, scaling queues down (`scale_in`), deleting queue plans (**metadata is permanently irrecoverable — verify target and scope before confirming**) |
| Business SQL | This Skill performs **cloud-side operations only**. It never autonomously runs business write/overwrite SQL (`INSERT OVERWRITE`, `DELETE`, `UPDATE`, `DROP`) against user business tables via `CreateSqlJob`. SQL submission is allowed only for explicitly user-confirmed, non-destructive statements (e.g. `SELECT` / metadata `SHOW`), scoped to inspection or user-authorized tasks |
| Production idle cleanup | Never arbitrarily clean production business metadata. Idle-resource cleanup proposals must be reported and confirmed by the user first |
| Scope | All operations stay within DLI resource management; no changes to OBS data content, no IAM policy changes |

## Prerequisites

1. **hcloud CLI** installed and authenticated with a valid AK/SK profile (installation guide and verification: see `references/cli-installation-guide.md`).
2. **IAM permissions**: DLI read permissions for query operations; DLI admin/write permissions for create/update/delete. See `references/iam-policies.md`.
3. **Region**: DLI resources are regional; pass `--cli-region={region}` on every command.
4. **OBS paths** (resource upload / result export): a pre-existing OBS bucket with readable paths, passed as OBS object URLs for `--paths.[N]`.
5. **Queue for SQL/Spark jobs**: a running SQL or general queue is required to submit jobs; check `ListQueues` first.

## Workflow

### Scenario 1: Daily Resource Patrol (巡检)

```
ListQueues --with-charge-info -> queue inventory/CU; ListElasticResourcePools + ScaleRecords -> pool CU
ListSqlJobs / ListFlinkJobs -> running & failed jobs; ShowQuota -> CU used/remaining (>80% flag)
ShowDliAgency -> agency state; Output: structured patrol report (inventory + risks + cleanup proposals)
```

### Scenario 2: Batch Job Troubleshooting (批作业故障排查)

```
ListSqlJobs --job-status=failed / ListSparkJobs --state=failed -> find failures
ShowSqlJobStatus/ShowSqlJobDetail -> reason & logs; (Spark) ShowSparkJobLog -> log tail
ShowSqlJobProgress -> running progress; Output: root-cause report (SQL/parameter/quota/connection)
```

### Scenario 3: Flink Stream Job Operations (流作业运维)

```
ListFlinkJobs --job_type --status -> jobs; ShowFlinkJob -> detail/restart/checkpoint info
BatchRunFlinkJobs / BatchStopFlinkJobs (--trigger_savepoint) -> start/stop after double confirmation
ShowFlinkMetric -> CU metrics; Output: change snapshot of start/stop actions
```

### Scenario 4: Metadata Governance (库表元数据治理)

```
ListDatabases / ListTables --with-detail -> inventory; ShowTable -> schema/location/owner
ListPartitions -> partition layout; UpdateTableOwner / UpdateDatabaseOwner -> ownership alignment
DeleteDatabase/DeleteTable -> ONLY with user double confirmation (cascade risk!); Output: change snapshot
```

### Scenario 5: Cross-Source Connection (跨源连接)

```
ListEnhancedConnections -> inventory + status; CreateConnectivityTask + ShowConnectivityTask -> test result
AssociateQueueToEnhancedConnection / DisassociateQueueFromEnhancedConnection -> queue binding (if test fails)
UpdateEnhancedConnection --hosts.[N].ip/.name -> host whitelist (full overwrite); Output: connectivity risk report
```

### Scenario 6: Idle Resource Cleanup (闲置资源清理)

```
ListQueues/ListQueuePlans/ListJobResources/ListGlobalVariables/ListSqlJobTemplates -> stale inventory
Report cleanup proposals to user -> wait for confirmation
After confirmation: DeleteQueue, DeleteJobResource, DeleteGlobalVariable, BatchDeleteSqlJobTemplates; Output: snapshot
```

### Safety Gate (all scenarios)

Before any high-risk command (see Constraints), present the exact command, its
scope, and irreversibility warning to the user and wait for an explicit
confirmation keyword. Never batch-execute destructive commands without per-command
confirmation. Mask AK/SK in outputs and logs.

## Core Commands

All commands use `hcloud dli <Operation>`. `--cli-region` and `--project_id`
are auto-filled by KooCLI (from profile) and omitted in parameter tables below.
The full operation catalog with per-command parameter tables lives in
`references/dli-operation-catalog.md`.

### 1. Queue Management

#### List Queues

```bash
hcloud dli ListQueues --cli-region={region} --queue_type={sql|general|all} [--tags={key=value}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--queue_type` | No | `sql`, `general`, or `all` (default `sql`) |
| `--tags` | No | Tag filter, e.g. `owner=ph` |

#### Show Queue

```bash
hcloud dli ShowQueue --cli-region={region} --queue_name={queue_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--queue_name` | Yes | Name of the queue |

#### Create Queue

```bash
hcloud dli CreateQueue --cli-region={region} --queue_name={queue_name} --cu_count={cu_count} [--queue_type={sql|general}] [--engine={spark|flink|hetero}] [--charging_mode={prePaid|postPaid}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--queue_name` | Yes | Queue name (unique in project) |
| `--cu_count` | Yes | Number of CUs (16 minimum) |
| `--queue_type` | No | `sql` or `general` (default `sql`) |
| `--engine` | No | `spark`, `flink`, or `hetero` |
| `--charging_mode` | No | `prePaid` or `postPaid` |

#### Scale Queue (risk: double confirm for scale_in)

```bash
hcloud dli RunQueueAction --cli-region={region} --queue_name={queue_name} --action={scale_out|scale_in} [--cu_count={cu_count}] [--force=true]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--action` | Yes | `scale_out` or `scale_in` |
| `--queue_name` | Yes | Queue to scale |
| `--cu_count` | No | Target CU count |
| `--force` | No | Force scale when jobs are running |

#### Delete Queue (risk: double confirm)

```bash
hcloud dli DeleteQueue --cli-region={region} --queue_name={queue_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--queue_name` | Yes | Queue to delete (must be stopped/empty) |

#### Queue Plans (定时扩缩容)

```bash
hcloud dli ListQueuePlans --cli-region={region} --queue_name={queue_name}
hcloud dli CreateQueuePlan --cli-region={region} --queue_name={queue_name} --plan_name={plan_name} \
  --start_hour={hour} --start_minute={minute} --target_cu={cu_count} [--activate={true|false}]
hcloud dli UpdateQueuePlan --cli-region={region} --queue_name={queue_name} --plan_id={plan_id} \
  --plan_name={plan_name} --start_hour={hour} --start_minute={minute} --target_cu={cu_count}
hcloud dli DeleteQueuePlan --cli-region={region} --queue_name={queue_name} --plan_id={plan_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--queue_name` | Yes | Target queue |
| `--plan_name` | Yes (create/update) | Plan name |
| `--plan_id` | Yes (update/delete) | Plan ID |
| `--start_hour` / `--start_minute` | Yes (create/update) | Trigger time of day (0-23 / 0-59) |
| `--target_cu` | Yes (create/update) | Target CU count after scaling |
| `--activate` | No | Activate immediately |

### 2. Batch Jobs (SQL / Spark)

#### Submit SQL Job (cloud-side only; see Constraints)

```bash
hcloud dli CreateSqlJob --cli-region={region} --sql={sql_statement} \
  [--queue_name={queue_name}] [--currentdb={database}] [--sql_type={ddl|dcl|import|query|insert}] [--conf.1={key=value}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--sql` | Yes | SQL statement (non-destructive only unless user-confirmed) |
| `--queue_name` | No | Target queue (default queue if omitted) |
| `--currentdb` | No | Database context for the SQL |
| `--sql_type` | No | `ddl`, `dcl`, `import`, `query`, `insert` |
| `--conf.[N]` | No | Job config as `key=value` array |

#### List SQL Jobs

```bash
hcloud dli ListSqlJobs --cli-region={region} [--job-status={pending|running|success|failed|cancelled}] [--job-type={DDL|DCL|IMPORT|QUERY|INSERT}] [--db_name={database}] [--queue_name={queue_name}] [--page-size={n}] [--current-page={n}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--job-status` | No | `pending`, `running`, `success`, `failed`, `cancelled` |
| `--job-type` | No | `DDL`, `DCL`, `IMPORT`, `QUERY`, `INSERT` |
| `--db_name` | No | Database filter |
| `--queue_name` | No | Queue filter |
| `--page-size` / `--current-page` | No | Pagination (default 10 / 1) |

#### Show SQL Job Status / Detail / Progress

```bash
hcloud dli ShowSqlJobStatus --cli-region={region} --job_id={job_id}
hcloud dli ShowSqlJobDetail --cli-region={region} --job_id={job_id}
hcloud dli ShowSqlJobProgress --cli-region={region} --job_id={job_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--job_id` | Yes | SQL job ID |

#### Cancel SQL Job (risk: double confirm for running jobs)

```bash
hcloud dli CancelSqlJob --cli-region={region} --job_id={job_id}
```

#### Export / Preview SQL Result

```bash
hcloud dli ExportSqlJobResult --cli-region={region} --job_id={job_id} --data_path={obs_path} --data_type={csv|json|parquet} [--compress={gzip|none}]
hcloud dli PreviewSqlJobResult --cli-region={region} --job_id={job_id} [--queue-name={queue_name}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--job_id` | Yes | Completed SQL job ID |
| `--data_path` | Yes (export) | OBS destination path (`s3a://...` or `obs://...`) |
| `--data_type` | Yes (export) | `csv`, `json`, `parquet` |

#### Spark Jobs

```bash
hcloud dli CreateSparkJob --cli-region={region} --file={jar_resource} --className={main_class} \
  [--queue={queue_name}] [--name={job_name}] [--args.1={arg}] [--conf.1={key=value}] [--driver_memory={mem}] [--executor_memory={mem}] [--executor_cores={n}] [--num_executors={n}]
hcloud dli ListSparkJobs --cli-region={region} [--state={starting|running|success|failed|cancelled}] [--job_name={name}] [--queue_name={queue}] [--size={n}] [--from={offset}]
hcloud dli ShowSparkJob --cli-region={region} --batch_id={batch_id}
hcloud dli ShowSparkJobStatus --cli-region={region} --batch_id={batch_id}
hcloud dli ShowSparkJobLog --cli-region={region} --batch_id={batch_id} [--size={n}] [--type={all|driver|executor}]
hcloud dli CancelSparkJob --cli-region={region} --batch_id={batch_id}   # risk: double confirm
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--file` | Yes (create) | JAR resource name already uploaded to DLI resource management |
| `--className` | Yes (create) | Java/Spark main class (capital C) |
| `--batch_id` | Yes (show/cancel) | Spark batch job ID |

### 3. Flink Stream Jobs

```bash
hcloud dli CreateFlinkSqlJob --cli-region={region} --name={job_name} [--queue_name={queue}] [--cu_number={cu}] [--sql={flink_sql}] [--parallel_number={n}] [--smn_topic={topic}]
hcloud dli CreateFlinkJarJob --cli-region={region} --name={job_name} [--queue_name={queue}] [--entrypoint={jar_resource}] [--cu_number={cu}]
hcloud dli ListFlinkJobs --cli-region={region} [--job_type={flink_sql_job|flink_jar_job}] [--status={job_running|job_cancelled|job_failed|...}] [--name={name}] [--queue_name={queue}] [--limit={n}] [--offset={n}]
hcloud dli ShowFlinkJob --cli-region={region} --job_id={job_id}
hcloud dli UpdateFlinkSqlJob --cli-region={region} --job_id={job_id} [--cu_number={cu}] [--sql={flink_sql}] [--parallel_number={n}]
hcloud dli UpdateFlinkJarJob --cli-region={region} --job_id={job_id} [--cu_number={cu}] [--entrypoint={jar_resource}]
hcloud dli BatchRunFlinkJobs --cli-region={region} --job_ids.1={job_id} [--resume_savepoint={true|false}]      # risk: double confirm
hcloud dli BatchStopFlinkJobs --cli-region={region} --job_ids.1={job_id} [--trigger_savepoint={true|false}]     # risk: double confirm
hcloud dli BatchDeleteFlinkJobs --cli-region={region} --job_ids.1={job_id}                                      # risk: double confirm
hcloud dli ShowFlinkMetric --cli-region={region} --job_ids.1={job_id} [--job_ids.2={job_id_2}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes (create) | Flink job name |
| `--job_id` | Yes (show/update) | Flink job ID |
| `--job_ids.[N]` | Yes (batch ops / ShowFlinkMetric) | One or more job IDs, e.g. `--job_ids.1=101 --job_ids.2=102` |

### 4. Database Management

```bash
hcloud dli ListDatabases --cli-region={region} [--keyword={kw}] [--limit={n}] [--offset={n}] [--tags={k=v}]
hcloud dli CreateDatabase --cli-region={region} --database_name={db_name} [--description={desc}]
hcloud dli DeleteDatabase --cli-region={region} --database_name={db_name} [--cascade={true|false}] [--async={true|false}]   # risk: double confirm
hcloud dli UpdateDatabaseOwner --cli-region={region} --database_name={db_name} --new_owner={user_name}
hcloud dli ListDatabaseUsers --cli-region={region} --database_name={db_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--database_name` | Yes | Database name |
| `--new_owner` | Yes (owner update) | New owner username |
| `--cascade` | No (delete) | Delete tables inside the database too (irreversible!) |

### 5. Table Management

```bash
hcloud dli ListTables --cli-region={region} --database_name={db_name} [--table-type={MANAGED|EXTERNAL|VIEW}] [--keyword={kw}] [--with-detail={true|false}] [--page-size={n}] [--current-page={n}]
hcloud dli ShowTable --cli-region={region} --database_name={db_name} --table_name={table_name}
hcloud dli CreateTable --cli-region={region} --database_name={db_name} --table_name={table_name} --data_location={DLI|OBS|VIEW} \
  --columns.1.column_name={col} --columns.1.type={TYPE} [--columns.2.column_name={col2}] [--columns.2.type={TYPE2}] \
  [--data_path={s3a://...}] [--data_type={Parquet|ORC|CSV|JSON|Carbon|Avro}] [--delimiter={c}]
hcloud dli DeleteTable --cli-region={region} --database_name={db_name} --table_name={table_name} [--async={true|false}]   # risk: double confirm
hcloud dli UpdateTableOwner --cli-region={region} --database_name={db_name} --table_name={table_name} --new_owner={user_name}
hcloud dli ListPartitions --cli-region={region} --database_name={db_name} --table_name={table_name} [--limit={n}] [--offset={n}]
hcloud dli PreviewTable --cli-region={region} --database_name={db_name} --table_name={table_name} [--mode={preview|sample}]
hcloud dli ListTableUsers --cli-region={region} --database_name={db_name} --table_name={table_name}
hcloud dli ListTablePrivileges --cli-region={region} --database_name={db_name} --table_name={table_name} --user_name={user}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--database_name` | Yes | Parent database |
| `--table_name` | Yes | Table name |
| `--data_location` | Yes (create) | `DLI`, `OBS`, or `VIEW` |
| `--columns.[N].column_name` / `.type` | Yes (create) | Column schema as indexed pairs |
| `--data_path` | No | Required for OBS tables, must start with `s3a://` |

### 6. Enhanced / Cross-Source Connections

```bash
hcloud dli ListEnhancedConnections --cli-region={region} [--name={name}] [--status={ACTIVE|FAILED}] [--limit={n}] [--offset={n}]
hcloud dli ShowEnhancedConnection --cli-region={region} --connection_id={connection_id}
hcloud dli CreateEnhancedConnection --cli-region={region} --name={conn_name} --dest_vpc_id={vpc_id} --dest_network_id={subnet_id} [--routetable_id={rt_id}]
hcloud dli UpdateEnhancedConnection --cli-region={region} --connection_id={connection_id} [--hosts.1.ip={ip}] [--hosts.1.name={host}]   # full overwrite of host list
hcloud dli DeleteEnhancedConnection --cli-region={region} --connection_id={connection_id}                                            # risk: double confirm
hcloud dli AssociateQueueToEnhancedConnection --cli-region={region} --connection_id={connection_id} --queues.1={queue_name}
hcloud dli DisassociateQueueFromEnhancedConnection --cli-region={region} --connection_id={connection_id}
hcloud dli CreateConnectivityTask --cli-region={region} --queue_name={queue_name} --address={ip_or_domain:port}
hcloud dli ShowConnectivityTask --cli-region={region} --queue_name={queue_name} --task_id={task_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--connection_id` | Yes (show/update/delete) | Enhanced/datasource connection UUID |
| `--dest_vpc_id` / `--dest_network_id` | Yes (create enhanced) | Destination VPC and subnet |
| `--queue_name` / `--address` | Yes (connectivity) | Queue and target address for connectivity test |
| `--hosts.[N].ip` / `.name` | No (update) | New host whitelist; provided host list fully replaces old one |

### 7. Resource Packages

```bash
hcloud dli ListJobResources --cli-region={region} [--kind={jar|pyFile|file}] [--tags={k=v}]
hcloud dli ShowJobResource --cli-region={region} --resource_name={resource_name} [--group={group_name}]
hcloud dli UploadJarJobResources --cli-region={region} --group={group_name} --paths.1={obs://bucket/xx.jar}
hcloud dli UploadPythonFileJobResources --cli-region={region} --group={group_name} --paths.1={obs://bucket/xx.py}
hcloud dli UploadFileJobResources --cli-region={region} --group={group_name} --paths.1={obs://bucket/xx.conf}
hcloud dli DeleteJobResource --cli-region={region} --resource_name={resource_name} [--group={group_name}]                         # risk: double confirm
hcloud dli UpdateJobResourceOwner --cli-region={region} --group_name={group_name} --new_owner={user_name} [--resource_name={name}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--group` | Yes (upload) | Package group name (new group with same name overwrites old) |
| `--paths.[N]` | Yes (upload) | OBS object URL list, e.g. `--paths.1=obs://bkt/x.jar` |
| `--resource_name` | Yes (show/delete) | Resource name |
| `--new_owner` | Yes (owner update) | New owner |

### 8. Global Variables

```bash
hcloud dli ListGlobalVariables --cli-region={region} [--limit={n}] [--offset={n}]
hcloud dli CreateGlobalVariable --cli-region={region} --var_name={var_name} --var_value={var_value} [--is_sensitive={true|false}]
hcloud dli UpdateGlobalVariable --cli-region={region} --var_name={var_name} --var_value={var_value}
hcloud dli DeleteGlobalVariable --cli-region={region} --var_name={var_name}   # risk: double confirm
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--var_name` | Yes | Variable name |
| `--var_value` | Yes (create/update) | Variable value |
| `--is_sensitive` | No | Mark as sensitive (hidden in job details) |

### 9. Job Templates

```bash
hcloud dli ListSqlJobTemplates --cli-region={region} [--keyword={kw}]
hcloud dli CreateSqlJobTemplate --cli-region={region} --sql_name={template_name} --sql={sql_body} [--description={desc}] [--group={group}]
hcloud dli UpdateSqlJobTemplate --cli-region={region} --sql_id={template_id} [--sql_name={name}] [--sql={sql_body}] [--description={desc}]
hcloud dli BatchDeleteSqlJobTemplates --cli-region={region} --sql_ids.1={template_id}                                            # risk: double confirm
hcloud dli ListFlinkSqlJobTemplates --cli-region={region} [--name={name}] [--limit={n}] [--offset={n}]
hcloud dli CreateFlinkSqlJobTemplate --cli-region={region} --name={template_name} [--sql_body={flink_sql}] [--job_type={flink_sql_job|flink_jar_job}] [--desc={desc}]
hcloud dli UpdateFlinkSqlJobTemplate --cli-region={region} --template_id={template_id} [--name={name}] [--sql_body={flink_sql}] [--desc={desc}]
hcloud dli DeleteFlinkSqlJobTemplate --cli-region={region} --template_id={template_id}                                         # risk: double confirm
hcloud dli ListSparkJobTemplates --cli-region={region} [--type={1|2}] [--page-size={n}] [--current-page={n}]
hcloud dli CreateSparkJobTemplate --cli-region={region} --name={template_name} --type={1|2} [--description={desc}] [--group={group}] [--language={en|zh}]
hcloud dli UpdateSparkJobTemplate --cli-region={region} --template_id={template_id} --name={template_name} [--description={desc}] [--group={group}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--sql_name` / `--name` | Yes (create) | Template name |
| `--sql_ids.[N]` | Yes (batch delete) | SQL template IDs |
| `--template_id` / `--sql_id` | Yes (update/delete) | Template ID |

### 10. Privileges & Patrol

```bash
hcloud dli ListAuthorizationPrivileges --cli-region={region} --object={object}
hcloud dli RunAuthorizationAction --cli-region={region} --action={grant|revoke} [--user_name={user}] [--privileges.1.object={object}] [--privileges.1.privileges.1={privilege}]
hcloud dli RunDataAuthorizationAction --cli-region={region} --action={grant|revoke} --user_name={user}          # data-level auth
hcloud dli RegisterAuthorizedQueue --cli-region={region} --queue_name={queue_name} --user_name={user} --action={grant|revoke}
hcloud dli ShowEnhancedConnectionPrivilege --cli-region={region} --connection_id={connection_id}
hcloud dli ListElasticResourcePools --cli-region={region} [--name={name}] [--status={AVAILABLE|SCALING|CREATING|FAILED}] [--limit={n}]
hcloud dli UpdateElasticResourcePool --cli-region={region} --elastic_resource_pool_name={pool_name} [--min_cu={n}] [--max_cu={n}] [--description={desc}]   # risk: double confirm for shrinking
hcloud dli ListElasticResourcePoolScaleRecords --cli-region={region} --elastic_resource_pool_name={pool_name} [--status={SUCCESS|FAIL}] [--limit={n}]
hcloud dli ShowQuota --cli-region={region}
hcloud dli ShowDliAgency --cli-region={region}
hcloud dli ShowFlinkMetric --cli-region={region} --job_ids.1={job_id} [--job_ids.2={job_id_2}]
hcloud dli ListCatalogs --cli-region={region} [--limit={n}] [--offset={n}]
hcloud dli ShowCatalog --cli-region={region} --catalog_name={catalog_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--object` | Yes (list privileges) | Authorization object to inspect |
| `--action` | Yes (auth) | `grant` or `revoke` |
| `--user_name` | Yes (data auth / register) | Target user |
| `--elastic_resource_pool_name` | Yes (pool ops) | Elastic resource pool name |

## Parameter Confirmation

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, auto-filled by KooCLI profile; explicitly pass `--cli-region={region}` |
| `--project_id` | Yes (auto) | Project ID, auto-filled by KooCLI (parent project of the region) |
| `--queue_name` | Depends | Queue operations; job submit routing |
| `--job_id` / `--batch_id` | Depends | SQL job ID / Spark batch ID / Flink job ID |
| `--database_name` | Depends | Database-scoped operations |
| `--table_name` | Depends | Table-scoped operations |
| `--connection_id` | Depends | Connection-scoped operations |
| `--user_name` | Depends | Owner change / authorization operations |

Common conventions:

- Indexed/array parameters use `.[N]` suffixes (`--paths.1=...`, `--job_ids.1=...`); booleans accept `true`/`false`; time params use RFC3339.
- OBS paths use `obs://bucket/key`, except `CreateTable --data_path` which requires `s3a://`.

## KooCLI Command Format Standard

Generic command template (do not execute as-is — replace `<service>`, `<Operation>` and parameters):

> `hcloud <service> <Operation> --cli-region=<region> [--key=value ...]`

| Feature | Standard |
|---------|----------|
| Service name | `dli` (metadata case; `hcloud dli <Operation>` works, KooCLI shows `DLI`) |
| Operation name | PascalCase, e.g. `ListQueues`, `CreateSqlJob`, `BatchStopFlinkJobs` |
| Region | `--cli-region=<value>` always included |
| Simple / indexed parameter | `--key=value`, e.g. `--queue_name=myqueue`; indexed `--key.1=value1`, e.g. `--job_ids.1=101` |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for DLI operations
- `references/cli-installation-guide.md` — hcloud CLI installation & AK/SK configuration
- `references/dli-operation-catalog.md` — Full DLI operation catalog with parameter tables
- `references/common-workflows.md` — Scenario-based workflow recipes
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/verification-method.md` — Verification method details
- `references/acceptance-criteria.md` — Acceptance criteria

## Best Practices

- Confirm the queue exists (`ListQueues`) before submitting jobs; never submit to an unknown queue.
- Keep output small: paginate with `--limit`/`--offset` or `--page-size`/`--current-page`; use status filters (`--job-status`, `--status`) for targeted troubleshooting.
- Merge multiple `List*` outputs into one structured markdown report; mask AK/SK and sensitive variable values (`--is_sensitive` variables render masked).
- **Always** present high-risk commands to the user with expected impact and wait for explicit confirmation (see Constraints).
- When a connectivity check fails, verify queue binding (`AssociateQueueToEnhancedConnection`), security group, and VPC route before recreating the connection.
- CU patrol: compare `ShowQuota` used vs quota; flag > 80%; use `ListElasticResourcePoolScaleRecords` before suggesting scaling changes.

## Verification Method

```bash
hcloud dli ListQueues --cli-region={region} --queue_type=all        # read smoke test
hcloud dli ListDatabases --cli-region={region} --limit=5            # metadata read smoke test
hcloud dli ShowQuota --cli-region={region}                          # quota read smoke test
```

See `references/verification-method.md` for the detailed verification matrix.