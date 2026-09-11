---
name: huawei-cloud-cts-trace-management
description: >
  Huawei Cloud CTS (Cloud Trace Service / 云审计服务) management and audit analysis via hcloud CLI.
  Covers tracker lifecycle (list/create/delete), audit trace query and analysis (filter by time/user/
  service), cloud service operation listing, key event notifications, trace resources, and retention
  compliance analysis (7-day default vs LTS long retention vs OBS delivery). Query and Analyze actions
  run automatically (R3); Create/Delete actions require preview and explicit user confirmation (R2/R1).
  Supports AK/SK credentials and local hcloud profile authentication.
  Triggers include: CTS, Cloud Trace Service, 云审计服务, audit log, 审计日志, tracker, 追踪器,
  trace, 审计事件, operation record, 操作记录, notification, 通知规则, retention, 保留策略,
  compliance, 合规, audit, 审计.
tags: [huawei-cloud, cts, audit, tracker, trace]
---

# Huawei Cloud CTS (Cloud Trace Service)

## Overview

This skill operates Huawei Cloud CTS (Cloud Trace Service / 云审计服务) through the `hcloud` CLI.
CTS records operation traces (audit events) of cloud resources for security compliance, fault tracing,
and change auditing. The skill covers:

| Category | Capabilities |
|----------|--------------|
| **Query** | List trackers (`huawei_list_cts_trackers`), query audit traces (`huawei_list_cts_traces`), list cloud service operations (`huawei_list_cts_operations`), list key event notifications (`huawei_list_cts_notifications`), list trace resources (`huawei_list_cts_trace_resources`) |
| **Diagnose** | Aggregate audit events by user/time/operation (`huawei_analyze_cts_traces`), evaluate retention & compliance (`huawei_analyze_cts_retention`) |
| **Manage** | Create tracker (`huawei_create_cts_tracker`), create notification (`huawei_create_cts_notification`), delete tracker (`huawei_delete_cts_tracker`) |

> **Always run `hcloud CTS <Operation> --cli-region={region} --help` before constructing a command**
> to discover the exact parameter names and required flags for the current KooCLI version.
> Do not answer from general knowledge — follow the procedures in this document.

### Critical Warnings

| Trap | Why |
|------|-----|
| **Tracker required for traces** | Audit traces are only recorded after a tracker exists. No tracker → no events. Check `ListTrackers` first. |
| **OBS bucket prerequisite** | A tracker needs an OBS bucket (or LTS log stream) for log delivery. Creation fails if the bucket is missing or lacks permissions. |
| **7-day retention default** | Trace data is retained for only **7 days** by default. Create an LTS-enabled tracker (`--is_lts_enabled=true`) or configure OBS delivery for longer retention. |
| **Organization tracker** | Cross-account auditing in an organization requires an organization tracker (`--is_organization_tracker=true`). A normal tracker only covers the current account. |

## Prerequisites

1. **hcloud CLI** installed and authenticated — see `references/cli-installation-guide.md`
2. **Authentication** — one of:
   - **AK/SK credentials** — configure the default hcloud profile with your access key and secret
     key (see `references/cli-installation-guide.md`, section "Authentication"), or
   - Environment variables `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`) — hcloud auto-detects them
3. **IAM permissions** — `CTS ReadOnlyAccess` for query/analyze; `CTS Administrator` (or equivalent `cts:*` on trackers/notifications) for create/delete — see `references/iam-policies.md`
4. **Region & project**: most CTS APIs are region/project scoped. Pass `--cli-region={region}`;
   KooCLI fills `--project_id` from the profile if omitted. `ListTraceResources` requires
   `--domain_id` (account ID).
5. **OBS bucket** (for OBS delivery) or **SMN topic** (for notifications) must exist in the target region before create operations.

