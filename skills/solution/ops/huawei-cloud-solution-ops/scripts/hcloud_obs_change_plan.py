#!/usr/bin/env python3
"""Create non-executing OBS obsutil change plans."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

import hcloud_change_plan
import hcloud_common
import hcloud_obs_readonly
import hcloud_resource_discovery
from hcloud_core import CommandPlan

CHANGE_OPERATIONS = {
    "CreateBucket": {
        "parts": ("mb", "{bucket_url}"),
        "requires_bucket": True,
        "requires_local_file": False,
        "verification_operation": "StatBucket",
    },
    "DeleteBucket": {
        "parts": ("rm", "{bucket_url}"),
        "requires_bucket": True,
        "requires_local_file": False,
        "verification_operation": "ListBuckets",
    },
    "PutBucketLifecycle": {
        "parts": ("lifecycle", "{bucket_url}", "-method=put", "-localfile={local_file}"),
        "requires_bucket": True,
        "requires_local_file": True,
        "verification_operation": "GetBucketLifecycle",
    },
    "DeleteBucketLifecycle": {
        "parts": ("lifecycle", "{bucket_url}", "-method=delete"),
        "requires_bucket": True,
        "requires_local_file": False,
        "verification_operation": "GetBucketLifecycle",
    },
    "PutBucketPolicy": {
        "parts": ("bucketpolicy", "{bucket_url}", "-method=put", "-localfile={local_file}"),
        "requires_bucket": True,
        "requires_local_file": True,
        "verification_operation": "GetBucketPolicy",
    },
    "DeleteBucketPolicy": {
        "parts": ("bucketpolicy", "{bucket_url}", "-method=delete"),
        "requires_bucket": True,
        "requires_local_file": False,
        "verification_operation": "GetBucketPolicy",
    },
}
OPERATION_ALIASES = {
    "SetBucketLifecycle": "PutBucketLifecycle",
    "UpdateBucketLifecycle": "PutBucketLifecycle",
    "CreateBucketLifecycle": "PutBucketLifecycle",
    "SetBucketPolicy": "PutBucketPolicy",
    "UpdateBucketPolicy": "PutBucketPolicy",
}
PUBLIC_ACLS = {"public-read", "public-read-write"}


def canonical_operation(operation: str) -> str | None:
    """Resolve a user-facing OBS change operation to a supported operation."""
    aliased = OPERATION_ALIASES.get(operation, operation)
    normalized = hcloud_resource_discovery.normalize_operation(aliased)
    for candidate in CHANGE_OPERATIONS:
        if hcloud_resource_discovery.normalize_operation(candidate) == normalized:
            return candidate
    return None


def local_file_arg(args: argparse.Namespace) -> str | None:
    """Return the local file path used by obsutil put-style operations."""
    return args.local_file or args.json_input_file


def command_parts(args: argparse.Namespace, operation: str) -> list[str]:
    """Return `hcloud obs` command parts for one planned change operation."""
    spec = CHANGE_OPERATIONS[operation]
    if spec["requires_bucket"] and not args.bucket:
        raise ValueError(f"{operation} requires --bucket.")
    local_file = local_file_arg(args)
    if spec["requires_local_file"] and not local_file:
        raise ValueError(f"{operation} requires --local-file or --json-input-file.")

    replacements = {
        "bucket_url": hcloud_obs_readonly.bucket_url(args.bucket) if args.bucket else "",
        "local_file": local_file or "",
    }
    parts = [item.format(**replacements) for item in spec["parts"]]
    if args.endpoint:
        parts.append(f"-e={args.endpoint}")
    if args.config:
        parts.append(f"-config={args.config}")
    if args.payer:
        parts.append(f"-payer={args.payer}")
    for raw_arg in args.arg:
        hcloud_obs_readonly.validate_raw_obs_arg(raw_arg)
        parts.append(raw_arg)
    return parts


def json_path(parent: str, key: str | int) -> str:
    """Return a simple JSON path for policy-risk findings."""
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent else str(key)


def contains_public_wildcard(value: Any) -> bool:
    """Return True when a policy value grants access to every principal/resource."""
    if value == "*":
        return True
    if isinstance(value, list):
        return any(contains_public_wildcard(item) for item in value)
    if isinstance(value, dict):
        return any(contains_public_wildcard(item) for item in value.values())
    return False


def scan_policy_value(value: Any, path: str = "$") -> list[dict[str, str]]:
    """Return high-signal risk findings from an OBS bucket policy document."""
    findings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = json_path(path, str(key))
            lowered_key = str(key).lower()
            if lowered_key == "principal" and contains_public_wildcard(child):
                findings.append(
                    {
                        "severity": "high",
                        "code": "public_principal",
                        "path": child_path,
                        "message": "Bucket policy uses Principal '*' and may grant public or broad cross-account access.",
                    }
                )
            elif lowered_key == "notprincipal":
                findings.append(
                    {
                        "severity": "high",
                        "code": "not_principal_policy",
                        "path": child_path,
                        "message": "Bucket policy uses NotPrincipal; review the effective deny/allow scope manually.",
                    }
                )
            elif lowered_key == "resource" and contains_public_wildcard(child):
                findings.append(
                    {
                        "severity": "high",
                        "code": "wildcard_resource",
                        "path": child_path,
                        "message": "Bucket policy resource scope contains '*' and may affect more objects than intended.",
                    }
                )
            findings.extend(scan_policy_value(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_policy_value(child, json_path(path, index)))
    return findings


def policy_risk_findings(args: argparse.Namespace, operation: str) -> list[dict[str, str]]:
    """Return OBS ACL and bucket-policy risk findings visible from planner inputs."""
    findings: list[dict[str, str]] = []
    for raw_arg in args.arg:
        key, _, raw_value = raw_arg.partition("=")
        if key.lower() == "-acl" and raw_value.lower() in PUBLIC_ACLS:
            findings.append(
                {
                    "severity": "high",
                    "code": "public_acl",
                    "path": "--arg",
                    "message": f"OBS ACL {raw_value!r} can expose bucket or object data publicly.",
                }
            )

    if operation != "PutBucketPolicy":
        return findings

    local_file = local_file_arg(args)
    if not local_file:
        return findings
    try:
        policy = json.loads(Path(local_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(
            {
                "severity": "medium",
                "code": "policy_file_unreadable",
                "path": str(local_file),
                "message": f"Bucket policy file could not be parsed during planning: {exc}",
            }
        )
        return findings
    return findings + scan_policy_value(policy)


def build_safe_exec_command(args: argparse.Namespace, operation: str) -> list[str]:
    """Build the safe_exec wrapper command for a planned OBS change."""
    command = hcloud_common.safe_exec_command_prefix() + ["--command-part=obs"]
    for part in command_parts(args, operation):
        command.append(f"--command-part={part}")
    command.extend(["--timeout", str(args.timeout)])
    return command


def verification_plan(args: argparse.Namespace, operation: str) -> dict[str, Any] | None:
    """Return a read-only verification plan for the OBS change when possible."""
    verification_operation = CHANGE_OPERATIONS[operation]["verification_operation"]
    verify_args = argparse.Namespace(
        operation=verification_operation,
        bucket=args.bucket,
        endpoint=args.endpoint,
        config=args.config,
        payer=args.payer,
        limit=20,
        arg=[],
        execute=False,
        timeout=args.timeout,
    )
    return hcloud_obs_readonly.build_plan(verify_args)


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a non-executing OBS change plan."""
    requested_operation = args.operation
    operation = canonical_operation(requested_operation)
    if operation is None:
        return {
            "success": False,
            "service": "OBS",
            "operation": requested_operation,
            "error": "Unsupported OBS change operation.",
            "available_change_operations": sorted(CHANGE_OPERATIONS),
        }

    try:
        submit_command = build_safe_exec_command(args, operation)
    except ValueError as exc:
        return {
            "success": False,
            "service": "OBS",
            "operation": operation,
            "requested_operation": requested_operation,
            "error": str(exc),
        }

    risk = hcloud_change_plan.assess_risk(operation, dryrun_supported=False)
    risk_dict = risk.to_dict()
    obs_policy_findings = policy_risk_findings(args, operation)
    if obs_policy_findings:
        risk_dict["policy_risk_findings"] = obs_policy_findings
        risk_dict["requires_confirmation"] = True
        risk_dict["verification_required"] = True
        if any(item["severity"] == "high" for item in obs_policy_findings):
            risk_dict["level"] = "high"
        risk_dict.setdefault("reasons", []).append(
            "OBS policy or ACL input can broaden public, wildcard, or cross-account access."
        )
    warnings = [
        "OBS obsutil bucket and lifecycle changes do not use the generic OpenAPI dry-run path.",
        "Do not run the submit command without a separate explicit user confirmation.",
    ]
    if obs_policy_findings:
        warnings.append("Review OBS policy_risk_findings before running the submit command.")
    command_plan = CommandPlan(
        service="OBS",
        operation=operation,
        command=submit_command,
        mode="plan",
        dryrun_required=False,
        expect_json=False,
        warnings=warnings,
    )
    result: dict[str, Any] = {
        "success": True,
        "service": "OBS",
        "operation": operation,
        "planning_only": True,
        "adapter": "hcloud obs",
        "risk": risk_dict,
        "plan": command_plan.to_dict(),
        "commands": {
            "submit": submit_command,
            "submit_shell": shlex.join(submit_command),
        },
        "verification_plan": verification_plan(args, operation),
        "next_steps": [
            "Review bucket, endpoint, lifecycle or policy file, and rollback expectations.",
            "Run the submit command only after explicit confirmation.",
            "Run the verification plan after submit and inspect obsutil output before declaring success.",
        ],
    }
    if requested_operation != operation:
        result["requested_operation"] = requested_operation
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", required=True, help="OBS change operation, for example PutBucketLifecycle.")
    parser.add_argument("--bucket", help="OBS bucket name or obs://bucket URL.")
    parser.add_argument("--local-file", help="Local lifecycle or policy file for put-style operations.")
    parser.add_argument("--json-input-file", help="Alias for --local-file for compatibility with other planners.")
    parser.add_argument("--endpoint", help="Optional OBS endpoint passed as -e=...")
    parser.add_argument("--config", help="Optional obsutil config path passed as -config=...")
    parser.add_argument("--payer", help="Optional request payer passed as -payer=...")
    parser.add_argument("--arg", action="append", default=[], help="Raw obsutil option such as -acl=private.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for generated safe_exec commands.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build and print an OBS change plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
