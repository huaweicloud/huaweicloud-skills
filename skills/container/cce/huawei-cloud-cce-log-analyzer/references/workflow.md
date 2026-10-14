# Workflow

## Kubernetes Pod Stdout Logs

1. Identify `region`, `cluster_id`, `namespace`, `pod_name`, and optional `container`.
2. Use `huawei_get_pod_stdout_logs` for stdout/stderr retrieval through `kubectl`. Cluster access uses the `kubectl cce` plugin.
3. Use `tail_lines` for focused recent output; use `previous=true` for a previously terminated container.
4. Summarize errors, warnings, stack traces, restarts, or repeated messages.
5. If logs indicate Pod startup, image pull, scheduling, node, or network failures, hand off to the relevant diagnosis skill with exact evidence.

**Example workflow**:

```
User: "Check Pod my-app-xyz123 logs for errors"
  → huawei_get_pod_stdout_logs (tail_lines=200)
  → Summarize: 3 OOMKilled restarts, last crash at 2026-05-30 10:15
  → Recommend: huawei-cloud-cce-pod-failure-diagnoser (OOM pattern detected)
```

## CCE Application Logs Through LTS

All explicit `start_time` and `end_time` values for LTS application and audit log queries use UTC in `YYYY-MM-DD HH:MM:SS` format. When omitted, the tools generate the recent time window in UTC.

### Step 1: Locate Application Collection Rules

When the user provides `namespace` and `app_name`, application-log tools inspect both collection-rule types: CCE LogConfig workload/namespace scope and LTS Access Config namespace/pod regex scope. A unique usable match is selected automatically for this read-only query. If multiple rules match, the tool returns candidates and stops for the user to choose; it never guesses. Only when no usable collection rule exists may the workflow use `huawei_get_pod_stdout_logs`; require `namespace` and an explicit `pod_name` from the user rather than selecting a Pod automatically.

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs \
  region=<region> \
  cluster_id=<cluster-id>

python3 scripts/huawei-cloud.py huawei_list_lts_access_configs \
  region=<region>
