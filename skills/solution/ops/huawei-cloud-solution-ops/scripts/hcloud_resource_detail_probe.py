#!/usr/bin/env python3
"""Probe list-then-detail read paths without printing resource details."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_discovery
import hcloud_resource_query
import hcloud_resource_verify

PROFILES = {
    "VPC": {
        "list_operation": "ListVpcs",
        "detail_operation": "ShowVpc",
        "target_param": "vpc_id",
        "id_paths": (("id",), ("vpc", "id")),
    },
    "ELB": {
        "list_operation": "ListLoadbalancers",
        "detail_operation": "ShowLoadBalancer",
        "target_param": "loadbalancer_id",
        "id_paths": (("id",), ("loadbalancer", "id")),
    },
    "EVS": {
        "list_operation": "ListVolumes",
        "detail_operation": "ShowVolume",
        "target_param": "volume_id",
        "id_paths": (("id",), ("volume", "id")),
    },
    "NAT": {
        "list_operation": "ListNatGateways",
        "detail_operation": "ShowNatGateway",
        "target_param": "nat_gateway_id",
        "id_paths": (("id",), ("nat_gateway", "id")),
    },
    "IMS": {
        "list_operation": "ListImages",
        "detail_operation": "GlanceShowImage",
        "target_param": "image_id",
        "id_paths": (("id",), ("image", "id")),
    },
    "KPS": {
        "list_operation": "ListKeypairs",
        "detail_operation": "ListKeypairDetail",
        "target_param": "keypair_name",
        "id_paths": (("name",), ("keypair", "name"), ("keypair", "keypair_name")),
    },
}


def discovery_args(args: argparse.Namespace, service: str, operation: str) -> SimpleNamespace:
    """Return arguments for a list-only discovery command."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        execute=False,
    )


def query_args(args: argparse.Namespace, service: str, operation: str, param_name: str, param_value: str) -> SimpleNamespace:
    """Return arguments for an explicit detail query."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        param=[f"{param_name}={param_value}"],
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=True,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def first_path_value(resources: list[dict[str, Any]], paths: tuple[tuple[str, ...], ...]) -> str | None:
    """Return the first value found at any candidate path."""
    for item in resources:
        for path in paths:
            current: Any = item
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    break
                current = current[key]
            else:
                if current:
                    return str(current)
    return None


def probe_service(args: argparse.Namespace, service: str) -> dict[str, Any]:
    """Build or run one list-then-detail probe for a service."""
    profile = PROFILES[service]
    list_plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, profile["list_operation"]))
    result: dict[str, Any] = {
        "service": service,
        "list_operation": profile["list_operation"],
        "detail_operation": profile["detail_operation"],
        "stage": "plan",
        "success": bool(list_plan.get("success")),
        "list_plan": list_plan,
    }
    if not args.execute or not list_plan.get("success"):
        return result

    listed = hcloud_resource_discovery.execute_plan(list_plan, args.timeout)
    list_result = listed.get("results", [{}])[0].get("result", {}) if listed.get("results") else {}
    payload = list_result.get("parsed_json")
    resources = hcloud_resource_verify.collect_dicts(payload, service) if payload is not None else []
    target = first_path_value(resources, profile["id_paths"])
    result.update(
        {
            "stage": "execute",
            "list_success": bool(listed.get("success")),
            "resource_count": len(resources),
        }
    )
    if not listed.get("success"):
        result["success"] = False
        return result
    if not target:
        result.update(
            {
                "success": True,
                "detail_attempted": False,
                "skipped": True,
                "reason": "No resource was returned by the list operation, so detail query was skipped.",
            }
        )
        return result

    detail = hcloud_resource_query.build_plan(
        query_args(args, service, profile["detail_operation"].lower(), profile["target_param"], target)
    )
    result.update(
        {
            "success": bool(detail.get("success")),
            "detail_attempted": True,
            "detail_success": bool(detail.get("success")),
            "resolved_detail_operation": detail.get("operation"),
            "parsed_json_error": detail.get("result", {}).get("parsed_json_error"),
        }
    )
    return result


def build_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run resource detail probes for selected services."""
    services = [service.upper() for service in (args.service or ("EVS", "NAT"))]
    unknown = [service for service in services if service not in PROFILES]
    if unknown:
        return {
            "success": False,
            "error": "Unsupported service(s) for detail probe.",
            "unsupported_services": unknown,
            "available_services": sorted(PROFILES),
        }
    checks = [probe_service(args, service) for service in services]
    return {
        "success": all(item.get("success") for item in checks),
        "mode": "execute" if args.execute else "plan",
        "region": args.region,
        "project_id_present": bool(args.project_id),
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Service to probe. Defaults to EVS and NAT.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=5, help="List limit for the probe.")
    parser.add_argument("--execute", action="store_true", help="Execute list and detail read-only commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per hcloud command.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run resource detail probes."""
    args = parse_args()
    result = build_probe(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
