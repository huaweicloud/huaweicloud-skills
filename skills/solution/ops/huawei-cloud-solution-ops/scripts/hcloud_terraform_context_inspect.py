#!/usr/bin/env python3
"""Inspect local Terraform readiness for Huawei Cloud IaC workflows."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import credential_aliases
import hcloud_common
import hcloud_terraform_catalog

TERRAFORM_ENV_KEYS = tuple(
    dict.fromkeys(
        (
            *credential_aliases.ALL_CREDENTIAL_ENV_NAMES,
            "HW_ACCESS_KEY",
            "HW_SECRET_KEY",
            "HW_REGION_NAME",
            "HW_DOMAIN_ID",
            "HW_DOMAIN_NAME",
            "HW_USER_NAME",
            "HW_USER_ID",
            "HW_USER_PASSWORD",
            "HW_PROJECT_ID",
            "HW_PROJECT_NAME",
            "HW_SECURITY_TOKEN",
            "HW_AUTH_TOKEN",
            "HW_AUTH_URL",
            "HW_CLOUD",
            "HW_SHARED_CONFIG_FILE",
            "HW_PROFILE",
            "HW_ENTERPRISE_PROJECT_ID",
            "HW_MAX_RETRIES",
            "HW_ENABLE_FORCE_NEW",
            "HW_SIGNING_ALGORITHM",
            "HW_INSECURE",
            "HW_ASSUME_ROLE_AGENCY_NAME",
            "HW_ASSUME_ROLE_DOMAIN_NAME",
            "HW_ASSUME_ROLE_DOMAIN_ID",
            "HW_ASSUME_ROLE_DURATION",
            "HW_ASSUME_ROLE_IDP_ID",
            "HW_ASSUME_ROLE_ID_TOKEN",
            "HW_ASSUME_ROLE_ID_TOKEN_FILE",
            "OS_ACCESS_KEY",
            "OS_SECRET_KEY",
            "OS_REGION_NAME",
            "OS_DOMAIN_ID",
            "OS_USER_DOMAIN_ID",
            "OS_PROJECT_DOMAIN_ID",
            "OS_DOMAIN_NAME",
            "OS_USER_DOMAIN_NAME",
            "OS_PROJECT_DOMAIN_NAME",
            "OS_USERNAME",
            "OS_USER_ID",
            "OS_PASSWORD",
            "OS_PROJECT_ID",
            "OS_PROJECT_NAME",
            "OS_TENANT_ID",
            "OS_TENANT_NAME",
            "OS_AUTH_TOKEN",
            "OS_AUTH_URL",
            "OS_INSECURE",
            "OS_CACERT",
            "OS_CERT",
            "OS_KEY",
            "OS_AGENCY_NAME",
            "OS_AGENCY_DOMAIN_NAME",
            "OS_DELEGATED_PROJECT",
            "HUAWEICLOUD_ACCESS_KEY",
            "HUAWEICLOUD_SECRET_KEY",
            "HUAWEICLOUD_REGION",
            "HUAWEICLOUD_PROJECT_ID",
            "HUAWEICLOUD_SECURITY_TOKEN",
            "HUAWEI_ACCESS_KEY",
            "HUAWEI_SECRET_KEY",
            "HUAWEI_REGION",
            "HUAWEI_PROJECT_ID",
            "HUAWEI_DOMAIN_ID",
            "TF_PLUGIN_CACHE_DIR",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
        )
    )
)
HUAWEICLOUD_MIRROR_URL = "https://mirrors.huaweicloud.com/terraform/"
PROVIDER_CACHE_CANDIDATES = (
    Path.home() / ".terraform.d" / "providers" / "registry.terraform.io" / "huaweicloud" / "huaweicloud",
    Path.home() / ".terraform.d" / "plugins" / "registry.terraform.io" / "huaweicloud" / "huaweicloud",
    Path.home() / ".terraform.d" / "plugins" / "local-registry" / "huaweicloud" / "huaweicloud",
)


def env_status() -> dict[str, dict[str, Any]]:
    """Return redacted environment variable status for Terraform-related keys."""
    result = {}
    for key in TERRAFORM_ENV_KEYS:
        value = os.environ.get(key)
        result[key] = {
            "set": value is not None and value != "",
            "empty": value == "",
        }
    return result


def shared_config_status() -> dict[str, Any]:
    """Inspect hcloud shared config usability for the Terraform provider."""
    env_path = os.environ.get("HW_SHARED_CONFIG_FILE")
    config_path = Path(env_path).expanduser() if env_path else Path.home() / ".hcloud" / "config.json"
    result: dict[str, Any] = {
        "path_source": "HW_SHARED_CONFIG_FILE" if env_path else "default_hcloud_config",
        "exists": config_path.exists(),
        "auth_encrypt": None,
        "usable_for_provider_shared_config": False,
        "warning": None,
    }
    if not config_path.exists():
        return result
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result["warning"] = "hcloud_shared_config_unreadable"
        return result
    auth_encrypt = str(config.get("authEncrypt", "")).lower()
    result["auth_encrypt"] = auth_encrypt or None
    if auth_encrypt == "false":
        result["usable_for_provider_shared_config"] = True
    elif auth_encrypt == "true":
        result["warning"] = "hcloud_shared_config_encrypted"
    return result


def run_command(command: list[str], timeout: int = 15) -> dict[str, Any]:
    """Run a local command and return structured output."""
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
    except FileNotFoundError:
        return {"found": False, "return_code": None, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired:
        return {"found": True, "return_code": None, "stdout": "", "stderr": "timeout"}
    return {
        "found": True,
        "return_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def inspect_terraform() -> dict[str, Any]:
    """Inspect Terraform CLI availability."""
    path = shutil.which("terraform")
    result: dict[str, Any] = {"found": bool(path), "path": path}
    if not path:
        return result
    version = run_command([path, "version"], timeout=15)
    result["version_command"] = version
    version_match = re.search(r"Terraform v([0-9][^\s]+)", version.get("stdout", ""))
    result["version"] = version_match.group(1) if version_match else None
    return result


def inspect_hcloud() -> dict[str, Any]:
    """Inspect hcloud availability for discovery and post-apply verification."""
    path = shutil.which("hcloud")
    result: dict[str, Any] = {"found": bool(path), "path": path}
    if not path:
        return result
    result["version_command"] = run_command([path, "version"], timeout=15)
    return result


def forbidden_artifacts(workdir: Path) -> list[str]:
    """Return Terraform runtime artifacts that should not be committed."""
    if not workdir.exists():
        return []
    patterns = [
        "**/.terraform",
        "**/terraform.tfstate",
        "**/terraform.tfstate.*",
        "**/*.tfvars",
        "**/crash.log",
    ]
    findings: list[str] = []
    for pattern in patterns:
        for path in workdir.glob(pattern):
            if path.name.endswith(".tfvars.example"):
                continue
            findings.append(str(path))
    return sorted(dict.fromkeys(findings))


def provider_cache_hints(workdir: Path) -> dict[str, Any]:
    """Inspect local Terraform provider cache hints."""
    lock_files = sorted(path for path in workdir.rglob(".terraform.lock.hcl")) if workdir.exists() else []
    terraform_dirs = sorted(path for path in workdir.rglob(".terraform") if path.is_dir()) if workdir.exists() else []
    plugin_cache = os.environ.get("TF_PLUGIN_CACHE_DIR")
    global_candidates = [
        {
            "path": str(path),
            "exists": path.exists(),
        }
        for path in PROVIDER_CACHE_CANDIDATES
    ]
    return {
        "lock_file_count": len(lock_files),
        "lock_files_sample": [str(path) for path in lock_files[:10]],
        "local_terraform_dir_count": len(terraform_dirs),
        "plugin_cache_dir": plugin_cache,
        "plugin_cache_dir_exists": bool(plugin_cache and Path(plugin_cache).exists()),
        "global_provider_cache_candidates": global_candidates,
    }


def terraform_cli_config_hints() -> dict[str, Any]:
    """Inspect Terraform CLI config hints without modifying local files."""
    env_path = os.environ.get("TF_CLI_CONFIG_FILE")
    default_path = Path(os.environ.get("APPDATA", "")) / "terraform.rc" if os.name == "nt" else Path.home() / ".terraformrc"
    config_path = Path(env_path).expanduser() if env_path else default_path
    result: dict[str, Any] = {
        "path_source": "TF_CLI_CONFIG_FILE" if env_path else "default",
        "path": str(config_path),
        "exists": config_path.exists(),
        "readable": False,
        "has_provider_installation": False,
        "uses_network_mirror": False,
        "uses_filesystem_mirror": False,
        "allows_direct": False,
        "huaweicloud_mirror_configured": False,
        "notes": [
            "inspect_only",
            "no_terraform_install_or_provider_download_attempted",
        ],
    }
    if not config_path.exists():
        return result
    try:
        content = config_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return result
    lowered = content.lower()
    result.update(
        {
            "readable": True,
            "has_provider_installation": "provider_installation" in lowered,
            "uses_network_mirror": "network_mirror" in lowered,
            "uses_filesystem_mirror": "filesystem_mirror" in lowered,
            "allows_direct": "direct" in lowered,
            "huaweicloud_mirror_configured": HUAWEICLOUD_MIRROR_URL in content,
        }
    )
    return result


def readiness(
    terraform: dict[str, Any],
    env: dict[str, dict[str, Any]],
    forbidden: list[str],
    shared_config: dict[str, Any],
) -> dict[str, Any]:
    """Return readiness flags and blockers."""
    has_terraform = bool(terraform.get("found"))
    has_region = any(env[name]["set"] for name in credential_aliases.REGION_ENV_NAMES)
    family_auth = {
        family.name: (env[family.access_key]["set"] and env[family.secret_key]["set"] and has_region)
        for family in credential_aliases.CLOUD_CREDENTIAL_FAMILIES
    }
    has_hw_auth = family_auth["hw"]
    has_os_auth = family_auth["os"]
    has_huaweicloud_auth = family_auth["huaweicloud"]
    has_huawei_auth = family_auth["huawei"]
    has_token_auth = (env["HW_AUTH_TOKEN"]["set"] or env["OS_AUTH_TOKEN"]["set"]) and (
        env["HW_REGION_NAME"]["set"] or env["OS_REGION_NAME"]["set"]
    )
    has_shared_config_auth = bool(shared_config["usable_for_provider_shared_config"])
    has_assume_role_hint = env["HW_ASSUME_ROLE_AGENCY_NAME"]["set"] or env["HW_ASSUME_ROLE_IDP_ID"]["set"]
    has_auth = any(family_auth.values()) or has_token_auth or has_shared_config_auth
    blockers = []
    warnings = []
    if not has_terraform:
        blockers.append("terraform_cli_missing")
    if forbidden:
        warnings.append("terraform_runtime_artifacts_present")
    if not has_hw_auth and has_huaweicloud_auth:
        warnings.append("huaweicloud_env_set_but_hw_env_unset")
    if not has_hw_auth and has_huawei_auth:
        warnings.append("huawei_env_set_but_hw_env_unset")
    if has_os_auth and not has_hw_auth:
        warnings.append("os_env_aliases_set")
    if shared_config.get("warning"):
        warnings.append(shared_config["warning"])
    if has_assume_role_hint and not has_auth:
        warnings.append("assume_role_hint_set_without_base_credentials")
    if not has_auth:
        warnings.append("terraform_cloud_credentials_unset")
    return {
        "can_generate": True,
        "can_fmt": has_terraform,
        "can_validate": has_terraform,
        "can_plan": has_terraform and has_auth,
        "can_apply": has_terraform and has_auth,
        "blockers": blockers,
        "warnings": warnings,
        "auth": {
            **{f"{family_name}_env_complete": complete for family_name, complete in family_auth.items()},
            "token_env_complete": has_token_auth,
            "shared_config_usable": has_shared_config_auth,
            "assume_role_hint_set": has_assume_role_hint,
            "cloud_credentials_complete": has_auth,
            "visibility": "current_process_only",
            "configuration_status": ("observed_in_current_process" if has_auth else "unknown"),
        },
        "execution_boundary": "plan/apply require credentials and explicit user confirmation; hcloud remains post-apply verification path",
    }


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    """Build the Terraform context readiness report."""
    workdir = args.workdir.resolve()
    terraform = inspect_terraform()
    env = env_status()
    shared_config = shared_config_status()
    forbidden = forbidden_artifacts(workdir)
    return {
        "success": True,
        "workdir": str(workdir),
        "terraform": terraform,
        "hcloud": inspect_hcloud(),
        "environment": env,
        "shared_config": shared_config,
        "provider_cache": provider_cache_hints(workdir),
        "terraform_cli_config": terraform_cli_config_hints(),
        "asset_catalog": {
            "example_catalog": str(hcloud_terraform_catalog.EXAMPLE_CATALOG_PATH),
            "reference_catalog": str(hcloud_terraform_catalog.REFERENCE_CATALOG_PATH),
            "example_catalog_exists": hcloud_terraform_catalog.EXAMPLE_CATALOG_PATH.exists(),
            "reference_catalog_exists": hcloud_terraform_catalog.REFERENCE_CATALOG_PATH.exists(),
        },
        "forbidden_artifacts": forbidden,
        "readiness": readiness(terraform, env, forbidden, shared_config),
        "redaction": hcloud_common.redaction_metadata(),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workdir",
        type=Path,
        default=hcloud_common.ROOT,
        help="Directory to inspect for Terraform assets and artifacts.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Inspect Terraform readiness."""
    args = parse_args()
    result = build_context(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
