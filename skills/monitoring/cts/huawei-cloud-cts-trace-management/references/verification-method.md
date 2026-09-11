# Verification Method for huawei-cloud-cts-trace-management

This document defines how to verify each action class of the skill.

## Prerequisites for Verification

- hcloud CLI ≥ 7.x installed and authenticated (see `cli-installation-guide.md`)
- A region and project where you have at least read access to CTS
- For manage actions: an existing OBS bucket (OBS delivery) or SMN topic (notification)

## Query Actions (R3) — Verification

| Action | Verification Command | Expected Result |
|--------|---------------------|-----------------|
| `huawei_list_cts_trackers` | `hcloud CTS ListTrackers --cli-region={region} --project_id={project_id}` | JSON array with tracker objects (name, type, status, bucket name) |
| `huawei_list_cts_traces` | `hcloud CTS ListTraces --cli-region={region} --project_id={project_id} --trace_type=system --limit=10` | JSON array of trace objects in last hour (empty if no events) |
| `huawei_list_cts_operations` | `hcloud CTS ListOperations --cli-region={region} --project_id={project_id}` | JSON array of operations grouped by service |
| `huawei_list_cts_notifications` | `hcloud CTS ListNotifications --cli-region={region} --project_id={project_id} --notification_type=smn` | JSON array of notifications (may be empty) |
| `huawei_list_cts_trace_resources` | `hcloud CTS ListTraceResources --cli-region={region} --domain_id={domain_id}` | JSON array of tracked resources |

**Error semantics:** empty lists are valid results (e.g. no tracker → no traces — see Critical Warnings
in SKILL.md). Non-zero exit / error JSON indicates auth, scope, or parameter problems.

## Analyze Actions (R3) — Verification

- `huawei_analyze_cts_traces`: run `ListTraces` with a time range (`--from`/`--to`, 13-digit UTC ms)
  and aggregate locally by user (`--user`), service (`--service_type`), or trace status
  (`--trace_rating`). Verify the aggregation counts match the raw trace list.
- `huawei_analyze_cts_retention`: run `ListTrackers` and evaluate each tracker's retention:
  - `obs_info.bucket_name` set → OBS delivery with bucket-lifecycle retention
  - `is_lts_enabled=true` → LTS long retention
  - neither → 7-day default retention (trap: advise LTS/OBS for compliance)
  - `is_organization_tracker=true` → covers org cross-account

## Manage Actions (R1/R2) — Verification

Always preview the exact command and wait for explicit user confirmation before execution.

| Action | Verification After Execution |
|--------|------------------------------|
| `huawei_create_cts_tracker` | `ListTrackers` shows the new tracker with expected type/bucket/LTS flags |
| `huawei_create_cts_notification` | `ListNotifications --notification_type={smn\|fun}` shows the new notification |
| `huawei_delete_cts_tracker` | `ListTrackers` no longer contains the deleted data tracker |

**Resource lifecycle note:** the system tracker cannot be deleted (only data trackers can).
Deleting a tracker does not remove already-collected traces.

## Negative Tests

1. Missing `--project_id` → error; confirm the parameter is required and correctly spelled.
2. Wrong `--trace_type` value → error listing valid enum (`system`/`data`).
3. `ListTraces` with only `--from` (no `--to`) → validation error; they must be used together.
4. Create tracker with a nonexistent OBS bucket → creation fails; verify bucket first.
5. `ListTraceResources` with `--project_id` instead of `--domain_id` → error; the operation
   uses the account ID.

## Pass Criteria

All positive commands return valid JSON; all negative tests fail with a clear error; no command
requires user confirmation for read-only actions; write actions require confirmation.