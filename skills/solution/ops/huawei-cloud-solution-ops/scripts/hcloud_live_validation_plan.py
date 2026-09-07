#!/usr/bin/env python3
"""Build non-executing live validation plans for curated high-frequency services."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_query
import hcloud_service_readiness

PROFILE_PATH = hcloud_common.REFERENCES_DIR / "live-validation-profiles.json"
DEFAULT_SERVICES = ("ECS", "VPC", "EIP", "OBS", "ELB", "RDS")
SERVICE_ALIASES = {
    "CLOUDSERVER": "ECS",
    "CLOUDSERVERS": "ECS",
    "PUBLICIP": "EIP",
    "PUBLICIPS": "EIP",
    "LOADBALANCER": "ELB",
    "LOADBALANCERS": "ELB",
    "MYSQL": "RDS",
    "POSTGRESQL": "RDS",
    "POSTGRES": "RDS",
    "BUCKET": "OBS",
}


def load_profiles(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Load service live validation profile data."""
    return hcloud_common.load_json(path)


def canonical_service(value: str) -> str:
    """Return a canonical service key accepted by the live validation profiles."""
    normalized = value.strip().upper().replace("-", "").replace("_", "")
    return SERVICE_ALIASES.get(normalized, normalized)


def selected_services(values: list[str] | None, profiles: dict[str, Any]) -> list[str]:
    """Return selected service IDs in stable order."""
    available = profiles.get("services", {})
    if not values or any(value.lower() == "all" for value in values):
        return [service for service in DEFAULT_SERVICES if service in available]

    selected: list[str] = []
    for value in values:
        service = canonical_service(value)
        if service not in available:
            raise ValueError(f"Unknown live validation service: {value}")
        selected.append(service)
    return selected


def parse_key_values(values: list[str]) -> dict[str, str]:
    """Parse repeated KEY=VALUE params using the shared hcloud parameter normalizer."""
    return hcloud_resource_query.parse_key_value(values, "--param")


def non_sensitive_params(params: dict[str, str]) -> dict[str, str]:
    """Return user params that are safe to keep in planner output and command shapes."""
    return {key: value for key, value in params.items() if not hcloud_common.looks_like_secret_arg(key)}


def sensitive_param_count(params: dict[str, str]) -> int:
    """Return the count of ignored sensitive-looking params."""
    return sum(1 for key in params if hcloud_common.looks_like_secret_arg(key))


def context_value(args: argparse.Namespace, params: dict[str, str], key: str) -> str | None:
    """Return a CLI option value, falling back to a non-sensitive explicit param."""
    return getattr(args, key, None) or params.get(key)


def context_inputs(args: argparse.Namespace, params: dict[str, str]) -> dict[str, str]:
    """Return provided context inputs from CLI options plus explicit params."""
    context = dict(non_sensitive_params(params))
    for key in ("region", "project_id", "profile", "obs_endpoint"):
        value = context_value(args, context, key)
        if value:
            context[key] = value
    return context


def missing_required(profile: dict[str, Any], context: dict[str, str]) -> list[str]:
    """Return missing required input names for one live validation profile."""
    return [name for name in profile.get("required_inputs", []) if name not in context]


def provided_optional(profile: dict[str, Any], context: dict[str, str]) -> list[str]:
    """Return optional profile inputs that were provided."""
    return [name for name in profile.get("optional_inputs", []) if name in context]


def readiness_target_keys(service: str) -> set[str]:
    """Return target keys consumed by hcloud_service_readiness for a service."""
    keys: set[str] = set()
    for item in hcloud_service_readiness.READINESS_PROFILES.get(service, []):
        keys.update(str(name) for name in item.get("required_targets", []))
    return keys


