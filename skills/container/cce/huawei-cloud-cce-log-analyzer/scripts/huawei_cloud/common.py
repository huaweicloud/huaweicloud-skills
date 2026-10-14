"""Credential and hcloud helpers for CCE log analysis."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Optional


_STANDARD_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
# Loose check: any UUID-like string (hex groups, dashes at fixed positions) that fails the
# standard UUID v4 pattern should be rejected at the input layer, not forwarded to the API.
_LOOSE_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
# Pattern for valid CCE cluster names: Kubernetes-style (alphanumeric, hyphens, dots)
_VALID_CLUSTER_NAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$")


def get_credentials(
    ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve explicit credentials before environment-variable fallback."""
    return (
        ak or os.getenv("HW_ACCESS_KEY") or os.getenv("HUAWEICLOUD_SDK_AK"),
        sk or os.getenv("HW_SECRET_KEY") or os.getenv("HUAWEICLOUD_SDK_SK"),
        project_id or os.getenv("HW_PROJECT_ID") or os.getenv("HUAWEICLOUD_SDK_PROJECT_ID"),
    )


def has_hcloud_profile() -> bool:
    """Return whether a usable local hcloud profile is present."""
    config_dir = os.environ.get("HCLOUD_CONFIG_DIR")
    candidates = [os.path.join(config_dir, "config.json")] if config_dir else []
    candidates.extend(
        [
            os.path.expanduser("~/.hcloud/config.json"),
            os.path.expanduser("~/.hcloud/config.yaml"),
            os.path.expanduser("~/.hcloud/config.yml"),
        ]
    )
    return any(os.path.isfile(path) and os.path.getsize(path) > 0 for path in candidates)


