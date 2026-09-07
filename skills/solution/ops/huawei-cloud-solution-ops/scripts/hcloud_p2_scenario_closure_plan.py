#!/usr/bin/env python3
"""Build P2 scenario closure plans for Huawei Cloud service groups."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_catalog
import hcloud_common
import hcloud_curated_promotion_audit
import hcloud_resource_discovery
import hcloud_resource_query

P2_GROUPS = (
    "CCE",
    "NAT",
    "DCS",
    "RFS",
    "UCS",
    "DEPENDENCY_IAM_KPS_IMS",
    "SECURITY_POSTURE",
    "DATABASE_FAMILY",
)
GROUP_ALIASES = {
    "DEPENDENCY": "DEPENDENCY_IAM_KPS_IMS",
    "DEPENDENCIES": "DEPENDENCY_IAM_KPS_IMS",
    "IAM_KPS_IMS": "DEPENDENCY_IAM_KPS_IMS",
    "SECURITY": "SECURITY_POSTURE",
    "SECURITY_SERVICES": "SECURITY_POSTURE",
    "DATABASE": "DATABASE_FAMILY",
    "DATABASES": "DATABASE_FAMILY",
    "DB_FAMILY": "DATABASE_FAMILY",
}

GROUP_SERVICES = {
    "CCE": ["CCE"],
    "NAT": ["NAT"],
    "DCS": ["DCS"],
    "RFS": ["RFS"],
    "UCS": ["UCS"],
    "DEPENDENCY_IAM_KPS_IMS": ["IAM", "KPS", "IMS"],
    "SECURITY_POSTURE": ["HSS", "SecMaster", "CFW", "DBSS", "KMS"],
    "DATABASE_FAMILY": ["GaussDB", "GaussDBforNoSQL", "GaussDBforopenGauss", "DDS", "DDM", "DWS"],
}
P2_METADATA_RESOURCE_QUERY_ACTIONS = {"List", "Show", "Get", "Count", "Search", "Query", "Check"}

GROUP_TASKS: dict[str, dict[str, Any]] = {
    "CCE": {
        "summary": "Plan CCE cluster, node, kubeconfig boundary, and workload-health evidence without creating or deleting clusters.",
        "tenant_goals": ["上好云", "用好云"],
        "required_inputs": ["cluster_id", "workload_scope"],
        "review_checks": [
            "Separate cloud-side cluster status, node status, kubeconfig access, and Kubernetes workload readiness.",
            "Do not persist kubeconfig tokens or print cluster credentials.",
            "Treat cluster create/delete/upgrade and workload deployment as separate guarded workflows.",
        ],
    },
    "NAT": {
        "summary": "Plan NAT gateway, SNAT/DNAT, route, EIP, and connectivity evidence for private/public network paths.",
        "tenant_goals": ["上好云", "管好云"],
        "required_inputs": ["nat_gateway_id", "dnat_rule_id", "snat_rule_id", "eip_id"],
        "review_checks": [
            "Review VPC, subnet, route, EIP binding, and security group boundaries together.",
            "DNAT public-port exposure must be checked with source CIDR and backend listener readiness.",
            "Keep NAT gateway and rule mutations behind guarded flow and explicit confirmation.",
        ],
    },
    "DCS": {
        "summary": "Plan DCS instance health, configuration, backup, maintenance window, and diagnosis evidence.",
        "tenant_goals": ["用好云", "管好云"],
        "required_inputs": ["instance_id"],
        "review_checks": [
            "Separate instance availability, configuration, backup freshness, and diagnosis evidence.",
            "Check maintenance windows before any parameter, failover, resize, or restart planning.",
            "Do not submit DCS mutations without a dedicated guarded flow.",
        ],
    },
    "RFS": {
        "summary": "Plan RFS stack, template, resource, execution-plan, and drift-review evidence.",
        "tenant_goals": ["上好云", "管好云"],
        "required_inputs": ["stack_name", "execution_plan_name"],
        "review_checks": [
            "Review stack metadata, template, resources, execution plan, and rollback path before apply.",
            "Treat template parameters and stack outputs as potentially sensitive.",
            "Do not run apply/continue/rollback from this planner.",
        ],
    },
    "UCS": {
        "summary": "Plan UCS fleet, cluster, policy, addon, and multi-cluster governance evidence.",
        "tenant_goals": ["用好云", "管好云"],
        "required_inputs": ["clusterid", "clustergroupid", "policydefinitionid"],
        "review_checks": [
            "Separate fleet/group status, managed cluster state, policies, addons, and credential boundaries.",
            "Do not persist kubeconfig tokens or cluster access credentials.",
            "Keep federation, policy, addon, and cluster-access mutations behind dedicated guarded flow.",
        ],
    },
    "DEPENDENCY_IAM_KPS_IMS": {
        "summary": "Plan IAM context, KPS keypair, and IMS image evidence as cloud-onboarding dependencies.",
        "tenant_goals": ["上好云"],
        "required_inputs": ["project_id", "keypair_name", "image_id"],
        "review_checks": [
            "Confirm profile, domain, region, project, image, and keypair before ECS or workload creation.",
            "Do not export or print private keys unless a separate credential-handling flow is approved.",
            "Treat IAM mutations as out of scope for this dependency planner.",
        ],
    },
    "SECURITY_POSTURE": {
        "summary": "Plan read-only security posture discovery and evidence gaps for HSS, SecMaster, CFW, DBSS, and KMS.",
        "tenant_goals": ["管好云"],
        "required_inputs": ["security_scope", "resource_id", "policy_id", "key_id"],
        "review_checks": [
            "Start with visibility and evidence gaps before recommending security policy changes.",
            "Treat events, host posture, firewall rules, database audit records, and keys as sensitive.",
            "Keep security policy, host agent, firewall, audit, and key mutations hard-gated.",
        ],
        "metadata_only": True,
    },
    "DATABASE_FAMILY": {
        "summary": "Plan database-family readiness using the RDS pattern: backup, connection, parameter, restart, and rollback evidence.",
        "tenant_goals": ["用好云", "管好云"],
        "required_inputs": ["instance_id", "config_id", "backup_id"],
        "review_checks": [
            "Apply the RDS-style safety model: backup posture, connection evidence, parameter scope, restart impact, and rollback path.",
            "Do not claim database availability from instance status alone.",
            "Keep resize, parameter mutation, restart, delete, and restore operations behind dedicated guarded flow.",
        ],
        "metadata_only": True,
    },
}

PARAM_ALIASES: dict[str, dict[str, str]] = {
    "CCE": {"cluster_id": "cluster_id"},
    "NAT": {
        "nat_gateway_id": "nat_gateway_id",
        "dnat_rule_id": "dnat_rule_id",
        "snat_rule_id": "snat_rule_id",
    },
    "DCS": {"instance_id": "instance_id"},
    "RFS": {"stack_name": "stack_name", "execution_plan_name": "execution_plan_name"},
    "UCS": {
        "clusterid": "clusterid",
        "clustergroupid": "clustergroupid",
        "policydefinitionid": "policydefinitionid",
    },
    "KPS": {"keypair_name": "keypair_name"},
    "IMS": {"image_id": "image_id", "job_id": "job_id"},
}


def canonical_group(value: str) -> str:
    """Return a canonical P2 group key."""
    token = value.upper().replace("-", "_").replace(" ", "")
    return GROUP_ALIASES.get(token, token)


def parse_params(values: list[str]) -> dict[str, str]:
    """Parse repeated key=value parameters."""
    params: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected --param KEY=VALUE, got {item!r}.")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"Expected non-empty key in --param {item!r}.")
        params[key] = value
    return params


def load_profiles() -> dict[str, Any]:
    """Load service curation profiles."""
    return hcloud_curated_promotion_audit.load_curation_profiles()


def profile_summary(profiles: dict[str, Any], service: str) -> dict[str, Any] | None:
    """Return compact service curation profile summary."""
    profile = hcloud_curated_promotion_audit.profile_for_service(profiles, service)
    return hcloud_curated_promotion_audit.profile_summary(profile)


def discovery_args(args: argparse.Namespace, service: str, operation: str | None = None) -> SimpleNamespace:
    """Return arguments for one read-only discovery plan."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=args.catalog_max_operations,
        execute=False,
        timeout=args.timeout,
    )


