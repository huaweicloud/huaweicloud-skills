#!/usr/bin/env python3
"""Build P1 governance closure plans for Huawei Cloud services."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_billing_readonly
import hcloud_catalog
import hcloud_common
import hcloud_curated_promotion_audit
import hcloud_resource_discovery
import hcloud_resource_query

P1_SERVICES = ("TMS", "CTS", "CBR", "RMS_CONFIG", "BILLING_BSS", "WAF", "DLI", "CODEARTSREPO")
SERVICE_ALIASES = {
    "RMS": "RMS_CONFIG",
    "CONFIG": "RMS_CONFIG",
    "RMS_CONFIG": "RMS_CONFIG",
    "RMS/CONFIG": "RMS_CONFIG",
    "BILLING": "BILLING_BSS",
    "COST": "BILLING_BSS",
    "BSS": "BILLING_BSS",
    "BILLING_BSS": "BILLING_BSS",
    "BILLING/COST/BSS": "BILLING_BSS",
    "CODEARTS_REPO": "CODEARTSREPO",
    "CODEARTSREPO": "CODEARTSREPO",
}

SERVICE_GROUPS = {
    "TMS": ["TMS"],
    "CTS": ["CTS"],
    "CBR": ["CBR"],
    "RMS_CONFIG": ["RMS", "Config"],
    "BILLING_BSS": ["BSS"],
    "WAF": ["WAF"],
    "DLI": ["DLI"],
    "CODEARTSREPO": ["CodeArtsRepo"],
}

SERVICE_TASKS: dict[str, dict[str, Any]] = {
    "TMS": {
        "task": "tag-coverage-and-cost-allocation-governance",
        "tenant_goals": ["上好云", "管好云"],
        "summary": "Plan tag taxonomy, tag coverage, owner/cost-center evidence, and tag-fix review without writing tags.",
        "required_inputs": ["required_tag_keys", "resource_types", "owner_taxonomy"],
        "review_checks": [
            "Confirm the mandatory tag taxonomy such as owner, env, cost-center, app, and expiry.",
            "Map supported resource types before checking tag coverage.",
            "Use target-scoped resource tag readback before proposing tag fixes.",
            "Record tag gaps as review candidates rather than immediate tag mutations.",
        ],
        "reporting_outputs": [
            "Tag key/value taxonomy summary.",
            "Resource tag coverage gaps by service/resource type.",
            "Batch tag remediation plan requiring owner approval.",
        ],
    },
    "CTS": {
        "task": "audit-tracker-and-trace-readiness",
        "tenant_goals": ["管好云"],
        "summary": "Plan audit tracker, trace query, notification, OBS delivery, and sensitive trace handling checks.",
        "required_inputs": ["trace_type", "time_range", "region", "audit_scope"],
        "review_checks": [
            "Confirm tracker status, tracker type, OBS delivery bucket, and encryption posture.",
            "Use bounded trace time ranges and trace types.",
            "Treat operator, source IP, resource ID, and request metadata as sensitive output.",
            "Do not treat empty traces as proof until tracker, region, time range, and trace type are verified.",
        ],
        "reporting_outputs": [
            "Tracker readiness summary.",
            "Bounded trace evidence summary.",
            "Audit gap review items for tracker, notification, and OBS delivery.",
        ],
    },
    "CBR": {
        "task": "backup-posture-and-recovery-governance",
        "tenant_goals": ["用好云", "管好云"],
        "summary": "Plan backup vault, policy, backup checkpoint, and protectable-resource evidence before resilience conclusions.",
        "required_inputs": ["resource_scope", "recovery_objective", "vault_or_policy_id"],
        "review_checks": [
            "Inventory vaults, policies, backup records, and protectable resources.",
            "Check whether critical resources are protected by an active policy.",
            "Separate backup existence from restore readiness.",
            "Keep policy changes, protection changes, and deletes hard-gated.",
        ],
        "reporting_outputs": [
            "Protected/unprotected resource summary.",
            "Backup freshness and policy gap list.",
            "Recovery-readiness review plan.",
        ],
    },
    "RMS_CONFIG": {
        "task": "resource-inventory-and-compliance-governance",
        "tenant_goals": ["管好云"],
        "summary": "Plan resource inventory, policy state, conformance-pack, and aggregator evidence across RMS/Config.",
        "required_inputs": ["domain_id", "provider", "resource_type", "compliance_scope"],
        "review_checks": [
            "Confirm domain/account scope before account-wide inventory or compliance checks.",
            "Collect provider/resource inventory and policy-state evidence separately.",
            "State freshness and scope limits for compliance data.",
            "Keep policy assignment, aggregator, remediation, and conformance-pack mutations hard-gated.",
        ],
        "reporting_outputs": [
            "Resource inventory coverage summary.",
            "Compliance gap summary by policy/provider/resource type.",
            "Aggregator and organization-scope readiness gaps.",
        ],
    },
    "BILLING_BSS": {
        "task": "billing-cost-evidence-planning",
        "tenant_goals": ["管好云"],
        "summary": "Plan official Billing/Cost/BSS request specs and data-sensitivity boundaries without signing or sending requests.",
        "required_inputs": ["bill_cycle", "begin_time", "end_time", "enterprise_project_id"],
        "review_checks": [
            "Confirm account, enterprise project, time range, and permission scope before live billing access.",
            "Use official Billing/Cost APIs or API Explorer; do not infer spend from resource inventory.",
            "Keep raw records narrow because billing data contains account, resource, and spend-sensitive fields.",
            "Record freshness limits before using data for optimization decisions.",
        ],
        "reporting_outputs": [
            "Monthly summary or cost-analysis request spec.",
            "Resource fee/detail request spec.",
            "Cost data freshness and permission boundary summary.",
        ],
    },
    "WAF": {
        "task": "waf-policy-posture-governance",
        "tenant_goals": ["管好云"],
        "summary": "Plan WAF instance, host, certificate, and policy-rule readback before any web security policy change.",
        "required_inputs": ["domain", "policy_id", "enterprise_project_id"],
        "review_checks": [
            "Inventory WAF instances, protected hosts, certificates, and policy rules.",
            "Separate security visibility from policy enforcement changes.",
            "Keep host binding, certificate replacement, rule changes, and bypass controls hard-gated.",
            "Use event/rule evidence before claiming protection posture.",
        ],
        "reporting_outputs": [
            "Protected host and policy posture summary.",
            "Certificate and rule readback gaps.",
            "Policy change review plan.",
        ],
    },
    "DLI": {
        "task": "analytics-sql-governance-readiness",
        "tenant_goals": ["用好云", "管好云"],
        "summary": "Plan DLI auth, catalog, database, queue, and SQL check evidence for analytics readiness.",
        "required_inputs": ["queue_name", "database_name", "sql_check_scope"],
        "review_checks": [
            "Check auth info, catalogs, databases, and elastic resource pools before SQL workload claims.",
            "Use SQL check/read-only metadata before recommending job execution.",
            "Keep queue, permission, and workload changes planner-only until curated flow exists.",
            "Avoid exposing broad table metadata unless scope is approved.",
        ],
        "reporting_outputs": [
            "Catalog/database/queue readiness summary.",
            "Permission and SQL-check gaps.",
            "Analytics workload readiness review plan.",
        ],
    },
    "CODEARTSREPO": {
        "task": "repository-devops-governance-readiness",
        "tenant_goals": ["管好云"],
        "summary": "Plan repository, branch, merge-request, member, and deploy-key evidence for DevOps governance.",
        "required_inputs": ["project_id", "repository_id", "branch"],
        "review_checks": [
            "Inventory repositories, groups, branches, and merge-request scope before DevOps conclusions.",
            "Treat repository metadata, branch names, and merge requests as potentially sensitive.",
            "Keep repository, branch, member, webhook, and deploy-key mutations planner-only until curated flow exists.",
            "Use target-scoped repository readback before recommending automation changes.",
        ],
        "reporting_outputs": [
            "Repository and branch governance summary.",
            "MR/member/deploy-key evidence gaps.",
            "DevOps hygiene review plan.",
        ],
    },
}

PARAM_ALIASES: dict[str, dict[str, str]] = {
    "CBR": {
        "vault_id": "vault_or_policy_id",
        "policy_id": "vault_or_policy_id",
        "backup_id": "backup_id",
    },
    "CodeArtsRepo": {
        "repository_uuid": "repository_id",
        "project_uuid": "project_id",
        "repository_id": "repository_id",
        "branch_name": "branch",
    },
    "DLI": {
        "sql": "sql_check_scope",
        "queue_name": "queue_name",
        "database_name": "database_name",
    },
    "RMS": {
        "domain_id": "domain_id",
        "provider": "provider",
        "resource_type": "resource_type",
        "resource_id": "resource_id",
        "policy_assignment_id": "policy_assignment_id",
        "aggregator_id": "aggregator_id",
    },
    "Config": {
        "domain_id": "domain_id",
        "provider": "provider",
        "resource_type": "resource_type",
        "resource_id": "resource_id",
        "policy_assignment_id": "policy_assignment_id",
        "aggregator_id": "aggregator_id",
        "conformance_pack_id": "conformance_pack_id",
    },
    "TMS": {
        "resource_id": "resource_id",
        "resource_type": "resource_type",
        "resource_types": "resource_types",
        "tags": "tags",
        "key": "tag_key",
    },
    "WAF": {
        "enterprise_project_id": "enterprise_project_id",
        "policy_id": "policy_id",
        "domain": "domain",
        "host_id": "host_id",
        "certificate_id": "certificate_id",
    },
}


def canonical_service(value: str) -> str:
    """Return a canonical P1 governance service key."""
    token = value.upper().replace("-", "_").replace(" ", "")
    return SERVICE_ALIASES.get(token, token)


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


def billing_args(operation: str, params: dict[str, str]) -> SimpleNamespace:
    """Return arguments for the Billing/Cost request-spec planner."""
    return SimpleNamespace(
        operation=operation,
        endpoint_base=params.get("endpoint_base", hcloud_billing_readonly.DEFAULT_ENDPOINT_BASE),
        language=params.get("language", "zh_CN"),
        bill_cycle=params.get("bill_cycle"),
        begin_time=params.get("begin_time"),
        end_time=params.get("end_time"),
        time_measure_id=int(params.get("time_measure_id", "1")),
        group_by=params.get("group_by", "CLOUD_SERVICE_TYPE").split(","),
        filter=[],
        cost_type=params.get("cost_type", "ORIGINAL_COST"),
        amount_type=params.get("amount_type", "PAYMENT_AMOUNT"),
        service_type_code=params.get("service_type_code"),
        resource_type=params.get("resource_type"),
        region_code=params.get("region_code"),
        resource_id=params.get("resource_id"),
        enterprise_project_id=params.get("enterprise_project_id"),
        charge_mode=params.get("charge_mode"),
        bill_type=int(params["bill_type"]) if params.get("bill_type") else None,
        method=params.get("method"),
        sub_customer_id=params.get("sub_customer_id"),
        include_zero_record=params.get("include_zero_record"),
        statistic_type=int(params["statistic_type"]) if params.get("statistic_type") else None,
        offset=int(params.get("offset", "0")),
        limit=int(params.get("limit", "10")),
        query=[],
        body_json_file=None,
        body_json_text=None,
    )


def build_billing_specs(params: dict[str, str]) -> list[dict[str, Any]]:
    """Return planner-only Billing/Cost specs and hcloud command plans for governance review."""
    specs = []
    for operation in ("monthly-sum", "cost-data", "resource-records"):
        spec = hcloud_billing_readonly.build_request_spec(billing_args(operation, params))
        specs.append(
            {
                "operation": operation,
                "success": bool(spec.get("success")),
                "title": spec.get("title"),
                "execution_supported": bool(spec.get("execution_supported")),
                "request_spec": spec.get("request_spec"),
                "hcloud_command_plan": spec.get("hcloud_command_plan"),
                "pagination_scope": spec.get("pagination_scope"),
                "validation": spec.get("validation"),
                "official_docs": spec.get("official_docs"),
            }
        )
    return specs


def discovery_args(args: argparse.Namespace, service: str, operation: str) -> SimpleNamespace:
    """Return arguments for one metadata-backed governance discovery plan."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=getattr(args, "limit", 10),
        catalog_max_operations=1,
        execute=False,
        timeout=getattr(args, "timeout", 120),
    )


