#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Convert a Huawei Cloud RDS for MySQL single instance to HA.

Overview:
    This script executes the full single-to-HA conversion for a Huawei
    Cloud RDS for MySQL instance via the `hcloud` (KooCLI) command line
    tool: pre-checks, a mandatory manual pre-backup, the conversion job,
    job polling, result verification and a structured JSON report. It is
    the Step 8 tool of the SKILL workflow and is irreversible.

Detailed Description:
    The region's project id is resolved automatically via
    KeystoneListAuthProjects. Before any mutation the script refuses to
    start when a valid unfinished state file exists (the user should
    resume with resume.py instead). A manual backup is created and awaited
    by default (it can be skipped with --skip-backup to save backup
    storage cost; the automatic backup policy still applies). The
    conversion is started with StartInstanceSingleToHaAction, the job is
    polled via ListJobInfo, the result is verified via ListInstances, and
    the report is written.
    Intermediate state (backup_id / job_id) is persisted to
    `<output>.state.json` so a killed process can be resumed. The command
    line stays minimal: only --region, --instance-id, --target-az,
    --skip-backup and an optional --output are exposed; backup name, poll
    intervals, limits and the subprocess timeout are rds_common defaults.

Workflow:
    1. Parse the command line arguments.
    2. Resolve the project id of the region.
    3. Refuse to start while a valid unfinished state exists.
    4. Run the pre-condition checks and abort on failure.
    5. Unless --skip-backup, create and wait for the manual backup,
       persisting state.
    6. Start the single-to-HA action, persist the job id and poll it.
    7. Verify the converted instance and write the report.
    8. Clear the state file on success.

Dependencies:
    - Python 3.9+ standard library only (argparse, json, logging, sys,
      time, datetime).
    - rds_common (same directory, shared helpers).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

import rds_common as common

