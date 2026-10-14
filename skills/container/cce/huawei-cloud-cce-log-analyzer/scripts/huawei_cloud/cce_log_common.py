"""Shared parsing, classification, and pagination helpers for CCE log analysis."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import lts


DEFAULT_ERROR_PATTERNS = [
    r"\berror\b", r"\bexception\b", r"\btraceback\b", r"\bpanic\b", r"\bfatal\b",
    r"\bfailed?\b", r"\bfailure\b", r"\btimeout\b", r"\btimed out\b",
    r"\bconnection refused\b", r"\bunavailable\b", r"\boom\b", r"out of memory",
    r"segmentation fault", r"stacktrace",
]
DEFAULT_WARNING_PATTERNS = [r"\bwarn(?:ing)?\b", r"\bdeprecated\b", r"\bretry(?:ing)?\b", r"\bslow\b"]
_KUBERNETES_NAMESPACE_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_APPLICATION_LABEL_ALIASES = {
    "cluster": ("clusterId", "cluster_id", "k8s.cluster.id"),
    "namespace": ("nameSpace", "namespace", "k8s.namespace.name"),
    "app": ("appName", "app.kubernetes.io/name", "app"),
}


def _get_policy_name(params: Dict[str, str]) -> Optional[str]:
    return params.get("logconfig_name") or params.get("policy_name")

def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "y", "on"}

def _to_int(value: Optional[str], default: int) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default

def _parse_text_list(value: Optional[str], default: List[str]) -> List[str]:
    if not value:
        return default
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return default
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in text.split(",") if item.strip()]

def _parse_logconfig_namespaces(value: Optional[str]) -> List[str]:
    """Parse and validate namespace scope for all-container stdout collection."""
    namespaces = _parse_text_list(value, [])
    invalid = [namespace for namespace in namespaces if not _KUBERNETES_NAMESPACE_RE.fullmatch(namespace)]
    if invalid:
        raise ValueError(
            "namespaces must be a JSON array such as '[\"default\"]' or a comma-separated list such as 'default,kube-system'; "
            f"invalid namespace value(s): {', '.join(invalid)}"
        )
    return namespaces

def _parse_json_value(value: Optional[str], default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))

def _format_ts(timestamp_ms: Optional[int]) -> Optional[str]:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

def _recent_lts_window(hours: int) -> Tuple[str, str]:
    """Return a UTC time range compatible with the LTS timestamp parser."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    return (
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time.strftime("%Y-%m-%d %H:%M:%S"),
    )

def _content_of(log: Dict[str, Any]) -> str:
    content = log.get("content")
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    if content is None:
        return ""
    return str(content)

def _json_content_of(log: Dict[str, Any]) -> Dict[str, Any]:
    content = log.get("content")
    if isinstance(content, dict):
        return content
    if not content:
        return {}
    text = str(content).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for nested_key in ("log", "message", "content"):
                nested = parsed.get(nested_key)
                if isinstance(nested, str) and nested.strip().startswith("{"):
                    try:
                        nested_parsed = json.loads(nested)
                        if isinstance(nested_parsed, dict):
                            merged = dict(parsed)
                            merged.update(nested_parsed)
                            return merged
                    except json.JSONDecodeError:
                        pass
            return parsed
        return {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\})", text)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}

