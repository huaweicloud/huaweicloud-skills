---
name: huawei-cloud-cce-log-analyzer
description: "Query and analyze Huawei Cloud CCE workload, audit, and control-plane logs. Use when investigating CCE logs, Kubernetes logs, Pod logs, application logs, audit logs, LTS logs, kube-apiserver logs, kube-scheduler logs, log analysis, log collection, 日志查询, 日志分析, 审计日志, 调度器日志."
version: 1.1.0
metadata:
  tags: [cce, kubernetes, logs, lts, observability]
---

# Huawei Cloud CCE Log Analyzer

## Overview

Use this skill for read-only log queries and analysis, or for confirmed management of CCE LogConfig and LTS Access Config collection rules. It does not modify workloads, log groups, log streams, LTS log data, or unrelated cloud resources.

| Need | Use |
|---|---|
| Pod stdout/stderr or previous container output | Pod log tools |
| Application logs collected to LTS | Application log workflow; locate by `namespace` + `app_name` or use a rule selector |
| Pod/workload operation history and actor | Audit log tools |
| API status codes and latency | kube-apiserver log tools |
| Pending Pods and scheduler decisions | kube-scheduler log tools |
| Create or remove collection rules | LogConfig or LTS Access Config tools with preview and confirmation |

## Prerequisites

- Python 3.8+, `hcloud` (≥ 7.2.2), and credentials with the required CCE and LTS permissions.
- Pod stdout and CCE LogConfig tools require `kubectl` with the `kubectl cce` plugin for cluster access.
- **kubectl cce dependency:** The `kubectl cce` plugin provides CCE cluster access. Install it through the dedicated [kubectl-cce installer](../huawei-cloud-kubectl-cce-installer/SKILL.md) skill. Follow the [plugin usage](references/kubectl-cce.md) contract.
- The Cloud Native Logging add-on is required for CCE `LogConfig` tools. LTS `AGENT` collection requires a healthy iCagent.
- Audit, kube-apiserver, and kube-scheduler tools require their matching CCE Log Center switch. The tools check the switch through `CCE ShowClusterConfig` and never enable it.
- Explicit `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token` use only the supplied credentials. AK/SK must be supplied together, and a token requires that pair. They are forwarded to hcloud and `kubectl cce`; profile and credential environment-variable fallback are disabled. `--cli-project-id` or `project_id` can provide the target project when required. Without explicit CLI credentials, the order is `ak`/`sk`/`project_id`, local hcloud profile, then `HW_ACCESS_KEY`, `HW_SECRET_KEY`, and `HW_PROJECT_ID`.
- LTS `start_time` and `end_time` use UTC `YYYY-MM-DD HH:MM:SS`. If omitted, the tools generate a recent UTC window.

### Environment Variables

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Reporting endpoint, default https://skillsapi.developer.myhuaweicloud.com/api/quality/report |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set to `1` to disable reporting (local debugging) |
| `SKILL_QUALITY_TIMEOUT` | No | Report timeout in seconds (default 3) |

## Region Selection

- Use `region=<region>` from the current user request or established task context when it is available.
- If no `region` parameter is supplied, use `HW_REGION_NAME`.
- If neither source provides a region, return an error asking the user to provide `region` or set `HW_REGION_NAME`. Do not infer a target region from an hcloud profile or any other environment variable.

## Core Commands And Tool Routing

