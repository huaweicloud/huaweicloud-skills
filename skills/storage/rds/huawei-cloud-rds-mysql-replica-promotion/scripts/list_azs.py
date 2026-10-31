#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""List the availability zones of a Huawei Cloud region as structured JSON.

Overview:
    This script discovers the availability zones of a region via the
    `hcloud` (KooCLI) command line tool and prints them as pretty JSON to
    stdout. It is the Step 4 tool of the SKILL workflow: the Agent renders
    the JSON as a table and asks the user to pick the standby AZ. By
    default the standby AZ should differ from the instance's current AZ
    (cross-AZ DR), but the same AZ is also allowed (shortest intra-AZ
    latency).

Detailed Description:
    The region's project id is resolved automatically via
    KeystoneListAuthProjects instead of a --project-id argument. Zones are
    queried with `ECS NovaListAvailabilityZones` (verified service/command
    pairing) and the `availabilityZoneInfo` list is printed. The script is
    read-only: it never mutates anything and writes no report file. All
    shared behavior (hcloud execution, project id resolution, JSON
    formatting) lives in rds_common.

Workflow:
    1. Parse the required --region argument.
    2. Resolve the project id of the region.
    3. Call ECS NovaListAvailabilityZones.
    4. Print the zones as pretty JSON to stdout.

Dependencies:
    - Python 3.9+ standard library only (argparse, logging, sys).
    - rds_common (same directory, shared helpers).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated.
"""

from __future__ import annotations

import argparse
import logging
import sys

import rds_common as common

LOGGER = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add the region option only, keeping the help manual minimal.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--region", "cn-north-4"])
        >>> args.region == "cn-north-4"
        True
    """
    parser = argparse.ArgumentParser(
        prog="list_azs",
        description=(
            "List the availability zones of a region as pretty JSON via "
            "the hcloud CLI."
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Required. Cloud region (e.g. cn-north-4).",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Resolve the project id and print the availability zone list.

    1. Resolve the region project id via KeystoneListAuthProjects.
    2. Call ECS NovaListAvailabilityZones for the region.
    3. Print the zones as pretty JSON to stdout.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 on success, 1 on failure).

    Examples:
        # Requires hcloud credentials:
        # >>> run(args)
        1
    """
    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        prefix = [
            "ECS",
            "--cli-region={}".format(args.region),
            "--project_id={}".format(project_id),
        ]
        payload = common.run_hcloud(
            prefix + [common.CMD_LIST_AVAILABILITY_ZONES],
            common.DEFAULT_TIMEOUT,
        )
        print(common.format_discovery_json([], payload.get("availabilityZoneInfo") or []))
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1
    return 0


def main() -> int:
    """Run the availability zone discovery workflow.

    1. Parse arguments and set up logging.
    2. Delegate to run() for resolution and printing.

    Args:
        None

    Returns:
        int: Exit code (0 on success, 1 on failure).

    Examples:
        # Running the script requires hcloud credentials:
        # >>> main()
        1
    """
    args = build_arg_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
