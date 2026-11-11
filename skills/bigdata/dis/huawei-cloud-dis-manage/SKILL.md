---
name: huawei-cloud-dis-manage
description: >
  Manages Huawei Cloud DIS (Data Ingestion Service) full lifecycle: stream
  channel create/list/show/delete, retention and data-type updates, partition
  scale-up/scale-down, dump (transfer) tasks to OBS/DWS/DLI/MRS/CloudTable with
  start/stop/delete, real-time ingestion metrics for streams and partitions,
  consumer apps, cursors, checkpoints, data upload/consumption verification,
  stream authorization policies and resource tags. Produces structured inventory
  and monitoring reports; all mutating operations require explicit user
  confirmation. Triggers include: "DIS通道管理", "DIS数据接入", "创建DIS通道",
  "查询DIS通道", "删除DIS通道", "DIS分区扩容", "DIS转储任务", "DIS监控指标",
  "DIS消费组", "DIS数据上传", "DIS日常巡检", "DIS troubleshooting",
  "Data Ingestion Service", "DIS stream", "create DIS stream", "DIS dump task",
  "DIS metrics", "DIS partition scale", "ingest data into DIS".
tags: [huawei-cloud, dis, data-ingestion, bigdata, streaming]
---

# Huawei Cloud DIS Stream Management Skill

## Overview

This Skill provides a full-lifecycle operations toolkit for Huawei Cloud DIS
(Data Ingestion Service, 数据接入服务) using the `dis` service of the hcloud
CLI. It covers six capability groups:

1. **Stream channels** — `ListStreams`, `ShowStream`, `CreateStream`, `DeleteStream`, `UpdateStream`, `UpdatePartitionCount`
2. **Dump (transfer) tasks** — `CreateObsTransferTask`, `CreateDwsTransferTask`, `CreateDliTransferTask`, `CreateMrsTransferTask`, `CreateCloudTableTransferTask`, `ListTransferTasks`, `ShowTransferTask`, `BatchStartTransferTask`, `BatchStopTransferTask`, `DeleteTransferTask`
3. **Monitoring** — `ShowStreamMetrics`, `ShowPartitionMetrics`, `ShowConsumerState`
4. **Consumption apps and checkpoints** — `CreateApp`, `ListApp`, `ShowApp`, `DeleteApp`, `CommitCheckpoint`, `ShowCheckpoint`, `DeleteCheckpoint`
5. **Data verification** — `SendRecords`, `ShowCursor`, `ConsumeRecords`
6. **Governance** — `CreatePolicies`, `ListPolicies`, stream tags (`CreateTag`, `BatchCreateTags`, `ListTags`, `ShowStreamTags`, `DeleteTag`, `BatchDeleteTags`, `ListResourcesByTags`)

Every operation is executed through KooCLI against the DIS v2/v3 REST API; the
verified operation catalog (method, path, required parameters) is in
`references/dis-operation-catalog.md`.

### Important Constraints

| Constraint | Policy |
|------------|--------|
| High-risk operations | **Double confirmation required** before `DeleteStream`, `DeleteTransferTask`, `BatchStopTransferTask`/`BatchStartTransferTask` on production streams, `DeleteApp`, `DeleteCheckpoint`, `UpdatePartitionCount` scale-down, `UpdateStream` retention/data-type changes, and `CreatePolicies`/`DeleteTag`. Never delete streams or dump tasks during a patrol — report candidates and wait for confirmation |
| Data privacy | `SendRecords` accepts Base64-encoded payloads. Never include production customer data in test records; use synthetic payloads |
| Credentials | AK/SK are read from the user's KooCLI profile or environment. Never hardcode, print, or extract credentials; mask them in every report |
| Scope | All operations stay within DIS resources; no OBS object content changes, no IAM policy changes, no changes to DWS/DLI/MRS/CloudTable internal data |

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

1. **hcloud CLI** installed (KooCLI 3.x or later) and authenticated with a valid
   AK/SK profile. Installation and configuration: `references/cli-installation-guide.md`.
2. **IAM permissions**: DIS read permissions for queries; DIS write permissions
   for create/update/delete/scale/policy actions. See `references/iam-policies.md`.
