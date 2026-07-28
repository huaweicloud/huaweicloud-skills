"""Local aggregation for Kubernetes Event query results."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional


def _as_int(value: Any, default: int = 1) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _event_times(event: Dict[str, Any]) -> List[Optional[str]]:
    first = event.get("first_timestamp") or event.get("eventTime")
    last = event.get("last_timestamp") or event.get("eventTime")
    return [first, last] if first != last else [first]


def _parse_events(value: Optional[str]) -> List[Dict[str, Any]]:
    if not value:
        raise ValueError("events is required and must be a JSON array or an object containing an events array")
    parsed = json.loads(value)
    if isinstance(parsed, dict):
        parsed = parsed.get("events")
    if not isinstance(parsed, list):
        raise ValueError("events must be a JSON array or an object containing an events array")
    return [event for event in parsed if isinstance(event, dict)]


def _range(values: Iterable[Optional[str]]) -> Dict[str, Optional[str]]:
    timestamps = sorted(value for value in values if value)
    return {"first": timestamps[0] if timestamps else None, "last": timestamps[-1] if timestamps else None}


def _as_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _query_events(params: Dict[str, str]) -> tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """Query a supported Event source before local aggregation."""
    source = (
        params.get("event_source")
        or ("lts" if params.get("start_time") or params.get("end_time") else "current")
    ).lower()
    region = params.get("region")
    cluster_id = params.get("cluster_id")
    if source not in {"current", "lts"}:
        raise ValueError("event_source must be current or lts")
    if not region or not cluster_id:
        raise ValueError("region and cluster_id are required when events is not provided")

    if source == "current":
        from . import cce

        try:
            limit = int(params.get("limit", "500"))
        except ValueError:
            raise ValueError("limit must be an integer")
        result = cce.get_kubernetes_events(
            region=region,
            cluster_id=cluster_id,
            namespace=params.get("namespace"),
            event_type=params.get("event_type"),
            limit=max(1, min(limit, 1000)),
            ak=params.get("ak"),
            sk=params.get("sk"),
            project_id=params.get("project_id"),
            security_token=params.get("security_token"),
        )
    else:
        from . import cce_events_lts

        if not params.get("start_time") or not params.get("end_time"):
            raise ValueError("start_time and end_time are required when event_source=lts")
        result = cce_events_lts.query_k8s_events_from_lts_action(params)

    if not result.get("success"):
        raise RuntimeError(result.get("error") or f"failed to query {source} events")
    return result.get("events") or [], source, result


def analyze_cce_events_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Query an Event source when needed, then aggregate its Event records locally."""
    query_result: Optional[Dict[str, Any]] = None
    try:
        if params.get("events"):
            events = _parse_events(params.get("events"))
            source = params.get("event_source") or "provided_events"
        else:
            events, source, query_result = _query_events(params)
    except (ValueError, json.JSONDecodeError, RuntimeError) as exc:
        return {"success": False, "error": str(exc)}

    try:
        max_groups = max(1, min(int(params.get("max_groups", "10")), 100))
    except ValueError:
        return {"success": False, "error": "max_groups must be an integer between 1 and 100"}

    reason_counts: Counter[str] = Counter()
    reason_warnings: Counter[str] = Counter()
    reason_times: Dict[str, List[Optional[str]]] = defaultdict(list)
    namespace_counts: Counter[str] = Counter()
    object_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    repeated_patterns: List[Dict[str, Any]] = []

    for event in events:
        event_type = str(event.get("type") or "Unknown")
        reason = str(event.get("reason") or "Unknown")
        namespace = str(event.get("namespace") or (event.get("involved_object") or {}).get("namespace") or "unknown")
        occurrences = _as_int(event.get("count"))
        involved_object = event.get("involved_object") or event.get("involvedObject") or {}
        if not isinstance(involved_object, dict):
            involved_object = {}
        object_key = "/".join(
            filter(
                None,
                (
                    namespace,
                    str(involved_object.get("kind") or "Unknown"),
                    str(involved_object.get("name") or "Unknown"),
                ),
            )
        )

        reason_counts[reason] += occurrences
        namespace_counts[namespace] += occurrences
        object_counts[object_key] += occurrences
        type_counts[event_type] += occurrences
        reason_times[reason].extend(_event_times(event))
        if event_type.lower() == "warning":
            reason_warnings[reason] += occurrences
        if occurrences > 1:
            repeated_patterns.append(
                {
                    "reason": reason,
                    "type": event_type,
                    "namespace": namespace,
                    "involved_object": involved_object or None,
                    "count": occurrences,
                    "first_timestamp": event.get("first_timestamp"),
                    "last_timestamp": event.get("last_timestamp"),
                }
            )

    top_reasons = [
        {
            "reason": reason,
            "count": count,
            "warning_count": reason_warnings[reason],
            "time_range": _range(reason_times[reason]),
        }
        for reason, count in reason_counts.most_common(max_groups)
    ]
    repeated_patterns.sort(key=lambda item: item["count"], reverse=True)

    response = {
        "success": True,
        "source": source,
        "event_records": len(events),
        "total_occurrences": sum(type_counts.values()),
        "event_type_breakdown": dict(type_counts.most_common()),
        "warning_count": type_counts.get("Warning", 0),
        "normal_count": type_counts.get("Normal", 0),
        "time_range": _range(timestamp for event in events for timestamp in _event_times(event)),
        "top_reasons": top_reasons,
        "namespace_breakdown": [
            {"namespace": namespace, "count": count}
            for namespace, count in namespace_counts.most_common(max_groups)
        ],
        "affected_objects": [
            {"object": object_key, "count": count}
            for object_key, count in object_counts.most_common(max_groups)
        ],
        "repeated_patterns": repeated_patterns[:max_groups],
    }
    region = params.get("region") or (query_result or {}).get("region")
    cluster_id = params.get("cluster_id") or (query_result or {}).get("cluster_id")
    should_check_resources = _as_bool(params.get("check_resource_status"), bool(region and cluster_id))
    if should_check_resources and region and cluster_id:
        from . import resource_status

        try:
            response["resource_status"] = resource_status.check_event_resource_statuses(
                events=events,
                region=region,
                cluster_id=cluster_id,
                max_resources=max_groups,
                ak=params.get("ak"),
                sk=params.get("sk"),
                project_id=params.get("project_id"),
                security_token=params.get("security_token"),
            )
        except Exception as exc:
            response["resource_status"] = {
                "checked": 0,
                "summary": {"query_failed": 1},
                "resources": [],
                "message": f"Resource status checks failed: {exc}",
            }
    else:
        response["resource_status"] = {
            "checked": 0,
            "summary": {},
            "resources": [],
            "message": "Resource status checks require region and cluster_id, or can be disabled with check_resource_status=false",
        }
    if query_result is not None:
        response["query"] = {
            "source": source,
            "region": query_result.get("region"),
            "cluster_id": query_result.get("cluster_id"),
            "event_count": len(events),
            "access_method": query_result.get("access_method"),
            "time_range": query_result.get("time_range"),
            "log_config": query_result.get("log_config"),
        }
    return response
