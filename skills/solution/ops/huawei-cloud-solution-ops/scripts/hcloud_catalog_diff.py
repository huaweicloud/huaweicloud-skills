#!/usr/bin/env python3
"""Compare two generated hcloud catalogs or two catalog fingerprints."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common


def load_document(path: Path) -> dict[str, Any]:
    """Load a catalog or fingerprint JSON document."""
    return hcloud_common.load_json(path)


def document_kind(payload: dict[str, Any]) -> str:
    """Return whether a document is a full catalog or a compact fingerprint."""
    services = payload.get("services", {})
    sample = next((value for value in services.values() if isinstance(value, dict)), {})
    if "catalog_hash" in payload or "operations_hash" in sample:
        return "fingerprint"
    if payload.get("split") is True or "service_file" in sample:
        return "catalog_index"
    return "catalog"


def service_name(key: str, entry: dict[str, Any]) -> str:
    """Return a stable service display name for diff output."""
    return str(entry.get("name") or key)


def full_catalog_services(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return comparable service summaries from a full generated catalog."""
    services: dict[str, dict[str, Any]] = {}
    for key, entry in payload.get("services", {}).items():
        if not isinstance(entry, dict):
            continue
        operations = entry.get("operations", {}) if isinstance(entry.get("operations"), dict) else {}
        operation_names = sorted(str(name) for name in operations)
        required_by_operation = {}
        for operation_name in operation_names:
            operation = operations.get(operation_name)
            if not isinstance(operation, dict):
                continue
            required_by_operation[operation_name] = sorted(hcloud_catalog.required_param_names(operation))
        token = hcloud_catalog.normalize_token(service_name(str(key), entry))
        services[token] = {
            "key": str(key),
            "name": service_name(str(key), entry),
            "category": entry.get("category"),
            "operation_count": len(operation_names),
            "operations": operation_names,
            "required_params_by_operation": required_by_operation,
        }
    return services


