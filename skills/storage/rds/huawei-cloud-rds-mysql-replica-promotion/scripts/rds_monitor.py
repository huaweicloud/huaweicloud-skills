#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Monitor key CES metrics of Huawei Cloud RDS for MySQL instances.

Overview:
    This script pulls a snapshot of the key Cloud Eye Service (CES)
    metrics of Huawei Cloud RDS for MySQL instances through the `hcloud`
    (KooCLI) command line tool and writes a structured JSON report. It is
    a standalone companion tool of the SKILL workflow, used by the Agent
    for post-conversion business verification and routine health checks;
    it never mutates any cloud resource.

Detailed Description:
    The region's project id is resolved automatically via
    KeystoneListAuthProjects (rds_common.resolve_project_id). Instances
    are selected either singly (--instance-id), in a comma separated list
    (--instance-ids), or by listing all MySQL instances of the region
    (--all-instances). For every target instance the type field
    (Single/Ha/Replica) is read from ListInstances so the replication
    delay metric rds073_replication_delay is only queried for Ha/Replica
    instances and left null for Single instances. Metrics are fetched
    through the batch API CES BatchListMetricData (at most 83 instances
    per batch of 6 metrics each = 498 metrics, under the 500 limit) with
    the verified metric names (rds001_cpu_util, rds002_mem_util,
    rds039_disk_util, rds003_iops, rds072_conn_usage,
    rds073_replication_delay) and the literal comma dimension
    rds_cluster_id,<instance_id>; the batch constraint
    metrics_count * (to-from)_seconds / 60 <= 3000 is enforced by
    shrinking the window when needed. When --show-absolute-connections is
    given, ShowInstanceConfiguration provides max_connections so an
    estimated absolute connection count can be computed. Failures degrade
    in layers (instance/metric/API) and never abort the whole run.

Workflow:
    1. Parse the command line arguments.
    2. Validate the instance input (id, ids or all).
    3. Resolve the project id of the region.
    4. Resolve the target instances and their type/name/spec.
    5. Query the CES metrics in batches.
    6. Optionally compute absolute connections.
    7. Write the structured JSON report.

Dependencies:
    - Python 3.9+ standard library only (argparse, json, logging, os,
      sys, time, datetime).
    - rds_common (same directory, shared helpers).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import rds_common as common

LOGGER = logging.getLogger(__name__)

METRICS = [
    "rds001_cpu_util",
    "rds002_mem_util",
    "rds039_disk_util",
    "rds003_iops",
    "rds072_conn_usage",
]
METRIC_REPLICATION_DELAY = "rds073_replication_delay"
NAMESPACE_RDS = "SYS.RDS"
DIMENSION_NAME = "rds_cluster_id"
BATCH_METRIC_LIMIT = 500
METRICS_PER_INSTANCE = 6
INSTANCES_PER_BATCH = 83
BATCH_CONSTRAINT_NUM = 3000
DEFAULT_WINDOW_MS = 300000
DEFAULT_PERIOD = 300
EFFECTIVE_PERIOD_SECONDS = 60
DEFAULT_OUTPUT_PREFIX = "rds_monitor_result_{ts}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add the region, instance input, window, period, absolute
       connections and output options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--region", "cn-north-4", "--instance-id", "i1"])
        >>> args.instance_id == "i1"
        True
    """
    parser = argparse.ArgumentParser(
        prog="rds_monitor",
        description=(
            "Monitor key CES metrics of Huawei Cloud RDS for MySQL "
            "instances via the hcloud CLI and write a structured JSON "
            "snapshot."
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Required. Cloud region (e.g. cn-north-4).",
    )
    parser.add_argument(
        "--instance-id",
        default=None,
        help="Optional. Single target RDS instance id.",
    )
    parser.add_argument(
        "--instance-ids",
        default=None,
        help="Optional. Comma separated list of target RDS instance ids.",
    )
    parser.add_argument(
        "--all-instances",
        action="store_true",
        help="Optional. Monitor every MySQL instance of the region.",
    )
    parser.add_argument(
        "--from-ms",
        type=int,
        default=None,
        help="Optional. Window start as a millisecond epoch (default now-300000).",
    )
    parser.add_argument(
        "--to-ms",
        type=int,
        default=None,
        help="Optional. Window end as a millisecond epoch (default now).",
    )
    parser.add_argument(
        "--period",
        type=int,
        default=DEFAULT_PERIOD,
        help=(
            "Optional. CES period in seconds; 300 means 5-minute "
            "aggregation (default 300)."
        ),
    )
    parser.add_argument(
        "--show-absolute-connections",
        action="store_true",
        help=(
            "Optional. Query ShowInstanceConfiguration for max_connections "
            "and estimate the absolute connection count."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional. Path to the output JSON report file.",
    )
    return parser


def validate_instance_input(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Validate that exactly one instance input form is present.

    1. Count how many of instance-id/instance-ids/all-instances are set.
    2. Reject when none is set or more than one is set via parser.error.

    Args:
        parser: argparse.ArgumentParser — The configured parser.
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        None

    Examples:
        # An invalid combination exits the process with code 2.
        # >>> validate_instance_input(parser, argparse.Namespace(instance_id=None, instance_ids=None, all_instances=False))
        # SystemExit: 2
    """
    forms = [
        args.instance_id is not None,
        args.instance_ids is not None,
        bool(args.all_instances),
    ]
    if sum(forms) != 1:
        parser.error(
            "exactly one of --instance-id, --instance-ids or --all-instances must be provided"
        )


