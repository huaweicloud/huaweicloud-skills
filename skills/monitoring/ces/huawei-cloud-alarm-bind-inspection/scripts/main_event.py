#!/usr/bin/env python3
"""
Extract event-type alarm rules from CES alarm rules.
In CES, there are no separate "notification rules" — event information is
embedded in alarm rules with type EVENT_SYS or EVENT_CUSTOM.

This script reads online_alarm_rules.json (produced by main_alarm.py),
filters event-type rules, and outputs online_notification_rules.json
for downstream event_bind_analysis.py consumption.

Usage:
    python main_event.py
"""

import json
import logging
from pathlib import Path
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main-event")

ALARM_RULES_PATH = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")
OUTPUT_PATH = str(Path(INTERMEDIATE_DIR) / "online_notification_rules.json")

# CES alarm rule types that represent events (not metric alarms)
EVENT_TYPES = {"EVENT.SYS", "EVENT.CUSTOM"}


def _extract_service_from_namespace(namespace: str) -> str:
    """
    Extract service short name from CES namespace.
    e.g., "SYS.RDS" -> "RDS", "SYS.ECS" -> "ECS"
    """
    if not namespace:
        return ""
    parts = namespace.split(".")
    if len(parts) >= 2:
        return parts[1]
    return namespace


def _extract_event_ids(policies: list) -> list:
    """
    Extract event IDs from alarm rule policies.
    In event-type alarm rules, each policy's metric_name is the event ID.
    """
    event_ids = []
    if not policies:
        return event_ids
    for policy in policies:
        metric_name = policy.get("metric_name", "")
        if metric_name:
            event_ids.append(metric_name)
    return event_ids


def _extract_resource_ids(resources: list) -> list:
    """
    Extract resource IDs from CES alarm rule resources.
    Each resource has 'dimensions' (list of {name, value}).
    We extract the dimension values as resource identifiers.
    """
    result = []
    if not resources:
        return result
    for res in resources:
        dimensions = res.get("dimensions", [])
        dim_dict = {}
        for dim in dimensions:
            name = dim.get("name", "")
            value = dim.get("value", "")
            if name and value:
                dim_dict[name] = value
        result.append(dim_dict)
    return result


def main():
    # Read alarm rules produced by main_alarm.py
    try:
        with open(ALARM_RULES_PATH, "r", encoding="utf-8") as f:
            alarm_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Alarm rules file not found: {ALARM_RULES_PATH}. Run main_alarm.py first.")
        return

    all_rules = alarm_data.get("rules", [])
    logger.info(f"Loaded {len(all_rules)} alarm rules from {ALARM_RULES_PATH}")

    # Filter event-type rules
    event_rules = []
    for rule in all_rules:
        rule_type = rule.get("type", "")
        if rule_type not in EVENT_TYPES:
            continue
        if not rule.get("enabled", False):
            continue

        namespace = rule.get("namespace", "")
        service = _extract_service_from_namespace(namespace)
        policies = rule.get("policies", [])
        event_ids = _extract_event_ids(policies)
        resources = rule.get("resources", [])
        resource_dims = _extract_resource_ids(resources)

        event_rules.append({
            "alarm_id": rule.get("alarm_id", ""),
            "name": rule.get("name", ""),
            "namespace": namespace,
            "service": service,
            "type": rule_type,
            "enabled": rule.get("enabled", False),
            "notification_enabled": rule.get("notification_enabled", False),
            "event_ids": event_ids,
            "resources": resource_dims,
            "enterprise_project_id": rule.get("enterprise_project_id", ""),
            "region": rule.get("region", ""),
        })

    logger.info(f"Filtered {len(event_rules)} event-type alarm rules (types: {EVENT_TYPES})")

    output = {
        "total_rules": len(event_rules),
        "rules": event_rules,
    }

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