def query_params_for_operation(service: str, operation: str, params: dict[str, str]) -> list[str]:
    """Return explicit query params that can satisfy a resource query operation."""
    required = hcloud_resource_query.required_params(service, operation)
    aliases = PARAM_ALIASES.get(service, {})
    selected: list[str] = []
    for required_name in required:
        if required_name in params:
            selected.append(f"{required_name}={params[required_name]}")
            continue
        source_name = aliases.get(required_name)
        if source_name and source_name in params:
            selected.append(f"{required_name}={params[source_name]}")
    return selected


def query_args(args: argparse.Namespace, service: str, operation: str, params: dict[str, str]) -> SimpleNamespace:
    """Return arguments for one target-scoped read query plan."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        param=query_params_for_operation(service, operation, params),
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def compact_discovery_plan(args: argparse.Namespace, service: str, operation: str | None = None) -> dict[str, Any]:
    """Build a compact discovery plan for P2 evidence."""
    plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, operation))
    return {
        "service": service,
        "operation": operation,
        "success": bool(plan.get("success")),
        "metadata_backed": bool(plan.get("metadata_backed")),
        "coverage": plan.get("coverage"),
        "commands": plan.get("commands", []),
        "error": plan.get("error"),
    }


def compact_query_plan(args: argparse.Namespace, service: str, operation: str, params: dict[str, str]) -> dict[str, Any]:
    """Build a compact resource query plan for P2 evidence."""
    plan = hcloud_resource_query.build_plan(query_args(args, service, operation, params))
    return {
        "service": service,
        "operation": plan.get("operation", operation),
        "success": bool(plan.get("success")),
        "operation_scope": plan.get("operation_scope"),
        "metadata_backed": bool(plan.get("metadata_backed")),
        "coverage": plan.get("coverage"),
        "required_params": plan.get("required_params", []),
        "provided_params": plan.get("provided_params", []),
        "missing_params": plan.get("missing_params", []),
        "command": plan.get("command"),
        "risk": plan.get("risk"),
        "error": plan.get("error"),
    }


def profile_evidence(
    args: argparse.Namespace,
    services: list[str],
    profiles: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any]:
    """Return evidence plans for services with curation profiles."""
    discovery_plans = []
    query_plans = []
    profile_entries = []
    for service in services:
        summary = profile_summary(profiles, service)
        profile_entries.append({"service": service, "profile_present": bool(summary), "profile": summary})
        if not summary:
            continue
        for operation in summary.get("readiness_operations", []):
            discovery_plans.append(compact_discovery_plan(args, service, str(operation)))
        for operation in summary.get("resource_query_operations", []):
            query_plans.append(compact_query_plan(args, service, str(operation), params))
    return summarize_evidence(discovery_plans, query_plans, profile_entries)


def metadata_service_evidence(args: argparse.Namespace, services: list[str], params: dict[str, str]) -> dict[str, Any]:
    """Return conservative metadata-backed evidence plans for services without curation profiles."""
    discovery_plans = []
    query_plans = []
    catalog = hcloud_catalog.load_catalog()
    profile_entries = []
    for service in services:
        catalog_service = hcloud_catalog.resolve_service(catalog, service)
        profile_entries.append({"service": service, "profile_present": False, "profile": None})
        if not catalog_service:
            discovery_plans.append({"service": service, "success": False, "commands": [], "error": "missing_catalog_service"})
            continue
        discovery_plans.append(compact_discovery_plan(args, service))
        for candidate in hcloud_curated_promotion_audit.resource_query_candidates(catalog_service, limit=2):
            operation = str(candidate.get("operation") or "")
            if operation and metadata_resource_query_candidate_allowed(catalog_service, operation):
                query_plans.append(compact_query_plan(args, service, operation, params))
    return summarize_evidence(discovery_plans, query_plans, profile_entries)


def metadata_resource_query_candidate_allowed(catalog_service: dict[str, Any], operation_name: str) -> bool:
    """Return whether a metadata-backed operation is conservative enough for P2 evidence planning."""
    operation = hcloud_catalog.resolve_operation(catalog_service, operation_name)
    action = str((operation or {}).get("action") or "")
    return action in P2_METADATA_RESOURCE_QUERY_ACTIONS


def summarize_evidence(
    discovery_plans: list[dict[str, Any]],
    query_plans: list[dict[str, Any]],
    profile_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a compact evidence summary."""
    planned_command_count = sum(len(plan.get("commands", [])) for plan in discovery_plans)
    planned_command_count += sum(1 for plan in query_plans if plan.get("command"))
    missing_param_items = [
        {
            "service": plan["service"],
            "operation": plan["operation"],
            "missing_params": plan.get("missing_params", []),
        }
        for plan in query_plans
        if plan.get("missing_params")
    ]
    return {
        "summary": {
            "profile_count": sum(1 for entry in profile_entries if entry.get("profile_present")),
            "discovery_plan_count": len(discovery_plans),
            "resource_query_plan_count": len(query_plans),
            "planned_command_count": planned_command_count,
            "missing_param_query_count": len(missing_param_items),
        },
        "profiles": profile_entries,
        "discovery_plans": discovery_plans,
        "resource_query_plans": query_plans,
        "missing_param_items": missing_param_items,
    }


