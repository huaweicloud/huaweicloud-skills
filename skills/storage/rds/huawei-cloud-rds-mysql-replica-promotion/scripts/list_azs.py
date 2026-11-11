#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""List the availability zones usable by a flavor as structured JSON.

Overview:
    This script lists the availability zones where a given RDS for MySQL
    flavor can host the standby node, via the `hcloud` (KooCLI) command
    line tool, and prints them as pretty JSON to stdout. It is the standby
    AZ discovery tool of the SKILL workflow: the Agent renders the JSON as
    a table and asks the user to pick the target availability zone.

Detailed Description:
    Availability is flavor-scoped, not region-scoped: ECS
    NovaListAvailabilityZones reports an AZ as available even when the
    target RDS flavor is unsupported or sold out there, and the single
    flavor's az_status differs from its HA counterpart for some specs.
    The script therefore reads `az_status` and `az_desc` from the HA flavor
    entry of RDS ListFlavors and never uses the ECS AZ list.

    The caller passes database name, version name and spec code. The spec
    code may be the single spec: the script detects the returned
    instance_mode and derives the HA spec with the shared rule (append
    `.ha` for dedicated/general, replace `.single` with `.ha` for ARM), so
    a single instance spec is accepted and converted automatically. Only
    entries with instance_mode `ha` are treated as primary/standby
    flavors; `replica` and `cluster` entries are never selected.

    When an optional --instance-id is given, the instance's current AZ is
    read from ListInstances and marked in the output, so the Agent can tell
    the user whether a candidate is cross-AZ or same-AZ. When no AZ is
    `normal` for the flavor, the script reports that explicitly and exits
    non-zero instead of printing an empty table. The script is read-only:
    it never mutates anything and writes no report file.

