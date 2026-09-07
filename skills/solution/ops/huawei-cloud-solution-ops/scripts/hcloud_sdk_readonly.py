#!/usr/bin/env python3
"""Plan or run curated Huawei Cloud SDK read-only calls.

This convenience runner intentionally supports a small registry of stable
read-only calls. Its registry is not a policy boundary for task-specific SDK
programs written by an Agent.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_resource_query
import hcloud_sdk_catalog
import hcloud_sdk_supplement_audit


def parse_key_value(values: list[str], label: str) -> dict[str, str]:
    """Parse repeated KEY=VALUE arguments."""
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid {label}, expected KEY=VALUE: {value}")
        key, raw = value.split("=", 1)
        key = hcloud_sdk_catalog.normalize_param_name(key)
        raw = raw.strip()
        if not key or not raw:
            raise ValueError(f"Invalid {label}, expected non-empty KEY=VALUE: {value}")
        parsed[key] = raw
    return parsed


def coerce_value(value: str, type_name: str) -> Any:
    """Coerce a CLI string into a simple SDK request scalar."""
    lowered_type = type_name.lower()
    if lowered_type in {"int", "integer"}:
        return int(value)
    if lowered_type in {"float", "double"}:
        return float(value)
    if lowered_type == "bool":
        lowered = value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        raise ValueError(f"Invalid bool value: {value}")
    return value


def sdk_python_paths(sdk_root: Path | None, package: str) -> list[str]:
    """Return import paths required for optional local SDK source execution."""
    paths = []
    if not sdk_root:
        return paths
    core_path = sdk_root / "huaweicloud-sdk-core"
    if core_path.exists():
        paths.append(str(core_path))
    for distribution in sdk_root.glob("huaweicloud-sdk-*"):
        if (distribution / package).exists():
            paths.append(str(distribution))
            break
    return paths


def hcloud_fallback_plan(args: argparse.Namespace, operation: str | None = None) -> dict[str, Any]:
    """Return the equivalent hcloud read query plan when possible."""
    hcloud_args = argparse.Namespace(
        service=args.service,
        operation=operation or args.operation,
        param=list(args.param),
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )
    try:
        return hcloud_resource_query.build_plan(hcloud_args)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def select_sdk_operation(sdk_result: dict[str, Any], expected_operation: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return the best package/version/operation match from SDK metadata."""
    candidates = []
    for package in sdk_result.get("packages", []):
        for version in package.get("versions", []):
            operation = version.get("operation")
            if operation:
                candidates.append((package, version, operation))
    if expected_operation:
        for package, version, operation in candidates:
            if operation.get("name") == expected_operation:
                return package, version, operation
    if candidates:
        return candidates[0]
    raise ValueError("SDK operation metadata not found.")


def missing_required_params(operation: dict[str, Any], provided: dict[str, str]) -> list[str]:
    """Return required business path params missing from provided inputs."""
    required = [hcloud_sdk_catalog.normalize_param_name(name) for name in operation.get("required_business_path_params", [])]
    return sorted(name for name in required if name not in provided)