def resolve_window(args: argparse.Namespace) -> tuple[int, int]:
    """Resolve the query window as (from_ms, to_ms).

    1. Use the explicit from/to values when provided.
    2. Default to now and now minus the default 300000 ms window (300
       seconds, covering one full 5-minute CES collection cycle).

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        tuple[int, int]: (from_ms, to_ms).

    Examples:
        >>> args = argparse.Namespace(from_ms=None, to_ms=None)
        >>> f, t = resolve_window(args)
        >>> t - f == 300000
        True
    """
    to_ms = args.to_ms if args.to_ms is not None else int(time.time() * 1000)
    from_ms = (
        args.from_ms
        if args.from_ms is not None
        else to_ms - DEFAULT_WINDOW_MS
    )
    return from_ms, to_ms


def effective_period(period: int) -> int:
    """Return the effective period in seconds for the batch constraint.

    1. Map period=1 (realtime) to 60 seconds.
    2. Return other period values unchanged.

    Args:
        period: int — The CES period value.

    Returns:
        int: Effective period in seconds.

    Examples:
        >>> effective_period(1)
        60
        >>> effective_period(60)
        60
    """
    return EFFECTIVE_PERIOD_SECONDS if period == 1 else period


def shrink_window(
    from_ms: int,
    to_ms: int,
    metric_count: int,
    period: int,
) -> int:
    """Shrink the window start so the batch constraint is satisfied.

    1. Compute the maximum window in seconds under the constraint
       metric_count * window_seconds / effective_period <= 3000.
    2. Return the from timestamp that satisfies the constraint.

    Args:
        from_ms: int — Original window start in milliseconds.
        to_ms: int — Window end in milliseconds.
        metric_count: int — Number of metrics in the batch.
        period: int — The CES period value.

    Returns:
        int: Adjusted from timestamp in milliseconds.

    Examples:
        >>> shrink_window(0, 60000, 498, 1) == 0
        True
        >>> shrink_window(0, 14400000, 498, 1) > 0
        True
    """
    window_seconds = (to_ms - from_ms) // 1000
    eff_period = effective_period(period)
    max_window_seconds = (
        BATCH_CONSTRAINT_NUM * eff_period // metric_count
        if metric_count > 0
        else BATCH_CONSTRAINT_NUM * eff_period
    )
    if window_seconds <= max_window_seconds:
        return from_ms
    return to_ms - max_window_seconds * 1000


def build_metric_args(index: int, instance_id: str, metric_name: str) -> list[str]:
    """Build the BatchListMetricData arguments for one metric.

    1. Emit the namespace, metric name and dimension for the metric index.

    Args:
        index: int — The 1-based metric index in the batch request.
        instance_id: str — The RDS instance id used as the dimension value.
        metric_name: str — The CES metric name.

    Returns:
        list[str]: metrics.<index> command arguments.

    Examples:
        >>> args = build_metric_args(1, "i1", "rds001_cpu_util")
        >>> "--metrics.1.metric_name=rds001_cpu_util" in args
        True
        >>> "--metrics.1.dimensions.1.name=rds_cluster_id" in args
        True
    """
    return [
        "--metrics.{}.namespace={}".format(index, NAMESPACE_RDS),
        "--metrics.{}.metric_name={}".format(index, metric_name),
        "--metrics.{}.dimensions.1.name={}".format(index, DIMENSION_NAME),
        "--metrics.{}.dimensions.1.value={}".format(index, instance_id),
    ]


