#!/usr/bin/env python3
"""Shared helpers for Huawei Cloud CLI skill scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
REFERENCES_DIR = ROOT / "references"
REGISTRY_PATH = REFERENCES_DIR / "service-registry.json"

SECRET_HINTS = (
    "authorization",
    "api-key",
    "api_key",
    "apikey",
    "client-secret",
    "client_secret",
    "clientsecret",
    "access-key",
    "accesskey",
    "secret-key",
    "secretaccesskey",
    "security-token",
    "securitytoken",
    "x-auth-token",
    "auth-token",
    "access-token",
    "access_token",
    "accesstoken",
    "auth_token",
    "bearer-token",
    "bearer_token",
    "refresh-token",
    "refresh_token",
    "session-token",
    "session_token",
    "credential",
    "credentials",
    "password",
    "passwd",
    "adminpass",
    "private-key",
    "private_key",
    "privatekey",
    "user-data",
    "user_data",
    "userdata",
)
SECRET_EXACT_NAMES = {"ak", "sk"}
OBSUTIL_SECRET_ARG_NAMES = {"-i", "-k", "-t", "-token"}
MIN_REDACT_SECRET_LENGTH = 8
REDACTION_MARKER = "***"
PUBLIC_RESULT_CONTRACT = "huaweicloud_skill_public_result_v1"
PUBLIC_OUTCOME_STATUSES = (
    "planned",
    "succeeded",
    "partially_succeeded",
    "failed",
    "outcome_unknown",
)
PUBLIC_RECEIPT_RESERVED_FIELDS = {
    "result_contract",
    "success",
    "mode",
    "outcome_status",
    "result_file",
}
INLINE_SECRET_ASSIGNMENT_RE = re.compile(r"(?P<key>--?[A-Za-z0-9_.:-]+)(?P<sep>=)(?P<quote>['\"]?)(?P<value>[^\s'\"`,}\]]+)(?P=quote)")
JSON_SECRET_FIELD_RE = re.compile(
    r"(?P<prefix>(?P<key_quote>['\"])(?P<key>[^'\"]+)(?P=key_quote)\s*:\s*)"
    r"(?P<value_quote>['\"])(?P<value>.*?)(?P=value_quote)"
)
COMMAND_KEYS = {
    "command",
    "safe_exec",
    "hcloud",
    "dryrun",
    "dryrun_or_plan",
    "submit",
}


def script_path(name: str) -> Path:
    """Return an absolute path to a bundled script."""
    return SCRIPTS_DIR / name


def safe_exec_command_prefix() -> list[str]:
    """Return a cross-platform command prefix for the bundled safe executor."""
    return bundled_script_command("hcloud_safe_exec.py")


def bundled_script_command(name: str) -> list[str]:
    """Return a cross-platform Python command for a bundled script.

    ``sys.executable`` keeps generated planner commands inside the agent's
    active runtime. This avoids assuming a POSIX-only ``python3`` executable
    when the skill is installed on Windows.
    """
    python_executable = sys.executable or ("python.exe" if sys.platform == "win32" else "python3")
    return [python_executable, str(script_path(name))]


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a UTF-8 file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Return the curated service registry."""
    return load_json(path)


def emit_json(value: Any, pretty: bool = False) -> None:
    """Print a JSON value using the repository's standard formatting."""
    if pretty:
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(value, ensure_ascii=False))


def write_json_artifact(path: Path, value: Any, pretty: bool = False) -> dict[str, Any]:
    """Atomically persist JSON with private permissions and return a file receipt."""
    destination = path.expanduser().absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n"
    encoded = text.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(destination)
        destination.chmod(0o600)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise
    return {
        "path": str(destination),
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "permissions": "0600",
    }


def result_outcome_status(
    result: dict[str, Any],
    *,
    default_mode: str | None = None,
) -> str:
    """Return a stable high-level outcome for a public script result."""
    declared = result.get("outcome_status")
    if isinstance(declared, str) and declared.strip():
        normalized = declared.strip().lower()
        return normalized if normalized in PUBLIC_OUTCOME_STATUSES else "outcome_unknown"
    if not result.get("success", False):
        return "failed"
    if result.get("mode", default_mode) == "plan":
        return "planned"
    return "succeeded"


