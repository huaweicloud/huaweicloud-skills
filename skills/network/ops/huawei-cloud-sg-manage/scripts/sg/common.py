"""Shared helpers for the huawei-cloud-sg-manage skill.

All cloud operations go through the local hcloud (KooCLI) CLI — this module
builds, runs, and parses hcloud VPC security-group commands. No SDK is used.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

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


def run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run an hcloud command and return the parsed JSON result.

    Raises RuntimeError (message with hcloud stderr) when the process fails,
    or when the API returns a business error envelope in the response body
    (Huawei Cloud reports business errors with rc=0, e.g.
    ``{"error_code": "SYS.0403", "error_msg": "..."}``).
    """
    if not shutil.which("hcloud"):
        raise RuntimeError("hcloud CLI is not installed or not found in PATH")

    ak, sk = _resolve_credentials()
    command: List[str] = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
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

    proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        # Some list operations fail with "missing project_id" when the profile
        # cannot resolve it — surface the raw error for the caller to retry with
        # an explicit project_id.
        raise RuntimeError(
            f"hcloud {service} {operation} failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:500]}"
        )
    stdout = proc.stdout.strip()
    if not stdout:
        # rc=0 with empty body: some DELETE operations return empty output —
        # treat as success with no payload.
        return {}
    data = _parse_json(stdout)
    api_error = _extract_api_error(data)
    if api_error:
        code, message = api_error
        raise RuntimeError(
            f"hcloud {service} {operation} API error: [{code}] {message}"
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


def _parse_json(text: str) -> Dict[str, Any]:
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
        raise RuntimeError(f"Unable to parse hcloud output: {text[:300]}")


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
    params: Dict[str, Any] = {}
    if limit:
        params["limit"] = limit
    if name:
        params["name.1"] = name
    if sg_id:
        params["id.1"] = sg_id
    data = run_hcloud("VPC", "ListSecurityGroups/v3", region, params, project_id)
    groups = _first_key(data, "security_groups")
    return groups if isinstance(groups, list) else []


def list_security_group_rules(
    region: str,
    project_id: Optional[str] = None,
    security_group_id: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """List security group rules (v3 API). Optionally filtered by SG id."""
    params: Dict[str, Any] = {}
    if limit:
        params["limit"] = limit
    if security_group_id:
        params["security_group_id.1"] = security_group_id
    data = run_hcloud("VPC", "ListSecurityGroupRules/v3", region, params, project_id)
    items = _first_key(data, "security_group_rules")
    return items if isinstance(items, list) else []


def get_security_group(
    region: str,
    security_group_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Show a single security group (v3 API)."""
    data = run_hcloud(
        "VPC", "ShowSecurityGroup/v3", region,
        {"security_group_id": security_group_id}, project_id,
    )
    sg = _first_key(data, "security_group")
    return sg if isinstance(sg, dict) else data


def get_security_group_rule(
    region: str,
    security_group_rule_id: str,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Show a single security group rule (v2 API — id lookup)."""
    data = run_hcloud(
        "VPC", "ShowSecurityGroupRule/v2", region,
        {"security_group_rule_id": security_group_rule_id}, project_id,
    )
    detail = _first_key(data, "security_group_rule")
    return detail if isinstance(detail, dict) else data