def _deep_get(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current

def _extract_log_time_ms(log: Dict[str, Any]) -> Optional[int]:
    timestamp = log.get("timestamp")
    if timestamp not in (None, ""):
        try:
            value = int(timestamp)
            if value < 10_000_000_000:
                value *= 1000
            return value
        except (TypeError, ValueError):
            pass

    content = _content_of(log)
    nginx_match = re.search(r"\[(\d{1,2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]", content)
    if nginx_match:
        try:
            parsed = datetime.strptime(nginx_match.group(1), "%d/%b/%Y:%H:%M:%S %z")
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass

    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b", content)
    if iso_match:
        try:
            parsed = datetime.strptime(iso_match.group(1).replace("T", " "), "%Y-%m-%d %H:%M:%S")
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass

    epoch_match = re.search(r"\b(1[6-9]\d{8}(?:\d{3})?)\b", content)
    if epoch_match:
        value = int(epoch_match.group(1))
        if value < 10_000_000_000:
            value *= 1000
        return value
    return None

def _extract_audit_time_ms(log: Dict[str, Any], audit: Dict[str, Any]) -> Optional[int]:
    for path in ("stageTimestamp", "requestReceivedTimestamp", "timestamp", "time"):
        value = _deep_get(audit, path)
        if not value:
            continue
        if isinstance(value, (int, float)):
            numeric = int(value)
            return numeric * 1000 if numeric < 10_000_000_000 else numeric
        text = str(value).replace("T", " ").replace("Z", "").split(".")[0]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z"):
            try:
                return int(datetime.strptime(text, fmt).timestamp() * 1000)
            except ValueError:
                continue
    return _extract_log_time_ms(log)

def _extract_http_status(content: str) -> Optional[int]:
    match = re.search(r'"\S+\s+\S+\s+HTTP/[^"]+"\s+(\d{3})\b', content)
    if not match:
        match = re.search(r"\bstatus(?:=|:|\s)(\d{3})\b", content, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None

def _classify_log(
    content: str,
    error_patterns: List[str],
    warning_patterns: List[str],
    http_error_status_threshold: int,
    include_http_4xx: bool,
) -> Tuple[bool, str, List[str], Optional[int]]:
    reasons = []
    lower_content = content.lower()
    severity = "normal"

    for pattern in error_patterns:
        try:
            if re.search(pattern, content, flags=re.IGNORECASE):
                reasons.append(pattern)
        except re.error:
            if pattern.lower() in lower_content:
                reasons.append(pattern)

    warning_reasons = []
    for pattern in warning_patterns:
        try:
            if re.search(pattern, content, flags=re.IGNORECASE):
                warning_reasons.append(pattern)
        except re.error:
            if pattern.lower() in lower_content:
                warning_reasons.append(pattern)

    status_code = _extract_http_status(content)
    if status_code is not None:
        if status_code >= http_error_status_threshold:
            reasons.append(f"http_{status_code}")
        elif include_http_4xx and status_code >= 400:
            warning_reasons.append(f"http_{status_code}")

    if reasons:
        if re.search(r"\b(fatal|panic|oom|out of memory|segmentation fault|traceback)\b", content, flags=re.IGNORECASE):
            severity = "critical"
        else:
            severity = "error"
        return True, severity, reasons, status_code
    if warning_reasons:
        return True, "warning", warning_reasons, status_code
    return False, severity, [], status_code

def _analysis_options(params: Dict[str, str]) -> Tuple[List[str], List[str], int, bool, int, int]:
    return (
        _parse_text_list(params.get("error_patterns"), DEFAULT_ERROR_PATTERNS),
        _parse_text_list(params.get("warning_patterns"), DEFAULT_WARNING_PATTERNS),
        _to_int(params.get("http_error_status_threshold"), 500),
        _to_bool(params.get("include_http_4xx"), False),
        _to_int(params.get("incident_gap_minutes"), 5),
        _to_int(params.get("sample_limit"), 20),
    )

def _new_log_lines(initial_logs: str, followup_logs: str) -> Tuple[List[str], int]:
    """Return follow-up lines that do not overlap with the initial tail sample."""
    initial_lines = initial_logs.splitlines()
    followup_lines = followup_logs.splitlines()
    for overlap in range(min(len(initial_lines), len(followup_lines)), -1, -1):
        if not overlap or initial_lines[-overlap:] == followup_lines[:overlap]:
            return followup_lines[overlap:], overlap
    return followup_lines, 0

def _build_incident_windows(anomalies: List[Dict[str, Any]], gap_minutes: int) -> List[Dict[str, Any]]:
    if not anomalies:
        return []
    gap_ms = max(gap_minutes, 1) * 60 * 1000
    sorted_items = sorted(anomalies, key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0, item["index"]))
    windows = []
    current = None
    for item in sorted_items:
        item_ts = item.get("timestamp_ms")
        if current is None:
            current = {
                "start_time": item.get("time"),
                "end_time": item.get("time"),
                "start_timestamp": item_ts,
                "end_timestamp": item_ts,
                "count": 1,
                "severities": {item["severity"]: 1},
                "reasons": {},
            }
        elif item_ts is not None and current.get("end_timestamp") is not None and item_ts - current["end_timestamp"] <= gap_ms:
            current["end_time"] = item.get("time")
            current["end_timestamp"] = item_ts
            current["count"] += 1
            current["severities"][item["severity"]] = current["severities"].get(item["severity"], 0) + 1
        elif item_ts is None and current.get("end_timestamp") is None:
            current["count"] += 1
            current["severities"][item["severity"]] = current["severities"].get(item["severity"], 0) + 1
        else:
            windows.append(current)
            current = {
                "start_time": item.get("time"),
                "end_time": item.get("time"),
                "start_timestamp": item_ts,
                "end_timestamp": item_ts,
                "count": 1,
                "severities": {item["severity"]: 1},
                "reasons": {},
            }
        for reason in item.get("reasons", []):
            current["reasons"][reason] = current["reasons"].get(reason, 0) + 1
    if current:
        windows.append(current)
    for window in windows:
        if window.get("start_timestamp") is not None and window.get("end_timestamp") is not None:
            window["duration_seconds"] = max(0, int((window["end_timestamp"] - window["start_timestamp"]) / 1000))
        else:
            window["duration_seconds"] = None
        window["top_reasons"] = sorted(window.pop("reasons").items(), key=lambda item: item[1], reverse=True)[:10]
    return windows

def _parse_labels(labels: Optional[str]) -> Optional[Dict[str, str]]:
    if not labels:
        return None
    if isinstance(labels, dict):
        return labels
    return json.loads(labels)

def _query_logs_with_pagination(
    params: Dict[str, str],
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str],
    end_time: Optional[str],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    auto_paginate = _to_bool(params.get("auto_paginate"), False)
    page_limit = _to_int(params.get("limit"), 1000)
    max_pages = _to_int(params.get("max_pages"), 10 if auto_paginate else 1)
    max_pages = max(max_pages, 1)
    is_desc = _to_bool(params.get("is_desc"), True)
    is_iterative = _to_bool(params.get("is_iterative"), auto_paginate)

    all_logs = []
    page_results = []
    scroll_id = params.get("scroll_id")
    seen_scroll_ids = set()
    last_result: Dict[str, Any] = {}
    stopped_reason = "completed"

    for page_index in range(max_pages):
        page = lts.query_logs(
            region=params["region"],
            log_group_id=log_group_id,
            log_stream_id=log_stream_id,
            start_time=start_time,
            end_time=end_time,
            keywords=params.get("keywords"),
            limit=page_limit,
            scroll_id=scroll_id,
            is_desc=is_desc,
            is_iterative=is_iterative,
            labels=labels,
            ak=params.get("ak"),
            sk=params.get("sk"),
            project_id=params.get("project_id"),
            security_token=params.get("security_token"),
        )
        if not page.get("success"):
            if not all_logs:
                return page
            page["partial_logs"] = all_logs
            page["partial_total"] = len(all_logs)
            page["pages_fetched"] = len(page_results)
            return page

        page_logs = page.get("logs", [])
        all_logs.extend(page_logs)
        next_scroll_id = page.get("scroll_id")
        page_results.append(
            {
                "page": page_index + 1,
                "count": len(page_logs),
                "scroll_id": next_scroll_id,
            }
        )
        last_result = page

        if not auto_paginate:
            stopped_reason = "auto_paginate_disabled"
            break
        if not next_scroll_id:
            stopped_reason = "no_more_pages"
            break
        if next_scroll_id in seen_scroll_ids:
            stopped_reason = "repeated_scroll_id"
            break

        seen_scroll_ids.add(next_scroll_id)
        scroll_id = next_scroll_id
    else:
        stopped_reason = "max_pages_reached"

    result = dict(last_result)
    result["logs"] = all_logs
    result["total"] = len(all_logs)
    result["auto_paginate"] = auto_paginate
    result["page_limit"] = page_limit
    result["max_pages"] = max_pages
    result["pages_fetched"] = len(page_results)
    result["page_results"] = page_results
    result["stopped_reason"] = stopped_reason
    result["has_more"] = stopped_reason == "max_pages_reached" and bool(result.get("scroll_id"))
    return result