LOGGER = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add the region, instance id, target AZ, backup and output options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--instance-id", "i", "--target-az", "az-b"])
        >>> args.instance_id == "i" and args.target_az == "az-b"
        True
        >>> args = parser.parse_args(["--instance-id", "i", "--target-az", "az-b", "--skip-backup"])
        >>> args.skip_backup
        True
    """
    parser = argparse.ArgumentParser(
        prog="convert",
        description=(
            "Convert a Huawei Cloud RDS for MySQL single instance to a "
            "primary/standby (HA) instance via the hcloud CLI and write a "
            "structured JSON report."
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
        "--skip-backup",
        action="store_true",
        help=(
            "Optional. Skip the pre-conversion manual backup and convert "
            "directly (the automatic backup policy still applies)."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional. Path to the output JSON report file.",
    )
    return parser


def run_backup_and_conversion(
    cmd_prefix: list[str],
    instance_id: str,
    target_az: str,
    charge_mode: str,
    project_id: str,
    state_path: str,
    region: str,
    skip_backup: bool,
) -> dict:
    """Create the pre-backup, start the conversion and poll the job.

    1. Unless skip_backup is set, create and wait for the manual backup.
    2. Persist the recovery state after the backup starts or directly as a
       job-phase state when the backup is skipped.
    3. Start the single-to-HA action, persist the job id and poll it.
    4. Poll the job until Completed, Failed or timeout.

    Args:
        cmd_prefix: list[str] — Base hcloud RDS command prefix.
        instance_id: str — The target RDS instance ID.
        target_az: str — The target availability zone code.
        charge_mode: str — The instance charge mode (prePaid or postPaid).
        project_id: str — The resolved project id of the region.
        state_path: str — Recovery state file path.
        region: str — The cloud region.
        skip_backup: bool — When True, skip the manual backup and convert
            directly.

    Returns:
        dict: conversion section with backup and job results.

    Examples:
        # With stubbed hcloud calls the result dict is populated:
        # >>> result = run_backup_and_conversion([...], "i", "az-b", "postPaid", "p", "s.json", "r", False)
        # >>> "job_id" in result
        True
    """
    conversion: dict = {}

    backup_id = ""
    if skip_backup:
        conversion["pre_backup"] = {
            "pass": False,
            "skipped": True,
            "detail": "manual backup skipped by --skip-backup",
        }
    else:
        backup_cmd = cmd_prefix + [
            common.CMD_CREATE_MANUAL_BACKUP,
            "--instance_id={}".format(instance_id),
            "--name={}".format(common.build_backup_name(instance_id)),
        ]
        backup_id, _ = common.create_pre_backup(
            backup_cmd, common.DEFAULT_TIMEOUT, instance_id
        )
        common.save_state(
            state_path,
            {
                "instance_id": instance_id,
                "region": region,
                "project_id": project_id,
                "phase": common.PHASE_BACKUP,
                "backup_id": backup_id,
                "started_at": time.monotonic(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        list_backups_prefix = cmd_prefix + [
            common.CMD_LIST_BACKUPS,
            "--instance_id={}".format(instance_id),
        ]
        backup_status, backup_detail = common.poll_backup_status(
            list_backups_prefix,
            backup_id,
            common.DEFAULT_BACKUP_POLL_INTERVAL,
            common.DEFAULT_BACKUP_MAX_POLL_TIME,
            common.DEFAULT_TIMEOUT,
        )
        conversion["pre_backup"] = {
            "pass": backup_status == "COMPLETED",
            "backup_id": backup_id,
            "backup_status": backup_status,
            "detail": backup_detail,
        }
        if backup_status != "COMPLETED":
            conversion["error"] = "manual backup did not complete"
            return conversion
        LOGGER.info("Manual backup %s completed.", backup_id)

    start_cmd = common.execute_single_to_ha(
        cmd_prefix
        + [common.CMD_START_SINGLE_TO_HA, "--instance_id={}".format(instance_id)],
        target_az,
        charge_mode,
    )
    start_payload = common.run_hcloud(start_cmd, common.DEFAULT_TIMEOUT)
    job_id = start_payload.get("job_id", "")
    order_id = start_payload.get("order_id", "")
    if not job_id and not order_id:
        raise common.HcloudError(
            "StartInstanceSingleToHaAction returned neither job_id nor "
            "order_id: {}".format(json.dumps(start_payload))
        )
    if job_id:
        conversion["job_id"] = job_id
        LOGGER.info("Single-to-HA job started: %s", job_id)
        common.save_state(
            state_path,
            {
                "instance_id": instance_id,
                "region": region,
                "project_id": project_id,
                "phase": common.PHASE_JOB,
                "backup_id": backup_id,
                "job_id": job_id,
                "started_at": time.monotonic(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        list_job_prefix = cmd_prefix + [common.CMD_LIST_JOB_INFO]
        job_status, job_detail, elapsed = common.poll_job_status(
            list_job_prefix,
            job_id,
            common.DEFAULT_POLL_INTERVAL,
            common.DEFAULT_MAX_POLL_TIME,
            common.DEFAULT_TIMEOUT,
        )
        conversion["final_status"] = job_status
        conversion["elapsed_seconds"] = round(elapsed, 1)
        conversion["detail"] = job_detail
        LOGGER.info("Job %s final status: %s (elapsed %.1fs)", job_id, job_status, elapsed)
    else:
        conversion["order_id"] = order_id
        LOGGER.info("Single-to-HA order started: %s", order_id)
        common.save_state(
            state_path,
            {
                "instance_id": instance_id,
                "region": region,
                "project_id": project_id,
                "phase": common.PHASE_JOB,
                "backup_id": backup_id,
                "order_id": order_id,
                "started_at": time.monotonic(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        list_instances_prefix = cmd_prefix + [
            common.CMD_LIST_INSTANCES,
        ]
        job_status, job_detail, elapsed = common.poll_prepaid_conversion(
            list_instances_prefix,
            instance_id,
            common.DEFAULT_PREPAID_POLL_INTERVAL,
            common.DEFAULT_PREPAID_MAX_POLL_TIME,
            common.DEFAULT_TIMEOUT,
        )
        conversion["final_status"] = job_status
        conversion["elapsed_seconds"] = round(elapsed, 1)
        conversion["detail"] = job_detail
        LOGGER.info(
            "Prepaid conversion %s final status: %s (elapsed %.1fs)",
            order_id,
            job_status,
            elapsed,
        )
    return conversion


def run(args: argparse.Namespace) -> int:
    """Run the full single-to-HA conversion workflow.

    1. Resolve the project id of the region.
    2. Refuse to start while a valid unfinished state exists.
    3. Run the pre-checks, then create the backup (unless skipped) and run
       the job.
    4. Verify the result, write the report and clear the state.

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
        LOGGER.info("Resolved project id %s for region %s.", project_id, args.region)
    except common.HcloudError as exc:
        LOGGER.error("Failed to resolve project id: %s", exc)
        return 1

    state_path = common.state_path_for(args.output)

    # Refuse to start a fresh conversion while an unfinished state exists.
    state = common.load_state(state_path)
    if state is not None and common.is_state_valid(
        state,
        args.instance_id,
        args.region,
        max(common.DEFAULT_BACKUP_MAX_POLL_TIME, common.DEFAULT_MAX_POLL_TIME),
    ):
        LOGGER.error(
            "An unfinished conversion exists for instance %s; use resume.py to "
            "continue it or remove %s before starting a new one.",
            args.instance_id,
            state_path,
        )
        return 1

    cmd_prefix = common.make_rds_prefix(args.region, project_id)

    report: dict = {
        "metadata": {
            "script": "convert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": args.region,
            "project_id": project_id,
            "instance_id": args.instance_id,
            "target_az": args.target_az,
            "phase": "full",
        },
        "pre_check": {},
        "conversion": {},
        "verification": {},
    }

    try:
        pre_check = run_pre_checks(cmd_prefix, args.instance_id, args.target_az)
        report["pre_check"] = pre_check
        if not pre_check.get("_all_pass", False):
            LOGGER.error("Pre-condition checks failed; aborting before any change.")
            return common.write_report(report, args.output, common.timestamp_now())
        LOGGER.info("Pre-condition checks passed for instance %s.", args.instance_id)

        charge_mode = (
            (pre_check.get("instance_status") or {}).get("charge_mode", "")
            or ""
        )

        conversion = run_backup_and_conversion(
            cmd_prefix,
            args.instance_id,
            args.target_az,
            charge_mode,
            project_id,
            state_path,
            args.region,
            args.skip_backup,
        )
        report["conversion"] = conversion

        if conversion.get("final_status") != "Completed":
            LOGGER.error("Conversion did not complete: %s", conversion.get("detail"))
            return common.write_report(report, args.output, common.timestamp_now())

        verify_payload = common.run_hcloud(
            cmd_prefix + [common.CMD_LIST_INSTANCES, "--id={}".format(args.instance_id)],
            common.DEFAULT_TIMEOUT,
        )
        verified, verify_detail = common.verify_conversion_result(verify_payload)
        report["verification"] = verify_detail
        if not verified:
            LOGGER.error("Result verification failed: %s", json.dumps(verify_detail))
            return common.write_report(report, args.output, common.timestamp_now())

        LOGGER.info(
            "Single-to-HA conversion completed and verified for instance %s.",
            args.instance_id,
        )
        exit_code = common.write_report(report, args.output, common.timestamp_now())
        if exit_code == 0:
            common.clear_state(state_path)
        return exit_code

    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return common.write_report(report, args.output, common.timestamp_now())


