#!/usr/bin/env python3
"""Create a risk-gated plan for Huawei Cloud change operations."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_cost_estimate
import hcloud_request_preflight
import hcloud_security_policy
from hcloud_core import CommandPlan, RiskAssessment

READ_ONLY_ACTIONS = ("List", "Show", "Count", "Check", "Search", "Query", "Get", "Download")
DESTRUCTIVE_ACTIONS = (
    "Clear",
    "Delete",
    "Detach",
    "Disable",
    "Disassociate",
    "Reboot",
    "Remove",
    "Reset",
    "Revoke",
    "Stop",
    "Unbind",
    "Unsubscribe",
)
BILLABLE_ACTIONS = ("Add", "Associate", "Attach", "Bind", "Create", "Import", "Start")
MUTATING_ACTIONS = (
    *BILLABLE_ACTIONS,
    "Accept",
    "Batch",
    "Change",
    "Copy",
    "Enable",
    "Execute",
    "Expand",
    "Extend",
    "Export",
    "Migrate",
    "Modify",
    "Move",
    "Redeploy",
    "Resize",
    "Restore",
    "Retype",
    "Set",
    "Switch",
    "Update",
)
KNOWN_ACTIONS = set(READ_ONLY_ACTIONS + DESTRUCTIVE_ACTIONS + BILLABLE_ACTIONS + MUTATING_ACTIONS)
HIGH_RISK_CONTEXT_TERMS = ("Os", "Password", "PrivateKey", "Private", "Key", "Credential", "Secret", "Token")
NAMESPACE_OR_MODIFIER_TOKENS = ("Batch", "Nova", "Neutron", "Glance", "Cinder", "Keystone")
HARD_GUARD_CATEGORIES = {"security & compliance"}
HARD_GUARD_SERVICES = {
    "BSS",
    "IAM",
    "IAMACCESSANALYZER",
    "IDENTITYCENTER",
    "IDENTITYCENTEROIDC",
    "IDENTITYCENTERPORTALAPI",
    "IDENTITYCENTERSCIM",
    "IDENTITYCENTERSTORE",
    "KMS",
    "ORGANIZATIONS",
    "RAM",
    "RGC",
    "RMS",
    "STS",
}
MEDIUM_FLOOR_CATEGORIES = {"management & governance"}
LOWERCASE_SCAN_TOKENS = set(KNOWN_ACTIONS).union(
    NAMESPACE_OR_MODIFIER_TOKENS,
    {"Os", "Password", "PrivateKey", "Private", "Credential", "Secret", "Token", "Flag", "Policy", "Policies"},
)
CANONICAL_TOKENS_BY_LOWER = {token.lower(): token for token in LOWERCASE_SCAN_TOKENS.union(HIGH_RISK_CONTEXT_TERMS)}


def operation_tokens(operation: str) -> list[str]:
    """Split a Huawei Cloud operation name into semantic tokens."""
    operation_name = operation.split("-", 1)[-1]
    operation_name = re.sub(r"[^A-Za-z0-9]+", " ", operation_name)
    tokens: list[str] = []
    for piece in operation_name.split():
        if not any(char.isupper() for char in piece):
            tokens.extend(split_lowercase_operation(piece))
            continue
        raw_tokens = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+", piece)
        tokens.extend(CANONICAL_TOKENS_BY_LOWER.get(token.lower(), token) for token in raw_tokens)
    return tokens


def split_lowercase_operation(operation_name: str) -> list[str]:
    """Extract known action and sensitive-context tokens from a lowercase operation name."""
    matches: list[tuple[int, int, str]] = []
    lowered = operation_name.lower()
    for token in LOWERCASE_SCAN_TOKENS:
        index = lowered.find(token.lower())
        if index >= 0:
            matches.append((index, -len(token), token))

    ordered_tokens: list[str] = []
    seen: set[str] = set()
    for _, _, token in sorted(matches):
        if token in seen:
            continue
        ordered_tokens.append(token)
        seen.add(token)
    return ordered_tokens or [operation_name]


def operation_prefix(operation: str) -> str | None:
    """Return the first recognized action token in an operation name."""
    return first_action_token(operation_tokens(operation))


def first_action_token(tokens: list[str]) -> str | None:
    """Return the first non-namespace action token from parsed operation tokens."""
    for token in tokens:
        if token in KNOWN_ACTIONS:
            return token
    return None


def has_high_risk_context(tokens: list[str]) -> bool:
    """Return True when a medium verb targets especially sensitive state."""
    token_set = set(tokens)
    if "Change" in token_set and "Os" in token_set:
        return True
    if token_set.intersection({"Reset", "Export", "Clear"}) and token_set.intersection(HIGH_RISK_CONTEXT_TERMS):
        return True
    return False


def has_sensitive_read_context(tokens: list[str]) -> bool:
    """Return True when a read-only operation can expose secrets."""
    token_set = set(tokens)
    if token_set.intersection({"Credential", "Secret", "Token"}):
        return True
    if "Password" in token_set and not token_set.intersection({"Flag", "Policy", "Policies"}):
        return True
    if "PrivateKey" in token_set or {"Private", "Key"}.issubset(token_set):
        return True
    return False


def looks_read_only(tokens: list[str]) -> bool:
    """Return True when the operation appears to be a read-only query."""
    return first_action_token(tokens) in READ_ONLY_ACTIONS


def apply_metadata_risk_floor(
    *,
    operation: str,
    tokens: list[str],
    service: str | None,
    metadata_category: str | None,
    dryrun_supported: bool,
    level: str,
    requires_confirmation: bool,
    dryrun_required: bool,
    verification_required: bool,
    hard_guard: bool,
    reasons: list[str],
) -> tuple[str, bool, bool, bool, bool]:
    """Raise risk based on metadata service/category without lowering name-based risk."""
    if looks_read_only(tokens):
        return level, requires_confirmation, dryrun_required, verification_required, hard_guard

    service_key = (service or "").replace("-", "").replace("_", "").upper()
    category_key = (metadata_category or "").strip().lower()
    category_label = metadata_category or "unknown category"

    if category_key in HARD_GUARD_CATEGORIES or service_key in HARD_GUARD_SERVICES:
        if level != "high":
            level = "high"
        requires_confirmation = True
        verification_required = True
        dryrun_required = dryrun_supported
        hard_guard = True
        if category_key in HARD_GUARD_CATEGORIES:
            reasons.append(
                f"Service category '{category_label}' is security-sensitive; metadata-backed mutations require a hard manual gate."
            )
        else:
            reasons.append(
                f"Service '{service or service_key}' controls identity, governance, key, or policy state; mutations require a hard manual gate."
            )
    elif category_key in MEDIUM_FLOOR_CATEGORIES and level == "low":
        level = "medium"
        requires_confirmation = True
        verification_required = True
        dryrun_required = dryrun_supported
        reasons.append(
            f"Service category '{category_label}' can affect governance state; risk was raised to medium."
        )

    return level, requires_confirmation, dryrun_required, verification_required, hard_guard


def assess_risk(
    operation: str,
    dryrun_supported: bool,
    service: str | None = None,
    metadata_category: str | None = None,
) -> RiskAssessment:
    """Assess risk for a cloud operation from its name and optional metadata context."""
    tokens = operation_tokens(operation)
    action_tokens = [token for token in tokens if token in KNOWN_ACTIONS and token not in NAMESPACE_OR_MODIFIER_TOKENS]
    reasons: list[str] = []
    level = "low"
    requires_confirmation = False
    dryrun_required = False
    verification_required = False
    hard_guard = False

    destructive_matches = [token for token in action_tokens if token in DESTRUCTIVE_ACTIONS]
    billable_matches = [token for token in action_tokens if token in BILLABLE_ACTIONS]
    mutating_matches = [
        token
        for token in action_tokens
        if token in MUTATING_ACTIONS and token not in READ_ONLY_ACTIONS and token not in DESTRUCTIVE_ACTIONS
    ]

    if looks_read_only(tokens) and has_sensitive_read_context(tokens):
        level = "high"
        requires_confirmation = True
        reasons.append("Operation is read-only but can expose password, private key, credential, secret, or token data.")
    elif looks_read_only(tokens):
        reasons.append("Operation appears to be read-only.")
    elif destructive_matches or has_high_risk_context(tokens):
        level = "high"
        requires_confirmation = True
        dryrun_required = dryrun_supported
        verification_required = True
        if destructive_matches:
            reasons.append(
                f"Matched destructive action token(s): {', '.join(sorted(set(destructive_matches)))}."
            )
        if has_high_risk_context(tokens):
            reasons.append("Matched sensitive context such as OS, password, key, credential, secret, or token state.")
    elif billable_matches or mutating_matches:
        level = "medium"
        requires_confirmation = True
        dryrun_required = dryrun_supported
        verification_required = True
        if billable_matches:
            reasons.append(f"Matched billable or binding action token(s): {', '.join(sorted(set(billable_matches)))}.")
        if mutating_matches:
            reasons.append(f"Matched mutating action token(s): {', '.join(sorted(set(mutating_matches)))}.")
    else:
        level = "medium"
        requires_confirmation = True
        dryrun_required = dryrun_supported
        verification_required = True
        reasons.append("Operation is not recognized as read-only; use a conservative change gate.")

    if not reasons:
        reasons.append("No elevated risk was inferred from the operation name.")

    level, requires_confirmation, dryrun_required, verification_required, hard_guard = apply_metadata_risk_floor(
        operation=operation,
        tokens=tokens,
        service=service,
        metadata_category=metadata_category,
        dryrun_supported=dryrun_supported,
        level=level,
        requires_confirmation=requires_confirmation,
        dryrun_required=dryrun_required,
        verification_required=verification_required,
        hard_guard=hard_guard,
        reasons=reasons,
    )

    return RiskAssessment(
        level=level,
        reasons=reasons,
        requires_confirmation=requires_confirmation,
        dryrun_required=dryrun_required,
        verification_required=verification_required,
        hard_guard=hard_guard,
    )


def build_command(args: argparse.Namespace, use_dryrun: bool) -> list[str]:
    """Build a safe_exec command for a planned change operation."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        args.service,
        "--operation",
        args.operation,
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    if args.region:
        command.append(f"--arg=--cli-region={args.region}")
    if args.project_id:
        command.append(f"--arg=--project_id={args.project_id}")
    for item in args.arg:
        command.append(f"--arg={item}")
    if use_dryrun:
        command.append("--arg=--dryrun")
    if args.json_input_file:
        command.append(f"--json-input-file={args.json_input_file}")
    return command


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a risk-gated change plan without executing it."""
    allow_public_web = bool(getattr(args, "allow_public_web", False))
    risk = assess_risk(
        args.operation,
        dryrun_supported=not args.no_dryrun,
        service=args.service,
        metadata_category=getattr(args, "metadata_category", None),
    )
    cost_estimate = hcloud_cost_estimate.unknown_cost_estimate(
        service=args.service,
        operation=args.operation,
        region=args.region,
        reason=(
            "This generic change plan has no executed provider quote. Use "
            "hcloud_cost_estimate.py with an exact billable SKU before making a cost claim."
        ),
        reason_code="PROVIDER_QUOTE_NOT_EXECUTED",
    )
    policy_check = hcloud_security_policy.check_change_inputs(
        args.arg,
        args.json_input_file,
        allow_public_web=allow_public_web,
    )
    policy_violations = policy_check["violations"]
    if policy_violations:
        return {
            "success": False,
            "service": args.service,
            "operation": args.operation,
            "risk": risk.to_dict(),
            "cost_estimate": cost_estimate,
            "policy_violations": policy_violations,
            "policy_scan_error": policy_check["scan_error"],
            "commands": {},
            "next_steps": [
                "Replace 0.0.0.0/0 with a restricted source CIDR before planning or submitting the security group change.",
                "For SSH, prefer a fixed administrator IP, VPN CIDR, bastion host, or private management network.",
                "For HTTP/Web ports, use the expected client CIDR, load balancer source range, private CIDR, or an explicitly approved allowlist.",
                "Re-run the planner after updating the source range.",
            ],
        }

    request_preflight: dict[str, Any] | None = None
    if args.json_input_file:
        request_preflight = hcloud_request_preflight.preflight_request_file(
            args.service,
            args.operation,
            Path(args.json_input_file),
            direct_arguments=args.arg,
            project_id=args.project_id,
        )
        if not request_preflight.get("success"):
            return {
                "success": False,
                "service": args.service,
                "operation": args.operation,
                "risk": risk.to_dict(),
                "cost_estimate": cost_estimate,
                "request_preflight": request_preflight,
                "policy_violations": [],
                "policy_scan_error": policy_check["scan_error"],
                "commands": {},
                "next_steps": [
                    "Fix the local request preflight errors before generating or running dry-run and submit commands.",
                    "Use the reported request_contract and exact-version SDK schema evidence; do not guess nested fields.",
                    "Re-run hcloud_request_preflight.py, then rebuild this change plan.",
                ],
            }
    dryrun_command = build_command(args, use_dryrun=risk.dryrun_required)
    submit_command = build_command(args, use_dryrun=False)
    warnings: list[str] = []
    if not args.region:
        warnings.append("No --region provided. Generated commands will rely on the active hcloud profile region.")
    if risk.requires_confirmation:
        if risk.verification_required:
            warnings.append("Do not run the submit command until the user has confirmed cost, scope, and rollback expectations.")
        else:
            warnings.append("Do not run the command until the user has confirmed sensitive output scope and handling expectations.")
    if risk.hard_guard:
        warnings.append("This operation is under a hard manual gate; generic guarded flows must not execute submit automatically.")
    if risk.dryrun_required and args.no_dryrun:
        warnings.append("Dry-run was disabled by --no-dryrun; use only when the operation does not support dry-run.")
    if allow_public_web:
        warnings.append(
            "Explicit public Web exposure is enabled for planning. Only exact TCP 80/443 rules may use 0.0.0.0/0; "
            "submit still requires review and user confirmation."
        )
    if policy_check["scan_error"]:
        warnings.append(policy_check["scan_error"])
    if request_preflight and request_preflight.get("validation_status") == "partial":
        warnings.append(
            "Local request preflight passed with partial schema evidence; dry-run or operation help must validate the remaining fields before submit."
        )

    command_plan = CommandPlan(
        service=args.service,
        operation=args.operation,
        command=dryrun_command,
        mode="dryrun" if risk.dryrun_required else "plan",
        dryrun_required=risk.dryrun_required,
        warnings=warnings,
    )

    result = {
        "success": True,
        "service": args.service,
        "operation": args.operation,
        "risk": risk.to_dict(),
        "cost_estimate": cost_estimate,
        "plan": command_plan.to_dict(),
        "commands": {
            "dryrun_or_plan": dryrun_command,
            "dryrun_or_plan_shell": shlex.join(dryrun_command),
            "submit": submit_command,
            "submit_shell": shlex.join(submit_command),
        },
        "next_steps": [
            "Run the dry-run or plan command first when supported.",
            "Review returned request body, target project, cost impact, and rollback path.",
            "Only then run the submit command after explicit user confirmation.",
            "Verify job, resource, network, and protocol state according to the target service.",
        ],
    }
    if request_preflight is not None:
        result["request_preflight"] = request_preflight
    if allow_public_web:
        result["public_web_exposure"] = {
            "enabled": True,
            "allowed_protocol": "tcp",
            "allowed_ports": [80, 443],
            "allowed_ipv4_source": "0.0.0.0/0",
        }
        result["next_steps"].append(
            "After submit, read back the security group rule and verify the intended HTTP/HTTPS endpoint from outside the VPC."
        )
    if risk.hard_guard:
        result["hard_guard"] = True
        result["next_steps"] = [
            "Treat this as a hard-gated change because the service/category can affect security, identity, key, or governance state.",
            *result["next_steps"],
            "Do not execute this submit command through a generic auto-submit flow; require a separate human-reviewed runbook or service-specific planner.",
        ]
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Huawei Cloud service name, for example ECS.")
    parser.add_argument("--operation", required=True, help="Change operation name, for example CreateServers.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--json-input-file", help="Optional JSON input file to pass via --cli-jsonInput.")
    parser.add_argument("--arg", action="append", default=[], help="Additional raw hcloud argument token.")
    parser.add_argument("--no-dryrun", action="store_true", help="Do not add --dryrun even when the operation is risky.")
    parser.add_argument(
        "--allow-public-web",
        action="store_true",
        help=("Allow exact TCP 80/443 ingress from 0.0.0.0/0 for a user-confirmed public website plan. This does not authorize submit."),
    )
    parser.add_argument("--metadata-category", help="Optional service category from generated hcloud catalog for risk floors.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build and print a risk-gated change plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
