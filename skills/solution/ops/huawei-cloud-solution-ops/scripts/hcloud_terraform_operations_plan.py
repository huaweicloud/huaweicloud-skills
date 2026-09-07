#!/usr/bin/env python3
"""Plan and optionally run gated Terraform import/drift operations."""

from __future__ import annotations

import argparse
import hashlib
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_query

OPERATIONS = ("import", "drift", "remote-state", "full")


class TerraformOperationsError(ValueError):
    """Raised when a Terraform operations plan cannot be built safely."""


def parse_key_value(value: str, label: str) -> tuple[str, str]:
    """Parse one KEY=VALUE pair."""
    if "=" not in value:
        raise TerraformOperationsError(f"Expected {label} as KEY=VALUE, got {value!r}.")
    key, raw = value.split("=", 1)
    if not key or not raw:
        raise TerraformOperationsError(f"Expected non-empty {label} KEY=VALUE, got {value!r}.")
    return key, raw


def parse_import_targets(values: list[str]) -> list[dict[str, str]]:
    """Parse Terraform import targets as ADDRESS=REMOTE_ID."""
    targets = []
    for value in values:
        address, remote_id = parse_key_value(value, "--import-target")
        targets.append({"address": address, "id": remote_id})
    return targets


def parse_readback(value: str) -> dict[str, Any]:
    """Parse a readback spec as SERVICE:OPERATION:KEY=VALUE[,KEY=VALUE]."""
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise TerraformOperationsError(f"Expected --readback SERVICE:OPERATION:KEY=VALUE, got {value!r}.")
    service, operation, raw_params = parts
    params = []
    for item in raw_params.split(","):
        key, raw = parse_key_value(item, "--readback parameter")
        params.append(f"{key}={raw}")
    return {"service": service.upper(), "operation": operation, "params": params}


