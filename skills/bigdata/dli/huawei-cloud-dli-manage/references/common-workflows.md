# Common Workflows

Scenario recipes for the most frequent DLI operations. All commands assume
`{region}` and auto-filled project; filters are examples — adjust to the actual
environment.

## W1. Full Resource Patrol (日常巡检)

```bash
# Queue inventory
hcloud dli ListQueues --cli-region={region} --queue_type=all --with-charge-info
# Elastic pools + recent scaling
hcloud dli ListElasticResourcePools --cli-region={region} --limit=50
hcloud dli ListElasticResourcePoolScaleRecords --cli-region={region} --elastic_resource_pool_name={pool} --limit=20
# Running/failed jobs
hcloud dli ListSqlJobs --cli-region={region} --job-status=running --page-size=20
hcloud dli ListFlinkJobs --cli-region={region} --limit=20
# CU quota and agency
hcloud dli ShowQuota --cli-region={region}
hcloud dli ShowDliAgency --cli-region={region}
```

Report: inventory table (queue name, CU, type, status), job counts by status,
CU used/quota with > 80% flags, connectivity anomalies, cleanup proposals.

## W2. SQL Job Failure Troubleshooting (SQL作业排查)

```bash
# 1. Find failed jobs
hcloud dli ListSqlJobs --cli-region={region} --job-status=failed --page-size=10
# 2. Failure details
hcloud dli ShowSqlJobStatus --cli-region={region} --job_id={job_id}
hcloud dli ShowSqlJobDetail --cli-region={region} --job_id={job_id}
# 3. If job is stuck, check progress
hcloud dli ShowSqlJobProgress --cli-region={region} --job_id={job_id}
```

Common failure classes: SQL syntax (check `message`/`exception` in detail),
queue missing (confirm `ListQueues`), permission denied (check
`ListAuthorizationPrivileges`), resource quota (check `ShowQuota`).

## W3. Spark Job Troubleshooting

```bash
hcloud dli ListSparkJobs --cli-region={region} --state=failed --size=10
hcloud dli ShowSparkJob --cli-region={region} --batch_id={batch_id}
hcloud dli ShowSparkJobStatus --cli-region={region} --batch_id={batch_id}
hcloud dli ShowSparkJobLog --cli-region={region} --batch_id={batch_id} --type=all --size=200
```

## W4. Flink Job Start/Stop with Confirmation (流作业启停)

```bash
hcloud dli ListFlinkJobs --cli-region={region} --status=job_running --limit=20
hcloud dli ShowFlinkJob --cli-region={region} --job_id={job_id}
# --- double confirmation required before the next two commands ---
hcloud dli BatchRunFlinkJobs --cli-region={region} --job_ids.1={job_id}
hcloud dli BatchStopFlinkJobs --cli-region={region} --job_ids.1={job_id} --trigger_savepoint=true
# verify
hcloud dli ShowFlinkJob --cli-region={region} --job_id={job_id}
```

## W5. Upload a JAR and Submit a Spark Job

```bash
# 1. Upload resource (OBS URL)
hcloud dli UploadJarJobResources --cli-region={region} --group={group_name} --paths.1={obs://bucket/app.jar}
# 2. Verify upload
hcloud dli ListJobResources --cli-region={region} --kind=jar
# 3. Submit Spark batch job
hcloud dli CreateSparkJob --cli-region={region} --file={resource_name} --className={main_class} \
  --queue={queue_name} --name={job_name} --driver_memory=2G --executor_memory=2G --executor_cores=1
```

## W6. Cross-Source Connectivity Check

```bash
hcloud dli ListEnhancedConnections --cli-region={region} --limit=20
hcloud dli CreateConnectivityTask --cli-region={region} --queue_name={queue_name} --address={target_ip:port}
hcloud dli ShowConnectivityTask --cli-region={region} --queue_name={queue_name} --task_id={task_id}
```

If failed: re-check queue binding
(`AssociateQueueToEnhancedConnection --connection_id={conn_id}`), security
group/route of the destination VPC, then re-test.

## W7. Owner/Privilege Change

```bash
hcloud dli UpdateTableOwner --cli-region={region} --database_name={db} --table_name={table} --new_owner={user}
hcloud dli UpdateDatabaseOwner --cli-region={region} --database_name={db} --new_owner={user}
hcloud dli RunAuthorizationAction --cli-region={region} --action=grant --user_name={user} --object_name={obj} --object_type={database|table|queue} --privileges.1={SELECT|INSERT|...}
hcloud dli RegisterAuthorizedQueue --cli-region={region} --queue_name={queue} --user_name={user} --action=grant
```

## W8. Template Lifecycle

```bash
hcloud dli CreateSqlJobTemplate --cli-region={region} --sql_name={name} --sql={select 1}
hcloud dli ListSqlJobTemplates --cli-region={region}
hcloud dli UpdateSqlJobTemplate --cli-region={region} --sql_id={id} --description={new_desc}
hcloud dli BatchDeleteSqlJobTemplates --cli-region={region} --sql_ids.1={id}   # double confirm
```

## Safety Rules for All Workflows

- Destructive/impactful commands (delete, cancel, stop, scale_in, owner
  changes) require the agent to display the exact command + impact and obtain
  explicit user confirmation.
- Export job results only to user-approved OBS paths.
- Never submit `INSERT OVERWRITE` / `DELETE` / `UPDATE` / `DROP` SQL against
  business tables autonomously.