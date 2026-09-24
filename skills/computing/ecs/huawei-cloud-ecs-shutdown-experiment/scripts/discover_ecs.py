#!/usr/bin/env python3
"""
discover_ecs.py — Discover ECS instances for shutdown experiment.

Queries Huawei Cloud ECS instances via hcloud CLI and returns key attributes
needed for fault injection experiment preparation.

Usage:
    python3 discover_ecs.py --cli-region cn-north-4
    python3 discover_ecs.py --cli-region cn-north-4 --az cn-north-4a
    python3 discover_ecs.py --cli-region cn-north-4 --name-pattern "web-"
    python3 discover_ecs.py --cli-region cn-north-4 --ids "i-xxx,i-yyy"
    python3 discover_ecs.py --cli-region cn-north-4 --status ACTIVE

Output: JSON array of ECS instances with id, name, status, az, flavor, 
        charging_mode, and other key fields.
"""

import argparse
import json
import os
import subprocess
import sys

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
    # Ensure region is passed as a CLI parameter (--cli-region is the hcloud convention)
    if region and "--cli-region" not in args:
        cmd.append(f"--cli-region={region}")
    env = _build_env(region)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=60
        )
        if result.returncode != 0:
            print(f"Error running hcloud: {result.stderr.strip()}", file=sys.stderr)
            return None
        # hcloud JSON output may have leading log lines; find the JSON part
        output = result.stdout.strip()
        # Try to parse as JSON directly
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Try to find JSON array/object in output
            for i in range(len(output)):
                if output[i] in "[{":
                    try:
                        return json.loads(output[i:])
                    except json.JSONDecodeError:
                        continue
            print(f"Could not parse hcloud output as JSON", file=sys.stderr)
            return None
    except FileNotFoundError:
        print("hcloud CLI not found. Please install KooCLI (Huawei Cloud CLI) first:\n"
              "  Download and run the official installation script from the Huawei Cloud\n"
              "  KooCLI documentation page.\n"
              "  See references/cli-installation-guide.md for details.", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("hcloud command timed out", file=sys.stderr)
        return None


def discover_ecs(region, az=None, name_pattern=None, ids=None, status=None):
    """Discover ECS instances matching the given filters.

    Uses a batch-query-then-local-filter pattern: queries ListServersDetails
    with explicit paging (default page size is 25, max 1000 per request), then
    applies all filters locally in Python. No per-instance network calls
    (avoids N+1 query pattern).
    """
    # Batch-query then local-filter, with explicit paging: the API default
    # page size is 25 (max 1000 per request). Without paging, instances
    # beyond the first page would be silently missing from discovery.
    servers = []
    limit = 1000
    offset = 1

    while True:
        args = ["ECS", "ListServersDetails", f"--limit={limit}", f"--offset={offset}", "--cli-output=json"]
        data = run_hcloud(args, region=region)
        if data is None:
            return []

        # Normalize: hcloud may return {"servers": [...]} or a direct list
        if isinstance(data, dict):
            page = data.get("servers", data.get("items", []))
            total = int(data.get("count", 0) or 0)
        elif isinstance(data, list):
            page = data
            total = len(page)
        else:
            page = []
            total = 0

        servers.extend(page)

        # offset is a 1-based page number; continue while more pages remain
        pages = (total + limit - 1) // limit if total else 1
        if offset >= pages or not page:
            break
        offset += 1

    # Pre-compute filter sets for efficient local filtering
    ids_set = set(ids) if ids else None

    results = []
    for srv in servers:
        # Extract key fields (local processing only — no network calls in this loop)
        server_id = srv.get("id", "")
        server_name = srv.get("name", "")
        server_status = srv.get("status", "")
        server_az = srv.get("OS-EXT-AZ:availability_zone", srv.get("availability_zone", ""))
        flavor = srv.get("flavor", {})
        if isinstance(flavor, dict):
            flavor_id = flavor.get("id", "")
        else:
            flavor_id = str(flavor)

        # Charging mode: look in metadata or OS-EXT-SRV-ATTR fields
        metadata = srv.get("metadata", {})
        charging_mode = srv.get("charging_mode", metadata.get("charging_mode", "unknown"))

        # Tags
        tags = srv.get("tags", [])

        # Power state
        power_state = srv.get("OS-EXT-STS:power_state", srv.get("power_state", -1))

        instance = {
            "id": server_id,
            "name": server_name,
            "status": server_status,
            "availability_zone": server_az,
            "flavor_id": flavor_id,
            "charging_mode": charging_mode,
            "power_state": power_state,
            "tags": tags,
        }

        # Apply filters locally (no network calls)
        if ids_set and server_id not in ids_set:
            continue
        if az and server_az != az:
            continue
        if name_pattern and name_pattern not in server_name:
            continue
        if status and server_status != status:
            continue

        results.append(instance)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Discover ECS instances for shutdown experiment preparation."
    )
    parser.add_argument(
        "--cli-region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
        help="Huawei Cloud region (default: cn-north-4 or HW_REGION_NAME)"
    )
    parser.add_argument("--az", help="Filter by availability zone")
    parser.add_argument("--name-pattern", help="Filter by name substring match")
    parser.add_argument("--ids", help="Comma-separated list of ECS IDs to filter")
    parser.add_argument("--status", help="Filter by status (ACTIVE, SHUTOFF, etc.)")
    parser.add_argument(
        "--output", choices=["json", "table"], default="json",
        help="Output format (default: json)"
    )
    args = parser.parse_args()

    ids_list = None
    if args.ids:
        ids_list = [i.strip() for i in args.ids.split(",")]

    instances = discover_ecs(
        region=args.cli_region,
        az=args.az,
        name_pattern=args.name_pattern,
        ids=ids_list,
        status=args.status,
    )

    if args.output == "json":
        print(json.dumps({"total": len(instances), "items": instances}, indent=2, ensure_ascii=False))
    else:
        # Table output
        print(f"{'ID':<40} {'Name':<20} {'Status':<10} {'AZ':<15} {'Flavor':<15} {'Charging':<10}")
        print("-" * 115)
        for inst in instances:
            print(f"{inst['id']:<40} {inst['name']:<20} {inst['status']:<10} "
                  f"{inst['availability_zone']:<15} {inst['flavor_id']:<15} {inst['charging_mode']:<10}")
        print(f"\nTotal: {len(instances)}")


if __name__ == "__main__":
    main()
