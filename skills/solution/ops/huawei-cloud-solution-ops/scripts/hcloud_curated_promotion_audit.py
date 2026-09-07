#!/usr/bin/env python3
"""Audit metadata-backed services against curated registry promotion criteria."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_catalog
import hcloud_common

DEFAULT_CANDIDATES = (
    "DCS",
    "CCI",
    "RFS",
    "UCS",
    "WAF",
    "CodeArtsRepo",
    "DLI",
    "CTS",
    "TMS",
    "CBR",
    "RMS",
    "Config",
    "LTS",
)
PROFILES_PATH = hcloud_common.REFERENCES_DIR / "service-curation-profiles.json"
REQUIRED_PROFILE_FIELDS = {
    "status",
    "target_coverage",
    "readiness_operations",
    "resource_query_operations",
    "playbooks",
    "risk_profile",
}
REQUIRED_RISK_PROFILE_FIELDS = {
    "mutation_policy",
    "default_risk",
    "submit_policy",
    "verification_policy",
}
SERVICE_GOAL_TAGS = {
    "ECS": {"上好云", "用好云"},
    "VPC": {"上好云", "管好云"},
    "EIP": {"上好云", "管好云"},
    "ELB": {"上好云", "用好云"},
    "EVS": {"上好云", "用好云"},
    "NAT": {"上好云", "管好云"},
    "RDS": {"用好云"},
    "DCS": {"用好云"},
    "CCE": {"上好云", "用好云"},
    "CCI": {"上好云", "用好云", "管好云"},
    "CDN": {"上好云", "用好云"},
    "DNS": {"上好云", "管好云"},
    "SCM": {"上好云", "管好云"},
    "OBS": {"上好云", "用好云", "管好云"},
    "CES": {"用好云", "管好云"},
    "RFS": {"上好云", "管好云"},
    "UCS": {"用好云", "管好云"},
    "WAF": {"管好云"},
    "DLI": {"用好云", "管好云"},
    "CTS": {"管好云"},
    "TMS": {"上好云", "管好云"},
    "CBR": {"用好云", "管好云"},
    "RMS": {"管好云"},
    "CONFIG": {"管好云"},
    "LTS": {"用好云", "管好云"},
}
CATEGORY_GOAL_TAGS = {
    "compute": {"上好云", "用好云"},
    "network": {"上好云", "管好云"},
    "storage": {"上好云", "用好云", "管好云"},
    "database": {"用好云"},
    "middleware": {"用好云"},
    "containers": {"上好云", "用好云"},
    "management & governance": {"管好云"},
    "security & compliance": {"管好云"},
}


def load_curation_profiles(path: Path = PROFILES_PATH) -> dict[str, Any]:
    """Load curated service maintenance and promotion candidate profiles."""
    if not path.exists():
        return {"schema_version": 1, "services": {}}
    return hcloud_common.load_json(path)


def profile_for_service(profiles: dict[str, Any], service_name: str) -> dict[str, Any] | None:
    """Return a curation profile by loose service name matching."""
    wanted = hcloud_catalog.normalize_token(service_name)
    for name, profile in profiles.get("services", {}).items():
        if hcloud_catalog.normalize_token(str(name)) == wanted and isinstance(profile, dict):
            return profile
    return None


def profile_missing_fields(profile: dict[str, Any] | None, expected_status: str | None = None) -> list[str]:
    """Return missing or incomplete profile fields."""
    if not profile:
        return ["curation_profile"]
    missing = [f"profile_field:{field}" for field in sorted(REQUIRED_PROFILE_FIELDS) if field not in profile]
    if expected_status and profile.get("status") != expected_status:
        missing.append(f"profile_status:{profile.get('status') or 'missing'}")
    risk_profile = profile.get("risk_profile")
    if not isinstance(risk_profile, dict):
        missing.append("risk_profile")
    else:
        missing.extend(
            f"risk_profile_field:{field}"
            for field in sorted(REQUIRED_RISK_PROFILE_FIELDS)
            if not risk_profile.get(field)
        )
    return missing


def playbook_missing_items(profile: dict[str, Any] | None, root: Path = hcloud_common.ROOT) -> list[str]:
    """Return missing playbook fields or files for a profile."""
    if not profile:
        return []
    playbooks = profile.get("playbooks")
    if not isinstance(playbooks, list) or not playbooks:
        return ["playbook"]
    missing = []
    for playbook in playbooks:
        playbook_path = root / str(playbook)
        if not playbook_path.exists():
            missing.append(f"playbook_file:{playbook}")
    return missing


def catalog_operation_missing_items(
    catalog_service: dict[str, Any],
    profile: dict[str, Any] | None,
    field: str,
) -> list[str]:
    """Return profile operations that do not resolve in the generated catalog."""
    if not profile:
        return []
    operations = profile.get(field)
    if not isinstance(operations, list):
        return [f"profile_field:{field}"]
    missing = []
    for operation_name in operations:
        if not hcloud_catalog.resolve_operation(catalog_service, str(operation_name)):
            missing.append(f"{field}:{operation_name}")
    return missing


def live_read_smoked_operations(confidence: dict[str, Any], service_name: str, catalog_service: dict[str, Any]) -> list[str]:
    """Return live-smoked read-only operations that still exist in the catalog."""
    service_confidence = hcloud_catalog.service_confidence(confidence, service_name)
    operations = service_confidence.get("operations", {})
    if not isinstance(operations, dict):
        return []
    result = []
    for operation_name, entry in operations.items():
        if not isinstance(entry, dict) or entry.get("confidence") != "live-read-smoked":
            continue
        operation = hcloud_catalog.resolve_operation(catalog_service, str(operation_name))
        if operation and hcloud_catalog.is_read_only(operation):
            result.append(str(operation.get("name") or operation_name))
    return sorted(dict.fromkeys(result))


def resource_query_candidates(catalog_service: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    """Return read-only operations that can become explicit resource query paths."""
    result = []
    for operation in catalog_service.get("operations", {}).values():
        if not isinstance(operation, dict) or not hcloud_catalog.is_read_only(operation):
            continue
        required = hcloud_catalog.required_param_names(operation)
        if not required:
            continue
        result.append(
            {
                "operation": operation.get("name"),
                "required_params": required,
                "summary": operation.get("summary"),
            }
        )
    result.sort(key=lambda item: str(item.get("operation", "")).lower())
    return result[:limit]


def promotion_candidate(
    service_name: str,
    catalog: dict[str, Any],
    registry: dict[str, Any],
    confidence: dict[str, Any],
    profiles: dict[str, Any],
    min_live_ops: int,
) -> dict[str, Any]:
    """Audit one service against the medium-coverage curated promotion line."""
    registry_services = registry.get("services", {})
    service_token = hcloud_catalog.normalize_token(service_name)
    if service_token in {hcloud_catalog.normalize_token(name) for name in registry_services}:
        return {
            "service": service_name,
            "status": "already_curated",
            "eligible": False,
            "missing": [],
        }

    catalog_service = hcloud_catalog.resolve_service(catalog, service_name)
    if not catalog_service:
        return {
            "service": service_name,
            "status": "missing_catalog_service",
            "eligible": False,
            "missing": ["catalog_service"],
        }

    live_ops = live_read_smoked_operations(confidence, service_name, catalog_service)
    profile = profile_for_service(profiles, service_name)
    discovery_ops = [
        str(operation.get("name"))
        for operation in hcloud_catalog.discovery_operations(catalog_service, 12)
        if operation.get("name")
    ]
    resource_ops = resource_query_candidates(catalog_service)
    missing = []
    if len(live_ops) < min_live_ops:
        missing.append(f"live_read_smoked_operations:{len(live_ops)}/{min_live_ops}")
    if not resource_ops:
        missing.append("resource_query_candidate")
    if not discovery_ops:
        missing.append("readiness_discovery_candidate")
    missing.extend(profile_missing_fields(profile, expected_status="candidate"))
    missing.extend(playbook_missing_items(profile))
    missing.extend(catalog_operation_missing_items(catalog_service, profile, "readiness_operations"))
    missing.extend(catalog_operation_missing_items(catalog_service, profile, "resource_query_operations"))

    value = candidate_value_profile(
        service_name=str(catalog_service.get("name") or service_name),
        category=str(catalog_service.get("category") or ""),
        eligible=not missing,
        live_read_smoked_operation_count=len(live_ops),
        min_live_ops=min_live_ops,
        has_resource_query_candidate=bool(resource_ops),
        has_readiness_discovery_candidate=bool(discovery_ops),
        profile=profile,
        missing=missing,
    )
    return {
        "service": str(catalog_service.get("name") or service_name),
        "status": "eligible" if not missing else "blocked",
        "eligible": not missing,
        "category": catalog_service.get("category"),
        "operation_count": catalog_service.get("operation_count"),
        "live_read_smoked_operations": live_ops,
        "live_read_smoked_operation_count": len(live_ops),
        "readiness_discovery_candidates": discovery_ops,
        "resource_query_candidates": resource_ops,
        "profile": profile_summary(profile),
        "missing": missing,
        "next_steps": promotion_next_steps(missing),
        "value": value,
    }


def tenant_goal_tags(service_name: str, category: str) -> list[str]:
    """Return tenant-goal tags for service value ranking."""
    tags = set(SERVICE_GOAL_TAGS.get(service_name.upper(), set()))
    tags.update(CATEGORY_GOAL_TAGS.get(category.strip().lower(), set()))
    return sorted(tags)


def candidate_value_profile(
    *,
    service_name: str,
    category: str,
    eligible: bool,
    live_read_smoked_operation_count: int,
    min_live_ops: int,
    has_resource_query_candidate: bool,
    has_readiness_discovery_candidate: bool,
    profile: dict[str, Any] | None,
    missing: list[str],
) -> dict[str, Any]:
    """Return a value-oriented ranking profile for one promotion candidate."""
    tags = set(tenant_goal_tags(service_name, category))
    score = 20
    reasons: list[str] = []
    if eligible:
        score += 30
        reasons.append("Candidate meets current promotion gates.")
    else:
        score += max(0, 18 - len(set(missing)) * 2)
        reasons.append("Candidate is blocked but may still be worth grooming if tenant value is high.")
    if live_read_smoked_operation_count >= min_live_ops:
        score += 15
        reasons.append("Read-only live-smoke evidence meets the configured threshold.")
    else:
        score += min(10, live_read_smoked_operation_count * 5)
    if has_resource_query_candidate:
        score += 10
        reasons.append("Has target-scoped read candidates for post-change or inventory verification.")
    if has_readiness_discovery_candidate:
        score += 10
        reasons.append("Has parameter-light discovery operations for readiness and inventory.")
    if profile:
        score += 8
        reasons.append("Has a curation profile to maintain service-specific policy.")
        profile_goal_tags = profile.get("tenant_goal_tags", [])
        if isinstance(profile_goal_tags, list):
            tags.update(str(item) for item in profile_goal_tags if item)
        if profile.get("user_value"):
            score += 4
            reasons.append("Profile documents user value for prioritization.")
    if "管好云" in tags:
        score += 8
        reasons.append("Supports governance, risk, visibility, or control-plane management goals.")
    if "用好云" in tags:
        score += 5
    if "上好云" in tags:
        score += 5

    score = min(score, 100)
    if score >= 80:
        priority = "high"
    elif score >= 55:
        priority = "medium"
    else:
        priority = "low"
    return {
        "score": score,
        "promotion_priority": priority,
        "tenant_goal_tags": sorted(tags),
        "scenario_tags": sorted(str(item) for item in profile.get("scenario_tags", []) if item) if profile else [],
        "reasons": reasons,
    }


def ranked_candidate_values(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidates sorted by value score without mutating candidate order."""
    ranked = []
    for candidate in candidates:
        value = candidate.get("value")
        if not isinstance(value, dict):
            continue
        ranked.append(
            {
                "service": candidate.get("service"),
                "status": candidate.get("status"),
                "eligible": candidate.get("eligible"),
                "score": value.get("score"),
                "promotion_priority": value.get("promotion_priority"),
                "tenant_goal_tags": value.get("tenant_goal_tags", []),
                "scenario_tags": value.get("scenario_tags", []),
            }
        )
    return sorted(ranked, key=lambda item: (int(item.get("score") or 0), str(item.get("service") or "")), reverse=True)


