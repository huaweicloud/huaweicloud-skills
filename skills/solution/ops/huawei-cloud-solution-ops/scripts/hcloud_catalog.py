#!/usr/bin/env python3
"""Read the generated hcloud metadata catalog used for broad service discovery."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CATALOG_PATH = ROOT / "references" / "hcloud-service-catalog.generated.json"
CATALOG_INDEX_PATH = ROOT / "references" / "hcloud-service-catalog.index.json"
CATALOG_PATH = CATALOG_INDEX_PATH if CATALOG_INDEX_PATH.exists() else LEGACY_CATALOG_PATH
CONFIDENCE_PATH = ROOT / "references" / "hcloud-service-confidence.json"

READ_ONLY_ACTIONS = {"List", "Show", "Count", "Check", "Search", "Query", "Get", "Download"}
DISCOVERY_ACTIONS = {"List", "Count", "Search", "Query", "Check"}
IGNORED_REQUIRED_PARAMS = {"x-auth-token", "content-type", "authorization", "x-language", "project_id", "projectid"}
PROJECT_PARAM_NAMES = {"project_id", "projectid"}
AUTH_PARAM_NAMES = IGNORED_REQUIRED_PARAMS - PROJECT_PARAM_NAMES
VERSION_SUFFIX_RE = re.compile(r"^(?P<name>.+?)/(?P<version>v[0-9][a-z0-9._-]*)$", re.IGNORECASE)


def normalize_token(value: str) -> str:
    """Return a lowercase alphanumeric-only token for loose matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_param_name(value: str) -> str:
    """Normalize a KooCLI parameter name for comparison."""
    return value.strip().lstrip("-").replace("-", "_").lower()


def split_operation_version(operation_name: str) -> tuple[str, str | None]:
    """Return a base operation name and optional explicit API version."""

    match = VERSION_SUFFIX_RE.fullmatch(operation_name.strip())
    if not match:
        return operation_name.strip(), None
    return match.group("name"), match.group("version").lower()


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    """Load the generated hcloud service catalog."""
    if not path.exists():
        if path == CATALOG_INDEX_PATH and LEGACY_CATALOG_PATH.exists():
            return load_catalog(LEGACY_CATALOG_PATH)
        return {"schema_version": 1, "services": {}}
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(catalog, dict):
        catalog["_catalog_path"] = str(path)
    return catalog


def catalog_base_path(catalog: dict[str, Any]) -> Path:
    """Return the base directory used for relative lazy service files."""
    raw_path = catalog.get("_catalog_path")
    if raw_path:
        return Path(str(raw_path)).parent
    return CATALOG_PATH.parent


def load_service_entry(catalog: dict[str, Any], service: dict[str, Any]) -> dict[str, Any]:
    """Return a full service entry, loading per-service catalog files on demand."""
    if isinstance(service.get("operations"), dict):
        return service
    cached = service.get("_loaded_service")
    if isinstance(cached, dict):
        return cached
    service_file = service.get("service_file")
    if not service_file:
        return service
    path = catalog_base_path(catalog) / str(service_file)
    if not path.exists():
        return service
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        service["_loaded_service"] = loaded
        return loaded
    return service


