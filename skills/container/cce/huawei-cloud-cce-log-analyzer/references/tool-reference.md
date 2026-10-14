# Tool Reference

Run every command from this skill directory:

```bash
python3 scripts/huawei-cloud.py help
python3 scripts/huawei-cloud.py <action> key=value ...
```

All actions require `region`; cluster-scoped actions also require `cluster_id`. Pass `ak`, `sk`, and `project_id` only when the local hcloud profile is not the intended credential source. Do not print credential values.

### Explicit CLI Credentials

For an isolated credential path, pass `--cli-access-key`, `--cli-secret-key`, and optionally `--cli-security-token`. Both key parameters are required together. The skill forwards them to every hcloud and `kubectl cce` invocation and does not read profile or credential environment-variable values for that call. Use `--cli-project-id` when the target project must be explicit.

```bash
python3 scripts/huawei-cloud.py huawei_query_kube_apiserver_logs \
  region=<region> cluster_id=<cluster-id> hours=1 \
  --cli-access-key=<ak> --cli-secret-key=<sk> \
  --cli-security-token=<sts-token> --cli-project-id=<project-id>
```

## Read and Analyze

| Tool | Required parameters | Useful optional parameters | Notes |
|---|---|---|---|
| `huawei_get_pod_stdout_logs` | `region`, `cluster_id`, `namespace`, `pod_name` | `container`, `previous`, `tail_lines` | Pod name and namespace are both required. `tail_lines` defaults to 1000; `previous=true` reads a terminated container instance. |
| `huawei_analyze_pod_stdout_realtime_logs` | `region`, `cluster_id`, `namespace`, `pod_name` | `container`, `wait_seconds`, `tail_lines` | Pod name and namespace are both required; samples twice and `wait_seconds` defaults to 30. |
| `huawei_get_cce_logconfigs` | `region`, `cluster_id` | `namespace`, `project_id` | Requires Cloud Native Logging add-on. `namespace` defaults to `kube-system`; `project_id` is optional when explicit CLI credentials are used. |
| `huawei_list_lts_access_configs` | `region` | `access_config_name` | Filter returned rules by target `cluster_id` before showing users application-log choices. |
| `huawei_query_application_logs` | `region`, `cluster_id`, and one rule selector or `namespace` + `app_name` | `hours`, `start_time`, `end_time`, `keywords`, `auto_paginate`, `max_pages`, `limit` | Without a selector, discover CCE LogConfig and LTS Access Config candidates. A unique candidate is used; multiple candidates require user choice. |
| `huawei_analyze_application_logs` | `region`, `cluster_id`, and one rule selector or `namespace` + `app_name` | Same as query plus `sample_limit` | Avoid `keywords` when reporting an unscoped abnormal ratio. |
| `huawei_query_cce_audit_logs` | `region`, `cluster_id` | `audit_type`, `pod_name`, `resource_name`, `namespace`, `hours`, `start_time`, `end_time` | Convenience filters are LTS keyword filters, not structured API filters. |
| `huawei_analyze_cce_audit_timeline` | `region`, `cluster_id` | `resource_name`, `resources`, `namespace`, `verbs`, `hours`, `timeline_limit` | Defaults to mutating verbs; use `include_read_events=true` only when needed. |
| `huawei_query_kube_apiserver_logs` | `region`, `cluster_id` | `hours`, `start_time`, `end_time`, `keywords`, pagination parameters | Requires kube-apiserver control-plane logging. |
| `huawei_analyze_kube_apiserver_logs` | `region`, `cluster_id` | `hours`, `slow_latency_ms`, pagination parameters, `sample_limit` | Use `non_success_status_count` and `non_watch_latency` for health conclusions. |
| `huawei_query_kube_scheduler_logs` | `region`, `cluster_id` | `hours`, `start_time`, `end_time`, `keywords`, pagination parameters | Requires kube-scheduler control-plane logging. |
| `huawei_analyze_kube_scheduler_logs` | `region`, `cluster_id` | `hours`, pagination parameters, `sample_limit` | Reports scheduling, binding, preemption, and leader-election categories. |

### Examples

```bash
# Pod stdout
python3 scripts/huawei-cloud.py huawei_get_pod_stdout_logs \
  region=<region> cluster_id=<cluster-id> namespace=default \
  pod_name=<pod-name> tail_lines=200

# Application logs by namespace and application identity
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=<region> cluster_id=<cluster-id> \
  namespace=<namespace> app_name=<application-name> \
  hours=1 auto_paginate=true max_pages=5 limit=100

# API server latency and status analysis
python3 scripts/huawei-cloud.py huawei_analyze_kube_apiserver_logs \
  region=<region> cluster_id=<cluster-id> hours=1 slow_latency_ms=1000

# Scheduler diagnosis
python3 scripts/huawei-cloud.py huawei_analyze_kube_scheduler_logs \
  region=<region> cluster_id=<cluster-id> hours=1
```

## Collection Rule Changes

| Tool | Required parameters | Additional parameters | Execution rule |
|---|---|---|---|
| `huawei_create_cce_logconfig` | `region`, `cluster_id`, `logconfig_name`, `source_type` | `workload_namespace` + workload selector, or `all_containers=true` + `namespaces`; file-source parameters; destination IDs; `update_existing` | `logconfig_namespace` stores the rule and does not set collection scope. A same-name rule is rejected unless the user reviews the diff and provides `update_existing=true confirm=true`. |
| `huawei_delete_cce_logconfig` | `region`, `cluster_id`, `logconfig_name` | `logconfig_namespace` | Preview exact target first; require confirmation. |
| `huawei_create_lts_access_config` | `region`, `access_config_name` | `access_config_type`, collection-source parameters, destination IDs | Preview first; require confirmation. A same-name rule is rejected and never overwritten. |
| `huawei_delete_lts_access_config` | `region`, `access_config_id` | - | Preview exact target first; require confirmation. |

`source_type` for CCE LogConfig is one of `container_stdout`, `container_file`, or `host_file`. For one workload, use `workload_namespace` (or `namespace`) and `workload_name`/`app_name`. To collect stdout from every container in selected namespaces, use `all_containers=true namespaces='["default","kube-system"]'`; `default,kube-system` is also valid. `[default]` is invalid and rejected. Omit `namespaces` only for all namespaces. `host_file` applies to all eligible cluster nodes; no node selector or namespace filter exists. For LTS Access Config, `K8S_CCE` supports container stdout and file collection through the LTS SDK and requires `namespace_regex` plus `pod_name_regex`; `AGENT` collection requires iCagent.

When destination IDs are omitted during a create preview, the tools list the dedicated `k8s-log-<cluster-id>` destination when available and otherwise list existing LTS alternatives. The user must explicitly choose and provide both `log_group_id` and `log_stream_id` before creation.