def query_metrics_batch(
    region: str,
    project_id: str,
    instances: list[dict],
    from_ms: int,
    to_ms: int,
    period: int,
    timeout: int,
) -> tuple[dict, list[str]]:
    """Query the CES metrics of one batch of instances.

    1. Build the metric list per instance, appending the replication delay
       metric only for Ha/Replica instances so Single instances are never
       queried for it.
    2. Enforce the batch constraint by shrinking the window if needed.
    3. Run BatchListMetricData and return the payload keyed by instance.

    Args:
        region: str — The cloud region code.
        project_id: str — The resolved project id of the region.
        instances: list[dict] — The instances of this batch with their
            type field.
        from_ms: int — Window start in milliseconds.
        to_ms: int — Window end in milliseconds.
        period: int — The CES period value.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        tuple[dict, list[str]]: (payload, warnings).

    Examples:
        # Requires hcloud credentials:
        # >>> query_metrics_batch("cn-north-4", "p1", [{"id": "i1", "type": "Ha"}], 1, 2, 1, 5)
        # ({}, [])
    """
    warnings: list[str] = []
    metric_args = []
    metric_count = 0
    for instance in instances:
        names = list(METRICS)
        if instance.get("type") in ("Ha", "Replica"):
            names.append(METRIC_REPLICATION_DELAY)
        for name in names:
            metric_count += 1
            metric_args.extend(
                build_metric_args(metric_count, instance["id"], name)
            )
    adjusted_from = shrink_window(from_ms, to_ms, metric_count, period)
    if adjusted_from != from_ms:
        warnings.append(
            "window shrunk from {} ms to {} ms to satisfy the batch constraint".format(
                from_ms, adjusted_from
            )
        )
    cmd = [
        "CES",
        "--cli-region={}".format(region),
        "--project_id={}".format(project_id),
        "BatchListMetricData",
    ] + metric_args + [
        "--filter=average",
        "--from={}".format(adjusted_from),
        "--to={}".format(to_ms),
        "--period={}".format(period),
    ]
    try:
        payload = common.run_hcloud(cmd, timeout)
    except common.HcloudError as exc:
        warnings.append("BatchListMetricData failed: {}".format(exc))
        return {}, warnings
    if "error_code" in payload:
        warnings.append(
            "BatchListMetricData failed: {}".format(
                common.extract_error_message(payload)
            )
        )
        return {}, warnings
    return payload, warnings


def parse_batch_payload(
    payload: dict, instance_ids: list[str]
) -> dict[str, dict]:
    """Parse a BatchListMetricData payload into per-instance metric dicts.

    1. Group metrics by instance id from the dimensions.
    2. For each metric take the datapoint with the largest timestamp.
    3. Read the unit from the metrics[] level, not the datapoints.

    Args:
        payload: dict — The parsed BatchListMetricData payload.
        instance_ids: list[str] — The instance ids of the batch.

    Returns:
        dict[str, dict]: instance_id -> {metric_name: {value, unit, timestamp}}.

    Examples:
        >>> payload = {"metrics": [{"metric_name": "rds001_cpu_util", "unit": "%",
        ...     "dimensions": [{"name": "rds_cluster_id", "value": "i1"}],
        ...     "datapoints": [{"average": 12.5, "timestamp": 100}]}]}
        >>> parsed = parse_batch_payload(payload, ["i1"])
        >>> parsed["i1"]["rds001_cpu_util"]["value"] == 12.5
        True
    """
    parsed = {instance_id: {} for instance_id in instance_ids}
    metrics = payload.get("metrics") or []
    for metric in metrics:
        instance_id = ""
        dimensions = metric.get("dimensions") or []
        for dimension in dimensions:
            if dimension.get("name") == DIMENSION_NAME:
                instance_id = dimension.get("value", "")
        if instance_id not in parsed:
            continue
        metric_name = metric.get("metric_name", "")
        unit = metric.get("unit", "")
        datapoints = metric.get("datapoints") or []
        if not datapoints:
            parsed[instance_id][metric_name] = None
            continue
        latest = max(datapoints, key=lambda dp: dp.get("timestamp", 0))
        parsed[instance_id][metric_name] = {
            "value": latest.get("average"),
            "unit": unit,
            "timestamp": latest.get("timestamp"),
        }
    return parsed


