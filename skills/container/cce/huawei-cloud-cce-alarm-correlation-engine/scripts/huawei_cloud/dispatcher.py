"""CLI dispatch helpers for the CCE alarm-correlation skill."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict

from . import aom

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if missing:
        return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"
    return None


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_json_param(value: str | None, key: str = "json") -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{key} must be valid JSON: {exc.msg}") from exc


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


def _alarm_rule_fields(params: Dict[str, str], json_key: str) -> Dict[str, Any]:
    fields = _parse_json_param(params.get(json_key), json_key) or {}
    for key in (
        "action_enabled",
        "alarm_actions",
        "alarm_advice",
        "alarm_description",
        "alarm_level",
        "bind_notification_rule_id",
        "cluster_id",
        "comparison_operator",
        "dimensions",
        "evaluation_periods",
        "is_turn_on",
        "insufficient_data_actions",
        "metric_name",
        "metric_labels",
        "namespace",
        "ok_actions",
        "period",
        "prom_instance_id",
        "promql",
        "promql_for",
        "recovery_timeframe",
        "severity",
        "statistic",
        "threshold",
        "threshold_value",
        "trigger_interval",
        "trigger_type",
        "unit",
    ):
        if key not in params:
            continue

        value: Any = params[key]
        if key in {"alarm_actions", "dimensions", "insufficient_data_actions", "metric_labels", "ok_actions"}:
            value = _parse_json_param(value, key)
        elif key in {"action_enabled", "is_turn_on"}:
            value = value.lower() == "true"
        elif key in {"alarm_level", "evaluation_periods", "period", "recovery_timeframe"}:
            value = _to_int(value, 0)
        fields[key] = value
    return fields


def _list_aom_alarm_rules(params: Dict[str, str]) -> Dict[str, Any]:
    if params.get("cluster_name"):
        return {
            "success": False,
            "error": "cluster_name is not supported by huawei_list_aom_alarm_rules. Use cluster_id instead.",
        }
    return aom.list_aom_alarm_rules(
        params["region"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
        _to_int(params.get("limit"), 100),
        _to_int(params.get("offset"), 0),
        params.get("enterprise_project_id"),
        params.get("cluster_id"),
    )


def _create_aom_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.create_aom_alarm_rule(
        region=params["region"],
        rule_name=params.get("rule_name"),
        metric_name=params.get("metric_name"),
        namespace=params.get("namespace"),
        comparison_operator=params.get("comparison_operator"),
        threshold=params.get("threshold"),
        period=_to_int(params.get("period"), 0),
        evaluation_periods=_to_int(params.get("evaluation_periods"), 0),
        statistic=params.get("statistic"),
        alarm_level=_to_int(params.get("alarm_level"), 0),
        create_fields=_alarm_rule_fields(params, "fields"),
        cluster_id=params.get("cluster_id"),
        alarm_item=params.get("alarm_item") or params.get("template_item") or params.get("alias"),
        prom_instance_id=params.get("prom_instance_id"),
        enterprise_project_id=params.get("enterprise_project_id"),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )


def _create_aom_event_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    bind_notification_rule_id = params.get("bind_notification_rule_id") or params.get("notification_rule_name")
    return aom.create_aom_event_alarm_rule(
        region=params["region"],
        cluster_id=params["cluster_id"],
        rule_name=params.get("rule_name"),
        event_name=params["event_name"],
        bind_notification_rule_id=bind_notification_rule_id,
        event_label=params.get("event_label"),
        alarm_level=params.get("alarm_level", "Major"),
        description=params.get("description"),
        alias=params.get("alias"),
        trigger_type=params.get("trigger_type", "immediately"),
        frequency=params.get("frequency", "-1"),
        prom_instance_id=params.get("prom_instance_id"),
        enterprise_project_id=params.get("enterprise_project_id"),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )


def _configure_cce_aom_alarm_rules(params: Dict[str, str]) -> Dict[str, Any]:
    bind_notification_rule_id = params.get("bind_notification_rule_id") or params.get("notification_rule_name")
    return aom.configure_cce_aom_alarm_rules(
        region=params["region"],
        cluster_id=params["cluster_id"],
        bind_notification_rule_id=bind_notification_rule_id,
        rule_name_prefix=params.get("rule_name_prefix"),
        include_metric_alarms=_to_bool(params.get("include_metric_alarms"), True),
        include_event_alarms=_to_bool(params.get("include_event_alarms"), True),
        alarm_items=params.get("alarm_items"),
        skip_existing=_to_bool(params.get("skip_existing"), True),
        prom_instance_id=params.get("prom_instance_id"),
        enterprise_project_id=params.get("enterprise_project_id"),
        alarm_template_id=params.get("alarm_template_id") or aom.CCE_ALARM_RULE_TEMPLATE_ID,
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )


def _cleanup_cce_aom_alarm_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.cleanup_cce_aom_alarm_rules(
        region=params["region"],
        cluster_id=params["cluster_id"],
        rule_name_prefix=params.get("rule_name_prefix"),
        include_metric_alarms=_to_bool(params.get("include_metric_alarms"), True),
        include_event_alarms=_to_bool(params.get("include_event_alarms"), True),
        alarm_items=params.get("alarm_items"),
        alarm_template_id=params.get("alarm_template_id") or aom.CCE_ALARM_RULE_TEMPLATE_ID,
        delete_auto_notification_rule=_to_bool(params.get("delete_auto_notification_rule"), False),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        enterprise_project_id=params.get("enterprise_project_id"),
    )


def _create_aom_notification_action_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.create_aom_notification_action_rule(
        region=params["region"],
        rule_name=params["rule_name"],
        notification_topic_urn=params["notification_topic_urn"],
        notification_topic_name=params["notification_topic_name"],
        notification_topic_display_name=params.get("notification_topic_display_name"),
        notification_user_name=params.get("notification_user_name"),
        description=params.get("description"),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )


def _resolve_cce_aom_prom_instance(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.resolve_cce_aom_prom_instance(
        params["region"],
        params["cluster_id"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _update_aom_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.update_aom_alarm_rule(
        params["region"],
        params["rule_name"],
        _alarm_rule_fields(params, "updates"),
        params.get("confirm", "").lower() == "true",
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _delete_aom_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.delete_aom_alarm_rule(
        params["region"],
        params["rule_name"],
        params.get("confirm", "").lower() == "true",
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _disable_aom_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.disable_aom_alarm_rule(
        params["region"],
        params["rule_id"],
        params.get("confirm", "").lower() == "true",
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _enable_aom_alarm_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.enable_aom_alarm_rule(
        params["region"],
        params["rule_id"],
        params.get("confirm", "").lower() == "true",
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _list_aom_action_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_action_rules(
        params["region"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
        params.get("enterprise_project_id"),
    )


def _delete_aom_action_rule(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.delete_aom_action_rule(
        params["region"],
        params["rule_name"],
        params.get("confirm", "").lower() == "true",
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _list_aom_mute_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_mute_rules(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_aom_current_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_current_alarms(
        params["region"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
        params.get("event_type", "active_alert"),
        params.get("event_severity"),
        params.get("time_range"),
        _to_int(params.get("limit"), 100),
        params.get("cluster_id"),
    )


def _list_aom_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_alarms(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        hours=_to_int(params.get("hours"), 1),
        event_severity=params.get("event_severity"),
        cluster_id=params.get("cluster_id"),
        cluster_name=params.get("cluster_name"),
        limit=_to_int(params.get("limit"), 500),
    )


def _analyze_aom_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.analyze_aom_alarms(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        cluster_id=params.get("cluster_id"),
        cluster_name=params.get("cluster_name"),
        hours=_to_int(params.get("hours"), 1),
        chronic_threshold=_to_int(params.get("chronic_threshold"), 5),
        sudden_window_minutes=_to_int(params.get("sudden_window_minutes"), 10),
    )


def _aom_alarm_inspection_action(params: Dict[str, str]) -> Dict[str, Any]:
    analysis = _analyze_aom_alarms(params)
    if not analysis.get("success"):
        return analysis

    summary = analysis.get("summary", {})
    sudden = analysis.get("sudden_alarms", [])
    attention = analysis.get("attention_alarms", [])
    chronic = analysis.get("chronic_alarms", [])
    risk_items = []

    if sudden:
        risk_items.append({
            "level": "high",
            "category": "sudden_alarms",
            "message": f"{len(sudden)} sudden alarm groups require immediate attention",
            "items": sudden[:10],
        })
    if attention:
        risk_items.append({
            "level": "medium",
            "category": "attention_alarms",
            "message": f"{len(attention)} alarm groups require follow-up",
            "items": attention[:10],
        })
    if chronic:
        risk_items.append({
            "level": "low",
            "category": "chronic_alarms",
            "message": f"{len(chronic)} chronic alarm groups may be noise or recurring issues",
            "items": chronic[:10],
        })

    check = {
        "name": "aom_alarm_inspection",
        "cluster_id": params["cluster_id"],
        "region": params["region"],
        "status": "failed" if sudden else "warning" if attention else "passed",
        "summary": summary,
        "report": analysis.get("report"),
    }
    return {"success": True, "check": check, "issues": risk_items, "analysis": analysis}


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_list_aom_alarm_rules": (("region",), _list_aom_alarm_rules),
    "huawei_create_aom_alarm_rule": (
        ("region",),
        _create_aom_alarm_rule,
    ),
    "huawei_create_aom_event_alarm_rule": (("region", "cluster_id", "event_name"), _create_aom_event_alarm_rule),
    "huawei_configure_cce_aom_alarm_rules": (("region", "cluster_id"), _configure_cce_aom_alarm_rules),
    "huawei_cleanup_cce_aom_alarm_rules": (("region", "cluster_id"), _cleanup_cce_aom_alarm_rules),
    "huawei_create_aom_notification_action_rule": (("region", "rule_name", "notification_topic_urn", "notification_topic_name"), _create_aom_notification_action_rule),
    "huawei_resolve_cce_aom_prom_instance": (("region", "cluster_id"), _resolve_cce_aom_prom_instance),
    "huawei_update_aom_alarm_rule": (("region", "rule_name"), _update_aom_alarm_rule),
    "huawei_delete_aom_alarm_rule": (("region", "rule_name"), _delete_aom_alarm_rule),
    "huawei_disable_aom_alarm_rule": (("region", "rule_id"), _disable_aom_alarm_rule),
    "huawei_enable_aom_alarm_rule": (("region", "rule_id"), _enable_aom_alarm_rule),
    "huawei_list_aom_action_rules": (("region",), _list_aom_action_rules),
    "huawei_delete_aom_action_rule": (("region", "rule_name"), _delete_aom_action_rule),
    "huawei_list_aom_mute_rules": (("region",), _list_aom_mute_rules),
    "huawei_list_aom_current_alarms": (("region",), _list_aom_current_alarms),
    "huawei_list_aom_alarms": (("region",), _list_aom_alarms),
    "huawei_analyze_aom_alarms": (("region",), _analyze_aom_alarms),
    "huawei_aom_alarm_inspection": (("region", "cluster_id"), _aom_alarm_inspection_action),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    if error:
        return {"success": False, "error": error}
    try:
        return handler(params)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