def query_params_for_operation(service: str, operation: str, params: dict[str, str]) -> list[str]:
    """Return explicit query params relevant to an operation without leaking unrelated task params."""
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
    """Return arguments for one target-scoped governance evidence query plan."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        param=query_params_for_operation(service, operation, params),
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=getattr(args, "timeout", 120),
        allow_sensitive_read=False,
    )


def compact_discovery_plan(args: argparse.Namespace, service: str, operation: str) -> dict[str, Any]:
    """Build a compact read-only discovery command plan."""
    plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, operation))
    return {
        "service": service,
        "operation": operation,
        "success": bool(plan.get("success")),
        "mode": plan.get("mode"),
        "metadata_backed": bool(plan.get("metadata_backed")),
        "coverage": plan.get("coverage"),
        "commands": plan.get("commands", []),
        "error": plan.get("error"),
        "required_params": plan.get("catalog_required_params", []),
    }


def compact_query_plan(
    args: argparse.Namespace,
    service: str,
    operation: str,
    params: dict[str, str],
) -> dict[str, Any]:
    """Build a compact target-scoped read query command plan."""
    plan = hcloud_resource_query.build_plan(query_args(args, service, operation, params))
    return {
        "service": service,
        "operation": plan.get("operation", operation),
        "requested_operation": plan.get("requested_operation"),
        "success": bool(plan.get("success")),
        "mode": plan.get("mode"),
        "metadata_backed": bool(plan.get("metadata_backed")),
        "coverage": plan.get("coverage"),
        "operation_scope": plan.get("operation_scope"),
        "required_params": plan.get("required_params", []),
        "provided_params": plan.get("provided_params", []),
        "missing_params": plan.get("missing_params", []),
        "command": plan.get("command"),
        "command_shell": plan.get("command_shell"),
        "risk": plan.get("risk"),
        "error": plan.get("error"),
    }


def evidence_command_plans(
    args: argparse.Namespace,
    profile_entries: list[dict[str, Any]],
    params: dict[str, str],
    *,
    billing_specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return read-only evidence command plans for governance profiles."""
    if billing_specs is not None:
        command_plans = [
            spec.get("hcloud_command_plan")
            for spec in billing_specs
            if isinstance(spec.get("hcloud_command_plan"), dict) and spec.get("hcloud_command_plan", {}).get("supported")
        ]
        return {
            "summary": {
                "discovery_plan_count": 0,
                "resource_query_plan_count": 0,
                "planned_command_count": len(command_plans),
                "missing_param_query_count": 0,
            },
            "discovery_plans": [],
            "resource_query_plans": [],
            "missing_param_items": [],
            "billing_hcloud_command_plans": command_plans,
            "execution_boundary": "planner_only; run billing safe_exec commands only after explicit live billing read approval.",
        }

    discovery_plans = []
    query_plans = []
    for entry in profile_entries:
        service = entry["service"]
        profile = entry.get("profile") or {}
        for operation in profile.get("readiness_operations", []) if isinstance(profile, dict) else []:
            discovery_plan = compact_discovery_plan(args, service, str(operation))
            discovery_plans.append(discovery_plan)
            if not discovery_plan.get("success"):
                query_plans.append(compact_query_plan(args, service, str(operation), params))
        for operation in profile.get("resource_query_operations", []) if isinstance(profile, dict) else []:
            query_plans.append(compact_query_plan(args, service, str(operation), params))

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
            "discovery_plan_count": len(discovery_plans),
            "resource_query_plan_count": len(query_plans),
            "planned_command_count": planned_command_count,
            "missing_param_query_count": len(missing_param_items),
        },
        "discovery_plans": discovery_plans,
        "resource_query_plans": query_plans,
        "missing_param_items": missing_param_items,
    }


