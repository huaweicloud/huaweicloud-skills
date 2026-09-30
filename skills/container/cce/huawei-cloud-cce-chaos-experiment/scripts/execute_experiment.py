#!/usr/bin/env python3
"""
Execute CCE AZ power outage experiment.

6 phases: pre-check → shutdown → monitor → wait → rollback → verify
After execution, recommends log analysis via the built-in scripts/analyze_logs.py.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
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


# Add scripts dir to path for monitor_resources import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor_resources import (
    get_node_statuses,
    get_pod_statuses,
    detect_state_changes,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def run_hcloud(args, region, extra_params=None):
    """Run hcloud CLI command and return parsed JSON.

    Uses native hcloud parameter format (e.g. --os-stop.servers.1.id=xxx)
    instead of --body, which is not supported by hcloud KooCLI for ECS APIs.
    Uses list args (no shell=True) to prevent shell injection.

    Note: hcloud KooCLI may append diagnostic table text after the JSON output
    when an error occurs (e.g. "获取终端宽度失败" + a diagnostic table). This
    function extracts only the JSON portion to avoid json.loads failures.
    """
    cmd = ["hcloud"] + shlex.split(args) + [f"--cli-region={region}", "--cli-output=json"]
    if extra_params:
        cmd += shlex.split(extra_params)
    env = _build_env(region)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    if not result.stdout.strip():
        if result.returncode != 0:
            raise RuntimeError(f"hcloud command failed: {result.stderr}")
        return {}
    # Extract only the JSON object — hcloud may append non-JSON diagnostic text
    stdout = result.stdout.strip()
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Try to find the JSON object boundary (first { to matching })
        decoder = json.JSONDecoder()
        obj, end_idx = decoder.raw_decode(stdout)
        # Check if hcloud returned an error object even with exit code 0
        if isinstance(obj, dict) and "error" in obj:
            err = obj["error"]
            raise RuntimeError(f"hcloud API error: {err.get('code', 'unknown')} - {err.get('message', 'unknown')}")
        return obj


def batch_stop_servers(instance_ids, region, os_stop="SOFT"):
    """Shutdown ECS instances using native hcloud parameter format."""
    params = f"--os-stop.type={os_stop}"
    for i, iid in enumerate(instance_ids, 1):
        params += f" --os-stop.servers.{i}.id={iid}"
    return run_hcloud("ECS BatchStopServers", region, params)


def batch_start_servers(instance_ids, region):
    """Start ECS instances using native hcloud parameter format."""
    params = ""
    for i, iid in enumerate(instance_ids, 1):
        params += f" --os-start.servers.{i}.id={iid}"
    return run_hcloud("ECS BatchStartServers", region, params)


def main():
    parser = argparse.ArgumentParser(description="Execute CCE AZ power outage experiment")
    parser.add_argument("--experiment-dir", required=True, help="Experiment directory path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without actual API calls")
    parser.add_argument("--auto-rollback", action="store_true", help="Auto-rollback on failure")
    args = parser.parse_args()

    # Load experiment.json
    exp_path = os.path.join(args.experiment_dir, "experiment.json")
    if not os.path.exists(exp_path):
        print(f"Error: experiment.json not found in {args.experiment_dir}", file=sys.stderr)
        sys.exit(1)

    with open(exp_path) as f:
        exp = json.load(f)

    exp_name = exp["experiment_name"]
    region = exp.get("region", "cn-north-4")
    target_az = exp.get("az", "")
    duration = exp["actions"]["shutdown"].get("duration_seconds", 300)
    os_stop = exp["actions"]["shutdown"]["parameters"].get("os_stop", "SOFT")
    nodes = exp["targets"]["nodes"]
    node_names = [n["name"] for n in nodes]
    instance_ids = [n["instance_id"] for n in nodes if n.get("instance_id")]

    print()
    print("=" * 60)
    print(f"  CCE AZ Power Outage Experiment: {exp_name}")
    print(f"  Region: {region}")
    print(f"  Target AZ: {target_az}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Duration: {duration}s")
    print(f"  Dry run: {args.dry_run}")
    print("=" * 60)

    # Initialize execution log
    log = {
        "experiment_name": exp_name,
        "region": region,
        "az": target_az,
        "started_at": now_iso(),
        "phases": {},
        "node_timeline": [],
        "pod_timeline": [],
        "rescheduling_events": [],
        "overall_result": "unknown",
    }

    # ========== Phase 1: Pre-check ==========
    print()
    print("[1/6] Pre-check: verifying all nodes are Ready ...")

    prev_node_states = {}
    phase_start = now_iso()

    node_statuses = get_node_statuses(node_names)
    all_ready = True
    for name, status in node_statuses.items():
        ready = status.get("ready", False)
        prev_node_states[name] = "Ready" if ready else "NotReady"
        marker = "✓" if ready else "✗"
        print(f"  [{marker}] {name}: {'Ready' if ready else 'NotReady'}")
        if not ready:
            all_ready = False

    if not all_ready:
        print("  ✗ Pre-check FAILED — some nodes are not Ready")
        log["phases"]["pre_check"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "failed"}
        log["overall_result"] = "failed"
        log["completed_at"] = now_iso()
        _write_log(log, args.experiment_dir)
        sys.exit(1)

    print("  ✓ Pre-check passed")
    log["phases"]["pre_check"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "passed"}

    # Record initial pod states
    prev_pod_states = {}
    pod_statuses = get_pod_statuses()
    for key, status in pod_statuses.items():
        prev_pod_states[key] = status.get("phase", "Unknown")

    # ========== Phase 2: Shutdown ==========
    print()
    print(f"[2/6] Shutdown: executing BatchStopServers (os_stop={os_stop}) ...")

    phase_start = now_iso()
    if args.dry_run:
        print("  [DRY RUN] Skipping actual shutdown")
    else:
        try:
            result = batch_stop_servers(instance_ids, region, os_stop)
            job_id = result.get("job_id", "")
            print(f"  ✓ BatchStopServers command sent (job_id: {job_id})")
        except Exception as e:
            print(f"  ✗ Shutdown failed: {e}")
            log["phases"]["shutdown"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "failed", "error": str(e)}
            if args.auto_rollback:
                print("  Auto-rollback triggered. Starting nodes ...")
                _do_rollback(instance_ids, region, args.dry_run, log, args.experiment_dir)
            log["overall_result"] = "failed"
            log["completed_at"] = now_iso()
            _write_log(log, args.experiment_dir)
            sys.exit(1)

    log["phases"]["shutdown"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "success"}

    # ========== Phase 3: Monitor shutdown ==========
    print()
    print("[3/6] Monitor: waiting for nodes to become NotReady ...")

    phase_start = now_iso()
    monitor_timeout = 300
    monitor_interval = 10
    elapsed = 0

    while elapsed < monitor_timeout:
        time.sleep(monitor_interval)
        elapsed += monitor_interval

        node_statuses = get_node_statuses(node_names)
        changes = detect_state_changes(node_names, node_statuses, prev_node_states, "node")
        for change in changes:
            log["node_timeline"].append({
                "timestamp": now_iso(),
                "node": change["name"],
                "old_status": change["old"],
                "new_status": change["new"],
            })
            print(f"  Node {change['name']}: {change['old']} → {change['new']}")
            prev_node_states[change["name"]] = change["new"]

        # Check pod changes
        pod_statuses = get_pod_statuses()
        pod_changes = detect_state_changes(None, pod_statuses, prev_pod_states, "pod")
        for change in pod_changes:
            log["pod_timeline"].append({
                "timestamp": now_iso(),
                "pod": change["name"],
                "old_phase": change["old"],
                "new_phase": change["new"],
            })
            prev_pod_states[change["name"]] = change["new"]

        all_notready = all(prev_node_states.get(n) == "NotReady" for n in node_names)
        if all_notready:
            break

    print(f"  ✓ All nodes NotReady (elapsed: {elapsed}s)")
    log["phases"]["monitor"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "all_notready", "elapsed_seconds": elapsed}

    # ========== Phase 4: Wait ==========
    print()
    print(f"[4/6] Wait: experiment duration {duration}s ...")

    phase_start = now_iso()
    for i in range(0, duration, 30):
        remaining = duration - i
        print(f"  ... {min(i + 30, duration)}s / {duration}s elapsed")
        time.sleep(min(30, remaining))

        # Continue monitoring pod changes
        pod_statuses = get_pod_statuses()
        pod_changes = detect_state_changes(None, pod_statuses, prev_pod_states, "pod")
        for change in pod_changes:
            log["pod_timeline"].append({
                "timestamp": now_iso(),
                "pod": change["name"],
                "old_phase": change["old"],
                "new_phase": change["new"],
            })
            if change["new"] == "Running" and change["old"] in ("Pending", "Terminating"):
                log["rescheduling_events"].append({
                    "timestamp": now_iso(),
                    "pod": change["name"],
                    "event": "rescheduled",
                    "new_phase": "Running",
                })
            prev_pod_states[change["name"]] = change["new"]

    print(f"  ✓ Wait complete ({duration}s)")
    log["phases"]["wait"] = {"started_at": phase_start, "completed_at": now_iso(), "duration": duration}

    # ========== Phase 5: Rollback ==========
    print()
    print("[5/6] Rollback: executing BatchStartServers ...")

    phase_start = now_iso()
    if args.dry_run:
        print("  [DRY RUN] Skipping actual start")
    else:
        try:
            result = batch_start_servers(instance_ids, region)
            job_id = result.get("job_id", "")
            print(f"  ✓ BatchStartServers command sent (job_id: {job_id})")
        except Exception as e:
            print(f"  ✗ Rollback failed: {e}")
            log["phases"]["rollback"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "failed", "error": str(e)}
            log["overall_result"] = "failed"
            log["completed_at"] = now_iso()
            _write_log(log, args.experiment_dir)
            sys.exit(1)

    log["phases"]["rollback"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "success"}

    # ========== Phase 6: Verify ==========
    print()
    print("[6/6] Verify: waiting for nodes to become Ready ...")

    phase_start = now_iso()
    verify_timeout = 300
    elapsed = 0

    while elapsed < verify_timeout:
        time.sleep(monitor_interval)
        elapsed += monitor_interval

        node_statuses = get_node_statuses(node_names)
        changes = detect_state_changes(node_names, node_statuses, prev_node_states, "node")
        for change in changes:
            log["node_timeline"].append({
                "timestamp": now_iso(),
                "node": change["name"],
                "old_status": change["old"],
                "new_status": change["new"],
            })
            print(f"  Node {change['name']}: {change['old']} → {change['new']}")
            prev_node_states[change["name"]] = change["new"]

        all_ready = all(prev_node_states.get(n) == "Ready" for n in node_names)
        if all_ready:
            break

    # Check pod recovery
    pod_statuses = get_pod_statuses()
    running_pods = sum(1 for s in pod_statuses.values() if s.get("phase") == "Running")

    if all_ready:
        print(f"  ✓ All nodes Ready (elapsed: {elapsed}s)")
        print(f"  ✓ Running pods: {running_pods}")
        log["phases"]["verify"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "all_ready", "elapsed_seconds": elapsed, "running_pods": running_pods}
        log["overall_result"] = "success"
    else:
        print(f"  ✗ Verification timeout — some nodes not Ready")
        log["phases"]["verify"] = {"started_at": phase_start, "completed_at": now_iso(), "result": "timeout", "elapsed_seconds": elapsed}
        log["overall_result"] = "failed"

    log["completed_at"] = now_iso()
    total_time = int((datetime.fromisoformat(log["completed_at"]) - datetime.fromisoformat(log["started_at"])).total_seconds())
    log["total_duration_seconds"] = total_time

    _write_log(log, args.experiment_dir)

    print()
    print("=" * 60)
    print(f"  Experiment result: {log['overall_result']}")
    print(f"  Total time: {total_time}s")
    print("=" * 60)

    # ========== Post-Execution: Log Analysis Recommendation ==========
    _print_log_analysis_recommendation(args.experiment_dir)


def _print_log_analysis_recommendation(exp_dir):
    """Print recommendation to run the built-in log analysis scripts."""
    log_path = os.path.join(exp_dir, "execution-log.json")

    print()
    print("=" * 60)
    print("  📋 日志分析推荐 (Log Analysis Recommendation)")
    print("=" * 60)
    print()
    print("  实验已完成！建议运行本 skill 内置的日志分析脚本 scripts/analyze_logs.py")
    print("  对实验日志进行深入分析，获取以下洞察：")
    print()
    print("  • Pod 重调度时间线与影响评估")
    print("  • 应用日志中的错误模式检测 (ERROR/Exception/timeout/5xx)")
    print("  • 业务影响评估与 RTO 分析")
    print("  • 改进建议（PDB 配置、副本分布等）")
    print()
    print("  ── 使用方法 ──")
    print()
    print("  运行日志分析脚本：")
    print(f"    python3 scripts/analyze_logs.py --experiment-dir {exp_dir}")
    print()
    print(f"  实验日志路径: {log_path}")
    print(f"  实验目录:     {exp_dir}")
    print()
    print("  ── 完整工作流 ──")
    print()
    print("  prepare → execute → 【log-analysis】 ← 当前阶段")
    print()
    print("=" * 60)


def _do_rollback(instance_ids, region, dry_run, log, exp_dir):
    """Perform emergency rollback."""
    if dry_run:
        print("  [DRY RUN] Skipping rollback")
        return
    try:
        batch_start_servers(instance_ids, region)
        print("  ✓ Rollback (BatchStartServers) sent")
    except Exception as e:
        print(f"  ✗ Rollback failed: {e}")


def _write_log(log, exp_dir):
    """Write execution log."""
    log_path = os.path.join(exp_dir, "execution-log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\nExecution log written to: {log_path}")


if __name__ == "__main__":
    main()
