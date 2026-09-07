#!/usr/bin/env python3
"""Build or run list-only discovery commands from the service registry."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common
import hcloud_output_policy
import hcloud_sdk_catalog
import hcloud_sdk_supplement_audit
from hcloud_meta_lookup import (
    collect_template_dirs,
    load_operation_detail,
    normalize_token,
)

ROOT = hcloud_common.ROOT
REGISTRY_PATH = hcloud_common.REGISTRY_PATH
DEFAULT_CATALOG_DISCOVERY_LIMIT = 5
DEFAULT_CLIENT_REQUEST_ID = "00000000-0000-0000-0000-000000000000"
CURATED_LIMIT_OPERATIONS = {
    ("ECS", "ListCloudServers"),
    ("ECS", "ListServersDetails"),
}
SAFE_GENERATED_HEADER_VALUES = {
    "client_request_id": DEFAULT_CLIENT_REQUEST_ID,
    "clientrequestid": DEFAULT_CLIENT_REQUEST_ID,
}


def normalize_operation(value: str) -> str:
    """Return a loose operation key for case-insensitive matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Return the machine-readable service registry."""
    return hcloud_common.load_registry(path)


def operation_param_names(service: str, operation: str) -> set[str]:
    """Return known hcloud parameter names for an operation from local metadata."""
    catalog_names = catalog_operation_param_names(service, operation)
    if catalog_names:
        return catalog_names

    sdk_names = sdk_supplement_param_names(service, operation)
    if sdk_names:
        return sdk_names

    meta_repo = Path.home() / ".hcloud" / "metaRepo"
    template_dir = collect_template_dirs(meta_repo).get(normalize_token(service))
    detail = load_operation_detail(template_dir, operation)
    if not isinstance(detail, dict):
        if (service.upper(), operation) in CURATED_LIMIT_OPERATIONS:
            return {"limit"}
        return set()

    names: set[str] = set()
    for param in detail.get("params", []):
        for name in param.get("name", []):
            names.add(str(name).lower())
    return names


def sdk_supplement_param_names(service: str, operation: str) -> set[str]:
    """Return parameter names from curated SDK supplement metadata."""
    supplement = hcloud_sdk_supplement_audit.registry_entry_for_hcloud_operation(service, operation)
    if not supplement:
        return set()
    sdk_operation = str(supplement.get("sdk_operation") or operation)
    hint = hcloud_sdk_catalog.sdk_hint_for_operation(service, sdk_operation)
    if not hint:
        return set()
    names = set()
    for name in hint.get("query_params", []):
        normalized = hcloud_catalog.normalize_param_name(str(name))
        if normalized:
            names.add(normalized)
    for name in (hint.get("request_types") or {}):
        normalized = hcloud_catalog.normalize_param_name(str(name))
        if normalized:
            names.add(normalized)
    return names


def sdk_supplement_context(service: str, operation: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return curated SDK supplement entry and metadata hint for discovery output."""
    supplement = hcloud_sdk_supplement_audit.registry_entry_for_hcloud_operation(service, operation)
    if not supplement:
        return None, None
    sdk_operation = str(supplement.get("sdk_operation") or operation)
    return supplement, hcloud_sdk_catalog.sdk_hint_for_operation(service, sdk_operation)


def catalog_operation_param_names(service: str, operation: str) -> set[str]:
    """Return known parameter names for an operation from the generated catalog."""
    catalog = hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return set()
    catalog_operation = hcloud_catalog.resolve_operation(catalog_service, operation)
    if not catalog_operation:
        return set()
    names = {hcloud_catalog.normalize_param_name(name) for name in hcloud_catalog.operation_param_names(catalog_operation)}
    if hcloud_catalog.supports_limit(catalog_operation):
        names.add("limit")
    return {name for name in names if name}


def catalog_operation(service: str, operation: str) -> dict[str, Any] | None:
    """Return a generated catalog operation when available."""
    catalog = hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return None
    return hcloud_catalog.resolve_operation(catalog_service, operation)


