#!/usr/bin/env python3
"""Build or run explicit-parameter read queries from the service registry."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_change_plan
import hcloud_common
import hcloud_operation_resolver
import hcloud_resource_discovery
import hcloud_sdk_catalog
import hcloud_sdk_supplement_audit
from hcloud_meta_lookup import collect_template_dirs, load_operation_detail, normalize_token

ROOT = hcloud_common.ROOT

CURATED_REQUIRED_PARAMS = {
    ("CCE", "ListNodes"): ("cluster_id",),
    ("CCE", "ShowCluster"): ("cluster_id",),
    ("CDN", "ShowDomainDetail"): ("domain_id",),
    ("DNS", "ShowPublicZone"): ("zone_id",),
    ("DNS", "ShowRecordSet"): ("zone_id", "recordset_id"),
    ("ECS", "ListServerBlockDevices"): ("server_id",),
    ("ECS", "ListServerInterfaces"): ("server_id",),
    ("ECS", "ListServerVolumeAttachments"): ("server_id",),
    ("ECS", "ShowJob"): ("job_id",),
    ("ECS", "ShowResetPasswordFlag"): ("server_id",),
    ("ECS", "ShowServer"): ("server_id",),
    ("ECS", "ShowServerBlockDevice"): ("server_id", "volume_id"),
    ("ECS", "ShowServerGroup"): ("server_group_id",),
    ("ECS", "ShowServerTags"): ("server_id",),
    ("EIP", "ShowPublicip"): ("publicip_id",),
    ("ELB", "ShowCertificate"): ("certificate_id",),
    ("ELB", "ShowHealthMonitor"): ("healthmonitor_id",),
    ("ELB", "ShowListener"): ("listener_id",),
    ("ELB", "ShowLoadBalancer"): ("loadbalancer_id",),
    ("ELB", "ShowLoadBalancerStatus"): ("loadbalancer_id",),
    ("ELB", "ShowMember"): ("pool_id", "member_id"),
    ("ELB", "ShowPool"): ("pool_id",),
    ("ELB", "ListMembers"): ("pool_id",),
    ("EVS", "ShowJob"): ("job_id",),
    ("EVS", "ShowSnapshot"): ("snapshot_id",),
    ("EVS", "ShowVolume"): ("volume_id",),
    ("EVS", "ShowVolumeTags"): ("volume_id",),
    ("IMS", "GlanceShowImage"): ("image_id",),
    ("IMS", "GlanceShowImageMember"): ("image_id", "member_id"),
    ("IMS", "ShowImageMember"): ("image_id", "member_id"),
    ("IMS", "ShowJob"): ("job_id",),
    ("KPS", "ListKeypairDetail"): ("keypair_name",),
    ("NAT", "ShowNatGateway"): ("nat_gateway_id",),
    ("NAT", "ShowNatGatewayDnatRule"): ("dnat_rule_id",),
    ("NAT", "ShowNatGatewaySnatRule"): ("snat_rule_id",),
    ("RDS", "ShowBackupPolicy"): ("instance_id",),
    ("RDS", "ShowConfiguration"): ("config_id",),
    ("RDS", "ShowInstanceConfiguration"): ("instance_id",),
    ("SCM", "ShowCertificate"): ("certificate_id",),
    ("VPC", "ShowPort"): ("port_id",),
    ("VPC", "ShowSecurityGroup"): ("security_group_id",),
    ("VPC", "ShowSecurityGroupRule"): ("security_group_rule_id",),
    ("VPC", "ShowSubnet"): ("subnet_id",),
    ("VPC", "ShowVpc"): ("vpc_id",),
}
OPERATION_ALIASES = {
    ("CDN", "ShowDomain"): "ShowDomainDetail",
    ("RDS", "ShowConfigurationDetail"): "ShowConfiguration",
}
IGNORED_REQUIRED_PARAMS = {"x-auth-token", "project_id", "projectid"}


def parse_key_value(values: list[str], label: str) -> dict[str, str]:
    """Parse repeated KEY=VALUE arguments."""
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid {label}, expected KEY=VALUE: {value}")
        key, raw = value.split("=", 1)
        key = normalize_param_name(key)
        raw = raw.strip()
        if not key or not raw:
            raise ValueError(f"Invalid {label}, expected non-empty KEY=VALUE: {value}")
        parsed[key] = raw
    return parsed


def normalize_param_name(value: str) -> str:
    """Normalize a KooCLI parameter name for comparison."""
    return value.strip().lstrip("-").replace("-", "_").lower()


def arg_param_name(value: str) -> str | None:
    """Extract the parameter name from a raw hcloud argument token."""
    token = value.strip()
    if not token.startswith("--"):
        return None
    return normalize_param_name(token.split("=", 1)[0])


def arg_param_value(value: str) -> tuple[str, str] | None:
    """Extract normalized name/value from a raw --arg=... token."""
    token = value.strip()
    if not token.startswith("--") or "=" not in token:
        return None
    key, raw = token.split("=", 1)
    return normalize_param_name(key), raw


def operation_scope(service_entry: dict[str, Any], operation: str) -> str | None:
    """Return whether an operation is a generic or explicit-parameter read query."""
    base_operation, _ = hcloud_catalog.split_operation_version(operation)
    if base_operation in service_entry.get("resource_query_operations", []):
        return "resource_query"
    if base_operation in service_entry.get("query_operations", []):
        return "query"
    return None


def canonical_operation(service: str, operation: str) -> str:
    """Return the executable KooCLI operation name for a user-facing alias."""
    base_operation, version = hcloud_catalog.split_operation_version(operation)
    canonical = OPERATION_ALIASES.get((service.upper(), base_operation), base_operation)
    return f"{canonical}/{version}" if version else canonical


def resolve_registered_operation(service_entry: dict[str, Any], operation: str) -> str | None:
    """Resolve operation aliases and case variants against registered read operations."""
    base_operation, explicit_version = hcloud_catalog.split_operation_version(operation)
    registered = list(service_entry.get("resource_query_operations", [])) + list(service_entry.get("query_operations", []))
    if base_operation in registered:
        return f"{base_operation}/{explicit_version}" if explicit_version else base_operation
    normalized_operation = hcloud_resource_discovery.normalize_operation(base_operation)
    for item in registered:
        if hcloud_resource_discovery.normalize_operation(item) == normalized_operation:
            return f"{item}/{explicit_version}" if explicit_version else item
    return None


def metadata_required_params(service: str, operation: str) -> list[str]:
    """Return required non-header params from local KooCLI metadata when available."""
    meta_repo = Path.home() / ".hcloud" / "metaRepo"
    template_dir = collect_template_dirs(meta_repo).get(normalize_token(service))
    detail = load_operation_detail(template_dir, operation)
    if not isinstance(detail, dict):
        return []

    required: list[str] = []
    for param in detail.get("params", []):
        if not param.get("required"):
            continue
        if str(param.get("position", "")).lower() == "header":
            continue
        names = param.get("name", [])
        if not names:
            continue
        name = normalize_param_name(str(names[0]))
        if name in IGNORED_REQUIRED_PARAMS:
            continue
        required.append(name)
    return required


def required_params(service: str, operation: str) -> list[str]:
    """Return required explicit parameters for a read query."""
    base_operation, _ = hcloud_catalog.split_operation_version(operation)
    params = set(metadata_required_params(service, operation))
    params.update(catalog_required_params(service, operation))
    params.update(CURATED_REQUIRED_PARAMS.get((service.upper(), base_operation), ()))
    return sorted(params)


def catalog_required_params(service: str, operation: str) -> list[str]:
    """Return required non-auth parameters from the generated hcloud catalog."""
    catalog = hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return []
    catalog_operation = hcloud_catalog.resolve_operation(catalog_service, operation)
    if not catalog_operation:
        return []
    _, version = hcloud_catalog.split_operation_version(operation)
    detail = hcloud_catalog.operation_version_detail(catalog_operation, version)
    return hcloud_catalog.normalized_required_params(detail or catalog_operation)


def provided_param_names(args: argparse.Namespace, params: dict[str, str]) -> set[str]:
    """Return normalized parameter names already provided by the user."""
    names = set(params)
    if args.project_id:
        names.add("project_id")
    for raw_arg in args.arg:
        name = arg_param_name(raw_arg)
        if name:
            names.add(name)
    return names


def sdk_supplement_for_hcloud(service: str, operation: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return curated SDK supplement entry and metadata hint for a hcloud operation."""
    base_operation, _ = hcloud_catalog.split_operation_version(operation)
    supplement = hcloud_sdk_supplement_audit.registry_entry_for_hcloud_operation(service, base_operation)
    if not supplement:
        return None, None
    sdk_operation = str(supplement.get("sdk_operation") or base_operation)
    return supplement, hcloud_sdk_catalog.sdk_hint_for_operation(service, sdk_operation)


