#!/usr/bin/env python3
"""
generate_experiment.py — Generate experiment configuration files for ECS shutdown fault injection.

Creates a self-contained experiment directory with:
  - experiment.json: Machine-readable experiment template
  - README.md: Human-readable experiment overview and execution instructions

The experiment.json format is designed for Huawei Cloud ECS BatchStopServers / BatchStartServers.

Usage:
    python3 generate_experiment.py \\
        --targets "i-xxx,i-yyy" \\
        --cli-region cn-north-4 \\
        --duration 300 \\
        --output-dir ./experiments
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


def generate_experiment_json(targets, region, duration, scenario_name,
                              monitoring=None, stop_conditions=None):
    """Generate the experiment.json configuration."""
    target_ids = [t.strip() for t in targets.split(",")] if isinstance(targets, str) else targets

    experiment = {
        "schema_version": "1.0",
        "experiment_name": scenario_name or f"ecs-shutdown-experiment-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "description": "ECS shutdown fault injection experiment — simulates instance failure for chaos engineering",
        "platform": "huawei-cloud",
        "region": region,
        "created_at": datetime.now(timezone.utc).isoformat(),

        "scenario": {
            "type": "ecs-shutdown",
            "category": "resource-operation",
            "huawei_api": "ECS.BatchStopServers",
        },

        "targets": {
            "resource_type": "huawei-cloud:ecs:instance",
            "selection_mode": "EXPLICIT",
            "instance_ids": target_ids,
            "count": len(target_ids),
        },

        "actions": {
            "shutdown": {
                "action_id": "huawei:ecs:stop-instances",
                "api": "ECS BatchStopServers",
                "parameters": {
                    "os_stop": "SOFT",
                    "servers": [{"id": tid} for tid in target_ids],
                },
                "start_after": 0,
                "duration_seconds": duration,
            }
        },

        "rollback": {
            "action_id": "huawei:ecs:start-instances",
            "api": "ECS BatchStartServers",
            "parameters": {
                "servers": [{"id": tid} for tid in target_ids],
            },
            "description": "Start all target instances to restore pre-experiment state",
            "automatic": False,
        },

        "monitoring": monitoring or {
            "enabled": False,
            "source": "none",
            "description": "No monitoring configured. Set up CES alarms for stop conditions if needed.",
        },

        "stop_conditions": stop_conditions or [],

        "safety": {
            "max_duration_seconds": duration,
            "auto_rollback_on_failure": True,
            "require_confirmation": True,
        },
    }

    return experiment


def generate_readme(experiment, targets_info=None):
    """Generate the README.md for the experiment.

    All target information is passed in via targets_info (batch data),
    so there are no network calls inside the loop below — avoids N+1 pattern.
    """
    exp_name = experiment["experiment_name"]
    region = experiment["region"]
    target_ids = experiment["targets"]["instance_ids"]
    duration = experiment["actions"]["shutdown"]["duration_seconds"]
    created = experiment["created_at"]

    # Build target table (local processing only — no network calls in this loop)
    target_table = "| # | Instance ID | Name | AZ | Status |\n|---|---|---|---|---|\n"
    for i, tid in enumerate(target_ids, 1):
        info = targets_info.get(tid, {}) if targets_info else {}
        name = info.get("name", "—")
        az = info.get("availability_zone", "—")
        status = info.get("status", "—")
        target_table += f"| {i} | {tid} | {name} | {az} | {status} |\n"

    # Build flat CLI params for rollback reference (hcloud 7.2.x rejects --body;
    # BatchStartServers requires flat --os-start.servers.[N].id= params)
    flat_servers = " \\\n    ".join(
        f"--os-start.servers.{n}.id={tid}" for n, tid in enumerate(target_ids, start=1)
    )

    readme = f"""# ECS Shutdown Fault Injection Experiment

## Overview

