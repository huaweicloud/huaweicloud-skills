#!/usr/bin/env python3
"""Validate an ECS create cli-jsonInput file and build safe execution commands."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import hcloud_common  # noqa: E402
import hcloud_cost_estimate  # noqa: E402
import hcloud_operation_evidence  # noqa: E402
import hcloud_run_journal  # noqa: E402

PLACEHOLDER_PATTERN = re.compile(r"<[^<>]+>")
ALLOWED_OPERATIONS = ("CreateServers", "CreatePostPaidServers")
DEFAULT_SAFE_MAX_COUNT = 10
API_MAX_COUNT = 100
REQUIRED_PATHS: tuple[tuple[str | int, ...], ...] = (
    ("path", "project_id"),
    ("body", "server", "name"),
    ("body", "server", "availability_zone"),
    ("body", "server", "flavorRef"),
    ("body", "server", "imageRef"),
    ("body", "server", "vpcid"),
    ("body", "server", "nics", 0, "subnet_id"),
    ("body", "server", "root_volume", "volumetype"),
    ("body", "server", "count"),
)
SECURITY_GROUP_EVIDENCE_ERROR = (
    "Existing ECS security group reference requires rule evidence: provide "
    "--security-group-evidence-file from VPC ListSecurityGroupRules or ShowSecurityGroup before submit."
)


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a nested dict/list path for human-readable diagnostics."""
    parts: list[str] = []
    for item in path:
        if isinstance(item, int):
            if not parts:
                parts.append(f"[{item}]")
            else:
                parts[-1] = f"{parts[-1]}[{item}]"
        else:
            parts.append(item)
    return ".".join(parts)


def get_path_value(data: Any, path: tuple[str | int, ...]) -> tuple[bool, Any]:
    """Return whether a nested path exists and its value when present."""
    current = data
    for item in path:
        if isinstance(item, int):
            if not isinstance(current, list) or item >= len(current):
                return False, None
            current = current[item]
            continue
        if not isinstance(current, dict) or item not in current:
            return False, None
        current = current[item]
    return True, current


def iter_leaf_values(value: Any, path: tuple[str | int, ...] = ()) -> list[tuple[tuple[str | int, ...], Any]]:
    """Return leaf values and their nested paths."""
    if isinstance(value, dict):
        leaves: list[tuple[tuple[str | int, ...], Any]] = []
        for key, child in value.items():
            leaves.extend(iter_leaf_values(child, path + (key,)))
        return leaves
    if isinstance(value, list):
        leaves = []
        for index, child in enumerate(value):
            leaves.extend(iter_leaf_values(child, path + (index,)))
        return leaves
    return [(path, value)]


def find_placeholders(data: Any) -> list[dict[str, str]]:
    """Return unresolved placeholder string values in a JSON payload."""
    placeholders = []
    for path, value in iter_leaf_values(data):
        if isinstance(value, str) and PLACEHOLDER_PATTERN.search(value.strip()):
            placeholders.append({"path": format_path(path), "value": value})
    return placeholders


def is_empty_value(value: Any) -> bool:
    """Return True when a required value should be treated as empty."""
    return value is None or (isinstance(value, str) and not value.strip())


def detect_credential_mode(data: Any) -> str:
    """Return the SSH credential mode declared by an ECS create payload."""
    key_exists, key_name = get_path_value(data, ("body", "server", "key_name"))
    password_exists, admin_pass = get_path_value(data, ("body", "server", "adminPass"))
    has_key = key_exists and not is_empty_value(key_name)
    has_password = password_exists and not is_empty_value(admin_pass)
    if has_key and has_password:
        return "conflict"
    if has_key:
        return "keypair"
    if has_password:
        return "password"
    return "missing"


def referenced_security_group_ids(data: Any) -> list[str]:
    """Return security group IDs referenced by an ECS create payload."""
    exists, security_groups = get_path_value(data, ("body", "server", "security_groups"))
    if not exists or not isinstance(security_groups, list):
        return []
    ids: list[str] = []
    for item in security_groups:
        if not isinstance(item, dict):
            continue
        group_id = item.get("id")
        if isinstance(group_id, str) and group_id.strip():
            ids.append(group_id.strip())
    return ids


