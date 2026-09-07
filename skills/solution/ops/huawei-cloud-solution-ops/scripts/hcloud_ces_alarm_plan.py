#!/usr/bin/env python3
"""Build a planner-only CES alarm readiness and rule plan."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_discovery

METRIC_GUIDANCE_PATH = hcloud_common.REFERENCES_DIR / "observability" / "ces-ecs-metric-guidance.json"


def load_metric_guidance(path=METRIC_GUIDANCE_PATH) -> dict[str, Any]:
    """Load compact CES metric guidance."""
    if not path.exists():
        return {"schema_version": 1, "namespaces": {}}
    return hcloud_common.load_json(path)


def find_metric_guidance(
    namespace: str | None,
    metric_name: str | None,
    catalog: dict[str, Any] | None = None,
) -> tuple[str | None, str | None, dict[str, Any] | None, bool]:
    """Find metric guidance by exact name or alias."""
    if not namespace or not metric_name:
        return None, None, None, False
    catalog = catalog or load_metric_guidance()
    namespaces = catalog.get("namespaces", {})
    requested_namespace = namespace.strip()
    requested_metric = metric_name.strip()
    requested_namespace_info = namespaces.get(requested_namespace, {})
    requested_metrics = requested_namespace_info.get("metrics", {})
    if requested_metric in requested_metrics:
        return requested_namespace, requested_metric, requested_metrics[requested_metric], False

    for namespace_name, namespace_info in namespaces.items():
        metrics = namespace_info.get("metrics", {})
        if requested_metric in metrics:
            return namespace_name, requested_metric, metrics[requested_metric], False
        for canonical_name, metric_info in metrics.items():
            aliases = {str(alias) for alias in metric_info.get("aliases", [])}
            if requested_metric in aliases:
                return namespace_name, canonical_name, metric_info, True
    return None, None, None, False


def metric_guidance(args: argparse.Namespace) -> dict[str, Any] | None:
    """Return metric namespace, Agent, and period guidance for a draft alarm."""
    if not args.namespace or not args.metric_name:
        return None
    catalog = load_metric_guidance()
    namespaces = catalog.get("namespaces", {})
    recommended_namespace, recommended_metric, metric_info, alias_match = find_metric_guidance(
        args.namespace,
        args.metric_name,
        catalog,
    )
    namespace_info = namespaces.get(recommended_namespace or args.namespace, {})
    min_period = namespace_info.get("min_period")
    warnings: list[str] = []
    next_actions: list[str] = []

    if not metric_info:
        warnings.append("Metric is not present in the compact ECS CES guidance; run ListMetrics before using it.")
    if alias_match and recommended_metric:
        warnings.append(f"Metric name looks like an alias; prefer canonical metric name {recommended_metric}.")
    if recommended_namespace and recommended_namespace != args.namespace:
        warnings.append(
            f"Metric {args.metric_name} is not available in {args.namespace}; use {recommended_namespace} or choose a metric from ListMetrics."
        )
    if min_period and args.period < int(min_period):
        warnings.append(f"Requested period {args.period} is below the minimum period {min_period} for {recommended_namespace}.")
    if namespace_info.get("agent_required"):
        next_actions.extend(
            [
                "Verify the host monitoring Agent is installed and reporting before creating the alarm.",
                "If Agent cannot be installed, choose a SYS.ECS metric such as cpu_util or another metric returned by ListMetrics.",
            ]
        )

    return {
        "requested_namespace": args.namespace,
        "requested_metric_name": args.metric_name,
        "found": bool(metric_info),
        "recommended_namespace": recommended_namespace,
        "recommended_metric_name": recommended_metric,
        "canonical_name_used": bool(alias_match),
        "agent_required": bool(namespace_info.get("agent_required")),
        "min_period": min_period,
        "default_dimensions": metric_info.get("default_dimensions") if metric_info else namespace_info.get("default_dimensions", []),
        "fallback": metric_info.get("fallback") if metric_info else None,
        "caveats": metric_info.get("caveats", []) if metric_info else [],
        "known_error": metric_info.get("known_error") if metric_info else None,
        "namespace_notes": namespace_info.get("notes", []),
        "warnings": warnings,
        "next_actions": next_actions,
        "source_assets": catalog.get("source_assets", []),
    }


def discovery_args(args: argparse.Namespace, operation: str) -> SimpleNamespace:
    """Return read-only CES discovery arguments."""
    return SimpleNamespace(
        service="CES",
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=1,
        execute=args.execute,
        timeout=args.timeout,
    )


def build_readonly_plan(args: argparse.Namespace, operation: str) -> dict[str, Any]:
    """Build or execute a read-only CES discovery plan."""
    plan = hcloud_resource_discovery.build_plan(discovery_args(args, operation))
    if plan.get("success") and args.execute:
        plan = hcloud_resource_discovery.execute_plan(plan, args.timeout)
    return plan


def alarm_rule_spec(args: argparse.Namespace) -> dict[str, Any]:
    """Return a non-executable CES alarm rule draft."""
    return {
        "alarm_name": args.alarm_name,
        "namespace": args.namespace,
        "metric_name": args.metric_name,
        "dimensions": args.dimension,
        "comparison_operator": args.comparison_operator,
        "threshold": args.threshold,
        "period": args.period,
        "evaluation_periods": args.evaluation_periods,
        "statistic": args.statistic,
        "notification_enabled": args.notification_enabled,
        "planner_only": True,
        "submit_command": None,
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a CES alarm readiness and planner-only rule plan."""
    metric_plan = build_readonly_plan(args, "ListMetrics")
    alarm_plan = build_readonly_plan(args, "ListAlarmRules")
    guidance = metric_guidance(args)
    missing = [
        name
        for name in ("alarm_name", "namespace", "metric_name", "threshold")
        if getattr(args, name) in (None, "")
    ]
    rule_spec = alarm_rule_spec(args) if not missing else None
    return {
        "success": bool(metric_plan.get("success")) and bool(alarm_plan.get("success")),
        "mode": "execute" if args.execute else "plan",
        "planning_only": not args.execute,
        "service": "CES",
        "metric_discovery_plan": metric_plan,
        "existing_alarm_rules_plan": alarm_plan,
        "alarm_rule_planner": {
            "success": not missing,
            "missing_fields": missing,
            "rule_spec": rule_spec,
            "executable": False,
            "submit_command": None,
            "metric_guidance": guidance,
            "risk": {
                "level": "medium",
                "reason": "Alarm rule changes can affect notification noise and incident handling; this planner never submits changes.",
            },
        },
        "next_steps": [
            "Discover metric namespace, metric_name, and dimensions before finalizing any alarm rule.",
            "Review existing alarm rules to avoid duplicates and notification noise.",
            "Use a separate reviewed change planner before creating or modifying CES alarm rules.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", help="Explicit cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=50, help="Read-only discovery limit when supported.")
    parser.add_argument("--alarm-name", help="Draft alarm rule name.")
    parser.add_argument("--namespace", help="Draft CES metric namespace.")
    parser.add_argument("--metric-name", help="Draft CES metric name.")
    parser.add_argument("--dimension", action="append", default=[], help="Draft metric dimension as name=value. Can be repeated.")
    parser.add_argument("--comparison-operator", default=">", help="Draft comparison operator.")
    parser.add_argument("--threshold", type=float, help="Draft alarm threshold.")
    parser.add_argument("--period", type=int, default=300, help="Draft period in seconds.")
    parser.add_argument("--evaluation-periods", type=int, default=3, help="Draft consecutive evaluation periods.")
    parser.add_argument("--statistic", default="average", help="Draft statistic, for example average/max/min.")
    parser.add_argument("--notification-enabled", action="store_true", help="Draft notification flag; planner-only.")
    parser.add_argument("--execute", action="store_true", help="Execute approved read-only CES discovery commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed read-only command.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.period < 1:
        parser.error("--period must be greater than 0.")
    if args.evaluation_periods < 1:
        parser.error("--evaluation-periods must be greater than 0.")
    return args


def main() -> int:
    """Build the planner-only CES alarm plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
