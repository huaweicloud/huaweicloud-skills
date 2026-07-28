"""Dispatcher for the public CCE Kubernetes Event Analyzer tools."""

from __future__ import annotations

from typing import Any, Callable, Dict

from . import cce, cce_events_lts, event_analysis

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if not missing:
        return None
    return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _get_cce_events(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_events(
        region=params["region"],
        cluster_id=params["cluster_id"],
        namespace=params.get("namespace"),
        event_type=params.get("event_type"),
        limit=_to_int(params.get("limit"), 500),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_cce_events": (("region", "cluster_id"), _get_cce_events),
    "huawei_query_k8s_events_from_lts": (
        ("region", "cluster_id", "start_time", "end_time"),
        cce_events_lts.query_k8s_events_from_lts_action,
    ),
    "huawei_analyze_cce_events": ((), event_analysis.analyze_cce_events_action),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    return {"success": False, "error": error} if error else handler(params)
