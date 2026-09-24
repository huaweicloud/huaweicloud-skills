#!/usr/bin/env python3
"""
execute_experiment.py — Execute ECS shutdown fault injection experiment.

Main execution script: loads experiment.json, pre-checks instance states,
executes BatchStopServers, monitors instance status, waits for duration,
executes BatchStartServers rollback, verifies recovery, logs everything.

Supports: --dry-run, --auto-rollback, --abort-on-failure

Usage:
    python3 execute_experiment.py --experiment-dir ./experiments/xxx/ --cli-region cn-north-4
    python3 execute_experiment.py --experiment-dir ./experiments/xxx/ --dry-run --cli-region cn-north-4
    python3 execute_experiment.py --experiment-dir ./experiments/xxx/ --auto-rollback --cli-region cn-north-4
    Real shutdown requires --yes (or --dry-run); without it execution is refused.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# Add scripts dir to path for monitor_instances import
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from monitor_instances import (monitor, query_instance_statuses, now_iso,
                               _build_subprocess_env, check_stop_conditions)


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
    except FileNotFoundError:
        return False, "hcloud CLI not found"
    except subprocess.TimeoutExpired:
        return False, "hcloud command timed out"


def load_experiment(experiment_dir):
    """Load experiment.json from the experiment directory."""
    path = os.path.join(experiment_dir, "experiment.json")
    if not os.path.exists(path):
        print(f"Error: experiment.json not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def batch_stop(instance_ids, region, os_stop="SOFT"):
    """Execute BatchStopServers to stop target instances.
    
    Sends all instance IDs in a single API call (batch, not per-instance).
    hcloud CLI uses flat parameter format, not --body JSON:
      --os-stop.servers.1.id=<id1> --os-stop.servers.2.id=<id2> --os-stop.type=SOFT
    """
    args = ["ECS", "BatchStopServers", "--cli-output=json"]
    for idx, iid in enumerate(instance_ids, 1):
        args.append(f"--os-stop.servers.{idx}.id={iid}")
    args.append(f"--os-stop.type={os_stop}")
    success, result = run_hcloud(args, region=region)
    return success, result


def batch_start(instance_ids, region):
    """Execute BatchStartServers to start target instances.
    
    Sends all instance IDs in a single API call (batch, not per-instance).
    hcloud CLI uses flat parameter format, not --body JSON:
      --os-start.servers.1.id=<id1> --os-start.servers.2.id=<id2>
    """
    args = ["ECS", "BatchStartServers", "--cli-output=json"]
    for idx, iid in enumerate(instance_ids, 1):
        args.append(f"--os-start.servers.{idx}.id={iid}")
    success, result = run_hcloud(args, region=region)
    return success, result


def execute_experiment(exp, region, dry_run=False, auto_rollback=False,
                       abort_on_failure=False, poll_interval=10, confirmed=False):
    """Execute the full experiment workflow."""
    instance_ids = exp["targets"]["instance_ids"]
    duration = exp["actions"]["shutdown"]["duration_seconds"]
    os_stop = exp["actions"]["shutdown"]["parameters"].get("os_stop", "SOFT")
    stop_conditions = exp.get("stop_conditions", [])
    stop_condition_triggered = None  # description of the first triggered stop condition
    stopped_early = False            # True when a stop condition aborts the duration wait
    exp_name = exp.get("experiment_name", "unnamed")

    log = {
        "experiment_name": exp_name,
        "region": region,
        "started_at": now_iso(),
        "completed_at": None,
        "instance_ids": instance_ids,
        "duration_config": duration,
        "phases": {},
        "instance_timeline": [],
        "overall_result": None,
        "dry_run": dry_run,
    }

    print(f"\n{'='*60}")
    print(f"  ECS Shutdown Experiment: {exp_name}")
    print(f"  Region: {region}")
    print(f"  Targets: {len(instance_ids)} instance(s)")
    print(f"  Duration: {duration}s")
    print(f"  Dry run: {dry_run}")
    print(f"{'='*60}\n")

    # ---- Confirmation gate: real shutdown requires explicit --yes ----
    if not dry_run and not confirmed:
        print("  \u2717 REFUSED: real execution requires explicit confirmation (--yes).")
        print("    This experiment will SHUT DOWN the following instances:")
        for iid in instance_ids:
            print(f"      - {iid}")
        print(f"    Region: {region} | Duration: {duration}s | os_stop: {os_stop}")
        print("    Business on these instances will be interrupted until rollback (Phase 5).")
        print("    Re-run with --yes to confirm you accept this impact.")
        log["overall_result"] = "refused_no_confirmation"
        log["completed_at"] = now_iso()
        print(f"\n  Experiment result: {log['overall_result']}")
        return log

    # ---- Phase 1: Pre-check ----
    print("[1/6] Pre-check: verifying all instances are ACTIVE ...")
    log["phases"]["pre_check"] = {"started_at": now_iso()}

    if dry_run:
        print("  [DRY RUN] Skipping actual status query")
        log["phases"]["pre_check"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
    else:
        # Batch query: single ListServersDetails call for all instances
        statuses = query_instance_statuses(instance_ids, region)
        all_active = all(statuses.get(i) == "ACTIVE" for i in instance_ids)
        # Local iteration over results (no network calls in this loop)
        for iid in instance_ids:
            s = statuses.get(iid, "UNKNOWN")
            marker = "✓" if s == "ACTIVE" else "✗"
            print(f"  [{marker}] {iid}: {s}")

        if not all_active:
            log["phases"]["pre_check"].update({
                "completed_at": now_iso(), "result": "failed",
                "statuses": statuses
            })
            log["overall_result"] = "failed_pre_check"
            log["completed_at"] = now_iso()
            print("\n  ✗ Pre-check FAILED: not all instances are ACTIVE")
            return log
        print("  ✓ Pre-check passed")
        log["phases"]["pre_check"].update({
            "completed_at": now_iso(), "result": "passed", "statuses": statuses
        })

    # ---- Phase 2: Shutdown (fault injection) ----
    print(f"\n[2/6] Shutdown: executing BatchStopServers (os_stop={os_stop}) ...")
    log["phases"]["shutdown"] = {"started_at": now_iso()}

    if dry_run:
        print(f"  [DRY RUN] Would stop instances: {', '.join(instance_ids)}")
        log["phases"]["shutdown"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
    else:
        # Single batch API call for all instances
        success, result = batch_stop(instance_ids, region, os_stop)
        if not success:
            print(f"  ✗ BatchStopServers failed: {result}")
            log["phases"]["shutdown"].update({
                "completed_at": now_iso(), "result": "failed", "error": str(result)
            })
            if auto_rollback:
                print("  [auto-rollback] Attempting rollback ...")
                success_rb, _ = batch_start(instance_ids, region)
                log["overall_result"] = "failed_shutdown_auto_rollback"
            else:
                log["overall_result"] = "failed_shutdown"
            log["completed_at"] = now_iso()
            return log
        print(f"  ✓ BatchStopServers command sent (job_id: {result.get('job_id', 'N/A') if isinstance(result, dict) else 'N/A'})")
        log["phases"]["shutdown"].update({
            "completed_at": now_iso(), "result": "success", "response": result
        })

    # ---- Phase 3: Monitor shutdown ----
    print(f"\n[3/6] Monitor: waiting for all instances to reach SHUTOFF ...")
    log["phases"]["monitor"] = {"started_at": now_iso()}

    if dry_run:
        print("  [DRY RUN] Would poll until SHUTOFF")
        log["phases"]["monitor"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
    else:
        # monitor() uses batch polling: one ListServersDetails call per cycle
        mon = monitor(instance_ids, "SHUTOFF", region=region, timeout=300,
                       interval=poll_interval, stop_conditions=stop_conditions)
        log["instance_timeline"].extend(mon["timeline"])
        monitor_result = "all_stopped" if mon["reached"] else "timeout_or_error"
        if mon["stop_condition_triggered"]:
            monitor_result = "stopped_by_condition"
        log["phases"]["monitor"].update({
            "completed_at": now_iso(),
            "result": monitor_result,
            "elapsed": mon["elapsed_seconds"],
            "final_statuses": mon["final_statuses"],
        })
        if mon["stop_condition_triggered"]:
            print(f"  [!] Stop condition triggered: {mon['stop_condition_triggered']}")
            log["phases"]["monitor"]["stop_condition"] = mon["stop_condition_triggered"]
            stop_condition_triggered = mon["stop_condition_triggered"]

        if mon["reached"]:
            print(f"  ✓ All instances stopped (elapsed: {mon['elapsed_seconds']}s)")
        else:
            print(f"  [!] Not all instances stopped (elapsed: {mon['elapsed_seconds']}s)")
            # Local iteration over cached results (no network calls)
            for iid in instance_ids:
                s = mon["final_statuses"].get(iid, "UNKNOWN")
                print(f"    {iid}: {s}")

    # ---- Phase 4: Wait for duration ----
    print(f"\n[4/6] Wait: experiment duration {duration}s ...")
    log["phases"]["wait"] = {"started_at": now_iso()}

    if dry_run:
        print(f"  [DRY RUN] Would wait {duration}s")
        log["phases"]["wait"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
    else:
        if stop_condition_triggered:
            # Already aborted during Phase 3: do not sleep the remaining duration
            print(f"  [!] Stop condition already triggered, skipping remaining duration "
                  f"({duration}s) and rolling back now: {stop_condition_triggered}")
            waited_seconds = 0
            stopped_early = True
        else:
            # Wait in chunks; each chunk also re-checks stop conditions (CES alarms)
            elapsed = 0
            chunk = min(poll_interval, 10)
            while elapsed < duration:
                time.sleep(chunk)
                elapsed += chunk
                remaining = duration - elapsed

                # Stop conditions are evaluated every chunk, not just during Phase 3
                triggered = check_stop_conditions(stop_conditions, region)
                if triggered:
                    print(f"  [!] Stop condition triggered during wait, aborting remaining "
                          f"duration ({remaining}s): {triggered}")
                    stop_condition_triggered = triggered
                    stopped_early = True
                    break

                if elapsed % 30 == 0 or remaining <= 0:
                    # Batch query: single API call for all instances
                    statuses = query_instance_statuses(instance_ids, region)
                    # Local iteration over results (no network calls in this loop)
                    for iid in instance_ids:
                        s = statuses.get(iid, "UNKNOWN")
                        if s != "SHUTOFF":
                            log["instance_timeline"].append({
                                "timestamp": now_iso(),
                                "instance_id": iid,
                                "old_status": "SHUTOFF",
                                "new_status": s,
                            })
                    print(f"  ... {elapsed}s / {duration}s elapsed")

            waited_seconds = elapsed if stopped_early else duration

        wait_update = {
            "completed_at": now_iso(),
            "result": "stopped_early" if stopped_early else "completed",
            "duration": duration,
        }
        if stop_condition_triggered:
            wait_update["stop_condition"] = stop_condition_triggered
        if stopped_early:
            wait_update["waited_seconds"] = waited_seconds
            wait_update["elapsed"] = waited_seconds
            print(f"  ⏹ Wait aborted early at {waited_seconds}s / {duration}s")
        else:
            print(f"  ✓ Wait complete ({duration}s)")
        log["phases"]["wait"].update(wait_update)

    # ---- Phase 5: Rollback (start instances) ----
    print(f"\n[5/6] Rollback: executing BatchStartServers ...")
    log["phases"]["rollback"] = {"started_at": now_iso()}

    if dry_run:
        print(f"  [DRY RUN] Would start instances: {', '.join(instance_ids)}")
        log["phases"]["rollback"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
    else:
        # Single batch API call for all instances
        success, result = batch_start(instance_ids, region)
        if not success:
            print(f"  ✗ BatchStartServers failed: {result}")
            log["phases"]["rollback"].update({
                "completed_at": now_iso(), "result": "failed", "error": str(result)
            })
            log["overall_result"] = "failed_rollback"
            log["completed_at"] = now_iso()
            return log
        print(f"  ✓ BatchStartServers command sent (job_id: {result.get('job_id', 'N/A') if isinstance(result, dict) else 'N/A'})")
        log["phases"]["rollback"].update({
            "completed_at": now_iso(), "result": "success", "response": result
        })

    # ---- Phase 6: Verify recovery ----
    print(f"\n[6/6] Verify: waiting for all instances to reach ACTIVE ...")
    log["phases"]["verify"] = {"started_at": now_iso()}

    if dry_run:
        print("  [DRY RUN] Would poll until ACTIVE")
        log["phases"]["verify"].update({
            "completed_at": now_iso(), "result": "skipped_dry_run"
        })
        log["overall_result"] = "dry_run_complete"
    else:
        # monitor() uses batch polling: one ListServersDetails call per cycle
        mon = monitor(instance_ids, "ACTIVE", region=region, timeout=300,
                       interval=poll_interval)
        log["instance_timeline"].extend(mon["timeline"])
        if mon["reached"]:
            print(f"  ✓ All instances active (elapsed: {mon['elapsed_seconds']}s)")
            log["phases"]["verify"].update({
                "completed_at": now_iso(), "result": "all_active",
                "elapsed": mon["elapsed_seconds"]
            })
            log["overall_result"] = "success"
        else:
            print(f"  ✗ Not all instances recovered (elapsed: {mon['elapsed_seconds']}s)")
            # Local iteration over cached results (no network calls)
            for iid in instance_ids:
                s = mon["final_statuses"].get(iid, "UNKNOWN")
                print(f"    {iid}: {s}")
            log["phases"]["verify"].update({
                "completed_at": now_iso(), "result": "not_all_active",
                "elapsed": mon["elapsed_seconds"],
                "final_statuses": mon["final_statuses"]
            })
            log["overall_result"] = "failed_verify"

    # A stop-condition abort that still recovers cleanly is reported as stopped_early,
    # so consumers can distinguish an early-terminated run from a full-duration run.
    if stopped_early and log["overall_result"] == "success":
        log["overall_result"] = "stopped_early"

    log["completed_at"] = now_iso()
    started = datetime.fromisoformat(log["started_at"])
    completed = datetime.fromisoformat(log["completed_at"])
    log["total_duration_seconds"] = int((completed - started).total_seconds())

    print(f"\n{'='*60}")
    print(f"  Experiment result: {log['overall_result']}")
    print(f"  Total time: {log['total_duration_seconds']}s")
    print(f"{'='*60}\n")

    return log


def main():
    parser = argparse.ArgumentParser(
        description="Execute ECS shutdown fault injection experiment."
    )
    parser.add_argument("--experiment-dir", required=True,
                        help="Path to experiment directory (containing experiment.json)")
    parser.add_argument("--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region (default: cn-north-4 or HW_REGION_NAME env)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without making any API calls")
    parser.add_argument("--yes", action="store_true",
                        help="Explicitly confirm real execution (instance shutdown). "
                             "Required unless --dry-run is set; default is refuse.")
    parser.add_argument("--auto-rollback", action="store_true",
                        help="Automatically rollback if shutdown fails")
    parser.add_argument("--abort-on-failure", action="store_true",
                        help="Abort immediately on any failure")
    parser.add_argument("--poll-interval", type=int, default=10,
                        help="Status polling interval in seconds (default: 10)")
    parser.add_argument("--log-file", help="Write execution log to file")
    args = parser.parse_args()

    exp = load_experiment(args.experiment_dir)
    region = args.cli_region or exp.get("region", "cn-north-4")

    log = execute_experiment(
        exp, region,
        dry_run=args.dry_run,
        auto_rollback=args.auto_rollback,
        abort_on_failure=args.abort_on_failure,
        poll_interval=args.poll_interval,
        confirmed=args.yes,
    )

    log_json = json.dumps(log, indent=2, ensure_ascii=False)

    # Always write log to experiment dir
    log_path = args.log_file or os.path.join(args.experiment_dir, "execution-log.json")
    with open(log_path, "w") as f:
        f.write(log_json)
    if log.get("overall_result") == "refused_no_confirmation":
        print("Execution refused: no confirmation given (--yes).")
        sys.exit(1)
    print(f"Execution log written to: {log_path}")


if __name__ == "__main__":
    main()
