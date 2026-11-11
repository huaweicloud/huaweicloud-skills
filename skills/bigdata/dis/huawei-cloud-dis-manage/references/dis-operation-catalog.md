# DIS Operation Catalog

All 38 DIS operations exposed by KooCLI `hcloud dis <Operation>`. REST method
and path come from the DIS v2/v3 API metadata; required parameters were verified
against `hcloud dis <Operation> --help` (KooCLI 7.3.12).

Common parameters on every command:

| Parameter | Required | Notes |
|-----------|----------|-------|
| `--cli-region` | Yes (auto) | Region; pass explicitly on every command |
| `--project_id` | Yes (auto) | Path parameter auto-filled by KooCLI from the profile |

KooCLI parameter names below are the exact spellings from `--help`. Note the
hyphenated names in cursor/consume APIs.

## Streams

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `ListStreams` | GET | `/v2/{project_id}/streams` | — | `--limit`, `--start_stream_name` |
| `ShowStream` | GET | `/v2/{project_id}/streams/{stream_name}` | `--stream_name` | `--limit_partitions`, `--start_partitionId` |
| `CreateStream` | POST | `/v2/{project_id}/streams` | `--stream_name`, `--partition_count` | `--stream_type`, `--data_type`, `--data_duration`, `--compression_format`, `--data_schema`, `--auto_scale_enabled`, `--auto_scale_max_partition_count`, `--auto_scale_min_partition_count`, `--tags.[N].key/value`, `--sys_tags.[N].key/value/status` |
| `UpdateStream` | PUT | `/v3/{project_id}/streams/{stream_name}` | `--cli-jsonInput` with `path.project_id`, `path.stream_name`, `body.stream_name` | `--data_duration`, `--data_type`, `--data_schema`, `--auto_scale_enabled`, `--auto_scale_max_partition_count`, `--auto_scale_min_partition_count` (body keys inside the jsonInput file) |
| `UpdatePartitionCount` | PUT | `/v2/{project_id}/streams/{stream_name}` | `--cli-jsonInput` with `path.project_id`, `path.stream_name`, `body.stream_name`, `body.target_partition_count` | — |
| `DeleteStream` | DELETE | `/v2/{project_id}/streams/{stream_name}` | `--stream_name` | — |

### `UpdateStream` / `UpdatePartitionCount` — required `--cli-jsonInput` form

KooCLI 7.3.12 declares `--stream_name` twice for both operations (once as a
`path` parameter and once as a `body` parameter). A command-line
`--stream_name` therefore cannot satisfy both declarations:

```text
$ hcloud dis UpdateStream --cli-region=cn-north-4 --stream_name=e2e-probe --data_duration=24 --dryrun
[USE_ERROR]The following parameters are required: stream_name

$ hcloud dis UpdateStream ... --stream_name=e2e-probe --stream_name=e2e-probe --dryrun
[USE_ERROR]Duplicate parameter: stream_name.
```

`UpdatePartitionCount` shows the same behavior, while `DeleteStream` (path-only
declaration) and `ListStreams` are unaffected. The verified working form is
positional `--cli-jsonInput`; it generates the correct requests
`PUT /v3/{project_id}/streams/{stream_name}` and
`PUT /v2/{project_id}/streams/{stream_name}`.

```bash
cat > dis-update-stream.json <<'JSON'
{
  "path": {"project_id": "{project_id}", "stream_name": "{stream_name}"},
  "body": {"stream_name": "{stream_name}", "data_duration": 24}
}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdateStream --cli-region={region} --cli-jsonInput=./dis-update-stream.json

cat > dis-update-partition-count.json <<'JSON'
{
  "path": {"project_id": "{project_id}", "stream_name": "{stream_name}"},
  "body": {"stream_name": "{stream_name}", "target_partition_count": 5}
}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdatePartitionCount --cli-region={region} --cli-jsonInput=./dis-update-partition-count.json
```

`project_id` cannot be omitted from the `path` block: when `--cli-jsonInput` is
used, KooCLI stops auto-filling path parameters from the profile. Always
`--dryrun` first and confirm the generated method and path before executing.

