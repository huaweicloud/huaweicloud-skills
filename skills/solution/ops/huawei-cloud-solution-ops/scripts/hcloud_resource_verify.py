#!/usr/bin/env python3
"""Verify service-specific Huawei Cloud resource state from JSON query results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import hcloud_common

load_json = hcloud_common.load_json


SERVICE_COLLECTION_KEYS = {
    "ECS": ("servers", "server", "cloudservers", "cloudserver", "items"),
    "EIP": ("publicips", "publicip", "eips", "floatingips", "items"),
    "VPC": (
        "vpcs",
        "vpc",
        "subnets",
        "subnet",
        "security_groups",
        "security_group",
        "security_group_rules",
        "security_group_rule",
        "route_tables",
        "route_table",
        "routes",
        "route",
        "ports",
        "port",
        "firewall",
        "items",
    ),
    "ELB": (
        "loadbalancers",
        "loadbalancer",
        "listeners",
        "listener",
        "pools",
        "pool",
        "members",
        "member",
        "healthmonitors",
        "healthmonitor",
        "certificates",
        "certificate",
        "items",
    ),
    "EVS": ("volumes", "volume", "snapshots", "snapshot", "attachments", "job", "items"),
    "NAT": (
        "nat_gateways",
        "nat_gateway",
        "dnat_rules",
        "dnat_rule",
        "snat_rules",
        "snat_rule",
        "transit_ips",
        "transit_ip",
        "items",
    ),
    "RDS": ("instances", "instance", "configurations", "configuration", "items"),
    "CCE": ("clusters", "nodes", "items"),
    "CDN": ("domains", "domain", "items"),
    "DNS": ("recordsets", "recordset", "zones", "zone", "items"),
    "SCM": ("certificates", "certificate", "items"),
    "CES": ("metrics", "items"),
    "IMS": ("images", "image", "members", "member", "items"),
    "KPS": ("keypairs", "keypair", "keypair_detail", "items"),
}

ID_KEYS = (
    "id",
    "resource_id",
    "server_id",
    "publicip_id",
    "port_id",
    "volume_id",
    "instance_id",
    "cluster_id",
    "domain_id",
    "zone_id",
    "recordset_id",
    "certificate_id",
    "nat_gateway_id",
    "dnat_rule_id",
    "snat_rule_id",
    "transit_ip_id",
    "loadbalancer_id",
    "listener_id",
    "pool_id",
    "member_id",
    "healthmonitor_id",
    "snapshot_id",
    "image_id",
    "keypair_name",
    "security_group_id",
    "security_group_rule_id",
    "subnet_id",
    "vpc_id",
    "config_id",
    "configuration_id",
)
SERVICE_FALLBACK_ID_KEYS = {
    "ECS": ("id", "server_id"),
    "EIP": ("id", "publicip_id"),
    "VPC": (
        "id",
        "vpc_id",
        "subnet_id",
        "security_group_id",
        "security_group_rule_id",
        "port_id",
    ),
    "ELB": (
        "id",
        "loadbalancer_id",
        "listener_id",
        "pool_id",
        "member_id",
        "healthmonitor_id",
        "certificate_id",
    ),
    "EVS": ("id", "volume_id", "snapshot_id"),
    "NAT": ("id", "nat_gateway_id", "dnat_rule_id", "snat_rule_id", "transit_ip_id"),
    "RDS": ("id", "instance_id", "config_id", "configuration_id"),
    "CCE": ("id", "cluster_id"),
    "CDN": ("id", "domain_id"),
    "DNS": ("id", "zone_id", "recordset_id"),
    "SCM": ("id", "certificate_id"),
    "CES": ("id",),
    "IMS": ("id", "image_id"),
    "KPS": ("keypair_name",),
}
NAME_KEYS = (
    "name",
    "alias",
    "display_name",
    "instance_name",
    "cluster_name",
    "domain_name",
    "zone_name",
    "recordset_name",
    "certificate_name",
)
STATUS_KEYS = (
    "status",
    "state",
    "provisioning_status",
    "operating_status",
    "health_status",
    "admin_state_up",
    "volume_state",
    "domain_status",
    "certificate_status",
)
CIDR_KEYS = ("cidr", "cidr_v4", "vpc_cidr", "subnet_cidr", "gateway_ip")
BINDING_KEYS = (
    "instance_id",
    "associate_instance_id",
    "server_id",
    "port_id",
    "device_id",
    "bound_server_id",
    "resource_id",
)


def normalize(value: Any) -> str | None:
    """Return a stripped string or None."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_status(value: Any) -> str | None:
    """Return normalized status text for comparison."""
    text = normalize(value)
    return text.upper() if text else None


def unwrap_payload(payload: Any) -> Any:
    """Return raw service JSON from a hcloud_safe_exec result when needed."""
    if isinstance(payload, dict) and "parsed_json" in payload:
        return payload.get("parsed_json")
    return payload


