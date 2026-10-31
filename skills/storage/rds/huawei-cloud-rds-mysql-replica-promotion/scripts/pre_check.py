#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the pre-condition checks for a single-to-HA conversion.

Overview:
    This script verifies that a Huawei Cloud RDS for MySQL instance is
    eligible for single-to-HA conversion via the `hcloud` (KooCLI) command
    line tool, and writes a structured JSON report. It is the Step 5 tool
    of the SKILL workflow: it never mutates the cloud instance.

Detailed Description:
    The region's project id is resolved automatically via
    KeystoneListAuthProjects. The script runs the three pre-condition
    checks in order: instance status/type (ListInstances), HA flavor
    support for the target AZ (ListFlavors, `{flavor_ref}.ha` entry), and
    automatic backup enablement (ShowBackupPolicy, keep_days > 0). The
    instance_status entry also carries the instance name, current
    availability zone and charge mode so the SKILL workflow can source
    Step 6 display data (charge_mode) from the pre-check report. If any
    check fails, the report is still written with the failure detail and
    the script exits non-zero. The command line stays minimal: only
    --region, --instance-id, --target-az and an optional --output are
    exposed; the subprocess timeout is a rds_common default.

Workflow:
    1. Parse the command line arguments (region, instance id, target AZ,
       output).
    2. Resolve the project id of the region.
    3. Query and check the instance status and type.
    4. Query and check the HA flavor support for the target AZ.
    5. Query and check the backup policy.
    6. Write the structured JSON report.

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
from datetime import datetime, timezone

import rds_common as common

LOGGER = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add the region, instance id, target AZ and output options only.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--instance-id", "i"])
        >>> args.instance_id == "i"
        True
    """
    parser = argparse.ArgumentParser(
        prog="pre_check",
        description=(
            "Verify the pre-conditions for converting a Huawei Cloud RDS "
            "for MySQL single instance to HA via the hcloud CLI and write "
            "a structured JSON report."
        ),
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Required. Cloud region (e.g. cn-north-4).",
    )
    parser.add_argument(
        "--instance-id",
        required=True,
        help="Required. ID of the target RDS instance.",
    )
    parser.add_argument(
        "--target-az",
        required=True,
        help=(
            "Required. Availability zone code for the new standby node "
            "(e.g. cn-north-4b)."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional. Path to the output JSON report file.",
    )
    return parser


def run_pre_checks(
    cmd_prefix: list[str],
    instance_id: str,
    target_az: str,
    timeout: int,
) -> dict:
    """Run all pre-condition checks and collect their results.

    1. Query and check the instance status and type.
    2. Query and check the HA flavor support for the target AZ.
    3. Query and check the backup policy.

    Args:
        cmd_prefix: list[str] — Base hcloud RDS command prefix with region/project.
        instance_id: str — The target RDS instance ID.
        target_az: str — The target availability zone code.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        dict: pre_check section with pass/fail entries and details.

    Examples:
        # With stubbed hcloud calls the result dict is populated:
        # >>> result = run_pre_checks([...], "i", "az-b", 5)
        # >>> "instance_status" in result
        True
    """
    report: dict = {}

    payload = common.run_hcloud(
        cmd_prefix + [common.CMD_LIST_INSTANCES, "--id={}".format(instance_id)],
        timeout,
    )
    ok, status, inst_type, detail = common.check_instance_status(payload)
    instance = payload["instances"][0] if payload.get("instances") else {}
    volume = instance.get("volume") or {}
    report["instance_status"] = {
        "pass": ok,
        "status": status,
        "type": inst_type,
        "name": instance.get("name", ""),
        "availability_zone": instance.get("availability_zone", ""),
        "charge_mode": (instance.get("charge_info") or {}).get("charge_mode", ""),
        "volume_type": volume.get("type", ""),
        "volume_size": volume.get("size", ""),
        "detail": detail,
    }

    flavor_ref = ""
    if payload.get("instances"):
        flavor_ref = payload["instances"][0].get("flavor_ref", "")
    report["flavor_support"] = {"pass": False, "detail": "skipped"}
    report["backup_policy"] = {"pass": False, "detail": "skipped"}

    if not ok:
        return report

    flavor_payload = common.run_hcloud(
        cmd_prefix
        + [
            common.CMD_LIST_FLAVORS,
            "--database_name=MySQL",
            "--version_name={}".format(
                payload["instances"][0].get("datastore", {}).get("version", "8.0")
            ),
        ],
        timeout,
    )
    ok_flavor, ha_spec, flavor_detail = common.check_flavor_support(
        flavor_payload, flavor_ref, target_az
    )
    report["flavor_support"] = {
        "pass": ok_flavor,
        "spec_code": flavor_ref,
        "ha_spec_code": ha_spec,
        "detail": flavor_detail,
    }

    policy_payload = common.run_hcloud(
        cmd_prefix
        + [common.CMD_SHOW_BACKUP_POLICY, "--instance_id={}".format(instance_id)],
        timeout,
    )
    ok_policy, keep_days, policy_detail = common.check_backup_policy(policy_payload)
    report["backup_policy"] = {
        "pass": ok_policy,
        "keep_days": keep_days,
        "detail": policy_detail,
    }

    report["_all_pass"] = bool(
        report["instance_status"]["pass"]
        and report["flavor_support"]["pass"]
        and report["backup_policy"]["pass"]
    )
    return report


def run(args: argparse.Namespace) -> int:
    """Resolve the project id, run the pre-checks and write the report.

    1. Resolve the region project id via KeystoneListAuthProjects.
    2. Run the three pre-condition checks.
    3. Write the structured JSON report and return the exit code.

    Args:
        args: argparse.Namespace — Parsed command line arguments.

    Returns:
        int: Exit code (0 when all checks pass, 1 otherwise).

    Examples:
        # Requires hcloud credentials:
        # >>> run(args)
        1
    """
    try:
        project_id = common.resolve_project_id(args.region, common.DEFAULT_TIMEOUT)
        cmd_prefix = common.make_rds_prefix(args.region, project_id)
        report: dict = {
            "metadata": {
                "script": "pre_check",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "region": args.region,
                "project_id": project_id,
                "instance_id": args.instance_id,
                "target_az": args.target_az,
                "phase": "pre_check",
            },
            "pre_check": {},
            "conversion": {},
            "verification": {},
        }
        report["pre_check"] = run_pre_checks(
            cmd_prefix, args.instance_id, args.target_az, common.DEFAULT_TIMEOUT
        )
        if not report["pre_check"].get("_all_pass", False):
            LOGGER.error("Pre-condition checks failed; aborting before any change.")
            return common.write_report(report, args.output, common.timestamp_now())
        LOGGER.info("Pre-condition checks passed for instance %s.", args.instance_id)
        return common.write_report(report, args.output, common.timestamp_now())
    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return 1


def main() -> int:
    """Run the pre-condition check workflow.

    1. Parse arguments and set up logging.
    2. Delegate to run() for resolution, checks and reporting.

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