def request_kwargs(operation: dict[str, Any], params: dict[str, str]) -> dict[str, Any]:
    """Build SDK request constructor kwargs from provided parameters and SDK types."""
    types = (operation.get("request_model") or {}).get("openapi_types", {})
    attribute_map = (operation.get("request_model") or {}).get("attribute_map", {})
    normalized_to_attr = {
        hcloud_sdk_catalog.normalize_param_name(str(serialized_name)): attr
        for attr, serialized_name in attribute_map.items()
    } if isinstance(attribute_map, dict) else {}
    kwargs: dict[str, Any] = {}
    for key, value in params.items():
        if key not in normalized_to_attr and key not in types:
            continue
        attr = normalized_to_attr.get(key, key)
        kwargs[attr] = coerce_value(value, str(types.get(attr, "str"))) if isinstance(types, dict) else value
    return kwargs


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a curated SDK read-only plan, optionally executing it."""
    service = args.service.upper()
    operation = hcloud_resource_query.canonical_operation(service, args.operation)
    supplement_registry = getattr(args, "supplement_registry", hcloud_sdk_supplement_audit.REGISTRY_PATH)
    registry_allowlist = hcloud_sdk_supplement_audit.registry_allowlist(supplement_registry)
    registry_entry = registry_allowlist.get((service, operation))
    hcloud_operation = str((registry_entry or {}).get("hcloud_operation") or operation)
    sdk_result = hcloud_sdk_catalog.inspect_sdk(args.sdk_root, service=service, operation=operation, max_regions=10)
    result: dict[str, Any] = {
        "success": False,
        "mode": "execute" if args.execute else "plan",
        "runtime": "sdk",
        "backend": "sdk",
        "runner_scope": "curated_readonly_shortcut",
        "backend_preference": "hcloud_then_sdk",
        "service": service,
        "operation": operation,
        "sdk_source_root": str(args.sdk_root) if args.sdk_root else None,
        "package_discovery": "installed_packages_first",
        "supplement_registry": str(supplement_registry),
        "allowlist": sorted(f"{item[0]}:{item[1]}" for item in registry_allowlist),
        "registry_entry": registry_entry,
        "hcloud_fallback_plan": hcloud_fallback_plan(args, hcloud_operation),
    }
    if registry_entry is None:
        result["error"] = (
            "SDK operation is not in sdk-supplement-registry; this registry limits "
            "only this convenience runner. Prefer hcloud, or write task-specific SDK "
            "code after validating the installed official package and API contract."
        )
        result["sdk_metadata"] = sdk_result
        return result
    if not sdk_result.get("success"):
        result["error"] = sdk_result.get("error", "SDK metadata lookup failed.")
        result["sdk_metadata"] = sdk_result
        return result

    package, version, operation_entry = select_sdk_operation(sdk_result, str(registry_entry.get("sdk_operation") or operation))
    result["sdk_metadata"] = {
        "package": package.get("package"),
        "distribution": package.get("distribution"),
        "source_kind": package.get("source_kind"),
        "version": version.get("version"),
        "client_module": version.get("client_module"),
        "client_class": version.get("client_class"),
        "operation": operation_entry.get("name"),
        "method_name": operation_entry.get("method_name"),
        "method": operation_entry.get("method"),
        "resource_path": operation_entry.get("resource_path"),
        "read_only": operation_entry.get("read_only"),
        "request_params": operation_entry.get("request_params", []),
        "regions_sample": version.get("regions", [])[:5],
    }
    if not operation_entry.get("read_only"):
        result["error"] = "SDK bridge only supports read-only operations."
        return result
    if operation_entry["name"] != registry_entry.get("sdk_operation"):
        result["error"] = "SDK metadata operation does not match supplement registry entry."
        return result

    params = parse_key_value(args.param, "--param")
    if args.project_id:
        params.setdefault("project_id", args.project_id)
    missing = missing_required_params(operation_entry, params)
    if missing:
        result.update(
            {
                "missing_params": missing,
                "provided_params": sorted(params),
                "error": "Missing required SDK operation parameters.",
            }
        )
        return result

    result.update(
        {
            "success": True,
            "provided_params": sorted(params),
            "request_kwargs": request_kwargs(operation_entry, params),
            "execution_boundary": "execute only when --execute is set; generic SDK mutations are not supported",
        }
    )
    if args.execute:
        execution = execute_sdk_call(args, package, version, operation_entry, params)
        result["execution_success"] = execution.get("success", False)
        result["result"] = execution
        result["success"] = bool(execution.get("success"))
    return result


def execute_sdk_call(
    args: argparse.Namespace,
    package: dict[str, Any],
    version: dict[str, Any],
    operation: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any]:
    """Execute one allowlisted SDK read-only call."""
    package_name = str(package["package"])
    for path in sdk_python_paths(args.sdk_root, package_name):
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        client_module = importlib.import_module(str(version["client_module"]))
        client_class = getattr(client_module, str(version["client_class"]))
        builder = client_class.new_builder()
        if args.endpoint:
            builder = builder.with_endpoint(args.endpoint)
        elif args.region:
            service_key = str(package["service_key"])
            region_module = importlib.import_module(f"{package_name}.{version['version']}.region.{service_key}_region")
            region_class = getattr(region_module, f"{hcloud_sdk_catalog.snake_to_camel(service_key)}Region")
            builder = builder.with_region(region_class.value_of(args.region))
        else:
            return {"success": False, "error": "SDK execution requires --region or --endpoint."}

        client = builder.build()
        model_module = importlib.import_module(f"{package_name}.{version['version']}.model")
        request_class = getattr(model_module, str(operation["request_type"]))
        request = request_class(**request_kwargs(operation, params))
        response = getattr(client, str(operation["method_name"]))(request)
        if hasattr(response, "to_str"):
            return {"success": True, "response": json.loads(response.to_str())}
        if hasattr(response, "to_json_object"):
            return {"success": True, "response": response.to_json_object()}
        if hasattr(response, "to_dict"):
            return {"success": True, "response": response.to_dict()}
        return {"success": True, "response": str(response)}
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "credential_note": "SDK uses Huawei Cloud SDK provider chain; prefer HUAWEICLOUD_SDK_AK/SK or SDK credentials file.",
        }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdk-root",
        type=Path,
        default=hcloud_sdk_catalog.DEFAULT_SDK_ROOT,
        help="Explicit huaweicloud-sdk-python-v3 source tree used only as a maintenance/test fallback after installed packages.",
    )
    parser.add_argument(
        "--supplement-registry",
        type=Path,
        default=hcloud_sdk_supplement_audit.REGISTRY_PATH,
        help="Path to sdk-supplement-registry.json.",
    )
    parser.add_argument("--service", required=True, help="Huawei Cloud service name.")
    parser.add_argument("--operation", required=True, help="SDK operation name.")
    parser.add_argument("--param", action="append", default=[], help="Explicit SDK request parameter as KEY=VALUE. Can be repeated.")
    parser.add_argument("--region", help="SDK region id. Required for execution unless --endpoint is set.")
    parser.add_argument("--endpoint", help="Explicit SDK endpoint for execution.")
    parser.add_argument("--project-id", help="Optional project_id parameter.")
    parser.add_argument("--profile", help="Optional hcloud profile used only for fallback hcloud plan generation.")
    parser.add_argument("--execute", action="store_true", help="Execute the allowlisted SDK read-only call.")
    parser.add_argument("--timeout", type=int, default=120, help="Reserved timeout hint for fallback hcloud plan.")
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write the full JSON result privately and print a compact receipt.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build or run a narrow SDK read-only plan."""
    args = parse_args()
    if args.execute:
        os.environ.setdefault("PYTHONWARNINGS", "ignore::DeprecationWarning")
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
