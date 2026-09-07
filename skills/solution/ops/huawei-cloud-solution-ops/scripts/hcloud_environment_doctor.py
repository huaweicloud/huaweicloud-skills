#!/usr/bin/env python3
"""Check local Huawei Cloud tool readiness without installing or calling cloud APIs."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import credential_aliases
import hcloud_common
import hcloud_context_inspect
import hcloud_terraform_context_inspect

MIN_PYTHON = (3, 12)
NEED_CHOICES = (
    "hcloud",
    "live",
    "sdk",
    "terraform",
    "obs",
    "obsutil",
    "maas",
    "network",
    "artifacts",
)
KOOCLI_QUICKSTART_URL = "https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"
KOOCLI_WINDOWS_DOWNLOAD_URL = "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip"
POSIX_HCLOUD_INSTALL_COMMANDS = [
    "curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh",
    "bash ./hcloud_install.sh -y",
    "hcloud version",
]
HCLOUD_CONFIG_COMMANDS = [
    "hcloud configure init --cli-profile <profile-name>",
    "hcloud configure set --cli-profile <profile-name> --cli-region <region>",
    "hcloud configure list",
]
HCLOUD_PRIVACY_COMMAND = "hcloud configure set --cli-agree-privacy-statement=true"
HCLOUD_METADATA_COMMAND = "hcloud meta download"
PROJECT_RESOLVE_COMMAND = (
    "python3 scripts/hcloud_project_resolve.py --region <region> --pretty"
)


def platform_family(system_name: str | None = None) -> str:
    """Return a stable platform family for installation guidance."""
    value = (system_name or platform.system()).strip().lower()
    return "windows" if value == "windows" else "posix"


def command_python(system_name: str | None = None) -> str:
    """Return the conventional Python command for user-facing local guidance."""
    return "python" if platform_family(system_name) == "windows" else "python3"


def hcloud_install_guidance(system_name: str | None = None) -> tuple[list[str], list[str]]:
    """Return platform-specific KooCLI setup guidance without executing it."""
    if platform_family(system_name) != "windows":
        return list(POSIX_HCLOUD_INSTALL_COMMANDS), []
    return (
        [
            f'Invoke-WebRequest -Uri "{KOOCLI_WINDOWS_DOWNLOAD_URL}" -OutFile "$env:TEMP\\hcloud.zip"',
            '$installDir = Join-Path $env:LOCALAPPDATA "HuaweiCloud\\KooCLI"; New-Item -ItemType Directory -Force -Path $installDir',
            'Expand-Archive -Path "$env:TEMP\\hcloud.zip" -DestinationPath $installDir -Force',
            '$env:Path += ";$installDir"; hcloud version',
        ],
        [
            "Persist the directory containing hcloud.exe in the user Path before opening a new PowerShell session.",
            f"Verify the download and installation steps against {KOOCLI_QUICKSTART_URL} before running them.",
        ],
    )


def sdk_install_commands(
    services: list[str] | None = None,
    system_name: str | None = None,
) -> list[str]:
    """Return one task-scoped SDK installation command for user review."""
    service_specs, _ = normalize_sdk_services(services)
    packages = sorted({f"huaweicloudsdk{suffix}" for _, suffix in service_specs})
    if not packages:
        return []
    return [f"{command_python(system_name)} -m pip install {' '.join(packages)}"]


def normalize_sdk_services(
    services: list[str] | None,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Normalize requested SDK services into display names and package suffixes."""
    normalized: dict[str, str] = {}
    invalid: list[str] = []
    for raw_service in services or []:
        display_name = raw_service.strip().upper()
        package_suffix = "".join(
            character for character in raw_service.strip().lower() if character.isalnum()
        )
        if not display_name:
            continue
        if not package_suffix:
            invalid.append(display_name)
            continue
        normalized[display_name] = package_suffix
    return sorted(normalized.items()), sorted(set(invalid))


def terraform_check_commands(system_name: str | None = None) -> list[str]:
    """Return platform-appropriate Terraform readiness commands for user review."""
    return ["terraform version", f"{command_python(system_name)} scripts/hcloud_terraform_context_inspect.py --pretty"]


def obsutil_check_commands(system_name: str | None = None) -> list[str]:
    """Return the platform-appropriate obsutil version command for user review."""
    executable = "obsutil.exe" if platform_family(system_name) == "windows" else "obsutil"
    return [f"{executable} version"]