def build_public_result_receipt(
    result: dict[str, Any],
    artifact: dict[str, Any],
    *,
    default_mode: str | None = None,
    receipt_fields: tuple[str, ...] = (),
    receipt_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact public receipt without copying the full result payload."""
    receipt: dict[str, Any] = {
        "result_contract": PUBLIC_RESULT_CONTRACT,
        "success": bool(result.get("success", False)),
        "mode": result.get("mode", default_mode or "unknown"),
        "outcome_status": result_outcome_status(result, default_mode=default_mode),
        "result_file": artifact,
    }
    for key in ("service", "operation", *receipt_fields):
        value = result.get(key)
        if value is not None:
            receipt[key] = value
    for key, value in (receipt_extra or {}).items():
        if key in PUBLIC_RECEIPT_RESERVED_FIELDS:
            raise ValueError(f"receipt_extra cannot override reserved field: {key}")
        if value is not None:
            receipt[key] = value
    return receipt


def emit_public_result(
    result: dict[str, Any],
    *,
    output_file: Path | None = None,
    pretty: bool = False,
    default_mode: str | None = None,
    receipt_fields: tuple[str, ...] = (),
    receipt_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit a public CLI result, optionally storing the full JSON as an artifact.

    Without ``output_file`` this preserves the historical full-stdout behavior.
    With ``output_file`` it writes the unmodified result using private permissions
    and prints a compact, stable receipt so large responses do not fill the
    Agent's context.
    """
    if output_file is None:
        emit_json(result, pretty=pretty)
        return result

    artifact = write_json_artifact(output_file, result, pretty=pretty)
    receipt = build_public_result_receipt(
        result,
        artifact,
        default_mode=default_mode,
        receipt_fields=receipt_fields,
        receipt_extra=receipt_extra,
    )
    emit_json(receipt, pretty=pretty)
    return receipt


def collect_known_secrets(config_path: Path | None = None) -> set[str]:
    """Collect locally known hcloud secrets so they can be redacted from output."""
    target = config_path or (Path.home() / ".hcloud" / "config.json")
    if not target.exists():
        return set()

    try:
        config = load_json(target)
    except (OSError, json.JSONDecodeError):
        return set()

    secrets: set[str] = set()
    for profile in config.get("profiles", []):
        for key in ("accessKeyId", "secretAccessKey", "securityToken"):
            value = profile.get(key)
            if is_redactable_secret_value(value):
                secrets.add(str(value))
    return secrets


def is_redactable_secret_value(value: Any) -> bool:
    """Return True when a scalar value is safe to redact by exact text match."""
    if value is None:
        return False
    text = str(value).strip()
    if len(text) < MIN_REDACT_SECRET_LENGTH:
        return False
    if text.isdigit():
        return False
    return True


def looks_like_secret_arg(arg: str) -> bool:
    """Return True when an argument or JSON key suggests sensitive data."""
    lowered = arg.lower()
    compact = lowered.replace("_", "").replace("-", "")
    if lowered.split("=", 1)[0] in OBSUTIL_SECRET_ARG_NAMES:
        return True
    if compact in SECRET_EXACT_NAMES:
        return True
    return any(hint in lowered or hint.replace("_", "").replace("-", "") in compact for hint in SECRET_HINTS)


def is_redaction_marker(value: Any) -> bool:
    """Return True for an all-asterisk masked value of at least three stars."""
    return isinstance(value, str) and bool(re.fullmatch(r"\*{3,}", value.strip()))


def redaction_metadata() -> dict[str, Any]:
    """Describe the stable masking contract for Agent and caller interpretation."""
    return {
        "marker": REDACTION_MARKER,
        "accepted_marker_pattern": "three_or_more_asterisks",
        "masked_value_semantics": "present_but_hidden",
        "masked_value_means_missing": False,
    }


def looks_like_command_key(key: str | None) -> bool:
    """Return True when a JSON key usually stores command tokens."""
    if key is None:
        return False
    normalized = key.strip().replace("-", "_").lower()
    return normalized in COMMAND_KEYS or normalized.endswith("_command")


def collect_inline_secrets(args: list[str]) -> set[str]:
    """Collect secret values passed directly via CLI argument tokens."""
    secrets: set[str] = set()
    for index, arg in enumerate(args):
        if "=" in arg and looks_like_secret_arg(arg.split("=", 1)[0]):
            value = arg.split("=", 1)[1]
            if is_redactable_secret_value(value):
                secrets.add(value)
            continue
        if looks_like_secret_arg(arg.split("=", 1)[0]) and index + 1 < len(args):
            next_arg = args[index + 1]
            if next_arg and not next_arg.startswith("-") and is_redactable_secret_value(next_arg):
                secrets.add(next_arg)
    return secrets


def collect_json_secrets(value: Any) -> set[str]:
    """Collect sensitive scalar values from a JSON-like object."""
    secrets: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if looks_like_secret_arg(str(key)):
                if isinstance(child, str) and is_redactable_secret_value(child):
                    secrets.add(child)
                elif isinstance(child, (int, float, bool)) and is_redactable_secret_value(child):
                    secrets.add(str(child))
                continue
            secrets.update(collect_json_secrets(child))
    elif isinstance(value, list):
        for child in value:
            secrets.update(collect_json_secrets(child))
    return secrets


def coerce_output_text(value: str | bytes | None) -> str:
    """Normalize subprocess output to text for redaction and reporting."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def redact_inline_secret_assignments(text: str) -> str:
    """Redact obvious inline secret assignments in shell or JSON text."""

    def replace_cli_assignment(match: re.Match[str]) -> str:
        key = match.group("key")
        if not looks_like_secret_arg(key):
            return match.group(0)
        return f"{key}{match.group('sep')}{match.group('quote')}{REDACTION_MARKER}{match.group('quote')}"

    def replace_json_field(match: re.Match[str]) -> str:
        if not looks_like_secret_arg(match.group("key")):
            return match.group(0)
        return f"{match.group('prefix')}{match.group('value_quote')}{REDACTION_MARKER}{match.group('value_quote')}"

    redacted = INLINE_SECRET_ASSIGNMENT_RE.sub(replace_cli_assignment, text)
    return JSON_SECRET_FIELD_RE.sub(replace_json_field, redacted)


def redact_text(text: str | bytes | None, secrets: set[str]) -> str:
    """Replace exact secret values with a redaction marker."""
    redacted = coerce_output_text(text)
    safe_secrets = (item for item in secrets if is_redactable_secret_value(item))
    for secret in sorted(safe_secrets, key=len, reverse=True):
        redacted = re.sub(re.escape(secret), REDACTION_MARKER, redacted)
    return redact_inline_secret_assignments(redacted)


def redact_command(command: list[str], secrets: set[str]) -> list[str]:
    """Return a command list with sensitive argument values redacted."""
    redacted: list[str] = []
    redact_next = False
    for item in command:
        if redact_next:
            redacted.append(item if item.startswith("-") else REDACTION_MARKER)
            redact_next = False
            continue
        if "=" in item and looks_like_secret_arg(item.split("=", 1)[0]):
            key = item.split("=", 1)[0]
            redacted.append(f"{key}={REDACTION_MARKER}")
        elif looks_like_secret_arg(item.split("=", 1)[0]):
            redacted.append(item)
            redact_next = True
        else:
            redacted.append(redact_text(item, secrets))
    return redacted


def redact_json(value: Any, secrets: set[str], key: str | None = None) -> Any:
    """Recursively redact sensitive values in parsed JSON-like data."""
    if key is not None and looks_like_secret_arg(key):
        return REDACTION_MARKER
    if isinstance(value, dict):
        return {item_key: redact_json(child, secrets, str(item_key)) for item_key, child in value.items()}
    if isinstance(value, list):
        if looks_like_command_key(key) and all(isinstance(child, str) for child in value):
            command = [str(child) for child in value]
            return redact_command(command, secrets | collect_inline_secrets(command))
        return [redact_json(child, secrets) for child in value]
    if isinstance(value, str):
        return redact_text(value, secrets)
    return value


def stable_plan_token(value: Any) -> str:
    """Return a short stable token for confirming an exact generated plan."""
    serialized = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
