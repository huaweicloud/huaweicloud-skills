#!/usr/bin/env python3
"""Build a compact hcloud service catalog from a local KooCLI metaRepo tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / ".hcloud" / "metaRepo"
DEFAULT_FINGERPRINT_OUTPUT = ROOT / "references" / "hcloud-service-catalog.fingerprint.json"
DEFAULT_INDEX_OUTPUT = ROOT / "references" / "hcloud-service-catalog.index.json"
DEFAULT_SERVICE_OUTPUT_DIR = ROOT / "references" / "hcloud-service-catalog"

LANGUAGE_ORDER = ("en", "cn")
READ_ONLY_ACTIONS = ("List", "Show", "Count", "Check", "Search", "Query", "Get", "Download")
MUTATING_ACTIONS = (
    "Accept",
    "Add",
    "Apply",
    "Associate",
    "Attach",
    "Batch",
    "Bind",
    "Change",
    "Clear",
    "Copy",
    "Create",
    "Delete",
    "Detach",
    "Disable",
    "Disassociate",
    "Enable",
    "Execute",
    "Expand",
    "Export",
    "Import",
    "Migrate",
    "Modify",
    "Move",
    "Pause",
    "Reboot",
    "Remove",
    "Reset",
    "Resize",
    "Restore",
    "Resume",
    "Retry",
    "Run",
    "Set",
    "Start",
    "Stop",
    "Switch",
    "Unbind",
    "Uninstall",
    "Update",
    "Upgrade",
    "Upload",
    "Verify",
)
NAMESPACE_TOKENS = ("Batch", "Nova", "Neutron", "Glance", "Cinder", "Keystone")
ACTION_TOKENS = tuple(dict.fromkeys((*READ_ONLY_ACTIONS, *MUTATING_ACTIONS)))
IGNORED_PARAM_NAMES = {"x-auth-token", "content-type", "authorization", "x-language", "[n]"}
PROJECT_PARAM_NAMES = {"project_id", "projectid"}
MAX_TEXT = 320
PRIVATE_CLOUD_CATEGORY = "hcs"


def parameter_metadata_complete(detail_file: str | None) -> bool:
    """Return whether a cached detail uses KooCLI's normalized parameter schema."""

    filename = str(detail_file or "").lower()
    return bool(filename and "_origin_" not in filename)


def normalize_token(value: str) -> str:
    """Return a lowercase alphanumeric-only token for loose matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_param_name(value: str) -> str:
    """Normalize a KooCLI parameter name for comparison."""
    return value.strip().lstrip("-").replace("-", "_").lower()


def clean_text(value: Any, max_chars: int = MAX_TEXT) -> str:
    """Return a compact single-line text value."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_service_items(meta_repo: Path) -> dict[str, dict[str, Any]]:
    """Load service metadata keyed by normalized service name.

    English service metadata remains preferred for stable existing catalog text.
    Chinese metadata fills services that are visible to KooCLI but absent from
    `services_en.json`.
    """
    services: dict[str, dict[str, Any]] = {}
    for language in LANGUAGE_ORDER:
        services_file = meta_repo / f"services_{language}.json"
        if not services_file.exists():
            continue
        data = load_json(services_file)
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            service = item.get("Service", {})
            if not isinstance(service, dict):
                continue
            name = str(service.get("Text") or "").strip()
            service_key = normalize_token(name)
            if not service_key or service_key in services:
                continue
            services[service_key] = {
                "name": name,
                "description": clean_text(service.get("Description")),
                "category": str(item.get("Category") or "Unknown"),
                "is_global": item.get("IsGlobal"),
                "metadata_language": language,
            }
    return services


def load_services_update_times(meta_repo: Path) -> dict[str, Any]:
    """Return update times from available service catalog metadata files."""
    update_times: dict[str, Any] = {}
    for language in LANGUAGE_ORDER:
        services_file = meta_repo / f"services_{language}.json"
        if services_file.exists():
            update_times[language] = load_json(services_file).get("updateTime")
    return update_times


def is_private_cloud_service(service_info: dict[str, Any]) -> bool:
    """Return whether service metadata describes an HCS/ManageOne control plane."""
    return str(service_info.get("category") or "").strip().casefold() == PRIVATE_CLOUD_CATEGORY


def select_version(versions: Any) -> str:
    """Select the highest version token from an apiList Versions field."""
    raw_versions = [str(version).strip() for version in versions if str(version).strip()] if isinstance(versions, list) else []
    if not raw_versions:
        return ""

    def version_key(version: str) -> list[int]:
        parts: list[int] = []
        for part in re.split(r"[._-]", version.lower().lstrip("v")):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(-1)
        return parts

    return max(raw_versions, key=version_key)


