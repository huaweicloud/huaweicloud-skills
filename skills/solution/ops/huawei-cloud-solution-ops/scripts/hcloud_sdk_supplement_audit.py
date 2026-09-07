#!/usr/bin/env python3
"""Audit the curated SDK read-only convenience-runner registry."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_sdk_catalog

REGISTRY_PATH = hcloud_common.REFERENCES_DIR / "sdk-supplement-registry.json"
ALLOWED_VALUES = {
    "request_types",
    "query_params",
    "path_params",
    "body_params",
    "sensitive_fields",
    "region_endpoint",
    "error_structure",
    "stable_readonly_query",
    "pagination",
}
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_STATUSES = {"candidate", "curated", "deprecated"}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the curated SDK runner registry JSON."""
    if not path.exists():
        return {"schema_version": 1, "operations": []}
    return hcloud_common.load_json(path)


def operation_key(entry: dict[str, Any]) -> str:
    """Return the stable service:operation key for a registry entry."""
    return f"{str(entry.get('service') or '').upper()}:{entry.get('sdk_operation') or ''}"


def registry_allowlist(path: Path = REGISTRY_PATH, execute_only: bool = True) -> dict[tuple[str, str], dict[str, Any]]:
    """Return registry entries keyed by (SERVICE, sdk_operation)."""
    registry = load_registry(path)
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in registry.get("operations", []):
        if not isinstance(entry, dict):
            continue
        if execute_only and not entry.get("execute_allowed"):
            continue
        service = str(entry.get("service") or "").upper()
        operation = str(entry.get("sdk_operation") or "")
        if service and operation:
            result[(service, operation)] = entry
    return result


def registry_entries_by_hcloud_operation(path: Path = REGISTRY_PATH) -> dict[tuple[str, str], dict[str, Any]]:
    """Return registry entries keyed by (SERVICE, hcloud_operation)."""
    registry = load_registry(path)
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in registry.get("operations", []):
        if not isinstance(entry, dict):
            continue
        service = str(entry.get("service") or "").upper()
        operation = str(entry.get("hcloud_operation") or "")
        if service and operation and entry.get("status") != "deprecated":
            result[(service, operation)] = entry
    return result


def registry_entry_for_hcloud_operation(service: str, operation: str, path: Path = REGISTRY_PATH) -> dict[str, Any] | None:
    """Return the SDK supplement entry for a hcloud operation when curated."""
    return registry_entries_by_hcloud_operation(path).get((service.upper(), operation))


def validate_entry_shape(entry: dict[str, Any], index: int, root: Path) -> list[dict[str, Any]]:
    """Return structural validation findings for one registry entry."""
    findings: list[dict[str, Any]] = []
    key = operation_key(entry) or f"entry-{index}"
    required_fields = [
        "service",
        "sdk_operation",
        "hcloud_operation",
        "requires_sdk_package",
        "purpose",
        "value",
        "risk",
        "read_only_required",
        "execute_allowed",
        "fallback",
        "evidence",
        "status",
    ]
    for field in required_fields:
        if field not in entry:
            findings.append({"level": "error", "entry": key, "field": field, "message": "Missing required field."})

    service = str(entry.get("service") or "")
    if service and service != service.upper():
        findings.append({"level": "error", "entry": key, "field": "service", "message": "Service must be uppercase."})

    package = str(entry.get("requires_sdk_package") or "")
    if package and not package.startswith("huaweicloudsdk"):
        findings.append({"level": "error", "entry": key, "field": "requires_sdk_package", "message": "SDK package must start with huaweicloudsdk."})

    values = entry.get("value")
    if not isinstance(values, list) or not values:
        findings.append({"level": "error", "entry": key, "field": "value", "message": "Value must be a non-empty list."})
    else:
        unknown = [item for item in values if item not in ALLOWED_VALUES]
        if unknown:
            findings.append({"level": "error", "entry": key, "field": "value", "message": f"Unknown value tags: {unknown}"})

    risk = entry.get("risk")
    if risk not in ALLOWED_RISKS:
        findings.append({"level": "error", "entry": key, "field": "risk", "message": f"Risk must be one of {sorted(ALLOWED_RISKS)}."})

    status = entry.get("status")
    if status not in ALLOWED_STATUSES:
        findings.append({"level": "error", "entry": key, "field": "status", "message": f"Status must be one of {sorted(ALLOWED_STATUSES)}."})

    fallback = entry.get("fallback")
    if not isinstance(fallback, dict):
        findings.append({"level": "error", "entry": key, "field": "fallback", "message": "Fallback must be an object."})
    else:
        runner = fallback.get("runner")
        if not runner:
            findings.append({"level": "error", "entry": key, "field": "fallback.runner", "message": "Fallback runner is required."})
        elif not (root / str(runner)).exists():
            findings.append({"level": "error", "entry": key, "field": "fallback.runner", "message": f"Fallback runner does not exist: {runner}"})
        if fallback.get("operation") != entry.get("hcloud_operation"):
            findings.append(
                {
                    "level": "error",
                    "entry": key,
                    "field": "fallback.operation",
                    "message": "Fallback operation must match hcloud_operation.",
                }
            )

    if entry.get("execute_allowed"):
        if entry.get("read_only_required") is not True:
            findings.append({"level": "error", "entry": key, "field": "read_only_required", "message": "Executable SDK supplements must require read-only metadata."})
        if risk != "low":
            findings.append({"level": "error", "entry": key, "field": "risk", "message": "Executable SDK supplements must be low risk."})
        if "unit-test" not in (entry.get("evidence") or []):
            findings.append({"level": "error", "entry": key, "field": "evidence", "message": "Executable SDK supplements require unit-test evidence."})

    return findings


