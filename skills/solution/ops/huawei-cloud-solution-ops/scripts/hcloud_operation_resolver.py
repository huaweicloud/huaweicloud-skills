#!/usr/bin/env python3
"""Resolve a KooCLI operation to an explicit API version using local evidence."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common
import hcloud_operation_evidence
import hcloud_output_policy

SYSTEM_PARAM_NAMES = {
    "debug",
    "dryrun",
    "help",
    "project_id",
    "projectid",
    "skeleton",
}
DEFAULT_VERSION_PATTERNS = (
    re.compile(r"默认使用(?:该API)?版本\s*(v[0-9][a-z0-9._-]*)", re.IGNORECASE),
    re.compile(r"default(?:\s+api)?\s+version[^v0-9]*(v[0-9][a-z0-9._-]*)", re.IGNORECASE),
)
RAW_ORIGIN_DETAIL_RE = re.compile(
    r"_origin_(?:cn|en)\.ya?ml$",
    re.IGNORECASE,
)


def normalize_version(value: str | None) -> str | None:
    """Return a normalized KooCLI API version token."""

    normalized = str(value or "").strip().lower().rstrip(".,;:。")
    if not normalized:
        return None
    return normalized if normalized.startswith("v") else f"v{normalized}"


def version_sort_key(version: str) -> tuple[int, ...]:
    """Return a numeric key suitable for deterministic version ordering."""

    parts = []
    for part in re.split(r"[._-]", version.lower().lstrip("v")):
        match = re.match(r"\d+", part)
        parts.append(int(match.group()) if match else -1)
    return tuple(parts)


def comparable_param_name(value: str) -> str:
    """Normalize a CLI parameter and collapse indexed/nested KooCLI fields."""

    normalized = hcloud_catalog.normalize_param_name(value)
    return re.split(r"[.]", normalized, maxsplit=1)[0]


def is_system_param(value: str) -> bool:
    """Return whether a parameter controls KooCLI rather than an API request."""

    normalized = comparable_param_name(value)
    return normalized.startswith("cli_") or normalized in SYSTEM_PARAM_NAMES


def provided_param_names_from_args(arguments: Iterable[str]) -> set[str]:
    """Extract API parameter names from raw hcloud argument tokens."""

    names: set[str] = set()
    for raw_argument in arguments:
        argument = str(raw_argument).strip()
        if not argument.startswith("--"):
            continue
        name = comparable_param_name(argument.split("=", 1)[0])
        if name and not is_system_param(name):
            names.add(name)
    return names


def parse_default_version_from_help(text: str) -> str | None:
    """Extract KooCLI's reported default API version from help output."""

    for pattern in DEFAULT_VERSION_PATTERNS:
        match = pattern.search(text)
        if match:
            return normalize_version(match.group(1))
    return None


