#!/usr/bin/env python3
"""Build non-executing probe plans for lifecycle acceptance evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import hcloud_common

PROBE_TEMPLATES = {
    "entry_path_probe": ["tcp_connect <target-host> <port_range_min> from <remote_ip_prefix>"],
    "public_protocol_probe": ["curl -fsS --max-time 10 <probe_url-or-public-ip-url>"],
    "guest_device_filesystem": [
        "lsblk -f",
        "blkid",
        "findmnt <mountpoint>",
        "df -h <mountpoint>",
        "test -w <mountpoint> && touch <mountpoint>/.hcloud-skill-write-test && rm <mountpoint>/.hcloud-skill-write-test",
    ],
    "backend_health": ["Use ELB member health readback plus backend ECS/security group evidence."],
    "elb_protocol_probe": ["curl -fsS --max-time 10 <elb-probe-url>", "tcp_connect <elb-address> <listener_port>"],
    "client_connection_probe": ["Run a bounded DB client connection check from the intended source network; do not include credentials in output."],
    "static_site_or_object_probe": ["curl -fsS --max-time 10 <static-site-or-object-url>"],
    "dns_resolution_probe": ["dig +short <record_name>", "nslookup <record_name>"],
    "https_chain_probe": ["openssl s_client -connect <domain_name>:443 -servername <domain_name> </dev/null"],
    "cdn_and_origin_probe": ["curl -I --max-time 10 https://<domain_name>", "curl -I --max-time 10 <origin-url>"],
    "metric_window": ["Plan a bounded CES datapoint query after metric namespace/dimension discovery."],
    "bounded_log_window": ["Plan a bounded LTS query by group, stream, start/end time, and keyword."],
    "user_path_probe": ["curl -fsS --max-time 10 <probe_url>"],
}
GOVERNANCE_ONLY_LAYERS = {"governance"}


def acceptance_plan_from_service(service: dict[str, Any]) -> dict[str, Any] | None:
    """Return the acceptance evidence plan from one lifecycle service entry."""
    for stage in service.get("stages", []):
        if isinstance(stage, dict) and stage.get("id") == "post_change_verification":
            plan = stage.get("acceptance_evidence_plan")
            return plan if isinstance(plan, dict) else None
    return None


def probe_templates_for_item(item: dict[str, Any]) -> list[str]:
    """Return conservative non-executing probe templates for one evidence item."""
    item_id = str(item.get("id"))
    if item_id in PROBE_TEMPLATES:
        return PROBE_TEMPLATES[item_id]
    layer = str(item.get("layer") or "")
    if layer == "cloud_control_plane":
        return ["Use the lifecycle readiness/resource-query plan for cloud-control-plane readback."]
    if layer == "protocol_or_network":
        return ["Run a bounded protocol probe against the intended user path."]
    if layer == "observability":
        return ["Run bounded metric or log evidence collection only after selecting an explicit time window."]
    return ["Collect the named evidence item and attach a local evidence status before acceptance."]


def build_item_probe(item: dict[str, Any]) -> dict[str, Any]:
    """Build one non-executing probe plan item."""
    missing = sorted(set(item.get("missing_required_inputs", []) + item.get("missing_any_of_inputs", [])))
    status = "skipped_missing_inputs" if missing else "planned"
    layer = str(item.get("layer") or "")
    return {
        "id": item.get("id"),
        "layer": layer,
        "status": status,
        "execution_boundary": "not_executed",
        "requires_manual_context": layer in {"guest_runtime", "application_runtime"} or bool(missing),
        "missing_inputs": missing,
        "probe_templates": [] if status == "skipped_missing_inputs" else probe_templates_for_item(item),
        "notes": [
            "Templates are not executed by this planner.",
            "Do not include credentials, tokens, private keys, or raw sensitive logs in probe output.",
        ],
    }


def build_probe_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Build non-executing probe plans from a lifecycle closure plan."""
    services = []
    for service in plan.get("services", []):
        if not isinstance(service, dict):
            continue
        acceptance_plan = acceptance_plan_from_service(service)
        if not acceptance_plan:
            continue
        probes = [build_item_probe(item) for item in acceptance_plan.get("evidence_items", [])]
        services.append(
            {
                "service": acceptance_plan.get("service") or service.get("service"),
                "probe_count": len(probes),
                "planned_probe_count": sum(1 for item in probes if item["status"] == "planned"),
                "skipped_missing_input_count": sum(1 for item in probes if item["status"] == "skipped_missing_inputs"),
                "probes": probes,
                "claim_boundaries": acceptance_plan.get("claim_boundaries", []),
            }
        )
    return {
        "success": True,
        "mode": "plan",
        "planning_only": True,
        "execution_boundary": "templates_only_no_live_probe",
        "service_count": len(services),
        "services": services,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", type=Path, required=True, help="Lifecycle closure plan JSON.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    """Build and print non-executing probe plans."""
    args = parse_args()
    result = build_probe_plan(hcloud_common.load_json(args.plan_file))
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
