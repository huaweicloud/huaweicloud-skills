"""AOM alarm actions implemented through hcloud CLI."""

from __future__ import annotations

import json
import re
import copy
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .common import extract_items, get_project_id_for_region, redact_command, resolve_project_id_for_region, run_hcloud, run_hcloud_json_input


CLUSTER_ID_PLACEHOLDER = "__CCE_CLUSTER_ID__"
CCE_ALARM_RULE_TEMPLATE_ID = "at0000000000000000cce001"
CCE_ALARM_RULE_TEMPLATE_NAME = "CCE模板"


EVENT_NAME_ALIASES = {
    "FailedScheduling": "调度失败##FailedScheduling",
    "FailedCreate": "创建失败##FailedCreate",
    "FailedDelete": "删除失败##FailedDelete",
    "FailedUpdate": "更新失败##FailedUpdate",
    "NodeNotReady": "节点未就绪##NodeNotReady",
    "NodeReady": "节点就绪##NodeReady",
    "Unhealthy": "不健康##Unhealthy",
    "BackOff": "容器启动退避##BackOff",
    "OOMKilling": "OOM 击杀##OOMKilling",
    "Killing": "容器终止##Killing",
    "Pulling": "拉取镜像##Pulling",
    "Pulled": "镜像拉取完成##Pulled",
    "Cluster status is Unavailable": "集群状态不可用##Cluster status is Unavailable",
    "Cluster status is Error": "集群状态故障##Cluster status is Error",
    "Cluster status is not updated for a long time": "集群状态长时间不更新##Cluster status is not updated for a long time",
}

def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return slug or fallback


def _safe_alarm_alias(value: Any, fallback: str = "cce_alarm_rule") -> str:
    """Return an AOM alias using only API-accepted characters."""
    raw = str(value or "")
    alias = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_-")
    if not alias:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
        alias = f"{fallback}_{digest}"
    alias = alias[:256].strip("_-")
    return alias or fallback


def _sanitize_metric_alarm_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only fields accepted by AddOrUpdateMetricOrEventAlarmRule."""
    allowed_spec_keys = {
        "alarm_rule_template_bind_enable",
        "alarm_rule_template_id",
        "alarm_tags",
        "monitor_objects",
        "monitor_type",
        "no_data_conditions",
        "recovery_conditions",
        "trigger_conditions",
    }
    allowed_condition_keys = {
        "aggregate_type",
        "aggregation_type",
        "aggregation_window",
        "aom_monitor_level",
        "cmdb",
        "expression",
        "metric_labels",
        "metric_name",
        "metric_namespace",
        "metric_query_mode",
        "metric_statistic_method",
        "metric_unit",
        "mix_promql",
        "operator",
        "promql",
        "promql_expr",
        "promql_for",
        "query_match",
        "query_param",
        "thresholds",
        "trigger_interval",
        "trigger_times",
        "trigger_type",
    }
    sanitized = {key: copy.deepcopy(value) for key, value in spec.items() if key in allowed_spec_keys}
    sanitized["trigger_conditions"] = [
        {key: copy.deepcopy(value) for key, value in condition.items() if key in allowed_condition_keys}
        for condition in spec.get("trigger_conditions") or []
        if isinstance(condition, dict)
    ]
    return sanitized


def _sanitize_event_alarm_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only fields accepted by AddOrUpdateMetricOrEventAlarmRule."""
    allowed_spec_keys = {
        "alarm_rule_template_bind_enable",
        "alarm_rule_template_id",
        "alarm_source",
        "event_source",
        "monitor_objects",
        "trigger_conditions",
    }
    allowed_condition_keys = {
        "aggregation_window",
        "event_name",
        "frequency",
        "operator",
        "thresholds",
        "trigger_type",
    }
    sanitized = {key: copy.deepcopy(value) for key, value in spec.items() if key in allowed_spec_keys}
    sanitized["trigger_conditions"] = [
        {key: copy.deepcopy(value) for key, value in condition.items() if key in allowed_condition_keys}
        for condition in spec.get("trigger_conditions") or []
        if isinstance(condition, dict)
    ]
    return sanitized


def _scope_promql_to_cluster(promql: str, cluster_id: str) -> str:
    def add_cluster(match: re.Match[str]) -> str:
        labels = match.group(1).strip()
        if re.search(r'(^|,)\s*cluster\s*=~?\s*"', labels):
            return "{" + labels + "}"
        return "{" + (labels + "," if labels else "") + f'cluster="{cluster_id}"' + "}"

    scoped = re.sub(r"\{([^{}]*)\}", add_cluster, promql)
    if scoped == promql:
        return f"{promql} and on() kube_node_info{{cluster=\"{cluster_id}\"}} >= 0"
    return scoped


def _template_monitor_object(spec: Dict[str, Any], kind: str) -> Dict[str, str]:
    if kind == "event":
        return {"clusterId": CLUSTER_ID_PLACEHOLDER}
    for condition in spec.get("trigger_conditions") or []:
        templates = condition.get("promql_monitor_templates") or []
        if templates:
            return {str(templates[0]): CLUSTER_ID_PLACEHOLDER}
    return {"cluster": CLUSTER_ID_PLACEHOLDER}


def _scope_template_promql(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return _scope_promql_to_cluster(value, CLUSTER_ID_PLACEHOLDER)


def _template_item_to_rule(template_item: Dict[str, Any], template_id: str) -> Optional[Dict[str, Any]]:
    kind = template_item.get("alarm_template_spec_type")
    if kind not in {"metric", "event"}:
        return None

    spec_key = "metric_alarm_template_spec" if kind == "metric" else "event_alarm_template_spec"
    rule_spec_key = "metric_alarm_spec" if kind == "metric" else "event_alarm_spec"
    source_spec = template_item.get(spec_key)
    if not isinstance(source_spec, dict):
        return None

    spec = copy.deepcopy(source_spec)
    spec = _replace_cluster_id(spec, _first_cluster_id(spec), CLUSTER_ID_PLACEHOLDER)
    monitor_object = _template_monitor_object(spec, kind)
    spec["alarm_rule_template_bind_enable"] = False
    spec["alarm_rule_template_id"] = template_id
    spec["bind_alarm_rule_template_info"] = {
        "alarm_rule_template_id": template_id,
        "alarm_rule_template_rule_desc": template_item.get("desc") or "",
        "alarm_rule_template_rule_name": template_item.get("alarm_template_name") or "",
        "monitor_object": monitor_object,
        "related_cloud_service": "CCEFromProm",
    }
    spec["monitor_objects"] = [monitor_object]
    spec["update_alarm_rule"] = template_item.get("update_alarm_rule", True)

    for condition in spec.get("trigger_conditions") or []:
        if not isinstance(condition, dict):
            continue
        for key in ("promql", "promql_expr", "mix_promql"):
            if key in condition:
                condition[key] = _scope_template_promql(condition[key])
        if kind == "event":
            condition.setdefault("frequency", "-1")

    display_name = template_item.get("alarm_template_name") or template_item.get("alarm_template_name_en") or "CCE alarm rule"
    alias = _safe_alarm_alias(template_item.get("alarm_template_name_en") or display_name)
    return {
        "alarm_rule_description": template_item.get("desc") or template_item.get("desc_en") or str(display_name),
        "alarm_rule_enable": True,
        "alarm_rule_name": f"CCE_{display_name}_{CLUSTER_ID_PLACEHOLDER}",
        "alarm_rule_type": kind,
        "alias": alias,
        rule_spec_key: spec,
    }


def _load_cce_alarm_rule_templates_from_cloud(
    region: str,
    ak: Optional[str],
    sk: Optional[str],
    project_id: Optional[str],
    enterprise_project_id: Optional[str],
    template_id: str = CCE_ALARM_RULE_TEMPLATE_ID,
) -> Dict[str, Any]:
    params: List[tuple[str, Any]] = [
        ("type", "template"),
        ("id", template_id),
        ("Enterprise-Project-Id", enterprise_project_id or "all_granted_eps"),
    ]
    result = run_hcloud("AOM", "ListAlarmRuleTemplate", region, params, ak, sk, project_id)
    if not result.get("success"):
        result.update({"action": "load_cce_alarm_rule_template", "template_id": template_id})
        return result

    templates = extract_items(result.get("data"), "alarm_rule_templates", "templates")
    template = next((item for item in templates if item.get("alarm_rule_template_id") == template_id), None)
    if not template:
        return {
            "success": False,
            "action": "load_cce_alarm_rule_template",
            "template_id": template_id,
            "error": f"CCE alarm rule template not found: {template_id}",
            "hcloud_command": result.get("command"),
        }

    rule_templates: List[Dict[str, Any]] = []
    for spec_group in template.get("alarm_template_spec_list") or []:
        for template_item in spec_group.get("alarm_template_spec_items") or []:
            rule = _template_item_to_rule(template_item, template_id)
            if rule:
                rule_templates.append({"raw": rule, "template_item": template_item})

    if not rule_templates:
        return {
            "success": False,
            "action": "load_cce_alarm_rule_template",
            "template_id": template_id,
            "error": "CCE alarm rule template does not contain metric or event template items.",
            "hcloud_command": result.get("command"),
        }

    return {
        "success": True,
        "action": "load_cce_alarm_rule_template",
        "template_id": template_id,
        "template_name": template.get("alarm_rule_template_name") or CCE_ALARM_RULE_TEMPLATE_NAME,
        "template_version": template.get("alarm_rule_template_version"),
        "template_source": template.get("alarm_rule_template_source"),
        "templates": rule_templates,
        "count": len(rule_templates),
        "hcloud_command": result.get("command"),
    }


def _cluster_id_in_rule(rule: Dict[str, Any]) -> Optional[str]:
    match = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        json.dumps(rule, ensure_ascii=False),
    )
    return match.group(0) if match else None


def _candidate_from_rule_template(
    template_rule: Dict[str, Any],
    cluster_id: str,
    prefix: str,
    explicit_prefix: bool,
) -> Dict[str, Any]:
    alias = template_rule.get("alias") or template_rule.get("alarm_rule_name") or "CCE alarm rule"
    old_cluster_id = _cluster_id_in_rule(template_rule)
    if explicit_prefix:
        rule_name = f"{prefix}-{_slug(str(alias), str(alias))}"
    else:
        rule_name = _replace_cluster_id(
            template_rule.get("alarm_rule_name") or f"CCE_{alias}_{cluster_id}",
            old_cluster_id,
            cluster_id,
        )
    return {
        "kind": template_rule.get("alarm_rule_type"),
        "name": str(alias),
        "description": template_rule.get("alarm_rule_description") or str(alias),
        "rule_name": rule_name,
        "display_name": str(alias),
        "_template_rule": template_rule,
    }


