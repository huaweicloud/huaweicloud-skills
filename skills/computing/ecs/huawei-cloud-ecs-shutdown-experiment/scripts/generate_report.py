#!/usr/bin/env python3
"""
generate_report.py - Generate Markdown execution report from execution log.

Reads execution-log.json (produced by execute_experiment.py) and generates
a human-readable Markdown report with experiment overview, timeline, status
changes, and conclusions.

NOTE: This module performs NO network/API calls. All data comes from the
local JSON log file. All loops iterate over in-memory data structures only.

Usage:
    python3 generate_report.py --log-file ./experiments/xxx/execution-log.json
    python3 generate_report.py --log-file ./experiments/xxx/execution-log.json --output report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime


def format_duration(seconds):
    """Format seconds as 'Xm Ys'."""
    if seconds is None:
        return "-"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def format_timestamp(ts):
    """Format ISO timestamp for display."""
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        return ts


def generate_report(log):
    """Generate Markdown report from execution log.

    All data is read from the in-memory ``log`` dict (loaded from a local
    JSON file). The loops below iterate over local data only - no network
    or API calls are made anywhere in this module.
    """
    exp_name = log.get("experiment_name", "unnamed")
    region = log.get("region", "unknown")
    instance_ids = log.get("instance_ids", [])
    started = format_timestamp(log.get("started_at"))
    completed = format_timestamp(log.get("completed_at"))
    total_dur = log.get("total_duration_seconds")
    overall = log.get("overall_result", "unknown")
    dry_run = log.get("dry_run", False)
    phases = log.get("phases", {})
    timeline = log.get("instance_timeline", [])

    # Result emoji
    result_emoji = {
        "success": "✅",
        "dry_run_complete": "ℹ️",
        "failed_pre_check": "❌",
        "failed_shutdown": "❌",
        "failed_shutdown_auto_rollback": "❌",
        "failed_rollback": "❌",
        "failed_verify": "⚠️",
        "stopped_early": "⏹️",
    }.get(overall, "❓")

    # Phase summary table - local iteration over in-memory phases dict
    phase_rows = ""
    phase_names = {
        "pre_check": "Pre-check", "shutdown": "Shutdown", "monitor": "Monitor",
        "wait": "Wait", "rollback": "Rollback", "verify": "Verify"
    }
    # No network calls: iterates over local phase_names dict only
    for pk, label in phase_names.items():
        ph = phases.get(pk, {})
        result = ph.get("result", "-")
        elapsed = ph.get("elapsed", ph.get("duration"))
        phase_rows += f"| {label} | {format_timestamp(ph.get('started_at'))} | {format_timestamp(ph.get('completed_at'))} | {format_duration(elapsed) if elapsed else '-'} | {result} |\n"

    # Instance timeline table - local iteration over in-memory timeline list
    timeline_rows = ""
    # No network calls: iterates over local timeline list only
    for event in timeline:
        iid = event.get("instance_id", "-")
        ts = format_timestamp(event.get("timestamp"))
        old = event.get("old_status") or "-"
        new = event.get("new_status", "-")
        timeline_rows += f"| {ts} | {iid} | {old} | {new} |\n"
    if not timeline_rows:
        timeline_rows = "| - | - | - | - |\n"

    # Instance list - local iteration over in-memory instance_ids list
    inst_list = "\n".join(f"  - `{iid}`" for iid in instance_ids)

    report = f"""# ECS Shutdown Fault Injection Experiment - Execution Report

## Experiment Overview

| Field | Value |
|---|---|
| Experiment Name | {exp_name} |
| Region | {region} |
| Target Instances | {len(instance_ids)} |
| Started At | {started} |
| Completed At | {completed} |
| Total Duration | {format_duration(total_dur) if total_dur else '-'} |
| Result | {result_emoji} {overall} |
| Dry Run | {'Yes' if dry_run else 'No'} |

## Target Instances

{inst_list}

## Phase Timeline

| Phase | Started At | Completed At | Duration | Result |
|---|---|---|---|---|
{phase_rows}

## Instance State Changes

| Timestamp | Instance ID | Old Status | New Status |
|---|---|---|---|
{timeline_rows}

## Conclusion

"""

    # Conclusions
    if overall == "success":
        report += """**Experiment completed successfully.** All target instances were stopped and successfully recovered after the configured duration.

Recommendations:
- Check business availability metrics during the experiment to confirm resilience goals were met
- Analyze instance recovery time (from SHUTOFF to ACTIVE) to evaluate RTO
- If business was affected, consider adding cross-AZ redundancy or automatic failover
"""
    elif overall == "dry_run_complete":
        report += """**Dry run completed.** No API calls were made; only the experiment flow was validated.

Recommendations:
- After confirming the experiment configuration, remove `--dry-run` to run the real experiment
- Notify stakeholders and arrange monitoring coverage before executing
"""
    elif overall == "failed_pre_check":
        report += """**Pre-check failed.** Some target instances were not ACTIVE, so shutdown could not proceed.

Recommendations:
- Check instance status and confirm the instances are running
- Exclude abnormal instances or restore them to ACTIVE first
- Re-run the experiment
"""
    elif "failed_shutdown" in overall:
        report += """**Shutdown failed.** The BatchStopServers API call was not successful.

Recommendations:
- Check whether the hcloud CLI permission includes ECS BatchStopServers
- Check whether the instances are in a stoppable state (not migrating, no running task)
- If `--auto-rollback` was configured, instances should have auto-recovered; please verify
"""
    elif overall == "failed_rollback":
        report += """**⚠️ Rollback failed.** The BatchStartServers API call was not successful; instances may still be stopped.

Recommendations:
- Immediately run `hcloud ECS BatchStartServers` manually to start the instances
- Check whether instances entered ERROR state
- Contact the operations team to confirm instance status
"""
    elif overall == "failed_verify":
        report += """**⚠️ Verification failed.** Some instances did not recover to ACTIVE within the timeout.

Recommendations:
- Check the status and system logs of unrecovered instances
- Manual restart or operations team involvement may be required
- Analyze the startup delay causes (image size, startup scripts, system load, etc.)
"""
    else:
        report += f"**Experiment result: {overall}**\n\nCheck the execution log for details.\n"

    report += f"""
---
*Report generated at: {format_timestamp(datetime.now().astimezone().isoformat())}*
"""

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate Markdown execution report from execution log."
    )
    parser.add_argument("--log-file", required=True,
                        help="Path to execution-log.json")
    parser.add_argument("--output", help="Output report file path (default: alongside log file)")
    args = parser.parse_args()

    if not os.path.exists(args.log_file):
        print(f"Error: log file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.log_file) as f:
        log = json.load(f)

    report = generate_report(log)

    output_path = args.output
    if not output_path:
        log_dir = os.path.dirname(args.log_file)
        output_path = os.path.join(log_dir, "execution-report.md")

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()