"""CCE audit log discovery, query, and timeline analysis."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from . import common, lts
from .cce_log_common import (
    _content_of,
    _extract_audit_time_ms,
    _format_ts,
    _json_content_of,
    _parse_labels,
    _parse_text_list,
    _query_logs_with_pagination,
    _recent_lts_window,
    _to_bool,
    _to_int,
)


def _discover_audit_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    cluster_id = params["cluster_id"]
    config_command = common.hcloud_command(
        "CCE", "ShowClusterConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    config_command.append(f"--cluster_id={cluster_id}")
    if params.get("project_id"):
        config_command.append(f"--project_id={params['project_id']}")
    config_result = common.run_hcloud(config_command)
    if not config_result.get("success"):
        return config_result
    audit_config = next(
        (item for item in config_result.get("data", {}).get("log_configs", []) if item.get("name") == "audit"),
        None,
    )
    if not audit_config or not audit_config.get("enable"):
        return {
            "success": False,
            "error": "CCE audit log collection is not enabled",
            "note": "Enable the audit log configuration before querying or analyzing Kubernetes audit logs.",
        }

    if params.get("log_group_id") and params.get("log_stream_id"):
        return {
            "success": True,
            "log_group_id": params["log_group_id"],
            "log_stream_id": params["log_stream_id"],
            "match_type": "explicit_ids",
            "cluster_audit_enabled": True,
        }

    expected_group_name = f"k8s-log-{cluster_id}"
    expected_stream_name = f"audit-{cluster_id}"

    groups_result = lts.list_log_groups(
        params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not groups_result.get("success"):
        return groups_result
    group = next(
        (item for item in groups_result.get("log_groups", []) if item.get("log_group_name") == expected_group_name),
        None,
    )
    if not group:
        return {
            "success": False,
            "error": f"CCE audit log group {expected_group_name} was not found",
            "note": "Audit is enabled, but the expected LTS log group is unavailable or has not been created yet.",
        }
    streams_result = lts.list_log_streams(
        params["region"],
        group["log_group_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not streams_result.get("success"):
        return streams_result
    stream = next(
        (item for item in streams_result.get("log_streams", []) if item.get("log_stream_name") == expected_stream_name),
        None,
    )
    if not stream:
        return {
            "success": False,
            "error": f"CCE audit log stream {expected_stream_name} was not found",
            "note": "Audit is enabled, but the expected LTS log stream is unavailable or has not been created yet.",
        }
    return {
        "success": True,
        "log_group_id": group.get("log_group_id"),
        "log_stream_id": stream.get("log_stream_id"),
        "log_group_name": expected_group_name,
        "log_stream_name": expected_stream_name,
        "match_type": "cluster_config_name",
        "cluster_audit_enabled": True,
    }

def _audit_filters(params: Dict[str, str]) -> Dict[str, Any]:
    audit_type = params.get("audit_type") or params.get("scenario")
    resource_name = params.get("resource_name") or params.get("pod_name") or params.get("workload_name") or params.get("app_name")
    content_keywords = _parse_text_list(params.get("content_keywords"), [])
    for keyword in (
        resource_name,
        params.get("namespace"),
        params.get("user"),
        params.get("status_code"),
        params.get("verb"),
        params.get("resource"),
        *(_parse_text_list(params.get("verbs"), [])),
        *(_parse_text_list(params.get("resources"), [])),
    ):
        if keyword and keyword not in content_keywords:
            content_keywords.append(keyword)
    if audit_type == "pod_delete":
        for keyword in ("delete", "pods"):
            if keyword not in content_keywords:
                content_keywords.append(keyword)
    elif audit_type in {"workload_change", "application_change", "app_change"}:
        for keyword in ("create", "update", "patch", "delete"):
            if keyword not in content_keywords:
                content_keywords.append(keyword)
    filters: Dict[str, Any] = {
        "audit_type": audit_type,
        "resource_name": resource_name,
        "content_keywords": content_keywords,
    }
    return filters

def _extract_audit_event(log: Dict[str, Any]) -> Dict[str, Any]:
    content = _content_of(log)
    audit = _json_content_of(log)
    object_ref = audit.get("objectRef", {}) if isinstance(audit.get("objectRef"), dict) else {}
    user_info = audit.get("user", {}) if isinstance(audit.get("user"), dict) else {}
    response_status = audit.get("responseStatus", {}) if isinstance(audit.get("responseStatus"), dict) else {}
    timestamp_ms = _extract_audit_time_ms(log, audit)
    return {
        "timestamp_ms": timestamp_ms,
        "time": _format_ts(timestamp_ms),
        "verb": audit.get("verb"),
        "user": user_info.get("username") or audit.get("username"),
        "resource": object_ref.get("resource"),
        "subresource": object_ref.get("subresource"),
        "namespace": object_ref.get("namespace"),
        "name": object_ref.get("name"),
        "api_group": object_ref.get("apiGroup"),
        "api_version": object_ref.get("apiVersion"),
        "request_uri": audit.get("requestURI"),
        "source_ips": audit.get("sourceIPs"),
        "user_agent": audit.get("userAgent"),
        "stage": audit.get("stage"),
        "status_code": response_status.get("code"),
        "status_reason": response_status.get("reason"),
        "content": content[:1000],
        "raw": audit,
    }

def _audit_event_matches(event: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    content_lower = re.sub(r"</?highlighttag>", "", str(event.get("content") or ""), flags=re.IGNORECASE).lower()
    keywords = [item.lower() for item in filters.get("content_keywords", [])]
    if keywords and not all(keyword in content_lower for keyword in keywords):
        return False
    return True

def query_cce_audit_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    stream_result = _discover_audit_log_stream(params)
    if not stream_result.get("success"):
        return stream_result

    filters = _audit_filters(params)
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("keywords") and filters.get("content_keywords"):
        query_params["keywords"] = " ".join(filters["content_keywords"])
    if not query_params.get("start_time") and not query_params.get("end_time"):
        hours = _to_int(query_params.get("hours"), 1)
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(hours)

    labels = _parse_labels(query_params.get("labels")) or {}
    if query_params.get("cluster_id") and _to_bool(query_params.get("add_cluster_label"), False):
        labels.setdefault("clusterId", query_params["cluster_id"])

    query_result = _query_logs_with_pagination(
        params=query_params,
        log_group_id=stream_result["log_group_id"],
        log_stream_id=stream_result["log_stream_id"],
        start_time=query_params.get("start_time"),
        end_time=query_params.get("end_time"),
        labels=labels,
    )
    if not query_result.get("success"):
        return query_result

    events = [_extract_audit_event(log) for log in query_result.get("logs", [])]
    matched_events = [event for event in events if _audit_event_matches(event, filters)]
    sample_limit = _to_int(params.get("sample_limit"), 50)

    def _count_by(key: str) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for event in matched_events:
            value = event.get(key)
            if value is None or value == "":
                value = "unknown"
            value = str(value)
            counts[value] = counts.get(value, 0) + 1
        return [{"value": value, "count": count} for value, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:20]]

    return {
        "success": True,
        "cluster_id": params["cluster_id"],
        "log_group_id": stream_result["log_group_id"],
        "log_stream_id": stream_result["log_stream_id"],
        "log_group_name": stream_result.get("log_group_name"),
        "log_stream_name": stream_result.get("log_stream_name"),
        "stream_match_type": stream_result.get("match_type"),
        "analysis_window": {
            "start_time": query_result.get("start_time"),
            "end_time": query_result.get("end_time"),
        },
        "filters": filters,
        "summary": {
            "queried_logs": len(query_result.get("logs", [])),
            "parsed_audit_events": len(events),
            "matched_events": len(matched_events),
            "matched_ratio": round(len(matched_events) / len(events), 6) if events else 0.0,
        },
        "top_users": _count_by("user"),
        "top_verbs": _count_by("verb"),
        "top_resources": _count_by("resource"),
        "top_namespaces": _count_by("namespace"),
        "top_status_codes": _count_by("status_code"),
        "events": matched_events[:sample_limit],
        "query_summary": {
            "auto_paginate": query_result.get("auto_paginate"),
            "page_limit": query_result.get("page_limit"),
            "max_pages": query_result.get("max_pages"),
            "pages_fetched": query_result.get("pages_fetched"),
            "stopped_reason": query_result.get("stopped_reason"),
            "labels": labels,
            "lts_keywords": query_params.get("keywords"),
        },
        "discovery_candidates": stream_result.get("candidates"),
    }

def _audit_timeline_event_matches(
    event: Dict[str, Any],
    resource_names: List[str],
    namespaces: List[str],
    resources: List[str],
    verbs: List[str],
) -> bool:
    if resource_names and str(event.get("name") or "") not in resource_names:
        return False
    if namespaces and str(event.get("namespace") or "") not in namespaces:
        return False
    if resources and str(event.get("resource") or "").lower() not in {item.lower() for item in resources}:
        return False
    if verbs and str(event.get("verb") or "").lower() not in {item.lower() for item in verbs}:
        return False
    return True

def analyze_cce_audit_timeline_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Group CCE audit events into resource change timelines and lifecycle summaries."""
    resource_names = _parse_text_list(
        params.get("resource_names") or params.get("resource_name") or params.get("pod_name") or params.get("workload_name") or params.get("app_name"),
        [],
    )
    namespaces = _parse_text_list(params.get("namespaces") or params.get("namespace"), [])
    resources = _parse_text_list(params.get("resources") or params.get("resource"), [])
    requested_verbs = _parse_text_list(params.get("verbs") or params.get("verb"), [])
    include_read_events = _to_bool(params.get("include_read_events"), False)
    mutation_verbs = {"create", "update", "patch", "delete", "deletecollection"}
    effective_verbs = requested_verbs or ([] if include_read_events else sorted(mutation_verbs))
    query_params = dict(params)
    # LTS keywords combine terms conjunctively. Apply multi-value resource and verb
    # filters after retrieval so a timeline can include either Pods or Deployments.
    if len(resources) > 1:
        query_params.pop("resources", None)
        query_params.pop("resource", None)
    if len(requested_verbs) > 1:
        query_params.pop("verbs", None)
        query_params.pop("verb", None)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "500")
    query_params.setdefault("sample_limit", str(_to_int(params.get("timeline_limit"), 500)))
    query_results = []
    events = []
    seen_events = set()
    for verb in effective_verbs or [None]:
        verb_query_params = dict(query_params)
        if verb:
            verb_query_params["verb"] = verb
        query_result = query_cce_audit_logs_action(verb_query_params)
        if not query_result.get("success"):
            return query_result
        query_results.append(query_result)
        for event in query_result.get("events", []):
            key = (
                event.get("timestamp_ms"), event.get("verb"), event.get("resource"),
                event.get("namespace"), event.get("name"), event.get("request_uri"),
            )
            if key not in seen_events:
                seen_events.add(key)
                events.append(event)

    source_result = query_results[0]

    filtered_events = [
        event
        for event in events
        if _audit_timeline_event_matches(event, resource_names, namespaces, resources, effective_verbs)
    ]
    filtered_events.sort(key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0))

    lifecycles: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for event in filtered_events:
        key = (
            str(event.get("resource") or "unknown"),
            str(event.get("namespace") or ""),
            str(event.get("name") or ""),
            str(event.get("api_group") or ""),
        )
        lifecycle = lifecycles.setdefault(
            key,
            {
                "resource": key[0],
                "namespace": key[1] or None,
                "name": key[2] or None,
                "api_group": key[3] or None,
                "event_count": 0,
                "observed_create_time": None,
                "observed_delete_time": None,
                "last_change_time": None,
                "last_verb": None,
                "actors": {},
                "status_codes": {},
            },
        )
        lifecycle["event_count"] += 1
        verb = str(event.get("verb") or "").lower()
        event_time = event.get("time")
        if verb == "create" and lifecycle["observed_create_time"] is None:
            lifecycle["observed_create_time"] = event_time
        if verb in {"delete", "deletecollection"}:
            lifecycle["observed_delete_time"] = event_time
        lifecycle["last_change_time"] = event_time
        lifecycle["last_verb"] = event.get("verb")
        actor = str(event.get("user") or "unknown")
        lifecycle["actors"][actor] = lifecycle["actors"].get(actor, 0) + 1
        status_code = str(event.get("status_code") or "unknown")
        lifecycle["status_codes"][status_code] = lifecycle["status_codes"].get(status_code, 0) + 1

    lifecycle_items = []
    for lifecycle in lifecycles.values():
        lifecycle["actors"] = [
            {"user": user, "count": count}
            for user, count in sorted(lifecycle["actors"].items(), key=lambda item: item[1], reverse=True)
        ]
        lifecycle["status_codes"] = [
            {"status_code": code, "count": count}
            for code, count in sorted(lifecycle["status_codes"].items(), key=lambda item: item[1], reverse=True)
        ]
        lifecycle_items.append(lifecycle)
    lifecycle_items.sort(key=lambda item: (item.get("last_change_time") is None, item.get("last_change_time") or ""))

    timeline = [
        {
            "time": event.get("time"),
            "verb": event.get("verb"),
            "resource": event.get("resource"),
            "namespace": event.get("namespace"),
            "name": event.get("name"),
            "user": event.get("user"),
            "status_code": event.get("status_code"),
            "status_reason": event.get("status_reason"),
            "request_uri": event.get("request_uri"),
        }
        for event in filtered_events
    ]
    return {
        "success": True,
        "action": "analyze_cce_audit_timeline",
        "cluster_id": params["cluster_id"],
        "analysis_window": source_result.get("analysis_window"),
        "audit_source": {
            "log_group_id": source_result.get("log_group_id"),
            "log_stream_id": source_result.get("log_stream_id"),
            "log_group_name": source_result.get("log_group_name"),
            "log_stream_name": source_result.get("log_stream_name"),
        },
        "filters": {
            "resource_names": resource_names,
            "namespaces": namespaces,
            "resources": resources,
            "verbs": effective_verbs,
            "include_read_events": include_read_events,
        },
        "summary": {
            "queried_audit_events": sum(result.get("summary", {}).get("matched_events", 0) for result in query_results),
            "timeline_events": len(timeline),
            "resources_observed": len(lifecycle_items),
        },
        "resource_lifecycles": lifecycle_items,
        "timeline": timeline,
        "note": "Creation and deletion times are inferred only from retained audit records; they do not establish the resource's current existence.",
        "query_summary": {
            "query_count": len(query_results),
            "per_verb": [
                {"verb": verb, "matched_events": result.get("summary", {}).get("matched_events", 0)}
                for verb, result in zip(effective_verbs or [None], query_results)
            ],
        },
    }
