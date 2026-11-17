"""Shared helpers for the huawei-cloud-sg-manage skill.

All cloud operations go through the local hcloud (KooCLI) CLI — this module
builds, runs, and parses hcloud VPC security-group commands. No SDK is used.

Failure contract: every cloud call either returns parsed data or raises
:class:`HcloudError`, which carries a machine-readable ``error_code`` and a
remediation ``hint``. Callers turn it into ``{"success": false, ...}`` — an
empty list is NEVER returned as a substitute for a failed call.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

DEFAULT_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Error contract
# ---------------------------------------------------------------------------

class HcloudError(RuntimeError):
    """A hcloud call failed; carries the structured fields callers report."""

    def __init__(
        self,
        message: str,
        error_code: str = "hcloud_error",
        hint: str = "",
        command: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.hint = hint
        self.command = list(command or [])

    def to_payload(self) -> Dict[str, Any]:
        """Return the JSON body reported to the caller (never leaks secrets)."""
        payload: Dict[str, Any] = {
            "success": False,
            "error": self.message,
            "error_code": self.error_code,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.command:
            payload["command"] = " ".join(redact_command(self.command))
        return payload


def error_payload(exc: BaseException) -> Dict[str, Any]:
    """Normalise any exception into the structured failure envelope."""
    if isinstance(exc, HcloudError):
        return exc.to_payload()
    return {
        "success": False,
        "error": str(exc),
        "error_code": "internal_error",
        "hint": "Unexpected failure — re-run with an explicit region/project_id, or check `hcloud VPC <Op>/v3 --cli-region=cn-north-4 --help`.",
    }


# ---------------------------------------------------------------------------
# Credentials — dual mode (AK/SK env vars OR local hcloud profile)
# ---------------------------------------------------------------------------

def _has_hcloud_profile() -> bool:
    """Return whether a local hcloud profile config exists."""
    config_dir = os.environ.get("HCLOUD_CONFIG_DIR")
    candidates = []
    if config_dir:
        candidates.append(os.path.join(config_dir, "config.json"))
    candidates.extend([
        os.path.expanduser("~/.hcloud/config.json"),
        os.path.expanduser("~/.hcloud/config.yaml"),
        os.path.expanduser("~/.hcloud/config.yml"),
    ])
    return any(os.path.isfile(p) and os.path.getsize(p) > 0 for p in candidates)


def _env_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Return (ak, sk) from standard Huawei Cloud env vars, or (None, None)."""
    ak = (
        os.environ.get("HUAWEI_ACCESS_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_AK")
        or os.environ.get("HW_ACCESS_KEY")
    )
    sk = (
        os.environ.get("HUAWEI_SECRET_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_SK")
        or os.environ.get("HW_SECRET_KEY")
    )
    return (ak, sk)


