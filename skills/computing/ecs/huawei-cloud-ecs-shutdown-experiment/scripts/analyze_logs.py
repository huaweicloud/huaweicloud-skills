#!/usr/bin/env python3
"""
analyze_logs.py — Main analysis script for ECS shutdown experiment log analysis.

Loads experiment context, identifies affected services, collects logs from
LTS, analyzes error patterns, and generates an analysis result.

Supports two modes:
  - Real-time: experiment in progress, loads from experiment.json (prepare output)
  - Post-hoc: experiment completed, loads from execution-log.json (execute output)

Usage:
    python3 analyze_logs.py --experiment-dir ./experiments/xxx/ --log-group-id <lts-group-id>
    python3 analyze_logs.py --log-file ./experiments/xxx/execution-log.json --log-group-id <lts-group-id>
    python3 analyze_logs.py --experiment-dir ./experiments/xxx/ --dry-run
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from collect_logs import collect_lts_logs, get_instance_endpoints
from collect_ces_metrics import collect_ces_metrics, summarize_ces_metrics


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_experiment_context(experiment_dir=None, log_file=None):
    """Load experiment context from execution-log.json (post-hoc) or
    experiment.json (real-time fallback).

    Returns a normalized dict with:
      - mode: "post-hoc" or "real-time"
      - experiment_name, region, started_at, completed_at
      - instance_ids, instance_timeline
    """
    # 1. Try execution-log.json first (post-hoc mode)
    exec_log_path = log_file
    if not exec_log_path and experiment_dir:
        exec_log_path = os.path.join(experiment_dir, "execution-log.json")

    if exec_log_path and os.path.exists(exec_log_path):
        with open(exec_log_path) as f:
            data = json.load(f)
        return {
            "mode": "post-hoc",
            "experiment_name": data.get("experiment_name", "unnamed"),
            "region": data.get("region", ""),
            "started_at": data.get("started_at", ""),
            "completed_at": data.get("completed_at", ""),
            "instance_ids": data.get("instance_ids", []),
            "instance_timeline": data.get("instance_timeline", []),
        }

    # 2. Fall back to experiment.json (real-time mode)
    exp_json_path = None
    if experiment_dir:
        exp_json_path = os.path.join(experiment_dir, "experiment.json")
    elif log_file:
        sibling = os.path.join(os.path.dirname(log_file), "experiment.json")
        if os.path.exists(sibling):
            exp_json_path = sibling

    if exp_json_path and os.path.exists(exp_json_path):
        with open(exp_json_path) as f:
            data = json.load(f)

        instance_ids = data.get("targets", {}).get("instance_ids", [])
        duration = data.get("actions", {}).get("shutdown", {}).get("duration_seconds", 300)

        start_dt = datetime.now(timezone.utc)
        end_dt = start_dt + timedelta(seconds=duration, minutes=3)

        return {
            "mode": "real-time",
            "experiment_name": data.get("experiment_name", "unnamed"),
            "region": data.get("region", ""),
            "started_at": start_dt.isoformat(),
            "completed_at": end_dt.isoformat(),
            "instance_ids": instance_ids,
            "instance_timeline": [],
        }

    # 3. Neither file found
    tried = []
    if exec_log_path:
        tried.append(exec_log_path)
    if exp_json_path:
        tried.append(exp_json_path)
    print(f"Error: No experiment context found. Tried: {', '.join(tried)}", file=sys.stderr)
    print("Provide --experiment-dir containing execution-log.json or experiment.json,"
          " or --log-file pointing to execution-log.json.", file=sys.stderr)
    sys.exit(1)


def parse_iso_to_datetime(ts):
    """Parse ISO 8601 timestamp to datetime."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# Error pattern definitions
ERROR_PATTERNS = [
    {"name": "error", "regex": re.compile(r"(?i)\b(ERROR|Exception|Traceback|FATAL)\b"), "severity": "high", "label": "ERROR/Exception"},
    {"name": "connection_refused", "regex": re.compile(r"(?i)(connection.*refused|ECONNREFUSED|connect.*fail)"), "severity": "high", "label": "Connection refused"},
    {"name": "timeout", "regex": re.compile(r"(?i)(timeout|timed?\s*out|ETIMEDOUT)"), "severity": "high", "label": "Timeout"},
    {"name": "http_5xx", "regex": re.compile(r"(?i)(HTTP\s*5\d\d|status[:\s]*5\d\d|error.*500|503|502)"), "severity": "high", "label": "HTTP 5xx"},
    {"name": "reconnect", "regex": re.compile(r"(?i)(reconnect|retry|retrying|retry.*count)"), "severity": "medium", "label": "Reconnect attempt"},
    {"name": "degrade", "regex": re.compile(r"(?i)(degrade|fallback|circuit.*breaker|hystrix)"), "severity": "medium", "label": "Degrade/Circuit breaker"},
    {"name": "recovery", "regex": re.compile(r"(?i)(recover|restored|reconnected|back.*online|healthy)"), "severity": "info", "label": "Recovery"},
]


