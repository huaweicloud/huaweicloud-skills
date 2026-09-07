#!/usr/bin/env python3
"""Build or run service-level read-only readiness checks."""

from __future__ import annotations

import argparse
import collections
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_obs_readonly
import hcloud_resource_discovery
import hcloud_resource_query
import hcloud_resource_verify

DEFAULT_SERVICES = ("ECS", "VPC", "RDS", "IMS", "EVS", "EIP", "ELB", "NAT", "KPS", "IAM", "CCE", "CDN", "DNS", "SCM", "OBS", "CES")
READINESS_PROFILES = {
    "ECS": [
        {"operation": "ListCloudServers"},
        {"operation": "ListServersDetails"},
        {"operation": "ListFlavors"},
        {"operation": "ListServerAzInfo"},
        {"operation": "ShowServer", "required_targets": ["server_id"]},
    ],
    "VPC": [
        {"operation": "ListVpcs"},
        {"operation": "ListSubnets"},
        {"operation": "ListSecurityGroups"},
        {"operation": "ListSecurityGroupRules"},
        {"operation": "ListVpcPeerings"},
        {"operation": "ShowVpc", "required_targets": ["vpc_id"]},
        {"operation": "ShowSubnet", "required_targets": ["subnet_id"]},
        {"operation": "ShowSecurityGroup", "required_targets": ["security_group_id"]},
        {"operation": "ShowSecurityGroupRule", "required_targets": ["security_group_rule_id"]},
    ],
    "EIP": [
        {"operation": "ListPublicips"},
        {"operation": "ShowPublicip", "required_targets": ["publicip_id"]},
    ],
    "ELB": [
        {"operation": "ListLoadbalancers"},
        {"operation": "ListListeners"},
        {"operation": "ListPools"},
        {"operation": "ShowLoadBalancer", "required_targets": ["loadbalancer_id"]},
        {"operation": "ShowListener", "required_targets": ["listener_id"]},
        {"operation": "ShowPool", "required_targets": ["pool_id"]},
        {"operation": "ListMembers", "required_targets": ["pool_id"]},
        {"operation": "ShowMember", "required_targets": ["pool_id", "member_id"]},
    ],
    "EVS": [
        {"operation": "ListVolumes"},
        {"operation": "ListSnapshots"},
        {"operation": "ShowVolume", "required_targets": ["volume_id"]},
        {"operation": "ShowSnapshot", "required_targets": ["snapshot_id"]},
    ],
    "NAT": [
        {"operation": "ListNatGateways"},
        {"operation": "ListNatGatewayDnatRules"},
        {"operation": "ListNatGatewaySnatRules"},
        {"operation": "ShowNatGateway", "required_targets": ["nat_gateway_id"]},
        {"operation": "ShowNatGatewayDnatRule", "required_targets": ["dnat_rule_id"]},
        {"operation": "ShowNatGatewaySnatRule", "required_targets": ["snat_rule_id"]},
    ],
    "RDS": [
        {"operation": "ListInstances"},
        {"operation": "ListBackups", "required_targets": ["instance_id"]},
        {"operation": "ListConfigurations"},
        {"operation": "ShowBackupPolicy", "required_targets": ["instance_id"]},
        {"operation": "ShowConfiguration", "required_targets": ["config_id"]},
        {"operation": "ShowInstanceConfiguration", "required_targets": ["instance_id"]},
    ],
    "CCE": [
        {"operation": "ListClusters"},
        {"operation": "ShowCluster", "required_targets": ["cluster_id"]},
        {"operation": "ListNodes", "required_targets": ["cluster_id"]},
    ],
    "CDN": [
        {"operation": "ListDomains"},
        {"operation": "ShowDomainDetail", "required_targets": ["domain_id"]},
    ],
    "DNS": [
        {"operation": "ListPublicZones"},
        {"operation": "ListRecordSets"},
        {"operation": "ShowPublicZone", "required_targets": ["zone_id"]},
        {"operation": "ShowRecordSet", "required_targets": ["zone_id", "recordset_id"]},
    ],
    "SCM": [
        {"operation": "ListCertificates"},
        {"operation": "ShowCertificate", "required_targets": ["certificate_id"]},
    ],
    "OBS": [
        {"operation": "ListBuckets"},
        {"operation": "StatBucket", "required_targets": ["bucket"]},
        {"operation": "GetBucketLifecycle", "required_targets": ["bucket"]},
        {"operation": "GetBucketPolicy", "required_targets": ["bucket"]},
    ],
    "CES": [
        {"operation": "ListMetrics"},
    ],
    "IMS": [
        {"operation": "ListImages"},
        {"operation": "ListOsVersions"},
        {"operation": "GlanceShowImage", "required_targets": ["image_id"]},
    ],
    "KPS": [
        {"operation": "ListKeypairs"},
        {"operation": "ListKeypairDetail", "required_targets": ["keypair_name"]},
    ],
    "IAM": [
        {"operation": "ShowProjectDetailsAndStatus"},
    ],
}


