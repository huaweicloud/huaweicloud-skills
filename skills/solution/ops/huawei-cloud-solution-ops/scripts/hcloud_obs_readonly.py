#!/usr/bin/env python3
"""Build or run read-only OBS obsutil commands through `hcloud obs`."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_resource_discovery

READ_OPERATIONS = {
    "ListBuckets": {
        "scope": "query",
        "requires_bucket": False,
        "parts": ("ls",),
    },
    "StatBucket": {
        "scope": "resource_query",
        "requires_bucket": True,
        "parts": ("stat", "{bucket_url}"),
    },
    "GetBucketLifecycle": {
        "scope": "resource_query",
        "requires_bucket": True,
        "parts": ("lifecycle", "{bucket_url}", "-method=get"),
    },
    "GetBucketPolicy": {
        "scope": "resource_query",
        "requires_bucket": True,
        "parts": ("bucketpolicy", "{bucket_url}", "-method=get"),
    },
}
OPERATION_ALIASES = {
    "ShowBucket": "StatBucket",
    "GetBucketStat": "StatBucket",
    "GetLifecycle": "GetBucketLifecycle",
    "GetLifecycleConfiguration": "GetBucketLifecycle",
    "GetBucketPolicyStatus": "GetBucketPolicy",
}


def canonical_operation(operation: str) -> str | None:
    """Resolve a user-facing OBS operation to a supported adapter operation."""
    aliased = OPERATION_ALIASES.get(operation, operation)
    normalized = hcloud_resource_discovery.normalize_operation(aliased)
    for candidate in READ_OPERATIONS:
        if hcloud_resource_discovery.normalize_operation(candidate) == normalized:
            return candidate
    return None


def bucket_url(bucket: str) -> str:
    """Return an obs:// URL from a bucket name or OBS URL."""
    value = bucket.strip()
    if value.startswith("obs://"):
        return value
    return f"obs://{value}"


def validate_raw_obs_arg(value: str) -> None:
    """Validate one raw obsutil argument before passing it through."""
    if not value.startswith("-"):
        raise ValueError(f"OBS raw --arg values must start with '-': {value}")


def command_parts(args: argparse.Namespace, operation: str) -> list[str]:
    """Return `hcloud obs` command parts for one read-only operation."""
    spec = READ_OPERATIONS[operation]
    if spec["requires_bucket"] and not args.bucket:
        raise ValueError(f"{operation} requires --bucket.")

    replacements = {"bucket_url": bucket_url(args.bucket) if args.bucket else ""}
    parts = [
        item.format(**replacements)
        for item in spec["parts"]
    ]
    if args.limit is not None and operation == "ListBuckets":
        parts.append(f"-limit={args.limit}")
    if args.endpoint:
        parts.append(f"-e={args.endpoint}")
    if args.config:
        parts.append(f"-config={args.config}")
    if args.payer:
        parts.append(f"-payer={args.payer}")
    for raw_arg in args.arg:
        validate_raw_obs_arg(raw_arg)
        parts.append(raw_arg)
    return parts


def build_safe_exec_command(args: argparse.Namespace, operation: str) -> list[str]:
    """Build the safe_exec wrapper command for an OBS read-only operation."""
    command = hcloud_common.safe_exec_command_prefix() + ["--command-part=obs"]
    for part in command_parts(args, operation):
        command.append(f"--command-part={part}")
    command.extend(["--timeout", str(args.timeout)])
    return command


def execute_command(command: list[str], timeout: int) -> dict[str, Any]:
    """Run a safe_exec OBS command and parse the structured JSON wrapper output."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout + 5,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "parsed_json_error": "hcloud_safe_exec.py did not return valid JSON.",
        }


def summarize_execution(operation: str, execution: dict[str, Any] | None) -> dict[str, Any]:
    """Return a compact OBS execution summary without exposing resource details."""
    if not execution:
        return {}
    stdout = str(execution.get("stdout") or "")
    summary: dict[str, Any] = {
        "parsed_json_error": execution.get("parsed_json_error"),
        "obs_log_warning_present": ".obsutil_log" in stdout,
    }
    if operation == "ListBuckets":
        match = re.search(r"Bucket\s+number\s*:?\s*(\d+)", stdout, flags=re.IGNORECASE)
        if match:
            summary["bucket_count"] = int(match.group(1))
    error_match = re.search(
        r"status\s+\[(?P<status>\d+)\],\s+error code\s+\[(?P<code>[^\]]+)\],\s+error message\s+\[(?P<message>[^\]]+)\]",
        stdout,
        flags=re.IGNORECASE,
    )
    if error_match:
        code = error_match.group("code")
        summary["obs_status"] = int(error_match.group("status"))
        summary["obs_error_code"] = code
        summary["obs_error_message"] = error_match.group("message")
        if code in {"InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            summary["advice"] = "Check OBS obsutil credentials and endpoint, for example via `hcloud obs config`; OBS does not automatically reuse every normal KooCLI profile setting."
        elif code in {"AccessDenied", "NoSuchBucket"}:
            summary["advice"] = "Check OBS bucket permissions, bucket name, endpoint, and request payer settings."
    return summary


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run a read-only OBS obsutil plan."""
    requested_operation = args.operation
    operation = canonical_operation(requested_operation)
    if operation is None:
        return {
            "success": False,
            "service": "OBS",
            "operation": requested_operation,
            "error": "Unsupported OBS read-only operation.",
            "available_operations": sorted(READ_OPERATIONS),
        }

    try:
        command = build_safe_exec_command(args, operation)
    except ValueError as exc:
        return {
            "success": False,
            "service": "OBS",
            "operation": operation,
            "requested_operation": requested_operation,
            "error": str(exc),
            "required_params": ["bucket"] if READ_OPERATIONS[operation]["requires_bucket"] else [],
        }

    result: dict[str, Any] = {
        "success": True,
        "mode": "execute" if args.execute else "plan",
        "service": "OBS",
        "operation": operation,
        "operation_scope": READ_OPERATIONS[operation]["scope"],
        "adapter": "hcloud obs",
        "requires_bucket": READ_OPERATIONS[operation]["requires_bucket"],
        "command": command,
        "command_shell": shlex.join(command),
        "notes": [
            "OBS uses KooCLI's integrated obsutil command shape: hcloud obs <command>.",
            "OBS output is obsutil text, not standard OpenAPI JSON.",
        ],
    }
    if requested_operation != operation:
        result["requested_operation"] = requested_operation
    if args.execute:
        execution = execute_command(command, args.timeout)
        result["execution_success"] = bool(execution.get("success"))
        result["result"] = execution
        result["summary"] = summarize_execution(operation, execution)
        result["success"] = bool(execution.get("success"))
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", required=True, help="OBS read operation, for example ListBuckets or GetBucketLifecycle.")
    parser.add_argument("--bucket", help="OBS bucket name or obs://bucket URL for bucket-scoped operations.")
    parser.add_argument("--endpoint", help="Optional OBS endpoint passed as -e=...")
    parser.add_argument("--config", help="Optional obsutil config path passed as -config=...")
    parser.add_argument("--payer", help="Optional request payer passed as -payer=...")
    parser.add_argument("--limit", type=int, help="Optional bucket list limit.")
    parser.add_argument("--arg", action="append", default=[], help="Raw obsutil option such as -s or -sc. Can be repeated.")
    parser.add_argument("--execute", action="store_true", help="Execute the read-only OBS command.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for the wrapped hcloud obs command.")
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write the full JSON result privately and print a compact receipt.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run a read-only OBS obsutil command."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
