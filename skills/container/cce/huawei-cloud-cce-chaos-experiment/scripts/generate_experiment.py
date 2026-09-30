#!/usr/bin/env python3
"""
Generate experiment.json and README.md for CCE AZ power outage experiment.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Generate CCE AZ power outage experiment config")
    parser.add_argument("--discovery-file", required=True, help="Path to discovery JSON")
    parser.add_argument("--validation-file", help="Path to validation JSON")
    parser.add_argument("--cluster-id", required=True, help="CCE cluster ID")
    parser.add_argument("--cluster-name", default="", help="CCE cluster name")
    parser.add_argument("--az", required=True, help="Target availability zone")
    parser.add_argument("--region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"))
    parser.add_argument("--duration", type=int, default=300, help="Experiment duration in seconds")
    parser.add_argument("--shutdown-mode", choices=["SOFT", "HARD"], default="SOFT", help="Shutdown mode")
    parser.add_argument("--output-dir", default="./experiments", help="Output directory (used when --experiment-dir is not given)")
    parser.add_argument("--experiment-dir", default=None, help="Use an existing experiment directory directly (skip auto-generating timestamp subdir). When set, --output-dir is ignored.")
    args = parser.parse_args()

    # Load discovery data
    with open(args.discovery_file) as f:
        discovery = json.load(f)

    # Load validation data if available
    validation = None
    if args.validation_file and os.path.exists(args.validation_file):
        with open(args.validation_file) as f:
            validation = json.load(f)

    target_nodes = discovery.get("target_nodes", [])
    if not target_nodes:
        print("Error: No target nodes found in discovery data", file=sys.stderr)
        sys.exit(1)

    # Generate experiment name
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    az_slug = args.az.replace("-", "")
    experiment_name = f"cce-az-power-{timestamp}"

    # Build node list for experiment.json
    node_list = []
    for node in target_nodes:
        node_list.append({
            "name": node["name"],
            "instance_id": node.get("instance_id", ""),
            "az": node["az"],
            "ready": node.get("ready", False),
        })

    # Collect pods to reschedule
    pods_to_reschedule = []
    for node in target_nodes:
        for pod in node.get("pods", []):
            pods_to_reschedule.append({
                "name": pod["name"],
                "namespace": pod["namespace"],
                "node": node["name"],
                "workload_kind": pod.get("workload_kind", ""),
                "workload_name": pod.get("workload_name", ""),
            })

    # Build experiment.json
    experiment = {
        "schema_version": "1.0",
        "experiment_name": experiment_name,
        "description": f"CCE AZ power outage experiment — simulate AZ {args.az} power failure by shutting down all CCE nodes",
        "platform": "huawei-cloud",
        "region": args.region,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": {
            "type": "cce-az-power-outage",
            "category": "az-power",
            "huawei_api": "ECS.BatchStopServers",
            "description": f"Simulate AZ {args.az} power outage by shutting down all CCE nodes in this AZ",
        },
        "cluster": {
            "cluster_id": args.cluster_id,
            "cluster_name": args.cluster_name or discovery.get("selected_cluster", {}).get("name", ""),
        },
        "az": args.az,
        "targets": {
            "resource_type": "huawei-cloud:cce:node",
            "selection_mode": "AZ",
            "az": args.az,
            "nodes": node_list,
            "count": len(node_list),
        },
        "actions": {
            "shutdown": {
                "action_id": "huawei:ecs:stop-instances",
                "api": "ECS BatchStopServers",
                "parameters": {
                    "os_stop": args.shutdown_mode,
                    "servers": [{"id": n["instance_id"]} for n in node_list if n["instance_id"]],
                },
                "duration_seconds": args.duration,
            }
        },
        "rollback": {
            "action_id": "huawei:ecs:start-instances",
            "api": "ECS BatchStartServers",
            "parameters": {
                "servers": [{"id": n["instance_id"]} for n in node_list if n["instance_id"]],
            },
            "description": "Start all target nodes to restore pre-experiment state",
            "automatic": True,
        },
        "monitoring": {
            "enabled": True,
            "node_status": True,
            "pod_rescheduling": True,
            "poll_interval_seconds": 10,
            "description": "Monitor Node status (Ready→NotReady) and Pod rescheduling (Running→Pending→Running)",
        },
        "pods_to_reschedule": pods_to_reschedule,
        "safety": {
            "max_duration_seconds": args.duration,
            "auto_rollback_on_failure": False,
            "require_confirmation": True,
            "check_pdb": True,
            "check_cross_az_capacity": True,
        },
    }

    # Determine output directory:
    # --experiment-dir (use directly) takes priority over --output-dir (auto-generate subdir)
    if args.experiment_dir:
        output_path = args.experiment_dir
    else:
        dir_name = f"{timestamp}-cce-az-power-{az_slug}"
        output_path = os.path.join(args.output_dir, dir_name)
    os.makedirs(output_path, exist_ok=True)

    # Write experiment.json
    exp_json_path = os.path.join(output_path, "experiment.json")
    with open(exp_json_path, "w") as f:
        json.dump(experiment, f, indent=2, ensure_ascii=False)

    # Write README.md
    readme_path = os.path.join(output_path, "README.md")

    # Build a native-parameter rollback command covering ALL target instances
    # (hcloud KooCLI does not support --body for ECS APIs; see Known Script
    # Issue #5). Matches execute_experiment.py / rollback_experiment.py.
    rollback_params = " \\\n".join(
        f"    --os-start.servers.{i}.id={n['instance_id']}" for i, n in enumerate(node_list, 1)
    )
    rollback_cmd = f"hcloud ECS BatchStartServers --cli-region={args.region} --cli-output=json \\\n{rollback_params}"

    readme_content = f"""# CCE AZ Power Outage Experiment — {experiment_name}

