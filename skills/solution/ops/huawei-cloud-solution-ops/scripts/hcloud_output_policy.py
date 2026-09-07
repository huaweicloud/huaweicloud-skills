#!/usr/bin/env python3
"""Resolve and summarize hcloud output policies for agent-safe execution."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import hcloud_catalog

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "references" / "hcloud-output-policies.json"
OUTPUT_MODES = ("auto", "full", "summary", "file-only")


def load_policy_registry(path: Path = POLICY_PATH) -> dict[str, Any]:
    """Load the machine-readable output policy registry."""

    with path.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise ValueError("Unsupported hcloud output policy registry schema.")
    return registry


def normalize_service(value: str | None) -> str:
    """Return a stable case-insensitive service key."""

    return str(value or "").strip().upper()


def normalize_operation(value: str | None) -> str:
    """Return an operation name without an explicit API version suffix."""

    operation, _ = hcloud_catalog.split_operation_version(str(value or "").strip())
    return operation


def operation_policy(
    service: str | None,
    operation: str | None,
    *,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the exact or family output policy for one hcloud operation."""

    registry = registry or load_policy_registry()
    service_key = normalize_service(service)
    operation_key = normalize_operation(operation)
    wanted_key = f"{service_key}:{operation_key}".lower()
    for key, entry in registry.get("operations", {}).items():
        if str(key).lower() == wanted_key and isinstance(entry, dict):
            return {
                **entry,
                "policy_id": str(key),
                "policy_source": "operation",
            }

    for family in registry.get("families", []):
        if not isinstance(family, dict):
            continue
        services = {normalize_service(item) for item in family.get("services", [])}
        if services and service_key not in services:
            continue
        pattern = str(family.get("operation_pattern") or "")
        if pattern and re.search(pattern, operation_key, flags=re.IGNORECASE):
            return {
                **family,
                "policy_id": str(family.get("id") or "family"),
                "policy_source": "family",
            }
    return None


def default_limit(
    service: str | None,
    operation: str | None,
    *,
    registry: dict[str, Any] | None = None,
) -> tuple[str, int] | None:
    """Return the policy default pagination parameter and value, if defined."""

    policy = operation_policy(service, operation, registry=registry)
    value = policy.get("default_limit") if policy else None
    if not isinstance(value, dict):
        return None
    param = str(value.get("param") or "").strip()
    limit = value.get("value")
    if not param or not isinstance(limit, int) or limit < 1:
        return None
    return param, limit


