#!/usr/bin/env python3
"""Resolve a Huawei Cloud regional project ID using local context then IAM."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import credential_aliases
import hcloud_common

RemoteLookup = Callable[[str], dict[str, Any]]
DEFAULT_CONFIG_PATH = Path.home() / ".hcloud" / "config.json"


def _local_profile_project(config_path: Path, region: str) -> str | None:
    """Return a matching cached profile project ID without exposing credentials."""
    if not config_path.exists():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    profiles = payload.get("profiles")
    if not isinstance(profiles, list):
        return None
    current_name = payload.get("current")
    matching: list[Mapping[str, Any]] = [
        profile
        for profile in profiles
        if isinstance(profile, Mapping)
        and str(profile.get("region") or "").strip() == region
        and str(profile.get("projectId") or "").strip()
    ]
    matching.sort(key=lambda item: item.get("name") != current_name)
    if not matching:
        return None
    return str(matching[0]["projectId"]).strip()


def _remote_failure(result: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a safe-executor IAM failure into a stable project error."""
    error_type = str(result.get("error_type") or "").strip().upper()
    error_category = str(result.get("error_category") or "").strip().lower()
    error_code = str(result.get("error_code") or "").strip().upper()
    text = " ".join(
        str(result.get(key) or "")
        for key in ("error_type", "error_category", "error_code", "stdout", "stderr")
    ).lower()

    # A structured local-output failure takes precedence over words that may
    # merely appear in argparse usage text, such as ``--timeout TIMEOUT``.
    if error_type == "HCLOUD_OUTPUT_INVALID" or error_code == "HCLOUD_OUTPUT_INVALID":
        code, retryable = "HCLOUD_OUTPUT_INVALID", False
    elif error_type == "HCLOUD_UNAVAILABLE" or error_code == "HCLOUD_UNAVAILABLE":
        code, retryable = "HCLOUD_UNAVAILABLE", False
    elif (
        error_type in {"NETWORK_ERROR", "TIMEOUT"}
        or error_category == "network"
        or error_code in {"NETWORK_ERROR", "TIMEOUT"}
        or any(
            token in text
            for token in ("timed out", "network_error", "connection timeout")
        )
    ):
        code, retryable = "IAM_NETWORK_TIMEOUT", True
    elif any(token in text for token in ("credential", "authentication", "unauthorized")):
        code, retryable = "IAM_AUTH_FAILED", False
    elif any(token in text for token in ("permission", "forbidden", "accessdenied")):
        code, retryable = "IAM_PERMISSION_DENIED", False
    elif any(token in text for token in ("not found", "no such file", "hcloud_unavailable")):
        code, retryable = "HCLOUD_UNAVAILABLE", False
    else:
        code, retryable = "HCLOUD_OUTPUT_INVALID", False
    return {
        "success": False,
        "project_id": None,
        "source": None,
        "remote_lookup_performed": True,
        "error_code": code,
        "retryable": retryable,
    }


def _projects_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Extract IAM project records from common KooCLI response envelopes."""
    if isinstance(payload, dict):
        projects = payload.get("projects")
        if isinstance(projects, list):
            return [item for item in projects if isinstance(item, dict)]
        for key in ("data", "body", "result"):
            nested = _projects_from_payload(payload.get(key))
            if nested:
                return nested
    return []


def resolve_project_id(
    *,
    region: str,
    explicit_project_id: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    remote_lookup: RemoteLookup | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve one project ID with deterministic precedence and stable errors."""
    normalized_region = region.strip()
    if explicit_project_id and explicit_project_id.strip():
        return {
            "success": True,
            "project_id": explicit_project_id.strip(),
            "source": "explicit",
            "source_name": None,
            "region": normalized_region,
            "remote_lookup_performed": False,
        }

    env_project, env_name = credential_aliases.resolve_first_value(
        credential_aliases.PROJECT_ID_ENV_NAMES,
        environ,
    )
    if env_project:
        return {
            "success": True,
            "project_id": env_project,
            "source": "environment",
            "source_name": env_name,
            "region": normalized_region,
            "remote_lookup_performed": False,
        }

    cached_project = _local_profile_project(config_path, normalized_region)
    if cached_project:
        return {
            "success": True,
            "project_id": cached_project,
            "source": "hcloud_profile_cache",
            "source_name": str(config_path),
            "region": normalized_region,
            "remote_lookup_performed": False,
        }

    if remote_lookup is None:
        return {
            "success": False,
            "project_id": None,
            "source": None,
            "region": normalized_region,
            "remote_lookup_performed": False,
            "error_code": "PROJECT_ID_NOT_FOUND",
            "retryable": False,
        }

    result = remote_lookup(normalized_region)
    if not result.get("success"):
        return {**_remote_failure(result), "region": normalized_region}

    projects = _projects_from_payload(result.get("parsed_json"))
    matches = [
        project
        for project in projects
        if str(project.get("name") or "").strip() == normalized_region and str(project.get("id") or "").strip()
    ]
    unique = list(dict.fromkeys(str(project["id"]).strip() for project in matches))
    if len(unique) == 1:
        return {
            "success": True,
            "project_id": unique[0],
            "source": "iam_keystone_list_projects",
            "source_name": "IAM.KeystoneListProjects",
            "region": normalized_region,
            "remote_lookup_performed": True,
        }
    if len(unique) > 1:
        return {
            "success": False,
            "project_id": None,
            "source": None,
            "region": normalized_region,
            "remote_lookup_performed": True,
            "error_code": "PROJECT_ID_AMBIGUOUS",
            "retryable": False,
            "candidate_count": len(unique),
        }
    return {
        "success": False,
        "project_id": None,
        "source": None,
        "region": normalized_region,
        "remote_lookup_performed": True,
        "error_code": "PROJECT_ID_NOT_FOUND",
        "retryable": False,
        "candidate_count": 0,
    }


def default_remote_lookup(region: str, timeout: int = 30) -> dict[str, Any]:
    """Query IAM projects through the bundled safe KooCLI executor."""
    command = [
        *hcloud_common.bundled_script_command("hcloud_safe_exec.py"),
        "--service",
        "IAM",
        "--operation",
        "KeystoneListProjects",
        f"--arg=--name={region}",
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"success": False, "error_type": "HCLOUD_UNAVAILABLE"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error_type": "NETWORK_ERROR", "stderr": "timeout"}
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error_type": "HCLOUD_OUTPUT_INVALID",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    return (
        result
        if isinstance(result, dict)
        else {
            "success": False,
            "error_type": "HCLOUD_OUTPUT_INVALID",
        }
    )


def parse_args() -> argparse.Namespace:
    """Parse project resolution arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, help="Huawei Cloud region name.")
    parser.add_argument("--project-id", help="Explicit project ID override.")
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Resolve and print one regional project ID."""
    args = parse_args()
    remote_lookup: RemoteLookup | None = None
    if not args.local_only:

        def lookup(region: str) -> dict[str, Any]:
            """Run the IAM lookup with the caller-selected timeout."""
            return default_remote_lookup(region, args.timeout)

        remote_lookup = lookup
    result = resolve_project_id(
        region=args.region,
        explicit_project_id=args.project_id,
        config_path=args.config_path,
        remote_lookup=remote_lookup,
    )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