| Tool | Risk | Purpose |
|---|---:|---|
| `huawei_get_pod_stdout_logs` | R3 | Get current or previous Pod stdout/stderr |
| `huawei_analyze_pod_stdout_realtime_logs` | R3 | Sample newly produced Pod stdout and analyze it |
| `huawei_get_cce_logconfigs` | R3 | List CCE Cloud Native Logging rules |
| `huawei_list_lts_access_configs` | R3 | List LTS collection rules |
| `huawei_query_application_logs` | R3 | Query application logs from an explicit or uniquely discovered collection rule |
| `huawei_analyze_application_logs` | R3 | Analyze application logs from an explicit or uniquely discovered collection rule |
| `huawei_query_cce_audit_logs` | R3 | Query retained Kubernetes audit events |
| `huawei_analyze_cce_audit_timeline` | R3 | Build a resource change timeline from audit events |
| `huawei_query_kube_apiserver_logs` | R3 | Query kube-apiserver control-plane logs |
| `huawei_analyze_kube_apiserver_logs` | R3 | Analyze API status codes, errors, and latency |
| `huawei_query_kube_scheduler_logs` | R3 | Query kube-scheduler control-plane logs |
| `huawei_analyze_kube_scheduler_logs` | R3 | Analyze scheduling, binding, preemption, and leader-election messages |
| `huawei_create_cce_logconfig` | R2 | Preview and create a CCE LogConfig rule |
| `huawei_create_lts_access_config` | R2 | Preview and create an LTS Access Config rule |
| `huawei_delete_cce_logconfig` | R1 | Preview and remove a CCE LogConfig rule |
| `huawei_delete_lts_access_config` | R1 | Preview and remove an LTS Access Config rule |

Use `python3 scripts/huawei-cloud.py help` to print the available actions and required parameters. Full invocation and parameter details are in [references/tool-reference.md](references/tool-reference.md).

## Parameters And Collection Scope

### Input Parameter Validation

Required parameters must be provided before execution. A required `cluster_id`, or an optional `cluster_id` supplied by the user, must pass the following validation before any cluster-targeted request. Query tools may query the region globally only when their optional `cluster_id` is omitted:
1. Check whether `cluster_id` is a standard UUID:
   - UUID: call `hcloud CCE ShowCluster` to verify it.
   - Otherwise: call `hcloud CCE ListClusters`, perform an exact and unique name match, convert it to a UUID, then call `ShowCluster` to verify it.
If a required `cluster_id` is missing, or any supplied `cluster_id` is invalid, unmatched, or ambiguous, stop the operation and require the user to provide the correct region and cluster ID. A supplied invalid `cluster_id` must never fall back to a global query; never guess or select a cluster. For any other required resource identifier, first use the corresponding read-only query tool to list candidates when the user cannot provide an unambiguous value, then ask the user to choose; never select a candidate automatically.

### Input Parameters

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Region from request context or `HW_REGION_NAME`; otherwise ask the user. |
| `cluster_id` | Operation-specific | Target CCE cluster UUID, or an exact cluster name resolved and verified through hcloud. Required for Pod, LogConfig, audit, control-plane, and application-log operations. |
| `project_id` | Optional | Target project ID. Required by some `kubectl cce` paths; explicit credentials or hcloud profile may supply it where supported. |
| `namespace`, `pod_name`, `container` | Operation-specific | Pod stdout queries require both `namespace` and `pod_name`; `container` narrows a multi-container Pod. |
| `logconfig_name`, `access_config_id`, `access_config_name` | Operation-specific | Optional explicit collection-rule selector. Without one, application-log tools require `namespace` plus `app_name` and discover matching rules. |
| `log_group_id`, `log_stream_id` | Create only | User-selected LTS destination IDs for LogConfig or LTS Access Config creation. |
| `hours`, `start_time`, `end_time` | Optional | Narrow bounded query window; start with `hours=1` when the user has not specified a window. |
| `keywords` | Optional | LTS keyword filter. Do not use it for an unscoped abnormal-ratio analysis unless the user requests keyword-scoped analysis. |
| `limit`, `max_pages`, `auto_paginate`, `sample_limit` | Optional | Result and analysis bounds; expand only when the initial result is insufficient. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | Optional | Explicit credentials forwarded unchanged to hcloud and `kubectl cce`. |

### Tool Parameters

