#!/usr/bin/env python3
"""Execute hcloud commands with structured JSON output and basic secret redaction."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_operation_resolver
import hcloud_output_policy
from hcloud_common import (
    coerce_output_text,
    collect_inline_secrets,
    collect_json_secrets,
    collect_known_secrets,
    emit_json,
    load_json,
    redact_command,
    redact_json,
    redact_text,
    redaction_metadata,
    safe_exec_command_prefix,
)

ERROR_TYPES = ("USE_ERROR", "NETWORK_ERROR", "CLI_ERROR", "OPENAPI_ERROR", "APIE_ERROR")
CLOUD_ERROR_CODE_KEYS = ("error_code", "errorCode", "code", "errCode")
CLOUD_ERROR_MESSAGE_KEYS = ("error_msg", "errorMsg", "message", "msg", "error_description", "reason")

COMMON_ERROR_CATEGORIES = (
    (
        "credential",
        (
            r"\binvalidaccesskeyid\b",
            r"\bsignaturedoesnotmatch\b",
            r"\binvalidcredential\b",
            r"\binvalidtoken\b",
            r"\bauthentication\b",
            r"\baccess key\b",
            r"\bak/sk\b",
            r"\bsignature\b",
        ),
        "Check AK/SK/security token, active profile, and whether the credentials belong to the target Huawei Cloud account or site.",
    ),
    (
        "permission",
        (
            r"\baccessdenied\b",
            r"\bforbidden\b",
            r"\bunauthorized\b",
            r"\bnot authorized\b",
            r"\bpermission\b",
            r"\biam\b",
        ),
        "Check IAM permissions, agency policy, project scope, and whether the service is enabled for this account.",
    ),
    (
        "quota",
        (
            r"\bquota\b",
            r"\binsufficient\b",
            r"\blimit exceeded\b",
            r"\btoo many\b",
        ),
        "Check service quota, resource limits, and current usage before retrying or requesting quota increase.",
    ),
    (
        "region_or_endpoint",
        (
            r"\bunsupported region\b",
            r"\binvalid region\b",
            r"\bregion\b",
            r"\bendpoint\b",
        ),
        "Check --cli-region, endpoint availability, and whether this service accepts the requested CLI region.",
    ),
    (
        "project",
        (
            r"\bproject[_ -]?id\b",
            r"\bproject\b",
        ),
        "Check project_id, region-project mapping, and whether the active profile has access to the target project.",
    ),
    (
        "parameter",
        (
            r"\binvalidparameter\b",
            r"\bmissingparameter\b",
            r"\brequired parameter\b",
            r"\bparameter\b",
            r"\bbad request\b",
            r"\binvalid request\b",
            r"\bunknown flag\b",
            r"\bunknown command\b",
        ),
        "Check operation help, required parameters, JSON body shape, and CLI argument names.",
    ),
    (
        "not_found",
        (
            r"\bnotfound\b",
            r"\bnot found\b",
            r"\bnosuch\b",
            r"\bdoes not exist\b",
        ),
        "Check resource ID/name, region, project, and whether the resource has already been deleted.",
    ),
    (
        "network",
        (
            r"\btimeout\b",
            r"\bconnection refused\b",
            r"\bno such host\b",
            r"\bi/o timeout\b",
            r"\btls handshake\b",
        ),
        "Check connectivity, proxy/DNS settings, and KooCLI timeout/retry configuration.",
    ),
)

ERROR_TYPE_CATEGORY = {
    "USE_ERROR": "parameter",
    "NETWORK_ERROR": "network",
    "CLI_ERROR": "cli_runtime",
    "OPENAPI_ERROR": "cloud_api",
    "APIE_ERROR": "metadata",
    "TIMEOUT": "network",
}
AMBIGUOUS_MUTATION_ERROR_TYPES = {"CLI_ERROR", "NETWORK_ERROR", "TIMEOUT"}
TRANSIENT_READ_ERROR_TYPES = {"CLI_ERROR", "NETWORK_ERROR", "TIMEOUT"}
KNOWN_FAILED_REQUEST_ERROR_TYPES = {
    "APIE_ERROR",
    "OPENAPI_ERROR",
    "OUTPUT_POLICY_REQUIRED",
    "USE_ERROR",
    "VERSION_RESOLUTION_ERROR",
}
VERSION_USAGE_ERROR_PATTERNS = (
    r"unsupported\s+(?:operation|parameter|version)",
    r"unknown\s+(?:operation|flag|command)",
    r"不支持.{0,12}(?:operation|参数|版本)",
    r"(?:operation|参数|版本).{0,12}不支持",
)
REFERENCES_DIR = Path(__file__).resolve().parents[1] / "references"
IAM_ACTIONS_PATH = REFERENCES_DIR / "iam-actions-catalog.json"


def normalize_bool_text(value: Any) -> Any:
    """Normalize KooCLI config booleans stored as strings."""
    if isinstance(value, str):
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return value


def collect_json_input_secrets(args: argparse.Namespace) -> set[str]:
    """Collect secrets embedded in JSON input text or files when parseable."""
    secrets: set[str] = set()
    try:
        if args.json_input_file:
            secrets.update(collect_json_secrets(load_json(Path(args.json_input_file))))
        if args.json_input_text:
            secrets.update(collect_json_secrets(json.loads(args.json_input_text)))
    except (OSError, json.JSONDecodeError):
        return secrets
    return secrets


def collect_json_input_param_names(args: argparse.Namespace) -> set[str]:
    """Collect normalized parameter names embedded in JSON input."""

    payloads: list[Any] = []
    try:
        if args.json_input_file:
            payloads.append(load_json(Path(args.json_input_file)))
        if args.json_input_text:
            payloads.append(json.loads(args.json_input_text))
    except (OSError, json.JSONDecodeError):
        return set()

    names: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = hcloud_catalog.normalize_param_name(str(key))
                if normalized:
                    names.add(normalized)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for payload in payloads:
        visit(payload)
    return names


def classify_error(stdout: str, stderr: str) -> str | None:
    """Extract the first known KooCLI error type from output."""
    combined = f"{stdout}\n{stderr}"
    for error_type in ERROR_TYPES:
        if f"[{error_type}]" in combined:
            return error_type
    return None


def advice_for_error(error_type: str | None) -> str | None:
    """Return a short next-step hint for a known error type."""
    if error_type == "USE_ERROR":
        return "Re-check the active profile, region, service, operation, and parameter names."
    if error_type == "NETWORK_ERROR":
        return "Check connectivity and consider increasing cli-connect-timeout, cli-read-timeout, and cli-retry-count."
    if error_type == "CLI_ERROR":
        return "KooCLI failed while processing the command. Check local KooCLI logs under ~/.hcloud/logs/ and verify the installed hcloud version."
    if error_type == "OPENAPI_ERROR":
        return "The cloud API rejected the request. Re-check the actual business parameters and service-side constraints."
    if error_type == "APIE_ERROR":
        return "Live metadata lookup failed. Fall back to local meta cache or curated references before guessing parameters."
    return None


def iter_dicts(value: Any) -> list[dict[str, Any]]:
    """Return all dictionaries found inside a JSON-like value."""
    if isinstance(value, dict):
        nested = [value]
        for child in value.values():
            nested.extend(iter_dicts(child))
        return nested
    if isinstance(value, list):
        nested = []
        for child in value:
            nested.extend(iter_dicts(child))
        return nested
    return []


def first_string_field(mapping: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty string value for any known key."""
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return None