def readiness_args(args: argparse.Namespace, service: str, params: dict[str, str]) -> SimpleNamespace:
    """Build arguments for the existing read-only readiness planner."""
    targets = [
        f"{key}={params[key]}"
        for key in sorted(readiness_target_keys(service))
        if key in params
    ]
    return SimpleNamespace(
        service=[service],
        target=targets,
        region=context_value(args, params, "region"),
        project_id=context_value(args, params, "project_id"),
        profile=context_value(args, params, "profile"),
        limit=args.limit,
        obs_endpoint=context_value(args, params, "obs_endpoint"),
        obs_config=args.obs_config,
        obs_payer=args.obs_payer,
        execute=False,
        timeout=args.timeout,
        strict=False,
        require_all=False,
    )


def first_command(plan: dict[str, Any]) -> list[str] | None:
    """Extract the first safe command shape from a nested readiness plan."""
    commands = plan.get("commands")
    if isinstance(commands, list) and commands:
        command = commands[0].get("command")
        return command if isinstance(command, list) else None
    command = plan.get("command")
    return command if isinstance(command, list) else None


def summarize_readiness(readiness: dict[str, Any]) -> dict[str, Any]:
    """Return a compact hcloud readback summary from service readiness output."""
    service = readiness.get("services", [{}])[0]
    checks = []
    for check in service.get("checks", []):
        plan = check.get("plan", {})
        checks.append(
            {
                "service": check.get("service"),
                "operation": check.get("operation"),
                "runner": check.get("runner"),
                "stage": check.get("stage"),
                "skipped": bool(check.get("skipped")),
                "missing_targets": check.get("missing_targets", []),
                "command": first_command(plan) if plan else None,
                "plan_error": plan.get("error") if isinstance(plan, dict) else None,
            }
        )
    return {
        "source": "scripts/hcloud_service_readiness.py",
        "mode": readiness.get("mode"),
        "service_success": service.get("success"),
        "check_count": service.get("check_count", 0),
        "skipped_count": service.get("skipped_count", 0),
        "checks": checks,
    }


def item_status(item: dict[str, Any], context: dict[str, str]) -> dict[str, Any]:
    """Return evidence or probe readiness status based on input availability."""
    required = list(item.get("required_inputs", []) or item.get("requires_inputs", []))
    any_of = list(item.get("any_of_inputs", []) or item.get("requires_any_of_inputs", []))
    missing = [name for name in required if name not in context]
    missing_any = any_of if any_of and not any(name in context for name in any_of) else []
    status = "ready_to_collect" if not missing and not missing_any else "missing_inputs"
    return {
        **item,
        "missing_required_inputs": missing,
        "missing_any_of_inputs": missing_any,
        "status": status,
    }


def gate_status(gate: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]], context: dict[str, str]) -> dict[str, Any]:
    """Return promotion gate readiness from evidence and input availability."""
    required_evidence = list(gate.get("required_evidence", []))
    blocked_evidence = [
        evidence_id
        for evidence_id in required_evidence
        if evidence_by_id.get(evidence_id, {}).get("status") != "ready_to_collect"
    ]
    required_inputs = list(gate.get("required_inputs", []))
    missing_inputs = [name for name in required_inputs if name not in context]
    status = "ready_to_validate" if not blocked_evidence and not missing_inputs else "blocked_by_missing_inputs"
    return {
        **gate,
        "blocked_evidence": blocked_evidence,
        "missing_required_inputs": missing_inputs,
        "status": status,
    }