Workflow:
    1. Parse database name, version name, spec code, region and optional
       instance id.
    2. Resolve the project id and query ListFlavors for the given spec.
    3. Detect the flavor's instance_mode; derive the HA spec when the given
       spec is a single flavor and query it.
    4. Build one row per AZ with its name, status, availability and whether
       it is the instance's current AZ.
    5. Print the rows as pretty JSON, or report that no AZ is available.

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

    1. Add the required database name, version name, spec code and region.
    2. Add the optional instance id used to mark the current AZ.
    3. Register the platform-injected `--domain_id` and `--x_user_auth_token`
       options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--region", "cn-north-4",
        ...     "--database-name", "MySQL", "--version-name", "8.0",
        ...     "--spec-code", "rds.mysql.n1.large.2.ha"])
        >>> args.spec_code
        'rds.mysql.n1.large.2.ha'
    """
    parser = argparse.ArgumentParser(
        prog="list_azs",
        description=(
            "List the availability zones usable by an RDS for MySQL HA "
            "flavor as pretty JSON via the hcloud CLI. The spec code may be "
            "the single spec; the HA spec is derived automatically."
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Required. Cloud region of the instance (e.g. cn-north-4).",
    )
    parser.add_argument(
        "--database-name",
        required=True,
        help="Required. Database engine name (e.g. MySQL).",
    )
    parser.add_argument(
        "--version-name",
        required=True,
        help="Required. Database version (e.g. 8.0).",
    )
    parser.add_argument(
        "--spec-code",
        required=True,
        help=(
            "Required. Spec code of the HA flavor, or of the single flavor "
            "(the HA spec is then derived automatically)."
        ),
    )
    parser.add_argument(
        "--instance-id",
        default=None,
        help=(
            "Optional. Instance id used to mark its current availability "
            "zone in the output."
        ),
    )
    common.add_platform_arguments(parser)
    return parser


def resolve_ha_flavor(
    cmd_prefix: list[str], args: argparse.Namespace, timeout: int
) -> tuple[dict | None, str]:
    """Resolve the HA flavor entry for the given spec code.

    1. Query ListFlavors filtered by the given spec code.
    2. Use the entry directly when its instance_mode is `ha`.
    3. When it is `single`, derive the HA spec code and query it again.
    4. Report an error when neither query yields an `ha` entry.

    Args:
        cmd_prefix: list[str] — Base RDS command prefix with region/project.
        args: argparse.Namespace — Parsed command line arguments.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        tuple[dict | None, str]: (ha flavor entry or None, error detail).

    Examples:
        # Requires hcloud credentials:
        # >>> resolve_ha_flavor(["RDS"], args, 5)
        (None, '...')
    """
    base_query = [
        common.CMD_LIST_FLAVORS,
        "--database_name={}".format(args.database_name),
        "--version_name={}".format(args.version_name),
    ]
    payload = common.run_hcloud(
        cmd_prefix + base_query + ["--spec_code={}".format(args.spec_code)],
        timeout,
    )
    entry = common.find_flavor(payload, args.spec_code)
    if entry is None:
        return None, "spec {} not found in ListFlavors".format(args.spec_code)
    mode = entry.get("instance_mode", "")
    if mode == common.FLAVOR_MODE_HA:
        return entry, ""
    if mode != common.FLAVOR_MODE_SINGLE:
        return None, (
            "spec {} has instance_mode {}, expected single or ha".format(
                args.spec_code, mode
            )
        )
    ha_spec_code = common.derive_ha_spec_code(args.spec_code)
    LOGGER.info(
        "Given spec %s is a single flavor; derived HA spec %s.",
        args.spec_code,
        ha_spec_code,
    )
    payload = common.run_hcloud(
        cmd_prefix + base_query + ["--spec_code={}".format(ha_spec_code)],
        timeout,
    )
    entry = common.find_flavor(payload, ha_spec_code)
    if entry is None:
        return None, "ha spec {} not found in ListFlavors".format(ha_spec_code)
    if entry.get("instance_mode", "") != common.FLAVOR_MODE_HA:
        return None, "spec {} is not an ha flavor".format(ha_spec_code)
    return entry, ""


def resolve_current_az(
    cmd_prefix: list[str], instance_id: str, timeout: int
) -> str:
    """Read the instance's current availability zone from ListInstances.

    1. Return an empty string when no instance id was given.
    2. Query ListInstances for the instance and read availability_zone.

    Args:
        cmd_prefix: list[str] — Base RDS command prefix with region/project.
        instance_id: str — The instance id, or an empty string.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        str: The current availability zone, or an empty string.

    Examples:
        # Requires hcloud credentials:
        # >>> resolve_current_az(["RDS"], "", 5)
        ''
    """
    if not instance_id:
        return ""
    payload = common.run_hcloud(
        cmd_prefix + [common.CMD_LIST_INSTANCES, "--id={}".format(instance_id)],
        timeout,
    )
    instances = payload.get("instances") or []
    if not instances:
        return ""
    return instances[0].get("availability_zone", "")


def run(args: argparse.Namespace) -> int:
    """Resolve the HA flavor and print its availability zone rows.

    1. Resolve the region project id.
    2. Resolve the HA flavor entry for the given spec code.
    3. Read the instance's current AZ when --instance-id was given.
    4. Build the AZ rows and report when none is available.
    5. Print the rows as pretty JSON to stdout.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 when at least one AZ is available, 1 otherwise).

    Examples:
        # Requires hcloud credentials:
        # >>> run(args)
        1
    """
    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        cmd_prefix = common.make_rds_prefix(args.region, project_id)
        flavor, error = resolve_ha_flavor(cmd_prefix, args, common.DEFAULT_TIMEOUT)
        if flavor is None:
            LOGGER.error("%s", error)
            return 1
        current_az = resolve_current_az(
            cmd_prefix, args.instance_id or "", common.DEFAULT_TIMEOUT
        )
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1

    rows = common.build_az_rows(flavor, current_az)
    available = [row for row in rows if row["available"]]
    if not available:
        LOGGER.error(
            "No availability zone is available for %s in %s: every zone is "
            "sellout or unsupported. The instance cannot be converted.",
            flavor.get("spec_code", ""),
            args.region,
        )
        return 1
    LOGGER.info(
        "%d of %d availability zones are available for %s.",
        len(available),
        len(rows),
        flavor.get("spec_code", ""),
    )
    print(common.format_discovery_json([], rows))
    return 0


def main() -> int:
    """Run the availability zone discovery workflow.

    1. Parse arguments, including the platform-injected compatibility
       options, and set up logging.
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
    args = common.parse_known_arguments(build_arg_parser())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