def extract_cloud_error(parsed_json: Any, stdout: str, stderr: str) -> dict[str, str | None]:
    """Extract cloud error code and message from parsed JSON or text output."""
    for mapping in iter_dicts(parsed_json):
        has_error_key = any(key in mapping for key in ("error", "error_code", "errorCode", "errCode", "error_msg", "errorMsg"))
        if isinstance(mapping.get("error"), dict):
            nested = mapping["error"]
            code = first_string_field(nested, CLOUD_ERROR_CODE_KEYS)
            message = first_string_field(nested, CLOUD_ERROR_MESSAGE_KEYS)
            if code or message:
                return {"code": code, "message": message, "source": "parsed_json"}
        if not has_error_key:
            continue
        code = first_string_field(mapping, CLOUD_ERROR_CODE_KEYS)
        message = first_string_field(mapping, CLOUD_ERROR_MESSAGE_KEYS)
        if code or message:
            return {"code": code, "message": message, "source": "parsed_json"}

    combined = f"{stdout}\n{stderr}"
    bracket_match = re.search(
        r"error code\s+\[(?P<code>[^\]]+)\].*?error message\s+\[(?P<message>[^\]]+)\]",
        combined,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if bracket_match:
        return {
            "code": bracket_match.group("code").strip(),
            "message": bracket_match.group("message").strip(),
            "source": "text",
        }

    code_match = re.search(
        r'"(?:error_code|errorCode|errCode)"\s*:\s*"(?P<code>[^"]+)"',
        combined,
        flags=re.IGNORECASE,
    )
    message_match = re.search(
        r'"(?:error_msg|errorMsg|message|msg)"\s*:\s*"(?P<message>[^"\n]+)"',
        combined,
        flags=re.IGNORECASE,
    )
    if code_match or message_match:
        return {
            "code": code_match.group("code").strip() if code_match else None,
            "message": message_match.group("message").strip() if message_match else None,
            "source": "text",
        }
    return {"code": None, "message": None, "source": None}


def load_iam_actions_catalog(path: Path = IAM_ACTIONS_PATH) -> dict[str, Any]:
    """Return the local IAM action hint catalog when available."""
    try:
        value = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def iam_action_hint(
    service: str | None,
    operation: str | None,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return best-effort IAM action hints for a service operation."""
    if not service:
        return None
    catalog = catalog if catalog is not None else load_iam_actions_catalog()
    services = catalog.get("services") if isinstance(catalog.get("services"), dict) else {}
    service_key = str(service).upper()
    service_entry = services.get(service_key)
    if not isinstance(service_entry, dict):
        return None

    operation_key, _ = hcloud_catalog.split_operation_version(str(operation or "").strip())
    operations = service_entry.get("operations") if isinstance(service_entry.get("operations"), dict) else {}
    operation_entry = operations.get(operation_key)
    match = "operation"
    if not isinstance(operation_entry, dict):
        operation_entry = None
        match = "service_default"

    actions = []
    risk = None
    notes = None
    if operation_entry:
        actions = [str(item) for item in operation_entry.get("required_actions", []) if str(item).strip()]
        risk = operation_entry.get("risk")
        notes = operation_entry.get("notes")

    if not actions:
        actions_key = "default_change_actions" if risk in {"change", "destructive"} else "default_readonly_actions"
        actions = [str(item) for item in service_entry.get(actions_key, []) if str(item).strip()]

    if not actions:
        return None

    return {
        "source": "references/iam-actions-catalog.json",
        "service": service_key,
        "operation": operation_key or None,
        "match": match,
        "risk": risk or "unknown",
        "permission_scope": service_entry.get("permission_scope") or "unknown",
        "required_actions": actions,
        "notes": notes,
        "verify_exact_policy": True,
        "next_steps": [
            "Check allow and explicit-deny policies for the required action hints.",
            "Check region/project or enterprise-project scope, agency trust, service enablement, and organization-level SCP/custom deny rules.",
        ],
    }


def classify_common_error(
    error_type: str | None,
    stdout: str,
    stderr: str,
    parsed_json: Any,
    service: str | None = None,
    operation: str | None = None,
) -> dict[str, Any] | None:
    """Return a structured diagnosis for common hcloud configuration and API failures."""
    if not error_type and not stdout and not stderr and parsed_json is None:
        return None

    cloud_error = extract_cloud_error(parsed_json, stdout, stderr)
    combined = "\n".join(
        item
        for item in (
            error_type or "",
            cloud_error.get("code") or "",
            cloud_error.get("message") or "",
            stdout,
            stderr,
        )
        if item
    )

    signals: list[str] = []
    category = ERROR_TYPE_CATEGORY.get(error_type or "", "unknown")
    advice = advice_for_error(error_type)
    for candidate, patterns, candidate_advice in COMMON_ERROR_CATEGORIES:
        matched_patterns = [pattern for pattern in patterns if re.search(pattern, combined, flags=re.IGNORECASE)]
        if matched_patterns:
            category = candidate
            advice = candidate_advice
            signals.extend(matched_patterns[:3])
            break

    if error_type == "APIE_ERROR" and category == "metadata":
        advice = advice or "Live metadata lookup failed. Use local metadata cache, curated references, or official docs."
    if category == "unknown" and not cloud_error.get("code") and not cloud_error.get("message"):
        return None

    details = {
        "category": category,
        "error_type": error_type,
        "cloud_error_code": cloud_error.get("code"),
        "cloud_error_message": cloud_error.get("message"),
        "source": cloud_error.get("source") or ("error_type" if error_type else "text"),
        "signals": signals,
        "advice": advice,
    }
    if category == "permission":
        permission_hint = iam_action_hint(service, operation)
        if permission_hint:
            details["permission_hint"] = permission_hint
    return details


def operation_kind(version_resolution: dict[str, Any] | None) -> str:
    """Return the resolved operation effect without guessing from its name."""

    if not isinstance(version_resolution, dict):
        return "unknown"
    read_only = version_resolution.get("read_only")
    if read_only is True:
        return "read"
    if read_only is False:
        return "mutation"
    return "unknown"


def build_execution_semantics(
    result: dict[str, Any],
    version_resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Describe request certainty, retry safety, and required cloud readback.

    A mutation interrupted by a transport/runtime failure may already have
    reached Huawei Cloud. Such a request must be read back before retrying;
    this function never authorizes automatic mutation replay.
    """

    kind = operation_kind(version_resolution)
    success = bool(result.get("success"))
    error_type = str(result.get("error_type") or "") or None
    raw_details = result.get("error_details")
    details = raw_details if isinstance(raw_details, dict) else {}
    has_cloud_rejection = details.get("source") != "exception" and bool(
        details.get("cloud_error_code") or details.get("cloud_error_message")
    )

    if success:
        verification_required = kind == "mutation"
        return {
            "operation_kind": kind,
            "request_outcome": "succeeded",
            "resource_verification_required": verification_required,
            "retry_strategy": "not_needed",
            "completion_claim_allowed": kind == "read",
            "reason": (
                "mutation_request_succeeded_resource_state_unverified"
                if verification_required
                else "request_succeeded"
            ),
        }

    known_failed_request = (
        error_type in KNOWN_FAILED_REQUEST_ERROR_TYPES
        or has_cloud_rejection
        or details.get("category")
        in {
            "local_environment",
            "metadata",
            "operation_version",
            "output_policy",
        }
    )
    ambiguous_mutation = (
        kind in {"mutation", "unknown"}
        and not known_failed_request
        and (error_type in AMBIGUOUS_MUTATION_ERROR_TYPES or error_type is None)
    )
    if ambiguous_mutation:
        return {
            "operation_kind": kind,
            "request_outcome": "outcome_unknown",
            "resource_verification_required": True,
            "retry_strategy": "verify_before_retry",
            "completion_claim_allowed": False,
            "reason": "mutation_or_unknown_operation_interrupted_after_process_start",
        }

    retry_strategy = (
        "retry_allowed"
        if kind == "read" and error_type in TRANSIENT_READ_ERROR_TYPES
        else "correct_before_retry"
    )
    return {
        "operation_kind": kind,
        "request_outcome": "failed",
        "resource_verification_required": kind == "mutation",
        "retry_strategy": retry_strategy,
        "completion_claim_allowed": False,
        "reason": "request_failed_with_actionable_error_evidence",
    }


def trim_text(text: str, max_chars: int) -> tuple[str, bool]:
    """Trim text to a maximum length and report whether truncation happened."""
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def build_safe_exec_retry_command(
    args: argparse.Namespace,
    *,
    output_mode: str,
    extra_operation_args: list[str] | None = None,
) -> list[str]:
    """Rebuild this safe-exec invocation for a policy-guided retry."""

    command = safe_exec_command_prefix()
    if args.command_part:
        for part in args.command_part:
            command.append(f"--command-part={part}")
    else:
        command.extend(["--service", args.service, "--operation", args.operation])
    for raw_arg in [*args.arg, *(extra_operation_args or [])]:
        command.append(f"--arg={raw_arg}")
    if args.json_input_file:
        command.append(f"--json-input-file={args.json_input_file}")
    if args.cwd:
        command.append(f"--cwd={args.cwd}")
    command.extend(
        [
            f"--timeout={args.timeout}",
            f"--max-output-chars={args.max_output_chars}",
            f"--max-parsed-json-chars={args.max_parsed_json_chars}",
            f"--sample-items={args.sample_items}",
            f"--output-mode={output_mode}",
        ]
    )
    if args.expect_json:
        command.append("--expect-json")
    if args.result_file:
        command.append(f"--result-file={args.result_file}")
    if args.parsed_json_file:
        command.append(f"--parsed-json-file={args.parsed_json_file}")
    if args.raw_output_file:
        command.append(f"--raw-output-file={args.raw_output_file}")
    if args.skip_version_resolve:
        command.append("--skip-version-resolve")
    if args.pretty:
        command.append("--pretty")
    return command


def default_artifact_path(
    service: str | None,
    operation: str | None,
    *,
    suffix: str,
) -> Path:
    """Create a unique temporary artifact path for a large cloud response."""

    safe_service = re.sub(r"[^A-Za-z0-9]+", "-", str(service or "hcloud")).strip("-")
    safe_operation = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        hcloud_output_policy.normalize_operation(operation) or "output",
    ).strip("-")
    handle = tempfile.NamedTemporaryFile(
        prefix=f"hcloud-{safe_service}-{safe_operation}-",
        suffix=suffix,
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def artifact_metadata(path: Path, kind: str) -> dict[str, Any]:
    """Return integrity and size metadata for one persisted redacted artifact."""

    payload = path.read_bytes()
    return {
        "kind": kind,
        "path": str(path),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "redacted": True,
    }


def write_json_artifact(path: Path, value: Any) -> dict[str, Any]:
    """Persist redacted JSON and return artifact metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return artifact_metadata(path, "parsed_json")


def write_text_artifact(path: Path, value: str) -> dict[str, Any]:
    """Persist redacted command stdout and return artifact metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return artifact_metadata(path, "raw_stdout")


def select_emission_mode(result: dict[str, Any], policy: dict[str, Any]) -> str:
    """Select the final agent-facing mode after the response size is known."""

    effective_mode = str(policy.get("effective_mode") or "auto")
    if effective_mode != "auto":
        return effective_mode
    parsed_json = result.get("parsed_json")
    if parsed_json is None:
        return "summary" if result.get("stdout_truncated") else "full"
    serialized = json.dumps(
        parsed_json,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(serialized) > int(policy.get("max_parsed_json_chars", 12000)):
        return "summary"
    return "full"


def build_output_policy_error(
    args: argparse.Namespace,
    policy: dict[str, Any],
    known_secrets: set[str],
    started_at: float,
) -> dict[str, Any]:
    """Return a structured preflight failure with a safe retry command."""

    missing = list(policy.get("missing_required", []))
    if missing:
        additions = [f"--{name}=<required:{name}>" for name in missing]
        retry = build_safe_exec_retry_command(
            args,
            output_mode=str(policy.get("effective_mode") or "summary"),
            extra_operation_args=additions,
        )
        advice = "Supply the missing bounded query filters, then execute corrected_command_template."
        corrected_key = "corrected_command_template"
    else:
        retry = build_safe_exec_retry_command(args, output_mode="summary")
        advice = "Use the corrected summary command, or repeat the full request with --allow-large-output and an explicit artifact path."
        corrected_key = "corrected_command"

    redacted_retry = redact_command(retry, known_secrets)
    return {
        "success": False,
        "return_code": None,
        "duration_seconds": round(time.time() - started_at, 3),
        "service": args.service,
        "operation": args.operation,
        "resolved_operation": None,
        "command": [],
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "error_type": "OUTPUT_POLICY_REQUIRED",
        "error_details": {
            "category": "output_policy",
            "error_type": "OUTPUT_POLICY_REQUIRED",
            "cloud_error_code": None,
            "cloud_error_message": policy.get("blocked_reason"),
            "source": "local_output_policy",
            "signals": missing or [policy.get("risk_class")],
            "advice": advice,
        },
        "advice": advice,
        "parsed_json": None,
        "parsed_json_error": None,
        "output_policy": policy,
        corrected_key: redacted_retry,
        f"{corrected_key}_shell": shlex.join(redacted_retry),
        "attempts": [],
        "config_context": {
            "cwd": args.cwd,
            "timeout": args.timeout,
            "expect_json": args.expect_json,
            "used_temp_json_input": False,
        },
    }


def maybe_parse_json(stdout: str | bytes | None) -> tuple[Any | None, str | None]:
    """Try to parse stdout as JSON."""
    stdout = coerce_output_text(stdout)
    stripped = stdout.strip()
    if not stripped:
        return None, None
    try:
        return json.loads(stripped), None
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        for marker in ("{", "["):
            marker_index = stripped.find(marker)
            if marker_index >= 0:
                candidate = stripped[marker_index:]
                try:
                    parsed, _ = decoder.raw_decode(candidate)
                    return parsed, None
                except json.JSONDecodeError:
                    continue
        return None, str(exc)


def normalize_hcloud_args(
    raw_args: list[str],
    *,
    add_missing_prefix: bool = True,
) -> list[str]:
    """Normalize direct ``--arg`` values into hcloud option tokens.

    Internal callers already pass long options such as ``--limit=20``. Direct
    service/operation users may omit the leading dashes, so add them without
    changing existing long or short options. Generic command-part mode can
    contain positional tokens and therefore disables prefix insertion. Reject
    malformed tokens before version resolution and subprocess execution.
    """

    normalized: list[str] = []
    for raw in raw_args:
        if not raw or not raw.strip():
            raise ValueError("--arg values must not be empty")
        if raw != raw.strip() or any(control in raw for control in ("\x00", "\r", "\n")):
            raise ValueError("--arg values must be single tokens without surrounding whitespace")
        normalized.append(
            raw if raw.startswith("-") or not add_missing_prefix else f"--{raw}"
        )
    return normalized


def build_command(
    args: argparse.Namespace,
    temp_json_file: Path | None,
    operation: str | None = None,
) -> list[str]:
    """Build the final hcloud subprocess command."""
    binary = shutil.which("hcloud")
    if not binary:
        raise FileNotFoundError("hcloud binary not found in PATH.")

    if args.command_part:
        command = [binary] + args.command_part
    else:
        command = [binary, args.service, operation or args.operation]

    command.extend(args.arg)

    if args.json_input_file:
        command.append(f"--cli-jsonInput={args.json_input_file}")
    if temp_json_file is not None:
        command.append(f"--cli-jsonInput={temp_json_file}")

    return command


def execute_once(
    command: list[str],
    args: argparse.Namespace,
    known_secrets: set[str],
    operation_for_hint: str | None,
) -> dict[str, Any]:
    """Execute one hcloud attempt and return a redacted structured result."""

    started_at = time.time()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=args.cwd,
        env=build_hcloud_subprocess_env(),
        timeout=args.timeout,
        check=False,
    )
    duration_seconds = round(time.time() - started_at, 3)
    raw_stdout = completed.stdout
    raw_stderr = completed.stderr
    parsed_json = None
    parsed_json_error = None
    if args.expect_json:
        parsed_json, parsed_json_error = maybe_parse_json(raw_stdout)
        if parsed_json is not None:
            known_secrets.update(collect_json_secrets(parsed_json))

    redacted_stdout = redact_text(raw_stdout, known_secrets)
    redacted_stderr = redact_text(raw_stderr, known_secrets)
    stdout_trimmed, stdout_truncated = trim_text(redacted_stdout, args.max_output_chars)
    stderr_trimmed, stderr_truncated = trim_text(redacted_stderr, args.max_output_chars)
    error_type = classify_error(raw_stdout, raw_stderr)
    redacted_parsed_json = redact_json(parsed_json, known_secrets) if parsed_json is not None else None
    cloud_error = extract_cloud_error(redacted_parsed_json, redacted_stdout, redacted_stderr)
    has_cloud_error = bool(cloud_error.get("code") or cloud_error.get("message"))
    logical_success = completed.returncode == 0 and error_type is None and not has_cloud_error

    error_details = None
    if not logical_success:
        error_details = classify_common_error(
            error_type,
            redacted_stdout,
            redacted_stderr,
            redacted_parsed_json,
            args.service,
            operation_for_hint,
        )

    return {
        "success": logical_success,
        "return_code": completed.returncode,
        "duration_seconds": duration_seconds,
        "service": args.service,
        "operation": args.operation,
        "command": redact_command(command, known_secrets),
        "stdout": stdout_trimmed,
        "stderr": stderr_trimmed,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "error_type": error_type,
        "error_details": error_details,
        "advice": (error_details or {}).get("advice") or advice_for_error(error_type),
        "parsed_json": redacted_parsed_json,
        "parsed_json_error": parsed_json_error,
        "_raw_stdout": redacted_stdout,
        "config_context": {
            "cwd": args.cwd,
            "timeout": args.timeout,
            "expect_json": args.expect_json,
            "used_temp_json_input": False,
        },
    }


def is_version_usage_error(result: dict[str, Any]) -> bool:
    """Return whether a failed attempt is eligible for version correction."""

    if result.get("error_type") not in {"USE_ERROR", "APIE_ERROR"}:
        return False
    combined = "\n".join(
        str(value or "")
        for value in (
            result.get("stdout"),
            result.get("stderr"),
            (result.get("error_details") or {}).get("cloud_error_message"),
        )
    )
    return any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in VERSION_USAGE_ERROR_PATTERNS)


def attempt_summary(
    result: dict[str, Any],
    resolved_operation: str | None,
    attempt: int,
) -> dict[str, Any]:
    """Return a compact auditable record for one execution attempt."""

    return {
        "attempt": attempt,
        "resolved_operation": resolved_operation,
        "success": bool(result.get("success")),
        "return_code": result.get("return_code"),
        "command": result.get("command", []),
        "error_type": result.get("error_type"),
        "error_details": result.get("error_details"),
    }


def build_hcloud_subprocess_env(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an inherited environment KooCLI can use in a minimal sandbox.

    KooCLI resolves the current user's home directory through the ``USER``
    environment variable when CGO-backed user lookup is unavailable. Some
    non-login sandbox images omit both shell variables, so provide stable,
    non-secret defaults while preserving any runtime-projected credential home.
    """

    command_env = dict(os.environ if environ is None else environ)
    if not command_env.get("USER", "").strip():
        command_env["USER"] = "hcloud"
    if not command_env.get("HOME", "").strip():
        command_env["HOME"] = "/tmp"
    return command_env


def ensure_json_input_args(args: argparse.Namespace) -> None:
    """Validate JSON input arguments."""
    if args.json_input_file and args.json_input_text:
        raise ValueError("Use either --json-input-file or --json-input-text, not both.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", help="Huawei Cloud service name, for example ECS.")
    parser.add_argument("--operation", help="Huawei Cloud operation name, for example ListFlavors.")
    parser.add_argument(
        "--command-part",
        action="append",
        default=[],
        help="Generic hcloud command parts, for example --command-part=configure --command-part=show.",
    )
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help=(
            "An hcloud argument token. Service/operation mode adds a missing -- prefix; "
            "command-part mode preserves positional tokens."
        ),
    )
    parser.add_argument("--json-input-file", help="Existing JSON file path to pass via --cli-jsonInput.")
    parser.add_argument("--json-input-text", help="Inline JSON text to write to a temporary file for --cli-jsonInput.")
    parser.add_argument("--cwd", help="Working directory for the hcloud subprocess.")
    parser.add_argument("--timeout", type=int, default=120, help="Subprocess timeout in seconds.")
    parser.add_argument("--max-output-chars", type=int, default=20000, help="Maximum number of chars kept for stdout and stderr.")
    parser.add_argument(
        "--max-parsed-json-chars",
        type=int,
        default=12000,
        help="Maximum parsed JSON size emitted in auto mode before switching to a summary.",
    )
    parser.add_argument(
        "--sample-items",
        type=int,
        default=3,
        help="Maximum primary-array items included in a summary.",
    )
    parser.add_argument(
        "--output-mode",
        choices=hcloud_output_policy.OUTPUT_MODES,
        default="auto",
        help="Agent-facing output contract. Auto applies local operation policies.",
    )
    parser.add_argument(
        "--allow-large-output",
        action="store_true",
        help="Allow explicit full output for a locally classified high-volume operation.",
    )
    parser.add_argument("--expect-json", action="store_true", help="Attempt to parse stdout as JSON.")
    parser.add_argument("--result-file", help="Optional path to save the full structured result JSON.")
    parser.add_argument("--parsed-json-file", help="Optional path to save only parsed_json when available.")
    parser.add_argument(
        "--raw-output-file",
        help="Optional path to save complete redacted stdout for non-JSON or file-only operations.",
    )
    parser.add_argument(
        "--skip-version-resolve",
        action="store_true",
        help="Bypass catalog-backed API version resolution for compatibility or diagnostics.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    args = parser.parse_args()

    if not args.command_part and not (args.service and args.operation):
        parser.error("Provide either --command-part ... or both --service and --operation.")
    if args.command_part and (args.service or args.operation):
        parser.error("Do not mix --command-part with --service/--operation.")
    if args.max_output_chars < 1:
        parser.error("--max-output-chars must be greater than 0.")
    if args.max_parsed_json_chars < 1:
        parser.error("--max-parsed-json-chars must be greater than 0.")
    if args.sample_items < 0:
        parser.error("--sample-items must be 0 or greater.")
    try:
        args.arg = normalize_hcloud_args(
            args.arg,
            add_missing_prefix=not bool(args.command_part),
        )
    except ValueError as exc:
        parser.error(str(exc))

    return args


def finalize_output(
    result: dict[str, Any],
    args: argparse.Namespace,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Persist full artifacts and return the bounded agent-facing result."""

    full_result = copy.deepcopy(result)
    raw_stdout = str(full_result.pop("_raw_stdout", ""))
    selected_mode = select_emission_mode(full_result, policy) if full_result.get("success") else "error"
    final_policy = copy.deepcopy(policy)
    final_policy["selected_mode"] = selected_mode
    parsed_json = full_result.get("parsed_json")
    if parsed_json is not None:
        serialized = json.dumps(
            parsed_json,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        final_policy["parsed_json_chars"] = len(serialized)
    else:
        final_policy["parsed_json_chars"] = 0

    artifacts: list[dict[str, Any]] = []
    if args.parsed_json_file and parsed_json is not None:
        artifacts.append(write_json_artifact(Path(args.parsed_json_file), parsed_json))
    elif args.parsed_json_file and raw_stdout and selected_mode == "file-only" and full_result.get("success"):
        artifacts.append(write_text_artifact(Path(args.parsed_json_file), raw_stdout))
    if args.raw_output_file and raw_stdout:
        artifacts.append(write_text_artifact(Path(args.raw_output_file), raw_stdout))

    final_policy["full_payload_persisted"] = bool(artifacts or args.result_file)
    final_policy["artifact_required_for_full_payload"] = (
        selected_mode in {"summary", "file-only"} and not final_policy["full_payload_persisted"]
    )
    full_result["output_policy"] = final_policy
    if artifacts:
        full_result["artifacts"] = artifacts
    if args.result_file:
        result_path = Path(args.result_file)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(full_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result_path.chmod(0o600)
        result_artifact = artifact_metadata(result_path, "structured_result")
        artifacts.append(result_artifact)

    generated_artifact = final_policy.get("generated_artifact")
    if not full_result.get("success") and isinstance(generated_artifact, dict) and generated_artifact.get("path"):
        generated_path = Path(str(generated_artifact["path"]))
        if generated_path.exists() and generated_path.stat().st_size == 0:
            generated_path.unlink()

    emitted = copy.deepcopy(full_result)
    emitted["output_policy"] = final_policy
    if artifacts:
        emitted["artifacts"] = artifacts

    if full_result.get("success") and parsed_json is not None:
        emitted["stdout"] = ""
        emitted["stdout_suppressed"] = True
        emitted["stdout_suppressed_reason"] = "parsed_json_available"
        if selected_mode in {"summary", "file-only"}:
            emitted["parsed_json_summary"] = hcloud_output_policy.summarize_json(
                parsed_json,
                final_policy,
                include_sample=selected_mode == "summary",
            )
            emitted["parsed_json"] = None
            emitted["parsed_json_suppressed"] = True
    elif full_result.get("success") and selected_mode in {"summary", "file-only"}:
        emitted["stdout_summary"] = {
            "chars": len(raw_stdout),
            "content_suppressed": True,
        }
        emitted["stdout"] = ""
        emitted["stdout_suppressed"] = True
        emitted["stdout_suppressed_reason"] = "output_policy"

    return emitted


def main() -> int:
    """Run hcloud and print a structured execution result."""
    args = parse_args()
    ensure_json_input_args(args)

    temp_json_file: Path | None = None
    if args.json_input_text:
        temp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        temp.write(args.json_input_text)
        temp.flush()
        temp.close()
        temp_json_file = Path(temp.name)

    known_secrets = collect_known_secrets()
    known_secrets.update(collect_inline_secrets(args.arg + args.command_part))
    known_secrets.update(collect_json_input_secrets(args))

    started_at = time.time()
    result: dict[str, Any] | None = None
    version_resolution: dict[str, Any] | None = None
    resolved_operation = args.operation
    provided_params = hcloud_operation_resolver.provided_param_names_from_args(args.arg)
    output_policy_params = provided_params | collect_json_input_param_names(args)
    output_policy = hcloud_output_policy.resolve_output_policy(
        args.service,
        args.operation,
        requested_mode=args.output_mode,
        provided_params=output_policy_params,
        allow_large_output=args.allow_large_output,
        max_parsed_json_chars=args.max_parsed_json_chars,
        sample_items=args.sample_items,
    )
    default_limit = output_policy.get("default_limit")
    if (
        isinstance(default_limit, dict)
        and output_policy.get("effective_mode") == "summary"
        and str(default_limit.get("param")) not in provided_params
    ):
        limit_param = str(default_limit["param"])
        limit_value = int(default_limit["value"])
        args.arg.append(f"--{limit_param}={limit_value}")
        provided_params.add(limit_param)
        output_policy_params.add(limit_param)
        output_policy["applied_default_args"] = [
            {
                "param": limit_param,
                "value": limit_value,
                "reason": "output_policy_default",
            }
        ]

    if output_policy.get("effective_mode") == "file-only" and not (args.result_file or args.parsed_json_file or args.raw_output_file):
        if args.expect_json:
            args.parsed_json_file = str(
                default_artifact_path(
                    args.service,
                    args.operation,
                    suffix=".json",
                )
            )
            output_policy["generated_artifact"] = {
                "kind": "parsed_json",
                "path": args.parsed_json_file,
            }
        else:
            args.raw_output_file = str(
                default_artifact_path(
                    args.service,
                    args.operation,
                    suffix=".txt",
                )
            )
            output_policy["generated_artifact"] = {
                "kind": "raw_stdout",
                "path": args.raw_output_file,
            }

    if output_policy.get("blocked"):
        result = build_output_policy_error(
            args,
            output_policy,
            known_secrets,
            started_at,
        )
    try:
        if result is None and args.service and args.operation and not args.skip_version_resolve:
            version_resolution = hcloud_operation_resolver.resolve_operation_version(
                args.service,
                args.operation,
                provided_params,
            )
            if not version_resolution.get("success"):
                corrected_operation = version_resolution.get("corrected_operation")
                corrected_command = None
                if corrected_operation:
                    corrected_command = [
                        "hcloud",
                        args.service,
                        str(corrected_operation),
                        *args.arg,
                    ]
                result = {
                    "success": False,
                    "return_code": None,
                    "duration_seconds": round(time.time() - started_at, 3),
                    "service": args.service,
                    "operation": args.operation,
                    "resolved_operation": None,
                    "command": [],
                    "stdout": "",
                    "stderr": "",
                    "stdout_truncated": False,
                    "stderr_truncated": False,
                    "error_type": "VERSION_RESOLUTION_ERROR",
                    "error_details": {
                        "category": "operation_version",
                        "error_type": "VERSION_RESOLUTION_ERROR",
                        "cloud_error_code": None,
                        "cloud_error_message": version_resolution.get("reason"),
                        "source": "local_catalog",
                        "signals": [version_resolution.get("confidence")],
                        "advice": "Use corrected_operation/corrected_command or revise the supplied API parameters.",
                    },
                    "advice": "Use corrected_operation/corrected_command or revise the supplied API parameters.",
                    "parsed_json": None,
                    "parsed_json_error": None,
                    "version_resolution": version_resolution,
                    "corrected_operation": corrected_operation,
                    "corrected_command": redact_command(corrected_command or [], known_secrets),
                    "attempts": [],
                    "config_context": {
                        "cwd": args.cwd,
                        "timeout": args.timeout,
                        "expect_json": args.expect_json,
                        "used_temp_json_input": bool(temp_json_file),
                    },
                }
            else:
                resolved_operation = str(version_resolution.get("resolved_operation") or args.operation)

        if result is None:
            attempts: list[dict[str, Any]] = []
            base_operation, explicit_version = hcloud_catalog.split_operation_version(args.operation or "")
            current_resolution = version_resolution
            command = build_command(args, temp_json_file, resolved_operation)
            result = execute_once(command, args, known_secrets, base_operation or args.operation)
            attempts.append(attempt_summary(result, resolved_operation, 1))

            can_correct = (
                not result["success"]
                and current_resolution is not None
                and current_resolution.get("resolved")
                and current_resolution.get("read_only") is True
                and explicit_version is None
                and is_version_usage_error(result)
            )
            if can_correct:
                alternate_resolution = hcloud_operation_resolver.resolve_operation_version(
                    args.service,
                    base_operation,
                    provided_params,
                    excluded_versions=[str(current_resolution.get("selected_version") or "")],
                )
                alternate_operation = alternate_resolution.get("resolved_operation")
                if (
                    alternate_resolution.get("success")
                    and alternate_resolution.get("resolved")
                    and alternate_operation
                    and alternate_operation != resolved_operation
                ):
                    original_operation = resolved_operation
                    resolved_operation = str(alternate_operation)
                    alternate_command = build_command(args, temp_json_file, resolved_operation)
                    result = execute_once(
                        alternate_command,
                        args,
                        known_secrets,
                        base_operation or args.operation,
                    )
                    attempts.append(attempt_summary(result, resolved_operation, 2))
                    result["version_correction"] = {
                        "reason": "read_only_version_usage_error",
                        "from_operation": original_operation,
                        "to_operation": resolved_operation,
                        "resolution": alternate_resolution,
                    }
                    current_resolution = alternate_resolution

            result["duration_seconds"] = round(time.time() - started_at, 3)
            result["resolved_operation"] = resolved_operation
            result["attempts"] = attempts
            if current_resolution is not None:
                result["version_resolution"] = current_resolution
            result["config_context"]["used_temp_json_input"] = bool(temp_json_file)
            result["output_policy"] = output_policy
    except FileNotFoundError as exc:
        result = {
            "success": False,
            "return_code": None,
            "duration_seconds": round(time.time() - started_at, 3),
            "service": args.service,
            "operation": args.operation,
            "resolved_operation": resolved_operation,
            "command": [],
            "stdout": "",
            "stderr": str(exc),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "error_type": None,
            "error_details": {
                "category": "local_environment",
                "error_type": None,
                "cloud_error_code": None,
                "cloud_error_message": str(exc),
                "source": "exception",
                "signals": ["hcloud binary not found"],
                "advice": "Install KooCLI or make sure `hcloud` is available in PATH.",
            },
            "advice": "Install KooCLI or make sure `hcloud` is available in PATH.",
            "parsed_json": None,
            "parsed_json_error": None,
            "config_context": {
                "cwd": args.cwd,
                "timeout": args.timeout,
                "expect_json": args.expect_json,
                "used_temp_json_input": bool(temp_json_file),
            },
            "version_resolution": version_resolution,
            "attempts": [],
        }
    except subprocess.TimeoutExpired as exc:
        stdout_text = coerce_output_text(exc.stdout)
        stderr_text = coerce_output_text(exc.stderr)
        result = {
            "success": False,
            "return_code": None,
            "duration_seconds": round(time.time() - started_at, 3),
            "service": args.service,
            "operation": args.operation,
            "resolved_operation": resolved_operation,
            "command": redact_command(exc.cmd if isinstance(exc.cmd, list) else [], known_secrets),
            "stdout": redact_text(stdout_text, known_secrets),
            "stderr": redact_text(stderr_text, known_secrets),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "error_type": "TIMEOUT",
            "error_details": {
                "category": "network",
                "error_type": "TIMEOUT",
                "cloud_error_code": None,
                "cloud_error_message": "The command timed out.",
                "source": "exception",
                "signals": ["timeout"],
                "advice": "The command timed out. Consider increasing --timeout or KooCLI timeout arguments.",
            },
            "advice": "The command timed out. Consider increasing --timeout or KooCLI timeout arguments.",
            "parsed_json": None,
            "parsed_json_error": None,
            "config_context": {
                "cwd": args.cwd,
                "timeout": args.timeout,
                "expect_json": args.expect_json,
                "used_temp_json_input": bool(temp_json_file),
            },
            "version_resolution": version_resolution,
            "attempts": [],
        }
    finally:
        if temp_json_file and temp_json_file.exists():
            temp_json_file.unlink()

    assert result is not None
    result["execution_semantics"] = build_execution_semantics(
        result,
        version_resolution,
    )
    emitted_result = finalize_output(result, args, output_policy)
    emitted_result["redaction"] = redaction_metadata()
    emit_json(emitted_result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
