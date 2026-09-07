#!/usr/bin/env python3
"""Build a read-only observability readiness plan for a cloud resource."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_discovery
import hcloud_resource_query

RESOURCE_STATE_QUERIES = {
    "ECS": ("ShowServer", "server_id"),
    "EIP": ("ShowPublicip", "publicip_id"),
    "ELB": ("ShowLoadBalancer", "loadbalancer_id"),
    "EVS": ("ShowVolume", "volume_id"),
    "NAT": ("ShowNatGateway", "nat_gateway_id"),
    "RDS": ("ShowInstanceConfiguration", "instance_id"),
    "CCE": ("ShowCluster", "cluster_id"),
    "CDN": ("ShowDomainDetail", "domain_id"),
    "SCM": ("ShowCertificate", "certificate_id"),
    "VPC": ("ShowVpc", "vpc_id"),
}

OBSERVABILITY_HINTS = {
    "ECS": {
        "dimension_hints": ["instance_id or server_id"],
        "signals": ["CPU utilization", "memory utilization", "disk usage", "network in/out", "instance status"],
    },
    "EIP": {
        "dimension_hints": ["publicip_id, bandwidth_id, or public IP address depending on returned CES metrics"],
        "signals": ["bandwidth inbound/outbound", "traffic volume", "packet rate", "binding state"],
    },
    "ELB": {
        "dimension_hints": ["loadbalancer_id, listener_id, pool_id, or member_id"],
        "signals": ["request count", "HTTP status distribution", "latency", "backend health", "connection count"],
    },
    "EVS": {
        "dimension_hints": ["volume_id or instance_id plus disk device dimension"],
        "signals": ["disk read/write throughput", "IOPS", "disk usage when in-band metrics exist"],
    },
    "RDS": {
        "dimension_hints": ["instance_id and engine-specific node dimensions"],
        "signals": ["CPU", "memory", "connections", "storage usage", "slow queries", "replication lag"],
    },
    "NAT": {
        "dimension_hints": ["nat_gateway_id and rule dimensions when available"],
        "signals": ["connection count", "traffic volume", "SNAT/DNAT rule health"],
    },
    "CCE": {
        "dimension_hints": ["cluster_id, node_id, workload, or namespace depending on metric scope"],
        "signals": ["cluster status", "node readiness", "pod health", "CPU/memory pressure"],
    },
    "CDN": {
        "dimension_hints": ["domain_id or domain name"],
        "signals": ["bandwidth", "traffic", "request count", "cache hit ratio", "HTTP status distribution"],
    },
}


def metric_discovery_args(args: argparse.Namespace) -> SimpleNamespace:
    """Return hcloud_resource_discovery arguments for CES metric discovery."""
    return SimpleNamespace(
        service="CES",
        operation="ListMetrics",
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=1,
        execute=False,
        timeout=args.timeout,
    )


def resource_query_args(args: argparse.Namespace, operation: str, param_name: str) -> SimpleNamespace:
    """Return hcloud_resource_query arguments for a target resource state check."""
    return SimpleNamespace(
        service=args.service.upper(),
        operation=operation,
        param=[f"{param_name}={args.target_id}"],
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=args.execute,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def build_resource_state_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a target resource state check when a supported target ID is available."""
    service = args.service.upper()
    if not args.target_id:
        return {
            "success": True,
            "skipped": True,
            "reason": "No --target-id was provided.",
            "next_action": "Pass --target-id to add a service-specific Show* state check.",
        }
    query = RESOURCE_STATE_QUERIES.get(service)
    if query is None:
        return {
            "success": True,
            "skipped": True,
            "reason": f"No built-in state query mapping is registered for {service}.",
            "next_action": "Use hcloud_resource_query.py with an explicit Show/Get operation and parameters.",
        }
    operation, param_name = query
    return hcloud_resource_query.build_plan(resource_query_args(args, operation, param_name))


def observability_hints(service: str) -> dict[str, Any]:
    """Return service-specific observability hints without assuming exact CES metric names."""
    service = service.upper()
    hints = OBSERVABILITY_HINTS.get(
        service,
        {
            "dimension_hints": ["Confirm namespace and dimensions from CES ListMetrics before querying datapoints."],
            "signals": ["availability", "latency", "errors", "saturation", "traffic"],
        },
    )
    return {
        "service": service,
        "metric_discovery_first": True,
        **hints,
        "minimum_loop": [
            "Confirm resource exists and is in the expected state.",
            "Discover CES namespace, metric_name, and dimensions with ListMetrics.",
            "Select a recent time range and period that match the metric retention and aggregation.",
            "Interpret empty data as unknown until region, namespace, dimension, period, and collection delay are checked.",
        ],
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run a read-only observability readiness plan."""
    metric_plan = hcloud_resource_discovery.build_plan(metric_discovery_args(args))
    if metric_plan.get("success") and args.execute:
        metric_plan = hcloud_resource_discovery.execute_plan(metric_plan, args.timeout)

    state_plan = build_resource_state_plan(args)
    service = args.service.upper()
    success = bool(metric_plan.get("success")) and bool(state_plan.get("success", True))
    return {
        "success": success,
        "mode": "execute" if args.execute else "plan",
        "planning_only": not args.execute,
        "service": service,
        "target": {
            "id": args.target_id,
            "name": args.target_name,
            "region": args.region,
            "project_id": args.project_id,
        },
        "resource_state_plan": state_plan,
        "metric_discovery_plan": metric_plan,
        "hints": observability_hints(service),
        "next_steps": [
            "Run the metric discovery plan before assuming namespace, metric_name, or dimensions.",
            "Use resource state, CES metrics, service logs, and protocol checks together before declaring health.",
            "This planner does not create or modify alarms; alert-rule changes require a separate reviewed plan.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True, help="Target service, for example ECS, EIP, ELB, EVS, RDS.")
    parser.add_argument("--target-id", help="Optional target resource ID for a service-specific Show* state check.")
    parser.add_argument("--target-name", help="Optional human-readable target name for plan context.")
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=50, help="Metric discovery limit when supported.")
    parser.add_argument("--execute", action="store_true", help="Execute approved read-only metric discovery/state checks.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed read-only command.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Build or run the observability readiness plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