def _cce_alarm_rule_candidates(
    cloud_template: Dict[str, Any],
    cluster_id: str,
    rule_name_prefix: Optional[str],
    include_metric_alarms: bool,
    include_event_alarms: bool,
    alarm_items: Optional[str],
) -> List[Dict[str, Any]]:
    explicit_rule_name_prefix = bool(rule_name_prefix)
    prefix = rule_name_prefix or cluster_id
    wanted_items = _split_csv(alarm_items)
    candidates: List[Dict[str, Any]] = []

    for item in cloud_template.get("templates") or []:
        template_rule = item.get("raw") or {}
        kind = template_rule.get("alarm_rule_type")
        if kind == "metric" and not include_metric_alarms:
            continue
        if kind == "event" and not include_event_alarms:
            continue
        candidate = _candidate_from_rule_template(template_rule, cluster_id, prefix, explicit_rule_name_prefix)
        if wanted_items and not _matches_any(candidate["name"], wanted_items):
            continue
        candidates.append(candidate)
    return candidates


def _split_csv(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _matches_any(value: str, candidates: set[str]) -> bool:
    return any(item == value or item in value or value in item for item in candidates)


def _name_key(value: str) -> str:
    value = str(value or "").lower()
    replacements = {
        "百分之八十": "80",
        "百分之十": "10",
        "百分之九十": "90",
        "%": "",
        ">": "",
        "<": "",
        "大于": "",
        "超过": "",
        "不足": "",
        "小于": "",
        " ": "",
        "_": "",
        "-": "",
        "(": "",
        ")": "",
        "（": "",
        "）": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def _promql_metric_names(promql: str) -> set[str]:
    names = set(re.findall(r"\b([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{|\[)", promql or ""))
    return {name for name in names if not name.endswith("_over_time")}


def _to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normalize_alarm_rule_name(rule_name: str) -> str:
    return "_".join(str(rule_name).split())


def _period_to_window(period: int) -> str:
    if period <= 30:
        return "30s"
    if period <= 60:
        return "1m"
    if period <= 300:
        return "5m"
    if period <= 900:
        return "15m"
    return "1h"


def _seconds_to_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _severity_key(alarm_level: Any) -> str:
    mapping = {
        "critical": "1",
        "major": "2",
        "minor": "3",
        "info": "4",
        "warning": "4",
        "important": "2",
    }
    return mapping.get(str(alarm_level).strip().lower(), str(alarm_level))


def _severity_name(alarm_level: Any) -> str:
    mapping = {
        "1": "Critical",
        "2": "Major",
        "3": "Minor",
        "4": "Info",
        "critical": "Critical",
        "major": "Major",
        "minor": "Minor",
        "info": "Info",
        "warning": "Info",
        "important": "Major",
    }
    return mapping.get(str(alarm_level).strip().lower(), str(alarm_level))


def _normalize_event_name(event_name: str) -> str:
    if "##" in event_name:
        return event_name
    return EVENT_NAME_ALIASES.get(event_name, event_name)


def _event_short_name(event_name: str) -> str:
    return event_name.split("##", 1)[1] if "##" in event_name else event_name


def _find_event_template_rule(cloud_template: Dict[str, Any], event_name: str, alias: Optional[str] = None) -> Optional[Dict[str, Any]]:
    normalized = _normalize_event_name(event_name)
    wanted_keys = {
        _name_key(event_name),
        _name_key(normalized),
        _name_key(_event_short_name(normalized)),
    }
    if alias:
        wanted_keys.add(_name_key(alias))

    for item in cloud_template.get("templates") or []:
        raw = item.get("raw") or {}
        if raw.get("alarm_rule_type") != "event":
            continue
        raw_names = {
            _name_key(raw.get("alias") or ""),
            _name_key(raw.get("alarm_rule_name") or ""),
        }
        event_spec = raw.get("event_alarm_spec") or {}
        for condition in event_spec.get("trigger_conditions") or []:
            if not isinstance(condition, dict):
                continue
            raw_event = str(condition.get("event_name") or "")
            raw_names.update({
                _name_key(raw_event),
                _name_key(_event_short_name(raw_event)),
            })
        if wanted_keys & {item for item in raw_names if item}:
            return raw
    return None


def _find_alarm_template_rule(cloud_template: Dict[str, Any], alarm_item: str, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    wanted = _name_key(alarm_item)
    if not wanted:
        return None
    for item in cloud_template.get("templates") or []:
        raw = item.get("raw") or {}
        if kind and raw.get("alarm_rule_type") != kind:
            continue
        raw_names = {
            _name_key(raw.get("alias") or ""),
            _name_key(raw.get("alarm_rule_name") or ""),
        }
        metric_spec = raw.get("metric_alarm_spec") or {}
        for condition in metric_spec.get("trigger_conditions") or []:
            if not isinstance(condition, dict):
                continue
            raw_names.add(_name_key(condition.get("metric_name") or ""))
            raw_names.update(_name_key(metric) for metric in _promql_metric_names(str(condition.get("promql") or "")))
        event_spec = raw.get("event_alarm_spec") or {}
        for condition in event_spec.get("trigger_conditions") or []:
            if not isinstance(condition, dict):
                continue
            raw_event = str(condition.get("event_name") or "")
            raw_names.update({
                _name_key(raw_event),
                _name_key(_event_short_name(raw_event)),
            })
        if wanted in {name for name in raw_names if name}:
            return raw
    return None


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _get_nested(source: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = source
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
            if cur is None:
                break
        if cur is not None:
            return cur
    return None


def _normalize_event(raw: Dict[str, Any], default_status: str) -> Dict[str, Any]:
    metadata = _first_dict(raw.get("metadata"), raw.get("annotations"), raw.get("resource_provider"))
    starts_at = _get_nested(raw, "starts_at", "start_time", "create_time", "occur_time", "arrives_at", "metadata.starts_at")
    try:
        starts_at = int(starts_at) if starts_at is not None else None
    except (TypeError, ValueError):
        starts_at = None

    status = _get_nested(raw, "status", "event_status", "metadata.status") or default_status
    if default_status == "active_alert" and status == default_status:
        status = "firing"
    elif default_status == "history_alert" and status == default_status:
        status = "resolved"

    normalized = {
        "event_sn": _get_nested(raw, "event_sn", "id", "event_id", "metadata.event_sn"),
        "event_name": _get_nested(raw, "event_name", "name", "metadata.event_name") or "Unknown",
        "event_severity": _get_nested(raw, "event_severity", "severity", "level", "metadata.event_severity") or "Unknown",
        "status": status,
        "starts_at": starts_at,
        "resource_id": _get_nested(raw, "resource_id", "resource", "metadata.resource_id") or "",
        "cluster_id": _get_nested(raw, "cluster_id", "metadata.clusterId", "metadata.cluster_id") or "",
        "cluster_name": _get_nested(raw, "cluster_name", "metadata.clusterName", "metadata.cluster_name") or "",
        "cluster_alias_name": _get_nested(raw, "cluster_alias_name", "metadata.clusterAliasName") or "",
        "namespace": _get_nested(raw, "namespace", "metadata.namespace") or "",
        "pod_name": _get_nested(raw, "pod_name", "metadata.podName", "metadata.pod_name") or "",
        "message": _get_nested(raw, "message", "description", "metadata.message") or "",
        "raw": raw,
    }
    if isinstance(metadata, dict):
        normalized["metadata"] = metadata
    return normalized


def _filter_events_by_cluster(events: list, cluster_id: Optional[str] = None, cluster_name: Optional[str] = None) -> list:
    if not cluster_id and not cluster_name:
        return events

    filtered = []
    for event in events:
        resource_id = event.get("resource_id", "")
        if cluster_id and (event.get("cluster_id") == cluster_id or cluster_id in resource_id or cluster_id in str(event.get("raw", ""))):
            filtered.append(event)
            continue
        if cluster_name and (
            event.get("cluster_name") == cluster_name
            or cluster_name in event.get("cluster_alias_name", "")
            or cluster_name in str(event.get("raw", ""))
        ):
            filtered.append(event)
    return filtered


def _rule_matches_scope(rule: Dict[str, Any], cluster_id: Optional[str] = None) -> bool:
    if not cluster_id:
        return True
    raw_text = json.dumps(rule, ensure_ascii=False)
    if cluster_id and cluster_id in raw_text:
        return True
    return False


def _build_metric_alarm_params(
    rule_name: str,
    metric_name: str,
    namespace: str,
    comparison_operator: str,
    threshold: str,
    period: int,
    evaluation_periods: int,
    statistic: str,
    alarm_level: int,
    create_fields: Optional[Dict[str, Any]] = None,
    action_id: str = "add-alarm-action",
) -> List[tuple[str, Any]]:
    fields = create_fields or {}
    level_key = _severity_key(fields.get("alarm_level", alarm_level))
    if fields.get("promql"):
        level_key = fields.get("severity") or fields.get("alarm_level_name") or _severity_name(fields.get("alarm_level", alarm_level))
        threshold = str(fields.get("threshold_value", 0))
    monitor_type = "promql" if fields.get("promql") else fields.get("monitor_type", "all_metric")
    params: List[tuple[str, Any]] = [
        ("action_id", action_id),
        ("alarm_rule_name", _normalize_alarm_rule_name(rule_name)),
        ("alarm_rule_type", "metric"),
        ("alarm_rule_enable", fields.get("is_turn_on", fields.get("alarm_rule_enable", True))),
        ("alarm_rule_description", fields.get("alarm_rule_description") or fields.get("alarm_description") or "Created by Codex hcloud skill."),
        ("metric_alarm_spec.monitor_type", monitor_type),
        ("metric_alarm_spec.trigger_conditions.1.metric_name", metric_name),
        ("metric_alarm_spec.trigger_conditions.1.metric_namespace", namespace),
        ("metric_alarm_spec.trigger_conditions.1.operator", comparison_operator),
        (f"metric_alarm_spec.trigger_conditions.1.thresholds.{level_key}", threshold),
        ("metric_alarm_spec.trigger_conditions.1.aggregation_window", _period_to_window(period)),
        ("metric_alarm_spec.trigger_conditions.1.trigger_times", evaluation_periods),
        ("metric_alarm_spec.trigger_conditions.1.aggregation_type", statistic),
    ]
    if fields.get("unit"):
        params.append(("metric_alarm_spec.trigger_conditions.1.metric_unit", fields["unit"]))
    if fields.get("prom_instance_id"):
        params.append(("prom_instance_id", fields["prom_instance_id"]))
    if fields.get("promql"):
        params = [
            item for item in params
            if item[0] not in {
                "metric_alarm_spec.trigger_conditions.1.metric_namespace",
                "metric_alarm_spec.trigger_conditions.1.operator",
                "metric_alarm_spec.trigger_conditions.1.aggregation_window",
                "metric_alarm_spec.trigger_conditions.1.aggregation_type",
            }
        ]
        metric_labels = fields.get("metric_labels") or ["cluster", "cluster_name", "node"]
        params.extend([
            ("alias", fields.get("alias") or _normalize_alarm_rule_name(rule_name)),
            ("metric_alarm_spec.alarm_rule_template_bind_enable", False),
            ("metric_alarm_spec.alarm_rule_template_id", fields.get("alarm_rule_template_id", "at0000000000000000cce001")),
            ("metric_alarm_spec.alarm_tags.1.custom_tags.1", "resource_type=node"),
            ("metric_alarm_spec.monitor_objects.1.cluster", fields.get("cluster_id")),
            ("metric_alarm_spec.update_alarm_rule", True),
            ("metric_alarm_spec.trigger_conditions.1.metric_query_mode", fields.get("metric_query_mode", "NATIVE_PROM")),
            ("metric_alarm_spec.trigger_conditions.1.trigger_type", fields.get("trigger_type", "FIXED_RATE")),
            ("metric_alarm_spec.trigger_conditions.1.trigger_interval", fields.get("trigger_interval", _period_to_window(period))),
            ("metric_alarm_spec.trigger_conditions.1.promql_for", fields.get("promql_for", _seconds_to_duration(period * evaluation_periods))),
            ("metric_alarm_spec.trigger_conditions.1.promql", fields["promql"]),
            ("metric_alarm_spec.recovery_conditions.recovery_timeframe", fields.get("recovery_timeframe", min(max(evaluation_periods, 1), 3))),
        ])
        for index, label in enumerate(metric_labels, 1):
            params.append((f"metric_alarm_spec.trigger_conditions.1.metric_labels.{index}", label))
    if fields.get("bind_notification_rule_id"):
        params.extend([
            ("alarm_notifications.notification_type", "direct"),
            ("alarm_notifications.notification_enable", True),
            ("alarm_notifications.route_group_enable", False),
            ("alarm_notifications.route_group_rule", ""),
            ("alarm_notifications.bind_notification_rule_id", fields["bind_notification_rule_id"]),
            ("alarm_notifications.notify_frequency", 0),
            ("alarm_notifications.notify_resolved", True),
            ("alarm_notifications.notify_triggered", True),
        ])
    elif not fields.get("promql"):
        params.extend([
            ("alarm_notifications.notification_type", "alarm_policy"),
            ("alarm_notifications.notification_enable", False),
            ("alarm_notifications.route_group_enable", False),
            ("alarm_notifications.notify_frequency", -1),
            ("alarm_notifications.notify_resolved", False),
            ("alarm_notifications.notify_triggered", False),
        ])
    return params


def _preview(action: str, region: str, params: List[tuple[str, Any]], risk: str, message: str) -> Dict[str, Any]:
    command = ["hcloud", "AOM", action, f"--cli-region={region}", "--cli-output=json"]
    for key, value in params:
        if value is not None:
            if isinstance(value, bool):
                value = "true" if value else "false"
            command.append(f"--{key}={value}")
    return {
        "success": True,
        "action": action,
        "region": region,
        "risk": risk,
        "confirm_required": True,
        "will_execute": False,
        "executed": False,
        "hcloud_command": redact_command(command),
        "message": message,
    }


def _insert_payload_value(target: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current: Any = target
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        next_part = parts[index + 1] if not is_last else None
        if isinstance(current, list) and part.isdigit():
            item_index = int(part) - 1
            while len(current) <= item_index:
                current.append({})
            if is_last:
                current[item_index] = value
                return
            current = current[item_index]
            continue

        if is_last:
            current[part] = value
            return

        if next_part and next_part.isdigit() and part != "thresholds":
            current = current.setdefault(part, [])
            continue

        current = current.setdefault(part, {})


def _metric_alarm_payload(params: List[tuple[str, Any]], project_id: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"query": {}, "body": {}}
    if project_id:
        payload["path"] = {"project_id": project_id}
    for key, value in params:
        if key == "action_id":
            payload["query"][key] = value
        elif key == "Enterprise-Project-Id":
            payload.setdefault("header", {})[key] = value
        else:
            _insert_payload_value(payload["body"], key, value)
    return payload


def _custom_promql_payload_from_template(
    template_rule: Dict[str, Any],
    cluster_id: str,
    rule_name: str,
    metric_name: str,
    promql: str,
    fields: Dict[str, Any],
    bind_notification_rule_id: Optional[str],
    prom_instance_id: Optional[str],
    enterprise_project_id: Optional[str],
    project_id: Optional[str],
    threshold: Optional[str],
    period: int,
    evaluation_periods: int,
    alarm_level: int,
) -> Dict[str, Any]:
    candidate = {
        "kind": "metric",
        "display_name": rule_name,
        "promql": promql,
        "description": fields.get("alarm_rule_description") or fields.get("alarm_description"),
    }
    payload = _build_rule_from_template(
        template_rule,
        candidate,
        cluster_id,
        rule_name,
        bind_notification_rule_id,
        prom_instance_id,
        enterprise_project_id,
        project_id,
    )
    body = payload["body"]
    body["alarm_rule_description"] = (
        fields.get("alarm_rule_description")
        or fields.get("alarm_description")
        or body.get("alarm_rule_description")
        or "Created by Codex hcloud skill."
    )

    metric_spec = body.setdefault("metric_alarm_spec", {})
    metric_spec["monitor_type"] = "promql"
    metric_spec["update_alarm_rule"] = True
    metric_spec["monitor_objects"] = [{"cluster": cluster_id}]
    metric_spec["recovery_conditions"] = {
        "recovery_timeframe": fields.get("recovery_timeframe", min(max(evaluation_periods, 1), 3))
    }

    conditions = metric_spec.setdefault("trigger_conditions", [{}])
    if not conditions:
        conditions.append({})
    condition = conditions[0]
    condition.clear()
    severity = fields.get("severity") or fields.get("alarm_level_name") or _severity_name(fields.get("alarm_level", alarm_level))
    condition.update({
        "metric_labels": fields.get("metric_labels") or ["cluster", "cluster_name", "node"],
        "metric_name": metric_name,
        "metric_query_mode": fields.get("metric_query_mode", "NATIVE_PROM"),
        "promql": promql,
        "promql_for": fields.get("promql_for", _seconds_to_duration(period * evaluation_periods)),
        "thresholds": {severity: str(fields.get("threshold_value", threshold if threshold is not None else 0))},
        "trigger_interval": fields.get("trigger_interval", _period_to_window(period)),
        "trigger_times": evaluation_periods,
        "trigger_type": fields.get("trigger_type", "FIXED_RATE"),
    })
    return payload


def _replace_cluster_id(value: Any, old_cluster_id: Optional[str], new_cluster_id: str) -> Any:
    if isinstance(value, str):
        value = value.replace(CLUSTER_ID_PLACEHOLDER, new_cluster_id)
        return value.replace(old_cluster_id, new_cluster_id) if old_cluster_id else value
    if isinstance(value, list):
        return [_replace_cluster_id(item, old_cluster_id, new_cluster_id) for item in value]
    if isinstance(value, dict):
        return {key: _replace_cluster_id(item, old_cluster_id, new_cluster_id) for key, item in value.items()}
    return value


def _first_cluster_id(value: Any) -> Optional[str]:
    if isinstance(value, str):
        match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value)
        return match.group(0) if match else None
    if isinstance(value, list):
        for item in value:
            found = _first_cluster_id(item)
            if found:
                return found
    if isinstance(value, dict):
        for item in value.values():
            found = _first_cluster_id(item)
            if found:
                return found
    return None


def resolve_cce_aom_prom_instance(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve the AOM Prometheus instance ID from the target cluster addon config."""
    list_result = run_hcloud("CCE", "ListAddonInstances", region, [("cluster_id", cluster_id)], ak, sk, project_id)
    if not list_result.get("success"):
        return list_result

    addon_id = None
    for addon in extract_items(list_result.get("data"), "items"):
        metadata = addon.get("metadata") or {}
        if metadata.get("name") == "cie-collector":
            addon_id = metadata.get("uid")
            break
    if not addon_id:
        return {
            "success": False,
            "action": "resolve_cce_aom_prom_instance",
            "cluster_id": cluster_id,
            "error": "cie-collector addon not found in target cluster",
        }

    show_result = run_hcloud(
        "CCE",
        "ShowAddonInstance",
        region,
        [("id", addon_id), ("cluster_id", cluster_id)],
        ak,
        sk,
        project_id,
    )
    if not show_result.get("success"):
        return show_result

    detail = show_result.get("data") or {}
    detail_root = detail.get("addon_instance", detail) if isinstance(detail, dict) else {}
    spec = detail_root.get("spec") or {}
    candidates = []
    custom = spec.get("custom")
    if isinstance(custom, dict):
        candidates.append(("hcloud:cie-collector.spec.custom", custom))
    values = spec.get("values")
    if isinstance(values, dict):
        candidates.append(("hcloud:cie-collector.spec.values", values))
        nested_custom = values.get("custom")
        if isinstance(nested_custom, dict):
            candidates.append(("hcloud:cie-collector.spec.values.custom", nested_custom))

    for source, data in candidates:
        prom_instance_id = data.get("aom_instance_id") or data.get("prom_instance_id") or data.get("aom_id")
        if prom_instance_id:
            return {
                "success": True,
                "action": "resolve_cce_aom_prom_instance",
                "cluster_id": cluster_id,
                "prom_instance_id": prom_instance_id,
                "source": source,
                "hcloud_command": [list_result.get("command"), show_result.get("command")],
            }

    return {
        "success": False,
        "action": "resolve_cce_aom_prom_instance",
        "cluster_id": cluster_id,
        "error": "AOM Prometheus instance ID not found in cie-collector addon config",
        "hcloud_command": [list_result.get("command"), show_result.get("command")],
    }


def _resolve_auto_notification_rule_id(
    region: str,
    cluster_id: str,
    ak: Optional[str],
    sk: Optional[str],
    project_id: Optional[str],
) -> Optional[str]:
    expected = f"auto-cluster-{cluster_id}"
    result = list_aom_action_rules(region, ak, sk, project_id)
    if not result.get("success"):
        return None
    for rule in result.get("rules", []):
        if rule.get("rule_name") == expected:
            return expected
    return None


def _resolve_notification_rule_name(
    region: str,
    bind_notification_rule_id: Optional[str],
    ak: Optional[str],
    sk: Optional[str],
    project_id: Optional[str],
) -> Optional[str]:
    if not bind_notification_rule_id:
        return None
    result = list_aom_action_rules(region, ak, sk, project_id)
    if not result.get("success"):
        return bind_notification_rule_id
    for rule in result.get("rules", []):
        if bind_notification_rule_id in {str(rule.get("id")), str(rule.get("rule_name"))}:
            return str(rule.get("rule_name") or bind_notification_rule_id)
    return bind_notification_rule_id


def create_aom_notification_action_rule(
    region: str,
    rule_name: str,
    notification_topic_urn: str,
    notification_topic_name: str,
    notification_topic_display_name: Optional[str],
    notification_user_name: Optional[str],
    description: Optional[str] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    expected = rule_name
    existing = list_aom_action_rules(region, ak, sk, project_id)
    if not existing.get("success"):
        return existing

    for rule in existing.get("rules", []):
        if rule.get("rule_name") == expected:
            return {
                "success": True,
                "action": "create_aom_notification_action_rule",
                "created": False,
                "rule_name": expected,
                "message": "Notification action rule already exists.",
            }

    if not notification_topic_urn or not notification_topic_name:
        return {
            "success": False,
            "action": "create_aom_notification_action_rule",
            "created": False,
            "rule_name": expected,
            "error": "notification_topic_urn and notification_topic_name are required to create an AOM notification action rule.",
        }

    resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
    if not resolved_project_id:
        return {
            "success": False,
            "action": "create_aom_notification_action_rule",
            "created": False,
            "rule_name": expected,
            "error": "Project ID not found. Please provide project_id parameter.",
        }

    topic = {
        "name": notification_topic_name,
        "push_policy": 0,
        "topic_urn": notification_topic_urn,
    }
    if notification_topic_display_name:
        topic["display_name"] = notification_topic_display_name

    payload = {
        "path": {"project_id": resolved_project_id},
        "body": {
            "desc": description or "Automatically generated by the container service",
            "notification_template": "aom.built-in.template.zh",
            "project_id": resolved_project_id,
            "rule_name": expected,
            "smn_topics": [topic],
            "time_zone": "Asia/Shanghai",
            "type": "1",
            "user_name": notification_user_name or "hcloud",
        },
    }

    if not confirm:
        return {
            "success": True,
            "action": "create_aom_notification_action_rule",
            "region": region,
            "risk": "R2",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "created": False,
            "rule_name": expected,
            "notification_topic_name": notification_topic_name,
            "notification_topic_urn": notification_topic_urn,
            "hcloud_command": [
                "hcloud",
                "AOM",
                "AddActionRule",
                f"--cli-region={region}",
                "--cli-output=json",
                "--cli-jsonInput=<generated-aom-notification-action-rule-payload>",
            ],
            "rule_payload": payload,
            "message": "Preview only. Add confirm=true to create the AOM notification action rule through hcloud.",
        }

    result = run_hcloud_json_input("AOM", "AddActionRule", region, payload, ak, sk, resolved_project_id)
    if not result.get("success"):
        refreshed = list_aom_action_rules(region, ak, sk, resolved_project_id)
        for rule in refreshed.get("rules", []):
            if rule.get("rule_name") == expected:
                result["success"] = True
                result["verified_after_create"] = True
                result["message"] = "AddActionRule did not return JSON, but the notification action rule exists after creation."
                break
    result.update({
        "action": "create_aom_notification_action_rule",
        "created": result.get("success", False),
        "rule_name": expected,
    })
    return result


def _find_template_rule(candidate: Dict[str, Any], template_rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    wanted_kind = candidate.get("kind")
    display_key = _name_key(candidate.get("display_name") or candidate.get("name") or candidate.get("event_name") or "")
    candidate_metric_names = _promql_metric_names(candidate.get("promql", ""))
    if candidate.get("metric_name"):
        candidate_metric_names.add(str(candidate["metric_name"]))

    for item in template_rules:
        raw = item.get("raw") or {}
        if raw.get("alarm_rule_type") != wanted_kind:
            continue
        alias_key = _name_key(raw.get("alias") or raw.get("alarm_rule_name") or "")

        if wanted_kind == "event":
            raw_event_spec = raw.get("event_alarm_spec") or {}
            raw_conditions = raw_event_spec.get("trigger_conditions") or []
            raw_event_names = {condition.get("event_name") for condition in raw_conditions if isinstance(condition, dict)}
            if candidate.get("event_name") in raw_event_names or display_key and display_key in alias_key:
                return raw
            continue

        raw_metric_spec = raw.get("metric_alarm_spec") or {}
        raw_conditions = raw_metric_spec.get("trigger_conditions") or []
        raw_metric_names = {condition.get("metric_name") for condition in raw_conditions if isinstance(condition, dict)}
        for condition in raw_conditions:
            if isinstance(condition, dict):
                raw_metric_names.update(_promql_metric_names(str(condition.get("promql") or "")))
        raw_metric_names.discard(None)
        if candidate_metric_names and raw_metric_names and candidate_metric_names & raw_metric_names:
            return raw
        if display_key and alias_key and (display_key in alias_key or alias_key in display_key):
            return raw
    return None


def _build_rule_from_template(
    template_rule: Dict[str, Any],
    candidate: Dict[str, Any],
    cluster_id: str,
    rule_name: str,
    bind_notification_rule_id: Optional[str],
    prom_instance_id: Optional[str],
    enterprise_project_id: Optional[str],
    project_id: Optional[str],
    action_id: str = "add-alarm-action",
) -> Dict[str, Any]:
    old_cluster_id = _first_cluster_id(template_rule)
    body: Dict[str, Any] = {}
    if "metric_alarm_spec" in template_rule:
        body["metric_alarm_spec"] = _sanitize_metric_alarm_spec(template_rule["metric_alarm_spec"])
    if "event_alarm_spec" in template_rule:
        body["event_alarm_spec"] = _sanitize_event_alarm_spec(template_rule["event_alarm_spec"])
    body.update({
        "alarm_rule_description": template_rule.get("alarm_rule_description") or candidate.get("description") or "Created by Codex hcloud skill.",
        "alarm_rule_enable": True,
        "alarm_rule_name": _normalize_alarm_rule_name(rule_name),
        "alarm_rule_type": template_rule.get("alarm_rule_type"),
        "alias": _safe_alarm_alias(template_rule.get("alias") or candidate.get("display_name") or rule_name),
    })
    effective_prom_instance_id = prom_instance_id
    if effective_prom_instance_id:
        body["prom_instance_id"] = effective_prom_instance_id

    is_event_rule = body.get("alarm_rule_type") == "event"
    if bind_notification_rule_id:
        notifications = body.setdefault("alarm_notifications", {})
        notifications.update({
            "notification_type": "direct",
            "notification_enable": True,
            "route_group_enable": False,
            "bind_notification_rule_id": bind_notification_rule_id,
            "notify_frequency": -1 if is_event_rule else 0,
            "notify_resolved": True,
            "notify_triggered": True,
        })
    elif not is_event_rule and "alarm_notifications" not in body:
        body["alarm_notifications"] = {
            "notification_type": "alarm_policy",
            "notification_enable": False,
            "route_group_enable": False,
            "notify_frequency": -1,
            "notify_resolved": False,
            "notify_triggered": False,
        }

    body = _replace_cluster_id(body, old_cluster_id, cluster_id)
    event_spec = body.get("event_alarm_spec")
    if isinstance(event_spec, dict):
        if event_spec.get("alarm_source") == "CCE":
            event_spec["alarm_source"] = "systemEvent"
        conditions = event_spec.get("trigger_conditions") or []
        event_name = next(
            (condition.get("event_name") for condition in conditions if isinstance(condition, dict) and condition.get("event_name")),
            None,
        )
        if event_name:
            monitor_objects = event_spec.setdefault("monitor_objects", [{"clusterId": cluster_id}])
            for monitor_object in monitor_objects:
                if isinstance(monitor_object, dict):
                    monitor_object.setdefault("event_name", event_name)
    header_ep = enterprise_project_id
    payload: Dict[str, Any] = {
        "query": {"action_id": action_id},
        "body": body,
    }
    if project_id:
        payload["path"] = {"project_id": project_id}
    if header_ep:
        payload["header"] = {"Enterprise-Project-Id": header_ep}
    return payload


def list_aom_alarm_rules(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    enterprise_project_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
) -> Dict[str, Any]:
    filtered = bool(cluster_id)
    page_limit = max(1, min(limit, 200))
    scan_offset = offset
    all_rules: List[Dict[str, Any]] = []
    hcloud_commands = []
    raw_pages = []

    while True:
        params: List[tuple[str, Any]] = [
            ("limit", str(page_limit)),
            ("offset", str(scan_offset)),
            ("Enterprise-Project-Id", enterprise_project_id or "all_granted_eps"),
        ]
        result = run_hcloud("AOM", "ListMetricOrEventAlarmRule", region, params, ak, sk, project_id)
        if not result["success"]:
            return result

        hcloud_commands.append(result["command"])
        raw_pages.append(result.get("data"))
        page_rules = extract_items(result.get("data"), "alarm_rules", "rules")
        all_rules.extend(page_rules)
        if not filtered or len(page_rules) < page_limit:
            break
        scan_offset += page_limit

    total_count = len(all_rules)
    rules = [
        rule for rule in all_rules
        if _rule_matches_scope(rule, cluster_id)
    ] if filtered else all_rules

    formatted = []
    for rule in rules:
        metric_spec = rule.get("metric_alarm_spec") or {}
        event_spec = rule.get("event_alarm_spec") or {}
        formatted.append({
            "rule_name": rule.get("alarm_rule_name") or rule.get("name"),
            "rule_id": rule.get("alarm_rule_id") or rule.get("id"),
            "rule_type": rule.get("alarm_rule_type"),
            "enabled": rule.get("alarm_rule_enable"),
            "status": rule.get("alarm_rule_status"),
            "severity": rule.get("event_severity"),
            "metric_alarm_spec": metric_spec,
            "event_alarm_spec": event_spec,
            "raw": rule,
        })

    return {
        "success": True,
        "region": region,
        "action": "list_aom_alarm_rules",
        "filtered": filtered,
        "cluster_id": cluster_id,
        "total_count": total_count,
        "count": len(formatted),
        "rules": formatted,
        "raw": raw_pages[-1] if len(raw_pages) == 1 else raw_pages,
        "hcloud_command": hcloud_commands[-1] if len(hcloud_commands) == 1 else hcloud_commands,
    }


def _existing_alarm_rule(region: str, rule_name: str, cluster_id: Optional[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Optional[Dict[str, Any]]:
    result = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, cluster_id=cluster_id)
    if not result.get("success"):
        return None
    return next((rule for rule in result.get("rules", []) if rule.get("rule_name") == rule_name), None)


def create_aom_alarm_rule(
    region: str,
    rule_name: Optional[str],
    metric_name: Optional[str],
    namespace: Optional[str],
    comparison_operator: Optional[str],
    threshold: Optional[str],
    period: int,
    evaluation_periods: int,
    statistic: Optional[str],
    alarm_level: int,
    create_fields: Optional[Dict[str, Any]] = None,
    cluster_id: Optional[str] = None,
    alarm_item: Optional[str] = None,
    prom_instance_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    create_fields = create_fields or {}
    if cluster_id and alarm_item:
        cloud_template = _load_cce_alarm_rule_templates_from_cloud(
            region,
            ak,
            sk,
            project_id,
            enterprise_project_id,
            CCE_ALARM_RULE_TEMPLATE_ID,
        )
        if not cloud_template.get("success"):
            return {
                "success": False,
                "action": "create_aom_alarm_rule",
                "executed": False,
                "error": "Unable to load CCE alarm rule template through hcloud.",
                "template": cloud_template,
            }
        template_rule = _find_alarm_template_rule(cloud_template, alarm_item, "metric")
        if not template_rule:
            return {
                "success": False,
                "action": "create_aom_alarm_rule",
                "executed": False,
                "error": f"No CCE metric alarm template matched alarm_item: {alarm_item}",
                "template_id": CCE_ALARM_RULE_TEMPLATE_ID,
            }
        if rule_name:
            candidate = _candidate_from_rule_template(template_rule, cluster_id, rule_name, True)
            effective_rule_name = _normalize_alarm_rule_name(rule_name)
        else:
            candidate = _candidate_from_rule_template(template_rule, cluster_id, "", False)
            effective_rule_name = _normalize_alarm_rule_name(candidate["rule_name"])
        if not confirm:
            preview = {
                "success": True,
                "action": "AddOrUpdateMetricOrEventAlarmRule",
                "region": region,
                "risk": "MEDIUM",
                "confirm_required": True,
                "will_execute": False,
                "executed": False,
                "hcloud_command": [
                    "hcloud",
                    "AOM",
                    "AddOrUpdateMetricOrEventAlarmRule",
                    f"--cli-region={region}",
                    "--cli-output=json",
                    "--cli-jsonInput=<generated-cce-aom-template-payload>",
                ],
                "template_id": CCE_ALARM_RULE_TEMPLATE_ID,
                "matched_template": {
                    "rule_name": template_rule.get("alarm_rule_name"),
                    "alias": template_rule.get("alias"),
                },
                "rule_name": effective_rule_name,
                "message": "Preview only. Add confirm=true to create the AOM metric alarm rule through the same CCE template payload path as batch creation.",
            }
            if not create_fields.get("bind_notification_rule_id"):
                preview["required_for_confirm"] = ["bind_notification_rule_id"]
            return preview
        if not create_fields.get("bind_notification_rule_id"):
            return {
                "success": False,
                "action": "create_aom_alarm_rule",
                "executed": False,
                "error": "bind_notification_rule_id is required for confirmed AOM alarm rule creation. Query existing action rules with huawei_list_aom_action_rules and pass an existing rule ID.",
            }
        notification_rule_name = _resolve_notification_rule_name(
            region,
            str(create_fields["bind_notification_rule_id"]),
            ak,
            sk,
            project_id,
        )
        existing_rule = _existing_alarm_rule(region, effective_rule_name, cluster_id, ak, sk, project_id)
        if existing_rule:
            return {
                "success": True,
                "action": "create_aom_alarm_rule",
                "executed": False,
                "skipped": True,
                "reason": "matching alarm rule already exists",
                "rule": existing_rule,
            }
        effective_prom_instance_id = prom_instance_id
        if not effective_prom_instance_id:
            prom_result = resolve_cce_aom_prom_instance(region, cluster_id, ak, sk, project_id)
            if prom_result.get("success") and prom_result.get("prom_instance_id"):
                effective_prom_instance_id = str(prom_result["prom_instance_id"])
        resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
        if not resolved_project_id:
            return {"success": False, "error": "Project ID not found for JSON input. Please provide project_id parameter."}
        payload = _build_rule_from_template(
            template_rule,
            candidate,
            cluster_id,
            effective_rule_name,
            notification_rule_name,
            effective_prom_instance_id,
            enterprise_project_id,
            resolved_project_id,
        )
        result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
        result.update({"action": "create_aom_alarm_rule", "executed": result["success"]})
        return result

    missing = [
        key for key, value in {
            "rule_name": rule_name,
            "metric_name": metric_name,
            "namespace": namespace,
            "comparison_operator": comparison_operator,
            "threshold": threshold,
            "period": period,
            "evaluation_periods": evaluation_periods,
            "statistic": statistic,
            "alarm_level": alarm_level,
        }.items()
        if value in {None, "", 0}
    ]
    if missing:
        return {
            "success": False,
            "action": "create_aom_alarm_rule",
            "executed": False,
            "error": "Manual metric alarm creation requires these parameters, or use template mode with cluster_id and alarm_item: " + ", ".join(missing),
        }
    if create_fields.get("bind_notification_rule_id"):
        create_fields["bind_notification_rule_id"] = _resolve_notification_rule_name(
            region,
            str(create_fields["bind_notification_rule_id"]),
            ak,
            sk,
            project_id,
        )
    params = _build_metric_alarm_params(
        str(rule_name), str(metric_name), str(namespace), str(comparison_operator), str(threshold),
        period, evaluation_periods, str(statistic), alarm_level, create_fields,
    )
    if not confirm:
        preview = _preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "MEDIUM", "Preview only. Add confirm=true to create the AOM metric alarm rule through hcloud.")
        preview["rule_payload"] = dict(params)
        if not create_fields.get("bind_notification_rule_id"):
            preview["required_for_confirm"] = ["bind_notification_rule_id"]
        return preview

    if not create_fields.get("bind_notification_rule_id"):
        return {
            "success": False,
            "action": "create_aom_alarm_rule",
            "executed": False,
            "error": "bind_notification_rule_id is required for confirmed AOM alarm rule creation. Query existing action rules with huawei_list_aom_action_rules and pass an existing rule ID.",
        }
    existing_rule = _existing_alarm_rule(region, _normalize_alarm_rule_name(rule_name), None, ak, sk, project_id)
    if existing_rule:
        return {
            "success": True,
            "action": "create_aom_alarm_rule",
            "executed": False,
            "skipped": True,
            "reason": "matching alarm rule already exists",
            "rule": existing_rule,
        }

    if create_fields and create_fields.get("promql") and cluster_id and metric_name:
        cloud_template = _load_cce_alarm_rule_templates_from_cloud(
            region,
            ak,
            sk,
            project_id,
            enterprise_project_id,
            CCE_ALARM_RULE_TEMPLATE_ID,
        )
        template_rule = None
        if cloud_template.get("success"):
            template_rule = _find_template_rule(
                {
                    "kind": "metric",
                    "display_name": rule_name or metric_name,
                    "metric_name": str(metric_name),
                    "promql": str(create_fields["promql"]),
                },
                cloud_template.get("templates", []),
            )
        if template_rule:
            resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
            if not resolved_project_id:
                return {"success": False, "error": "Project ID not found for JSON input. Please provide project_id parameter."}
            payload = _custom_promql_payload_from_template(
                template_rule,
                cluster_id,
                _normalize_alarm_rule_name(str(rule_name)),
                str(metric_name),
                str(create_fields["promql"]),
                create_fields,
                str(create_fields["bind_notification_rule_id"]),
                str(create_fields["prom_instance_id"]) if create_fields.get("prom_instance_id") else prom_instance_id,
                enterprise_project_id,
                resolved_project_id,
                str(threshold) if threshold is not None else None,
                period,
                evaluation_periods,
                alarm_level,
            )
            result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
            result.update({
                "action": "create_aom_alarm_rule",
                "executed": result["success"],
                "template_payload": True,
            })
            return result

    if create_fields and create_fields.get("promql"):
        resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
        if not resolved_project_id:
            return {"success": False, "error": "Project ID not found for JSON input. Please provide project_id parameter."}
        payload = _metric_alarm_payload(params, resolved_project_id)
        result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
    else:
        result = run_hcloud("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "create_aom_alarm_rule", "executed": result["success"]})
    return result


def create_aom_event_alarm_rule(
    region: str,
    cluster_id: str,
    rule_name: Optional[str],
    event_name: str,
    bind_notification_rule_id: Optional[str] = None,
    event_label: Optional[str] = None,
    alarm_level: str = "Major",
    description: Optional[str] = None,
    alias: Optional[str] = None,
    trigger_type: str = "immediately",
    frequency: str = "-1",
    prom_instance_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    effective_prom_instance_id = prom_instance_id
    if not effective_prom_instance_id:
        prom_result = resolve_cce_aom_prom_instance(region, cluster_id, ak, sk, project_id)
        if prom_result.get("success") and prom_result.get("prom_instance_id"):
            effective_prom_instance_id = str(prom_result["prom_instance_id"])

    cloud_template = _load_cce_alarm_rule_templates_from_cloud(
        region,
        ak,
        sk,
        project_id,
        enterprise_project_id,
        CCE_ALARM_RULE_TEMPLATE_ID,
    )
    if not cloud_template.get("success"):
        return {
            "success": False,
            "action": "create_aom_event_alarm_rule",
            "executed": False,
            "error": "Unable to load CCE alarm rule template through hcloud.",
            "template": cloud_template,
        }
    template_rule = _find_event_template_rule(cloud_template, event_name, alias)
    if not template_rule:
        return {
            "success": False,
            "action": "create_aom_event_alarm_rule",
            "executed": False,
            "error": f"No CCE event alarm template matched event_name: {event_name}",
            "template_id": CCE_ALARM_RULE_TEMPLATE_ID,
        }
    if rule_name:
        candidate = _candidate_from_rule_template(template_rule, cluster_id, rule_name, True)
        effective_rule_name = _normalize_alarm_rule_name(rule_name)
    else:
        candidate = _candidate_from_rule_template(template_rule, cluster_id, "", False)
        effective_rule_name = _normalize_alarm_rule_name(candidate["rule_name"])

    if not confirm:
        preview = {
            "success": True,
            "action": "AddOrUpdateMetricOrEventAlarmRule",
            "region": region,
            "risk": "MEDIUM",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "hcloud_command": [
                "hcloud",
                "AOM",
                "AddOrUpdateMetricOrEventAlarmRule",
                f"--cli-region={region}",
                "--cli-output=json",
                "--cli-jsonInput=<generated-cce-aom-template-payload>",
            ],
            "template_id": CCE_ALARM_RULE_TEMPLATE_ID,
            "matched_template": {
                "rule_name": template_rule.get("alarm_rule_name"),
                "alias": template_rule.get("alias"),
            },
            "rule_name": effective_rule_name,
            "message": "Preview only. Add confirm=true to create the AOM event alarm rule through the same CCE template payload path as batch creation.",
        }
        if not bind_notification_rule_id:
            preview["required_for_confirm"] = ["bind_notification_rule_id"]
        return preview

    if not bind_notification_rule_id:
        return {
            "success": False,
            "action": "create_aom_event_alarm_rule",
            "executed": False,
            "error": "bind_notification_rule_id is required for confirmed AOM event alarm rule creation. Query existing action rules with huawei_list_aom_action_rules and pass an existing rule ID.",
        }
    existing_rule = _existing_alarm_rule(region, effective_rule_name, cluster_id, ak, sk, project_id)
    if existing_rule:
        return {
            "success": True,
            "action": "create_aom_event_alarm_rule",
            "executed": False,
            "skipped": True,
            "reason": "matching alarm rule already exists",
            "rule": existing_rule,
        }

    resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
    if not resolved_project_id:
        return {"success": False, "error": "Project ID not found for JSON input. Please provide project_id parameter."}

    payload = _build_rule_from_template(
        template_rule,
        candidate,
        cluster_id,
        effective_rule_name,
        _resolve_notification_rule_name(region, bind_notification_rule_id, ak, sk, project_id),
        effective_prom_instance_id,
        enterprise_project_id,
        resolved_project_id,
    )
    result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
    result.update({"action": "create_aom_event_alarm_rule", "executed": result["success"]})
    return result


def configure_cce_aom_alarm_rules(
    region: str,
    cluster_id: str,
    bind_notification_rule_id: Optional[str] = None,
    rule_name_prefix: Optional[str] = None,
    include_metric_alarms: bool = True,
    include_event_alarms: bool = True,
    alarm_items: Optional[str] = None,
    skip_existing: bool = True,
    prom_instance_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    alarm_template_id: str = CCE_ALARM_RULE_TEMPLATE_ID,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    explicit_rule_name_prefix = bool(rule_name_prefix)
    cloud_template = _load_cce_alarm_rule_templates_from_cloud(
        region,
        ak,
        sk,
        project_id,
        enterprise_project_id,
        alarm_template_id or CCE_ALARM_RULE_TEMPLATE_ID,
    )
    if not cloud_template.get("success"):
        return {
            "success": False,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "executed": False,
            "error": "Unable to load CCE alarm rule template through hcloud.",
            "template": cloud_template,
        }
    embedded_template_rules = cloud_template.get("templates") or []
    candidates = _cce_alarm_rule_candidates(
        cloud_template,
        cluster_id,
        rule_name_prefix,
        include_metric_alarms,
        include_event_alarms,
        alarm_items,
    )

    if not candidates:
        return {
            "success": False,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "error": "No alarm templates matched the requested filters.",
        }

    if not confirm:
        preview_commands = []
        for candidate in candidates[:10]:
            if candidate.get("_template_rule"):
                preview_commands.append([
                    "hcloud",
                    "AOM",
                    "AddOrUpdateMetricOrEventAlarmRule",
                    f"--cli-region={region}",
                    "--cli-output=json",
                    "--cli-jsonInput=<generated-cce-aom-template-payload>",
                ])
            elif candidate["kind"] == "metric":
                fields = {
                    "promql": candidate["promql"],
                    "cluster_id": cluster_id,
                    "prom_instance_id": prom_instance_id,
                    "bind_notification_rule_id": bind_notification_rule_id,
                    "alarm_rule_description": candidate["description"],
                    "severity": "Major",
                }
                params = _build_metric_alarm_params(
                    candidate["rule_name"],
                    candidate["metric_name"],
                    candidate["namespace"],
                    candidate["comparison_operator"],
                    candidate["threshold"],
                    candidate["period"],
                    candidate["evaluation_periods"],
                    candidate["statistic"],
                    candidate["alarm_level"],
                    fields,
                )
                preview_commands.append(_preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "R2", "Preview only.")["hcloud_command"])
            else:
                preview_commands.append(
                    create_aom_event_alarm_rule(
                        region=region,
                        cluster_id=cluster_id,
                        rule_name=candidate["rule_name"],
                        event_name=candidate["event_name"],
                        bind_notification_rule_id=bind_notification_rule_id,
                        alarm_level=candidate["alarm_level"],
                        description=candidate["description"],
                        prom_instance_id=prom_instance_id,
                        enterprise_project_id=enterprise_project_id,
                        confirm=False,
                    )["hcloud_command"]
                )
        return {
            "success": True,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "risk": "R2",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "alarm_template_id": cloud_template.get("template_id"),
            "alarm_template_name": cloud_template.get("template_name"),
            "alarm_template_version": cloud_template.get("template_version"),
            "alarm_template_source": "cloud",
            "template_count": len(candidates),
            "metric_template_count": sum(1 for item in candidates if item["kind"] == "metric"),
            "event_template_count": sum(1 for item in candidates if item["kind"] == "event"),
            "rules": [{"kind": item["kind"], "rule_name": item["rule_name"], "source_name": item["name"], "display_name": item.get("display_name")} for item in candidates],
            "hcloud_command_samples": preview_commands,
            "notes": [
                "Add confirm=true to create these AOM alarm rules through hcloud.",
                "bind_notification_rule_id is required during confirmed execution. Query existing rules with huawei_list_aom_action_rules or create one with huawei_create_aom_notification_action_rule first.",
                "skip_existing is evaluated only during confirmed execution.",
            ],
        }

    existing_names: set[str] = set()
    template_rules: List[Dict[str, Any]] = []
    if skip_existing:
        existing = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, cluster_id=cluster_id)
        if not existing.get("success"):
            return existing
        template_rules = existing.get("rules", [])
        existing_names = {
            _normalize_alarm_rule_name(str(rule.get("rule_name")))
            for rule in existing.get("rules", [])
            if rule.get("rule_name")
        }
    else:
        existing = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, cluster_id=cluster_id)
        if existing.get("success"):
            template_rules = existing.get("rules", [])

    resolved_prom_instance_id = prom_instance_id
    if not resolved_prom_instance_id and any(candidate.get("_template_rule") for candidate in candidates):
        prom_resolution = resolve_cce_aom_prom_instance(region, cluster_id, ak, sk, project_id)
        if not prom_resolution.get("success"):
            return {
                "success": False,
                "action": "configure_cce_aom_alarm_rules",
                "region": region,
                "cluster_id": cluster_id,
                "executed": False,
                "error": "Unable to resolve AOM Prometheus instance ID for target cluster.",
                "resolution": prom_resolution,
            }
        resolved_prom_instance_id = prom_resolution.get("prom_instance_id")

    resolved_notification_rule_id = _resolve_notification_rule_name(region, bind_notification_rule_id, ak, sk, project_id)
    if not resolved_notification_rule_id and any(candidate.get("kind") in {"event", "metric"} for candidate in candidates):
        return {
            "success": False,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "executed": False,
            "template_count": len(candidates),
            "created_count": 0,
            "skipped_count": 0,
            "failed_count": len(candidates),
            "error": "bind_notification_rule_id is required before creating CCE AOM alarm rules.",
            "bind_notification_rule_id": None,
            "next_steps": [
                "Call huawei_list_aom_action_rules to list existing notification action rules and ask the user to choose one.",
                "Or call huawei_create_aom_notification_action_rule with notification_topic_name and notification_topic_urn to create a new rule, then retry with bind_notification_rule_id.",
            ],
        }

    created = []
    skipped = []
    failed = []
    for candidate in candidates:
        normalized_name = _normalize_alarm_rule_name(candidate["rule_name"])
        if skip_existing and normalized_name in existing_names:
            skipped.append({"rule_name": candidate["rule_name"], "reason": "already exists"})
            continue

        existing_template_rule = _find_template_rule(candidate, template_rules)
        if existing_template_rule and skip_existing and not explicit_rule_name_prefix:
            skipped.append({
                "rule_name": existing_template_rule.get("alarm_rule_name") or candidate["rule_name"],
                "reason": "matching template rule already exists",
            })
            continue
        is_update = bool(existing_template_rule) and not skip_existing
        template_rule = existing_template_rule
        if not template_rule:
            template_rule = candidate.get("_template_rule") or _find_template_rule(candidate, embedded_template_rules)
        if template_rule:
            if candidate.get("kind") == "event" and not resolved_notification_rule_id:
                result = {
                    "success": False,
                    "action": "configure_cce_aom_alarm_rules.template_create",
                    "executed": False,
                    "error": (
                        "AOM event alarm rule creation requires a notification action rule, "
                        "but automatic creation failed."
                    ),
                }
                entry = {
                    "kind": candidate["kind"],
                    "rule_name": candidate["rule_name"],
                    "source_name": candidate["name"],
                    "result": result,
                }
                failed.append(entry)
                continue
            effective_rule_name = candidate["rule_name"]
            resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
            if not resolved_project_id:
                result = {"success": False, "error": "Project ID not found. Please provide project_id parameter."}
            else:
                payload = _build_rule_from_template(
                    template_rule,
                    candidate,
                    cluster_id,
                    effective_rule_name,
                    resolved_notification_rule_id,
                    resolved_prom_instance_id,
                    enterprise_project_id,
                    resolved_project_id,
                    "update-alarm-action" if is_update else "add-alarm-action",
                )
                result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
                result.update({
                    "action": "configure_cce_aom_alarm_rules.template_update" if is_update else "configure_cce_aom_alarm_rules.template_create",
                    "executed": result["success"],
                })
        elif candidate["kind"] == "metric":
            fields = {
                "promql": candidate["promql"],
                "cluster_id": cluster_id,
                "prom_instance_id": resolved_prom_instance_id,
                "bind_notification_rule_id": bind_notification_rule_id,
                "alarm_rule_description": candidate["description"],
                "severity": "Major",
            }
            result = create_aom_alarm_rule(
                region=region,
                rule_name=candidate["rule_name"],
                metric_name=candidate["metric_name"],
                namespace=candidate["namespace"],
                comparison_operator=candidate["comparison_operator"],
                threshold=candidate["threshold"],
                period=candidate["period"],
                evaluation_periods=candidate["evaluation_periods"],
                statistic=candidate["statistic"],
                alarm_level=candidate["alarm_level"],
                create_fields=fields,
                confirm=True,
                ak=ak,
                sk=sk,
                project_id=project_id,
            )
        else:
            result = create_aom_event_alarm_rule(
                region=region,
                cluster_id=cluster_id,
                rule_name=candidate["rule_name"],
                event_name=candidate["event_name"],
                bind_notification_rule_id=resolved_notification_rule_id,
                alarm_level=candidate["alarm_level"],
                description=candidate["description"],
                prom_instance_id=resolved_prom_instance_id,
                enterprise_project_id=enterprise_project_id,
                confirm=True,
                ak=ak,
                sk=sk,
                project_id=project_id,
            )

        entry = {
            "kind": candidate["kind"],
            "rule_name": candidate["rule_name"],
            "source_name": candidate["name"],
            "result": result,
        }
        if result.get("success"):
            created.append(entry)
        elif (result.get("data") or {}).get("error_code") == "AOM.02021062":
            skipped.append({"rule_name": candidate["rule_name"], "reason": "already exists"})
        else:
            failed.append(entry)

    return {
        "success": not failed,
        "action": "configure_cce_aom_alarm_rules",
        "region": region,
        "cluster_id": cluster_id,
        "executed": True,
        "alarm_template_id": cloud_template.get("template_id"),
        "alarm_template_name": cloud_template.get("template_name"),
        "alarm_template_version": cloud_template.get("template_version"),
        "alarm_template_source": "cloud",
        "template_count": len(candidates),
        "created_count": len(created),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "bind_notification_rule_id": resolved_notification_rule_id,
    }


def _rule_matches_any_candidate(rule: Dict[str, Any], candidates: List[Dict[str, Any]]) -> bool:
    rule_name = _normalize_alarm_rule_name(str(rule.get("rule_name") or ""))
    candidate_names = {
        _normalize_alarm_rule_name(str(candidate.get("rule_name") or ""))
        for candidate in candidates
        if candidate.get("rule_name")
    }
    if rule_name and rule_name in candidate_names:
        return True

    for candidate in candidates:
        if _find_template_rule(candidate, [rule]):
            return True
    return False


def cleanup_cce_aom_alarm_rules(
    region: str,
    cluster_id: str,
    rule_name_prefix: Optional[str] = None,
    include_metric_alarms: bool = True,
    include_event_alarms: bool = True,
    alarm_items: Optional[str] = None,
    alarm_template_id: str = CCE_ALARM_RULE_TEMPLATE_ID,
    delete_auto_notification_rule: bool = False,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    cloud_template = _load_cce_alarm_rule_templates_from_cloud(
        region,
        ak,
        sk,
        project_id,
        enterprise_project_id,
        alarm_template_id or CCE_ALARM_RULE_TEMPLATE_ID,
    )
    if not cloud_template.get("success"):
        return {
            "success": False,
            "action": "cleanup_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "executed": False,
            "error": "Unable to load CCE alarm rule template through hcloud.",
            "template": cloud_template,
        }

    candidates = _cce_alarm_rule_candidates(
        cloud_template,
        cluster_id,
        rule_name_prefix,
        include_metric_alarms,
        include_event_alarms,
        alarm_items,
    )
    if not candidates:
        return {
            "success": False,
            "action": "cleanup_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "executed": False,
            "error": "No alarm templates matched the requested filters.",
        }

    existing = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, enterprise_project_id=enterprise_project_id, cluster_id=cluster_id)
    if not existing.get("success"):
        return existing

    matched_rules = [
        rule for rule in existing.get("rules", [])
        if _rule_matches_any_candidate(rule, candidates)
    ]
    auto_notification_rule = f"auto-cluster-{cluster_id}"
    notification_rule_exists = False
    if delete_auto_notification_rule:
        notification_rule_exists = bool(_resolve_auto_notification_rule_id(region, cluster_id, ak, sk, project_id))

    if not confirm:
        delete_commands = [
            _preview(
                "DeleteMetricOrEventAlarmRule",
                region,
                [("alarm_rules.1", rule["rule_name"])],
                "R0",
                "Preview only. Add confirm=true to delete the CCE AOM alarm rule through hcloud.",
            )["hcloud_command"]
            for rule in matched_rules[:10]
            if rule.get("rule_name")
        ]
        if delete_auto_notification_rule and notification_rule_exists:
            delete_commands.append(
                _preview(
                    "DeleteActionRule",
                    region,
                    [("1", auto_notification_rule)],
                    "R0",
                    "Preview only. Add confirm=true to delete the auto-created notification action rule through hcloud.",
                )["hcloud_command"]
            )
        return {
            "success": True,
            "action": "cleanup_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "risk": "R0",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "alarm_template_id": cloud_template.get("template_id"),
            "alarm_template_name": cloud_template.get("template_name"),
            "alarm_template_version": cloud_template.get("template_version"),
            "alarm_template_source": "cloud",
            "template_count": len(candidates),
            "matched_count": len(matched_rules),
            "matched_rules": [
                {"rule_name": rule.get("rule_name"), "kind": rule.get("rule_type"), "rule_id": rule.get("rule_id")}
                for rule in matched_rules
            ],
            "delete_auto_notification_rule": delete_auto_notification_rule,
            "auto_notification_rule": auto_notification_rule if notification_rule_exists else None,
            "hcloud_command_samples": delete_commands,
            "notes": [
                "This is an R0 destructive operation and requires confirm=true.",
                "Only rules matching the cloud-side CCE alarm template and target cluster are selected.",
                "Set delete_auto_notification_rule=true to also delete auto-cluster-{cluster_id} when it exists.",
            ],
        }

    deleted = []
    failed = []
    for rule in matched_rules:
        rule_name = rule.get("rule_name")
        if not rule_name:
            failed.append({"rule": rule, "reason": "missing rule_name"})
            continue
        result = delete_aom_alarm_rule(region, rule_name, confirm=True, ak=ak, sk=sk, project_id=project_id)
        entry = {"rule_name": rule_name, "kind": rule.get("rule_type"), "rule_id": rule.get("rule_id"), "result": result}
        if result.get("success"):
            deleted.append(entry)
        else:
            failed.append(entry)

    notification_action_rule = None
    if delete_auto_notification_rule and notification_rule_exists:
        result = delete_aom_action_rule(region, auto_notification_rule, confirm=True, ak=ak, sk=sk, project_id=project_id)
        notification_action_rule = {
            "rule_name": auto_notification_rule,
            "deleted": result.get("success", False),
            "result": result,
        }
        if not result.get("success"):
            failed.append({"rule_name": auto_notification_rule, "kind": "notification_action_rule", "result": result})

    return {
        "success": not failed,
        "action": "cleanup_cce_aom_alarm_rules",
        "region": region,
        "cluster_id": cluster_id,
        "risk": "R0",
        "executed": True,
        "alarm_template_id": cloud_template.get("template_id"),
        "alarm_template_name": cloud_template.get("template_name"),
        "alarm_template_version": cloud_template.get("template_version"),
        "alarm_template_source": "cloud",
        "template_count": len(candidates),
        "matched_count": len(matched_rules),
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed,
        "delete_auto_notification_rule": delete_auto_notification_rule,
        "notification_action_rule": notification_action_rule,
    }


def update_aom_alarm_rule(
    region: str,
    rule_name: str,
    updates: Dict[str, Any],
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = _build_metric_alarm_params(
        rule_name=rule_name,
        metric_name=updates.get("metric_name", ""),
        namespace=updates.get("namespace", ""),
        comparison_operator=updates.get("comparison_operator", ">"),
        threshold=str(updates.get("threshold", "")),
        period=int(updates.get("period", 60) or 60),
        evaluation_periods=int(updates.get("evaluation_periods", 1) or 1),
        statistic=updates.get("statistic", "average"),
        alarm_level=int(updates.get("alarm_level", 2) or 2),
        create_fields=updates,
        action_id="update-alarm-action",
    )
    if not confirm:
        preview = _preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "HIGH", "Preview only. Add confirm=true to update the AOM alarm rule through hcloud.")
        preview["rule_payload"] = dict(params)
        return preview

    result = run_hcloud("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "update_aom_alarm_rule", "executed": result["success"]})
    return result


def delete_aom_alarm_rule(
    region: str,
    rule_name: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = [("alarm_rules.1", rule_name)]
    if not confirm:
        return _preview("DeleteMetricOrEventAlarmRule", region, params, "HIGH", "Preview only. Add confirm=true to delete the AOM alarm rule through hcloud.")
    result = run_hcloud("AOM", "DeleteMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "delete_aom_alarm_rule", "executed": result["success"]})
    return result


def _find_rule_by_id(region: str, rule_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Optional[Dict[str, Any]]:
    result = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0)
    for item in result.get("rules", []):
        raw = item.get("raw", {})
        if str(item.get("rule_id")) == str(rule_id):
            return raw
    return None


def _set_alarm_rule_enabled(region: str, rule_id: str, enabled: bool, confirm: bool, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    if not confirm:
        action = "enable" if enabled else "disable"
        return {
            "success": True,
            "action": f"{action}_aom_alarm_rule",
            "region": region,
            "rule_id": rule_id,
            "risk": "HIGH" if not enabled else "MEDIUM",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "message": f"Preview only. Add confirm=true to {action} the AOM alarm rule through hcloud.",
        }

    rule = _find_rule_by_id(region, rule_id, ak, sk, project_id)
    if not rule:
        return {"success": False, "error": f"Alarm rule not found by rule_id={rule_id}"}
    resolved_project_id = resolve_project_id_for_region(region, ak, sk, project_id)
    if not resolved_project_id:
        return {
            "success": False,
            "error": "Project ID not found. Please configure the hcloud profile project or provide project_id.",
            "action": "enable_aom_alarm_rule" if enabled else "disable_aom_alarm_rule",
            "executed": False,
        }

    body = {
        "alarm_rule_name": rule.get("alarm_rule_name"),
        "alarm_rule_type": rule.get("alarm_rule_type"),
        "alarm_rule_enable": enabled,
        "alarm_rule_description": rule.get("alarm_rule_description"),
        "prom_instance_id": rule.get("prom_instance_id"),
        "event_alarm_spec": rule.get("event_alarm_spec"),
        "metric_alarm_spec": rule.get("metric_alarm_spec"),
        "alarm_notifications": rule.get("alarm_notifications"),
    }
    body = {k: v for k, v in body.items() if v is not None}
    payload = {
        "query": {"action_id": "update-alarm-action"},
        "body": body,
        "path": {"project_id": resolved_project_id},
    }
    ep_id = rule.get("enterprise_project_id")
    if ep_id:
        payload["header"] = {"Enterprise-Project-Id": ep_id}

    result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
    result.update({"action": "enable_aom_alarm_rule" if enabled else "disable_aom_alarm_rule", "executed": result["success"]})
    return result


def disable_aom_alarm_rule(region: str, rule_id: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    return _set_alarm_rule_enabled(region, rule_id, False, confirm, ak, sk, project_id)


def enable_aom_alarm_rule(region: str, rule_id: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    return _set_alarm_rule_enabled(region, rule_id, True, confirm, ak, sk, project_id)


def list_aom_action_rules(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, enterprise_project_id: Optional[str] = None) -> Dict[str, Any]:
    del enterprise_project_id
    result = run_hcloud("AOM", "ListActionRule", region, [], ak, sk, project_id)
    if not result["success"]:
        return result
    rules = extract_items(result.get("data"), "action_rules", "rules")
    return {"success": True, "region": region, "action": "list_aom_action_rules", "count": len(rules), "rules": rules, "raw": result.get("data"), "hcloud_command": result["command"]}


def delete_aom_action_rule(region: str, rule_name: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    params = [("1", rule_name)]
    if not confirm:
        return _preview("DeleteActionRule", region, params, "HIGH", "Preview only. Add confirm=true to delete the AOM action rule through hcloud.")
    result = run_hcloud("AOM", "DeleteActionRule", region, params, ak, sk, project_id)
    result.update({"action": "delete_aom_action_rule", "executed": result["success"]})
    return result


def list_aom_mute_rules(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    result = run_hcloud("AOM", "ListMuteRule", region, [], ak, sk, project_id)
    if not result["success"]:
        return result
    rules = extract_items(result.get("data"), "mute_rules", "rules")
    return {"success": True, "region": region, "action": "list_aom_mute_rules", "count": len(rules), "rules": rules, "raw": result.get("data"), "hcloud_command": result["command"]}


def list_aom_current_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    event_type: str = "active_alert",
    event_severity: str = None,
    time_range: str = None,
    limit: int = 100,
    cluster_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: List[tuple[str, Any]] = [
        ("time_range", time_range or "-1.-1.1440"),
        ("type", event_type),
        ("limit", limit),
    ]
    result = run_hcloud("AOM", "ListEvents", region, params, ak, sk, project_id)
    if not result["success"]:
        return result

    raw_events = extract_items(result.get("data"), "events", "event_info", "alarms")
    events = [_normalize_event(item, event_type) for item in raw_events]
    events = _filter_events_by_cluster(events, cluster_id=cluster_id)
    if event_severity:
        events = [event for event in events if str(event.get("event_severity")).lower() == event_severity.lower()]

    firing_count = sum(1 for event in events if event.get("status") == "firing")
    resolved_count = sum(1 for event in events if event.get("status") == "resolved")
    severity_stats: Dict[str, int] = {}
    for event in events:
        sev = event.get("event_severity", "Unknown")
        severity_stats[sev] = severity_stats.get(sev, 0) + 1

    return {
        "success": True,
        "region": region,
        "api": "hcloud AOM ListEvents",
        "query_type": event_type,
        "cluster_id": cluster_id,
        "time_range": time_range or "-1.-1.1440",
        "total_count": len(events),
        "firing_count": firing_count,
        "resolved_count": resolved_count,
        "severity_stats": severity_stats,
        "events": events,
        "raw": result.get("data"),
        "hcloud_command": result["command"],
    }


def list_aom_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    hours: int = 1,
    event_severity: Optional[str] = None,
    cluster_id: Optional[str] = None,
    cluster_name: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    time_range_str = f"-1.-1.{hours * 60}"
    tz8 = timezone(timedelta(hours=8))

    active_result = list_aom_current_alarms(region, ak, sk, project_id, "active_alert", event_severity, time_range_str, limit, cluster_id)
    if not active_result.get("success"):
        return active_result
    history_result = list_aom_current_alarms(region, ak, sk, project_id, "history_alert", event_severity, time_range_str, limit, cluster_id)
    if not history_result.get("success"):
        return history_result

    seen_sns = set()
    all_events = []
    for event in active_result.get("events", []) + history_result.get("events", []):
        sn = event.get("event_sn") or json.dumps(event.get("raw", {}), sort_keys=True, ensure_ascii=False)
        if sn in seen_sns:
            continue
        seen_sns.add(sn)
        all_events.append(event)

    all_events = _filter_events_by_cluster(all_events, cluster_id=cluster_id, cluster_name=cluster_name)
    firing_count = sum(1 for event in all_events if event.get("status") == "firing")
    resolved_count = sum(1 for event in all_events if event.get("status") == "resolved")

    type_stats: Dict[str, Dict[str, int]] = {}
    severity_stats: Dict[str, int] = {}
    for event in all_events:
        name = event.get("event_name", "Unknown")
        type_stats.setdefault(name, {"count": 0, "firing": 0, "resolved": 0})
        type_stats[name]["count"] += 1
        if event.get("status") == "firing":
            type_stats[name]["firing"] += 1
        else:
            type_stats[name]["resolved"] += 1
        sev = event.get("event_severity", "Unknown")
        severity_stats[sev] = severity_stats.get(sev, 0) + 1

    lines = [
        f"告警查询报告 (近 {hours} 小时, active + history via hcloud)",
        f"活跃告警: {firing_count} 条 | 已恢复: {resolved_count} 条 | 合并去重后: {len(all_events)} 条",
        "",
    ]
    if type_stats:
        lines.append("按类型统计:")
        for name, stats in sorted(type_stats.items(), key=lambda item: item[1]["count"], reverse=True):
            lines.append(f"  {name}: {stats['count']}条 (触发中{stats['firing']} / 已恢复{stats['resolved']})")

    resource_alarms = [event for event in all_events if any(
        kw in (event.get("event_name", "") + " " + event.get("message", ""))
        for kw in ["CPU", "cpu", "Memory", "memory", "内存", "磁盘", "Disk", "OOM", "oom", "Pressure", "pressure"]
    )]
    if resource_alarms:
        lines.append("")
        lines.append(f"资源相关告警 ({len(resource_alarms)} 条):")
        for event in sorted(resource_alarms, key=lambda item: item.get("starts_at") or 0, reverse=True)[:10]:
            ts = datetime.fromtimestamp(event["starts_at"] / 1000, tz=tz8).strftime("%H:%M:%S") if event.get("starts_at") else "?"
            lines.append(f"  [{ts}] {event.get('event_name', '')} {event.get('status', '')}")

    return {
        "success": True,
        "region": region,
        "action": "list_aom_alarms",
        "hours": hours,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "total_count": len(all_events),
        "firing_count": firing_count,
        "resolved_count": resolved_count,
        "active_count": len(active_result.get("events", [])),
        "history_count": len(history_result.get("events", [])),
        "type_stats": type_stats,
        "severity_stats": severity_stats,
        "events": all_events,
        "report": "\n".join(lines),
        "message": f"查询完成: {len(all_events)}条告警(活跃{firing_count}+已恢复{resolved_count}), {len(type_stats)}种类型",
    }


def analyze_aom_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    cluster_name: Optional[str] = None,
    hours: int = 1,
    chronic_threshold: int = 5,
    sudden_window_minutes: int = 10,
) -> Dict[str, Any]:
    result = list_aom_alarms(region, ak, sk, project_id, hours, None, cluster_id, cluster_name)
    if not result.get("success"):
        return {"success": False, "error": f"获取告警失败: {result.get('error', '')}", "raw": result}

    all_alarms = result.get("events", [])
    if not all_alarms:
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "total_alarms": 0,
            "sudden_alarms": [],
            "attention_alarms": [],
            "chronic_alarms": [],
            "summary": {"total": 0, "sudden": 0, "attention": 0, "chronic": 0},
            "message": f"近{hours}小时无告警（active + history 均无）",
        }

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    sudden_window_ms = sudden_window_minutes * 60 * 1000
    chronic_patterns = ["NotTriggerScaleUp", "未触发节点扩容", "FailedScheduling", "调度失败", "Unhealthy", "不健康", "NodeNotReady", "节点未就绪"]
    resource_keywords = ["CPU", "cpu", "Memory", "memory", "内存", "磁盘", "Disk", "disk", "OOM", "oom", "Evicted", "evicted", "CrashLoopBackOff", "Pressure", "pressure"]

    groups: Dict[str, Dict[str, Any]] = {}
    for alarm in all_alarms:
        event_name = alarm.get("event_name", "Unknown")
        namespace = alarm.get("namespace", "")
        pod_name = alarm.get("pod_name", "")
        resource_id = alarm.get("resource_id", "")
        if pod_name:
            base_pod = re.sub(r"-[a-z0-9]{5,10}$", "", pod_name)
            resource_key = f"{namespace}/{base_pod}"
        else:
            resource_key = resource_id[:80]
        group_key = f"{event_name}||{resource_key}"
        group = groups.setdefault(group_key, {
            "event_name": event_name,
            "resource_key": resource_key,
            "namespace": namespace,
            "pods": set(),
            "count": 0,
            "first_seen_ms": now_ms,
            "last_seen_ms": 0,
            "severity": alarm.get("event_severity", "Major"),
            "messages": set(),
        })
        group["count"] += 1
        if pod_name:
            group["pods"].add(pod_name)
        starts = alarm.get("starts_at") or 0
        if starts and starts < group["first_seen_ms"]:
            group["first_seen_ms"] = starts
        if starts and starts > group["last_seen_ms"]:
            group["last_seen_ms"] = starts
        if alarm.get("message"):
            group["messages"].add(alarm["message"][:200])

    sudden_alarms: List[Dict[str, Any]] = []
    attention_alarms: List[Dict[str, Any]] = []
    chronic_alarms: List[Dict[str, Any]] = []

    for group in groups.values():
        event_name = group["event_name"]
        count = group["count"]
        is_recent = (now_ms - group["first_seen_ms"]) < sudden_window_ms if group["first_seen_ms"] else False
        is_chronic_pattern = any(pattern in event_name for pattern in chronic_patterns)
        has_resource_keyword = any(kw in event_name or any(kw in msg for msg in group["messages"]) for kw in resource_keywords)

        if is_chronic_pattern and count >= chronic_threshold and not has_resource_keyword:
            priority, label, reason = "chronic", "常态", f"已知常态模式在{hours}h内重复{count}次"
        elif is_recent and count <= 3:
            priority, label, reason = "sudden", "突发", f"近{sudden_window_minutes}分钟内首次出现，当前{count}次"
        elif has_resource_keyword and count <= chronic_threshold:
            priority, label, reason = "sudden", "突发", f"涉及资源指标且出现次数较少({count}次)"
        elif has_resource_keyword:
            priority, label, reason = "attention", "关注", f"涉及资源指标，重复{count}次需关注"
        elif count >= chronic_threshold or is_chronic_pattern:
            priority, label, reason = "chronic", "常态", f"重复{count}次或命中常态模式"
        else:
            priority, label, reason = "attention", "关注", f"出现{count}次，需要关注"

        entry = {
            "priority": priority,
            "priority_label": label,
            "event_name": event_name,
            "namespace": group["namespace"],
            "pods": sorted(group["pods"]),
            "pod_count": len(group["pods"]),
            "alarm_count": count,
            "severity": group["severity"],
            "first_seen": datetime.fromtimestamp(group["first_seen_ms"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if group["first_seen_ms"] else "-",
            "last_seen": datetime.fromtimestamp(group["last_seen_ms"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if group["last_seen_ms"] else "-",
            "sample_message": next(iter(group["messages"]), "-"),
            "reason": reason,
        }
        if priority == "sudden":
            sudden_alarms.append(entry)
        elif priority == "attention":
            attention_alarms.append(entry)
        else:
            chronic_alarms.append(entry)

    sudden_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    attention_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    chronic_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    total = len(all_alarms)
    summary = {
        "total_raw_alarms": total,
        "unique_alarm_groups": len(groups),
        "sudden_count": len(sudden_alarms),
        "attention_count": len(attention_alarms),
        "chronic_count": len(chronic_alarms),
        "noise_reduction_pct": round(sum(item["alarm_count"] for item in chronic_alarms) / total * 100, 1) if total else 0,
    }

    report = "\n".join([
        f"告警过滤分析报告 (近 {hours} 小时, via hcloud)",
        f"原始告警: {total} 条 -> 去重后: {len(groups)} 组",
        f"突发: {len(sudden_alarms)} | 关注: {len(attention_alarms)} | 常态: {len(chronic_alarms)}",
        f"噪音削减: {summary['noise_reduction_pct']}%",
    ])
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "hours": hours,
        "chronic_threshold": chronic_threshold,
        "sudden_window_minutes": sudden_window_minutes,
        "summary": summary,
        "sudden_alarms": sudden_alarms,
        "attention_alarms": attention_alarms,
        "chronic_alarms": chronic_alarms,
        "report": report,
        "message": f"告警过滤完成: {total}条原始告警 -> {summary['sudden_count']}突发 + {summary['attention_count']}关注 + {summary['chronic_count']}常态",
    }
