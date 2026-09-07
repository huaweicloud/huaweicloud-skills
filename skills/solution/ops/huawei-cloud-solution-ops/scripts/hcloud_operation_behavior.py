#!/usr/bin/env python3
"""Inspect portable batch and asynchronous behavior evidence for Huawei operations."""

from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common
import hcloud_dependency_evidence

PROFILE_PATH = hcloud_common.ROOT / "references" / "operation-behavior-profiles.json"
VERSION_SUFFIX = re.compile(r"/v[0-9][A-Za-z0-9._-]*$", re.IGNORECASE)


def load_profiles(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Load operation behavior profiles from the repository evidence file."""

    payload = hcloud_common.load_json(path)
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported operation behavior profile schema version.")
    if not isinstance(payload.get("operations"), dict):
        raise ValueError("Operation behavior profiles must contain an operations object.")
    return payload


def normalize_operation(service: str, operation: str) -> tuple[str, str]:
    """Return normalized service and unversioned operation names."""

    normalized_service = str(service or "").strip().upper()
    normalized_operation = VERSION_SUFFIX.sub("", str(operation or "").strip())
    prefix = f"{normalized_service}-"
    if normalized_operation.upper().startswith(prefix):
        normalized_operation = normalized_operation[len(prefix):]
    return normalized_service, normalized_operation


def find_operation_behavior(
    service: str,
    operation: str,
    *,
    profiles: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a copy of matching operation evidence, or ``None`` when unprofiled."""

    normalized_service, normalized_operation = normalize_operation(service, operation)
    source = profiles if profiles is not None else load_profiles()
    for profile in source.get("operations", {}).values():
        if not isinstance(profile, dict):
            continue
        profile_service, profile_operation = normalize_operation(
            str(profile.get("service") or ""),
            str(profile.get("operation") or ""),
        )
        if (
            profile_service == normalized_service
            and profile_operation.lower() == normalized_operation.lower()
        ):
            return copy.deepcopy(profile)
    return None


def service_profiles(
    service: str,
    profiles: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return sorted behavior profiles for one service."""

    normalized_service = str(service).strip().upper()
    matches = [
        copy.deepcopy(profile)
        for profile in profiles.get("operations", {}).values()
        if isinstance(profile, dict)
        and str(profile.get("service") or "").strip().upper() == normalized_service
    ]
    return sorted(matches, key=lambda item: str(item.get("operation") or "").lower())


def build_coverage_matrix(
    *,
    registry: dict[str, Any] | None = None,
    profiles: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
    dependency_profiles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a service matrix without cloud access or capability inflation."""

    registry_payload = registry if registry is not None else hcloud_common.load_registry()
    profile_payload = profiles if profiles is not None else load_profiles()
    catalog_payload = catalog if catalog is not None else hcloud_catalog.load_catalog()
    dependency_payload = (
        dependency_profiles
        if dependency_profiles is not None
        else hcloud_dependency_evidence.load_profiles()
    )
    rows: list[dict[str, Any]] = []
    for service, entry in sorted(registry_payload.get("services", {}).items()):
        operations = service_profiles(service, profile_payload)
        dependency_profiles_for_service = hcloud_dependency_evidence.service_profiles(
            service,
            dependency_payload,
        )
        catalog_service = hcloud_catalog.resolve_service(catalog_payload, service)
        profiled_names = [str(item["operation"]) for item in operations]
        batch_names = [
            str(item["operation"])
            for item in operations
            if item.get("cardinality") == "multi_resource"
        ]
        async_names = [
            str(item["operation"])
            for item in operations
            if (item.get("async_convergence") or {}).get("mode")
            not in (None, "none")
        ]
        metadata_backed = [
            str(item["operation"])
            for item in operations
            if item.get("support_level") == "metadata_backed"
        ]
        rows.append(
            {
                "service": service,
                "coverage": entry.get("coverage"),
                "query_operation_count": len(entry.get("query_operations", [])),
                "resource_query_operation_count": len(
                    entry.get("resource_query_operations", [])
                ),
                "curated_change_operation_count": len(entry.get("change_operations", [])),
                "generic_metadata_backed_available": catalog_service is not None,
                "metadata_catalog_operation_count": len(
                    (catalog_service or {}).get("operations", {})
                ),
                "planner": entry.get("planner"),
                "job_verifier": entry.get("job_verifier"),
                "resource_verifier": entry.get("resource_verifier"),
                "profiled_operations": profiled_names,
                "profiled_batch_operations": batch_names,
                "profiled_async_operations": async_names,
                "metadata_backed_profile_operations": metadata_backed,
                "has_operation_async_profile": bool(async_names),
                "dependency_profile_count": len(dependency_profiles_for_service),
                "dependency_profiled_operations": sorted(
                    {
                        operation
                        for profile in dependency_profiles_for_service
                        for operation in profile.get("applies_to_operations", [])
                    }
                ),
                "has_structured_dependency_evidence": bool(
                    dependency_profiles_for_service
                ),
            }
        )
    profiled_operations = profile_payload.get("operations", {})
    return {
        "success": True,
        "mode": "coverage_matrix",
        "schema_version": 1,
        "summary": {
            "service_count": len(rows),
            "profiled_operation_count": len(profiled_operations),
            "profiled_service_count": len(
                {str(item.get("service")) for item in profiled_operations.values()}
            ),
            "registry_service_with_metadata_count": sum(
                1 for row in rows if row["generic_metadata_backed_available"]
            ),
            "dependency_profile_count": len(
                dependency_payload.get("profiles", {})
            ),
            "dependency_profiled_service_count": len(
                {
                    str(item.get("service"))
                    for item in dependency_payload.get("profiles", {}).values()
                }
            ),
            "public_polling_framework_present": False,
        },
        "services": rows,
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    """Render a compact human-readable coverage table."""

    lines = [
        "| Service | Coverage | Query | Curated change | Metadata operations | Batch profiles | Async profiles | Dependency profiles | Verification |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for row in matrix.get("services", []):
        verification = "/".join(
            value
            for value in (row.get("job_verifier"), row.get("resource_verifier"))
            if value
        ) or "-"
        lines.append(
            "| {service} | {coverage} | {query_count} | {change_count} | {metadata_count} | {batch} | {async_ops} | {dependencies} | {verification} |".format(
                service=row["service"],
                coverage=row.get("coverage") or "-",
                query_count=(
                    int(row.get("query_operation_count") or 0)
                    + int(row.get("resource_query_operation_count") or 0)
                ),
                change_count=int(row.get("curated_change_operation_count") or 0),
                metadata_count=int(row.get("metadata_catalog_operation_count") or 0),
                batch=", ".join(row.get("profiled_batch_operations", [])) or "-",
                async_ops=", ".join(row.get("profiled_async_operations", [])) or "-",
                dependencies=int(row.get("dependency_profile_count") or 0),
                verification=verification,
            )
        )
    return "\n".join(lines)


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """Return operation evidence, service evidence, or the full coverage matrix."""

    profiles = load_profiles(args.profile_path)
    if args.operation:
        behavior = find_operation_behavior(args.service, args.operation, profiles=profiles)
        return {
            "success": behavior is not None,
            "mode": "operation_behavior",
            "service": args.service.upper(),
            "operation": args.operation,
            "operation_behavior": behavior,
            "error": None
            if behavior
            else "No operation-specific behavior profile is registered.",
        }
    if args.service:
        operations = service_profiles(args.service, profiles)
        return {
            "success": True,
            "mode": "service_behavior",
            "service": args.service.upper(),
            "operation_count": len(operations),
            "operations": operations,
        }
    return build_coverage_matrix(profiles=profiles)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for local evidence inspection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", help="Huawei Cloud service, for example ECS or EIP.")
    parser.add_argument("--operation", help="Optional operation name; requires --service.")
    parser.add_argument(
        "--profile-path",
        type=Path,
        default=PROFILE_PATH,
        help="Optional operation behavior profile file.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output JSON evidence or the full coverage matrix as Markdown.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.operation and not args.service:
        parser.error("--operation requires --service.")
    if args.format == "markdown" and (args.service or args.operation):
        parser.error("--format=markdown is only available for the full coverage matrix.")
    return args


def main() -> int:
    """Inspect local behavior evidence and print a stable result."""

    args = parse_args()
    try:
        result = build_result(args)
    except (OSError, ValueError) as exc:
        result = {"success": False, "mode": "inspect", "error": str(exc)}
    if args.format == "markdown" and result.get("success"):
        print(render_markdown(result))
    else:
        hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