def group_summary(group: str, evidence: dict[str, Any], metadata_only: bool) -> dict[str, Any]:
    """Return a group-level P2 readiness summary."""
    summary = evidence["summary"]
    if metadata_only:
        status = "metadata_evidence_gap"
    elif summary["missing_param_query_count"]:
        status = "target_params_needed"
    else:
        status = "review_ready"
    return {
        "status": status,
        "metadata_only": metadata_only,
        "planned_command_count": summary["planned_command_count"],
        "missing_param_query_count": summary["missing_param_query_count"],
        "profile_count": summary["profile_count"],
    }


def aggregate_summary(groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Return top-level P2 scenario summary."""
    statuses = [group["scenario_summary"]["status"] for group in groups]
    return {
        "group_count": len(groups),
        "review_ready_group_count": statuses.count("review_ready"),
        "target_params_needed_group_count": statuses.count("target_params_needed"),
        "metadata_evidence_gap_group_count": statuses.count("metadata_evidence_gap"),
        "planned_evidence_command_count": sum(
            int(group["scenario_summary"]["planned_command_count"]) for group in groups
        ),
        "missing_param_query_count": sum(
            int(group["scenario_summary"]["missing_param_query_count"]) for group in groups
        ),
    }


def build_group_plan(
    args: argparse.Namespace,
    group: str,
    profiles: dict[str, Any],
    params: dict[str, str],
) -> dict[str, Any]:
    """Build one P2 scenario group plan."""
    task = GROUP_TASKS[group]
    services = GROUP_SERVICES[group]
    metadata_only = bool(task.get("metadata_only"))
    evidence = metadata_service_evidence(args, services, params) if metadata_only else profile_evidence(args, services, profiles, params)
    return {
        "group": group,
        "services": services,
        "tenant_goals": task["tenant_goals"],
        "summary": task["summary"],
        "planning_only": True,
        "execution_supported": False,
        "scenario_summary": group_summary(group, evidence, metadata_only),
        "stages": [
            {
                "id": "scenario_scope",
                "description": "Confirm scenario boundary, target resources, and service-specific prerequisites.",
                "required_inputs": task["required_inputs"],
                "provided_params": {key: value for key, value in params.items() if key in task["required_inputs"]},
            },
            {
                "id": "read_only_evidence",
                "description": "Generate read-only evidence command plans and target-scoped missing-parameter gaps.",
                "evidence": evidence,
            },
            {
                "id": "risk_boundary",
                "description": "Keep P2 writes disabled until a dedicated guarded flow and validation evidence exist.",
                "checks": task["review_checks"],
                "mutation_boundary": "planner_only_no_submit",
            },
            {
                "id": "next_closure_steps",
                "description": "Use evidence gaps to decide whether this group needs live smoke, curated promotion, or a dedicated guarded flow.",
                "actions": [
                    "Collect live read-smoke for high-value read-only operations before claiming curated maturity.",
                    "Add target IDs and rerun the planner to convert skipped target queries into command plans.",
                    "Only add write support after playbook, risk profile, tests, explicit confirmation, and post-change verification exist.",
                ],
            },
        ],
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build planner-only P2 scenario closure plans."""
    params = parse_params(args.param)
    selected = [canonical_group(group) for group in (args.group or P2_GROUPS)]
    unsupported = [group for group in selected if group not in GROUP_TASKS]
    if unsupported:
        return {
            "success": False,
            "mode": "plan",
            "planning_only": True,
            "error": "Unsupported P2 scenario group.",
            "unsupported_groups": unsupported,
            "supported_groups": list(P2_GROUPS),
        }
    selected = list(dict.fromkeys(selected))
    profiles = load_profiles()
    groups = [build_group_plan(args, group, profiles, params) for group in selected]
    return {
        "success": True,
        "mode": "plan",
        "planning_only": True,
        "scope": "P2 scenario closure for containers, NAT, cache, IaC, multi-cluster, dependency, security, and database-family services.",
        "region": args.region,
        "project_id": args.project_id,
        "profile": args.profile,
        "selected_groups": selected,
        "scenario_summary": aggregate_summary(groups),
        "groups": groups,
        "global_boundaries": [
            "P2 scenario closure is read-only/planner-only by default.",
            "Metadata-backed security and database-family services remain evidence-gap plans, not curated maturity claims.",
            "Cluster, NAT, cache, stack, fleet, security, key, and database mutations require dedicated guarded flows before submit.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", action="append", help="P2 group. Defaults to all P2 scenario groups.")
    parser.add_argument("--param", action="append", default=[], help="Task parameter as KEY=VALUE. Can be repeated.")
    parser.add_argument("--region", help="Explicit cli-region for generated review context.")
    parser.add_argument("--project-id", help="Optional project_id for generated review context.")
    parser.add_argument("--profile", help="Optional cli-profile for generated review context.")
    parser.add_argument("--limit", type=int, default=10, help="Optional limit for generated read-only evidence commands.")
    parser.add_argument(
        "--catalog-max-operations",
        type=int,
        default=3,
        help="Maximum metadata-backed discovery operations per long-tail service.",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Timeout value carried into generated command plans.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.catalog_max_operations < 1:
        parser.error("--catalog-max-operations must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build the P2 scenario closure plan."""
    args = parse_args()
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "mode": "plan", "planning_only": True, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