def _resolve_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Resolve credentials with priority: hcloud profile > env AK/SK.

    When a local hcloud profile exists it stays authoritative (hcloud uses it
    automatically); env AK/SK is only passed explicitly when no profile exists.
    """
    if _has_hcloud_profile():
        return None, None
    return _env_credentials()


def check_prerequisites(command: Optional[Iterable[str]] = None) -> None:
    """Fail fast (<2s, no network) when hcloud or credentials are missing."""
    if not shutil.which("hcloud"):
        raise HcloudError(
            "hcloud (KooCLI) is not installed or not on PATH",
            error_code="cli_missing",
            hint=(
                "Install KooCLI >= 7.2.2 (see references/cli-installation-guide.md), "
                "then re-run `hcloud version` to confirm."
            ),
            command=command,
        )
    if not _has_hcloud_profile():
        ak, sk = _env_credentials()
        if not (ak and sk):
            raise HcloudError(
                "No Huawei Cloud credentials found",
                error_code="credentials_missing",
                hint=(
                    "Configure a KooCLI profile (`hcloud configure init`) or export "
                    "HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY, then retry."
                ),
                command=command,
            )


def timeout_seconds() -> float:
    """HCLOUD_TIMEOUT (seconds, 1-300) — hard per-call timeout, default 30."""
    raw = os.environ.get("HCLOUD_TIMEOUT", "")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(DEFAULT_TIMEOUT)
    if value <= 0:
        return float(DEFAULT_TIMEOUT)
    return min(value, 300.0)


# ---------------------------------------------------------------------------
# hcloud command execution
# ---------------------------------------------------------------------------

def redact_command(command: Iterable[str]) -> List[str]:
    """Return a copy of the command with secret-bearing options redacted."""
    redacted: List[str] = []
    sensitive_prefixes = ("--cli-access-key=", "--cli-secret-key=", "--cli-security-token=")
    for item in command:
        if item.startswith(sensitive_prefixes):
            key = item.split("=", 1)[0]
            redacted.append(f"{key}=***")
        else:
            redacted.append(item)
    return redacted


def build_command(
    service: str,
    operation: str,
    region: str,
    params: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
    include_credentials: bool = True,
) -> List[str]:
    """Build the exact hcloud argv (single source of truth for docs and runtime)."""
    ak, sk = _resolve_credentials() if include_credentials else (None, None)
    command: List[str] = [service, operation, f"--cli-region={region}", "--cli-output=json"]
    if ak and sk:
        command.append(f"--cli-access-key={ak}")
        command.append(f"--cli-secret-key={sk}")
        token = (
            os.environ.get("HUAWEI_SECURITY_TOKEN")
            or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")
        )
        if token:
            command.append(f"--cli-security-token={token}")
    if project_id:
        command.append(f"--project_id={project_id}")
    for key, value in (params or {}).items():
        command.append(f"--{key}={value}")
    return ["hcloud"] + command


def _classify_failure(text: str) -> Tuple[str, str]:
    """Map a raw hcloud/API failure to (error_code, hint)."""
    lowered = text.lower()
    if "apigw.0301" in lowered or "incorrect iam authentication" in lowered or "401" in lowered:
        return (
            "auth_error",
            "AK/SK rejected or expired — re-run `hcloud configure list`, then "
            "`hcloud configure init` if the profile is stale.",
        )
    if "no permission" in lowered or "403" in lowered or "not authorized" in lowered:
        return (
            "permission_denied",
            "Grant vpc:securityGroups:* and vpc:securityGroupRules:* to this account "
            "(see references/iam-policies.md).",
        )
    if "project_id" in lowered and ("missing" in lowered or "required" in lowered or "获取项目 id 失败" in lowered):
        return (
            "project_id_missing",
            "The profile cannot resolve a project id — pass project_id=<id> / "
            "--project_id=<id> explicitly.",
        )
    if "[use_error]" in lowered:
        return (
            "cli_error",
            "KooCLI rejected the command (service/operation/parameter). Follow the "
            "operation spelled in SKILL.md, e.g. `hcloud VPC ListSecurityGroups/v3`.",
        )
    return ("api_error", "Check the region, the resource id, and the IAM policy; retry with --cli-region=cn-north-4.")


def run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run an hcloud command and return the parsed JSON result.

    Raises :class:`HcloudError` when the CLI is missing, credentials are
    missing, the call times out (``HCLOUD_TIMEOUT``, default 30s), the process
    fails, KooCLI rejects the command (``[USE_ERROR]`` with rc=0), or the API
    returns a business error envelope in the response body (Huawei Cloud
    reports business errors with rc=0, e.g.
    ``{"error_code": "SYS.0403", "error_msg": "..."}``).
    """
    command = build_command(service, operation, region, params, project_id)
    check_prerequisites(command)

    timeout = timeout_seconds()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise HcloudError(
            f"hcloud {service} {operation} timed out after {timeout:g}s",
            error_code="timeout",
            hint=(
                "Raise HCLOUD_TIMEOUT (e.g. HCLOUD_TIMEOUT=60) or check the "
                "network/proxy to the region endpoint and retry."
            ),
            command=command,
        )
    except FileNotFoundError:
        raise HcloudError(
            "hcloud (KooCLI) is not installed or not on PATH",
            error_code="cli_missing",
            hint="Install KooCLI >= 7.2.2 and confirm with `hcloud version`.",
            command=command,
        )

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()

    if proc.returncode != 0:
        detail = (stderr or stdout)[:500]
        code, hint = _classify_failure(detail)
        raise HcloudError(
            f"hcloud {service} {operation} failed (rc={proc.returncode}): {detail}",
            error_code=code,
            hint=hint,
            command=command,
        )
    # KooCLI exits 0 for command-level rejections ([USE_ERROR] on stderr) — the
    # request never reached the API, so this must not look like an empty result.
    if "[USE_ERROR]" in stderr or "[USE_ERROR]" in stdout:
        detail = (stderr or stdout)[:500]
        raise HcloudError(
            f"hcloud {service} {operation} rejected the command: {detail}",
            error_code="cli_error",
            hint=(
                "Verify the operation name and parameter names with "
                f"`hcloud {service} {operation} --cli-region={region} --help`."
            ),
            command=command,
        )
    if not stdout:
        if stderr:
            raise HcloudError(
                f"hcloud {service} {operation} returned no data: {stderr[:500]}",
                error_code="cli_error",
                hint="KooCLI printed no JSON body — check credentials, region and the operation name.",
                command=command,
            )
        # rc=0 with an empty body is normal for DELETE operations.
        return {}
    data = _parse_json(stdout, command)
    api_error = _extract_api_error(data)
    if api_error:
        code, message = api_error
        hint = "Check the resource id/region; for auth or policy errors see references/iam-policies.md."
        if code.startswith("SYS.0403") or "Unauthorized" in message:
            hint = "AK/SK rejected — refresh the KooCLI profile or env AK/SK."
        elif code.startswith("SYS.0404"):
            hint = "Resource not found — confirm the id belongs to this region and project."
        raise HcloudError(
            f"hcloud {service} {operation} API error: [{code}] {message}",
            error_code=code,
            hint=hint,
            command=command,
        )
    return data