### Quality Reporting Environment Variables

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint, default `https://skillsapi.developer.myhuaweicloud.com/api/quality/report` |
| `SKILL_QUALITY_NAME` | No | Skill name (default auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set to `1` to disable reporting (local debugging) |
| `SKILL_QUALITY_TIMEOUT` | No | Report timeout seconds (default 3) |

## Workflow

```
1. Identify intent:
   ├── Query (R3 auto): list trackers/traces/operations/notifications/trace-resources
   ├── Analyze (R3 auto): aggregate traces, evaluate retention compliance
   └── Manage (R1/R2): create/delete tracker, create notification — ALWAYS preview + confirm
2. Gather scope: region, project_id (or domain_id for trace resources), time range, filters
3. Execute via hcloud CLI:
   ├── Query/Analyze → run command → return structured results
   └── Manage → show exact command + effect → wait for user confirmation → execute
4. Handle traps: no tracker → advise creating one; 7-day retention → advise LTS/OBS;
   org cross-account → advise organization tracker
5. Report results (JSON), masking AK/SK-like values in output
```

**Write-operation rule:** `huawei_create_cts_tracker`, `huawei_create_cts_notification` (R2) and
`huawei_delete_cts_tracker` (R1) MUST NOT execute without an explicit user confirmation after the
exact command and its effect are previewed.

## Core Commands

Service name is `CTS` (KooCLI metadata directory `cts`). Region parameter `--cli-region={region}`
is required on every command.

The required `--project_id` is **omitted from the examples below**: KooCLI automatically fills it
from the active profile when it is not passed (see Prerequisites), and the test harness injects it
from `templates/test-defaults.json` (`request_defaults.project_id`). Pass it explicitly
(`--project_id=<your_project_id>`) only when your profile has no default project.
`ListTraceResources` is the exception — it requires `--domain_id` (account ID), which is shown as a
concrete example value below; replace it with your own account ID.
Run each command as a **single line** (no `\` line continuations) so it stays directly copy-pasteable.

### Query — Trackers

```bash
# List all trackers of the tenant
hcloud CTS ListTrackers --cli-region={region}

# List a specific tracker (by name/type)
hcloud CTS ListTrackers --cli-region={region} --tracker_name=system --tracker_type=system
```

### Query — Audit Traces

```bash
# List recent traces (default: system traces, last hour)
hcloud CTS ListTraces --cli-region={region} --trace_type=system

# Query traces in a time range (from/to are UTC millisecond timestamps, 13 digits, used together)
hcloud CTS ListTraces --cli-region={region} --trace_type=system --from=1725000000000 --to=1725600000000 --limit=50

# Filter by user, service, and trace status (normal|warning|incident)
hcloud CTS ListTraces --cli-region={region} --trace_type=system --user=alice --service_type=ECS --trace_rating=warning

# Query a specific trace by ID (other criteria are ignored)
hcloud CTS ListTraces --cli-region={region} --trace_type=system --trace_id=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
```

### Query — Operations, Notifications, Trace Resources

```bash
# List all cloud service operations recorded by CTS (optionally filter by service/resource type)
hcloud CTS ListOperations --cli-region={region}
hcloud CTS ListOperations --cli-region={region} --service_type=ECS --resource_type=vm

# List key event notifications (notification_type: smn|fun)
hcloud CTS ListNotifications --cli-region={region} --notification_type=smn

# List resources involved in traces (NOTE: uses --domain_id, NOT --project_id)
# Replace the example domain ID with your own account ID
hcloud CTS ListTraceResources --cli-region={region} --domain_id=074c26ae7f0025b10fd7c0159cb576a0
```

### Manage — Create Tracker (R2, preview + confirm)

```bash
# Create a management (system) tracker delivering traces to an OBS bucket
hcloud CTS CreateTracker --cli-region={region} --tracker_name=system --tracker_type=system --obs_info.bucket_name={obs_bucket_name} --obs_info.is_obs_created=false --agency_name=cts_admin_trust

# Create an LTS-enabled tracker for long retention (>7 days)
hcloud CTS CreateTracker --cli-region={region} --tracker_name=system --tracker_type=system --is_lts_enabled=true --agency_name=cts_admin_trust

# Create an organization tracker for cross-account auditing
hcloud CTS CreateTracker --cli-region={region} --tracker_name=system --tracker_type=system --is_organization_tracker=true --obs_info.bucket_name={obs_bucket_name} --obs_info.is_obs_created=false --agency_name=cts_admin_trust
```

> Before creating a tracker with OBS delivery, verify the target OBS bucket exists
> (`hcloud OBS ListBuckets --cli-region={region}` or CTS `CheckObsBuckets`) and that
> the account has permissions — otherwise creation fails.

### Manage — Create Notification (R2, preview + confirm)

```bash
# Create a complete-type notification (all supported operations on all connected services)
hcloud CTS CreateNotification --cli-region={region} --notification_name={notification_name} --operation_type=complete --topic_id={smn_topic_urn}

# Create a customized notification for specific operations
hcloud CTS CreateNotification --cli-region={region} --notification_name={notification_name} --operation_type=customized --operations.1.service_type=ECS --operations.1.resource_type=vm --operations.1.trace_names.1=createServer --topic_id={smn_topic_urn} --agency_name=cts_admin_trust
```

### Manage — Delete Tracker (R1, preview + confirm)

```bash
# Delete a data tracker (only data trackers can be deleted)
hcloud CTS DeleteTracker --cli-region={region} --tracker_name={data_tracker_name} --tracker_type=data

# Disable/delete with explicit system tracker name
hcloud CTS DeleteTracker --cli-region={region} --tracker_name=system --tracker_type=system
```

> **Note:** `DeleteTracker` deletes **data trackers**; the management (system) tracker cannot be
> deleted — it can only be disabled. Deleting a tracker does not affect traces already collected.

## Parameter Confirmation

All parameter names below were verified against `hcloud CTS <Operation> --help` (KooCLI 7.2.12).
Values in `{}` are placeholders — replace with real values. **Do not invent parameter names.**

### ListOperations

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--resource_type` | No | string | Resource type; if used, `--service_type` is mandatory |
| `--service_type` | No | string | Cloud service type (e.g. ECS) |

### ListTraces

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--trace_type` | Yes | string | Trace type: `system` (default) or `data` |
| `--from` / `--to` | No | integer | UTC ms timestamps (13 digits), used together; default = last hour → now |
| `--limit` | No | integer | Number of traces, default 10, max 200 |
| `--next` | No | string | Pagination marker (value of `marker` in response) |
| `--user` | No | string | User name filter (system traces only) |
| `--service_type` | No | string | Cloud service acronym filter (system traces only) |
| `--resource_id` / `--resource_name` / `--resource_type` | No | string | Resource filters (system traces only) |
| `--trace_id` | No | string | Trace ID; if set, other criteria are ignored |
| `--trace_name` | No | string | Trace name (system traces only) |
| `--trace_rating` | No | string | Trace status: `normal` \| `warning` \| `incident` |
| `--tracker_name` | No | string | System traces: `system`; data traces: data tracker name |
| `--enterprise_project_id` | No | string | Enterprise project filter |
| `--access_key_id` | No | string | Access key used to query traces |

### CreateTracker

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--tracker_name` | Yes | string | Tracker name (default `system` for system type) |
| `--tracker_type` | Yes | string | `system` (management tracker) or `data` (data tracker) |
| `--obs_info.bucket_name` | No* | string | OBS bucket for log delivery (*needed for OBS delivery) |
| `--obs_info.is_obs_created` | No | boolean | `true` = create new bucket, `false` = use existing |
| `--obs_info.file_prefix_name` | No | string | File name prefix for OBS trace files |
| `--obs_info.compress_type` | No | string | `gzip` (default) or `json` |
| `--obs_info.bucket_lifecycle` | No | integer | Retention days in OBS bucket (data tracker only) |
| `--obs_info.is_sort_by_service` | No | boolean | Sort transfer path by cloud service (default true) |
| `--is_lts_enabled` | No | boolean | Enable LTS trace analysis (long retention) |
| `--is_organization_tracker` | No | boolean | `true` = org tracker (cross-account dumps) |
| `--is_support_trace_files_encryption` | No | boolean | Encrypt OBS trace files (with `--kms_id`) |
| `--kms_id` | No | string | KMS key ID (mandatory when encryption enabled) |
| `--is_support_validate` | No | boolean | Enable trace file verification |
| `--agency_name` | No | string | `cts_admin_trust` auto-creates the cloud service agency |
| `--data_bucket.data_bucket_name` | No | string | Bucket tracked by a data tracker |
| `--data_bucket.data_event.1` | No | array | Data tracker events: `WRITE` \| `READ` |
| `--management_event_selector.exclude_service.1` | No | array | Services excluded from dump (currently only KMS) |

### ListTrackers

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--tracker_name` | No | string | Tracker name; omitted → all trackers |
| `--tracker_type` | No | string | `system` or `data` |

### DeleteTracker

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--tracker_name` | No | string | Tracker name; omitted → all data trackers |
| `--tracker_type` | No | string | `data` (default) or `system` |

### CreateNotification

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--notification_name` | Yes | string | Notification name |
| `--operation_type` | Yes | string | `complete` (all operations) or `customized` |
| `--topic_id` | No | string | SMN topic URN or FunctionGraph function URN |
| `--agency_name` | No | string | `cts_admin_trust` auto-creates agency |
| `--operations.1.service_type` | No | string | Cloud service acronym (customized type) |
| `--operations.1.resource_type` | No | string | Resource type (customized type) |
| `--operations.1.trace_names.1` | No | array | Trace names (customized type) |
| `--notify_user_list.1.user_group` | No | string | IAM user group |
| `--notify_user_list.1.user_list.1` | No | array | IAM users |
| `--filter.is_support_filter` | No | boolean | Enable advanced filter |
| `--filter.condition` | No | string | `AND` or `OR` between filter rules |
| `--filter.rule.1` | No | array | Filter rule, format `field rule value` (fields: api_version, code, trace_rating, trace_type, resource_id, resource_name) |

### ListNotifications

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--project_id` | Yes | string | Project ID (path) |
| `--notification_type` | Yes | string | `smn` or `fun` (path param) |
| `--notification_name` | No | string | Notification name; omitted → all notifications |

### ListTraceResources

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--domain_id` | Yes | string | Account (domain) ID — **not** project ID |

## Quality Reporting

This Skill integrates `scripts/skill_quality_sdk.py` for execution quality reporting. Every run
automatically reports trace_id, status (success/biz_fail/sys_fail/cancel), error code, cost, and
masked input/output to the operations console.

### Integration

- **Python entry point:** wrap main logic with the `quality_context` context manager:

  ```python
  from skill_quality_sdk import quality_context, QualityError

  with quality_context(skill_name="huawei-cloud-cts-trace-management", skill_version="1.0.0") as q:
      q.input = {"action": "huawei_list_cts_trackers", "region": "cn-north-4"}
      result = run_hcloud_command(...)
      q.output = result
  ```

- **CLI-only Skill:** the SDK is vendored in `scripts/` for future Python wrapper use.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env, C02 missing project_id |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

Reporting is non-blocking and fails silently — it never interrupts the Skill main flow.
Disable via `SKILL_QUALITY_DISABLE=1` for local testing.

## KooCLI Command Format Standard

The generic invocation shape is `hcloud <service> <Operation> --cli-region=<region> [--key=value ...]`
— this is a **format description only**: `<...>` and `[--key=value]` are placeholders, never executed verbatim.

| Feature | Rule | Example |
|---------|------|---------|
| Service name | `CTS` (metadata directory `cts`; case-insensitive for invocation) | `hcloud CTS ListTrackers` |
| Operation name | PascalCase | `ListTrackers`, `CreateTracker` |
| Region parameter | `--cli-region=<value>` always included | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--project_id=xxx` |
| Indexed parameter | `--key.1=value1` | `--operations.1.service_type=ECS` |
| Nested parameter | `--parent.child=value` | `--obs_info.bucket_name=xxx` |
| Verification | Run `--help` first; parameter names come from `--help` output only | `hcloud CTS ListTraces --cli-region=cn-north-4 --help` |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for CTS
- `references/cli-installation-guide.md` — hcloud CLI installation and AK/SK/profile authentication
- `references/verification-method.md` — Verification procedures for query/analyze/manage actions
- `references/dataflow-diagram.md` — Mermaid data flow diagrams
- `references/acceptance-criteria.md` — Acceptance criteria for this skill