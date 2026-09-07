#!/usr/bin/env python3
"""Evaluate local acceptance evidence against lifecycle closure plans."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_common

STATUS_ORDER = {"passed": 0, "warning": 1, "missing": 2, "blocked": 3}
PASSED_ALIASES = {"pass", "passed", "ok", "success", "healthy", "ready"}
WARNING_ALIASES = {"warn", "warning", "degraded"}
MISSING_ALIASES = {"missing", "not_collected", "unavailable", "unknown"}
BLOCKED_ALIASES = {"block", "blocked", "fail", "failed", "error", "critical"}


def normalize_status(value: Any) -> str:
    """Return a supported evidence status."""
    token = str(value or "").strip().lower().replace("-", "_")
    if token in PASSED_ALIASES:
        return "passed"
    if token in WARNING_ALIASES:
        return "warning"
    if token in MISSING_ALIASES:
        return "missing"
    if token in BLOCKED_ALIASES:
        return "blocked"
    return "warning"


def load_evidence_statuses(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return evidence item statuses keyed by item id."""
    source: Any = data.get("evidence", data)
    if isinstance(source, dict):
        result = {}
        for item_id, value in source.items():
            if isinstance(value, dict):
                result[str(item_id)] = {
                    "status": normalize_status(value.get("status", value.get("result"))),
                    "summary": value.get("summary") or value.get("message"),
                    "source": value.get("source"),
                }
            else:
                result[str(item_id)] = {"status": normalize_status(value), "summary": None, "source": None}
        return result
    if isinstance(source, list):
        result = {}
        for item in source:
            if not isinstance(item, dict) or "id" not in item:
                continue
            result[str(item["id"])] = {
                "status": normalize_status(item.get("status", item.get("result"))),
                "summary": item.get("summary") or item.get("message"),
                "source": item.get("source"),
            }
        return result
    return {}


def acceptance_plan_from_service(service: dict[str, Any]) -> dict[str, Any] | None:
    """Return the acceptance evidence plan from one lifecycle service entry."""
    for stage in service.get("stages", []):
        if isinstance(stage, dict) and stage.get("id") == "post_change_verification":
            plan = stage.get("acceptance_evidence_plan")
            return plan if isinstance(plan, dict) else None
    return None


def item_result(item: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Evaluate one planned evidence item."""
    item_id = str(item.get("id"))
    supplied = evidence.get(item_id)
    if supplied:
        status = normalize_status(supplied.get("status"))
        reason = supplied.get("summary") or "Evidence status was supplied."
        source = supplied.get("source")
    else:
        status = "missing"
        source = None
        if item.get("status") == "missing_inputs":
            missing = sorted(set(item.get("missing_required_inputs", []) + item.get("missing_any_of_inputs", [])))
            reason = f"Evidence cannot be collected until inputs are provided: {', '.join(missing)}."
        else:
            reason = "Evidence status was not supplied."
    return {
        "id": item_id,
        "layer": item.get("layer"),
        "status": status,
        "reason": reason,
        "source": source,
        "planned_status": item.get("status"),
        "description": item.get("description"),
    }


def aggregate_status(results: list[dict[str, Any]]) -> str:
    """Return the highest-severity service status."""
    if not results:
        return "missing"
    return max((str(item["status"]) for item in results), key=lambda value: STATUS_ORDER[value])


def evaluate_service(service: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Evaluate acceptance evidence for one lifecycle service."""
    plan = acceptance_plan_from_service(service)
    if not plan:
        return {
            "service": service.get("service"),
            "status": "missing",
            "error": "Lifecycle service has no acceptance_evidence_plan.",
            "item_results": [],
        }
    results = [item_result(item, evidence) for item in plan.get("evidence_items", [])]
    status = aggregate_status(results)
    return {
        "service": plan.get("service") or service.get("service"),
        "status": status,
        "completion_rule": plan.get("completion_rule"),
        "claim_boundaries": plan.get("claim_boundaries", []),
        "item_results": results,
        "summary": {
            "passed": sum(1 for item in results if item["status"] == "passed"),
            "warning": sum(1 for item in results if item["status"] == "warning"),
            "missing": sum(1 for item in results if item["status"] == "missing"),
            "blocked": sum(1 for item in results if item["status"] == "blocked"),
        },
    }


def evaluate_plan(plan: dict[str, Any], evidence_data: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a lifecycle closure plan using local evidence statuses."""
    evidence = load_evidence_statuses(evidence_data)
    services = [
        evaluate_service(service, evidence)
        for service in plan.get("services", [])
        if isinstance(service, dict)
    ]
    overall = aggregate_status(services)
    return {
        "success": True,
        "mode": "evaluate",
        "planning_only": True,
        "execution_boundary": "local_evidence_status_only_no_live_probe",
        "overall_status": overall,
        "service_count": len(services),
        "services": services,
        "summary": {
            "passed": sum(1 for item in services if item["status"] == "passed"),
            "warning": sum(1 for item in services if item["status"] == "warning"),
            "missing": sum(1 for item in services if item["status"] == "missing"),
            "blocked": sum(1 for item in services if item["status"] == "blocked"),
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", type=Path, required=True, help="Lifecycle closure plan JSON.")
    parser.add_argument("--evidence-file", type=Path, required=True, help="Local evidence status JSON.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Evaluate local acceptance evidence and print JSON."""
    args = parse_args()
    result = evaluate_plan(hcloud_common.load_json(args.plan_file), hcloud_common.load_json(args.evidence_file))
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