| Tool | Required | Optional |
| --- | --- | --- |
| `huawei_get_pod_stdout_logs` | `region`, `cluster_id`, `namespace`, `pod_name` | `container`, `previous`, `tail_lines` |
| `huawei_analyze_pod_stdout_realtime_logs` | `region`, `cluster_id`, `namespace`, `pod_name` | `container`, `wait_seconds`, `tail_lines` |
| `huawei_get_cce_logconfigs` | `region`, `cluster_id` | `namespace`, `project_id` |
| `huawei_list_lts_access_configs` | `region` | `access_config_name` |
| `huawei_query_application_logs` | `region`, `cluster_id`, and either one rule selector or `namespace` + `app_name` | `hours`, `start_time`, `end_time`, `keywords`, `labels`, `output`, `sample_limit`, `auto_paginate`, `max_pages`, `limit` |
| `huawei_analyze_application_logs` | `region`, `cluster_id`, and either one rule selector or `namespace` + `app_name` | Query options plus `sample_limit` |
| `huawei_query_cce_audit_logs` | `region`, `cluster_id` | `audit_type`, `pod_name`, `resource_name`, `namespace`, `hours`, `start_time`, `end_time` |
| `huawei_analyze_cce_audit_timeline` | `region`, `cluster_id` | `resource_name`, `resources`, `namespace`, `verbs`, `hours`, `timeline_limit`, `include_read_events` |
| `huawei_query_kube_apiserver_logs` | `region`, `cluster_id` | `hours`, `start_time`, `end_time`, `keywords`, `limit`, `max_pages`, `auto_paginate` |
| `huawei_analyze_kube_apiserver_logs` | `region`, `cluster_id` | `hours`, `slow_latency_ms`, `limit`, `max_pages`, `auto_paginate`, `sample_limit` |
| `huawei_query_kube_scheduler_logs` | `region`, `cluster_id` | `hours`, `start_time`, `end_time`, `keywords`, `limit`, `max_pages`, `auto_paginate` |
| `huawei_analyze_kube_scheduler_logs` | `region`, `cluster_id` | `hours`, `limit`, `max_pages`, `auto_paginate`, `sample_limit` |

| Tool | Required | Optional | Notes |
| --- | --- | --- | --- |
| `huawei_create_cce_logconfig` | `region`, `cluster_id`, `logconfig_name`, `source_type` | Source-specific selector or file fields, destination IDs, `update_existing`, `confirm` | A confirmed create requires the source-specific selector/file fields and user-selected `log_group_id` plus `log_stream_id`. |
| `huawei_delete_cce_logconfig` | `region`, `cluster_id`, `logconfig_name` | `logconfig_namespace`, `confirm` | Preview the exact rule before confirmation. |
| `huawei_create_lts_access_config` | `region`, `access_config_name` | `access_config_type`, collection-source fields, destination IDs, `confirm` | A confirmed create requires collection-source fields and user-selected `log_group_id` plus `log_stream_id`. |
| `huawei_delete_lts_access_config` | `region`, `access_config_id` | `confirm` | Preview the exact rule before confirmation. |

### Collection Scope

Use the parameter that controls the collection source, not the namespace where a LogConfig object is stored.

| Collection mode | Namespace parameter | Scope |
| --- | --- | --- |
| CCE LogConfig, one workload stdout or container file | `workload_namespace` (or `namespace`) with `workload_name`/`app_name` | One workload in one namespace. |
| CCE LogConfig, all container stdout in selected namespaces | `all_containers=true` and `namespaces='["default"]'` | All container stdout in the listed namespaces. Use a JSON array or `default,kube-system`; `[default]` is invalid. Omit `namespaces` only when all namespaces are intended. |
| LTS Access Config, `K8S_CCE` container stdout or file | `namespace_regex`, for example `^default$` | Namespace regex; `pod_name_regex` is also required. |
| Node file collection | None | `host_file` applies to all eligible nodes in the bound host group. Namespace filtering does not apply. |

For `huawei_get_pod_stdout_logs` and `huawei_analyze_pod_stdout_realtime_logs`, both `pod_name` and `namespace` are required. Do not infer the namespace or fall back to `default`.

`logconfig_namespace` is only the Kubernetes namespace that stores the LogConfig custom resource, normally `kube-system`; it does not limit which application logs are collected. Review the previewed `request_body` before confirmation.

### `namespaces` Input

Use `namespaces` only with `source_type=container_stdout all_containers=true` to limit collection to one or more application namespaces. It is not the LogConfig storage namespace and is not the single-workload `namespace` selector.

