# Verification Method

## 1. Static verification (no cloud resources required)

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis --help
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListStreams --help
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateStream --help
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis CreateObsTransferTask --help
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ShowStreamMetrics --help
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis SendRecords --help
```

Expected: KooCLI lists 38 DIS operations and each `--help` call prints required
and optional parameters. Any "Unsupported service" result means the CLI version
is too old; upgrade with `hcloud update -y`.

Parameter-name checks:

| Operation | Required parameters to confirm |
|-----------|-------------------------------|
| `CreateStream` | `--stream_name`, `--partition_count` |
| `UpdatePartitionCount` | `--stream_name`, `--target_partition_count` |
| `CreateObsTransferTask` | `--stream_name`, `--destination_type` |
| `BatchStartTransferTask` | `--stream_name`, `--action`, `--tasks.[N].id` |
| `ShowStreamMetrics` | `--stream_name`, `--start_time`, `--end_time` |
| `ShowPartitionMetrics` | `--stream_name`, `--partition_id`, `--start_time`, `--end_time` |
| `SendRecords` | `--stream_name`, `--records.[N].data` |
| `ShowCursor` | `--stream-name`, `--partition-id` |
| `ConsumeRecords` | `--partition-cursor` |
| `CommitCheckpoint` | `--app_name`, `--checkpoint_type`, `--partition_id`, `--sequence_number`, `--stream_name` |

## 2. Read-only smoke tests

```bash
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListStreams --cli-region={region} --limit=5
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListTags --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis ListApp --cli-region={region} --limit=5
```

Pass criteria: HTTP 200 with a JSON body. An empty list is a pass (no resources).

If `DIS.4107 Invalid AccessKey header` is returned, the credential is not
accepted by DIS in that region. This is an environment/authorization problem,
not a command syntax problem: verify the profile, DIS enablement, and IAM
permissions before concluding that the operation failed.

## 3. Functional verification (requires a test stream)

Use a dedicated, non-production stream and synthetic payloads.

| Step | Command | Expected result |
|------|---------|-----------------|
| 1. Create | `CreateStream --stream_name=dis-skill-test --partition_count=2 --stream_type=COMMON --data_type=BLOB --data_duration=24` | Stream created |
| 2. Confirm | `ShowStream --stream_name=dis-skill-test` | Status `RUNNING`, `partition_count=2` |
| 3. Scale | `UpdatePartitionCount` via `--cli-jsonInput` (see 3.1) | Partition count becomes 3 |
| 4. Upload | `SendRecords --stream_name=dis-skill-test --records.1.data=ZGlzLXNraWxsLXRlc3Q=` | Record accepted, sequence number returned |
| 5. Consume | `ShowCursor --stream-name=dis-skill-test --partition-id=0 --cursor-type=TRIM_HORIZON`, then `ConsumeRecords --partition-cursor={cursor}` | The uploaded record is returned |
| 6. Metrics | `ShowStreamMetrics --stream_name=dis-skill-test --start_time={t0} --end_time={t1} --label_list=total_put_records_per_stream` | At least one data point |
| 7. Dump (optional) | `CreateObsTransferTask` + `ListTransferTasks` | Task visible with expected state |
| 8. Cleanup | `DeleteTransferTask` (if created) then `DeleteStream --stream_name=dis-skill-test` | Both removed |

Every mutating step needs explicit user confirmation before execution.

### 3.1 UpdateStream / UpdatePartitionCount `--cli-jsonInput` form

Both operations declare `--stream_name` in path and body in KooCLI 7.3.12, so a
plain `--stream_name` command fails (`The following parameters are required:
stream_name` or `Duplicate parameter: stream_name`). Use the tested positional
`--cli-jsonInput` form. The `project_id` placeholder must be replaced with the
real project ID, because `--cli-jsonInput` disables automatic path filling.

```bash
cat > dis-update-stream.json <<'JSON'
{
  "path": {"project_id": "{project_id}", "stream_name": "dis-skill-test"},
  "body": {"stream_name": "dis-skill-test", "data_duration": 48}
}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdateStream --cli-region={region} --cli-jsonInput=./dis-update-stream.json --dryrun

cat > dis-update-partition-count.json <<'JSON'
{
  "path": {"project_id": "{project_id}", "stream_name": "dis-skill-test"},
  "body": {"stream_name": "dis-skill-test", "target_partition_count": 3}
}
JSON
skill-quality-cli run --skill-name huawei-cloud-dis-manage -- hcloud dis UpdatePartitionCount --cli-region={region} --cli-jsonInput=./dis-update-partition-count.json --dryrun
```

Dry-run pass criteria: `UpdateStream` resolves to
`PUT https://dis.{region}.myhuaweicloud.com/v3/{project_id}/streams/dis-skill-test`
and `UpdatePartitionCount` to the `/v2/` equivalent, each with the expected JSON
body. Remove `--dryrun` only after explicit user confirmation.

## 4. Build-environment note (2026-11-08)

- KooCLI 7.3.12 is installed, `hcloud dis` exposes all 38 operations, and all
  `--help` parameter tables were captured successfully.
- The runtime credential available during this build was rejected by DIS
  (`DIS.4107 Invalid AccessKey header`) for `ListStreams` in `cn-north-4`,
  `cn-north-1`, `cn-east-3`, `cn-south-1`, and `ap-southeast-1`, while the same
  credential worked for ECS and IAM. The DIS data-plane tests therefore could
  not be executed here; re-run Section 2 with a DIS-authorized AK/SK.

## 5. Negative checks

| Scenario | Expected behavior |
|----------|-------------------|
| `CreateStream` without `--partition_count` | KooCLI rejects with a missing-required-parameter error |
| `ShowCursor` using underscore names (`--stream_name`) | KooCLI rejects; the API requires `--stream-name` |
| `SendRecords` with a non-Base64 payload | API rejects; encode first (`base64`) |
| `ConsumeRecords` after 5 minutes | Cursor expired; request a new one with `ShowCursor` |
| Scale more than 5 times in one hour | API rejects with a rate-limit error |