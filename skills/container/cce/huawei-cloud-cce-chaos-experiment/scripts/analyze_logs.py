#!/usr/bin/env python3
"""
CCE AZ power outage experiment log analysis main script.
Auto-detects real-time/post-hoc mode and orchestrates the full analysis workflow.
"""

import json
import os
import sys
import subprocess
import argparse
from datetime import datetime, timezone


# Only pass required environment variables to subprocess (avoid bulk env harvesting)
_ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL",
    "HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_REGION_NAME",
    "KUBECONFIG",
)


def _build_env(region=None):
    """Build a minimal environment dict with only needed variables."""
    env = {k: os.environ[k] for k in _ENV_WHITELIST if k in os.environ}
    if region and "HW_REGION_NAME" not in env:
        env["HW_REGION_NAME"] = region
    return env


def load_experiment_context(execution_log_path, experiment_path):
    """Load experiment context, auto-detecting analysis mode."""
    if os.path.exists(execution_log_path):
        with open(execution_log_path) as f:
            data = json.load(f)
        return data, "post-hoc"
    elif os.path.exists(experiment_path):
        with open(experiment_path) as f:
            data = json.load(f)
        return data, "realtime"
    else:
        print(f"[ERROR] Neither execution-log.json nor experiment.json found")
        print(f"  Tried paths: {execution_log_path}, {experiment_path}")
        sys.exit(1)


def extract_time_window(context, mode):
    """Extract experiment time window.

    Supports both field naming conventions:
    - execution-log.json: started_at / completed_at
    - experiment.json (legacy): start_time / end_time
    """
    if mode == "post-hoc":
        start = context.get("start_time") or context.get("started_at")
        end = context.get("end_time") or context.get("completed_at")
        return start, end
    else:
        now = datetime.now(timezone.utc).isoformat()
        return None, now


def get_affected_nodes(context):
    """Get affected node list.

    Extracts node names from multiple possible locations:
    - node_timeline entries (from execution-log.json)
    - targets.nodes[].name (from experiment.json)
    - targets.node_ids (legacy format)
    """
    # Try node_timeline first (execution-log.json)
    nodes = set()
    for event in context.get("node_timeline", []):
        node = event.get("node") or event.get("name")
        if node:
            nodes.add(node)
    if nodes:
        return list(nodes)

    # Try targets.nodes[].name (experiment.json)
    targets = context.get("targets", {})
    if isinstance(targets, dict):
        node_list = targets.get("nodes", [])
        if isinstance(node_list, list):
            for n in node_list:
                name = n.get("name") if isinstance(n, dict) else None
                if name:
                    nodes.add(name)
        if nodes:
            return list(nodes)
        # Legacy format
        return targets.get("node_ids", [])
    elif isinstance(targets, list):
        return targets
    return []


def get_affected_pods(context):
    """Get affected Pod list from pod_timeline."""
    pods = set()
    for event in context.get("pod_timeline", []):
        pod = event.get("pod")
        ns = event.get("namespace", "default")
        if pod:
            pods.add(f"{ns}/{pod}")
    return list(pods)


def analyze_error_patterns(log_lines):
    """Analyze error patterns in log lines."""
    patterns = {
        "ERROR": [],
        "Exception": [],
        "Connection refused": [],
        "Timeout": [],
        "5xx HTTP": [],
        "Reconnect": [],
        "Degraded": [],
        "Recovered": [],
    }
    for line in log_lines:
        lower = line.lower()
        if "error" in lower:
            patterns["ERROR"].append(line)
        if "exception" in lower or "stacktrace" in lower:
            patterns["Exception"].append(line)
        if "connection refused" in lower or "connect: connection refused" in lower:
            patterns["Connection refused"].append(line)
        if "timeout" in lower or "deadline exceeded" in lower:
            patterns["Timeout"].append(line)
        if " 500 " in line or " 502 " in line or " 503 " in line or " 504 " in line:
            patterns["5xx HTTP"].append(line)
        if "reconnect" in lower or "reconnected" in lower:
            patterns["Reconnect"].append(line)
        if "degrad" in lower:
            patterns["Degraded"].append(line)
        if "recover" in lower or "restored" in lower:
            patterns["Recovered"].append(line)
    return patterns


