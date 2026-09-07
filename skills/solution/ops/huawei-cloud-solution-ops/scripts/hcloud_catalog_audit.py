#!/usr/bin/env python3
"""Audit generated hcloud catalog coverage against the curated service registry."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common

REGISTRY_PATH = hcloud_common.REGISTRY_PATH
SPECIAL_RUNNER_SERVICES = {"OBS"}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Return the curated service registry."""
    return hcloud_common.load_registry(path)


def registered_operations(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """Return all registry operation names with their operation group."""
    result: list[tuple[str, str]] = []
    for group in ("query_operations", "resource_query_operations", "change_operations"):
        for operation in entry.get(group, []):
            result.append((group, str(operation)))
    return result


def registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    """Return stable registry coverage counts for docs and release notes."""
    services = registry.get("services", {})
    summary: dict[str, Any] = {
        "service_count": len(services),
        "query_operation_count": 0,
        "resource_query_operation_count": 0,
        "change_operation_count": 0,
    }
    for entry in services.values():
        summary["query_operation_count"] += len(entry.get("query_operations", []))
        summary["resource_query_operation_count"] += len(entry.get("resource_query_operations", []))
        summary["change_operation_count"] += len(entry.get("change_operations", []))
    summary["registered_operation_count"] = (
        summary["query_operation_count"]
        + summary["resource_query_operation_count"]
        + summary["change_operation_count"]
    )
    return summary


def audit(catalog_path: Path = hcloud_catalog.CATALOG_PATH, registry_path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Build a catalog-vs-registry audit report."""
    catalog = hcloud_catalog.load_catalog(catalog_path)
    registry = load_registry(registry_path)
    registry_counts = registry_summary(registry)
    service_findings = []
    missing_operations: dict[str, list[str]] = {}
    missing_services: list[str] = []
    registry_tokens = {hcloud_catalog.normalize_token(service) for service in registry.get("services", {})}

    for service_name, entry in sorted(registry.get("services", {}).items()):
        if service_name in SPECIAL_RUNNER_SERVICES:
            service_findings.append(
                {
                    "service": service_name,
                    "status": "special_runner",
                    "reason": "Service uses a dedicated non-OpenAPI runner and is intentionally absent from the catalog.",
                }
            )
            continue
        service = hcloud_catalog.resolve_service(catalog, service_name)
        if service is None:
            missing_services.append(service_name)
            service_findings.append({"service": service_name, "status": "missing_service"})
            continue
        service_missing = []
        for group, operation_name in registered_operations(entry):
            if hcloud_catalog.resolve_operation(service, operation_name) is None:
                service_missing.append(f"{group}:{operation_name}")
        if service_missing:
            missing_operations[service_name] = service_missing
        service_findings.append(
            {
                "service": service_name,
                "status": "drift" if service_missing else "ok",
                "catalog_name": service.get("name"),
                "catalog_operation_count": service.get("operation_count"),
                "missing_operations": service_missing,
            }
        )

    metadata_backed = [
        service
        for service in catalog.get("services", {}).values()
        if hcloud_catalog.normalize_token(str(service.get("name") or service.get("template_dir") or "")) not in registry_tokens
    ]
    metadata_backed.sort(key=lambda item: str(item.get("name", "")).lower())
    metadata_backed_services = [
        {
            "name": service.get("name"),
            "category": service.get("category"),
            "template_dir": service.get("template_dir"),
            "operation_count": service.get("operation_count"),
        }
        for service in metadata_backed
    ]
    result = {
        "success": not missing_services and not missing_operations,
        "catalog": {
            "service_count": catalog.get("source", {}).get("service_count", len(catalog.get("services", {}))),
            "operation_count": catalog.get("source", {}).get("operation_count"),
            "source": catalog.get("source", {}),
        },
        "registry": registry_counts,
        "metadata_backed": {
            "service_count": len(metadata_backed),
            "services": metadata_backed_services,
        },
        "registry_service_count": registry_counts["service_count"],
        "metadata_backed_service_count": len(metadata_backed),
        "metadata_backed_services": metadata_backed_services,
        "missing_services": missing_services,
        "missing_operations": missing_operations,
        "service_findings": service_findings,
    }
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(hcloud_catalog.CATALOG_PATH), help="Generated catalog path.")
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="Service registry path.")
    parser.add_argument("--fail-on-drift", action="store_true", help="Exit non-zero when registry drift is found.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Run the catalog audit."""
    args = parse_args()
    result = audit(Path(args.catalog), Path(args.registry))
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 1 if args.fail_on_drift and not result["success"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
