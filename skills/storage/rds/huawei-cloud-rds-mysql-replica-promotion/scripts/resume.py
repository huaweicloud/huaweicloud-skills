#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resume an unfinished single-to-HA conversion from its state file.

Overview:
    This script continues a conversion that was interrupted (for example
    by a shell/session timeout) from the state file written by convert.py,
    via the `hcloud` (KooCLI) command line tool. It never re-runs the
    conversion; it polls the persisted backup or job and finishes the
    verification and report. It is the recovery companion of the Step 8
    tool of the SKILL workflow.

Detailed Description:
    The region's project id is read from the persisted state rather than
    re-resolved. The state file is validated against the command line
    (instance id, region and age) before any cloud call. Depending on the
    persisted phase, the script finishes a pending backup poll (ListBackups)
    or a pending conversion poll: a persisted job_id is polled via
    ListJobInfo, while an order_id-only state (prepaid instances) is polled
    via the instance state in ListInstances. It then verifies the result via
    ListInstances, writes the full report and clears the state file. The
    command line stays minimal: only --region, --instance-id, an optional
    --target-az (needed only when the conversion job was not yet started),
    an optional --output and an optional --confirm (required only when the
    state has neither a job id nor an order id, so resume would (re-)start
    the irreversible single-to-HA conversion) are exposed; poll intervals,
    limits and the subprocess timeout are rds_common defaults.

Workflow:
    1. Parse the command line arguments.
    2. Load and validate the recovery state for the instance/region/age.
    3. Finish a pending backup poll if the state phase is backup.
    4. Start the conversion only if the state has no job id and no order id,
       and only when --confirm is given; without --confirm this branch
       writes a refused report and exits non-zero without calling
       StartInstanceSingleToHaAction.
    5. Poll the persisted job id or prepaid order (instance state), verify
       the result and write the report.
    6. Clear the state file on success.

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
        prog="resume",
        description=(
            "Resume an unfinished Huawei Cloud RDS for MySQL single-to-HA "
            "conversion from its state file and write the full report."
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
        default=None,
        help=(
            "Optional. Availability zone code for the standby node; needed "
            "only when the conversion job was not yet started."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional. Path to the output JSON report file.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "Optional. Required to (re-)start the irreversible "
            "single-to-HA conversion when the state file has neither a "
            "job id nor an order id (the original convert.py was killed "
            "before the StartInstanceSingleToHaAction response was "
            "captured). Without --confirm that branch writes a refused "
            "report and exits non-zero; the pure-polling recovery paths "
            "(state has a job id or order id) do not need this flag."
        ),
    )
    return parser