def resolve_output_policy(
    service: str | None,
    operation: str | None,
    *,
    requested_mode: str,
    provided_params: set[str],
    allow_large_output: bool,
    max_parsed_json_chars: int | None = None,
    sample_items: int | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the effective output contract before executing hcloud."""

    registry = registry or load_policy_registry()
    defaults = registry.get("defaults", {})
    matched = operation_policy(service, operation, registry=registry)
    high_volume = matched is not None
    policy_mode = str((matched or {}).get("mode") or "auto")
    effective_mode = policy_mode if requested_mode == "auto" else requested_mode
    required_all = [
        str(item)
        for item in (matched or {}).get("required_all", [])
        if str(item).strip()
    ]
    normalized_params = {
        str(item).strip().lstrip("-").replace("-", "_").lower()
        for item in provided_params
    }
    missing_required = [
        item
        for item in required_all
        if item.strip().lstrip("-").replace("-", "_").lower() not in normalized_params
    ]
    blocked_reason = None
    if missing_required:
        blocked_reason = "missing_required_output_filters"
    elif requested_mode == "full" and high_volume and not allow_large_output:
        blocked_reason = "large_output_requires_explicit_override"

    limit = default_limit(service, operation, registry=registry)
    resolved = {
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "policy_id": (matched or {}).get("policy_id"),
        "policy_source": (matched or {}).get("policy_source", "default"),
        "risk_class": (matched or {}).get("risk_class", "unclassified"),
        "high_volume": high_volume,
        "max_parsed_json_chars": int(
            max_parsed_json_chars
            if max_parsed_json_chars is not None
            else defaults.get("max_parsed_json_chars", 12000)
        ),
        "sample_items": int(
            sample_items
            if sample_items is not None
            else defaults.get("sample_items", 3)
        ),
        "sample_fields": list((matched or {}).get("sample_fields", [])),
        "sample_field_limit": int(defaults.get("sample_fields", 12)),
        "sample_string_chars": int(defaults.get("sample_string_chars", 240)),
        "required_all": required_all,
        "missing_required": missing_required,
        "default_limit": (
            {"param": limit[0], "value": limit[1]} if limit else None
        ),
        "allow_large_output": bool(allow_large_output),
        "blocked": blocked_reason is not None,
        "blocked_reason": blocked_reason,
    }
    return resolved


def compact_value(
    value: Any,
    *,
    field_limit: int,
    string_limit: int,
    depth: int = 0,
) -> Any:
    """Return a bounded representation suitable for an agent-facing sample."""

    if isinstance(value, str):
        if len(value) <= string_limit:
            return value
        return f"{value[:string_limit]}…"
    if isinstance(value, dict):
        if depth >= 2:
            return {"_type": "object", "_field_count": len(value)}
        keys = list(value)[:field_limit]
        result = {
            str(key): compact_value(
                value[key],
                field_limit=field_limit,
                string_limit=string_limit,
                depth=depth + 1,
            )
            for key in keys
        }
        if len(value) > len(keys):
            result["_omitted_field_count"] = len(value) - len(keys)
        return result
    if isinstance(value, list):
        if depth >= 2:
            return {"_type": "array", "_item_count": len(value)}
        sample = [
            compact_value(
                item,
                field_limit=field_limit,
                string_limit=string_limit,
                depth=depth + 1,
            )
            for item in value[:2]
        ]
        if len(value) > len(sample):
            sample.append({"_omitted_item_count": len(value) - len(sample)})
        return sample
    return value


def array_inventory(
    value: Any,
    *,
    path: str = "$",
    depth: int = 0,
    max_depth: int = 4,
) -> list[dict[str, Any]]:
    """Return bounded array paths and counts from a JSON-like value."""

    if depth > max_depth:
        return []
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        rows.append({"path": path, "count": len(value)})
        for index, item in enumerate(value[:1]):
            rows.extend(
                array_inventory(
                    item,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            )
    elif isinstance(value, dict):
        for key, child in list(value.items())[:50]:
            rows.extend(
                array_inventory(
                    child,
                    path=f"{path}.{key}",
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            )
    return rows


def primary_array(value: Any) -> tuple[str | None, list[Any] | None]:
    """Return the largest shallow array and its JSON path."""

    candidates: list[tuple[str, list[Any]]] = []

    def visit(child: Any, path: str, depth: int) -> None:
        if depth > 4:
            return
        if isinstance(child, list):
            candidates.append((path, child))
            if child:
                visit(child[0], f"{path}[0]", depth + 1)
        elif isinstance(child, dict):
            for key, nested in list(child.items())[:50]:
                visit(nested, f"{path}.{key}", depth + 1)

    visit(value, "$", 0)
    if not candidates:
        return None, None
    return max(candidates, key=lambda item: len(item[1]))


def summarize_json(value: Any, policy: dict[str, Any], *, include_sample: bool = True) -> dict[str, Any]:
    """Build a deterministic bounded summary of a parsed JSON response."""

    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    path, rows = primary_array(value)
    field_limit = int(policy.get("sample_field_limit", 12))
    string_limit = int(policy.get("sample_string_chars", 240))
    sample_limit = int(policy.get("sample_items", 3))
    selected_fields = [
        str(item)
        for item in policy.get("sample_fields", [])
        if str(item).strip()
    ]
    sample: list[Any] = []
    if include_sample and rows is not None:
        for row in rows[:sample_limit]:
            if isinstance(row, dict) and selected_fields:
                projected = {
                    key: compact_value(
                        row[key],
                        field_limit=field_limit,
                        string_limit=string_limit,
                    )
                    for key in selected_fields
                    if key in row
                }
                sample.append(
                    projected
                    or compact_value(
                        row,
                        field_limit=field_limit,
                        string_limit=string_limit,
                    )
                )
            else:
                sample.append(
                    compact_value(
                        row,
                        field_limit=field_limit,
                        string_limit=string_limit,
                    )
                )

    top_level_keys = list(value)[:50] if isinstance(value, dict) else []
    top_level_scalars = {}
    top_level_scalar_keys = []
    if isinstance(value, dict):
        for key, child in list(value.items())[:50]:
            if isinstance(child, (str, int, float, bool)) or child is None:
                top_level_scalar_keys.append(str(key))
                if include_sample:
                    top_level_scalars[str(key)] = compact_value(
                        child,
                        field_limit=field_limit,
                        string_limit=string_limit,
                    )

    return {
        "json_type": type(value).__name__,
        "serialized_chars": len(serialized),
        "top_level_keys": top_level_keys,
        "top_level_scalar_keys": top_level_scalar_keys,
        "top_level_scalars": top_level_scalars,
        "arrays": array_inventory(value)[:50],
        "primary_array_path": path,
        "primary_array_count": len(rows) if rows is not None else None,
        "sample": sample,
        "sample_count": len(sample),
    }
