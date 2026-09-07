#!/usr/bin/env python3
"""Route Huawei Cloud Terraform goals to curated local examples and references."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_terraform_catalog

HCLOUD_FIRST_TERMS = {
    "查",
    "查询",
    "查看",
    "排错",
    "排障",
    "状态",
    "验证",
    "list",
    "show",
    "inspect",
    "debug",
    "troubleshoot",
}

TERRAFORM_TERMS = {
    "terraform",
    "tofu",
    "opentofu",
    "iac",
    "tf",
    "backend",
    "drift",
    "remote state",
    "state",
    "模块",
    "模板",
    "纳管",
    "导入",
    "漂移",
    "远程状态",
    "状态文件",
    "复制环境",
    "长期维护",
    "可重复",
}

REUSE_TERMS = {
    "reuse",
    "existing",
    "import",
    "复用",
    "现网",
    "已有",
    "既有",
    "导入",
    "纳管",
}

QUERY_VARIANT_HINTS = {
    "安全组": ("security_group", "secgroup"),
    "security group": ("security_group", "secgroup"),
    "对等连接": ("peering",),
    "peering": ("peering",),
    "插件": ("addon",),
    "addon": ("addon",),
    "coredns": ("coredns",),
    "turbo": ("turbo",),
    "分区": ("partition",),
    "partition": ("partition",),
    "只读副本": ("read_replica",),
    "读副本": ("read_replica",),
    "read replica": ("read_replica",),
    "高可用": ("high_availability", "ha"),
    "ha": ("high_availability", "ha"),
    "mysql": ("mysql",),
    "postgresql": ("postgresql",),
    "sql server": ("sqlserver",),
    "sqlserver": ("sqlserver",),
    "静态网站": ("static_site",),
    "static site": ("static_site",),
}

SERVICE_SYNONYMS = {
    "云服务器": "ECS",
    "弹性云服务器": "ECS",
    "公网": "EIP",
    "负载均衡": "ELB",
    "数据库": "RDS",
    "容器": "CCE",
    "集群": "CCE",
    "节点池": "CCE",
    "对象存储": "OBS",
    "静态网站": "OBS",
    "日志": "LTS",
    "监控": "CES",
    "域名": "DNS",
    "虚拟私有云": "VPC",
    "安全组": "VPC",
    "对等连接": "VPC",
    "出网": "NAT",
    "入站": "NAT",
}

CORE_REFERENCE_IDS = {
    "provider-auth",
    "provider-validation",
    "generation-guardrails",
    "operations",
    "discovery-workflow",
    "interop-with-hcloud",
    "service-variant-guide",
    "data-source-selection-guide",
    "troubleshooting",
}


def normalize_token(value: str) -> str:
    """Return a loose matching token."""
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def latin_parts(value: str) -> list[str]:
    """Return lowercase Latin/number parts for exact cloud service matching."""
    return re.findall(r"[a-z0-9]+", value.lower())


def canonical_service(value: str) -> str:
    """Return the known service casing when possible."""
    normalized = value.lower()
    for service in hcloud_terraform_catalog.SERVICE_ALIASES.values():
        if service.lower() == normalized:
            return service
    return value.upper()


def alias_matches_latin_parts(alias: str, parts: list[str]) -> bool:
    """Return True when an alias matches complete query tokens."""
    alias_parts = latin_parts(alias)
    if not alias_parts:
        return False
    if len(alias_parts) == 1:
        return alias_parts[0] in parts
    window = len(alias_parts)
    return any(parts[index : index + window] == alias_parts for index in range(0, len(parts) - window + 1))


def query_matches_term(term: str, normalized_query: str, latin_query_parts: list[str]) -> bool:
    """Return True when a term appears in the query without short-token substring leakage."""
    term_parts = latin_parts(term)
    if term_parts:
        return alias_matches_latin_parts(term, latin_query_parts)
    normalized_term = normalize_token(term)
    return bool(normalized_term and normalized_term in normalized_query)


def load_catalog(path: Path) -> dict[str, Any]:
    """Load a catalog JSON file."""
    if path.exists():
        return hcloud_common.load_json(path)
    if path == hcloud_terraform_catalog.EXAMPLE_CATALOG_PATH:
        return hcloud_terraform_catalog.build_example_catalog()
    return hcloud_terraform_catalog.build_reference_catalog()


def query_services(query: str, service_hint: str | None = None) -> set[str]:
    """Infer service names from query and optional hint."""
    services = set()
    if service_hint:
        services.add(canonical_service(service_hint))
    lowered = query.lower()
    parts = latin_parts(query)
    for text, service in SERVICE_SYNONYMS.items():
        if text.lower() in lowered:
            services.add(service)
    for alias, service in hcloud_terraform_catalog.SERVICE_ALIASES.items():
        if alias_matches_latin_parts(alias, parts) or service.lower() in parts:
            services.add(service)
    return services


def should_use_hcloud_first(query: str) -> bool:
    """Return True when a query is readback/debug only and not Terraform intent."""
    normalized = normalize_token(query)
    has_hcloud_term = any(normalize_token(term) in normalized for term in HCLOUD_FIRST_TERMS)
    has_terraform_term = any(normalize_token(term) in normalized for term in TERRAFORM_TERMS)
    return has_hcloud_term and not has_terraform_term


def score_example(example: dict[str, Any], query: str, services: set[str], category: str | None = None) -> tuple[int, list[str]]:
    """Return score and reasons for one Terraform example."""
    normalized = normalize_token(query)
    query_parts = latin_parts(query)
    example_id = str(example.get("id") or "")
    normalized_example_id = normalize_token(example_id)
    example_intents = {str(intent) for intent in example.get("intent", [])}
    score = 0
    reasons: list[str] = []
    has_reuse_intent = any(normalize_token(term) in normalized for term in REUSE_TERMS)

    if example.get("default_route"):
        score += 2
        reasons.append("default_route +2")
    if category and normalize_token(str(example.get("category") or "")) == normalize_token(category):
        score += 6
        reasons.append("category match +6")
    for service in services:
        if service in example.get("services", []):
            score += 10
            reasons.append(f"service:{service} +10")
    if services:
        extra_services = [service for service in example.get("services", []) if service not in services]
        if extra_services:
            penalty = min(4, len(extra_services) * 2)
            score -= penalty
            reasons.append(f"extra service scope -{penalty}")
    for intent in example.get("intent", []):
        if query_matches_term(str(intent), normalized, query_parts):
            score += 4
            reasons.append(f"intent:{intent} +4")
    for term, target_intents in QUERY_VARIANT_HINTS.items():
        if not query_matches_term(term, normalized, query_parts):
            continue
        if any(normalize_token(target) in normalized_example_id or target in example_intents for target in target_intents):
            bonus = 12 if "read_replica" in target_intents or "reuse_existing" in target_intents else 8
            score += bonus
            reasons.append(f"variant:{term} +{bonus}")
    if example.get("requires_existing_resources"):
        if has_reuse_intent:
            score += 10
            reasons.append("reuse intent +10")
        else:
            score -= 3
            reasons.append("reuse not requested -3")
    for token in hcloud_terraform_catalog.token_parts(example_id):
        if token and token in query_parts:
            score += 3
            reasons.append(f"id:{token} +3")
    summary = normalize_token(str(example.get("recommended_for") or ""))
    for service in services:
        if normalize_token(service) in summary:
            score += 2
            reasons.append(f"summary:{service} +2")
    return score, reasons[:8]


def suggested_references(reference_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Return core references agents should load before deep Terraform work."""
    refs = []
    for item in reference_catalog.get("references", []):
        if item.get("id") in CORE_REFERENCE_IDS:
            refs.append(item)
    refs.sort(key=lambda item: str(item.get("id")))
    return refs


