#!/usr/bin/env python3
"""
Diagnostic script for CES event alarm rules.
Reads online_alarm_rules.json and shows event-type rules for inspection.
"""

import json
from pathlib import Path
from workspace import INTERMEDIATE_DIR

ALARM_RULES_PATH = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")

EVENT_TYPES = {"EVENT_SYS", "EVENT_CUSTOM"}


def diagnose():
    try:
        with open(ALARM_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {ALARM_RULES_PATH}. Run main_alarm.py first.")
        return

    rules = data.get("rules", [])
    print(f"Total alarm rules: {len(rules)}")

    event_rules = [r for r in rules if r.get("type", "") in EVENT_TYPES and r.get("enabled", False)]
    print(f"Event-type rules (enabled): {len(event_rules)}")

    for i, rule in enumerate(event_rules[:20]):
        print(f"\nRule {i+1} (alarm_id={rule.get('alarm_id', '')}):")
        print(f"  name: {rule.get('name', '')}")
        print(f"  namespace: {rule.get('namespace', '')}")
        print(f"  type: {rule.get('type', '')}")
        print(f"  notification_enabled: {rule.get('notification_enabled', False)}")
        policies = rule.get("policies", [])
        print(f"  policies count: {len(policies)}")
        for p in policies[:3]:
            print(f"    metric_name={p.get('metric_name', '')}, dimension_name={p.get('dimension_name', '')}")
        resources = rule.get("resources", [])
        print(f"  resources count: {len(resources)}")
        for r in resources[:3]:
            dims = r.get("dimensions", [])
            print(f"    dimensions: {json.dumps(dims, ensure_ascii=False)}")


if __name__ == "__main__":
    diagnose()
