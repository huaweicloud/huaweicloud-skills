#!/usr/bin/env python3
"""Build a true-account regression plan for huaweicloud-skill scenarios."""

from __future__ import annotations

import argparse
from typing import Any

import hcloud_common

SCENARIOS: dict[str, dict[str, Any]] = {
    "environment": {
        "title": "Environment and credential readiness",
        "risk": "read_only",
        "required_inputs": ["profile or HW_* credentials", "region"],
        "tools": ["scripts/hcloud_environment_doctor.py --need hcloud --need live --pretty"],
        "acceptance": ["hcloud found", "profile or env credentials ready", "region/project context understood"],
    },
    "core-service-validation": {
        "title": "ECS/VPC/EIP/OBS/ELB/RDS live validation profile",
        "risk": "read_only_then_protocol_probe",
        "required_inputs": ["region", "resource IDs for target services", "approved probe URLs/ports when user-path evidence is required"],
        "tools": ["scripts/hcloud_live_validation_plan.py --service ECS --service VPC --service EIP --service OBS --service ELB --service RDS --pretty"],
        "acceptance": ["missing service inputs are explicit", "hcloud readback plans are generated", "promotion gate gaps are recorded"],
    },
    "obs-static-site": {
        "title": "OBS static website and DNS/CDN handoff",
        "risk": "may_create_billable_resources",
        "required_inputs": ["test bucket name", "region", "optional domain", "cleanup decision"],
        "tools": [
            "scripts/hcloud_scenario_router.py 'OBS 静态网站自定义域名 CNAME 403 排查' --pretty",
            "scripts/hcloud_obs_readonly.py",
            "scripts/hcloud_acceptance_closure.py plan/run/evaluate",
        ],
        "acceptance": ["OBS website endpoint returns expected HTTP status", "DNS/CNAME evidence if domain is used", "cleanup plan recorded"],
    },
    "web-production": {
        "title": "Production Web/API closure",
        "risk": "may_create_billable_resources",
        "required_inputs": ["ECS or workload target", "ELB/DNS/HTTPS scope", "RDS scope if used", "allowed source CIDR"],
        "tools": [
            "scripts/hcloud_scenario_router.py '生产 Web 应用上线 ECS RDS ELB HTTPS WAF 闭环' --pretty",
            "scripts/hcloud_closure_plan.py --tier lifecycle",
            "scripts/hcloud_acceptance_closure.py chain",
        ],
        "acceptance": ["domain or ELB URL probe passes", "backend health evidence present", "RDS connection evidence if in scope"],
    },
    "monitoring": {
        "title": "ECS/CES monitoring troubleshooting",
        "risk": "read_only_or_alarm_plan",
        "required_inputs": ["ECS instance id", "metric namespace/dimension", "time window"],
        "tools": ["scripts/hcloud_ces_alarm_plan.py", "scripts/hcloud_observability_plan.py"],
        "acceptance": ["metric namespace/dimension identified", "datapoint or missing-agent reason recorded", "alarm remains planner-only unless approved"],
    },
    "eip-cost": {
        "title": "EIP idle and cost governance",
        "risk": "read_only_then_teardown_plan",
        "required_inputs": ["region", "cost review scope", "teardown approval policy"],
        "tools": ["scripts/hcloud_idle_audit.py", "scripts/hcloud_billing_result_summarize.py", "scripts/hcloud_teardown_plan.py"],
        "acceptance": ["unbound/high-bandwidth candidates classified", "billing correlation or permission gap recorded", "no release without teardown approval"],
    },
    "container-deploy": {
        "title": "SWR to CCI/CCE container deployment readiness",
        "risk": "may_create_billable_resources",
        "required_inputs": ["SWR namespace/repository/tag", "CCI or CCE target", "public exposure scope"],
        "tools": ["scripts/hcloud_scenario_router.py '用 CCI 部署 SWR Docker 镜像 Service 暴露' --pretty"],
        "acceptance": ["image tag exists", "runtime target readiness known", "Service/ELB/DNS exposure evidence collected"],
    },
    "functiongraph": {
        "title": "FunctionGraph trigger/log readiness",
        "risk": "may_create_billable_resources",
        "required_inputs": ["function name/id", "trigger type", "LTS/log expectation"],
        "tools": ["scripts/hcloud_scenario_router.py 'FunctionGraph OBS 触发器 LTS 日志' --pretty"],
        "acceptance": ["function state read back", "trigger evidence read back", "log or missing-log reason recorded"],
    },
    "cce-assessment": {
        "title": "CCE cloud-native assessment",
        "risk": "read_only_plus_optional_kubectl",
        "required_inputs": ["cluster_id", "namespace/workload scope", "kubeconfig approval if Kubernetes evidence is needed"],
        "tools": ["scripts/hcloud_cce_assessment_plan.py --include-kubernetes --pretty"],
        "acceptance": ["control plane evidence planned", "node/addon/workload gaps identified", "no kubeconfig/token persisted"],
    },
    "maas-usage": {
        "title": "MaaS usage governance",
        "risk": "signed_read_only",
        "required_inputs": ["AK/SK configured locally", "project_id", "date range", "service type"],
        "tools": ["scripts/maas_usage_request_plan.py --pretty", "scripts/maas_usage_request_plan.py --execute --pretty"],
        "acceptance": ["ShowStatistics request spec reviewed", "optional read-only execution returns a redacted summary", "token unit conversion understood", "no credentials printed"],
    },
    "terraform-operations": {
        "title": "Terraform import/drift/remote state closure",
        "risk": "state_changing_if_import_is_executed",
        "required_inputs": ["Terraform workdir", "resource address to cloud id map", "backend policy", "state-change confirmation token"],
        "tools": ["scripts/hcloud_terraform_operations_plan.py --operation full --pretty"],
        "acceptance": ["hcloud discovery planned", "import commands reviewed", "drift plan reviewed", "hcloud readback planned after state changes"],
    },
}


def selected_scenarios(values: list[str]) -> list[str]:
    """Return selected scenario IDs in stable order."""
    if not values or "all" in values:
        return list(SCENARIOS)
    selected = []
    for value in values:
        if value not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {value}")
        selected.append(value)
    return selected


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a true-account regression plan."""
    scenario_ids = selected_scenarios(args.scenario)
    scenarios = []
    for scenario_id in scenario_ids:
        item = SCENARIOS[scenario_id]
        scenarios.append(
            {
                "id": scenario_id,
                **item,
                "region": args.region,
                "profile": args.profile,
                "status": "needs_user_execution",
            }
        )
    return {
        "success": True,
        "planning_only": True,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "user_assistance_required": [
            "Provide a non-production Huawei Cloud account or isolated test project.",
            "Configure hcloud profile or local credentials; do not paste AK/SK into chat.",
            "Provide resource IDs/domains for target-scoped tests.",
            "Approve any billable or state-changing step separately.",
        ],
        "evidence_policy": "Store only redacted summaries, command shape, status buckets, and resource IDs approved for reports.",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", choices=("all", *SCENARIOS.keys()), help="Scenario to include. Repeatable. Default: all.")
    parser.add_argument("--region", help="Optional target region for the regression run.")
    parser.add_argument("--profile", help="Optional hcloud profile name for the regression run.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    try:
        result = build_plan(args)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
