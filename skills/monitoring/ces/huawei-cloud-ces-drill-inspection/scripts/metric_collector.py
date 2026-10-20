#!/usr/bin/env python3
"""Monitoring metric collection: CES ShowMetricData calls driven by metrics.json."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from hcloud_executor import parallel_execute

logger = logging.getLogger(__name__)
def build_metric_lookup(metrics_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build display name → metadata lookup table.

    metrics.json structure: {"ecs": {"ECS CPU使用率": {metric_name, namespace, ...}, ...}, ...}
    Returns: {"ecs": {"ECS CPU使用率": {metadata}, ...}, "rds": {...}, "dcs": {...}}

    Users reference metrics by display name in config; this function maps display names to metadata.
    """
    lookup = {}
    for svc_key, metrics_dict in metrics_data.items():
        lookup[svc_key] = {}
        for display_name, meta in metrics_dict.items():
            metric_name = meta.get("metric_name", "")
            if metric_name:
                lookup[svc_key][display_name] = {
                    "display_name": display_name,
                    "metric_name": metric_name,
                    "namespace": meta.get("namespace", ""),
                    "dimensions": meta.get("dimensions", []),
                    "unit": meta.get("unit", ""),
                    "ceiling": meta.get("ceiling"),
                }
    return lookup


def build_dim_args(dimensions: list[dict], instance: dict[str, Any]) -> list[str]:
    """Build CES --dim.N args from metrics.json dimension definitions and instance info.

    dimensions: [{"name": "instance_id", "source": "instance_id"}, ...]
    instance: contains instance_id, dim_resource_id, etc.
    """
    dim_args = []
    for i, dim in enumerate(dimensions):
        dim_name = dim["name"]
        source_field = dim.get("source", "instance_id")
        dim_value = instance.get(source_field, instance.get("instance_id", ""))
        dim_args.append(f"--dim.{i}={dim_name},{dim_value}")
    return dim_args


def collect_metrics_for_instance(
    instance: dict[str, Any],
    metric_names: list[str],
    metric_lookup: dict[str, dict[str, Any]],
    start: str,
    end: str,
    period: int = 60,
    max_workers: int = 8,
    hcloud_cmd: str = "hcloud",
    timeout: int = 60,
    service_metric_key_map: dict[str, str] | None = None,
    timezone_offset: int = 8,
) -> dict[str, Any]:
    """Collect all configured metrics for a single instance.

    metric_names: display name list (e.g. ["ECS CPU使用率", "ECS入方向带宽"])
    metric_lookup: output of build_metric_lookup(), indexed by display name

    Returns:
    {
        "instance_id": "...",
        "metrics": {
            "ECS CPU使用率": {"display_name": ..., "unit": ..., "datapoints": [...], "error": None},
            ...
        }
    }
    """
    service = instance["service"]
    if service_metric_key_map is None:
        raise ValueError("service_metric_key_map not configured, please specify in runtime.service_metric_key_map")
    svc_key = service_metric_key_map.get(service, service)
    svc_lookup = metric_lookup.get(svc_key, {})

    # CES API requires --from/--to (millisecond UNIX timestamps)
    # start/end are local-time strings (e.g. "2026-10-16 09:30:00" in UTC+8);
    # parse with the configured timezone offset, NOT UTC, to get the correct epoch timestamp.
    tz_local = timezone(timedelta(hours=timezone_offset))
    from_ts = str(int(datetime.strptime(start, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_local).timestamp() * 1000))
    to_ts = str(int(datetime.strptime(end, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_local).timestamp() * 1000))

    # Build parallel tasks
    tasks = []
    for display_name in metric_names:
        meta = svc_lookup.get(display_name)
        if not meta:
            logger.warning("Metric '%s' not found in metrics.json (service: %s)", display_name, svc_key)
            continue

        dim_args = build_dim_args(meta["dimensions"], instance)
        args = [
            "CES", "ShowMetricData",
            "--metric_name=" + meta["metric_name"],
            "--namespace=" + meta["namespace"],
        ] + dim_args + [
            "--period=" + str(period),
            "--filter=average",
            "--from=" + from_ts,
            "--to=" + to_ts,
        ]
        tasks.append({
            "args": args,
            "region": instance["region"],
            "key": f"{service}:{instance['instance_id']}:{display_name}",
            "display_name": display_name,
            "meta": meta,
        })

    raw_results = parallel_execute(tasks, max_workers=max_workers, hcloud_cmd=hcloud_cmd, default_timeout=timeout)

    metrics_result = {}
    for r in raw_results:
        display_name = r["display_name"]
        meta = r["meta"]
        data = r["result"]

        if "_error" in data:
            metrics_result[display_name] = {
                "display_name": display_name,
                "unit": meta["unit"],
                "ceiling": meta["ceiling"],
                "datapoints": [],
                "error": data["_error"],
            }
            continue

        # CES ShowMetricData returns {"datapoints": [{"timestamp": ..., "average": ...}, ...]}
        datapoints = data.get("datapoints", [])
        # Convert to unified format
        points = []
        for dp in datapoints:
            ts = dp.get("timestamp", 0)
            # timestamp may be in milliseconds
            if ts > 1e12:
                ts = ts / 1000
            value = dp.get("average", dp.get("value"))
            points.append({"timestamp": ts, "value": value})

        metrics_result[display_name] = {
            "display_name": display_name,
            "unit": meta["unit"],
            "ceiling": meta["ceiling"],
            "datapoints": points,
            "error": None,
        }

    return {
        "instance_id": instance["instance_id"],
        "service": service,
        "metrics": metrics_result,
    }


def collect_all_metrics(
    instances_by_service: dict[str, list[dict[str, Any]]],
    steady_state_rules: dict[str, Any],
    metric_lookup: dict[str, dict[str, Any]],
    start: str,
    end: str,
    runtime: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Collect monitoring metrics for all normal instances.

    Abnormal instances are skipped (determined by caller), returns {"ecs": [...], "rds": [...], "redis": [...]}
    Each item: {"instance_id": ..., "service": ..., "metrics": {...}}
    """
    if runtime is None:
        runtime = {}
    period = runtime.get("ces_period", 60)
    max_workers = runtime.get("metric_max_workers", 8)
    hcloud_cmd = runtime.get("hcloud_cmd", "hcloud")
    timeout = runtime.get("hcloud_timeout", 60)
    tz_offset = runtime.get("timezone_offset", 8)
    svc_key_map = runtime.get("service_metric_key_map")
    if not svc_key_map:
        raise ValueError("service_metric_key_map not configured, please specify in runtime.service_metric_key_map")

    result = {}
    for service, instances in instances_by_service.items():
        svc_rules = steady_state_rules.get(service, {})
        metric_names = svc_rules.get("metrics", [])
        if not metric_names:
            result[service] = []
            continue

        svc_metrics = []
        for inst in instances:
            # Skip abnormal instances
            if not inst.get("_is_normal", True):
                continue
            logger.info("Collecting metrics for %s/%s", service, inst["instance_id"])
            m = collect_metrics_for_instance(
                inst, metric_names, metric_lookup, start, end,
                period, max_workers, hcloud_cmd, timeout, svc_key_map,
                timezone_offset=tz_offset,
            )
            svc_metrics.append(m)
        result[service] = svc_metrics

    return result