def _extract_api_error(data: Any) -> Optional[Tuple[str, str]]:
    """Detect a Huawei Cloud API business error inside an rc=0 JSON response.

    KooCLI exits 0 even when the cloud API rejects the request; the error is
    carried in the response body. Supported envelopes:

    - ``{"error_code": "SYS.0403", "error_msg": "..."}``   (Huawei standard)
    - ``{"error": {"code": "...", "message": "..."}}``     (RFC 7807 style)
    - ``{"code": "...", "message": "..."}``                (flat fallback)

    Returns (code, message) when an error envelope is detected, else None.
    """
    if not isinstance(data, dict):
        return None
    code = data.get("error_code")
    msg = data.get("error_msg")
    if isinstance(code, str) and code and isinstance(msg, str) and msg:
        return (code, msg)
    err = data.get("error")
    if isinstance(err, dict):
        code = err.get("code") or err.get("error_code")
        msg = err.get("message") or err.get("error_msg")
        if isinstance(code, str) and code:
            return (code, str(msg) if msg is not None else "")
    code = data.get("code")
    msg = data.get("message")
    if isinstance(code, str) and code and isinstance(msg, str) and msg:
        return (code, msg)
    return None


def _parse_json(text: str, command: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Parse hcloud JSON output. Falls back to extracting the first JSON object."""
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {"data": data}
    except json.JSONDecodeError:
        # Some KooCLI outputs embed the JSON inside markdown fences or logging
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                return data if isinstance(data, dict) else {"data": data}
            except json.JSONDecodeError:
                pass
        raise HcloudError(
            f"Unable to parse hcloud output: {text[:300]}",
            error_code="parse_error",
            hint="Re-run with --cli-output=json; if it persists, upgrade KooCLI.",
            command=command,
        )


# ---------------------------------------------------------------------------
# Per-process result cache
# ---------------------------------------------------------------------------
# One dispatcher invocation can ask the same SG several times (diagnose reads
# the SG plus its rules, conflict/audit iterate every group). Cache the parsed
# lists so a single intent costs one hcloud call per resource, not one per
# analysis step. Failures are never cached.

_CACHE: Dict[Tuple[Any, ...], Any] = {}


def clear_cache() -> None:
    """Drop all cached hcloud results (used by tests and long-lived callers)."""
    _CACHE.clear()


def cache_size() -> int:
    return len(_CACHE)


# ---------------------------------------------------------------------------
# Security group data access
# ---------------------------------------------------------------------------

def _first_key(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def list_security_groups(
    region: str,
    project_id: Optional[str] = None,
    limit: int = 2000,
    name: Optional[str] = None,
    sg_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List security groups (v3 API). Returns a list of SG dicts."""
    key = ("list_security_groups", region, project_id, limit, name, sg_id)
    if key in _CACHE:
        return _CACHE[key]
    params: Dict[str, Any] = {}
    if limit:
        params["limit"] = limit
    if name:
        params["name.1"] = name
    if sg_id:
        params["id.1"] = sg_id
    data = run_hcloud("VPC", "ListSecurityGroups/v3", region, params, project_id)
    groups = _first_key(data, "security_groups")
    result = groups if isinstance(groups, list) else []
    _CACHE[key] = result
    return result


def list_security_group_rules(
    region: str,
    project_id: Optional[str] = None,
    security_group_id: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """List security group rules (v3 API). Optionally filtered by SG id."""
    key = ("list_security_group_rules", region, project_id, security_group_id, limit)
    if key in _CACHE:
        return _CACHE[key]
    params: Dict[str, Any] = {}
    if limit:
        params["limit"] = limit
    if security_group_id:
        params["security_group_id.1"] = security_group_id
    data = run_hcloud("VPC", "ListSecurityGroupRules/v3", region, params, project_id)
    items = _first_key(data, "security_group_rules")
    result = items if isinstance(items, list) else []
    _CACHE[key] = result
    return result


def get_security_group(
    region: str,
    security_group_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Show a single security group (v3 API)."""
    key = ("get_security_group", region, project_id, security_group_id)
    if key in _CACHE:
        return _CACHE[key]
    data = run_hcloud(
        "VPC", "ShowSecurityGroup/v3", region,
        {"security_group_id": security_group_id}, project_id,
    )
    sg = _first_key(data, "security_group")
    result = sg if isinstance(sg, dict) else data
    _CACHE[key] = result
    return result


def get_security_group_rule(
    region: str,
    security_group_rule_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Show a single security group rule (v2 API — id lookup)."""
    key = ("get_security_group_rule", region, project_id, security_group_rule_id)
    if key in _CACHE:
        return _CACHE[key]
    data = run_hcloud(
        "VPC", "ShowSecurityGroupRule/v2", region,
        {"security_group_rule_id": security_group_rule_id}, project_id,
    )
    detail = _first_key(data, "security_group_rule")
    result = detail if isinstance(detail, dict) else data
    _CACHE[key] = result
    return result