#!/usr/bin/env python3
"""Route natural-language Huawei Cloud goals to local hcloud-first guidance."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import hcloud_common

ROUTER_PATH = hcloud_common.REFERENCES_DIR / "scenario-router.json"
SERVICE_ALIAS_PATH = hcloud_common.REFERENCES_DIR / "service-aliases.json"
SCENARIO_CONTRACT_PATH = hcloud_common.REFERENCES_DIR / "scenario-contracts.json"

TERRAFORM_ROUTE = {
    "context_inspect": "scripts/hcloud_terraform_context_inspect.py",
    "router": "scripts/hcloud_terraform_router.py",
    "workflow": "references/terraform-workflow.md",
    "asset_index": "references/terraform/terraform-assets.md",
    "boundary": "Use only when the user explicitly wants IaC, repeatable infrastructure, import, drift review, or long-term management.",
}
P0_CLOSURE_SERVICES = {"VPC", "EIP", "EVS", "ELB", "RDS", "OBS", "DNS", "SCM", "CDN", "CES", "LTS"}
P0_ACCEPTANCE_FOLLOWUPS = [
    {
        "step": "closure_plan",
        "tool": "scripts/hcloud_closure_plan.py",
        "purpose": "Build the selected lifecycle/governance/scenario closure plan; use --tier lifecycle for P0.",
    },
    {
        "step": "acceptance_closure",
        "tool": "scripts/hcloud_acceptance_closure.py",
        "purpose": "Use plan/run/evaluate subcommands to collect and judge acceptance evidence.",
    },
]

WEBSITE_TERMS = (
    "网站",
    "站点",
    "网页",
    "官网",
    "独立站",
    "静态网站",
    "静态站",
    "展示站",
    "商城",
    "电商",
    "web app",
    "web应用",
    "web 应用",
    "web api",
    "api服务",
    "api 服务",
)
DEPLOYMENT_TERMS = (
    "搭建",
    "部署",
    "创建",
    "购买",
    "上线",
    "发布",
    "托管",
    "运行",
    "放在",
)
ECS_COMPUTE_CONSTRAINT_TERMS = (
    "弹性云服务器",
    "云服务器",
    "虚拟机",
    "云主机",
    "服务器",
    "机器",
    "主机",
    "ecs",
    "ssh",
    "nginx",
    "docker",
    "公网 ip",
    "公网ip",
    "返回 ip",
    "返回ip",
    "ip 地址",
    "ip地址",
)
FLEXUS_CONSTRAINT_TERMS = (
    "flexus l",
    "flexus",
    "轻量应用服务器",
    "轻量服务器",
)
OBS_CONSTRAINT_TERMS = (
    "对象存储",
    "使用 obs",
    "用 obs",
    "接受 obs",
    "可以用 obs",
    "obs 静态",
    "obs",
)
STATIC_SITE_TERMS = (
    "纯静态",
    "静态网站",
    "静态站",
    "纯前端",
    "html/css/js",
)
DYNAMIC_CAPABILITY_TERMS = (
    "购物车",
    "订单",
    "支付",
    "库存",
    "用户登录",
    "管理后台",
    "后台任务",
    "服务端",
    "后端",
    "数据库",
)
COMMERCE_AMBIGUITY_TERMS = (
    "电商",
    "商城",
)


def normalize_token(value: str) -> str:
    """Return a lowercase alphanumeric/CJK-friendly token."""
    return re.sub(r"[\s_\-./:]+", "", value.lower())


def load_router(path: Path = ROUTER_PATH) -> dict[str, Any]:
    """Load scenario router JSON."""
    if not path.exists():
        return {"schema_version": 1, "scenarios": []}
    return hcloud_common.load_json(path)


def load_service_aliases(path: Path = SERVICE_ALIAS_PATH) -> dict[str, str]:
    """Load Chinese-English service aliases for query expansion."""
    if not path.exists():
        return {}
    data = hcloud_common.load_json(path)
    aliases = data.get("aliases", {})
    if not isinstance(aliases, dict):
        return {}
    return {str(alias): str(service).upper() for alias, service in aliases.items()}


def load_scenario_contracts(path: Path = SCENARIO_CONTRACT_PATH) -> dict[str, dict[str, Any]]:
    """Load local scenario contracts keyed by their matching scenario IDs."""
    if not path.exists():
        return {}
    data = hcloud_common.load_json(path)
    contracts = data.get("contracts", [])
    if not isinstance(contracts, list):
        return {}
    return {
        str(item["id"]): dict(item)
        for item in contracts
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
    }


def recommended_followups(scenario: dict[str, Any]) -> list[dict[str, str]]:
    """Return standard local follow-up steps for a matched scenario."""
    if bool(scenario.get("skip_standard_followups", False)):
        return []
    services = {str(service).upper() for service in scenario.get("services", [])}
    if services & P0_CLOSURE_SERVICES:
        return [dict(item) for item in P0_ACCEPTANCE_FOLLOWUPS]
    return []


def matched_signals(query: str, terms: tuple[str, ...]) -> list[str]:
    """Return configured intent signals found in a natural-language query."""
    query_lower = query.lower()
    query_token = normalize_token(query)
    return [
        term
        for term in terms
        if term.lower() in query_lower or normalize_token(term) in query_token
    ]


def analyze_web_architecture(query: str) -> dict[str, Any]:
    """Extract website hosting constraints and decide whether clarification is required."""
    website_signals = matched_signals(query, WEBSITE_TERMS)
    deployment_signals = matched_signals(query, DEPLOYMENT_TERMS)
    compute_signals = matched_signals(query, ECS_COMPUTE_CONSTRAINT_TERMS)
    flexus_signals = matched_signals(query, FLEXUS_CONSTRAINT_TERMS)
    obs_signals = matched_signals(query, OBS_CONSTRAINT_TERMS)
    static_signals = matched_signals(query, STATIC_SITE_TERMS)
    dynamic_signals = matched_signals(query, DYNAMIC_CAPABILITY_TERMS)
    commerce_signals = matched_signals(query, COMMERCE_AMBIGUITY_TERMS)

    # "轻量服务器" contains "服务器" but names a distinct product choice.
    if flexus_signals:
        compute_signals = [
            signal for signal in compute_signals if signal not in {"服务器"}
        ]

    applicable = bool(
        website_signals
        and (
            deployment_signals
            or compute_signals
            or flexus_signals
            or obs_signals
            or static_signals
            or dynamic_signals
            or commerce_signals
        )
    )
    explicit_constraints = [
        *({"type": "compute", "signal": signal} for signal in compute_signals),
        *({"type": "flexus", "signal": signal} for signal in flexus_signals),
        *({"type": "obs", "signal": signal} for signal in obs_signals),
    ]
    conflicts: list[str] = []
    if compute_signals and obs_signals:
        conflicts.append("同时指定了 ECS/机器与 OBS 静态托管，运行载体不唯一。")
    if flexus_signals and obs_signals:
        conflicts.append("同时指定了 Flexus/轻量服务器与 OBS 静态托管，运行载体不唯一。")
    if obs_signals and dynamic_signals:
        conflicts.append("OBS 静态托管不能承载已声明的服务端动态能力。")

    recommended_architecture: str | None = None
    clarification_required = False
    clarification_question: str | None = None

    if applicable and conflicts:
        clarification_required = True
        clarification_question = (
            "你同时指定了不同运行载体或不兼容能力。请确认最终使用 "
            "OBS 静态托管、Flexus，还是 ECS；如果需要服务端能力，请选择计算实例路径。"
        )
    elif applicable and compute_signals:
        recommended_architecture = "ecs_web" if dynamic_signals else "ecs_single"
    elif applicable and flexus_signals:
        recommended_architecture = "flexus_l"
    elif applicable and obs_signals:
        recommended_architecture = "obs_static"
    elif applicable and dynamic_signals:
        recommended_architecture = "dynamic_web"
        clarification_required = True
        clarification_question = (
            "该站点包含服务端动态能力。请确认使用 Flexus/单台 ECS，"
            "还是需要 ELB、RDS 等生产 Web 架构；确认前不要创建资源。"
        )
    elif applicable and commerce_signals:
        clarification_required = True
        clarification_question = (
            "你需要的是静态电商展示页，还是包含登录、购物车、订单、支付、"
            "库存或管理后台的真实电商站点？"
        )
    elif applicable and static_signals:
        recommended_architecture = "obs_static"
    elif applicable:
        clarification_required = True
        clarification_question = (
            "这个站点要使用 OBS 静态托管，还是部署到 Flexus/ECS 机器？"
            "如果需要返回公网 IP、运行后端或登录机器，请选择 ECS/Flexus 路径。"
        )

    return {
        "applicable": applicable,
        "website_intent": bool(website_signals),
        "website_signals": website_signals,
        "deployment_signals": deployment_signals,
        "explicit_constraints": explicit_constraints,
        "static_signals": static_signals,
        "dynamic_signals": dynamic_signals,
        "commerce_signals": commerce_signals,
        "architecture_conflicts": conflicts,
        "recommended_architecture": recommended_architecture,
        "clarification_required": clarification_required,
        "clarification_question": clarification_question,
    }


def architecture_score_adjustment(
    scenario_id: str,
    decision: dict[str, Any],
) -> tuple[int, str | None]:
    """Return a deterministic route boost derived from explicit web constraints."""
    recommended = decision.get("recommended_architecture")
    if recommended == "ecs_single" and scenario_id == "ecs-compute-readiness":
        return 40, "architecture:explicit compute target +40"
    if recommended == "ecs_web":
        if scenario_id == "web-application-production-readiness":
            return 48, "architecture:dynamic workload on explicit compute target +48"
        if scenario_id == "ecs-compute-readiness":
            return 32, "architecture:explicit compute target +32"
    if recommended == "obs_static" and scenario_id == "obs-static-website-hosting":
        return 40, "architecture:explicit static/OBS target +40"
    if recommended == "flexus_l" and scenario_id == "entry-level-web-hosting":
        return 40, "architecture:explicit Flexus target +40"
    if recommended == "dynamic_web" and scenario_id == "web-application-production-readiness":
        return 40, "architecture:dynamic web capabilities +40"
    if (
        recommended is None
        and decision.get("commerce_signals")
        and scenario_id == "web-application-production-readiness"
    ):
        return 24, "architecture:commerce clarification route +24"
    return 0, None


def score_scenario(
    scenario: dict[str, Any],
    query: str,
    category: str | None = None,
    service: str | None = None,
    service_aliases: dict[str, str] | None = None,
) -> tuple[int, list[str]]:
    """Return match score and reasons for one scenario."""
    query_token = normalize_token(query)
    query_lower = query.lower()
    scenario_services = {str(item).upper() for item in scenario.get("services", [])}
    score = 0
    reasons: list[str] = []

    if category and normalize_token(str(scenario.get("category") or "")) == normalize_token(category):
        score += 6
        reasons.append("category match +6")

    if service:
        service_token = normalize_token(service)
        services = [normalize_token(str(item)) for item in scenario.get("services", [])]
        if service_token in services:
            score += 8
            reasons.append("service match +8")

    for alias, mapped_service in (service_aliases or {}).items():
        alias_text = str(alias)
        if mapped_service not in scenario_services:
            continue
        if alias_text.lower() in query_lower or normalize_token(alias_text) in query_token:
            score += 8
            reasons.append(f"alias:{alias_text}->{mapped_service} +8")

    name = str(scenario.get("name") or "")
    if normalize_token(name) and normalize_token(name) in query_token:
        score += 10
        reasons.append("name match +10")

    for trigger in scenario.get("triggers", []):
        trigger_text = str(trigger)
        if trigger_text.lower() in query_lower or normalize_token(trigger_text) in query_token:
            score += 8
            reasons.append(f"trigger:{trigger_text} +8")

    description = str(scenario.get("description") or "")
    for word in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", query):
        if len(word) < 2:
            continue
        if word.lower() in description.lower():
            score += 2
            reasons.append(f"description:{word} +2")

    return score, reasons


def route(query: str, category: str | None = None, service: str | None = None, limit: int = 5, router_path: Path = ROUTER_PATH) -> dict[str, Any]:
    """Route a user goal to local scenario entries."""
    router = load_router(router_path)
    service_aliases = load_service_aliases()
    scenario_contracts = load_scenario_contracts()
    architecture_decision = analyze_web_architecture(query)
    matches = []
    for scenario in router.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        score, reasons = score_scenario(
            scenario,
            query,
            category=category,
            service=service,
            service_aliases=service_aliases,
        )
        architecture_adjustment, architecture_reason = architecture_score_adjustment(
            str(scenario.get("id") or ""),
            architecture_decision,
        )
        score += architecture_adjustment
        if architecture_reason:
            reasons.append(architecture_reason)
        if score <= 0:
            continue
        matches.append(
            {
                "id": scenario.get("id"),
                "name": scenario.get("name"),
                "category": scenario.get("category"),
                "score": score,
                "reasons": reasons[:8],
                "services": scenario.get("services", []),
                "primary_playbooks": scenario.get("primary_playbooks", []),
                "guides": scenario.get("guides", []),
                "planners": scenario.get("planners", []),
                "scenario_contract": scenario_contracts.get(str(scenario.get("id") or "")),
                "recommended_followups": recommended_followups(scenario),
                "sdk_supplements": scenario.get("sdk_supplements", []),
                "terraform_candidate": scenario.get("terraform_candidate", False),
                "terraform_route": TERRAFORM_ROUTE if scenario.get("terraform_candidate", False) else None,
            }
        )
    matches.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    return {
        "success": bool(matches),
        "query": query,
        "category": category,
        "service": service,
        "match_count": len(matches),
        "matches": matches[:limit],
        "architecture_decision": architecture_decision,
        "change_execution_blocked": bool(
            architecture_decision.get("clarification_required", False)
        ),
        "routing_boundary": "Routes to local hcloud-first playbooks/planners; does not install or execute external skills.",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Natural-language cloud goal.")
    parser.add_argument("--category", help="Optional scenario category filter hint.")
    parser.add_argument("--service", help="Optional service hint such as ECS or VPC.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum matches to return.")
    parser.add_argument("--router", type=Path, default=ROUTER_PATH, help="Path to scenario-router.json.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    return args


def main() -> int:
    """Route a scenario query."""
    args = parse_args()
    result = route(args.query, category=args.category, service=args.service, limit=args.limit, router_path=args.router)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
