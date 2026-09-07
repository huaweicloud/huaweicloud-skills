#!/usr/bin/env python3
"""Unified closure planner for lifecycle, governance, and scenario tiers."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_governance_closure_plan
import hcloud_lifecycle_closure_plan
import hcloud_p2_scenario_closure_plan

TIER_ALIASES = {
    "p0": "lifecycle",
    "lifecycle": "lifecycle",
    "task": "lifecycle",
    "p1": "governance",
    "governance": "governance",
    "manage": "governance",
    "p2": "scenario",
    "scenario": "scenario",
}


def normalize_tier(value: str) -> str:
    """Return the canonical closure tier."""
    normalized = TIER_ALIASES.get(value.strip().lower())
    if not normalized:
        supported = ", ".join(sorted(TIER_ALIASES))
        raise ValueError(f"Unsupported --tier {value!r}. Supported values: {supported}.")
    return normalized


def namespace_for_lifecycle(args: argparse.Namespace) -> SimpleNamespace:
    """Build arguments for the P0 lifecycle closure planner."""
    return SimpleNamespace(
        service=args.service,
        task=args.task,
        operation=args.operation,
        param=args.param,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        json_input_file=args.json_input_file,
        arg=args.arg,
        no_dryrun=args.no_dryrun,
        allow_public_web=bool(getattr(args, "allow_public_web", False)),
        allow_unregistered=args.allow_unregistered,
        limit=args.limit or 20,
        timeout=args.timeout,
    )


def namespace_for_governance(args: argparse.Namespace) -> SimpleNamespace:
    """Build arguments for the P1 governance closure planner."""
    return SimpleNamespace(
        service=args.service,
        param=args.param,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit or 10,
        timeout=args.timeout,
        min_live_ops=args.min_live_ops,
    )


def namespace_for_scenario(args: argparse.Namespace) -> SimpleNamespace:
    """Build arguments for the P2 scenario closure planner."""
    return SimpleNamespace(
        group=args.group,
        param=args.param,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit or 10,
        catalog_max_operations=args.catalog_max_operations,
        timeout=args.timeout,
    )


def attach_wrapper_metadata(result: dict[str, Any], tier: str) -> dict[str, Any]:
    """Attach wrapper metadata without changing nested planner output."""
    wrapped = dict(result)
    wrapped["entrypoint"] = "scripts/hcloud_closure_plan.py"
    wrapped["selected_tier"] = tier
    wrapped["compatibility_modules"] = {
        "lifecycle": "scripts/hcloud_lifecycle_closure_plan.py",
        "governance": "scripts/hcloud_governance_closure_plan.py",
        "scenario": "scripts/hcloud_p2_scenario_closure_plan.py",
    }
    return wrapped


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a closure plan for the selected tier."""
    tier = normalize_tier(args.tier)
    if tier == "lifecycle":
        result = hcloud_lifecycle_closure_plan.build_lifecycle_plan(namespace_for_lifecycle(args))
    elif tier == "governance":
        result = hcloud_governance_closure_plan.build_plan(namespace_for_governance(args))
    else:
        result = hcloud_p2_scenario_closure_plan.build_plan(namespace_for_scenario(args))
    return attach_wrapper_metadata(result, tier)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        default="lifecycle",
        help="Closure tier: lifecycle/p0, governance/p1, or scenario/p2. Defaults to lifecycle.",
    )
    parser.add_argument("--service", action="append", help="P0/P1 service. Defaults depend on tier.")
    parser.add_argument("--group", action="append", help="P2 group. Defaults to all P2 groups.")
    parser.add_argument("--task", help="Human task label for P0 lifecycle closure.")
    parser.add_argument("--operation", help="Optional P0 change operation for the service planner.")
    parser.add_argument("--param", action="append", default=[], help="Task parameter as KEY=VALUE. Repeatable.")
    parser.add_argument("--region", help="Explicit cli-region for generated plans.")
    parser.add_argument("--project-id", help="Optional project_id for generated plans.")
    parser.add_argument("--profile", help="Optional cli-profile for generated plans.")
    parser.add_argument("--json-input-file", help="Optional JSON input file for P0 lower-level change planning.")
    parser.add_argument("--arg", action="append", default=[], help="Additional raw hcloud argument token for P0 planning.")
    parser.add_argument("--no-dryrun", action="store_true", help="Do not add --dryrun in P0 lower-level plans.")
    parser.add_argument(
        "--allow-public-web",
        action="store_true",
        help=(
            "Allow exact TCP 80/443 ingress from 0.0.0.0/0 for a user-confirmed P0 public website plan. "
            "This does not authorize submit."
        ),
    )
    parser.add_argument("--allow-unregistered", action="store_true", help="Pass through to P0 service change planning.")
    parser.add_argument("--limit", type=int, help="Optional read-only evidence/discovery limit.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout carried into generated command plans.")
    parser.add_argument("--min-live-ops", type=int, default=2, help="P1 promotion audit live-smoke threshold.")
    parser.add_argument("--catalog-max-operations", type=int, default=3, help="P2 metadata-backed operations per service.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.min_live_ops < 1:
        parser.error("--min-live-ops must be greater than 0.")
    if args.catalog_max_operations < 1:
        parser.error("--catalog-max-operations must be greater than 0.")
    try:
        args.tier = normalize_tier(args.tier)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main() -> int:
    """Build and print a closure plan for the selected tier."""
    args = parse_args()
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc), "selected_tier": args.tier}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