| Intended scope | Input |
| --- | --- |
| One namespace | `namespaces='["default"]'` or `namespaces=default` |
| Multiple namespaces | `namespaces='["default","kube-system"]'` or `namespaces=default,kube-system` |
| Every namespace | Omit `namespaces` entirely, only after the user explicitly requests cluster-wide collection. |

Quote JSON arrays so the shell passes them unchanged. Each value must be a valid Kubernetes namespace name. `[default]` is not a valid input format.

## Operating Workflow

### 1. Identify the source

- A named Pod: use `huawei_get_pod_stdout_logs` first.
- A named application: provide `namespace` and `app_name`; query LTS first through `huawei_query_application_logs`. A unique collection rule is discovered automatically, while multiple matches are presented for the user to choose. Only when no usable collection rule exists may the workflow use `huawei_get_pod_stdout_logs`; require the user to provide the Pod name and do not select one automatically.
- Who changed or deleted a resource: use audit logs first. Audit evidence contains actor information; kube-apiserver logs are supplemental HTTP evidence only.
- API availability or latency: use kube-apiserver analysis. Read `non_success_status_count` for failed HTTP requests and `non_watch_latency` for ordinary API latency.
- Pending or unschedulable workloads: use kube-scheduler analysis. Repeated scheduling/preemption messages are retries, not separate Pods.

### 2. Query narrowly, then expand

Start with `hours=1`, a specific namespace, Pod, or selected collection rule. Use `auto_paginate=true`, `limit`, and `max_pages` only when the initial result is insufficient. Do not apply `keywords` before an application-log abnormal-ratio analysis unless the user explicitly requests keyword-scoped analysis.

For application logs from a shared LTS stream, inspect `filter_quality` before attributing findings: `exact` means indexed `clusterId`, `nameSpace`, and `appName` labels were applied; `partial` or `unscoped` means returned logs can include other applications, so all statistics apply only to the returned set.

Application queries default to `output=summary`; use `output=samples` for a bounded sample or `output=raw` only when full log entries are required. The tool checks indexed aliases including `clusterId`/`cluster_id`/`k8s.cluster.id`, `nameSpace`/`namespace`/`k8s.namespace.name`, and `appName`/`app.kubernetes.io/name`/`app` before it sends label filters to LTS. It also validates `app_name` against current Deployment, StatefulSet, DaemonSet, Job, and CronJob resources in the specified namespace. An unmatched result is a warning, not a query failure, because historical logs can outlive workloads.

When an application query returns no logs, the result includes a prompt to verify `namespace` and `app_name`. If current workload validation is also unmatched, the prompt explicitly calls out that the supplied application name may be incorrect.

### 3. Interpret before acting

- A missing audit event does not disprove an operation; it may be outside retention or absent from audit delivery. Search kube-apiserver logs for the request when that switch is enabled, but do not infer the actor from its user agent alone.
- kube-apiserver `WATCH` duration is connection lifetime, not normal request-processing latency. Use `summary.non_watch_latency` for performance conclusions.
- kube-scheduler `preemption_issue` can accompany a scheduling failure caused by hard constraints such as PV node affinity or pod anti-affinity. Inspect the affected Pod and constraints before recommending capacity changes.
- Redact secrets, tokens, authorization headers, cookies, and personal data in all summaries.

### 4. Mutate only after confirmation

For R2 and R1 tools, discover the destination or exact target, call the tool without `confirm=true`, show the preview, and wait for explicit user confirmation before calling again with `confirm=true`. The skill never creates or selects an LTS log group or stream automatically; the user must provide the selected destination IDs.

## Parameter Confirmation

| Risk Level | Tools | Confirmation Required |
|---|---|---|
| R3 | All query and analysis tools | No — read-only, may run automatically |
| R2 | `huawei_create_cce_logconfig`, `huawei_create_lts_access_config` | Yes — preview the exact collection scope and destination, then wait for explicit user `confirm=true` |
| R1 | `huawei_delete_cce_logconfig`, `huawei_delete_lts_access_config` | Yes — preview the exact existing rule, then wait for explicit user `confirm=true` |