def readback_args(args: argparse.Namespace, spec: dict[str, Any]) -> SimpleNamespace:
    """Return args for hcloud_resource_query readback planning."""
    return SimpleNamespace(
        service=spec["service"],
        operation=spec["operation"],
        param=spec["params"],
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def command_item(command: list[str], purpose: str, *, state_changing: bool = False) -> dict[str, Any]:
    """Return a normalized command plan item."""
    return {
        "purpose": purpose,
        "command": command,
        "command_shell": shlex.join(command),
        "state_changing": state_changing,
    }


def import_commands(targets: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Return Terraform import command plans."""
    return [
        command_item(["terraform", "import", target["address"], target["id"]], f"Import {target['address']}.", state_changing=True)
        for target in targets
    ]


def drift_commands() -> list[dict[str, Any]]:
    """Return Terraform drift review command plans."""
    return [
        command_item(["terraform", "plan", "-refresh-only", "-detailed-exitcode", "-no-color"], "Refresh-only drift review."),
        command_item(["terraform", "plan", "-detailed-exitcode", "-no-color"], "Configuration-to-live plan review."),
    ]


def remote_state_checks(args: argparse.Namespace) -> dict[str, Any]:
    """Return remote state migration review guidance."""
    return {
        "backend_type": args.backend_type,
        "checks": [
            "Backend location, encryption, locking, and access control are reviewed.",
            "Workspace/environment separation is explicit.",
            "State files, .tfvars, .terraform, and secrets are not committed.",
            "Run terraform init -migrate-state only after backup and confirmation.",
        ],
        "commands": [
            command_item(["terraform", "init", "-migrate-state"], "Migrate local state to configured backend.", state_changing=True),
        ],
        "execution_boundary": "Remote state migration is state-changing and is not executed by default.",
    }


def state_change_token(args: argparse.Namespace, targets: list[dict[str, str]]) -> str:
    """Return a short confirmation token for Terraform state-changing commands."""
    raw = "|".join(
        [
            str(Path(args.workdir).resolve()),
            args.operation,
            args.backend_type or "",
            ";".join(f"{item['address']}={item['id']}" for item in targets),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def execute_command(command: list[str], workdir: Path, timeout: int, *, drift_exitcode: bool = False) -> dict[str, Any]:
    """Run a Terraform command and return a compact result."""
    completed = subprocess.run(command, cwd=workdir, text=True, capture_output=True, timeout=timeout, check=False)
    success_codes = {0, 2} if drift_exitcode else {0}
    return {
        "command": command,
        "command_shell": shlex.join(command),
        "return_code": completed.returncode,
        "success": completed.returncode in success_codes,
        "drift_detected": completed.returncode == 2 if drift_exitcode else None,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def execute_drift(commands: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """Execute non-state-changing drift plan commands."""
    return [
        execute_command(item["command"], Path(args.workdir), args.timeout, drift_exitcode=True)
        for item in commands
    ]


def execute_imports(commands: list[dict[str, Any]], args: argparse.Namespace, expected_token: str) -> list[dict[str, Any]]:
    """Execute gated Terraform import commands."""
    if not args.allow_state_change:
        raise TerraformOperationsError("Import execution requires --allow-state-change.")
    if args.confirm_token != expected_token:
        raise TerraformOperationsError("Import execution requires the exact --confirm-token from the plan.")
    return [execute_command(item["command"], Path(args.workdir), args.timeout) for item in commands]


def build_readback_plans(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build hcloud readback plans after Terraform operations."""
    plans = []
    for value in args.readback:
        spec = parse_readback(value)
        plan = hcloud_resource_query.build_plan(readback_args(args, spec))
        plans.append(
            {
                "spec": spec,
                "success": bool(plan.get("success")),
                "operation": plan.get("operation"),
                "command_shell": plan.get("command_shell"),
                "missing_params": plan.get("missing_params", []),
                "error": plan.get("error"),
            }
        )
    return plans


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a Terraform operations plan and optionally execute gated steps."""
    workdir = Path(args.workdir)
    targets = parse_import_targets(args.import_target)
    expected_token = state_change_token(args, targets)
    include_import = args.operation in {"import", "full"}
    include_drift = args.operation in {"drift", "full"}
    include_remote_state = args.operation in {"remote-state", "full"}
    import_plan = import_commands(targets) if include_import else []
    drift_plan = drift_commands() if include_drift else []
    result: dict[str, Any] = {
        "success": True,
        "mode": "execute" if (args.execute_drift or args.execute_import) else "plan",
        "operation": args.operation,
        "workdir": str(workdir),
        "import_targets": targets,
        "import_commands": import_plan,
        "drift_commands": drift_plan,
        "remote_state": remote_state_checks(args) if include_remote_state else None,
        "hcloud_readback": build_readback_plans(args),
        "state_change_gate": {
            "required_for": ["terraform import", "terraform init -migrate-state", "terraform state rm", "terraform state mv"],
            "confirm_token": expected_token,
            "allow_state_change_flag": "--allow-state-change",
        },
        "execution_boundary": "No terraform apply/destroy/state rm/state mv is generated. Import execution is gated by --allow-state-change and --confirm-token.",
    }
    if include_import and not targets:
        result["success"] = False
        result["error"] = "Import operation requires at least one --import-target ADDRESS=REMOTE_ID."
        return result
    if args.execute_drift:
        result["drift_execution"] = execute_drift(drift_plan, args)
    if args.execute_import:
        result["import_execution"] = execute_imports(import_plan, args, expected_token)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=OPERATIONS, default="full", help="Terraform operation workflow to plan.")
    parser.add_argument("--workdir", default=".", help="Terraform working directory.")
    parser.add_argument("--import-target", action="append", default=[], help="Terraform import target as ADDRESS=REMOTE_ID.")
    parser.add_argument("--readback", action="append", default=[], help="hcloud readback spec as SERVICE:OPERATION:KEY=VALUE[,KEY=VALUE].")
    parser.add_argument("--backend-type", help="Remote state backend type or label.")
    parser.add_argument("--region", help="Optional hcloud cli-region for readback plans.")
    parser.add_argument("--project-id", help="Optional project_id for readback plans.")
    parser.add_argument("--profile", help="Optional hcloud profile for readback plans.")
    parser.add_argument("--execute-drift", action="store_true", help="Execute terraform plan commands for drift review.")
    parser.add_argument("--execute-import", action="store_true", help="Execute terraform import commands after state-change confirmation.")
    parser.add_argument("--allow-state-change", action="store_true", help="Allow gated state-changing Terraform commands.")
    parser.add_argument("--confirm-token", help="Exact token from a prior plan, required for import execution.")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout for executed Terraform commands.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    try:
        result = build_plan(args)
    except (TerraformOperationsError, subprocess.TimeoutExpired, OSError) as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