def generated_header_args(operation: dict[str, Any] | None) -> tuple[list[str], list[dict[str, str]], list[str]]:
    """Return safe generated required header CLI args for a catalog operation."""
    if not operation:
        return [], [], []
    args = []
    generated = []
    unsupported = []
    for name in hcloud_catalog.required_header_param_names(operation):
        normalized = hcloud_catalog.normalize_param_name(name)
        value = SAFE_GENERATED_HEADER_VALUES.get(normalized)
        if value is None:
            unsupported.append(name)
            continue
        args.append(f"--arg=--{name}={value}")
        generated.append({"param": name, "reason": "safe_required_header"})
    return args, generated, unsupported


def resolve_cli_region(args: argparse.Namespace, service_entry: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve the cli-region for services with curated supported regions."""
    requested_region = args.region
    supported_regions = service_entry.get("supported_cli_regions", [])
    preferred_region = service_entry.get("preferred_cli_region")
    if not supported_regions:
        return requested_region, None

    if requested_region in supported_regions:
        return requested_region, None

    resolved_region = preferred_region or supported_regions[0]
    reason = "requested_region_not_supported" if requested_region else "explicit_supported_region_required"
    return resolved_region, {
        "requested_region": requested_region,
        "resolved_region": resolved_region,
        "supported_regions": supported_regions,
        "reason": reason,
    }


def resolve_query_operation(operations: list[str], requested_operation: str) -> str | None:
    """Resolve a requested operation against registered list-only operations."""
    if requested_operation in operations:
        return requested_operation
    normalized_requested = normalize_operation(requested_operation)
    for operation in operations:
        if normalize_operation(operation) == normalized_requested:
            return operation
    return None


def build_safe_exec_command(
    args: argparse.Namespace,
    service: str,
    operation: str,
    param_names: set[str],
    cli_region: str | None,
) -> tuple[list[str], list[str], list[dict[str, Any]], list[dict[str, str]], list[str]]:
    """Build a JSON-friendly safe_exec command for one list-only operation."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        service,
        "--operation",
        operation,
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    if cli_region:
        command.append(f"--arg=--cli-region={cli_region}")
    if args.project_id:
        command.append(f"--arg=--project_id={args.project_id}")
    omitted_args: list[str] = []
    parameter_adjustments: list[dict[str, Any]] = []
    operation_detail = catalog_operation(service, operation)
    unsupported_optional_args = hcloud_catalog.operation_unsupported_optional_args(
        hcloud_catalog.load_confidence(),
        service,
        operation,
    )
    requested_limit = args.limit
    default_limit = hcloud_output_policy.default_limit(service, operation)
    used_policy_default = False
    if requested_limit is None and default_limit and default_limit[0] == "limit":
        requested_limit = default_limit[1]
        used_policy_default = True
    if requested_limit is not None:
        if "limit" in unsupported_optional_args:
            omitted_args.append("--limit")
        elif "limit" in param_names:
            used_limit = requested_limit
            if operation_detail:
                used_limit, adjustment = hcloud_catalog.bounded_limit_value(
                    operation_detail,
                    requested_limit,
                )
                if adjustment:
                    parameter_adjustments.append(adjustment)
            command.append(f"--arg=--limit={used_limit}")
            if used_policy_default:
                parameter_adjustments.append(
                    {
                        "param": "limit",
                        "requested": None,
                        "used": used_limit,
                        "reason": "output_policy_default",
                    }
                )
        else:
            omitted_args.append("--limit")
    header_args, generated_headers, unsupported_headers = generated_header_args(operation_detail)
    command.extend(header_args)
    return command, omitted_args, parameter_adjustments, generated_headers, unsupported_headers


def build_command_item(args: argparse.Namespace, service: str, operation: str, service_entry: dict[str, Any]) -> dict[str, Any]:
    """Build one discovery command item with metadata-driven optional arguments."""
    cli_region, region_resolution = resolve_cli_region(args, service_entry)
    command, omitted_args, parameter_adjustments, generated_headers, unsupported_headers = build_safe_exec_command(
        args,
        service,
        operation,
        operation_param_names(service, operation),
        cli_region,
    )
    item: dict[str, Any] = {
        "service": service,
        "operation": operation,
        "command": command,
    }
    if region_resolution:
        item["region_resolution"] = region_resolution
    if omitted_args:
        item["omitted_args"] = omitted_args
        unsupported_optional_args = hcloud_catalog.operation_unsupported_optional_args(
            hcloud_catalog.load_confidence(),
            service,
            operation,
        )
        item["omitted_reason"] = (
            "Operation confidence sidecar marks these optional args unsupported by KooCLI help/live shape checks."
            if any(arg.lstrip("-") in unsupported_optional_args for arg in omitted_args)
            else "Operation metadata does not list these parameters."
        )
    if parameter_adjustments:
        item["parameter_adjustments"] = parameter_adjustments
    if generated_headers:
        item["generated_args"] = generated_headers
    if unsupported_headers:
        item["unsupported_required_headers"] = unsupported_headers
    sdk_supplement, sdk_hint = sdk_supplement_context(service, operation)
    if sdk_supplement:
        item["sdk_supplement"] = sdk_supplement
    if sdk_hint:
        item["sdk_evidence"] = sdk_hint
    return item


def build_catalog_command_item(
    args: argparse.Namespace,
    service: str,
    operation: dict[str, Any],
    service_entry: dict[str, Any],
) -> dict[str, Any]:
    """Build one metadata-backed discovery command item."""
    item = build_command_item(args, service, str(operation["name"]), service_entry)
    item.update(
        {
            "metadata_backed": True,
            "catalog_operation_summary": operation.get("summary"),
            "catalog_operation_method": operation.get("method"),
            "catalog_operation_path": operation.get("path"),
        }
    )
    return item


def build_catalog_plan(
    args: argparse.Namespace,
    requested_service: str,
    catalog_service: dict[str, Any],
    service_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build conservative discovery commands from the generated catalog."""
    command_service = hcloud_catalog.command_service_name(catalog_service, requested_service)
    service_entry = service_entry or {}
    if args.operation:
        operation = hcloud_catalog.resolve_operation(catalog_service, args.operation)
        if not operation:
            return {
                "success": False,
                "service": requested_service,
                "operation": args.operation,
                "coverage": "metadata-backed",
                "metadata_backed": True,
                "error": "Operation is not present in the generated hcloud catalog.",
                "available_catalog_operations_sample": sorted(catalog_service.get("operations", {}))[:50],
            }
        if not hcloud_catalog.is_discovery_operation(operation):
            required = hcloud_catalog.normalized_required_params(operation)
            if not hcloud_catalog.is_read_only(operation):
                error = "Operation is not read-only; use hcloud_service_change_plan.py for a planner-only change plan."
            elif required:
                error = "Operation requires explicit parameters; use hcloud_resource_query.py with --param KEY=VALUE."
            else:
                error = "Operation is read-only but is not a generic discovery action; use hcloud_resource_query.py."
            return {
                "success": False,
                "service": requested_service,
                "operation": str(operation.get("name") or args.operation),
                "coverage": "metadata-backed",
                "metadata_backed": True,
                "catalog_required_params": required,
                "catalog_operation_summary": operation.get("summary"),
                "catalog_operation_method": operation.get("method"),
                "catalog_operation_path": operation.get("path"),
                "error": error,
            }
        operations = [operation]
    else:
        max_operations = getattr(args, "catalog_max_operations", DEFAULT_CATALOG_DISCOVERY_LIMIT)
        operations = hcloud_catalog.discovery_operations(catalog_service, max_operations)
        if not operations:
            return {
                "success": False,
                "service": requested_service,
                "coverage": "metadata-backed",
                "metadata_backed": True,
                "error": "No parameter-free read-only discovery operations were found in the generated hcloud catalog.",
                "next_actions": [
                    "Use hcloud_resource_query.py with an explicit --operation and --param values for target-scoped reads.",
                    "Use hcloud_service_change_plan.py for mutating operations; it remains planner-only.",
                ],
            }

    commands = [build_catalog_command_item(args, command_service, operation, service_entry) for operation in operations]
    result = {
        "success": True,
        "mode": "execute" if args.execute else "plan",
        "service": requested_service,
        "coverage": "metadata-backed",
        "metadata_backed": True,
        "catalog_service": command_service,
        "catalog_operation_count": catalog_service.get("operation_count", len(catalog_service.get("operations", {}))),
        "known_limits": [
            "Metadata-backed discovery is generated from bundled hcloud catalog data, not a curated service playbook.",
            "Only read-only operations with no required non-project parameters are used automatically.",
            "Use explicit resource query or planner tools for target-scoped reads and mutating operations.",
        ],
        "playbooks": service_entry.get("playbooks", []),
        "commands": commands,
    }
    if args.operation and operations and args.operation != operations[0].get("name"):
        result["requested_operation"] = args.operation
    return result


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build list-only discovery commands without mutating cloud resources."""
    registry = load_registry()
    service = args.service.upper()
    service_entry = registry["services"].get(service)
    if service_entry is None:
        catalog = hcloud_catalog.load_catalog()
        catalog_service = hcloud_catalog.resolve_service(catalog, args.service)
        if catalog_service:
            return build_catalog_plan(args, service, catalog_service)
        return {
            "success": False,
            "service": service,
            "error": f"Service is not registered: {service}",
            "available_services": sorted(registry["services"]),
            "available_catalog_services": hcloud_catalog.catalog_service_names(catalog),
        }
    query_runner = service_entry.get("query_runner")
    if query_runner and query_runner != "scripts/hcloud_resource_discovery.py":
        return {
            "success": False,
            "service": service,
            "error": "Service uses a dedicated query runner and is not compatible with generic discovery.",
            "query_runner": query_runner,
            "available_query_operations": service_entry.get("query_operations", []),
        }

    operations = service_entry.get("query_operations", [])
    if args.operation:
        operation = resolve_query_operation(operations, args.operation)
        if operation is None:
            catalog = hcloud_catalog.load_catalog()
            catalog_service = hcloud_catalog.resolve_service(catalog, args.service)
            if catalog_service:
                return build_catalog_plan(args, service, catalog_service, service_entry)
            return {
                "success": False,
                "service": service,
                "operation": args.operation,
                "error": f"Operation is not registered as list-only query for {service}: {args.operation}",
                "available_query_operations": operations,
            }
        operations = [operation]

    commands = [build_command_item(args, service, operation, service_entry) for operation in operations]
    result = {
        "success": True,
        "mode": "execute" if args.execute else "plan",
        "service": service,
        "coverage": service_entry.get("coverage"),
        "known_limits": service_entry.get("known_limits", []),
        "playbooks": service_entry.get("playbooks", []),
        "commands": commands,
    }
    if args.operation and operations and args.operation != operations[0]:
        result["requested_operation"] = args.operation
    return result


def execute_plan(plan: dict[str, Any], timeout: int) -> dict[str, Any]:
    """Run discovery commands and attach structured results."""
    results = []
    for item in plan.get("commands", []):
        completed = subprocess.run(
            item["command"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
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
        results.append(
            {
                "service": item["service"],
                "operation": item["operation"],
                "result": result,
            }
        )
    plan = dict(plan)
    plan["results"] = results
    plan["success"] = all(item["result"].get("success") for item in results)
    return plan


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Registered service name, for example ECS, VPC, IMS, KPS, IAM.")
    parser.add_argument("--operation", help="Optional registered list-only operation to run.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, help="Optional limit parameter for list operations that support it.")
    parser.add_argument(
        "--catalog-max-operations",
        type=int,
        default=DEFAULT_CATALOG_DISCOVERY_LIMIT,
        help="Maximum metadata-backed discovery operations to generate for a registry-missing service.",
    )
    parser.add_argument("--execute", action="store_true", help="Run the generated safe_exec commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed command.")
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write the full JSON result privately and print a compact receipt.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.catalog_max_operations < 1:
        parser.error("--catalog-max-operations must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run list-only discovery commands."""
    args = parse_args()
    result = build_plan(args)
    if result["success"] and args.execute:
        result = execute_plan(result, args.timeout)
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
