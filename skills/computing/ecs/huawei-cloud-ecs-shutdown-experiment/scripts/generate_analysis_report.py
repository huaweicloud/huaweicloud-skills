#!/usr/bin/env python3
"""
generate_analysis_report.py — Generate Markdown analysis report from analysis results.

This script reads a pre-generated JSON result file and produces a Markdown report.
No network calls are made — all data is processed locally from the input file.

Usage:
    python3 generate_analysis_report.py --result-file ./log-analysis-result.json
    python3 generate_analysis_report.py --result-file ./xxx.json --output report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime


def format_ts(ts):
    """Format an ISO timestamp for display (pure local operation)."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        return ts


def format_dur(s):
    if s is None:
        return "—"
    return f"{int(s)}s"


def generate_report(result):
    """Generate Markdown report from analysis result data.
    All processing is local — reads from pre-loaded result dict, no network calls.
    """
    exp_name = result.get("experiment_name", "unnamed")
    region = result.get("region", "unknown")
    tw = result.get("time_window", {})
    instances = result.get("affected_instances", [])
    endpoints = result.get("instance_endpoints", {})
    log_analysis = result.get("log_analysis", {})
    timeline = result.get("instance_timeline", [])
    dry_run = result.get("dry_run", False)

    # Pre-compute instance list lines (local batch processing)
    inst_lines = [
        f"  - `{iid}` — IP: {', '.join(endpoints.get(iid, {}).get('private_ips', [])) or '—'}"
        for iid in instances
    ]
    inst_section = "\n".join(inst_lines) if inst_lines else "  —"

    # Pre-compute error pattern stats (local batch processing)
    by_pattern = log_analysis.get("by_pattern", {})
    by_severity = log_analysis.get("by_severity", {})
    events = log_analysis.get("events", [])
    total_errors = log_analysis.get("total_errors", 0)
    high_errors = by_severity.get("high", 0)
    error_dur = log_analysis.get("error_duration_seconds")
    recovery_time = log_analysis.get("recovery_time_seconds")

    pattern_labels = {
        "error": "ERROR/Exception", "connection_refused": "Connection refused",
        "timeout": "Timeout", "http_5xx": "HTTP 5xx",
        "reconnect": "Reconnect attempt", "degrade": "Degrade/Circuit breaker", "recovery": "Recovery",
    }
    if by_pattern:
        pattern_rows = "".join(
            f"| {pattern_labels.get(pname, pname)} | {count} |\n"
            for pname, count in sorted(by_pattern.items(), key=lambda x: -x[1])
        )
    else:
        pattern_rows = "| — | 0 |\n"

    # Pre-compute LTS source rows (local)
    lts_sources = result.get("lts_sources", [])
    if lts_sources:
        lts_rows = "".join(
            f"| {s.get('log_group_name') or s.get('log_group_id','')} "
            f"| {s.get('stream_name') or s.get('log_stream_id') or '—'} "
            f"| {s.get('stream_type') or '—'} | {s.get('count', 0)} "
            f"| {s.get('keywords') if s.get('keywords') else 'raw'} |\n"
            for s in lts_sources
        )
    else:
        lts_rows = "| — | — | — | — | — |\n"

    # Pre-compute error timeline rows (local, top 20)
    if events:
        timeline_rows = "".join(
            f"| {format_ts(ev.get('timestamp',''))} | {ev.get('label','')} "
            f"| {ev.get('severity','')} | {ev.get('message','')[:80]} |\n"
            for ev in events[:20]
        )
    else:
        timeline_rows = "| — | — | — | — |\n"

    # Pre-compute instance state timeline rows (local, top 20)
    if timeline:
        inst_tl_rows = "".join(
            f"| {format_ts(ev.get('timestamp',''))} | {ev.get('instance_id','')} "
            f"| {ev.get('old_status','—')} | {ev.get('new_status','—')} |\n"
            for ev in timeline[:20]
        )
    else:
        inst_tl_rows = "| — | — | — | — |\n"


    # Pre-compute CES metrics section (local processing from pre-collected data)
    ces_summary = result.get("ces_summary", {})
    if ces_summary:
        ces_rows = ""
        ces_observation_lines = ""
        for iid, summary in ces_summary.items():
            metrics = summary.get("metrics", [])
            observations = summary.get("observations", [])
            if not metrics:
                ces_rows += f"| _{iid}_ | — | — | — | — | — |\n"
                continue
            for m in metrics:
                label = m.get("label", m.get("metric_name", "—"))
                phases = m.get("phases")
                unit = m.get("unit", "") or ""
                if phases:
                    pre_avg = phases.get("pre_shutdown", {}).get("average")
                    during_min = phases.get("during_shutdown", {}).get("min")
                    during_avg = phases.get("during_shutdown", {}).get("average")
                    post_avg = phases.get("post_recovery", {}).get("average")
                    pre_str = f"{pre_avg} {unit}" if pre_avg is not None else "—"
                    if during_min is not None:
                        during_str = f"{during_min} {unit}" if during_min is not None else "—"
                    elif during_avg is not None:
                        during_str = f"{during_avg} {unit}"
                    else:
                        during_str = "No data"
                    post_str = f"{post_avg} {unit}" if post_avg is not None else "—"
                    ns = m.get("namespace", "")
                    ns_tag = f" (AGT)" if ns == "AGT.ECS" else ""
                    ces_rows += f"| {label}{ns_tag} | {pre_str} | {during_str} | {post_str} |\n"
                else:
                    err = m.get("error", "")
                    if err:
                        ces_rows += f"| {label} | Collection failed | — | — |\n"
                    else:
                        ces_rows += f"| {label} | No data | — | — |\n"
            for obs in observations:
                ces_observation_lines += f"- {obs}\n"
        if not ces_observation_lines:
            ces_observation_lines = "—\n"
    else:
        ces_rows = "| — | — | — | — |\n"
        ces_observation_lines = "CES metric data unavailable (experiment may be in dry-run mode or CES API unreachable)\n"

    # Assessment
    if total_errors == 0:
        assessment = "**Application not significantly affected.** No obvious error logs detected during the experiment.\n\nPossible reasons: the application has fault tolerance, does not directly depend on the stopped instance, or log collection is incomplete."
    elif high_errors == 0:
        assessment = f"**Application mildly affected.** Detected {total_errors} non-severe events (reconnect, degrade, etc.); the application likely recovered automatically."
    else:
        assessment = f"**Application significantly affected.** Detected {total_errors} log events, {high_errors} of high severity."
        if error_dur is not None:
            assessment += f"\n- Error duration: {format_dur(error_dur)}"
        if recovery_time is not None:
            assessment += f"\n- Recovery time: {format_dur(recovery_time)}"

    # Suggestions
    suggestions = []
    if high_errors > 0:
        suggestions.append("Analyze error root causes; verify the application has retry/circuit-breaker mechanisms")
        suggestions.append("Consider cross-AZ deployment or primary/standby failover capability")
    if by_pattern.get("connection_refused", 0) > 0:
        suggestions.append("High connection-refused count; consider connection-pool retry policies and health checks")
    if by_pattern.get("timeout", 0) > 0:
        suggestions.append("High timeout count; consider optimizing timeout configuration and degradation strategy")
    if total_errors == 0:
        suggestions.append("Verify log collection completeness (LTS log group configuration covers target instances)")
    suggestions.append("Combine CES monitoring metrics for an overall application assessment")

    report = f"""# ECS Shutdown Fault Injection Experiment — Log Analysis Report

## Experiment Overview

| Item | Value |
|---|---|
| Experiment name | {exp_name} |
| Region | {region} |
| Analysis time window | {format_ts(tw.get('start',''))} → {format_ts(tw.get('end',''))} |
| Target instances | {len(instances)} |
| Total log events | {log_analysis.get('total_logs', 0)} |
| Error events | {total_errors} |
| Dry Run | {'Yes' if dry_run else 'No'} |

## Affected Instances

{inst_section}

## LTS Log Sources

| Log group | Stream | Type | Entries | Keywords |
|---|---|---|---|---|
{lts_rows}

## Instance State Timeline

| Time | Instance ID | Old status | New status |
|---|---|---|---|
{inst_tl_rows}

## CES Metrics

| Metric | Pre-shutdown (avg) | During-shutdown (min) | Post-recovery (avg) |
|---|---|---|---|
{ces_rows}

### Key Observations

{ces_observation_lines}

## Error Pattern Statistics

| Pattern | Count |
|---|---|
{pattern_rows}

**By severity**: high={by_severity.get('high',0)}, medium={by_severity.get('medium',0)}, info={by_severity.get('info',0)}

## Error Event Timeline (top 20)

| Time | Pattern | Severity | Message summary |
|---|---|---|---|
{timeline_rows}

## Application Behavior Assessment

{assessment}

## Improvement Suggestions

"""
    for i, s in enumerate(suggestions, 1):
        report += f"{i}. {s}\n"

    report += f"""
---
*Report generated at: {format_ts(datetime.now().astimezone().isoformat())}*
"""
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate Markdown analysis report from log analysis result."
    )
    parser.add_argument("--result-file", required=True, help="Path to log-analysis-result.json")
    parser.add_argument("--output", help="Output report file path")
    args = parser.parse_args()

    if not os.path.exists(args.result_file):
        print(f"Error: result file not found: {args.result_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.result_file) as f:
        result = json.load(f)

    report = generate_report(result)

    output_path = args.output
    if not output_path:
        result_dir = os.path.dirname(args.result_file)
        output_path = os.path.join(result_dir, "log-analysis-report.md")

    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()