def route(
    query: str,
    service: str | None = None,
    category: str | None = None,
    limit: int = 5,
    example_catalog_path: Path = hcloud_terraform_catalog.EXAMPLE_CATALOG_PATH,
    reference_catalog_path: Path = hcloud_terraform_catalog.REFERENCE_CATALOG_PATH,
) -> dict[str, Any]:
    """Route a Terraform goal to examples and references."""
    if should_use_hcloud_first(query):
        return {
            "success": False,
            "recommended_runtime": "hcloud",
            "reason": "The query looks like readback/debug/status work rather than Terraform IaC generation.",
            "query": query,
            "matches": [],
            "routing_boundary": "Use hcloud discovery/query/verification first. Terraform is for IaC generation, plan, apply, and drift review.",
        }

    example_catalog = load_catalog(example_catalog_path)
    reference_catalog = load_catalog(reference_catalog_path)
    services = query_services(query, service)
    matches = []
    for example in example_catalog.get("examples", []):
        if services and not any(service_name in example.get("services", []) for service_name in services):
            continue
        score, reasons = score_example(example, query, services, category=category)
        if score <= 0:
            continue
        matches.append({**example, "score": score, "reasons": reasons})
    matches.sort(key=lambda item: (-int(item["score"]), not bool(item.get("default_route")), str(item["id"])))
    return {
        "success": bool(matches),
        "recommended_runtime": "terraform" if matches else "hcloud_then_terraform",
        "query": query,
        "service_hints": sorted(services),
        "category": category,
        "match_count": len(matches),
        "matches": matches[:limit],
        "references": suggested_references(reference_catalog),
        "hcloud_first_required": any(term in query.lower() for term in ("先查", "现网", "复用", "导入", "纳管", "import", "drift", "漂移")),
        "execution_boundary": "Router only selects assets. Run plan before apply; explicit confirmation is required for apply.",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Natural-language Terraform goal.")
    parser.add_argument("--service", help="Optional service hint, for example ECS or ELB.")
    parser.add_argument("--category", help="Optional category hint, for example network or database.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum examples to return.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    return args


def main() -> int:
    """Route a Terraform goal."""
    args = parse_args()
    result = route(args.query, service=args.service, category=args.category, limit=args.limit)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") or result.get("recommended_runtime") == "hcloud" else 1


if __name__ == "__main__":
    raise SystemExit(main())
