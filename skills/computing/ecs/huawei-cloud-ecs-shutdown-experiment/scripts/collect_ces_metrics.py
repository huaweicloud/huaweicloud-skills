#!/usr/bin/env python3
"""
collect_ces_metrics.py — Collect CES (Cloud Eye Service) monitoring metrics
for ECS instances during a shutdown fault injection experiment.

Queries Huawei Cloud CES for platform-level (SYS.ECS) and agent-level (AGT.ECS)
metrics within the experiment time window, and summarizes them by phase
(pre-shutdown / during-shutdown / post-recovery).

Usage:
    # As a module (imported by analyze_logs.py)
    from collect_ces_metrics import collect_ces_metrics, summarize_ces_metrics

    # Standalone
    python3 collect_ces_metrics.py \
        --instance-ids i-xxx \
        --start-time "2026-09-23T06:08:32Z" --end-time "2026-09-23T06:18:00Z" \
        --cli-region cn-north-4
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from collect_logs import run_hcloud, iso_to_epoch_ms


# ---------------------------------------------------------------------------
# Metric definitions
#
# SYS.ECS metrics are platform-level (collected by the hypervisor), present
# for any running ECS without needing an agent. AGT.ECS metrics require the
# telescope/uniagent Agent installed inside the ECS.
#
# IMPORTANT: period must be 300 (5 minutes) for SYS.ECS — period=60 returns
# empty datapoints (CES aggregates SYS.ECS at 5-min granularity). AGT.ECS
# supports finer periods but we use 300 for consistency.
# ---------------------------------------------------------------------------

CES_METRICS = [
    # SYS.ECS — platform-level, no agent required
    {
        "namespace": "SYS.ECS",
        "metric_name": "cpu_util",
        "label": "CPU Utilization",
        "unit_expected": "%",
        "requires_agent": False,
    },
    {
        "namespace": "SYS.ECS",
        "metric_name": "network_incoming_bytes_aggregate_rate",
        "label": "Network Incoming Rate",
        "unit_expected": "B/s",
        "requires_agent": False,
    },
    {
        "namespace": "SYS.ECS",
        "metric_name": "network_outgoing_bytes_aggregate_rate",
        "label": "Network Outgoing Rate",
        "unit_expected": "B/s",
        "requires_agent": False,
    },
    {
        "namespace": "SYS.ECS",
        "metric_name": "disk_read_bytes_rate",
        "label": "Disk Read Rate",
        "unit_expected": "B/s",
        "requires_agent": False,
    },
    {
        "namespace": "SYS.ECS",
        "metric_name": "disk_write_bytes_rate",
        "label": "Disk Write Rate",
        "unit_expected": "B/s",
        "requires_agent": False,
    },
    # AGT.ECS — requires Agent installed inside ECS
    {
        "namespace": "AGT.ECS",
        "metric_name": "mem_usedPercent",
        "label": "Memory Usage",
        "unit_expected": "%",
        "requires_agent": True,
    },
]

# Period for CES queries: 300 seconds (5 minutes).
# CES aggregates SYS.ECS metrics at 5-min granularity; period=60 returns empty.
CES_PERIOD = 300

# How far back to extend the query window before experiment start, to capture
# pre-shutdown baseline data. 10 minutes = 2 aggregation periods.
PRE_WINDOW_MINUTES = 10

# How far forward to extend the query window after experiment end, to capture
# post-recovery data. 10 minutes = 2 aggregation periods (CES 5-min granularity).
POST_WINDOW_MINUTES = 10


def _query_single_metric(instance_id, namespace, metric_name,
                         start_ms, end_ms, region=None):
    """Query CES ShowMetricData for a single metric. Returns parsed datapoints.

    Handles CES API network errors gracefully — in some sandboxed environments
    the CES endpoint resolves to an internal IP (100.125.x.x) that is not
    routable. See references/managed-service-logs.md → CES section.
    """
    command = [
        "CES", "ShowMetricData", "--cli-output=json",
        f"--namespace={namespace}",
        f"--metric_name={metric_name}",
        f"--dim.0=instance_id,{instance_id}",
        f"--from={start_ms}",
        f"--to={end_ms}",
        f"--period={CES_PERIOD}",
        "--filter=average",
    ]

    success, data = run_hcloud(command, region=region)

    if not success:
        return {
            "success": False,
            "error": str(data),
            "datapoints": [],
        }

    if not isinstance(data, dict):
        return {
            "success": False,
            "error": f"Unexpected response type: {type(data)}",
            "datapoints": [],
        }

    datapoints = data.get("datapoints", [])
    return {
        "success": True,
        "error": None,
        "datapoints": datapoints,
    }


def collect_ces_metrics(instance_ids, start_time, end_time, region=None):
    """Query CES metrics for all target instances within the time window.

    Extends the query window back by PRE_WINDOW_MINUTES to capture pre-shutdown
    baseline data.

    Args:
        instance_ids: list of ECS instance IDs
        start_time: ISO 8601 timestamp (experiment start)
        end_time: ISO 8601 timestamp (experiment end + buffer)
        region: Huawei Cloud region

    Returns:
        dict keyed by instance_id, each containing a list of metric results
        with datapoints.
    """
    # Extend start time back to capture baseline, and end time forward to
    # capture post-recovery data (CES aggregates at 5-min granularity, so we
    # need at least 2 periods after recovery to get a post-recovery datapoint)
    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    extended_start = start_dt - timedelta(minutes=PRE_WINDOW_MINUTES)
    extended_end = end_dt + timedelta(minutes=POST_WINDOW_MINUTES)

    start_ms = iso_to_epoch_ms(extended_start.isoformat())
    end_ms = iso_to_epoch_ms(extended_end.isoformat())

    results = {}
    for instance_id in instance_ids:
        metric_results = []
        for metric_def in CES_METRICS:
            result = _query_single_metric(
                instance_id,
                metric_def["namespace"],
                metric_def["metric_name"],
                start_ms, end_ms, region,
            )
            metric_results.append({
                "namespace": metric_def["namespace"],
                "metric_name": metric_def["metric_name"],
                "label": metric_def["label"],
                "requires_agent": metric_def["requires_agent"],
                "success": result["success"],
                "error": result["error"],
                "datapoints": result["datapoints"],
            })
        results[instance_id] = metric_results

    return results


def _parse_iso_ts(ts_str):
    """Parse ISO 8601 timestamp to datetime (UTC)."""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_dp_ts(ts_ms):
    """Parse epoch-millisecond timestamp from CES datapoint to datetime."""
    if ts_ms is None:
        return None
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    except (ValueNotFoundError, TypeError, OSError):
        return None


def _find_phase_boundaries(instance_timeline):
    """Extract shutdown and recovery timestamps from instance_timeline.

    Returns (shutdown_ts, recovery_ts) as datetime objects, or (None, None)
    if the timeline doesn't contain the expected state transitions.
    """
    shutdown_ts = None
    recovery_ts = None

    for event in instance_timeline:
        new_status = event.get("new_status")
        old_status = event.get("old_status")
        ts = _parse_iso_ts(event.get("timestamp"))

        if not ts:
            continue

        # Shutdown: ACTIVE → SHUTOFF
        if new_status == "SHUTOFF" and old_status == "ACTIVE":
            shutdown_ts = ts

        # Recovery: SHUTOFF → ACTIVE
        if new_status == "ACTIVE" and old_status == "SHUTOFF":
            recovery_ts = ts

    return shutdown_ts, recovery_ts


def _stats_for_phase(datapoints, phase_start, phase_end):
    """Calculate statistics for datapoints within a time range.

    Returns dict with count, average, min, max. If no datapoints in range,
    returns zeros.
    """
    in_range = []
    for dp in datapoints:
        dp_ts = _parse_dp_ts(dp.get("timestamp"))
        if not dp_ts:
            continue
        if phase_start and dp_ts < phase_start:
            continue
        if phase_end and dp_ts >= phase_end:
            continue
        in_range.append(dp.get("average", 0))

    if not in_range:
        return {"count": 0, "average": None, "min": None, "max": None}

    return {
        "count": len(in_range),
        "average": round(sum(in_range) / len(in_range), 2),
        "min": round(min(in_range), 2),
        "max": round(max(in_range), 2),
    }


def summarize_ces_metrics(metrics_data, instance_timeline):
    """Summarize CES metrics by experiment phase.

    Uses the instance_timeline to identify three phases:
      - pre_shutdown: before ACTIVE→SHUTOFF transition
      - during_shutdown: SHUTOFF period (shutdown to recovery)
      - post_recovery: after SHUTOFF→ACTIVE transition

    For each metric, computes average/min/max per phase.

    Args:
        metrics_data: output of collect_ces_metrics()
        instance_timeline: list of state-change events from execution-log.json

    Returns:
        dict keyed by instance_id, each containing per-metric phase summaries
        and observations.
    """
    shutdown_ts, recovery_ts = _find_phase_boundaries(instance_timeline)

    summary = {}
    for instance_id, metric_results in metrics_data.items():
        metric_summaries = []
        observations = []

        for metric in metric_results:
            label = metric["label"]
            metric_name = metric["metric_name"]
            namespace = metric["namespace"]
            datapoints = metric.get("datapoints", [])

            if not metric.get("success"):
                metric_summaries.append({
                    "label": label,
                    "metric_name": metric_name,
                    "namespace": namespace,
                    "error": metric.get("error", "unknown error"),
                    "phases": None,
                })
                observations.append(f"{label}: collection failed ({metric.get('error', '')[:60]})")
                continue

            if not datapoints:
                metric_summaries.append({
                    "label": label,
                    "metric_name": metric_name,
                    "namespace": namespace,
                    "error": None,
                    "phases": None,
                })
                observations.append(f"{label}: no datapoints")
                continue

            # Compute stats per phase
            pre_stats = _stats_for_phase(datapoints, None, shutdown_ts)
            during_stats = _stats_for_phase(datapoints, shutdown_ts, recovery_ts)
            post_stats = _stats_for_phase(datapoints, recovery_ts, None)

            unit = datapoints[0].get("unit", "") if datapoints else ""

            metric_summaries.append({
                "label": label,
                "metric_name": metric_name,
                "namespace": namespace,
                "unit": unit,
                "error": None,
                "phases": {
                    "pre_shutdown": pre_stats,
                    "during_shutdown": during_stats,
                    "post_recovery": post_stats,
                },
            })

            # Generate observations
            during_min = during_stats.get("min")
            during_avg = during_stats.get("average")
            pre_avg = pre_stats.get("average")
            post_avg = post_stats.get("average")

            if during_min is not None and during_min == 0:
                observations.append(
                    f"{label}: metric dropped to zero during shutdown (min=0{unit}), as expected")
            elif during_avg is not None and during_avg == 0:
                observations.append(
                    f"{label}: metric average was zero during shutdown, as expected")
            elif during_stats["count"] == 0:
                observations.append(
                    f"{label}: no datapoints during shutdown (instance stopped, CES paused collection)")
            elif during_avg is not None and pre_avg is not None and during_avg < pre_avg * 0.1:
                observations.append(
                    f"{label}: metric dropped sharply during shutdown ({pre_avg}{unit} → {during_avg}{unit})")

            if post_avg is not None and pre_avg is not None:
                if post_avg >= pre_avg * 0.5:
                    observations.append(
                        f"{label}: metric recovered to pre-shutdown level after restart ({pre_avg}{unit} → {post_avg}{unit})")
                else:
                    observations.append(
                        f"{label}: metric remains low after recovery (pre-shutdown {pre_avg}{unit} → post-recovery {post_avg}{unit}), needs attention")

        summary[instance_id] = {
            "metrics": metric_summaries,
            "observations": observations,
            "phase_boundaries": {
                "shutdown_ts": shutdown_ts.isoformat() if shutdown_ts else None,
                "recovery_ts": recovery_ts.isoformat() if recovery_ts else None,
            },
        }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Collect CES monitoring metrics for ECS instances during experiment."
    )
    parser.add_argument("--instance-ids", required=True,
                        help="Comma-separated ECS instance IDs")
    parser.add_argument("--start-time", required=True,
                        help="Experiment start time (ISO 8601)")
    parser.add_argument("--end-time", required=True,
                        help="Experiment end time (ISO 8601)")
    parser.add_argument("--cli-region", dest="region",
                        default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region")
    parser.add_argument("--output-file", help="Write result to file")
    args = parser.parse_args()

    instance_ids = [s.strip() for s in args.instance_ids.split(",") if s.strip()]

    print(f"Collecting CES metrics for {len(instance_ids)} instance(s) ...")
    print(f"  Time window: {args.start_time} → {args.end_time}")
    print(f"  Region: {args.region}")

    metrics = collect_ces_metrics(
        instance_ids, args.start_time, args.end_time, args.region
    )

    # Print summary
    for iid, metric_list in metrics.items():
        print(f"\n  Instance: {iid}")
        for m in metric_list:
            dp_count = len(m.get("datapoints", []))
            status = "OK" if m.get("success") else "FAILED"
            print(f"    [{status}] {m['label']} ({m['namespace']}/{m['metric_name']}): "
                  f"{dp_count} datapoints")

    output = json.dumps(metrics, indent=2, ensure_ascii=False)
    if args.output_file:
        with open(args.output_file, "w") as f:
            f.write(output)
        print(f"\nResult written to {args.output_file}")
    else:
        print(f"\n{output}")


if __name__ == "__main__":
    main()
