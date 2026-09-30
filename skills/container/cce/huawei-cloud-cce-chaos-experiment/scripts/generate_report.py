#!/usr/bin/env python3
"""
Generate Markdown execution report from execution-log.json (Phase 2 output).

Includes a recommendation to proceed to Phase 3 (log analysis) using
the same skill's analyze_logs.py and generate_analysis_report.py scripts.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def format_time(iso_str):
    """Format ISO timestamp to readable string."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return iso_str


def format_duration(seconds):
    """Format seconds as Xm Ys."""
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def main():
    parser = argparse.ArgumentParser(description="Generate execution report")
    parser.add_argument("--log-file", required=True, help="Path to execution-log.json")
    parser.add_argument("--output", help="Output report path (default: same dir as log)")
    args = parser.parse_args()

    with open(args.log_file) as f:
        log = json.load(f)

    exp_name = log.get("experiment_name", "unknown")
    region = log.get("region", "cn-north-4")
    target_az = log.get("az", "")
    started_at = log.get("started_at", "")
    completed_at = log.get("completed_at", "")
    total_duration = log.get("total_duration_seconds", 0)
    overall_result = log.get("overall_result", "unknown")
    phases = log.get("phases", {})
    node_timeline = log.get("node_timeline", [])
    pod_timeline = log.get("pod_timeline", [])
    rescheduling_events = log.get("rescheduling_events", [])

    result_emoji = "PASS" if overall_result == "success" else "FAIL"

    report = f"""# CCE AZ Power Outage Drill — Execution Report

## Experiment Overview

| Item | Value |
|---|---|
| Experiment name | {exp_name} |
| Region | {region} |
| Target AZ | {target_az} |
| Started at | {format_time(started_at)} |
| Completed at | {format_time(completed_at)} |
| Total duration | {format_duration(total_duration)} |
| Result | {result_emoji} {overall_result} |

## Execution Phase Timeline

| Phase | Started | Completed | Elapsed | Result |
|---|---|---|---|---|
"""

    phase_labels = {
        "pre_check": "Pre-check",
        "shutdown": "Fault injection (shutdown)",
        "monitor": "Monitor shutdown",
        "wait": "Wait (duration)",
        "rollback": "Rollback (startup)",
        "verify": "Verify recovery",
    }

    for phase_key in ["pre_check", "shutdown", "monitor", "wait", "rollback", "verify"]:
        phase = phases.get(phase_key, {})
        label = phase_labels.get(phase_key, phase_key)
        p_start = format_time(phase.get("started_at", ""))
        p_end = format_time(phase.get("completed_at", ""))
        elapsed = phase.get("elapsed_seconds", phase.get("duration", "—"))
        if isinstance(elapsed, int) and elapsed > 0:
            elapsed_str = format_duration(elapsed)
        else:
            elapsed_str = "—"
        result = phase.get("result", "—")
        report += f"| {label} | {p_start} | {p_end} | {elapsed_str} | {result} |\n"

    # Node timeline
    report += f"""
## Node Status Change Timeline

| Time | Node | Old Status | New Status |
|---|---|---|---|
"""
    if node_timeline:
        for event in node_timeline:
            report += f"| {format_time(event['timestamp'])} | {event['node']} | {event['old_status']} | {event['new_status']} |\n"
    else:
        report += "| — | — | — | — |\n"

    # Pod timeline
    report += f"""
## Pod Status Change Timeline

| Time | Pod | Old Phase | New Phase |
|---|---|---|---|
"""
    if pod_timeline:
        for event in pod_timeline[:50]:  # Limit to 50 events
            report += f"| {format_time(event['timestamp'])} | {event['pod']} | {event['old_phase']} | {event['new_phase']} |\n"
        if len(pod_timeline) > 50:
            report += f"| ... | ({len(pod_timeline) - 50} more events) | ... | ... |\n"
    else:
        report += "| — | — | — | — |\n"

    # Rescheduling events
    report += f"""
## Pod Rescheduling Records

| Time | Pod | Event |
|---|---|---|
"""
    if rescheduling_events:
        for event in rescheduling_events:
            report += f"| {format_time(event['timestamp'])} | {event['pod']} | {event['event']} |\n"
    else:
        report += "| — | — | — |\n"

    report += f"""
## Conclusion and Recommendations

**Experiment {'completed successfully' if overall_result == 'success' else 'execution failed'}.**

{'All target nodes were shut down and successfully recovered after the specified duration. Pods were rescheduled to nodes in other AZs.' if overall_result == 'success' else 'Please check the failure cause and perform manual rollback.'}

Recommendations:
- Check business system availability metrics during the experiment to confirm whether resilience targets were met
- Analyze Pod rescheduling time to evaluate RTO
- Check whether cross-AZ replica distribution is balanced
- If business was impacted, consider optimizing PDB configuration or increasing cross-AZ replica count

## Log Analysis Recommendation

> Experiment execution is complete. It is recommended to proceed with Phase 3 (log analysis) for deeper insights.

### Usage

Invoke the Phase 3 analysis scripts from this skill directly:

```bash
# Automated orchestration: collect logs + analyze error patterns + generate report
python3 scripts/analyze_logs.py --experiment-dir {os.path.dirname(args.log_file)}

# Or run step by step
python3 scripts/collect_logs.py --output-dir collected_logs \\
    --since <start_time> --until <end_time> --pods <pod_list>
python3 scripts/generate_analysis_report.py \\
    --analysis analysis-result.json \\
    --context execution-log.json \\
    --output analysis-report.md
```

### Complete Workflow

```
huawei-cloud-cce-chaos-experiment (unified skill)
  Phase 1: Prepare (discover + validate + generate experiment.json)
  Phase 2: Execute (shutdown -> monitor -> wait -> rollback -> verify)  <-- current phase complete
  Phase 3: Log Analysis (collect logs + analyze events + generate report)  <-- recommended next step
```

---
*Report generated at: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}*
"""

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(os.path.dirname(args.log_file), "execution-report.md")

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()
