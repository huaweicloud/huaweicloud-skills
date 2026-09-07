#!/usr/bin/env python3
"""Poll an ECS ShowJob result until it reaches a terminal status."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from typing import Any

import hcloud_common

SUCCESS_STATUSES = {"SUCCESS", "SUCCEEDED", "COMPLETE", "COMPLETED"}
FAILURE_STATUSES = {"FAIL", "FAILED", "ERROR", "CANCELLED", "CANCELED", "ROLLBACK", "ROLLED_BACK"}
RUNNING_STATUSES = {"INIT", "PENDING", "RUNNING", "PROCESSING", "WAITING"}


def normalize_status(value: Any) -> str | None:
    """Normalize a status-like value to uppercase text."""
    if value is None:
        return None
    text = str(value).strip()
    return text.upper() if text else None


def extract_status(payload: Any) -> str | None:
    """Extract a job status from common ECS ShowJob response shapes."""
    if isinstance(payload, dict):
        for key in ("status", "job_status", "jobStatus"):
            status = normalize_status(payload.get(key))
            if status:
                return status
        for key in ("job", "Job", "data", "result"):
            status = extract_status(payload.get(key))
            if status:
                return status
        for value in payload.values():
            status = extract_status(value)
            if status:
                return status
    elif isinstance(payload, list):
        for value in payload:
            status = extract_status(value)
            if status:
                return status
    return None


def classify_status(status: str | None) -> str:
    """Classify a normalized job status."""
    if status in SUCCESS_STATUSES:
        return "success"
    if status in FAILURE_STATUSES:
        return "failure"
    if status in RUNNING_STATUSES:
        return "running"
    return "unknown"


def build_show_job_command(args: argparse.Namespace) -> list[str]:
    """Build the hcloud_safe_exec.py command used for one ShowJob poll."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        "ECS",
        "--operation",
        "ShowJob",
        f"--arg=--job_id={args.job_id}",
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    if args.region:
        command.append(f"--arg=--cli-region={args.region}")
    if args.project_id:
        command.append(f"--arg=--project_id={args.project_id}")
    return command


def run_show_job(command: list[str], timeout: int) -> dict[str, Any]:
    """Run one ShowJob poll through hcloud_safe_exec.py."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "success": False,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "parsed_json": None,
            "parsed_json_error": "hcloud_safe_exec.py did not return valid JSON.",
        }
    return result


def compact_attempt(index: int, exec_result: dict[str, Any], status: str | None, classification: str) -> dict[str, Any]:
    """Return a compact attempt summary suitable for final output."""
    return {
        "attempt": index,
        "safe_exec_success": exec_result.get("success"),
        "return_code": exec_result.get("return_code"),
        "error_type": exec_result.get("error_type"),
        "status": status,
        "classification": classification,
    }


def build_resource_verification(args: argparse.Namespace) -> dict[str, Any]:
    """Return follow-up guidance for ECS resource state verification."""
    followup_command = hcloud_common.bundled_script_command("hcloud_ecs_verify_active.py")
    for server_id in args.server_id:
        followup_command.append(f"--server-id={server_id}")
    for server_name in args.server_name:
        followup_command.append(f"--server-name={server_name}")
    if args.profile:
        followup_command.append(f"--profile={args.profile}")
    if args.region:
        followup_command.append(f"--region={args.region}")
    if args.project_id:
        followup_command.append(f"--project-id={args.project_id}")

    return {
        "required_for_create_completion": True,
        "performed": False,
        "reason": "This script only verifies the ECS async job terminal status, not target server ACTIVE state.",
        "recommended_followup_command": followup_command,
        "has_targets": bool(args.server_id or args.server_name),
    }


def base_result(args: argparse.Namespace) -> dict[str, Any]:
    """Return common output fields for the ECS job waiter."""
    return {
        "verification_scope": "job_terminal_only",
        "resource_verification": build_resource_verification(args),
    }


def wait_for_job(args: argparse.Namespace) -> dict[str, Any]:
    """Poll ECS ShowJob until success, failure, or timeout."""
    command = build_show_job_command(args)
    if args.print_command_only:
        return {
            **base_result(args),
            "success": True,
            "mode": "print_command_only",
            "command": command,
            "attempts": [],
            "final_status": None,
            "classification": None,
        }

    started_at = time.time()
    deadline = started_at + args.timeout
    attempts: list[dict[str, Any]] = []
    consecutive_failures = 0
    attempt_index = 0

    while True:
        attempt_index += 1
        exec_result = run_show_job(command, timeout=args.command_timeout)
        status = extract_status(exec_result.get("parsed_json"))
        classification = classify_status(status)
        attempts.append(compact_attempt(attempt_index, exec_result, status, classification))

        if exec_result.get("success"):
            consecutive_failures = 0
        else:
            consecutive_failures += 1

        if classification == "success":
            return {
                **base_result(args),
                "success": True,
                "mode": "poll",
                "command": command,
                "attempts": attempts,
                "final_status": status,
                "classification": classification,
                "duration_seconds": round(time.time() - started_at, 3),
            }
        if classification == "failure":
            return {
                **base_result(args),
                "success": False,
                "mode": "poll",
                "command": command,
                "attempts": attempts,
                "final_status": status,
                "classification": classification,
                "duration_seconds": round(time.time() - started_at, 3),
            }
        if consecutive_failures >= args.max_command_failures:
            return {
                **base_result(args),
                "success": False,
                "mode": "poll",
                "command": command,
                "attempts": attempts,
                "final_status": status,
                "classification": "command_failure",
                "duration_seconds": round(time.time() - started_at, 3),
            }
        if time.time() >= deadline:
            return {
                **base_result(args),
                "success": False,
                "mode": "poll",
                "command": command,
                "attempts": attempts,
                "final_status": status,
                "classification": "timeout",
                "duration_seconds": round(time.time() - started_at, 3),
            }
        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True, help="ECS job ID returned by a create or change operation.")
    parser.add_argument("--region", help="Explicit cli-region used for ShowJob.")
    parser.add_argument("--project-id", help="Optional project_id passed to ShowJob.")
    parser.add_argument("--profile", help="Optional cli-profile passed to ShowJob.")
    parser.add_argument("--server-id", action="append", default=[], help="Target ECS server ID for follow-up ACTIVE verification.")
    parser.add_argument("--server-name", action="append", default=[], help="Target ECS server name for follow-up ACTIVE verification.")
    parser.add_argument("--interval", type=float, default=10.0, help="Seconds between ShowJob polls.")
    parser.add_argument("--timeout", type=float, default=600.0, help="Maximum total polling time in seconds.")
    parser.add_argument("--command-timeout", type=int, default=120, help="Timeout for each hcloud_safe_exec.py call.")
    parser.add_argument("--max-command-failures", type=int, default=3, help="Stop after this many consecutive command failures.")
    parser.add_argument("--print-command-only", action="store_true", help="Print the ShowJob command without polling.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than 0.")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0.")
    if args.command_timeout <= 0:
        parser.error("--command-timeout must be greater than 0.")
    if args.max_command_failures < 1:
        parser.error("--max-command-failures must be at least 1.")
    return args


def main() -> int:
    """Run the ECS job waiter and print a structured JSON result."""
    args = parse_args()
    result = wait_for_job(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