def run(args: argparse.Namespace, state_path: str) -> int:
    """Resume an unfinished conversion from its persisted state.

    1. Load and validate the recovery state for the instance/region/age.
    2. Finish a pending backup poll if the state phase is backup.
    3. Start the conversion only when the state has no job id and no order
       id, and only when --confirm is given; without --confirm write a
       refused report and exit non-zero without calling
       StartInstanceSingleToHaAction.
    4. Poll the persisted job id (ListJobInfo) or the persisted order id
       (prepaid, via the instance state), verify the result and write the
       report.

    Args:
        args: argparse.Namespace — Parsed command line arguments.
        state_path: str — Recovery state file path.

    Returns:
        int: Exit code (0 on success, 1 on failure).

    Examples:
        # Requires a state file written by a previous run:
        # >>> run(args, "s.state.json")
        1
    """
    state = common.load_state(state_path)
    if state is None:
        LOGGER.error("No recovery state found at %s; nothing to resume.", state_path)
        return 1
    if not common.is_state_valid(
        state,
        args.instance_id,
        args.region,
        max(common.DEFAULT_BACKUP_MAX_POLL_TIME, common.DEFAULT_MAX_POLL_TIME),
    ):
        LOGGER.error(
            "Recovery state at %s is stale or does not match instance %s in "
            "region %s; refusing to resume.",
            state_path,
            args.instance_id,
            args.region,
        )
        return 1

    project_id = state.get("project_id", "")

    cmd_prefix = common.make_rds_prefix(args.region, project_id)

    report: dict = {
        "metadata": {
            "script": "resume",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": args.region,
            "project_id": project_id,
            "instance_id": args.instance_id,
            "phase": "full",
        },
        "pre_check": {},
        "conversion": {},
        "verification": {},
    }

    try:
        phase = state.get("phase", "")
        backup_id = state.get("backup_id", "")
        job_id = state.get("job_id", "")
        order_id = state.get("order_id", "")

        if phase == common.PHASE_BACKUP and backup_id:
            LOGGER.info("Resuming backup %s.", backup_id)
            list_backups_prefix = cmd_prefix + [
                common.CMD_LIST_BACKUPS,
                "--instance_id={}".format(args.instance_id),
            ]
            backup_status, backup_detail = common.poll_backup_status(
                list_backups_prefix,
                backup_id,
                common.DEFAULT_BACKUP_POLL_INTERVAL,
                common.DEFAULT_BACKUP_MAX_POLL_TIME,
                common.DEFAULT_TIMEOUT,
            )
            report["conversion"]["pre_backup"] = {
                "pass": backup_status == "COMPLETED",
                "backup_id": backup_id,
                "backup_status": backup_status,
                "detail": backup_detail,
            }
            if backup_status != "COMPLETED":
                LOGGER.error("Manual backup did not complete: %s", backup_detail)
                return common.write_report(report, args.output, common.timestamp_now())
            LOGGER.info("Manual backup %s completed.", backup_id)

        # The job must be started (backup phase) or was already started.
        if not job_id and not order_id:
            if not args.confirm:
                LOGGER.error(
                    "State has no job_id and no order_id; resume would "
                    "(re-)start the irreversible single-to-HA conversion. "
                    "Re-run with --confirm to proceed."
                )
                report["conversion"] = {
                    "refused": True,
                    "reason": "missing --confirm for start-conversion branch",
                }
                common.write_report(report, args.output, common.timestamp_now())
                return 1
            if not args.target_az:
                LOGGER.error("--target-az is required to start the conversion job.")
                return common.write_report(report, args.output, common.timestamp_now())
            payload = common.run_hcloud(
                cmd_prefix + [common.CMD_LIST_INSTANCES, "--id={}".format(args.instance_id)],
                common.DEFAULT_TIMEOUT,
            )
            instances = payload.get("instances") or []
            charge_mode = (
                (instances[0].get("charge_info") or {}).get("charge_mode", "")
                if instances
                else ""
            )
            start_cmd = common.execute_single_to_ha(
                cmd_prefix
                + [common.CMD_START_SINGLE_TO_HA, "--instance_id={}".format(args.instance_id)],
                args.target_az,
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
                report["conversion"]["job_id"] = job_id
                LOGGER.info("Single-to-HA job started: %s", job_id)
            else:
                report["conversion"]["order_id"] = order_id
                LOGGER.info("Single-to-HA order started: %s", order_id)
            common.save_state(
                state_path,
                {
                    "instance_id": args.instance_id,
                    "region": args.region,
                    "project_id": project_id,
                    "phase": common.PHASE_JOB,
                    "backup_id": backup_id,
                    "job_id": job_id,
                    "order_id": order_id,
                    "started_at": state.get("started_at", time.monotonic()),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        elif job_id:
            report["conversion"]["job_id"] = job_id
            LOGGER.info("Resuming job %s.", job_id)
        else:
            report["conversion"]["order_id"] = order_id
            LOGGER.info("Resuming prepaid order %s via instance state.", order_id)

        if job_id:
            list_job_prefix = cmd_prefix + [common.CMD_LIST_JOB_INFO]
            job_status, job_detail, elapsed = common.poll_job_status(
                list_job_prefix,
                job_id,
                common.DEFAULT_POLL_INTERVAL,
                common.DEFAULT_MAX_POLL_TIME,
                common.DEFAULT_TIMEOUT,
            )
        else:
            list_instances_prefix = cmd_prefix + [
                common.CMD_LIST_INSTANCES,
            ]
            job_status, job_detail, elapsed = common.poll_prepaid_conversion(
                list_instances_prefix,
                args.instance_id,
                common.DEFAULT_PREPAID_POLL_INTERVAL,
                common.DEFAULT_PREPAID_MAX_POLL_TIME,
                common.DEFAULT_TIMEOUT,
            )
        report["conversion"]["final_status"] = job_status
        report["conversion"]["elapsed_seconds"] = round(elapsed, 1)
        report["conversion"]["detail"] = job_detail

        if job_status != "Completed":
            LOGGER.error("Conversion did not complete: %s", job_detail)
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
            "Single-to-HA conversion resumed, completed and verified for "
            "instance %s.",
            args.instance_id,
        )
        exit_code = common.write_report(report, args.output, common.timestamp_now())
        if exit_code == 0:
            common.clear_state(state_path)
        return exit_code

    except common.HcloudError as exc:
        LOGGER.error("hcloud error: %s", exc)
        return common.write_report(report, args.output, common.timestamp_now())


def main() -> int:
    """Run the resume workflow.

    1. Parse arguments and set up logging.
    2. Delegate to run() with the derived state file path.

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
    state_path = common.state_path_for(args.output)
    return run(args, state_path)


if __name__ == "__main__":
    sys.exit(main())