def security_group_rule_candidates(data: Any) -> list[dict[str, Any]]:
    """Return rule-like objects from security group readback evidence."""
    import hcloud_security_policy

    rule_markers = {
        "direction",
        "ethertype",
        "protocol",
        "remote_group_id",
        "remote_ip_prefix",
        "security_group_rule_id",
        "port_range_min",
        "port_range_max",
        "multiport",
    }
    rules: list[dict[str, Any]] = []
    for path, fields in hcloud_security_policy.iter_dict_candidates(data):
        normalized_fields = {hcloud_security_policy.normalize_key(key): value for key, value in fields.items()}
        if not set(normalized_fields).intersection(rule_markers):
            continue
        if not set(normalized_fields).intersection({"direction", "remote_ip_prefix", "remote_group_id", "protocol", "ethertype"}):
            continue
        rules.append(
            {
                "path": format_path(path),
                "id": normalized_fields.get("id") or normalized_fields.get("security_group_rule_id"),
                "security_group_id": normalized_fields.get("security_group_id"),
                "direction": normalized_fields.get("direction"),
                "protocol": normalized_fields.get("protocol"),
                "remote_ip_prefix": normalized_fields.get("remote_ip_prefix"),
                "port_range_min": normalized_fields.get("port_range_min"),
                "port_range_max": normalized_fields.get("port_range_max"),
            }
        )
    return rules


def validate_security_group_rule_evidence(
    data: Any,
    evidence: Any | None,
    source: str | None,
) -> dict[str, Any]:
    """Validate that referenced existing security groups have readback rule evidence."""
    security_group_ids = referenced_security_group_ids(data)
    summary: dict[str, Any] = {
        "required": bool(security_group_ids),
        "provided": evidence is not None,
        "source": source,
        "security_group_ids": security_group_ids,
        "rule_count": 0,
        "rules_sample": [],
        "errors": [],
    }
    if not security_group_ids:
        return summary
    if evidence is None:
        summary["errors"].append(SECURITY_GROUP_EVIDENCE_ERROR)
        return summary

    evidence_text = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    missing_mentions = [group_id for group_id in security_group_ids if group_id not in evidence_text]
    if missing_mentions:
        summary["errors"].append(
            "Security group rule evidence does not mention referenced security group ID(s): "
            + ", ".join(missing_mentions)
        )

    rules = security_group_rule_candidates(evidence)
    summary["rule_count"] = len(rules)
    summary["rules_sample"] = rules[:10]
    if not rules:
        summary["errors"].append(SECURITY_GROUP_EVIDENCE_ERROR)
    return summary


