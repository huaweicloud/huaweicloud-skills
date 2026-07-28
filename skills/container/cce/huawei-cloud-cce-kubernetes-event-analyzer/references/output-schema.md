# Output Schema

This is the single source of truth for the public response fields emitted by this skill.

## Current Event Response (`huawei_get_cce_events`)

| Field | Description |
| --- | --- |
| `success` | Whether the query completed successfully |
| `region`, `cluster_id` | Requested Huawei Cloud region and CCE cluster ID |
| `namespace` | Requested namespace or `all` |
| `event_type` | Applied Event type filter |
| `access_method` | `kubectl_kubeconfig_external` or `kubectl_cce_plugin` |
| `count`, `limit` | Returned Event record count and requested maximum |
| `events` | Normalized Event records |

## Historical Event Response (`huawei_query_k8s_events_from_lts`)

| Field | Description |
| --- | --- |
| `success` | Whether the LTS query completed successfully |
| `region`, `cluster_id` | Requested Huawei Cloud region and CCE cluster ID |
| `log_group_id`, `log_stream_id` | LTS source identifiers read from `default-event` |
| `event_type`, `keywords` | Applied LTS type and keyword filter |
| `event_count`, `events` | Returned historical Event record count and parsed records |
| `time_range` | Requested UTC start and end time |
| `log_config` | `default-event` LogConfig metadata and discovery method |
| `pagination` | Page count, limit, and whether more results are available |

## Event Analysis Response (`huawei_analyze_cce_events`)

| Field | Description |
| --- | --- |
| `source` | `current`, `lts`, or caller-provided source label |
| `event_records`, `total_occurrences` | Input record count and sum of Event `count` values |
| `event_type_breakdown` | Occurrence totals by Event type |
| `warning_count`, `normal_count` | Warning and Normal occurrence totals |
| `time_range` | First and last observed Event timestamps |
| `top_reasons` | Most frequent reasons with occurrence count, Warning count, and time range |
| `namespace_breakdown`, `affected_objects` | Most affected namespaces and resources |
| `repeated_patterns` | Event records whose `count` is greater than one |
| `resource_status` | Current-state checks for Event resources when `region` and `cluster_id` are available |
| `query` | Source-query metadata when the tool fetched Events itself |

### Resource Status

| Field | Description |
| --- | --- |
| `checked` | Number of distinct resources checked, capped by `max_groups` |
| `summary` | Resource counts grouped by current state |
| `resources` | Per-resource kind, name, namespace, state, and message |
| `state` | `normal`, `abnormal`, `unknown`, `not_found`, `unsupported`, or `query_failed` |

## Normalized Event Record

| Field | Description |
| --- | --- |
| `name`, `namespace` | Event name and namespace when available |
| `type`, `reason`, `message` | Event type, reason, and message |
| `involved_object` | Referenced resource `kind`, `name`, and `namespace` |
| `count` | Number of occurrences represented by the record |
| `first_timestamp`, `last_timestamp` | First and latest observed timestamps |