def load_profiles() -> dict[str, Any]:
    """Load service curation profiles."""
    return hcloud_curated_promotion_audit.load_curation_profiles()


def profile_for(profiles: dict[str, Any], service_name: str) -> dict[str, Any] | None:
    """Return a curation profile for a service."""
    return hcloud_curated_promotion_audit.profile_for_service(profiles, service_name)


def audit_map(services: list[str], min_live_ops: int) -> dict[str, dict[str, Any]]:
    """Return promotion audit entries keyed by normalized service name."""
    if not services:
        return {}
    result = hcloud_curated_promotion_audit.audit(services=services, min_live_ops=min_live_ops)
    return {
        hcloud_catalog.normalize_token(str(item.get("service"))): item
        for item in result.get("candidates", [])
        if isinstance(item, dict)
    }


def profile_summaries(service_key: str, profiles: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact profile summaries for the underlying services."""
    summaries = []
    for service_name in SERVICE_GROUPS[service_key]:
        profile = profile_for(profiles, service_name)
        summary = hcloud_curated_promotion_audit.profile_summary(profile)
        summaries.append(
            {
                "service": service_name,
                "profile": summary,
                "profile_present": bool(summary),
            }
        )
    return summaries


def promotion_entries(service_key: str, audits: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return promotion audit snippets for the underlying services."""
    entries = []
    for service_name in SERVICE_GROUPS[service_key]:
        entry = audits.get(hcloud_catalog.normalize_token(service_name))
        if not entry:
            continue
        entries.append(
            {
                "service": entry.get("service"),
                "status": entry.get("status"),
                "eligible": entry.get("eligible"),
                "missing": entry.get("missing", []),
                "next_steps": entry.get("next_steps", []),
                "value": entry.get("value", {}),
                "live_read_smoked_operations": entry.get("live_read_smoked_operations", []),
                "readiness_discovery_candidates": entry.get("readiness_discovery_candidates", []),
                "resource_query_candidates": entry.get("resource_query_candidates", []),
            }
        )
    return entries


def profile_operations(profile_entries: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    """Return profile operations for each underlying service."""
    result = []
    for entry in profile_entries:
        profile = entry.get("profile") or {}
        operations = profile.get(field, []) if isinstance(profile, dict) else []
        result.append({"service": entry["service"], "operations": operations})
    return result


def service_governance_summary(
    service_key: str,
    promotion: list[dict[str, Any]],
    evidence: dict[str, Any],
    billing_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a compact governance readiness summary for one P1 service group."""
    if promotion:
        scores = [int((entry.get("value") or {}).get("score") or 0) for entry in promotion]
        eligible = [str(entry.get("service")) for entry in promotion if entry.get("eligible")]
        blocked = [str(entry.get("service")) for entry in promotion if not entry.get("eligible")]
        missing = [
            {"service": entry.get("service"), "missing": entry.get("missing", [])}
            for entry in promotion
            if entry.get("missing")
        ]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0
    else:
        eligible = []
        blocked = []
        missing = []
        average_score = 0

    billing_errors = [
        {"operation": spec.get("operation"), "errors": (spec.get("validation") or {}).get("errors", [])}
        for spec in billing_specs
        if not spec.get("success")
    ]
    evidence_summary = evidence.get("summary", {})
    if blocked or billing_errors or evidence_summary.get("missing_param_query_count"):
        status = "evidence_gap"
    elif eligible or service_key == "BILLING_BSS":
        status = "review_ready"
    else:
        status = "profile_only"
    return {
        "status": status,
        "average_value_score": average_score,
        "eligible_services": eligible,
        "blocked_services": blocked,
        "promotion_missing": missing,
        "billing_spec_errors": billing_errors,
        "evidence_summary": evidence_summary,
    }


def aggregate_governance_summary(service_plans: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a top-level P1 governance summary."""
    statuses = [plan.get("governance_summary", {}).get("status") for plan in service_plans]
    evidence_command_count = sum(
        int(plan.get("governance_summary", {}).get("evidence_summary", {}).get("planned_command_count") or 0)
        for plan in service_plans
    )
    missing_param_query_count = sum(
        int(plan.get("governance_summary", {}).get("evidence_summary", {}).get("missing_param_query_count") or 0)
        for plan in service_plans
    )
    blocked_services = [
        service
        for plan in service_plans
        for service in plan.get("governance_summary", {}).get("blocked_services", [])
    ]
    eligible_services = [
        service
        for plan in service_plans
        for service in plan.get("governance_summary", {}).get("eligible_services", [])
    ]
    return {
        "service_group_count": len(service_plans),
        "review_ready_group_count": statuses.count("review_ready"),
        "evidence_gap_group_count": statuses.count("evidence_gap"),
        "profile_only_group_count": statuses.count("profile_only"),
        "eligible_services": sorted(dict.fromkeys(eligible_services)),
        "blocked_services": sorted(dict.fromkeys(blocked_services)),
        "planned_evidence_command_count": evidence_command_count,
        "missing_param_query_count": missing_param_query_count,
    }


def build_service_plan(
    args: argparse.Namespace,
    service_key: str,
    params: dict[str, str],
    profiles: dict[str, Any],
    audits: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build one P1 governance closure service plan."""
    task = SERVICE_TASKS[service_key]
    profile_entries = profile_summaries(service_key, profiles)
    promotion = promotion_entries(service_key, audits)
    billing_specs = build_billing_specs(params) if service_key == "BILLING_BSS" else []
    evidence = evidence_command_plans(
        args,
        profile_entries,
        params,
        billing_specs=billing_specs if service_key == "BILLING_BSS" else None,
    )
    governance_summary = service_governance_summary(service_key, promotion, evidence, billing_specs)
    risk_profiles = [
        {
            "service": entry["service"],
            "risk_profile": (entry.get("profile") or {}).get("risk_profile", {}),
        }
        for entry in profile_entries
    ]
    return {
        "service_key": service_key,
        "services": SERVICE_GROUPS[service_key],
        "task": task["task"],
        "tenant_goals": task["tenant_goals"],
        "summary": task["summary"],
        "planning_only": True,
        "execution_supported": False,
        "governance_summary": governance_summary,
        "stages": [
            {
                "id": "governance_scope",
                "description": "Confirm tenant goal, scope, account/region/domain boundary, and required inputs.",
                "required_inputs": task["required_inputs"],
                "provided_params": {key: value for key, value in params.items() if key in task["required_inputs"]},
            },
            {
                "id": "read_only_evidence",
                "description": "Collect or plan read-only discovery and target-scoped evidence before any conclusion.",
                "readiness_operations": profile_operations(profile_entries, "readiness_operations"),
                "resource_query_operations": profile_operations(profile_entries, "resource_query_operations"),
                "evidence_command_plans": evidence,
                "billing_request_specs": billing_specs,
            },
            {
                "id": "risk_and_privacy_gate",
                "description": "Keep governance/security/cost data narrow and keep mutations behind hard gates.",
                "risk_profiles": risk_profiles,
                "mutation_boundary": "planner_only_no_submit",
                "sensitive_data_notes": [
                    "Governance data can expose owners, resource IDs, policies, audit traces, repository metadata, or spend.",
                    "Summaries should prefer counts, gaps, and scoped evidence over broad raw dumps.",
                ],
            },
            {
                "id": "review_plan",
                "description": "Convert evidence into reviewable governance gaps rather than immediate mutations.",
                "checks": task["review_checks"],
                "reporting_outputs": task["reporting_outputs"],
            },
            {
                "id": "promotion_readiness",
                "description": "Show what is still needed before curated promotion or guarded write support.",
                "promotion_audit": promotion,
                "profiles": profile_entries,
            },
        ],
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a planner-only P1 governance closure plan."""
    params = parse_params(args.param)
    selected = [canonical_service(service) for service in (args.service or P1_SERVICES)]
    unsupported = [service for service in selected if service not in SERVICE_TASKS]
    if unsupported:
        return {
            "success": False,
            "mode": "plan",
            "planning_only": True,
            "error": "Unsupported P1 governance service.",
            "unsupported_services": unsupported,
            "supported_services": list(P1_SERVICES),
        }

    selected = list(dict.fromkeys(selected))
    underlying_services = [
        service
        for service_key in selected
        for service in SERVICE_GROUPS[service_key]
    ]
    profiles = load_profiles()
    audits = audit_map(underlying_services, args.min_live_ops)
    service_plans = [build_service_plan(args, service_key, params, profiles, audits) for service_key in selected]
    return {
        "success": True,
        "mode": "plan",
        "planning_only": True,
        "scope": "P1 governance closure for tag, audit, backup, compliance, cost, security, analytics, and DevOps readiness.",
        "region": args.region,
        "project_id": args.project_id,
        "profile": args.profile,
        "selected_services": selected,
        "service_count": len(service_plans),
        "governance_summary": aggregate_governance_summary(service_plans),
        "services": service_plans,
        "global_boundaries": [
            "P1 governance closure is read-only/planner-only by default.",
            "No tag, tracker, backup, policy, billing, WAF, DLI, or repository mutation is generated by this planner.",
            "Curated promotion requires live read-smoke evidence, target-scoped queries, playbooks, risk profiles, and tests.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="P1 governance service. Defaults to all P1 services.")
    parser.add_argument("--param", action="append", default=[], help="Task parameter as KEY=VALUE. Can be repeated.")
    parser.add_argument("--region", help="Explicit cli-region for generated review context.")
    parser.add_argument("--project-id", help="Optional project_id for generated review context.")
    parser.add_argument("--profile", help="Optional cli-profile for generated review context.")
    parser.add_argument("--limit", type=int, default=10, help="Optional limit for generated read-only evidence commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout value carried into generated read-only command plans.")
    parser.add_argument("--min-live-ops", type=int, default=2, help="Minimum live-read-smoked ops used in promotion audit.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.min_live_ops < 1:
        parser.error("--min-live-ops must be greater than 0.")
    return args


def main() -> int:
    """Build the P1 governance closure plan."""
    args = parse_args()
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "mode": "plan", "planning_only": True, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
