---
name: huawei-cloud-cce-kubernetes-event-analyzer
description: Query and analyze Kubernetes Events in Huawei Cloud CCE clusters. Trigger when users ask about CCE events, Kubernetes warning events, FailedScheduling, FailedMount, ImagePullBackOff, event patterns, historical events in LTS, or event-based diagnosis for a CCE cluster or namespace.
tags: [CCE, Kubernetes, events, observability]
---

# Huawei Cloud CCE Kubernetes Event Analyzer

## Overview

Query and analyze Kubernetes Events in Huawei Cloud CCE clusters to identify warnings, repeated failure patterns, affected resources, and useful diagnosis handoffs. The skill supports a current Event view through `kubectl` and a historical Event view through LTS.

**Architecture**: `python3 scripts/huawei-cloud.py` dispatcher -> `kubectl` through external kubeconfig or `kubectl cce` for current Events / `kubectl cce` LogConfig discovery plus `hcloud LTS ListLogs` for historical Events -> filtering and grouping -> diagnosis handoff.

**Execution Method**: Invoke only the bundled dispatcher. Do not query Kubernetes Events with raw Python Kubernetes SDK calls, direct Kubernetes API calls, or ad hoc cloud commands. The `huawei_get_cce_events` implementation invokes `kubectl` internally: external kubeconfig access first, then the `kubectl cce` plugin fallback.

**Related Skills**:
- `huawei-cloud-kubectl-cce-installer` - Install `kubectl` and the `kubectl-cce` plugin required for cluster access
- `huawei-cloud-cce-metric-analyzer` - CCE and cloud-resource metrics

**Capabilities**:
- Query current Kubernetes Events across a cluster or in a namespace
- Read Events through external `kubectl` kubeconfig access or `kubectl cce`
- Query historical Event records from LTS within an explicit time window
- Filter and group Events by type, reason, namespace, resource, and timestamps
- Check the current status of supported resources referenced by Events
- Analyze a supplied current or historical Event result locally without another cloud request
- Identify repeated warning patterns and hand off evidence to diagnosis skills

**Typical Use Cases**:
- "List Warning events for this CCE cluster"
- "Find repeated FailedScheduling events in namespace default"
- "Query historical ImagePullBackOff events from LTS"
- "Analyze the top Kubernetes event reasons during an incident"

## Prerequisites

### 1. Runtime Dependencies

- Python 3.8+ for the dispatcher and result processing
- `hcloud` (KooCLI) for cluster lookup and temporary external kubeconfig generation
- `kubectl` for current Event reads
- `kubectl-cce` when the cluster has no usable external endpoint; see [kubectl-cce.md](references/kubectl-cce.md)
- `hcloud` LTS command support and the Cloud Native Log Collection add-on (`log-agent`) with a `default-event` Event-to-LTS `LogConfig`. `huawei_query_k8s_events_from_lts` reads `logconfigs.logging.openvessel.io` through `kubectl cce`, then invokes `hcloud LTS ListLogs` using the configured LTS IDs.

### 2. Credential Configuration

- External kubeconfig access uses hcloud credential priority: explicit tool parameters > local hcloud profile > environment variables.
- The `kubectl cce` fallback requires AK/SK and the target cluster's `project_id` from explicit tool parameters or environment variables; encrypted hcloud profile credentials cannot be reused by the plugin. When `project_id` is available, the implementation passes it explicitly as `kubectl cce --project-id <project-id>`.
- LTS queries require valid Huawei Cloud credentials and an authorized project.

**Security Rules**:
- Never print, persist, or hardcode AK/SK, security tokens, kubeconfig content, or temporary client credentials.
- Never use `echo $HUAWEI_AK` or `echo $HUAWEI_SK` to inspect credentials.
- Prefer a local hcloud profile for external kubeconfig access.
- Use least-privilege IAM identities and read-only Kubernetes RBAC permissions.

**Optional Environment Fallback**:

```bash
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_REGION=cn-north-4
export HUAWEI_PROJECT_ID=<project-id>
export HUAWEI_SECURITY_TOKEN=<security-token>
```

### 3. IAM Permission Requirements

| Permission | Purpose |
| ---------- | ------- |
| `cce:cluster:get` | Inspect cluster external endpoint availability |
| `cce:cluster:createCert` | Generate temporary kubeconfig for external `kubectl` access |
| `lts:logs:search` | Query historical Event records in LTS |

The effective Kubernetes identity also needs read-only `get` and `list` permission for Events in the target namespace or cluster.

**Permission Failure Handling**:

1. Report the failed operation and required permission.
2. Ask the user to grant the missing IAM or Kubernetes RBAC permission.
3. Do not retry until the user confirms the permission is ready.

## Core Commands

All commands use the bundled dispatcher:

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

## KooCLI Command Format Standard

