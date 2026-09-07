#!/usr/bin/env python3
"""Build or run read-only smoke checks across registered Huawei Cloud services."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_obs_readonly
import hcloud_resource_discovery

DEFAULT_SERVICES = ("ECS", "EIP", "VPC", "IMS", "KPS", "ELB", "EVS", "NAT", "RDS", "CCE", "CDN", "DNS", "SCM", "OBS", "CES")
PREFERRED_SMOKE_OPERATIONS = {
    "ECS": "ListServersDetails",
    "EIP": "ListPublicips",
    "VPC": "ListVpcs",
    "IMS": "ListImages",
    "KPS": "ListKeypairs",
    "ELB": "ListLoadbalancers",
    "EVS": "ListVolumes",
    "NAT": "ListNatGateways",
    "RDS": "ListInstances",
    "CCE": "ListClusters",
    "CDN": "ListDomains",
    "DNS": "ListRecordSets",
    "SCM": "ListCertificates",
    "OBS": "ListBuckets",
    "CES": "ListMetrics",
}


def load_registry() -> dict[str, Any]:
    """Return the service registry used by discovery scripts."""
    return hcloud_resource_discovery.load_registry()


def choose_operation(service: str, service_entry: dict[str, Any], requested: str | None) -> str | None:
    """Return the operation to use for one smoke check."""
    if requested:
        return requested
    operations = service_entry.get("query_operations", [])
    preferred = PREFERRED_SMOKE_OPERATIONS.get(service.upper())
    if preferred in operations:
        return preferred
    return operations[0] if operations else None


def parse_operation_overrides(values: list[str]) -> dict[str, str]:
    """Parse service=operation override arguments."""
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid operation override, expected SERVICE=Operation: {value}")
        service, operation = value.split("=", 1)
        service = service.strip().upper()
        operation = operation.strip()
        if not service or not operation:
            raise ValueError(f"Invalid operation override, expected SERVICE=Operation: {value}")
        overrides[service] = operation
    return overrides


def discovery_args(args: argparse.Namespace, service: str, operation: str | None) -> SimpleNamespace:
    """Build an argparse-like object for hcloud_resource_discovery."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        execute=False,
    )


def obs_args(args: argparse.Namespace, operation: str | None) -> SimpleNamespace:
    """Build an argparse-like object for OBS obsutil read-only checks."""
    return SimpleNamespace(
        operation=operation,
        bucket=None,
        endpoint=getattr(args, "obs_endpoint", None),
        config=getattr(args, "obs_config", None),
        payer=getattr(args, "obs_payer", None),
        limit=args.limit,
        arg=[],
        execute=False,
        timeout=args.timeout,
    )


def build_smoke_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run read-only smoke checks for selected services."""
    registry = load_registry()
    overrides = parse_operation_overrides(args.operation)
    selected_services = [service.upper() for service in (args.service or DEFAULT_SERVICES)]
    checks: list[dict[str, Any]] = []

    for service in selected_services:
        entry = registry.get("services", {}).get(service)
        if entry is None:
            checks.append(
                {
                    "service": service,
                    "success": False,
                    "stage": "plan",
                    "error": "Service is not registered.",
                }
            )
            continue

        operation = choose_operation(service, entry, overrides.get(service))
        if not operation:
            checks.append(
                {
                    "service": service,
                    "success": False,
                    "stage": "plan",
                    "error": "Service has no query_operations entry.",
                }
            )
            continue

        runner = entry.get("query_runner") or "scripts/hcloud_resource_discovery.py"
        if runner == "scripts/hcloud_obs_readonly.py":
            plan = hcloud_obs_readonly.build_plan(obs_args(args, operation))
        else:
            plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, operation))
        check: dict[str, Any] = {
            "service": service,
            "operation": operation,
            "coverage": entry.get("coverage"),
            "stage": "plan",
            "success": plan.get("success", False),
            "plan": plan,
            "runner": runner,
        }
        if plan.get("success") and args.execute:
            if runner == "scripts/hcloud_obs_readonly.py":
                exec_args = obs_args(args, operation)
                exec_args.execute = True
                executed_obs = hcloud_obs_readonly.build_plan(exec_args)
                check["stage"] = "execute"
                check["execution_success"] = executed_obs.get("execution_success", False)
                check["result"] = executed_obs.get("result")
                check["summary"] = executed_obs.get("summary", {})
                check["success"] = bool(executed_obs.get("success"))
            else:
                executed = hcloud_resource_discovery.execute_plan(plan, args.timeout)
                check["stage"] = "execute"
                check["execution_success"] = executed.get("success", False)
                check["results"] = executed.get("results", [])
                check["success"] = bool(executed.get("success"))
        checks.append(check)

    plan_success = all(item.get("success") for item in checks) if args.strict or not args.execute else True
    if args.execute and args.strict:
        plan_success = all(item.get("execution_success") for item in checks)

    return {
        "success": plan_success,
        "mode": "execute" if args.execute else "plan",
        "strict": args.strict,
        "region": args.region,
        "project_id_present": bool(args.project_id),
        "service_count": len(checks),
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Service to check. Can be repeated. Defaults to common services.")
    parser.add_argument("--operation", action="append", default=[], help="Override as SERVICE=Operation. Can be repeated.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=20, help="Optional limit for operations that support it.")
    parser.add_argument("--obs-endpoint", help="Optional OBS endpoint for hcloud obs checks.")
    parser.add_argument("--obs-config", help="Optional obsutil config path for hcloud obs checks.")
    parser.add_argument("--obs-payer", help="Optional OBS request payer for hcloud obs checks.")
    parser.add_argument("--execute", action="store_true", help="Execute read-only checks through hcloud_safe_exec.py.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed command.")
    parser.add_argument("--strict", action="store_true", help="Return failure when any selected check fails.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run read-only service smoke checks."""
    args = parse_args()
    try:
        result = build_smoke_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