| Field | Value |
|---|---|
| Experiment Name | {exp_name} |
| Platform | Huawei Cloud ECS |
| Region | {region} |
| Scenario | ECS Shutdown |
| Created | {created} |
| Duration | {duration} seconds ({duration // 60} min {duration % 60} sec) |

## Target Instances

{target_table}

## Experiment Actions

### 1. Shutdown (Fault Injection)
- **API**: `ECS BatchStopServers`
- **Stop Mode**: SOFT (graceful shutdown)
- **Duration**: {duration} seconds
- **Targets**: {len(target_ids)} instance(s)

### 2. Rollback (Recovery)
- **API**: `ECS BatchStartServers`
- **Mode**: Manual (not automatic)
- **Description**: Start all target instances to restore pre-experiment state

## Execution Instructions

### Prerequisites
1. hcloud CLI installed and configured with AK/SK
2. All target instances are in ACTIVE state
3. No AS scaling group will interfere (pause scaling if needed)
4. Monitoring/alerting configured (optional but recommended)

### Execute via dedicated execution workflow (Recommended)

This experiment should be executed through the dedicated execution workflow, which reads
`experiment.json` and performs the full execution flow:

```
pre-check → shutdown → poll status (ACTIVE→STOPPING→SHUTOFF) → wait → rollback → verify → report
```

The execution workflow provides:
- Instance state validation before shutdown
- Status polling during shutdown and recovery
- `--dry-run` mode for simulation
- `--auto-rollback` on failure
- Markdown execution report and execution-log.json

## Emergency Rollback

If the experiment needs to be aborted early, use the generated `rollback_experiment.sh`
script or run the rollback command directly:

```bash
# Option 1: Use the generated rollback script
bash rollback_experiment.sh

# Option 2: Run the rollback command directly
hcloud ECS BatchStartServers --cli-output=json \\
    --cli-region={region} \\
    {flat_servers}
```

## Safety Notes

- This experiment **does not start automatically**. Execute via the dedicated execution workflow.
- The rollback (instance start) is **not automatic**. The execution workflow handles rollback after the configured duration.
- For on-demand instances, basic resources (vCPU/memory) stop billing during shutdown.
- For yearly/monthly instances, billing continues during shutdown.
- Spot/bidding instances may be **released** instead of stopped — verify billing mode.

## Related

- **Huawei Cloud API**: [BatchStopServers](https://support.huaweicloud.com/api-ecs/ecs_02_0302.html)
"""

    return readme


def main():
    parser = argparse.ArgumentParser(
        description="Generate ECS shutdown experiment configuration files."
    )
    parser.add_argument("--targets", required=True,
                        help="Comma-separated ECS instance IDs")
    parser.add_argument("--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region")
    parser.add_argument("--duration", type=int, default=300,
                        help="Experiment duration in seconds (default: 300 = 5 min)")
    parser.add_argument("--scenario-name", help="Custom experiment name")
    parser.add_argument("--output-dir", default="./experiments",
                        help="Output directory for experiment files")
    parser.add_argument("--targets-info", help="JSON file with target instance details for README")
    args = parser.parse_args()

    # --- Validate target IDs (untrusted input gate) ---
    # Cloud instance IDs are alphanumeric + dash/underscore only. Reject
    # anything else (single quotes, spaces, shell metacharacters) so untrusted
    # input can neither poison the output directory name nor flow into later
    # shell/Python contexts. This is defense in depth: even though
    # deploy_experiment.sh now treats paths as data, keep names sane.
    target_ids = [t.strip() for t in args.targets.split(",")]
    if not target_ids or any(t == "" for t in target_ids):
        parser.error("--targets must be a non-empty comma-separated list of instance IDs")
    invalid = [t for t in target_ids if not re.fullmatch(r"[A-Za-z0-9_-]+", t)]
    if invalid:
        parser.error(
            "invalid instance ID(s): {} — IDs may only contain letters, digits, '-' and '_'".format(", ".join(invalid))
        )

    # Load targets info if provided (batch-loaded, no per-instance network calls)
    targets_info = None
    if args.targets_info and os.path.exists(args.targets_info):
        with open(args.targets_info) as f:
            data = json.load(f)
            items = data.get("items", data) if isinstance(data, dict) else data
            targets_info = {item["id"]: item for item in items if "id" in item}

    # Generate experiment.json
    experiment = generate_experiment_json(
        targets=args.targets,
        region=args.cli_region,
        duration=args.duration,
        scenario_name=args.scenario_name,
    )

    # Generate README.md
    readme = generate_readme(experiment, targets_info)

    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # Sanitize slug so the on-disk directory name never contains shell/Python
    # metacharacters (defense in depth — paths are data, keep names sane).
    target_slug = re.sub(r"[^A-Za-z0-9_-]", "_", args.targets.split(",")[0])[:12]
    exp_dir_name = f"{timestamp}-ecs-shutdown-{target_slug}"
    exp_dir = os.path.join(args.output_dir, exp_dir_name)
    os.makedirs(exp_dir, exist_ok=True)

    # Write files
    exp_json_path = os.path.join(exp_dir, "experiment.json")
    readme_path = os.path.join(exp_dir, "README.md")

    with open(exp_json_path, "w") as f:
        json.dump(experiment, f, indent=2, ensure_ascii=False)

    with open(readme_path, "w") as f:
        f.write(readme)

    # Output result
    result = {
        "status": "success",
        "experiment_dir": exp_dir,
        "files": {
            "experiment_json": exp_json_path,
            "readme_md": readme_path,
        },
        "experiment_name": experiment["experiment_name"],
        "target_count": experiment["targets"]["count"],
        "duration_seconds": args.duration,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