def discover_hcloud_default_version(
    service: str,
    operation: str,
    timeout: int = 10,
) -> tuple[str | None, dict[str, Any]]:
    """Query local KooCLI help for a multi-version operation's default."""

    binary = shutil.which("hcloud")
    if not binary:
        return None, {"attempted": False, "reason": "hcloud_not_found"}
    command_env = dict(os.environ)
    if not command_env.get("USER"):
        command_env["USER"] = "hcloud"
    if not command_env.get("HOME"):
        command_env["HOME"] = "/tmp"
    try:
        completed = subprocess.run(
            [binary, service, operation, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=command_env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, {"attempted": True, "reason": "help_timeout"}

    default_version = parse_default_version_from_help(f"{completed.stdout}\n{completed.stderr}")
    return default_version, {
        "attempted": True,
        "return_code": completed.returncode,
        "default_version": default_version,
        "reason": "parsed_default" if default_version else "default_not_reported",
    }


def candidate_for_version(
    operation: dict[str, Any],
    version: str,
    provided_params: set[str],
) -> dict[str, Any]:
    """Return parameter compatibility evidence for one operation version."""

    detail = hcloud_catalog.operation_version_detail(operation, version)
    detail_cached = bool(detail.get("detail_cached"))
    detail_file = str(detail.get("detail_file") or "")
    explicit_completeness = detail.get("parameter_metadata_complete")
    parameter_metadata_complete = (
        explicit_completeness
        if isinstance(explicit_completeness, bool)
        else bool(detail_cached and not RAW_ORIGIN_DETAIL_RE.search(detail_file))
    )
    known_params = {
        comparable_param_name(name)
        for name in hcloud_catalog.operation_param_names(detail)
        if comparable_param_name(name)
    }
    required_params = {
        comparable_param_name(name)
        for name in hcloud_catalog.normalized_required_params(detail)
        if comparable_param_name(name)
    }
    unsupported_params = (
        sorted(provided_params - known_params)
        if parameter_metadata_complete
        else []
    )
    missing_required_params = sorted(required_params - provided_params)
    if unsupported_params:
        compatibility = "incompatible"
    elif parameter_metadata_complete:
        compatibility = "compatible"
    else:
        compatibility = "unknown"
    return {
        "version": version,
        "compatibility": compatibility,
        "detail_cached": detail_cached,
        "detail_file": detail.get("detail_file"),
        "parameter_metadata_complete": parameter_metadata_complete,
        "known_params": sorted(known_params),
        "unsupported_params": unsupported_params,
        "missing_required_params": missing_required_params,
    }


def request_contract(
    service: str,
    operation: dict[str, Any],
    version: str,
) -> dict[str, Any]:
    """Return bounded request-shape evidence for one resolved API version.

    KooCLI metadata is reliable for top-level path/query/body placement but can
    flatten nested bodies to strings. This contract exposes that boundary and
    points to optional SDK evidence instead of inventing dotted arguments.
    """

    detail = hcloud_catalog.operation_version_detail(operation, version)
    parameters: list[dict[str, Any]] = []
    parameter_indexes: dict[tuple[str, str], int] = {}
    for item in hcloud_catalog.parameter_items(detail):
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        position = str(item.get("position") or item.get("in") or "unknown")
        parameter = {
            "name": name,
            "required": item.get("required") is True,
            "position": position,
            "type": str(item.get("type") or "unknown"),
        }
        enum = item.get("enum")
        if isinstance(enum, list):
            parameter["enum"] = enum[:50]
        key = (comparable_param_name(name), position.lower())
        existing_index = parameter_indexes.get(key)
        if existing_index is None:
            parameter_indexes[key] = len(parameters)
            parameters.append(parameter)
            continue

        existing = parameters[existing_index]
        existing["required"] = bool(existing.get("required")) or parameter["required"]
        occurrences = int(existing.get("flattened_occurrences") or 1) + 1
        existing.update(
            {
                "flattened_occurrences": occurrences,
                "nested_metadata_flattened": True,
            }
        )
        existing.pop("enum", None)
        if existing.get("type") != parameter.get("type"):
            existing["type"] = "ambiguous"

    has_body = bool(detail.get("has_body_params")) or any(
        parameter["position"].lower() == "body" for parameter in parameters
    )
    operation_name = str(operation.get("name") or "")
    contract: dict[str, Any] = {
        "source": "generated_hcloud_catalog",
        "version": version,
        "method": detail.get("method"),
        "path": detail.get("path"),
        "parameters": parameters,
        "has_body_params": has_body,
        "body_shape_confidence": "top_level_only" if has_body else "not_applicable",
        "preferred_body_transport": "cli_json_input" if has_body else "cli_arguments",
        "nested_cli_arguments_safe_to_infer": not has_body,
    }
    if any(parameter.get("nested_metadata_flattened") for parameter in parameters):
        contract["flattened_parameter_roots_present"] = True
    if has_body:
        contract.update(
            {
                "warning": (
                    "KooCLI catalog metadata may flatten nested body objects. "
                    "Do not infer indexed or dotted nested arguments from this top-level contract."
                ),
                "sdk_evidence_command": (
                    "python3 scripts/hcloud_sdk_catalog.py "
                    f"--service={service} --operation={operation_name} "
                    "--schema-depth=3 --pretty"
                ),
                "next_actions": [
                    "Prefer --cli-jsonInput for complex request bodies.",
                    "Inspect hcloud operation help or the optional SDK request schema before constructing nested fields.",
                ],
            }
        )
    return contract


def preferred_candidate(
    candidates: list[dict[str, Any]],
    default_version: str | None,
) -> dict[str, Any] | None:
    """Choose a compatible candidate using the verified/default version first."""

    viable = [candidate for candidate in candidates if candidate["compatibility"] != "incompatible"]
    if not viable:
        return None
    normalized_default = normalize_version(default_version)
    for candidate in viable:
        if candidate["version"] == normalized_default:
            return candidate
    compatible = [candidate for candidate in viable if candidate["compatibility"] == "compatible"]
    pool = compatible or viable
    return max(pool, key=lambda candidate: version_sort_key(candidate["version"]))


def unresolved_result(
    service: str,
    requested_operation: str,
    base_operation: str,
    reason: str,
) -> dict[str, Any]:
    """Return a non-blocking passthrough result for missing catalog evidence."""

    return {
        "success": True,
        "resolved": False,
        "service": service,
        "requested_operation": requested_operation,
        "base_operation": base_operation,
        "resolved_operation": requested_operation,
        "selected_version": None,
        "confidence": "unresolved",
        "reason": reason,
        "evidence": [],
        "candidates": [],
        "read_only": None,
        "retryable": False,
        "warning": "No local version evidence was found; validate the operation with hcloud --help.",
    }


def resolve_operation_version(
    service: str,
    operation_name: str,
    provided_params: Iterable[str] = (),
    *,
    catalog: dict[str, Any] | None = None,
    verify_help: bool = False,
    help_timeout: int = 10,
    excluded_versions: Iterable[str] = (),
) -> dict[str, Any]:
    """Resolve an operation to ``Operation/vN`` from explicit and parameter evidence."""

    requested_operation = operation_name.strip()
    base_operation, explicit_version = hcloud_catalog.split_operation_version(requested_operation)
    explicit_version = normalize_version(explicit_version)
    normalized_params = {
        comparable_param_name(param)
        for param in provided_params
        if comparable_param_name(param) and not is_system_param(param)
    }
    catalog = catalog if catalog is not None else hcloud_catalog.load_catalog()
    catalog_service = hcloud_catalog.resolve_service(catalog, service)
    if not catalog_service:
        return unresolved_result(service, requested_operation, base_operation, "service_not_in_catalog")
    operation = hcloud_catalog.resolve_operation(catalog_service, base_operation)
    if not operation:
        return unresolved_result(service, requested_operation, base_operation, "operation_not_in_catalog")

    canonical_operation = str(operation.get("name") or base_operation)
    excluded = {normalize_version(version) for version in excluded_versions}
    versions = [
        version
        for version in hcloud_catalog.operation_versions(operation)
        if version not in excluded
    ]
    if not versions:
        return unresolved_result(service, requested_operation, canonical_operation, "no_version_candidates")

    help_evidence: dict[str, Any] | None = None
    reported_default = None
    if verify_help and len(versions) > 1:
        reported_default, help_evidence = discover_hcloud_default_version(
            hcloud_catalog.command_service_name(catalog_service, service),
            canonical_operation,
            timeout=help_timeout,
        )
    catalog_default = normalize_version(operation.get("selected_version"))
    default_version = reported_default if reported_default in versions else catalog_default
    candidates = [
        candidate_for_version(operation, version, normalized_params)
        for version in versions
    ]
    evidence = ["generated_hcloud_catalog", "per_version_operation_detail"]
    if help_evidence and help_evidence.get("default_version"):
        evidence.insert(0, "local_hcloud_help")

    if explicit_version:
        explicit_candidate = next(
            (candidate for candidate in candidates if candidate["version"] == explicit_version),
            None,
        )
        if explicit_candidate is None:
            corrected = preferred_candidate(candidates, default_version)
            corrected_operation = (
                f"{canonical_operation}/{corrected['version']}" if corrected else None
            )
            return {
                "success": False,
                "resolved": False,
                "service": service,
                "requested_operation": requested_operation,
                "base_operation": canonical_operation,
                "resolved_operation": None,
                "selected_version": None,
                "confidence": "explicit_version_unavailable",
                "reason": "explicit_version_not_available",
                "evidence": evidence,
                "candidates": candidates,
                "available_versions": versions,
                "corrected_operation": corrected_operation,
                "retryable": bool(corrected_operation),
                "read_only": hcloud_catalog.is_read_only(operation),
            }
        if explicit_candidate["compatibility"] == "incompatible":
            corrected = preferred_candidate(
                [candidate for candidate in candidates if candidate["version"] != explicit_version],
                default_version,
            )
            corrected_operation = (
                f"{canonical_operation}/{corrected['version']}" if corrected else None
            )
            return {
                "success": False,
                "resolved": False,
                "service": service,
                "requested_operation": requested_operation,
                "base_operation": canonical_operation,
                "resolved_operation": None,
                "selected_version": explicit_version,
                "confidence": "explicit_parameter_conflict",
                "reason": "provided_parameters_are_not_supported_by_explicit_version",
                "evidence": evidence,
                "candidates": candidates,
                "corrected_operation": corrected_operation,
                "retryable": bool(corrected_operation),
                "read_only": hcloud_catalog.is_read_only(operation),
            }
        selected = explicit_candidate
        confidence = (
            "explicit_verified"
            if explicit_candidate["compatibility"] == "compatible"
            else "explicit_unverified"
        )
        reason = "explicit_version"
    else:
        compatible = [
            candidate for candidate in candidates if candidate["compatibility"] == "compatible"
        ]
        if normalized_params and len(compatible) == 1:
            selected = compatible[0]
            confidence = "exact_parameter_match"
            reason = "only_one_version_supports_all_provided_parameters"
        else:
            selected = preferred_candidate(candidates, default_version)
            if selected is None:
                return {
                    "success": False,
                    "resolved": False,
                    "service": service,
                    "requested_operation": requested_operation,
                    "base_operation": canonical_operation,
                    "resolved_operation": None,
                    "selected_version": None,
                    "confidence": "no_compatible_version",
                    "reason": "no_version_supports_all_provided_parameters",
                    "evidence": evidence,
                    "candidates": candidates,
                    "retryable": False,
                    "read_only": hcloud_catalog.is_read_only(operation),
                }
            if reported_default and selected["version"] == reported_default:
                confidence = "local_hcloud_default"
                reason = "multiple_versions_match; selected_local_hcloud_default"
            elif selected["version"] == catalog_default:
                confidence = "catalog_default"
                reason = "multiple_versions_match; selected_catalog_default"
            else:
                confidence = "best_available"
                reason = "selected_highest_compatible_version"

    selected_version = selected["version"]
    resolved_operation = f"{canonical_operation}/{selected_version}"
    result = {
        "success": True,
        "resolved": True,
        "service": service,
        "requested_operation": requested_operation,
        "base_operation": canonical_operation,
        "resolved_operation": resolved_operation,
        "selected_version": selected_version,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
        "provided_params": sorted(normalized_params),
        "candidates": candidates,
        "metadata_default_version": catalog_default,
        "read_only": hcloud_catalog.is_read_only(operation),
        "retryable": False,
        "request_contract": request_contract(
            hcloud_catalog.command_service_name(catalog_service, service),
            operation,
            selected_version,
        ),
    }
    result.update(
        hcloud_operation_evidence.operation_evidence_fields(
            service,
            canonical_operation,
        )
    )
    if help_evidence:
        result["hcloud_help"] = help_evidence
    return result


def parse_key_value_params(values: Iterable[str]) -> tuple[list[str], list[str]]:
    """Return provided parameter names and CLI argument tokens."""

    names: list[str] = []
    arguments: list[str] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected NAME=VALUE for --param: {value}")
        name, raw_value = value.split("=", 1)
        name = name.strip().lstrip("-")
        if not name or not raw_value:
            raise ValueError(f"Expected non-empty NAME=VALUE for --param: {value}")
        names.append(name)
        arguments.append(f"--{name}={raw_value}")
    return names, arguments


def execution_command(
    service: str,
    operation: str,
    param_arguments: list[str],
    raw_arguments: list[str],
    *,
    read_only: bool | None,
) -> tuple[list[str], list[str] | None, dict[str, Any]]:
    """Return the preferred command and an optional direct-hcloud alternative."""

    direct_command = [
        "hcloud",
        service,
        operation,
        *param_arguments,
        *raw_arguments,
    ]
    provided_params = provided_param_names_from_args(
        [*param_arguments, *raw_arguments]
    )
    policy = hcloud_output_policy.resolve_output_policy(
        service,
        operation,
        requested_mode="auto",
        provided_params=provided_params,
        allow_large_output=False,
    )
    if read_only is not True or not policy.get("high_volume"):
        return direct_command, None, policy

    operation_arguments = [*param_arguments, *raw_arguments]
    if not any(
        hcloud_catalog.normalize_param_name(argument.split("=", 1)[0])
        == "cli_output"
        for argument in operation_arguments
    ):
        operation_arguments.append("--cli-output=json")
    safe_command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        service,
        "--operation",
        operation,
        *[f"--arg={argument}" for argument in operation_arguments],
        "--expect-json",
        "--output-mode=auto",
    ]
    return safe_command, direct_command, policy


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Huawei Cloud KooCLI service.")
    parser.add_argument("--operation", required=True, help="Base or versioned KooCLI operation.")
    parser.add_argument("--param", action="append", default=[], help="API parameter as NAME=VALUE.")
    parser.add_argument("--arg", action="append", default=[], help="Raw hcloud argument such as --cli-region=cn-north-4.")
    parser.add_argument("--catalog-path", type=Path, help="Optional generated catalog index/full file.")
    parser.add_argument("--verify-help", action="store_true", help="Ask local hcloud help to confirm the default version.")
    parser.add_argument("--help-timeout", type=int, default=10, help="Timeout for local hcloud help.")
    parser.add_argument(
        "--emit-command",
        action="store_true",
        help="Print the preferred resolved command; high-volume reads use hcloud_safe_exec.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.help_timeout < 1:
        parser.error("--help-timeout must be greater than 0.")
    return args


def main() -> int:
    """Resolve one operation and emit structured evidence or a direct command."""

    args = parse_args()
    try:
        param_names, param_arguments = parse_key_value_params(args.param)
        raw_param_names = provided_param_names_from_args(args.arg)
        catalog = hcloud_catalog.load_catalog(args.catalog_path) if args.catalog_path else None
        result = resolve_operation_version(
            args.service,
            args.operation,
            [*param_names, *raw_param_names],
            catalog=catalog,
            verify_help=args.verify_help,
            help_timeout=args.help_timeout,
        )
        command_service = args.service
        if catalog is None:
            catalog = hcloud_catalog.load_catalog()
        catalog_service = hcloud_catalog.resolve_service(catalog, args.service)
        if catalog_service:
            command_service = hcloud_catalog.command_service_name(catalog_service, args.service)
        if result.get("success"):
            command, direct_command, output_policy = execution_command(
                command_service,
                str(result["resolved_operation"]),
                param_arguments,
                args.arg,
                read_only=result.get("read_only"),
            )
            known_secrets = hcloud_common.collect_inline_secrets(command)
            result["command"] = hcloud_common.redact_command(command, known_secrets)
            result["command_shell"] = shlex.join(result["command"])
            if output_policy.get("high_volume"):
                result["output_policy"] = output_policy
            if direct_command is not None:
                result["direct_hcloud_command"] = hcloud_common.redact_command(
                    direct_command,
                    known_secrets,
                )
        elif result.get("corrected_operation"):
            corrected_command, direct_command, output_policy = execution_command(
                command_service,
                str(result["corrected_operation"]),
                param_arguments,
                args.arg,
                read_only=result.get("read_only"),
            )
            known_secrets = hcloud_common.collect_inline_secrets(corrected_command)
            result["corrected_command"] = hcloud_common.redact_command(
                corrected_command,
                known_secrets,
            )
            result["corrected_command_shell"] = shlex.join(result["corrected_command"])
            if output_policy.get("high_volume"):
                result["output_policy"] = output_policy
            if direct_command is not None:
                result["direct_hcloud_command"] = hcloud_common.redact_command(
                    direct_command,
                    known_secrets,
                )
    except ValueError as exc:
        result = {"success": False, "error": str(exc), "retryable": False}

    if args.emit_command:
        command_shell = result.get("command_shell") or result.get("corrected_command_shell")
        if command_shell:
            print(command_shell)
        else:
            hcloud_common.emit_json(result, pretty=args.pretty)
    else:
        hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
