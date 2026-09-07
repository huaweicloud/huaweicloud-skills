#!/usr/bin/env python3
"""Validate a KooCLI API request locally before dry-run or submission.

The preflight combines generated KooCLI catalog evidence with an optional,
bounded static schema from an installed Huawei Cloud Python SDK. It never
imports generated SDK models, executes hcloud, or contacts Huawei Cloud.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_operation_resolver
import hcloud_sdk_catalog

KOOCLI_JSON_LOCATIONS = {
    "path": "path",
    "query": "query",
    "body": "body",
    "formdata": "formData",
    "header": "header",
    "cookie": "cookie",
}
MAX_KOOCLI_JSON_BYTES = 5 * 1024 * 1024
SDK_RESULT_AUTO = object()
PARTIAL_EVIDENCE_CODES = {
    "CATALOG_REQUEST_CONTRACT_UNAVAILABLE",
    "SDK_SCHEMA_TRUNCATED",
    "SDK_SCHEMA_UNAVAILABLE",
    "SDK_VERSION_SCHEMA_UNAVAILABLE",
}


def normalize_location(value: str | None) -> str:
    """Return a normalized KooCLI request location."""

    return str(value or "").strip().replace("_", "").lower()


def issue(code: str, message: str, *, path: str | None = None) -> dict[str, str]:
    """Return one stable validation issue without request values."""

    result = {"code": code, "message": message}
    if path:
        result["path"] = path
    return result


def parameter_name(value: str) -> str:
    """Return a catalog-comparable top-level API parameter name."""

    return hcloud_operation_resolver.comparable_param_name(value)


def direct_parameter_names(
    arguments: Iterable[str],
    project_id: str | None = None,
) -> set[str]:
    """Extract direct API parameter names while ignoring KooCLI options."""

    names: set[str] = set()
    for raw in arguments:
        token = str(raw).strip()
        if not token.startswith("--"):
            continue
        name = parameter_name(token.split("=", 1)[0])
        if not name:
            continue
        if name != "project_id" and hcloud_operation_resolver.is_system_param(name):
            continue
        names.add(name)
    if project_id:
        names.add("project_id")
    return names


def validate_envelope(payload: Any) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    """Validate and normalize a KooCLI cli-jsonInput envelope."""

    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        return {}, [
            issue(
                "KOOCLI_JSON_OBJECT_REQUIRED",
                "The cli-jsonInput top-level value must be an object.",
            )
        ]

    locations: dict[str, dict[str, Any]] = {}
    for raw_location, value in payload.items():
        normalized = normalize_location(str(raw_location))
        canonical = KOOCLI_JSON_LOCATIONS.get(normalized)
        if canonical is None:
            errors.append(
                issue(
                    "KOOCLI_JSON_LOCATION_INVALID",
                    "Only path, query, body, formData, header, and cookie are valid top-level locations.",
                    path=str(raw_location),
                )
            )
            continue
        if not isinstance(value, dict):
            errors.append(
                issue(
                    "KOOCLI_JSON_LOCATION_OBJECT_REQUIRED",
                    f"KooCLI location {canonical} must contain an object.",
                    path=canonical,
                )
            )
            continue
        locations[normalized] = value
    return locations, errors


def location_parameter_names(locations: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """Return normalized top-level parameter names grouped by request location."""

    return {
        location: {parameter_name(str(name)) for name in values if parameter_name(str(name))}
        for location, values in locations.items()
    }


def contract_parameters(contract: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Index request-contract parameters by normalized top-level name."""

    if not isinstance(contract, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in contract.get("parameters", []):
        if not isinstance(item, dict):
            continue
        name = parameter_name(str(item.get("name") or ""))
        if name:
            result[name] = item
    return result


def validate_catalog_contract(
    locations: dict[str, dict[str, Any]],
    direct_names: set[str],
    contract: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Validate request locations and required fields using KooCLI metadata."""

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    parameters = contract_parameters(contract)
    if not parameters:
        warnings.append(
            issue(
                "CATALOG_REQUEST_CONTRACT_UNAVAILABLE",
                "Local KooCLI metadata cannot prove parameter placement for this operation.",
            )
        )
        return errors, warnings

    json_names = location_parameter_names(locations)
    all_json_names = set().union(*json_names.values()) if json_names else set()
    provided_names = all_json_names | direct_names

    for location, names in json_names.items():
        for name in sorted(names):
            item = parameters.get(name)
            if item is None:
                warnings.append(
                    issue(
                        "CATALOG_PARAMETER_UNKNOWN",
                        "The local catalog does not describe this top-level parameter; keep dry-run or operation help as the next evidence step.",
                        path=f"{KOOCLI_JSON_LOCATIONS[location]}.{name}",
                    )
                )
                continue
            expected = normalize_location(str(item.get("position") or ""))
            if expected and expected != location:
                errors.append(
                    issue(
                        "CATALOG_PARAMETER_LOCATION_MISMATCH",
                        f"Catalog evidence places this parameter in {KOOCLI_JSON_LOCATIONS.get(expected, expected)}, not {KOOCLI_JSON_LOCATIONS[location]}.",
                        path=f"{KOOCLI_JSON_LOCATIONS[location]}.{name}",
                    )
                )

    direct_positions: dict[str, set[str]] = {}
    for name in sorted(direct_names):
        item = parameters.get(name)
        if item is None:
            warnings.append(
                issue(
                    "CATALOG_DIRECT_PARAMETER_UNKNOWN",
                    "The local catalog does not describe this direct API parameter.",
                    path=name,
                )
            )
            continue
        location = normalize_location(str(item.get("position") or ""))
        if location:
            direct_positions.setdefault(location, set()).add(name)

    for location, names in json_names.items():
        direct_at_location = direct_positions.get(location, set())
        if names and direct_at_location:
            errors.append(
                issue(
                    "KOOCLI_POSITION_SPLIT",
                    "KooCLI requires parameters from one request location to be supplied together in JSON or together on the command line.",
                    path=KOOCLI_JSON_LOCATIONS[location],
                )
            )

    for name, item in sorted(parameters.items()):
        if item.get("required") is True and name not in provided_names:
            position = normalize_location(str(item.get("position") or ""))
            prefix = KOOCLI_JSON_LOCATIONS.get(position, position)
            errors.append(
                issue(
                    "CATALOG_REQUIRED_PARAMETER_MISSING",
                    "A required top-level API parameter is missing.",
                    path=f"{prefix}.{name}" if prefix else name,
                )
            )
    return errors, warnings


def primitive_type_matches(value: Any, type_name: str) -> bool:
    """Return whether a JSON value matches a generated SDK primitive type."""

    normalized = type_name.strip().lower()
    if normalized in {"any", "object"}:
        return True
    if normalized in {"str", "date", "datetime", "bytes"}:
        return isinstance(value, str)
    if normalized == "bool":
        return isinstance(value, bool)
    if normalized == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if normalized == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if normalized in {"dict", "map"}:
        return isinstance(value, dict)
    return True


def validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    """Validate one JSON value against bounded static SDK schema evidence."""

    if schema.get("truncated") is True or schema.get("recursive_reference") is True:
        warnings.append(
            issue(
                "SDK_SCHEMA_TRUNCATED",
                "Nested SDK schema evidence stops at this field; dry-run or operation help must validate deeper content.",
                path=path,
            )
        )
        return
    if schema.get("available") is False:
        warnings.append(
            issue(
                "SDK_SCHEMA_UNAVAILABLE",
                "The referenced SDK model source is unavailable.",
                path=path,
            )
        )
        return

    schema_type = str(schema.get("type") or "any").lower()
    if schema_type == "model":
        if not isinstance(value, dict):
            errors.append(
                issue(
                    "SDK_TYPE_MISMATCH",
                    "SDK schema expects an object.",
                    path=path,
                )
            )
            return
        fields = [item for item in schema.get("fields", []) if isinstance(item, dict)]
        by_serialized = {
            str(item.get("serialized_name") or item.get("name")): item
            for item in fields
            if item.get("serialized_name") or item.get("name")
        }
        for name, field in by_serialized.items():
            child_path = f"{path}.{name}" if path else name
            if field.get("required") is True and name not in value:
                errors.append(
                    issue(
                        "SDK_REQUIRED_FIELD_MISSING",
                        "A required field from the official SDK model is missing.",
                        path=child_path,
                    )
                )
                continue
            if name not in value:
                continue
            child_value = value[name]
            child_schema = field.get("schema")
            if isinstance(child_schema, dict):
                validate_schema_value(
                    child_value,
                    child_schema,
                    child_path,
                    errors,
                    warnings,
                )
            elif not primitive_type_matches(child_value, str(field.get("type") or "any")):
                errors.append(
                    issue(
                        "SDK_TYPE_MISMATCH",
                        f"SDK schema expects type {field.get('type') or 'unknown'}.",
                        path=child_path,
                    )
                )
        for name in sorted(set(value) - set(by_serialized)):
            warnings.append(
                issue(
                    "SDK_UNKNOWN_FIELD",
                    "This field is not present in the installed SDK schema; keep it only with operation-help, skeleton, or official API evidence.",
                    path=f"{path}.{name}" if path else name,
                )
            )
        return

    if schema_type == "array":
        if not isinstance(value, list):
            errors.append(
                issue("SDK_TYPE_MISMATCH", "SDK schema expects an array.", path=path)
            )
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema_value(
                    item,
                    item_schema,
                    f"{path}[{index}]",
                    errors,
                    warnings,
                )
        return

    if schema_type == "object" and "additional_properties" in schema:
        if not isinstance(value, dict):
            errors.append(
                issue("SDK_TYPE_MISMATCH", "SDK schema expects an object map.", path=path)
            )
            return
        value_schema = schema.get("additional_properties")
        if isinstance(value_schema, dict):
            for key, item in value.items():
                validate_schema_value(
                    item,
                    value_schema,
                    f"{path}.{key}" if path else str(key),
                    errors,
                    warnings,
                )
        return

    if not primitive_type_matches(value, schema_type):
        errors.append(
            issue(
                "SDK_TYPE_MISMATCH",
                f"SDK schema expects type {schema_type}.",
                path=path,
            )
        )


def exact_sdk_operation(
    sdk_result: dict[str, Any],
    selected_version: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return the SDK package and operation matching the resolved API version."""

    wanted = hcloud_operation_resolver.normalize_version(selected_version)
    for package in sdk_result.get("packages", []):
        if not isinstance(package, dict):
            continue
        for version in package.get("versions", []):
            if not isinstance(version, dict):
                continue
            if hcloud_operation_resolver.normalize_version(str(version.get("version") or "")) != wanted:
                continue
            operation = version.get("operation")
            if isinstance(operation, dict):
                return package, operation
    return None, None


def value_at_location(
    locations: dict[str, dict[str, Any]],
    location: str,
    serialized_name: str,
) -> tuple[bool, Any, str]:
    """Return a request value from its KooCLI envelope location."""

    normalized = normalize_location(location)
    values = locations.get(normalized, {})
    if normalized == "body" and serialized_name == "body":
        return normalized in locations, values, "body"
    if serialized_name in values:
        return True, values[serialized_name], f"{KOOCLI_JSON_LOCATIONS[normalized]}.{serialized_name}"
    if normalized == "header":
        wanted = serialized_name.lower()
        for name, value in values.items():
            if str(name).lower() == wanted:
                return True, value, f"header.{name}"
    return False, None, f"{KOOCLI_JSON_LOCATIONS.get(normalized, normalized)}.{serialized_name}"


def validate_sdk_request(
    locations: dict[str, dict[str, Any]],
    operation: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Validate envelope values against one exact SDK request schema."""

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    schema = operation.get("request_schema")
    if not isinstance(schema, dict):
        return errors, [
            issue(
                "SDK_SCHEMA_UNAVAILABLE",
                "The matching SDK operation does not expose a bounded request schema.",
            )
        ]

    request_params = {
        str(item.get("name") or item.get("serialized_name")): item
        for item in operation.get("request_params", [])
        if isinstance(item, dict)
    }
    for field in schema.get("fields", []):
        if not isinstance(field, dict):
            continue
        field_name = str(field.get("name") or field.get("serialized_name") or "")
        serialized_name = str(field.get("serialized_name") or field_name)
        param = request_params.get(field_name) or request_params.get(serialized_name) or {}
        location = str(param.get("position") or "unknown")
        if normalize_location(location) not in KOOCLI_JSON_LOCATIONS:
            warnings.append(
                issue(
                    "SDK_PARAMETER_LOCATION_UNKNOWN",
                    "SDK evidence does not prove the request location for this field.",
                    path=serialized_name,
                )
            )
            continue
        present, value, value_path = value_at_location(
            locations,
            location,
            serialized_name,
        )
        if field.get("required") is True and not present:
            errors.append(
                issue(
                    "SDK_REQUIRED_FIELD_MISSING",
                    "A required SDK request field is missing.",
                    path=value_path,
                )
            )
            continue
        if not present:
            continue
        child_schema = field.get("schema")
        if isinstance(child_schema, dict):
            validate_schema_value(value, child_schema, value_path, errors, warnings)
        elif not primitive_type_matches(value, str(field.get("type") or "any")):
            errors.append(
                issue(
                    "SDK_TYPE_MISMATCH",
                    f"SDK schema expects type {field.get('type') or 'unknown'}.",
                    path=value_path,
                )
            )
    return errors, warnings


def build_sdk_result(
    service: str,
    operation: str,
    *,
    schema_depth: int,
    sdk_root: Path | None,
) -> dict[str, Any]:
    """Inspect exact installed SDK metadata without importing generated models."""

    return hcloud_sdk_catalog.inspect_sdk(
        sdk_root,
        service=service,
        operation=operation,
        max_regions=0,
        schema_depth=schema_depth,
    )


def sdk_schema_evidence(
    service: str,
    operation: str,
    selected_version: str,
    locations: dict[str, dict[str, Any]],
    *,
    sdk_result: dict[str, Any] | object,
    sdk_root: Path | None,
    schema_depth: int,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    """Return exact-version SDK schema summary and validation issues."""

    summary: dict[str, Any] = {
        "available": False,
        "version": selected_version,
        "schema_depth": schema_depth,
    }
    inspected = (
        build_sdk_result(
            service,
            operation,
            schema_depth=schema_depth,
            sdk_root=sdk_root,
        )
        if sdk_result is SDK_RESULT_AUTO
        else sdk_result
    )
    if not isinstance(inspected, dict) or not inspected.get("success"):
        message = (
            str(inspected.get("error") or "SDK schema evidence is unavailable.")
            if isinstance(inspected, dict)
            else "SDK schema evidence is unavailable."
        )
        warning = issue("SDK_SCHEMA_UNAVAILABLE", message)
        if isinstance(inspected, dict) and inspected.get("install_hint"):
            warning["install_hint"] = str(inspected["install_hint"])
        return summary, [], [warning]

    package, sdk_operation = exact_sdk_operation(inspected, selected_version)
    if sdk_operation is None:
        return summary, [], [
            issue(
                "SDK_VERSION_SCHEMA_UNAVAILABLE",
                "The installed SDK has no request schema for the exact resolved API version.",
            )
        ]

    summary.update(
        {
            "available": True,
            "package": package.get("package") if package else None,
            "operation": sdk_operation.get("name"),
        }
    )
    errors, warnings = validate_sdk_request(locations, sdk_operation)
    return summary, errors, warnings


def preflight_request(
    service: str,
    operation: str,
    payload: Any,
    *,
    direct_arguments: Iterable[str] = (),
    project_id: str | None = None,
    catalog: dict[str, Any] | None = None,
    sdk_result: dict[str, Any] | object = SDK_RESULT_AUTO,
    sdk_root: Path | None = None,
    schema_depth: int = 3,
) -> dict[str, Any]:
    """Validate an in-memory KooCLI request using bounded local evidence."""

    locations, errors = validate_envelope(payload)
    warnings: list[dict[str, str]] = []
    direct_names = direct_parameter_names(direct_arguments, project_id)
    json_names = location_parameter_names(locations)
    provided_names = set().union(*json_names.values()) if json_names else set()
    provided_names.update(direct_names)

    resolution = hcloud_operation_resolver.resolve_operation_version(
        service,
        operation,
        provided_names,
        catalog=catalog,
    )
    contract = resolution.get("request_contract") if resolution.get("resolved") else None
    if not resolution.get("success"):
        errors.append(
            issue(
                "OPERATION_VERSION_RESOLUTION_FAILED",
                str(resolution.get("reason") or "No API version supports the provided request parameters."),
            )
        )
    elif not resolution.get("resolved"):
        warnings.append(
            issue(
                "CATALOG_REQUEST_CONTRACT_UNAVAILABLE",
                str(resolution.get("warning") or "No local request contract is available."),
            )
        )

    catalog_errors, catalog_warnings = validate_catalog_contract(
        locations,
        direct_names,
        contract,
    )
    errors.extend(catalog_errors)
    warnings.extend(catalog_warnings)

    sdk_summary: dict[str, Any] = {
        "available": False,
        "version": resolution.get("selected_version"),
        "schema_depth": schema_depth,
    }
    if resolution.get("resolved") and resolution.get("selected_version"):
        sdk_summary, sdk_errors, sdk_warnings = sdk_schema_evidence(
            service,
            str(resolution.get("base_operation") or operation.split("/", 1)[0]),
            str(resolution["selected_version"]),
            locations,
            sdk_result=sdk_result,
            sdk_root=sdk_root,
            schema_depth=schema_depth,
        )
        errors.extend(sdk_errors)
        warnings.extend(sdk_warnings)

    partial_evidence = any(item.get("code") in PARTIAL_EVIDENCE_CODES for item in warnings)
    success = not errors
    resolution_summary = dict(resolution)
    resolution_summary.pop("request_contract", None)
    return {
        "success": success,
        "mode": "local_request_preflight",
        "outcome_status": "succeeded" if success else "failed",
        "cloud_access": "none",
        "service": service,
        "operation": operation,
        "ready_for_dryrun": success,
        "submit_authorization_granted": False,
        "validation_status": "failed" if errors else "partial" if partial_evidence else "passed",
        "version_resolution": resolution_summary,
        "request_contract": contract,
        "sdk_schema": sdk_summary,
        "errors": errors,
        "warnings": warnings,
        "boundaries": [
            "This validates local request shape only; it does not authorize or execute a cloud mutation.",
            "Dry-run, regional product availability, quotas, prices, permissions, dependencies, and post-change readiness still require separate evidence.",
            "Unknown SDK fields are warnings because an installed SDK can lag the live API.",
        ],
    }


def file_error_result(
    service: str,
    operation: str,
    code: str,
    message: str,
    path: Path,
) -> dict[str, Any]:
    """Return a stable local file-validation failure."""

    return {
        "success": False,
        "mode": "local_request_preflight",
        "outcome_status": "failed",
        "cloud_access": "none",
        "service": service,
        "operation": operation,
        "json_input_file": str(path),
        "ready_for_dryrun": False,
        "submit_authorization_granted": False,
        "validation_status": "failed",
        "version_resolution": None,
        "request_contract": None,
        "sdk_schema": {"available": False},
        "errors": [issue(code, message, path=str(path))],
        "warnings": [],
    }


def preflight_request_file(
    service: str,
    operation: str,
    path: Path,
    *,
    direct_arguments: Iterable[str] = (),
    project_id: str | None = None,
    catalog: dict[str, Any] | None = None,
    sdk_result: dict[str, Any] | object = SDK_RESULT_AUTO,
    sdk_root: Path | None = None,
    schema_depth: int = 3,
) -> dict[str, Any]:
    """Load and validate one KooCLI cli-jsonInput file locally."""

    if path.suffix.lower() != ".json":
        return file_error_result(
            service,
            operation,
            "KOOCLI_JSON_EXTENSION_REQUIRED",
            "KooCLI cli-jsonInput requires a .json file.",
            path,
        )
    try:
        size = path.stat().st_size
    except OSError as exc:
        return file_error_result(
            service,
            operation,
            "KOOCLI_JSON_READ_FAILED",
            str(exc),
            path,
        )
    if size > MAX_KOOCLI_JSON_BYTES:
        return file_error_result(
            service,
            operation,
            "KOOCLI_JSON_TOO_LARGE",
            "KooCLI cli-jsonInput files must not exceed 5 MiB.",
            path,
        )
    try:
        payload = hcloud_common.load_json(path)
    except json.JSONDecodeError as exc:
        return file_error_result(
            service,
            operation,
            "KOOCLI_JSON_PARSE_FAILED",
            f"Invalid JSON: {exc}",
            path,
        )
    except OSError as exc:
        return file_error_result(
            service,
            operation,
            "KOOCLI_JSON_READ_FAILED",
            str(exc),
            path,
        )

    result = preflight_request(
        service,
        operation,
        payload,
        direct_arguments=direct_arguments,
        project_id=project_id,
        catalog=catalog,
        sdk_result=sdk_result,
        sdk_root=sdk_root,
        schema_depth=schema_depth,
    )
    result["json_input_file"] = str(path)
    result["json_input_bytes"] = size
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Huawei Cloud service name.")
    parser.add_argument("--operation", required=True, help="Huawei Cloud operation name, optionally with /vN.")
    parser.add_argument("--json-input-file", type=Path, required=True, help="KooCLI cli-jsonInput JSON file.")
    parser.add_argument("--project-id", help="Optional project_id supplied directly rather than in JSON.")
    parser.add_argument("--arg", action="append", default=[], help="Additional direct hcloud API argument token.")
    parser.add_argument("--sdk-root", type=Path, help="Optional Huawei Cloud SDK source tree fallback.")
    parser.add_argument("--schema-depth", type=int, default=3, help="Bounded SDK schema depth, from 0 to 5.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.schema_depth < 0 or args.schema_depth > 5:
        parser.error("--schema-depth must be between 0 and 5.")
    return args


def main() -> int:
    """Run local request preflight and print a structured result."""

    args = parse_args()
    result = preflight_request_file(
        args.service,
        args.operation,
        args.json_input_file,
        direct_arguments=args.arg,
        project_id=args.project_id,
        sdk_root=args.sdk_root,
        schema_depth=args.schema_depth,
    )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
