"""
Query Kubernetes events from LTS log streams.

This module implements huawei_query_k8s_events_from_lts tool which:
1. Reads Event-to-LTS LogConfig resources through kubectl-cce
2. Queries LTS for K8s events in the specified time range
3. Parses and returns structured event data
"""

import json
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

try:
    from . import cce_app_logs, lts as lts_mod
    _lts_available = True
except ImportError:
    _lts_available = False
    cce_app_logs = None
    lts_mod = None


def _convert_timestamp_to_ms(time_str: str) -> int:
    """Convert a UTC 'YYYY-MM-DD HH:MM:SS' timestamp to milliseconds."""
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _parse_event_content(log_content: str) -> Optional[Dict[str, Any]]:
    """
    Parse K8s event from LTS log content.

    Supports two formats:
    - Format A: lowercase keys (standard K8s event format)
    - Format B: uppercase keys (Huawei CCE event format)

    Returns normalized dict with lowercase keys, or None if parsing fails.
    """
    try:
        data = json.loads(log_content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    normalized = {}

    # Handle both lowercase and uppercase key formats
    key_mapping = {
        'reason': 'reason',
        'message': 'message',
        'type': 'type',
        'count': 'count',
        'firsttimestamp': 'first_timestamp',
        'lasttimestamp': 'last_timestamp',
        'involvedobject': 'involved_object',
    }

    # Uppercase format mapping
    uppercase_mapping = {
        'Reason': 'reason',
        'Message': 'message',
        'Type': 'type',
        'Count': 'count',
        'FirstTimestamp': 'first_timestamp',
        'LastTimestamp': 'last_timestamp',
        'InvolvedObject': 'involved_object',
    }

    # Determine which format we're dealing with.
    if 'reason' in data:
        # Format A (lowercase)
        for k, v in data.items():
            if k in key_mapping:
                normalized[key_mapping[k]] = v
            else:
                normalized[k] = v
    elif 'Reason' in data:
        # Format B (uppercase) - convert to lowercase
        for k, v in data.items():
            mapped_key = uppercase_mapping.get(k, k.lower())
            normalized[mapped_key] = v
    else:
        # Unknown format, just lowercase everything
        for k, v in data.items():
            normalized[k.lower()] = v

    # Cloud Native Log Collection writes Event records with this compact schema:
    # `name` is the Kubernetes Event reason and `reason` contains the message.
    if data.get("resource_kind") and data.get("name"):
        if not normalized.get("message") and data.get("reason"):
            normalized["message"] = data["reason"]
        normalized["reason"] = data["name"]
    elif not normalized.get("reason") and data.get("name"):
        normalized["reason"] = data["name"]
    if not normalized.get("first_timestamp") and data.get("start_time"):
        normalized["first_timestamp"] = data["start_time"]
        normalized["last_timestamp"] = data["start_time"]
    if not normalized.get("involved_object") and (data.get("resource_kind") or data.get("resource_name")):
        normalized["involved_object"] = {
            "kind": data.get("resource_kind"),
            "name": data.get("resource_name"),
        }
    try:
        if int(normalized.get("count", 1)) <= 0:
            normalized["count"] = 1
    except (TypeError, ValueError):
        normalized["count"] = 1

    for field in ("type", "reason", "message"):
        if isinstance(normalized.get(field), str):
            normalized[field] = re.sub(r"<[^>]+>", "", normalized[field])

    return normalized


def _normalize_involved_object(obj: Any) -> Optional[Dict[str, Any]]:
    """Normalize involvedObject field to consistent format."""
    if not obj:
        return None

    if isinstance(obj, dict):
        result = {}
        # Handle both formats
        for k, v in obj.items():
            key_lower = k.lower()
            if key_lower in ('kind', 'name', 'namespace'):
                result[key_lower] = v
        return result if result else None

    return None


def _query_k8s_events_from_lts(
    region: str,
    cluster_id: str,
    start_time: str,
    end_time: str,
    keywords: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 500,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query K8s events from LTS based on LogConfig settings.

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        start_time: Start time 'YYYY-MM-DD HH:MM:SS'
        end_time: End time 'YYYY-MM-DD HH:MM:SS'
        keywords: Optional keywords to filter events
        event_type: Optional Event type (`Warning`, `Normal`, or `all`) to filter server-side
        limit: Maximum number of events to return (default 500)
        ak: Access key (optional, uses env if not provided)
        sk: Secret key (optional, uses env if not provided)
        project_id: Project ID (optional)

    Returns:
        Dict with success status, events, and metadata
    """
    if not _lts_available:
        return {
            "success": False,
            "error": "LTS query module is not available."
        }

    effective_event_type = event_type or "Warning"
    if effective_event_type not in {"Warning", "Normal", "all"}:
        return {"success": False, "error": "event_type must be Warning, Normal, or all"}
    if effective_event_type != "all":
        if keywords and keywords != effective_event_type:
            return {
                "success": False,
                "error": "LTS supports one server-side keyword filter; use event_type=all before providing keywords",
            }
        keywords = effective_event_type

    # Step 1: Read LogConfig CRs through kubectl-cce and find the Event-to-LTS rule.
    logconfigs_result = cce_app_logs.get_cce_logconfigs_action({
        "region": region,
        "cluster_id": cluster_id,
        "ak": ak,
        "sk": sk,
        "project_id": project_id,
    })
    if not logconfigs_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to get LogConfigs: {logconfigs_result.get('error', 'Unknown error')}",
        }
    event_config = next(
        (
            config for config in logconfigs_result.get("logconfigs") or []
            if config.get("name") == "default-event"
            and config.get("input_type") == "event"
            and config.get("output_type") == "LTS"
        ),
        None,
    )
    if not event_config:
        return {
            "success": False,
            "error": "No default-event LogConfig with LTS output was found in the cluster.",
            "checked_logconfigs": logconfigs_result.get("count", 0),
        }
    lts_config = (event_config.get("spec") or {}).get("outputDetail", {}).get("LTS", {})
    log_group_id = lts_config.get("ltsGroupID")
    log_stream_id = lts_config.get("ltsStreamID")
    if not log_group_id or not log_stream_id:
        return {
            "success": False,
            "error": "The default-event LogConfig does not contain LTS group and stream IDs.",
        }

    # Step 4: Convert time to milliseconds
    try:
        start_ms = _convert_timestamp_to_ms(start_time)
        end_ms = _convert_timestamp_to_ms(end_time)
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid UTC time format; expected 'YYYY-MM-DD HH:MM:SS': {e}",
        }

    # Step 5: Query LTS with pagination
    all_events = []
    scroll_id = None
    total_fetched = 0
    page_count = 0
    page_limit = 1000  # LTS API page size
    page_request_delay_seconds = 0.1

    while total_fetched < limit:
        page_count += 1
        page_remaining = limit - total_fetched
        current_page_limit = min(page_limit, page_remaining)

        lts_result = lts_mod.query_logs(
            region=region,
            log_group_id=log_group_id,
            log_stream_id=log_stream_id,
            start_time=str(start_ms),
            end_time=str(end_ms),
            keywords=keywords,
            limit=current_page_limit,
            scroll_id=scroll_id,
            ak=ak,
            sk=sk,
            project_id=project_id
        )

        if not lts_result.get("success"):
            return {
                "success": False,
                "error": f"LTS query failed: {lts_result.get('error', 'Unknown error')}",
                "log_group_id": log_group_id,
                "log_stream_id": log_stream_id,
                "events_fetched": total_fetched,
                "pages_fetched": page_count - 1
            }

        # Step 6: Parse events from logs
        raw_logs = lts_result.get("logs", [])
        for log in raw_logs:
            content = log.get("content", "")
            if not content:
                continue

            parsed = _parse_event_content(content)
            if not parsed:
                continue

            # Normalize involved object
            involved_obj = parsed.get("involved_object")
            if involved_obj:
                parsed["involved_object"] = _normalize_involved_object(involved_obj)

            all_events.append(parsed)
            total_fetched += 1

            if total_fetched >= limit:
                break

        # Check for next page
        scroll_id = lts_result.get("scroll_id")
        if not scroll_id:
            break
        if total_fetched < limit:
            time.sleep(page_request_delay_seconds)

    # Step 7: Build response
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "keywords": keywords,
        "event_type": effective_event_type,
        "event_count": len(all_events),
        "events": all_events,
        "time_range": {
            "start": start_time,
            "end": end_time
        },
        "log_config": {
            "name": event_config.get("name"),
            "namespace": event_config.get("namespace"),
            "input_type": "event",
            "discovery_method": "kubectl_cce_logconfig",
            "access_method": logconfigs_result.get("access_method"),
        },
        "pagination": {
            "pages_fetched": page_count,
            "limit": limit,
            "has_more": scroll_id is not None and total_fetched >= limit
        }
    }


def query_k8s_events_from_lts_action(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Action handler for huawei_query_k8s_events_from_lts tool.

    Expected parameters:
    - region: Huawei Cloud region (required)
    - cluster_id: CCE cluster ID (required)
    - start_time: Start time 'YYYY-MM-DD HH:MM:SS' (required)
    - end_time: End time 'YYYY-MM-DD HH:MM:SS' (required)
    - keywords: Optional keywords to filter events
    - event_type: Optional Event type (`Warning`, `Normal`, or `all`) for server-side filtering
    - limit: Maximum number of events to return (default 500)
    """
    region = params.get("region")
    cluster_id = params.get("cluster_id")
    start_time = params.get("start_time")
    end_time = params.get("end_time")
    keywords = params.get("keywords")
    event_type = params.get("event_type")

    # Validate required parameters
    if not region:
        return {"success": False, "error": "region is required"}
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not start_time:
        return {"success": False, "error": "start_time is required"}
    if not end_time:
        return {"success": False, "error": "end_time is required"}

    # Parse limit parameter
    try:
        limit = int(params.get("limit", 500))
    except (ValueError, TypeError):
        limit = 500

    return _query_k8s_events_from_lts(
        region=region,
        cluster_id=cluster_id,
        start_time=start_time,
        end_time=end_time,
        keywords=keywords,
        event_type=event_type,
        limit=limit,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id")
    )