def read_optional_json(path: str | None) -> tuple[Any | None, list[str]]:
    """Read an optional JSON artifact and return non-fatal validation errors."""
    if not path:
        return None, []
    try:
        return hcloud_common.load_json(Path(path)), []
    except FileNotFoundError:
        return None, [f"Security group evidence file not found: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"Invalid security group evidence JSON file: {exc}"]


def validate_payload(
    data: Any,
    allow_placeholders: bool = False,
    max_count: int = DEFAULT_SAFE_MAX_COUNT,
    allow_large_count: bool = False,
    security_group_evidence: Any | None = None,
    allow_public_web: bool = False,
) -> dict[str, Any]:
    """Validate an ECS create cli-jsonInput payload without calling Huawei Cloud."""
    import hcloud_security_policy

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["Top-level JSON value must be an object."],
            "warnings": [],
            "unresolved_placeholders": [],
            "credential_mode": "invalid",
            "policy_violations": [],
            "security_group_rule_evidence": {
                "required": False,
                "provided": False,
                "source": None,
                "security_group_ids": [],
                "rule_count": 0,
                "rules_sample": [],
                "errors": [],
            },
        }

    for path in REQUIRED_PATHS:
        exists, value = get_path_value(data, path)
        path_text = format_path(path)
        if not exists:
            errors.append(f"Missing required field: {path_text}")
            continue
        if is_empty_value(value):
            errors.append(f"Required field is empty: {path_text}")

    exists, count_value = get_path_value(data, ("body", "server", "count"))
    if exists and not isinstance(count_value, int):
        errors.append("body.server.count must be an integer.")
    elif exists and count_value < 1:
        errors.append("body.server.count must be greater than 0.")
    elif exists and count_value > API_MAX_COUNT:
        errors.append(f"body.server.count must be less than or equal to {API_MAX_COUNT}.")
    elif exists and count_value > max_count and not allow_large_count:
        errors.append(
            f"body.server.count exceeds conservative max {max_count}. "
            "Use --allow-large-count only after confirming cost and quota impact."
        )

    credential_mode = detect_credential_mode(data)
    if credential_mode == "missing":
        errors.append(
            "No SSH login credential configured: set exactly one of body.server.key_name or body.server.adminPass."
        )
    elif credential_mode == "conflict":
        errors.append(
            "Conflicting SSH login credentials: body.server.key_name and body.server.adminPass must not both be set."
        )
    elif credential_mode == "keypair":
        warnings.append(
            "SSH credential mode is keypair; confirm the matching private key exists locally with 0600 permissions before submit."
        )
    elif credential_mode == "password":
        warnings.append(
            "SSH credential mode is password; body.server.adminPass must be generated and saved to a restricted credential artifact before submit."
        )

    security_group_exists, security_group_id = get_path_value(data, ("body", "server", "security_groups", 0, "id"))
    if not security_group_exists or is_empty_value(security_group_id):
        warnings.append(
            "No body.server.security_groups[0].id found. Huawei Cloud may bind the default security group, "
            "but network exposure rules should be reviewed before submit."
        )
    inline_security_group_rules = security_group_rule_candidates(data)
    effective_security_group_evidence = security_group_evidence
    evidence_source = "security_group_evidence_file" if security_group_evidence is not None else None
    if effective_security_group_evidence is None and inline_security_group_rules:
        effective_security_group_evidence = data
        evidence_source = "inline_payload"
        warnings.append(
            "Security group rule evidence was found inline in the ECS JSON. Prefer --security-group-evidence-file "
            "so local evidence does not get mixed into the cli-jsonInput body."
        )
    security_group_rule_evidence = validate_security_group_rule_evidence(
        data,
        effective_security_group_evidence,
        evidence_source,
    )
    errors.extend(security_group_rule_evidence["errors"])

    exists, data_volumes = get_path_value(data, ("body", "server", "data_volumes"))
    if exists:
        if not isinstance(data_volumes, list):
            errors.append("body.server.data_volumes must be a list when present.")
        else:
            for index, volume in enumerate(data_volumes):
                if not isinstance(volume, dict):
                    errors.append(f"body.server.data_volumes[{index}] must be an object.")
                    continue
                size = volume.get("size")
                if size is not None and (not isinstance(size, int) or size < 1):
                    errors.append(f"body.server.data_volumes[{index}].size must be a positive integer.")

    placeholders = find_placeholders(data)
    if placeholders and not allow_placeholders:
        for item in placeholders:
            errors.append(f"Unresolved placeholder at {item['path']}: {item['value']}")

    exists, publicip = get_path_value(data, ("body", "server", "publicip"))
    if not exists:
        warnings.append("No publicip block found. The ECS may be private-only unless network access is configured elsewhere.")
    elif not isinstance(publicip, dict):
        errors.append("body.server.publicip must be an object when present.")

    policy_violations = hcloud_security_policy.check_json_payload(
        data,
        allow_public_web=allow_public_web,
    )
    if security_group_evidence is not None:
        policy_violations.extend(
            hcloud_security_policy.check_json_payload(
                security_group_evidence,
                allow_public_web=allow_public_web,
            )
        )
    for violation in policy_violations:
        errors.append(f"Security group policy violation at {violation['path']}: {violation['message']}")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "unresolved_placeholders": placeholders,
        "credential_mode": credential_mode if isinstance(data, dict) else "invalid",
        "policy_violations": policy_violations,
        "security_group_rule_evidence": security_group_rule_evidence,
    }


