# Output Schema

## Log Query Summary

When querying logs (Pod stdout, application logs, or audit logs), prefer this output structure:

| Field           | Description                                                     |
| --------------- | --------------------------------------------------------------- |
| `region`        | Huawei Cloud region                                             |
| `cluster_id`    | CCE cluster ID when querying Kubernetes or CCE application logs |
| `namespace`     | Kubernetes namespace when available                             |
| `pod_name`      | Pod name when available                                         |
| `container`     | Container name when available                                   |
| `log_group_id`  | LTS log group ID when querying LTS                              |
| `log_stream_id` | LTS log stream ID when querying LTS                             |
| `time_range`    | Effective start/end time or recent-hours window                 |
| `keywords`      | Keyword filter used                                             |
| `total`         | Number of returned log entries                                  |
| `has_more`      | Whether an LTS scroll id indicates more data                    |
| `filter_quality` | Application-log filter precision: `exact`, `partial`, or `unscoped` |
| `filter_reason` | Indexed identity labels actually applied to the LTS query       |
| `analysis_scope_note` | Boundary for attributing findings from a shared log stream |
| `output` | Query response level: `summary`, `samples`, or `raw` |
| `identity_label_fields` | Indexed label aliases selected for cluster, namespace, and application |

## Application Log Collection Rule

| Field | Description |
|------|-------------|
| `collection_mode` | `cce_logconfig` or `lts_access_config` |
| `rule_name` / `rule_id` | Collection-rule identity; LTS Access Config has an ID |
| `source_type` | `container_stdout` or `container_file` |
| `log_group_id` / `log_group_name` | LTS destination log group |
| `log_stream_id` / `log_stream_name` | LTS destination log stream |

For application logs, `exact` requires the LTS query to apply indexed `clusterId`, `nameSpace`, and `appName` labels matching the request. `partial` means only some identity labels were applied; `unscoped` means none were applied. In the latter two cases, statistics and findings describe only the returned log set and must not be attributed conclusively to the requested application.

## LogConfig Preview Summary

When previewing LogConfig creation or deletion:

| Field            | Description                                               |
| ---------------- | --------------------------------------------------------- |
| `request_body`   | Generated LogConfig specification (create preview)        |
| `existing`       | Current LogConfig details being targeted (delete preview) |
| `action`         | `create` or `delete`                                      |
| `logconfig_name` | LogConfig policy name                                     |
| `namespace`      | LogConfig namespace                                       |

## Audit Log Summary

| Field          | Description                                           |
| -------------- | ----------------------------------------------------- |
| `audit_type`   | Keyword preset used (`pod_delete`, `workload_change`) |
| `verbs`        | Operation verbs found (delete, create, update, etc.)  |
| `users`        | Actors performing operations                          |
| `resources`    | Resource types affected                               |
| `namespaces`   | Namespaces affected                                   |
| `status_codes` | Response status codes distribution                    |
| `event_count`  | Number of audit events returned                       |
| `top_events`   | Top audit events with counts and timestamps           |

## Analysis Summary

When analyzing logs, prefer this structure:

| Field                | Description                                         |
| -------------------- | --------------------------------------------------- |
| `error_patterns`     | Recurring error messages or stack trace roots       |
| `first_seen`         | Earliest returned timestamp for a pattern           |
| `last_seen`          | Latest returned timestamp for a pattern             |
| `affected_resources` | Pods, containers, workloads, or namespaces involved |
| `evidence`           | Short redacted examples, not full raw logs          |
| `next_steps`         | Suggested follow-up query or diagnosis skill        |

## Control-Plane Log Summary

| Component | Important fields | Interpretation |
|---|---|---|
| kube-apiserver | `non_200_count`, `successful_non_200_count`, `non_success_status_count`, `watch_latency`, `non_watch_latency`, `slow_watch_count` | `non_200_count` is literal. Use `non_success_status_count` and `non_watch_latency` for health conclusions. WATCH duration is connection lifetime. |
| kube-scheduler | `successful_assignment_count`, `leader_renewal_count`, `scheduling_failure`, `binding_failure`, `preemption_issue`, `leader_election_issue`, `generic_abnormal_count` | Repeated scheduler messages can be retries for one Pod. Group samples by Pod and constraint before reporting impact. |

Control-plane query outputs include `component`, `log_group_name`, `log_stream_name`, `analysis_window`, and `query_summary`. When a control-plane switch is disabled, the output contains `requires_control_plane_log` and no log query is attempted.

## Abnormality Analysis Output

| Field | Description |
|------|-------------|
| `abnormal_ratio` | Percentage of abnormal logs vs total |
| `log_rate_total` | Total log entries per time unit |
| `log_rate_abnormal` | Abnormal log entries per time unit |
| `first_abnormal_time` | First abnormal log timestamp |
| `last_abnormal_time` | Last abnormal log timestamp |
| `recovery_time` | Observed recovery timestamp (if detected) |
| `incident_windows` | Time windows where abnormality is concentrated |
| `top_patterns` | Top recurring abnormal patterns with counts |
| `status_code_distribution` | HTTP status code counts (especially 5xx) |
| `samples` | Redacted sample abnormal log entries |
| `exception_fingerprints` | Deduplicated abnormal-message groups with count and time range |
| `next_steps` | Follow-up actions derived from filter precision and observed anomalies |