def build_service_plan(
    args: argparse.Namespace,
    service: str,
    profile: dict[str, Any],
    params: dict[str, str],
    context: dict[str, str],
) -> dict[str, Any]:
    """Build one service live validation plan."""
    readiness = hcloud_service_readiness.build_readiness(readiness_args(args, service, params))
    evidence = [item_status(item, context) for item in profile.get("acceptance_evidence", [])]
    probes = [item_status(item, context) for item in profile.get("probe_candidates", [])]
    evidence_by_id = {item["id"]: item for item in evidence}
    gates = [gate_status(gate, evidence_by_id, context) for gate in profile.get("promotion_gates", [])]
    missing_inputs = missing_required(profile, context)
    blocked_gates = [gate["id"] for gate in gates if gate["status"] != "ready_to_validate"]
    return {
        "service": service,
        "current_status": profile.get("current_status"),
        "target_tier": profile.get("target_tier"),
        "tenant_goals": profile.get("tenant_goals", []),
        "risk": profile.get("risk", []),
        "required_inputs": profile.get("required_inputs", []),
        "missing_required_inputs": missing_inputs,
        "provided_inputs": sorted(context),
        "provided_optional_inputs": provided_optional(profile, context),
        "hcloud_readback_operations": profile.get("hcloud_readback_operations", []),
        "hcloud_readback_plan": summarize_readiness(readiness),
        "acceptance_evidence": evidence,
        "probe_candidates": probes,
        "promotion_gates": gates,
        "blocked_gate_ids": blocked_gates,
        "blockers": profile.get("blockers", []),
        "user_assistance_required": service_user_assistance(missing_inputs, blocked_gates),
        "execution_boundary": "planner_only_no_live_hcloud_no_probe_no_mutation",
    }


def service_user_assistance(missing_inputs: list[str], blocked_gates: list[str]) -> list[str]:
    """Return user-facing assistance requirements for a service plan."""
    assistance = []
    if missing_inputs:
        assistance.append("Provide required live-validation input(s): " + ", ".join(missing_inputs) + ".")
    if blocked_gates:
        assistance.append("Collect or approve evidence for blocked gate(s): " + ", ".join(blocked_gates) + ".")
    assistance.append("Run any real hcloud query or network probe only through the existing guarded tools after review.")
    return assistance


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build non-executing live validation plans for selected services."""
    profiles = load_profiles(args.profile_file)
    params = parse_key_values(args.param)
    context = context_inputs(args, params)
    ignored_sensitive_param_count = sensitive_param_count(params)
    services = selected_services(args.service, profiles)
    service_plans = [
        build_service_plan(args, service, profiles["services"][service], params, context)
        for service in services
    ]
    return {
        "success": True,
        "mode": "live_validation_plan",
        "planning_only": True,
        "profile_schema_version": profiles.get("schema_version"),
        "target_services": services,
        "service_count": len(service_plans),
        "region": context.get("region"),
        "project_id_present": "project_id" in context,
        "profile_present": "profile" in context,
        "ignored_sensitive_param_count": ignored_sensitive_param_count,
        "services": service_plans,
        "user_assistance_required": [
            "Use an isolated Huawei Cloud account/project for live validation.",
            "Configure hcloud profile or environment locally; do not paste AK/SK, passwords, or private keys into chat.",
            "Provide target resource IDs, domains, ports, and approved source CIDRs for target-scoped evidence.",
            "Run generated hcloud readback and acceptance probes separately; this command only plans evidence.",
        ],
        "execution_boundary": "planner_only_no_live_hcloud_no_probe_no_mutation",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Service to plan. Repeatable. Default: ECS,VPC,EIP,OBS,ELB,RDS.")
    parser.add_argument("--param", action="append", default=[], help="Input parameter as KEY=VALUE, for example server_id=<id>.")
    parser.add_argument("--region", help="Target region for generated readback plans.")
    parser.add_argument("--project-id", help="Optional project_id for generated readback plans.")
    parser.add_argument("--profile", help="Optional hcloud profile name.")
    parser.add_argument("--limit", type=int, default=20, help="Limit for list-style hcloud readback plans.")
    parser.add_argument("--obs-endpoint", help="Optional OBS endpoint for OBS readback planning.")
    parser.add_argument("--obs-config", help="Optional obsutil config path for OBS readback planning.")
    parser.add_argument("--obs-payer", help="Optional OBS request payer for OBS readback planning.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout to place in generated safe_exec command shapes.")
    parser.add_argument("--profile-file", type=Path, default=PROFILE_PATH, help="Live validation profile JSON path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    try:
        result = build_plan(args)
    except (OSError, ValueError) as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
