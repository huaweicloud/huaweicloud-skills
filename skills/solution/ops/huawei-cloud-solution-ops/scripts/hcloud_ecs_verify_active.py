#!/usr/bin/env python3
"""Verify ECS servers exist and reach ACTIVE after an async job succeeds."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from typing import Any

import hcloud_common

ACTIVE_STATUS = "ACTIVE"


def normalize_status(value: Any) -> str | None:
    """Return an uppercase status string when one is present."""
    if value is None:
        return None
    text = str(value).strip()
    return text.upper() if text else None


def extract_servers(payload: Any) -> list[dict[str, Any]]:
    """Extract server dictionaries from common ECS list response shapes."""
    if isinstance(payload, dict):
        for key in ("servers", "cloudservers", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        for value in payload.values():
            nested = extract_servers(value)
            if nested:
                return nested
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def server_identifier(server: dict[str, Any]) -> str | None:
    """Return the most likely ECS server ID from a server object."""
    for key in ("id", "server_id", "serverId"):
        value = server.get(key)
        if value:
            return str(value)
    return None


def server_name(server: dict[str, Any]) -> str | None:
    """Return the ECS server name when present."""
    value = server.get("name")
    return str(value) if value else None


def server_status(server: dict[str, Any]) -> str | None:
    """Return the normalized ECS server status when present."""
    for key in ("status", "vm_state", "OS-EXT-STS:vm_state"):
        status = normalize_status(server.get(key))
        if status:
            return status
    return None


def build_list_servers_command(args: argparse.Namespace) -> list[str]:
    """Build the safe_exec command used for one ECS ListServersDetails poll."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        "ECS",
        "--operation",
        "ListServersDetails",
        "--arg=--cli-output=json",
        f"--arg=--limit={args.limit}",
        "--expect-json",
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    if args.region:
        command.append(f"--arg=--cli-region={args.region}")
    if args.project_id:
        command.append(f"--arg=--project_id={args.project_id}")
    return command


def run_list_servers(command: list[str], timeout: int) -> dict[str, Any]:
    """Run one ECS ListServersDetails poll through hcloud_safe_exec.py."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "parsed_json": None,
            "parsed_json_error": "hcloud_safe_exec.py did not return valid JSON.",
        }


def classify_targets(
    servers: list[dict[str, Any]],
    target_ids: list[str],
    target_names: list[str],
) -> dict[str, Any]:
    """Classify target ECS servers as active, pending, or missing."""
    by_id = {server_identifier(server): server for server in servers if server_identifier(server)}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for server in servers:
        name = server_name(server)
        if name:
            by_name.setdefault(name, []).append(server)

    matched: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []

    for target_id in target_ids:
        server = by_id.get(target_id)
        if server is None:
            missing.append({"type": "id", "value": target_id})
            continue
        matched.append(server)

    for target_name in target_names:
        name_matches = by_name.get(target_name, [])
        if not name_matches:
            missing.append({"type": "name", "value": target_name})
            continue
        matched.extend(name_matches)

    seen_ids: set[str] = set()
    unique_matched: list[dict[str, Any]] = []
    for server in matched:
        identity = server_identifier(server) or f"name:{server_name(server)}"
        if identity in seen_ids:
            continue
        seen_ids.add(identity)
        unique_matched.append(server)

    summaries = [
        {
            "id": server_identifier(server),
            "name": server_name(server),
            "status": server_status(server),
        }
        for server in unique_matched
    ]
    inactive = [item for item in summaries if item["status"] != ACTIVE_STATUS]

    return {
        "all_active": bool(unique_matched) and not missing and not inactive,
        "matched": summaries,
        "missing": missing,
        "inactive": inactive,
    }


def wait_for_active(args: argparse.Namespace) -> dict[str, Any]:
    """Poll ECS server details until all requested targets are ACTIVE or timeout."""
    command = build_list_servers_command(args)
    if args.print_command_only:
        return {
            "success": True,
            "mode": "print_command_only",
            "verification_scope": "resource_active",
            "command": command,
            "targets": {
                "server_ids": args.server_id,
                "server_names": args.server_name,
            },
        }

    started_at = time.time()
    deadline = started_at + args.timeout
    attempts: list[dict[str, Any]] = []
    consecutive_failures = 0
    attempt_index = 0

    while True:
        attempt_index += 1
        exec_result = run_list_servers(command, timeout=args.command_timeout)
        servers = extract_servers(exec_result.get("parsed_json"))
        classification = classify_targets(servers, args.server_id, args.server_name)
        attempts.append(
            {
                "attempt": attempt_index,
                "safe_exec_success": exec_result.get("success"),
                "return_code": exec_result.get("return_code"),
                "error_type": exec_result.get("error_type"),
                "matched": classification["matched"],
                "missing": classification["missing"],
                "inactive": classification["inactive"],
            }
        )

        if exec_result.get("success"):
            consecutive_failures = 0
        else:
            consecutive_failures += 1

        if classification["all_active"]:
            return {
                "success": True,
                "mode": "poll",
                "verification_scope": "resource_active",
                "command": command,
                "attempts": attempts,
                "final": classification,
                "duration_seconds": round(time.time() - started_at, 3),
            }
        if consecutive_failures >= args.max_command_failures:
            return {
                "success": False,
                "mode": "poll",
                "verification_scope": "resource_active",
                "command": command,
                "attempts": attempts,
                "final": classification,
                "classification": "command_failure",
                "duration_seconds": round(time.time() - started_at, 3),
            }
        if time.time() >= deadline:
            return {
                "success": False,
                "mode": "poll",
                "verification_scope": "resource_active",
                "command": command,
                "attempts": attempts,
                "final": classification,
                "classification": "timeout",
                "duration_seconds": round(time.time() - started_at, 3),
            }
        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-id", action="append", default=[], help="Target ECS server ID. Can be repeated.")
    parser.add_argument("--server-name", action="append", default=[], help="Target ECS server name. Can be repeated.")
    parser.add_argument("--region", help="Explicit cli-region used for ListServersDetails.")
    parser.add_argument("--project-id", help="Optional project_id passed to ListServersDetails.")
    parser.add_argument("--profile", help="Optional cli-profile passed to ListServersDetails.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum servers to list per poll.")
    parser.add_argument("--interval", type=float, default=10.0, help="Seconds between polls.")
    parser.add_argument("--timeout", type=float, default=600.0, help="Maximum total polling time in seconds.")
    parser.add_argument("--command-timeout", type=int, default=120, help="Timeout for each safe_exec call.")
    parser.add_argument("--max-command-failures", type=int, default=3, help="Stop after this many consecutive command failures.")
    parser.add_argument("--print-command-only", action="store_true", help="Print the ListServersDetails command without polling.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    args = parser.parse_args()
    if not args.server_id and not args.server_name:
        parser.error("Provide at least one --server-id or --server-name.")
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
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
    """Run ECS ACTIVE verification and print a structured JSON result."""
    args = parse_args()
    result = wait_for_active(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