def query_metric_single(
    region: str,
    project_id: str,
    instance_id: str,
    metric_name: str,
    from_ms: int,
    to_ms: int,
    period: int,
    timeout: int,
) -> dict | None:
    """Query one metric of one instance via ShowMetricData.

    1. Build the ShowMetricData command with the literal comma dimension.
    2. Run it and parse the latest datapoint.

    Args:
        region: str — The cloud region code.
        project_id: str — The resolved project id of the region.
        instance_id: str — The target RDS instance id.
        metric_name: str — The CES metric name.
        from_ms: int — Window start in milliseconds.
        to_ms: int — Window end in milliseconds.
        period: int — The CES period value.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        dict | None: {value, unit, timestamp} or None on failure/empty.

    Examples:
        # Requires hcloud credentials:
        # >>> query_metric_single("cn-north-4", "p1", "i1", "rds001_cpu_util", 1, 2, 1, 5)
        # None
    """
    cmd = [
        "CES",
        "--cli-region={}".format(region),
        "--project_id={}".format(project_id),
        "ShowMetricData",
        "--namespace={}".format(NAMESPACE_RDS),
        "--metric_name={}".format(metric_name),
        "--dim.0={},{}".format(DIMENSION_NAME, instance_id),
        "--filter=average",
        "--from={}".format(from_ms),
        "--to={}".format(to_ms),
        "--period={}".format(period),
    ]
    try:
        payload = common.run_hcloud(cmd, timeout)
    except common.HcloudError:
        return None
    if "error_code" in payload:
        return None
    datapoints = payload.get("datapoints") or []
    if not datapoints:
        return None
    latest = max(datapoints, key=lambda dp: dp.get("timestamp", 0))
    return {
        "value": latest.get("average"),
        "unit": latest.get("unit", ""),
        "timestamp": latest.get("timestamp"),
    }


def resolve_instances(
    args: argparse.Namespace,
    cmd_prefix: list[str],
    timeout: int,
) -> tuple[list[dict], list[str]]:
    """Resolve the target instances and their type/name/spec.

    1. Build the instance id list from the input form.
    2. For each instance call ListInstances filtered by id and read the
       type/name/spec; on failure skip the instance with a warning.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        cmd_prefix: list[str] — Base RDS hcloud command prefix.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        tuple[list[dict], list[str]]: (instance list, warnings).

    Examples:
        # Requires hcloud credentials:
        # >>> resolve_instances(argparse.Namespace(), ["RDS"], 5)
        # ([], [])
    """
    warnings: list[str] = []
    if args.instance_id:
        instance_ids = [args.instance_id]
    elif args.instance_ids:
        instance_ids = [part.strip() for part in args.instance_ids.split(",") if part.strip()]
    else:
        try:
            payload = common.run_hcloud(
                cmd_prefix
                + [common.CMD_LIST_INSTANCES, "--datastore_type=MySQL"],
                timeout,
            )
        except common.HcloudError as exc:
            warnings.append("ListInstances failed: {}".format(exc))
            return [], warnings
        instance_ids = [
            instance.get("id", "")
            for instance in (payload.get("instances") or [])
            if instance.get("id")
        ]

    instances: list[dict] = []
    for instance_id in instance_ids:
        try:
            payload = common.run_hcloud(
                cmd_prefix
                + [common.CMD_LIST_INSTANCES, "--id={}".format(instance_id)],
                timeout,
            )
        except common.HcloudError as exc:
            warnings.append(
                "ListInstances failed for {}: {}".format(instance_id, exc)
            )
            continue
        listed = payload.get("instances") or []
        if not listed:
            warnings.append("no instance found for id {}".format(instance_id))
            continue
        instance = listed[0]
        instances.append(
            {
                "id": instance_id,
                "name": instance.get("name", ""),
                "type": instance.get("type", ""),
                "status": instance.get("status", ""),
                "spec_code": instance.get("flavor_ref", ""),
            }
        )
    return instances, warnings


