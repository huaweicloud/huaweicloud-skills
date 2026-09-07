#!/usr/bin/env python3
"""Create a service-aware, non-executing Huawei Cloud change plan."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_catalog
import hcloud_change_plan
import hcloud_common
import hcloud_operation_evidence
import hcloud_operation_resolver
import hcloud_resource_discovery

ROOT = hcloud_common.ROOT
REGISTRY_PATH = hcloud_common.REGISTRY_PATH

SERVICE_VERIFICATION_HINTS = {
    "EIP": [
        "After create/bind/update, query ListPublicips or ShowPublicip and verify status, public IP address, bandwidth, and port/instance binding.",
        "For public reachability, also verify the target ECS/ELB/NAT dependency and security group ingress before declaring the entry path usable.",
        "For unbind/delete, verify the public IP is no longer bound or no longer appears in ListPublicips.",
    ],
    "VPC": [
        "After VPC/subnet/security group changes, query ListVpcs, ListSubnets, ListSecurityGroups, ListSecurityGroupRules, ShowSecurityGroup, and ShowSecurityGroupRule when target IDs are known.",
        "Verify CIDR, gateway, VPC ID, subnet ID, direction, protocol, port range, and remote IP prefix.",
        "For public-entry tasks, verify the full EIP or ELB path after the security group readback.",
    ],
    "ELB": [
        "After load balancer/listener/pool/member changes, query ListLoadbalancers, ListListeners, ListPools, and ListMembers.",
        "Verify provisioning_status is ACTIVE, backend member operating_status is ONLINE, and backend ECS security groups allow health-check and service traffic before protocol testing.",
    ],
    "EVS": [
        "After volume create/attach/resize, query ListVolumes or ShowVolume and verify status, size, type, and attachment target.",
        "Guest filesystem formatting, partition expansion, mount persistence, and write checks require an ECS remote-command or SSH path before declaring application readiness.",
    ],
    "RDS": [
        "After instance/configuration/backup changes, query ListInstances and relevant Show* detail APIs.",
        "Verify instance status, engine version, flavor, storage, backup policy, endpoint, parameter status, and pending restart state.",
        "For connection readiness, run a bounded client-side connection probe from the intended source network before declaring the database usable.",
    ],
    "NAT": [
        "After NAT gateway or rule changes, query ListNatGateways and rule list APIs, then verify route and EIP dependencies.",
    ],
    "DNS": [
        "After DNS record changes, query ListRecordSets and verify zone ID, name, type, TTL, and values.",
        "Verify DNS resolution from a resolver and explain TTL/cache propagation before declaring traffic cutover complete.",
    ],
    "SCM": [
        "After certificate operations, query ListCertificates and verify domain, status, expiration, and deployment target.",
        "For HTTPS readiness, verify the public endpoint certificate chain and domain/SAN match after deployment.",
    ],
    "CDN": [
        "After CDN domain or config changes, query ShowDomainDetail/ListDomains and verify online status, origin, HTTPS, and cache config.",
        "Probe representative HTTP/HTTPS URLs through CDN and, when needed, direct origin to distinguish CDN faults from origin faults.",
    ],
    "CCE": [
        "After cluster or node changes, query ShowCluster/ListNodes and verify cluster availability and node readiness.",
    ],
}

SERVICE_CONTEXT_HINTS = {
    "EIP": [
        "Resolve VPC/port/ECS target before bind or unbind operations.",
        "Confirm same-region target, current binding, bandwidth size, billing mode, and whether an idle EIP can be reused.",
    ],
    "VPC": [
        "Resolve region, project, VPC CIDR, subnet CIDR, availability zone, and security group intent.",
        "For security group rules, require direction, protocol, port range, and remote IP prefix.",
        "Do not use 0.0.0.0/0 for SSH 22 or development ports 3000, 5000, 8000, and 8080. "
        "For a user-confirmed public website, exact TCP 80/443 requires --allow-public-web.",
    ],
    "ELB": [
        "Resolve VPC, subnet, EIP/public/private network type, listener protocol/port, pool protocol, health monitor, backend member address, backend ECS ID, and backend security group.",
    ],
    "EVS": [
        "Resolve volume type, size, AZ, target ECS ID, expected device, mount path, filesystem, snapshot/backup posture, and whether guest filesystem actions are in scope.",
    ],
    "RDS": [
        "Resolve engine, version, flavor, storage, VPC/subnet/security group, backup retention, maintenance window, restart impact, rollback path, and credential handling.",
    ],
    "DNS": [
        "Resolve zone ID, record name/type/value, TTL, current records, conflict policy, and rollback record values.",
    ],
    "SCM": [
        "Resolve certificate ID, domain/SAN, expiration, target service, deployment target, replacement certificate, and rollback target.",
    ],
    "CDN": [
        "Resolve domain ID/name, origin, origin protocol, certificate, cache rules, refresh/preheat scope, direct-origin health, and rollback origin.",
    ],
}

GENERAL_CONVERGENCE_HINTS = [
    "Treat a successful mutation response as request acceptance until the target resource is read back.",
    "If a mutation times out or loses transport without an explicit provider rejection, read back the target before any retry.",
    "For asynchronous operations, follow the provider job to a terminal state and then verify resource and task-level readiness.",
]

SERVICE_DEPENDENCY_HINTS = {
    "ECS": [
        "Before create, resolve image, flavor/AZ availability, VPC/subnet, security group, keypair, disk, and optional EIP dependencies.",
        "After delete, separately verify EIP and data-volume disposition; delete flags and detach behavior do not prove every dependent resource was released.",
    ],
    "EIP": [
        "Discover region-supported public IP types before constructing a create request; do not hard-code a type from another region.",
        "Before release, verify current port/resource binding and confirm that the dependent public entry path is no longer required.",
    ],
    "ELB": [
        "Model teardown as a dependency graph: remove pool members and health monitors before their pool, then remove listeners/pools before the load balancer as required by current readback.",
        "Members and health monitors are sibling dependencies of a pool, not a universally valid single linear chain; refresh topology after each approved change.",
    ],
}

PREFERRED_DISCOVERY_OPERATIONS = {
    "EIP": "ListPublicips",
    "VPC": "ListVpcs",
    "ELB": "ListLoadbalancers",
    "EVS": "ListVolumes",
    "RDS": "ListInstances",
    "NAT": "ListNatGateways",
    "DNS": "ListRecordSets",
    "SCM": "ListCertificates",
    "CDN": "ListDomains",
    "CCE": "ListClusters",
}

CHANGE_OPERATION_ALIASES = {
    ("CDN", "UpdateDomain"): "UpdateDomainFullConfig",
    ("RDS", "ResizeInstance"): "StartResizeFlavorAction",
    ("RDS", "SetConfiguration"): "UpdateConfiguration",
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Return the service registry."""
    return hcloud_common.load_registry(path)