def parse_targets(values: list[str]) -> dict[str, str]:
    """Parse target parameters shared by readiness checks."""
    return hcloud_resource_query.parse_key_value(values, "--target")


def discovery_args(args: argparse.Namespace, service: str, operation: str) -> SimpleNamespace:
    """Build arguments for generic list-only discovery."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        execute=False,
    )


def query_args(args: argparse.Namespace, service: str, operation: str, params: list[str]) -> SimpleNamespace:
    """Build arguments for explicit-parameter read queries."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        param=params,
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def obs_args(args: argparse.Namespace, operation: str, targets: dict[str, str]) -> SimpleNamespace:
    """Build arguments for OBS obsutil read-only checks."""
    return SimpleNamespace(
        operation=operation,
        bucket=targets.get("bucket"),
        endpoint=getattr(args, "obs_endpoint", None),
        config=getattr(args, "obs_config", None),
        payer=getattr(args, "obs_payer", None),
        limit=args.limit,
        arg=[],
        execute=False,
        timeout=args.timeout,
    )


def operation_is_generic_query(service_entry: dict[str, Any], operation: str, required_targets: list[str]) -> bool:
    """Return True when a readiness check can use list-only discovery."""
    return not required_targets and operation in service_entry.get("query_operations", [])


def summarize_execution(service: str, execution: dict[str, Any] | None) -> dict[str, Any]:
    """Return a compact summary from one hcloud_safe_exec result."""
    if not execution:
        return {}
    payload = execution.get("parsed_json")
    resources = hcloud_resource_verify.collect_dicts(payload, service)
    status_counts = collections.Counter(
        status for item in resources if (status := hcloud_resource_verify.resource_status(item))
    )
    return {
        "resource_count": len(resources),
        "status_counts": dict(sorted(status_counts.items())),
        "parsed_json_error": execution.get("parsed_json_error"),
    }


def readiness_blocking_failures(checks: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """Return checks that should make the readiness result fail."""
    failures: list[dict[str, Any]] = []
    for check in checks:
        if check.get("skipped"):
            if args.require_all:
                failures.append(check)
            continue
        if check.get("stage") == "execute" and args.execute and not args.strict:
            continue
        if not check.get("success"):
            failures.append(check)
    return failures


def build_check(
    args: argparse.Namespace,
    service: str,
    service_entry: dict[str, Any],
    check_spec: dict[str, Any],
    targets: dict[str, str],
) -> dict[str, Any]:
    """Build one readiness check plan."""
    operation = str(check_spec["operation"])
    required_targets = [str(item) for item in check_spec.get("required_targets", [])]
    missing_targets = [name for name in required_targets if name not in targets]
    if missing_targets:
        return {
            "service": service,
            "operation": operation,
            "stage": "skip",
            "success": True,
            "skipped": True,
            "missing_targets": missing_targets,
            "reason": "Readiness check requires explicit target parameter(s).",
        }

    runner = service_entry.get("query_runner") or "scripts/hcloud_resource_discovery.py"
    resource_runner = service_entry.get("resource_query_runner") or "scripts/hcloud_resource_query.py"
    if runner == "scripts/hcloud_obs_readonly.py" or resource_runner == "scripts/hcloud_obs_readonly.py":
        plan = hcloud_obs_readonly.build_plan(obs_args(args, operation, targets))
        check = {
            "service": service,
            "operation": operation,
            "stage": "plan",
            "success": plan.get("success", False),
            "skipped": False,
            "plan": plan,
            "runner": "scripts/hcloud_obs_readonly.py",
        }
        if plan.get("success") and args.execute:
            exec_args = obs_args(args, operation, targets)
            exec_args.execute = True
            executed = hcloud_obs_readonly.build_plan(exec_args)
            check.update(
                {
                    "stage": "execute",
                    "execution_success": executed.get("execution_success", False),
                    "result": executed.get("result"),
                    "summary": executed.get("summary", {}),
                    "success": bool(executed.get("success")),
                }
            )
        return check

    if operation_is_generic_query(service_entry, operation, required_targets):
        plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, operation))
        check = {
            "service": service,
            "operation": operation,
            "stage": "plan",
            "success": plan.get("success", False),
            "skipped": False,
            "plan": plan,
            "runner": "scripts/hcloud_resource_discovery.py",
        }
        if plan.get("success") and args.execute:
            executed = hcloud_resource_discovery.execute_plan(plan, args.timeout)
            execution = executed.get("results", [{}])[0].get("result") if executed.get("results") else None
            check.update(
                {
                    "stage": "execute",
                    "execution_success": executed.get("success", False),
                    "results": executed.get("results", []),
                    "summary": summarize_execution(service, execution),
                    "success": bool(executed.get("success")),
                }
            )
        return check

    params = [f"{name}={targets[name]}" for name in required_targets]
    plan = hcloud_resource_query.build_plan(query_args(args, service, operation, params))
    check = {
        "service": service,
        "operation": operation,
        "stage": "plan",
        "success": plan.get("success", False),
        "skipped": False,
        "plan": plan,
        "runner": "scripts/hcloud_resource_query.py",
    }
    if plan.get("success") and args.execute:
        exec_args = query_args(args, service, operation, params)
        exec_args.execute = True
        executed = hcloud_resource_query.build_plan(exec_args)
        check.update(
            {
                "stage": "execute",
                "execution_success": executed.get("execution_success", False),
                "result": executed.get("result"),
                "summary": summarize_execution(service, executed.get("result")),
                "success": bool(executed.get("success")),
            }
        )
    return check