def read_logs_recursively(log_dir):
    """Recursively read all files in a log directory (including subdirectories like pods/, lts/).

    Fix: The original implementation only traversed top-level isfile() files,
    missing log files created by collect_logs.py in pods/ and lts/ subdirectories.
    """
    all_logs = []
    if not os.path.exists(log_dir):
        return all_logs
    for root, dirs, files in os.walk(log_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, errors="replace") as f:
                        all_logs.extend(f.read().splitlines())
                except Exception:
                    continue
    return all_logs


def analyze_k8s_events(events_file):
    """Analyze Kubernetes Events, extracting scheduling failures, evictions, node state changes, etc.

    Returns a dict of event_type -> count, plus pod restart info.
    """
    event_counts = {
        "FailedScheduling": 0,
        "TaintManagerEviction": 0,
        "NodeNotReady": 0,
        "NodeReady": 0,
    }
    if not events_file or not os.path.exists(events_file):
        return event_counts, {}, 0

    try:
        with open(events_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return event_counts, {}, 0

    items = data.get("items", [])
    for event in items:
        reason = event.get("reason", "")
        if reason in event_counts:
            event_counts[reason] += 1

    return event_counts, {}, len(items)


def count_pod_restarts_and_pending():
    """Count Pod restarts and pending Pods."""
    import subprocess
    restarts = {}
    pending_count = 0

    env = _build_env()
    if "KUBECONFIG" not in env and os.path.exists(os.path.expanduser("~/.kube/config")):
        env["KUBECONFIG"] = os.path.expanduser("~/.kube/config")

    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
            capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode != 0:
            return restarts, pending_count
        data = json.loads(result.stdout)
        for pod in data.get("items", []):
            ns = pod["metadata"]["namespace"]
            name = pod["metadata"]["name"]
            phase = pod.get("status", {}).get("phase", "")
            if phase == "Pending":
                pending_count += 1
            for cs in pod.get("status", {}).get("containerStatuses", []):
                rc = cs.get("restartCount", 0)
                if rc > 0:
                    restarts[f"{ns}/{name}"] = rc
    except Exception:
        pass

    return restarts, pending_count


def run_analysis(experiment_dir, output_dir):
    """Run the full analysis workflow."""
    execution_log_path = os.path.join(experiment_dir, "execution-log.json")
    experiment_path = os.path.join(experiment_dir, "experiment.json")

    # Step 1: Load context
    print("[1/5] Loading experiment context...")
    context, mode = load_experiment_context(execution_log_path, experiment_path)
    print(f"  Mode: {mode}")
    print(f"  Experiment name: {context.get('experiment_name', 'unknown')}")

    # Step 2: Extract time window and affected resources
    print("[2/5] Extracting time window and affected resources...")
    start_time, end_time = extract_time_window(context, mode)
    affected_nodes = get_affected_nodes(context)
    affected_pods = get_affected_pods(context)
    print(f"  Time window: {start_time} ~ {end_time}")
    print(f"  Affected nodes: {len(affected_nodes)}")
    print(f"  Affected Pods: {len(affected_pods)}")

    # Step 3: Discover service dependencies
    print("[3/5] Discovering service dependencies...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dep_script = os.path.join(script_dir, "discover_dependencies.py")
    dep_output = os.path.join(output_dir, "dependencies.json")
    if os.path.exists(dep_script):
        cmd = ["python3", dep_script, "--output", dep_output]
        if affected_nodes:
            cmd.extend(["--nodes", ",".join(affected_nodes)])
        subprocess.run(cmd, check=False, env=_build_env())
    else:
        print("  [WARN] discover_dependencies.py not found, skipping")

    # Step 4: Collect logs
    print("[4/5] Collecting logs...")
    collect_script = os.path.join(script_dir, "collect_logs.py")
    logs_output = os.path.join(output_dir, "collected_logs")
    if os.path.exists(collect_script):
        cmd = ["python3", collect_script, "--output-dir", logs_output]
        if start_time:
            cmd.extend(["--since", start_time])
        if end_time:
            cmd.extend(["--until", end_time])
        if affected_pods:
            cmd.extend(["--pods", ",".join(affected_pods)])
        subprocess.run(cmd, check=False, env=_build_env())
    else:
        print("  [WARN] collect_logs.py not found, skipping")

    # Step 5: Analyze error patterns + Kubernetes Events
    print("[5/5] Analyzing error patterns and Kubernetes Events...")

    # 5a: Recursively read all collected log files (including pods/ and lts/ subdirectories)
    all_logs = read_logs_recursively(logs_output)
    error_patterns = analyze_error_patterns(all_logs)
    total_errors = sum(len(v) for k, v in error_patterns.items() if k != "Recovered")
    print(f"  Total container log lines: {len(all_logs)}")
    print(f"  Container log errors: {total_errors}")
    for pattern, matches in error_patterns.items():
        if matches:
            print(f"    {pattern}: {len(matches)} matches")

    # 5b: Analyze Kubernetes Events
    events_file = os.path.join(logs_output, "k8s_events.json")
    k8s_event_counts, _, total_events = analyze_k8s_events(events_file)
    if total_events > 0:
        print(f"  Kubernetes Events: {total_events} entries")
        for evt_type, count in k8s_event_counts.items():
            if count > 0:
                print(f"    {evt_type}: {count}")

    # 5c: Count Pod restarts and pending Pods
    pod_restarts, pending_pods = count_pod_restarts_and_pending()
    if pod_restarts:
        print(f"  Pod restarts: {len(pod_restarts)} Pods")
    if pending_pods:
        print(f"  Pending Pods: {pending_pods}")

    # Merge error patterns: container log errors + K8s Events
    combined_patterns = {k: len(v) for k, v in error_patterns.items()}
    combined_patterns.update(k8s_event_counts)
    combined_total = total_errors + sum(k8s_event_counts.values())

    # Save analysis result
    analysis_result = {
        "mode": mode,
        "experiment_name": context.get("experiment_name"),
        "time_window": {"start": start_time, "end": end_time},
        "affected_nodes": affected_nodes,
        "affected_pods": affected_pods,
        "error_patterns": combined_patterns,
        "total_log_lines": len(all_logs),
        "total_errors": combined_total,
        "pod_restarts": pod_restarts,
        "pending_pods_after_experiment": pending_pods,
    }
    result_path = os.path.join(output_dir, "analysis-result.json")
    with open(result_path, "w") as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    print(f"\nAnalysis result saved: {result_path}")

    # Generate report
    report_script = os.path.join(script_dir, "generate_analysis_report.py")
    if os.path.exists(report_script):
        print("\nGenerating analysis report...")
        subprocess.run([
            "python3", report_script,
            "--analysis", result_path,
            "--context", execution_log_path if os.path.exists(execution_log_path) else experiment_path,
            "--output", os.path.join(output_dir, "analysis-report.md")
        ], check=False, env=_build_env())

    print("\n=== Log analysis complete ===")


def main():
    parser = argparse.ArgumentParser(description="CCE AZ power outage experiment log analysis")
    parser.add_argument("--experiment-dir", default=".", help="Experiment directory (containing execution-log.json or experiment.json)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: <experiment-dir>/log-analysis)")
    args = parser.parse_args()

    # Default: place analysis output inside the experiment directory
    if args.output_dir is None:
        args.output_dir = os.path.join(args.experiment_dir, "log-analysis")
    os.makedirs(args.output_dir, exist_ok=True)
    run_analysis(args.experiment_dir, args.output_dir)


if __name__ == "__main__":
    main()
