#!/usr/bin/env python3
"""Build a planner-only teardown review plan from idle-resource candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import hcloud_common

SERVICE_ORDER = {
    "ELB": 10,
    "NAT": 20,
    "EIP": 30,
    "EVS": 40,
    "ECS": 50,
    "RDS": 60,
    "VPC": 90,
}
ACTION_BY_TYPE = {
    "unbound_public_ip": "review_release_or_reuse_eip",
    "unattached_volume": "review_snapshot_then_delete_or_reuse_volume",
    "stopped_or_abnormal_instance": "review_stop_start_rebuild_or_delete_ecs",
    "load_balancer_health_or_idle_review": "review_elb_listeners_members_and_traffic",
    "load_balancer_without_listeners": "review_delete_empty_load_balancer",
    "load_balancer_without_members": "review_delete_or_repair_load_balancer_pool",
    "database_lifecycle_review": "review_rds_owner_backup_and_dependency",
    "database_backup_policy_review": "review_enable_or_fix_backup_policy",
    "nat_gateway_idle_review": "review_nat_rules_routes_and_traffic",
    "public_sensitive_ingress_rule": "review_restrict_security_group_rule",
}


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a UTF-8 file."""
    return json.loads(path.read_text(encoding="utf-8"))


def candidates_from_value(value: Any) -> list[dict[str, Any]]:
    """Extract idle-audit candidate objects from JSON input."""
    if isinstance(value, dict) and isinstance(value.get("candidates"), list):
        return [item for item in value["candidates"] if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, str]:
    """Return dependency-aware teardown review ordering."""
    service = str(candidate.get("service") or "").upper()
    return SERVICE_ORDER.get(service, 80), str(candidate.get("id") or candidate.get("name") or "")


def build_step(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    """Return one planner-only teardown review step."""
    service = str(candidate.get("service") or "").upper()
    candidate_type = str(candidate.get("candidate_type") or "resource_review")
    return {
        "step": index,
        "service": service,
        "candidate_type": candidate_type,
        "id": candidate.get("id"),
        "name": candidate.get("name"),
        "status": candidate.get("status"),
        "confidence": candidate.get("confidence"),
        "planned_action": ACTION_BY_TYPE.get(candidate_type, "review_resource_lifecycle"),
        "executable": False,
        "submit_command": None,
        "required_prechecks": [
            "Refresh read-only state immediately before any change.",
            "Confirm owner, tags, environment, dependencies, backups, metrics, and retention policy.",
            "Get explicit user approval for the exact resource and action before building any mutating command.",
        ],
        "verification_after_manual_change": [
            "Use service-specific Show/List queries to confirm the intended state.",
            "For delete/release flows, not_found or disappearance from List* can be expected only after explicit approved action.",
        ],
        "source_reason": candidate.get("reason"),
    }


def build_plan(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a non-executable teardown review plan."""
    ordered = sorted(candidates, key=candidate_sort_key)
    steps = [build_step(candidate, index + 1) for index, candidate in enumerate(ordered)]
    return {
        "success": True,
        "planning_only": True,
        "destructive_action_allowed": False,
        "candidate_count": len(candidates),
        "step_count": len(steps),
        "steps": steps,
        "next_steps": [
            "Treat this as a review checklist, not a teardown script.",
            "Run fresh read-only inventory and observability checks before any deletion/release plan.",
            "Use guarded change planners only after user approval for each exact resource action.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle-audit-json-file", required=True, help="Path to hcloud_idle_audit.py JSON output or a candidate list.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build a planner-only teardown review plan."""
    args = parse_args()
    try:
        candidates = candidates_from_value(load_json(Path(args.idle_audit_json_file)))
        result = build_plan(candidates)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
