#!/usr/bin/env python3
"""
Collect CCE Pod logs, LTS logs, and Kubernetes Events.

Design notes:
- Pod logs: Pods on affected nodes are evicted and deleted during the experiment,
  so kubectl logs cannot retrieve historical logs of deleted Pods. The script
  therefore tries both: (1) collect logs from the original Pod in pod_timeline
  if it still exists; (2) find a currently alive Pod of the same
  Deployment/StatefulSet and collect its logs as a substitute.
- Kubernetes Events: Serve as the primary data source for post-hoc analysis,
  filtered by the experiment time window.
- LTS logs: Query log groups/streams and fetch actual log content via hcloud CLI.

Environment variables:
- KUBECONFIG: Passed to kubectl subprocess if set.
- HW_REGION_NAME: Used for hcloud LTS queries (default cn-north-4).
"""

import json
import os
import sys
import subprocess
import argparse
import re
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


def get_kubectl_env():
    """Build environment for kubectl subprocess, ensuring KUBECONFIG is passed."""
    env = _build_env()
    # KUBECONFIG may be unset in the trimmed env; fall back to default path if present
    if "KUBECONFIG" not in env and os.path.exists(os.path.expanduser("~/.kube/config")):
        env["KUBECONFIG"] = os.path.expanduser("~/.kube/config")
    return env


def run_kubectl(args, timeout=30):
    """Run a kubectl command."""
    cmd = ["kubectl"] + args
    env = get_kubectl_env()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return result
    except Exception as e:
        return None


def find_current_pod_name(pod_spec):
    """Find a currently alive Pod with the same name from pod_timeline.

    Pod name format: namespace/podname (e.g. kube-system/coredns-77ff9f4bbf-hb7mk)
    For Deployment/StatefulSet Pods, the old Pod is deleted and a new one is created.
    Uses label selector to match the current Pod of the same Deployment.
    """
    parts = pod_spec.split("/", 1)
    if len(parts) == 2:
        ns, pod_name = parts
    else:
        ns, pod_name = "default", parts[0]

    # Extract pod-template-hash or replica name from pod name
    # e.g. coredns-77ff9f4bbf-hb7mk -> deployment coredns, hash 77ff9f4bbf
    # e.g. prometheus-lightweight-0 -> statefulset prometheus-lightweight
    result = run_kubectl(["get", "pods", "-n", ns, "-o", "json"])
    if not result or result.returncode != 0:
        return ns, pod_name, None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ns, pod_name, None

    # Try to find a currently running pod with the same prefix
    # (same Deployment/StatefulSet, different hash suffix)
    # Extract the base name by removing the last "-xxxxx" hash segment
    base_match = re.match(r"^(.+)-[a-f0-9]{8,10}-[a-z0-9]{5}$", pod_name)
    if not base_match:
        # StatefulSet pod: name-0, name-1
        base_match = re.match(r"^(.+)-\d+$", pod_name)

    if base_match:
        base_name = base_match.group(1)
        for item in data.get("items", []):
            current_name = item["metadata"]["name"]
            current_ns = item["metadata"]["namespace"]
            if current_ns == ns and current_name.startswith(base_name + "-"):
                phase = item.get("status", {}).get("phase", "")
                if phase in ("Running", "Pending"):
                    return ns, pod_name, current_name

    return ns, pod_name, None


def collect_pod_logs(pods, since_time, until_time, output_dir):
    """Collect Pod logs.

    For each Pod in pod_timeline:
    1. Try to get logs directly from the Pod (if it still exists)
    2. If the Pod was deleted, find a currently alive Pod of the same Deployment/StatefulSet
    3. Collect logs from the alive Pod as a substitute
    """
    os.makedirs(output_dir, exist_ok=True)
    collected = []

    for pod_spec in pods:
        ns, original_pod, current_pod = find_current_pod_name(pod_spec)

        # Determine which pod to query
        target_pod = current_pod or original_pod
        is_substitute = current_pod is not None and current_pod != original_pod

        if current_pod is None:
            # Original pod no longer exists and no substitute found
            # Try directly anyway — might still exist
            target_pod = original_pod

        cmd = ["logs", target_pod, "-n", ns, "--tail=1000"]
        if since_time:
            cmd.extend(["--since-time", since_time])
        if until_time:
            cmd.extend(["--since-time", since_time])  # kubectl logs has no --until-time

        result = run_kubectl(cmd, timeout=30)
        if result and result.returncode == 0 and result.stdout.strip():
            output_file = os.path.join(output_dir, f"{ns}_{original_pod}.log")
            with open(output_file, "w") as f:
                f.write(result.stdout)
            collected.append(output_file)
            label = f" -> {target_pod}" if is_substitute else ""
            print(f"  [OK] {ns}/{original_pod}{label}: {len(result.stdout.splitlines())} lines")
        else:
            # Pod was deleted and no substitute found
            reason = "Pod deleted, no alive substitute found" if current_pod is None else "Failed to retrieve logs"
            print(f"  [SKIP] {ns}/{original_pod}: {reason}")

    return collected


