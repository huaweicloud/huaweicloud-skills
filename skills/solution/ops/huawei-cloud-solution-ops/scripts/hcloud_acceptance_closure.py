#!/usr/bin/env python3
"""Unified acceptance closure entry point for lifecycle evidence plans."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_acceptance_evidence_result as evidence_result
import hcloud_acceptance_probe_plan as probe_plan
import hcloud_acceptance_probe_run as probe_run
import hcloud_common


def build_chain(
    lifecycle_plan: dict[str, Any],
    values: dict[str, str],
    *,
    execute: bool,
    timeout: int,
    allow_private_targets: bool = False,
) -> dict[str, Any]:
    """Build probe templates, run supported probes, and evaluate evidence in one flow."""
    planned_probes = probe_plan.build_probe_plan(lifecycle_plan)
    probe_execution = probe_run.build_execution(
        planned_probes,
        values,
        execute=execute,
        timeout=timeout,
        allow_private_targets=allow_private_targets,
    )
    evaluation = evidence_result.evaluate_plan(lifecycle_plan, probe_execution)
    return {
        "success": True,
        "mode": "chain",
        "planning_only": not execute,
        "execution_boundary": (
            "plan/run/evaluate wrapper; live execution is limited to built-in HTTP/TCP/DNS/TLS probes "
            "when --execute is set"
        ),
        "overall_status": evaluation.get("overall_status"),
        "probe_plan": planned_probes,
        "probe_execution": probe_execution,
        "evidence_result": evaluation,
    }


def add_pretty(parser: argparse.ArgumentParser) -> None:
    """Add common output formatting options."""
    parser.add_argument("--output-file", type=Path, help="Write the full JSON result privately and print a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")


def add_values(parser: argparse.ArgumentParser) -> None:
    """Add common probe execution options."""
    parser.add_argument("--value", action="append", default=[], help="Placeholder value as KEY=VALUE. Repeatable.")
    parser.add_argument("--execute", action="store_true", help="Run supported live probes.")
    parser.add_argument(
        "--allow-private-targets",
        action="store_true",
        help="Allow private, loopback, or local probe targets after explicit user confirmation.",
    )
    parser.add_argument("--timeout", type=int, default=10, help="Network timeout for each supported probe.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Build non-executing probe templates from a lifecycle plan.")
    plan_parser.add_argument("--plan-file", type=Path, required=True, help="Lifecycle closure plan JSON.")
    add_pretty(plan_parser)

    run_parser = subparsers.add_parser("run", help="Prepare or run supported probes from a probe plan.")
    run_parser.add_argument("--probe-plan-file", type=Path, required=True, help="Probe plan JSON.")
    add_values(run_parser)
    add_pretty(run_parser)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate local evidence against a lifecycle plan.")
    evaluate_parser.add_argument("--plan-file", type=Path, required=True, help="Lifecycle closure plan JSON.")
    evaluate_parser.add_argument("--evidence-file", type=Path, required=True, help="Local evidence status JSON.")
    add_pretty(evaluate_parser)

    chain_parser = subparsers.add_parser(
        "chain",
        help="Build probe templates, prepare or run supported probes, then evaluate evidence.",
    )
    chain_parser.add_argument("--plan-file", type=Path, required=True, help="Lifecycle closure plan JSON.")
    add_values(chain_parser)
    add_pretty(chain_parser)

    args = parser.parse_args()
    if getattr(args, "timeout", 1) < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Run the selected acceptance closure subcommand."""
    if args.command == "plan":
        return probe_plan.build_probe_plan(hcloud_common.load_json(args.plan_file))
    if args.command == "run":
        values = probe_run.parse_values(args.value)
        return probe_run.build_execution(
            hcloud_common.load_json(args.probe_plan_file),
            values,
            execute=args.execute,
            timeout=args.timeout,
            allow_private_targets=args.allow_private_targets,
        )
    if args.command == "evaluate":
        return evidence_result.evaluate_plan(
            hcloud_common.load_json(args.plan_file),
            hcloud_common.load_json(args.evidence_file),
        )
    if args.command == "chain":
        values = probe_run.parse_values(args.value)
        return build_chain(
            hcloud_common.load_json(args.plan_file),
            values,
            execute=args.execute,
            timeout=args.timeout,
            allow_private_targets=args.allow_private_targets,
        )
    raise ValueError(f"Unsupported command: {args.command}")


def main() -> int:
    """Execute the selected acceptance closure subcommand and print JSON."""
    args = parse_args()
    try:
        result = dispatch(args)
    except probe_run.ProbeRunError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
        default_mode=args.command,
    )
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