def sdk_request_types(sdk_hint: dict[str, Any] | None) -> dict[str, str]:
    """Return SDK request types keyed by normalized parameter name."""
    if not sdk_hint:
        return {}
    request_types = sdk_hint.get("request_types") or {}
    if not isinstance(request_types, dict):
        return {}
    return {normalize_param_name(str(key)): str(value) for key, value in request_types.items()}


def validate_sdk_param_value(name: str, value: str, type_name: str) -> dict[str, Any] | None:
    """Return a validation error for an SDK typed parameter value, if any."""
    normalized_type = type_name.lower()
    try:
        if normalized_type in {"int", "integer"}:
            int(value)
        elif normalized_type in {"float", "double"}:
            float(value)
        elif normalized_type == "bool":
            if value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("expected bool")
    except ValueError:
        return {
            "param": name,
            "value": value,
            "expected_type": type_name,
            "message": f"Parameter {name} must be {type_name} according to SDK metadata.",
        }
    return None


def validate_sdk_typed_params(
    args: argparse.Namespace,
    params: dict[str, str],
    sdk_hint: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Validate explicit parameters using curated SDK request type metadata."""
    request_types = sdk_request_types(sdk_hint)
    if not request_types:
        return None
    checked = []
    errors = []
    for name, value in params.items():
        type_name = request_types.get(normalize_param_name(name))
        if not type_name:
            continue
        checked.append({"param": name, "type": type_name, "source": "--param"})
        error = validate_sdk_param_value(name, value, type_name)
        if error:
            errors.append(error)
    for raw_arg in args.arg:
        parsed = arg_param_value(raw_arg)
        if not parsed:
            continue
        name, value = parsed
        type_name = request_types.get(name)
        if not type_name:
            continue
        checked.append({"param": name, "type": type_name, "source": "--arg"})
        error = validate_sdk_param_value(name, value, type_name)
        if error:
            errors.append(error)
    return {
        "source": "sdk_supplement_registry",
        "checked": checked,
        "errors": errors,
    }


def build_command(
    args: argparse.Namespace,
    service_entry: dict[str, Any],
    params: dict[str, str],
    operation: str,
    command_service: str,
    param_flag_names: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, Any] | None]:
    """Build the safe_exec command for an explicit read query."""
    param_flag_names = param_flag_names or {}
    cli_region, region_resolution = hcloud_resource_discovery.resolve_cli_region(args, service_entry)
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        command_service,
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
    for key, value in sorted(params.items()):
        flag_name = param_flag_names.get(key, key)
        command.append(f"--arg=--{flag_name}={value}")
    for raw_arg in args.arg:
        if not raw_arg.startswith("--"):
            raise ValueError(f"Raw --arg values must start with --: {raw_arg}")
        command.append(f"--arg={raw_arg}")
    return command, region_resolution


def catalog_context(service: str, operation: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    """Return catalog service, operation, and hcloud command service name."""
    catalog = hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return None, None, service.upper()
    catalog_operation = hcloud_catalog.resolve_operation(catalog_service, operation)
    command_service = hcloud_catalog.command_service_name(catalog_service, service.upper())
    return catalog_service, catalog_operation, command_service


def catalog_param_flag_names(catalog_operation: dict[str, Any] | None) -> dict[str, str]:
    """Return normalized parameter names mapped to catalog-preserved CLI flag names."""
    if not catalog_operation:
        return {}
    result: dict[str, str] = {}
    for name in hcloud_catalog.operation_param_names(catalog_operation):
        normalized = normalize_param_name(name)
        if normalized:
            result[normalized] = name
    return result


def execute_command(command: list[str], timeout: int) -> dict[str, Any]:
    """Run one safe_exec read query and parse its JSON output."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
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


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run an explicit-parameter read query plan."""
    registry = hcloud_resource_discovery.load_registry()
    service = args.service.upper()
    requested_operation = args.operation
    aliased_operation = canonical_operation(service, requested_operation)
    entry = registry.get("services", {}).get(service)
    catalog_service, catalog_operation, command_service = catalog_context(service, aliased_operation)
    if entry is None:
        if catalog_service is None:
            return {
                "success": False,
                "service": service,
                "operation": aliased_operation,
                "requested_operation": requested_operation,
                "error": f"Service is not registered and is not present in the generated hcloud catalog: {service}",
                "available_services": sorted(registry.get("services", {})),
                "available_catalog_services": hcloud_catalog.catalog_service_names(hcloud_catalog.load_catalog()),
            }
        if catalog_operation is None:
            return {
                "success": False,
                "service": service,
                "operation": aliased_operation,
                "requested_operation": requested_operation,
                "coverage": "metadata-backed",
                "metadata_backed": True,
                "error": "Operation is not present in the generated hcloud catalog.",
                "available_catalog_operations_sample": sorted(catalog_service.get("operations", {}))[:50],
            }
        if not hcloud_catalog.is_read_only(catalog_operation):
            return {
                "success": False,
                "service": service,
                "operation": str(catalog_operation.get("name") or aliased_operation),
                "requested_operation": requested_operation,
                "coverage": "metadata-backed",
                "metadata_backed": True,
                "catalog_operation_summary": catalog_operation.get("summary"),
                "error": "Operation is mutating; use hcloud_service_change_plan.py for a planner-only change plan.",
            }
        operation = str(catalog_operation.get("name") or aliased_operation)
        scope = "metadata_resource_query" if hcloud_catalog.normalized_required_params(catalog_operation) else "metadata_query"
        command_entry: dict[str, Any] = {}
    else:
        resource_query_runner = entry.get("resource_query_runner")
        if resource_query_runner and resource_query_runner != "scripts/hcloud_resource_query.py":
            return {
                "success": False,
                "service": service,
                "operation": aliased_operation,
                "requested_operation": requested_operation,
                "error": "Service uses a dedicated resource query runner and is not compatible with generic resource query.",
                "resource_query_runner": resource_query_runner,
                "available_resource_query_operations": entry.get("resource_query_operations", []),
            }

        operation = resolve_registered_operation(entry, aliased_operation)
        if operation is None:
            if catalog_operation is None:
                return {
                    "success": False,
                    "service": service,
                    "operation": aliased_operation,
                    "requested_operation": requested_operation,
                    "error": "Operation is not registered as a read query for this service and is not present in the generated hcloud catalog.",
                    "available_query_operations": entry.get("query_operations", []),
                    "available_resource_query_operations": entry.get("resource_query_operations", []),
                    "available_catalog_operations_sample": sorted(catalog_service.get("operations", {}))[:50] if catalog_service else [],
                }
            if not hcloud_catalog.is_read_only(catalog_operation):
                return {
                    "success": False,
                    "service": service,
                    "operation": str(catalog_operation.get("name") or aliased_operation),
                    "requested_operation": requested_operation,
                    "coverage": "metadata-backed",
                    "metadata_backed": True,
                    "catalog_operation_summary": catalog_operation.get("summary"),
                    "error": "Operation is mutating; use hcloud_service_change_plan.py for a planner-only change plan.",
                }
            operation = str(catalog_operation.get("name") or aliased_operation)
            scope = "metadata_resource_query" if hcloud_catalog.normalized_required_params(catalog_operation) else "metadata_query"
        else:
            scope = operation_scope(entry, operation)
        command_entry = entry

    if scope is None:
        return {
            "success": False,
            "service": service,
            "operation": operation,
            "requested_operation": requested_operation,
            "error": "Operation is not registered as a read query for this service.",
            "available_query_operations": entry.get("query_operations", []) if entry else [],
            "available_resource_query_operations": entry.get("resource_query_operations", []) if entry else [],
        }

    base_operation, _ = hcloud_catalog.split_operation_version(operation)
    risk = hcloud_change_plan.assess_risk(base_operation, dryrun_supported=False)
    if risk.level == "high" and not args.allow_sensitive_read:
        return {
            "success": False,
            "service": service,
            "operation": base_operation,
            "requested_operation": requested_operation,
            "operation_scope": scope,
            "risk": risk.to_dict(),
            "error": "Sensitive read operation requires --allow-sensitive-read.",
        }

    params = parse_key_value(args.param, "--param")
    provided_params = provided_param_names(args, params)
    version_resolution = hcloud_operation_resolver.resolve_operation_version(
        command_service,
        operation,
        provided_params,
    )
    if not version_resolution.get("success"):
        result = {
            "success": False,
            "service": service,
            "operation": base_operation,
            "requested_operation": requested_operation,
            "operation_scope": scope,
            "provided_params": sorted(provided_params),
            "version_resolution": version_resolution,
            "corrected_operation": version_resolution.get("corrected_operation"),
            "error": "Operation API version resolution failed.",
        }
        corrected_operation = version_resolution.get("corrected_operation")
        if corrected_operation:
            corrected_command, _ = build_command(
                args,
                command_entry,
                params,
                str(corrected_operation),
                command_service if scope.startswith("metadata_") else service,
            )
            result["corrected_command"] = corrected_command
            result["corrected_command_shell"] = shlex.join(corrected_command)
        return result

    resolved_operation = str(version_resolution.get("resolved_operation") or operation)
    resolved_base_operation, resolved_version = hcloud_catalog.split_operation_version(
        resolved_operation
    )
    selected_catalog_detail = (
        hcloud_catalog.operation_version_detail(catalog_operation, resolved_version)
        if catalog_operation
        else None
    )
    required = required_params(service, resolved_operation)
    missing = [name for name in required if name not in provided_params]
    sdk_supplement, sdk_hint = sdk_supplement_for_hcloud(service, resolved_operation)
    if missing:
        return {
            "success": False,
            "service": service,
            "operation": resolved_base_operation,
            "resolved_operation": resolved_operation,
            "requested_operation": requested_operation,
            "operation_scope": scope,
            "required_params": required,
            "provided_params": sorted(provided_params),
            "missing_params": missing,
            "version_resolution": version_resolution,
            "error": "Missing required explicit query parameters.",
        }
    sdk_validation = validate_sdk_typed_params(args, params, sdk_hint)
    if sdk_validation and sdk_validation["errors"]:
        return {
            "success": False,
            "service": service,
            "operation": resolved_base_operation,
            "resolved_operation": resolved_operation,
            "requested_operation": requested_operation,
            "operation_scope": scope,
            "sdk_supplement": sdk_supplement,
            "sdk_evidence": sdk_hint,
            "sdk_param_validation": sdk_validation,
            "version_resolution": version_resolution,
            "error": "SDK supplement parameter validation failed.",
        }

    command, region_resolution = build_command(
        args,
        command_entry,
        params,
        resolved_operation,
        command_service if scope.startswith("metadata_") else service,
        catalog_param_flag_names(selected_catalog_detail) if scope.startswith("metadata_") else None,
    )
    result: dict[str, Any] = {
        "success": True,
        "mode": "execute" if args.execute else "plan",
        "service": service,
        "operation": resolved_base_operation,
        "resolved_operation": resolved_operation,
        "operation_scope": scope,
        "coverage": "metadata-backed" if scope.startswith("metadata_") else entry.get("coverage"),
        "risk": risk.to_dict(),
        "required_params": required,
        "provided_params": sorted(provided_params),
        "version_resolution": version_resolution,
        "command": command,
        "command_shell": shlex.join(command),
    }
    if scope.startswith("metadata_"):
        result.update(
            {
                "metadata_backed": True,
                "catalog_service": command_service,
                "catalog_operation_summary": (
                    selected_catalog_detail.get("summary")
                    if selected_catalog_detail
                    else catalog_operation.get("summary") if catalog_operation else None
                ),
                "catalog_operation_method": (
                    selected_catalog_detail.get("method")
                    if selected_catalog_detail
                    else catalog_operation.get("method") if catalog_operation else None
                ),
                "catalog_operation_path": (
                    selected_catalog_detail.get("path")
                    if selected_catalog_detail
                    else catalog_operation.get("path") if catalog_operation else None
                ),
            }
        )
    if requested_operation != resolved_base_operation:
        result["requested_operation"] = requested_operation
    if region_resolution:
        result["region_resolution"] = region_resolution
    if sdk_supplement:
        result["sdk_supplement"] = sdk_supplement
    if sdk_hint:
        result["sdk_evidence"] = sdk_hint
    if sdk_validation:
        result["sdk_param_validation"] = sdk_validation
    if args.execute:
        execution = execute_command(command, args.timeout)
        result["execution_success"] = execution.get("success", False)
        result["result"] = execution
        result["success"] = bool(execution.get("success"))
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Registered Huawei Cloud service name.")
    parser.add_argument("--operation", required=True, help="Registered query or resource query operation.")
    parser.add_argument("--param", action="append", default=[], help="Explicit operation parameter as KEY=VALUE. Can be repeated.")
    parser.add_argument("--arg", action="append", default=[], help="Raw hcloud argument token such as --name=value. Can be repeated.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--execute", action="store_true", help="Execute the read query through hcloud_safe_exec.py.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for the executed command.")
    parser.add_argument("--allow-sensitive-read", action="store_true", help="Allow high-risk read operations such as password/private-key reads.")
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write the full JSON result privately and print a compact receipt.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run an explicit-parameter resource query."""
    args = parse_args()
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