3. **Region and project**: DIS is regional. Pass `--cli-region={region}` on every
   command; `--project_id` is auto-filled from the profile (parent project of the
   selected region) and normally omitted.
4. **Transfer task dependencies**: an agency (`dis_admin_agency` or an equivalent
   user-created agency granting DIS access) plus the destination resource
   (OBS bucket, DWS cluster/table, DLI database/table, MRS cluster with
   non-Kerberos auth, or CloudTable cluster/table).
5. **Consumer app**: create an app (`CreateApp`) before committing checkpoints.

- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade); if a new shell reports `command not found`, run `export PATH="$HOME/.local/bin:$PATH"`.
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`
## Workflow

### Scenario 1: Stream Inventory and Health Patrol (巡检)

```
ListStreams --limit -> stream names; ShowStream per stream -> status, partitions, retention, data type
ListTransferTasks per stream -> dump task state; ShowStreamMetrics -> ingest/egress rate and latency
Output: structured patrol report (inventory + unhealthy streams + failed dump tasks + cleanup proposals)
```

### Scenario 2: Create a Stream Channel

```
ListStreams -> verify the name is free (DIS stream names are unique per tenant/region)
CreateStream --stream_name --partition_count --stream_type --data_type --data_duration
ShowStream -> verify status RUNNING and partition count
Output: created stream snapshot (name, id, partitions, retention, type)
```

Partition sizing: one partition is the base throughput unit; COMMON streams are
1 Mbit/s each and ADVANCED streams 5 Mbit/s each. Default quota is 50 COMMON or
10 ADVANCED partitions per account; request a quota increase for larger streams.

### Scenario 3: Capacity Changes (扩容/缩容)

```
ShowStream -> current partition count and status
UpdatePartitionCount --target_partition_count -> scale-up or scale-down (max 5 changes/hour)
UpdateStream -> retention (24-72 h), data type, auto-scaling bounds
ShowStream -> verify the new partition count
```

### Scenario 4: Configure a Dump Task (数据转储)

```
ListTransferTasks -> existing tasks (avoid duplicate task names)
Create<Destination>TransferTask -> choose OBS, DWS, DLI, MRS, or CLOUDTABLE descriptor
ListTransferTasks / ShowTransferTask -> verify task state
BatchStartTransferTask / BatchStopTransferTask -> start or pause after confirmation
```

Destination selection: use `CreateObsTransferTask` for object storage archives,
`CreateDwsTransferTask` for DWS tables, `CreateDliTransferTask` for DLI tables
(data location must be DLI), `CreateMrsTransferTask` for MRS HDFS (non-Kerberos),
and `CreateCloudTableTransferTask` for CloudTable HBase/OpenTSDB.

### Scenario 5: Real-Time Ingestion Monitoring (实时监控)

```
ShowStreamMetrics --label_list -> put/get bytes, records, latency, success requests, throttling
ShowPartitionMetrics --partition_id --label_list -> per-partition throughput
ShowConsumerState --checkpoint_type=LAST_READ -> committed sequence numbers per partition
Output: throughput table, latency trend, throttling evidence, and consumer lag assessment
```

Backlog: compare the latest sequence number (from a `LATEST` cursor via
`ShowCursor`) with the checkpointed number from `ShowConsumerState`.

### Scenario 6: Data Path Verification (数据上传/消费验证)

```
CreateApp -> create a dedicated verification app if absent
SendRecords --records.1.data=<base64> --stream_name -> upload synthetic record
ShowCursor --cursor-type=TRIM_HORIZON -> obtain a cursor (valid 5 minutes)
ConsumeRecords --partition-cursor -> read the record back
CommitCheckpoint -> persist the consumption position (optional)
Output: end-to-end verification result (write latency, record count, payload hash)
```

### Scenario 7: Authorization and Tags (权限与标签)

```
CreatePolicies --action_type --effect=accept --principal_name --stream_id -> grant put/get/getStreamInfo
ListPolicies -> verify grants
CreateTag / BatchCreateTags / ShowStreamTags / ListTags -> tag governance
ListResourcesByTags --action=filter -> find streams by tag
```

### Safety Gate

Before any high-risk command, present the exact command, target, and impact to
the user and wait for explicit confirmation. Never batch-execute destructive
commands; mask AK/SK and DWS passwords in outputs and reports.

## Core Commands

All commands use `hcloud dis <Operation>`. `--cli-region` is always included;
`--project_id` is auto-filled by KooCLI and omitted below. The full operation
catalog with every parameter lives in `references/dis-operation-catalog.md`.

### 1. Stream Channels

#### List Streams

> **⚠️ Mandatory: every `hcloud dis <Operation>` business command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-dis-manage -- ` — bare `hcloud dis` calls are strictly forbidden.** Lifecycle commands used only to install or configure KooCLI (`hcloud version`, `hcloud update`, `hcloud configure ...`) are setup steps, not DIS business operations, and are exempt in `references/cli-installation-guide.md`.

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListStreams --cli-region={region} [--limit={limit}] [--start_stream_name={start_stream_name}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, always passed explicitly |
| `--limit` | No | Max streams returned in one call |
| `--start_stream_name` | No | Pagination cursor: last stream name of the previous page (omitted on page 1) |

#### Show Stream

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowStream --cli-region={region} --stream_name={stream_name} [--limit_partitions={limit}] [--start_partitionId={partition_id}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Stream name to inspect |
| `--limit_partitions` | No | Max partitions returned |
| `--start_partitionId` | No | Partition pagination cursor |

#### Create Stream

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateStream --cli-region={region} --stream_name={stream_name} --partition_count={partition_count} [--stream_type={COMMON|ADVANCED}] [--data_type={BLOB|JSON|CSV}] [--data_duration={data_duration}] [--compression_format={snappy|gzip|zip}] [--auto_scale_enabled={true|false}] [--auto_scale_max_partition_count={max}] [--auto_scale_min_partition_count={min}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | 1-64 chars: letters, digits, underscores, hyphens |
| `--partition_count` | Yes | Number of partitions (base throughput unit) |
| `--stream_type` | No | `COMMON` (1 Mbit/s per partition) or `ADVANCED` (5 Mbit/s) |
| `--data_type` | No | `BLOB` (default), `JSON`, or `CSV` |
| `--data_duration` | No | Retention hours, 24-72 (default per service) |
| `--compression_format` | No | `snappy`, `gzip`, or `zip`; none by default |
| `--auto_scale_enabled` / `--auto_scale_max_partition_count` / `--auto_scale_min_partition_count` | No | Auto-scaling switch and bounds |

#### Update Stream

> **KooCLI 7.3.12 caveat: do NOT pass `--stream_name` on the command line.** The metadata declares `--stream_name` twice (path and body), so `hcloud dis UpdateStream ... --stream_name={name}` fails with `The following parameters are required: stream_name`, and passing it twice fails with `Duplicate parameter: stream_name`. Use the tested `--cli-jsonInput` path/body form below instead.

```bash
cat > dis-update-stream.json <<'JSON'
{"path":{"project_id":"{project_id}","stream_name":"{stream_name}"},"body":{"stream_name":"{stream_name}","data_duration":24}}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdateStream --cli-region={region} --cli-jsonInput=./dis-update-stream.json
```

`project_id` must be present inside the `path` block because `--cli-jsonInput` disables KooCLI's automatic path filling; copy it from the console or the active account. Add only the optional `body` keys you intend to change. Preview the generated request with `--dryrun` before the real call.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `path.project_id` | Yes | Project ID (not auto-filled with `--cli-jsonInput`) |
| `path.stream_name` / `body.stream_name` | Yes | Stream to update (declared in both path and body) |
| `body.data_duration` / `data_type` / `data_schema` / `auto_scale_*` | No | Retention hours, data type/schema, auto-scaling switch and bounds |

#### Update Partition Count (risk: confirm scale-down)

> **KooCLI 7.3.12 caveat: same duplicate `--stream_name` declaration as `UpdateStream`.** The plain `--stream_name` form is rejected; use the `--cli-jsonInput` form below.

```bash
cat > dis-update-partition-count.json <<'JSON'
{"path":{"project_id":"{project_id}","stream_name":"{stream_name}"},"body":{"stream_name":"{stream_name}","target_partition_count":{target_partition_count}}}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdatePartitionCount --cli-region={region} --cli-jsonInput=./dis-update-partition-count.json
```

Preview with `--dryrun` first: the generated request must be `PUT https://dis.{region}.myhuaweicloud.com/v2/{project_id}/streams/{stream_name}`.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `path.project_id` | Yes | Project ID (not auto-filled with `--cli-jsonInput`) |
| `path.stream_name` / `body.stream_name` | Yes | Stream whose partitions change |
| `body.target_partition_count` | Yes | Target count (> 0); greater = scale-up, smaller = scale-down. Max 5 changes per hour |

#### Delete Stream (risk: double confirm)

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis DeleteStream --cli-region={region} --stream_name={stream_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Stream to delete (irreversible; check for active dump tasks and consumers first) |

### 2. Dump (Transfer) Tasks

#### List / Show Transfer Tasks

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListTransferTasks --cli-region={region} --stream_name={stream_name}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowTransferTask --cli-region={region} --stream_name={stream_name} --task_name={task_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Parent stream |
| `--task_name` | Yes (show/delete) | Dump task name |

#### Create OBS Transfer Task

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateObsTransferTask --cli-region={region} --stream_name={stream_name} --destination_type=OBS --obs_destination_descriptor.task_name={task_name} --obs_destination_descriptor.obs_bucket_path={obs_bucket_path} [--obs_destination_descriptor.agency_name={agency_name}] [--obs_destination_descriptor.deliver_time_interval={seconds}] [--obs_destination_descriptor.destination_file_type={text|parquet|carbon}] [--obs_destination_descriptor.file_prefix={file_prefix}] [--obs_destination_descriptor.partition_format={yyyy/MM/dd/HH/mm}] [--obs_destination_descriptor.consumer_strategy={LATEST|TRIM_HORIZON}] [--obs_destination_descriptor.record_delimiter={delimiter}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Source stream |
| `--destination_type` | Yes | Must be `OBS` for this operation |
| `--obs_destination_descriptor.task_name` | Yes (logical) | Task name, 1-64 chars |
| `--obs_destination_descriptor.obs_bucket_path` | Yes (logical) | Target OBS bucket/path |
| `--obs_destination_descriptor.agency_name` / `consumer_strategy` | No | DIS agency (`dis_admin_agency` or custom) and `LATEST`/`TRIM_HORIZON` |
| `--obs_destination_descriptor.destination_file_type` | No | `text` (default), `parquet`, `carbon` (parquet/carbon require JSON source) |
| `--obs_destination_descriptor.file_prefix` / `partition_format` / `deliver_time_interval` | No | Object directory layout and dump interval |

#### Create DWS Transfer Task

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateDwsTransferTask --cli-region={region} --stream_name={stream_name} --destination_type=DWS --dws_destination_descriptor.task_name={task_name} --dws_destination_descriptor.dws_cluster_id={dws_cluster_id} --dws_destination_descriptor.dws_database_name={dws_database} --dws_destination_descriptor.dws_table_name={dws_table} --dws_destination_descriptor.user_name={db_user} --dws_destination_descriptor.user_password={db_password} --dws_destination_descriptor.obs_bucket_path={obs_bucket_path} [--dws_destination_descriptor.kms_user_key_id={kms_key_id}] [--dws_destination_descriptor.dws_schema={schema}] [--dws_destination_descriptor.dws_table_columns={c1,c2}] [--dws_destination_descriptor.dws_delimiter={delimiter}] [--dws_destination_descriptor.retry_duration={seconds}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` / `--destination_type=DWS` | Yes | Source stream and task type |
| `--dws_destination_descriptor.task_name` / `dws_cluster_id` | Yes (logical) | Task name and target DWS cluster |
| `--dws_destination_descriptor.dws_database_name` / `dws_table_name` | Yes (logical) | Target database and table |
| `--dws_destination_descriptor.user_name` / `user_password` / `obs_bucket_path` | Yes (logical) | DWS account (never log the password) and OBS staging bucket |
| `--dws_destination_descriptor.kms_user_key_id` / `kms_user_key_name` | No | KMS key used to encrypt the DB password |

#### Create DLI / MRS / CloudTable Transfer Tasks

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateDliTransferTask --cli-region={region} --stream_name={stream_name} --destination_type=DLI --dli_destination_descriptor.task_name={task_name} --dli_destination_descriptor.dli_database_name={dli_database} --dli_destination_descriptor.dli_table_name={dli_table} --dli_destination_descriptor.obs_bucket_path={obs_bucket_path} [--dli_destination_descriptor.agency_name={agency_name}] [--dli_destination_descriptor.retry_duration={seconds}]
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateMrsTransferTask --cli-region={region} --stream_name={stream_name} --destination_type=MRS --mrs_destination_descriptor.task_name={task_name} --mrs_destination_descriptor.mrs_cluster_id={mrs_cluster_id} --mrs_destination_descriptor.mrs_hdfs_path={hdfs_path} --mrs_destination_descriptor.obs_bucket_path={obs_bucket_path} [--mrs_destination_descriptor.agency_name={agency_name}] [--mrs_destination_descriptor.hdfs_prefix_folder={folder}]
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateCloudTableTransferTask --cli-region={region} --stream_name={stream_name} --destination_type=CLOUDTABLE --cloudtable_destination_descriptor.task_name={task_name} --cloudtable_destination_descriptor.cloudtable_cluster_id={cluster_id} --cloudtable_destination_descriptor.cloudtable_table_name={table_name} --cloudtable_destination_descriptor.obs_backup_bucket_path={obs_bucket_path} [--cloudtable_destination_descriptor.backup_file_prefix={prefix}] [--cloudtable_destination_descriptor.cloudtable_row_key_delimiter={delimiter}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` / `--destination_type` | Yes | Stream and `DLI`, `MRS`, or `CLOUDTABLE` |
| `--dli_destination_descriptor.dli_database_name` / `dli_table_name` | Yes (logical) | DLI target; table must have a DLI data location |
| `--mrs_destination_descriptor.mrs_cluster_id` / `mrs_hdfs_path` | Yes (logical) | MRS cluster and HDFS path (non-Kerberos only) |
| `--cloudtable_destination_descriptor.cloudtable_cluster_id` / `cloudtable_table_name` | Yes (logical) | CloudTable HBase target and staging/backup OBS location (`--*_destination_descriptor.obs_bucket_path` / `obs_backup_bucket_path`) |

#### Start / Stop Transfer Tasks (risk: confirm on production)

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis BatchStartTransferTask --cli-region={region} --stream_name={stream_name} --action=start --tasks.1.id={task_id}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis BatchStopTransferTask --cli-region={region} --stream_name={stream_name} --action=stop --tasks.1.id={task_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Parent stream |
| `--action` | Yes | `start` or `stop` |
| `--tasks.[N].id` | Yes | Dump task ID(s); indexed form `--tasks.1.id=`, `--tasks.2.id=` |

#### Delete Transfer Task (risk: double confirm)

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis DeleteTransferTask --cli-region={region} --stream_name={stream_name} --task_name={task_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Parent stream |
| `--task_name` | Yes | Task to delete |

### 3. Monitoring

#### Stream Metrics

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowStreamMetrics --cli-region={region} --stream_name={stream_name} --start_time={start_time} --end_time={end_time} [--label={label}] [--label_list={label1,label2}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Stream to monitor |
| `--start_time` / `--end_time` | Yes | 10-digit Unix timestamps (seconds) |
| `--label` | No | One of `total_put_bytes_per_stream`, `total_get_bytes_per_stream`, `total_put_records_per_stream`, `total_get_records_per_stream`, `total_put_req_latency`, `total_get_req_latency`, `total_put_req_suc_per_stream`, `total_get_req_suc_per_stream`, `traffic_control_put`, `traffic_control_get` |
| `--label_list` | No | Comma-separated labels; takes precedence over `--label` |

#### Partition Metrics

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowPartitionMetrics --cli-region={region} --stream_name={stream_name} --partition_id={partition_id} --start_time={start_time} --end_time={end_time} [--label_list={label1,label2}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--partition_id` | Yes | `0`, `1`, ... or `shardId-0000000000` |
| `--label_list` | No | `total_put_bytes_per_partition`, `total_get_bytes_per_partition`, `total_put_records_per_partition`, `total_get_records_per_partition` |

#### Consumer State

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowConsumerState --cli-region={region} --app_name={app_name} --stream_name={stream_name} --checkpoint_type=LAST_READ [--limit={limit}] [--start_partition_id={partition_id}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--app_name` | Yes | Consumer app name |
| `--stream_name` | Yes | Stream being consumed |
| `--checkpoint_type` | Yes | Only `LAST_READ` is supported |
| `--limit` | No | Partitions returned, 1-1000 (default 100) |
| `--start_partition_id` | No | Partition pagination cursor |

### 4. Consumption Apps and Checkpoints

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateApp --cli-region={region} --app_name={app_name}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListApp --cli-region={region} [--stream_name={stream_name}] [--limit={limit}] [--start_app_name={start_app_name}]
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowApp --cli-region={region} --app_name={app_name}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis DeleteApp --cli-region={region} --app_name={app_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--app_name` | Yes (create/show/delete) | App name, 1-200 chars: letters, digits, hyphens, underscores |
| `--stream_name` | No (list) | Filter apps by stream |
| `--start_app_name` / `--limit` | No (list) | Pagination |

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CommitCheckpoint --cli-region={region} --app_name={app_name} --stream_name={stream_name} --checkpoint_type=LAST_READ --partition_id={partition_id} --sequence_number={sequence_number} [--metadata={metadata}]
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowCheckpoint --cli-region={region} --app_name={app_name} --stream_name={stream_name} --checkpoint_type=LAST_READ --partition_id={partition_id}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis DeleteCheckpoint --cli-region={region} --app_name={app_name} --stream_name={stream_name} --checkpoint_type=LAST_READ [--partition_id={partition_id}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--app_name` / `--stream_name` / `--checkpoint_type` | Yes | App, stream, and `LAST_READ` |
| `--partition_id` | Yes (commit/show) | Partition identifier |
| `--sequence_number` | Yes (commit) | Sequence number to persist |
| `--metadata` | No (commit) | Up to 1,000 chars |

### 5. Data Path Verification

#### Send Records (data upload)

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis SendRecords --cli-region={region} --stream_name={stream_name} --records.1.data={base64_data} [--records.1.partition_id={partition_id}] [--records.1.partition_key={partition_key}] [--stream_id={stream_id}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_name` | Yes | Target stream (or use `--stream_id` for authorized streams) |
| `--records.[N].data` | Yes | Base64-encoded payload, e.g. `ZGF0YQ==` for `data` |
| `--records.[N].partition_id` / `partition_key` | No | Explicit partition or hash key routing |
| `--stream_id` | No | Required when writing to an authorized stream |

#### Show Cursor / Consume Records

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowCursor --cli-region={region} --stream-name={stream_name} --partition-id={partition_id} [--cursor-type={AT_SEQUENCE_NUMBER|AFTER_SEQUENCE_NUMBER|TRIM_HORIZON|LATEST|AT_TIMESTAMP}] [--starting-sequence-number={sequence_number}] [--timestamp={timestamp_ms}]
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ConsumeRecords --cli-region={region} --partition-cursor={partition_cursor} [--max_fetch_bytes={max_fetch_bytes}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream-name` / `--partition-id` | Yes (cursor) | Stream and partition |
| `--cursor-type` | No | Default `AT_SEQUENCE_NUMBER`; `TRIM_HORIZON` reads from earliest valid record, `LATEST` from newest |
| `--starting-sequence-number` / `--timestamp` | No | Position for sequence-number / timestamp cursor types |
| `--partition-cursor` | Yes (consume) | Cursor from `ShowCursor`; valid for 5 minutes |
| `--max_fetch_bytes` | No | Max bytes per consume request |

### 6. Authorization Policies and Tags

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreatePolicies --cli-region={region} --stream_name={stream_name} --action_type={putRecords|getRecords|getStreamInfo} --effect=accept --principal_name={domainName.userName} --stream_id={stream_id}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListPolicies --cli-region={region} --stream_name={stream_name}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--action_type` | Yes | `putRecords`, `getRecords`, or `getStreamInfo` |
| `--effect` | Yes | Only `accept` is supported |
| `--principal_name` | Yes | `domainName.*` for a tenant or `domainName.userName` for a sub-user; comma-separated for multiple |
| `--stream_id` | Yes | Stream unique ID (from `ShowStream`) |

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateTag --cli-region={region} --stream_id={stream_id} --tag.key={tag_key} --tag.value={tag_value}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis BatchCreateTags --cli-region={region} --stream_id={stream_id} --action=create --tags.1.key={tag_key} --tags.1.value={tag_value}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListTags --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowStreamTags --cli-region={region} --stream_id={stream_id}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis DeleteTag --cli-region={region} --stream_id={stream_id} --key={tag_key}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis BatchDeleteTags --cli-region={region} --stream_id={stream_id} --action=delete --tags.1.key={tag_key}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListResourcesByTags --cli-region={region} --action={filter|count} [--tags.1.key={tag_key}] [--tags.1.values.1={tag_value}] [--limit={limit}] [--offset={offset}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--stream_id` | Yes (tag operations) | Stream unique ID |
| `--tag.key` / `--tag.value` | Yes (single tag create) | Tag pair |
| `--tags.[N].key` / `--tags.[N].value` | Yes (batch) | Indexed tag pairs |
| `--key` | Yes (delete) | Tag key to delete |
| `--action` | Yes (batch/list) | `create`, `delete`, `filter`, or `count` |

## Parameter Confirmation

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region; always passed explicitly on every command |
| `--project_id` | Yes (auto) | Auto-filled by KooCLI from the profile/region |
| `--stream_name` / `--stream_id` | Depends | Stream identity (`--stream_id` for tags/policies/authorized upload) |
| `--partition_count` / `--target_partition_count` | Yes (create / scale) | Initial / target partitions |
| `--partition_id` | Depends | `N` or `shardId-000000000N` |
| `--task_name` / `--app_name` | Depends | Dump task / consumer app identity |
| `--start_time` / `--end_time` | Yes (metrics) | 10-digit Unix timestamps (seconds) |

Conventions: indexed parameters use `.[N]` (`--tasks.1.id=`); booleans are
`true`/`false`; `SendRecords` payloads are Base64. Cursor/consume APIs use
hyphenated names (`--stream-name`, `--partition-cursor`).

## KooCLI Command Format Standard

Template (do not run as-is): `hcloud dis <Operation> --cli-region=<region> [--key=value ...]`. Operations are PascalCase; indexed parameters use `--key.N=valueN` (e.g. `--tags.1.key=env`).

## Reference Documents

- `references/dis-operation-catalog.md` — All 38 DIS operations: method, REST path, required/optional parameters
- `references/iam-policies.md` — Least-privilege IAM policies for DIS read and management operations
- `references/cli-installation-guide.md` — KooCLI installation, AK/SK configuration, and region/project setup
- `references/verification-method.md` — Read-only smoke tests and functional verification steps
- `references/acceptance-criteria.md` — Acceptance checklist for DIS operations
- `references/dataflow-diagram.md` — Mermaid data flow from producers to DIS to dump destinations

## Best Practices

- Verify the name is free (`ListStreams`) before `CreateStream`; keep output
  small with `--limit` / `--start_stream_name`.
- Before `DeleteStream`, check `ListTransferTasks` and `ShowConsumerState`;
  never silently delete a stream with active consumers or dump tasks.
- Reuse the `dis_admin_agency` agency for dump tasks and keep the OBS staging
  bucket in the same region. Query metrics over a narrow window with
  `--label_list`.
- Partition scaling is limited to 5 changes per hour per stream; the full functional checklist is in `references/verification-method.md`.
- Mask AK/SK and DWS passwords in every generated report and command echo.