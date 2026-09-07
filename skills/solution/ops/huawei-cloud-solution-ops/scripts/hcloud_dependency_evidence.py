#!/usr/bin/env python3
"""Inspect local Huawei Cloud resource dependency evidence without execution."""

from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common

PROFILE_PATH = hcloud_common.ROOT / "references" / "resource-dependency-profiles.json"
VERSION_SUFFIX = re.compile(r"/v[0-9][A-Za-z0-9._-]*$", re.IGNORECASE)


def load_profiles(path: Path = PROFILE_PATH) -> dict[str, Any]:
    """Load and minimally validate the versioned dependency evidence file."""

    payload = hcloud_common.load_json(path)
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported resource dependency profile schema version.")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("Resource dependency profiles must contain a profiles object.")
    return payload


def normalize_operation(service: str, operation: str) -> tuple[str, str]:
    """Return normalized service and unversioned operation names."""

    normalized_service = str(service or "").strip().upper()
    normalized_operation = VERSION_SUFFIX.sub("", str(operation or "").strip())
    prefix = f"{normalized_service}-"
    if normalized_operation.upper().startswith(prefix):
        normalized_operation = normalized_operation[len(prefix):]
    return normalized_service, normalized_operation


def find_dependency_evidence(
    service: str,
    operation: str,
    *,
    profiles: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a copy of matching dependency evidence, or ``None``."""

    normalized_service, normalized_operation = normalize_operation(service, operation)
    payload = profiles if profiles is not None else load_profiles()
    for profile in payload.get("profiles", {}).values():
        if not isinstance(profile, dict):
            continue
        if str(profile.get("service") or "").strip().upper() != normalized_service:
            continue
        operations = {
            normalize_operation(normalized_service, item)[1].lower()
            for item in profile.get("applies_to_operations", [])
        }
        if normalized_operation.lower() in operations:
            return copy.deepcopy(profile)
    return None


def service_profiles(
    service: str,
    profiles: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return sorted dependency profiles for one service."""

    normalized_service = str(service or "").strip().upper()
    matches = [
        copy.deepcopy(profile)
        for profile in profiles.get("profiles", {}).values()
        if isinstance(profile, dict)
        and str(profile.get("service") or "").strip().upper() == normalized_service
    ]
    return sorted(matches, key=lambda item: str(item.get("id") or ""))


def build_coverage_matrix(
    *,
    registry: dict[str, Any] | None = None,
    profiles: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a local dependency coverage matrix without cloud access."""

    registry_payload = registry if registry is not None else hcloud_common.load_registry()
    profile_payload = profiles if profiles is not None else load_profiles()
    catalog_payload = catalog if catalog is not None else hcloud_catalog.load_catalog()
    rows: list[dict[str, Any]] = []
    for service, entry in sorted(registry_payload.get("services", {}).items()):
        matches = service_profiles(service, profile_payload)
        catalog_service = hcloud_catalog.resolve_service(catalog_payload, service)
        operations = sorted(
            {
                operation
                for profile in matches
                for operation in profile.get("applies_to_operations", [])
            }
        )
        rows.append(
            {
                "service": service,
                "coverage": entry.get("coverage"),
                "metadata_catalog_operation_count": len(
                    (catalog_service or {}).get("operations", {})
                ),
                "profile_count": len(matches),
                "profiled_operations": operations,
                "resource_kinds": sorted(
                    {str(profile.get("resource_kind") or "") for profile in matches}
                ),
                "blocker_count": sum(len(profile.get("blockers", [])) for profile in matches),
                "prerequisite_count": sum(
                    len(profile.get("prerequisites", [])) for profile in matches
                ),
                "related_resource_count": sum(
                    len(profile.get("related_resources", [])) for profile in matches
                ),
            }
        )
    profile_values = list(profile_payload.get("profiles", {}).values())
    return {
        "success": True,
        "mode": "dependency_coverage_matrix",
        "schema_version": 1,
        "summary": {
            "profile_count": len(profile_values),
            "profiled_service_count": len(
                {str(profile.get("service")) for profile in profile_values}
            ),
            "workflow_engine_present": False,
            "cloud_access_performed": False,
            "execution_performed": False,
        },
        "services": rows,
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    """Render a compact dependency coverage table."""

    lines = [
        "| Service | Coverage | Profiles | Operations | Prerequisites | Blockers | Related |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in matrix.get("services", []):
        lines.append(
            "| {service} | {coverage} | {profiles} | {operations} | {prerequisites} | {blockers} | {related} |".format(
                service=row["service"],
                coverage=row.get("coverage") or "-",
                profiles=row.get("profile_count", 0),
                operations=", ".join(row.get("profiled_operations", [])) or "-",
                prerequisites=row.get("prerequisite_count", 0),
                blockers=row.get("blocker_count", 0),
                related=row.get("related_resource_count", 0),
            )
        )
    return "\n".join(lines)


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """Return operation, service, or full dependency evidence."""

    profiles = load_profiles(args.profile_path)
    if args.operation:
        evidence = find_dependency_evidence(
            args.service,
            args.operation,
            profiles=profiles,
        )
        return {
            "success": evidence is not None,
            "mode": "dependency_evidence",
            "service": args.service.upper(),
            "operation": args.operation,
            "dependency_evidence": evidence,
            "error": None
            if evidence
            else "No operation-specific dependency profile is registered.",
        }
    if args.service:
        matches = service_profiles(args.service, profiles)
        return {
            "success": True,
            "mode": "service_dependency_evidence",
            "service": args.service.upper(),
            "profile_count": len(matches),
            "profiles": matches,
        }
    return build_coverage_matrix(profiles=profiles)


def parse_args() -> argparse.Namespace:
    """Parse local dependency inspector arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", help="Huawei Cloud service, for example ELB.")
    parser.add_argument("--operation", help="Optional operation; requires --service.")
    parser.add_argument(
        "--profile-path",
        type=Path,
        default=PROFILE_PATH,
        help="Optional dependency profile file.",
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
    """Inspect local dependency evidence and print a stable result."""

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