def operation_tokens(operation: str) -> list[str]:
    """Split an hcloud operation name into useful tokens."""
    raw_tokens = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+", operation)
    if raw_tokens:
        return [token[:1].upper() + token[1:] for token in raw_tokens]

    lowered = operation.lower()
    matches: list[tuple[int, int, str]] = []
    for token in (*NAMESPACE_TOKENS, *ACTION_TOKENS):
        index = lowered.find(token.lower())
        if index >= 0:
            matches.append((index, -len(token), token))
    return [token for _, _, token in sorted(matches)] or [operation]


def operation_action(operation: str) -> str | None:
    """Return the first recognized action token in an operation name."""
    for token in operation_tokens(operation):
        if token in ACTION_TOKENS and token not in NAMESPACE_TOKENS:
            return token
    return None


def load_detail(
    template_dir: Path,
    operation_name: str,
    version: str,
    language: str,
) -> tuple[dict[str, Any], str | None, str | None]:
    """Load a selected operation detail file when present."""
    candidates: list[Path] = []
    detail_languages = (language, *(candidate for candidate in LANGUAGE_ORDER if candidate != language))
    for detail_language in detail_languages:
        if version:
            candidates.append(template_dir / f"{operation_name}_{version}_{detail_language}.yaml")
        candidates.append(template_dir / f"{operation_name}_{detail_language}.yaml")
        candidates.extend(sorted(template_dir.glob(f"{operation_name}_*_{detail_language}.yaml")))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        try:
            payload = load_json(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            detail_language = candidate.stem.rsplit("_", 1)[-1]
            return payload, candidate.name, detail_language
    return {}, None, None


def load_version_detail(
    template_dir: Path,
    operation_name: str,
    version: str,
    language: str,
    *,
    allow_unversioned: bool,
) -> tuple[dict[str, Any], str | None, str | None]:
    """Load metadata for one exact API version.

    Multi-version operations must not borrow another version's detail file:
    their parameters and request paths can differ even when the operation name
    is identical. An unversioned detail file is accepted only for operations
    that expose a single version.
    """

    detail_languages = (language, *(candidate for candidate in LANGUAGE_ORDER if candidate != language))
    candidates: list[Path] = []
    for detail_language in detail_languages:
        candidates.append(template_dir / f"{operation_name}_{version}_{detail_language}.yaml")
        if allow_unversioned:
            candidates.append(template_dir / f"{operation_name}_{detail_language}.yaml")

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = load_json(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            detail_language = candidate.stem.rsplit("_", 1)[-1]
            return payload, candidate.name, detail_language
    return {}, None, None


def iter_param_names(param: dict[str, Any]) -> list[str]:
    """Return parameter names from one metadata param object."""
    raw_names = param.get("Name", [])
    names = raw_names if isinstance(raw_names, list) else [raw_names]
    result: list[str] = []
    for raw_name in names:
        name = str(raw_name or "").strip()
        if not name or name.lower() in IGNORED_PARAM_NAMES:
            continue
        result.append(name)
    return result


def build_param_items(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact structured parameter items from an operation detail payload."""
    result: list[dict[str, Any]] = []
    params = detail.get("Params", [])
    if not isinstance(params, list):
        return result
    for param in params:
        if not isinstance(param, dict):
            continue
        names = iter_param_names(param)
        if not names:
            continue
        name = names[0]
        normalized = normalize_param_name(name)
        if not normalized:
            continue
        item: dict[str, Any] = {
            "name": name,
            "required": param.get("Required") is True,
            "position": str(param.get("Position") or "").lower(),
        }
        if param.get("ParamType"):
            item["type"] = param.get("ParamType")
        for source_key, target_key in (
            ("Default", "default"),
            ("Minimum", "minimum"),
            ("Maximum", "maximum"),
            ("MinLength", "min_length"),
            ("MaxLength", "max_length"),
            ("EnumValue", "enum"),
            ("CollectionFormat", "collection_format"),
        ):
            if source_key in param and param.get(source_key) is not None:
                item[target_key] = param.get(source_key)
        result.append(item)
    return result


def business_param_names(params: list[dict[str, Any]], required: bool | None = None) -> list[str]:
    """Return non-header, non-project parameter names for compatibility fields."""
    names: list[str] = []
    for param in params:
        if required is not None and bool(param.get("required")) is not required:
            continue
        if str(param.get("position") or "").lower() == "header":
            continue
        normalized = normalize_param_name(str(param.get("name") or ""))
        if not normalized or normalized in PROJECT_PARAM_NAMES:
            continue
        names.append(str(param.get("name")))
    return list(dict.fromkeys(names))


def all_param_names(params: list[dict[str, Any]]) -> list[str]:
    """Return all non-ignored parameter names for compatibility checks."""
    return [str(param.get("name")) for param in params if param.get("name")]


def retained_param_items(params: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return structured params worth retaining in the compact generated catalog."""
    result = []
    for param in params:
        name = str(param.get("name") or "")
        if param.get("required") is True or normalize_param_name(name) == "limit":
            result.append(param)
    return result


def build_version_detail(
    template_dir: Path,
    operation_name: str,
    version: str,
    language: str,
    suggests: dict[str, Any],
    *,
    allow_unversioned: bool,
) -> dict[str, Any]:
    """Build compact metadata for one operation API version."""

    detail, detail_file, detail_language = load_version_detail(
        template_dir,
        operation_name,
        version,
        language,
        allow_unversioned=allow_unversioned,
    )
    all_params = build_param_items(detail)
    request = detail.get("Request", {}) if isinstance(detail.get("Request"), dict) else {}
    params_lower = {normalize_param_name(name) for name in all_param_names(all_params)}
    return {
        "version": version,
        "summary": clean_text(suggests.get(version)),
        "description": clean_text(detail.get("Description")),
        "detail_cached": bool(detail_file),
        "detail_file": detail_file,
        "parameter_metadata_complete": parameter_metadata_complete(detail_file),
        "detail_language": detail_language,
        "method": request.get("Method"),
        "path": request.get("Path"),
        "has_body_params": request.get("HasBodyParams"),
        "params": retained_param_items(all_params),
        "required_params": business_param_names(all_params, required=True),
        "optional_params": business_param_names(all_params, required=False),
        "supports_limit": "limit" in params_lower,
    }


def build_operation(template_dir: Path, raw_api: dict[str, Any], language: str) -> dict[str, Any] | None:
    """Build one compact catalog operation item."""
    operation_name = str(raw_api.get("Name") or "").strip()
    if not operation_name:
        return None
    raw_versions = raw_api.get("Versions", [])
    versions = (
        [str(item).strip() for item in raw_versions if str(item).strip()]
        if isinstance(raw_versions, list)
        else []
    )
    version = select_version(versions)
    suggests = raw_api.get("Suggests", {})
    suggests = suggests if isinstance(suggests, dict) else {}
    version_details = {
        candidate_version: build_version_detail(
            template_dir,
            operation_name,
            candidate_version,
            language,
            suggests,
            allow_unversioned=len(versions) == 1,
        )
        for candidate_version in versions
    }
    selected_detail = version_details.get(version, {})
    if not selected_detail.get("detail_cached"):
        detail, detail_file, detail_language = load_detail(template_dir, operation_name, version, language)
        all_params = build_param_items(detail)
        request = detail.get("Request", {}) if isinstance(detail.get("Request"), dict) else {}
        selected_detail = {
            "version": version,
            "summary": clean_text(suggests.get(version)),
            "description": clean_text(detail.get("Description")),
            "detail_cached": bool(detail_file),
            "detail_file": detail_file,
            "parameter_metadata_complete": parameter_metadata_complete(detail_file),
            "detail_language": detail_language,
            "method": request.get("Method"),
            "path": request.get("Path"),
            "has_body_params": request.get("HasBodyParams"),
            "params": retained_param_items(all_params),
            "required_params": business_param_names(all_params, required=True),
            "optional_params": business_param_names(all_params, required=False),
            "supports_limit": "limit"
            in {normalize_param_name(name) for name in all_param_names(all_params)},
        }
    action = operation_action(operation_name)
    operation = {
        "name": operation_name,
        "summary": selected_detail.get("summary")
        or clean_text(next((value for value in suggests.values() if value), "")),
        "description": selected_detail.get("description", ""),
        "versions": versions,
        "selected_version": version,
        "metadata_language": language,
        "action": action,
        "read_only": action in READ_ONLY_ACTIONS,
        "detail_cached": bool(selected_detail.get("detail_cached")),
        "detail_file": selected_detail.get("detail_file"),
        "parameter_metadata_complete": bool(
            selected_detail.get("parameter_metadata_complete")
        ),
        "detail_language": selected_detail.get("detail_language"),
        "method": selected_detail.get("method"),
        "path": selected_detail.get("path"),
        "has_body_params": selected_detail.get("has_body_params"),
        "params": selected_detail.get("params", []),
        "required_params": selected_detail.get("required_params", []),
        "optional_params": selected_detail.get("optional_params", []),
        "supports_limit": bool(selected_detail.get("supports_limit")),
    }
    if len(versions) > 1:
        operation["version_details"] = version_details
    return operation


def load_api_entries(template_dir: Path) -> list[tuple[str, dict[str, Any], str]]:
    """Return operation API entries, preferring English and filling gaps from Chinese."""
    operations: dict[str, tuple[str, dict[str, Any], str]] = {}
    for language in LANGUAGE_ORDER:
        apis_file = template_dir / f"apis_{language}.json"
        if not apis_file.exists():
            continue
        apis_data = load_json(apis_file)
        api_list = apis_data.get("apiList", {})
        if not isinstance(api_list, dict):
            continue
        for raw_api in api_list.values():
            if not isinstance(raw_api, dict):
                continue
            operation_name = str(raw_api.get("Name") or "").strip()
            operation_key = normalize_token(operation_name)
            if not operation_key or operation_key in operations:
                continue
            operations[operation_key] = (operation_name, raw_api, language)
    return sorted(operations.values(), key=lambda item: item[0].lower())


def build_catalog(meta_repo: Path, include_hcs: bool = False) -> dict[str, Any]:
    """Build a generated catalog, excluding private-cloud services by default.

    The raw KooCLI metadata cache contains HCS and ManageOne control-plane
    templates alongside Huawei Cloud public-cloud metadata. They are retained
    in the source cache, but are not compatible with this skill's default
    public-cloud runtime. Set ``include_hcs`` only for dedicated private-cloud
    maintenance or review.
    """
    services = load_service_items(meta_repo)
    template_root = meta_repo / "template"
    catalog_services: dict[str, Any] = {}
    if not template_root.exists():
        return {"schema_version": 2, "source": {"format": "hcloud metaRepo"}, "services": catalog_services}

    for template_dir in sorted(path for path in template_root.iterdir() if path.is_dir()):
        api_entries = load_api_entries(template_dir)
        if not api_entries:
            continue
        service_key = normalize_token(template_dir.name)
        service_info = services.get(service_key, {})
        if not include_hcs and is_private_cloud_service(service_info):
            continue
        service_name = str(service_info.get("name") or template_dir.name.upper())
        operations: dict[str, Any] = {}
        operation_language_counts: dict[str, int] = {}
        for _, raw_api, language in api_entries:
            operation = build_operation(template_dir, raw_api, language)
            if operation:
                operations[operation["name"]] = operation
                operation_language_counts[language] = operation_language_counts.get(language, 0) + 1
        if not operations:
            continue
        metadata_languages = sorted(operation_language_counts)
        service_metadata_language = metadata_languages[0] if len(metadata_languages) == 1 else "mixed"
        catalog_services[service_key] = {
            "name": service_name,
            "service_key": service_key,
            "template_dir": template_dir.name,
            "category": service_info.get("category", "Unknown"),
            "description": service_info.get("description", ""),
            "is_global": service_info.get("is_global"),
            "metadata_language": service_metadata_language,
            "service_metadata_language": service_info.get("metadata_language"),
            "operation_language_counts": dict(sorted(operation_language_counts.items())),
            "operation_count": len(operations),
            "operations": dict(sorted(operations.items(), key=lambda item: item[0].lower())),
        }

    services_update_times = load_services_update_times(meta_repo)
    operation_count = sum(service["operation_count"] for service in catalog_services.values())
    return {
        "schema_version": 2,
        "source": {
            "format": "hcloud metaRepo",
            "runtime_scope": "all-metadata" if include_hcs else "public-cloud",
            "excluded_categories": [] if include_hcs else ["HCS"],
            "languages": list(LANGUAGE_ORDER),
            "merge_strategy": "operation-level English metadata preferred; Chinese metadata fills missing services, operations, and details",
            "services_update_time": services_update_times.get("en"),
            "services_update_times": services_update_times,
            "service_count": len(catalog_services),
            "operation_count": operation_count,
        },
        "services": dict(sorted(catalog_services.items(), key=lambda item: item[1]["name"].lower())),
    }


def hash_json(value: Any) -> str:
    """Return a stable short SHA-256 hash for a JSON-like value."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def build_fingerprint(catalog: dict[str, Any]) -> dict[str, Any]:
    """Build a compact review-friendly fingerprint for catalog diffs."""
    services: dict[str, Any] = {}
    for service_key, service in sorted(catalog.get("services", {}).items()):
        operations = service.get("operations", {}) if isinstance(service, dict) else {}
        operation_names = sorted(str(name) for name in operations)
        required_by_operation = {
            name: sorted(str(param) for param in operations[name].get("required_params", []))
            for name in operation_names
            if isinstance(operations.get(name), dict)
        }
        services[service_key] = {
            "name": service.get("name"),
            "operation_count": len(operation_names),
            "operations_hash": hash_json(operation_names),
            "required_params_hash": hash_json(required_by_operation),
        }
    return {
        "schema_version": 1,
        "catalog_schema_version": catalog.get("schema_version"),
        "source": catalog.get("source", {}),
        "services": services,
        "catalog_hash": hash_json(
            {
                "source": catalog.get("source", {}),
                "services": services,
            }
        ),
    }


def split_service_catalog(catalog: dict[str, Any], service_output_dir: Path, index_output: Path) -> tuple[dict[str, Any], dict[Path, dict[str, Any]]]:
    """Build a light catalog index and per-service payloads for lazy loading."""
    services: dict[str, Any] = {}
    service_payloads: dict[Path, dict[str, Any]] = {}
    base_dir = index_output.parent
    for service_key, service in sorted(catalog.get("services", {}).items()):
        service_file = service_output_dir / f"{service_key}.json"
        entry = {key: value for key, value in service.items() if key != "operations"}
        entry["service_file"] = service_file.relative_to(base_dir).as_posix()
        services[service_key] = entry
        service_payloads[service_file] = service
    index = {
        "schema_version": catalog.get("schema_version", 1),
        "split": True,
        "source": catalog.get("source", {}),
        "services": services,
    }
    return index, service_payloads


def write_json(path: Path, payload: Any, pretty: bool = True) -> None:
    """Write JSON using repository-standard UTF-8 formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    path.write_text(f"{text}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-meta-repo", default=str(DEFAULT_SOURCE), help="Source hcloud metaRepo directory.")
    parser.add_argument(
        "--output",
        default="",
        help="Optional full generated catalog output path. Empty by default so committed assets stay below package size limits.",
    )
    parser.add_argument(
        "--fingerprint-output",
        default=str(DEFAULT_FINGERPRINT_OUTPUT),
        help="Generated compact fingerprint output path. Use an empty string to skip.",
    )
    parser.add_argument(
        "--index-output",
        default=str(DEFAULT_INDEX_OUTPUT),
        help="Generated lazy catalog index output path. Use an empty string to skip split output.",
    )
    parser.add_argument(
        "--service-output-dir",
        default=str(DEFAULT_SERVICE_OUTPUT_DIR),
        help="Generated per-service catalog output directory.",
    )
    parser.add_argument(
        "--include-hcs",
        action="store_true",
        help="Include HCS/ManageOne private-cloud metadata instead of the default public-cloud catalog scope.",
    )
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON instead of compact JSON.")
    return parser.parse_args()


def main() -> int:
    """Generate the hcloud service catalog."""
    args = parse_args()
    source = Path(args.source_meta_repo).expanduser().resolve()
    catalog = build_catalog(source, include_hcs=args.include_hcs)
    output = Path(args.output).expanduser().resolve() if args.output else None
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.pretty:
            text = json.dumps(catalog, ensure_ascii=False, indent=2)
        else:
            text = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
        output.write_text(text + "\n", encoding="utf-8")
    fingerprint_path = Path(args.fingerprint_output).expanduser().resolve() if args.fingerprint_output else None
    if fingerprint_path:
        fingerprint_path.parent.mkdir(parents=True, exist_ok=True)
        fingerprint_path.write_text(
            json.dumps(build_fingerprint(catalog), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    index_path = Path(args.index_output).expanduser().resolve() if args.index_output else None
    service_output_dir = Path(args.service_output_dir).expanduser().resolve()
    if index_path:
        index, service_payloads = split_service_catalog(catalog, service_output_dir, index_path)
        write_json(index_path, index, pretty=True)
        for service_file, payload in service_payloads.items():
            write_json(service_file, payload, pretty=False)
    print(
        json.dumps(
            {
                "success": True,
                "output": str(output) if output else None,
                "fingerprint_output": str(fingerprint_path) if fingerprint_path else None,
                "index_output": str(index_path) if index_path else None,
                "service_output_dir": str(service_output_dir) if index_path else None,
                "service_count": catalog["source"]["service_count"],
                "operation_count": catalog["source"]["operation_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
