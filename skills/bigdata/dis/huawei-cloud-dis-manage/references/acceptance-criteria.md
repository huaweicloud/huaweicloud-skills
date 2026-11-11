# Acceptance Criteria

## Functional coverage

| # | Capability | Operation(s) | Acceptance |
|---|------------|--------------|------------|
| 1 | List streams | `ListStreams` | Returns stream names; pagination via `--start_stream_name` works |
| 2 | Show stream detail | `ShowStream` | Returns status, partition count, retention, data type, stream type, stream ID |
| 3 | Create stream | `CreateStream` | Stream created with requested name, partitions, type, retention, data type |
| 4 | Delete stream | `DeleteStream` | Stream removed after explicit confirmation |
| 5 | Update stream config | `UpdateStream` | Retention/data type/auto-scaling changes reflected in `ShowStream` |
| 6 | Scale partitions | `UpdatePartitionCount` | Target partition count applied; scale-down confirmed by user |
| 7 | Dump tasks to OBS/DWS/DLI/MRS/CloudTable | `Create*TransferTask` | Task created with destination descriptor and visible in `ListTransferTasks` |
| 8 | Dump task lifecycle | `ShowTransferTask`, `BatchStartTransferTask`, `BatchStopTransferTask`, `DeleteTransferTask` | Start/stop/delete verified after confirmation |
| 9 | Stream metrics | `ShowStreamMetrics` | Requested labels return time series data points |
| 10 | Partition metrics | `ShowPartitionMetrics` | Per-partition throughput series returned |
| 11 | Consumer state | `ShowConsumerState` | Per-partition committed sequence numbers returned |
| 12 | Apps and checkpoints | `CreateApp`, `ListApp`, `ShowApp`, `DeleteApp`, `CommitCheckpoint`, `ShowCheckpoint`, `DeleteCheckpoint` | App lifecycle and checkpoint persistence verified |
| 13 | Data upload/consume | `SendRecords`, `ShowCursor`, `ConsumeRecords` | Synthetic record written and read back |
| 14 | Authorization policies | `CreatePolicies`, `ListPolicies` | Policy created for `putRecords`/`getRecords`/`getStreamInfo` and listed |
| 15 | Tags | `CreateTag`, `BatchCreateTags`, `ListTags`, `ShowStreamTags`, `DeleteTag`, `BatchDeleteTags`, `ListResourcesByTags` | Tags created, listed, filtered, deleted |

## Safety and quality

- [ ] Every mutating command is preceded by an explicit user confirmation for
      deletes, scale-downs, retention changes, and dump start/stop.
- [ ] No AK/SK, DWS password, or production payload appears in reports, logs, or
      command echoes.
- [ ] Delete operations verify dependent resources (dump tasks, consumers) first.
- [ ] Outputs are summarized; large lists are paginated with `--limit`.
- [ ] Failures are reported with the command, error code, and remediation instead
      of being hidden.
- [ ] `DIS.4107 Invalid AccessKey header` is classified as an authorization
      problem, not a syntax problem.

## Documentation

- [ ] `SKILL.md` frontmatter has `name` and `description` with trigger terms and `tags`.
- [ ] Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation,
      KooCLI Command Format Standard, and Reference Documents sections exist.
- [ ] Every documented CLI command includes `--cli-region` and all required parameters.
- [ ] Operation catalog matches the 38 `hcloud dis` operations.
- [ ] IAM policies follow least privilege and cover dump-task agency needs.