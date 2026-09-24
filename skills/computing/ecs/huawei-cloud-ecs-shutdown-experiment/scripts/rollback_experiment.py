#!/usr/bin/env python3
"""
rollback_experiment.py — Emergency rollback for ECS shutdown experiment.

Loads experiment.json, executes BatchStartServers to start all target
instances, and verifies recovery. Used for emergency termination mid-experiment.

Usage:
    python3 rollback_experiment.py --experiment-dir ./experiments/xxx/ --cli-region cn-north-4
    python3 rollback_experiment.py --ids "i-xxx,i-yyy" --cli-region cn-north-4
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from monitor_instances import monitor, query_instance_statuses, now_iso, _build_subprocess_env


def run_hcloud(args, region=None):
    """Run hcloud CLI command and return (success, parsed_json_or_stderr)."""
    cmd = ["hcloud"] + args
    # Ensure region is passed as a CLI parameter
    if region and "--cli-region" not in args and "--region" not in args:
        cmd.append(f"--cli-region={region}")
    env = _build_subprocess_env(region=region)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=120
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        output = result.stdout.strip()
        try:
            return True, json.loads(output)
        except json.JSONDecodeError:
            for i in range(len(output)):
                if output[i] in "[{":
                    try:
                        return True, json.loads(output[i:])
                    except json.JSONDecodeError:
                        continue
            return True, {"raw": output}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def batch_start(instance_ids, region):
    """Execute BatchStartServers to start target instances.
    
    Sends all instance IDs in a single API call (batch, not per-instance).
    Uses flat parameter format consistent with execute_experiment.py:
      --os-start.servers.1.id=<id1> --os-start.servers.2.id=<id2>
    """
    args = ["ECS", "BatchStartServers", "--cli-output=json"]
    for idx, iid in enumerate(instance_ids, 1):
        args.append(f"--os-start.servers.{idx}.id={iid}")
    success, result = run_hcloud(args, region=region)
    return success, result


def rollback(instance_ids, region, poll_interval=10, verify_timeout=300):
    """Execute emergency rollback: start all instances and verify."""
    log = {
        "action": "emergency_rollback",
        "started_at": now_iso(),
        "instance_ids": instance_ids,
        "region": region,
    }

    print(f"\n{'='*60}")
    print(f"  EMERGENCY ROLLBACK")
    print(f"  Instances: {', '.join(instance_ids)}")
    print(f"  Region: {region}")
    print(f"{'='*60}\n")

    # Step 1: Check current status — batch query for all instances
    print("[1/3] Checking current instance status ...")
    statuses = query_instance_statuses(instance_ids, region)
    # Local iteration over cached results (no network calls in this loop)
    for iid in instance_ids:
        s = statuses.get(iid, "UNKNOWN")
        print(f"  {iid}: {s}")

    already_active = all(statuses.get(i) == "ACTIVE" for i in instance_ids)
    if already_active:
        print("\n  All instances are already ACTIVE. No rollback needed.")
        log["result"] = "already_active"
        log["completed_at"] = now_iso()
        return log

    # Step 2: Start instances — single batch API call
    print(f"\n[2/3] Starting instances via BatchStartServers ...")
    success, result = batch_start(instance_ids, region)
    if not success:
        print(f"  ✗ BatchStartServers failed: {result}")
        log["result"] = "failed"
        log["error"] = str(result)
        log["completed_at"] = now_iso()
        return log

    print("  ✓ BatchStartServers command sent")

    # Step 3: Verify recovery — monitor() uses batch polling
    print(f"\n[3/3] Verifying all instances reach ACTIVE ...")
    mon = monitor(instance_ids, "ACTIVE", region=region, timeout=verify_timeout,
                   interval=poll_interval)

    if mon["reached"]:
        print(f"  ✓ All instances ACTIVE (elapsed: {mon['elapsed_seconds']}s)")
        log["result"] = "success"
    else:
        print(f"  ✗ Not all instances recovered (elapsed: {mon['elapsed_seconds']}s)")
        # Local iteration over cached results (no network calls)
        for iid in instance_ids:
            s = mon["final_statuses"].get(iid, "UNKNOWN")
            print(f"    {iid}: {s}")
        log["result"] = "verify_failed"
        log["final_statuses"] = mon["final_statuses"]

    log["timeline"] = mon["timeline"]
    log["elapsed_seconds"] = mon["elapsed_seconds"]
    log["completed_at"] = now_iso()

    print(f"\n{'='*60}")
    print(f"  Rollback result: {log['result']}")
    print(f"{'='*60}\n")

    return log


def main():
    parser = argparse.ArgumentParser(
        description="Emergency rollback: start all ECS target instances."
    )
    parser.add_argument("--experiment-dir",
                        help="Path to experiment directory (containing experiment.json)")
    parser.add_argument("--ids", help="Comma-separated ECS instance IDs (alternative to --experiment-dir)")
    parser.add_argument("--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region (default: cn-north-4 or HW_REGION_NAME env)")
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--verify-timeout", type=int, default=300)
    parser.add_argument("--log-file", help="Write rollback log to file")
    args = parser.parse_args()

    # Get instance IDs
    if args.experiment_dir:
        exp_path = os.path.join(args.experiment_dir, "experiment.json")
        if not os.path.exists(exp_path):
            print(f"Error: experiment.json not found at {exp_path}", file=sys.stderr)
            sys.exit(1)
        with open(exp_path) as f:
            exp = json.load(f)
        instance_ids = exp["targets"]["instance_ids"]
        region = args.cli_region or exp.get("region", "cn-north-4")
    elif args.ids:
        instance_ids = [i.strip() for i in args.ids.split(",")]
        region = args.cli_region
    else:
        print("Error: provide --experiment-dir or --ids", file=sys.stderr)
        sys.exit(1)

    log = rollback(instance_ids, region, args.poll_interval, args.verify_timeout)

    log_json = json.dumps(log, indent=2, ensure_ascii=False)
    log_path = args.log_file
    if not log_path and args.experiment_dir:
        log_path = os.path.join(args.experiment_dir, "rollback-log.json")
    if log_path:
        with open(log_path, "w") as f:
            f.write(log_json)
        print(f"Rollback log written to: {log_path}")


if __name__ == "__main__":
    main()