def registry_change_operations(registry: dict[str, Any], service: str) -> set[str]:
    """Return registered change operations for a service."""
    entry = registry.get("services", {}).get(service.upper(), {})
    return {str(item) for item in entry.get("change_operations", [])}


def resolve_change_operation(registered_changes: set[str], requested_operation: str) -> str | None:
    """Resolve a requested change operation against registered operation names."""
    if requested_operation in registered_changes:
        return requested_operation
    normalized_requested = hcloud_resource_discovery.normalize_operation(requested_operation)
    for operation in registered_changes:
        if hcloud_resource_discovery.normalize_operation(operation) == normalized_requested:
            return operation
    return None


def canonical_change_operation(service: str, operation: str) -> str:
    """Return the executable KooCLI operation name for a known old change alias."""
    return CHANGE_OPERATION_ALIASES.get((service.upper(), operation), operation)


def service_entry(registry: dict[str, Any], service: str) -> dict[str, Any]:
    """Return a registry service entry or an empty dictionary."""
    return registry.get("services", {}).get(service.upper(), {})


def planner_args(args: argparse.Namespace, cli_region: str | None, command_service: str | None = None) -> SimpleNamespace:
    """Convert service planner args to hcloud_change_plan args."""
    return SimpleNamespace(
        service=command_service or args.service.upper(),
        operation=args.operation,
        region=cli_region,
        project_id=args.project_id,
        profile=args.profile,
        json_input_file=args.json_input_file,
        arg=args.arg,
        no_dryrun=args.no_dryrun,
        allow_public_web=bool(getattr(args, "allow_public_web", False)),
        metadata_category=getattr(args, "metadata_category", None),
    )


