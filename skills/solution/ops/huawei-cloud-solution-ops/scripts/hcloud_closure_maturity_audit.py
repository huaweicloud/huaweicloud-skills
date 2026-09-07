#!/usr/bin/env python3
"""Audit closure maturity tiers across huaweicloud-skill planners."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

import hcloud_common
import hcloud_governance_closure_plan
import hcloud_lifecycle_closure_plan
import hcloud_p2_scenario_closure_plan

ECS_SAMPLE_ASSETS = [
    "scripts/hcloud_context_inspect.py",
    "scripts/hcloud_resource_discovery.py",
    "scripts/hcloud_ecs_create_plan.py",
    "scripts/hcloud_change_plan.py",
    "scripts/hcloud_ecs_wait_job.py",
    "scripts/hcloud_ecs_verify_active.py",
    "references/playbooks/ecs-create-readiness.md",
    "references/playbooks/ecs-ssh-access-readiness.md",
]
METADATA_EVIDENCE_GAP_EXAMPLES = [
    "HSS",
    "SecMaster",
    "CFW",
    "DBSS",
    "KMS",
    "GaussDB",
    "GaussDBforNoSQL",
    "GaussDBforopenGauss",
    "DDS",
    "DDM",
    "DWS",
]
CURATION_PROFILES_PATH = hcloud_common.REFERENCES_DIR / "service-curation-profiles.json"
CLOSURE_TARGET_PROFILES_PATH = hcloud_common.REFERENCES_DIR / "live-validation-profiles.json"
CONFIDENCE_PATH = hcloud_common.REFERENCES_DIR / "hcloud-service-confidence.json"


def has_source_revision(last_smoke: dict[str, Any]) -> bool:
    """Return whether smoke evidence identifies a concrete source revision."""
    if last_smoke.get("commit") or last_smoke.get("source_ref"):
        return True
    evidence_source = last_smoke.get("evidence_source")
    if not isinstance(evidence_source, dict):
        return False
    return any(evidence_source.get(key) for key in ("skill_commit", "commit", "source_ref"))


def evidence_provenance_summary() -> dict[str, Any]:
    """Summarize maturity facts without treating target profiles as run history."""
    curation = hcloud_common.load_json(CURATION_PROFILES_PATH)
    closure_targets = hcloud_common.load_json(CLOSURE_TARGET_PROFILES_PATH)
    confidence = hcloud_common.load_json(CONFIDENCE_PATH)

    curation_services = curation.get("services", {})
    closure_services = closure_targets.get("services", {})
    status_counts = Counter(
        str(profile.get("status") or "unknown")
        for profile in curation_services.values()
        if isinstance(profile, dict)
    )

    live_smoke_entries: list[dict[str, Any]] = []
    live_smoke_services: set[str] = set()
    for service_name, service in confidence.get("services", {}).items():
        if not isinstance(service, dict):
            continue
        operations = service.get("operations", {})
        if not isinstance(operations, dict):
            continue
        for operation_name, operation in operations.items():
            if not isinstance(operation, dict) or operation.get("confidence") != "live-read-smoked":
                continue
            last_smoke = operation.get("last_smoke")
            live_smoke_services.add(str(service_name))
            live_smoke_entries.append(
                {
                    "service": str(service_name),
                    "operation": str(operation_name),
                    "last_smoke": last_smoke if isinstance(last_smoke, dict) else {},
                }
            )

    timestamp_keys = {"observed_at", "validated_at", "timestamp"}
    source_keys = {"evidence_source", "source", "report", "commit"}
    environment_keys = {"environment", "region", "cli_version", "runtime"}
    timestamped_count = sum(
        any(entry["last_smoke"].get(key) for key in timestamp_keys)
        for entry in live_smoke_entries
    )
    sourced_count = sum(
        any(entry["last_smoke"].get(key) for key in source_keys)
        for entry in live_smoke_entries
    )
    source_revision_count = sum(
        has_source_revision(entry["last_smoke"])
        for entry in live_smoke_entries
    )
    environment_count = sum(
        any(entry["last_smoke"].get(key) for key in environment_keys)
        for entry in live_smoke_entries
    )
    provenance_complete_count = sum(
        any(entry["last_smoke"].get(key) for key in timestamp_keys)
        and any(entry["last_smoke"].get(key) for key in source_keys)
        and has_source_revision(entry["last_smoke"])
        and any(entry["last_smoke"].get(key) for key in environment_keys)
        for entry in live_smoke_entries
    )
    if not live_smoke_entries:
        freshness_status = "not_available"
    elif timestamped_count == 0:
        freshness_status = "unknown_missing_observed_at"
    elif timestamped_count < len(live_smoke_entries):
        freshness_status = "partial_timestamps_age_not_evaluated"
    else:
        freshness_status = "timestamps_present_age_not_evaluated"

    return {
        "source_files": [
            "references/service-curation-profiles.json",
            "references/live-validation-profiles.json",
            "references/hcloud-service-confidence.json",
        ],
        "curation_profiles": {
            "service_count": len(curation_services),
            "status_counts": dict(sorted(status_counts.items())),
            "semantics": "current_design_and_maintenance_profiles",
        },
        "closure_target_profiles": {
            "service_count": len(closure_services),
            "semantics": "target_evidence_contract_not_run_history",
        },
        "live_smoke_evidence": {
            "service_count": len(live_smoke_services),
            "operation_count": len(live_smoke_entries),
            "timestamped_operation_count": timestamped_count,
            "sourced_operation_count": sourced_count,
            "source_revision_described_operation_count": source_revision_count,
            "environment_described_operation_count": environment_count,
            "provenance_complete_operation_count": provenance_complete_count,
            "freshness_status": freshness_status,
        },
        "recent_live_validation_claimed": False,
        "interpretation": [
            "Curation profiles describe the current design and maintenance boundary.",
            "Closure target profiles describe evidence contracts; they are not execution history.",
            "Only confidence entries marked live-read-smoked are counted as live operation evidence.",
            "This audit does not claim recent validation unless an external run record establishes age and environment.",
        ],
    }


def tier(
    tier_id: str,
    status: str,
    execution_boundary: str,
    services: list[str],
    implemented_assets: list[str],
    closure_outputs: list[str],
    remaining_gaps: list[str],
) -> dict[str, Any]:
    """Build one maturity tier entry."""
    return {
        "id": tier_id,
        "status": status,
        "execution_boundary": execution_boundary,
        "service_or_group_count": len(services),
        "services_or_groups": services,
        "implemented_assets": implemented_assets,
        "closure_outputs": closure_outputs,
        "remaining_gaps": remaining_gaps,
    }


def build_audit() -> dict[str, Any]:
    """Return a planner-only audit of current closure maturity."""
    p0_services = list(hcloud_lifecycle_closure_plan.CLOSURE_SERVICES)
    p1_services = list(hcloud_governance_closure_plan.P1_SERVICES)
    p2_groups = list(hcloud_p2_scenario_closure_plan.GROUP_SERVICES)
    tiers = [
        tier(
            "ecs_end_to_end_sample",
            "sample_reference",
            "guarded_plan_dryrun_submit_with_job_and_resource_readiness_guidance",
            ["ECS"],
            ECS_SAMPLE_ASSETS,
            [
                "dependency discovery",
                "create JSON validation",
                "security gate",
                "dry-run/submit plan",
                "ShowJob polling",
                "ACTIVE verification",
                "SSH/application readiness guidance",
            ],
            [
                "Not every ECS API is automated.",
                "Application readiness still needs task-specific protocol or host-level evidence.",
            ],
        ),
        tier(
            "p0_task_level_planner",
            "implemented_task_level_planner",
            "planner_only_no_live_probe",
            p0_services,
            [
                "scripts/hcloud_lifecycle_closure_plan.py",
                "scripts/hcloud_service_change_plan.py",
                "scripts/hcloud_service_readiness.py",
                "scripts/hcloud_resource_verify.py",
                "scripts/hcloud_obs_readonly.py",
                "scripts/hcloud_lts_readonly.py",
            ],
            [
                "six-stage closure plan",
                "service-specific risk gates",
                "readiness plan",
                "acceptance_evidence_plan",
                "governance/audit follow-up",
            ],
            [
                "Live protocol probes are planned, not executed by the lifecycle planner.",
                "Guest OS checks for EVS and application probes still require task-specific execution.",
                "Some write paths still require dedicated guarded flows before submit.",
            ],
        ),
        tier(
            "p1_governance_planner_only",
            "implemented_governance_planner",
            "planner_only_or_request_spec_only",
            p1_services,
            [
                "scripts/hcloud_governance_closure_plan.py",
                "scripts/hcloud_billing_readonly.py",
                "scripts/hcloud_curated_promotion_audit.py",
            ],
            [
                "inventory/candidate framing",
                "read-only evidence command plans",
                "Billing/BSS request specs without credentials or HTTP",
                "review plan",
                "curated promotion gaps",
            ],
            [
                "Governance mutations remain intentionally disabled.",
                "Billing live queries need a reviewed signed-request or SDK path before execution.",
            ],
        ),
        tier(
            "p2_scenario_planner_only",
            "implemented_scenario_planner",
            "planner_only_no_submit",
            p2_groups,
            [
                "scripts/hcloud_p2_scenario_closure_plan.py",
                "references/playbooks/cce-cluster-readiness.md",
                "references/playbooks/nat-gateway-readiness.md",
                "references/playbooks/dcs-readiness.md",
                "references/playbooks/rfs-stack-readiness.md",
                "references/playbooks/ucs-fleet-readiness.md",
            ],
            [
                "scenario scope",
                "read-only evidence command plan",
                "target-scoped parameter gaps",
                "risk boundary",
                "next closure steps",
            ],
            [
                "P2 groups are not ECS-level end-to-end flows.",
                "Cluster, NAT, cache, stack, fleet, security, key, IAM, and database mutations need dedicated guarded flows.",
            ],
        ),
        tier(
            "metadata_backed_evidence_gap",
            "evidence_gap_until_promoted",
            "discovery_readonly_or_planner_only",
            METADATA_EVIDENCE_GAP_EXAMPLES,
            [
                "references/hcloud-service-catalog.index.json",
                "references/hcloud-service-catalog/",
                "scripts/hcloud_catalog_readonly_smoke.py",
                "scripts/hcloud_curated_promotion_audit.py",
            ],
            [
                "service/operation discovery",
                "explicit-parameter read-only query planning",
                "planner-only mutation classification",
                "promotion gap reporting",
            ],
            [
                "Needs live read-smoke evidence before curated promotion.",
                "Needs playbook, risk profile, target-scoped verifier, and tests before higher maturity claims.",
            ],
        ),
    ]
    return {
        "success": True,
        "mode": "audit",
        "planning_only": True,
        "all_services_ecs_level": False,
        "summary": {
            "tier_count": len(tiers),
            "p0_service_count": len(p0_services),
            "p1_service_count": len(p1_services),
            "p2_group_count": len(p2_groups),
            "metadata_gap_example_count": len(METADATA_EVIDENCE_GAP_EXAMPLES),
            "highest_maturity": "ecs_end_to_end_sample",
            "current_focus": "Strengthen P0 acceptance evidence and keep P1/P2 boundaries explicit.",
        },
        "evidence_provenance": evidence_provenance_summary(),
        "tiers": tiers,
        "audit_boundary": "This audit reports local planner maturity only; it does not execute hcloud, SDK, or Terraform.",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build and print the closure maturity audit."""
    args = parse_args()
    result = build_audit()
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
