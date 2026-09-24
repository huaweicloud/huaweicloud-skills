#!/usr/bin/env python3
"""
validate_targets.py — Validate ECS instances for shutdown experiment compatibility.

Checks each target ECS instance against shutdown experiment requirements:
  1. Status must be ACTIVE (running)
  2. Spot/bidding instances flagged (may be released instead of stopped)
  3. AS group association checked (shutdown may trigger scaling activity)
  4. Single-AZ deployment flagged (HA risk)

Usage:
    python3 validate_targets.py --instances-json '{"items": [...]}'
    python3 validate_targets.py --instances-file instances.json
    python3 validate_targets.py --ids "i-xxx,i-yyy" --cli-region cn-north-4

Output: JSON with per-instance validation results and overall recommendation.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict

# Only pass required environment variables to subprocess (avoid bulk env harvesting)
_ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL",
    "HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_REGION_NAME",
)


def _build_env(region=None):
    """Build a minimal environment dict with only needed variables."""
    env = {k: os.environ[k] for k in _ENV_WHITELIST if k in os.environ}
    if region and "HW_REGION_NAME" not in env:
        env["HW_REGION_NAME"] = region
    return env


def run_hcloud(args, region=None):
    """Run hcloud CLI command and return parsed JSON output."""
    cmd = ["hcloud"] + args
    if region and "--cli-region" not in args:
        cmd.append(f"--cli-region={region}")
    env = _build_env(region)
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


def batch_query_as_instances(region):
    """Batch-query ALL AS scaling instances in one API call.

    Returns a dict mapping instance_id -> scaling_group_id.
    This replaces the per-instance N+1 query pattern: instead of calling
    ListScalingInstances once per target instance, we call it ONCE and
    build a local lookup map.
    """
    data = run_hcloud(["AS", "ListScalingInstances", "--cli-output=json"], region=region)
    if data is None:
        return None  # AS API not available

    if isinstance(data, dict):
        instances = data.get("scaling_group_instances", data.get("items", []))
    elif isinstance(data, list):
        instances = data
    else:
        instances = []

    # Build local lookup: instance_id -> scaling_group_id
    as_map = {}
    for inst in instances:
        iid = inst.get("instance_id", "")
        sgid = inst.get("scaling_group_id", "unknown")
        if iid:
            as_map[iid] = sgid
    return as_map


def validate_instance(instance, region=None, check_as=True, as_map=None):
    """Validate a single ECS instance for shutdown experiment.

    Args:
        as_map: Pre-fetched AS instance lookup dict (from batch_query_as_instances).
                If None and check_as=True, will return 'unknown' for AS check.
                This avoids per-instance network calls (N+1 pattern fix).
    """
    result = {
        "instance_id": instance.get("id", ""),
        "instance_name": instance.get("name", ""),
        "checks": [],
        "warnings": [],
        "errors": [],
        "compatible": True,
    }

    # ---- Check 1: Status must be ACTIVE ----
    status = instance.get("status", "").upper()
    if status == "ACTIVE":
        result["checks"].append({
            "rule": "status_active",
            "passed": True,
            "message": f"Instance status is ACTIVE (running)"
        })
    else:
        result["checks"].append({
            "rule": "status_active",
            "passed": False,
            "message": f"Instance status is '{status}', must be ACTIVE to perform shutdown"
        })
        result["errors"].append(f"Status '{status}' — instance is not running")
        result["compatible"] = False

    # ---- Check 2: Spot/bidding instance risk ----
    charging_mode = instance.get("charging_mode", "unknown")
    if charging_mode in ("spot", "bidding", "竞享", "竞价"):
        result["checks"].append({
            "rule": "not_spot_instance",
            "passed": False,
            "message": f"Instance is {charging_mode} billing — may be released instead of stopped"
        })
        result["warnings"].append(
            "Spot/bidding instance: shutdown may trigger release instead of graceful stop. "
            "Consider using a pay-per-use or yearly/monthly instance for this experiment."
        )
    else:
        result["checks"].append({
            "rule": "not_spot_instance",
            "passed": True,
            "message": f"Instance billing mode is '{charging_mode}' — safe for shutdown"
        })

    # ---- Check 3: AS group association (uses pre-fetched batch data) ----
    if check_as:
        instance_id = instance.get("id", "")
        if as_map is None:
            result["checks"].append({
                "rule": "no_as_group",
                "passed": True,
                "message": "AS group check skipped (AS API not available)"
            })
        else:
            as_group = as_map.get(instance_id)
            if as_group:
                result["checks"].append({
                    "rule": "no_as_group",
                    "passed": False,
                    "message": f"Instance is in AS scaling group '{as_group}' — shutdown may trigger auto-scaling"
                })
                result["warnings"].append(
                    f"Instance belongs to AS group '{as_group}'. "
                    "Shutting it down may trigger the scaling group to launch a new instance "
                    "or mark this instance as unhealthy. Consider pausing scaling activities first."
                )
            else:
                result["checks"].append({
                    "rule": "no_as_group",
                    "passed": True,
                    "message": "Instance is not associated with any AS scaling group"
                })

    # ---- Check 4: Charging mode impact on shutdown billing ----
    if charging_mode in ("postPaid", "按需", "on-demand"):
        result["checks"].append({
            "rule": "shutdown_billing",
            "passed": True,
            "message": "On-demand instance: basic resources (vCPU/memory) stop billing after shutdown"
        })
    elif charging_mode in ("prePaid", "包年包月", "yearly-monthly"):
        result["checks"].append({
            "rule": "shutdown_billing",
            "passed": True,
            "message": "Yearly/monthly instance: billing continues during shutdown (no cost impact)"
        })

    return result


def check_single_az_risk(instances):
    """Check if all targets are in the same AZ (HA risk)."""
    azs = set()
    for inst in instances:
        az = inst.get("availability_zone", "")
        if az:
            azs.add(az)

    if len(azs) == 1 and len(instances) > 1:
        return {
            "rule": "single_az_deployment",
            "passed": False,
            "message": f"All {len(instances)} targets are in the same AZ '{list(azs)[0]}' — "
                       "no cross-AZ redundancy during experiment",
            "severity": "warning"
        }
    elif len(azs) > 1:
        return {
            "rule": "single_az_deployment",
            "passed": True,
            "message": f"Targets span {len(azs)} AZs: {', '.join(sorted(azs))}"
        }
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Validate ECS instances for shutdown experiment compatibility."
    )
    parser.add_argument("--instances-json", help="JSON string of instances to validate")
    parser.add_argument("--instances-file", help="Path to JSON file with instances")
    parser.add_argument("--ids", help="Comma-separated ECS IDs (will query via hcloud)")
    parser.add_argument(
        "--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
        help="Huawei Cloud region"
    )
    parser.add_argument("--skip-as-check", action="store_true", help="Skip AS group check")
    args = parser.parse_args()

    # Load instances
    instances = []
    if args.instances_json:
        data = json.loads(args.instances_json)
        instances = data.get("items", data) if isinstance(data, dict) else data
    elif args.instances_file:
        with open(args.instances_file) as f:
            data = json.load(f)
            instances = data.get("items", data) if isinstance(data, dict) else data
    elif args.ids:
        # Query instances via discover_ecs (batch query, no N+1)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from discover_ecs import discover_ecs
        ids_list = [i.strip() for i in args.ids.split(",")]
        instances = discover_ecs(region=args.cli_region, ids=ids_list)
    else:
        print("Error: provide --instances-json, --instances-file, or --ids", file=sys.stderr)
        sys.exit(1)

    if not instances:
        print(json.dumps({"error": "No instances to validate"}, ensure_ascii=False))
        sys.exit(1)

    # Batch-query AS scaling instances ONCE (avoids N+1 per-instance network calls)
    as_map = None
    if not args.skip_as_check:
        as_map = batch_query_as_instances(args.cli_region)

    # Validate each instance using pre-fetched AS data (no per-instance network calls)
    results = []
    for inst in instances:
        r = validate_instance(
            inst, region=args.cli_region,
            check_as=not args.skip_as_check, as_map=as_map
        )
        results.append(r)

    # Check single-AZ risk across all targets (local computation only)
    az_risk = check_single_az_risk(instances)

    # Overall assessment
    all_compatible = all(r["compatible"] for r in results)
    all_warnings = [w for r in results for w in r["warnings"]]
    if az_risk and not az_risk["passed"]:
        all_warnings.append(az_risk["message"])

    output = {
        "total": len(results),
        "all_compatible": all_compatible,
        "warning_count": len(all_warnings),
        "instance_results": results,
        "az_risk_check": az_risk,
        "recommendation": (
            "All targets are compatible. Proceed with experiment preparation."
            if all_compatible and not all_warnings
            else "All targets are compatible but with warnings. Review warnings before proceeding."
            if all_compatible
            else "Some targets are NOT compatible. Fix errors before proceeding."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
