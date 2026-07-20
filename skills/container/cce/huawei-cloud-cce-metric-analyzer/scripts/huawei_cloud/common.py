"""Common Huawei Cloud helpers shared by service modules."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_PROJECT_ID_CACHE = {}

def _safe_delete_file(filepath: Optional[str]) -> None:
    if not filepath:
        return
    if os.path.exists(filepath):
        os.remove(filepath)

def _has_hcloud_profile() -> bool:
    """Return whether local hcloud profile configuration appears to exist."""
    config_dir = os.environ.get("HCLOUD_CONFIG_DIR")
    candidates = []
    if config_dir:
        candidates.append(os.path.join(config_dir, "config.json"))
    candidates.extend([
        os.path.expanduser("~/.hcloud/config.json"),
        os.path.expanduser("~/.hcloud/config.yaml"),
        os.path.expanduser("~/.hcloud/config.yml"),
    ])
    return any(os.path.isfile(path) and os.path.getsize(path) > 0 for path in candidates)


def _env_credentials() -> tuple:
    return (
        os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY"),
        os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY"),
        os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID"),
    )


def get_security_token(security_token: Optional[str] = None) -> Optional[str]:
    """Return an optional temporary security token for signed HTTP requests."""
    return (
        security_token
        or os.environ.get("HUAWEI_SECURITY_TOKEN")
        or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")
        or os.environ.get("HW_SECURITY_TOKEN")
    )


def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Return optional hcloud CLI credentials.

    Priority: explicit tool parameters > local hcloud profile > environment variables.
    When a local hcloud profile exists and AK/SK are not explicitly provided, do not
    pass environment credentials so the profile remains authoritative.
    """
    if ak or sk or project_id:
        return ak, sk, project_id
    if _has_hcloud_profile():
        return None, None, None
    return _env_credentials()


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def _redact_text(text: str, *secrets: Optional[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, _mask_secret(secret) or "")
    return redacted


def _parse_hcloud_json_output(output: str) -> tuple[Optional[Any], Optional[str]]:
    """Parse hcloud JSON output, allowing warning text before/after JSON."""
    text = (output or "").strip()
    if not text:
        return None, "empty output"
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
            return parsed, None
        except json.JSONDecodeError:
            continue
    return None, "no valid JSON object or array found"


def run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Optional[Dict[str, Any]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Run a Huawei Cloud KooCLI command and parse JSON output.

    The caller may pass explicit AK/SK, but the preferred path is the local
    hcloud profile. This keeps SDK dependencies out of read-only metric calls.
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    cmd = [
        "hcloud",
        service,
        operation,
        f"--cli-region={region}",
        "--cli-output=json",
        "--cli-connect-timeout=10",
        "--cli-read-timeout=60",
    ]
    if access_key:
        cmd.append(f"--cli-access-key={access_key}")
    if secret_key:
        cmd.append(f"--cli-secret-key={secret_key}")
    if proj_id:
        cmd.append(f"--cli-project-id={proj_id}")

    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd.append(f"--{key}={value}")

    safe_cmd = [
        re.sub(r"(--cli-(?:access|secret)-key=).*", r"\1***", part)
        for part in cmd
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud CLI not found in PATH", "command": safe_cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"hcloud command timed out after {timeout}s", "command": safe_cmd}

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        message = stderr or stdout or f"hcloud exited with code {proc.returncode}"
        message = _redact_text(message, access_key, secret_key)
        return {"success": False, "error": message, "command": safe_cmd, "returncode": proc.returncode}

    data, parse_error = _parse_hcloud_json_output(stdout)
    if parse_error:
        combined_output = "\n".join(item for item in [stdout, stderr] if item)
        return {
            "success": False,
            "error": f"hcloud returned non-JSON output: {parse_error}",
            "output": _redact_text(combined_output[:2000], access_key, secret_key),
            "command": safe_cmd,
            "returncode": proc.returncode,
        }

    return {"success": True, "data": data, "command": safe_cmd}


def hcloud_show_metric_data(
    region: str,
    namespace: str,
    metric_name: str,
    dim_0: str,
    start_time: int,
    end_time: int,
    period: int,
    filter_name: str = "average",
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query CES ShowMetricData via hcloud and normalize datapoints."""
    result = run_hcloud(
        "CES",
        "ShowMetricData",
        region,
        {
            "namespace": namespace,
            "metric_name": metric_name,
            "dim.0": dim_0,
            "from": start_time,
            "to": end_time,
            "period": period,
            "filter": filter_name,
            "project_id": project_id,
        },
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    datapoints = data.get("datapoints") or data.get("datapoint") or data.get("metric_data") or []
    return {"success": True, "datapoints": datapoints, "raw": data}

def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    """Get project ID for a specific region via hcloud IAM if not cached.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)

    Returns:
        Project ID string or None if not found
    """
    global _PROJECT_ID_CACHE

    # Check cache first
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]

    result = run_hcloud("IAM", "KeystoneListProjects", region, {"name": region}, ak=ak, sk=sk)
    if not result.get("success"):
        result = run_hcloud("IAM", "KeystoneListProjects", region, {}, ak=ak, sk=sk)
    if result.get("success"):
        projects = (result.get("data") or {}).get("projects") or []
        for project in projects:
            name = project.get("name")
            project_id = project.get("id")
            if name and project_id:
                _PROJECT_ID_CACHE[name] = project_id
        return _PROJECT_ID_CACHE.get(region)

    return None

def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Get signing credentials with automatic project_id lookup for region.

    AOM Prometheus range-query and Kubernetes certificate setup require AK/SK
    material and cannot sign requests with an encrypted local hcloud profile.
    Therefore this helper intentionally uses explicit params first, then
    environment variables. hcloud CLI calls should use get_credentials().

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional, will auto-fetch if not provided)

    Returns:
        Tuple of (access_key, secret_key, project_id)
    """
    env_ak, env_sk, env_project_id = _env_credentials()
    access_key = ak or env_ak
    secret_key = sk or env_sk
    proj_id = project_id or env_project_id

    # If no project_id provided, try to get it for the region
    if not proj_id and region and access_key and secret_key:
        proj_id = get_project_id_for_region(region, access_key, secret_key)

    return access_key, secret_key, proj_id