def collect_dicts(payload: Any, service: str) -> list[dict[str, Any]]:
    """Collect candidate resource dictionaries from common service response shapes."""
    service = service.upper()
    keys = SERVICE_COLLECTION_KEYS.get(service, ("items",))
    fallback_id_keys = SERVICE_FALLBACK_ID_KEYS.get(service, ("id",))
    collected: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    collected.append(item)
            return
        if not isinstance(value, dict):
            return
        for key in keys:
            item = value.get(key)
            if isinstance(item, list):
                for nested in item:
                    if isinstance(nested, dict):
                        collected.append(nested)
            elif isinstance(item, dict):
                collected.append(item)
        if not collected and any(normalize(value.get(key)) for key in fallback_id_keys):
            collected.append(value)
            return
        if not collected:
            for nested in value.values():
                if isinstance(nested, (dict, list)):
                    visit(nested)

    visit(unwrap_payload(payload))
    return collected


def first_value(resource: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first present value for candidate keys."""
    for key in keys:
        value = normalize(resource.get(key))
        if value is not None:
            return value
    return None


def resource_id(resource: dict[str, Any]) -> str | None:
    """Return the most likely resource ID."""
    return first_value(resource, ID_KEYS)


def resource_name(resource: dict[str, Any]) -> str | None:
    """Return the most likely resource name."""
    return first_value(resource, NAME_KEYS)


def resource_status(resource: dict[str, Any]) -> str | None:
    """Return the most likely resource status."""
    for key in STATUS_KEYS:
        status = normalize_status(resource.get(key))
        if status is not None:
            return status
    return None


def resource_cidr(resource: dict[str, Any]) -> str | None:
    """Return the most likely CIDR-like field."""
    return first_value(resource, CIDR_KEYS)


def resource_bindings(resource: dict[str, Any]) -> set[str]:
    """Return IDs that indicate a resource binding or attachment."""
    values = {value for key in BINDING_KEYS if (value := normalize(resource.get(key)))}
    for attachment in resource.get("attachments", []) if isinstance(resource.get("attachments"), list) else []:
        if isinstance(attachment, dict):
            values.update(value for key in BINDING_KEYS if (value := normalize(attachment.get(key))))
            values.update(value for key in ("server_id", "device_id") if (value := normalize(attachment.get(key))))
    return values


def match_targets(resources: list[dict[str, Any]], target_ids: list[str], target_names: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Return matched resources and missing target descriptors."""
    matched: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    by_id = {resource_id(item): item for item in resources if resource_id(item)}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in resources:
        name = resource_name(item)
        if name:
            by_name.setdefault(name, []).append(item)

    for target_id in target_ids:
        item = by_id.get(target_id)
        if item is None:
            missing.append({"type": "id", "value": target_id})
        else:
            matched.append(item)
    for target_name in target_names:
        items = by_name.get(target_name, [])
        if not items:
            missing.append({"type": "name", "value": target_name})
        else:
            matched.extend(items)

    if not target_ids and not target_names:
        matched = resources

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in matched:
        identity = resource_id(item) or resource_name(item) or json.dumps(item, sort_keys=True, ensure_ascii=False)
        if identity in seen:
            continue
        unique.append(item)
        seen.add(identity)
    return unique, missing


def summarize_resource(resource: dict[str, Any]) -> dict[str, Any]:
    """Return a compact resource summary for verification output."""
    summary = {
        "id": resource_id(resource),
        "name": resource_name(resource),
        "status": resource_status(resource),
        "cidr": resource_cidr(resource),
        "bindings": sorted(resource_bindings(resource)),
    }
    return {key: value for key, value in summary.items() if value not in (None, [], "")}


def check_expected_status(resources: list[dict[str, Any]], statuses: list[str]) -> list[dict[str, Any]]:
    """Return resources whose status does not match expected statuses."""
    if not statuses:
        return []
    expected = {status.upper() for status in statuses}
    return [
        summarize_resource(item)
        for item in resources
        if resource_status(item) not in expected
    ]


def check_expected_cidr(resources: list[dict[str, Any]], expected_cidr: str | None) -> list[dict[str, Any]]:
    """Return resources whose CIDR-like field does not match expectation."""
    if not expected_cidr:
        return []
    return [summarize_resource(item) for item in resources if resource_cidr(item) != expected_cidr]


def check_expected_binding(resources: list[dict[str, Any]], expected_binding: str | None) -> list[dict[str, Any]]:
    """Return resources that are not bound or attached to the expected resource ID."""
    if not expected_binding:
        return []
    return [summarize_resource(item) for item in resources if expected_binding not in resource_bindings(item)]


def parse_expected_fields(values: list[str]) -> dict[str, str]:
    """Parse exact field expectations from KEY=VALUE strings."""
    expected: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid field expectation, expected KEY=VALUE: {value}")
        key, raw_expected = value.split("=", 1)
        key = key.strip()
        raw_expected = raw_expected.strip()
        if not key:
            raise ValueError(f"Invalid field expectation, missing key: {value}")
        expected[key] = raw_expected
    return expected


def check_expected_fields(resources: list[dict[str, Any]], expected_fields: dict[str, str]) -> list[dict[str, Any]]:
    """Return resources whose top-level fields do not match exact expectations."""
    mismatches: list[dict[str, Any]] = []
    for item in resources:
        field_errors = []
        for key, expected in expected_fields.items():
            actual = normalize(item.get(key))
            if actual != expected:
                field_errors.append({"field": key, "expected": expected, "actual": actual})
        if field_errors:
            summary = summarize_resource(item)
            summary["field_errors"] = field_errors
            mismatches.append(summary)
    return mismatches


def verify_payload(args: argparse.Namespace, payload: Any) -> dict[str, Any]:
    """Verify target resource state from a JSON payload."""
    resources = collect_dicts(payload, args.service)
    matched, missing = match_targets(resources, args.target_id, args.target_name)
    status_mismatches = check_expected_status(matched, args.expect_status)
    cidr_mismatches = check_expected_cidr(matched, args.expect_cidr)
    binding_mismatches = check_expected_binding(matched, args.expect_bound_to)
    field_mismatches = check_expected_fields(matched, parse_expected_fields(args.expect_field))
    failures = []
    if missing:
        failures.append("missing_targets")
    if args.require_match and not matched:
        failures.append("no_matched_resources")
    if status_mismatches:
        failures.append("status_mismatch")
    if cidr_mismatches:
        failures.append("cidr_mismatch")
    if binding_mismatches:
        failures.append("binding_mismatch")
    if field_mismatches:
        failures.append("field_mismatch")

    return {
        "success": not failures,
        "service": args.service.upper(),
        "verification_scope": "service_resource_state",
        "resource_count": len(resources),
        "matched_count": len(matched),
        "matched": [summarize_resource(item) for item in matched],
        "missing": missing,
        "status_mismatches": status_mismatches,
        "cidr_mismatches": cidr_mismatches,
        "binding_mismatches": binding_mismatches,
        "field_mismatches": field_mismatches,
        "failures": failures,
        "next_actions": next_actions(args.service.upper(), failures),
    }


def next_actions(service: str, failures: list[str]) -> list[str]:
    """Return service-specific next actions for failed verification."""
    if not failures:
        return []
    hints = {
        "EIP": "Check ListPublicips/ShowPublicip output and confirm status, port_id, and instance binding.",
        "VPC": "Check ListVpcs/ListSubnets/ListSecurityGroups and confirm CIDR, IDs, and security group rules.",
        "ELB": "Check load balancer provisioning_status, listener/pool IDs, and member operating_status.",
        "EVS": "Check ListVolumes/ShowVolume and confirm volume status, attachment target, and capacity.",
        "NAT": "Check ListNatGateways and rule list output, then confirm gateway/rule IDs and EIP dependencies.",
        "RDS": "Check ListInstances/Show* detail output and confirm instance status, engine, and backup settings.",
        "CCE": "Check ShowCluster/ListNodes output and confirm cluster/node statuses.",
        "CDN": "Check ListDomains/ShowDomainDetail output and confirm domain status, origin, HTTPS, and cache settings.",
        "DNS": "Check ListRecordSets output and confirm zone ID, record name, type, TTL, and values.",
        "SCM": "Check ListCertificates output and confirm certificate status, domain, expiration, and deployment target.",
    }
    return [hints.get(service, "Check the service list/show response and verify target IDs, names, and status fields.")]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Service to verify, for example EIP, VPC, ELB, EVS, RDS.")
    parser.add_argument("--json-file", required=True, help="Path to raw service JSON or hcloud_safe_exec JSON result.")
    parser.add_argument("--target-id", action="append", default=[], help="Expected resource ID. Can be repeated.")
    parser.add_argument("--target-name", action="append", default=[], help="Expected resource name. Can be repeated.")
    parser.add_argument("--expect-status", action="append", default=[], help="Allowed status. Can be repeated.")
    parser.add_argument("--expect-field", action="append", default=[], help="Expected top-level field as KEY=VALUE. Can be repeated.")
    parser.add_argument("--expect-cidr", help="Expected CIDR for VPC/subnet-like resources.")
    parser.add_argument("--expect-bound-to", help="Expected bound/attached target ID.")
    parser.add_argument("--require-match", action="store_true", help="Fail when no target is matched.")
    parser.add_argument("--output-file", type=Path, help="Write the full JSON result privately and print a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Verify resource state from a JSON file."""
    args = parse_args()
    try:
        result = verify_payload(args, hcloud_common.load_json(Path(args.json_file)))
    except (OSError, ValueError) as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_public_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
        default_mode="verify",
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