def build_readiness(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run read-only readiness checks for selected services."""
    registry = hcloud_resource_discovery.load_registry()
    targets = parse_targets(args.target)
    selected_services = [service.upper() for service in (args.service or DEFAULT_SERVICES)]
    service_results: list[dict[str, Any]] = []

    for service in selected_services:
        entry = registry.get("services", {}).get(service)
        profile = READINESS_PROFILES.get(service)
        if entry is None:
            service_results.append(
                {
                    "service": service,
                    "success": False,
                    "error": "Service is not registered.",
                }
            )
            continue
        if profile is None:
            service_results.append(
                {
                    "service": service,
                    "success": False,
                    "error": "Service has no readiness profile.",
                }
            )
            continue

        checks = [build_check(args, service, entry, item, targets) for item in profile]
        skipped_count = sum(1 for item in checks if item.get("skipped"))
        blocking_failures = readiness_blocking_failures(checks, args)
        service_results.append(
            {
                "service": service,
                "success": not blocking_failures,
                "coverage": entry.get("coverage"),
                "check_count": len(checks),
                "skipped_count": skipped_count,
                "checks": checks,
            }
        )

    readiness_success = all(item.get("success") for item in service_results)
    return {
        "success": readiness_success,
        "mode": "execute" if args.execute else "plan",
        "strict": args.strict,
        "require_all": args.require_all,
        "region": args.region,
        "project_id_present": bool(args.project_id),
        "target_params": sorted(targets),
        "service_count": len(service_results),
        "services": service_results,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Service readiness profile to run. Can be repeated.")
    parser.add_argument("--target", action="append", default=[], help="Target parameter as KEY=VALUE, such as pool_id=<id>.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=20, help="Optional limit for operations that support it.")
    parser.add_argument("--obs-endpoint", help="Optional OBS endpoint for hcloud obs checks.")
    parser.add_argument("--obs-config", help="Optional obsutil config path for hcloud obs checks.")
    parser.add_argument("--obs-payer", help="Optional OBS request payer for hcloud obs checks.")
    parser.add_argument("--execute", action="store_true", help="Execute readiness checks through hcloud_safe_exec.py.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed command.")
    parser.add_argument("--strict", action="store_true", help="Return failure when any executed check fails.")
    parser.add_argument("--require-all", action="store_true", help="Fail if target-dependent checks are skipped.")
    parser.add_argument("--output-file", type=Path, help="Write the full JSON result privately and print a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run service-level readiness checks."""
    args = parse_args()
    try:
        result = build_readiness(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
        default_mode="execute" if args.execute else "plan",
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