def run_command(command: list[str], timeout: int = 15) -> dict[str, Any]:
    """Run a local command for version checks only."""
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


def check_item(
    name: str,
    status: str,
    *,
    required: bool,
    summary: str,
    details: dict[str, Any] | None = None,
    next_actions: list[str] | None = None,
    install_commands: list[str] | None = None,
    recovery_commands: list[str] | None = None,
) -> dict[str, Any]:
    """Build one normalized environment check result."""
    return {
        "name": name,
        "status": status,
        "required": required,
        "summary": summary,
        "details": details or {},
        "next_actions": next_actions or [],
        "install_commands": install_commands or [],
        "recovery_commands": recovery_commands or [],
    }


def skipped_check(name: str) -> dict[str, Any]:
    """Return a normalized result for a dependency outside the selected task scope."""
    return check_item(
        name,
        "skipped",
        required=False,
        summary="Dependency was not selected for this task-scoped check.",
    )


def inspect_python() -> dict[str, Any]:
    """Inspect Python runtime compatibility for local helper scripts."""
    version = sys.version_info[:3]
    ok = version >= MIN_PYTHON
    return check_item(
        "python",
        "ok" if ok else "blocker",
        required=True,
        summary=f"Python {version[0]}.{version[1]}.{version[2]}",
        details={
            "version": list(version),
            "minimum": list(MIN_PYTHON),
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        next_actions=[]
        if ok
        else [
            "Install Python 3.12+ and rerun this doctor."
            if platform_family() != "windows"
            else "Install Python 3.12+ so the `python` command is available, then rerun this doctor."
        ],
    )


def inspect_hcloud(needs: set[str]) -> dict[str, Any]:
    """Inspect KooCLI and hcloud config without making cloud API calls."""
    summary = hcloud_context_inspect.build_summary(
        include_meta_files=False,
        include_sdk_runtime=False,
    )
    hcloud = summary.get("hcloud", {})
    config = summary.get("config", {})
    found = bool(hcloud.get("found"))
    current_profile = config.get("current_profile") if isinstance(config, dict) else None
    profile_auth_ready = bool(
        isinstance(current_profile, dict)
        and (current_profile.get("has_access_key") or current_profile.get("mode") in {"ecsAgency", "SSO", "AssumeRole"})
    )
    privacy_statement_accepted = config.get("agree_privacy") is True if isinstance(config, dict) else False
    region_ready = bool(
        isinstance(current_profile, dict)
        and str(current_profile.get("region") or "").strip()
    )
    project_id_configured = bool(
        isinstance(current_profile, dict)
        and str(current_profile.get("project_id") or "").strip()
    )
    required = "hcloud" in needs
    live_call_context_ready = bool(
        found
        and privacy_statement_accepted
        and profile_auth_ready
        and region_ready
    )
    if not found:
        status = "blocker" if required else "skipped"
    elif required and not live_call_context_ready:
        status = "warning"
    else:
        status = "ok"
    next_actions = []
    install_commands = []
    recovery_commands: list[str] = []
    if not found:
        next_actions.append("Install Huawei Cloud KooCLI before live hcloud discovery or changes.")
        install_commands, platform_notes = hcloud_install_guidance()
        next_actions.extend(platform_notes)
    if found and not privacy_statement_accepted:
        next_actions.append("Review and accept the KooCLI privacy statement before non-interactive calls.")
        recovery_commands.append(HCLOUD_PRIVACY_COMMAND)
    if found and not profile_auth_ready:
        next_actions.append(
            "Configure or choose an hcloud profile before live cloud calls; do not put credential values in doctor arguments or output."
        )
        recovery_commands.extend(HCLOUD_CONFIG_COMMANDS)
    if found and not region_ready:
        next_actions.append("Set the intended Huawei Cloud region on the selected profile.")
        for command in HCLOUD_CONFIG_COMMANDS:
            if "--cli-region" in command and command not in recovery_commands:
                recovery_commands.append(command)
        recovery_commands.append(PROJECT_RESOLVE_COMMAND)
    elif found and not project_id_configured:
        next_actions.append(
            "Resolve the regional project ID before an operation that requires project_id."
        )
        recovery_commands.append(PROJECT_RESOLVE_COMMAND)
    meta_repo = summary.get("meta_repo", {})
    metadata_cache_ready = bool(
        isinstance(meta_repo, dict)
        and meta_repo.get("services_file_exists")
        and int(meta_repo.get("cached_service_count") or 0) > 0
    )
    if found and not metadata_cache_ready:
        next_actions.append(
            "Preload KooCLI metadata when repeated operation discovery is slow or offline templates are missing."
        )
        recovery_commands.append(HCLOUD_METADATA_COMMAND)
    return check_item(
        "hcloud",
        status,
        required=required,
        summary="KooCLI is available." if found else "KooCLI hcloud binary is missing.",
        details={
            "platform": platform_family(),
            "hcloud": hcloud,
            "config_exists": config.get("exists") if isinstance(config, dict) else False,
            "current_profile_name": config.get("current_profile_name") if isinstance(config, dict) else None,
            "profile_auth_ready": profile_auth_ready,
            "privacy_statement_accepted": privacy_statement_accepted,
            "region_ready": region_ready,
            "project_id_configured": project_id_configured,
            "metadata_cache_ready": metadata_cache_ready,
            "live_call_context_ready": live_call_context_ready,
            "meta_repo": {
                "exists": meta_repo.get("exists") if isinstance(meta_repo, dict) else False,
                "services_file_exists": meta_repo.get("services_file_exists") if isinstance(meta_repo, dict) else False,
                "cached_service_count": meta_repo.get("cached_service_count") if isinstance(meta_repo, dict) else 0,
                "services_update_time": meta_repo.get("services_update_time") if isinstance(meta_repo, dict) else None,
                "template_service_count": len(meta_repo.get("template_services", [])) if isinstance(meta_repo, dict) else 0,
                "template_file_count": meta_repo.get("template_file_count") if isinstance(meta_repo, dict) else 0,
            },
        },
        next_actions=next_actions,
        install_commands=install_commands,
        recovery_commands=recovery_commands,
    )


def env_presence(keys: list[str]) -> dict[str, dict[str, bool]]:
    """Return redacted presence information for environment variables."""
    return credential_aliases.credential_environment_presence(keys)


def inspect_auth(needs: set[str]) -> dict[str, Any]:
    """Inspect current-process credential visibility without exposing values."""
    env = credential_aliases.credential_environment_presence()
    resolved = credential_aliases.resolve_cloud_credentials()
    observation = credential_aliases.redact_credential_resolution(resolved)
    cloud_ready = bool(resolved["complete"])
    live_required = "live" in needs
    status = "ok" if cloud_ready else ("blocker" if live_required else "warning")
    auth_modes: dict[str, bool] = {}
    for family in credential_aliases.CLOUD_CREDENTIAL_FAMILIES:
        pair_set = env[family.access_key]["set"] and env[family.secret_key]["set"]
        region_set = any(env[name]["set"] for name in credential_aliases.REGION_ENV_NAMES)
        auth_modes[f"{family.name}_env_complete"] = pair_set and region_set
    auth_modes["maas_api_key_set"] = any(env[name]["set"] for name in credential_aliases.MAAS_API_KEY_ENV_NAMES)
    return check_item(
        "cloud_credentials",
        status,
        required=live_required,
        summary=(
            "A complete cloud credential environment is visible to the current process."
            if cloud_ready
            else "The current process cannot observe a complete cloud credential environment; stored or action-scoped configuration remains unknown."
        ),
        details={
            "environment": env,
            "auth_modes": auth_modes,
            "credential_observation": {
                **observation,
                "selected_family": observation["family"],
            },
            "redaction": hcloud_common.redaction_metadata(),
        },
        next_actions=[]
        if cloud_ready
        else [
            "For a cloud action, use the platform's approved action path so stored credentials can be injected only into that subprocess.",
            "Outside a credential broker, use an existing hcloud profile or one supported same-family AK/SK pair plus a supported region variable.",
            "Never paste AK/SK into chat or logs; masked values made only of asterisks mean present but hidden, not missing.",
        ],
        install_commands=HCLOUD_CONFIG_COMMANDS if not cloud_ready else [],
    )


def inspect_sdk(
    needs: set[str],
    services: list[str] | None = None,
    *,
    broad_overview: bool = False,
) -> dict[str, Any]:
    """Inspect optional Huawei Cloud Python SDK availability."""
    service_specs, invalid_services = normalize_sdk_services(services)
    requested_services = [service for service, _ in service_specs]
    required = "sdk" in needs
    if service_specs:
        installed_services = [
            service
            for service, package_suffix in service_specs
            if hcloud_context_inspect.hcloud_sdk_catalog.installed_package_path(
                f"huaweicloudsdk{package_suffix}"
            )
        ]
        missing_services = [service for service in requested_services if service not in installed_services]
        sdk_runtime = {
            "backend": "sdk",
            "availability_role": "supported_programmatic_backend",
            "backend_preference": "hcloud_then_sdk",
            "requested_services": requested_services,
            "installed_services": installed_services,
            "missing_services": missing_services,
            "invalid_services": invalid_services,
            "installed_package_count": len(installed_services),
        }
        ready = not missing_services and not invalid_services
    elif broad_overview:
        sdk_runtime = hcloud_context_inspect.inspect_sdk_runtime(
            hcloud_context_inspect.hcloud_sdk_catalog.DEFAULT_SDK_ROOT
        )
        installed_services = list(sdk_runtime.get("installed_services_sample") or [])
        missing_services = []
        sdk_runtime.update(
            {
                "requested_services": [],
                "installed_services": installed_services,
                "missing_services": [],
                "invalid_services": [],
                "package_scan": "full_overview",
            }
        )
        ready = bool(sdk_runtime.get("installed_package_count"))
    else:
        installed_services = []
        missing_services = []
        sdk_runtime = {
            "backend": "sdk",
            "availability_role": "supported_programmatic_backend",
            "backend_preference": "hcloud_then_sdk",
            "requested_services": [],
            "installed_services": [],
            "missing_services": [],
            "invalid_services": invalid_services,
            "installed_package_count": 0,
            "package_scan": "skipped_without_task_service_scope",
        }
        ready = False
    scope_missing = required and not requested_services and not invalid_services
    if scope_missing:
        status = "unknown"
    elif ready:
        status = "ok"
    else:
        status = "blocker" if required else "skipped"
    install_services = missing_services or ([] if ready else requested_services)
    return check_item(
        "huaweicloud_python_sdk",
        status,
        required=required,
        summary=(
            "SDK service scope is required before readiness can be determined."
            if scope_missing
            else "SDK service scope is invalid."
            if invalid_services
            else "All requested Huawei Cloud Python SDK packages are installed."
            if ready and requested_services
            else "Huawei Cloud Python SDK packages are installed."
            if ready
            else "Required Huawei Cloud Python SDK packages are missing."
            if required
            else "SDK is optional and no matching package was found."
        ),
        details=sdk_runtime,
        next_actions=(
            [
                "Specify --sdk-service for every service used by the task, then install only the reported missing packages."
            ]
            if required and not ready
            else []
        ),
        install_commands=sdk_install_commands(install_services) if not ready else [],
    )


def inspect_terraform(needs: set[str], workdir: Path) -> dict[str, Any]:
    """Inspect optional Terraform readiness through the existing Terraform inspector."""
    context = hcloud_terraform_context_inspect.build_context(SimpleNamespace(workdir=workdir))
    found = bool(context.get("terraform", {}).get("found"))
    required = "terraform" in needs
    status = "ok" if found else ("blocker" if required else "skipped")
    return check_item(
        "terraform",
        status,
        required=required,
        summary="Terraform CLI is available." if found else "Terraform is optional and not installed.",
        details={
            "terraform": context.get("terraform", {}),
            "readiness": context.get("readiness", {}),
            "terraform_cli_config": context.get("terraform_cli_config", {}),
            "provider_cache": context.get("provider_cache", {}),
            "forbidden_artifacts": context.get("forbidden_artifacts", []),
        },
        next_actions=[]
        if found
        else ["Install Terraform only when the task explicitly needs IaC, import, drift, or long-term management."],
        install_commands=[] if found else terraform_check_commands(),
    )


def obsutil_config_status(config_path: Path) -> dict[str, Any]:
    """Inspect obsutil config presence without printing credential values."""
    result = {
        "path": str(config_path),
        "exists": config_path.exists(),
        "has_ak": False,
        "has_sk": False,
        "has_security_token": False,
        "read_error": None,
    }
    if not config_path.exists():
        return result
    try:
        lines = config_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        result["read_error"] = str(exc)
        return result
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip().lower()
        has_value = bool(value.strip())
        if key in {"ak", "accesskey", "access_key"}:
            result["has_ak"] = result["has_ak"] or has_value
        elif key in {"sk", "secretkey", "secret_key"}:
            result["has_sk"] = result["has_sk"] or has_value
        elif key in {"securitytoken", "security_token", "token"}:
            result["has_security_token"] = result["has_security_token"] or has_value
    return result


def inspect_obsutil(needs: set[str]) -> dict[str, Any]:
    """Inspect optional OBS command tooling readiness."""
    path = shutil.which("obsutil")
    version = run_command([path, "version"], timeout=15) if path else {"found": False}
    hcloud_path = shutil.which("hcloud")
    config = obsutil_config_status(Path.home() / ".obsutilconfig")
    standalone_required = "obsutil" in needs
    obs_required = "obs" in needs
    found = bool(path or hcloud_path) if obs_required and not standalone_required else bool(path)
    required = standalone_required or obs_required
    status = "ok" if found else ("blocker" if required else "skipped")
    return check_item(
        "obsutil",
        status,
        required=required,
        summary=(
            "OBS command tooling is available."
            if found
            else "OBS command tooling is required but unavailable."
            if required
            else "OBS tooling is optional and not installed."
        ),
        details={
            "path": path,
            "standalone_obsutil_path": path,
            "hcloud_path": hcloud_path,
            "requirement": "obs_tooling_any" if obs_required and not standalone_required else "standalone_obsutil",
            "version_command": version,
            "config": config,
        },
        next_actions=[]
        if found
        else ["Install KooCLI for `hcloud obs`, or install standalone obsutil when the task requires it."],
        install_commands=[] if found else obsutil_check_commands(),
    )


def inspect_maas(needs: set[str]) -> dict[str, Any]:
    """Inspect optional MaaS API key presence."""
    required = "maas" in needs
    env = credential_aliases.credential_environment_presence(credential_aliases.MAAS_API_KEY_ENV_NAMES)
    _, source_name = credential_aliases.resolve_maas_api_key()
    has_key = source_name is not None
    status = "ok" if has_key else ("blocker" if required else "skipped")
    return check_item(
        "modelarts_maas",
        status,
        required=required,
        summary="A MaaS API key environment variable is set." if has_key else "MaaS API calls are optional and no MaaS API key is set.",
        details={
            "environment": env,
            "selected_source": source_name,
            "visibility": "current_process_only",
            "configuration_status": ("observed_in_current_process" if has_key else "unknown"),
            "redaction": hcloud_common.redaction_metadata(),
        },
        next_actions=[] if has_key else ["Set MAAS_API_KEY or MODELARTS_MAAS_API_KEY only when calling Huawei Cloud MaaS APIs."],
    )


def inspect_proxy() -> dict[str, Any]:
    """Inspect proxy environment presence."""
    env = env_presence(["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"])
    any_proxy = any(item["set"] for item in env.values())
    return check_item(
        "proxy",
        "ok" if any_proxy else "skipped",
        required=False,
        summary="Proxy variables are set." if any_proxy else "No proxy variables set; this is fine for direct networks.",
        details={"environment": env},
    )


def inspect_network(needs: set[str]) -> dict[str, Any]:
    """Declare host network readiness without performing an external probe."""
    required = "network" in needs
    return check_item(
        "network",
        "unknown" if required else "skipped",
        required=required,
        summary=(
            "Network access is required but is not probed by this check-only doctor."
            if required
            else "Network access was not requested for this task."
        ),
        details={"verification_owner": "host_runtime_or_explicit_preflight"},
        next_actions=(
            ["Use the host's approved network preflight for the selected Huawei endpoint before a long live workflow."]
            if required
            else []
        ),
    )


def inspect_artifacts(needs: set[str], workdir: Path) -> dict[str, Any]:
    """Inspect whether the selected artifact directory exists and is writable."""
    required = "artifacts" in needs
    exists = workdir.exists()
    is_directory = workdir.is_dir()
    writable = exists and is_directory and os.access(workdir, os.W_OK)
    status = "ok" if writable else ("blocker" if required else "skipped")
    return check_item(
        "artifacts",
        status,
        required=required,
        summary=(
            "Artifact directory is writable."
            if writable
            else "A writable artifact directory is required but unavailable."
            if required
            else "Artifact output was not required for this task."
        ),
        details={
            "path": str(workdir),
            "exists": exists,
            "is_directory": is_directory,
            "writable": writable,
        },
        next_actions=[] if writable else ["Choose a host-provided writable task directory for result artifacts."],
    )


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact status summary."""
    counts = {"ok": 0, "warning": 0, "blocker": 0, "skipped": 0}
    for item in checks:
        counts[str(item.get("status"))] = counts.get(str(item.get("status")), 0) + 1
    required_unready = [
        item["name"]
        for item in checks
        if item.get("required") and item.get("status") != "ok"
    ]
    return {
        **counts,
        "ready": not required_unready,
        "required_blockers": [item["name"] for item in checks if item.get("required") and item.get("status") == "blocker"],
        "required_unready": required_unready,
    }


def build_recovery_plan(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Project actionable recovery steps from completed local checks only.

    The projection does not run commands or inspect anything beyond the supplied
    check records. Hosts and Agents remain responsible for reviewing and running
    any suggested action in their own permission boundary.
    """

    steps: list[dict[str, Any]] = []
    for check in checks:
        status = str(check.get("status") or "unknown")
        required = bool(check.get("required"))
        if status == "skipped":
            continue
        has_recovery = bool(
            check.get("next_actions")
            or check.get("install_commands")
            or check.get("recovery_commands")
        )
        if status == "ok" and not (required and has_recovery):
            continue
        if not required and status != "blocker":
            continue
        commands = [
            str(command)
            for command in (
                list(check.get("install_commands") or [])
                + list(check.get("recovery_commands") or [])
            )
            if str(command).strip()
        ]
        steps.append(
            {
                "dependency": check.get("name"),
                "status": status,
                "required": required,
                "blocking": required and status != "ok",
                "summary": check.get("summary"),
                "actions": list(check.get("next_actions") or []),
                "commands": list(dict.fromkeys(commands)),
                "execution_owner": "agent_or_host_after_review",
            }
        )
    return {
        "contract": "huaweicloud_skill_recovery_plan_v1",
        "ready": not any(step["blocking"] for step in steps),
        "step_count": len(steps),
        "steps": steps,
        "execution_performed": False,
        "host_neutral": True,
        "credential_values_accepted": False,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    """Build the check-only environment doctor report."""
    needs = {str(item).lower() for item in getattr(args, "need", [])}
    full_scan = not needs
    workdir = Path(getattr(args, "workdir", hcloud_common.ROOT)).resolve()
    sdk_services = getattr(args, "sdk_service", [])
    if full_scan:
        sdk_check = inspect_sdk(needs, sdk_services, broad_overview=True)
    elif "sdk" in needs:
        sdk_check = inspect_sdk(needs, sdk_services)
    else:
        sdk_check = skipped_check("huaweicloud_python_sdk")
    checks = [
        inspect_python(),
        inspect_hcloud(needs) if full_scan or "hcloud" in needs else skipped_check("hcloud"),
        inspect_auth(needs) if full_scan or "live" in needs else skipped_check("cloud_credentials"),
        sdk_check,
        (
            inspect_terraform(needs, workdir)
            if full_scan or "terraform" in needs
            else skipped_check("terraform")
        ),
        (
            inspect_obsutil(needs)
            if full_scan or needs.intersection({"obs", "obsutil"})
            else skipped_check("obsutil")
        ),
        inspect_maas(needs) if full_scan or "maas" in needs else skipped_check("modelarts_maas"),
        inspect_proxy() if full_scan or "network" in needs else skipped_check("proxy"),
        inspect_network(needs),
        inspect_artifacts(needs, workdir)
        if full_scan or "artifacts" in needs
        else skipped_check("artifacts"),
    ]
    return {
        "success": True,
        "mode": "check_only",
        "dependency_contract": "huaweicloud_skill_runtime_dependencies_v1",
        "no_changes_made": True,
        "scan_scope": "full_overview" if full_scan else "task_scoped",
        "needs": sorted(needs),
        "workdir": str(workdir),
        "summary": summarize(checks),
        "recovery_plan": build_recovery_plan(checks),
        "checks": checks,
        "source_references": [
            "references/auth-and-context.md",
            "references/runtime-dependencies.md",
            "references/terraform/terraform-assets.md",
            "references/playbooks/obs-static-website-hosting.md",
        ],
        "redaction": hcloud_common.redaction_metadata(),
        "execution_boundary": "This doctor does not install packages, modify credentials, write config, run terraform init/plan/apply, or call Huawei Cloud APIs.",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--need",
        action="append",
        choices=NEED_CHOICES,
        default=[],
        help="Mark a capability as required for this task. Can be repeated.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=hcloud_common.ROOT,
        help="Workspace directory to inspect for Terraform runtime artifacts.",
    )
    parser.add_argument(
        "--sdk-service",
        action="append",
        default=[],
        help="Huawei Cloud SDK service package required by the task, for example ECS. Can be repeated.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Run the environment doctor."""
    args = parse_args()
    result = build_report(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