Users invoke the dispatcher rather than raw `hcloud` commands. For current Event queries, the dispatcher internally uses hcloud only to inspect the CCE cluster and generate a temporary external kubeconfig when appropriate.

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id>
```

Follow these rules:

- Use `key=value` parameters and quote values containing spaces or special shell characters.
- Do not print or persist credentials, security tokens, or temporary kubeconfig files.
- Use exact `cluster_id` values for cluster-scoped queries.
- Keep LTS queries time-bounded with both `start_time` and `end_time`.

### 1. Current Kubernetes Events

```bash
# Query Warning Events (default)
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id>

# Query Events in a namespace
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id> namespace=default

# Limit returned Event records
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id> limit=100

# Query all Event types only when explicitly needed
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id> event_type=all limit=100
```

The tool returns only Warning Events by default, using the Kubernetes API server-side field selector. It first uses the external endpoint with a temporary kubeconfig; it then falls back to `kubectl cce`. For large clusters, full Event history can be substantial; query all types only after the user explicitly requests it with `event_type=all`.

### 2. Historical Events From LTS

```bash
# Query an explicit historical window
python3 scripts/huawei-cloud.py huawei_query_k8s_events_from_lts \
  region=cn-north-4 cluster_id=<cluster-id> \
  start_time="2026-05-30 06:00:00" \
  end_time="2026-05-30 08:00:00"

# Query with an LTS keyword filter
python3 scripts/huawei-cloud.py huawei_query_k8s_events_from_lts \
  region=cn-north-4 cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" \
  end_time="2026-05-30 23:59:59" \
  keywords=FailedScheduling
```

LTS time format is UTC `YYYY-MM-DD HH:MM:SS`; the tool always interprets input values as UTC, not the local time zone of the host. The cluster must have the Cloud Native Log Collection add-on (`log-agent`) installed and healthy with the `default-event` Event-to-LTS `LogConfig`. The tool uses `kubectl cce --cluster-id <cluster-id> --region <region> get logconfigs.logging.openvessel.io -A -o json`, selects `default-event`, and reads `outputDetail.LTS.ltsGroupID` and `ltsStreamID`. LTS queries default to `event_type=Warning`, using `Warning` as a server-side keyword filter. For large clusters, request full Event history only after user confirmation with `event_type=all`; this removes the type keyword filter. LTS filtering is keyword matching, not a structured-field selector.

### 3. Query and Analyze Event Results

Without `events`, the tool queries and analyzes current cluster Events by default. For historical requests spanning more than one hour, use LTS with a bounded time window. Providing `start_time` or `end_time` automatically selects LTS; `event_source=lts` may also be set explicitly. Passing an `events` array (or a complete response object containing it) retains offline analysis behavior.

```bash
# Query and analyze current Events
python3 scripts/huawei-cloud.py huawei_analyze_cce_events \
  region=cn-north-4 cluster_id=<cluster-id>

# Query and analyze historical LTS Events
python3 scripts/huawei-cloud.py huawei_analyze_cce_events \
  region=cn-north-4 cluster_id=<cluster-id> event_source=lts \
  start_time="2026-05-30 06:00:00" end_time="2026-05-30 08:00:00"

# Analyze supplied Events without a cloud query
python3 scripts/huawei-cloud.py huawei_analyze_cce_events \
  events='[{"type":"Warning","reason":"FailedScheduling","namespace":"default","count":3}]' \
  max_groups=10
```

## Risk Levels

This skill is read-only. It never changes cloud resources, Kubernetes resources, LTS configuration, or local cluster access configuration.

| Level | Meaning | Execution Guidance |
| ----- | ------- | ------------------ |
| R3 | Read-only Event query or local Event analysis | May run automatically |

| Tool | Operation Type | Risk Level | Description |
| ---- | -------------- | ---------- | ----------- |
| `huawei_get_cce_events` | Query | R3 | Query current cluster or namespace Events through `kubectl` |
| `huawei_query_k8s_events_from_lts` | Query | R3 | Query historical Event records from configured LTS collection |
| `huawei_analyze_cce_events` | Query and analyze | R3 | Query current or LTS Events when needed, then aggregate by type, reason, namespace, and resource |

## Parameter Reference

### Common Parameters

| Parameter | Required/Optional | Description | Default |
| --------- | ----------------- | ----------- | ------- |
| `region` | Required | Huawei Cloud region | `HUAWEI_REGION` |
| `cluster_id` | Required | Exact CCE cluster ID | N/A |
| `ak` | Optional | Explicit AK for access paths that support it | profile/environment fallback |
| `sk` | Optional | Explicit SK for access paths that support it | profile/environment fallback |
| `project_id` | Required for `kubectl cce`; optional otherwise | Target cluster's Huawei Cloud project ID | hcloud profile/IAM/environment fallback for external kubeconfig access |

### Current Event Query Parameters

| Tool | Required | Optional |
| ---- | -------- | -------- |
| `huawei_get_cce_events` | `region`, `cluster_id` | `namespace`, `event_type` (`Warning` default, `Normal`, or `all`), `limit`, `ak`, `sk`, `project_id` (required for `kubectl cce`), `security_token` |

### Historical Event Query Parameters

| Tool | Required | Optional |
| ---- | -------- | -------- |
| `huawei_query_k8s_events_from_lts` | `region`, `cluster_id`, `start_time`, `end_time`, `project_id` | `event_type` (`Warning` default, `Normal`, or `all`), `keywords` (requires `event_type=all`), `ak`, `sk` |

### Event Analysis Parameters

| Tool | Required | Optional |
| ---- | -------- | -------- |
| `huawei_analyze_cce_events` | Either `events`, or `region` + `cluster_id` | `event_source` (`current` default or `lts`), `start_time`/`end_time` (required for `lts`), `namespace`, `event_type`, `keywords`, `limit`, `max_groups` (1-100, default 10), `check_resource_status` (default true when `region` and `cluster_id` are present), `ak`, `sk`, `project_id`, `security_token` |

## Output Format

All public response fields, Event record fields, and resource-status states are defined in [output-schema.md](references/output-schema.md). That reference is the single source of truth for output contracts.

## Workflow

1. Identify `region`, exact `cluster_id`, optional namespace, and incident time window.
2. Use `huawei_get_cce_events` for current Event inspection.
3. Use `huawei_query_k8s_events_from_lts` for historical Event windows longer than one hour, or when a precise LTS time range or keyword filtering is required.
4. Pass the returned `events` to `huawei_analyze_cce_events` to aggregate reasons, namespaces, resources, and repeated patterns.
5. Hand off evidence to the relevant Pod, Workload, Node, Storage, or Network diagnosis skill.

See [workflow.md](references/workflow.md) for pattern recognition and time-window analysis guidance.

## Verification

Run a current Event query first:

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 cluster_id=<cluster-id> limit=10
```