def build_safe_exec_command(args: argparse.Namespace, json_input_file: Path) -> list[str]:
    """Build the hcloud_safe_exec.py command for the requested ECS create operation."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        "ECS",
        "--operation",
        args.operation,
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    if args.region:
        command.append(f"--arg=--cli-region={args.region}")
    if args.mode == "dryrun":
        command.append("--arg=--dryrun")
    command.extend(
        [
            "--arg=--cli-output=json",
            f"--json-input-file={json_input_file}",
            "--expect-json",
            "--pretty",
        ]
    )
    return command


def build_hcloud_command(args: argparse.Namespace, json_input_file: Path) -> list[str]:
    """Build the direct hcloud command for review or manual execution."""
    command = ["hcloud", "ECS", args.operation]
    if args.profile:
        command.append(f"--cli-profile={args.profile}")
    if args.region:
        command.append(f"--cli-region={args.region}")
    if args.mode == "dryrun":
        command.append("--dryrun")
    command.append(f"--cli-jsonInput={json_input_file}")
    return command


def build_next_steps(args: argparse.Namespace, validation: dict[str, Any]) -> list[str]:
    """Return concise next-step guidance for the current plan result."""
    if validation["errors"]:
        return [
            "Fix the validation errors before running dry-run.",
            "Re-run this script after replacing placeholders with real resource IDs.",
        ]
    if validation["unresolved_placeholders"]:
        return [
            "This payload still contains placeholders and should be treated as a template only.",
            "Replace placeholders with real resource IDs before generating dry-run or submit commands.",
        ]
    if args.mode == "dryrun":
        steps = [
            "Run the safe_exec dry-run command and inspect the returned request or error.",
            "Only after dry-run passes, rerun this script with --mode submit --confirm-submit to build a non-dryrun command.",
        ]
    else:
        steps = [
            "Execute the submit command only after user confirmation because it can create billable resources.",
            "Capture the returned job_id and poll it with scripts/hcloud_ecs_wait_job.py until terminal status.",
            "After the ECS is ACTIVE, verify SSH with the selected credential before declaring the server login-ready.",
        ]
    credential_mode = validation.get("credential_mode")
    if credential_mode == "keypair":
        steps.append("Before submit, verify the local private key that matches body.server.key_name and keep it chmod 600.")
    elif credential_mode == "password":
        steps.append("Before submit, save body.server.adminPass to a restricted credential artifact because Linux passwords cannot be retrieved later.")
    return steps


def operation_behavior(operation: str) -> dict[str, Any] | None:
    """Return ECS create batch and convergence evidence for Agent orchestration."""

    return hcloud_operation_evidence.operation_evidence_fields(
        "ECS",
        operation,
    ).get("operation_behavior")


def build_ecs_cost_estimate(
    payload: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Build a compute-only provider quote plan from a valid ECS request."""

    exists_project, project_id = get_path_value(payload, ("path", "project_id"))
    exists_flavor, flavor = get_path_value(
        payload,
        ("body", "server", "flavorRef"),
    )
    exists_count, count = get_path_value(payload, ("body", "server", "count"))
    exists_az, availability_zone = get_path_value(
        payload,
        ("body", "server", "availability_zone"),
    )
    exists_period_type, period_type = get_path_value(
        payload,
        ("body", "server", "extendparam", "periodType"),
    )
    exists_period_num, period_num = get_path_value(
        payload,
        ("body", "server", "extendparam", "periodNum"),
    )
    scope_values_ready = all(
        (exists_project, exists_flavor, exists_count)
    ) and isinstance(count, int)
    period_scope_ready = (
        args.operation == "CreateServers"
        and exists_period_type
        and bool(str(period_type).strip())
        and exists_period_num
        and isinstance(period_num, int)
        and period_num > 0
    )
    if args.operation == "CreateServers" and not period_scope_ready:
        return hcloud_cost_estimate.unknown_cost_estimate(
            service="ECS",
            operation=args.operation,
            region=args.region,
            reason=(
                "Period pricing needs an explicit period type and period count; "
                "the ECS request is not used to guess that commercial choice."
            ),
            reason_code="PERIOD_PRICING_SCOPE_INCOMPLETE",
            quantity=count if isinstance(count, int) else None,
            resource_spec=[str(flavor)] if exists_flavor else [],
            components_included=["ECS compute"],
            components_excluded=hcloud_cost_estimate.SERVICE_EXCLUDED_COMPONENTS[
                "ECS"
            ],
        )
    if not scope_values_ready or not args.region:
        return hcloud_cost_estimate.unknown_cost_estimate(
            service="ECS",
            operation=args.operation,
            region=args.region,
            reason=(
                "ECS compute quote planning requires project_id, region, flavor, "
                "and count from the validated request."
            ),
            quantity=count if isinstance(count, int) else None,
            resource_spec=[str(flavor)] if exists_flavor else [],
            components_included=["ECS compute"],
            components_excluded=hcloud_cost_estimate.SERVICE_EXCLUDED_COMPONENTS[
                "ECS"
            ],
        )
    charge_mode = (
        "period" if args.operation == "CreateServers" else "on_demand"
    )
    result = hcloud_cost_estimate.build_cost_estimate(
        SimpleNamespace(
            service="ECS",
            region=args.region,
            project_id=str(project_id),
            charge_mode=charge_mode,
            pricing_preset="ecs",
            resource_spec=[str(flavor)],
            quantity=count,
            resource_size=[],
            size_measure_id=[],
            usage_value=[] if charge_mode == "period" else [1.0],
            available_zone=str(availability_zone) if exists_az else None,
            period_type=[str(period_type)] if charge_mode == "period" else [],
            period_num=[period_num] if charge_mode == "period" else [],
            fee_installment_mode=None,
            execute=False,
            confirm_live_billing_read=None,
            timeout=120,
            max_output_chars=20000,
            output_file=None,
            pretty=False,
        )
    )
    estimate = result["cost_estimate"]
    estimate["scope"]["operation"] = args.operation
    return estimate


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """Build a validation and command plan for an ECS create JSON file."""
    json_input_file = Path(args.json_input_file)
    errors: list[str] = []
    warnings: list[str] = []
    payload: Any = None

    if args.mode == "submit" and not args.confirm_submit:
        errors.append("Non-dryrun submit mode requires --confirm-submit.")

    if not args.region:
        warnings.append("No --region provided. Generated commands will rely on the active hcloud profile region.")

    try:
        payload = hcloud_common.load_json(json_input_file)
        security_group_evidence, evidence_errors = read_optional_json(
            getattr(args, "security_group_evidence_file", None)
        )
        validation = validate_payload(
            payload,
            allow_placeholders=args.allow_placeholders,
            max_count=getattr(args, "max_count", DEFAULT_SAFE_MAX_COUNT),
            allow_large_count=getattr(args, "allow_large_count", False),
            security_group_evidence=security_group_evidence,
            allow_public_web=bool(getattr(args, "allow_public_web", False)),
        )
        if evidence_errors:
            validation["errors"].extend(evidence_errors)
            validation["valid"] = False
    except FileNotFoundError:
        validation = {
            "valid": False,
            "errors": [f"JSON input file not found: {json_input_file}"],
            "warnings": [],
            "unresolved_placeholders": [],
            "policy_violations": [],
            "security_group_rule_evidence": {
                "required": False,
                "provided": False,
                "source": None,
                "security_group_ids": [],
                "rule_count": 0,
                "rules_sample": [],
                "errors": [],
            },
        }
    except json.JSONDecodeError as exc:
        validation = {
            "valid": False,
            "errors": [f"Invalid JSON input file: {exc}"],
            "warnings": [],
            "unresolved_placeholders": [],
            "policy_violations": [],
            "security_group_rule_evidence": {
                "required": False,
                "provided": False,
                "source": None,
                "security_group_ids": [],
                "rule_count": 0,
                "rules_sample": [],
                "errors": [],
            },
        }

    all_errors = errors + validation["errors"]
    all_warnings = warnings + validation["warnings"]
    validation = dict(validation)
    validation["errors"] = all_errors
    validation["warnings"] = all_warnings
    validation["valid"] = not all_errors

    ready_to_run = validation["valid"] and not validation["unresolved_placeholders"]
    commands = {
        "safe_exec": build_safe_exec_command(args, json_input_file),
        "safe_exec_shell": shlex.join(build_safe_exec_command(args, json_input_file)),
        "hcloud": build_hcloud_command(args, json_input_file),
        "hcloud_shell": shlex.join(build_hcloud_command(args, json_input_file)),
    } if ready_to_run else {}
    cost_estimate = build_ecs_cost_estimate(payload, args)

    result = {
        "success": validation["valid"],
        "ready_to_run": ready_to_run,
        "operation": args.operation,
        **hcloud_operation_evidence.operation_evidence_fields("ECS", args.operation),
        "mode": args.mode,
        "json_input_file": str(json_input_file),
        "validation": validation,
        "cost_estimate": cost_estimate,
        "commands": commands,
        "next_steps": build_next_steps(args, validation),
    }
    if getattr(args, "allow_public_web", False):
        result["public_web_exposure"] = {
            "enabled": True,
            "allowed_protocol": "tcp",
            "allowed_ports": [80, 443],
            "allowed_ipv4_source": "0.0.0.0/0",
        }
        result["next_steps"].append(
            "After creation, read back the security group rules and verify HTTP/HTTPS from outside the VPC before declaring the website reachable."
        )
    journal = getattr(args, "journal", None)
    if journal:
        hcloud_run_journal.append_event(
            Path(journal),
            {
                "type": "plan",
                "stage": "ecs_create_plan",
                "service": "ECS",
                "operation": args.operation,
                "mode": args.mode,
                "success": bool(result["success"]),
                "ready_to_run": ready_to_run,
                "validation": validation,
                "cost_estimate": cost_estimate,
                "commands": commands,
            },
        )
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-input-file", required=True, help="Path to the ECS cli-jsonInput JSON file.")
    parser.add_argument(
        "--operation",
        choices=ALLOWED_OPERATIONS,
        default="CreateServers",
        help="ECS create operation to plan.",
    )
    parser.add_argument("--region", help="Explicit cli-region for the generated command.")
    parser.add_argument("--profile", help="Optional cli-profile for the generated command.")
    parser.add_argument(
        "--mode",
        choices=("dryrun", "submit"),
        default="dryrun",
        help="Generate a dry-run command by default. Submit mode omits --dryrun.",
    )
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="Required with --mode submit to generate a non-dryrun create command.",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow placeholder values such as <project_id> to remain in the JSON file.",
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=DEFAULT_SAFE_MAX_COUNT,
        help=f"Conservative local count limit before --allow-large-count is required. Default: {DEFAULT_SAFE_MAX_COUNT}.",
    )
    parser.add_argument(
        "--allow-large-count",
        action="store_true",
        help="Allow body.server.count above --max-count after confirming cost and quota impact.",
    )
    parser.add_argument(
        "--allow-public-web",
        action="store_true",
        help=(
            "Allow exact TCP 80/443 ingress from 0.0.0.0/0 for a user-confirmed public website plan. "
            "This does not replace --confirm-submit."
        ),
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    parser.add_argument("--journal", help="Optional JSONL journal path for validation/command-plan events.")
    parser.add_argument(
        "--security-group-evidence-file",
        help="JSON readback evidence from VPC ListSecurityGroupRules or ShowSecurityGroup for referenced security groups.",
    )
    args = parser.parse_args()
    if args.max_count < 1:
        parser.error("--max-count must be at least 1.")
    if args.max_count > API_MAX_COUNT:
        parser.error(f"--max-count must be less than or equal to {API_MAX_COUNT}.")
    return args


def main() -> int:
    """Run the ECS create planner and print a structured JSON result."""
    args = parse_args()
    result = build_result(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
