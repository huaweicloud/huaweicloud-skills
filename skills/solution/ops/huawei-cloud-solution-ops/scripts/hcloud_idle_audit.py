#!/usr/bin/env python3
"""Identify idle-resource candidates from saved Huawei Cloud query JSON."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import hcloud_common
import hcloud_resource_verify

STOPPED_ECS_STATUSES = {"SHUTOFF", "STOPPED", "SHELVED", "SUSPENDED"}
ERROR_STATUSES = {"ERROR", "FAILED", "FAULT", "ABNORMAL"}
UNATTACHED_VOLUME_STATUSES = {"AVAILABLE"}
IDLE_EIP_STATUSES = {"DOWN", "UNBOUND", "INACTIVE"}
ELB_REVIEW_STATUSES = {"OFFLINE", "NO_MONITOR", "ERROR", "ABNORMAL"}
RDS_REVIEW_STATUSES = {"SHUTDOWN", "STOPPED", "FAILED", "FROZEN", "ABNORMAL"}
NAT_REVIEW_STATUSES = {"INACTIVE", "DOWN", "ERROR", "ABNORMAL"}
SENSITIVE_INGRESS_PORTS = {22, 80, 443, 3000, 5000, 8000, 8080}
PUBLIC_CIDRS = {"0.0.0.0/0", "::/0"}
SCOPE_KEYS = {
    "region": ("region", "cli_region", "region_id", "region_code"),
    "project_id": ("project_id", "projectId", "project"),
    "enterprise_project_id": ("enterprise_project_id", "enterpriseProjectId", "eps_id", "epsId"),
}
TAG_KEYS = ("tags", "resource_tags", "sys_tags")


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a UTF-8 file."""
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: Any) -> str | None:
    """Return a stripped string or None."""
    return hcloud_resource_verify.normalize(value)


def normalize_status(value: Any) -> str | None:
    """Return uppercase status text or None."""
    return hcloud_resource_verify.normalize_status(value)