## Overview

| Item | Value |
|---|---|
| Experiment Name | {experiment_name} |
| Scenario | CCE AZ Power Outage (Node Shutdown) |
| Region | {args.region} |
| Target AZ | {args.az} |
| Target Nodes | {len(node_list)} |
| Pods to Reschedule | {len(pods_to_reschedule)} |
| Duration | {args.duration}s ({args.duration // 60}m {args.duration % 60}s) |
| Shutdown Mode | {args.shutdown_mode} |
| Created At | {experiment['created_at']} |

## Target Nodes

| Node Name | Instance ID | AZ | Ready |
|---|---|---|---|
"""
    for node in node_list:
        readme_content += f"| {node['name']} | {node['instance_id']} | {node['az']} | {'✅' if node['ready'] else '❌'} |\n"

    if pods_to_reschedule:
        readme_content += f"""
## Pods to Reschedule ({len(pods_to_reschedule)} pods)

| Namespace | Pod | Workload | Node |
|---|---|---|---|
"""
        for pod in pods_to_reschedule:
            wl = f"{pod['workload_kind']}/{pod['workload_name']}" if pod['workload_kind'] else "—"
            readme_content += f"| {pod['namespace']} | {pod['name']} | {wl} | {pod['node']} |\n"

    readme_content += f"""
## Execution

To execute this experiment, use the companion skill:

```bash
# Using the execute skill
python3 scripts/execute_experiment.py --experiment-dir {output_path}/

# With dry-run mode (no actual shutdown)
python3 scripts/execute_experiment.py --experiment-dir {output_path}/ --dry-run

# With auto-rollback on failure
python3 scripts/execute_experiment.py --experiment-dir {output_path}/ --auto-rollback
```

## Safety

- **Duration**: {args.duration}s — pods will be rescheduled to other AZ nodes during this period
- **Shutdown Mode**: {args.shutdown_mode} — {'graceful shutdown' if args.shutdown_mode == 'SOFT' else 'force shutdown'}
- **Auto Rollback**: Enabled — target nodes are started automatically after the duration elapses
- **PDB Check**: Enabled — PodDisruptionBudgets will be validated before execution
- **Cross-AZ Capacity**: Enabled — other AZs must have sufficient resources

## Rollback

Emergency rollback script will be generated during deployment. To manually rollback:

```bash
{rollback_cmd}
```
"""

    with open(readme_path, "w") as f:
        f.write(readme_content)

    # Output result
    result = {
        "status": "success",
        "experiment_dir": output_path,
        "files": {
            "experiment_json": exp_json_path,
            "readme_md": readme_path,
        },
        "experiment_name": experiment_name,
        "target_node_count": len(node_list),
        "pods_to_reschedule": len(pods_to_reschedule),
        "duration_seconds": args.duration,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
