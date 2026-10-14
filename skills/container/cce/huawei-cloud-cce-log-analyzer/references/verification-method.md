
# Feature Verification Steps

## Overview

Functional verification process for the huawei-cloud-cce-log-analyzer skill (hcloud + kubectl / kubectl cce architecture). Run these checks before relying on the skill in a new environment.

## Verification Checklist

| No. | Verification Item | Command |
|-----|-------------------|---------|
| 1 | hcloud version (>= 7.2.2) | `hcloud version` |
| 2 | kubectl + kubectl-cce plugin installed | `kubectl cce --help` |
| 3 | Credentials env vars set | `echo $HW_ACCESS_KEY $HW_SECRET_KEY` (+ `$HW_SECURITY_TOKEN` for temp credentials) |
| 4 | hcloud -> CCE connectivity | `hcloud CCE ListClusters --cli-region=cn-north-4` |
| 5 | LTS connectivity | `hcloud LTS ListLogGroups --cli-region=cn-north-4` |
| 6 | Pod stdout logs | `python3 scripts/huawei-cloud.py huawei_get_pod_stdout_logs region=cn-north-4 cluster_id=<uuid> namespace=default pod_name=<pod>` |
| 7 | CCE LogConfig list | `python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs region=cn-north-4 cluster_id=<uuid>` |
| 8 | CCE audit logs | `python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs region=cn-north-4 cluster_id=<uuid> hours=1` |
| 9 | kube-apiserver logs | `python3 scripts/huawei-cloud.py huawei_query_kube_apiserver_logs region=cn-north-4 cluster_id=<uuid> hours=1` |
| 10 | kube-scheduler logs | `python3 scripts/huawei-cloud.py huawei_query_kube_scheduler_logs region=cn-north-4 cluster_id=<uuid> hours=1` |
| 11 | Application logs | `python3 scripts/huawei-cloud.py huawei_query_application_logs region=cn-north-4 cluster_id=<uuid> namespace=<ns> app_name=<app>` |
| 12 | LTS Access Config list | `python3 scripts/huawei-cloud.py huawei_list_lts_access_configs region=cn-north-4` |

## Verification Steps

### Step 1: Toolchain Check

```bash
# hcloud must be 7.2.2+
hcloud version

# kubectl + kubectl-cce plugin for Pod logs and LogConfig tools
kubectl cce --help

# LTS SDK retained only for K8S_CCE access config creation
python3 -c "import huaweicloudsdklts; print('lts sdk ok')"
```

### Step 2: Credential Check

```bash
# Permanent credentials
echo "AK=${HW_ACCESS_KEY:0:4}... SK=${HW_SECRET_KEY:0:4}..."

# Temporary credentials (optional) — must be set together with AK/SK
echo "SecurityToken set: $([ -n "$HW_SECURITY_TOKEN" ] && echo yes || echo no)"
```

Expected: AK and SK prefixes are visible (never print full values). If `HW_SECURITY_TOKEN` is set, all three must be set together. Explicit `--cli-access-key` / `--cli-secret-key` (with optional `--cli-security-token`) bypass profile and environment fallback.

### Step 3: hcloud + LTS Connectivity Test

```bash
hcloud CCE ListClusters --cli-region=cn-north-4
hcloud LTS ListLogGroups --cli-region=cn-north-4
```

Expected: JSON lists (possibly empty) with no `[NETWORK_ERROR]` / `[OPENAPI_ERROR]` tags.

### Step 4: Verify Query Functions

```bash
# Pod stdout (kubectl with the kubectl cce plugin for cluster access)
python3 scripts/huawei-cloud.py huawei_get_pod_stdout_logs region=cn-north-4 cluster_id=<uuid> namespace=default pod_name=<pod> tail_lines=50
```

Expected: `{"success": true, "logs": ...}` with an `access_method` of `kubectl_cce_plugin`.

```bash
# CCE LogConfig list (requires Cloud Native Logging add-on)
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs region=cn-north-4 cluster_id=<uuid>
```

Expected: `{"success": true, "logconfigs": [...]}`.

```bash
# Audit logs (requires CCE audit log switch enabled)
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs region=cn-north-4 cluster_id=<uuid> hours=1
```

Expected: `{"success": true, "summary": {"matched_events": N, ...}}`.

```bash
# kube-apiserver / kube-scheduler (requires matching Log Center switch)
python3 scripts/huawei-cloud.py huawei_query_kube_apiserver_logs region=cn-north-4 cluster_id=<uuid> hours=1
python3 scripts/huawei-cloud.py huawei_query_kube_scheduler_logs region=cn-north-4 cluster_id=<uuid> hours=1
```

Expected: `{"success": true, "logs": [...], "component": "kube-apiserver" | "kube-scheduler"}`.

```bash
# Application logs (auto-discovery requires the collection rule to cover ns/app)
python3 scripts/huawei-cloud.py huawei_query_application_logs region=cn-north-4 cluster_id=<uuid> namespace=<ns> app_name=<app> hours=1
```

Expected: `{"success": true, "log_group_id": ..., "log_stream_id": ..., "logs": [...]}`. When no single rule covers the pair, the tool reports candidate rules and asks for a selector.

### Step 5: Verify Analysis Functions

```bash
python3 scripts/huawei-cloud.py huawei_analyze_application_logs region=cn-north-4 cluster_id=<uuid> namespace=<ns> app_name=<app> hours=1
python3 scripts/huawei-cloud.py huawei_analyze_kube_apiserver_logs region=cn-north-4 cluster_id=<uuid> hours=1 slow_latency_ms=1000
python3 scripts/huawei-cloud.py huawei_analyze_kube_scheduler_logs region=cn-north-4 cluster_id=<uuid> hours=1
python3 scripts/huawei-cloud.py huawei_analyze_cce_audit_timeline region=cn-north-4 cluster_id=<uuid> resource_names='["<pod>"]'
```

Expected: `{"success": true, "summary": {...}, "anomaly_samples": [...]}`. Read-only; these tools never modify cluster resources.

### Step 6: Verify Manage Functions (preview + confirm)

```bash
# Preview first — confirmation required
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig region=cn-north-4 cluster_id=<uuid> logconfig_name=test source_type=container_stdout log_group_id=<gid> log_stream_id=<sid>
```

Expected: `{"success": false, "requires_confirmation": true, "request_body": {...}}` with no change applied. Re-run with `confirm=true` to apply; re-running a create on an existing rule requires `update_existing=true`.

```bash
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig region=cn-north-4 cluster_id=<uuid> logconfig_name=test
```

Expected: preview of the target rule; re-run with `confirm=true` to delete.

```bash
python3 scripts/huawei-cloud.py huawei_create_lts_access_config region=cn-north-4 access_config_name=cfg source_type=K8S_CCE ...
python3 scripts/huawei-cloud.py huawei_delete_lts_access_config region=cn-north-4 access_config_id=<id>
```

Expected: preview then confirmed apply/delete as above. Duplicate LTS Access Config names are rejected.

## Scope And Cleanup

- All query and analysis tools are read-only (R3) and run automatically without confirmation.
- Create/delete LogConfig and LTS Access Config are management tools (R2/R1) that always preview and require `confirm=true` before applying.
- No log data, log groups, or log streams are deleted by this skill; only the collection rule is removed.
- After verification, remove any test LogConfig / LTS Access Config rule created during the run so no collection change is left behind.
