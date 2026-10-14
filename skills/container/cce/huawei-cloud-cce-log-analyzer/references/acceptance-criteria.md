
# Acceptance Criteria — huawei-cloud-cce-log-analyzer

## 1. Query Tools (Read-only, R3 — automatic execution)

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 1.1 | Pod stdout logs | `huawei_get_pod_stdout_logs` with `namespace`, `pod_name`, `tail_lines` | `{"success": true, "logs": ...}` with `access_method` set |
| 1.2 | Previous container logs | Same tool with `previous=true` | Returns previous terminated container output or a clear error |
| 1.3 | CCE LogConfig list | `huawei_get_cce_logconfigs` with `cluster_id` | Returns rules with name/namespace/source type |
| 1.4 | LTS Access Config list | `huawei_list_lts_access_configs` | Returns all access configs (optionally by name) |
| 1.5 | Application logs (explicit rule) | `huawei_query_application_logs` with a unique `logconfig_name` / `access_config_name` / `access_config_id` | Returns `{log_group_id, log_stream_id, logs}` |
| 1.6 | Application logs (auto-discovery) | Same tool with only `namespace` + `app_name` | Single candidate -> logs; multiple -> selector required; none -> clear error |
| 1.7 | Audit logs | `huawei_query_cce_audit_logs` with `hours` | Returns parsed events + top users/verbs/resources |
| 1.8 | kube-apiserver logs | `huawei_query_kube_apiserver_logs` | Returns recent apiserver logs |
| 1.9 | kube-scheduler logs | `huawei_query_kube_scheduler_logs` | Returns recent scheduler logs |

## 2. Analysis Tools (Read-only, R3 — automatic execution)

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 2.1 | Application log anomaly analysis | `huawei_analyze_application_logs` | Returns severity counts, abnormal ratio, incident windows, top patterns, recovery time |
| 2.2 | Pod realtime log analysis | `huawei_analyze_pod_stdout_realtime_logs` with `wait_seconds` | Samples twice, analyzes only newly produced lines |
| 2.3 | Audit timeline analysis | `huawei_analyze_cce_audit_timeline` with optional `resource_names` | Builds per-resource create/update/delete timeline and lifecycle summary |
| 2.4 | kube-apiserver analysis | `huawei_analyze_kube_apiserver_logs` with `slow_latency_ms` | Returns status-code distribution, latency stats (incl. WATCH split), anomaly samples |
| 2.5 | kube-scheduler analysis | `huawei_analyze_kube_scheduler_logs` | Returns scheduling/binding/preemption/leader-election anomaly counts |

## 3. Manage Tools (Preview + `confirm=true`)

| # | Acceptance Item | Verification Method | Expected Result |
|---|-----------------|---------------------|-----------------|
| 3.1 | Create CCE LogConfig | `huawei_create_cce_logconfig` without `confirm` | Returns preview (`requires_confirmation=true`); cluster unchanged |
| 3.2 | Confirm create LogConfig | Re-run with `confirm=true` | LogConfig created in `kube-system` (or specified namespace) |
| 3.3 | Create duplicate LogConfig | Re-run create on existing name without `update_existing` | Rejected; requires `update_existing=true` + `confirm=true` |
| 3.4 | Delete CCE LogConfig | `huawei_delete_cce_logconfig` without `confirm` | Returns preview of the target rule; no deletion |
| 3.5 | Confirm delete LogConfig | Re-run with `confirm=true` | LogConfig deleted; collection stops |
| 3.6 | Create LTS Access Config | `huawei_create_lts_access_config` (no confirm) -> confirm | Rule created with preview; duplicate name rejected |
| 3.7 | Delete LTS Access Config | `huawei_delete_lts_access_config` (no confirm) -> confirm | Rule deleted |

> **Risk Expectations:**
> - All query/analysis tools are strictly read-only; they never create, update, or delete resources.
> - Create/delete tools always surface a preview and require `confirm=true` before applying.
> - Delete LogConfig / Access Config is **not reversible** programmatically — the rule must be recreated manually.
> - The skill never modifies workloads, log data, log groups, or log streams.

## 4. Error Handling Acceptance

| # | Acceptance Item | Expected Result |
|---|-----------------|---------------------|
| 4.1 | Invalid `cluster_id` (not UUID / unmatchable name) | Clear error; no LTS/kubectl call issued on malformed UUID |
| 4.2 | Audit collection disabled | Error explaining how to enable it; no crash |
| 4.3 | Control-plane log switch disabled | Error naming the component; no crash |
| 4.4 | Missing namespace/app for auto-discovery | Clear error requiring `namespace` and `app_name` |
| 4.5 | Ambiguous application source | `requires_collection_rule_selection=true` with candidate list |
| 4.6 | Missing confirmation | `requires_confirmation=true` with target/body preview |
| 4.7 | Unauthenticated / insufficient permission | hcloud error surfaced with `success:false`; credentials never printed |
| 4.8 | Invalid `output` value | `output must be summary, samples, or raw` |

## 5. Security Acceptance

| # | Acceptance Item | Expected Result |
|---|-----------------|---------------------|
| 5.1 | No credential logging | AK/SK/tokens never appear in results or error summaries |
| 5.2 | Scoped env access | Only named credential env vars are read; no environment harvesting |
| 5.3 | Read-only default | All log queries execute without mutation; write tools require confirmation |
| 5.4 | No hardcoded secrets | Skill package contains no AK/SK/API keys (gitleaks clean) |
| 5.5 | No prompt injection | No hidden instructions or zero-width characters in metadata files |
