#!/usr/bin/env python3
"""
monitor_instances.py — Monitor ECS instance status during shutdown experiment.

Polls ECS instance status at regular intervals, records state transitions,
and optionally checks CES alarms as stop conditions.

State machine: ACTIVE → STOPPING → SHUTOFF (shutdown)
               SHUTOFF → STARTING → ACTIVE (startup)

Usage:
    python3 monitor_instances.py --ids "i-xxx,i-yyy" --target-status SHUTOFF --cli-region cn-north-4
    python3 monitor_instances.py --ids "i-xxx" --target-status ACTIVE --timeout 300 --cli-region cn-north-4
    python3 monitor_instances.py --ids "i-xxx" --target-status SHUTOFF --interval 5 --cli-region cn-north-4
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _build_subprocess_env(region=None):
    """Build subprocess environment with an explicit whitelist of variables.

    Security: never bulk-copy os.environ — only pass the specific vars that
    hcloud CLI needs. This avoids inadvertently leaking other secret-bearing
    environment variables into the child process.
    """
    env = {}
    # Inherit only non-sensitive runtime vars needed to locate binaries and config
    for key in ("PATH", "HOME", "LANG", "LC_ALL"):
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    # Explicitly forward Huawei Cloud credential vars by name
    for key in ("HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_REGION_NAME", "HW_PROJECT_ID"):
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    if region and "HW_REGION_NAME" not in env:
        env["HW_REGION_NAME"] = region
    return env


def run_hcloud(args, region=None):
    """Run hcloud CLI command and return parsed JSON output."""
    cmd = ["hcloud"] + args
    # Ensure region is passed as a CLI parameter
    if region and "--cli-region" not in args and "--region" not in args:
        cmd.append(f"--cli-region={region}")
    env = _build_subprocess_env(region=region)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=60
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            for i in range(len(output)):
                if output[i] in "[{":
                    try:
                        return json.loads(output[i:])
                    except json.JSONDecodeError:
                        continue
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def query_instance_statuses(instance_ids, region=None):
    """Query current status of specified ECS instances.

    Uses ListServersDetails with explicit paging (the API default page size is
    25, max 1000 per request) and filters locally by instance ID — no
    per-instance N+1 network calls. Paging is required so targets beyond the
    first page are not silently missed (which would report them as UNKNOWN).
    """
    status_map = {}
    limit = 1000
    offset = 1

    while True:
        data = run_hcloud(
            ["ECS", "ListServersDetails", f"--limit={limit}", f"--offset={offset}", "--cli-output=json"],
            region=region
        )

        if data is None:
            break

        if isinstance(data, dict):
            servers = data.get("servers", data.get("items", []))
            total = int(data.get("count", 0) or 0)
        elif isinstance(data, list):
            servers = data
            total = len(servers)
        else:
            servers = []
            total = 0

        # Build a lookup map from the batch response (local filtering, no network)
        for srv in servers:
            sid = srv.get("id", "")
            status = srv.get("status", "UNKNOWN")
            status_map[sid] = status

        # offset is a 1-based page number; continue while more pages remain
        pages = (total + limit - 1) // limit if total else 1
        if offset >= pages or not servers:
            break
        offset += 1

    # Ensure all requested IDs are present
    for iid in instance_ids:
        if iid not in status_map:
            status_map[iid] = "UNKNOWN"

    return status_map


def check_ces_alarm(alarm_id, region=None):
    """Check if a CES alarm is currently in ALARM state.

    CES ListAlarmHistories API accepts a single alarm_id — there is no batch
    endpoint for querying multiple alarms at once.
    """
    data = run_hcloud(
        ["CES", "ListAlarmHistories", f"--alarm_id.1={alarm_id}", "--cli-output=json"],
        region=region
    )
    if data is None:
        return False

    if isinstance(data, dict):
        histories = data.get("alarm_histories", data.get("items", []))
    elif isinstance(data, list):
        histories = data
    else:
        histories = []

    for h in histories:
        if h.get("alarm_state", "") in ("ALARM", "alarm", "insufficient_data"):
            return True
    return False


def check_stop_conditions(stop_conditions, region=None):
    """Evaluate all stop conditions in a single pass.

    Pre-collects alarm IDs from stop_conditions, then queries each alarm.
    Returns the description of the first triggered condition, or None.

    Note: CES API only supports single-alarm queries (no batch endpoint),
    so alarm checks are sequential. This function is called once per polling
    cycle — the loop over alarm_ids is encapsulated here, not in the caller.
    """
    if not stop_conditions:
        return None

    alarm_conds = [
        c for c in stop_conditions if c.get("type") == "ces_alarm" and c.get("alarm_id")
    ]
    for cond in alarm_conds:
        alarm_id = cond.get("alarm_id", "")
        if check_ces_alarm(alarm_id, region):
            return cond.get("description", alarm_id)
    return None


def monitor(instance_ids, target_status, region=None, timeout=300, interval=10,
            stop_conditions=None):
    """
    Poll instance statuses until all reach target_status or timeout.

    Each polling cycle makes a single batch API call (ListServersDetails)
    for all instances — no per-instance N+1 network calls.

    Returns a dict with:
      - reached: bool (all instances reached target status)
      - timeline: list of state transition events
      - final_statuses: dict of instance_id -> status
      - elapsed_seconds: int
      - stop_condition_triggered: str or None
    """
    timeline = []
    prev_statuses = {}
    start_time = time.time()
    deadline = start_time + timeout
    stop_triggered = None

    # Initial query — single batch call for all instances
    current = query_instance_statuses(instance_ids, region)
    for iid in instance_ids:
        prev_statuses[iid] = current.get(iid, "UNKNOWN")
        timeline.append({
            "timestamp": now_iso(),
            "instance_id": iid,
            "old_status": None,
            "new_status": prev_statuses[iid],
        })

    while time.time() < deadline:
        # Check stop conditions (CES alarms) — single evaluation per cycle
        stop_triggered = check_stop_conditions(stop_conditions, region)
        if stop_triggered:
            break

        # Check if all reached target (local check, no network)
        all_reached = all(
            prev_statuses.get(iid) == target_status for iid in instance_ids
        )
        if all_reached:
            break

        # Wait
        time.sleep(interval)

        # Query again — single batch call for all instances
        current = query_instance_statuses(instance_ids, region)
        for iid in instance_ids:
            new_status = current.get(iid, "UNKNOWN")
            old_status = prev_statuses.get(iid)
            if new_status != old_status:
                timeline.append({
                    "timestamp": now_iso(),
                    "instance_id": iid,
                    "old_status": old_status,
                    "new_status": new_status,
                })
                prev_statuses[iid] = new_status

                # Check for ERROR state
                if new_status == "ERROR":
                    stop_triggered = f"Instance {iid} entered ERROR state"
                    break
        if stop_triggered:
            break

    elapsed = int(time.time() - start_time)
    all_reached = all(
        prev_statuses.get(iid) == target_status for iid in instance_ids
    )

    return {
        "reached": all_reached,
        "timeline": timeline,
        "final_statuses": prev_statuses,
        "elapsed_seconds": elapsed,
        "stop_condition_triggered": stop_triggered,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Monitor ECS instance status during shutdown experiment."
    )
    parser.add_argument("--ids", required=True, help="Comma-separated ECS instance IDs")
    parser.add_argument("--target-status", required=True,
                        help="Target status to wait for (SHUTOFF, ACTIVE, etc.)")
    parser.add_argument("--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region (default: cn-north-4 or HW_REGION_NAME env)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval in seconds")
    parser.add_argument("--stop-conditions", help="JSON string of stop conditions")
    parser.add_argument("--output-file", help="Write result to file instead of stdout")
    args = parser.parse_args()

    instance_ids = [i.strip() for i in args.ids.split(",")]
    stop_conditions = None
    if args.stop_conditions:
        stop_conditions = json.loads(args.stop_conditions)

    result = monitor(
        instance_ids=instance_ids,
        target_status=args.target_status,
        region=args.cli_region,
        timeout=args.timeout,
        interval=args.interval,
        stop_conditions=stop_conditions,
    )

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output_file:
        with open(args.output_file, "w") as f:
            f.write(output)
        print(f"Result written to {args.output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