### Confirmation Flow

```
Call without confirm=true → Preview output → User reviews → User confirms → Call with confirm=true
```

- Do not skip preview for any LogConfig or LTS Access Config operation
- Do not call with `confirm=true` without showing the preview first
- Do not assume the preview is correct without user verification

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description |
|---------|-------------|
| Service name | Use the actual service name as detected from KooCLI metadata: `CCE`, `LTS` |
| Operation name | PascalCase, e.g., `ListClusters`, `ShowCluster`, `ListAccessConfig`, `ListLogs` |
| Region parameter | `--cli-region=<value>` |
| Simple parameter | `--key=value` |
| Indexed parameter | `--key.1=value1` for array parameters |

### Verified CLI Commands

| Operation | Required Parameters |
|---|---|
| `hcloud CCE ListClusters` | `--project_id` |
| `hcloud CCE ShowCluster` | `--cluster_id`, `--project_id` |
| `hcloud CCE ShowClusterConfig` | `--cluster_id`, `--project_id` |
| `hcloud LTS ListLogGroups` | `--project_id` |
| `hcloud LTS ListLogStream` | `--log_group_id`, `--project_id` |
| `hcloud LTS ListLogs` | `--log_group_id`, `--log_stream_id`, `--start_time`, `--end_time`, `--project_id` |
| `hcloud LTS ListAccessConfig` | `--project_id` |
| `hcloud LTS CreateAccessConfig` | `--access_config_name`, `--access_config_type`, `--log_info.log_group_id`, `--log_info.log_stream_id`, `--project_id` |
| `hcloud LTS DeleteAccessConfig` | `--access_config_id_list.[N]`, `--project_id` |
| `hcloud LTS ListHostGroup` | `--project_id` |

## References

| Reference | Read when |
|---|---|
| [workflow.md](references/workflow.md) | Following Pod, application, audit, control-plane, or collection-rule workflows |
| [tool-reference.md](references/tool-reference.md) | Choosing parameters or running a command |
| [risk-rules.md](references/risk-rules.md) | Evaluating risk, confirmation, or data-security boundaries |
| [output-schema.md](references/output-schema.md) | Interpreting query and analysis results |
| [kubectl-cce.md](references/kubectl-cce.md) | Using the kubectl cce plugin for cluster access |
| [iam-policies.md](references/iam-policies.md) | Required IAM policies and least-privilege permissions |
| [cli-installation-guide.md](references/cli-installation-guide.md) | Installing and configuring KooCLI and dependencies |
| [verification-method.md](references/verification-method.md) | Verifying toolchain, connectivity, and each action before relying on the skill |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Reviewing acceptance criteria and expected results per tool |

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution quality reporting. Every run automatically reports trace_id, status (success/biz_fail/sys_fail/cancel), error code, cost, and masked input/output to the operations console.

### Integration

- **Python entry point:** wrap main logic with `quality_context` context manager:
  ```python
  from skill_quality_sdk import quality_context, QualityError

  with quality_context(skill_name="huawei-cloud-cce-log-analyzer", skill_version="1.0.0") as q:
      q.input = {...}
      result = do_something()
      q.output = result
  ```
- **CLI-only Skill:** the SDK is vendored in `scripts/` for future Python wrapper use.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

Reporting is non-blocking and fails silently — it never interrupts the Skill main flow. Disable via `SKILL_QUALITY_DISABLE=1` for local testing.

## Output Format

See [output-schema.md](references/output-schema.md) for the response shape. Summaries include the target, time window, source, findings, and any query limits.

## Verification

Confirm the returned source, time window, and collection-rule or Pod target match the requested scope before interpreting results.

## Best Practices

Start with a narrow namespace, Pod, time window, or application identity. For application logs, a unique discovered collection rule is used automatically; multiple matching rules are presented for the user to choose.

## Notes

Missing data can indicate unavailable collection, retention expiry, or an unmatched source rule; it does not prove that the workload is healthy.