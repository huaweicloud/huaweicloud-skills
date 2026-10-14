"""Application log discovery, query, analysis, and Pod realtime log analysis."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from . import cce, kubectl_client, lts
from .cce_log_common import (
    _APPLICATION_LABEL_ALIASES,
    _analysis_options,
    _build_incident_windows,
    _classify_log,
    _content_of,
    _extract_log_time_ms,
    _format_ts,
    _get_policy_name,
    _new_log_lines,
    _parse_labels,
    _query_logs_with_pagination,
    _recent_lts_window,
    _to_bool,
    _to_int,
)
from .cce_logconfig import get_cce_logconfigs_action


def _extract_logconfig_lts_destination(logconfig: Dict[str, Any]) -> Dict[str, Optional[str]]:
    lts_config = logconfig.get("spec", {}).get("outputDetail", {}).get("LTS", {})
    log_stream_id = lts_config.get("ltsStreamID", lts_config.get("streamID"))
    if not log_stream_id:
        log_stream_id = logconfig.get("spec", {}).get("logConfigStatus", {}).get("LTS", {}).get("streamID")
    return {"log_group_id": lts_config.get("ltsGroupID"), "log_stream_id": log_stream_id}

def _matches_collection_regex(pattern: Any, value: str, allow_pod_suffix: bool = False) -> bool:
    """Return whether one collection-rule regex can cover an application value."""
    if not pattern:
        return True
    try:
        if re.fullmatch(str(pattern), value):
            return True
        return allow_pod_suffix and bool(re.fullmatch(str(pattern), f"{value}-sample"))
    except re.error:
        return False

def _logconfig_covers_application(logconfig: Dict[str, Any], namespace: str, app_name: str) -> bool:
    input_detail = (logconfig.get("spec") or {}).get("inputDetail") or {}
    input_type = str(input_detail.get("type") or "").replace("_", "").replace("-", "").lower()
    if input_type not in {"containerstdout", "containerfile"}:
        return False
    source = input_detail.get("containerStdout") if input_type == "containerstdout" else input_detail.get("containerFile")
    source = source or {}
    if source.get("allContainers") is True:
        namespaces = source.get("namespaces") or []
        return not namespaces or namespace in namespaces
    for workload in source.get("workloads") or []:
        if workload.get("namespace") == namespace and workload.get("name") == app_name:
            return True
    return False

def _application_log_source_candidate(
    collection_rule: Dict[str, Any],
    log_group_id: Optional[str],
    log_stream_id: Optional[str],
    match_basis: str,
) -> Optional[Dict[str, Any]]:
    if not log_group_id or not log_stream_id:
        return None
    return {
        "collection_rule": collection_rule,
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "match_basis": match_basis,
    }

def _discover_application_log_sources(params: Dict[str, str]) -> Dict[str, Any]:
    """Find collection rules that can cover one namespace/application pair."""
    namespace = params.get("namespace")
    app_name = params.get("app_name")
    if not namespace or not app_name:
        return {
            "success": False,
            "error": "namespace and app_name are required when no collection rule is specified",
        }

    candidates: List[Dict[str, Any]] = []
    discovery_errors: List[Dict[str, str]] = []
    logconfig_params = dict(params)
    logconfig_params["namespace"] = params.get("logconfig_namespace") or "kube-system"
    logconfig_result = get_cce_logconfigs_action(logconfig_params)
    if logconfig_result.get("success"):
        for logconfig in logconfig_result.get("logconfigs", []):
            if not _logconfig_covers_application(logconfig, namespace, app_name):
                continue
            destination = _extract_logconfig_lts_destination(logconfig)
            candidate = _application_log_source_candidate(
                {
                    "collection_mode": "cce_logconfig",
                    "rule_name": logconfig.get("name"),
                    "rule_namespace": logconfig.get("namespace"),
                    "rule_id": None,
                    "source_type": (logconfig.get("spec") or {}).get("inputDetail", {}).get("type"),
                    "selector": {
                        "logconfig_name": logconfig.get("name"),
                        "logconfig_namespace": logconfig.get("namespace"),
                    },
                },
                destination.get("log_group_id"),
                destination.get("log_stream_id"),
                "LogConfig workload or namespace scope",
            )
            if candidate:
                candidates.append(candidate)
    else:
        discovery_errors.append({"source": "cce_logconfig", "error": str(logconfig_result.get("error", "unknown error"))})

    access_result = lts.list_access_configs(
        params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if access_result.get("success"):
        for access_config in access_result.get("access_configs", []):
            if access_config.get("cluster_id") != params["cluster_id"]:
                continue
            if not _matches_collection_regex(access_config.get("namespace_regex"), namespace):
                continue
            if not _matches_collection_regex(access_config.get("pod_name_regex"), app_name, allow_pod_suffix=True):
                continue
            candidate = _application_log_source_candidate(
                {
                    "collection_mode": "lts_access_config",
                    "rule_name": access_config.get("access_config_name"),
                    "rule_namespace": None,
                    "rule_id": access_config.get("access_config_id"),
                    "source_type": str(access_config.get("path_type") or "").lower(),
                    "selector": {"access_config_id": access_config.get("access_config_id")},
                },
                access_config.get("log_group_id"),
                access_config.get("log_stream_id"),
                "LTS Access Config namespaceRegex and podNameRegex",
            )
            if candidate:
                candidates.append(candidate)
    else:
        discovery_errors.append({"source": "lts_access_config", "error": str(access_result.get("error", "unknown error"))})

    return {"success": True, "candidates": candidates, "discovery_errors": discovery_errors}

def _resolve_application_log_source(params: Dict[str, str]) -> Dict[str, Any]:
    """Resolve one user-selected collection rule to its LTS destination."""
    logconfig_name = _get_policy_name(params)
    access_config_name = params.get("access_config_name")
    access_config_id = params.get("access_config_id")
    selected = [value for value in (logconfig_name, access_config_name, access_config_id) if value]
    if len(selected) > 1:
        return {
            "success": False,
            "error": "exactly one collection rule is required: logconfig_name, access_config_name, or access_config_id",
        }

    if not selected:
        discovered = _discover_application_log_sources(params)
        if not discovered.get("success"):
            return discovered
        candidates = discovered.get("candidates", [])
        if not candidates:
            return {
                "success": False,
                "error": f"no usable collection rule covers namespace={params.get('namespace')} app_name={params.get('app_name')}",
                "candidate_collection_rules": [],
                "discovery_errors": discovered.get("discovery_errors", []),
            }
        if len(candidates) > 1:
            return {
                "success": False,
                "error": "multiple collection rules cover this application; choose one rule selector and retry",
                "requires_collection_rule_selection": True,
                "candidate_collection_rules": candidates,
                "discovery_errors": discovered.get("discovery_errors", []),
            }
        source = dict(candidates[0])
        source["source_resolution"] = "auto_discovered"
        return {"success": True, **source}


    if logconfig_name:
        lookup_params = dict(params)
        if params.get("logconfig_namespace"):
            lookup_params["namespace"] = params["logconfig_namespace"]
        else:
            lookup_params.pop("namespace", None)
        result = get_cce_logconfigs_action(lookup_params)
        if not result.get("success"):
            return result
        matches = [
            item for item in result.get("logconfigs", [])
            if item.get("name") == logconfig_name
            and (not params.get("logconfig_namespace") or item.get("namespace") == params["logconfig_namespace"])
        ]
        if not matches:
            return {
                "success": False,
                "error": f"CCE LogConfig {logconfig_name} was not found in cluster {params['cluster_id']}",
            }
        if len(matches) > 1:
            return {
                "success": False,
                "error": f"multiple CCE LogConfigs named {logconfig_name} were found; logconfig_namespace is required",
            }
        logconfig = matches[0]
        destination = _extract_logconfig_lts_destination(logconfig)
        if logconfig.get("spec", {}).get("outputDetail", {}).get("type") != "LTS" or not all(destination.values()):
            return {
                "success": False,
                "error": f"CCE LogConfig {logconfig_name} does not have a usable LTS log group and stream destination",
            }
        return {
            "success": True,
            "collection_rule": {
                "collection_mode": "cce_logconfig",
                "rule_name": logconfig.get("name"),
                "rule_namespace": logconfig.get("namespace"),
                "rule_id": None,
                "source_type": logconfig.get("spec", {}).get("inputDetail", {}).get("type"),
            },
            "source_resolution": "explicit_selector",
            **destination,
        }

    result = lts.list_access_configs(
        params["region"],
        access_config_name=access_config_name,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not result.get("success"):
        return result
    matches = [
        item for item in result.get("access_configs", [])
        if item.get("cluster_id") == params["cluster_id"]
        and (not access_config_name or item.get("access_config_name") == access_config_name)
        and (not access_config_id or item.get("access_config_id") == access_config_id)
    ]
    if not matches:
        selector = access_config_id or access_config_name
        return {
            "success": False,
            "error": f"LTS Access Config {selector} was not found for cluster {params['cluster_id']}",
        }
    if len(matches) > 1:
        return {
            "success": False,
            "error": "multiple LTS Access Config rules matched; provide access_config_id",
        }
    access_config = matches[0]
    if not access_config.get("log_group_id") or not access_config.get("log_stream_id"):
        return {
            "success": False,
            "error": f"LTS Access Config {access_config.get('access_config_name')} does not have a usable LTS log group and stream destination",
        }
    return {
        "success": True,
        "collection_rule": {
            "collection_mode": "lts_access_config",
            "rule_name": access_config.get("access_config_name"),
            "rule_namespace": None,
            "rule_id": access_config.get("access_config_id"),
            "source_type": str(access_config.get("path_type") or "").lower(),
        },
        "source_resolution": "explicit_selector",
        "log_group_id": access_config["log_group_id"],
        "log_stream_id": access_config["log_stream_id"],
    }

def _application_filter_precision(
    cluster_id: str,
    namespace: Optional[str],
    app_name: Optional[str],
    labels: Dict[str, str],
) -> Dict[str, str]:
    """Describe whether actual LTS labels isolate one application in a shared stream."""
    expected = {"clusterId": cluster_id, "nameSpace": namespace, "appName": app_name}
    applied = [key for key, value in expected.items() if value and labels.get(key) == value]
    missing = [key for key, value in expected.items() if value and key not in applied]
    if namespace and app_name and not missing:
        return {
            "filter_quality": "exact",
            "filter_reason": "LTS indexed labels isolate clusterId, nameSpace, and appName.",
            "analysis_scope_note": "Results and analysis are scoped to the requested application labels.",
        }
    if applied:
        return {
            "filter_quality": "partial",
            "filter_reason": f"Only these requested identity labels were applied: {', '.join(applied)}; missing: {', '.join(missing) or 'application identity'}.",
            "analysis_scope_note": "A shared log stream may include other applications. Findings apply only to the returned log set, not conclusively to the requested application.",
        }
    return {
        "filter_quality": "unscoped",
        "filter_reason": "No requested application identity label is indexed and applied to the LTS query.",
        "analysis_scope_note": "A shared log stream may include unrelated applications. Findings apply only to the returned log set, not to the requested application.",
    }

def _application_identity_filters(cluster_id: str, namespace: Optional[str], app_name: Optional[str], indexed_fields: Set[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Select one available Kubernetes label alias for each application identity field."""
    values = {"cluster": cluster_id, "namespace": namespace, "app": app_name}
    filters: Dict[str, str] = {}
    chosen: Dict[str, str] = {}
    for identity, value in values.items():
        if not value:
            continue
        field = next((candidate for candidate in _APPLICATION_LABEL_ALIASES[identity] if candidate in indexed_fields), None)
        if field:
            filters[field] = value
            chosen[identity] = field
    return filters, chosen