def validate_metadata(entry: dict[str, Any], sdk_root: Path | None, require_metadata: bool) -> list[dict[str, Any]]:
    """Validate registry entry against installed/source SDK metadata when available."""
    key = operation_key(entry)
    result = hcloud_sdk_catalog.inspect_sdk(
        sdk_root,
        service=str(entry.get("service") or ""),
        operation=str(entry.get("sdk_operation") or ""),
        max_regions=3,
    )
    if not result.get("success"):
        level = "error" if require_metadata else "warning"
        return [{"level": level, "entry": key, "field": "sdk_metadata", "message": result.get("error", "SDK metadata unavailable.")}]

    findings: list[dict[str, Any]] = []
    matched_operations = [
        version.get("operation")
        for package in result.get("packages", [])
        for version in package.get("versions", [])
        if version.get("operation")
    ]
    if not matched_operations:
        level = "error" if require_metadata else "warning"
        return [{"level": level, "entry": key, "field": "sdk_operation", "message": "SDK operation metadata not found."}]

    operation = matched_operations[0]
    if entry.get("read_only_required") and operation.get("read_only") is not True:
        findings.append({"level": "error", "entry": key, "field": "read_only_required", "message": "SDK metadata marks this operation as mutating."})

    expected_package = entry.get("requires_sdk_package")
    packages = {package.get("package") for package in result.get("packages", [])}
    if expected_package and expected_package not in packages:
        findings.append(
            {
                "level": "error",
                "entry": key,
                "field": "requires_sdk_package",
                "message": f"Expected package {expected_package} not found in SDK metadata packages {sorted(packages)}.",
            }
        )
    return findings


def audit_registry(path: Path = REGISTRY_PATH, sdk_root: Path | None = hcloud_sdk_catalog.DEFAULT_SDK_ROOT, require_metadata: bool = False) -> dict[str, Any]:
    """Audit the curated SDK runner registry and return structured findings."""
    registry = load_registry(path)
    findings: list[dict[str, Any]] = []
    operations = registry.get("operations", [])
    if not isinstance(operations, list):
        findings.append({"level": "error", "entry": "registry", "field": "operations", "message": "Operations must be a list."})
        operations = []

    seen: set[str] = set()
    for index, entry in enumerate(operations):
        if not isinstance(entry, dict):
            findings.append({"level": "error", "entry": f"entry-{index}", "message": "Operation entry must be an object."})
            continue
        key = operation_key(entry)
        if key in seen:
            findings.append({"level": "error", "entry": key, "message": "Duplicate SDK supplement entry."})
        seen.add(key)
        findings.extend(validate_entry_shape(entry, index, hcloud_common.ROOT))
        findings.extend(validate_metadata(entry, sdk_root, require_metadata))

    error_count = sum(1 for item in findings if item.get("level") == "error")
    warning_count = sum(1 for item in findings if item.get("level") == "warning")
    return {
        "success": error_count == 0,
        "registry": str(path),
        "schema_version": registry.get("schema_version"),
        "operation_count": len(operations),
        "execute_allowed_count": sum(1 for entry in operations if isinstance(entry, dict) and entry.get("execute_allowed")),
        "error_count": error_count,
        "warning_count": warning_count,
        "findings": findings,
        "boundaries": registry.get("boundaries", {}),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Path to sdk-supplement-registry.json.")
    parser.add_argument(
        "--sdk-root",
        type=Path,
        default=hcloud_sdk_catalog.DEFAULT_SDK_ROOT,
        help="Explicit SDK source fallback for maintenance metadata validation after installed packages.",
    )
    parser.add_argument("--require-metadata", action="store_true", help="Fail when SDK metadata is unavailable.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Audit the curated SDK runner registry."""
    args = parse_args()
    result = audit_registry(args.registry, sdk_root=args.sdk_root, require_metadata=args.require_metadata)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
