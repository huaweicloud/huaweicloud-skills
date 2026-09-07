#!/usr/bin/env python3
"""Suggest metadata-backed services for the next read-only live smoke batch."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common

DEFAULT_QUESTIONS_DIR: Path | None = None


def split_api_reference(raw_api: str, default_service: str) -> tuple[str, str]:
    """Split a generated question API reference into service and operation."""
    value = str(raw_api).strip()
    if "." in value:
        service, operation = value.split(".", 1)
        return service.upper(), operation
    if "-" in value:
        service, operation = value.split("-", 1)
        return service.upper(), operation
    return default_service.upper(), value


def iter_question_files(questions_dir: Path) -> list[Path]:
    """Return generated question JSON files when the dataset is available."""
    files: list[Path] = []
    for subset in ("read_type", "crud"):
        subset_dir = questions_dir / subset
        if subset_dir.exists():
            files.extend(sorted(subset_dir.glob("*.json")))
    return files


def collect_question_frequency(questions_dir: Path | None) -> dict[str, Any]:
    """Return per-service and per-operation reference counts from question files."""
    service_counts: collections.Counter[str] = collections.Counter()
    operation_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    errors: list[dict[str, str]] = []
    files = iter_question_files(questions_dir) if questions_dir else []
    if not files:
        return {
            "available": False,
            "questions_dir": str(questions_dir) if questions_dir else None,
            "files_checked": 0,
            "service_counts": {},
            "operation_counts": {},
            "errors": [],
        }

    for path in files:
        default_service = path.stem.split("_", 1)[0]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append({"file": str(path), "error": str(exc)})
            continue
        if not isinstance(data, list):
            errors.append({"file": str(path), "error": "Top-level JSON value must be a list."})
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            apis = item.get("relevant_apis")
            if not isinstance(apis, list):
                continue
            for api in apis:
                service, operation = split_api_reference(str(api), default_service)
                service_counts[service] += 1
                operation_counts[service][operation] += 1
    return {
        "available": True,
        "questions_dir": str(questions_dir),
        "files_checked": len(files),
        "service_counts": dict(sorted(service_counts.items())),
        "operation_counts": {service: dict(counter) for service, counter in sorted(operation_counts.items())},
        "errors": errors,
    }


def registry_tokens(registry: dict[str, Any]) -> set[str]:
    """Return normalized curated service names from the registry."""
    return {hcloud_catalog.normalize_token(service) for service in registry.get("services", {})}


def confidence_service(confidence: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Return a confidence service entry using exact or normalized matching."""
    services = confidence.get("services", {})
    if not isinstance(services, dict):
        return {}
    direct = services.get(service_name) or services.get(service_name.upper())
    if isinstance(direct, dict):
        return direct
    target = hcloud_catalog.normalize_token(service_name)
    for name, entry in services.items():
        if hcloud_catalog.normalize_token(str(name)) == target and isinstance(entry, dict):
            return entry
    return {}


def operation_confidence(confidence: dict[str, Any], service_name: str, operation_name: str) -> dict[str, Any]:
    """Return operation-level confidence metadata for a service operation."""
    service = confidence_service(confidence, service_name)
    operations = service.get("operations", {})
    if not isinstance(operations, dict):
        return {}
    direct = operations.get(operation_name)
    if isinstance(direct, dict):
        return direct
    target = hcloud_catalog.normalize_token(operation_name)
    for name, entry in operations.items():
        if hcloud_catalog.normalize_token(str(name)) == target and isinstance(entry, dict):
            return entry
    return {}