def query_max_connections(
    cmd_prefix: list[str],
    instance_id: str,
    timeout: int,
) -> tuple[str | None, str | None]:
    """Query the max_connections parameter of an instance.

    1. Run ShowInstanceConfiguration for the instance.
    2. Read the value of the configuration_parameters entry whose name is
       max_connections.

    Args:
        cmd_prefix: list[str] — Base RDS hcloud command prefix.
        instance_id: str — The target RDS instance id.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        tuple[str | None, str | None]: (max_connections value, error).

    Examples:
        # Requires hcloud credentials:
        # >>> query_max_connections(["RDS"], "i1", 5)
        # (None, None)
    """
    try:
        payload = common.run_hcloud(
            cmd_prefix
            + [
                "ShowInstanceConfiguration",
                "--instance_id={}".format(instance_id),
            ],
            timeout,
        )
    except common.HcloudError as exc:
        return None, str(exc)
    if "error_code" in payload:
        return None, common.extract_error_message(payload)
    parameters = payload.get("configuration_parameters") or []
    for parameter in parameters:
        if parameter.get("name") == "max_connections":
            return parameter.get("value"), None
    return None, "max_connections not found in configuration"


def build_snapshot_window(from_ms: int, to_ms: int, period: int) -> dict:
    """Build the snapshot_window metadata dict.

    Args:
        from_ms: int — Window start in milliseconds.
        to_ms: int — Window end in milliseconds.
        period: int — The CES period value.

    Returns:
        dict: Snapshot window metadata.

    Examples:
        >>> build_snapshot_window(1, 2, 1)["period"] == 1
        True
    """
    return {"from": from_ms, "to": to_ms, "period": period}


def resolve_default_output() -> str:
    """Resolve the default output path in the script directory.

    1. Join the script directory with the timestamped file name.

    Args:
        None

    Returns:
        str: Absolute default output file path.

    Examples:
        >>> resolve_default_output().endswith("rds_monitor_result_")
        True
    """
    return os.path.join(
        common.SCRIPT_DIR,
        DEFAULT_OUTPUT_PREFIX.format(ts=common.timestamp_now()),
    )


