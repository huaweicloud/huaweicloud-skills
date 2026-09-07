#!/usr/bin/env python3
"""Probe local Huawei Cloud catalog support for billing and cost workflows."""

from __future__ import annotations

import argparse
from typing import Any

import hcloud_catalog
import hcloud_common

DEFAULT_SERVICE_TOKENS = ("BSS", "BSSINTL", "Billing", "Cost", "CBC", "BSSO")
DEFAULT_OPERATION_KEYWORDS = (
    "bill",
    "billing",
    "cost",
    "expense",
    "invoice",
    "order",
    "payment",
    "price",
    "pricing",
    "renew",
    "subscription",
    "usage",
)


def operation_text(operation: dict[str, Any]) -> str:
    """Return searchable text for one catalog operation."""
    fields = (
        operation.get("name"),
        operation.get("summary"),
        operation.get("description"),
        operation.get("path"),
    )
    return " ".join(str(item or "") for item in fields).lower()


def direct_service_candidates(catalog: dict[str, Any], service_tokens: list[str]) -> list[dict[str, Any]]:
    """Return exact service candidates for requested billing/cost service tokens."""
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for token in service_tokens:
        service = hcloud_catalog.resolve_service(catalog, token)
        if not service:
            continue
        name = str(service.get("name") or token)
        if name in seen:
            continue
        candidates.append(
            {
                "service": name,
                "service_key": service.get("service_key"),
                "category": service.get("category"),
                "description": service.get("description"),
                "operation_count": service.get("operation_count", len(service.get("operations", {}))),
            }
        )
        seen.add(name)
    return candidates


def keyword_operation_matches(
    catalog: dict[str, Any],
    keywords: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    """Return weak keyword matches across catalog operations."""
    lowered_keywords = [item.lower() for item in keywords]
    matches: list[dict[str, Any]] = []
    for _, service in hcloud_catalog.iter_services(catalog, expand=True):
        service_name = str(service.get("name") or service.get("service_key") or "")
        if not service_name:
            continue
        for operation in service.get("operations", {}).values():
            if not isinstance(operation, dict):
                continue
            text = operation_text(operation)
            matched_keywords = [keyword for keyword in lowered_keywords if keyword in text]
            if not matched_keywords:
                continue
            matches.append(
                {
                    "service": service_name,
                    "operation": operation.get("name"),
                    "matched_keywords": matched_keywords,
                    "read_only": hcloud_catalog.is_read_only(operation),
                    "action": operation.get("action"),
                    "required_params": hcloud_catalog.normalized_required_params(operation),
                    "summary": operation.get("summary"),
                    "match_strength": "weak_keyword_match",
                }
            )
    matches.sort(key=lambda item: (item["service"], str(item["operation"])))
    return matches[:limit]


def read_only_discovery_matches(
    matches: list[dict[str, Any]],
    service_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return keyword matches that are safe-looking read-only discovery operations."""
    return [
        item
        for item in matches
        if service_names is None or str(item.get("service") or "") in service_names
        if item.get("read_only") and not item.get("required_params") and item.get("action") in {"List", "Count", "Query", "Search"}
    ]


def assess_feasibility(
    direct_services: list[dict[str, Any]],
    direct_read_only_matches: list[dict[str, Any]],
    curated_registry_has_direct_service: bool,
) -> dict[str, Any]:
    """Return a conservative billing/cost feasibility assessment."""
    if not direct_services:
        return {
            "status": "not_available_in_current_catalog",
            "can_run_live_billing_query": False,
            "blockers": [
                "No direct BSS/Billing/Cost service is present in the bundled catalog or curated registry.",
                "Weak keyword operation matches are not enough to treat billing or cost management as supported.",
                "Do not infer cost, invoice, or spend from resource inventory alone.",
            ],
            "next_steps": [
                "Use hcloud_billing_readonly.py to build a planner-only request spec from Huawei Cloud official billing/cost API documentation.",
                "Research KooCLI service naming before adding any live billing probe.",
                "Add a curated billing service profile only after read-only billing operations are verified.",
                "Keep billing live probes read-only and avoid order, renewal, payment, subscription, or budget mutations.",
            ],
        }
    blockers = [
        "Curated registry coverage and live read-only smoke evidence are still required before default use.",
        "Mutating billing/order/payment operations require a hard manual gate and separate runbook.",
    ]
    if not curated_registry_has_direct_service:
        blockers.insert(0, "Direct billing/cost service candidates are metadata-backed but not curated registry coverage yet.")
    if not direct_read_only_matches:
        blockers.insert(0, "No direct billing/cost read-only discovery match was found for the selected keywords.")
    return {
        "status": "candidate_service_present",
        "can_run_live_billing_query": curated_registry_has_direct_service and bool(direct_read_only_matches),
        "blockers": blockers,
        "next_steps": [
            "Identify read-only billing operations with no required business parameters or explicit safe parameters.",
            "Run smoke tests only after confirming account, region/global endpoint, and permission boundaries.",
            "Document cost data freshness, currency, enterprise project scope, and pagination behavior.",
        ],
    }


def build_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Build a local billing/cost capability probe report."""
    catalog = hcloud_catalog.load_catalog()
    direct = direct_service_candidates(catalog, args.service_token)
    matches = keyword_operation_matches(catalog, args.operation_keyword, args.limit)
    read_only_matches = read_only_discovery_matches(matches)
    direct_service_names = {str(item.get("service") or "") for item in direct}
    direct_read_only_matches = read_only_discovery_matches(matches, direct_service_names)
    registry_services = hcloud_common.load_registry().get("services", {})
    curated_registry_has_direct_service = any(item["service"].upper() in registry_services for item in direct)
    return {
        "success": True,
        "mode": "local_catalog_probe",
        "service_tokens": args.service_token,
        "operation_keywords": args.operation_keyword,
        "direct_service_candidates": direct,
        "direct_service_count": len(direct),
        "operation_keyword_matches": matches,
        "operation_keyword_match_count": len(matches),
        "read_only_discovery_matches": read_only_matches,
        "read_only_discovery_match_count": len(read_only_matches),
        "direct_read_only_discovery_matches": direct_read_only_matches,
        "direct_read_only_discovery_match_count": len(direct_read_only_matches),
        "curated_registry_has_direct_service": curated_registry_has_direct_service,
        "assessment": assess_feasibility(direct, direct_read_only_matches, curated_registry_has_direct_service),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service-token",
        action="append",
        default=None,
        help="Billing/cost service token to resolve in the catalog. Can be repeated.",
    )
    parser.add_argument(
        "--operation-keyword",
        action="append",
        default=None,
        help="Operation keyword for weak catalog search. Can be repeated.",
    )
    parser.add_argument("--limit", type=int, default=40, help="Maximum weak keyword operation matches to return.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    args.service_token = args.service_token or list(DEFAULT_SERVICE_TOKENS)
    args.operation_keyword = args.operation_keyword or list(DEFAULT_OPERATION_KEYWORDS)
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    return args


def main() -> int:
    """Run the local billing/cost capability probe."""
    args = parse_args()
    result = build_probe(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
