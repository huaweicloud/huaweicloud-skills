#!/usr/bin/env python3
"""Inspect local hcloud context and print a structured JSON summary."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_sdk_catalog


def safe_bool_text(value: Any) -> Any:
    """Normalize boolean-like string values from KooCLI config."""
    if isinstance(value, str):
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return value


def summarize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted profile summary."""
    return {
        "name": profile.get("name"),
        "mode": profile.get("mode"),
        "region": profile.get("region"),
        "project_id": profile.get("projectId") or "",
        "domain_id": profile.get("domainId") or "",
        "connect_timeout": profile.get("connectTimeout"),
        "read_timeout": profile.get("readTimeout"),
        "retry_count": profile.get("retryCount"),
        "skip_secure_verify": safe_bool_text(profile.get("skipSecureVerify")),
        "has_access_key": bool(profile.get("accessKeyId")),
        "has_secret_key": bool(profile.get("secretAccessKey")),
        "has_security_token": bool(profile.get("securityToken")),
    }


def inspect_config(config_path: Path) -> dict[str, Any]:
    """Inspect ~/.hcloud/config.json without exposing secrets."""
    if not config_path.exists():
        return {"exists": False, "path": str(config_path)}

    try:
        config = hcloud_common.load_json(config_path)
    except Exception as exc:
        return {"exists": True, "path": str(config_path), "error": str(exc)}

    profiles = config.get("profiles", [])
    current_name = config.get("current")
    summarized_profiles = [summarize_profile(profile) for profile in profiles]
    current_profile = next(
        (profile for profile in summarized_profiles if profile.get("name") == current_name),
        None,
    )

    return {
        "exists": True,
        "path": str(config_path),
        "current_profile_name": current_name,
        "language": config.get("language"),
        "offline": safe_bool_text(config.get("offline")),
        "warning": safe_bool_text(config.get("warning")),
        "agree_privacy": safe_bool_text(config.get("agreePrivacy")),
        "auth_encrypt": safe_bool_text(config.get("authEncrypt")),
        "local_dea": config.get("localDea"),
        "profile_count": len(summarized_profiles),
        "profiles": summarized_profiles,
        "current_profile": current_profile,
    }


def inspect_meta_repo(meta_repo_path: Path, include_meta_files: bool) -> dict[str, Any]:
    """Inspect local meta cache availability and cached services."""
    result: dict[str, Any] = {
        "exists": meta_repo_path.exists(),
        "path": str(meta_repo_path),
    }
    if not meta_repo_path.exists():
        return result

    services_file = meta_repo_path / "services_en.json"
    result["services_file_exists"] = services_file.exists()
    if services_file.exists():
        services_data = hcloud_common.load_json(services_file)
        items = services_data.get("items", [])
        result["cached_service_count"] = len(items)
        result["services_update_time"] = services_data.get("updateTime")
    else:
        result["cached_service_count"] = 0
        result["services_update_time"] = None

    template_root = meta_repo_path / "template"
    template_services = sorted(path.name for path in template_root.iterdir() if path.is_dir()) if template_root.exists() else []
    result["template_services"] = template_services

    template_file_count = 0
    template_files: dict[str, list[str]] = {}
    for service_dir_name in template_services:
        service_dir = template_root / service_dir_name
        files = sorted(path.name for path in service_dir.iterdir() if path.is_file())
        template_file_count += len(files)
        if include_meta_files:
            template_files[service_dir_name] = files
    result["template_file_count"] = template_file_count
    if include_meta_files:
        result["template_files"] = template_files

    return result


def inspect_meta_origin(meta_origin_path: Path, include_meta_files: bool) -> dict[str, Any]:
    """Inspect downloaded offline metadata package storage."""
    result: dict[str, Any] = {
        "exists": meta_origin_path.exists(),
        "path": str(meta_origin_path),
    }
    if not meta_origin_path.exists():
        return result

    top_level_files = sorted(path.name for path in meta_origin_path.iterdir() if path.is_file())
    top_level_dirs = sorted(path.name for path in meta_origin_path.iterdir() if path.is_dir())

    file_count = 0
    dir_count = 0
    for path in meta_origin_path.rglob("*"):
        if path.is_file():
            file_count += 1
        elif path.is_dir():
            dir_count += 1

    result["file_count"] = file_count
    result["dir_count"] = dir_count
    if include_meta_files:
        result["top_level_files"] = top_level_files
        result["top_level_dirs"] = top_level_dirs

    return result


def inspect_hcloud_binary() -> dict[str, Any]:
    """Locate hcloud and try to read its version."""
    binary = shutil.which("hcloud")
    result: dict[str, Any] = {"found": bool(binary), "path": binary}
    if not binary:
        return result

    try:
        completed = subprocess.run(
            [binary, "version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        result["version_command"] = {
            "return_code": None,
            "stdout": "",
            "stderr": "Timed out while running `hcloud version`.",
        }
        return result

    result["version_command"] = {
        "return_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    return result


def inspect_sdk_runtime(sdk_root_path: Path | None) -> dict[str, Any]:
    """Inspect optional Huawei Cloud Python SDK runtime/package availability."""
    installed_packages = hcloud_sdk_catalog.find_installed_service_packages()
    source_root_exists = bool(sdk_root_path and sdk_root_path.exists())
    source_packages = hcloud_sdk_catalog.find_service_packages(sdk_root_path) if sdk_root_path and source_root_exists else []
    result: dict[str, Any] = {
        "installed_package_count": len(installed_packages),
        "installed_services_sample": sorted({str(package["service_key"]).upper() for package in installed_packages})[:80],
        "source_root_exists": source_root_exists,
        "source_root_path": str(sdk_root_path) if sdk_root_path else None,
        "source_service_package_count": len(source_packages),
        "backend": "sdk",
        "availability_role": "supported_programmatic_backend",
        "backend_preference": "hcloud_then_sdk",
    }
    return result


def build_summary(
    include_meta_files: bool,
    *,
    include_sdk_runtime: bool = True,
) -> dict[str, Any]:
    """Build the local hcloud context summary with optional SDK discovery."""
    home = Path.home()
    hcloud_root = home / ".hcloud"
    result = {
        "hcloud": inspect_hcloud_binary(),
        "config": inspect_config(hcloud_root / "config.json"),
        "meta_repo": inspect_meta_repo(hcloud_root / "metaRepo", include_meta_files),
        "meta_origin": inspect_meta_origin(hcloud_root / "metaOrigin", include_meta_files),
        "redaction": hcloud_common.redaction_metadata(),
        "credential_visibility": {
            "scope": "local_profile_and_current_process_only",
            "stored_platform_credentials_checked": False,
            "configuration_status_when_absent": "unknown",
        },
    }
    if include_sdk_runtime:
        result["sdk_runtime"] = inspect_sdk_runtime(hcloud_sdk_catalog.DEFAULT_SDK_ROOT)
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-meta-files",
        action="store_true",
        help="Include per-service cached file names under ~/.hcloud/metaRepo/template.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the inspector and print JSON output."""
    args = parse_args()
    summary = {
        "success": True,
        "mode": "inspect",
        **build_summary(include_meta_files=args.include_meta_files),
    }
    if args.pretty:
        hcloud_common.emit_json(summary, pretty=True)
    else:
        hcloud_common.emit_json(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