def operation_record(operation: dict[str, Any], confidence: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Return a compact candidate operation record."""
    operation_name = str(operation.get("name") or "")
    op_confidence = operation_confidence(confidence, service_name, operation_name)
    return {
        "operation": operation_name,
        "summary": operation.get("summary"),
        "action": operation.get("action"),
        "supports_limit": bool(operation.get("supports_limit")),
        "required_headers": hcloud_catalog.required_header_param_names(operation),
        "confidence": op_confidence.get("confidence", "catalog-derived"),
        "unsupported_optional_args": op_confidence.get("unsupported_optional_args", []),
    }


def select_candidates(
    catalog_path: Path = hcloud_catalog.CATALOG_PATH,
    registry_path: Path = hcloud_common.REGISTRY_PATH,
    confidence_path: Path = hcloud_catalog.CONFIDENCE_PATH,
    questions_dir: Path | None = DEFAULT_QUESTIONS_DIR,
    limit: int = 12,
    operations_per_service: int = 2,
    include_curated: bool = False,
    include_live_smoked: bool = False,
    services: list[str] | None = None,
) -> dict[str, Any]:
    """Select metadata-backed services that are useful for future live smoke."""
    catalog = hcloud_catalog.load_catalog(catalog_path)
    registry = hcloud_common.load_registry(registry_path)
    confidence = hcloud_catalog.load_confidence(confidence_path)
    frequencies = collect_question_frequency(questions_dir)
    curated_tokens = registry_tokens(registry)
    service_filter = {hcloud_catalog.normalize_token(service) for service in services or []}
    candidates = []

    for key, service in hcloud_catalog.iter_services(catalog, expand=True):
        if not isinstance(service, dict):
            continue
        service_name = str(service.get("name") or key)
        service_token = hcloud_catalog.normalize_token(service_name)
        if service_filter and service_token not in service_filter:
            continue
        if not include_curated and service_token in curated_tokens:
            continue

        discovery_ops = hcloud_catalog.discovery_operations(service, max(operations_per_service * 4, operations_per_service))
        if not discovery_ops:
            continue
        live_smoked_count = 0
        suggested_ops = []
        for operation in discovery_ops:
            op_confidence = operation_confidence(confidence, service_name, str(operation.get("name") or ""))
            if op_confidence.get("confidence") == "live-read-smoked":
                live_smoked_count += 1
                if not include_live_smoked:
                    continue
            suggested_ops.append(operation_record(operation, confidence, service_name))
            if len(suggested_ops) >= operations_per_service:
                break
        if not suggested_ops:
            continue

        service_count = int(frequencies["service_counts"].get(service_name.upper(), 0))
        operation_counter = frequencies["operation_counts"].get(service_name.upper(), {})
        candidates.append(
            {
                "service": service_name,
                "category": service.get("category"),
                "template_dir": service.get("template_dir"),
                "is_global": service.get("is_global"),
                "question_reference_count": service_count,
                "unique_question_operation_count": len(operation_counter),
                "catalog_operation_count": service.get("operation_count"),
                "discovery_operation_count": len(discovery_ops),
                "live_read_smoked_operation_count": live_smoked_count,
                "suggested_operations": suggested_ops,
                "reasons": [
                    "metadata-backed",
                    "has-read-only-discovery-operation",
                    "not-curated-registry" if service_token not in curated_tokens else "curated-registry-included",
                ],
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item["question_reference_count"]),
            -int(item["unique_question_operation_count"]),
            -int(item["discovery_operation_count"]),
            str(item["service"]).lower(),
        )
    )
    selected = candidates[:limit]
    return {
        "success": True,
        "catalog": {
            "service_count": catalog.get("source", {}).get("service_count", len(catalog.get("services", {}))),
            "operation_count": catalog.get("source", {}).get("operation_count"),
        },
        "questions": {
            "available": frequencies["available"],
            "questions_dir": frequencies["questions_dir"],
            "files_checked": frequencies["files_checked"],
            "errors": frequencies["errors"],
        },
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "candidates": selected,
        "selection": {
            "limit": limit,
            "operations_per_service": operations_per_service,
            "include_curated": include_curated,
            "include_live_smoked": include_live_smoked,
            "service_filter": services or [],
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(hcloud_catalog.CATALOG_PATH), help="Generated catalog path.")
    parser.add_argument("--registry", default=str(hcloud_common.REGISTRY_PATH), help="Service registry path.")
    parser.add_argument("--confidence", default=str(hcloud_catalog.CONFIDENCE_PATH), help="Confidence sidecar path.")
    parser.add_argument(
        "--questions-dir",
        help="Explicit generated questions directory used as an optional maintenance ranking signal.",
    )
    parser.add_argument("--limit", type=int, default=12, help="Maximum services to return.")
    parser.add_argument("--operations-per-service", type=int, default=2, help="Suggested read-only operations per service.")
    parser.add_argument("--service", action="append", help="Restrict candidates to specific services. Can be repeated.")
    parser.add_argument("--include-curated", action="store_true", help="Include curated registry services.")
    parser.add_argument("--include-live-smoked", action="store_true", help="Include already live-read-smoked operations.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.operations_per_service < 1:
        parser.error("--operations-per-service must be greater than 0.")
    return args


def main() -> int:
    """Print live smoke service candidates."""
    args = parse_args()
    result = select_candidates(
        catalog_path=Path(args.catalog),
        registry_path=Path(args.registry),
        confidence_path=Path(args.confidence),
        questions_dir=Path(args.questions_dir) if args.questions_dir else None,
        limit=args.limit,
        operations_per_service=args.operations_per_service,
        include_curated=args.include_curated,
        include_live_smoked=args.include_live_smoked,
        services=args.service,
    )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