def limited_params(values: list[str], limit: int = 80) -> dict[str, Any]:
    """Return a bounded parameter list for planner output."""
    values = list(dict.fromkeys(values))
    return {
        "items": values[:limit],
        "omitted_count": max(0, len(values) - limit),
    }


def catalog_context(service: str, operation: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    """Return catalog service, catalog operation, and command service name."""
    catalog = hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return None, None, service.upper()
    catalog_operation = hcloud_catalog.resolve_operation(catalog_service, operation)
    command_service = hcloud_catalog.command_service_name(catalog_service, service.upper())
    return catalog_service, catalog_operation, command_service


def catalog_readiness_plan(args: argparse.Namespace, service: str) -> dict[str, Any]:
    """Build a small metadata-backed read-only smoke plan when possible."""
    return hcloud_resource_discovery.build_plan(
        SimpleNamespace(
            service=service,
            operation=None,
            region=args.region,
            project_id=args.project_id,
            profile=args.profile,
            limit=20,
            catalog_max_operations=3,
            execute=False,
        )
    )


def change_request_contract(
    command_service: str,
    catalog_operation: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return top-level request evidence for a catalog-backed change."""

    if not catalog_operation:
        return None
    versions = hcloud_catalog.operation_versions(catalog_operation)
    selected = str(catalog_operation.get("selected_version") or "").strip().lower()
    if not selected and versions:
        selected = versions[0]
    if not selected:
        return None
    return hcloud_operation_resolver.request_contract(
        command_service,
        catalog_operation,
        selected,
    )


def dependency_and_convergence_hints(service: str) -> list[str]:
    """Return generic convergence rules plus bounded service dependency facts."""

    return [
        *GENERAL_CONVERGENCE_HINTS,
        *SERVICE_DEPENDENCY_HINTS.get(service.upper(), []),
    ]


def build_catalog_change_plan(
    args: argparse.Namespace,
    service: str,
    requested_operation: str,
    operation: str,
    catalog_service: dict[str, Any],
    catalog_operation: dict[str, Any] | None,
    command_service: str,
    entry: dict[str, Any],
    registered: bool,
) -> dict[str, Any]:
    """Build a planner-only change plan from generated hcloud catalog metadata."""
    if catalog_operation is None:
        return {
            "success": False,
            "service": service,
            "operation": operation,
            "requested_operation": requested_operation,
            "coverage": "metadata-backed",
            "metadata_backed": True,
            "error": "Operation is not present in the generated hcloud catalog.",
            "available_catalog_operations_sample": sorted(catalog_service.get("operations", {}))[:50],
        }
    operation = str(catalog_operation.get("name") or operation)
    if hcloud_catalog.is_read_only(catalog_operation):
        return {
            "success": False,
            "service": service,
            "operation": operation,
            "requested_operation": requested_operation,
            "coverage": "metadata-backed",
            "metadata_backed": True,
            "catalog_operation_summary": catalog_operation.get("summary"),
            "catalog_operation_method": catalog_operation.get("method"),
            "catalog_operation_path": catalog_operation.get("path"),
            "error": "Operation is read-only; use hcloud_resource_discovery.py or hcloud_resource_query.py instead of the change planner.",
        }

    cli_region, region_resolution = hcloud_resource_discovery.resolve_cli_region(args, entry)
    dryrun_state = hcloud_catalog.operation_dryrun_state(
        hcloud_catalog.load_confidence(),
        command_service,
        operation,
    )
    plan_args = planner_args(args, cli_region, command_service)
    plan_args.operation = operation
    plan_args.metadata_category = catalog_service.get("category")
    if dryrun_state != "supported":
        plan_args.no_dryrun = True
    plan = hcloud_change_plan.build_plan(plan_args)
    plan.update(
        {
            "planning_only": True,
            "registered_change_operation": registered,
            "coverage": "metadata-backed",
            "metadata_backed": True,
            "catalog_service": command_service,
            "catalog_category": catalog_service.get("category"),
            "catalog_dryrun": dryrun_state,
            "catalog_required_params": limited_params(hcloud_catalog.normalized_required_params(catalog_operation)),
            "catalog_optional_params": limited_params(hcloud_catalog.optional_param_names(catalog_operation)),
            "catalog_operation_summary": catalog_operation.get("summary"),
            "catalog_operation_method": catalog_operation.get("method"),
            "catalog_operation_path": catalog_operation.get("path"),
            "request_contract": change_request_contract(command_service, catalog_operation),
            **hcloud_operation_evidence.operation_evidence_fields(service, operation),
            "service_known_limits": entry.get("known_limits", []),
            "service_context_hints": SERVICE_CONTEXT_HINTS.get(service, []),
            "service_verification_hints": SERVICE_VERIFICATION_HINTS.get(service, []),
            "dependency_and_convergence_hints": dependency_and_convergence_hints(service),
            "submit_requires_confirmation": True,
            "submit_is_not_executed_by_this_planner": True,
            "read_only_smoke_plan": catalog_readiness_plan(args, service),
        }
    )
    if region_resolution:
        plan["region_resolution"] = region_resolution
    if requested_operation != operation:
        plan["requested_operation"] = requested_operation
    plan.setdefault("next_steps", []).extend(
        [
            "This operation is metadata-backed rather than curated; confirm required parameters with hcloud help or official Huawei Cloud docs before execution.",
            "Dry-run support is unknown for metadata-backed operations unless catalog_dryrun is supported; confirm operation help before assuming dry-run is available.",
            "Do not run submit commands from this plan without a separate explicit user confirmation.",
            "Use read_only_smoke_plan or an explicit resource query after submit to verify the changed resource.",
        ]
    )
    return plan


def build_service_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing service-aware change plan."""
    registry = load_registry()
    service = args.service.upper()
    requested_operation = args.operation
    aliased_operation = canonical_change_operation(service, requested_operation)
    entry = service_entry(registry, service)
    catalog_service, catalog_operation, command_service = catalog_context(service, aliased_operation)
    if not entry:
        if catalog_service:
            return build_catalog_change_plan(
                args=args,
                service=service,
                requested_operation=requested_operation,
                operation=aliased_operation,
                catalog_service=catalog_service,
                catalog_operation=catalog_operation,
                command_service=command_service,
                entry={},
                registered=False,
            )
        return {
            "success": False,
            "service": service,
            "operation": args.operation,
            "error": f"Service is not registered: {service}",
            "available_services": sorted(registry.get("services", {})),
            "available_catalog_services": hcloud_catalog.catalog_service_names(hcloud_catalog.load_catalog()),
        }

    registered_changes = registry_change_operations(registry, service)
    resolved_operation = resolve_change_operation(registered_changes, aliased_operation)
    operation = resolved_operation or aliased_operation
    registered = operation in registered_changes
    if operation != requested_operation:
        _, catalog_operation, _ = catalog_context(service, operation)
    preferred_discovery = PREFERRED_DISCOVERY_OPERATIONS.get(service)
    custom_planner = entry.get("planner")
    if custom_planner and custom_planner != "scripts/hcloud_service_change_plan.py" and registered:
        return {
            "success": True,
            "service": service,
            "operation": operation,
            "requested_operation": requested_operation,
            "planning_only": True,
            "delegated_planner": custom_planner,
            "registered_change_operation": registered,
            "coverage": entry.get("coverage"),
            "service_known_limits": entry.get("known_limits", []),
            **hcloud_operation_evidence.operation_evidence_fields(service, operation),
            "next_steps": [
                f"Use {custom_planner} for this service-specific change plan.",
                "Do not run submit commands without a separate explicit user confirmation.",
            ],
        }
    if not registered and catalog_service and catalog_operation:
        return build_catalog_change_plan(
            args=args,
            service=service,
            requested_operation=requested_operation,
            operation=operation,
            catalog_service=catalog_service,
            catalog_operation=catalog_operation,
            command_service=command_service,
            entry=entry,
            registered=False,
        )
    if registered_changes and not registered and not args.allow_unregistered:
        return {
            "success": False,
            "service": service,
            "operation": operation,
            "requested_operation": requested_operation,
            "error": "Operation is not registered as a planned change for this service.",
            "available_change_operations": sorted(registered_changes),
            "next_actions": [
                "Use --allow-unregistered only after confirming the operation from hcloud help or official Huawei Cloud docs.",
                "Keep the plan non-executing until dry-run or equivalent validation has passed.",
            ],
        }

    cli_region, region_resolution = hcloud_resource_discovery.resolve_cli_region(args, entry)
    plan_args = planner_args(args, cli_region)
    plan_args.operation = operation
    if catalog_service:
        plan_args.metadata_category = catalog_service.get("category")
    plan = hcloud_change_plan.build_plan(plan_args)
    if not plan.get("success"):
        plan.update(
            {
                "planning_only": True,
                "registered_change_operation": registered,
                "coverage": entry.get("coverage"),
                "service_known_limits": entry.get("known_limits", []),
                "service_context_hints": SERVICE_CONTEXT_HINTS.get(service, []),
                "service_verification_hints": SERVICE_VERIFICATION_HINTS.get(service, []),
                "request_contract": change_request_contract(command_service, catalog_operation),
                **hcloud_operation_evidence.operation_evidence_fields(service, operation),
                "dependency_and_convergence_hints": dependency_and_convergence_hints(service),
                "submit_requires_confirmation": True,
                "submit_is_not_executed_by_this_planner": True,
            }
        )
        if region_resolution:
            plan["region_resolution"] = region_resolution
        if requested_operation != operation:
            plan["requested_operation"] = requested_operation
        return plan
    plan.update(
        {
            "success": True,
            "planning_only": True,
            "registered_change_operation": registered,
            "coverage": entry.get("coverage"),
            "service_known_limits": entry.get("known_limits", []),
            "service_context_hints": SERVICE_CONTEXT_HINTS.get(service, []),
            "service_verification_hints": SERVICE_VERIFICATION_HINTS.get(service, []),
            "request_contract": change_request_contract(command_service, catalog_operation),
            **hcloud_operation_evidence.operation_evidence_fields(service, operation),
            "dependency_and_convergence_hints": dependency_and_convergence_hints(service),
            "resource_verifier": "scripts/hcloud_resource_verify.py",
            "submit_requires_confirmation": True,
            "submit_is_not_executed_by_this_planner": True,
            "read_only_smoke_plan": hcloud_resource_discovery.build_plan(
                SimpleNamespace(
                    service=service,
                    operation=preferred_discovery,
                    region=args.region,
                    project_id=args.project_id,
                    profile=args.profile,
                    limit=20,
                    execute=False,
                )
            ),
        }
    )
    if region_resolution:
        plan["region_resolution"] = region_resolution
    if requested_operation != operation:
        plan["requested_operation"] = requested_operation
    plan["next_steps"] = [
        *plan.get("next_steps", []),
        "Use hcloud_resource_verify.py against post-change JSON results before declaring the resource ready.",
        "Do not run submit commands from this plan without a separate explicit user confirmation.",
    ]
    return plan


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Huawei Cloud service name.")
    parser.add_argument("--operation", required=True, help="Change operation name.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--json-input-file", help="Optional JSON input file to pass via --cli-jsonInput.")
    parser.add_argument("--arg", action="append", default=[], help="Additional raw hcloud argument token.")
    parser.add_argument("--no-dryrun", action="store_true", help="Do not add --dryrun even when risk gate asks for it.")
    parser.add_argument(
        "--allow-public-web",
        action="store_true",
        help=("Allow exact TCP 80/443 ingress from 0.0.0.0/0 for a user-confirmed public website plan. This does not authorize submit."),
    )
    parser.add_argument("--allow-unregistered", action="store_true", help="Allow an operation not listed in service-registry.json.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build and print a service-aware change plan."""
    args = parse_args()
    result = build_service_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