def analyze_log_entries(logs, instance_timeline=None):
    """Analyze log entries for error patterns and build timeline.
    All processing is local (no network calls) — patterns are matched against
    pre-collected log entries.
    """
    matched_events = []
    pattern_counts = {}
    severity_counts = {"high": 0, "medium": 0, "info": 0}

    # Pre-compile pattern list for efficient local matching
    compiled_patterns = ERROR_PATTERNS

    for log_entry in logs:
        message = log_entry.get("message", "")
        timestamp = log_entry.get("timestamp", "")
        source = log_entry.get("source", "unknown")
        level = log_entry.get("level", "")

        for pat in compiled_patterns:
            if pat["regex"].search(message) or (level.upper() == "ERROR" and pat["name"] == "error"):
                event = {
                    "timestamp": timestamp,
                    "pattern": pat["name"],
                    "label": pat["label"],
                    "severity": pat["severity"],
                    "message": message[:200],
                    "source": source,
                }
                matched_events.append(event)
                pattern_counts[pat["name"]] = pattern_counts.get(pat["name"], 0) + 1
                severity_counts[pat["severity"]] += 1
                break  # One match per log entry

    # Sort by timestamp (local operation)
    matched_events.sort(key=lambda e: e.get("timestamp", ""))

    # Calculate recovery time from pre-loaded timeline (local processing)
    recovery_time = None
    if instance_timeline and matched_events:
        recovery_ts = None
        for event in instance_timeline:
            if event.get("new_status") == "ACTIVE" and event.get("old_status") in ("STARTING", "SHUTOFF"):
                recovery_ts = event.get("timestamp")
        if recovery_ts:
            last_error_ts = None
            for ev in matched_events:
                if ev["severity"] == "high" and ev["timestamp"] and ev["timestamp"] > recovery_ts:
                    last_error_ts = ev["timestamp"]
            if last_error_ts:
                r_start = parse_iso_to_datetime(recovery_ts)
                r_end = parse_iso_to_datetime(last_error_ts)
                if r_start and r_end:
                    recovery_time = int((r_end - r_start).total_seconds())

    # Calculate error duration (local processing)
    error_duration = None
    high_errors = [e for e in matched_events if e["severity"] == "high"]
    if len(high_errors) >= 2:
        first = parse_iso_to_datetime(high_errors[0].get("timestamp", ""))
        last = parse_iso_to_datetime(high_errors[-1].get("timestamp", ""))
        if first and last:
            error_duration = int((last - first).total_seconds())

    return {
        "total_logs": len(logs),
        "total_errors": len(matched_events),
        "by_pattern": pattern_counts,
        "by_severity": severity_counts,
        "events": matched_events,
        "error_duration_seconds": error_duration,
        "recovery_time_seconds": recovery_time,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze application logs during ECS shutdown experiment."
    )
    parser.add_argument("--experiment-dir", help="Path to experiment directory")
    parser.add_argument("--log-file", help="Direct path to execution-log.json")
    parser.add_argument("--cli-region", dest="region",
                        default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region (e.g. cn-north-4)")
    parser.add_argument("--log-group-id",
                        help="LTS log group ID for log collection (required unless --dry-run)")
    parser.add_argument("--log-stream-id", help="LTS log stream ID")
    parser.add_argument("--keywords", default="ERROR", help="LTS search keywords")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual API calls")
    parser.add_argument("--output-file", help="Write analysis result to file")
    args = parser.parse_args()

    if not args.dry_run and not args.log_group_id:
        print("Error: --log-group-id is required for real analysis "
              "(omit it only with --dry-run).", file=sys.stderr)
        sys.exit(1)

    # Step 1: Load experiment context
    print(f"\n{'='*60}")
    print(f"  ECS Shutdown Experiment — Log Analysis")
    print(f"{'='*60}\n")

    print("[1/5] Loading experiment context ...")
    ctx = load_experiment_context(args.experiment_dir, args.log_file)

    mode = ctx["mode"]
    exp_name = ctx["experiment_name"]
    started_at = ctx["started_at"]
    completed_at = ctx["completed_at"]
    instance_ids = ctx["instance_ids"]
    instance_timeline = ctx["instance_timeline"]
    region = args.region or ctx["region"] or "cn-north-4"

    # Add 3-minute buffer to end time for recovery behavior (post-hoc mode)
    if mode == "post-hoc":
        end_dt = parse_iso_to_datetime(completed_at)
        if end_dt:
            end_dt = end_dt + timedelta(minutes=3)
            analysis_end_time = end_dt.isoformat()
        else:
            analysis_end_time = completed_at
    else:
        analysis_end_time = completed_at

    print(f"  Mode: {mode}")
    print(f"  Experiment: {exp_name}")
    print(f"  Time window: {started_at} → {analysis_end_time}")
    print(f"  Instances: {len(instance_ids)}")
    print(f"  Timeline events: {len(instance_timeline)}")
    if mode == "real-time":
        print(f"  (Real-time mode: instance_timeline not available until experiment completes)")

    # Step 2: Identify affected services (single batch API call for all instances)
    print(f"\n[2/5] Identifying affected services ...")
    if args.dry_run:
        print("  [DRY RUN] Skipping instance endpoint query")
        endpoints = {iid: {"id": iid, "private_ips": [], "private_dns": "", "eip": ""} for iid in instance_ids}
    else:
        endpoints = get_instance_endpoints(instance_ids, region)
        # Print endpoint summary (local iteration over pre-fetched data)
        for sid, info in endpoints.items():
            ips = ", ".join(info.get("private_ips", []))
            print(f"  {sid}: IPs=[{ips}], DNS={info.get('private_dns','')}")


    # Step 3: Collect CES monitoring metrics
    print(f"\n[3/5] Collecting CES monitoring metrics ...")

    ces_metrics = {}
    ces_summary = {}
    if args.dry_run:
        print("  [DRY RUN] Skipping CES metric collection")
    else:
        ces_metrics = collect_ces_metrics(
            instance_ids, started_at, analysis_end_time, region
        )
        # Print metric summary
        for iid, metric_list in ces_metrics.items():
            for m in metric_list:
                dp_count = len(m.get("datapoints", []))
                status = "OK" if m.get("success") else "FAILED"
                print(f"  [{status}] {m['label']} ({m['namespace']}/{m['metric_name']}): "
                      f"{dp_count} datapoints")
        # Summarize by phase (pre-shutdown / during-shutdown / post-recovery)
        ces_summary = summarize_ces_metrics(ces_metrics, instance_timeline)

    # Step 3: Collect logs — explicit LTS group + stream
    print(f"\n[4/5] Collecting logs ...")
    all_logs = []
    lts_sources = []
    if args.dry_run:
        print("  [DRY RUN] Skipping log collection")
    else:
        # LTS logs (one API call per stream)
        print(f"  Querying LTS (group: {args.log_group_id}) ...")
        lts_result = collect_lts_logs(
            args.log_group_id, args.log_stream_id,
            started_at, analysis_end_time, args.keywords, region
        )
        print(f"  LTS: {lts_result.get('count', 0)} entries")
        all_logs.extend(lts_result.get("logs", []))
        lts_sources.append({
            "log_group_id": args.log_group_id,
            "log_group_name": "",
            "log_stream_id": args.log_stream_id,
            "stream_name": "", "stream_type": "",
            "count": lts_result.get("count", 0),
            "keywords": args.keywords,
        })

    print(f"  Total log entries (pattern analysis): {len(all_logs)}")

    # Step 4: Analyze error patterns (pure local processing)
    print(f"\n[5/5] Analyzing error patterns ...")
    analysis = analyze_log_entries(all_logs, instance_timeline)

    print(f"  Total errors: {analysis['total_errors']}")
    print(f"  By severity: {analysis['by_severity']}")
    print(f"  By pattern: {analysis['by_pattern']}")

    # Build final result
    result = {
        "analysis_timestamp": now_iso(),
        "mode": mode,
        "experiment_name": exp_name,
        "region": region,
        "time_window": {"start": started_at, "end": analysis_end_time},
        "affected_instances": instance_ids,
        "instance_endpoints": endpoints,
        "log_analysis": analysis,
        "lts_sources": lts_sources,
        "ces_metrics": ces_metrics,
        "ces_summary": ces_summary,
        "instance_timeline": instance_timeline,
        "dry_run": args.dry_run,
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)

    # Write output
    output_path = args.output_file
    if not output_path and args.experiment_dir:
        output_path = os.path.join(args.experiment_dir, "log-analysis-result.json")
    if output_path:
        with open(output_path, "w") as f:
            f.write(output)
        print(f"\nAnalysis result written to: {output_path}")

    print(f"\n{'='*60}")
    print(f"  Analysis complete ({mode} mode). Errors found: {analysis['total_errors']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()