#!/usr/bin/env python3
"""
Emergency rollback for CCE AZ power outage experiment.
Starts all target nodes and waits for recovery.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor_resources import get_node_statuses, get_pod_statuses


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def batch_start_servers(instance_ids, region):
    """Start ECS instances using native hcloud parameter format."""
    cmd = ["hcloud", "ECS", "BatchStartServers", f"--cli-region={region}", "--cli-output=json"]
    for i, iid in enumerate(instance_ids, 1):
        cmd.append(f"--os-start.servers.{i}.id={iid}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BatchStartServers failed: {result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def main():
    parser = argparse.ArgumentParser(description="Emergency rollback for CCE AZ power outage experiment")
    parser.add_argument("--experiment-dir", help="Experiment directory with experiment.json")
    parser.add_argument("--ids", help="Comma-separated instance IDs")
    parser.add_argument("--region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"))
    parser.add_argument("--timeout", type=int, default=600, help="Recovery timeout in seconds")
    args = parser.parse_args()

    # Get instance IDs
    if args.ids:
        instance_ids = [i.strip() for i in args.ids.split(",")]
        node_names = []
    elif args.experiment_dir:
        exp_path = os.path.join(args.experiment_dir, "experiment.json")
        if not os.path.exists(exp_path):
            print(f"Error: experiment.json not found", file=sys.stderr)
            sys.exit(1)
        with open(exp_path) as f:
            exp = json.load(f)
        instance_ids = [n["instance_id"] for n in exp["targets"]["nodes"] if n.get("instance_id")]
        node_names = [n["name"] for n in exp["targets"]["nodes"]]
        args.region = exp.get("region", args.region)
    else:
        print("Error: provide --experiment-dir or --ids", file=sys.stderr)
        sys.exit(1)

    if not instance_ids:
        print("Error: no instance IDs found", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 60)
    print("  EMERGENCY ROLLBACK: CCE AZ Power Outage Experiment")
    print("=" * 60)
    print(f"  Region: {args.region}")
    print(f"  Instances: {len(instance_ids)}")
    print()

    # Step 1: Start all instances
    print("[1/3] Starting all target nodes (BatchStartServers) ...")
    try:
        result = batch_start_servers(instance_ids, args.region)
        print(f"  ✓ BatchStartServers sent (job_id: {result.get('job_id', '')})")
    except Exception as e:
        print(f"  ✗ Failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Wait for nodes to become Ready
    print()
    print("[2/3] Waiting for nodes to become Ready ...")

    if node_names:
        elapsed = 0
        interval = 10
        while elapsed < args.timeout:
            time.sleep(interval)
            elapsed += interval

            node_statuses = get_node_statuses(node_names)
            all_ready = all(s.get("ready") for s in node_statuses.values()) if node_statuses else False

            ready_count = sum(1 for s in node_statuses.values() if s.get("ready"))
            print(f"  ... {elapsed}s elapsed, {ready_count}/{len(node_names)} nodes Ready")

            if all_ready:
                break

        if all_ready:
            print(f"  ✓ All nodes Ready (elapsed: {elapsed}s)")
        else:
            print(f"  ⚠️ Timeout: not all nodes Ready after {elapsed}s")
    else:
        print("  (Node names not available — skipping node status check)")

    # Step 3: Check pod recovery
    print()
    print("[3/3] Checking pod recovery ...")

    pod_statuses = get_pod_statuses()
    running_pods = sum(1 for s in pod_statuses.values() if s.get("phase") == "Running")
    pending_pods = sum(1 for s in pod_statuses.values() if s.get("phase") == "Pending")

    print(f"  Running pods: {running_pods}")
    print(f"  Pending pods: {pending_pods}")

    print()
    print("=" * 60)
    print("  Rollback complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
