#!/usr/bin/env python3
"""
Monitor CCE Node and Pod status during AZ power outage experiment.

Provides functions to query node/pod status and detect state changes.
"""

import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone


def kubectl_json(args):
    """Run kubectl command and return parsed JSON."""
    cmd = ["kubectl"] + shlex.split(args) + ["-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def get_node_statuses(node_names=None):
    """Get status of all nodes or specific nodes.

    Returns: {node_name: {"ready": bool, "az": str, "allocatable_cpu": str}}
    """
    data = kubectl_json("get nodes")
    if not data:
        return {}

    result = {}
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        if node_names and name not in node_names:
            continue

        conditions = item.get("status", {}).get("conditions", [])
        ready = False
        for cond in conditions:
            if cond.get("type") == "Ready":
                ready = cond.get("status") == "True"

        labels = item["metadata"].get("labels", {})
        az = labels.get("topology.kubernetes.io/zone",
                       labels.get("failure-domain.beta.kubernetes.io/zone", "unknown"))

        allocatable = item.get("status", {}).get("allocatable", {})

        result[name] = {
            "ready": ready,
            "az": az,
            "allocatable_cpu": allocatable.get("cpu", "0"),
            "allocatable_memory": allocatable.get("memory", "0"),
        }

    return result


def get_pod_statuses(namespaces=None):
    """Get status of all pods or pods in specific namespaces.

    Returns: {"namespace/podname": {"phase": str, "node": str, "ready": bool}}
    """
    cmd = "get pods --all-namespaces"
    data = kubectl_json(cmd)
    if not data:
        return {}

    result = {}
    for item in data.get("items", []):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        key = f"{ns}/{name}"

        if namespaces and ns not in namespaces:
            continue

        phase = item.get("status", {}).get("phase", "Unknown")
        node = item.get("spec", {}).get("nodeName", "")

        # Check container ready status
        container_statuses = item.get("status", {}).get("containerStatuses", [])
        containers_ready = all(cs.get("ready", False) for cs in container_statuses) if container_statuses else False

        result[key] = {
            "phase": phase,
            "node": node,
            "containers_ready": containers_ready,
        }

    return result


def detect_state_changes(target_names, current_states, prev_states, resource_type):
    """Detect state changes between previous and current polling.

    Args:
        target_names: List of target resource names (None for all)
        current_states: Current state dict from get_node_statuses/get_pod_statuses
        prev_states: Previous state dict
        resource_type: "node" or "pod"

    Returns: List of {"name": str, "old": str, "new": str}
    """
    changes = []

    if resource_type == "node":
        for name, status in current_states.items():
            if target_names and name not in target_names:
                continue
            current = "Ready" if status.get("ready") else "NotReady"
            previous = prev_states.get(name, "Unknown")
            if current != previous:
                changes.append({"name": name, "old": previous, "new": current})

    elif resource_type == "pod":
        for key, status in current_states.items():
            current = status.get("phase", "Unknown")
            previous = prev_states.get(key, "Unknown")
            if current != previous:
                changes.append({"name": key, "old": previous, "new": current})

        # Check for pods that disappeared (deleted/evicted)
        for key, prev_phase in prev_states.items():
            if key not in current_states and prev_phase != "Terminating":
                changes.append({"name": key, "old": prev_phase, "new": "Deleted"})

    return changes


def get_rescheduling_summary(pod_timeline, rescheduling_events):
    """Summarize pod rescheduling events.

    Returns: {"total_rescheduled": int, "avg_reschedule_time": float, "details": list}
    """
    details = []
    for event in rescheduling_events:
        details.append({
            "timestamp": event["timestamp"],
            "pod": event["pod"],
            "event": event["event"],
        })

    return {
        "total_rescheduled": len(rescheduling_events),
        "details": details,
    }


def monitor_until_stable(target_node_names, timeout=300, interval=10):
    """Monitor nodes and pods until all nodes reach target state or timeout.

    Returns: (node_timeline, pod_timeline, rescheduling_events)
    """
    node_timeline = []
    pod_timeline = []
    rescheduling_events = []

    prev_node_states = {}
    prev_pod_states = {}

    # Initialize
    node_statuses = get_node_statuses(target_node_names)
    for name, status in node_statuses.items():
        prev_node_states[name] = "Ready" if status.get("ready") else "NotReady"

    pod_statuses = get_pod_statuses()
    for key, status in pod_statuses.items():
        prev_pod_states[key] = status.get("phase", "Unknown")

    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

        # Check node changes
        node_statuses = get_node_statuses(target_node_names)
        changes = detect_state_changes(target_node_names, node_statuses, prev_node_states, "node")
        for change in changes:
            node_timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **change,
            })
            prev_node_states[change["name"]] = change["new"]

        # Check pod changes
        pod_statuses = get_pod_statuses()
        pod_changes = detect_state_changes(None, pod_statuses, prev_pod_states, "pod")
        for change in pod_changes:
            pod_timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **change,
            })
            if change["new"] == "Running" and change["old"] in ("Pending", "Terminating"):
                rescheduling_events.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "pod": change["name"],
                    "event": "rescheduled",
                })
            prev_pod_states[change["name"]] = change["new"]

    return node_timeline, pod_timeline, rescheduling_events


if __name__ == "__main__":
    # Standalone monitoring mode
    import argparse
    parser = argparse.ArgumentParser(description="Monitor CCE resources")
    parser.add_argument("--nodes", help="Comma-separated node names to monitor")
    parser.add_argument("--timeout", type=int, default=300, help="Monitor timeout in seconds")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval in seconds")
    args = parser.parse_args()

    node_names = args.nodes.split(",") if args.nodes else None

    print(f"Monitoring for {args.timeout}s (interval={args.interval}s) ...")
    node_tl, pod_tl, resched = monitor_until_stable(node_names, args.timeout, args.interval)

    print(f"\nNode timeline ({len(node_tl)} events):")
    for event in node_tl:
        print(f"  {event['timestamp']}: {event['name']} {event['old']} → {event['new']}")

    print(f"\nPod timeline ({len(pod_tl)} events):")
    for event in pod_tl:
        print(f"  {event['timestamp']}: {event['name']} {event['old']} → {event['new']}")

    print(f"\nRescheduling events: {len(resched)}")