def resolve_hcloud_credentials(
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Resolve hcloud authentication: arguments, profile, then environment."""
    if ak or sk or project_id or security_token:
        return ak, sk, project_id, security_token
    if has_hcloud_profile():
        return None, None, None, None
    access_key, secret_key, resolved_project_id = get_credentials()
    return access_key, secret_key, resolved_project_id, os.getenv("HW_SECURITY_TOKEN")


def redact_command(command: list[str]) -> list[str]:
    """Redact credential values before returning a command to callers."""
    return [
        re.sub(r"(--cli-(?:access-key|secret-key|security-token)=).*", r"\1***", part)
        for part in command
    ]


def _redact_hcloud_output(text: str, command: list[str], limit: int = 2000) -> str:
    """Redact credentials if hcloud echoes command arguments in diagnostics."""
    redacted = text or ""
    for item in command:
        if item.startswith(("--cli-access-key=", "--cli-secret-key=", "--cli-security-token=")):
            secret = item.split("=", 1)[1]
            if secret:
                redacted = redacted.replace(secret, "***")
    return redacted[:limit]


def _parse_hcloud_output(output: str) -> Any:
    """Parse hcloud JSON while tolerating diagnostics appended after the payload."""
    candidate = output.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # LTS log content can contain literal backslashes (for example, regexes)
        # that hcloud emits without JSON escaping.
        candidate = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Some hcloud releases append terminal diagnostics after a valid JSON
            # response. Keep only the first JSON value in that case.
            value, _ = json.JSONDecoder().raw_decode(candidate)
            return value


def run_hcloud(command: list[str]) -> dict[str, Any]:
    """Run hcloud and parse its JSON response."""
    safe_command = redact_command(command)
    try:
        process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud not found in PATH", "command": safe_command}
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "error": "hcloud command timed out after 75 seconds",
            "command": safe_command,
            "returncode": None,
            "stdout": _redact_hcloud_output(exc.stdout or "", command) if isinstance(exc.stdout, str) else "",
            "stderr": _redact_hcloud_output(exc.stderr or "", command) if isinstance(exc.stderr, str) else "",
        }
    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()
    safe_stdout = _redact_hcloud_output(stdout, command)
    safe_stderr = _redact_hcloud_output(stderr, command)
    if process.returncode:
        diagnostic = safe_stderr or safe_stdout
        return {
            "success": False,
            "error": f"hcloud exited with code {process.returncode}: {diagnostic}" if diagnostic else f"hcloud exited with code {process.returncode}",
            "command": safe_command,
            "returncode": process.returncode,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "raw_error": diagnostic or None,
        }
    output = stdout or "{}"
    try:
        data = _parse_hcloud_output(output)
    except json.JSONDecodeError as error:
        diagnostic = safe_stderr or safe_stdout
        return {
            "success": False,
            "error": f"hcloud returned non-JSON output: {diagnostic}" if diagnostic else f"hcloud returned non-JSON output: {error}",
            "command": safe_command,
            "returncode": process.returncode,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "raw_error": diagnostic or None,
        }
    if isinstance(data, dict) and data.get("error_code"):
        return {
            "success": False,
            "error": f"{data['error_code']}: {data.get('error_msg', 'hcloud request failed')}",
            "command": safe_command,
            "returncode": process.returncode,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "raw_error": safe_stderr or safe_stdout or None,
        }
    return {"success": True, "data": data, "command": safe_command, "returncode": process.returncode}


def hcloud_command(
    service: str,
    operation: str,
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> list[str]:
    """Build an hcloud command with the shared authentication priority."""
    access_key, secret_key, resolved_project_id, resolved_security_token = resolve_hcloud_credentials(
        ak, sk, project_id, security_token
    )
    command = [
        "hcloud", service, operation, f"--cli-region={region}", "--cli-output=json",
        "--cli-connect-timeout=10", "--cli-read-timeout=60",
    ]
    if resolved_project_id:
        command.append(f"--cli-project-id={resolved_project_id}")
    if access_key:
        command.append(f"--cli-access-key={access_key}")
    if secret_key:
        command.append(f"--cli-secret-key={secret_key}")
    if resolved_security_token:
        command.append(f"--cli-security-token={resolved_security_token}")
    return command


def resolve_cce_cluster_id(
    region: str,
    value: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> dict[str, Any]:
    """Validate a cluster UUID or resolve one exact CCE cluster-name match."""
    # Input-layer format validation: reject obviously invalid cluster_id values
    # before making any API calls (CCE-LOG-001).
    raw = value or ""
    if not (_STANDARD_UUID_RE.fullmatch(raw) or _VALID_CLUSTER_NAME_RE.fullmatch(raw)):
        return {
            "success": False,
            "error": f"cluster_id '{value}' is not a valid UUID or CCE cluster name. "
            f"A valid UUID follows the pattern xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx; "
            f"a valid cluster name uses alphanumeric, hyphens, or dots.",
        }
    if _STANDARD_UUID_RE.fullmatch(raw):
        result = run_hcloud(
            hcloud_command("CCE", "ShowCluster", region, ak, sk, project_id, security_token)
            + [f"--cluster_id={value}"]
        )
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error', '')}",
                "cluster_id": value,
            }
        return {"success": True, "id": value, "resolved_from_name": False}
    # Input-layer UUID format validation: if the value looks like a UUID (dashes, hex groups)
    # but fails the RFC 4122 v4 pattern, reject it immediately without an API call.
    if _LOOSE_UUID_RE.fullmatch(value or ""):
        return {"success": False, "error": f"cluster_id '{value}' is not a valid UUID v4 format; provide a standard UUID or an exact cluster name"}
    # CCE ListClusters returns all items and does not accept limit or offset parameters.
    result = run_hcloud(hcloud_command("CCE", "ListClusters", region, ak, sk, project_id, security_token))
    if not result.get("success"):
        return {"success": False, "error": f"Unable to list CCE clusters for cluster_id resolution: {result.get('error', '')}"}
    items = ((result.get("data") or {}).get("items") or [])
    matches = [item for item in items if ((item.get("metadata") or {}).get("name") == value)]
    if len(matches) == 1:
        cluster_id = (matches[0].get("metadata") or {}).get("uid")
        if _STANDARD_UUID_RE.fullmatch(cluster_id or ""):
            verification = run_hcloud(
                hcloud_command("CCE", "ShowCluster", region, ak, sk, project_id, security_token)
                + [f"--cluster_id={cluster_id}"]
            )
            if not verification.get("success"):
                return {
                    "success": False,
                    "error": f"Unable to verify CCE cluster resolved from name '{value}': {verification.get('error', '')}",
                    "cluster_id": cluster_id,
                }
            return {"success": True, "id": cluster_id, "resolved_from_name": True}
    if len(matches) > 1:
        return {"success": False, "error": f"cluster_id '{value}' matched multiple CCE clusters; provide a standard UUID"}
    return {"success": False, "error": f"cluster_id must be a standard UUID. No CCE cluster named '{value}' was found"}