def run_pre_checks(cmd_prefix: list[str], instance_id: str, target_az: str) -> dict:
    """Run all pre-condition checks and collect their results.

    1. Query and check the instance status and type.
    2. Query and check the HA flavor support for the target AZ.
    3. Query and check the backup policy.

    Args:
        cmd_prefix: list[str] — Base hcloud RDS command prefix with region/project.
        instance_id: str — The target RDS instance ID.
        target_az: str — The target availability zone code.

    Returns:
        dict: pre_check section with pass/fail entries and details.

    Examples:
        # With stubbed hcloud calls the result dict is populated:
        # >>> result = run_pre_checks([...], "i", "az-b")
        # >>> "instance_status" in result
        True
    """
    report: dict = {}

    payload = common.run_hcloud(
        cmd_prefix + [common.CMD_LIST_INSTANCES, "--id={}".format(instance_id)],
        common.DEFAULT_TIMEOUT,
    )
    ok, status, inst_type, detail = common.check_instance_status(payload)
    instance = payload["instances"][0] if payload.get("instances") else {}
    report["instance_status"] = {
        "pass": ok,
        "status": status,
        "type": inst_type,
        "name": instance.get("name", ""),
        "availability_zone": instance.get("availability_zone", ""),
        "charge_mode": (instance.get("charge_info") or {}).get("charge_mode", ""),
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
        common.DEFAULT_TIMEOUT,
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
        common.DEFAULT_TIMEOUT,
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


def main() -> int:
    """Run the single-to-HA conversion workflow.

    1. Parse arguments and set up logging.
    2. Delegate to run() for the full workflow.

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