When default Event-to-LTS collection is enabled, verify a bounded historical query:

```bash
python3 scripts/huawei-cloud.py huawei_query_k8s_events_from_lts \
  region=cn-north-4 cluster_id=<cluster-id> \
  start_time="2026-05-30 06:00:00" \
  end_time="2026-05-30 07:00:00"
```

Verify that the current Event response includes `access_method`, and that the LTS response identifies the default LTS group and stream. Do not create or change logging configuration as part of verification.

## Best Practices

1. **Start with warnings** - filter `type == "Warning"` before detailed inspection.
2. **Group by reason** - repeated reasons reveal systemic issues faster than individual records.
3. **Use exact cluster IDs** - do not infer a cluster from its name.
4. **Keep LTS windows bounded** - use the smallest incident window that answers the question.
5. **Use LTS for history** - current Kubernetes Events have limited retention.
6. **Hand off rather than remediate** - this skill provides evidence only.

## Notes

- No active warning does not prove a cluster is healthy; inspect historical LTS Events for recent or recovered incidents when available.
- The Event-to-LTS path depends on a healthy log-agent add-on with default Event collection enabled.
- Event summaries should redact sensitive production workload, Pod, and node identifiers where the audience does not need them.
- Do not modify Kubernetes, CCE logging, LTS, or cloud resources through this skill.

## Troubleshooting

| Symptom | Likely Cause | Action |
| ------- | ------------ | ------ |
| External kubeconfig access fails | No external endpoint, invalid profile, or missing CCE permission | Verify `cce:cluster:get` and `cce:cluster:createCert`; the tool then tries `kubectl cce` |
| `kubectl cce` fallback fails | Plugin missing or plugin credentials unavailable | Install/configure the plugin using [kubectl-cce.md](references/kubectl-cce.md) |
| LTS query finds no default Event stream | Default Event collection is not enabled or has not finished provisioning | Enable default Event collection through the log-agent add-on, then retry |
| LTS query returns no records | Time window, keywords, retention, or event collection does not match | Narrow or correct the window and verify the default LTS group and stream |
| Too many current Events | Broad cluster query | Warning is the default; provide `namespace` and a lower `limit` to further reduce data at the source |
| Permission denied | Missing IAM or Kubernetes RBAC permission | Grant the reported least-privilege permission, then retry |

## Limitations

- The skill provides only the two documented read-only Event tools.
- Current Event queries support only namespace and Event type (`Warning`, `Normal`, or `all`) server-side selection.
- Historical queries require default Event-to-LTS collection enabled before the incident; the skill cannot recover uncollected history.
- The skill cannot create, modify, or delete LTS streams, Kubernetes resources, or CCE resources.
- The skill does not automatically select a cluster, namespace, event filter, or diagnosis/remediation action for the user.

## References

| Document | Use |
| -------- | --- |
| [Workflow](references/workflow.md) | Event query sequence, grouping, patterns, and time-window analysis |
| [Risk Rules](references/risk-rules.md) | Read-only boundaries, redaction, and handoff constraints |
| [Output Schema](references/output-schema.md) | Query, analysis, and Event record fields |
| [kubectl-cce](references/kubectl-cce.md) | kubectl-cce installation, credentials, and access fallback |
| [Acceptance Criteria](references/acceptance-criteria.md) | Expected outcomes for current, historical, and combined query-and-analysis flows |
