# Acceptance Criteria

## Current Events

- `huawei_get_cce_events` returns `success: true`, the requested `cluster_id`, a non-empty `access_method`, and an `events` array when Events exist.
- `huawei_analyze_cce_events` with `region` and `cluster_id` returns `source: current`, a `query` object, and aggregate counters.

## Historical LTS Events

- `huawei_query_k8s_events_from_lts` reads the cluster `default-event` LogConfig through `kubectl cce` and returns its configured LTS group and stream IDs.
- A bounded query that has collected Events returns normalized records with `type`, `reason`, timestamp, and affected-object fields when available.
- `huawei_analyze_cce_events event_source=lts` returns `source: lts`, query time-range metadata, and aggregate counters.

## Analysis Quality

- Analysis returns event-record and occurrence totals, type breakdown, top reasons, namespaces, affected objects, and repeated patterns.
- Supplying an `events` array continues to perform offline analysis without a cloud request.
- Missing credentials, missing LTS collection, inaccessible clusters, and invalid time windows return actionable errors without changing cloud or Kubernetes resources.