def fingerprint_services(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return comparable service summaries from a compact fingerprint."""
    services: dict[str, dict[str, Any]] = {}
    for key, entry in payload.get("services", {}).items():
        if not isinstance(entry, dict):
            continue
        token = hcloud_catalog.normalize_token(service_name(str(key), entry))
        services[token] = {
            "key": str(key),
            "name": service_name(str(key), entry),
            "operation_count": entry.get("operation_count"),
            "operations_hash": entry.get("operations_hash"),
            "required_params_hash": entry.get("required_params_hash"),
        }
    return services


def service_record(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a compact service record for added/removed service lists."""
    record = {
        "name": entry.get("name"),
        "key": entry.get("key"),
        "operation_count": entry.get("operation_count"),
    }
    if entry.get("category"):
        record["category"] = entry.get("category")
    return record


def compare_full_catalogs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compare two full generated catalogs."""
    old_services = full_catalog_services(old)
    new_services = full_catalog_services(new)
    old_tokens = set(old_services)
    new_tokens = set(new_services)
    added_services = [service_record(new_services[token]) for token in sorted(new_tokens - old_tokens)]
    removed_services = [service_record(old_services[token]) for token in sorted(old_tokens - new_tokens)]
    changed_services = []

    for token in sorted(old_tokens & new_tokens):
        old_entry = old_services[token]
        new_entry = new_services[token]
        old_ops = set(old_entry["operations"])
        new_ops = set(new_entry["operations"])
        added_operations = sorted(new_ops - old_ops)
        removed_operations = sorted(old_ops - new_ops)
        required_param_changes = []
        for operation in sorted(old_ops & new_ops):
            old_params = old_entry["required_params_by_operation"].get(operation, [])
            new_params = new_entry["required_params_by_operation"].get(operation, [])
            if old_params != new_params:
                required_param_changes.append(
                    {
                        "operation": operation,
                        "old_required_params": old_params,
                        "new_required_params": new_params,
                    }
                )
        if added_operations or removed_operations or required_param_changes:
            changed_services.append(
                {
                    "name": new_entry["name"],
                    "key": new_entry["key"],
                    "old_operation_count": old_entry["operation_count"],
                    "new_operation_count": new_entry["operation_count"],
                    "added_operations": added_operations,
                    "removed_operations": removed_operations,
                    "required_param_changes": required_param_changes,
                }
            )

    return {
        "comparison_kind": "catalog",
        "added_services": added_services,
        "removed_services": removed_services,
        "changed_services": changed_services,
    }


def compare_fingerprints(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compare two compact catalog fingerprints."""
    old_services = fingerprint_services(old)
    new_services = fingerprint_services(new)
    old_tokens = set(old_services)
    new_tokens = set(new_services)
    added_services = [service_record(new_services[token]) for token in sorted(new_tokens - old_tokens)]
    removed_services = [service_record(old_services[token]) for token in sorted(old_tokens - new_tokens)]
    changed_services = []

    for token in sorted(old_tokens & new_tokens):
        old_entry = old_services[token]
        new_entry = new_services[token]
        hash_fields = ("operation_count", "operations_hash", "required_params_hash")
        changes = {
            field: {"old": old_entry.get(field), "new": new_entry.get(field)}
            for field in hash_fields
            if old_entry.get(field) != new_entry.get(field)
        }
        if changes:
            changed_services.append(
                {
                    "name": new_entry["name"],
                    "key": new_entry["key"],
                    "changes": changes,
                }
            )

    return {
        "comparison_kind": "fingerprint",
        "old_catalog_hash": old.get("catalog_hash"),
        "new_catalog_hash": new.get("catalog_hash"),
        "added_services": added_services,
        "removed_services": removed_services,
        "changed_services": changed_services,
    }


def summarize_changes(diff: dict[str, Any]) -> dict[str, int]:
    """Return high-level counts for a diff result."""
    required_param_change_count = 0
    added_operation_count = 0
    removed_operation_count = 0
    for service in diff.get("changed_services", []):
        required_param_change_count += len(service.get("required_param_changes", []))
        added_operation_count += len(service.get("added_operations", []))
        removed_operation_count += len(service.get("removed_operations", []))
    return {
        "added_service_count": len(diff.get("added_services", [])),
        "removed_service_count": len(diff.get("removed_services", [])),
        "changed_service_count": len(diff.get("changed_services", [])),
        "added_operation_count": added_operation_count,
        "removed_operation_count": removed_operation_count,
        "required_param_change_count": required_param_change_count,
    }


def compare_documents(old_path: Path, new_path: Path) -> dict[str, Any]:
    """Compare two catalog-like documents and return a structured report."""
    old = load_document(old_path)
    new = load_document(new_path)
    old_kind = document_kind(old)
    new_kind = document_kind(new)
    if old_kind == "catalog_index" or new_kind == "catalog_index":
        return {
            "success": False,
            "old": str(old_path),
            "new": str(new_path),
            "old_kind": old_kind,
            "new_kind": new_kind,
            "error": "Catalog index files are lazy runtime inputs; compare full generated catalogs or fingerprints instead.",
        }
    if old_kind != new_kind:
        return {
            "success": False,
            "old": str(old_path),
            "new": str(new_path),
            "old_kind": old_kind,
            "new_kind": new_kind,
            "error": "Both inputs must be the same document kind.",
        }

    diff = compare_fingerprints(old, new) if old_kind == "fingerprint" else compare_full_catalogs(old, new)
    summary = summarize_changes(diff)
    return {
        "success": True,
        "old": str(old_path),
        "new": str(new_path),
        "document_kind": old_kind,
        "has_changes": any(summary.values()),
        "summary": summary,
        **diff,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="Old catalog or fingerprint JSON path.")
    parser.add_argument("--new", required=True, help="New catalog or fingerprint JSON path.")
    parser.add_argument("--fail-on-change", action="store_true", help="Exit non-zero when changes are detected.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Run the catalog diff."""
    args = parse_args()
    result = compare_documents(Path(args.old), Path(args.new))
    hcloud_common.emit_json(result, pretty=args.pretty)
    if not result.get("success"):
        return 2
    return 1 if args.fail_on_change and result.get("has_changes") else 0


if __name__ == "__main__":
    raise SystemExit(main())
