"""kube-apiserver and kube-scheduler control-plane log query and analysis."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from . import common, lts
from .cce_log_common import (
    _analysis_options,
    _classify_log,
    _content_of,
    _extract_http_status,
    _extract_log_time_ms,
    _format_ts,
    _parse_labels,
    _query_logs_with_pagination,
    _recent_lts_window,
    _to_int,
)


def _discover_control_plane_log_stream(
    params: Dict[str, str], component: str, config_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Verify a control-plane log switch and resolve its standard LTS stream."""
    cluster_id = params["cluster_id"]
    command = common.hcloud_command(
        "CCE", "ShowClusterConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    command.append(f"--cluster_id={cluster_id}")
    config_result = common.run_hcloud(command)
    if not config_result.get("success"):
        return config_result
    config = next(
        (item for item in config_result.get("data", {}).get("log_configs", [])
         if item.get("name") in (config_names or {component})),
        None,
    )
    if not config or not config.get("enable"):
        return {
            "success": False,
            "error": f"CCE {component} log collection is not enabled",
            "note": f"Enable {component} control-plane logs in the CCE Log Center before querying or analyzing them.",
            "requires_control_plane_log": component,
        }
    group_name = f"k8s-log-{cluster_id}"
    stream_name = f"{component}-{cluster_id}"
    groups = lts.list_log_groups(params["region"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token"))
    if not groups.get("success"):
        return groups
    group = next((item for item in groups.get("log_groups", []) if item.get("log_group_name") == group_name), None)
    if not group:
        return {"success": False, "error": f"CCE {component} log group {group_name} was not found"}
    streams = lts.list_log_streams(params["region"], group["log_group_id"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token"))
    if not streams.get("success"):
        return streams
    stream = next((item for item in streams.get("log_streams", []) if item.get("log_stream_name") == stream_name), None)
    if not stream:
        return {
            "success": False,
            "error": f"CCE {component} log stream {stream_name} was not found",
            "note": f"{component} logging is enabled, but its expected LTS stream is unavailable or has not been created yet.",
        }
    return {"success": True, "log_group_id": group["log_group_id"], "log_stream_id": stream["log_stream_id"], "log_group_name": group_name, "log_stream_name": stream_name}

def _discover_kube_apiserver_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    return _discover_control_plane_log_stream(
        params, "kube-apiserver", {"kube-apiserver", "kube_apiserver", "apiserver"},
    )

def _discover_kube_scheduler_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    return _discover_control_plane_log_stream(
        params, "kube-scheduler", {"kube-scheduler", "kube_scheduler", "scheduler"},
    )

def query_kube_apiserver_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source = _discover_kube_apiserver_log_stream(params)
    if not source.get("success"):
        return source
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("start_time") and not query_params.get("end_time"):
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(_to_int(query_params.get("hours"), 1))
    labels = _parse_labels(query_params.get("labels")) or {}
    result = _query_logs_with_pagination(query_params, source["log_group_id"], source["log_stream_id"], query_params.get("start_time"), query_params.get("end_time"), labels)
    if result.get("success"):
        result.update({"cluster_id": params["cluster_id"], "component": "kube-apiserver", "log_group_name": source["log_group_name"], "log_stream_name": source["log_stream_name"], "labels": labels})
    return result

def query_kube_scheduler_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source = _discover_kube_scheduler_log_stream(params)
    if not source.get("success"):
        return source
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("start_time") and not query_params.get("end_time"):
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(_to_int(query_params.get("hours"), 1))
    labels = _parse_labels(query_params.get("labels")) or {}
    result = _query_logs_with_pagination(query_params, source["log_group_id"], source["log_stream_id"], query_params.get("start_time"), query_params.get("end_time"), labels)
    if result.get("success"):
        result.update({"cluster_id": params["cluster_id"], "component": "kube-scheduler", "log_group_name": source["log_group_name"], "log_stream_name": source["log_stream_name"], "labels": labels})
    return result

def _extract_apiserver_status(content: str) -> Optional[int]:
    match = re.search(r"\b(?:resp|status(?:_code)?)[=:]?(\d{3})\b", content, flags=re.IGNORECASE)
    return int(match.group(1)) if match else _extract_http_status(content)

def _extract_apiserver_latency_ms(content: str) -> Optional[float]:
    match = re.search(r"\b(?:latency|duration|elapsed|took)[=:]?\"?([0-9][0-9A-Za-zµ.]*)", content, flags=re.IGNORECASE)
    if not match:
        return None
    units = re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|us|µs|h|m|s)", match.group(1).lower())
    if not units:
        return None
    multipliers = {"us": 0.001, "µs": 0.001, "ms": 1, "s": 1000, "m": 60000, "h": 3600000}
    return sum(float(value) * multipliers[unit] for value, unit in units)

def _extract_apiserver_verb(content: str) -> Optional[str]:
    match = re.search(r'\bverb="([^"]+)"', content, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None

def _latency_statistics(latencies: List[float]) -> Dict[str, Any]:
    if not latencies:
        return {"samples": 0, "avg_ms": None, "p95_ms": None, "max_ms": None}
    values = sorted(latencies)
    return {
        "samples": len(values),
        "avg_ms": round(sum(values) / len(values), 3),
        "p95_ms": values[max(0, int((len(values) - 1) * 0.95))],
        "max_ms": values[-1],
    }

def _without_http_timeout_query_parameter(content: str) -> str:
    """Exclude timeout-duration metadata while preserving actual timeout failures."""
    without_query_parameter = re.sub(
        r"([?&])timeout=[^&\"\s]*", r"\1", content, flags=re.IGNORECASE
    )
    return re.sub(
        r'\btimeout="?[0-9]+(?:\.[0-9]+)?(?:h|m|s|ms|us|µs)+"?',
        "request_deadline_metadata",
        without_query_parameter,
        flags=re.IGNORECASE,
    )

def analyze_kube_apiserver_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("hours", "1")
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    result = query_kube_apiserver_logs_action(query_params)
    if not result.get("success"):
        return result
    threshold, sample_limit = float(params.get("slow_latency_ms") or 1000), _to_int(params.get("sample_limit"), 20)
    statuses: Dict[str, int] = {}
    latencies: List[float] = []
    watch_latencies: List[float] = []
    non_watch_latencies: List[float] = []
    anomalies = []
    slow_watch_count = 0
    for index, log in enumerate(result.get("logs", [])):
        content = _content_of(log)
        status = _extract_apiserver_status(content)
        latency = _extract_apiserver_latency_ms(content)
        verb = _extract_apiserver_verb(content)
        reasons = []
        if status is not None:
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            if not 200 <= status < 300:
                reasons.append(f"http_{status}")
        if latency is not None:
            latencies.append(latency)
            (watch_latencies if verb == "WATCH" else non_watch_latencies).append(latency)
            if latency >= threshold:
                reasons.append("slow_request")
                if verb == "WATCH":
                    slow_watch_count += 1
        classification_content = _without_http_timeout_query_parameter(content)
        generic, _, generic_reasons, _ = _classify_log(classification_content, *_analysis_options(params)[:4])
        if generic:
            reasons.extend(reason for reason in generic_reasons if reason not in reasons)
        if reasons:
            anomalies.append({"index": index, "time": _format_ts(_extract_log_time_ms(log)), "verb": verb, "status_code": status, "latency_ms": latency, "reasons": reasons, "content": content[:500]})
    all_latency = _latency_statistics(latencies)
    watch_latency = _latency_statistics(watch_latencies)
    non_watch_latency = _latency_statistics(non_watch_latencies)
    non_200 = sum(count for code, count in statuses.items() if code != "200")
    successful_non_200 = sum(count for code, count in statuses.items() if code != "200" and 200 <= int(code) < 300)
    non_success = sum(count for code, count in statuses.items() if not 200 <= int(code) < 300)
    return {
        "success": True, "cluster_id": result["cluster_id"], "component": "kube-apiserver",
        "log_group_name": result["log_group_name"], "log_stream_name": result["log_stream_name"],
        "analysis_window": {"start_time": result.get("start_time"), "end_time": result.get("end_time")},
        "summary": {
            "total_logs": len(result.get("logs", [])),
            "non_200_count": non_200,
            "successful_non_200_count": successful_non_200,
            "non_success_status_count": non_success,
            "slow_request_count": sum("slow_request" in item["reasons"] for item in anomalies),
            "slow_watch_count": slow_watch_count,
            "other_abnormal_count": sum(any(reason != "slow_request" and not reason.startswith("http_") for reason in item["reasons"]) for item in anomalies),
            "slow_latency_ms": threshold,
            "latency_samples": all_latency["samples"],
            "latency_avg_ms": all_latency["avg_ms"],
            "latency_p95_ms": all_latency["p95_ms"],
            "latency_max_ms": all_latency["max_ms"],
            "watch_latency": watch_latency,
            "non_watch_latency": non_watch_latency,
        },
        "status_codes": [{"status_code": code, "count": count} for code, count in sorted(statuses.items(), key=lambda item: item[1], reverse=True)],
        "anomaly_samples": anomalies[:sample_limit], "query_summary": {"pages_fetched": result.get("pages_fetched"), "stopped_reason": result.get("stopped_reason")},
    }

_SCHEDULER_ANOMALY_PATTERNS = {
    "scheduling_failure": r"\bfailed to schedule\b|\bfailedscheduling\b|\b0/\d+ nodes are available\b",
    "binding_failure": r"\bfailed to bind\b|\berror binding\b|\bfailed binding\b",
    "preemption_issue": r"\bpreemption is not helpful\b|\bno preemption victims found\b|\bpreemption.*failed\b",
    "leader_election_issue": r"\bfailed to renew lease\b|\blost lease\b|\bfailed to acquire lease\b|\bleaderelection.*error\b",
}

def analyze_kube_scheduler_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("hours", "1")
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    result = query_kube_scheduler_logs_action(query_params)
    if not result.get("success"):
        return result

    sample_limit = _to_int(params.get("sample_limit"), 20)
    counts = {name: 0 for name in _SCHEDULER_ANOMALY_PATTERNS}
    successful_assignment_count = 0
    leader_renewal_count = 0
    generic_abnormal_count = 0
    anomalies = []
    for index, log in enumerate(result.get("logs", [])):
        content = _content_of(log)
        reasons = [
            name for name, pattern in _SCHEDULER_ANOMALY_PATTERNS.items()
            if re.search(pattern, content, flags=re.IGNORECASE)
        ]
        for reason in reasons:
            counts[reason] += 1
        if re.search(r"\bsuccessfully assigned\b", content, flags=re.IGNORECASE):
            successful_assignment_count += 1
        if re.search(r"\bsuccessfully renewed lease\b", content, flags=re.IGNORECASE):
            leader_renewal_count += 1
        generic, _, generic_reasons, _ = _classify_log(content, *_analysis_options(params)[:4])
        if generic and not reasons:
            generic_abnormal_count += 1
            reasons.extend(generic_reasons)
        if reasons:
            anomalies.append({
                "index": index,
                "time": _format_ts(_extract_log_time_ms(log)),
                "reasons": reasons,
                "content": content[:500],
            })
    return {
        "success": True,
        "cluster_id": result["cluster_id"],
        "component": "kube-scheduler",
        "log_group_name": result["log_group_name"],
        "log_stream_name": result["log_stream_name"],
        "analysis_window": {"start_time": result.get("start_time"), "end_time": result.get("end_time")},
        "summary": {
            "total_logs": len(result.get("logs", [])),
            "successful_assignment_count": successful_assignment_count,
            "leader_renewal_count": leader_renewal_count,
            **counts,
            "generic_abnormal_count": generic_abnormal_count,
            "abnormal_log_count": len(anomalies),
        },
        "anomaly_samples": anomalies[:sample_limit],
        "query_summary": {"pages_fetched": result.get("pages_fetched"), "stopped_reason": result.get("stopped_reason")},
    }
