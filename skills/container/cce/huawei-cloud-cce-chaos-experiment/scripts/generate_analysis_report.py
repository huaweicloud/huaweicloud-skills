#!/usr/bin/env python3
"""
Generate CCE AZ power outage experiment log analysis report (Markdown).

Based on analysis-result.json + execution-log.json + collected Events,
generates a comprehensive report including Pod rescheduling timeline,
error pattern statistics, and business impact assessment.
"""

import json
import os
import sys
import argparse
from datetime import datetime


def generate_report(analysis_path, context_path, output_path):
    """Generate Markdown analysis report."""
    with open(analysis_path) as f:
        analysis = json.load(f)

    context = {}
    if os.path.exists(context_path):
        with open(context_path) as f:
            context = json.load(f)

    lines = []
    lines.append("# CCE AZ Power Outage Experiment — Log Analysis Report\n")
    lines.append(f"**Generated at**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # -- 1. Experiment Overview --
    lines.append("## 1. Experiment Overview\n")
    lines.append(f"- **Experiment name**: {analysis.get('experiment_name', 'N/A')}")
    lines.append(f"- **Analysis mode**: {analysis.get('mode', 'N/A')}")
    tw = analysis.get("time_window", {})
    lines.append(f"- **Time window**: {tw.get('start', 'N/A')} ~ {tw.get('end', 'N/A')}")
    lines.append(f"- **Affected nodes**: {len(analysis.get('affected_nodes', []))}")
    lines.append(f"- **Affected Pods**: {len(analysis.get('affected_pods', []))}")
    lines.append("")

    # -- 2. Affected Resources --
    lines.append("## 2. Affected Resources\n")
    nodes = analysis.get("affected_nodes", [])
    if nodes:
        lines.append("### Affected Nodes")
        for n in nodes:
            lines.append(f"- {n}")
        lines.append("")
    pods = analysis.get("affected_pods", [])
    if pods:
        lines.append("### Affected Pods")
        for p in pods:
            lines.append(f"- {p}")
        lines.append("")

    # -- 3. Pod Rescheduling Timeline --
    # Fix: execution-log.json uses old_phase/new_phase (not old_status/new_status/new_node)
    lines.append("## 3. Pod Rescheduling Timeline\n")
    pod_timeline = context.get("pod_timeline", [])
    if pod_timeline:
        lines.append("| Time | Pod | Namespace | Old Phase | New Phase |")
        lines.append("|------|-----|-----------|-----------|-----------|")
        for event in pod_timeline:
            timestamp = event.get("timestamp", "")
            pod_full = event.get("pod", "")
            # pod field may be "namespace/podname" or just "podname"
            if "/" in pod_full:
                ns, pod_name = pod_full.split("/", 1)
            else:
                ns = event.get("namespace", "")
                pod_name = pod_full
            old_phase = event.get("old_phase", event.get("old_status", ""))
            new_phase = event.get("new_phase", event.get("new_status", ""))
            lines.append(f"| {timestamp} | {pod_name} | {ns} | {old_phase} | {new_phase} |")
        lines.append("")
    else:
        lines.append("No Pod rescheduling records found.\n")

    # -- 4. Node Status Timeline --
    node_timeline = context.get("node_timeline", [])
    if node_timeline:
        lines.append("## 4. Node Status Changes\n")
        lines.append("| Time | Node | Old Status | New Status |")
        lines.append("|------|------|------------|------------|")
        for event in node_timeline:
            lines.append(
                f"| {event.get('timestamp', '')} | {event.get('node', '')} "
                f"| {event.get('old_status', event.get('old_phase', ''))} "
                f"| {event.get('new_status', event.get('new_phase', ''))} |"
            )
        lines.append("")

    # -- 5. Error Pattern Statistics --
    lines.append("## 5. Error Pattern Statistics\n")
    error_patterns = analysis.get("error_patterns", {})
    total_log_lines = analysis.get("total_log_lines", 0)
    total_errors = analysis.get("total_errors", 0)
    lines.append(f"- **Total log lines**: {total_log_lines}")
    lines.append(f"- **Total error/exception events**: {total_errors}")
    lines.append("")
    lines.append("| Error Pattern | Occurrences |")
    lines.append("|---------------|-------------|")
    for pattern, count in error_patterns.items():
        if count and count > 0:
            lines.append(f"| {pattern} | {count} |")
    lines.append("")

    # -- 6. Business Impact Assessment --
    # Fix: don't just check total_errors==0 — also analyze Kubernetes Events
    # for scheduling failures, evictions, and node state changes
    lines.append("## 6. Business Impact Assessment\n")

    # Count K8s event types from error_patterns
    failed_scheduling = error_patterns.get("FailedScheduling", 0)
    evictions = error_patterns.get("TaintManagerEviction", 0)
    node_not_ready = error_patterns.get("NodeNotReady", 0)
    pod_restarts = analysis.get("pod_restarts", {})
    pending_pods = analysis.get("pending_pods_after_experiment", 0)
    impact = analysis.get("impact_summary", {})

    if total_errors == 0 and failed_scheduling == 0 and evictions == 0 and not impact:
        lines.append("No application error logs were detected during this experiment. "
                     "The application remained stable throughout node failure and Pod rescheduling.\n")
    else:
        # Detailed impact assessment based on K8s events
        if failed_scheduling:
            lines.append(f"- Warning: **Scheduling failures**: {failed_scheduling} FailedScheduling events — "
                         f"surviving node resources insufficient to schedule all rescheduled Pods")
        if evictions:
            lines.append(f"- Info: **Pod evictions**: {evictions} TaintManagerEviction events — "
                         f"normal Kubernetes taint-based eviction mechanism")
        if node_not_ready:
            lines.append(f"- Info: **Node unreachable**: {node_not_ready} Pods affected by NodeNotReady")
        if pod_restarts:
            lines.append(f"- Warning: **Pod restarts**: {len(pod_restarts)} Pods restarted after node recovery")
        if pending_pods:
            lines.append(f"- Warning: **Residual Pending Pods**: {pending_pods} Pods still in Pending state after experiment")
        if impact:
            lines.append("")
            lines.append("### Per-Service Impact")
            for service, desc in impact.items():
                lines.append(f"- **{service}**: {desc}")
        lines.append("")

    # -- 7. Improvement Recommendations --
    lines.append("## 7. Improvement Recommendations\n")
    if total_errors == 0 and failed_scheduling == 0 and not impact:
        lines.append("- The application demonstrates good fault tolerance; no additional improvements needed")
        lines.append("- Recommend running chaos experiments periodically to verify application resilience")
    else:
        if failed_scheduling:
            lines.append("- **Scale nodes or optimize resource quotas**: Insufficient resources on surviving nodes "
                         "prevented Pod scheduling. Consider increasing node size/count or reducing system component resource requests")
        lines.append("- **Increase replicas for critical components**: Single-replica components are fully disrupted "
                     "during node failure; recommend at least 2 replicas")
        lines.append("- **Configure Pod anti-affinity**: Use `topologyKey: topology.kubernetes.io/zone` "
                     "to ensure replicas are distributed across different AZs")
        lines.append("- **Configure PDB**: Set up PodDisruptionBudget for critical services")
        if pending_pods:
            lines.append(f"- **Clean up residual Pending Pods**: {pending_pods} Pending Pods need manual cleanup after experiment")
        lines.append("- **Deploy LTS log collection**: Configure log policies in CCE to deliver Pod logs to LTS "
                     "for complete container log access after failures")
        lines.append("- Recommend running chaos experiments periodically to verify application resilience")
    lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Analysis report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate log analysis report")
    parser.add_argument("--analysis", required=True, help="Path to analysis-result.json")
    parser.add_argument("--context", required=True,
                        help="Path to execution-log.json or experiment.json")
    parser.add_argument("--output", default="analysis-report.md", help="Output report path")
    args = parser.parse_args()
    generate_report(args.analysis, args.context, args.output)


if __name__ == "__main__":
    main()