def _validate_application_workload(params: Dict[str, str], namespace: Optional[str], app_name: Optional[str]) -> Dict[str, Any]:
    """Report whether a named application matches a current common workload."""
    checked_kinds = ["Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"]
    if not namespace or not app_name:
        return {
            "status": "not_requested",
            "checked_workload_kinds": checked_kinds,
        }
    result = kubectl_client.run_kubectl(
        params["region"],
        params["cluster_id"],
        ["get", "deployments,statefulsets,daemonsets,jobs,cronjobs", "--namespace", namespace, "--output=json"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
        explicit_cli_credentials=params.get("_explicit_cli_credentials") == "true",
    )
    if not result.get("success"):
        return {
            "status": "unavailable",
            "checked_workload_kinds": checked_kinds,
            "error": result.get("error"),
        }
    matched_workloads = []
    for item in (result.get("data") or {}).get("items", []):
        metadata = item.get("metadata") or {}
        labels = metadata.get("labels") or {}
        matched_by = "name" if metadata.get("name") == app_name else next((
            key for key in ("app", "app.kubernetes.io/name", "appName", "k8s-app")
            if labels.get(key) == app_name
        ), None)
        if matched_by:
            matched_workloads.append({
                "kind": item.get("kind"),
                "name": metadata.get("name"),
                "matched_by": matched_by,
            })
    return {
        "status": "matched" if matched_workloads else "unmatched",
        "checked_workload_kinds": checked_kinds,
        "matched_workloads": matched_workloads,
        "warning": None if matched_workloads else (
            "No current common workload matches app_name. LTS label matches may represent a deleted workload, "
            "a collector component, or an incorrect application name."
        ),
    }

def _application_query_output_mode(params: Dict[str, str]) -> str:
    mode = (params.get("output") or "summary").lower()
    if mode not in {"summary", "samples", "raw"}:
        raise ValueError("output must be summary, samples, or raw")
    return mode

def _shape_application_query_output(result: Dict[str, Any], mode: str, sample_limit: int) -> Dict[str, Any]:
    result["output"] = mode
    if not result.get("success") or mode == "raw":
        return result
    logs = result.pop("logs", [])
    if mode == "samples":
        result["log_samples"] = logs[:sample_limit]
        result["sample_limit"] = sample_limit
    return result

def _exception_fingerprints(anomalies: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for anomaly in anomalies:
        content = str(anomaly.get("content") or "")
        normalized = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b|\b\d+\b", "?", content.lower())
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        group = groups.setdefault(fingerprint, {"fingerprint": fingerprint, "count": 0, "severity": anomaly.get("severity"), "reasons": anomaly.get("reasons") or [], "first_seen": anomaly.get("time"), "last_seen": anomaly.get("time"), "sample": content[:500]})
        group["count"] += 1
        if anomaly.get("time") and (not group["first_seen"] or anomaly["time"] < group["first_seen"]):
            group["first_seen"] = anomaly["time"]
        if anomaly.get("time") and (not group["last_seen"] or anomaly["time"] > group["last_seen"]):
            group["last_seen"] = anomaly["time"]
    return sorted(groups.values(), key=lambda item: item["count"], reverse=True)[:limit]

def query_application_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source_result = _resolve_application_log_source(params)
    if not source_result.get("success"):
        return source_result

    app_name = params.get("app_name")
    policy_name = _get_policy_name(params) or (
        source_result.get("collection_rule", {}).get("rule_name")
        if source_result.get("collection_rule", {}).get("collection_mode") == "cce_logconfig"
        else None
    )
    namespace = params.get("namespace")
    try:
        output_mode = _application_query_output_mode(params)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    custom_labels = _parse_labels(params.get("labels"))
    index_result = lts.list_log_stream_index(
        params["region"],
        source_result["log_group_id"],
        source_result["log_stream_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    indexed_fields = index_result.get("indexed_fields", set()) if index_result.get("success") else set()
    auto_label_filter, identity_label_fields = _application_identity_filters(params["cluster_id"], namespace, app_name, indexed_fields)
    # Explicit labels remain caller-controlled. Automatic filters are used only
    # when the stream index confirms they can be queried safely.
    final_labels = dict(auto_label_filter)
    if custom_labels:
        final_labels.update(custom_labels)
    filter_precision = _application_filter_precision(params["cluster_id"], namespace, app_name, {
        "clusterId": params["cluster_id"] if identity_label_fields.get("cluster") else None,
        "nameSpace": namespace if identity_label_fields.get("namespace") else None,
        "appName": app_name if identity_label_fields.get("app") else None,
    })
    workload_validation = _validate_application_workload(params, namespace, app_name)

    start_time = params.get("start_time")
    end_time = params.get("end_time")
    hours = None
    if not start_time and not end_time:
        hours = _to_int(params.get("hours"), 1)
        start_time, end_time = _recent_lts_window(hours)

    result = _query_logs_with_pagination(
        params=params,
        log_group_id=source_result["log_group_id"],
        log_stream_id=source_result["log_stream_id"],
        start_time=start_time,
        end_time=end_time,
        labels=final_labels,
    )
    if hours is not None:
        result["hours"] = hours
    no_logs_hint = None
    if result.get("success") and result.get("total", 0) == 0:
        if workload_validation.get("status") == "unmatched":
            no_logs_hint = (
                "No logs matched. Check whether namespace and app_name are correct; no current common workload "
                "matches the supplied app_name."
            )
        else:
            no_logs_hint = (
                "No logs matched. Check namespace, app_name, the selected collection rule, and the requested time window."
            )
    result.update(
        {
            "cluster_id": params["cluster_id"],
            "namespace": namespace,
            "app_name": app_name,
            "log_group_id": source_result["log_group_id"],
            "log_stream_id": source_result["log_stream_id"],
            "collection_rule": source_result["collection_rule"],
            "source_resolution": source_result.get("source_resolution"),
            "policy_name": policy_name,
            "auto_label_filter": auto_label_filter,
            "identity_label_fields": identity_label_fields,
            "log_stream_index_available": index_result.get("success", False),
            "log_stream_index_error": None if index_result.get("success") else index_result.get("error"),
            "custom_labels": custom_labels,
            "final_labels": final_labels,
            "workload_identity_validation": workload_validation,
            "no_logs_hint": no_logs_hint,
            **filter_precision,
        }
    )
    return _shape_application_query_output(result, output_mode, _to_int(params.get("sample_limit"), 20))

def analyze_application_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    query_params.setdefault("is_desc", "false")
    query_params["output"] = "raw"

    query_params.setdefault("hours", "1")
    query_result = query_application_logs_action(query_params)
    if not query_result.get("success"):
        return query_result

    (
        error_patterns,
        warning_patterns,
        http_error_status_threshold,
        include_http_4xx,
        incident_gap_minutes,
        sample_limit,
    ) = _analysis_options(params)

    logs = query_result.get("logs", [])
    analyzed_logs = []
    anomalies = []
    status_code_counts: Dict[str, int] = {}
    reason_counts: Dict[str, int] = {}
    severity_counts = {"critical": 0, "error": 0, "warning": 0, "normal": 0}
    timestamped_logs = []

    for index, log in enumerate(logs):
        content = _content_of(log)
        timestamp_ms = _extract_log_time_ms(log)
        is_abnormal, severity, reasons, status_code = _classify_log(
            content,
            error_patterns,
            warning_patterns,
            http_error_status_threshold,
            include_http_4xx,
        )
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if status_code is not None:
            key = str(status_code)
            status_code_counts[key] = status_code_counts.get(key, 0) + 1
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        analyzed = {
            "index": index,
            "timestamp_ms": timestamp_ms,
            "time": _format_ts(timestamp_ms),
            "is_abnormal": is_abnormal,
            "severity": severity,
            "reasons": reasons,
            "status_code": status_code,
        }
        analyzed_logs.append(analyzed)
        if timestamp_ms is not None:
            timestamped_logs.append(analyzed)
        if is_abnormal:
            sample = dict(analyzed)
            sample["content"] = content[:500]
            anomalies.append(sample)

    total_logs = len(logs)
    abnormal_logs = len(anomalies)
    abnormal_ratio = round(abnormal_logs / total_logs, 6) if total_logs else 0.0
    timestamped_sorted = sorted(timestamped_logs, key=lambda item: item["timestamp_ms"])
    anomalies_sorted = sorted(anomalies, key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0, item["index"]))
    first_abnormal = anomalies_sorted[0] if anomalies_sorted else None
    last_abnormal = anomalies_sorted[-1] if anomalies_sorted else None
    recovery = None
    if last_abnormal and last_abnormal.get("timestamp_ms") is not None:
        for item in timestamped_sorted:
            if item["timestamp_ms"] > last_abnormal["timestamp_ms"] and not item["is_abnormal"]:
                recovery = item
                break

    http_4xx_count = sum(count for code, count in status_code_counts.items() if 400 <= int(code) < 500)
    http_5xx_count = sum(count for code, count in status_code_counts.items() if int(code) >= 500)
    top_status_codes = sorted(status_code_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    top_patterns = sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:20]
    next_steps = []
    if query_result.get("filter_quality") != "exact":
        next_steps.append("Create LTS indexes for cluster, namespace, and application labels before attributing shared-stream findings to one application.")
    if http_5xx_count:
        next_steps.append("Inspect the top 5xx patterns and correlate their timestamps with the target workload's Pod stdout logs.")
    if abnormal_logs and not recovery:
        next_steps.append("Expand the time window or inspect current Pod stdout to determine whether the abnormal pattern is ongoing.")
    if not total_logs:
        next_steps.append("Verify the collection rule, LTS destination, retention window, and application label indexes.")
    window_start = query_result.get("start_time")
    window_end = query_result.get("end_time")
    window_duration_minutes = None
    if isinstance(window_start, int) and isinstance(window_end, int) and window_end > window_start:
        window_duration_minutes = round((window_end - window_start) / 60000, 4)
    logs_per_minute = round(total_logs / window_duration_minutes, 6) if window_duration_minutes else None
    abnormal_logs_per_minute = round(abnormal_logs / window_duration_minutes, 6) if window_duration_minutes else None

    return {
        "success": True,
        "cluster_id": query_result.get("cluster_id"),
        "namespace": query_result.get("namespace"),
        "app_name": query_result.get("app_name"),
        "logconfig_name": query_result.get("collection_rule", {}).get("rule_name")
        if query_result.get("collection_rule", {}).get("collection_mode") == "cce_logconfig" else None,
        "policy_name": query_result.get("policy_name"),
        "source_type": query_result.get("collection_rule", {}).get("source_type"),
        "collection_rule": query_result.get("collection_rule"),
        "log_group_id": query_result.get("log_group_id"),
        "log_stream_id": query_result.get("log_stream_id"),
        "filter_quality": query_result.get("filter_quality"),
        "filter_reason": query_result.get("filter_reason"),
        "analysis_scope_note": query_result.get("analysis_scope_note"),
        "analysis_window": {
            "start_time": _format_ts(window_start) if isinstance(window_start, int) else window_start,
            "end_time": _format_ts(window_end) if isinstance(window_end, int) else window_end,
            "start_timestamp": window_start,
            "end_timestamp": window_end,
            "duration_minutes": window_duration_minutes,
        },
        "summary": {
            "total_logs": total_logs,
            "timestamped_logs": len(timestamped_logs),
            "abnormal_logs": abnormal_logs,
            "normal_logs": total_logs - abnormal_logs,
            "abnormal_ratio": abnormal_ratio,
            "abnormal_percent": round(abnormal_ratio * 100, 4),
            "critical_logs": severity_counts.get("critical", 0),
            "error_logs": severity_counts.get("error", 0),
            "warning_logs": severity_counts.get("warning", 0),
            "http_4xx_count": http_4xx_count,
            "http_5xx_count": http_5xx_count,
            "logs_per_minute": logs_per_minute,
            "abnormal_logs_per_minute": abnormal_logs_per_minute,
            "is_recovered": bool(recovery) if abnormal_logs else True,
        },
        "timeline": {
            "first_abnormal_time": first_abnormal.get("time") if first_abnormal else None,
            "first_abnormal_timestamp": first_abnormal.get("timestamp_ms") if first_abnormal else None,
            "last_abnormal_time": last_abnormal.get("time") if last_abnormal else None,
            "last_abnormal_timestamp": last_abnormal.get("timestamp_ms") if last_abnormal else None,
            "recovery_time": recovery.get("time") if recovery else None,
            "recovery_timestamp": recovery.get("timestamp_ms") if recovery else None,
            "recovery_observed": bool(recovery) if abnormal_logs else True,
        },
        "incident_windows": _build_incident_windows(anomalies, incident_gap_minutes),
        "top_patterns": [{"pattern": pattern, "count": count} for pattern, count in top_patterns],
        "exception_fingerprints": _exception_fingerprints(anomalies, sample_limit),
        "next_steps": next_steps,
        "top_status_codes": [{"status_code": code, "count": count} for code, count in top_status_codes],
        "abnormal_samples": anomalies_sorted[:sample_limit],
        "query_summary": {
            "auto_paginate": query_result.get("auto_paginate"),
            "page_limit": query_result.get("page_limit"),
            "max_pages": query_result.get("max_pages"),
            "pages_fetched": query_result.get("pages_fetched"),
            "stopped_reason": query_result.get("stopped_reason"),
            "final_labels": query_result.get("final_labels"),
            "filter_quality": query_result.get("filter_quality"),
            "filter_reason": query_result.get("filter_reason"),
            "keywords": params.get("keywords"),
            "keywords_scope_note": "When keywords is set, ratios are calculated only over logs matched by that keyword filter." if params.get("keywords") else None,
        },
    }

def analyze_pod_realtime_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Sample a running Pod twice and analyze only the newly observed log lines."""
    if _to_bool(params.get("previous"), False):
        return {"success": False, "error": "previous=true is not supported for realtime Pod log analysis"}

    wait_seconds = _to_int(params.get("wait_seconds"), 30)
    if not 1 <= wait_seconds <= 300:
        return {"success": False, "error": "wait_seconds must be between 1 and 300"}
    tail_lines = max(1, _to_int(params.get("tail_lines"), 100))
    namespace = params.get("namespace", "default")
    pod_name = params["pod_name"]
    container = params.get("container")
    pod_args = {
        "region": params["region"],
        "cluster_id": params["cluster_id"],
        "pod_name": pod_name,
        "namespace": namespace,
        "container": container,
        "tail_lines": tail_lines,
        "ak": params.get("ak"),
        "sk": params.get("sk"),
        "project_id": params.get("project_id"),
        "security_token": params.get("security_token"),
        "explicit_cli_credentials": params.get("_explicit_cli_credentials") == "true",
    }

    initial = cce.get_pod_logs(**pod_args)
    if not initial.get("success"):
        return initial
    time.sleep(wait_seconds)
    followup = cce.get_pod_logs(**pod_args)
    if not followup.get("success"):
        return followup

    new_lines, overlap_lines = _new_log_lines(initial.get("logs", ""), followup.get("logs", ""))
    (
        error_patterns,
        warning_patterns,
        http_error_status_threshold,
        include_http_4xx,
        incident_gap_minutes,
        sample_limit,
    ) = _analysis_options(params)
    anomalies = []
    severity_counts = {"critical": 0, "error": 0, "warning": 0, "normal": 0}
    reason_counts: Dict[str, int] = {}
    status_code_counts: Dict[str, int] = {}

    for index, content in enumerate(new_lines):
        timestamp_ms = _extract_log_time_ms({"content": content})
        is_abnormal, severity, reasons, status_code = _classify_log(
            content, error_patterns, warning_patterns, http_error_status_threshold, include_http_4xx
        )
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if status_code is not None:
            code = str(status_code)
            status_code_counts[code] = status_code_counts.get(code, 0) + 1
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if is_abnormal:
            anomalies.append(
                {
                    "index": index,
                    "timestamp_ms": timestamp_ms,
                    "time": _format_ts(timestamp_ms),
                    "severity": severity,
                    "reasons": reasons,
                    "status_code": status_code,
                    "content": content[:500],
                }
            )

    total_lines = len(new_lines)
    abnormal_lines = len(anomalies)
    abnormal_ratio = round(abnormal_lines / total_lines, 6) if total_lines else 0.0
    return {
        "success": True,
        "action": "analyze_pod_realtime_logs",
        "region": params["region"],
        "cluster_id": params["cluster_id"],
        "namespace": namespace,
        "pod_name": pod_name,
        "container": container,
        "access_method": followup.get("access_method"),
        "sampling": {
            "tail_lines": tail_lines,
            "wait_seconds": wait_seconds,
            "initial_line_count": len(initial.get("logs", "").splitlines()),
            "followup_line_count": len(followup.get("logs", "").splitlines()),
            "overlap_lines": overlap_lines,
            "new_line_count": total_lines,
        },
        "summary": {
            "abnormal_lines": abnormal_lines,
            "normal_lines": total_lines - abnormal_lines,
            "abnormal_ratio": abnormal_ratio,
            "abnormal_percent": round(abnormal_ratio * 100, 4),
            "critical_lines": severity_counts["critical"],
            "error_lines": severity_counts["error"],
            "warning_lines": severity_counts["warning"],
            "http_4xx_count": sum(count for code, count in status_code_counts.items() if 400 <= int(code) < 500),
            "http_5xx_count": sum(count for code, count in status_code_counts.items() if int(code) >= 500),
        },
        "incident_windows": _build_incident_windows(anomalies, incident_gap_minutes),
        "top_patterns": [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "top_status_codes": [
            {"status_code": code, "count": count}
            for code, count in sorted(status_code_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "abnormal_samples": anomalies[:sample_limit],
    }