```

Show all returned CCE LogConfig rules for the cluster. From the LTS response, show only rules whose `cluster_id` equals the target cluster ID. Do not choose a rule based on a matching workload, namespace, policy name, or destination.

### Step 2: Resolve Multiple Candidates

When multiple rules cover the application, show the returned candidates and require exactly one selector (`logconfig_name` with `logconfig_namespace`, or `access_config_id`) before querying. An explicit selector is also supported when the user already knows the intended rule.

For a shared LTS stream, inspect the result's `filter_quality`: only `exact` confirms that indexed `clusterId`, `nameSpace`, and `appName` filters were applied. With `partial` or `unscoped`, report that other applications may be present and do not attribute error rates or findings conclusively to the requested application.

Selection guidance:
- Use **stdout policies** for standard output logs
- Use **container_file policies** for file logs collected from configured paths (e.g., `/var/log/*.log`)
- For a CCE LogConfig, pass `logconfig_name` and `logconfig_namespace` when needed.
- For an LTS Access Config, pass `access_config_id` (or an unambiguous `access_config_name`).

### Step 3: Query Application Logs

`huawei_query_application_logs` resolves the LTS destination internally. Supply one explicit CCE LogConfig or LTS Access Config selector, or supply `namespace` and `app_name` to discover an applicable rule.

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  namespace=default \
  app_name=<workload-name> \
  hours=1
```

For **recent logs** (time window in hours):

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  access_config_id=<selected-access-config-id> \
  namespace=default \
  app_name=<workload-name> \
  hours=1
```

For **explicit time windows**:

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<selected-logconfig-name> \
  namespace=default \
  app_name=<workload-name> \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00"
```

### Step 4: Paginate Large Results

Use `auto_paginate=true` when more than one LTS page is needed. `limit` controls per-page size and `max_pages` caps total pages fetched.

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  ... \
  auto_paginate=true \
  max_pages=5 \
  limit=100
```

### Step 5: Analyze for Abnormalities

Use `huawei_analyze_application_logs` for time-window abnormality analysis. It accepts an explicit selector or discovers one from `namespace` plus `app_name`, detects exception/error/fatal/timeout/OOM patterns and HTTP 5xx status codes, then returns:

- Abnormal ratio
- Log rates (total and abnormal per time unit)
- First/last abnormal timestamp
- Observed recovery time
- Incident windows
- Top abnormal patterns
- Status-code distribution
- Redacted samples

**Important**: Do not set `keywords` unless the user explicitly wants a keyword-scoped ratio. Keyword filtering changes the denominator to only matched logs, which distorts the abnormal ratio.

```bash
python3 scripts/huawei-cloud.py huawei_analyze_application_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  namespace=<namespace> \
  app_name=<workload-name> \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00" \
  auto_paginate=true \
  max_pages=5 \
  limit=1000
```

## LogConfig Management

`huawei_get_cce_logconfigs`, `huawei_create_cce_logconfig`, and `huawei_delete_cce_logconfig` use the CCE Cloud Native Logging collection mode. They require the Cloud Native Logging add-on to be installed and running in the target cluster. The add-on provides the `logconfigs.logging.openvessel.io` resource used by these tools. Install or recover the add-on before attempting LogConfig discovery or mutation. See the [CCE Cloud Native Logging documentation](https://support.huaweicloud.com/usermanual-cce/cce_10_0416.html).

### List LogConfig Resources

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs \
  region=<region> \
  cluster_id=<cluster-id> \
  namespace=kube-system
```

The query is scoped to one namespace and defaults to `kube-system`; it never uses an all-namespace Kubernetes request. `project_id` is optional when credentials are passed with `--cli-access-key` and `--cli-secret-key`.

### Create a LogConfig (Preview → Confirm)

Before previewing a creation, call the tool without `log_group_id` or `log_stream_id`. When the target cluster's `k8s-log-<cluster-id>` group and streams exist, it lists that dedicated destination. If the group or a stream is missing, it also returns existing LTS log groups and streams as alternatives. Prefer creating the missing dedicated destination, but an existing non-dedicated destination is valid when the user explicitly selects it. The user must provide both IDs in the next call. The tool never creates or selects LTS destinations.

If the same `logconfig_namespace` and `logconfig_name` already exist, creation stops and returns the existing rule plus requested changes. It never overwrites by default. To intentionally update that exact LogConfig, review the diff and provide both `update_existing=true` and `confirm=true`.

1. Call without `confirm=true` to preview the generated `request_body`
2. Inspect the preview output with the user
3. Call with `confirm=true` only after user confirmation

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=container_stdout \
  workload_namespace=default \
  workload_name=<workload-name> \
  workload_kind=Deployment \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>

# Step 2: Confirm (after user review)
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  ... \
  confirm=true
```

For **all container stdout in selected namespaces**, do not provide a workload selector. `logconfig_namespace` remains the namespace where the LogConfig resource is stored and does not control the collection scope.

Pass the actual collection scope through `namespaces`: use `namespaces='["default"]'` for one namespace or `namespaces='["default","kube-system"]'` for several. A comma-separated form such as `namespaces=default,kube-system` is also valid. Omit the parameter only after the user explicitly requests collection from every namespace.

```bash
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=container_stdout \
  all_containers=true \
  namespaces='["default","kube-system"]' \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
```

Omit `namespaces` only when the user explicitly requests stdout collection from every namespace in the cluster.

For **container file collection**:

```bash
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=container_file \
  workload_namespace=default \
  workload_name=<workload-name> \
  workload_kind=Deployment \
  container=<container-name> \
  log_path=/var/log \
  file_pattern="*.log" \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
```

For **node file collection** on every cluster node, use `source_type=host_file`. This mode has no node selector, so inspect the preview carefully before confirmation.

```bash
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=host_file \
  log_path=/var/log/messages \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
```

### Delete a LogConfig (Preview → Confirm)

1. Call without `confirm=true` to preview the exact target summary
2. Inspect the returned `existing` LogConfig details with the user
3. Call with `confirm=true` only after user confirms the exact `logconfig_name` and namespace

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  region=<region> \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  logconfig_namespace=kube-system

# Step 2: Confirm (after user review)
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  ... \
  confirm=true
```

## Kube-apiserver Logs

Use `huawei_query_kube_apiserver_logs` to query the standard control-plane stream `kube-apiserver-<cluster-id>`. The tool first calls `CCE ShowClusterConfig` and returns an error when the kube-apiserver log switch is not enabled; it never enables control-plane logging automatically.

Use `huawei_analyze_kube_apiserver_logs` to analyze the same stream. It reports status-code counts, slow requests above `slow_latency_ms` (default `1000`), latency average/P95/maximum, and error or timeout patterns. `non_200_count` is a literal HTTP count; use `successful_non_200_count` for successful 2xx responses other than 200 and `non_success_status_count` for actual non-2xx responses. The analyzer does not classify HTTP `timeout=<duration>` query parameters or `timeout="<duration>"` request metadata as timeout errors. The `summary.watch_latency` and `summary.non_watch_latency` fields provide independent sample counts, average, P95, and maximum latency, so long-running `WATCH` requests do not obscure normal API request latency. `slow_watch_count` remains available for direct counting.

```bash
python3 scripts/huawei-cloud.py huawei_analyze_kube_apiserver_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  hours=1 \
  slow_latency_ms=1000
```

## Kube-scheduler Logs

Use `huawei_query_kube_scheduler_logs` to query the standard control-plane stream `kube-scheduler-<cluster-id>`. The tool first calls `CCE ShowClusterConfig` and returns an error when the kube-scheduler log switch is not enabled; it never enables control-plane logging automatically.

Use `huawei_analyze_kube_scheduler_logs` to analyze the same stream. It counts successful assignments and leader-renewal messages, then identifies scheduling failures, binding failures, preemption issues, leader-election failures, and remaining generic errors. A scheduling-specific line is classified once under its specific category and is not double-counted as a generic `failed` error.

```bash
python3 scripts/huawei-cloud.py huawei_analyze_kube_scheduler_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  hours=1
```

## LTS Access Config Management

Use these tools for LTS iCagent collection rules managed directly through the LTS API and hcloud. They are independent of CCE LogConfig resources. For CCE application or node collection, install iCagent in the target CCE cluster and verify it is healthy before creating an Access Config; rule creation does not install iCagent. Prefer this mode for high-throughput collection. See the [LTS iCagent documentation](https://support.huaweicloud.com/usermanual-lts/lts_07_1118.html).

### List Access Configs

```bash
python3 scripts/huawei-cloud.py huawei_list_lts_access_configs \
  region=<region>
```

### Create an Access Config (Preview -> Confirm)

If an LTS Access Config with the same `access_config_name` already exists, creation stops and returns the existing rule summary. It never overwrites or deletes an existing Access Config; provide a new name or use a dedicated update workflow.

Before previewing a creation, discover the destination with `region`, `access_config_name`, and `cluster_id`, without `log_group_id` or `log_stream_id`. When the cluster-specific group `k8s-log-<cluster-id>` and its streams exist, the tool lists that dedicated destination. If the group or a stream is missing, it also returns existing LTS log groups and streams as user-selectable alternatives. Prefer creating the missing dedicated destination, but an existing non-dedicated destination is valid when the user explicitly selects it. The user must provide both IDs in the next call. It never creates a log group or log stream and never chooses one on the user's behalf.

```bash
hcloud LTS CreateLogGroup --cli-region=<region> \
  --log_group_name=k8s-log-<cluster-id> --ttl_in_days=<1-365>
hcloud LTS CreateLogStream --cli-region=<region> \
  --log_group_id=<lts-group-id> --log_stream_name=<stream-name>
```

For CCE stdout collection:

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_create_lts_access_config \
  region=<region> \
  access_config_name=<access-config-name> \
  access_config_type=K8S_CCE \
  cluster_id=<cluster-id> \
  path_type=CONTAINER_STDOUT \
  namespace_regex='^default$' \
  pod_name_regex='<pod-name-regex>' \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>

# Step 2: Execute only after user confirmation
python3 scripts/huawei-cloud.py huawei_create_lts_access_config \
  ... \
  confirm=true
```

`K8S_CCE` creation uses the official LTS SDK because hcloud rejects that enum locally. It requires `cluster_id`, `namespace_regex`, and `pod_name_regex`, and supports `CONTAINER_STDOUT` and `CONTAINER_FILE`. Standard-output collection omits `paths` and collects both stdout and stderr unless either switch is explicitly set to false. File collection requires `paths`, `path`, or `log_path`; stdout and stderr are disabled by default. It defaults `container_name_regex` to `^.*$` to match all containers; provide an explicit regex when the scope must be narrowed. It automatically discovers and attaches the exact LTS host group named `k8s-log-<cluster-id>`; provide `host_group_id` only when that standard group cannot be discovered. It uses LTS single-line `format_mode=system` with the current timestamp and requires explicit AK/SK and project ID (or their supported environment variables). Provide `format_mode=wildcard` and `format_value=<time-pattern>` only when logs contain a timestamp that must be parsed.

Use `access_config_type=AGENT` for hcloud and iCagent collection. `AGENT` stdout defaults `paths` to `/var/log/containers`; file collection requires `path_type=CONTAINER_FILE` or `path_type=HOST_FILE` and explicit paths such as `/var/log/messages`. For cluster-scoped `HOST_FILE`, the tool automatically resolves and binds the exact `k8s-log-<cluster-id>` host group; without `cluster_id`, an explicit `host_group_id` is required. Node-file collection applies to every host in the bound group; no node selector is available in this API.

### Delete an Access Config (Preview -> Confirm)

First use `huawei_list_lts_access_configs` to obtain the exact `access_config_id`.

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_delete_lts_access_config \
  region=<region> \
  access_config_id=<access-config-id>

# Step 2: Execute only after user confirmation
python3 scripts/huawei-cloud.py huawei_delete_lts_access_config \
  ... \
  confirm=true
```

## CCE Audit Logs

Use `huawei_query_cce_audit_logs` for Kubernetes audit questions. It is pure keyword search over audit log content in LTS; all convenience parameters are converted into keywords and no parsed-field filtering is applied.

### Audit Type Presets

| `audit_type` | Keywords added | Use case |
|---------------|----------------|----------|
| `pod_delete` | `delete`, `pods` | Find Pod deletion events |
| `workload_change` | Workload-related keywords | Find Deployment/StatefulSet changes |

### Required vs Auto-Discovered Parameters

- The tool first calls `CCE ShowClusterConfig` and requires `audit.enable=true`.
- If LTS IDs are omitted, it resolves the exact group `k8s-log-<cluster-id>` and stream `audit-<cluster-id>` through hcloud.
- Explicit `log_group_id` and `log_stream_id` can be used when the standard LTS names are unavailable.

### Example: Pod Deletion Audit

```bash
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  audit_type=pod_delete \
  namespace=default \
  hours=6 \
  log_group_id=<audit-lts-group-id> \
  log_stream_id=<audit-lts-stream-id>
```

### Example: Workload Change Audit

```bash
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=<region> \
  cluster_id=<cluster-id> \
  audit_type=workload_change \
  namespace=default \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00"
```

### Analyze Resource Change Timeline

Use `huawei_analyze_cce_audit_timeline` to group retained audit events by resource and return observed create, update, patch, and delete times. It supports Pods and workload resources such as Deployments, StatefulSets, DaemonSets, Jobs, and CronJobs. It reports only evidence retained in audit logs and does not determine the resource's current state.

```bash
python3 scripts/huawei-cloud.py huawei_analyze_cce_audit_timeline \
  region=<region> \
  cluster_id=<cluster-id> \
  namespace=default \
  resource_name=<resource-name> \
  resources=deployments,statefulsets \
  hours=24
```

### Audit and Apiserver Evidence

Use audit logs first when the question asks who changed a resource. Audit records include the user and object reference when retained. If a matching audit event is absent, query kube-apiserver logs for the same resource name and time window to confirm HTTP request evidence. Apiserver logs can show verb, URI, response, user agent, and source address, but they are not a replacement for an audit actor record.

### Additional Audit Filter Parameters

All of these are converted into LTS keyword search terms, not structured filters:

| Parameter | Converted to keyword |
|-----------|---------------------|
| `pod_name` | Pod name in audit content |
| `resource_name` | Resource name in audit content |
| `workload_name` | Workload name in audit content |
| `namespace` | Namespace in audit content |
| `user` | User/actor in audit content |
| `verb` | Operation verb (create, delete, update, etc.) |
| `resource` | Resource type (pods, deployments, etc.) |
| `status_code` | Response status code in audit content |

## Analysis Strategy

- Start with the narrowest useful scope: Pod stdout first when the user names a Pod, application LTS logs when they name a workload
- Prefer recent windows (`hours=1`, `tail_lines=100-500`) before broad historical searches
- For workload-level LTS queries, first list target-cluster LogConfig and LTS Access Config rules, then wait for the user to select one
- When summarizing logs, group repeated lines by pattern and include counts when possible
- Redact tokens, passwords, cookies, authorization headers, and personally identifiable data
- If logs point to specific failures, recommend the corresponding diagnosis skill with exact evidence
