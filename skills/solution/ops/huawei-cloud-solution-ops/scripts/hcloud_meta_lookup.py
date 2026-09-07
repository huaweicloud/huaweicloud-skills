#!/usr/bin/env python3
"""Inspect local hcloud metadata cache and expose cached Huawei Cloud service details."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common

LANGUAGE_ORDER = ("en", "cn")


def load_structured_detail(path: Path) -> tuple[Any | None, str, str | None]:
    """Load a metadata detail file as JSON first, then YAML when PyYAML is available."""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text), "json", None
    except json.JSONDecodeError as json_exc:
        try:
            import yaml  # type: ignore[import-untyped]
        except ModuleNotFoundError:
            return None, "yaml_unavailable", f"JSON parse failed and PyYAML is not installed: {json_exc}"

        try:
            return yaml.safe_load(text), "yaml", None
        except Exception as yaml_exc:  # pragma: no cover - exact PyYAML exception classes vary.
            return None, "unparsed", f"Could not parse as JSON or YAML: {yaml_exc}"


def normalize_token(value: str) -> str:
    """Return a lowercase alphanumeric-only token for loose matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def collect_service_catalog(meta_repo: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load service catalogs and build an index keyed by normalized service name."""
    items_by_key: dict[str, dict[str, Any]] = {}
    service_index: dict[str, dict[str, Any]] = {}
    for language in LANGUAGE_ORDER:
        services_file = meta_repo / f"services_{language}.json"
        if not services_file.exists():
            continue
        services_data = hcloud_common.load_json(services_file)
        for item in services_data.get("items", []):
            service = item.get("Service", {})
            name = service.get("Text", "")
            service_key = normalize_token(name)
            if not service_key or service_key in items_by_key:
                continue
            copied_item = dict(item)
            copied_item["MetadataLanguage"] = language
            items_by_key[service_key] = copied_item
            service_index[service_key] = copied_item
    items = sorted(items_by_key.values(), key=lambda item: str(item.get("Service", {}).get("Text", "")).lower())
    return items, service_index


def collect_template_dirs(meta_repo: Path) -> dict[str, Path]:
    """Map normalized template service names to their directory paths."""
    template_root = meta_repo / "template"
    if not template_root.exists():
        return {}

    template_dirs: dict[str, Path] = {}
    for child in template_root.iterdir():
        if child.is_dir():
            template_dirs[normalize_token(child.name)] = child
    return template_dirs


def detail_operation_name(detail_file: Path, language: str) -> str:
    """Return the operation name represented by a cached detail file."""
    operation_name, _ = detail_operation_identity(detail_file, language)
    return operation_name


def detail_operation_identity(detail_file: Path, language: str) -> tuple[str, str | None]:
    """Return the operation name and optional API version from a detail file."""
    suffix = f"_{language}.yaml"
    stem = detail_file.name[: -len(suffix)]
    candidate, _, maybe_version = stem.rpartition("_")
    if candidate and re.fullmatch(r"v[0-9][A-Za-z0-9._-]*", maybe_version):
        return candidate, maybe_version.lower()
    return stem, None


def summarize_service(item: dict[str, Any], template_dir: Path | None) -> dict[str, Any]:
    """Return a compact service summary."""
    service = item.get("Service", {})
    return {
        "name": service.get("Text"),
        "description": service.get("Description"),
        "category": item.get("Category"),
        "is_global": item.get("IsGlobal"),
        "metadata_language": item.get("MetadataLanguage"),
        "cached_locally": template_dir is not None,
        "template_dir": template_dir.name if template_dir else None,
    }


def load_cached_operations(template_dir: Path | None) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load cached operation summaries from local metadata when available."""
    if template_dir is None:
        return [], {}

    operations: list[dict[str, Any]] = []
    operation_index: dict[str, dict[str, Any]] = {}
    for language in LANGUAGE_ORDER:
        apis_file = template_dir / f"apis_{language}.json"
        if not apis_file.exists():
            continue
        apis_data = hcloud_common.load_json(apis_file)
        api_list = apis_data.get("apiList", {})
        if not isinstance(api_list, dict):
            continue
        for raw_entry in api_list.values():
            name = raw_entry.get("Name") if isinstance(raw_entry, dict) else None
            normalized_name = normalize_token(str(name or ""))
            if not normalized_name or normalized_name in operation_index:
                continue
            entry = {
                "name": name,
                "versions": raw_entry.get("Versions", []),
                "suggests": raw_entry.get("Suggests", {}),
                "metadata_language": language,
                "detail_cached": False,
            }
            operations.append(entry)
            operation_index[normalized_name] = entry

    operations.sort(key=lambda entry: entry["name"])

    for language in LANGUAGE_ORDER:
        for detail_file in template_dir.glob(f"*_{language}.yaml"):
            operation_name = detail_operation_name(detail_file, language)
            normalized = normalize_token(operation_name)
            if normalized in operation_index:
                operation_index[normalized]["detail_cached"] = True
                operation_index[normalized]["detail_language"] = language

    return operations, operation_index


def load_operation_detail(template_dir: Path | None, operation_name: str) -> dict[str, Any] | None:
    """Load cached per-operation detail from a local metadata file when available."""
    if template_dir is None:
        return None

    base_operation, explicit_version = hcloud_catalog.split_operation_version(operation_name)
    target = normalize_token(base_operation)
    for language in LANGUAGE_ORDER:
        for detail_file in sorted(template_dir.glob(f"*_{language}.yaml")):
            candidate_name, candidate_version = detail_operation_identity(detail_file, language)
            if normalize_token(candidate_name) != target:
                continue
            if explicit_version and candidate_version != explicit_version:
                continue
            detail, detail_format, error = load_structured_detail(detail_file)
            if not isinstance(detail, dict):
                return {
                    "detail_file": detail_file.name,
                    "detail_file_format": detail_format,
                    "detail_language": language,
                    "version": candidate_version,
                    "error": error or "Cached detail file exists but did not parse to an object.",
                }

            params = detail.get("Params", [])
            request = detail.get("Request", {})
            return {
                "detail_file": detail_file.name,
                "detail_file_format": detail_format,
                "detail_language": language,
                "version": candidate_version,
                "description": detail.get("Description"),
                "group_id": detail.get("GroupId"),
                "cli_version": detail.get("CLIVersion"),
                "request": {
                    "method": request.get("Method"),
                    "path": request.get("Path"),
                    "scheme": request.get("Scheme"),
                    "content_type": request.get("ContentType"),
                    "has_body_params": request.get("HasBodyParams"),
                },
                "params": [
                    {
                        "name": param.get("Name", []),
                        "required": param.get("Required"),
                        "position": param.get("Position"),
                        "type": param.get("ParamType"),
                        "enum": param.get("EnumValue"),
                        "default": param.get("Default"),
                    }
                    for param in params
                ],
                "param_count": len(params),
            }
    return None


def load_endpoints(template_dir: Path | None, region: str | None) -> dict[str, Any] | None:
    """Load cached endpoint data and optionally filter by region."""
    if template_dir is None:
        return None

    endpoints_file = next(
        (
            template_dir / f"endpoints_{language}.json"
            for language in LANGUAGE_ORDER
            if (template_dir / f"endpoints_{language}.json").exists()
        ),
        None,
    )
    if endpoints_file is None:
        return None

    endpoints_data = hcloud_common.load_json(endpoints_file)
    groups = endpoints_data.get("groupInfo", [])
    if region:
        groups = [group for group in groups if group.get("region") == region]

    return {
        "service": endpoints_data.get("service"),
        "update_time": endpoints_data.get("updateTime"),
        "metadata_language": endpoints_file.stem.rsplit("_", 1)[-1],
        "region_count": len(groups),
        "groups": groups,
    }


def run_service_help(service_name: str, timeout: int) -> dict[str, Any]:
    """Try `hcloud <service> --help` and parse visible operation names when possible."""
    binary = shutil.which("hcloud")
    if not binary:
        return {
            "attempted": False,
            "available": False,
            "operations": [],
            "error": "hcloud binary not found in PATH.",
        }

    completed = subprocess.run(
        [binary, service_name, "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    stdout = completed.stdout
    operations: list[str] = []
    capture = False
    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        if line.strip() == "Available Operations:":
            capture = True
            continue
        if capture:
            if not line.strip():
                continue
            if line.startswith("Run `hcloud "):
                break
            if line.startswith("  "):
                operations.append(line.strip())
            else:
                break

    return {
        "attempted": True,
        "available": bool(operations),
        "return_code": completed.returncode,
        "operations": operations,
        "stdout": stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", help="Service name, for example ECS.")
    parser.add_argument("--operation", help="Operation name, for example ListFlavors.")
    parser.add_argument("--list-services", action="store_true", help="List known services from services_en.json.")
    parser.add_argument("--region", help="Optional region filter for endpoint data.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of services or operations returned.")
    parser.add_argument(
        "--allow-help-fallback",
        action="store_true",
        help="If local cache is incomplete, try `hcloud <service> --help` and parse visible operations.",
    )
    parser.add_argument(
        "--help-timeout",
        type=int,
        default=20,
        help="Timeout in seconds for service help fallback.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    return parser.parse_args()


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """Build the local metadata lookup result."""
    meta_repo = Path.home() / ".hcloud" / "metaRepo"
    services, service_index = collect_service_catalog(meta_repo)
    template_dirs = collect_template_dirs(meta_repo)

    if args.list_services:
        results = []
        for item in services[: args.limit]:
            name = item.get("Service", {}).get("Text", "")
            template_dir = template_dirs.get(normalize_token(name))
            results.append(summarize_service(item, template_dir))
        return {
            "meta_repo_exists": meta_repo.exists(),
            "service_count": len(services),
            "services": results,
        }

    if not args.service:
        raise ValueError("Provide --service or use --list-services.")

    normalized_service = normalize_token(args.service)
    service_item = service_index.get(normalized_service)
    template_dir = template_dirs.get(normalized_service)
    operations, operation_index = load_cached_operations(template_dir)

    result: dict[str, Any] = {
        "meta_repo_exists": meta_repo.exists(),
        "service_found": service_item is not None,
        "service": summarize_service(service_item, template_dir) if service_item else None,
        "cached_operations_count": len(operations),
        "cached_operations": operations[: args.limit],
        "endpoints": load_endpoints(template_dir, args.region),
    }

    if args.allow_help_fallback:
        service_name = service_item.get("Service", {}).get("Text", args.service) if service_item else args.service
        result["service_help_fallback"] = run_service_help(service_name, args.help_timeout)

    if args.operation:
        normalized_operation = normalize_token(args.operation)
        cached_operation = operation_index.get(normalized_operation)
        result["operation_found_in_cache_index"] = cached_operation is not None
        result["operation"] = cached_operation
        result["operation_detail"] = load_operation_detail(template_dir, args.operation)

    return result


def main() -> int:
    """Run the metadata lookup and print JSON output."""
    args = parse_args()
    result = {
        "success": True,
        "mode": "metadata_lookup",
        **build_result(args),
    }
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