def run(args: argparse.Namespace) -> int:
    """Resolve the project id, query the metrics and write the report.

    1. Resolve the region project id via KeystoneListAuthProjects.
    2. Resolve the target instances with their type/name/spec.
    3. Query the CES metrics in batches of at most 83 instances.
    4. Fall back to per-metric ShowMetricData when a batch fails.
    5. Optionally compute absolute connections.
    6. Write the structured JSON report and return the exit code.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 with at least one metric, 1 otherwise).

    Examples:
        # Requires hcloud credentials:
        # >>> run(args)
        1
    """
    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        cmd_prefix = common.make_rds_prefix(args.region, project_id)
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1

    warnings: list[str] = []
    instances, resolve_warnings = resolve_instances(
        args, cmd_prefix, common.DEFAULT_TIMEOUT
    )
    warnings.extend(resolve_warnings)
    if not instances:
        report = build_report(args, [], warnings)
        return common.write_report(report, args.output, common.timestamp_now())

    from_ms, to_ms = resolve_window(args)
    period = args.period
    metrics_any: dict[str, dict] = {}

    # Batch query per group of instances (at most 83 per batch).
    for start in range(0, len(instances), INSTANCES_PER_BATCH):
        batch = instances[start : start + INSTANCES_PER_BATCH]
        payload, batch_warnings = query_metrics_batch(
            args.region,
            project_id,
            batch,
            from_ms,
            to_ms,
            period,
            common.DEFAULT_TIMEOUT,
        )
        warnings.extend(batch_warnings)
        if not payload:
            # API-level fallback: query every metric individually.
            warnings.append(
                "batch query failed; degraded to per-metric ShowMetricData"
            )
            for instance in batch:
                instance_id = instance["id"]
                names = list(METRICS)
                if instance["type"] in ("Ha", "Replica"):
                    names.append(METRIC_REPLICATION_DELAY)
                for metric_name in names:
                    metric = query_metric_single(
                        args.region,
                        project_id,
                        instance_id,
                        metric_name,
                        from_ms,
                        to_ms,
                        period,
                        common.DEFAULT_TIMEOUT,
                    )
                    if metric is None:
                        warnings.append(
                            "metric {} has no data for {}".format(
                                metric_name, instance_id
                            )
                        )
                    metrics_any.setdefault(instance_id, {})[metric_name] = metric
        else:
            parsed = parse_batch_payload(
                payload, [instance["id"] for instance in batch]
            )
            for instance_id, parsed_metrics in parsed.items():
                for metric_name, metric in parsed_metrics.items():
                    if metric is None:
                        # Single-metric fallback: the batch succeeded but
                        # this metric is missing; query it individually.
                        metric = query_metric_single(
                            args.region,
                            project_id,
                            instance_id,
                            metric_name,
                            from_ms,
                            to_ms,
                            period,
                            common.DEFAULT_TIMEOUT,
                        )
                        if metric is None:
                            warnings.append(
                                "metric {} has no data for {}".format(
                                    metric_name, instance_id
                                )
                            )
                    metrics_any.setdefault(instance_id, {})[metric_name] = metric

    instances_out: list[dict] = []
    for instance in instances:
        instance_id = instance["id"]
        instance_metrics = metrics_any.get(instance_id, {})
        cpu = instance_metrics.get("rds001_cpu_util")
        mem = instance_metrics.get("rds002_mem_util")
        disk = instance_metrics.get("rds039_disk_util")
        iops = instance_metrics.get("rds003_iops")
        usage_percent = instance_metrics.get("rds072_conn_usage")
        delay = instance_metrics.get(METRIC_REPLICATION_DELAY)
        connections: dict = {"usage_percent": usage_percent.get("value") if usage_percent else None}
        if args.show_absolute_connections and usage_percent:
            max_conn, error = query_max_connections(
                cmd_prefix, instance_id, common.DEFAULT_TIMEOUT
            )
            if error:
                warnings.append(
                    "ShowInstanceConfiguration failed for {}: {}".format(
                        instance_id, error
                    )
                )
            connections["max_connections"] = max_conn
            if usage_percent.get("value") is not None and max_conn is not None:
                try:
                    connections["current_connections_estimated"] = "{:.0f}".format(
                        float(usage_percent["value"]) * float(max_conn) / 100
                    )
                except (TypeError, ValueError):
                    connections["current_connections_estimated"] = None
            else:
                connections["current_connections_estimated"] = None
        else:
            connections["max_connections"] = None
            connections["current_connections_estimated"] = None
        if usage_percent:
            connections["timestamp"] = usage_percent.get("timestamp")
        instances_out.append(
            {
                "id": instance_id,
                "name": instance["name"],
                "type": instance["type"],
                "status": instance["status"],
                "spec_code": instance["spec_code"],
                "metrics": {
                    "cpu_util": cpu,
                    "mem_util": mem,
                    "disk_util": disk,
                    "iops": iops,
                    "connections": connections,
                    "replication_delay": delay,
                },
            }
        )

    report = build_report(args, instances_out, warnings)
    write_result = common.write_report(report, args.output, common.timestamp_now())
    if write_result != 0:
        return 1
    return 0


def build_report(
    args: argparse.Namespace, instances: list[dict], warnings: list[str]
) -> dict:
    """Build the structured JSON report payload.

    1. Fill the metadata section from the run context.
    2. Resolve the query window for the snapshot_window section.
    3. Attach the instances array and the warnings array.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        instances: list[dict] — Per-instance metric results.
        warnings: list[str] — Collected warnings.

    Returns:
        dict: The report payload.

    Examples:
        >>> report = build_report(argparse.Namespace(region="cn-north-4", from_ms=None, to_ms=None, period=1), [], [])
        >>> report["metadata"]["script"] == "rds_monitor"
        True
    """
    from_ms, to_ms = resolve_window(args)
    return {
        "metadata": {
            "script": "rds_monitor",
            "version": "1.0",
            "region": args.region,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_window": build_snapshot_window(from_ms, to_ms, args.period),
        },
        "instances": instances,
        "warnings": warnings,
    }


def main() -> int:
    """Run the monitoring workflow.

    1. Parse arguments and validate the instance input.
    2. Set up logging and delegate to run().

    Args:
        None

    Returns:
        int: Exit code (0 on success, 1 on failure, 2 on invalid arguments).

    Examples:
        # Running the script requires hcloud credentials:
        # >>> main()
        1
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    validate_instance_input(parser, args)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
