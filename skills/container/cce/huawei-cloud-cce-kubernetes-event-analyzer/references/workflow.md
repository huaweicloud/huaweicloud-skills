# Event Query Workflow

## Event Query Sequence

1. Identify `region`, `cluster_id`, and optional `namespace` from the user query.
2. Use `huawei_get_cce_events` for current Events. Use `huawei_query_k8s_events_from_lts` for historical windows longer than one hour.
3. Apply follow-up filters based on user needs:
   - `reason` patterns (FailedScheduling, ImagePullBackOff, FailedMount, etc.)
   - `involved_object.kind` / `involved_object.name` for specific resources
   - `first_timestamp` / `last_timestamp` for time-window analysis
4. Group events by `reason`, `type`, or `namespace`.
5. Summarize top reasons, repeated patterns, and affected resources.

## Event Pattern Recognition

| Pattern | Likely Cause | Handoff Target |
|---------|-------------|---------------|
| `ImagePullBackOff` repeated | Wrong image or pull secret missing | `huawei-cloud-cce-pod-failure-diagnoser` |
| `FailedScheduling` + `insufficient` | Resource pressure or node not ready | `huawei-cloud-cce-workload-failure-diagnoser` |
| `FailedMount` | Volume attach or PVC issue | `huawei-cloud-cce-storage-failure-diagnoser` |
| `Evicted` pods | Budget disruption or node pressure | `huawei-cloud-cce-pod-failure-diagnoser` |
| `NodeNotReady` | Node agent or network issue | `huawei-cloud-cce-node-failure-diagnoser` |
| `Unhealthy` + Readiness probe | Application issue or startup failure | `huawei-cloud-cce-pod-failure-diagnoser` |
| `FailedCreatePodSandBox` | CNI or network issue | `huawei-cloud-cce-network-failure-diagnoser` |
| `OOMKilled` | Memory limit exceeded | `huawei-cloud-cce-pod-failure-diagnoser` |

## Time-Window Analysis

1. Events include `first_timestamp` and `last_timestamp` fields.
2. If the user provides an incident window, filter events by these timestamps.
3. Compare event frequency before, during, and after the incident window.
4. Flag events that started or peaked during the incident window.
5. Report `warning_count` vs `normal_count` ratio within each window segment.

## Event Aggregation

1. For large event volumes, aggregate by `reason` and show top N patterns with total counts.
2. For repeated events (count > 1), show the first and last timestamp and the object involved.
3. If a namespace has > 50% of events, flag it as high-noise and suggest namespace-level investigation.
4. Report `warning_count` vs `normal_count` to give a quick health signal.

## LTS vs K8s API Selection Guide

| Criteria | Use K8s API (`huawei_get_cce_events`) | Use LTS (`huawei_query_k8s_events_from_lts`) |
|----------|---------------------------------------|---------------------------------------------|
| Current Events or a recent check within one hour | Yes | No (needs time range) |
| Precise time range | No (client-side only) | Yes (server-side filter) |
| Keyword search | No (client-side only) | Yes (keywords parameter) |
| Historical Events over one hour | No | Yes |
| Requires Kubernetes LogConfig | No | Yes (`default-event` with LTS output) |
| Default route | Primary for current Events | Primary for historical windows over one hour |