def load_confidence(path: Path = CONFIDENCE_PATH) -> dict[str, Any]:
    """Load optional confidence and live-validation metadata."""
    if not path.exists():
        return {"schema_version": 1, "services": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def service_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return catalog services keyed by normalized service name and template dir."""
    index: dict[str, dict[str, Any]] = {}
    for service in catalog.get("services", {}).values():
        if not isinstance(service, dict):
            continue
        candidates = [
            str(service.get("name") or ""),
            str(service.get("template_dir") or ""),
            str(service.get("service_key") or ""),
        ]
        for candidate in candidates:
            token = normalize_token(candidate)
            if token:
                index[token] = service
    return index


def resolve_service(catalog: dict[str, Any], service_name: str) -> dict[str, Any] | None:
    """Resolve a service name against the generated catalog."""
    service = service_index(catalog).get(normalize_token(service_name))
    if service is None:
        return None
    return load_service_entry(catalog, service)


def iter_services(catalog: dict[str, Any], expand: bool = False) -> list[tuple[str, dict[str, Any]]]:
    """Return catalog services, optionally loading split per-service entries."""
    result = []
    for key, service in catalog.get("services", {}).items():
        if not isinstance(service, dict):
            continue
        result.append((str(key), load_service_entry(catalog, service) if expand else service))
    return result


def operation_index(service: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return service operations keyed by normalized operation name."""
    index: dict[str, dict[str, Any]] = {}
    for operation in service.get("operations", {}).values():
        if not isinstance(operation, dict):
            continue
        name = str(operation.get("name") or "")
        token = normalize_token(name)
        if token:
            index[token] = operation
    return index


def resolve_operation(service: dict[str, Any], operation_name: str) -> dict[str, Any] | None:
    """Resolve an operation name against a catalog service."""
    base_operation, _ = split_operation_version(operation_name)
    return operation_index(service).get(normalize_token(base_operation))


def operation_versions(operation: dict[str, Any]) -> list[str]:
    """Return normalized API versions exposed for an operation."""

    versions = [
        str(version).strip().lower()
        for version in operation.get("versions", [])
        if str(version).strip()
    ]
    if versions:
        return list(dict.fromkeys(versions))
    selected = str(operation.get("selected_version") or "").strip().lower()
    return [selected] if selected else []


def operation_version_detail(operation: dict[str, Any], version: str | None) -> dict[str, Any]:
    """Return parameter/request metadata for one API version.

    Schema-v1 catalogs only contain flat metadata for their selected version.
    Keep accepting those catalogs while preferring schema-v2 per-version data.
    """

    normalized_version = str(version or "").strip().lower()
    version_details = operation.get("version_details")
    if isinstance(version_details, dict):
        for candidate, detail in version_details.items():
            if str(candidate).strip().lower() == normalized_version and isinstance(detail, dict):
                return detail
    selected = str(operation.get("selected_version") or "").strip().lower()
    if not normalized_version or normalized_version == selected:
        return operation
    return {}


def command_service_name(service: dict[str, Any], fallback: str) -> str:
    """Return the service name to pass to hcloud."""
    return str(service.get("name") or fallback)


def parameter_items(operation: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured parameter items, falling back to legacy lists."""
    raw_params = operation.get("params")
    if isinstance(raw_params, list):
        items = [param for param in raw_params if isinstance(param, dict)]
        known = {normalize_param_name(str(param.get("name") or "")) for param in items}
        for raw_name in operation.get("optional_params") or []:
            name = str(raw_name)
            normalized = normalize_param_name(name)
            if not normalized or normalized in known:
                continue
            items.append(
                {
                    "name": name,
                    "required": False,
                    "position": "",
                }
            )
        return items

    items: list[dict[str, Any]] = []
    for required, field in ((True, "required_params"), (False, "optional_params")):
        for raw_name in operation.get(field) or []:
            name = str(raw_name)
            normalized = normalize_param_name(name)
            if not normalized:
                continue
            items.append(
                {
                    "name": name,
                    "normalized_name": normalized,
                    "required": required,
                    "position": "",
                }
            )
    return items


def is_header_param(param: dict[str, Any]) -> bool:
    """Return whether a parameter is a header parameter."""
    return str(param.get("position") or param.get("in") or "").lower() == "header"


def operation_param_names(operation: dict[str, Any], include_headers: bool = False) -> list[str]:
    """Return known operation parameter names preserving catalog spelling."""
    names: list[str] = []
    for param in parameter_items(operation):
        if not include_headers and is_header_param(param):
            continue
        name = str(param.get("name") or "")
        normalized = normalize_param_name(name)
        if not normalized or normalized in IGNORED_REQUIRED_PARAMS:
            continue
        names.append(name)
    return list(dict.fromkeys(names))


def normalized_required_params(operation: dict[str, Any], include_project: bool = False) -> list[str]:
    """Return required non-auth parameter names for a catalog operation."""
    required: list[str] = []
    for param in parameter_items(operation):
        if param.get("required") is not True:
            continue
        if is_header_param(param):
            continue
        normalized = normalize_param_name(str(param.get("name") or ""))
        if not normalized:
            continue
        if normalized in AUTH_PARAM_NAMES:
            continue
        if not include_project and normalized in PROJECT_PARAM_NAMES:
            continue
        required.append(normalized)
    return list(dict.fromkeys(required))


def required_header_param_names(operation: dict[str, Any]) -> list[str]:
    """Return required non-auth header parameter names preserving catalog spelling."""
    names: list[str] = []
    for param in parameter_items(operation):
        if param.get("required") is not True or not is_header_param(param):
            continue
        name = str(param.get("name") or "")
        normalized = normalize_param_name(name)
        if not normalized or normalized in AUTH_PARAM_NAMES:
            continue
        names.append(name)
    return list(dict.fromkeys(names))


def required_param_names(operation: dict[str, Any], include_project: bool = False) -> list[str]:
    """Return required non-auth parameter names preserving catalog spelling."""
    names: list[str] = []
    for param in parameter_items(operation):
        if param.get("required") is not True:
            continue
        if is_header_param(param):
            continue
        name = str(param.get("name") or "")
        normalized = normalize_param_name(name)
        if not normalized:
            continue
        if normalized in AUTH_PARAM_NAMES:
            continue
        if not include_project and normalized in PROJECT_PARAM_NAMES:
            continue
        names.append(name)
    return list(dict.fromkeys(names))


def optional_param_names(operation: dict[str, Any]) -> list[str]:
    """Return optional non-header parameter names preserving catalog spelling."""
    names: list[str] = []
    for param in parameter_items(operation):
        if param.get("required") is True:
            continue
        if is_header_param(param):
            continue
        name = str(param.get("name") or "")
        normalized = normalize_param_name(name)
        if not normalized or normalized in PROJECT_PARAM_NAMES:
            continue
        names.append(name)
    return list(dict.fromkeys(names))


def parameter_by_name(operation: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Return a structured parameter by normalized name."""
    target = normalize_param_name(name)
    for param in parameter_items(operation):
        if normalize_param_name(str(param.get("name") or "")) == target:
            return param
    return None


def numeric_param_bound(param: dict[str, Any], key: str) -> int | None:
    """Return an integer parameter bound when catalog metadata provides one."""
    value = param.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def bounded_limit_value(operation: dict[str, Any], requested_limit: int) -> tuple[int, dict[str, Any] | None]:
    """Return a metadata-bounded limit value and an optional adjustment record."""
    param = parameter_by_name(operation, "limit")
    if not param:
        return requested_limit, None
    minimum = numeric_param_bound(param, "minimum")
    maximum = numeric_param_bound(param, "maximum")
    used_limit = requested_limit
    reason = None
    if minimum is not None and used_limit < minimum:
        used_limit = minimum
        reason = "metadata_minimum"
    if maximum is not None and used_limit > maximum:
        used_limit = maximum
        reason = "metadata_maximum"
    if used_limit == requested_limit:
        return requested_limit, None
    return used_limit, {
        "param": "limit",
        "requested": requested_limit,
        "used": used_limit,
        "minimum": minimum,
        "maximum": maximum,
        "reason": reason,
    }


def supports_limit(operation: dict[str, Any]) -> bool:
    """Return whether operation metadata exposes a limit parameter."""
    return any(normalize_param_name(name) == "limit" for name in operation_param_names(operation, include_headers=False))


def service_confidence(confidence: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Return optional confidence metadata for a service."""
    services = confidence.get("services", {})
    if not isinstance(services, dict):
        return {}
    return services.get(service_name) or services.get(service_name.upper()) or {}


def operation_confidence(confidence: dict[str, Any], service_name: str, operation_name: str) -> dict[str, Any]:
    """Return optional confidence metadata for a service operation."""
    service = service_confidence(confidence, service_name)
    operations = service.get("operations", {})
    if not isinstance(operations, dict):
        return {}
    return operations.get(operation_name) or {}


def operation_dryrun_state(confidence: dict[str, Any], service_name: str, operation_name: str) -> str:
    """Return dry-run support state for an operation."""
    state = str(operation_confidence(confidence, service_name, operation_name).get("dryrun") or "unknown").lower()
    if state not in {"supported", "unsupported", "unknown"}:
        return "unknown"
    return state


def operation_unsupported_optional_args(confidence: dict[str, Any], service_name: str, operation_name: str) -> set[str]:
    """Return optional CLI args that live/help evidence says this operation does not accept."""
    raw_args = operation_confidence(confidence, service_name, operation_name).get("unsupported_optional_args", [])
    if not isinstance(raw_args, list):
        return set()
    return {normalize_param_name(str(name)) for name in raw_args if normalize_param_name(str(name))}


def is_read_only(operation: dict[str, Any]) -> bool:
    """Return whether the catalog classifies an operation as read-only."""
    return bool(operation.get("read_only"))


def is_discovery_operation(operation: dict[str, Any]) -> bool:
    """Return whether an operation is safe as a generic list/count discovery entry."""
    return (
        is_read_only(operation)
        and str(operation.get("action") or "") in DISCOVERY_ACTIONS
        and not normalized_required_params(operation)
    )


def discovery_operations(service: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    """Return deterministic metadata-backed discovery operations for one service."""
    operations = [
        operation
        for operation in service.get("operations", {}).values()
        if isinstance(operation, dict) and is_discovery_operation(operation)
    ]
    priority = {"List": 0, "Count": 1, "Search": 2, "Query": 3, "Check": 4}
    operations.sort(key=lambda item: (priority.get(str(item.get("action")), 99), str(item.get("name", "")).lower()))
    return operations[:limit]


def catalog_service_names(catalog: dict[str, Any]) -> list[str]:
    """Return sorted catalog service display names."""
    return sorted(
        str(service.get("name") or key)
        for key, service in catalog.get("services", {}).items()
        if isinstance(service, dict)
    )