def _rfc3339_to_ms(value):
    """Convert RFC3339 string to epoch milliseconds (UTC)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return None


def collect_lts_logs(since_time, until_time, output_dir):
    """Collect LTS log content via hcloud CLI.

    Lists log groups and streams, then queries actual log content with
    `hcloud LTS ListLogs` (start_time/end_time are UTC epoch milliseconds)
    and saves the response per stream. Falls back to recording only stream
    metadata when the query fails.
    """
    os.makedirs(output_dir, exist_ok=True)
    region = os.environ.get("HW_REGION_NAME", "cn-north-4")
    collected = []

    # Convert experiment window to UTC epoch ms; default to the last hour.
    start_ms = _rfc3339_to_ms(since_time)
    end_ms = _rfc3339_to_ms(until_time)
    if start_ms is None or end_ms is None:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = end_ms - 3600 * 1000
        print(f"  [INFO] LTS time window not set, using last 1h ({start_ms}~{end_ms})")

    # Step 1: List log groups
    cmd = ["hcloud", "LTS", "ListLogGroups", "--cli-output=json", f"--cli-region={region}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=_build_env(region))
        if result.returncode != 0:
            print("  [INFO] LTS log group query failed, skipping LTS log collection")
            return []
        print("  [INFO] LTS log group query succeeded")

        # Parse log groups
        try:
            # hcloud may append diagnostic text after JSON; extract JSON part
            output = result.stdout.strip()
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(output)
        except (json.JSONDecodeError, ValueError):
            data = []

        groups = data if isinstance(data, list) else data.get("log_groups", [])
        if not groups:
            print("  [INFO] No LTS log groups found")
            return []

        # Step 2: For each group, list log streams and query log content
        for group in groups[:5]:  # limit to first 5 groups
            group_id = group.get("log_group_id", "")
            group_name = group.get("log_group_name", "")
            if not group_id:
                continue

            stream_cmd = [
                "hcloud", "LTS", "ListLogStream", "--cli-output=json",
                f"--cli-region={region}", f"--log_group_id={group_id}",
            ]
            try:
                stream_result = subprocess.run(
                    stream_cmd, capture_output=True, text=True, timeout=30, env=_build_env(region)
                )
                if stream_result.returncode != 0:
                    continue
                stream_output = stream_result.stdout.strip()
                try:
                    decoder = json.JSONDecoder()
                    stream_data, _ = decoder.raw_decode(stream_output)
                except (json.JSONDecodeError, ValueError):
                    stream_data = []

                streams = stream_data if isinstance(stream_data, list) else stream_data.get("log_streams", [])
                for stream in streams[:3]:  # limit streams per group
                    stream_id = stream.get("log_stream_id", "")
                    stream_name = stream.get("log_stream_name", "")
                    if not stream_id:
                        continue

                    # Query actual log content with the real LTS ListLogs API
                    query_cmd = [
                        "hcloud", "LTS", "ListLogs", "--cli-output=json",
                        f"--cli-region={region}",
                        f"--log_group_id={group_id}",
                        f"--log_stream_id={stream_id}",
                        f"--start_time={start_ms}",
                        f"--end_time={end_ms}",
                        "--limit=100",
                    ]
                    try:
                        qr = subprocess.run(
                            query_cmd, capture_output=True, text=True, timeout=60, env=_build_env(region)
                        )
                        if qr.returncode != 0:
                            print(f"  [SKIP] LTS {group_name}/{stream_name}: query failed ({qr.stderr.strip()[:120]})")
                            continue
                        q_out = qr.stdout.strip()
                        q_data = None
                        try:
                            decoder = json.JSONDecoder()
                            q_data, _ = decoder.raw_decode(q_out)
                        except (json.JSONDecodeError, ValueError):
                            q_data = None

                        # Write the query result (log content) to a file. The
                        # response schema may vary across LTS versions, so save
                        # the parsed object (or raw text) without losing data.
                        out_file = os.path.join(output_dir, f"lts_{group_name}_{stream_name}.json")
                        if q_data is not None:
                            with open(out_file, "w") as f:
                                json.dump(q_data, f, indent=2, ensure_ascii=False)
                            logs = q_data.get("logs") if isinstance(q_data, dict) else None
                            if isinstance(logs, list):
                                print(f"  [OK] LTS {group_name}/{stream_name}: {len(logs)} log entries -> {os.path.basename(out_file)}")
                            else:
                                print(f"  [OK] LTS {group_name}/{stream_name}: response saved -> {os.path.basename(out_file)}")
                        else:
                            with open(out_file, "w") as f:
                                f.write(q_out)
                            print(f"  [OK] LTS {group_name}/{stream_name}: raw response saved -> {os.path.basename(out_file)}")
                        collected.append(out_file)
                    except Exception as e:
                        print(f"  [SKIP] LTS {group_name}/{stream_name}: query error ({e})")
                        continue

            except Exception:
                continue

        print(f"  [INFO] LTS log collection finished: {len(collected)} stream file(s) saved to {output_dir}")
    except Exception as e:
        print(f"  [INFO] LTS log collection skipped: {e}")
    return collected


def collect_events(since_time, until_time, output_dir):
    """Collect Kubernetes Events, filtered by experiment time window.

    Uses `kubectl get events --all-namespaces` to get all events,
    then filters by time window in Python (kubectl --since-time has limited
    support for events).
    """
    result = run_kubectl(["get", "events", "--all-namespaces", "-o", "json"], timeout=30)
    if not result or result.returncode != 0:
        print("  [SKIP] Kubernetes Events collection failed")
        return None

    try:
        all_events = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("  [SKIP] Failed to parse Kubernetes Events JSON")
        return None

    items = all_events.get("items", [])
    if not since_time:
        # No time filter, save all
        events_file = os.path.join(output_dir, "k8s_events.json")
        with open(events_file, "w") as f:
            json.dump(all_events, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Kubernetes Events: {len(items)} entries (unfiltered)")
        return events_file

    # Filter events by time window
    # Event timestamps can be in firstTimestamp, lastTimestamp, or eventTime
    filtered = []
    # Parse since_time to datetime for comparison
    # since_time format: 2026-09-23T09:41:06.160768+00:00
    try:
        since_dt = datetime.fromisoformat(since_time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        since_dt = None

    try:
        until_dt = datetime.fromisoformat(until_time.replace("Z", "+00:00")) if until_time else None
    except (ValueError, TypeError):
        until_dt = None

    for event in items:
        ts_str = (
            event.get("firstTimestamp")
            or event.get("lastTimestamp")
            or event.get("eventTime")
            or ""
        )
        if not ts_str:
            continue

        # Parse event timestamp
        try:
            event_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # Can't parse, include it anyway
            filtered.append(event)
            continue

        # Check if within window
        if since_dt and event_dt < since_dt:
            continue
        if until_dt and event_dt > until_dt:
            continue
        filtered.append(event)

    filtered_data = {"items": filtered, "total": len(filtered), "unfiltered_total": len(items)}
    events_file = os.path.join(output_dir, "k8s_events.json")
    with open(events_file, "w") as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Kubernetes Events: {len(filtered)} entries (filtered from {len(items)} total)")
    return events_file


def main():
    parser = argparse.ArgumentParser(description="Collect CCE Pod logs, LTS logs, and Kubernetes Events")
    parser.add_argument("--pods", help="Pod list (namespace/name, comma-separated)")
    parser.add_argument("--since", help="Start time (RFC3339)")
    parser.add_argument("--until", help="End time (RFC3339)")
    parser.add_argument("--output-dir", default="./collected_logs", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("[1/3] Collecting Pod logs...")
    pods = args.pods.split(",") if args.pods else []
    if pods:
        pod_logs_dir = os.path.join(args.output_dir, "pods")
        collect_pod_logs(pods, args.since, args.until, pod_logs_dir)
    else:
        print("  [SKIP] No Pod list specified")

    print("[2/3] Collecting LTS logs...")
    lts_logs_dir = os.path.join(args.output_dir, "lts")
    collect_lts_logs(args.since, args.until, lts_logs_dir)

    print("[3/3] Collecting Kubernetes Events...")
    collect_events(args.since, args.until, args.output_dir)

    print(f"\nLogs saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