## Dump (Transfer) Tasks

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `ListTransferTasks` | GET | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name` | — |
| `ShowTransferTask` | GET | `/v2/{project_id}/streams/{stream_name}/transfer-tasks/{task_name}` | `--stream_name`, `--task_name` | — |
| `CreateObsTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name`, `--destination_type=OBS` | `--obs_destination_descriptor.*` (task_name, agency_name, consumer_strategy, deliver_time_interval, destination_file_type, file_prefix, obs_bucket_path, partition_format, processing_schema.*, record_delimiter) |
| `CreateDwsTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name`, `--destination_type=DWS` | `--dws_destination_descriptor.*` (task_name, agency_name, consumer_strategy, deliver_time_interval, dws_cluster_id, dws_cluster_name, dws_database_name, dws_schema, dws_table_name, dws_table_columns, dws_delimiter, file_prefix, obs_bucket_path, user_name, user_password, kms_user_key_id, kms_user_key_name, retry_duration, options.*) |
| `CreateDliTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name`, `--destination_type=DLI` | `--dli_destination_descriptor.*` (task_name, agency_name, consumer_strategy, deliver_time_interval, dli_database_name, dli_table_name, file_prefix, obs_bucket_path, retry_duration) |
| `CreateMrsTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name`, `--destination_type=MRS` | `--mrs_destination_descriptor.*` (task_name, agency_name, consumer_strategy, deliver_time_interval, file_prefix, hdfs_prefix_folder, mrs_cluster_id, mrs_cluster_name, mrs_hdfs_path, obs_bucket_path, retry_duration) |
| `CreateCloudTableTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks` | `--stream_name`, `--destination_type=CLOUDTABLE` | `--cloudtable_destination_descriptor.*` (task_name, agency_name, consumer_strategy, deliver_time_interval, cloudtable_cluster_id/name, cloudtable_table_name, cloudtable_row_key_delimiter, cloudtable_schema.*, obs_backup_bucket_path, backup_file_prefix, opentsdb_schema.*, retry_duration) |
| `BatchStartTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks/action` | `--stream_name`, `--action=start`, `--tasks.[N].id` | — |
| `BatchStopTransferTask` | POST | `/v2/{project_id}/streams/{stream_name}/transfer-tasks/action` | `--stream_name`, `--action=stop`, `--tasks.[N].id` | — |
| `DeleteTransferTask` | DELETE | `/v2/{project_id}/streams/{stream_name}/transfer-tasks/{task_name}` | `--stream_name`, `--task_name` | — |

## Monitoring

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `ShowStreamMetrics` | GET | `/v2/{project_id}/streams/{stream_name}/metrics` | `--stream_name`, `--start_time`, `--end_time` | `--label`, `--label_list` |
| `ShowPartitionMetrics` | GET | `/v2/{project_id}/streams/{stream_name}/partitions/{partition_id}/metrics` | `--stream_name`, `--partition_id`, `--start_time`, `--end_time` | `--label`, `--label_list` |
| `ShowConsumerState` | GET | `/v2/{project_id}/apps/{app_name}/streams/{stream_name}` | `--app_name`, `--stream_name`, `--checkpoint_type=LAST_READ` | `--limit`, `--start_partition_id` |

Stream metric labels: `total_put_bytes_per_stream`,
`total_get_bytes_per_stream`, `total_put_records_per_stream`,
`total_get_records_per_stream`, `total_put_req_latency`,
`total_get_req_latency`, `total_put_req_suc_per_stream`,
`total_get_req_suc_per_stream`, `traffic_control_put`, `traffic_control_get`.

Partition metric labels: `total_put_bytes_per_partition`,
`total_get_bytes_per_partition`, `total_put_records_per_partition`,
`total_get_records_per_partition`.

## Consumer Apps and Checkpoints

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `CreateApp` | POST | `/v2/{project_id}/apps` | `--app_name` | — |
| `ListApp` | GET | `/v2/{project_id}/apps` | — | `--limit`, `--start_app_name`, `--stream_name` |
| `ShowApp` | GET | `/v2/{project_id}/apps/{app_name}` | `--app_name` | — |
| `DeleteApp` | DELETE | `/v2/{project_id}/apps/{app_name}` | `--app_name` | — |
| `CommitCheckpoint` | POST | `/v2/{project_id}/checkpoints` | `--app_name`, `--checkpoint_type=LAST_READ`, `--partition_id`, `--sequence_number`, `--stream_name` | `--metadata` |
| `ShowCheckpoint` | GET | `/v2/{project_id}/checkpoints` | `--app_name`, `--checkpoint_type=LAST_READ`, `--partition_id`, `--stream_name` | — |
| `DeleteCheckpoint` | DELETE | `/v2/{project_id}/checkpoints` | `--app_name`, `--checkpoint_type=LAST_READ`, `--stream_name` | `--partition_id` |

## Data Upload and Consumption

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `SendRecords` | POST | `/v2/{project_id}/records` | `--stream_name`, `--records.[N].data` (Base64) | `--stream_id`, `--records.[N].explicit_hash_key`, `--records.[N].partition_id`, `--records.[N].partition_key` |
| `ShowCursor` | GET | `/v2/{project_id}/cursors` | `--stream-name`, `--partition-id` | `--cursor-type`, `--starting-sequence-number`, `--timestamp` |
| `ConsumeRecords` | GET | `/v2/{project_id}/records` | `--partition-cursor` | `--max_fetch_bytes` |

## Authorization Policies and Tags

| Operation | Method | Path | Required CLI parameters | Common optional parameters |
|-----------|--------|------|-------------------------|----------------------------|
| `CreatePolicies` | POST | `/v2/{project_id}/streams/{stream_name}/policies` | `--stream_name`, `--action_type`, `--effect=accept`, `--principal_name`, `--stream_id` | — |
| `ListPolicies` | GET | `/v2/{project_id}/streams/{stream_name}/policies` | `--stream_name` | — |
| `CreateTag` | POST | `/v2/{project_id}/stream/{stream_id}/tags` | `--stream_id` | `--tag.key`, `--tag.value` |
| `BatchCreateTags` | POST | `/v2/{project_id}/stream/{stream_id}/tags/action` | `--stream_id`, `--action=create` | `--tags.[N].key`, `--tags.[N].value` |
| `ListTags` | GET | `/v2/{project_id}/stream/tags` | — | — |
| `ShowStreamTags` | GET | `/v2/{project_id}/stream/{stream_id}/tags` | `--stream_id` | — |
| `DeleteTag` | DELETE | `/v2/{project_id}/stream/{stream_id}/tags/{key}` | `--stream_id`, `--key` | — |
| `BatchDeleteTags` | POST | `/v2/{project_id}/stream/{stream_id}/tags/action` | `--stream_id`, `--action=delete` | `--tags.[N].key`, `--tags.[N].value` |
| `ListResourcesByTags` | POST | `/v2/{project_id}/stream/resource_instances/action` | `--action=filter|count` | `--limit`, `--offset`, `--matches`, `--tags.[N].key`, `--tags.[N].values.[N]`, `--tags_any.*`, `--not_tags.*`, `--not_tags_any.*` |

## Notes

- Operations with `--action` share a REST path; the action value selects the
  behavior (`start`, `stop`, `create`, `delete`, `filter`, `count`).
- Dump task creation operations all POST to the same transfer-tasks path; the
  `--destination_type` value selects the descriptor schema
  (`obs_`, `dws_`, `dli_`, `mrs_`, `cloudtable_destination_descriptor.*`).
- `UpdateStream` uses the v3 path; the other stream operations use v2. KooCLI
  selects the correct version automatically.
- `UpdateStream` and `UpdatePartitionCount` must be invoked through
  `--cli-jsonInput` in KooCLI 7.3.12 (duplicate `--stream_name` declaration);
  see the dedicated subsection above.
- `--project_id` is declared required by KooCLI but is auto-filled from the
  profile; only pass it explicitly when using a non-default project.