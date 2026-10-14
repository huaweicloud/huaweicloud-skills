"""Dispatcher for the public CCE Log Analyzer tools."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from . import cce, cce_app_logs, common, lts

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _resolve_region(params: Dict[str, str]) -> Dict[str, str]:
    """Prefer an explicit region and otherwise use the configured region."""
    resolved = dict(params)
    if not resolved.get("region") and os.environ.get("HW_REGION_NAME"):
        resolved["region"] = os.environ["HW_REGION_NAME"]
    return resolved


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if missing == ["region"]:
        return "region is required; provide region or set HW_REGION_NAME"
    return None if not missing else (f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required")


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _normalize_cli_credentials(params: Dict[str, str]) -> tuple[Dict[str, str], str | None]:
    """Map explicit CLI credentials and prevent fallback to local credential sources."""
    cli_keys = ("cli_access_key", "cli_secret_key", "cli_security_token")
    normalized = dict(params)
    for cli_key, internal_key in (("cli_access_key", "ak"), ("cli_secret_key", "sk"), ("cli_security_token", "security_token")):
        value = normalized.pop(cli_key, None)
        if not value:
            continue
        if normalized.get(internal_key) and normalized[internal_key] != value:
            return params, f"{cli_key} and {internal_key} must not provide different values"
        normalized[internal_key] = value
    has_ak = bool(normalized.get("ak"))
    has_sk = bool(normalized.get("sk"))
    has_token = bool(normalized.get("security_token"))
    if has_ak != has_sk:
        return params, "cli_access_key and cli_secret_key must be provided together"
    if has_token and not has_ak:
        return params, "cli_security_token requires cli_access_key and cli_secret_key"
    if has_ak:
        normalized["_explicit_cli_credentials"] = "true"
    if normalized.get("cli_project_id"):
        normalized["project_id"] = normalized["cli_project_id"]
    return normalized, None


def _pod_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_pod_logs(
        params["region"], params["cluster_id"], params["pod_name"], params.get("ak"), params.get("sk"),
        params.get("project_id"), params.get("namespace", "default"), params.get("container"),
        params.get("previous", "false").lower() == "true", _to_int(params.get("tail_lines"), 1000),
        params.get("security_token"), params.get("_explicit_cli_credentials") == "true",
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_pod_stdout_logs": (("region", "cluster_id", "namespace", "pod_name"), _pod_logs),
    "huawei_analyze_pod_stdout_realtime_logs": (("region", "cluster_id", "namespace", "pod_name"), cce_app_logs.analyze_pod_realtime_logs_action),
    "huawei_list_lts_access_configs": (("region",), lambda params: lts.list_access_configs(params["region"], params.get("access_config_name"), params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token"))),
    "huawei_create_lts_access_config": (("region", "access_config_name"), lts.create_access_config_action),
    "huawei_delete_lts_access_config": (("region", "access_config_id"), lts.delete_access_config_action),
    "huawei_get_cce_logconfigs": (("region", "cluster_id"), cce_app_logs.get_cce_logconfigs_action),
    "huawei_create_cce_logconfig": (("region", "cluster_id", "logconfig_name", "source_type"), cce_app_logs.create_cce_logconfig_action),
    "huawei_delete_cce_logconfig": (("region", "cluster_id", "logconfig_name"), cce_app_logs.delete_cce_logconfig_action),
    "huawei_query_cce_audit_logs": (("region", "cluster_id"), cce_app_logs.query_cce_audit_logs_action),
    "huawei_analyze_cce_audit_timeline": (("region", "cluster_id"), cce_app_logs.analyze_cce_audit_timeline_action),
    "huawei_query_kube_apiserver_logs": (("region", "cluster_id"), cce_app_logs.query_kube_apiserver_logs_action),
    "huawei_analyze_kube_apiserver_logs": (("region", "cluster_id"), cce_app_logs.analyze_kube_apiserver_logs_action),
    "huawei_query_kube_scheduler_logs": (("region", "cluster_id"), cce_app_logs.query_kube_scheduler_logs_action),
    "huawei_analyze_kube_scheduler_logs": (("region", "cluster_id"), cce_app_logs.analyze_kube_scheduler_logs_action),
    "huawei_query_application_logs": (("region", "cluster_id"), cce_app_logs.query_application_logs_action),
    "huawei_analyze_application_logs": (("region", "cluster_id"), cce_app_logs.analyze_application_logs_action),
}


def list_actions() -> Dict[str, tuple[str, ...]]:
    """Return public actions with their required parameters."""
    return {action: required for action, (required, _) in sorted(ACTION_SPECS.items())}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    params, credential_error = _normalize_cli_credentials(params)
    if credential_error:
        return {"success": False, "error": credential_error}
    params = _resolve_region(params)
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    if error:
        return {"success": False, "error": error}
    resolution = None
    if params.get("cluster_id"):
        input_cluster_id = params["cluster_id"]
        resolution = common.resolve_cce_cluster_id(
            params["region"], input_cluster_id, params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
        )
        if not resolution.get("success"):
            return resolution
        params["cluster_id"] = resolution["id"]
    result = handler(params)
    if resolution and resolution.get("resolved_from_name") and result.get("success"):
        result["resolved_resource_ids"] = [{"parameter": "cluster_id", "input": input_cluster_id, "resolved_id": resolution["id"]}]
    return result