def first_value(resource: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first present resource value from candidate keys."""
    return hcloud_resource_verify.first_value(resource, keys)


def unknown_if_empty(value: Any) -> str:
    """Return a normalized string or unknown."""
    return normalize(value) or "unknown"


def resource_scope(resource: dict[str, Any]) -> dict[str, str]:
    """Return region/project/EPS scope from resource fields or inherited inventory scope."""
    inherited = resource.get("_hcloud_scope") if isinstance(resource.get("_hcloud_scope"), dict) else {}
    scope: dict[str, str] = {}
    for key, field_names in SCOPE_KEYS.items():
        value = first_value(resource, field_names)
        if value is None:
            value = normalize(inherited.get(key))
        scope[key] = unknown_if_empty(value)
    return scope


def resource_tags(resource: dict[str, Any]) -> dict[str, Any] | str:
    """Return compact tag evidence or unknown."""
    for key in TAG_KEYS:
        value = resource.get(key)
        if isinstance(value, dict) and value:
            return value
        if isinstance(value, list) and value:
            compact: dict[str, Any] = {}
            for item in value:
                if not isinstance(item, dict):
                    continue
                tag_key = item.get("key") or item.get("tag_key") or item.get("name")
                tag_value = item.get("value") or item.get("tag_value")
                if tag_key:
                    compact[str(tag_key)] = tag_value
            return compact or value[:5]
    inherited = resource.get("_hcloud_scope") if isinstance(resource.get("_hcloud_scope"), dict) else {}
    inherited_tags = inherited.get("tags")
    if isinstance(inherited_tags, (dict, list)) and inherited_tags:
        return inherited_tags
    return "unknown"


def candidate_base(
    service: str,
    resource: dict[str, Any],
    *,
    candidate_type: str,
    confidence: str,
    reason: str,
) -> dict[str, Any]:
    """Return common candidate fields."""
    return {
        "service": service,
        "candidate_type": candidate_type,
        "confidence": confidence,
        "id": hcloud_resource_verify.resource_id(resource),
        "name": hcloud_resource_verify.resource_name(resource),
        "status": hcloud_resource_verify.resource_status(resource),
        "scope": resource_scope(resource),
        "tags": resource_tags(resource),
        "reason": reason,
        "evidence": compact_evidence(resource),
        "destructive_action_allowed": False,
        "required_human_checks": [
            "Confirm business owner, tags, environment, and retention policy.",
            "Check recent metrics, logs, backups, dependencies, and billing data before any release/downsize action.",
        ],
    }


def compact_evidence(resource: dict[str, Any]) -> dict[str, Any]:
    """Return a small non-sensitive evidence subset for a candidate."""
    keys = (
        "id",
        "name",
        "status",
        "state",
        "operating_status",
        "provisioning_status",
        "port_id",
        "associate_instance_id",
        "instance_id",
        "server_id",
        "volume_id",
        "size",
        "attachments",
        "created_at",
        "updated_at",
        "direction",
        "protocol",
        "ethertype",
        "port_range_min",
        "port_range_max",
        "remote_ip_prefix",
        "listeners",
        "pools",
        "members",
        "backup_policy",
        "backup_strategy",
        "region",
        "project_id",
        "enterprise_project_id",
        "tags",
    )
    return {key: resource.get(key) for key in keys if key in resource}


def eip_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return idle EIP candidates from one EIP resource."""
    bindings = hcloud_resource_verify.resource_bindings(resource)
    status = normalize_status(resource.get("status") or resource.get("state"))
    if bindings:
        return []
    confidence = "high" if status in IDLE_EIP_STATUSES or status is None else "medium"
    candidate = candidate_base(
        "EIP",
        resource,
        candidate_type="unbound_public_ip",
        confidence=confidence,
        reason="No binding fields were found on the public IP resource.",
    )
    candidate["recommended_readonly_followups"] = [
        "Run ShowPublicip for the publicip_id to confirm it is still unbound.",
        "Check bandwidth billing mode and recent traffic metrics before release or reuse.",
    ]
    return [candidate]


def evs_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return unattached EVS candidates from one volume resource."""
    status = normalize_status(resource.get("status") or resource.get("state"))
    attachments = resource.get("attachments")
    has_attachments = isinstance(attachments, list) and len(attachments) > 0
    if has_attachments or status not in UNATTACHED_VOLUME_STATUSES:
        return []
    candidate = candidate_base(
        "EVS",
        resource,
        candidate_type="unattached_volume",
        confidence="high",
        reason="Volume status is available and no attachments were found.",
    )
    candidate["recommended_readonly_followups"] = [
        "Run ShowVolume for the volume_id to confirm attachments are still empty.",
        "Check snapshots, backup policy, tags, and filesystem ownership before deleting or reusing the disk.",
    ]
    return [candidate]


def ecs_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return stopped or abnormal ECS review candidates."""
    status = normalize_status(resource.get("status") or resource.get("state"))
    if status not in STOPPED_ECS_STATUSES and status not in ERROR_STATUSES:
        return []
    confidence = "medium" if status in STOPPED_ECS_STATUSES else "high"
    candidate = candidate_base(
        "ECS",
        resource,
        candidate_type="stopped_or_abnormal_instance",
        confidence=confidence,
        reason=f"ECS status {status} should be reviewed for ownership, scheduling, and cost intent.",
    )
    candidate["recommended_readonly_followups"] = [
        "Run ShowServer and ListServerTags for the server_id.",
        "Check recent CPU/network/disk metrics and maintenance schedule before stop/start/delete decisions.",
    ]
    return [candidate]


def elb_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ELB resources that need idle or health review."""
    candidates: list[dict[str, Any]] = []
    status = normalize_status(resource.get("operating_status") or resource.get("provisioning_status") or resource.get("status"))
    if status in ELB_REVIEW_STATUSES:
        candidate = candidate_base(
            "ELB",
            resource,
            candidate_type="load_balancer_health_or_idle_review",
            confidence="medium",
            reason=f"ELB operating/provisioning status {status} needs listener, pool, and member verification.",
        )
        candidate["recommended_readonly_followups"] = [
            "Run ListListeners, ListPools, and ListMembers for the loadbalancer.",
            "Check access logs and backend health before release or reconfiguration.",
        ]
        candidates.append(candidate)

    for field, candidate_type in (("listeners", "load_balancer_without_listeners"), ("members", "load_balancer_without_members")):
        value = resource.get(field)
        if isinstance(value, list) and not value:
            candidate = candidate_base(
                "ELB",
                resource,
                candidate_type=candidate_type,
                confidence="medium",
                reason=f"ELB resource explicitly reports no {field}; verify it is not serving traffic.",
            )
            candidate["recommended_readonly_followups"] = [
                "Run ListListeners, ListPools, and ListMembers for the loadbalancer.",
                "Check recent access metrics and owner tags before release.",
            ]
            candidates.append(candidate)
    return candidates


def rds_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return RDS instances that need lifecycle or idle review."""
    candidates: list[dict[str, Any]] = []
    status = normalize_status(resource.get("status") or resource.get("state"))
    if status in RDS_REVIEW_STATUSES:
        candidate = candidate_base(
            "RDS",
            resource,
            candidate_type="database_lifecycle_review",
            confidence="medium",
            reason=f"RDS status {status} needs owner, backup, and dependency review.",
        )
        candidate["recommended_readonly_followups"] = [
            "Run the relevant Show* or ListBackups query for this instance.",
            "Check recent connections, backup retention, and application dependencies before stopping or deleting.",
        ]
        candidates.append(candidate)

    backup_policy = resource.get("backup_policy") or resource.get("backup_strategy")
    if isinstance(backup_policy, dict):
        keep_days = backup_policy.get("keep_days") or backup_policy.get("keepdays") or backup_policy.get("retention_days")
        enabled = backup_policy.get("enabled")
        if enabled is False or str(keep_days) in {"0", "None", ""}:
            candidate = candidate_base(
                "RDS",
                resource,
                candidate_type="database_backup_policy_review",
                confidence="high",
                reason="RDS backup policy appears disabled or has zero retention.",
            )
            candidate["recommended_readonly_followups"] = [
                "Run ShowBackupPolicy/ListBackups for the instance.",
                "Confirm RPO/RTO and retention requirements before changing database lifecycle state.",
            ]
            candidates.append(candidate)
    return candidates


def nat_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return NAT gateways that need idle or rule review."""
    status = normalize_status(resource.get("status") or resource.get("state"))
    if status not in NAT_REVIEW_STATUSES:
        return []
    candidate = candidate_base(
        "NAT",
        resource,
        candidate_type="nat_gateway_idle_review",
        confidence="medium",
        reason=f"NAT gateway status {status} should be checked against SNAT/DNAT rules and traffic.",
    )
    candidate["recommended_readonly_followups"] = [
        "Run ListNatGatewaySnatRules and ListNatGatewayDnatRules for the NAT gateway.",
        "Check route tables and recent traffic before release or reconfiguration.",
    ]
    return [candidate]


def parse_port(value: Any) -> int | None:
    """Return an integer port value when parseable."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def ingress_rule_exposes_sensitive_port(resource: dict[str, Any]) -> bool:
    """Return True when a security group rule exposes a sensitive port publicly."""
    direction = str(resource.get("direction") or "").lower()
    if direction and direction != "ingress":
        return False
    remote = str(resource.get("remote_ip_prefix") or resource.get("remote_group_id") or "").strip()
    if remote not in PUBLIC_CIDRS:
        return False
    protocol = str(resource.get("protocol") or "").lower()
    if protocol not in {"", "tcp", "any", "-1"}:
        return False
    minimum = parse_port(resource.get("port_range_min"))
    maximum = parse_port(resource.get("port_range_max"))
    if minimum is None and maximum is None:
        return True
    minimum = minimum if minimum is not None else maximum
    maximum = maximum if maximum is not None else minimum
    if minimum is None or maximum is None:
        return False
    return any(minimum <= port <= maximum for port in SENSITIVE_INGRESS_PORTS)


def vpc_candidates(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Return VPC/security-group governance candidates."""
    if not ingress_rule_exposes_sensitive_port(resource):
        return []
    candidate = candidate_base(
        "VPC",
        resource,
        candidate_type="public_sensitive_ingress_rule",
        confidence="high",
        reason="Security group ingress rule exposes a sensitive management or web port to a public CIDR.",
    )
    candidate["recommended_readonly_followups"] = [
        "Run ShowSecurityGroupRule or ListSecurityGroupRules to confirm the rule still exists.",
        "Identify owner and intended source CIDR before planning a restrictive replacement.",
    ]
    return [candidate]


RULES = {
    "ECS": ecs_candidates,
    "EIP": eip_candidates,
    "ELB": elb_candidates,
    "EVS": evs_candidates,
    "NAT": nat_candidates,
    "RDS": rds_candidates,
    "VPC": vpc_candidates,
}


def analyze_payload(service: str, payload: Any, scope: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return idle-resource candidates from one service payload."""
    service = service.upper()
    rule = RULES.get(service)
    if not rule:
        return []
    candidates: list[dict[str, Any]] = []
    for resource in hcloud_resource_verify.collect_dicts(payload, service):
        if scope:
            resource = dict(resource)
            resource["_hcloud_scope"] = scope
        candidates.extend(rule(resource))
    return candidates


def audit_payloads(payloads: list[tuple[Any, ...]]) -> dict[str, Any]:
    """Return a conservative idle-candidate audit for service payloads."""
    candidates: list[dict[str, Any]] = []
    analyzed_services = set()
    for item in payloads:
        service, payload = item[0], item[1]
        scope = item[2] if len(item) > 2 and isinstance(item[2], dict) else None
        service_key = str(service).upper()
        analyzed_services.add(service_key)
        candidates.extend(analyze_payload(service_key, payload, scope))

    by_service = Counter(candidate["service"] for candidate in candidates)
    by_type = Counter(candidate["candidate_type"] for candidate in candidates)
    by_confidence = Counter(candidate["confidence"] for candidate in candidates)
    by_region = Counter(candidate["scope"]["region"] for candidate in candidates)
    by_enterprise_project = Counter(candidate["scope"]["enterprise_project_id"] for candidate in candidates)
    unsupported = sorted(analyzed_services - set(RULES))
    return {
        "success": True,
        "candidate_count": len(candidates),
        "summary": {
            "analyzed_services": sorted(analyzed_services),
            "unsupported_services": unsupported,
            "by_service": dict(sorted(by_service.items())),
            "by_type": dict(sorted(by_type.items())),
            "by_confidence": dict(sorted(by_confidence.items())),
            "by_region": dict(sorted(by_region.items())),
            "by_enterprise_project": dict(sorted(by_enterprise_project.items())),
        },
        "candidates": candidates,
        "next_steps": [
            "Treat candidates as review prompts, not deletion approval.",
            "Before any release/downsize action, confirm owner, tags, recent metrics, backups, and dependency graph.",
            "Use hcloud_account_inventory.py and service-specific Show/List follow-ups to refresh evidence.",
        ],
    }


def parse_service_path(value: str) -> tuple[str, Path]:
    """Parse SERVICE=PATH input references."""
    if "=" not in value:
        raise ValueError(f"Invalid --input-json-file value, expected SERVICE=PATH: {value}")
    service, raw_path = value.split("=", 1)
    service = service.strip().upper()
    path = Path(raw_path).expanduser()
    if not service or not raw_path:
        raise ValueError(f"Invalid --input-json-file value, expected SERVICE=PATH: {value}")
    return service, path


def payloads_from_inventory(value: Any) -> list[tuple[str, Any, dict[str, Any]]]:
    """Extract executed check payloads from hcloud_account_inventory output."""
    payloads: list[tuple[str, Any, dict[str, Any]]] = []
    if not isinstance(value, dict):
        return payloads
    for check in value.get("checks", []):
        if not isinstance(check, dict):
            continue
        service = str(check.get("service") or "").upper()
        plan = check.get("plan")
        if not service or not isinstance(plan, dict):
            continue
        scope = check.get("scope") if isinstance(check.get("scope"), dict) else {}
        for result in plan.get("results", []):
            if isinstance(result, dict) and isinstance(result.get("result"), dict):
                payloads.append((service, result["result"], scope))
        if "result" in plan:
            payloads.append((service, plan, scope))
    return payloads


def load_payloads(args: argparse.Namespace) -> list[tuple[Any, ...]]:
    """Load service payloads from CLI arguments."""
    payloads: list[tuple[Any, ...]] = []
    for item in args.input_json_file:
        service, path = parse_service_path(item)
        payloads.append((service, load_json(path)))
    for item in args.inventory_json_file:
        payloads.extend(payloads_from_inventory(load_json(Path(item).expanduser())))
    return payloads


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-json-file",
        action="append",
        default=[],
        help="Saved query JSON as SERVICE=PATH. Can be repeated.",
    )
    parser.add_argument(
        "--inventory-json-file",
        action="append",
        default=[],
        help="Saved hcloud_account_inventory.py --execute output JSON. Can be repeated.",
    )
    parser.add_argument("--output-file", type=Path, help="Write the full JSON result privately and print a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if not args.input_json_file and not args.inventory_json_file:
        parser.error("Provide at least one --input-json-file or --inventory-json-file.")
    return args


def main() -> int:
    """Run the local idle-resource candidate audit."""
    args = parse_args()
    try:
        result = audit_payloads(load_payloads(args))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
        default_mode="audit",
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
