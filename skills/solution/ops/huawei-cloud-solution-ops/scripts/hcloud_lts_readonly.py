#!/usr/bin/env python3
"""Build or run read-only LTS log discovery and query plans."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_discovery
import hcloud_resource_query


def discovery_args(args: argparse.Namespace, operation: str) -> SimpleNamespace:
    """Return LTS discovery arguments."""
    return SimpleNamespace(
        service="LTS",
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=1,
        execute=args.execute,
        timeout=args.timeout,
    )


def query_args(args: argparse.Namespace) -> SimpleNamespace:
    """Return LTS ListLogs query arguments."""
    params = [
        f"log_group_id={args.log_group_id}",
        f"log_stream_id={args.log_stream_id}",
        f"start_time={args.start_time}",
        f"end_time={args.end_time}",
        f"limit={args.limit}",
    ]
    return SimpleNamespace(
        service="LTS",
        operation="ListLogs",
        param=params,
        arg=[f"--keywords={args.keyword}"] if args.keyword else [],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=args.execute,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def stream_query_args(args: argparse.Namespace) -> SimpleNamespace:
    """Return LTS ListLogStream query arguments for one log group."""
    return SimpleNamespace(
        service="LTS",
        operation="ListLogStream",
        param=[f"log_group_id={args.log_group_id}"],
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=args.execute,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def build_discovery_plan(args: argparse.Namespace, operation: str) -> dict[str, Any]:
    """Build or run one LTS discovery plan."""
    plan = hcloud_resource_discovery.build_plan(discovery_args(args, operation))
    if plan.get("success") and args.execute:
        plan = hcloud_resource_discovery.execute_plan(plan, args.timeout)
    return plan


def build_stream_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build log stream discovery or group-scoped stream query."""
    if args.log_group_id:
        return hcloud_resource_query.build_plan(stream_query_args(args))
    return build_discovery_plan(args, "ListLogStreams")


def build_log_query_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run an LTS ListLogs query when all required parameters are present."""
    required = ["log_group_id", "log_stream_id", "start_time", "end_time"]
    missing = [name for name in required if not getattr(args, name)]
    if missing:
        return {
            "success": False,
            "skipped": True,
            "missing_params": missing,
            "error": "LTS ListLogs requires log_group_id, log_stream_id, start_time, and end_time.",
        }
    return hcloud_resource_query.build_plan(query_args(args))


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run a read-only LTS discovery/log query plan."""
    group_plan = build_discovery_plan(args, "ListLogGroups")
    stream_plan = build_stream_plan(args)
    log_query_plan = build_log_query_plan(args)
    return {
        "success": bool(group_plan.get("success")) and bool(stream_plan.get("success")),
        "mode": "execute" if args.execute else "plan",
        "planning_only": not args.execute,
        "service": "LTS",
        "log_group_plan": group_plan,
        "log_stream_plan": stream_plan,
        "log_query_plan": log_query_plan,
        "next_steps": [
            "Run log group and stream discovery before querying logs.",
            "Use a bounded time range and keyword filter for log queries.",
            "Do not store or paste sensitive application logs unless the user explicitly approves the scope.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=50, help="Discovery limit when supported.")
    parser.add_argument("--log-group-id", help="LTS log_group_id for stream or log query.")
    parser.add_argument("--log-stream-id", help="LTS log_stream_id for log query.")
    parser.add_argument("--start-time", help="Log query start time expected by LTS API/KooCLI.")
    parser.add_argument("--end-time", help="Log query end time expected by LTS API/KooCLI.")
    parser.add_argument("--keyword", help="Optional keyword filter passed as a raw LTS query arg when supported.")
    parser.add_argument("--execute", action="store_true", help="Execute approved read-only LTS commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed command.")
    parser.add_argument("--output-file", type=Path, help="Write the full JSON result privately and print a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run the read-only LTS plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_public_result(result, output_file=args.output_file, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