def profile_summary(profile: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a compact profile summary for audit output."""
    if not profile:
        return None
    summary = {
        "status": profile.get("status"),
        "target_coverage": profile.get("target_coverage"),
        "readiness_operations": profile.get("readiness_operations", []),
        "resource_query_operations": profile.get("resource_query_operations", []),
        "playbooks": profile.get("playbooks", []),
        "risk_profile": profile.get("risk_profile", {}),
    }
    for field in (
        "lifecycle_stage",
        "user_value",
        "tenant_goal_tags",
        "scenario_tags",
        "min_live_read_smoked_operations",
        "official_docs",
        "known_shape_exceptions",
    ):
        if field in profile:
            summary[field] = profile.get(field)
    return summary


def curated_service_health(
    registry: dict[str, Any],
    profiles: dict[str, Any],
    root: Path = hcloud_common.ROOT,
) -> dict[str, Any]:
    """Audit existing curated registry services for profile, playbook, and risk metadata."""
    findings = []
    for service_name, service_entry in registry.get("services", {}).items():
        profile = profile_for_service(profiles, service_name)
        missing = []
        missing.extend(profile_missing_fields(profile, expected_status="curated"))
        missing.extend(playbook_missing_items(profile, root=root))
        missing.extend(registry_profile_operation_missing_items(service_entry, profile))
        registry_playbooks = service_entry.get("playbooks")
        if not isinstance(registry_playbooks, list) or not registry_playbooks:
            missing.append("registry_playbook")
        else:
            for playbook in registry_playbooks:
                if not (root / str(playbook)).exists():
                    missing.append(f"registry_playbook_file:{playbook}")
        if profile and isinstance(registry_playbooks, list):
            profile_playbooks = set(str(item) for item in profile.get("playbooks", []) if item)
            registry_playbook_set = set(str(item) for item in registry_playbooks if item)
            if profile_playbooks and profile_playbooks != registry_playbook_set:
                missing.append("registry_profile_playbook_mismatch")
        findings.append(
            {
                "service": service_name,
                "coverage": service_entry.get("coverage"),
                "status": "ok" if not missing else "blocked",
                "missing": sorted(dict.fromkeys(missing)),
                "profile": profile_summary(profile),
            }
        )
    return {
        "service_count": len(findings),
        "ok_count": sum(1 for item in findings if item.get("status") == "ok"),
        "blocked_count": sum(1 for item in findings if item.get("status") == "blocked"),
        "findings": findings,
    }


def registry_profile_operation_missing_items(
    service_entry: dict[str, Any],
    profile: dict[str, Any] | None,
) -> list[str]:
    """Return profile read operations missing from the curated registry entry."""
    if not profile:
        return []
    registered = {
        hcloud_catalog.normalize_token(str(operation))
        for field in ("query_operations", "resource_query_operations")
        for operation in service_entry.get(field, [])
    }
    missing = []
    for field in ("readiness_operations", "resource_query_operations"):
        operations = profile.get(field)
        if not isinstance(operations, list):
            continue
        for operation in operations:
            if hcloud_catalog.normalize_token(str(operation)) not in registered:
                missing.append(f"registry_operation:{field}:{operation}")
    return missing


def promotion_next_steps(missing: list[str]) -> list[str]:
    """Return concrete next steps for unmet promotion criteria."""
    steps = []
    if any(item.startswith("live_read_smoked_operations") for item in missing):
        steps.append("Run additional read-only live smoke until at least the required number of operations are command_shape_ok.")
    if "resource_query_candidate" in missing:
        steps.append("Pick at least one read-only target-scoped operation and document its required params.")
    if "readiness_discovery_candidate" in missing:
        steps.append("Define one read-only readiness discovery operation for post-change or inventory checks.")
    if "curation_profile" in missing:
        steps.append("Add a candidate entry to references/service-curation-profiles.json.")
    if any(item.startswith("profile_field:") for item in missing):
        steps.append("Complete the candidate profile fields required by the curation contract.")
    if "playbook" in missing or any(item.startswith("playbook_file:") for item in missing):
        steps.append("Add a service playbook before adding the service to service-registry.json.")
    if "risk_profile" in missing or any(item.startswith("risk_profile_field:") for item in missing):
        steps.append("Document mutation risk posture, even if first curated coverage remains read-only.")
    if any(item.startswith("readiness_operations:") for item in missing):
        steps.append("Fix profile readiness operations so they resolve in the generated catalog.")
    if any(item.startswith("resource_query_operations:") for item in missing):
        steps.append("Fix profile resource query operations so they resolve in the generated catalog.")
    return steps


def audit(
    services: list[str] | None = None,
    catalog_path: Path = hcloud_catalog.CATALOG_PATH,
    registry_path: Path = hcloud_common.REGISTRY_PATH,
    confidence_path: Path = hcloud_catalog.CONFIDENCE_PATH,
    profiles_path: Path = PROFILES_PATH,
    min_live_ops: int = 2,
    include_curated: bool = False,
) -> dict[str, Any]:
    """Audit candidate services for curated registry promotion readiness."""
    catalog = hcloud_catalog.load_catalog(catalog_path)
    registry = hcloud_common.load_registry(registry_path)
    confidence = hcloud_catalog.load_confidence(confidence_path)
    profiles = load_curation_profiles(profiles_path)
    candidates = [
        promotion_candidate(service, catalog, registry, confidence, profiles, min_live_ops)
        for service in (services or list(DEFAULT_CANDIDATES))
    ]
    result = {
        "success": True,
        "criteria": {
            "min_live_read_smoked_operations": min_live_ops,
            "requires_resource_query_candidate": True,
            "requires_readiness_discovery_candidate": True,
            "requires_curation_profile": True,
            "requires_playbook_file": True,
            "requires_risk_profile": True,
            "includes_value_ranking": True,
        },
        "candidate_count": len(candidates),
        "eligible_count": sum(1 for item in candidates if item.get("eligible")),
        "blocked_count": sum(1 for item in candidates if item.get("status") == "blocked"),
        "already_curated_count": sum(1 for item in candidates if item.get("status") == "already_curated"),
        "candidates": candidates,
        "value_ranked_candidates": ranked_candidate_values(candidates),
    }
    if include_curated:
        result["curated_service_health"] = curated_service_health(registry, profiles)
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", help="Candidate service to audit. Can be repeated.")
    parser.add_argument("--catalog", default=str(hcloud_catalog.CATALOG_PATH), help="Generated catalog or catalog index path.")
    parser.add_argument("--registry", default=str(hcloud_common.REGISTRY_PATH), help="Curated service registry path.")
    parser.add_argument("--confidence", default=str(hcloud_catalog.CONFIDENCE_PATH), help="Confidence sidecar path.")
    parser.add_argument("--profiles", default=str(PROFILES_PATH), help="Service curation profiles path.")
    parser.add_argument("--min-live-ops", type=int, default=2, help="Minimum live-read-smoked operations required.")
    parser.add_argument("--include-curated", action="store_true", help="Also audit existing curated registry services.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.min_live_ops < 1:
        parser.error("--min-live-ops must be greater than 0.")
    return args


def main() -> int:
    """Run curated promotion readiness audit."""
    args = parse_args()
    result = audit(
        services=args.service,
        catalog_path=Path(args.catalog),
        registry_path=Path(args.registry),
        confidence_path=Path(args.confidence),
        profiles_path=Path(args.profiles),
        min_live_ops=args.min_live_ops,
        include_curated=args.include_curated,
    )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
